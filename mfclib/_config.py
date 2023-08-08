import pint

UNIT_REGISTRY_KEY = 'unit_registry'

_configuration = {}

def unitRegistry() -> None | pint.UnitRegistry:
    if UNIT_REGISTRY_KEY in _configuration:
        return _configuration[UNIT_REGISTRY_KEY]
    else:
        None