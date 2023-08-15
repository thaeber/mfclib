import re

import click

import mfclib
from mfclib._config import unitRegistry


def validate_mixture(ctx, param, value):
    parts_regex = re.compile(r'[,;/:]')
    kv_regex = re.compile(r"(.*)=(.*)")
    mixture = {}
    for part in parts_regex.split(value):
        part = part.strip()
        match = kv_regex.match(part)
        if match is not None:
            key, value = match.groups()
            mixture[key] = value
        else:
            message = f'"{part}" is not a valid key value pair.'
            detail = f'Mixture argument: {value}'
            raise click.BadParameter('\n'.join([message, detail]))
    return mfclib.Mixture(composition=mixture)


def validate_quantity(ctx, param, value):
    try:
        ureg = unitRegistry()
        return ureg.Quantity(value)
    except ValueError:
        raise click.BadParameter(
            f"Could not convert {value} to a number or quantity."
        )
