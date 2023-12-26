from statistics import mean
from datetime import datetime, timedelta, date
from Helpers.SensorObject import SensorObject, EnergySensor
import re
import mqttapi as mqtt
import calendar
monthly_energy_prices = [""]


class UpdateEnergySensors(SensorObject):

  def initialize(self):

    ###Initialize
    self.add_sensors()
    self.read_sensors_from_namespace(*self.get_sensors())
    self.update_sensors_HA(*self.get_sensors())

    ###Functions

    #to test the functions which run at a certain time: "(datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S")"

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
