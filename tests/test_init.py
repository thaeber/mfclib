import mfclib
import mfclib.version


def test_version_is_defined():
    assert mfclib.__version__ == mfclib.version.__version__
