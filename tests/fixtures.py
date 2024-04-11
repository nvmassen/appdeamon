import pytest
from unittest.mock import MagicMock
import pytest_mock

from apps.energy_management_EV_test import EnergyManagementEV

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