from functools import reduce
from typing import Callable, TypeVar

import pint

from ..config import unit_registry


def pipe(value, *functions):
    return reduce(lambda v, f: f(v), functions, value)


def validate_dimension(
    value: str | pint.Quantity,
    dimension: str,
    conversion: Callable = lambda x: unit_registry().Quantity(x),
) -> pint.Quantity:
    value = conversion(value)

    # check dimensions of value
    if not value.check(dimension):
        raise ValueError(f'Value must have dimensions of {dimension}, got: {value}')

    return value


Q = TypeVar('Q')


def validate_range(value: Q, min_value: Q = None, max_value: Q = None) -> Q:
    if min_value is not None and max_value is not None:
        if not (min_value <= value <= max_value):
            raise ValueError(
                f'Value must be between {min_value} and {max_value}, got: {value}'
            )
    elif min_value is not None:
        if value < min_value:
            raise ValueError(
                f'Value must be greater than or equal to {min_value}, got: {value}'
            )
    elif max_value is not None:
        if value > max_value:
            raise ValueError(
                f'Value must be less than or equal to {max_value}, got: {value}'
            )

    return value
