from typing import Any, Dict, Optional
import pint

UNIT_REGISTRY_KEY = 'UNIT_REGISTRY'
BALANCE_SPECIES_KEY = 'BALANCE_SPECIES_INDICATOR'

__default_configuration: Dict[str, Any] = {
    BALANCE_SPECIES_KEY: '*',
    UNIT_REGISTRY_KEY: None,
}
_custom_configuration: Dict[str, Any] = {}


def _check_configuration_key(key: str):
    if key in __default_configuration:
        return key
    else:
        message = f'"key" is not a valid configuration key.'
        detail = 'Possible keys are: ' + ', '.join(
            __default_configuration.keys()
        )
        ValueError('\n'.join([message, detail]))


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


def balance_species_indicator():
    return _get_config_value(BALANCE_SPECIES_KEY)


def unitRegistry() -> None | pint.UnitRegistry:
    return _get_config_value(UNIT_REGISTRY_KEY)
