import datetime
from typing import (
    Literal,
)

import pint
import pydantic
import pydantic_core
from typing_extensions import Annotated


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
    pass
    # date: datetime.date
    # pressure: Quantity
    # temperature: Quantity
    # gas: Mixture
    # setpoint: List[Quantity]
    # flowrate: List[Quantity]
