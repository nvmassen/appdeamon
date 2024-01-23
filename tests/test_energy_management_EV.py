import pytest
from unittest.mock import patch,MagicMock,mock_open
from helpers.ad_helpers import AvailabilityError,EnergySensor
from apps.energy_management_EV import CarChargingMode
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

    energy_management_EV_fixture.car_charging_modes = [car_charging_mode_1]
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
               energy_management_EV_fixture.add_entities()
   
    assert energy_management_EV_fixture.input_entities == {"input_boolean.ev_charge_now":"","binary_sensor.car_charging_peak_consumption_above_limit":""}



def test_add_entities_2(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode("test")
    
    mock_defined_by = {}
    mock_extra_conditions = {"binary_sensor.car_charging_peak_consumption_above_limit": "off"}

    energy_management_EV_fixture.car_charging_modes = [car_charging_mode_1]
   
    with patch.object(car_charging_mode_1,"defined_by",new=mock_defined_by):
        with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
               with pytest.raises(ValueError) as e:
                energy_management_EV_fixture.add_entities()
   
    assert str(e.value) == f"Error: no 'defined by' values given for '{car_charging_mode_1.name}'"



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
        energy_management_EV_fixture.read_config()
    
    assert energy_management_EV_fixture.car_charging_modes_config == data["car_charging_modes"]
    assert energy_management_EV_fixture.car_charging_switch == data["car_charging_switch"]
    assert energy_management_EV_fixture.turns_allowed == data["turns_allowed"]
    assert energy_management_EV_fixture.time_between_turns == data["time_between_turns"]

def test_read_config_3(energy_management_EV_fixture):
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
        }
    }

    json_data = json.dumps(data)
    mock_open_file = mock_open(read_data=json_data)

    with patch("builtins.open",mock_open_file):
        with pytest.raises(ValueError) as e:
            energy_management_EV_fixture.read_config()
        assert str(e.value) == "Error: no valid car charging modes configuration found"
    


def test_read_config_4(energy_management_EV_fixture):
    energy_management_EV_fixture.args['path_to_config'] = '/config/energy_management_EV_config.json'

    mock_open_file = mock_open(read_data="test")

    with patch("builtins.open",mock_open_file):
        with pytest.raises(ValueError) as e:
            energy_management_EV_fixture.read_config()
        assert str(e.value) == "Error: no valid JSON configuration found"
    


def test_parse_config_car_charging_modes_1(energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_modes_config = ""

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config_car_charging_modes()
    
    assert str(e.value) == "Error: car charging config is empty"



def test_parse_config_car_charging_modes_2(energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_modes_config = {
        "car_charging_now": {
            "friendly_name": "Nu opladen",
        }
    }

    with pytest.raises(ValueError) as e:
        energy_management_EV_fixture.parse_config_car_charging_modes()
    
    assert str(e.value) == "Error: no valid configuration for car charging mode(s) given"



@patch("apps.energy_management_EV.CarChargingMode",autospec=True)
def test_parse_config_car_charging_modes_3(mockCarChargingMode,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_modes_config = {
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

    energy_management_EV_fixture.parse_config_car_charging_modes()

    mockCarChargingMode.assert_called_with('car_charging_now', 'Nu opladen', {'input_boolean.ev_charge_now': 'on'}, {'binary_sensor.car_charging_peak_consumption_above_limit': 'off', 'binary_sensor.boiler_charging_boost_mode': 'off'})

    assert isinstance(energy_management_EV_fixture.car_charging_modes["car_charging_now"],CarChargingMode)



@patch("apps.energy_management_EV.CarChargingMode",autospec=True)
def test_parse_config_car_charging_modes_4(mockCarChargingMode,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_modes_config = {
        "car_charging_now": {
            "friendly_name": "Nu opladen",
            "defined_by": {
                "input_boolean.ev_charge_now": "on"
            }
        }
    }
    mock = MagicMock()
    mockCarChargingMode.return_value = mock
    energy_management_EV_fixture.parse_config_car_charging_modes()

    mockCarChargingMode.assert_called_with('car_charging_now', 'Nu opladen', {'input_boolean.ev_charge_now': 'on'},{})
    assert energy_management_EV_fixture.car_charging_modes["car_charging_now"] == mock



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



@patch("apps.energy_management_EV.EnergyManagementEV.get_state")
def test_is_charging_on_1(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = None

    with pytest.raises(AvailabilityError) as e:
        energy_management_EV_fixture.is_car_charging_on()
   
    assert str(e.value) == '"Error: \'switch.test\' is not available"'



@patch("apps.energy_management_EV.EnergyManagementEV.get_state")
def test_is_charging_on_2(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = 'on'

    assert energy_management_EV_fixture.is_car_charging_on() == True
   


@patch("apps.energy_management_EV.EnergyManagementEV.get_state")
def test_is_charging_on_3(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_switch = 'switch.test'

    mock_get_state.return_value = 'off'

    assert energy_management_EV_fixture.is_car_charging_on() == False



def test_car_charging_requested_1(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')
    
    mock_extra_conditions = {'input_boolean.ev_charge_now':"on","input_boolean.test":"on"}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on","input_boolean.test":"on"}

    with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
        result = energy_management_EV_fixture.car_charging_requested(car_charging_mode_1)

    assert result == True



def test_car_charging_requested_2(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')
    
    mock_extra_conditions = {'input_boolean.ev_charge_now':"on","input_boolean.test":"off"}

    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':"on","input_boolean.test":"on"}

    with patch.object(car_charging_mode_1,"extra_conditions",new=mock_extra_conditions):
        result = energy_management_EV_fixture.car_charging_requested(car_charging_mode_1)

    assert result == False



def test_get_current_car_charging_mode(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')

    energy_management_EV_fixture.current_charging_mode = car_charging_mode_1

    assert energy_management_EV_fixture.get_current_car_charging_mode() == car_charging_mode_1



def test_set_car_charging_mode(energy_management_EV_fixture):
    car_charging_mode_1 = CarChargingMode('test')

    energy_management_EV_fixture.set_car_charging_mode(car_charging_mode_1)

    assert energy_management_EV_fixture.get_current_car_charging_mode() == car_charging_mode_1



@patch("helpers.ad_helpers.EnergySensor",autospec=True)
def test_add_sensors(MockEnergySensor,energy_management_EV_fixture):
    sensor_object_1 = MagicMock()
    
    MockEnergySensor.return_value = sensor_object_1

    with patch.object(sensor_object_1,"name",new='test'):
        energy_management_EV_fixture.add_sensors()

    #MockEnergySensor.assert_called()

    assert list(energy_management_EV_fixture.get_sensors()) == ['test']



