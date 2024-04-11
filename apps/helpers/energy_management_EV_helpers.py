class CarChargingMode():
  '''class to store the configuration for the different car charging modes'''

  def __init__(self,name="",friendly_name="",defined_by={},conditions_on={},conditions_off={}):
    self.name = name
    self.friendly_name = friendly_name
    self.defined_by = defined_by
    self.conditions_on = conditions_on
    self.conditions_off = conditions_off

  def __str__(self):
    output = f"Name: {self.name}\nFriendly name: {self.friendly_name}\nDefined_by: {self.defined_by}\nextra_conditions: {self.extra_conditions}"
    return output