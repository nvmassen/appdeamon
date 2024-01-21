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
    self.car_charging_modes = {"no_charging":CarChargingMode("no_charging","Off")}
    self.car_charging_modes_config = {}
    self.car_charging_switch = ""
    self.input_entities = {}
    self.current_charging_mode = self.car_charging_modes['no_charging']

  def initialize(self):

    ###Initialize
    #self.add_sensors()
    #self.read_sensors_from_namespace(*self.get_sensors())
    #self.update_sensors_HA(*self.get_sensors())

    #read config
    try:
      self.read_config()
    except Exception as e:
      self.log(e)
      return


    #translate config for the different car charging modes
    try:
      self.parse_config_car_charging_modes()
    except Exception as e:
      self.log(e)
      return


    #add the unique entity names involved in this automation
    try:
      self.add_entities()
    except Exception as e:
      self.log(e)
      return
    

    #listen to states
    self.listen_states()


  def add_sensors(self):
    self.add_sensor(EnergySensor("sensor.car_charging_start_charging_now", "Start Charging Now", ""))



  def car_charging_main(self, *args, **kwargs):
    '''
    Main method to switch on and off the charging of the EV
    '''

    #check if args for the callback are available
    try:
      entity_id,state = self.read_args(*args)
    except Exception as e:
      self.log(e)
      return
    

    #read entites from HA with will be used for conditions
    try:
      self.read_states()
    except AvailabilityError as e:
      self.log(e.value)


    #check if current mode if the same as new mode
    name_new_charging_mode = self.get_name_new_car_charging_mode()
    #if name_new_charging_mode == "no charging":
      

    #if self.get_name_new_car_charging_mode() == self.current_charging_mode.name:


    #if self.charging_on():
      #self.car_charging_switch_on()

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
    try:
      with open(self.args['path_to_config'],'r') as f:
        try:
          config = json.load(f)
        except ValueError:
          raise ValueError("Error: no valid JSON configuration found")
    except IOError:
      raise IOError("Error: no configuration file found")

    try:
      self.car_charging_modes_config = config['car_charging_modes']
      self.car_charging_switch = config['car_charging_switch']
    except:
      raise ValueError("Error: no valid car charging modes configuration found")

    return
  


  def add_entities(self):
    '''
    Method to add the unique entity names involved in the automation. Will be read from the config
    Values will be added later  
    '''
    
    for car_charging_mode in self.car_charging_modes:

      if len(car_charging_mode.defined_by) == 0:
        raise ValueError(f"Error: no 'defined by' values given for '{car_charging_mode.name}'")
      else:
        for entity_name in car_charging_mode.defined_by.keys():
            self.add_input_entity(entity_name)

      if len(car_charging_mode.extra_conditions) > 0:
        for entity_name in car_charging_mode.extra_conditions.keys():
            self.add_input_entity(entity_name)

    return



  def listen_states(self):
    '''Method to listen to the states of the different sensors'''

    for entity in self.input_entities:
      self.listen_state(self.car_charging_main,entity)
          
    return
  


  def read_args(self,*args):

      try:
        entity_id = args[0]
        state = args[3]
      except:
        raise ValueError("Error: one or more arguments misssing for 'car_charging_main'")
      
      if entity_id == "":
        raise ValueError("Error: no 'entity_id' given in arguments passed to 'car_charging_main'")

      if entity_id in self.input_entities.keys():
        pass
      else:
        raise ValueError(f"Error: sensor '{entity_id}' passed to 'car_charging_main' is not part of the input entities")

      if state == "on" or state == "off":
        pass
      else:
        raise ValueError(f"Error: state of '{entity_id}' should be 'on' or 'off' when passed as argument to 'car_charging_main'")

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
  


  def parse_config_car_charging_modes(self):
    '''Method to translate the config to individual car charging modes'''

    try:
      for name,car_charging_mode in self.car_charging_modes_config.items():
        friendly_name = car_charging_mode['friendly_name']
        defined_by = car_charging_mode['defined_by']
        try:
          extra_conditions = car_charging_mode['extra_conditions']
        except:
          extra_conditions = {}
          pass

        self.car_charging_modes[name] = CarChargingMode(name,friendly_name,defined_by,extra_conditions)
    except KeyError:
      raise ValueError("Error: no valid configuration for car charging mode(s) given")
    except AttributeError:
      raise ValueError("Error: car charging config is empty")

    return
  


  def get_name_new_car_charging_mode(self):
    '''Method to determine the new car charging mode, returns the name of the mode'''

    for name,car_charging_mode in self.car_charging_modes.items():
      match_found = False
      print(car_charging_mode)
      print(self.input_entities)
      for sensor_name,state in car_charging_mode.defined_by.items():
        match_found =  state == self.get_input_entity_state(sensor_name)
      if match_found:
        result = name
      else:
        result = "no_charging"
      
      return result
      

  def is_car_charging_on(self):
    '''Method to determine if the switch for car charging is on, if the switch is not available, raise error'''
    result = self.get_state(self.car_charging_switch)

    if result is None:
      raise AvailabilityError(f"Error: '{self.car_charging_switch}' is not available")
    
    return result == 'on'


  def add_input_entitie(self,name):
    self.input_entities[name] = ""


  
  def set_input_entity_state(self,name,state):
    self.input_entities[name] = state



  def get_input_entity_state(self,name):
    return self.input_entities[name] 
  


class CarChargingMode():
  '''class to store the configuration for the different car charging modes'''

  def __init__(self,name="",friendly_name="",defined_by={},extra_conditions={}):
    self.name = name
    self.friendly_name = friendly_name
    self.defined_by = defined_by
    self.extra_conditions = extra_conditions

  def __str__(self):
    output = f"Name: {self.name}\nFriendly name: {self.friendly_name}\nDefined_by: {self.defined_by}\nextra_conditions: {self.extra_conditions}"
    return output