import logging
from enum import Enum
from functools import partial
from itertools import starmap
from pathlib import Path
from typing import Any, Dict

import click
import numpy as np
import pandas as pd
import pint
from rich import box
from rich.console import Console
from rich.table import Table

import mfclib

from .. import models
from ..quantity_type import FlowRateQ, TemperatureQ
from ..config import balanceSpeciesIndicator, unit_registry
from ..models.configuration import Config
from ..tools import is_none, is_not_none, map_if, pipe, replace
from ._cli_tools import validate_unbalanced_mixture
from .main import run

logger = logging.getLogger(__name__)


class StatusFlag(Enum):
    NONE = 1
    OK = 2
    WARNING = 3
    ERROR = 4

    def __str__(self):
        match self:
            case StatusFlag.NONE:
                return ''
            case StatusFlag.OK:
                return '[green1]:heavy_check_mark:[/green1]'
            case StatusFlag.WARNING:
                return '[orange1]:warning:[/orange1]'
            case StatusFlag.ERROR:
                return '[bold red1]:x:[/bold red1]'

    def __repr__(self):
        return self.__str__()


def format_with_status(value: Any, status: StatusFlag):
    match status:
        case StatusFlag.NONE:
            return f'{value}'
        case StatusFlag.OK:
            return f"[green1]:heavy_check_mark: {value}[/green1]"
        case StatusFlag.WARNING:
            return f"[orange1]:warning: {value}[/orange1]"
        case StatusFlag.ERROR:
            return f"[bold red1]:x: {value}[/bold red1]"


def format_value(value: pint.Quantity, reference: str | pint.Quantity = '', rtol=1e-3):
    status = StatusFlag.NONE
    ureg = unit_registry()
    if isinstance(reference, ureg.Quantity):
        value = value.to(reference.units)

        if np.isclose(value, reference, rtol=rtol):
            status = StatusFlag.OK
        else:
            status = StatusFlag.ERROR
    elif reference == balanceSpeciesIndicator():
        status = StatusFlag.NONE
    elif reference == '':
        if np.isclose(value, 0.0):
            status = StatusFlag.OK
        else:
            status = StatusFlag.WARNING

    return format_with_status(value, status)


def mix_sources(sources, fractions):
    mixture = {}
    for source, phi in zip(sources, fractions):
        for name, x in source.items():
            if name not in mixture:
                mixture[name] = x * phi
            else:
                mixture[name] += x * phi
    mixture = models.Mixture.create(mixture)
    return mixture


