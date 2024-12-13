import collections.abc
import textwrap
import warnings
from typing import (
    Any,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    SupportsFloat,
    TypeAlias,
    Union,
    cast,
)

import numpy as np
import pint
import pydantic
import scipy.optimize
from numpy.typing import NDArray

from ..quantity_type import FractionQ

from ..cf import calculate_CF
from ..config import balanceSpeciesIndicator, unit_registry

AmountType: TypeAlias = SupportsFloat | Literal['*']
MixtureMapping: TypeAlias = Mapping[str, AmountType]
MixtureType: TypeAlias = 'Mixture' | MixtureMapping


def ensure_mixture_type(mixture: MixtureType, *, strict=True, balance=True):
    if isinstance(mixture, Mixture):
        return mixture
    else:
        return Mixture(composition=mixture, strict=strict, balance=balance)


class Mixture(pydantic.BaseModel, collections.abc.Mapping):
    name: Optional[str] = None
    composition: Mapping[str, str | FractionQ]

    @staticmethod
    def create(mixture: MixtureType):
        if isinstance(mixture, Mixture):
            return mixture
        else:
            match mixture:
                case {'name': name, 'composition': composition}:
                    return Mixture(name=name, composition=composition)
                case {'composition': composition}:
                    return Mixture(composition=composition)
                case _:
                    return Mixture(composition=mixture)

    @pydantic.model_validator(mode='after')
    def check_name(self):
        if not self.name:
            self.name = "/".join(self.composition.keys())
        # ensure mixture can be balanced
        _ = self.get_balance_species()
        return self

    @pydantic.field_validator('composition', mode='before')
    @classmethod
    def check_composition(cls, value):
        return cls._convert_mixture(value)

    @pydantic.field_serializer('composition')  # , mode='wrap')
    def serialize_composition(
        self,
        composition,
        # nxt: pydantic.SerializerFunctionWrapHandler,
        _info,
    ):
        ureg = unit_registry()

        def func(value):
            if isinstance(value, ureg.Quantity):
                if value.units == ureg.Unit('dimensionless'):
                    return float(value)
                else:
                    return f'{value:~D}'
            else:
                return value

        converted = {key: func(value) for key, value in composition.items()}
        return converted

    @property
    def species(self):
        return list(self.composition.keys())

    @property
    def fractions(self):
        values = [
            cast(FractionQ, value) for value in self.balanced.composition.values()
        ]
        return values

    @property
    def mole_fractions(self):
        return [value.m_as('') for value in self.fractions]

    @property
    def cf(self):
        """Calculates the thermal MFC conversion factor for the mixture composition."""
        return calculate_CF(self)

    @classmethod
    def from_kws(cls, name: str | None = None, **components: AmountType):
        return Mixture(composition=components, name=name)

    def __getitem__(self, key):
        return self.composition[key]

    def __iter__(self):
        return iter(self.composition.keys())

    def __len__(self):
        return len(self.composition)

    def __repr__(self) -> str:
        comp = [f"{key}={value}" for key, value in self.composition.items()]
        sep = ", "
        return f"[{self.name}]({sep.join(comp)})"

    def equivalent_flow_rate(
        self,
        flow_rate: SupportsFloat,
        reference_mixture: Optional[MixtureType] = None,
    ):
        if reference_mixture is None:
            _ref = Mixture.from_kws(N2=1.0)
        else:
            _ref = ensure_mixture_type(_ref)
        return flow_rate * _ref.cf / self.cf

    @classmethod
    def _convert_value(
        cls,
        value: str | float | pint.Quantity,
    ):
        if isinstance(value, str) and (value == balanceSpeciesIndicator()):
            return value
        else:
            # convert to dimensionless quantity
            converted = FractionQ(value)
            return converted

    @classmethod
    def _convert_mixture(cls, feed: MixtureMapping):
        # convert feed values
        converted = {key: cls._convert_value(value) for key, value in feed.items()}
        return converted

    def get_balance_species(self):
        balance_indicator = balanceSpeciesIndicator()
        balance_species = [
            key for key, value in self.composition.items() if value == balance_indicator
        ]

        # ensure there is at most one species marked for balance
        match balance_species:
            case [symbol]:
                return symbol
            case []:
                return None
            case _:
                raise ValueError(
                    'Only one species may be labelled as a balance species, found '
                    f'{len(balance_species)} in mixture: {self.composition}'
                )

    @property
    def balanced(self):
        balance_with: str | None = None

        # copy mixture composition
        mixture = self.composition.copy()

        balance_with = self.get_balance_species()

        if balance_with:
            # get sum of mole fractions
            total = sum([float(v) for key, v in mixture.items() if key != balance_with])

            # add back balance species
            if balance_with:
                mixture[balance_with] = 1.0 - total

        return Mixture(name=self.name, composition=mixture)


