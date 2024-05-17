import warnings
from typing import Any, Dict

import pint

UNIT_REGISTRY_KEY = 'UNIT_REGISTRY'
BALANCE_SPECIES_KEY = 'BALANCE_SPECIES_INDICATOR'
SOURCE_GASES_FILE_KEY = 'GASES_FILE'

__default_configuration: Dict[str, Any] = {
    BALANCE_SPECIES_KEY: '*',
    UNIT_REGISTRY_KEY: None,
    SOURCE_GASES_FILE_KEY: '.sources.json',
}
_custom_configuration: Dict[str, Any] = {}


def _check_configuration_key(key: str):
    if key in __default_configuration:
        return key
    else:
        message = '"key" is not a valid configuration key.'
        detail = 'Possible keys are: ' + ', '.join(__default_configuration.keys())
        raise ValueError('\n'.join([message, detail]))


def _get_config_value(key: str):
    if key in _custom_configuration:
        return _custom_configuration[key]
    elif key in __default_configuration:
        return __default_configuration[key]
    else:
        _check_configuration_key(key)


def _set_config_value(key: str, value: Any):
    key = _check_configuration_key(key)
    _custom_configuration[key] = value


def reset_to_default():
    _custom_configuration.clear()


def balanceSpeciesIndicator():
    indicator = _get_config_value(BALANCE_SPECIES_KEY)
    assert isinstance(indicator, str)
    return indicator


def unitRegistry() -> None | pint.UnitRegistry:
    return _get_config_value(UNIT_REGISTRY_KEY)


def sourceGasesFile():
    return _get_config_value(SOURCE_GASES_FILE_KEY)


def register_units(registry: pint.UnitRegistry):
    """
    Registers specialized dimensionless units in the provided unit registry.
    Also adds a preprocessor directive to enable usage of `%` as unit for
    percent values.

    Added units:
        'fraction = [] = frac',
        'percent = 1e-2 frac = %',
        'ppm = 1e-6 fraction',
        'ppb = 1e-9 fraction',

    Args:
        registry (pint.UnitRegistry): The pint unit registry.
    """
    # add preprocessor to use '%' in definitions
    registry.preprocessors.append(lambda s: s.replace('%', ' percent '))

    # define units
    unit_defs = [
        'fraction = [] = frac',
        'percent = 1e-2 frac = %',
        'ppm = 1e-6 fraction',
        'ppb = 1e-9 fraction',
    ]
    for unit_def in unit_defs:
        try:
            registry.define(unit_def)
        except pint.errors.RedefinitionError:
            warnings.warn(f'Fractional unit already defined.\n{unit_def}')

    return registry


def configure_unit_registry(registry: pint.UnitRegistry):
    _set_config_value(UNIT_REGISTRY_KEY, registry)
    return registry
