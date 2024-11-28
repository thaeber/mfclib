from abc import abstractmethod
import datetime
from typing import Literal, cast

import pint
import pydantic
import pydantic_core
from typing_extensions import Annotated

from ._quantity import FlowRateQ, TemperatureQ
from .mixture import Mixture
from . import unit_registry


class CalibrationBase(pydantic.BaseModel):
    date: datetime.date
    gas: Mixture
    temperature: TemperatureQ

    @staticmethod
    def validate_setpoint(setpoint: float | pint.Quantity):
        ureg = unit_registry()
        value = ureg.Quantity(setpoint)
        value = cast(pint.Quantity, value)

        # check that setpoint is dimensionless
        if not value.check('[]'):
            raise ValueError(f'Setpoint must be dimensionless, got: {setpoint}')

        value = value.m_as('')

        # check that magnitude is between 0 and 1
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f'Setpoint must be between 0 (0%) and 1 (100%), received: {setpoint}'
            )

        return float(value)

    @abstractmethod
    def setpoint_to_flowrate(self, setpoint: pint.Quantity):
        pass

    @abstractmethod
    def flowrate_to_setpoint(self, flowrate: pint.Quantity):
        pass


class LinearCalibration(CalibrationBase):
    offset: FlowRateQ
    slope: FlowRateQ

    def setpoint_to_flowrate(self, setpoint: pint.Quantity):
        pass

    def flowrate_to_setpoint(self, flowrate: pint.Quantity):
        pass


class MFC(pydantic.BaseModel):
    gas: Mixture
    calibration: LinearCalibration
