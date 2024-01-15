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
    self.car_charging_modes = {}
    self.car_charging_switch = ""
    self.input_entities = {}

  def initialize(self):

    ###Initialize
    #self.add_sensors()
    #self.read_sensors_from_namespace(*self.get_sensors())
    #self.update_sensors_HA(*self.get_sensors())

    #read config
    self.read_config()

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
     

    boiler_charging_needed = sensors_condition_to_check["binary_sensor.boiler_charging_needed"]
    boiler_boost_mode_on = sensors_condition_to_check["binary_sensor.boiler_charging_boost_mode"]
    charge_now = sensors_condition_to_check["input_boolean.ev_charge_now"]
    peak_consumption_above_limit = sensors_condition_to_check["binary_sensor.car_charging_peak_consumption_above_limit"]
    charging_on = sensors_condition_to_check["input_boolean.stopcontact_wagen_test"]

    #Charging on
    if (entity_id == "input_boolean.ev_charge_now" and state == "on") or \
       (entity_id == "binary_sensor.car_charging_peak_consumption_above_limit" and state == "off") or \
       (entity_id == "binary_sensor.boiler_charging_boost_mode" and state == "off"):
      #First check if already charging
      if charging_on:
        self.log("Car charging switching on is not possible, because car charging is already on")
        return
      else:
        #Second check if peak consumption is above limit
        if peak_consumption_above_limit:
          self.log("Car charging switching on is not possible, because peak consumption is above the limit")
          return
        else:
          #Then check if charging now is on
          if charge_now:
            #Check if boiler boost mode is on, if true, then EV cannot charge
            if boiler_boost_mode_on:
              self.log("Car charging switching on is not possible, because boiler boost mode is on")
              return
            else:
              #Temporary, delete later!
              self.turn_off("automation.car_charging_off_coming_home_after_work")
              self.turn_off("automation.car_charging_off_day_cloudy")
              self.turn_off("automation.car_charging_off_day_sunny")
              self.turn_off("automation.car_charging_off_night")

              #Switch on car charging
              self.car_charging_switch_on()
              #Register hour when charging is switched, automatically switch off after 5 (normal time need to charge car) +2.5 hours (to compensate for max boost mode boiler)
                
          #Check if time is after coming home from work
          
    #Charging off
    else:
      if not charging_on:
        self.log("Car charging switching off is not possible, because car charging is already off")
        return
      else:
        #Temporary, delete later!
        self.turn_on("automation.car_charging_off_coming_home_after_work")
        self.turn_on("automation.car_charging_off_day_cloudy")
        self.turn_on("automation.car_charging_off_day_sunny")
        self.turn_on("automation.car_charging_off_night")

        if self.car_charging_switch_off():
          self.log("Car charging switched off")
        else:
          self.log("Error: could not switch car charging off")


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




  def car_charging_switch_off(self):
    '''
    Method to switch charging EV off
    '''
    
    charging_on = True
    ticks = 0

    while charging_on:
      if ticks <= 5:
        try:
          self.turn_off("input_boolean.stopcontact_wagen_test")
        except:
          self.log("Error: 'switch.stopcontact_wagen' is not available, will try again")
          time.sleep(5)
          ticks += 1
          continue

        time.sleep(1) #wait for HA to update status of 'switch.stopcontact_wagen'
        try:
          if self.get_state("input_boolean.stopcontact_wagen_test") is None:
            raise Exception("Sensor does not exist")
        except:
          self.log("Error: 'switch.stopcontact_wagen' is not available, will try again")
        else:
          charging_on = True if self.get_state("input_boolean.stopcontact_wagen_test") == "on" else False
          if not charging_on:
            break

        time.sleep(5)
        ticks += 1
      else:
        return False
    
    return True
    


  def read_config(self):
    '''Method to read config'''
    
    with open('/config/energy_management_EV_config.json','r') as f:
      config = json.load(f)

    self.car_charging_modes = config['car_charging_modes']
    self.car_charging_switch = config['car_charging_switch']

    return
  


  def add_entities(self):
    '''
    Method to add the unique entity names involved in the automation. Will be read from the config
    Values will be added later  
    '''
    
    for car_charging_mode in self.car_charging_modes.values():
      for entity_name in car_charging_mode.keys():
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