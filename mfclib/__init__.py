import warnings

from . import config
from .cf import calculate_CF, get_CF_table
from .mixture import (
    Mixture,
    MixtureCollection,
    # Supply,
    supply_proportions_for_mixture,
    ensure_mixture_type,
)
from .mfc import Calibration

__version__ = "0.2.1"
