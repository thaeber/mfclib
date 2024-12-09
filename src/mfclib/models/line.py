from typing import List, Literal, Optional, Union

import pydantic

from .._quantity import FlowRateQ, TemperatureQ
from .mfc import MFC, CalibrationSelector
from .mixture import Mixture


class MFCDevice(pydantic.BaseModel):
    mfc: str
    calibration: CalibrationSelector = 'latest'


class MFCLine(pydantic.BaseModel):
    name: str
    gas: Mixture
    device: Optional[MFCDevice] = None

    @pydantic.field_validator('gas', mode='before')
    @classmethod
    def check_composition(cls, value):
        return Mixture.create(value)
