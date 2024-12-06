from typing import Literal

import pydantic


class ServerConfig(BaseModel):
    ip: IPv4Address = IPv4Address('127.0.0.1')
    port: int = 50061
    timeout: Annotated[TimeQ, Field(validate_default=True)] = '5s'


class SerialPortConfig(BaseModel):
    port: str = 'COM1'
    baudRate: int = 19200


class MFCDriverBase(pydantic.BaseModel):
    name: str


class MKSPAC100ModbusDriver(MFCDriverBase):
    protocol: Literal['MKS-PAC100-Modbus'] = 'MKS-PAC100-Modbus'


class FlowBusDriver(MFCDriverBase):
    protocol: Literal['FlowBus'] = 'FlowBus'
