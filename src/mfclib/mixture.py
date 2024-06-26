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
)

import numpy as np
import pint
import pydantic
import scipy.optimize
from numpy.typing import NDArray

from .cf import calculate_CF
from .config import balanceSpeciesIndicator, unitRegistry

AmountType: TypeAlias = SupportsFloat | Literal['*']
MixtureMapping: TypeAlias = Mapping[str, AmountType]
MixtureType: TypeAlias = 'Mixture' | MixtureMapping


def _convert_value(
    value: SupportsFloat,
):
    if value == balanceSpeciesIndicator():
        return value
    if ureg := unitRegistry():
        converted = ureg.Quantity(value)
        # check that value is dimensionless
        if not converted.check("[]"):
            raise ValueError(
                f"`{converted:~P}` is not dimensionless, but has "
                f"dimensions of `{converted.units:P}`"
            )
        return converted
    else:
        return float(value)


def _get_balance_species(feed: MixtureMapping):
    balance_indicator = balanceSpeciesIndicator()
    balance_species = [key for key, value in feed.items() if value == balance_indicator]

    # ensure there is at most one species marked for balance
    match balance_species:
        case [symbol]:
            return symbol
        case []:
            return None
        case _:
            message = 'Only one species may be marked as balance species.'
            detail = f'{feed}'
            raise ValueError('\n'.join([message, detail]))


def _convert_mixture(feed: MixtureMapping):
    # convert feed values
    converted = {key: _convert_value(value) for key, value in feed.items()}
    return converted


def _balance_mixture(feed: MixtureMapping):
    balance_with: str | None = None

    # convert feed values
    converted = _convert_mixture(feed)

    balance_with = _get_balance_species(feed)

    if balance_with:
        # get sum of mole fractions
        total = np.sum(
            [float(v) for key, v in converted.items() if key != balance_with]
        )

        # add back balance species
        if balance_with:
            converted[balance_with] = 1.0 - _convert_value(total)  # type: ignore

    return converted


def ensure_mixture_type(mixture: MixtureType, *, strict=True, balance=True):
    if isinstance(mixture, Mixture):
        return mixture
    else:
        return Mixture(composition=mixture, strict=strict, balance=balance)


class Mixture(pydantic.BaseModel, collections.abc.Mapping):
    name: Optional[str] = None
    composition: dict[str, Any]
    strict: bool = True
    balance: bool = True

    @pydantic.model_validator(mode='after')
    def check_name(self):
        if not self.name:
            self.name = "/".join(self.composition.keys())
        try:
            if self.balance:
                self.composition = _balance_mixture(self.composition)
        except ValueError as ex:
            if self.strict:
                raise ex
        return self

    @pydantic.field_validator('composition', mode='before')
    @classmethod
    def check_composition(cls, value):
        return _convert_mixture(value)

    @pydantic.field_serializer('composition', mode='wrap')
    def serialize_composition(
        self,
        composition,
        nxt: pydantic.SerializerFunctionWrapHandler,
        _info,
    ):
        def func(value):
            if isinstance(value, pint.Quantity):
                if value.units == unitRegistry().Unit(''):
                    return float(value)
                else:
                    return f'{value:~D}'
            else:
                return value

        converted = {key: func(value) for key, value in composition.items()}
        return nxt(converted)

    @property
    def species(self):
        return list(self.composition.keys())

    @property
    def mole_fractions(self):
        return list(self.composition.values())

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

    def get(self, key: str, default: float = 0.0):  # type: ignore
        if key in self.composition:
            return self.composition[key]
        else:
            return _convert_value(default)

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
        return value.to('frac').magnitude
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
            Inconsistent mixture composition:
            The sum of supply proportions (actual value: {total}) is not 1
            to within a tolerance of {tolerance}. Either the fit did not converge
            or the desired mixture cannot be obtained using the chosen gas
            supplies. Obtained proportions:
            """
        )
        for source, value in zip(sources, x):
            details += f"\n{source.name} = {value}"
        warnings.warn(details)

    # return relative flow rates for each supply
    return x
