import datetime
from abc import abstractmethod
from typing import Literal, cast

import pint
import pydantic

from .. import tools
from ..config import unit_registry
from .._quantity import FlowRateQ, TemperatureQ
from .mixture import Mixture, MixtureType


class CalibrationBase(pydantic.BaseModel):
    date: datetime.date
    gas: Mixture
    temperature: TemperatureQ

    @pydantic.field_validator('gas', mode='before')
    @classmethod
    def check_composition(cls, value):
        return Mixture.create(value)

    def setpoint_to_flowrate(
        self,
        setpoint: str | float | pint.Quantity,
        *,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
    ):
        ureg = unit_registry()
        # check input
        setpoint = tools.validate_range(
            tools.validate_dimension(setpoint, '[]'),
            min_value=0,
            max_value=1,
        )
        if gas is None:
            gas = self.gas
        else:
            gas = Mixture.create(gas)
        if temperature is None:
            temperature = self.temperature
        else:
            temperature = tools.validate_range(
                tools.validate_dimension(
                    temperature, '[temperature]', conversion=TemperatureQ
                ),
                min_value=0.0 * ureg.kelvin,
            )

        # calculate flowrate
        flowrate = self._impl_setpoint_to_flowrate(setpoint)

        # account for different calibration gas
        flowrate *= gas.cf / self.gas.cf

        # account for different temperature
        flowrate *= temperature.to('K') / self.temperature.to('K')
        flowrate = cast(pint.Quantity, flowrate)

        return flowrate

    @abstractmethod
    def _impl_setpoint_to_flowrate(self, setpoint: pint.Quantity) -> pint.Quantity:
        pass

    def flowrate_to_setpoint(
        self,
        flowrate: str | pint.Quantity,
        *,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
    ):
        ureg = unit_registry()
        # check input
        flowrate = tools.validate_dimension(flowrate, '[volume]/[time]')
        if gas is None:
            gas = self.gas
        else:
            gas = Mixture.create(gas)
        if temperature is None:
            temperature = self.temperature
        else:
            temperature = tools.validate_range(
                tools.validate_dimension(
                    temperature, '[temperature]', conversion=TemperatureQ
                ),
                min_value=0.0 * ureg.kelvin,
            )

        # account for different calibration gas
        flowrate *= self.gas.cf / gas.cf

        # account for different temperature
        flowrate *= self.temperature.to('K') / temperature.to('K')

        # calculate setpoint
        setpoint = self._impl_flowrate_to_setpoint(flowrate)

        # ensure setpoint is between 0 and 1
        setpoint = tools.validate_range(setpoint, min_value=0, max_value=1)

        setpoint = cast(pint.Quantity, setpoint)
        return setpoint

    @abstractmethod
    def _impl_flowrate_to_setpoint(self, flowrate: pint.Quantity) -> pint.Quantity:
        pass


class LinearCalibration(CalibrationBase):
    method: Literal['linear'] = 'linear'
    offset: FlowRateQ
    slope: FlowRateQ

    def _impl_setpoint_to_flowrate(self, setpoint: pint.Quantity) -> pint.Quantity:
        return self.offset + setpoint * self.slope

    def _impl_flowrate_to_setpoint(self, flowrate: pint.Quantity):
        return (flowrate - self.offset) / self.slope
