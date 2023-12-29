from Helpers.SensorObject import SensorObject
from datetime import datetime, timedelta, date

class light_on(SensorObject):

  def initialize(self): 

    
    self.run_daily(self.test, (datetime.now() + timedelta(seconds=3)).time().strftime("%H:%M:%S"))

  def test(self, **kwargs):
    self.set_state("sensor.test", state=10, namespace="ha_sensors", attributes={"name": "test"})
    value = self.get_state("sensor.test", namespace="ha_sensors", attribute="name")
    #self.remove_entity('senso.test', namespace = 'ha_sensors')
    self.log(value)
    self.log(kwargs)

  def turn_light_on(self, entity, attribute, old, new, **kwargs):
    status_niels = self.get_state("device_tracker.niels")
    if  status_niels == "home":
      self.turn_on("light.slaapkamer_zolder")