import pytest

from mfclib._quantity import TemperatureQ
from mfclib.config import unit_registry
from mfclib.tools import pipe, validate_dimension, validate_range


class TestValidateDimension:
    def test_validate_dimension_with_valid_input(self):
        ureg = unit_registry()
        value = '10 meter'
        dimension = '[length]'
        result = validate_dimension(value, dimension)
        assert isinstance(result, ureg.Quantity)
        assert result.magnitude == 10
        assert result.units == ureg.meter

    def test_validate_dimension_with_invalid_dimension(self):
        with pytest.raises(ValueError):
            validate_dimension('10 meter', '[time]')

    def test_validate_dimension_with_pint_quantity(self):
        ureg = unit_registry()
        value = ureg.Quantity(10, 'meter')
        dimension = '[length]'
        result = validate_dimension(value, dimension)
        assert isinstance(result, ureg.Quantity)
        assert result.magnitude == 10
        assert result.units == ureg.meter

    def test_validate_dimension_with_invalid_pint_quantity(self):
        ureg = unit_registry()
        value = ureg.Quantity(10, 'second')
        dimension = '[length]'
        with pytest.raises(ValueError):
            validate_dimension(value, dimension)

    def test_validate_dimension_with_custom_conversion(self):
        ureg = unit_registry()

        def custom_conversion(value):
            return ureg.Quantity(value) * 2

        value = '5 meter'
        dimension = '[length]'
        result = validate_dimension(value, dimension, custom_conversion)
        assert isinstance(result, ureg.Quantity)
        assert result.magnitude == 10
        assert result.units == ureg.meter

    def test_validate_dimension_with_temperature_conversion(self):
        ureg = unit_registry()

        value = '5 degC'
        dimension = '[temperature]'
        result = validate_dimension(value, dimension, TemperatureQ)
        assert isinstance(result, ureg.Quantity)
        assert result.magnitude == 5
        assert result.units == ureg.degC


class TestValidateRange:
    def test_validate_range_within_bounds(self):
        assert validate_range(5, 1, 10) == 5

    def test_validate_range_below_min(self):
        with pytest.raises(ValueError):
            validate_range(0, 1, 10)

    def test_validate_range_above_max(self):
        with pytest.raises(ValueError):
            validate_range(11, 1, 10)

    def test_validate_range_no_min(self):
        assert validate_range(5, max_value=10) == 5

    def test_validate_range_no_max(self):
        assert validate_range(5, min_value=1) == 5

    def test_validate_range_no_bounds(self):
        assert validate_range(5) == 5

    def test_validate_range_with_pint_quantity_within_bounds(self):
        ureg = unit_registry()
        value = ureg.Quantity(5, 'meter')
        min_value = ureg.Quantity(1, 'meter')
        max_value = ureg.Quantity(10, 'meter')
        assert validate_range(value, min_value, max_value) == value

    def test_validate_range_with_pint_quantity_below_min(self):
        ureg = unit_registry()
        value = ureg.Quantity(0, 'meter')
        min_value = ureg.Quantity(1, 'meter')
        max_value = ureg.Quantity(10, 'meter')
        with pytest.raises(ValueError):
            validate_range(value, min_value, max_value)

    def test_validate_range_with_pint_quantity_above_max(self):
        ureg = unit_registry()
        value = ureg.Quantity(11, 'meter')
        min_value = ureg.Quantity(1, 'meter')
        max_value = ureg.Quantity(10, 'meter')
        with pytest.raises(ValueError):
            validate_range(value, min_value, max_value)

    def test_validate_range_with_pint_quantity_no_min(self):
        ureg = unit_registry()
        value = ureg.Quantity(5, 'meter')
        max_value = ureg.Quantity(10, 'meter')
        assert validate_range(value, max_value=max_value) == value

    def test_validate_range_with_pint_quantity_no_max(self):
        ureg = unit_registry()
        value = ureg.Quantity(5, 'meter')
        min_value = ureg.Quantity(1, 'meter')
        assert validate_range(value, min_value=min_value) == value


class TestPipe:
    def test_pipe_with_single_function(self):
        def add_one(x):
            return x + 1

        result = pipe(1, add_one)
        assert result == 2

    def test_pipe_with_multiple_functions(self):
        def add_one(x):
            return x + 1

        def multiply_by_two(x):
            return x * 2

        result = pipe(1, add_one, multiply_by_two)
        assert result == 4

    def test_pipe_with_no_functions(self):
        result = pipe(1)
        assert result == 1

    def test_pipe_with_different_data_types(self):
        def to_upper(s):
            return s.upper()

        def add_exclamation(s):
            return s + '!'

        result = pipe('hello', to_upper, add_exclamation)
        assert result == 'HELLO!'

    def test_pipe_with_lambda_functions(self):
        result = pipe(2, lambda x: x + 3, lambda x: x * 2)
        assert result == 10
