import datetime

from pydantic import ValidationError
import pytest

import mfclib
from mfclib import Calibration
from mfclib.mixture import Mixture


class TestCalibration:
    def test_create_instance(self):
        ureg = mfclib.unit_registry()
        c = Calibration(
            date=datetime.date(2024, 6, 20),
            gas=Mixture(composition=dict(NH3='1%', He='*')),
            temperature=273.0 * ureg.kelvin,
            offset=0.0 * ureg.liter / ureg.min,
            slope=500.0 * ureg.liter / ureg.min,
        )
        assert isinstance(c, Calibration)
        assert c.date == datetime.date(2024, 6, 20)
        assert c.gas == Mixture(composition=dict(NH3='1%', He='*'))
        assert c.temperature == ureg('273.0 K')
        assert c.offset == ureg('0.0 L/min')
        assert c.slope == ureg('500.0 L/min')

    def test_create_instance_from_strings(self):
        ureg = mfclib.unit_registry()
        c = Calibration(
            date='2024-06-20',  # type: ignore
            gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
            temperature='273 K',  # type: ignore
            offset='0L/min',  # type: ignore
            slope='500[L/min]',  # type: ignore
        )
        assert isinstance(c, Calibration)
        assert c.date == datetime.date(2024, 6, 20)
        assert c.gas == Mixture(composition=dict(NH3='1%', He='*'))
        assert c.temperature == ureg('273.0 K')
        assert c.offset == ureg('0.0 L/min')
        assert c.slope == ureg('500.0 L/min')

    def test_create_invalid_temperature_units(self):
        with pytest.raises(ValidationError):
            Calibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0L/min',  # type: ignore
                slope='500[L/min]',  # type: ignore
            )

    def test_create_invalid_offset_units(self):
        with pytest.raises(ValidationError):
            Calibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0 min/L',  # type: ignore
                slope='500[L/min]',  # type: ignore
            )

    def test_create_invalid_slope_units(self):
        with pytest.raises(ValidationError):
            Calibration(
                date='2024-06-20',  # type: ignore
                gas=dict(composition=dict(NH3='1%', He='*')),  # type: ignore
                temperature='273 m',  # type: ignore
                offset='0 min/L',  # type: ignore
                slope='500',  # type: ignore
            )
