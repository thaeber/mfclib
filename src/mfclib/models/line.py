from typing import Optional

import pydantic

from .mfc import CalibrationSelector
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

    @pydantic.computed_field
    def mfc_name(self) -> Optional[str]:
        if self.device is None:
            return None
        else:
            return self.device.mfc
