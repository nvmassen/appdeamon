import pytest
from unittest.mock import patch,MagicMock,mock_open
from helpers.ad_helpers import AvailabilityError,EnergySensor
from helpers.energy_management_EV_helpers import CarChargingMode
import json
from helpers.energy_management_EV_const import NO_CHARGING



@pytest.mark.parametrize(
        "arguments,input_entities,error_message", [
            ((),[],"Error: one or more arguments misssing for 'car_charging_main'"),

            (('input_boolean.ev_charge_now',"","",""),{'input_boolean.ev_charge_now':""},"Error: state of 'input_boolean.ev_charge_now' should be 'on' or 'off' when passed as argument to 'car_charging_main'"),

            (("","","","on"),{},"Error: no 'entity_id' given in arguments passed to 'car_charging_main'"),

            (("input_boolean.ev_charge_now","","","on"),{"binary_sensor.car_charging_peak_consumption_above_limit":""},"Error: sensor 'input_boolean.ev_charge_now' passed to 'car_charging_main' is not part of the input entities"),

        ]
    )
def test_read_args_1(energy_management_EV_fixture,arguments,input_entities,error_message):
    energy_management_EV_fixture.input_entities = input_entities
    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.read_args(*arguments)
    
    assert str(e.value) == error_message




def test_read_args_2(energy_management_EV_fixture):
    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':""}

    entity_id,state = energy_management_EV_fixture.read_args(*['input_boolean.ev_charge_now',"","",'on'])

    assert entity_id == 'input_boolean.ev_charge_now'
    assert state == 'on' 



def test_add_entities_1(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode()
    
    mock_defined_by = {"input_boolean.ev_charge_now": "on"}
    mock_extra_conditions = {"binary_sensor.car_charging_peak_consumption_above_limit": "off"}

    energy_management_EV_fixture.car_charging_modes = {'car_charging_mode_1':car_charging_mode_1}
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
               energy_management_EV_fixture.add_entities()
   
    assert energy_management_EV_fixture.input_entities == {"input_boolean.ev_charge_now":"","binary_sensor.car_charging_peak_consumption_above_limit":""}



def test_add_entities_2(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode("test")
    
    mock_defined_by = {}
    mock_extra_conditions = {"binary_sensor.car_charging_peak_consumption_above_limit": "off"}

    energy_management_EV_fixture.car_charging_modes = {'car_charging_mode_1':car_charging_mode_1}
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
               with pytest.raises(ValueError) as e:
                energy_management_EV_fixture.add_entities()
   
    assert str(e.value) == f"Error: no 'defined by' values given for '{car_charging_mode_1.name}'"



def test_add_entities_3(energy_management_EV_fixture):
    config= {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            },
            "car_charging_night": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "binary_sensor.car_charging_night_time": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "input_boolean.car_needed_next_day": "on",
                    "binary_sensor.boiler_charging_needed": "off"
                }
            }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.car_charging_mode": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }

    energy_management_EV_fixture.parse_config(config)

    energy_management_EV_fixture.add_entities()

    assert energy_management_EV_fixture.input_entities == {'input_boolean.ev_charge_now': '', 'binary_sensor.car_charging_peak_consumption_above_limit': '', 'binary_sensor.boiler_charging_boost_mode': '', 'binary_sensor.car_charging_night_time': '', 'input_boolean.car_needed_next_day': '', 'binary_sensor.boiler_charging_needed': ''}



def test_read_config_1(energy_management_EV_fixture):
    energy_management_EV_fixture.args['path_to_config'] = ""

    with pytest.raises(IOError) as e:
        energy_management_EV_fixture.read_config()
    
    assert str(e.value) == "Error: no configuration file found"



def test_read_config_2(energy_management_EV_fixture):
    energy_management_EV_fixture.args['path_to_config'] = '/config/energy_management_EV_config.json'
    data = {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1
    }

    json_data = json.dumps(data)
    mock_open_file = mock_open(read_data=json_data)

    with patch("builtins.open",mock_open_file):
        assert energy_management_EV_fixture.read_config() == data



