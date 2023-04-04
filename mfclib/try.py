#%%
import collections
from typing import Any, Iterable, Mapping
import pandas as pd
import xarray as xr
import numpy as np

from mfclib import Mixture, Supply

#%%
sources = [
    Supply('carrier', feed=dict(Ar=1.0)),
    Supply('100% O2', feed=dict(O2=1.0)),
    Supply('10% CO in Ar', feed=dict(CO=0.1492, Ar='*')),
    Supply('3000ppm NO in Ar', feed=dict(NO=0.002959, Ar='*')),
    Supply.from_components('100% H2', H2='*'),
    Supply.from_components('1% NO2 in Ar', NO2=0.01072, N2O=0.0, Ar='*'),
]
sources

# %%
import scipy.optimize


def flow_rates_for_mixture(sources: Iterable[Supply],
                           mixture: Mixture | Mapping[str, Any]):
    if not isinstance(mixture, Mixture):
        mixture = Mixture(mixture)

    # get set of all involved species
    _species = set(mixture.species)
    for mfc in sources:
        _species |= set(mfc.feed.species)
    species = sorted(_species)

    # build MFC matrix
    A = xr.DataArray(
        [[source.feed.get(key, 0.0) for source in sources] for key in species],
        dims=('species', 'supply'),
        coords=dict(species=species,
                    supply=[source.name for source in sources]),
    )

    # build target composition vector
    b = xr.DataArray(
        [mixture.get(key, 0.0) for key in species],
        dims=('species', ),
        coords=dict(species=species),
    )

    # solve system of linear equations
    x = xr.DataArray(
        scipy.optimize.nnls(A.data, b.data)[0],
        dims=('supply', ),
        coords=dict(supply=[source.name for source in sources]),
    )

    return x


rates = flow_rates_for_mixture(sources, dict(NO=400e-6, CO=400e-6, Ar='*'))
rates *= 10.0
rates.to_dataframe('Vdot')

# %%
