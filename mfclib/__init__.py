import pint
import warnings

from .cf import calculate_CF, get_CF_table
from .supply import Mixture, Supply, supply_proportions_for_mixture

__version__ = '0.1.0'


def register_pint_fractions(registry: pint.UnitRegistry | None = None):
    if registry is None:
        registry = pint.application_registry.get()

    # add preprocessor to use '%' in definitions
    registry.preprocessors.append(lambda s: s.replace('%', ' percent '))

    # define units
    unit_defs = [
        'fraction = [] = frac',
        'percent = 1e-2 frac = pct = %',
        'ppm = 1e-6 fraction',
        'ppb = 1e-9 fraction',
    ]
    for unit_def in unit_defs:
        try:
            registry.define(unit_def)
        except pint.errors.RedefinitionError:
            warnings.warn(f'Fractional unit already defined.\n{unit_def}')

    return registry