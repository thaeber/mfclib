import warnings

import pint

_unit_registry: pint.UnitRegistry | None = None
Quantity: pint.Quantity | None = None


def register_pint(registry: pint.UnitRegistry | None = None):
    if registry is None:
        registry = pint.application_registry.get()

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

    # set global unit registry for use in package
    global _unit_registry
    _unit_registry = registry
    global Quantity
    Quantity = registry.Quantity

    return registry


def quantity() -> pint.Quantity:
    global _unit_registry
    if _unit_registry is not None:
        return _unit_registry.Quantity
    else:
        return register_pint().Quantity