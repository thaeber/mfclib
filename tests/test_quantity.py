from typing import Annotated

import pint
import pytest
from pydantic import BaseModel

from mfclib._quantity import (
    PressureQ,
    PydanticQuantity,
    TemperatureQ,
)


class TestQuantity:
    def test_create_instance(self):
        q = PydanticQuantity(1.0)
        assert q == pint.Quantity(1.0)

        q = PydanticQuantity(1.0, 'm')
        assert q == pint.Quantity(1.0, 'm')

        q = PydanticQuantity('1.0m')
        assert q == pint.Quantity(1.0, 'm')

    def test_pydantic_model(self):
        class Model(BaseModel):
            value: Annotated[str, PydanticQuantity]

        model = Model(value='1.0m')
        assert isinstance(model.value, pint.Quantity)
        assert model.value == pint.Quantity(1.0, 'm')

    def test_pydantic_json_dump(self):
        class Model(BaseModel):
            value: Annotated[str, PydanticQuantity]

        model = Model(value='1.0m')
        json = model.model_dump_json()
        model2 = Model.model_validate_json(json)
        assert model == model2


class TestTemperatureQ:
    def test_dimensionality(self):
        assert TemperatureQ.restrict_dimensionality == '[temperature]'

    def test_create(self):
        assert TemperatureQ(1.0, 'K') == pint.Quantity(1.0, 'K')
        assert TemperatureQ(1.0, 'degC') == pint.Quantity(1.0, 'degC')
        assert TemperatureQ('1.0K') == pint.Quantity(1.0, 'K')

        assert TemperatureQ('1.0degC') == pint.Quantity(1.0, 'degC')

    def test_wrong_dimension(self):
        with pytest.raises(ValueError):
            TemperatureQ(1.0)
        with pytest.raises(ValueError):
            TemperatureQ(1.0, 'm')
        with pytest.raises(ValueError):
            TemperatureQ('1.0m')
        with pytest.raises(ValueError):
            TemperatureQ('1.0')


class TestPressureQ:
    def test_dimensionality(self):
        assert PressureQ.restrict_dimensionality == '[pressure]'

    def test_create(self):
        assert PressureQ(1.0, 'Pa') == pint.Quantity(1.0, 'Pa')
        assert PressureQ(1.0, 'bar') == pint.Quantity(1.0, 'bar')
        assert PressureQ('1.0Pa') == pint.Quantity(1.0, 'Pa')
        assert PressureQ('1.0bar') == pint.Quantity(1.0, 'bar')

    def test_wrong_dimension(self):
        with pytest.raises(ValueError):
            PressureQ(1.0)
        with pytest.raises(ValueError):
            PressureQ(1.0, 'm')
        with pytest.raises(ValueError):
            PressureQ('1.0m')
        with pytest.raises(ValueError):
            PressureQ('1.0')
