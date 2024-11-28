import pint
import pytest
import mfclib.config


@pytest.fixture(scope='function', autouse=True)
def reset_config():
    """
    Resets the configuration to its default values before
    running each test.

    This ensures that each test in the session uses the
    same initial state of the configuration.
    """
    mfclib.config.reset_to_default()


@pytest.fixture
def unit_registry():
    # ureg = pipe(
    #     pint.UnitRegistry(),
    #     mfclib.config.register_units,
    #     mfclib.config.configure_unit_registry,
    # )
    # return ureg
    ureg = pint.get_application_registry()
    # mfclib.config.register_units(ureg)
    return ureg
