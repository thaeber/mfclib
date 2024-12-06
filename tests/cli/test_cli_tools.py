import pytest
from mfclib.cli._cli_tools import mixture_string_to_mapping
import click


class TestMixtureStringToMapping:
    def test_valid_mixture_string_with_comma(self):
        value = 'N2=50%, O2=50ppm'
        expected = {'N2': '50%', 'O2': '50ppm'}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_valid_mixture_string_with_semicolon(self):
        value = 'N2=50%; O2=50ppm'
        expected = {'N2': '50%', 'O2': '50ppm'}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_valid_mixture_string_with_slash(self):
        value = 'N2=50% / O2=50ppm'
        expected = {'N2': '50%', 'O2': '50ppm'}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_valid_mixture_string_with_mixed_separators(self):
        value = 'N2=50% / O2=50ppm, NH3:1000 ppm'
        expected = {'N2': '50%', 'O2': '50ppm', 'NH3': '1000 ppm'}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_space_between_value_and_unit(self):
        value = 'N2=50 %, O2=50ppm'
        expected = {'N2': '50 %', 'O2': '50ppm'}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_invalid_mixture_string1(self):
        value = 'N2=50%, O2'
        with pytest.raises(click.BadParameter) as excinfo:
            mixture_string_to_mapping(value)
        assert 'Invalid key value pair: O2' in str(excinfo.value)

    def test_invalid_mixture_string2(self):
        value = 'N2=50%, O2, NH3=500 ppm'
        with pytest.raises(click.BadParameter) as excinfo:
            mixture_string_to_mapping(value)
        assert 'Invalid key value pair: O2' in str(excinfo.value)

    def test_invalid_mixture_string3(self):
        value = 'N2=50%, O2=, NH3=500 ppm'
        with pytest.raises(click.BadParameter) as excinfo:
            mixture_string_to_mapping(value)
        assert 'Invalid key value pair: O2' in str(excinfo.value)

    def test_empty_mixture_string(self):
        value = ''
        expected = {}
        result = mixture_string_to_mapping(value)
        assert result == expected

    def test_mixture_string_with_different_separators(self):
        value = 'N2=50%; O2=50%/ He=10%'
        expected = {'N2': '50%', 'O2': '50%', 'He': '10%'}
        result = mixture_string_to_mapping(value)
        assert result == expected
