from abc import abstractmethod
import datetime
from typing import cast

import pint
import pydantic

from ._quantity import FlowRateQ, TemperatureQ
from .mixture import Mixture, MixtureType
from . import unit_registry


class CalibrationBase(pydantic.BaseModel):
    date: datetime.date
    gas: Mixture
    temperature: TemperatureQ

    @pydantic.field_validator('gas', mode='before')
    @classmethod
    def check_composition(cls, value):
        return Mixture.create(value)

    @staticmethod
    def validate_setpoint(setpoint: str | float | pint.Quantity):
        ureg = unit_registry()
        value = ureg.Quantity(setpoint)
        value = cast(pint.Quantity, value)  # just to please type checkers

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

    @staticmethod
    def validate_flowrate(flowrate: str | pint.Quantity):
        ureg = unit_registry()
        value = ureg.Quantity(flowrate)
        value = cast(pint.Quantity, value)  # just to please type checkers

        # check dimensions of flowrate
        if not value.check('[volume]/[time]'):
            raise ValueError(
                f'Flowrate must have dimensions of [volume]/[time], got: {flowrate}'
            )

        # ensure value is positive
        if value.magnitude < 0:
            raise ValueError(f'Flow rate must be zero or positive, got: {flowrate}')

        return value

    @staticmethod
    def validate_temperature(temperature: str | pint.Quantity):
        ureg = unit_registry()
        value = ureg.Quantity(temperature)
        value = cast(pint.Quantity, value)  # just to please type checkers

        # check dimensions of flowrate
        if not value.check('[temperature]'):
            raise ValueError(
                f'Temperature must have dimensions of [temperature], got: {temperature}'
            )

        # convert to Kelvin to avoid errors caused by ambiguous
        # operations with offset units
        value = value.to('kelvin')

        return value

    @abstractmethod
    def setpoint_to_flowrate(
        self,
        setpoint: str | float | pint.Quantity,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
    ):
        pass

    @abstractmethod
    def flowrate_to_setpoint(self, flowrate: pint.Quantity):
        pass


class LinearCalibration(CalibrationBase):
    offset: FlowRateQ
    slope: FlowRateQ

    def setpoint_to_flowrate(
        self,
        setpoint: str | float | pint.Quantity,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
    ):
        # check input
        setpoint = self.validate_setpoint(setpoint)
        if gas is None:
            gas = self.gas
        else:
            gas = Mixture.create(gas)
        if temperature is None:
            temperature = self.temperature
        else:
            self.validate_temperature(temperature)

        # calculate

    def flowrate_to_setpoint(self, flowrate: pint.Quantity):
        pass


class MFC(pydantic.BaseModel):
    gas: Mixture
    calibration: LinearCalibration
