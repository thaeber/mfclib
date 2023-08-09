import warnings

import pint
from . import _config


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
    _config._set_config_value(_config.UNIT_REGISTRY_KEY, registry)
    return registry
