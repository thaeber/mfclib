from typing import List, Literal, Optional, Sequence, cast

import numpy as np
import numpy.typing as npt
import pandas as pd
import pydantic
import scipy

from mfclib.tools import first

from ..quantity_type import FlowRateQ, FractionQ, TemperatureQ
from .configuration import Config
from .mixture import Mixture

LineSelection = Literal['all', 'default'] | List[str]


class MixtureResultComponent(pydantic.BaseModel):
    gas: Mixture
    weight: float
    flowrate: FlowRateQ
    line: str
    mfc: Optional[str] = None
    setpoint: Optional[FractionQ] = None


class MixtureResult(pydantic.BaseModel, Sequence):
    success: bool
    mixture: Mixture
    components: List[MixtureResultComponent]

    def __getitem__(self, item):
        return self.components[item]

    def __len__(self):
        return len(self.components)

    def as_dataframe(self):
        data = []
        for component in self.components:
            data.append(
                {
                    'gas': component.gas.label,
                    'composition': component.gas.as_str(),
                    'weight': component.weight,
                    'flowrate': component.flowrate,
                    'line': component.line,
                    'mfc': component.mfc,
                    'setpoint': component.setpoint,
                }
            )
        return pd.DataFrame(data)


class MixtureGenerator(pydantic.BaseModel):
    config: Config
    lines: LineSelection = 'all'

    @pydantic.model_validator(mode='after')
    def validate_lines(self):
        if self.lines == 'all':
            pass
        elif self.lines == 'default':
            pass
        else:
            available_lines = set(line.name for line in self.config.lines)
            requested_lines = set(self.lines)
            if not (requested_lines <= available_lines):
                raise ValueError(
                    'Some lines are not available in the configuration: '
                    f'{requested_lines - available_lines}'
                )
        return self

    def generate(
        self,
        mixture: Mixture,
        flowrate: str | FlowRateQ,
        temperature: str | TemperatureQ,
    ):
        # validate input
        flowrate = FlowRateQ(flowrate)
        temperature = TemperatureQ(temperature)

        # calculate mixing ratios
        lines = self._get_lines()
        weights = self.calculate_mixing_ratios(mixture)

        # generate output
        components: List[MixtureResultComponent] = []
        for weight, line in zip(weights, lines):
            flowrate_line = flowrate * weight
            components.append(
                MixtureResultComponent(
                    gas=line.gas,
                    weight=weight,
                    flowrate=flowrate_line,
                    line=line.name,
                    mfc=line.mfc_name,
                    setpoint=self.config.flowrate_to_setpoint(
                        line, flowrate_line, temperature
                    ),
                )
            )

        return MixtureResult(
            success=True if np.isclose(1.0, np.sum(weights), 1e-3) else False,
            mixture=Mixture.compose([c.gas for c in components], weights),
            components=components,
        )

    def calculate_mixing_ratios(self, mixture: Mixture):
        sources = [line.gas for line in self._get_lines()]
        return self._calculate_mixing_ratios(sources, mixture)

    def _get_lines(self):
        if (self.lines == 'all') or (self.lines == 'default'):
            return self.config.lines
        else:
            return [
                first(lambda line: line.name == name, self.config.lines)
                for name in self.lines
            ]

    @classmethod
    def _calculate_mixing_ratios(
        cls, sources: Sequence[Mixture], mixture: Mixture
    ) -> npt.NDArray:
        if not sources:
            raise ValueError("No sources provided")

        # all species in the sources
        source_species = set()
        for source in sources:
            source_species.update(source.species)

        # all species in the mixture
        mixture_species = set(mixture.species)

        if undefined := mixture_species - source_species:
            raise ValueError(
                f'Species {undefined} are not present in any of the sources'
            )

        balance_with = mixture.get_balance_species()

        # Calculation of the mixing ratios using only the species with known
        # concentrations in the target mixture, i.e. without balance species
        # or species whose concentration is not specified.
        species = mixture_species.copy()
        if balance_with:
            species.discard(balance_with)
        x = cls._solve_nnls_system(sources, mixture, sorted(species))
        mixture = Mixture.compose(sources, x, balance_with=balance_with)

        # solving the system again, this time with the balance species and using
        # all species in the sources
        x = MixtureGenerator._solve_nnls_system(
            sources, mixture.balanced, sorted(source_species)
        )

        # set very small values to zero
        x[np.isclose(x, np.zeros_like(x))] = 0.0

        # return weights of individual sources
        return x

    @classmethod
    def _solve_nnls_system(
        cls,
        sources: Sequence[Mixture],
        mixture: Mixture,
        species: Sequence[str],
    ):
        if not sources:
            raise ValueError("No sources provided")

        # shape of linear system
        N, M = len(sources), len(species)

        # build matrix of source lines and species with known concentrations
        A = np.zeros((M, N))
        for m, key in enumerate(species):
            for n, source in enumerate(sources):
                A[m, n] = source.get(key, 0.0).m_as('')

        # build target composition vector, which contains the desired concentrations
        # in the final mixture
        b = np.zeros(M)
        for k, key in enumerate(species):
            b[k] = mixture.get(key, 0.0).m_as('')

        # solve system of linear equations
        x, _ = scipy.optimize.nnls(A, b)
        x = cast(np.ndarray, x)
        return x
