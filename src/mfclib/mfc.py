import datetime
from abc import abstractmethod
from typing import Annotated, List, Literal, Optional, Union, cast

import pint
import pydantic

from . import tools, unit_registry
from ._quantity import FlowRateQ, TemperatureQ, ElectricPotentialQ
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
        flowrate *= temperature / self.temperature
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
        flowrate *= self.temperature / temperature

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


class MFCInfo(pydantic.BaseModel):
    manufacturer: Optional[str] = None
    make: Optional[str] = None
    serial_number: Optional[str] = None
    specifications: Optional[str] = None


class MFCNoDevice(pydantic.BaseModel):
    connection: Literal['None'] = 'None'


class MFCAnalogDevice(pydantic.BaseModel):
    connection: Literal['Analog'] = 'Analog'
    max_output_voltage: ElectricPotentialQ
    max_input_voltage: ElectricPotentialQ


class MFCFlowBusDevice(pydantic.BaseModel):
    connection: Literal['FlowBus'] = 'FlowBus'


CalibrationType = Annotated[
    Union[LinearCalibration], pydantic.Field(discriminator='method')
]

CalibrationSelector = Union[int, Literal['latest']]


class MFC(pydantic.BaseModel):
    name: str
    info: Optional[MFCInfo] = None
    calibrations: List[CalibrationType]
    device: Optional[Union[MFCAnalogDevice, MFCFlowBusDevice]] = pydantic.Field(
        discriminator='connection', default=None
    )

    def get_calibration(
        self, selector: CalibrationSelector = 'latest'
    ) -> CalibrationBase:
        if selector == 'latest':
            calibrations = sorted(self.calibrations, key=lambda c: c.date)
            return calibrations[-1]
        return self.calibrations[selector]

    def setpoint_to_flowrate(
        self,
        setpoint: str | float | pint.Quantity,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
        calibration: CalibrationSelector = 'latest',
    ):
        c = self.get_calibration(calibration)
        return c.setpoint_to_flowrate(setpoint, gas=gas, temperature=temperature)

    def flowrate_to_setpoint(
        self,
        flowrate: str | pint.Quantity,
        gas: None | MixtureType = None,
        temperature: None | str | pint.Quantity = None,
        calibration: CalibrationSelector = 'latest',
    ):
        c = self.get_calibration(calibration)
        return c.flowrate_to_setpoint(flowrate, gas=gas, temperature=temperature)

    # @pydantic.field_validator('gas', mode='before')
    # @classmethod
    # def check_composition(cls, value):
    #     return Mixture.create(value)
