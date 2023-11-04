import functools
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import click
import numpy as np
import pint
import rich.traceback
from rich import box
from rich.console import Console
from rich.table import Table
from toolz.curried import do, pipe

import mfclib

from ._cli_tools import (
    ensure_mixture,
    load_source_gases,
    save_source_gases,
    validate_balanced_mixture,
    validate_flowrate,
    validate_sources_filename,
    validate_temperature,
    validate_unbalanced_mixture,
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
    rich.traceback.install()
    cli()
    # try:
    #     cli()
    # except Exception as e:
    #     print(f"[bold red]ERROR[/bold red]: {e}")


@click.group()
@click.pass_context
def cli(ctx, **kws):
    # ctx.ensure_object(dict)
    # ctx.obj['gases'] = load_source_gases(kws['gases'])
    pass


class StatusFlag(Enum):
    NONE = 1
    OK = 2
    WARNING = 3
    ERROR = 4


def _format_status(value: Any, status: StatusFlag):
    match status:
        case StatusFlag.NONE:
            return f'{value}'
        case StatusFlag.OK:
            return f"[green1]:heavy_check_mark:[/green1] {value}"
        case StatusFlag.WARNING:
            return f"[orange1]:warning:[/orange1] {value}"
        case StatusFlag.ERROR:
            return f"[bold red1]:x:[/bold red1] {value}"


def _format(value, reference):
    # return f'{value}'
    try:
        value = value.to(reference.units)
    except AttributeError:
        pass
    tolerance = 1e-3
    if isinstance(reference, str):
        return _format_status(value, StatusFlag.NONE)
    elif reference is None:
        return _format_status(
            value,
            StatusFlag.OK if np.isclose(value, 0.0) else StatusFlag.WARNING,
        )
    elif reference == 0:
        return _format_status(
            value, StatusFlag.OK if abs(value) < tolerance else StatusFlag.ERROR
        )
    else:
        return _format_status(
            value,
            StatusFlag.OK
            if abs(1.0 - value / reference) < tolerance
            else StatusFlag.ERROR,
        )


def mix_sources(sources, fractions):
    mixture = {}
    for source, phi in zip(sources, fractions):
        for name, x in source.items():
            if name not in mixture:
                mixture[name] = x * phi
            else:
                mixture[name] += x * phi
    mixture = ensure_mixture(mixture)
    return mixture


@cli.command('mix')
@click.argument("mixture", type=str, callback=validate_unbalanced_mixture)
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
@click.option(
    "--Tref",
    default="273K",
    show_default=True,
    callback=validate_temperature,
    help="Calibration temperature of MFCs.",
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
    mixture_total = 1.0  # sum(mixture.mole_fractions).to("dimensionless")

    # get options
    flowrate = kws['flowrate']
    temperature = kws['temperature']
    Tref = kws['tref']
    emit_markdown = kws['markdown']

    # list of all species
    species = set(mixture.keys())
    for source in sources:
        species |= set(source.species)
    species = sorted(species)

    # solve for flow rates
    source_fractions = mfclib.supply_proportions_for_mixture(sources, mixture)

    # source flow rates at target and reference temperature
    T_ratio = Tref / temperature
    flow_rates = source_fractions * flowrate
    std_flow_rates = flow_rates * T_ratio

    # final mixture composition
    final_mixture = mix_sources(sources, source_fractions)

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
        footer=_format(sum(flow_rates), flowrate),
        justify="right",
    )
    table.add_column(
        f"flow rate @ {Tref}", footer=f"{sum(std_flow_rates)}", justify="right"
    )
    table.add_column(f"N2 flow rate @ {Tref}", justify="right")
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
        'soll',
        *[
            f"{mixture.get(name) if name in mixture else ''}"
            for name in species
        ],
        f"{mixture_total}",
    )
    table.add_row(
        "is",
        *[
            _format(
                final_mixture.get(name),
                mixture.get(name) if name in mixture else None,
            )
            for name in species
        ],
        _format(sum(final_mixture.mole_fractions), mixture_total),
    )
    console.print(table)

    if output := kws['output']:
        console.save_text(output)


@cli.command()
@click.argument("mixture", type=str, callback=validate_balanced_mixture)
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
@click.argument("mixture", type=str, callback=validate_balanced_mixture)
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
    mixture = ensure_mixture(mixture)
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
