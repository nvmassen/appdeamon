from datetime import datetime, timedelta, date  # timedelta: used by the commented-out test schedules
from helpers.ad_helpers import SensorObject, EnergySensor
import calendar

class UpdateEnergySensors(SensorObject):

  def initialize(self):

    ###Initialize
    self.add_sensors()
    self.read_sensors_from_namespace(*self.get_sensors())
    self.update_sensors_HA(*self.get_sensors())

    ###Functions

    #to test the functions which run at a certain time: "(datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S")"

    ###Belpex monthly price and monthly energy prices are template sensors in HA (configuration.yaml)

    ###update monthly quarterly peak values and monthly energy prices
    #checks every day and at start, so a rollover missed while AppDaemon was down runs at the next start
    self.run_daily(self.check_month_rollover, "00:00:01")
    self.check_month_rollover()
    #self.run_daily(self.check_month_rollover, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))
    self.update_quarterly_peak()


    
    ###Read quarterly peak from HA (Value taken from P1 meter)
    self.run_daily(self.update_quarterly_peak, "08:00:00")
    self.run_daily(self.update_quarterly_peak, "20:00:00")
    #self.run_daily(self.update_quarterly_peak, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))

    ###Hack to minor change calculated quarterly peak in HA to keep it stored in the appdeamon database
    self.run_daily(self.update_self_calculated_quarterly_peak_for_db, "00:00:01")
    #self.run_daily(self.update_self_calculated_quarterly_peak_for_db, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))

    ###Function to manualy input values in appdaemon database
    #self.set_sensors("sensor.monthly_energy_price_production_low_12", 0.03)

  def add_sensors(self):
    #Monthly quarterly peak
    self.add_sensor(EnergySensor("sensor.DSMR_quarterly_peak", "DSMR Quarterly Peak", "kW"))

    #Daily gas price
    self.add_sensor(EnergySensor("sensor.gas_daily_price", "Gas Daily Price", "EUR/MWh"))
    
    #Holders for monthly quarterly peaks and electricity prices to store them for 12 months
    num = datetime.now().month - 1
    year = datetime.now().year
    temp = []

    for i in range (12,-1,-1):
      if (num - i) != 0:
        if (num-i) < 0:
          temp.append(f"{calendar.month_name[num - i]} {year - 1}")
        else:
          temp.append(f"{calendar.month_name[num - i]} {year}")

    for i in range(1,13):
      self.add_sensor(EnergySensor(f"sensor.quarterly_peak_month_{i}", temp[i-1], "kW"))

    for i in range(1,13):
      self.add_sensor(EnergySensor(f"sensor.monthly_energy_price_consumption_normal_{i}", temp[i-1], "EUR/kWh"))
      self.add_sensor(EnergySensor(f"sensor.monthly_energy_price_consumption_low_{i}", temp[i-1], "EUR/kWh"))
      self.add_sensor(EnergySensor(f"sensor.monthly_energy_price_production_normal_{i}", temp[i-1], "EUR/kWh"))
      self.add_sensor(EnergySensor(f"sensor.monthly_energy_price_production_low_{i}", temp[i-1], "EUR/kWh"))

  def check_month_rollover(self, **kwargs):
    '''
    Shift the 12 monthly slots once for every month that started since the last rollover.
    The month of the last rollover is kept in the ha_sensors namespace, so a missed 1st is caught up at the next run.
    '''
    try:
      current_month = date.today().strftime("%Y-%m")
      last_month = self.get_rollover_month()

      if last_month is None:
        self.log(f"No rollover month stored, starting from {current_month}")
        self.set_rollover_month(current_month)
        return

      while last_month < current_month:
        year, month = (int(x) for x in last_month.split("-"))
        new_month = f"{year + month // 12}-{month % 12 + 1:02d}"
        self.log(f"Month rollover: closing {last_month}, starting {new_month}")
        self.update_monthly_values_db(last_month, new_month)
        self.set_rollover_month(new_month)
        last_month = new_month

    except Exception as e:
      self.log(f"Error checking month rollover: {e}", level="ERROR")


  def get_rollover_month(self):
    try:
      return self.get_entity("sensor.monthly_rollover_month", "ha_sensors").state
    except Exception:
      return None


  def set_rollover_month(self, month):
    self.set_state("sensor.monthly_rollover_month", state=month, namespace="ha_sensors")


  def get_closed_month_price(self, entity_id, closed_month):
    '''
    Price of the closed month from the HA template sensor: its state while it still holds that month, else its previous_value
    '''
    state = self.get_state(entity_id, attribute="all") or {}
    attributes = state.get("attributes", {})
    try:
      if attributes.get("month") == closed_month:
        return float(state.get("state"))
      if attributes.get("previous_month") == closed_month:
        return float(attributes.get("previous_value"))
    except (ValueError, TypeError):
      pass
    self.log(f"No value for {closed_month} in {entity_id}, storing 0", level="WARNING")
    return 0


  def update_monthly_values_db(self, closed_month, new_month):
    try:

      #friendly names of the closed month (slot 12) and the new month
      closed_year, closed_num = (int(x) for x in closed_month.split("-"))
      new_year, new_num = (int(x) for x in new_month.split("-"))
      friendly_name_month_12 = f"{calendar.month_name[closed_num]} {closed_year}"
      friendly_name_current_month = f"{calendar.month_name[new_num]} {new_year}"

      #Quarterly peakes
      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.quarterly_peak_month_{i+1}")
        self.set_sensor_value(f"sensor.quarterly_peak_month_{i}", value)

        friendly_name = self.get_sensor_friendly_name(f"sensor.quarterly_peak_month_{i+1}")
        self.set_sensor_friendly_name(f"sensor.quarterly_peak_month_{i}", friendly_name)

      self.set_sensor_value("sensor.quarterly_peak_month_12", self.get_sensor_value("sensor.DSMR_quarterly_peak"))
      self.set_sensor_friendly_name("sensor.quarterly_peak_month_12", friendly_name_month_12)

      self.set_sensor_value("sensor.DSMR_quarterly_peak",0)
      self.set_sensor_friendly_name("sensor.DSMR_quarterly_peak", friendly_name_current_month)


      #Monthly energy prices
      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_consumption_normal_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_consumption_normal_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_consumption_normal_12", self.get_closed_month_price("sensor.monthly_energy_price_consumption_normal", closed_month))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_consumption_normal_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_consumption_low_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_consumption_low_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_consumption_low_12", self.get_closed_month_price("sensor.monthly_energy_price_consumption_low", closed_month))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_consumption_low_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_production_normal_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_production_normal_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_production_normal_12", self.get_closed_month_price("sensor.monthly_energy_price_production_normal", closed_month))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_production_normal_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_production_low_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_production_low_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_production_low_12", self.get_closed_month_price("sensor.monthly_energy_price_production_low", closed_month))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_production_low_12", friendly_name_month_12)

      #Write to namespace and update HA
      for i in range(1,13):
        self.write_sensors_to_namespace(f"sensor.quarterly_peak_month_{i}")
        self.update_sensors_HA(f"sensor.quarterly_peak_month_{i}")

        self.write_sensors_to_namespace(f"sensor.monthly_energy_price_consumption_normal_{i}")
        self.update_sensors_HA(f"sensor.monthly_energy_price_consumption_normal_{i}")

        self.write_sensors_to_namespace(f"sensor.monthly_energy_price_consumption_low_{i}")
        self.update_sensors_HA(f"sensor.monthly_energy_price_consumption_low_{i}")

        self.write_sensors_to_namespace(f"sensor.monthly_energy_price_production_normal_{i}")
        self.update_sensors_HA(f"sensor.monthly_energy_price_production_normal_{i}")

        self.write_sensors_to_namespace(f"sensor.monthly_energy_price_production_low_{i}")
        self.update_sensors_HA(f"sensor.monthly_energy_price_production_low_{i}")

      self.write_sensors_to_namespace("sensor.DSMR_quarterly_peak")
      self.update_sensors_HA("sensor.DSMR_quarterly_peak")
    
    except Exception as e:
      self.log(f"Error updating monthly values in database: {e}", level="ERROR")


  def update_quarterly_peak(self, **kwargs):
    '''
    Update sensor in APPDAEMON with error handling
    '''
    try:
      state = self.get_state("sensor.p1_meter_peak_demand_current_month")
      
      if state is None or state == "unavailable" or state == "unknown":
        self.log("P1 meter peak demand sensor unavailable, skipping update", level="WARNING")
        return
      
      try:
        value = float(state) / 1000  # conversion from W to kW
      except (ValueError, TypeError) as e:
        self.log(f"Failed to convert peak demand to float: {e}", level="ERROR")
        return

      self.log(f"The peak value is: {value} kW")

      if value != self.get_sensor_value("sensor.DSMR_quarterly_peak"):
        self.set_sensor_value("sensor.DSMR_quarterly_peak", value)
        self.write_sensors_to_namespace("sensor.DSMR_quarterly_peak")
        self.update_sensors_HA("sensor.DSMR_quarterly_peak")
    
    except Exception as e:
      self.log(f"Error updating quarterly peak: {e}", level="ERROR")

  def set_sensors(self, entity_id, value):
    '''
    Manual sensor setting for debugging
    '''
    try:
      self.set_sensor_value(entity_id, value)
      self.write_sensors_to_namespace(entity_id)
    except Exception as e:
      self.log(f"Error setting sensor {entity_id}: {e}", level="ERROR")


  def update_self_calculated_quarterly_peak_for_db(self, **kwargs):
    """
    Method to update the sensor 'sensor.electricity_delivery_power_monthly_15m_max' to trigger an update in the HA database 
    """
    try:
      state = self.get_state("sensor.electricity_delivery_power_monthly_15m_max")
      
      if state is None or state == "unavailable" or state == "unknown":
        self.log("Electricity delivery power sensor unavailable", level="WARNING")
        return
      
      try:
        value = float(state)
      except (ValueError, TypeError) as e:
        self.log(f"Failed to convert electricity delivery power to float: {e}", level="ERROR")
        return
      
      if (date.today().day % 2 == 0):
        new_value = round((value - 0.01), 2)
      else:
        new_value = round((value + 0.01), 2)
      
      self.set_state("sensor.electricity_delivery_power_monthly_15m_max", 
                     state=new_value, 
                     attributes={"unit_of_measurement": "kW",
                                "friendly_name": "Electricity Delivery Power Monthly 15m Max"})
    
    except Exception as e:
      self.log(f"Error updating self-calculated quarterly peak: {e}", level="ERROR")
