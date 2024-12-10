import logging
from os import PathLike
from pathlib import Path
from typing import List, Literal, Optional

import pydantic
from omegaconf import OmegaConf

from mfclib._quantity import FlowRateQ, TemperatureQ

from ..tools import first_or_default
from .data_logging import DataLoggingConfig
from .line import MFCLine
from .mfc import MFC

logger = logging.getLogger(__name__)

LogLevelType = Literal[
    'NOTSET', 'DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL'
]


class AppLogging(pydantic.BaseModel):
    disable_logging: bool = False
    level: LogLevelType = 'INFO'
    formatters: dict[str, dict[str, str]] = pydantic.Field(default_factory=dict)
    handlers: dict[str, dict[str, str | int]] = pydantic.Field(default_factory=dict)


class Config(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='forbid')
    lines: List[MFCLine]
    controllers: List[MFC] = pydantic.Field(default_factory=list)
    logging: Optional[DataLoggingConfig] = None
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

    def get_mfc_by_name(self, name: str):
        return first_or_default(lambda x: x.name == name, self.controllers, None)

    def get_mfc_by_line(self, line: MFCLine):
        if (line is not None) and (line.device is not None):
            return self.get_mfc_by_name(line.device.mfc)

    def flowrate_to_setpoint(
        self,
        line: MFCLine,
        flowrate: FlowRateQ,
        temperature: TemperatureQ,
    ):
        if mfc := self.get_mfc_by_line(line):
            return mfc.flowrate_to_setpoint(
                flowrate,
                gas=line.gas,
                temperature=temperature,
                calibration=line.device.calibration,
            ).to('percent')
        else:
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
