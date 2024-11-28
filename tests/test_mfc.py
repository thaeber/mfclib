import datetime

from pydantic import ValidationError
import pytest

from mfclib.mfc import CalibrationBase
from mfclib import LinearCalibration
from mfclib.mixture import Mixture


class TestCalibrationBase:
    def test_validate_setpoint(self):
        assert CalibrationBase.validate_setpoint(0.5) == 0.5


class TestLinearCalibration:
    def test_create_instance(self, unit_registry):
        ureg = unit_registry
        c = LinearCalibration(
            date=datetime.date(2024, 6, 20),
            gas=Mixture(composition=dict(NH3='1%', He='*')),
            temperature=273.0 * ureg.kelvin,
            offset=0.0 * ureg.liter / ureg.min,
            slope=500.0 * ureg.liter / ureg.min,
        )
        assert isinstance(c, LinearCalibration)
        assert c.date == datetime.date(2024, 6, 20)
        assert c.gas == Mixture(composition=dict(NH3='1%', He='*'))
        assert c.temperature == ureg('273.0 K')
        assert c.offset == ureg('0.0 L/min')
        assert c.slope == ureg('500.0 L/min')

    def test_create_instance_from_strings(self, unit_registry):
        ureg = unit_registry
        c = LinearCalibration(
            date='2024-06-20',  # type: ignore
            gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
            temperature='273 K',  # type: ignore
            offset='0L/min',  # type: ignore
            slope='500[L/min]',  # type: ignore
        )
        assert isinstance(c, LinearCalibration)
        assert c.date == datetime.date(2024, 6, 20)
        assert c.gas == Mixture(composition=dict(NH3='1%', He='*'))
        assert c.temperature == ureg('273.0 K')
        assert c.offset == ureg('0.0 L/min')
        assert c.slope == ureg('500.0 L/min')

    def test_create_invalid_temperature_units(self):
        with pytest.raises(ValidationError):
            LinearCalibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0L/min',  # type: ignore
                slope='500[L/min]',  # type: ignore
            )

    def test_create_invalid_offset_units(self):
        with pytest.raises(ValidationError):
            LinearCalibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0 min/L',  # type: ignore
                slope='500[L/min]',  # type: ignore
            )

    def test_create_invalid_slope_units(self):
        with pytest.raises(ValidationError):
            LinearCalibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0 min/L',  # type: ignore
                slope='500',  # type: ignore
            )
