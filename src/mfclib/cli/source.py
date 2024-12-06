from typing import Optional

import click
from rich import box
from rich.console import Console
from rich.table import Table

import mfclib
from .main import run

from ._cli_tools import (
    ensure_mixture,
    load_source_gases,
    save_source_gases,
    validate_balanced_mixture,
)


@run.group()
def source():
    """Managing available source gas mixtures."""
    pass


@source.command('list')
# @sources_option
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
# @sources_option
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
@click.option('--all', is_flag=True, default=False, help='Removes all gas mixtures.')
# @sources_option
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
    run()
