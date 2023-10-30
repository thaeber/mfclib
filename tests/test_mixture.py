import pytest

import mfclib
from mfclib import Mixture, supply_proportions_for_mixture
from mfclib.mixture import _balance_mixture, _convert_value
import pint
from toolz import pipe
import numpy as np


class TestConvertValue:
    def test_with_float(self):
        assert _convert_value(0.9) == 0.9

    def test_with_int(self):
        value = _convert_value(2)
        assert isinstance(value, float)
        assert value == 2.0

    def test_with_str(self):
        value = _convert_value('0.678')
        assert isinstance(value, float)
        assert value == 0.678

    def test_fails_on_invalid_str(self):
        with pytest.raises(ValueError):
            _convert_value('test')

    @pytest.mark.skip(
        reason='Currently pint treats strings with commas in an inconsistent way'
    )
    def test_fail_on_thousands_separator(self):
        with pytest.raises(ValueError):
            _convert_value('0,678')

    def test_with_pint_quantity(self, unit_registry):
        assert _convert_value(pint.Quantity('2.0%')) == pytest.approx(0.02)
        assert _convert_value(pint.Quantity('235.1ppm')) == pytest.approx(
            0.0002351
        )

    def test_with_pint_str(self, unit_registry):
        assert _convert_value('2.0%') == pytest.approx(0.02)
        assert _convert_value('2.0percent') == pytest.approx(0.02)
        assert _convert_value('200ppm') == pytest.approx(0.0002)


class TestBalanceMixture:
    def test_with_floats(self):
        feed = _balance_mixture(dict(Ar=0.9, O2=0.1))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_str(self):
        feed = _balance_mixture(dict(Ar="0.9", O2="0.1"))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_mixed_types(self):
        # this might not be meaningful at all, because the mixture fraction should
        # not be greater than 1
        feed = _balance_mixture(dict(Ar=0.7, O2="0.1", NO=0.2))
        assert feed == dict(Ar=0.7, O2=0.1, NO=0.2)

    def test_balance_feed(self):
        feed = _balance_mixture(dict(NO=0.003, Ar='*', CO=0.005))
        assert feed == dict(Ar=0.992, NO=0.003, CO=0.005)

    def test_balance_feed_single_species(self):
        feed = _balance_mixture(dict(N2='*'))
        assert feed == dict(N2=1.0)

    def test_fails_on_multiple_balance_species(self):
        with pytest.raises(ValueError):
            _balance_mixture(dict(Ar='*', N2='*', NO=0.003))

    def test_with_pint_str(self, unit_registry):
        ureg = unit_registry
        feed = _balance_mixture(dict(Ar='*', NO='3000ppm'))
        assert feed == dict(
            Ar=ureg.Quantity(0.997), NO=ureg.Quantity(3000.0, 'ppm')
        )
        assert feed == dict(Ar=0.997, NO=0.003)


class TestMixture:
    def test_create_with_init(self):
        mfc = Mixture(composition=dict(N2=0.79, O2=0.21), name='carrier')
        assert mfc.name == 'carrier'
        assert mfc.composition == dict(N2=0.79, O2=0.21)
        assert dict(mfc) == dict(N2=0.79, O2=0.21)

    def test_from_kws(self):
        mfc = Mixture.from_kws(N2=0.79, O2=0.21)
        assert mfc.composition == dict(N2=0.79, O2=0.21)
        assert dict(mfc) == dict(N2=0.79, O2=0.21)
        assert mfc.name == 'N2/O2'

    def test_create_with_balanced_feed(self):
        mfc = Mixture(composition=dict(N2='*', O2=0.21), name='carrier')
        assert mfc.name == 'carrier'
        assert mfc.composition == dict(N2=0.79, O2=0.21)

    def test_synthesize_name(self):
        mixture = Mixture(composition=dict(NO=0.003, Ar='*'))
        assert mixture.name == 'NO/Ar'

        mixture = Mixture(composition=dict(Ar='*', NO=0.003))
        assert mixture.name == 'Ar/NO'

    def test_conversion_factor(self):
        mfc = Mixture(composition=dict(N2=0.79, O2=0.21))
        assert mfc.cf == pytest.approx(0.9974, abs=0.0001)

    def test_model_dump(self):
        mfc = Mixture(composition=dict(N2=0.79, O2=0.21), name='air')
        assert mfc.model_dump(exclude_defaults=True) == {
            'composition': {'N2': 0.79, 'O2': 0.21},
            'name': 'air',
        }

    def test_model_dump_with_units(self, unit_registry):
        mfc = Mixture(composition=dict(N2=0.79, O2='21.0 %'), name='air')
        assert mfc.model_dump(exclude_defaults=True) == {
            'composition': {'N2': 0.79, 'O2': '21.0 %'},
            'name': 'air',
        }

    def test_model_dump_roundtrip(self):
        original = Mixture(composition=dict(N2=0.79, O2=0.21), name='air')
        mfc = Mixture(**original.model_dump())
        assert mfc.name == 'air'
        assert mfc.composition == dict(N2=0.79, O2=0.21)
        assert dict(mfc) == dict(N2=0.79, O2=0.21)

    def test_model_dump_roundtrip_with_units(self, unit_registry):
        ureg = unit_registry

        original = Mixture(composition=dict(N2=0.79, O2='21%'), name='air')
        mfc = Mixture(**original.model_dump())

        assert mfc.name == 'air'
        assert mfc.composition == dict(N2=0.79, O2=0.21)
        assert dict(mfc) == dict(N2=0.79, O2=0.21)

        assert mfc['N2'] == ureg('0.79')
        assert isinstance(mfc['N2'], ureg.Quantity)
        assert mfc['N2'].magnitude == 0.79
        assert mfc['N2'].units == ureg.Unit('')

        assert mfc['O2'] == ureg('21%')
        assert isinstance(mfc['O2'], ureg.Quantity)
        assert mfc['O2'].magnitude == 21.0
        assert mfc['O2'].units == ureg.Unit('%')

    def test_unbalanced_mixture_not_allowed(self, unit_registry):
        with pytest.raises(ValueError):
            _ = Mixture(composition=dict(NO='3000ppm', Ar='*', He='*'))


