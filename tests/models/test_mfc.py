import datetime

import pytest
from omegaconf import OmegaConf

import mfclib
from mfclib.models import Mixture, LinearCalibration


class TestMFC:
    def test_create_instance(self):
        mfc = mfclib.models.MFC(
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

        assert isinstance(mfc, mfclib.models.MFC)
        assert mfc.name == 'MFC-1'

    def test_create_instance_from_dict(self):
        mfclib.models.MFC.model_validate(
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
        mfc = mfclib.models.MFC(
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
        mfc2 = mfclib.models.MFC.model_validate(data)
        assert mfc == mfc2

    def test_current_get_calibration_latest(self):
        mfc = mfclib.models.MFC(
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
        mfc = mfclib.models.MFC(
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
        mfc = mfclib.models.MFC(
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

    def test_load_mfc_config_from_yaml(self):
        yaml = """
            name: Device/MFC/Brooks01
            info:
              manufacturer: Brooks
              make: 5850E (Analog)
              serial_number: T63185/004
              specifications: "2 L/min Ar, 4 bar"
            calibrations:
              - date: 2024-06-20
                gas:
                    N2: "*"
                temperature: 20 degC
                method: linear
                offset: 0 ml/min
                slope: 2.0 L/min
            device:
              connection: Analog
              max_output_voltage: 5V
              max_input_voltage: 5V
        """
        config = OmegaConf.create(yaml)
        mfc = mfclib.models.MFC.model_validate(
            OmegaConf.to_container(config, resolve=True)
        )

        ureg = mfclib.unit_registry()
        assert mfc.name == 'Device/MFC/Brooks01'
        assert mfc.info.manufacturer == 'Brooks'
        assert mfc.info.make == '5850E (Analog)'
        assert mfc.info.serial_number == 'T63185/004'
        assert mfc.info.specifications == '2 L/min Ar, 4 bar'
        assert mfc.calibrations[0].date == datetime.date(2024, 6, 20)
        assert mfc.calibrations[0].gas == Mixture(composition=dict(N2='*'))
        assert mfc.calibrations[0].temperature == 293.15 * ureg.kelvin
        assert mfc.calibrations[0].offset == 0.0 * ureg.L / ureg.min
        assert mfc.calibrations[0].slope == 2.0 * ureg.L / ureg.min
        assert mfc.device.connection == 'Analog'
        assert mfc.device.max_output_voltage == 5.0 * ureg.volt
        assert mfc.device.max_input_voltage == 5.0 * ureg.volt
