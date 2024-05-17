import mfclib.cf
import mfclib
import pandas as pd


def test_ensure_CF_table():
    mfclib.cf._ensure_CF_table()
    assert mfclib.cf._CF_TABLE is not None


def test_get_CF_table():
    cf = mfclib.get_CF_table()
    assert isinstance(cf, pd.DataFrame)


def test_calculate_CF():
    mixture = dict(N2=0.9, CO=0.05, NO=0.05)
    mfclib.calculate_CF(mixture)
