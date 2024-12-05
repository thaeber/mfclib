import re
import tokenize
from typing import Any, Type

from pint import Quantity, UndefinedUnitError
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from .config import unit_registry


class PydanticQuantity(Quantity):
    restrict_dimensionality = None

    def __new__(cls, value, units=None):
        # Re-used the instance we are passed.  Do we need to copy?
        return cls._validate(value, units=units)

    @staticmethod
    def parse_expression(input_string: str):
        if m := re.match(
            rf'(?P<number>{tokenize.Number}){tokenize.Whitespace}(?P<unit>(\[(.*)\])|(.*))',
            input_string,
        ):
            number = m.group('number')
            try:
                number = int(number)
            except ValueError:
                number = float(number)

            unit = m.group('unit')
            # if unit and (unit[0] == '[') and (unit[-1] == ']'):
            if unit and unit[0].startswith('[') and unit.endswith(']'):
                unit = unit[1:-1]

            return number, unit

        else:
            return None

    @classmethod
    def _validate(cls, source_value, units=None):
        ureg = unit_registry()
        if source_value is None:
            raise ValueError
        try:
            if units is not None:
                value = ureg.Quantity(source_value, units=units)
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
                value = ureg.Quantity(source_value, units=units)
        except UndefinedUnitError as ex:
            raise ValueError(f'Cannot convert "{source_value}" to quantity') from ex
        if not isinstance(value, ureg.Quantity):
            raise TypeError(f'pint.Quantity required ({value}, type = {type(value)})')
        if cls.restrict_dimensionality is not None:
            if not value.check(cls.restrict_dimensionality):
                raise ValueError(
                    f"The dimensionality of the passed value ('{source_value}') must "
                    f"be compatible with '{cls.restrict_dimensionality}'"
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


class FlowRateQ(PydanticQuantity):
    restrict_dimensionality = '[volume]/[time]'


class VoltageQ(PydanticQuantity):
    restrict_dimensionality = '[voltage]'
