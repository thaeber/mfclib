import collections
from typing import Any, Callable, Dict, Mapping, TypeVar

from attrs import Factory, field, frozen

from .cf import calculate_CF

K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")


def valmap(func: Callable[[V], T], mappable: Mapping[K, V]):
    return {key: func(value) for key, value in mappable.items()}


def valfilter(predicate: Callable[[V], T], mappable: Mapping[K, V]):
    return {key: value for key, value in mappable.items() if predicate(value)}


def unify_mixture_value(value: Any):
    return float(value)


def unify_mixture(feed: Mapping[str, Any], balance=True):
    balance_indicator = '*'
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
                raise ValueError(
                    'Only one species may be marked as balance species.')

    # convert feed values
    converted = valmap(unify_mixture_value, _feed)

    # add balance species
    if balance_species:
        total = sum(converted.values(), start=0.0)
        if total > 1.0:
            raise ValueError(f'Sum of feed mole fractions is greater than one: {feed}')
        converted[balance_with] = 1.0 - total

    return converted


class Mixture(collections.abc.Mapping):

    def __init__(self, composition: Mapping[str, float]):
        self._composition = unify_mixture(composition)

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

    def __getitem__(self, key):
        return self._composition[key]

    def __iter__(self):
        return iter(self._composition.keys())

    def __len__(self):
        return len(self._composition)

    def __repr__(self) -> str:
        comp = [f'{key}={value}' for key, value in self._composition.items()]
        sep = ', '
        return f'Mixture({sep.join(comp)})'


@frozen
class Supply:
    name: str = field()
    feed: Mixture = field(factory=Mixture.from_kws, converter=Mixture)

    @name.validator
    def _validate_name(self, attribute, value: str):
        if not isinstance(value, str):
            raise TypeError('`name` must be of type `str`.')
        elif value == '':
            raise ValueError('`name` cannot be empty.')

    @feed.validator
    def _validate_feed_composition(self, attribute, value: Mixture):
        total = sum(value.values(), start=0.0)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"""The mole fractions in the feed composition do not add up to one:
                total = {total} for feed = {value}
                """)

    @classmethod
    def from_components(cls, name: str, **feed: Any):
        return Supply(name, feed=feed)
    
    @classmethod
    def from_dict(cls, name: str, components: Mapping[str, Any]):
        return Supply(name, components)
        
    @property
    def cf(self):
        """Calculates the conversion factor for the feed composition of the MFC.
        """
        return calculate_CF(self.feed)
    
    @property
    def species(self):
        return list(self.feed.keys())
    
    @property
    def mole_fractions(self):
        return list(self.feed.values())
    
