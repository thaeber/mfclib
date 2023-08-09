import re
import warnings
from pathlib import Path
from typing import Any, List

import click
import pint
import tomli
from rich import box, print
from rich.console import Console
from rich.table import Table
from toolz.curried import curry, do, pipe

import mfclib

warnings.filterwarnings("ignore")
ureg = pipe(
    pint.UnitRegistry(),
    mfclib.register_units,
    mfclib.configure_unit_registry,
    do(lambda obj: setattr(obj, 'default_format', '.4g~P')),
    do(lambda obj: setattr(obj, 'autoconvert_offset_to_baseunit', True)),
)
assert ureg is not None
# ureg.default_format = '.4g~P'
# ureg.autoconvert_offset_to_baseunit = True


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
            detail = f'Mixture argument: {arg}'
            raise click.BadParameter('\n'.join([message, detail]))
    return mfclib.Mixture(composition=mixture)


def validate_quantity(ctx, param, value):
    try:
        return ureg.Quantity(value)
    except ValueError:
        raise click.BadParameter(
            f"Could not convert {value} to a number or quantity."
        )


def safe_cli():
    try:
        cli()
    except Exception as e:
        print(f"[bold red]ERROR[/bold red]: {e}")


@click.group()
def cli():
    pass


def format_final_value(value, soll_value):
    print(value, soll_value)
    value = value.to(soll_value.units)
    tolerance = 1e-3
    if soll_value == 0:
        check = abs(value) < tolerance
    else:
        check = abs(1.0 - value / soll_value) < tolerance
    if not check:
        return f":x: [bold red]{value}[/bold red]"
    else:
        return f":heavy_check_mark: [green]{value}[/green]"


@cli.command()
@click.argument("gases_file", type=click.File("rb"))
@click.argument("mixture", type=str, callback=validate_mixture)
@click.option(
    "-f",
    "--flow",
    default="1.0L/min",
    show_default=True,
    callback=validate_quantity,
    help="Target flow rate of final mixture.",
)
@click.option(
    "-T",
    "--temperature",
    default="293K",
    show_default=True,
    callback=validate_quantity,
    help="Temperature of mixed flow.",
)
@click.option("-o", "--output", type=Path)
@click.option("--markdown", is_flag=True)
def flowmix(gases_file, mixture, flow, temperature, output, markdown):
    """
    Calculate flow rates of source gases to obtain a given gas mixture. GASES_FILE contains
    the composition of source gases in TOML format and MIXTURE_COMPOSITION defines the
    target mixture.

    Example:

    \b
    mfc flowmix --flow 2.0L/min -T 20°C methane_oxidation.toml "CH4=3200ppm,O2=10%,N2=*"

    """
    # setup
    console = Console(record=True)
    sources = [
        mfclib.Mixture.from_kws(**gas)
        for gas in tomli.load(gases_file)["gases"]
    ]
    mixture_total = sum(mixture.mole_fractions).to("dimensionless")

    # check dimensionality of flow rate
    if not (flow.check("[]") or flow.check("[length]**3 / [time]")):
        raise ValueError(
            "`flow` must be dimensionless or have units of volumetric flow rate \[volume/time]."
        )

    # list of all species
    species = set(mixture.species)
    for source in sources:
        species |= set(source.species)
    species = sorted(species)

    # solve for flow rates
    flow_rates = mfclib.supply_proportions_for_mixture(sources, mixture)
    flow_rates *= flow

    T_ratio = ureg.Quantity("273.15K") / temperature
    std_flow_rates = flow_rates * T_ratio

    # final mixture composition
    is_mixture = {name: 0.0 for name in species}
    for source, Vdot in zip(sources, flow_rates):
        for name, x in source.items():
            is_mixture[name] += x * Vdot / flow
    is_mixture = mfclib.Mixture(composition=is_mixture)

    # output
    console.print(f"Calculating volumetric flow rates for: {mixture!r}")
    console.print(f'Target flow rate: {flow} @ {temperature}')

    # flow rates table
    table = Table(
        show_header=True,
        header_style="bold",
        show_footer=True,
        row_styles=["dim", ""],
        box=box.MARKDOWN if markdown else box.HEAVY_HEAD,
    )
    table.add_column("gas")
    table.add_column("composition")
    table.add_column(
        f"flow rate @ {temperature}",
        footer=format_final_value(sum(flow_rates), flow),
        justify="right",
    )
    table.add_column(
        f"flow rate @ 273K", footer=f"{sum(std_flow_rates)}", justify="right"
    )
    table.add_column(f"N2 flow rate @ 273K", justify="right")
    for k, source in enumerate(sources):
        table.add_row(
            source.name,
            ", ".join([f"{key}={value}" for key, value in source.items()]),
            f"{flow_rates[k]}",
            f"{std_flow_rates[k]}",
            f"{source.equivalent_flow_rate(std_flow_rates[k])}",
        )
    console.print(table)

    # mixture composition table
    table = Table(
        show_header=True,
        row_styles=["dim", ""],
        box=box.MARKDOWN if markdown else box.HEAVY_HEAD,
    )
    table.add_column("")
    for name in species:
        table.add_column(name, justify="right")
    table.add_column("sum", justify="right")
    table.add_row(
        "soll",
        *[f"{mixture.get(name)}" for name in species],
        f"{mixture_total}",
    )
    table.add_row(
        "is",
        *[
            format_final_value(is_mixture.get(name), mixture.get(name))
            for name in species
        ],
        format_final_value(sum(is_mixture.mole_fractions), mixture_total),
    )
    console.print(table)

    if output:
        console.save_text(output)


@cli.command()
@click.argument("mixture", type=str, callback=validate_mixture)
def cf(mixture: mfclib.Mixture):
    """
    Calculate conversion factor (CF) for a given gas mixture. The conversion
    factor always refers to a temperature of 273K (0°C) and can be used
    to calculate the flow rate of a MFC if it has been calibrated with a
    different gas (mixture).

    Example:

    \b
    mfc cf CH4=3200ppm O2=10% N2=*

    """
    # setup
    console = Console()

    # output
    console.rule()
    console.print(f"Calculating conversion factor for: {mixture!r}")
    console.print(f"Conversion factor (CF): {mixture.cf:.4g}", style="bold")
    console.rule()


if __name__ == "__main__":
    cli()
