import collections.abc
import textwrap
import warnings
from typing import (
    Iterable,
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

from ..cf import calculate_CF
from ..config import balanceSpeciesIndicator, unit_registry
from ..quantity_type import FractionQ

AmountType: TypeAlias = SupportsFloat | Literal['*']
MixtureMapping: TypeAlias = Mapping[str, AmountType]
MixtureType: TypeAlias = 'Mixture' | MixtureMapping


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

    @pydantic.field_serializer('composition')
    def serialize_composition(
        self,
        composition,
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
        """
        Retrieve the fractions from the balanced composition.

        This method extracts the values from the balanced composition of the mixture
        and casts them to `FractionQ` type. It retains the original units used when
        creating the mixture.

        Returns:
            Dict[str, FractionQ]: A dictionary of fraction values from the balanced composition.
        """
        values = {
            key: cast(FractionQ, value)
            for key, value in self.balanced.composition.items()
        }
        return values

    @property
    def mole_fractions(self):
        """
        Calculate and return the mole fractions of the mixture.

        This method computes the mole fractions of each component in the mixture
        and returns them as dimensionless quantities (floats). Unlike the `fractions`
        property, which may include units, this method ensures the mole fractions are
        unitless.


        Returns:
            dict: A dictionary where the keys are the component names and the values
                  are the mole fractions (floats) of each component in the mixture.
        """
        return {key: float(value.m_as('')) for key, value in self.fractions.items()}

    @property
    def conversion_factor(self):
        """
        Calculate and return the conversion factor for the mixture.

        This method uses the `calculate_CF` function to determine the conversion factor
        based on the properties of the mixture instance.

        Returns:
            float: The conversion factor for the mixture.
        """
        return calculate_CF(self)

    @property
    def cf(self):
        """
        Returns the conversion factor for the mixture. Alias for `conversion_factor`.

        Returns:
            float: The conversion factor.
        """
        return self.conversion_factor

    @classmethod
    def from_kws(cls, name: str | None = None, **components: AmountType):
        return Mixture(composition=components, name=name)

    @property
    def balanced(self):
        # copy mixture composition
        mixture = self.composition.copy()

        balance_with = self.get_balance_species()

        if balance_with is None:
            return self.model_copy()
        else:
            composition = self.composition.copy()

            # get sum of mole fractions
            total = sum([float(v) for key, v in mixture.items() if key != balance_with])

            # add back balance species
            if balance_with:
                composition[balance_with] = 1.0 - total

            return Mixture(name=self.name, composition=composition)

    def __getitem__(self, key):
        return self.balanced.composition[key]

    def __iter__(self):
        return iter(self.composition.keys())

    def __len__(self):
        return len(self.composition)

    def __repr__(self) -> str:
        comp = [f"{key}={value}" for key, value in self.composition.items()]
        sep = ", "
        return f"[{self.name}]({sep.join(comp)})"


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
    mixture = Mixture.create(mixture)
    sources = [Mixture.create(M) for M in sources]

    # get all available species in the sources
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

    balance_with = mixture.get_balance_species()

    if balance_with:
        # exclude balance species and unspecified species
        unknown = []
        for name in species:
            if (name == balance_with) or (name not in mixture):
                unknown.append(name)

        # exclude balance species if present
        x = _solve_system(sources, mixture, [s for s in species if (s not in unknown)])

        # calculate resulting mixture composition and add balance species back
        composition = {name: 0.0 for name in species}
        for k, source in enumerate(sources):
            for name in source:
                composition[name] += x[k] * _strip_unit(source[name])
        if balance_with:
            # here we add back the balance species using the
            # wildcard option for the amount, so that the final
            # amount is calculated by balancing the mixture
            composition[balance_with] = balanceSpeciesIndicator()

        mixture = Mixture.create(composition)

    # mixture = _balance_mixture(mixture)
    x = _solve_system(sources, mixture.balanced, species)

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
