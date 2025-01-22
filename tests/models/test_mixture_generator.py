import numpy as np
import pytest
from pydantic import ValidationError
from mfclib.models.line import MFCLine
from mfclib.models.mixture_generator import MixtureGenerator
from mfclib.models.configuration import Config
from mfclib.models.mixture import Mixture
from mfclib import unit_registry


class TestMixtureGenerator:
    class TestValidateLines:
        def test_valid_all_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            assert mg.lines == 'all'

        def test_valid_specific_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=['line1'])
            assert mg.lines == ['line1']

        def test_invalid_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            with pytest.raises(ValidationError) as excinfo:
                MixtureGenerator(config=config, lines=['line3'])
            assert 'Some lines are not available in the configuration' in str(
                excinfo.value
            )

        def test_empty_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=[])
            assert mg.lines == []

        def test_no_lines_in_config(self):
            config = Config(lines=[])
            with pytest.raises(ValidationError) as excinfo:
                MixtureGenerator(config=config, lines=['line1'])
            assert 'Some lines are not available in the configuration' in str(
                excinfo.value
            )

    class TestSolveNnlsSystem:
        def test_unused_feed(self):
            sources = [
                Mixture.create(N2='80%', O2='20%'),
                Mixture.create(N2='90%', O2='10%'),
                Mixture.create(He='*'),
            ]
            target_mixture = Mixture.create(N2='85%', O2='15%')
            species = ['N2', 'O2']

            result = MixtureGenerator._solve_nnls_system(
                sources, target_mixture, species
            )

            assert list(result) == pytest.approx([0.5, 0.5, 0.0])
            assert np.allclose(result, [0.5, 0.5, 0.0], atol=1e-2)

        def test_specify_all_species(self):
            sources = [
                Mixture.create(O2='*'),
                Mixture.create(N2='*'),
                Mixture.create(N2='*', NH3='1%'),
            ]
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')
            species = ['N2', 'O2', 'NH3']

            result = MixtureGenerator._solve_nnls_system(
                sources, target_mixture, species
            )

            assert list(result) == pytest.approx([0.1, 0.8, 0.1])

        def test_specify_only_relevant_species(self):
            sources = [
                Mixture.create(O2='*'),
                Mixture.create(N2='*'),
                Mixture.create(He='*', NH3='1%'),
            ]
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')
            species = ['O2', 'NH3']

            result = MixtureGenerator._solve_nnls_system(
                sources, target_mixture, species
            )

            assert list(result) == pytest.approx([0.1, 0.0, 0.1])

        def test_no_sources(self):
            sources = []
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')
            species = ['O2', 'NH3']

            with pytest.raises(ValueError) as ex:
                MixtureGenerator._solve_nnls_system(sources, target_mixture, species)
            assert 'No sources provided' in str(ex.value)

    class TestGetLines:
        def test_get_all_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            sources = mg._get_lines()
            assert len(sources) == 2
            assert sources[0].name == 'line1'
            assert sources[1].name == 'line2'

        def test_get_specific_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=['line1'])
            sources = mg._get_lines()
            assert len(sources) == 1
            assert sources[0].name == 'line1'

        def test_retain_order_of_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=['line2', 'line1'])
            sources = mg._get_lines()
            assert len(sources) == 2
            assert sources[0].name == 'line2'
            assert sources[1].name == 'line1'

        def test_get_no_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(NO='400ppm', N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=[])
            sources = mg._get_lines()
            assert len(sources) == 0

    class TestCalculateMixingRatios:
        def test_valid_mixing_ratios(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='80%', O2='20%')},
                    {'name': 'line2', 'gas': dict(N2='90%', O2='10%')},
                    {'name': 'line3', 'gas': dict(He='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(N2='85%', O2='15%')

            result = mg.calculate_mixing_ratios(target_mixture)

            assert list(result) == pytest.approx([0.5, 0.5, 0.0])

        def test_mixing_ratios_with_balance_species(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(O2='*')},
                    {'name': 'line2', 'gas': dict(N2='*')},
                    {'name': 'line3', 'gas': dict(N2='*', NH3='1%')},
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')

            result = mg.calculate_mixing_ratios(target_mixture)

            assert list(result) == pytest.approx([0.1, 0.8, 0.1])

        def test_mixing_ratios_with_missing_species(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(O2='*')},
                    {'name': 'line2', 'gas': dict(N2='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')

            with pytest.raises(ValueError) as ex:
                mg.calculate_mixing_ratios(target_mixture)
            assert 'Species {\'NH3\'} are not present in any of the sources' in str(
                ex.value
            )

        def test_mixing_ratios_with_specific_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(O2='*')},
                    {'name': 'line3', 'gas': dict(He='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=['line1', 'line2'])
            target_mixture = Mixture.create(N2='79%', O2='21%')

            result = mg.calculate_mixing_ratios(target_mixture)

            assert list(result) == pytest.approx([0.79, 0.21])

        def test_retain_order_of_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='*')},
                    {'name': 'line2', 'gas': dict(O2='*')},
                    {'name': 'line3', 'gas': dict(He='*')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=['line2', 'line1'])
            target_mixture = Mixture.create(N2='79%', O2='21%')

            result = mg.calculate_mixing_ratios(target_mixture)

            assert list(result) == pytest.approx([0.21, 0.79])

        def test_mixing_ratios_with_no_lines(self):
            config = Config(
                lines=[
                    {'name': 'line1', 'gas': dict(N2='80%', O2='20%')},
                    {'name': 'line2', 'gas': dict(N2='90%', O2='10%')},
                ]
            )
            mg = MixtureGenerator(config=config, lines=[])

            target_mixture = Mixture.create(N2='85%', O2='15%')

            with pytest.raises(ValueError) as ex:
                mg.calculate_mixing_ratios(target_mixture)
            assert 'No sources provided' in str(ex.value)

    class TestGenerate:
        def test_valid_mixing_ratios(self):
            config = Config(
                lines=[
                    MFCLine(name='line1', gas=Mixture.create(N2='*')),
                    MFCLine(name='line2', gas=Mixture.create(O2='*')),
                    MFCLine(name='line3', gas=Mixture.create(He='*')),
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(N2='79%', O2='21%')

            result = mg.generate(target_mixture, '2 L/min', '25°C')

            assert result.success is True
            result.mixture.assert_equal_composition(
                Mixture.create(N2='79%', O2='21%', He=0.0)
            )
            assert len(result) == 3

            # line 1
            assert result[0].gas == Mixture.create(N2='*')
            assert result[0].weight == pytest.approx(0.79)
            assert result[0].flowrate.m_as('L/min') == pytest.approx(1.58)
            assert result[0].line == 'line1'
            assert result[0].mfc is None
            assert result[0].setpoint is None

            # line 2
            assert result[1].gas == Mixture.create(O2='*')
            assert result[1].weight == pytest.approx(0.21)
            assert result[1].flowrate.m_as('L/min') == pytest.approx(0.42)
            assert result[1].line == 'line2'
            assert result[1].mfc is None
            assert result[1].setpoint is None

            # line 3
            assert result[2].gas == Mixture.create(He='*')
            assert result[2].weight == pytest.approx(0.0)
            assert result[2].flowrate.m_as('L/min') == pytest.approx(0.0)
            assert result[2].line == 'line3'
            assert result[2].mfc is None
            assert result[2].setpoint is None

        def test_with_balance_species(self):
            config = Config(
                lines=[
                    MFCLine(name='line1', gas=Mixture.create(N2='*')),
                    MFCLine(name='line2', gas=Mixture.create(O2='*')),
                    MFCLine(name='line3', gas=Mixture.create(He='*')),
                    MFCLine(name='line4', gas=Mixture.create(NH3='1%', He='*')),
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(NH3='1000ppm', O2='10%', N2='*')

            ureg = unit_registry()
            result = mg.generate(target_mixture, 2.0 * ureg.L / ureg.min, '25°C')

            assert result.success is True
            result.mixture.assert_equal_composition(
                Mixture.create(NH3='1000ppm', O2='10%', N2=0.8, He='9.9%')
            )
            assert len(result) == 4

            # line 1
            assert result[0].gas == Mixture.create(N2='*')
            assert result[0].weight == pytest.approx(0.8)
            assert result[0].flowrate.m_as('L/min') == pytest.approx(1.6)
            assert result[0].line == 'line1'
            assert result[0].mfc is None
            assert result[0].setpoint is None

            # line 2
            assert result[1].gas == Mixture.create(O2='*')
            assert result[1].weight == pytest.approx(0.1)
            assert result[1].flowrate.m_as('L/min') == pytest.approx(0.2)
            assert result[1].line == 'line2'
            assert result[1].mfc is None
            assert result[1].setpoint is None

            # line 3
            assert result[2].gas == Mixture.create(He='*')
            assert result[2].weight == pytest.approx(0.0)
            assert result[2].flowrate.m_as('L/min') == pytest.approx(0.0)
            assert result[2].line == 'line3'
            assert result[2].mfc is None
            assert result[2].setpoint is None

            # line 4
            assert result[3].gas == Mixture.create(NH3='1%', He='*')
            assert result[3].weight == pytest.approx(0.1)
            assert result[3].flowrate.m_as('L/min') == pytest.approx(0.2)
            assert result[3].line == 'line4'
            assert result[3].mfc is None
            assert result[3].setpoint is None

        def test_invalid_mixture(self):
            config = Config(
                lines=[
                    MFCLine(name='line1', gas=Mixture.create(N2='*')),
                    MFCLine(name='line2', gas=Mixture.create(O2='*')),
                    MFCLine(name='line3', gas=Mixture.create(He='*')),
                    MFCLine(name='line4', gas=Mixture.create(NH3='1%', He='*')),
                ]
            )
            mg = MixtureGenerator(config=config, lines='all')
            target_mixture = Mixture.create(NH3='2%', O2='10%', N2='*')

            ureg = unit_registry()
            result = mg.generate(target_mixture, 2.0 * ureg.L / ureg.min, '25°C')

            assert result.success is False
            assert len(result) == 4
