from datetime import datetime
import logging
from os import PathLike
from pathlib import Path
from typing import Annotated, Dict, List, Literal, Optional

import pydantic
from omegaconf import OmegaConf

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
        self.directory.format(datetime.now())
        self.filename.format(datetime.now())
        return self


class AppLogging(pydantic.BaseModel):
    disable_logging: bool = False
    level: LogLevelType = 'INFO'
    formatters: dict[str, dict[str, str]] = pydantic.Field(default_factory=dict)
    handlers: dict[str, dict[str, str | int]] = pydantic.Field(default_factory=dict)


class Config(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='forbid')
    lines: List[models.MFCLine]
    controllers: List[models.MFC] = pydantic.Field(default_factory=list)
    logging: Optional[LoggingConfig] = None
    app_logging: Optional[AppLogging] = None

    @pydantic.model_validator(mode='after')
    def check_for_duplicated_controller_names(self):
        # Check for duplicate names in controllers
        controller_names = [controller.name for controller in self.controllers]
        duplicates = {
            name for name in controller_names if controller_names.count(name) > 1
        }
        if duplicates:
            raise ValueError(
                f'Duplicate controller names found: {", ".join(duplicates)}'
            )
        return self

    @pydantic.model_validator(mode='after')
    def check_for_duplicated_line_names(self):
        # Check for duplicate names in lines
        line_names = [line.name for line in self.lines]
        duplicates = {name for name in line_names if line_names.count(name) > 1}
        if duplicates:
            raise ValueError(f'Duplicate line names found: {", ".join(duplicates)}')
        return self

    @pydantic.model_validator(mode='after')
    def check_that_device_name_is_in_list_of_controllers(self):
        # loop through lines and check if referenced MFC is in controllers
        mfc_names = [mfc.name for mfc in self.controllers]
        for line in self.lines:
            if line.device is not None:
                if line.device.mfc not in mfc_names:
                    raise ValueError(
                        f'MFC device "{line.device.mfc}" not found in controllers'
                    )
        return self

    def get_mfc_for_line(self, line_name: str):
        device = None
        for line in self.lines:
            if line.name == line_name:
                device = line.device
                break
        if device is not None:
            for mfc in self.controllers:
                if mfc.name == device.mfc:
                    return mfc
        return None


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
