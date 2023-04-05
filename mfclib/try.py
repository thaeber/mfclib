#%%
import collections
from typing import Any, Iterable, Mapping
import pandas as pd
import xarray as xr
import numpy as np

import mfclib
from mfclib import Mixture, Supply

import pint

Q = pint.Quantity
mfclib.register_pint_fractions()

#%%
mfclib.supply.unify_mixture_value('1,54')

#%%
sources = [
    Supply('carrier', feed=dict(Ar=1.0)),
    Supply('100% O2', feed=dict(O2=1.0)),
    Supply('10% CO in Ar', feed=dict(CO=0.1492, Ar='*')),
    Supply('3000ppm NO in Ar', feed=dict(NO=0.002959, Ar='*')),
    Supply.from_components('100% H2', H2='*'),
    Supply.from_components('1% NO2 in Ar', NO2=0.01072, N2O=0.0, Ar='*'),
]

mfclib.supply_proportions_for_mixture(sources, dict(Ar='*', CH2O=0.1))

# %%
sources = [Supply.from_kws(O2=0.21, N2='*'), Supply.from_kws(NO=0.003, N2='*')]

mfclib.supply_proportions_for_mixture(
    sources,
    dict(CO=0.0004, N2='*'),
)

# %%
Supply.from_kws(CO=0.1492, Ar='*').equivalent_flow_rate(0.0272413)

# %%