class TestProportionsForMixture:
    def test_single_supply(self):
        x = supply_proportions_for_mixture(
            [Mixture.from_kws(name='carrier', N2='*')],
            Mixture.from_kws(N2=1.0),
        )
        assert x == pytest.approx([1.0])

    def test_complex_sources(self):
        sources = [
            Mixture.from_kws(Ar=1.0),
            Mixture.from_kws(O2=1.0),
            Mixture.from_kws(CO=0.1492, Ar='*'),
            Mixture.from_kws(NO=0.002959, Ar='*'),
            Mixture.from_kws(H2='*'),
            Mixture.from_kws(NO2=0.01072, N2O=0.0, Ar='*'),
        ]

        x = supply_proportions_for_mixture(
            sources,
            dict(Ar='*', NO=400e-6, CO=400e-6),
        )

        assert x == pytest.approx(
            [0.86213823, 0, 0.00268097, 0.1351808, 0, 0],
            abs=1e-8,
        )

    def test_warn_on_duplicate_species_in_mixture(self):
        sources = [
            Mixture.from_kws(O2=0.21, N2='*'),
            Mixture.from_kws(NO=0.003, N2='*'),
        ]

        with pytest.warns(UserWarning, match=r'Missing species in supply.'):
            supply_proportions_for_mixture(
                sources,
                dict(CO=0.0004, N2='*'),
            )

    def test_warn_on_invalid_sum(self):
        sources = [
            Mixture.from_kws(Ar=1.0),
            Mixture.from_kws(O2=1.0),
            Mixture.from_kws(CO=0.1492, Ar='*'),
            Mixture.from_kws(NO=0.002959, Ar='*'),
            Mixture.from_kws(H2='*'),
            Mixture.from_kws(NO2=0.01072, N2O=0.0, Ar='*'),
        ]

        with pytest.warns(
            UserWarning, match=r'Inconsistent mixture composition.'
        ):
            supply_proportions_for_mixture(
                sources,
                dict(N2='*', NO=400e-6, CO=400e-6),
            )

    def test_call_with_unbalanced_source(self, unit_registry):
        ureg = unit_registry

        sources = [
            dict(He=1.0),
            dict(O2=0.21, N2='*'),
            dict(CO='10%', He='*'),
            dict(NO='4%', He='*', N2='*'),
        ]

        with pytest.raises(ValueError):
            supply_proportions_for_mixture(
                sources,
                dict(NO='400ppm', CO='400ppm', O2='10%', He='*'),
            )

    def test_call_unbalanced_mixture_should_not_raise(self, unit_registry):
        ureg = unit_registry

        sources = [
            dict(He=1.0),
            dict(O2=0.21, N2='*'),
            dict(CO='10%', He='*'),
            dict(NO='4%', He='*'),
        ]

        try:
            _ = supply_proportions_for_mixture(
                sources,
                dict(NO='400ppm', CO='400ppm', O2='10%', He='*', N2='*'),
            )
        except ValueError as ex:
            pytest.fail(
                f'Call should not raise an ValueError exception:\n{repr(ex)}'
            )

    def test_calculate_with_unbalanced_mixture(self, unit_registry):
        ureg = unit_registry

        sources = [
            dict(He=1.0),
            dict(O2=0.20, N2='*'),
            dict(CO='10%', He='*'),
            dict(NO='4%', He='*'),
        ]

        x = supply_proportions_for_mixture(
            sources,
            dict(NO='400ppm', CO='800ppm', O2='10%', He='*'),
        )

        assert x == pytest.approx(
            [0.482, 0.500, 0.008, 0.010],
            abs=1e-8,
        )

    def test_calculate_with_missing_species_in_mixture(self, unit_registry):
        ureg = unit_registry

        sources = [
            dict(He=1.0),
            dict(O2=0.20, N2='*'),
            dict(CO='10%', He='*'),
            dict(NO='4%', He='*'),
        ]

        x = supply_proportions_for_mixture(
            sources,
            dict(NO='400ppm', CO='800ppm', O2='10%', He='*'),
        )

        assert x == pytest.approx(
            [0.482, 0.500, 0.008, 0.010],
            abs=1e-8,
        )
