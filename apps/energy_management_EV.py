from statistics import mean
from datetime import datetime, timedelta, date
from helpers.ad_helpers import SensorObject, EnergySensor, AvailabilityError
import re
import appdaemon.plugins.hass.hassapi as hass
import calendar
import time
import json
from helpers.energy_management_EV_const import NO_CHARGING
from helpers.energy_management_EV_helpers import CarChargingMode

class EnergyManagementEV(SensorObject):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.car_charging_modes = {NO_CHARGING:CarChargingMode(NO_CHARGING,"No Car Charging")}
    self.car_charging_switch = ""
    self.input_entities = {}
    self.turns_allowed = 0
    self.time_between_turns = 0
    self.car_charging_mode_sensor_HA = ""
    self.car_charging_cooldown_start_sensor_HA = ""
    self.cooldown_start = None


  def initialize(self):
    #Initialize
    self.initalize_car_charging()
    

    #listen to states to trigger car charging main function
    self.listen_states()


    #Reset car not needed boolean
    self.run_daily(self.reset_car_needed_next_day, "6:00:00")
    #self.run_daily(self.reset_car_needed_next_day, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))

    self.log('Car Charging Initialised.')

  def initalize_car_charging(self):
    '''
    Method to initialize car charging app
    '''

    #read config
    try:
      config = self.read_config()
    except Exception as e:
      self.log(e)
      return

    self.log('Config file succesfully read', level='DEBUG')

    #parse config
    try:
      self.parse_config(config)
    except Exception as e:
      self.log(e)
      return

    self.log('Config file succesfully parsed', level='DEBUG')


    #add the unique entity names involved in this automation
    try:
      self.add_entities()
    except Exception as e:
      self.log(e)
      return
    
    self.log('Input entities added', level='DEBUG')

    #initialize
    self.set_car_charging_mode(self.car_charging_modes[NO_CHARGING])
    
    self.log(f"Car charging mode set to '{self.get_current_car_charging_mode().name}'", level='DEBUG')

    self.car_charging_main()



  def car_charging_main(self, *args, **kwargs):
    '''
    Main method to switch on and off the charging of the EV
    '''

    #check if args for the callback are available
    try:
      entity_id,state = self.read_args(*args)
      self.log(f"Car charging app is triggered by: '{entity_id}' with state '{state}'", level='DEBUG')
    except Exception as e:
      self.log(e, level='DEBUG')

    #read entites from HA wich will be used for conditions
    try:
      self.read_states()
    except Exception as e:
      self.log(e)
      return

    #get new charging mode
    new_car_charging_mode = self.get_new_car_charging_mode()

    self.log(f"The current car charging mode is: '{self.get_current_car_charging_mode().name}'", level='DEBUG')
    self.log(f"The requested car charging mode is: '{new_car_charging_mode.name}'", level='DEBUG')
    

    #check if current car charging mode needs to be changed
    if new_car_charging_mode != self.get_current_car_charging_mode(): 
        self.set_car_charging_mode(new_car_charging_mode)
        self.log(f"Car charging mode changed to: '{new_car_charging_mode.name}'", level='DEBUG')


    #get state of the car charging switch
    try:
      is_car_charging_on = self.is_car_charging_on()
    except Exception as e:
      self.log(e)
      return
    
    if is_car_charging_on:
      self.log("Car charging is 'on'", level='DEBUG')
    else:
      self.log("Car charging is 'off'", level='DEBUG')


    #check if car charging is requested
    car_charging_requested = self.car_charging_requested(new_car_charging_mode, is_car_charging_on)

    if car_charging_requested:
      self.log("Car charging is requested", level='DEBUG')
    else:
      self.log("Car charging is not requested", level='DEBUG')


    if is_car_charging_on != car_charging_requested:
      try:
        self.toggle_car_charging()
      except Exception as e:
        self.log(e)
    else:
      self.log("No car charging toggle required", level='DEBUG')


  def toggle_car_charging(self):
    '''
    Method to switch charging EV on
    '''
    turns = 0

    state_car_charging_switch_old = self.get_state(self.car_charging_switch)

    while turns < self.turns_allowed:
      self.log(state_car_charging_switch_old, level='DEBUG')

      if state_car_charging_switch_old is None:
        time.sleep(self.time_between_turns)
        turns += 1
        
      if state_car_charging_switch_old  == 'off':
        self.turn_on(self.car_charging_switch)
      else:
        self.turn_off(self.car_charging_switch)

      time.sleep(1) #wait for HA to update status of 'switch.stopcontact_wagen'

      #check if switch toggled
      if self.get_state(self.car_charging_switch) == state_car_charging_switch_old :
        time.sleep(self.time_between_turns)
        turns += 1
        continue
      else:
        self.log(f"Car charging successfully toggled", level='DEBUG')
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

      if len(car_charging_mode.conditions_on) > 0:
        for entity_name in car_charging_mode.conditions_on.keys():
            self.add_input_entity(entity_name)

      if len(car_charging_mode.conditions_off) > 0:
        for entity_name in car_charging_mode.conditions_off.keys():
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
      HA_sensor_car_charging_mode_config = config['HA_sensor_car_charging_mode']
      for name,friendly_name in HA_sensor_car_charging_mode_config.items():
        self.car_charging_mode_sensor_HA = name
        self.add_sensor(EnergySensor(name,friendly_name))
    except:
      raise ValueError("Error: no valid car charging mode sensor for HA configuration found") 
    

    try:
      HA_sensor_car_charging_cooldown_start_config = config['HA_sensor_car_charging_cooldown_start']
      for name,friendly_name in HA_sensor_car_charging_cooldown_start_config.items():
        self.car_charging_cooldown_start_sensor_HA = name
        self.add_sensor(EnergySensor(name,friendly_name))
    except:
      raise ValueError("Error: no valid car charging cooldown start sensor for HA configuration found") 
    

    if car_charging_modes_config == {}:
      raise ValueError("Error: car charging modes config is empty")
    

    try:
      for name,car_charging_mode in car_charging_modes_config.items():
        friendly_name = car_charging_mode['friendly_name']
        defined_by = car_charging_mode['defined_by']
        try:
          conditions_on = car_charging_mode['conditions_on']
        except:
          conditions_on = {}
        try:
          conditions_off = car_charging_mode['conditions_off']
        except:
          conditions_off = {}

        self.car_charging_modes[name] = CarChargingMode(name,friendly_name,defined_by,conditions_on,conditions_off)

    except KeyError:
      raise ValueError("Error: no valid configuration for car charging mode(s) given")


    return
  


  def get_new_car_charging_mode(self):
    '''Method to determine the new car charging mode, returns the name of the mode'''

    for car_charging_mode in self.car_charging_modes.values():
      checks = set()
      for sensor_name,state in car_charging_mode.defined_by.items():
        checks.add(state == self.get_input_entity_state(sensor_name))

      if len(checks) == 1 and True in checks:
        result = car_charging_mode
        break
    else:
      result = self.car_charging_modes[NO_CHARGING]
      
    return result
    


  def get_current_car_charging_mode(self):
    '''Method to return the name of the car charging mode'''
    return self.current_charging_mode
      


  def car_charging_requested(self,new_car_charging_mode: CarChargingMode, is_car_charging_on: bool) -> bool : 
    '''Method to determine of the car charging needs to be switched on based on the conditions'''
    
    #check if new car charging mode is NO_CHARGING, if this is the case, return false
    if new_car_charging_mode == self.car_charging_modes[NO_CHARGING]:
      return False

    #if car charging mode is not NO_CHARGING, check conditions on and conditions off
    check_conditions_on = True

    if len(new_car_charging_mode.conditions_on) > 0:
      list_check_conditions_on = set()

      for sensor_name,state in new_car_charging_mode.conditions_on.items():
        list_check_conditions_on.add(state == self.get_input_entity_state(sensor_name))
      
      if len(list_check_conditions_on) == 1:
        check_conditions_on = list(list_check_conditions_on)[0]
      else:
        check_conditions_on = False
      

    check_conditions_off = False

    if len(new_car_charging_mode.conditions_off) > 0:

      list_check_conditions_off = set()

      for sensor_name,state in new_car_charging_mode.conditions_off.items():
        list_check_conditions_off.add(state == self.get_input_entity_state(sensor_name))

      check_conditions_off = True in list_check_conditions_off
    
    if check_conditions_on:
      car_charging_requested = True
    elif is_car_charging_on and not check_conditions_off:
      car_charging_requested = True
    else:
      car_charging_requested = False

    return car_charging_requested



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
  


  def reset_car_needed_next_day(self, *args, **kwargs):
    self.turn_on("input_boolean.car_needed_next_day")
  