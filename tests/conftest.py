import pint
import pytest
import mfclib._config
from toolz import pipe


@pytest.fixture(scope='function', autouse=True)
def reset_config():
    """
    Resets the configuration to its default values before
    running each test.

    This ensures that each test in the session uses the
    same initial state of the configuration.
    """
    mfclib._config.reset_to_default()


@pytest.fixture
def unit_registry():
    ureg = pipe(
        pint.UnitRegistry(),
        mfclib.register_units,
        mfclib.configure_unit_registry,
    )
    return ureg
