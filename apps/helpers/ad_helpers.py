import appdaemon.plugins.hass.hassapi as hass

class SensorObject(hass.Hass):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sensors = {}
    

    def read_sensors_from_namespace(self, *args):
        for key in args:
            sensor = self.sensors[key]
            value = self.get_state(sensor.name, namespace="ha_sensors")
            if value != None:
                sensor.value = value

    
    def add_sensor(self, energy_sensor):
        self.sensors[energy_sensor.name] = energy_sensor


    def get_sensor_value(self, name):
        return self.sensors[name].value


    def get_sensor_friendly_name(self, name):
        return self.sensors[name].friendly_name


    def set_sensor_value(self, name, value):
        self.sensors[name].value = value


    def set_sensor_friendly_name(self, name, friendly_name):
        self.sensors[name].friendly_name = friendly_name
        
    
    def write_sensors_to_namespace(self, *args):
        for key in args:
            sensor = self.sensors[key]
            self.set_state(sensor.name, state=sensor.value, namespace="ha_sensors")


    def print_sensors(self, *args):
        for key in args:    
            sensor = self.sensors[key]
            self.log(sensor)


    def update_sensors_HA(self, *args):
        for key in args:    
            sensor = self.sensors[key]
            self.set_state(sensor.name, state=sensor.value, attributes={"unit_of_measurement": sensor.unit_of_measurement,"friendly_name": sensor.friendly_name})
    

    def get_sensors(self):
        return self.sensors.keys()


class EnergySensor():
    """
    Represents a sensor with the following attributes: "name","value","friendly_name","unit_of_measurement"
    """

    def __init__(self, name, friendly_name="", unit_of_measurement="", value=0):
        self.name = name
        self.value = value
        self.friendly_name = friendly_name
        self.unit_of_measurement = unit_of_measurement


    def __str__(self):
        output = f"Name: {self.name}\nFriendly name: {self.friendly_name}\nValue: {self.value}\nUnit: {self.unit_of_measurement}"
        return output
    
    
# A python program to create user-defined exceptions
# class LookUpError is derived from super class Exception
class AvailabilityError(Exception):
 
    # Constructor or Initializer
    def __init__(self, value):
        self.value = value
 
    # __str__ is to print() the value
    def __str__(self):
        return(repr(self.value))
 
 
