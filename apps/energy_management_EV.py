from statistics import mean
from datetime import datetime, timedelta, date
from helpers.ad_helpers import SensorObject, EnergySensor, AvailabilityError
import re
import appdaemon.plugins.hass.hassapi as hass
import calendar
import time
import json
from helpers.energy_management_EV_const import NO_CHARGING

class EnergyManagementEV(SensorObject):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.car_charging_modes = {NO_CHARGING:CarChargingMode(NO_CHARGING,"Off")}
    self.car_charging_switch = ""
    self.input_entities = {}
    self.turns_allowed = 0
    self.time_between_turns = 0
    self.car_charging_mode_sensor_HA = ""


  def initialize(self):

    #read config
    try:
      config = self.read_config()
    except Exception as e:
      self.log(e)
      return


    #parse config
    try:
      self.parse_config(config)
    except Exception as e:
      self.log(e)
      return


    #add the unique entity names involved in this automation
    try:
      self.add_entities()
    except Exception as e:
      self.log(e)
      return
    

    #initialize
    self.set_car_charging_mode(self.car_charging_modes[NO_CHARGING])
    

    #listen to states
    self.listen_states()



  def car_charging_main(self, *args, **kwargs):
    '''
    Main method to switch on and off the charging of the EV
    '''

    '''
    #check if args for the callback are available
    try:
      entity_id,state = self.read_args(*args)
    except Exception as e:
      self.log(e)
      return
    '''
    

    #read entites from HA with will be used for conditions
    try:
      self.read_states()
    except Exception as e:
      self.log(e)


    #get new charging mode
    new_car_charging_mode = self.get_new_car_charging_mode()
    

    #get request to turn charging on
    car_charging_requested = self.car_charging_requested(new_car_charging_mode)


    #get state of the car charging switch
    try:
      is_car_charging_on = self.is_car_charging_on()
    except Exception as e:
      self.log(e)
      return
    

    #check if new charging mode is 'no charging'
    if new_car_charging_mode != self.get_current_car_charging_mode(): #check if current car charging mode needs to be changed
      self.set_car_charging_mode(new_car_charging_mode)


    if is_car_charging_on != car_charging_requested:
      try:
        self.toggle_car_charging()
      except Exception as e:
        self.log(e)


    #Temporary, delete later!
    '''
    self.turn_on("automation.car_charging_off_coming_home_after_work")
    self.turn_on("automation.car_charging_off_day_cloudy")
    self.turn_on("automation.car_charging_off_day_sunny")
    self.turn_on("automation.car_charging_off_night")
    '''



  def toggle_car_charging(self):
    '''
    Method to switch charging EV on
    '''
    turns = 0
    state_car_charging_switch = self.get_state(self.car_charging_switch)


    while turns < self.turns_allowed:

      if state_car_charging_switch is None:
        time.sleep(self.time_between_turns)
        turns += 1
        
      if state_car_charging_switch == 'off':
        self.turn_on(self.car_charging_switch)
      else:
        self.turn_off(self.car_charging_switch)

      time.sleep(1) #wait for HA to update status of 'switch.stopcontact_wagen'

      #check if switch toggled
      if self.get_state(self.car_charging_switch) == state_car_charging_switch:
        time.sleep(self.time_between_turns)
        turns += 1
        continue
      else:
        return

    raise AvailabilityError(f"Error: '{self.car_charging_switch}' is not available, could not toggle switch")  


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

    return config
  


  def add_entities(self):
    '''
    Method to add the unique entity names involved in the automation. Will be read from the config
    Values will be added later  
    '''
    
    for car_charging_mode in self.car_charging_modes.values():

      if len(car_charging_mode.defined_by) == 0 and car_charging_mode.name != NO_CHARGING:
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
  


  def parse_config(self, config):
    '''Method to translate the config'''

    try:
      car_charging_modes_config = config['car_charging_modes']
    except:
      raise ValueError("Error: no valid car charging mode(s) configuration found")
    
    try:
      self.car_charging_switch = config['car_charging_switch']
      self.turns_allowed = config['turns_allowed']
      self.time_between_turns = config['time_between_turns']
    except:
      raise ValueError("Error: no valid car charging switch configuration found") 
    

    try:
      car_charging_mode_sensor_HA_config = config['car_charging_mode_sensor_HA']
      for name,friendly_name in car_charging_mode_sensor_HA_config.items():
        self.car_charging_mode_sensor_HA = name
        self.add_sensor(EnergySensor(name,friendly_name))
    except:
      raise ValueError("Error: no valid car charging mode sensor for HA configuration found") 
    
    
    if car_charging_modes_config == {}:
      raise ValueError("Error: car charging modes config is empty")
    
    try:
      for name,car_charging_mode in car_charging_modes_config.items():
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


    return
  


  def get_new_car_charging_mode(self):
    '''Method to determine the new car charging mode, returns the name of the mode'''

    for name,car_charging_mode in self.car_charging_modes.items():
      match_found = False

      print(car_charging_mode.name)

      for sensor_name,state in car_charging_mode.defined_by.items():
        match_found = (state == self.get_input_entity_state(sensor_name))
      if match_found:
        result = car_charging_mode
      else:
        result = self.car_charging_modes[NO_CHARGING]
      
    return result
    


  def get_current_car_charging_mode(self):
    '''Method to return the name of the car charging mode'''
    return self.current_charging_mode
      


  def car_charging_requested(self,new_car_charging_mode):
    '''Method to determine of the car charging needs to be switched on based on the conditions'''
    
    switch_on = False

    for sensor_name,state in new_car_charging_mode.extra_conditions.items():
      switch_on = (state == self.get_input_entity_state(sensor_name))
    
    return switch_on



  def is_car_charging_on(self):
    '''Method to determine if the switch for car charging is on, if the switch is not available, raise error'''
    result = self.get_state(self.car_charging_switch)

    if result is None:
      raise AvailabilityError(f"Error: '{self.car_charging_switch}' is not available")
    
    return result == 'on'
  


  def set_car_charging_mode(self,new_car_charging_mode):
    '''Method to set a new car charging mode'''

    self.current_charging_mode = new_car_charging_mode

    self.set_sensor_value(self.car_charging_mode_sensor_HA,self.current_charging_mode.friendly_name)
    self.update_sensors_HA(self.car_charging_mode_sensor_HA)



  def add_input_entity(self,name):
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