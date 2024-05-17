from io import BytesIO
import token
import tokenize
from typing import Any, Generic, Type

from pint import Quantity, UndefinedUnitError
import pint
from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

import contextlib


class PydanticQuantity(Quantity):
    restrict_dimensionality = None

    def __new__(cls, value, units=None):
        # Re-used the instance we are passed.  Do we need to copy?
        return cls._validate(value, units=units)

    @staticmethod
    def parse_expression(input_string: str):
        tokens = tokenize.tokenize(
            BytesIO(input_string.encode("utf-8")).readline
        )
        t = next(tokens)
        if t.type != token.ENCODING:
            return None

        t = next(tokens)
        if t.type != token.NUMBER:
            return None
        number = t.string

        t = next(tokens)
        if t.type != token.NAME:
            return None
        unit = t.string

        t = next(tokens)
        if t.type != token.NEWLINE:
            return None

        t = next(tokens)
        if t.type != token.ENDMARKER:
            return None

        try:
            number = int(number)
        except ValueError:
            number = float(number)

        return number, unit

    @classmethod
    def _validate(cls, source_value, units=None):
        if source_value is None:
            raise ValueError
        try:
            if units is not None:
                value = Quantity(source_value, units=units)
            else:
                if isinstance(source_value, str):
                    # here we try to split the magnitude from the unit in case
                    # only a single unit is given, e.g. "20degC". This avoids
                    # an error with offset units where we cannot create a
                    # quantity via pint.Quantity("20.0degC"), but
                    # pint.Quantity(20.0, "degC") works
                    # (see https://github.com/hgrecco/pint/issues/386)
                    parsed = PydanticQuantity.parse_expression(source_value)
                    if parsed is not None:
                        source_value, units = parsed
                value = Quantity(source_value, units=units)
        except UndefinedUnitError as ex:
            raise ValueError(
                f'Cannot convert "{source_value}" to quantity'
            ) from ex
        if not isinstance(value, Quantity):
            raise TypeError(
                f'pint.Quantity required ({value}, type = {type(value)})'
            )
        if cls.restrict_dimensionality is not None:
            if not value.check(cls.restrict_dimensionality):
                raise ValueError(
                    f"The dimensionality of the passed value ('{source_value}') must be compatible with '{cls.restrict_dimensionality}'",
                )
        return value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Type[Any], handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        # assert source_type is Quantity
        # print(source_type, type(source_type))
        # assert issubclass(source_type, Quantity)
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize,
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )

    @staticmethod
    def _serialize(value: Quantity) -> str:
        return str(value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # Use the same schema that would be used for `int`
        return handler(core_schema.int_schema())


class TemperatureQ(PydanticQuantity):
    restrict_dimensionality = '[temperature]'


class PressureQ(PydanticQuantity):
    restrict_dimensionality = '[pressure]'
