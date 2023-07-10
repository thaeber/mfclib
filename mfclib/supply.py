import collections
import warnings
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, TypeVar

import numpy as np
import scipy.optimize
from attrs import field, frozen
from numpy.typing import NDArray
import pint
from .cf import calculate_CF
from . import _pint

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")


def valmap(func: Callable[[V], T], mappable: Mapping[K, V]) -> dict[K, T]:
    return {key: func(value) for key, value in mappable.items()}


def valfilter(predicate: Callable[[V], T], mappable: Mapping[K, V]) -> dict[K, V]:
    return {key: value for key, value in mappable.items() if predicate(value)}


def convert_mixture_value(value: Any):
    if ureg := _pint._unit_registry:
        converted = ureg.Quantity(value)
        # check that value is dimensionless
        if not converted.check("[]"):
            raise ValueError(
                f"`{converted:~P}` is not dimensionless, but has dimensions of `{converted.units:P}`"
            )
    else:
        converted = float(value)
    return converted


def convert_mixture(feed: Mapping[str, Any], balance=True):
    balance_indicator = "*"
    balance_with: str | None = None
    _feed = valmap(lambda x: x, feed)
    if balance:
        # ensure there is at most one species marked for balance
        balance_species = [
            key for key, value in _feed.items() if value == balance_indicator
        ]
        match balance_species:
            case [symbol]:
                balance_with = symbol
                del _feed[symbol]
            case []:
                pass
            case _:
                raise ValueError("Only one species may be marked as balance species.")

    # convert feed values
    converted = valmap(convert_mixture_value, _feed)

    # add balance species
    if balance_with:
        total = sum(converted.values(), start=0.0)
        if total > 1.0:
            raise ValueError(f"Sum of feed mole fractions is greater than one: {feed}")
        converted[balance_with] = 1.0 - total

    return converted


class Mixture(collections.abc.Mapping):
    def __init__(self, composition: Mapping[str, Any]):
        self._composition = convert_mixture(composition)

    @classmethod
    def from_kws(cls, **components: Any):
        return Mixture(components)

    @classmethod
    def from_dict(cls, components: Mapping[str, Any]):
        return Mixture(components)

    @property
    def species(self):
        return list(self._composition.keys())

    @property
    def mole_fractions(self):
        return list(self._composition.values())

    @property
    def cf(self):
        """Calculates the thermal MFC conversion factor for the mixture composition."""
        return calculate_CF(self)

    def __getitem__(self, key):
        return self._composition[key]

    def __iter__(self):
        return iter(self._composition.keys())

    def __len__(self):
        return len(self._composition)

    def __repr__(self) -> str:
        comp = [f"{key}={value}" for key, value in self._composition.items()]
        sep = ", "
        return f"Mixture({sep.join(comp)})"

    def get(self, key: str, default: float = 0.0):  # type: ignore
        if key in self._composition:
            return self._composition[key]
        else:
            return convert_mixture_value(default)


class MutableMixture(Mixture, MutableMapping):
    def __setitem__(self, key, value):
        self._composition[key] = convert_mixture_value(value)
        return self._composition[key]

    def __delitem__(self, key):
        del self._composition[key]

    def setdefault(self, key: str, default: float = 0.0):  # type: ignore
        if key in self:
            return self[key]
        else:
            self[key] = convert_mixture_value(default)
            return self[key]


@frozen
class Supply:
    name: str = field()
    feed: Mixture = field(factory=Mixture.from_kws, converter=Mixture)

    @name.validator
    def _validate_name(self, attribute, value: str):
        if not isinstance(value, str):
            raise TypeError("`name` must be of type `str`.")
        elif value == "":
            raise ValueError("`name` cannot be empty.")

    @feed.validator
    def _validate_feed_composition(self, attribute, value: Mixture):
        total = sum(value.values(), start=0.0)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"""The mole fractions in the feed composition do not add up to one:
                total = {total} for feed = {value}
                """
            )

    # @classmethod
    # def from_components(cls, name: str, **feed: Any):
    #     return Supply(name, feed=feed)

    # @classmethod
    # def from_dict(cls, name: str, components: Mapping[str, Any]):
    #     return Supply(name, components)

    @classmethod
    def from_kws(cls, name: str | None = None, **feed: Any):
        if (name is None) and len(feed) > 0:
            name = "|".join(feed.keys())
        return Supply(name, feed)  # type: ignore

    @property
    def species(self):
        return list(self.feed.keys())

    @property
    def mole_fractions(self):
        return list(self.feed.values())

    def equivalent_flow_rate(
        self, flow_rate, reference_mixture: Mapping[str, Any] | None = None
    ):
        if reference_mixture is None:
            _ref = Mixture.from_kws(N2=1.0)
        elif not isinstance(reference_mixture, Mixture):
            _ref = Mixture(reference_mixture)
        else:
            _ref = reference_mixture
        return flow_rate * _ref.cf / self.feed.cf


def supply_proportions_for_mixture(
    sources: Iterable[Supply], mixture: Mixture | Mapping[str, Any]
) -> NDArray[np.float64]:
    """Performs a non-negative linear least squares fit to determine the
    contribution of each gas supply to obtaining a given gas mixture.

    Args:
        `sources` (Iterable[Supply]): The compositions of the available supply gases.
        `mixture` (Mixture | Mapping[str, Any]): The composition of the final mixture solved for.

    Returns:
        NDArray[np.float64]: Array of relative flow rates of each supply required
            to obtain the desired mixture. The relative flow rates for the supplies
            are given in the same order as in the `sources` parameter.
            The sum of all relative flow rates is 1.
    """
    if not isinstance(mixture, Mixture):
        mixture = Mixture(mixture)

    # check species
    mixture_species = set(mixture.species)
    species_in_supply = set()
    for source in sources:
        species_in_supply |= set(source.feed.species)
    species = sorted(mixture_species | species_in_supply)

    # warn if mixture contains species that are not supplied
    missing_species = mixture_species - species_in_supply
    if missing_species:
        details = f"\nThe following species are in the mixture but not in any of the sources:\n{missing_species}"
        warnings.warn("Missing species in supply." + details)

    # build MFC matrix
    A = [[source.feed.get(key, 0.0) for source in sources] for key in species]

    # build target composition vector
    b = [mixture.get(key, 0.0) for key in species]

    # solve system of linear equations
    x: NDArray[np.float64] = scipy.optimize.nnls(A, b)[0]

    # check sum of proportions
    tolerance = 1.0e-4
    total = np.sum(x)
    if abs(total - 1.0) > tolerance:
        details = f"\nThe sum of supply proportions (actual value: {total}) is not 1 to within a tolerance of {tolerance}."
        details += " Either the fit did not converge or the desired mixture cannot be obtained using the chosen gas supplies."
        details += f"\nObtained proportions:"
        for source, value in zip(sources, x):
            details += f"\n{source.name} = {value}"
        warnings.warn("Inconsistent mixture composition." + details)

    # return relative flow rates for each supply
    return x
