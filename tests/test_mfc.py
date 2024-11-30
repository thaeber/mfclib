import datetime

from pydantic import ValidationError
import pytest

import mfclib
from mfclib.mfc import CalibrationBase
from mfclib import LinearCalibration
from mfclib.mixture import Mixture


class TestCalibrationBase:
    def test_validate_setpoint(self):
        # always returns float
        assert isinstance(
            CalibrationBase.validate_setpoint('10%'),
            float,
        )
        assert isinstance(
            CalibrationBase.validate_setpoint(mfclib.unit_registry()('2%')),
            float,
        )

        assert CalibrationBase.validate_setpoint(0.5) == 0.5
        assert CalibrationBase.validate_setpoint('10%') == 0.1
        assert CalibrationBase.validate_setpoint(mfclib.unit_registry()('2%')) == 0.02

    def test_setpoint_out_of_range(self):
        with pytest.raises(ValueError):
            CalibrationBase.validate_setpoint('110%')

    def test_setpoint_with_invalid_dimension(self):
        with pytest.raises(ValueError):
            CalibrationBase.validate_setpoint('1 L/min')

    def test_validate_flowrate(self):
        ureg = mfclib.unit_registry()

        # always return pint Quantity
        assert isinstance(CalibrationBase.validate_flowrate('1 ml/s'), ureg.Quantity)
        assert isinstance(
            CalibrationBase.validate_flowrate(ureg.Quantity(3.2, 'm^3/h')),
            ureg.Quantity,
        )

        assert CalibrationBase.validate_flowrate('1 L/s') == ureg.Quantity(1.0, 'L/s')

    def test_validate_flowrate_fails_on_invalid_units(self):
        with pytest.raises(ValueError):
            CalibrationBase.validate_flowrate('1 m/s')

        with pytest.raises(ValueError):
            CalibrationBase.validate_flowrate(1.0)

    def test_validate_flowrate_fails_on_negative_values(self):
        with pytest.raises(ValueError):
            CalibrationBase.validate_flowrate('-1.0 L/s')


class TestLinearCalibration:
    def test_create_instance(self):
        ureg = mfclib.unit_registry()
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

    def test_create_instance_from_strings(self):
        ureg = mfclib.unit_registry()
        c = LinearCalibration(
            date='2024-06-20',  # type: ignore
            gas=dict(NH3='1%', He='*'),  # type: ignore
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

    def test_setpoint_to_flowrate(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        ureg = mfclib.unit_registry()
        assert c.setpoint_to_flowrate(0.0) == ureg('10ml/min')
