import re
from typing import Any, Callable, List
import warnings

import click
import pint
import tomli
import xarray as xr
from rich import print
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
import rich.traceback

import mfclib

warnings.filterwarnings("ignore")
ureg = mfclib.register_pint()
ureg.default_format = ".4g~P"
ureg.autoconvert_offset_to_baseunit = True


def safe_cli():
    try:
        cli()
    except Exception as e:
        print(f"[bold red]ERROR[/bold red]: {e}")


@click.group()
def cli():
    pass


def unify_flow_rate(flow: Any):
    try:
        return pint.Quantity(flow)
    except ValueError:
        raise ValueError(f"Could not convert {flow} to a number.")


def parse_mixture_args(args: List[str]):
    regex = re.compile("(.*)\s*[=:]\s*(.*)")
    mixture = {}
    for arg in args:
        match = regex.match(arg)
        if match is not None:
            key, value = match.groups()
            mixture[key] = value
        else:
            raise ValueError(f"{arg} is not a valid key value pair.")
    return mfclib.Mixture(mixture)


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


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("gases_file", type=click.File("rb"))
@click.argument("mixture_composition", nargs=-1, type=str)
@click.option("--flow", default=1.0, type=str)
@click.option("-T", "--temperature", default="293K", type=str)
def flowmix(gases_file, mixture_composition, flow, temperature):
    # setup
    sources = [mfclib.Supply.from_kws(**gas) for gas in tomli.load(gases_file)["gases"]]
    total_flow_rate = unify_flow_rate(flow)
    temperature = ureg.Quantity(temperature)
    mixture = parse_mixture_args(mixture_composition)
    mixture_total = sum(mixture.mole_fractions).to("dimensionless")

    # check dimensionality of flow rate
    if not (
        total_flow_rate.check("[]") or total_flow_rate.check("[length]**3 / [time]")
    ):
        raise ValueError(
            "`flow` must be dimensionless or have units of volumetric flow rate \[volume/time]."
        )

    # list of all species
    species = set(mixture.species)
    for source in sources:
        species |= set(source.feed.species)
    species = sorted(species)

    # solve for flow rates
    flow_rates = mfclib.supply_proportions_for_mixture(sources, mixture)
    flow_rates *= total_flow_rate

    T_ratio = ureg.Quantity("273.15K") / temperature
    std_flow_rates = flow_rates * T_ratio

    # final mixture composition
    is_mixture = mfclib.MutableMixture({name: 0.0 for name in species})
    for source, Vdot in zip(sources, flow_rates):
        for name, x in source.feed.items():
            is_mixture[name] += x * Vdot / total_flow_rate
    # for name in species:
    #     if name in mixture:
    #         is_mixture[name] = is_mixture[name].to(mixture[name].units)

    # output
    console = Console()
    console.print(f"Calculating volumetric flow rates for: {mixture}")

    # flow rates table
    table = Table(
        show_header=True, header_style="bold", show_footer=True, row_styles=["dim", ""]
    )
    table.add_column("gas")
    table.add_column("composition")
    table.add_column(
        f"flow rate @ {temperature}",
        footer=format_final_value(sum(flow_rates), total_flow_rate),
        justify="right",
    )
    table.add_column(
        f"flow rate @ 273K", footer=f"{sum(std_flow_rates)}", justify="right"
    )
    table.add_column(f"N2 flow rate @ 273K", justify="right")
    for k, source in enumerate(sources):
        table.add_row(
            source.name,
            ", ".join([f"{key}={value}" for key, value in source.feed.items()]),
            f"{flow_rates[k]}",
            f"{std_flow_rates[k]}",
            f"{source.equivalent_flow_rate(std_flow_rates[k])}",
        )
    console.print(table)

    # mixture composition table
    table = Table(show_header=True, row_styles=["dim", ""])
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


if __name__ == "__main__":
    cli()
