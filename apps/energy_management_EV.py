from statistics import mean
from datetime import datetime, timedelta, date
from Helpers.SensorObject import SensorObject, EnergySensor
import re
import appdaemon.plugins.mqtt.mqttapi as mqtt
import calendar


class EnergyManagementEV(SensorObject):

  def initialize(self):

    ###Initialize
    self.add_sensors()
    self.read_sensors_from_namespace(*self.get_sensors())
    self.update_sensors_HA(*self.get_sensors())

    self.listen_state(self.car_charging_now, "input_boolean.ev_charge_now")
    self.listen_state(self.car_charging_now, "binary_sensor.car_charging_peak_consumption_above_limit")

    ###Functions


    ###update once a day belpex monthly price
    #self.run_daily(self.update_belpex_monthly_price, "16:00:01")
    #self.run_daily(self.update_belpex_monthly_price, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))


    ###update once a day monthly energy prices
    #self.run_daily(self.update_monthly_energy_prices, "16:00:01")
    #self.run_daily(self.update_monthly_energy_prices, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))


    ###update monthly quarterly peak values and monthly energy prices
    #self.run_daily(self.update_monthly_values_db, "00:00:01")
    #self.run_daily(self.update_monthly_values_db, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))

    
    ###Read quarterly peak from HA (Value taken from P1 meter)
    #self.run_daily(self.update_quarterly_peak, "08:00:00")
    #self.run_daily(self.update_quarterly_peak, "20:00:00")
    #self.run_daily(self.update_quarterly_peak, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))


    ###Hack to minor change calculated quarterly peak in HA to keep it stored in the appdeamon database
    #self.run_daily(self.update_self_calculated_quarterly_peak_for_db, "00:00:01")
    #self.run_daily(self.update_self_calculated_quarterly_peak_for_db, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))


    ###Function to manualy input values in appdaemon database
    #self.set_sensors()

  def add_sensors(self):
    return
    #Monthly Belpex price and amount of days to calculate monthly Belpex price
    #self.add_sensor(EnergySensor("sensor.belpex_monthly_price", "Belpex Monthly Price", "EUR/kWh"))

  def car_charging_now(self, *args, **kwargs):
    '''
    Function to switch on and off the charging of the EV
    '''

    boiler_charging_needed = True if self.entities.binary_sensor.boiler_charging_needed == "on" else False
    charge_now = True if self.entities.input_boolean.ev_charge_now.state == "on" else False
    peak_consumption_above_limit = True if self.entities.binary_sensor.car_charging_peak_consumption_above_limit == "on" else False
    charging_on = True if self.entities.switch.stopcontact_wagen == "on" else False

    #self.log(entity)
    #self.log(new)
    self.log(args)

    if charge_now:
      #self.turn_off("automation.car_charging_off_coming_home_after_work")
      #self.turn_off("automation.car_charging_off_day_cloudy")
      #self.turn_off("automation.car_charging_off_day_sunny")
      #self.turn_off("automation.car_charging_off_night")
      if not peak_consumption_above_limit:
        while not charging_on:
          self.turn_on("switch.stopcontact_wagen")
          charging_on = True if self.entities.switch.stopcontact_wagen == "on" else False
      
