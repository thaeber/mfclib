import re

import click

from .. import models


def mixture_string_to_mapping(input: str):
    parts_regex = re.compile(r'\s*[,;/]\s*')
    kv_regex = re.compile(r"(.*)[=:](.*)")
    mixture = {}
    for part in parts_regex.split(input):
        part = part.strip()
        if part == '':
            continue
        match = kv_regex.match(part)
        key, value = '', ''
        if match is not None:
            key, value = match.groups()
            key = key.strip()
            value = value.strip()

        if (key == '') or (value == ''):
            message = f'Invalid key value pair: {part}'
            detail = f'Mixture argument: {value}'
            raise click.BadParameter('\n'.join([message, detail]))

        mixture[key] = value

    return mixture


def validate_balanced_mixture(ctx, param, value):
    mixture = mixture_string_to_mapping(value)
    return models.Mixture(composition=mixture, strict=True, balance=True)


def validate_unbalanced_mixture(ctx, param, value):
    mixture = mixture_string_to_mapping(value)
    return models.Mixture(composition=mixture, strict=True, balance=False)
