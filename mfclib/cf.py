from pathlib import Path
from typing import Mapping

import pandas as pd

_CF_TABLE: pd.DataFrame = None


def _load_default_CF_table():
    filename = Path(__file__).parent / 'data/conversion_factors.csv'
    table = pd.read_csv(filename)
    return table


def _ensure_CF_table():
    global _CF_TABLE
    if _CF_TABLE is None:
        _CF_TABLE = _load_default_CF_table()


def get_CF_table():
    """Return the currently installed table of conversion factors.

    Returns:
        DataFrame: A pandas `DataFrame` with at least the following columns:
            name (str): The name of the compound, e.g. Nitrogen
            symbol (str): The symbol/formula of the compound, e.g. N2
            density (float): The reference gas density at 273K & 1bar.
            CF (float): The conversion factor at the reference point (273K, 1bar)
    """
    _ensure_CF_table()
    return _CF_TABLE


def calculate_CF(mixture: Mapping[str, float],
                 table: pd.DataFrame | None = None):
    # prepare table
    if table is None:
        # load default table
        table = get_CF_table()
    _table = table.set_index('symbol').CF

    # sum of contents
    total = sum(mixture.values(), start=0.0)

    # calculate conversion factor
    cf = 0.0
    for symbol, fraction in mixture.items():
        cf += fraction / float(_table.loc[symbol])

    return total / cf
