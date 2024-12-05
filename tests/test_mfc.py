import datetime

import pytest

import mfclib
from mfclib.mfc import CalibrationBase
from mfclib import LinearCalibration
from mfclib.mixture import Mixture


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

    def test_setpoint_to_flowrate(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        ureg = mfclib.unit_registry()
        assert c.setpoint_to_flowrate(0.0).m_as('ml/min') == pytest.approx(10.0)
        assert c.setpoint_to_flowrate(0.5).m_as('ml/min') == pytest.approx(760.0)
        assert c.setpoint_to_flowrate(1.0).m_as('ml/min') == pytest.approx(1510.0)

    def test_setpoint_to_flowrate_with_different_gas(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        gas = Mixture(composition=dict(CO2='*'))
        assert c.setpoint_to_flowrate(0.5, gas=gas).m_as('ml/min') == pytest.approx(
            760.0 * 0.740
        )

    def test_setpoint_to_flowrate_with_different_temperature(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='300K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        assert c.setpoint_to_flowrate(0.5, temperature='450K').m_as(
            'ml/min'
        ) == pytest.approx(1.5 * 760.0)

    def test_setpoint_to_flowrate_with_invalid_setpoint(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        with pytest.raises(ValueError):
            c.setpoint_to_flowrate('110%')

        with pytest.raises(ValueError):
            c.setpoint_to_flowrate('-10%')

    def test_setpoint_to_flowrate_with_invalid_temperature(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        with pytest.raises(ValueError):
            c.setpoint_to_flowrate(0.5, temperature='-1K')

        with pytest.raises(ValueError):
            c.setpoint_to_flowrate(0.5, temperature='100')

    def test_flowrate_to_setpoint(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        ureg = mfclib.unit_registry()
        assert c.flowrate_to_setpoint('10ml/min') == pytest.approx(0.0)
        assert c.flowrate_to_setpoint('760ml/min') == pytest.approx(0.5)
        assert c.flowrate_to_setpoint('1510ml/min') == pytest.approx(1.0)

    def test_flowrate_to_setpoint_with_different_gas(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        ureg = mfclib.unit_registry()
        gas = Mixture(composition=dict(CO2='*'))
        assert c.flowrate_to_setpoint(
            0.740 * 760 * ureg('ml/min'), gas=gas
        ) == pytest.approx(0.5)

    def test_flowrate_to_setpoint_with_different_temperature(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='300K',
            offset='0ml/min',
            slope='1.5L/min',
        )

        ureg = mfclib.unit_registry()
        assert c.flowrate_to_setpoint('1.5L/min', temperature='450K') == pytest.approx(
            2.0 / 3.0
        )

    def test_flowrate_to_setpoint_with_invalid_flowrate(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        with pytest.raises(ValueError):
            c.flowrate_to_setpoint('1 m/s')

        with pytest.raises(ValueError):
            c.flowrate_to_setpoint('-10ml/min')

    def test_flowrate_to_setpoint_with_invalid_temperature(self):
        c = LinearCalibration(
            date='2024-06-20',
            gas=dict(N2='*'),
            temperature='273K',
            offset='10ml/min',
            slope='1.5L/min',
        )

        with pytest.raises(ValueError):
            c.flowrate_to_setpoint('760ml/min', temperature='-1K')

        with pytest.raises(ValueError):
            c.flowrate_to_setpoint('760ml/min', temperature='100')


class TestMFC:
    def test_create_instance(self):
        mfc = mfclib.MFC(
            name='MFC-1',
            calibrations=[
                LinearCalibration(
                    date='2024-06-20',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                )
            ],
        )

        assert isinstance(mfc, mfclib.MFC)
        assert mfc.name == 'MFC-1'

    def test_create_instance_from_dict(self):
        mfc = mfclib.MFC.model_validate(
            dict(
                name='MFC-1',
                calibrations=[
                    dict(
                        date='2024-06-20',
                        gas=dict(N2='*'),
                        temperature='273K',
                        method='linear',
                        offset='10ml/min',
                        slope='1.5L/min',
                    )
                ],
            )
        )

    def test_dump_and_validate_roundtrip(self):
        mfc = mfclib.MFC(
            name='MFC-1',
            calibrations=[
                LinearCalibration(
                    date='2024-06-20',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                )
            ],
        )

        data = mfc.model_dump()
        mfc2 = mfclib.MFC.model_validate(data)
        assert mfc == mfc2

    def test_current_get_calibration_latest(self):
        mfc = mfclib.MFC(
            name='MFC-1',
            calibrations=[
                LinearCalibration(
                    date='2023-01-01',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
                LinearCalibration(
                    date='2024-06-20',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
            ],
        )

        assert mfc.get_calibration('latest').date == datetime.date(2024, 6, 20)

    def test_current_get_calibration_by_index(self):
        mfc = mfclib.MFC(
            name='MFC-1',
            calibrations=[
                LinearCalibration(
                    date='2023-01-01',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
                LinearCalibration(
                    date='2024-06-20',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
            ],
        )

        assert mfc.get_calibration(0).date == datetime.date(2023, 1, 1)

    def test_current_calibration_invalid_index(self):
        mfc = mfclib.MFC(
            name='MFC-1',
            calibrations=[
                LinearCalibration(
                    date='2023-01-01',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
                LinearCalibration(
                    date='2024-06-20',
                    gas=dict(N2='*'),
                    temperature='273K',
                    offset='10ml/min',
                    slope='1.5L/min',
                ),
            ],
        )

        with pytest.raises(IndexError):
            _ = mfc.get_calibration(2)
