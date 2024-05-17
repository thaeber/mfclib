import pint
import pytest

from mfclib import Calibration, Mixture


class TestCalibration:
    def test_create_instance(self):
        calib = Calibration(
            dummy='mist',
            # pressure=1.0,
            # temperature=273.0,
            # gas=Mixture.from_kws(N2='*'),
            # setpoint=[],
            # flowrate=[],
        )
        assert isinstance(calib, Calibration)
