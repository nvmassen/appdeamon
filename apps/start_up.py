import appdaemon.plugins.hass.hassapi as hass
import sys

#
# Hellow World App
#
# Args:
#

class StartUp(hass.Hass):

  def initialize(self):
    "Add path to helper module so appdaemon can find the helper "
    sys.path.append('/config')

    "Restart apps which use the helper module"
    self.restart_app("update_energy_sensors")
    self.restart_app("energy_management_EV")
    self.restart_app("test")