@run.command('mix')
@click.pass_context
@click.argument("mixture", type=str, callback=validate_unbalanced_mixture)
@click.option(
    "-V",
    "--flowrate",
    default="1.0L/min",
    show_default=True,
    type=FlowRateQ,
    help="Volumetric flow rate of final mixture.",
)
@click.option(
    "-T",
    "--temperature",
    default="20°C",
    show_default=True,
    type=TemperatureQ,
    help="Temperature of mixed flow.",
)
@click.option(
    "--Tref",
    "reference_temperature",
    default="273K",
    show_default=True,
    type=TemperatureQ,
    help="Calibration temperature of MFCs.",
)
@click.option("-o", "--output", type=Path)
@click.option("--markdown", "emit_markdown", is_flag=True, default=False)
def flowmix(
    ctx: click.Context,
    mixture: mfclib.models.Mixture,
    flowrate: FlowRateQ,
    temperature: TemperatureQ,
    reference_temperature: TemperatureQ,
    output: Path,
    emit_markdown: bool,
):
    """
    Calculate flow rates of source gases to obtain a given gas MIXTURE.
    The available sources are defined in the configuration file (see --config
    option of the base command `mfc`).

    Example:

    \b
    mfc mix --flowrate 2.0L/min -T 20°C "CH4=3200ppm,O2=10%,N2=*"

    """
    # setup
    ureg = mfclib.unit_registry()
    console = Console(record=True)
    sum(mixture.fractions.values()).to("dimensionless")
    config: Config = ctx.obj['config']

    # get options
    sources = [line.gas for line in config.lines]
    Tref = reference_temperature

    # list of all species
    species = set(mixture.keys())
    for source in sources:
        species |= set(source.species)
    species = sorted(species)

    # solve for flow rates
    source_fractions = models.supply_proportions_for_mixture(sources, mixture)

    # source flow rates at target and reference temperature
    T_ratio = Tref / temperature
    flow_rates = source_fractions * flowrate
    flow_rates * T_ratio

    # final mixture composition
    final_mixture = mix_sources(sources, source_fractions)

    # output
    console.print(f"Calculating volumetric flow rates for: {mixture!r}")
    console.print(f'Target flow rate: {flowrate} @ {temperature}')

    # gather results in DataFrame
    df_lines = pd.DataFrame()
    df_lines['gas'] = [line.gas.name for line in config.lines]
    df_lines['composition'] = [
        ", ".join([f"{key}={value}" for key, value in line.gas.items()])
        for line in config.lines
    ]
    df_lines['flowrate'] = [f for f in flow_rates]
    df_lines['setpoint'] = pipe(
        zip(config.lines, flow_rates),
        partial(
            starmap,
            lambda line, value: config.flowrate_to_setpoint(line, value, temperature),
        ),
        partial(replace, is_none, format_with_status(np.nan, StatusFlag.WARNING)),
        list,
    )
    df_lines['line'] = [line.name for line in config.lines]
    df_lines['MFC'] = pipe(
        config.lines,
        partial(map, config.get_mfc_by_line),
        partial(map_if, is_not_none, lambda x: x.name),
        partial(replace, is_none, format_with_status('missing', StatusFlag.WARNING)),
        list,
    )
    footer = {'flowrate': format_value(sum(flow_rates), flowrate)}

    # emit gas lines
    box_style = box.MARKDOWN if emit_markdown else box.HORIZONTALS
    emit_table(
        console,
        df_lines,
        box=box_style,
        header={'flowrate': f'flowrate @ {temperature}'},
        footer=footer,
        justify={'flowrate': 'right', 'setpoint': 'right'},
        column_style={'setpoint': 'bold'},
    )

    # mixture composition table
    df_mixture = pd.DataFrame.from_records(
        [
            {name: mixture.composition.get(name, '') for name in species},
            {
                name: format_value(
                    final_mixture[name], mixture.composition.get(name, '')
                )
                for name in species
            },
        ]
    )
    df_mixture['sum'] = [
        sum(mixture.fractions.values()).to('%'),
        format_value(
            sum(final_mixture.fractions.values()).to('%'), 100.0 * ureg.percent
        ),
    ]
    df_mixture.insert(0, 'name', ['soll', 'is'])

    box_style = box.MARKDOWN if emit_markdown else box.HORIZONTALS
    emit_table(
        console,
        df_mixture,
        box=box_style,
        justify={name: 'right' for name in df_mixture.columns},
        header={'name': ''},
        column_style={'sum': 'dim'},
    )

    if output:
        console.save_text(output)


def emit_table(
    console,
    df,
    header: None | Dict[str, Any] = None,
    footer: None | Dict[str, Any] = None,
    justify: None | Dict[str, Any] = None,
    column_style: None | Dict[str, Any] = None,
    box=box.SIMPLE,
):
    table = Table(
        show_header=True,
        header_style="bold",
        show_footer=footer is not None,
        # row_styles=["dim", ""],
        box=box,
    )
    if header is None:
        header = {}
    if footer is None:
        footer = {}
    if justify is None:
        justify = {}
    if column_style is None:
        column_style = {}

    for col in df.columns:
        table.add_column(
            header.get(col, col),
            footer=str(footer.get(col, '')),
            justify=justify.get(col, 'left'),
            style=column_style.get(col, None),
        )

    for k, row in df.iterrows():
        table.add_row(*[str(value) for value in row.values], style="")
    console.print(table)
