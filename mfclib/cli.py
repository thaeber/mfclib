import functools
import re
import warnings
from pathlib import Path
from typing import Any, List, Optional

import click
import pint
import tomli
from rich import box, print
from rich.console import Console
from rich.table import Table
from toolz.curried import curry, do, pipe

import mfclib
from ._cli_tools import (
    validate_mixture,
    validate_quantity,
    validate_flowrate,
    validate_temperature,
    validate_sources_filename,
    load_source_gases,
    save_source_gases,
)

warnings.filterwarnings("ignore")
ureg = pipe(
    pint.UnitRegistry(),
    mfclib.config.register_units,
    mfclib.config.configure_unit_registry,
    do(lambda obj: setattr(obj, 'default_format', '.4g~P')),
    do(lambda obj: setattr(obj, 'autoconvert_offset_to_baseunit', True)),
)
assert ureg is not None


def sources_option(f):
    @click.option(
        '-f',
        '--filename',
        type=str,
        default=None,
        callback=validate_sources_filename,
        help='''Specifies the name (and path) of the file that contains the
       source gas mixtures. If not specified, a default file will be created
       in the current directory.
       ''',
    )
    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


def safe_cli():
    try:
        cli()
    except Exception as e:
        print(f"[bold red]ERROR[/bold red]: {e}")


@click.group()
@click.pass_context
def cli(ctx, **kws):
    # ctx.ensure_object(dict)
    # ctx.obj['gases'] = load_source_gases(kws['gases'])
    pass


def format_final_value(value, soll_value):
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


@cli.command('mix')
@click.argument("mixture", type=str, callback=validate_mixture)
@sources_option
@click.option(
    "-V",
    "--flowrate",
    default="1.0L/min",
    show_default=True,
    callback=validate_flowrate,
    help="Volumetric flow rate of final mixture.",
)
@click.option(
    "-T",
    "--temperature",
    default="293K",
    show_default=True,
    callback=validate_temperature,
    help="Temperature of mixed flow.",
)
@click.option("-o", "--output", type=Path)
@click.option("--markdown", is_flag=True, default=False)
def flowmix(mixture: mfclib.Mixture, **kws):
    """
    Calculate flow rates of source gases to obtain a given gas mixture. GASES_FILE contains
    the composition of source gases in TOML format and MIXTURE_COMPOSITION defines the
    target mixture.

    Example:

    \b
    mfc mix --flowrate 2.0L/min -T 20°C "CH4=3200ppm,O2=10%,N2=*"

    """
    # setup
    console = Console(record=True)
    sources = load_source_gases(kws['filename'])
    mixture_total = sum(mixture.mole_fractions).to("dimensionless")

    # get options
    flowrate = kws['flowrate']
    temperature = kws['temperature']
    emit_markdown = kws['markdown']

    # list of all species
    species = set(mixture.species)
    for source in sources:
        species |= set(source.species)
    species = sorted(species)

    # solve for flow rates
    flow_rates = mfclib.supply_proportions_for_mixture(sources, mixture)
    flow_rates *= flowrate

    T_ratio = ureg.Quantity("273.15K") / temperature
    std_flow_rates = flow_rates * T_ratio

    # final mixture composition
    is_mixture = {name: 0.0 for name in species}
    for source, Vdot in zip(sources, flow_rates):
        for name, x in source.items():
            is_mixture[name] += x * Vdot / flowrate
    is_mixture = mfclib.Mixture(composition=is_mixture)

    # output
    console.print(f"Calculating volumetric flow rates for: {mixture!r}")
    console.print(f'Target flow rate: {flowrate} @ {temperature}')

    # flow rates table
    table = Table(
        show_header=True,
        header_style="bold",
        show_footer=True,
        row_styles=["dim", ""],
        box=box.MARKDOWN if emit_markdown else box.HEAVY_HEAD,
    )
    table.add_column("gas")
    table.add_column("composition")
    table.add_column(
        f"flow rate @ {temperature}",
        footer=format_final_value(sum(flow_rates), flowrate),
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
        box=box.MARKDOWN if emit_markdown else box.HEAVY_HEAD,
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

    if output := kws['output']:
        console.save_text(output)


@cli.command()
@click.argument("mixture", type=str, callback=validate_mixture)
def cf(mixture: mfclib.Mixture):
    """
    Calculate conversion factor (CF) for a given gas mixture.

    The conversion factor always refers to a temperature of 273K (0°C)
    and can be used to calculate the flow rate of a MFC if it has been
    calibrated with a different gas (mixture).

    Example:

    \b
    mfc cf "CH4=3200ppm,O2=10%,N2=*"

    """
    # setup
    console = Console()

    # output
    console.rule()
    console.print(f"Calculating conversion factor for: {mixture!r}")
    console.print(f"Conversion factor (CF): {mixture.cf:.4g}", style="bold")
    console.rule()


@cli.group()
def source():
    """Managing available source gas mixtures."""
    pass


@source.command('list')
@sources_option
def list_gases(filename: Optional[str] = None):
    """List the available gas mixtures."""
    gases = load_source_gases(filename)
    console = Console(record=True)
    table = Table(
        show_header=True,
        show_footer=False,
        row_styles=["dim", ""],
        # box=box.MARKDOWN if markdown else box.HEAVY_HEAD,
        box=box.MINIMAL,
    )
    table.add_column('#')
    table.add_column('name')
    table.add_column('composition')
    table.add_column('CF')

    for k, source in enumerate(gases):
        table.add_row(
            f'{k}',
            source.name,
            ", ".join([f"{key}={value}" for key, value in source.items()]),
            f'{source.cf.to("").magnitude:.3f}',
        )
    console.print(table)


@source.command('add')
@click.argument("mixture", type=str, callback=validate_mixture)
@click.option(
    '-n',
    '--name',
    type=str,
    default=None,
    help='''A user defined name of the gas mixture. If not provided,
        a name is synthesized from the component names of the mixture.
        ''',
)
@sources_option
def add_gas(
    mixture: mfclib.Mixture,
    filename: Optional[str] = None,
    name: Optional[str] = None,
):
    """
    Add a gas mixture to the list of source gases. Mixtures are defined
    as a list of key-value pairs, e.g. "CH4=5%,N2=*" or "NO=5000ppm,N2=*".
    """
    sources = load_source_gases(filename)
    if name:
        mixture.name = name
    sources.append(mixture)
    save_source_gases(sources, filename)

    # list gas mixtures
    ctx = click.get_current_context()
    ctx.invoke(list_gases, filename=filename)


@source.command('remove')
@click.option(
    '-i',
    '--id',
    type=int,
    help='The index (#) of the source gas mixture to remove.',
)
# @click.option('-n', '--name', type=str)
@click.option(
    '--all', is_flag=True, default=False, help='Removes all gas mixtures.'
)
@sources_option
def remove_gas(
    filename: Optional[str] = None,
    **kws,
):
    sources = load_source_gases(filename)
    if (id := kws['id']) is not None:
        del sources[id]
    if kws['all']:
        sources.clear()
    save_source_gases(sources, filename)

    # list gas mixtures
    ctx = click.get_current_context()
    ctx.invoke(list_gases, filename=filename)


if __name__ == "__main__":
    cli()
