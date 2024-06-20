import datetime
from typing import Literal

import pint
import pydantic
import pydantic_core
from typing_extensions import Annotated

from ._quantity import FlowRateQ, TemperatureQ
from .mixture import Mixture

FitType = Literal['linear', 'quadratic']
Quantity = Annotated[
    pint.Quantity,
    pydantic.GetPydanticSchema(
        lambda tp, handler: pydantic_core.core_schema.no_info_after_validator_function(
            lambda x: pint.Quantity(x), handler(tp)
        )
    ),
]


class Calibration(pydantic.BaseModel):
    date: datetime.date
    gas: Mixture
    temperature: TemperatureQ
    offset: FlowRateQ
    slope: FlowRateQ
