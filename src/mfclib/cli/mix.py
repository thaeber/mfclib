from functools import partial
import logging
from enum import Enum
from pathlib import Path
from typing import Any, List

import click
import numpy as np
import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table

import mfclib

from .. import models
from .._quantity import FlowRateQ, TemperatureQ
from ..configuration import Config
from ..tools import pipe
from ._cli_tools import validate_unbalanced_mixture
from .main import run

logger = logging.getLogger(__name__)


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
    default="293K",
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
    console = Console(record=True)
    mixture_total = 1.0  # sum(mixture.mole_fractions).to("dimensionless")
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
    std_flow_rates = flow_rates * T_ratio

    # final mixture composition
    final_mixture = mix_sources(sources, source_fractions)

    # gather results in DataFrame
    df = pd.DataFrame()
    df['gas'] = [line.gas.name for line in config.lines]
    df['composition'] = [
        ", ".join([f"{key}={value}" for key, value in line.gas.items()])
        for line in config.lines
    ]
    df[f'flowrate @ {temperature}'] = [f for f in flow_rates]
    df['line'] = [line.name for line in config.lines]
    mfcs: List[None | models.MFC] = pipe(
        config.lines,
        partial(map, lambda line: config.get_mfc_for_line(line.name)),
        list,
    )
    df['MFC'] = [mfc.name if mfc is not None else '' for mfc in mfcs]

    # output
    console.print(f"Calculating volumetric flow rates for: {mixture!r}")
    console.print(f'Target flow rate: {flowrate} @ {temperature}')

    # emit gas lines
    box_style = box.MARKDOWN if emit_markdown else box.SIMPLE
    emit_table(console, df, box=box_style)

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

    if output:
        console.save_text(output)


def emit_table(console, df, box=box.SIMPLE):
    table = Table(
        show_header=True,
        header_style="bold",
        show_footer=True,
        row_styles=["dim", ""],
        box=box,
    )
    for col in df.columns:
        table.add_column(col)

    for k, row in df.iterrows():
        table.add_row(*[str(value) for value in row.values])
    console.print(table)
