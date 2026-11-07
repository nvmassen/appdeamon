import pytest

import update_energy_sensors as ues

TARIFFS = {
    "sensor.consumption_tarive_normal": "0.48",
    "sensor.consumption_tarive_low": "0.43",
    "sensor.production_tarive_normal": "0.20",
    "sensor.production_tarive_low": "0.10",
}
MONTHLY = "sensor.monthly_energy_price_"


def make_app(freeze_today, day, month=11, year=2026):
    freeze_today(ues, year, month, day)
    app = ues.UpdateEnergySensors()
    app.add_sensors()
    return app


def errors(app):
    return [msg for level, msg in app.logs if level == "ERROR"]


# --- initialize / add_sensors


def test_initialize_schedules_all_jobs(freeze_today):
    freeze_today(ues, 2026, 11, 7)
    app = ues.UpdateEnergySensors()
    app.initialize()
    names = sorted(name for name, _ in app.schedules)
    assert names == sorted([
        "update_belpex_monthly_price",
        "update_monthly_energy_prices",
        "update_monthly_values_db",
        "update_quarterly_peak",
        "update_quarterly_peak",
        "update_self_calculated_quarterly_peak_for_db",
    ])


def test_initialize_reads_namespace_and_pushes_to_ha(freeze_today):
    freeze_today(ues, 2026, 11, 7)
    app = ues.UpdateEnergySensors()
    app.namespaces["ha_sensors"] = {"sensor.belpex_monthly_price": 123.4}
    app.initialize()
    assert app.get_sensor_value("sensor.belpex_monthly_price") == 123.4
    assert app.ha_written["sensor.belpex_monthly_price"]["state"] == "123.4"


@pytest.mark.parametrize("month, year, first, last", [
    (11, 2026, "November 2025", "October 2026"),
    (1, 2026, "January 2025", "December 2025"),
    (12, 2026, "December 2025", "November 2026"),
])
def test_history_labels_cover_the_last_12_months(freeze_today, month, year, first, last):
    app = make_app(freeze_today, 15, month, year)
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_1") == first
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == last
    assert app.get_sensor_friendly_name(f"{MONTHLY}production_low_12") == last


# --- update_belpex_monthly_price


def test_belpex_running_average(freeze_today):
    app = make_app(freeze_today, 7)
    app.set_sensor_value("sensor.belpex_monthly_price", 100.0)
    app.set_sensor_value("sensor.belpex_monthly_price_amount_of_days", 2)
    app.ha_states["sensor.belpex_daily_price"] = "160"
    app.update_belpex_monthly_price()
    assert app.get_sensor_value("sensor.belpex_monthly_price_amount_of_days") == 3
    assert app.get_sensor_value("sensor.belpex_monthly_price") == 120.0
    assert app.namespaces["ha_sensors"]["sensor.belpex_monthly_price"] == 120.0
    assert app.ha_written["sensor.belpex_monthly_price"]["state"] == "120.0"


def test_belpex_first_of_month_starts_a_new_average(freeze_today):
    app = make_app(freeze_today, 1)
    app.set_sensor_value("sensor.belpex_monthly_price", 100.0)
    app.set_sensor_value("sensor.belpex_monthly_price_amount_of_days", 30)
    app.ha_states["sensor.belpex_daily_price"] = "80.5"
    app.update_belpex_monthly_price()
    assert app.get_sensor_value("sensor.belpex_monthly_price_amount_of_days") == 1
    assert app.get_sensor_value("sensor.belpex_monthly_price") == 80.5


def test_belpex_zero_price_does_not_count_as_a_day(freeze_today):
    app = make_app(freeze_today, 7)
    app.set_sensor_value("sensor.belpex_monthly_price", 100.0)
    app.set_sensor_value("sensor.belpex_monthly_price_amount_of_days", 2)
    app.ha_states["sensor.belpex_daily_price"] = "0"
    app.update_belpex_monthly_price()
    assert app.get_sensor_value("sensor.belpex_monthly_price_amount_of_days") == 2
    assert app.get_sensor_value("sensor.belpex_monthly_price") == 100.0


@pytest.mark.parametrize("state", [None, "unavailable", "unknown", "not a number"])
def test_belpex_bad_daily_price_changes_nothing(freeze_today, state):
    app = make_app(freeze_today, 7)
    app.set_sensor_value("sensor.belpex_monthly_price", 100.0)
    app.ha_states["sensor.belpex_daily_price"] = state
    app.update_belpex_monthly_price()
    assert app.get_sensor_value("sensor.belpex_monthly_price") == 100.0
    assert app.ha_written == {}
    assert any(level in ("WARNING", "ERROR") for level, _ in app.logs)


# --- update_monthly_energy_prices


def test_energy_prices_running_average(freeze_today):
    app = make_app(freeze_today, 7)
    for kind in ("consumption_normal", "consumption_low", "production_normal", "production_low"):
        app.set_sensor_value(f"{MONTHLY}{kind}", 0.30)
    app.set_sensor_value(f"{MONTHLY}amount_of_days", 2)
    app.ha_states.update(TARIFFS)
    app.update_monthly_energy_prices()
    assert errors(app) == []
    assert app.get_sensor_value(f"{MONTHLY}amount_of_days") == 3
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal") == 0.36  # (0.30*2 + 0.48) / 3
    assert app.get_sensor_value(f"{MONTHLY}production_low") == 0.23  # (0.30*2 + 0.10) / 3
    assert app.ha_written[f"{MONTHLY}amount_of_days"]["state"] == "3"


