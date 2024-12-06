import logging
import os
import sys
from pathlib import Path

import click
import rich.traceback
from rich.console import Console
from rich.pretty import pretty_repr

import mfclib

from ..configuration import get_configuration
from ..logging import AppLoggingMode, configure_app_logging
from ._cli_tools import validate_balanced_mixture

logger = logging.getLogger(__name__)


# warnings.filterwarnings("ignore")
rich.traceback.install(suppress=[click])
os.environ["GRPC_VERBOSITY"] = "ERROR"


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
def run(ctx: click.Context, config_filename: str):
    # cli wide settings for underlying unit registry
    ureg = mfclib.unit_registry()
    ureg.default_format = ".4g~P"
    ureg.autoconvert_offset_to_baseunit = True

    # load configuration
    config = get_configuration(filename=config_filename)

    # configure logging
    mode = AppLoggingMode.NONE
    match sys.argv:
        case [_, 'ui', *rest]:
            mode = AppLoggingMode.NONE
        case [_, 'server', 'start']:
            mode = AppLoggingMode.SERVER
        case _:
            mode = AppLoggingMode.CLIENT
    configure_app_logging(mode, config=config.app_logging)

    # if config.app_logging is not None:
    #     logging.config.dictConfig(config.app_logging)
    logger.info(f'Loaded configuration from: {config_filename}')

    # log original command
    logger.info(f'[cli] {Path(sys.argv[0]).name} {" ".join(sys.argv[1:])}')
    logger.debug('Using configuration:')
    logger.debug(pretty_repr(config.model_dump()))

    ctx.obj = dict(config=config)


@run.command()
@click.argument("mixture", type=str, callback=validate_balanced_mixture)
def cf(mixture: mfclib.models.Mixture):
    """
    Calculate conversion factor (CF) for a given gas mixture.

    The conversion factor can be used to calculate the flow rate
    of a MFC if it has been calibrated with a different gas (mixture).
    Beware that the accuracy of the conversion factor is limited to
    about 5%.

    Example:

    \b
    mfc cf "CH4=3200ppm,O2=10%,N2=*"
    mfc cf "CH4=3200ppm; O2=10%; N2=*"
    mfc cf "CH4:3200ppm; O2:10%; N2:*"

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
