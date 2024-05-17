import re
from pathlib import Path

import click
import pandas as pd
from rich import box
from rich.table import Table

import mfclib


def _convert_mixture_string(value: str):
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
    return mixture


def validate_balanced_mixture(ctx, param, value):
    mixture = _convert_mixture_string(value)
    return mfclib.Mixture(composition=mixture, strict=True, balance=True)


def validate_unbalanced_mixture(ctx, param, value):
    mixture = _convert_mixture_string(value)
    return mfclib.Mixture(composition=mixture, strict=True, balance=False)


def ensure_mixture(mixture):
    return mfclib.ensure_mixture_type(mixture)


def _validate_quantity(ctx, param, value):
    try:
        ureg = mfclib.config.unitRegistry()
        return ureg.Quantity(value)
    except ValueError:
        raise click.BadParameter(f"Could not convert {value} to a number or quantity.")


def validate_flowrate(ctx, param, value):
    value = _validate_quantity(ctx, param, value)
    if not (value.check("[]") or value.check("[length]**3 / [time]")):
        raise click.BadParameter(
            "Value must be dimensionless or have units of "
            "volumetric flow rate [volume/time]."
        )
    return value


def validate_temperature(ctx, param, value):
    value = _validate_quantity(ctx, param, value)
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
        json = gases.model_dump_json(indent=2, exclude_defaults=True)
        with open(filename, 'w') as f:
            f.write(json)
    except IOError as e:
        raise click.BadParameter(e.message, param='filename')


def dataframe_to_table(df: pd.DataFrame, emit_markdown=False):
    table = Table(
        show_header=True,
        header_style="bold",
        show_footer=True,
        row_styles=["dim", ""],
        box=box.MARKDOWN if emit_markdown else box.HEAVY_HEAD,
    )
    for col in df.columns:
        table.add_column(col)

    for row in df.itertuples(index=False):
        table.add_row(*row)

    # table.add_column("gas")
    # table.add_column("composition")
    # table.add_column(
    #     f"flow rate @ {temperature}",
    #     footer=format_final_value(sum(flow_rates), flowrate),
    #     justify="right",
    # )
    # table.add_column(
    #     f"flow rate @ {Tref}", footer=f"{sum(std_flow_rates)}", justify="right"
    # )
    # table.add_column(f"N2 flow rate @ {Tref}", justify="right")

    # for k, source in enumerate(sources):
    #     table.add_row(
    #         source.name,
    #         ", ".join([f"{key}={value}" for key, value in source.items()]),
    #         f"{flow_rates[k]}",
    #         f"{std_flow_rates[k]}",
    #         f"{source.equivalent_flow_rate(std_flow_rates[k])}",
    #     )

    return table
