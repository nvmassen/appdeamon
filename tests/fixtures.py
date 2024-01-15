import pytest
from unittest.mock import MagicMock
import pytest_mock

from apps.workstation import Workstation
from apps.energy_management_EV import EnergyManagementEV

#workstation
@pytest.fixture()
def workstation_fixture(mocker: pytest_mock.MockerFixture, mock_entities):
    workstation = Workstation(
        ad=mocker.MagicMock(),  # mock the AppDaemon parameter
        name='mock workstation',
        logging=mocker.MagicMock(),
        args={'switch_entity': 'switch.test_entity','sensor_entity': 'sensor.test_entity'},
        config=None,
        app_config=None,
        global_vars=None,
    )

    workstation.constraints = []

    #mocker.patch('apps.workstation.Workstation.get_entity')

    #workstation.cancel_timer = mocker.MagicMock()
    #workstation.run_daily = mocker.MagicMock()
    #workstation.run_every = mocker.MagicMock()

    return workstation

class MockEntity:
    def __init__(self, state):
        self.state = state


@pytest.fixture()
def mock_switch_entity():
    return MockEntity('on')  # can be overwritten


@pytest.fixture()
def mock_sensor_entity():
    return MockEntity(15.0)  # can be overwritten


@pytest.fixture()
def mock_entities(mock_switch_entity, mock_sensor_entity):
    return {
        'switch.test_entity': mock_switch_entity,
        'sensor.test_entity': mock_sensor_entity,
    }


#energy_management_EV
@pytest.fixture()
def energy_management_EV_fixture(mocker: pytest_mock.MockerFixture):
    energy_management_EV = EnergyManagementEV(
        ad=mocker.MagicMock(),  # mock the AppDaemon parameter
        name='mock energyManagementEV',
        logging=mocker.MagicMock(),
        args={},
        config=None,
        app_config=None,
        global_vars=None,
    )

    return energy_management_EV