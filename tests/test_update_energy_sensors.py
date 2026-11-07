import pytest

import update_energy_sensors as ues

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
        "check_month_rollover",
        "update_quarterly_peak",
        "update_quarterly_peak",
        "update_self_calculated_quarterly_peak_for_db",
    ])


def test_initialize_reads_namespace_and_pushes_to_ha(freeze_today):
    freeze_today(ues, 2026, 11, 7)
    app = ues.UpdateEnergySensors()
    app.namespaces["ha_sensors"] = {"sensor.quarterly_peak_month_12": 2.76}
    app.initialize()
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 2.76
    assert app.ha_written["sensor.quarterly_peak_month_12"]["state"] == "2.76"


def test_initialize_does_not_write_the_monthly_prices_owned_by_ha(freeze_today):
    freeze_today(ues, 2026, 11, 7)
    app = ues.UpdateEnergySensors()
    app.initialize()
    assert "sensor.belpex_monthly_price" not in app.ha_written
    assert f"{MONTHLY}consumption_normal" not in app.ha_written


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


# --- month rollover


KINDS = ("consumption_normal", "consumption_low", "production_normal", "production_low")


def fill_history(app):
    for i in range(1, 13):
        app.set_sensor_value(f"sensor.quarterly_peak_month_{i}", float(i))
        app.set_sensor_value(f"{MONTHLY}consumption_normal_{i}", i / 100)
    app.set_sensor_value("sensor.DSMR_quarterly_peak", 4.2)


def set_ha_price(app, kind, state, month, previous_month=None, previous_value=None):
    """HA template sensor for a monthly price: state for its month, previous_* for the closed month."""
    app.ha_states[f"{MONTHLY}{kind}"] = state
    app.ha_attributes[f"{MONTHLY}{kind}"] = {
        "month": month, "previous_month": previous_month, "previous_value": previous_value}


def set_ha_prices_still_in(app, month, value=0.55):
    for kind in KINDS:
        set_ha_price(app, kind, str(value), month)


def rollover_months(app):
    return app.namespaces["ha_sensors"]["sensor.monthly_rollover_month"]


def test_first_run_stores_the_month_without_rollover(freeze_today):
    app = make_app(freeze_today, 7)
    fill_history(app)
    app.check_month_rollover()
    assert rollover_months(app) == "2026-11"
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 12.0
    assert app.ha_written == {}


def test_no_rollover_in_the_same_month(freeze_today):
    app = make_app(freeze_today, 2)
    fill_history(app)
    app.set_rollover_month("2026-11")
    app.check_month_rollover()
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 12.0
    assert app.ha_written == {}


def test_month_rollover_shifts_history_by_one(freeze_today):
    app = make_app(freeze_today, 1, 11, 2026)
    fill_history(app)
    set_ha_prices_still_in(app, "2026-10")
    app.set_rollover_month("2026-10")
    app.check_month_rollover()
    assert errors(app) == []
    assert rollover_months(app) == "2026-11"
    assert app.get_sensor_value("sensor.quarterly_peak_month_1") == 2.0
    assert app.get_sensor_value("sensor.quarterly_peak_month_11") == 12.0
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 4.2
    assert app.get_sensor_value("sensor.DSMR_quarterly_peak") == 0
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_11") == 0.12
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_12") == 0.55
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == "October 2026"
    assert app.get_sensor_friendly_name("sensor.DSMR_quarterly_peak") == "November 2026"
    assert app.ha_written["sensor.quarterly_peak_month_12"]["state"] == "4.2"
    assert app.namespaces["ha_sensors"][f"{MONTHLY}production_low_12"] == 0.55


def test_month_rollover_in_january_labels_december_of_last_year(freeze_today):
    app = make_app(freeze_today, 1, 1, 2027)
    fill_history(app)
    set_ha_prices_still_in(app, "2026-12")
    app.set_rollover_month("2026-12")
    app.check_month_rollover()
    assert rollover_months(app) == "2027-01"
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == "December 2026"
    assert app.get_sensor_friendly_name("sensor.DSMR_quarterly_peak") == "January 2027"


def test_missed_first_of_month_is_caught_up_later(freeze_today):
    # AppDaemon was down on 1 Nov; the HA sensors already started November and keep October in previous_*
    app = make_app(freeze_today, 7, 11, 2026)
    fill_history(app)
    for kind in KINDS:
        set_ha_price(app, kind, "0.47", "2026-11", previous_month="2026-10", previous_value=0.39)
    app.set_rollover_month("2026-10")
    app.check_month_rollover()
    assert errors(app) == []
    assert rollover_months(app) == "2026-11"
    assert app.get_sensor_value("sensor.quarterly_peak_month_12") == 4.2
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_12") == 0.39
    assert app.get_sensor_friendly_name(f"{MONTHLY}consumption_normal_12") == "October 2026"


def test_two_missed_months_shift_twice_and_warn_for_the_unknown_month(freeze_today):
    app = make_app(freeze_today, 3, 12, 2026)
    fill_history(app)
    for kind in KINDS:
        set_ha_price(app, kind, "0.47", "2026-12", previous_month="2026-11", previous_value=0.45)
    app.set_rollover_month("2026-10")
    app.check_month_rollover()
    assert rollover_months(app) == "2026-12"
    assert app.get_sensor_value("sensor.quarterly_peak_month_10") == 12.0
    assert app.get_sensor_value("sensor.quarterly_peak_month_11") == 4.2  # October
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_11") == 0  # October price is no longer in HA
    assert app.get_sensor_value(f"{MONTHLY}consumption_normal_12") == 0.45  # November
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_11") == "October 2026"
    assert app.get_sensor_friendly_name("sensor.quarterly_peak_month_12") == "November 2026"
    assert any(level == "WARNING" and "2026-10" in msg for level, msg in app.logs)


@pytest.mark.parametrize("state, attributes", [
    (None, None),  # sensor missing in HA
    ("unavailable", {"month": "2026-10"}),
    ("0.40", {"month": "2026-09"}),  # neither the current nor the previous month matches
])
def test_closed_month_price_without_a_value_is_0_with_a_warning(freeze_today, state, attributes):
    app = make_app(freeze_today, 1)
    if state is not None:
        app.ha_states[f"{MONTHLY}consumption_low"] = state
        app.ha_attributes[f"{MONTHLY}consumption_low"] = attributes
    assert app.get_closed_month_price(f"{MONTHLY}consumption_low", "2026-10") == 0
    assert any(level == "WARNING" for level, _ in app.logs)


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
