import appdaemon.plugins.hass.hassapi as hass
import sys
import time

#
# Hellow World App
#
# Args:
#

class StartUp(hass.Hass):

  def initialize(self):
    '''
    "Add path to helper module so appdaemon can find the helper "
    print (sys.path)
    sys.path.append('/config')

    time.sleep(5)

    "Restart apps which use the helper module"
    self.restart_app("update_energy_sensors")
    self.restart_app("energy_management_EV")
    '''
    pass