class MixtureCollection(
    pydantic.BaseModel,
    collections.abc.Iterable,
    collections.abc.Sized,
):
    mixtures: List[Mixture] = pydantic.Field(default_factory=lambda: [])

    def __len__(self) -> int:
        return len(self.mixtures)

    def __iter__(self) -> Iterator[Mixture]:
        return iter(self.mixtures)

    def __getitem__(self, index):
        return self.mixtures[index]

    def __delitem__(self, index):
        del self.mixtures[index]

    @pydantic.validate_call
    def append(self, mixture: Mixture):
        self.mixtures.append(mixture)

    def clear(self):
        self.mixtures.clear()


def _strip_unit(value):
    try:
        # convert quantity to dimensionless
        return value.m_as('')
    except AttributeError:
        return value


def _solve_system(sources, mixture, species):
    # solve system of linear equations of species with known concentrations
    # build source matrix
    A = [[_strip_unit(source.get(key, 0.0)) for source in sources] for key in species]

    # build target composition vector
    b = [_strip_unit(mixture.get(key, 0.0)) for key in species]

    # solve system of linear equations
    x: NDArray[np.float64] = scipy.optimize.nnls(A, b)[0]
    return x


def supply_proportions_for_mixture(
    sources: Iterable[Union[Mixture, dict[str, SupportsFloat]]],
    mixture: Union[Mixture, dict[str, SupportsFloat]],
) -> NDArray[np.float64]:
    """Performs a non-negative linear least squares fit to determine the
    contribution of each gas supply to obtaining a given gas mixture.

    Args:
        `sources` (Iterable[Supply]): The compositions of the available
            supply gases.
        `mixture` (Mixture | Mapping[str, Any]): The composition of the
            final mixture solved for.

    Returns:
        NDArray[np.float64]: Array of relative flow rates of each supply required
            to obtain the desired mixture. The relative flow rates for the supplies
            are given in the same order as in the `sources` parameter.
            The sum of all relative flow rates is 1.
    """
    mixture = _convert_mixture(mixture)
    sources = [ensure_mixture_type(M) for M in sources]

    # get all available species in the source
    species = set()
    for source in sources:
        species |= set(source.species)
    species = sorted(species)

    mixture_species = [name for name in mixture]

    # warn if mixture contains species that are not supplied
    missing_species = set(mixture_species) - set(species)
    if missing_species:
        details = (
            f"\nThe following species are in the mixture "
            f"but not in any of the sources:\n{missing_species}"
        )
        warnings.warn("Missing species in supply." + details)

    balance_with = _get_balance_species(mixture)

    if balance_with:
        # exclude balance species and unspecified species
        unknown = []
        for name in species:
            if (name == balance_with) or (name not in mixture):
                unknown.append(name)

        # exclude balance species if present
        x = _solve_system(sources, mixture, [s for s in species if (s not in unknown)])

        # calculate resulting mixture and add balance species back
        _old = {key: mixture[key] for key in mixture}
        mixture = {name: 0.0 for name in species}
        for k, source in enumerate(sources):
            for name in source:
                mixture[name] += x[k] * _strip_unit(source[name])
        if balance_with:
            # here we add back the balance species using the
            # wildcard option for the amount, so that the final
            # amount is calculated by balancing the mixture
            mixture[balance_with] = balanceSpeciesIndicator()  # type: ignore

    mixture = _balance_mixture(mixture)
    x = _solve_system(sources, mixture, species)

    # set very small values to zero
    x[np.isclose(x, np.zeros_like(x))] = 0.0

    # check sum of proportions
    tolerance = 1.0e-4
    total = np.sum(x)
    if abs(total - 1.0) > tolerance:
        details = textwrap.dedent(
            f"""
            Inconsistent mixture composition: The sum of the mixture components
            (actual value: {total}) is not 1 within a tolerance of {tolerance}.
            Either the fit has not converged or the desired mixture cannot be
            achieved with the selected gas supplies.
            """
        )
        warnings.warn(details)

    # return relative flow rates for each supply
    return x
