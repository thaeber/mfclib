import functools
import os
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

# warnings.filterwarnings("ignore")
rich.traceback.install(suppress=[click])
os.environ["GRPC_VERBOSITY"] = "ERROR"

# cli wide settings for underlying unit registry
ureg = mfclib.unit_registry()
ureg.default_format = ".4g~P"
ureg.autoconvert_offset_to_baseunit = True


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


@click.group()
@click.pass_context
@click.option(
    '-c',
    '--config',
    'config_filename',
    type=str,
    default='.mfc-config.yaml',
    show_default=True,
    help='''The name/path of the configuration file.''',
)
def run(ctx: click.Context, **kws):
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
            (
                StatusFlag.OK
                if abs(1.0 - value / reference) < tolerance
                else StatusFlag.ERROR
            ),
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


@run.command('mix')
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
def flowmix(mixture: mfclib.models.Mixture, **kws):
    """
    Calculate flow rates of source gases to obtain a given gas mixture.
    GASES_FILE contains the composition of source gases in TOML format
    and MIXTURE_COMPOSITION defines the target mixture.

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
        *[f"{mixture.get(name) if name in mixture else ''}" for name in species],
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


@run.command()
@click.argument("mixture", type=str, callback=validate_balanced_mixture)
def cf(mixture: mfclib.models.Mixture):
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


if __name__ == "__main__":
    run()
