import logging
from datetime import datetime
from typing import Dict, List, Literal

import pydantic

from ..quantity_type import TimeQ

logger = logging.getLogger(__name__)

LogLevelType = Literal[
    'NOTSET', 'DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL'
]


class DataLoggingConfig(pydantic.BaseModel):
    directory: str = './output/{:%Y-%m-%d}'
    filename: str = 'eurotherm-{:%Y-%m-%dT%H-%M-%S}.csv'
    format: str = "%.6g"
    separator: str = ";"
    rotate_every: TimeQ = TimeQ('1min')
    write_interval: TimeQ = TimeQ('10s')
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
