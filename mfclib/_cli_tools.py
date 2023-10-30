import re
from pathlib import Path

import click

import mfclib


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
    # return mfclib.Mixture(composition=mixture)
    return mixture


def validate_quantity(ctx, param, value):
    try:
        ureg = mfclib.config.unitRegistry()
        return ureg.Quantity(value)
    except ValueError:
        raise click.BadParameter(
            f"Could not convert {value} to a number or quantity."
        )


def validate_flowrate(ctx, param, value):
    value = validate_quantity(ctx, param, value)
    if not (value.check("[]") or value.check("[length]**3 / [time]")):
        raise click.BadParameter(
            "Value must be dimensionless or have units of volumetric flow rate \[volume/time]."
        )
    return value


def validate_temperature(ctx, param, value):
    value = validate_quantity(ctx, param, value)
    if not (value.check("[]") or value.check("[temperature]")):
        raise click.BadParameter(
            "Value must be dimensionless or have units of temperature."
        )
    return value


def validate_sources_filename(ctx, param, value):
    if value and not Path(value).exists():
        raise click.BadParameter('The file does not exists.')
    return value


def load_source_gases(filename: None | str | Path = None):
    if not filename:
        filename = mfclib.config.sourceGasesFile()
    filename = Path(filename)

    if not filename.exists():
        return mfclib.MixtureCollection()
    else:
        with open(filename) as f:
            json = f.read()
            return mfclib.MixtureCollection.model_validate_json(json)


def save_source_gases(
    gases: mfclib.MixtureCollection, filename: None | str | Path = None
):
    if not filename:
        filename = mfclib.config.sourceGasesFile()
    filename = Path(filename)

    # dump mixtures as JSON
    try:
        json = gases.model_dump_json(indent=2)
        with open(filename, 'w') as f:
            f.write(json)
    except IOError as e:
        raise click.BadParameter(e.message, param='filename')
