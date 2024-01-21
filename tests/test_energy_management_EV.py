import pytest
from unittest.mock import patch,MagicMock,mock_open
from helpers.ad_helpers import AvailabilityError
from apps.energy_management_EV import CarChargingMode
import json

'''
@patch('apps.energy_management_EV.EnergyManagementEV.turn_on')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_car_charging_switch_on_1(mock_get_state, mock_turn_on, energy_management_EV_fixture):
    mock_get_state.return_value = 'on'
    energy_management_EV_fixture.car_charging_switch_on()
    mock_turn_on.assert_called_once()


@patch('apps.energy_management_EV.EnergyManagementEV.turn_on')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_car_charging_switch_on_2(mock_get_state, mock_turn_on, energy_management_EV_fixture):
    mock_get_state.side_effect = [None,None,'on','on']
    energy_management_EV_fixture.car_charging_switch_on()
    mock_turn_on.assert_called_once()


@patch('apps.energy_management_EV.EnergyManagementEV.turn_on')
@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_car_charging_switch_on_3(mock_get_state, mock_turn_on, energy_management_EV_fixture):
    mock_get_state.side_effect = [None,None,None,'on']
    energy_management_EV_fixture.car_charging_switch_on()
    mock_turn_on.assert_called_once()

'''

@pytest.mark.parametrize(
        "test_input,sensors", [
        ((),[]),
        (('input_boolean.ev_charge_now',"","",""),{'input_boolean.ev_charge_now':""}),
        (("","","","on"),{}),
        (("input_boolean.ev_charge_now","","","on"),{}),
        (("input_boolean.ev_charge_now","","","on"),{"input_boolean.v_charge_now":""})
        ]
    )
def test_read_args_1(energy_management_EV_fixture,test_input,sensors):
    energy_management_EV_fixture.input_entities = sensors
    with pytest.raises(Exception):
        energy_management_EV_fixture.read_args(*test_input)



def test_read_args_2(energy_management_EV_fixture):
    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':""}

    entity_id,state = energy_management_EV_fixture.read_args(*['input_boolean.ev_charge_now',"","",'on'])

    assert entity_id == 'input_boolean.ev_charge_now'
    assert state == 'on' 



def test_add_entity(energy_management_EV_fixture):
    energy_management_EV_fixture.car_charging_modes = {
        "car_charging_now": {
            "input_boolean.ev_charge_now": "on",
            "binary_sensor.car_charging_peak_consumption_above_limit": "off",
        }
    }

    energy_management_EV_fixture.add_entities()

    assert energy_management_EV_fixture.input_entities == {"input_boolean.ev_charge_now":"","binary_sensor.car_charging_peak_consumption_above_limit":""}


   

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
        "car_charging_switch": "input_boolean.stopcontact_wagen_test"
    }

    json_data = json.dumps(data)
    mock_open_file = mock_open(read_data=json_data)

    with patch("builtins.open",mock_open_file):
        energy_management_EV_fixture.read_config()
    
    assert energy_management_EV_fixture.car_charging_modes_config == data["car_charging_modes"]
    assert energy_management_EV_fixture.car_charging_switch == data["car_charging_switch"]



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
    
    assert str(e.value) == "Error: no valid configuration for car charging mode(s) given"



@patch("apps.energy_management_EV.CarChargingMode",autospec=True)
def test_parse_config_car_charging_modes_2(mockCarChargingMode,energy_management_EV_fixture):
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

    assert isinstance(energy_management_EV_fixture.car_charging_modes[0],CarChargingMode)



@patch("apps.energy_management_EV.CarChargingMode",autospec=True)
def test_parse_config_car_charging_modes_3(mockCarChargingMode,energy_management_EV_fixture):
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
    assert energy_management_EV_fixture.car_charging_modes[0] == mock



@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_read_states(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':""}
    mock_get_state.return_value = None

    with pytest.raises(AvailabilityError) as error:
        energy_management_EV_fixture.read_states()
    assert '"Sensor: \'input_boolean.ev_charge_now\' is not available"' == str(error.value)