def test_read_config_3(energy_management_EV_fixture):
    energy_management_EV_fixture.args['path_to_config'] = '/config/energy_management_EV_config.json'

    mock_open_file = mock_open(read_data="test")

    with patch("builtins.open",mock_open_file):
        with pytest.raises(ValueError) as e:
            energy_management_EV_fixture.read_config()
        assert str(e.value) == "Error: no valid JSON configuration found"
    


def test_parse_config_1(energy_management_EV_fixture):
    config = ""

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config(config)
    
    assert str(e.value) == "Error: no valid car charging mode(s) configuration found"



def test_parse_config_2(energy_management_EV_fixture):
    config = {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            }
        }
    }

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config(config)
    
    assert str(e.value) == "Error: no valid car charging switch configuration found"



def test_parse_config_3(energy_management_EV_fixture):
    config = {
        "car_charging_modes": {
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.car_charging_mode": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config(config)
    
    assert str(e.value) == "Error: car charging modes config is empty"



def test_parse_config_4(energy_management_EV_fixture):
    config = {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen"
                }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.car_charging_mode": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }
 
    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config(config)
    
    assert str(e.value) == "Error: no valid configuration for car charging mode(s) given"



def test_parse_config_5(energy_management_EV_fixture):
    config = {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1
    }

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config(config)
    
    assert str(e.value) == "Error: no valid car charging mode sensor for HA configuration found"



@patch("apps.energy_management_EV_test.EnergySensor",autospec=True)
@patch("apps.energy_management_EV_test.CarChargingMode",autospec=True)
def test_parse_config_6(mockCarChargingMode,mockEnergySensor,energy_management_EV_fixture):
    config = {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                }
            },
            "car_charging_night": {
                "friendly_name": "Opladen Nacht",
                "defined_by": {
                    "binary_sensor.car_charging_night_time": "on",
                    "input_boolean.ev_charge_now": "off"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "input_boolean.car_needed_next_day": "on",
                    "binary_sensor.boiler_charging_needed": "off"
                }
            },
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.car_charging_mode": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }
    mock_1 = MagicMock()
    mockCarChargingMode.return_value = mock_1

    mock_2 = MagicMock()
    mockEnergySensor.return_value = mock_2

    with patch.object(mock_2,"name",new="sensor.car_charging_mode"):
     energy_management_EV_fixture.parse_config(config)

    mockCarChargingMode.assert_any_call('car_charging_now', 'Nu opladen', {'input_boolean.ev_charge_now': 'on'},{},{})
    mockCarChargingMode.assert_any_call('car_charging_night', 'Opladen Nacht', {"binary_sensor.car_charging_night_time": "on",
        "input_boolean.ev_charge_now": "off"},{},{"binary_sensor.car_charging_peak_consumption_above_limit": "off",
        "input_boolean.car_needed_next_day": "on","binary_sensor.boiler_charging_needed": "off"})
    assert energy_management_EV_fixture.car_charging_modes["car_charging_now"] == mock_1


    mockEnergySensor.assert_any_call("sensor.car_charging_mode","Car Charging Mode")
    mockEnergySensor.assert_any_call("sensor.car_charging_cooldown_start", "Cooldown Start")
    assert energy_management_EV_fixture.sensors["sensor.car_charging_mode"] == mock_2
    assert energy_management_EV_fixture.car_charging_mode_sensor_HA == "sensor.car_charging_mode"



@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_read_states(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':""}
    mock_get_state.return_value = None

    with pytest.raises(AvailabilityError) as error:
        energy_management_EV_fixture.read_states()
    assert '"Sensor: \'input_boolean.ev_charge_now\' is not available"' == str(error.value)



def test_get_new_car_charging_mode_1(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode("test")
    
    mock_defined_by = {'input_boolean.ev_charge_now':"on"}

    energy_management_EV_fixture.car_charging_modes = {"test":car_charging_mode_1}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on"}
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        result = energy_management_EV_fixture.get_new_car_charging_mode()

    assert result == car_charging_mode_1



def test_get_new_car_charging_mode_2(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode(NO_CHARGING)
    
    mock_defined_by = {'input_boolean.ev_charge_now':"off"}

    energy_management_EV_fixture.car_charging_modes = {NO_CHARGING:car_charging_mode_1}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on"}
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        result = energy_management_EV_fixture.get_new_car_charging_mode()

    assert result == car_charging_mode_1


@patch("apps.energy_management_EV_test.EnergyManagementEV.get_state")
def test_get_new_car_charging_mode_3(mock_get_state,energy_management_EV_fixture):
    config= {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            },
            "car_charging_night": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "binary_sensor.car_charging_night_time": "on",
                    "input_boolean.ev_charge_now": "off"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "input_boolean.car_needed_next_day": "on",
                    "binary_sensor.boiler_charging_needed": "off"
                }
            }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.car_charging_mode": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }

    mock_get_state.side_effect =  ["off","off","off","on","off","off","off"]
    
    energy_management_EV_fixture.parse_config(config)
    energy_management_EV_fixture.add_entities()
    energy_management_EV_fixture.read_states()
   
    result = energy_management_EV_fixture.get_new_car_charging_mode()

    assert result == energy_management_EV_fixture.car_charging_modes["car_charging_night"]


@patch("apps.energy_management_EV.EnergyManagementEV.get_state")
def test_is_charging_on_1(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = None

    with pytest.raises(AvailabilityError) as e:
        energy_management_EV_fixture.is_car_charging_on()
   
    assert str(e.value) == '"Error: \'switch.test\' is not available"'



@patch("apps.energy_management_EV_test.EnergyManagementEV.get_state")
def test_is_charging_on_2(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = 'on'

    assert energy_management_EV_fixture.is_car_charging_on() == True
   


@patch("apps.energy_management_EV_test.EnergyManagementEV.get_state")
def test_is_charging_on_3(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = 'off'

    assert energy_management_EV_fixture.is_car_charging_on() == False



def test_car_charging_requested_1(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')
    
    mock_extra_conditions = {'input_boolean.ev_charge_now':"off","input_boolean.test":"on"}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on","input_boolean.test":"on"}

    with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
        result = energy_management_EV_fixture.car_charging_requested(car_charging_mode_1)

    assert result == False



def test_car_charging_requested_2(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')
    
    mock_extra_conditions = {'input_boolean.ev_charge_now':"on","input_boolean.test":"off"}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on","input_boolean.test":"on"}

    with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
        result = energy_management_EV_fixture.car_charging_requested(car_charging_mode_1)

    assert result == False



def test_get_current_car_charging_mode(energy_management_EV_fixture):
    car_charging_mode_1 = MagicMock()

    energy_management_EV_fixture.current_charging_mode = car_charging_mode_1

    assert energy_management_EV_fixture.get_current_car_charging_mode() == car_charging_mode_1



@patch("apps.energy_management_EV_test.EnergyManagementEV.set_sensor_value")
@patch("apps.energy_management_EV_test.EnergyManagementEV.update_sensors_HA")
def test_set_car_charging_mode_1(mock_update_sensors_HA,mock_set_sensor_value,energy_management_EV_fixture):
    car_charging_mode_1 = MagicMock()

    energy_management_EV_fixture.car_charging_mode_sensor_HA = 'sensor.test'

    with patch.object(car_charging_mode_1,'friendly_name',new='test object'):
        energy_management_EV_fixture.set_car_charging_mode(car_charging_mode_1)

    assert energy_management_EV_fixture.get_current_car_charging_mode() == car_charging_mode_1
    mock_update_sensors_HA.assert_called_with('sensor.test')
    mock_set_sensor_value.assert_called_with('sensor.test','test object')



@patch("apps.energy_management_EV_test.EnergyManagementEV.set_sensor_value")
@patch("apps.energy_management_EV_test.EnergyManagementEV.update_sensors_HA")
@patch("apps.energy_management_EV_test.EnergyManagementEV.get_state")
@patch("apps.energy_management_EV_test.EnergyManagementEV.toggle_car_charging")
def test_car_charging_main_1(mock_toggle_car_charging,mock_get_state,mock_update_sensors_HA,mock_set_sensor_value,energy_management_EV_fixture):
    config= {
        "car_charging_modes": {
            "car_charging_now": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "input_boolean.ev_charge_now": "on"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "binary_sensor.boiler_charging_boost_mode": "off"
                }
            },
            "car_charging_night": {
                "friendly_name": "Nu opladen",
                "defined_by": {
                    "binary_sensor.car_charging_night_time": "on",
                    "input_boolean.ev_charge_now": "off"
                },
                "extra_conditions": {
                    "binary_sensor.car_charging_peak_consumption_above_limit": "off",
                    "input_boolean.car_needed_next_day": "on",
                    "binary_sensor.boiler_charging_needed": "off"
                }
            }
        },
        "car_charging_switch": "input_boolean.stopcontact_wagen_test",
        "turns_allowed": 1,
        "time_between_turns": 0.1,
        "HA_sensor_car_charging_mode": {
            "sensor.test": "Car Charging Mode"
        },
        "HA_sensor_car_charging_cooldown_start": {
            "sensor.car_charging_cooldown_start": "Cooldown Start"
        }
    }

    def get_state_mock(parameter):
        config = {
            "input_boolean.ev_charge_now": "on",
            "binary_sensor.car_charging_peak_consumption_above_limit": "off",
            "binary_sensor.boiler_charging_boost_mode":"off",
            "binary_sensor.car_charging_night_time":"off",
            "input_boolean.car_needed_next_day":"off",
            "binary_sensor.boiler_charging_needed":"off",
            "input_boolean.stopcontact_wagen_test":"off",
        }

        return config[parameter]
    
    
    energy_management_EV_fixture.parse_config(config)
    energy_management_EV_fixture.add_entities()
    energy_management_EV_fixture.set_car_charging_mode(energy_management_EV_fixture.car_charging_modes[NO_CHARGING])

    mock_get_state.side_effect = get_state_mock
    energy_management_EV_fixture.car_charging_main()

    assert energy_management_EV_fixture.get_current_car_charging_mode() == energy_management_EV_fixture.car_charging_modes["car_charging_now"]
    mock_update_sensors_HA.assert_any_call('sensor.test')
    mock_set_sensor_value.assert_called_with('sensor.test','Nu opladen')
    mock_toggle_car_charging.assert_called()




#tests for toggle car charging, only turn on when testing these functions, takes a lot of time to be tested
'''
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_toggle_car_charging_1(mock_get_state,energy_management_EV_fixture):

    energy_management_EV_fixture.turns_allowed = 1
    energy_management_EV_fixture.time_between_turns = 0.1

    mock_get_state.return_value = None

    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    with pytest.raises(Exception) as e:
        energy_management_EV_fixture.toggle_car_charging()
        mock_get_state.assert_called()
    
    assert str(e.value) == '"Error: \'switch.test\' is not available, could not toggle switch"'


@patch('apps.energy_management_EV.EnergyManagementEV.turn_off')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_toggle_car_charging_2(mock_get_state,mock_turn_off,energy_management_EV_fixture):

    energy_management_EV_fixture.turns_allowed = 1
    energy_management_EV_fixture.time_between_turns = 0.1

    mock_get_state.return_value = 'on'

    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    with pytest.raises(Exception) as e:
        energy_management_EV_fixture.toggle_car_charging()
        mock_get_state.assert_called_with('switch.test')
        mock_turn_off.assert_called_with('switch.test')
    
    assert str(e.value) == '"Error: \'switch.test\' is not available, could not toggle switch"'


@patch('apps.energy_management_EV.EnergyManagementEV.turn_off')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_toggle_car_charging_3(mock_get_state,mock_turn_off,energy_management_EV_fixture):

    energy_management_EV_fixture.turns_allowed = 1
    energy_management_EV_fixture.time_between_turns = 0.1

    mock_get_state.side_effect = ['on','off']

    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    energy_management_EV_fixture.toggle_car_charging()
    mock_get_state.assert_called_with('switch.test')
    mock_turn_off.assert_called_with('switch.test')
    

@patch('apps.energy_management_EV.EnergyManagementEV.turn_on')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_toggle_car_charging_4(mock_get_state,mock_turn_on,energy_management_EV_fixture):

    energy_management_EV_fixture.turns_allowed = 1
    energy_management_EV_fixture.time_between_turns = 0.1

    mock_get_state.side_effect = ['off','on']

    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    energy_management_EV_fixture.toggle_car_charging()
    mock_get_state.assert_called_with('switch.test')
    mock_turn_on.assert_called_with('switch.test')
'''    