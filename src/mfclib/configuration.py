from datetime import datetime
import logging
from os import PathLike
from pathlib import Path
from typing import Annotated, Dict, List, Literal, Optional

import pydantic
from omegaconf import OmegaConf
from rich.pretty import pretty_repr

from mfclib._quantity import TimeQ
from . import models

logger = logging.getLogger(__name__)

LogLevelType = Literal[
    'NOTSET', 'DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL'
]


class LoggingConfig(pydantic.BaseModel):
    directory: str = './output/{:%Y-%m-%d}'
    filename: str = 'eurotherm-{:%Y-%m-%dT%H-%M-%S}.csv'
    format: str = "%.6g"
    separator: str = ";"
    rotate_every: Annotated[TimeQ, pydantic.Field(validate_default=True)] = '1min'
    write_interval: Annotated[TimeQ, pydantic.Field(validate_default=True)] = '10s'
    columns: List[str] = [
        'timestamp',
        'processValue',
        'workingOutput',
        'workingSetpoint',
    ]
    units: Dict[str, str] = {
        'processValue': 'K',
        'workingOutput': '%',
        'workingSetpoint': 'K',
    }

    @pydantic.model_validator(mode='after')
    def check_time_intervals(self):
        if self.write_interval >= self.rotate_every:
            raise ValueError(
                (
                    f'The write interval of data packets '
                    f'(write_interval={self.write_interval:~P}) must be '
                    f'shorter than the rotation interval of data files '
                    f'(rotate_every={self.rotate_every:~P})'
                )
            )
        return self

    @pydantic.model_validator(mode='after')
    def check_formatting(self):
        try:
            self.directory.format(datetime.now())
        except:
            raise ValueError(
                f'Cannot format directory name with current date/time: {self.directory}'
            )
        try:
            self.filename.format(datetime.now())
        except:
            raise ValueError(
                f'Cannot format directory name with current date/time: {self.filename}'
            )
        return self


class AppLogging(pydantic.BaseModel):
    disable_logging: bool = False
    level: LogLevelType = 'INFO'
    formatters: dict[str, dict[str, str]] = pydantic.Field(default_factory=dict)
    handlers: dict[str, dict[str, str | int]] = pydantic.Field(default_factory=dict)


class Config(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='forbid')
    lines: List[models.MFCLine]
    logging: Optional[LoggingConfig] = None
    app_logging: Optional[AppLogging] = None


def get_configuration(
    *,
    cmd_args: Optional[List[str]] = None,
    filename: str | PathLike = '.eurotherm.yaml',
    use_cli=False,
):
    cfg = OmegaConf.load(Path(filename))
    if use_cli:
        cfg.merge_with_cli()
    if cmd_args is not None:
        cfg.merge_with_dotlist(cmd_args)

    result = Config.model_validate(OmegaConf.to_container(cfg, resolve=True))

    return result
