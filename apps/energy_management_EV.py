from statistics import mean
from datetime import datetime, timedelta, date
from helpers.ad_helpers import SensorObject, EnergySensor, AvailabilityError
import re
import appdaemon.plugins.hass.hassapi as hass
import calendar
import time
import json

class EnergyManagementEV(SensorObject):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.car_charging_modes = []
    self.car_charging_modes_config = {}
    self.car_charging_switch = ""
    self.input_entities = {}

  def initialize(self):

    ###Initialize
    #self.add_sensors()
    #self.read_sensors_from_namespace(*self.get_sensors())
    #self.update_sensors_HA(*self.get_sensors())

    #read config
    self.read_config()


    #translate config for the different car charging modes
    self.translate_config()


    #add the unique entity names involved in this automation
    self.add_entities()

    

    #listen to states
    self.listen_states()


  def add_sensors(self):
    self.add_sensor(EnergySensor("sensor.car_charging_start_charging_now", "Start Charging Now", ""))



  def car_charging_main(self, *args, **kwargs):
    '''
    Main method to switch on and off the charging of the EV
    '''

    #check if args are available
    try:
      entity_id,state = self.read_args(*args)
    except:
      self.log("No valid arguments given for charging method")
      return
    

    #read entites from HA with will be used for conditions
    try:
      self.read_states()
    except AvailabilityError as error:
      self.log(error.value)
     
    if self.charging_on():
      self.car_charging_switch_on()

    #Temporary, delete later!
    self.turn_on("automation.car_charging_off_coming_home_after_work")
    self.turn_on("automation.car_charging_off_day_cloudy")
    self.turn_on("automation.car_charging_off_day_sunny")
    self.turn_on("automation.car_charging_off_night")



  def car_charging_switch_on(self):
    '''
    Method to switch charging EV on
    '''

    while True:
      try:
        if self.get_state("input_boolean.stopcontact_wagen_test") is None:
          raise Exception("Sensor does not exist")
      except:
        self.log("Error: 'switch.stopcontact_wagen' is not available, will try again")
        time.sleep(1)
        continue
      else:
        self.turn_on("input_boolean.stopcontact_wagen_test")

      time.sleep(1) #wait for HA to update status of 'switch.stopcontact_wagen'

      #check if switch stopcontact wagen is turned on
      try:
        if self.get_state("input_boolean.stopcontact_wagen_test") != 'on' :
          raise Exception("")
      except:
        self.log("Error: 'switch.stopcontact_wagen' is not on, will try again")
        time.sleep(1)
        continue
      else:
        break


  def read_config(self):
    '''Method to read config'''
    
    with open('/config/energy_management_EV_config.json','r') as f:
      config = json.load(f)

    self.car_charging_modes_config = config['car_charging_modes']
    self.car_charging_switch = config['car_charging_switch']

    return
  


  def add_entities(self):
    '''
    Method to add the unique entity names involved in the automation. Will be read from the config
    Values will be added later  
    '''
    
    for car_charging_mode in self.car_charging_modes:

      for entity_name in car_charging_mode.defined_by.keys():
          self.input_entities[entity_name] = ""

      for entity_name in car_charging_mode.extra_conditions.keys():
          self.input_entities[entity_name] = ""

    return



  def listen_states(self):
    '''Method to listen to the states of the different sensors'''

    for entity in self.input_entities:
      self.listen_state(self.car_charging_main,entity)
          
    return
  


  def read_args(self,*args):
      print(args)
      entity_id = args[0]
      state = args[3]

      if entity_id in self.input_entities.keys():
        pass
      else:
        raise

      if state == "on" or state == "off":
        pass
      else:
        raise

      return entity_id,state
  


  def read_states(self):
    '''method to read states from HA, if entity not available, raise exception'''
    
    #check if entities are available in HA
    for entity_name in self.input_entities.keys():
      state = self.get_state(entity_name)
      if state is None:
        raise AvailabilityError(f"Sensor: '{entity_name}' is not available")
      else:
          self.input_entities[entity_name] = state
    
    return
  


  def translate_config(self):
    '''Method to translate the config to individual car charging modes'''
    for name,car_charging_mode in self.car_charging_modes_config.items():
      friendly_name = car_charging_mode['friendly_name']
      defined_by = car_charging_mode['defined_by']
      try:
        extra_conditions = car_charging_mode['extra_conditions']
      except:
        extra_conditions = {}
        pass

      self.car_charging_modes.append(self.CarChargingMode(name,friendly_name,defined_by,extra_conditions))

    return


  class CarChargingMode():
    '''class to store the configuration for the different car charging modes'''

    def __init__(self,name,friendly_name,defined_by,extra_conditions):
      self.name = name
      self.friendly_name = friendly_name
      self.defined_by = defined_by
      self.extra_conditions = extra_conditions

    def __str__(self):
      output = f"Name: {self.name}\nFriendly name: {self.friendly_name}\nDefined_by: {self.defined_by}\nextra_conditions: {self.extra_conditions}"
      return output