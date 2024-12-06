from typing import Annotated, List, Literal, Optional, Union

import pint
import pydantic

from .calibration import CalibrationBase, LinearCalibration
from .._quantity import ElectricPotentialQ
from .mixture import MixtureType


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
