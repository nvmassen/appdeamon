import pytest
from unittest.mock import patch
from helpers.ad_helpers import AvailabilityError

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


@patch('apps.energy_management_EV.EnergyManagementEV.get_state')
def test_read_states(mock_get_state,energy_management_EV_fixture):
    energy_management_EV_fixture.input_entities = {'input_boolean.ev_charge_now':""}
    mock_get_state.return_value = None

    with pytest.raises(AvailabilityError) as error:
        energy_management_EV_fixture.read_states()
    assert '"Sensor \'input_boolean.ev_charge_now\' is not available"' == str(error.value)