def test_energy_prices_first_of_month_starts_a_new_average(freeze_today):
    app = make_app(freeze_today, 1)
    app.set_sensor_value(f"{MONTHLY}consumption_normal", 0.30)
    app.set_sensor_value(f"{MONTHLY}amount_of_days", 31)
    app.ha_states.update(TARIFFS)
    app.update_monthly_energy_prices()
    assert app.get_sensor_value(f"{MONTHLY}amount_of_days") == 1
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal") == 0.48


@pytest.mark.parametrize("sensor, value", [
    ("sensor.production_tarive_low", "0"),
    ("sensor.production_tarive_normal", "0"),
    ("sensor.consumption_tarive_low", "0.0"),
    # Before the fix, only production_low was compared with 0, so this day counted
    ("sensor.production_tarive_normal", "-0.02"),
])
def test_energy_prices_skip_the_day_unless_all_tariffs_are_positive(freeze_today, sensor, value):
    app = make_app(freeze_today, 7)
    app.set_sensor_value(f"{MONTHLY}production_normal", 0.10)
    app.set_sensor_value(f"{MONTHLY}amount_of_days", 2)
    app.ha_states.update(TARIFFS)
    app.ha_states[sensor] = value
    app.update_monthly_energy_prices()
    assert app.get_sensor_value(f"{MONTHLY}amount_of_days") == 2
    assert app.get_sensor_value(f"{MONTHLY}production_normal") == 0.10


@pytest.mark.parametrize("state", [None, "unavailable", "unknown", "abc"])
def test_energy_prices_bad_tariff_changes_nothing(freeze_today, state):
    app = make_app(freeze_today, 7)
    app.set_sensor_value(f"{MONTHLY}amount_of_days", 2)
    app.ha_states.update(TARIFFS)
    app.ha_states["sensor.consumption_tarive_low"] = state
    app.update_monthly_energy_prices()
    assert app.get_sensor_value(f"{MONTHLY}amount_of_days") == 2
    assert app.ha_written == {}


# --- update_monthly_values_db


def fill_history(app):
    for i in range(1, 13):
        app.set_sensor_value(f"sensor.quarterly_peak_month_{i}", float(i))
        app.set_sensor_value(f"{MONTHLY}consumption_normal_{i}", i / 100)
    app.set_sensor_value("sensor.DSMR_quarterly_peak", 4.2)
    app.set_sensor_value(f"{MONTHLY}consumption_normal", 0.55)


def test_month_rollover_shifts_history_by_one(freeze_today):
    app = make_app(freeze_today, 1, 11, 2026)
    fill_history(app)
    app.update_monthly_values_db()
    assert errors(app) == []
    assert app.get_sensor_value("sensor.quarterly_peak_month_1") == 2.0
    assert app.get_sensor_value("sensor.quarterly_peak_month_11") == 12.0
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 4.2
    assert app.get_sensor_value("sensor.DSMR_quarterly_peak") == 0
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_11") == 0.12
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_12") == 0.55
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == "October 2026"
    assert app.get_sensor_friendly_name("sensor.DSMR_quarterly_peak") == "November 2026"
    assert app.ha_written["sensor.quarterly_peak_month_12"]["state"] == "4.2"


def test_month_rollover_in_january_labels_december_of_last_year(freeze_today):
    app = make_app(freeze_today, 1, 1, 2027)
    fill_history(app)
    app.update_monthly_values_db()
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == "December 2026"
    assert app.get_sensor_friendly_name("sensor.DSMR_quarterly_peak") == "January 2027"


def test_no_rollover_after_the_first(freeze_today):
    app = make_app(freeze_today, 2)
    fill_history(app)
    app.update_monthly_values_db()
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 12.0
    assert app.ha_written == {}


# --- update_quarterly_peak


def test_quarterly_peak_converts_w_to_kw(freeze_today):
    app = make_app(freeze_today, 7)
    app.ha_states["sensor.p1_meter_peak_demand_current_month"] = "3250"
    app.update_quarterly_peak()
    assert app.get_sensor_value("sensor.DSMR_quarterly_peak") == 3.25
    assert app.ha_written["sensor.DSMR_quarterly_peak"]["state"] == "3.25"


def test_quarterly_peak_unchanged_is_not_written(freeze_today):
    app = make_app(freeze_today, 7)
    app.set_sensor_value("sensor.DSMR_quarterly_peak", 3.25)
    app.ha_states["sensor.p1_meter_peak_demand_current_month"] = "3250"
    app.update_quarterly_peak()
    assert app.ha_written == {}


def test_quarterly_peak_unavailable_changes_nothing(freeze_today):
    app = make_app(freeze_today, 7)
    app.set_sensor_value("sensor.DSMR_quarterly_peak", 3.25)
    app.ha_states["sensor.p1_meter_peak_demand_current_month"] = "unavailable"
    app.update_quarterly_peak()
    assert app.get_sensor_value("sensor.DSMR_quarterly_peak") == 3.25
    assert app.ha_written == {}


# --- update_self_calculated_quarterly_peak_for_db


@pytest.mark.parametrize("day, expected", [(6, 2.99), (7, 3.01)])
def test_self_calculated_peak_nudges_value_each_day(freeze_today, day, expected):
    app = make_app(freeze_today, day)
    app.ha_states["sensor.electricity_delivery_power_monthly_15m_max"] = "3.0"
    app.update_self_calculated_quarterly_peak_for_db()
    assert app.ha_written["sensor.electricity_delivery_power_monthly_15m_max"]["state"] == expected
