from statistics import mean
from datetime import datetime, timedelta, date
from helpers.ad_helpers import SensorObject, EnergySensor
import re
import calendar
import requests
import bs4



class UpdateEnergySensors(SensorObject):

  def initialize(self):

    ###Initialize
    self.add_sensors()
    self.read_sensors_from_namespace(*self.get_sensors())
    self.update_sensors_HA(*self.get_sensors())

    ###Functions

    #to test the functions which run at a certain time: "(datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S")"

    ###update once a day belpex monthly price
    self.run_daily(self.update_belpex_monthly_price, "16:00:01")
    #self.run_daily(self.update_belpex_monthly_price, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))



    ###update once a day monthly energy prices
    self.run_daily(self.update_monthly_energy_prices, "16:00:01")
    #self.run_daily(self.update_monthly_energy_prices, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))



    ###update monthly quarterly peak values and monthly energy prices
    self.run_daily(self.update_monthly_values_db, "00:00:01")
    #self.run_daily(self.update_monthly_values_db, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))


    
    ###Read quarterly peak from HA (Value taken from P1 meter)
    self.run_daily(self.update_quarterly_peak, "08:00:00")
    self.run_daily(self.update_quarterly_peak, "20:00:00")
    #self.run_daily(self.update_quarterly_peak, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))



    ###Hack to minor change calculated quarterly peak in HA to keep it stored in the appdeamon database
    self.run_daily(self.update_self_calculated_quarterly_peak_for_db, "00:00:01")
    #self.run_daily(self.update_self_calculated_quarterly_peak_for_db, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))



    #Get daily gasprize from internet and update sensor in HA
    self.run_daily(self.set_daily_gas_price, "15:45:00")
    #self.run_daily(self.set_daily_gas_price, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))



    ###Function to manualy input values in appdaemon database
    #self.set_sensors()

  def add_sensors(self):
    #Monthly Belpex price and amount of days to calculate monthly Belpex price
    self.add_sensor(EnergySensor("sensor.belpex_monthly_price", "Belpex Monthly Price", "EUR/MWh"))
    self.add_sensor(EnergySensor("sensor.belpex_monthly_price_amount_of_days", "Belpex Monthly Price Amount Of Days", "days"))

    #Monthly energy price and amount of days to calculate monthly energy price
    self.add_sensor(EnergySensor("sensor.monthly_energy_price_consumption_normal", "Monthly Energy Price Consumption Normal", "EUR/kWh"))
    self.add_sensor(EnergySensor("sensor.monthly_energy_price_consumption_low", "Monthly Energy Price Consumption Low", "EUR/kWh"))
    self.add_sensor(EnergySensor("sensor.monthly_energy_price_production_normal", "Monthly Energy Price Production Normal", "EUR/kWh"))
    self.add_sensor(EnergySensor("sensor.monthly_energy_price_production_low", "Monthly Energy Price Production Low", "EUR/kWh"))
    self.add_sensor(EnergySensor("sensor.monthly_energy_price_amount_of_days", "Monthly Energy Price Amount Of Days", "days"))

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

  def update_belpex_monthly_price(self, **kwargs):
    '''
    Update belpex monthly price with 
    '''

    lst = []
    
    if date.today().day == 1:    
      belpex_monthly_price = 0
      belpex_monthly_price_amount_of_days = 0
    else:
      belpex_monthly_price = self.get_sensor_value("sensor.belpex_monthly_price")
      belpex_monthly_price_amount_of_days = self.get_sensor_value("sensor.belpex_monthly_price_amount_of_days")

    for i in range(7):
      value = float(self.get_state(f"sensor.belpex{i+1}"))
      if (value > 0):
        lst.append(value)
    
    belpex_daily_price = round(mean(lst),2)

    if belpex_daily_price > 0:
      belpex_monthly_price_amount_of_days+=1
      belpex_monthly_price = round((belpex_monthly_price * (belpex_monthly_price_amount_of_days-1) + belpex_daily_price) / belpex_monthly_price_amount_of_days,2)

    self.set_sensor_value("sensor.belpex_monthly_price", belpex_monthly_price)
    self.set_sensor_value("sensor.belpex_monthly_price_amount_of_days", belpex_monthly_price_amount_of_days)

    self.write_sensors_to_namespace("sensor.belpex_monthly_price","sensor.belpex_monthly_price_amount_of_days")
    self.update_sensors_HA("sensor.belpex_monthly_price","sensor.belpex_monthly_price_amount_of_days")


  def update_monthly_energy_prices(self, **kwargs):
    '''
    Update monthly energy prices once a day
    '''
    try:
      daily_energy_price_consumption_normal = float(self.get_state(f"sensor.consumption_tarive_normal"))
      daily_energy_price_consumption_low = float(self.get_state(f"sensor.consumption_tarive_low"))
      daily_energy_price_production_normal = float(self.get_state(f"sensor.production_tarive_normal"))
      daily_energy_price_production_low = float(self.get_state(f"sensor.production_tarive_low"))
    except:
      self.log('Necessary sensors not available')
      return

    #initialize
    monthly_energy_price_consumption_normal = 0
    monthly_energy_price_consumption_low = 0
    monthly_energy_price_production_normal = 0
    monthly_energy_price_production_low = 0
    monthly_energy_price_amount_of_days = 0

    #only if date is not the first, then the prices should be updated with the values from ha_sensors
    if date.today().day > 1:
      monthly_energy_price_consumption_normal = self.get_sensor_value("sensor.monthly_energy_price_consumption_normal")
      monthly_energy_price_consumption_low = self.get_sensor_value("sensor.monthly_energy_price_consumption_low")
      monthly_energy_price_production_normal = self.get_sensor_value("sensor.monthly_energy_price_production_normal")
      monthly_energy_price_production_low = self.get_sensor_value("sensor.monthly_energy_price_production_low")
      monthly_energy_price_amount_of_days = self.get_sensor_value("sensor.monthly_energy_price_amount_of_days")

    if (daily_energy_price_consumption_normal and daily_energy_price_consumption_low  and daily_energy_price_production_normal  and daily_energy_price_production_low) > 0:
      monthly_energy_price_amount_of_days+=1
      monthly_energy_price_consumption_normal = round((monthly_energy_price_consumption_normal * (monthly_energy_price_amount_of_days-1) + daily_energy_price_consumption_normal) / monthly_energy_price_amount_of_days,2)
      monthly_energy_price_consumption_low = round((monthly_energy_price_consumption_low * (monthly_energy_price_amount_of_days-1) + daily_energy_price_consumption_low) / monthly_energy_price_amount_of_days,2)
      monthly_energy_price_production_normal = round((monthly_energy_price_production_normal * (monthly_energy_price_amount_of_days-1) + daily_energy_price_production_normal) / monthly_energy_price_amount_of_days,2)
      monthly_energy_price_production_low = round((monthly_energy_price_production_low * (monthly_energy_price_amount_of_days-1) + daily_energy_price_production_low) / monthly_energy_price_amount_of_days,2)

    self.set_sensor_value("sensor.monthly_energy_price_consumption_normal", monthly_energy_price_consumption_normal)
    self.set_sensor_value("sensor.monthly_energy_price_consumption_low", monthly_energy_price_consumption_low)
    self.set_sensor_value("sensor.monthly_energy_price_production_normal", monthly_energy_price_production_normal)
    self.set_sensor_value("sensor.monthly_energy_price_production_low", monthly_energy_price_production_low)
    self.set_sensor_value("sensor.monthly_energy_price_amount_of_days", monthly_energy_price_amount_of_days)

    self.write_sensors_to_namespace("sensor.monthly_energy_price_consumption_normal","sensor.monthly_energy_price_consumption_low","sensor.monthly_energy_price_production_normal","sensor.monthly_energy_price_production_low","sensor.monthly_energy_price_amount_of_days")
    self.update_sensors_HA("sensor.monthly_energy_price_consumption_normal","sensor.monthly_energy_price_consumption_low","sensor.monthly_energy_price_production_normal","sensor.monthly_energy_price_production_low","sensor.monthly_energy_price_amount_of_days")


  def update_monthly_values_db(self, **kwargs):
    if (date.today().day == 1):

      #Get current month and year to update friendly name sensors
      month = datetime.now().month
      year = datetime.now().year
      if (month) == 1:
        friendly_name_month_12 = f"{calendar.month_name[12]} {year-1}"
        friendly_name_current_month = f"{calendar.month_name[1]} {year}"
      else:
        friendly_name_month_12 = f"{calendar.month_name[month-1]} {year}"
        friendly_name_current_month = f"{calendar.month_name[month]} {year}"

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

      self.set_sensor_value("sensor.monthly_energy_price_consumption_normal_12", self.get_sensor_value("sensor.monthly_energy_price_consumption_normal"))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_consumption_normal_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_consumption_low_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_consumption_low_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_consumption_low_12", self.get_sensor_value("sensor.monthly_energy_price_consumption_low"))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_consumption_low_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_production_normal_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_production_normal_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_production_normal_12", self.get_sensor_value("sensor.monthly_energy_price_production_normal"))
      self.set_sensor_friendly_name("sensor.monthly_energy_price_production_normal_12", friendly_name_month_12)

      for i in range(1,12):
        value = self.get_sensor_value(f"sensor.monthly_energy_price_production_low_{i+1}")
        self.set_sensor_value(f"sensor.monthly_energy_price_production_low_{i}", value)

      self.set_sensor_value("sensor.monthly_energy_price_production_low_12", self.get_sensor_value("sensor.monthly_energy_price_production_low"))
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


  def update_quarterly_peak(self, **kwargs):
    #FOR USE WHEN RECEIVING MONTHLY PEAK FROM MQTT
    '''
    Listen to the MQTT server and parse the incoming telegrams
    
    
    self.mqtt = self.get_plugin_api("MQTT")
    self.mqtt.mqtt_subscribe(topic='P1Reader/telegrams') 
    self.mqtt.listen_event(self.on_telegram, "MQTT_MESSAGE", state='Connected', topic='P1Reader/telegrams') 
    '''

    #FOR USE WHEN RECEIVING MONTHLY PEAK VIA HA
    '''
    Update sensor in APPDEAMON
    '''

    value = self.get_state("sensor.p1_meter_peak_demand_current_month")

    self.log(f"The peak value is: {value} W")

    if value is not None:
      value = int(value)/1000 #conversion from W to kW

    if value != self.get_sensor_value("sensor.DSMR_quarterly_peak"):
      self.set_sensor_value("sensor.DSMR_quarterly_peak", value)
      self.write_sensors_to_namespace("sensor.DSMR_quarterly_peak")

  #!!! Check *args and **kwargs!!
  def on_telegram(self, event_name, data, **kwargs):
    '''
    Parse the incoming telegrams and update the corresponding sensors
    '''

    telegram = data["payload"].strip()
    
    pattern = re.compile(r"^1-0:1\.6\.0\(\d+S\)\(\d+\.\d+\*kW\)", re.M)
    value = re.findall(pattern, telegram)

    if value:
      self.log(value)

      pattern = re.compile(r"\d+\.\d+\*kW")
      m = re.search(pattern, value[0])
  
      pattern = re.compile(r"\d+\.\d+")
      m = re.match(pattern, m.group())

      value = m.group()

      if value != self.get_sensor_value("sensor.DSMR_quarterly_peak"):
        self.set_sensor_value("sensor.DSMR_quarterly_peak", value)
        self.write_sensors_to_namespace("sensor.DSMR_quarterly_peak")
        self.update_sensors_HA("sensor.DSMR_quarterly_peak")

      self.restart_app("update_energy_sensors") #restart app to stop updating


  def set_sensors(self):
    '''
    for i in range(1,13):
      name = f"sensor.monthly_energy_price_consumption_normal_{i}"
      value = self.get_sensor_value(f"sensor.monthly_energy_price_normal_{i}")
      self.set_sensor_value(name, value)
      self.write_sensors_to_namespace(name)
      self.update_sensors_HA(name)
    '''
    for i in range(1,13):
      self.remove_entity(f"sensor.monthly_energy_price_low_{i}", namespace="ha_sensors")



  def update_self_calculated_quarterly_peak_for_db(self, **kwargs):
    """
    Method to update the sensor 'sensor.electricity_delivery_power_monthly_15m_max' to trigger an update in the HA database 
    """

    value = float(self.get_state("sensor.electricity_delivery_power_monthly_15m_max"))
    if (date.today().day % 2 == 0 ):
      self.set_state("sensor.electricity_delivery_power_monthly_15m_max", state=round((value - 0.01), 2), attributes={"unit_of_measurement": "kW","friendly_name": "Electricity Delivery Power Monthly 15m Max"})
    else:
      self.set_state("sensor.electricity_delivery_power_monthly_15m_max", state=round((value + 0.01),2), attributes={"unit_of_measurement": "kW","friendly_name": "Electricity Delivery Power Monthly 15m Max"})
  


  def set_daily_gas_price(self, **kwargs):
    '''
    Method to scrape the daily gas price and update the sensor in HA
    '''
    
    res = requests.get("https://my.elexys.be/MarketInformation/IceEndexTtfGas.aspx")

    soup = bs4.BeautifulSoup(res.text,"lxml")

    items = soup.select("#contentPlaceHolder_currentPricesMonthGridview_DXDataRow0")

    result = re.search("(\d\d),(\d\d)",items[0].text)

    value = result.group(1) + '.' + result.group(2)

    if value is not None:
        self.set_sensor_value("sensor.gas_daily_price", value)
        self.write_sensors_to_namespace("sensor.gas_daily_price")
        self.update_sensors_HA("sensor.gas_daily_price")

    return





