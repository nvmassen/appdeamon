import appdaemon.plugins.hass.hassapi as hass
import sys

#
# Hellow World App
#
# Args:
#

class StartUp(hass.Hass):

  def initialize(self):
    sys.path.append('/config')


