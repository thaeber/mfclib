from functools import reduce
from typing import Any, Callable, Iterable, TypeVar

import pint

from .config import unit_registry

_T = TypeVar('_T')
_S = TypeVar('_S')
_Q = TypeVar('_Q')


def is_none(value: Any):
    return value is None


def is_not_none(value: Any):
    return value is not None


def pipe(value, *functions):
    """
    Applies a series of functions to an initial value, passing the result of each function
    as the argument to the next function in the sequence.

    Args:
        value: The initial value to be passed through the pipeline of functions.
        *functions: A variable number of functions to be applied in sequence.

    Returns:
        The final result after all functions have been applied to the initial value.

    Example:
        result = pipe(5, lambda x: x + 2, lambda x: x * 3)
        # result is 21
    """
    return reduce(lambda v, f: f(v), functions, value)


map_to_list = lambda func, iterable: list(map(func, iterable))


def map_if(
    condition: Callable[[_T], bool], func: Callable[[_T], _T], iterable: Iterable[_T]
):
    """
    Maps a function to elements of an iterable that satisfy a given condition.

    Args:
        condition (Callable[[_T], bool]): A function that takes an element of the iterable and returns True if the element should be mapped.
        func (Callable[[_T], _T]): A function that takes an element of the iterable and returns the mapped value.
        iterable (Iterable[_T]): An iterable of elements to be checked and potentially mapped.

    Returns:
        Iterable[_T]: A generator that yields elements from the original iterable, with mappings where the condition is satisfied.
    """
    return (func(x) if condition(x) else x for x in iterable)


def first(condition: Callable[[_T], bool], iterable: Iterable[_T]):
    """
    Returns the first element in the iterable that satisfies the given condition.

    Args:
        condition (Callable[[_T], bool]): A function that takes an element of the iterable and returns True if the element satisfies the condition, otherwise False.
        iterable (Iterable[_T]): An iterable of elements to be filtered.

    Returns:
        _T: The first element in the iterable that satisfies the condition.

    Raises:
        StopIteration: If no element in the iterable satisfies the condition.
    """
    return next(filter(condition, iterable))


def first_or_default(
    condition: Callable[[_T], bool], iterable: Iterable[_T], default: _S
):
    """
    Returns the first element in the iterable that satisfies the condition.
    If no element satisfies the condition, returns the default value.

    Args:
        condition (Callable[[_T], bool]): A function that takes an element of the iterable and returns True if the element satisfies the condition, otherwise False.
        iterable (Iterable[_T]): An iterable of elements to be filtered.
        default (_T): The default value to return if no element satisfies the condition.

    Returns:
        _T: The first element that satisfies the condition, or the default value if no such element is found.
    """
    return next(filter(condition, iterable), default)


def replace(
    condition: Callable[[_T], bool], new_value: _T, iterable: Iterable[_T]
) -> Iterable[_T]:
    """
    Replace elements in an iterable that satisfy a given condition with a new value.

    Args:
        condition (Callable[[_T], bool]): A function that takes an element of the iterable and returns True if the element should be replaced.
        new_value (_T): The value to replace elements with if they satisfy the condition.
        iterable (Iterable[_T]): The iterable whose elements are to be checked and potentially replaced.

    Returns:
        Iterable[_T]: A generator that yields elements from the original iterable, with replacements where the condition is satisfied.
    """
    return (new_value if condition(x) else x for x in iterable)


def validate_dimension(
    value: str | pint.Quantity,
    dimension: str,
    conversion: Callable = lambda x: unit_registry().Quantity(x),
) -> pint.Quantity:
    """
    Validate that a given value has the specified dimension.

    Args:
        value (str | pint.Quantity): The value to be validated. It can be a string or a pint.Quantity.
        dimension (str): The expected dimension of the value.
        conversion (Callable, optional): A function to convert the value to a pint.Quantity.
                                        Defaults to a lambda function that uses unit_registry().Quantity.

    Returns:
        pint.Quantity: The validated value as a pint.Quantity.

    Raises:
        ValueError: If the value does not have the specified dimension.
    """
    value = conversion(value)

    # check dimensions of value
    if not value.check(dimension):
        raise ValueError(f'Value must have dimensions of {dimension}, got: {value}')

    return value


def validate_range(value: _Q, min_value: _Q = None, max_value: _Q = None) -> _Q:
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
