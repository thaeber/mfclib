import pytest

import mfclib
from mfclib import Mixture, Supply, supply_proportions_for_mixture
from mfclib.supply import convert_mixture, convert_mixture_value
import pint


class TestUnifyMixtureValue:
    def test_with_float(self):
        assert convert_mixture_value(0.9) == 0.9

    def test_with_int(self):
        value = convert_mixture_value(2)
        assert isinstance(value, float)
        assert value == 2.0

    def test_with_str(self):
        value = convert_mixture_value('0.678')
        assert isinstance(value, float)
        assert value == 0.678

    def test_fails_on_invalid_str(self):
        with pytest.raises(ValueError):
            convert_mixture_value('test')

    @pytest.mark.skip(
        reason='Currently pint treats strings with commas in an inconsistent way'
    )
    def test_fail_on_thousands_separator(self):
        with pytest.raises(ValueError):
            convert_mixture_value('0,678')

    def test_with_pint_quantity(self):
        mfclib.register_pint()
        assert convert_mixture_value(pint.Quantity('2.0%')) == pytest.approx(0.02)
        assert convert_mixture_value(pint.Quantity('235.1ppm')) == pytest.approx(
            0.0002351
        )

    def test_with_pint_str(self):
        mfclib.register_pint()
        assert convert_mixture_value('2.0%') == pytest.approx(0.02)
        assert convert_mixture_value('2.0percent') == pytest.approx(0.02)
        assert convert_mixture_value('200ppm') == pytest.approx(0.0002)


class TestUnifyMixture:
    def test_with_floats(self):
        feed = convert_mixture(dict(Ar=0.9, O2=0.1))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_str(self):
        feed = convert_mixture(dict(Ar="0.9", O2="0.1"))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_mixed_types(self):
        # this might not be meaningful at all, because the mixture fraction should
        # not be greater than 1
        feed = convert_mixture(dict(Ar=0.9, O2="0.1", NO=2))
        assert feed == dict(Ar=0.9, O2=0.1, NO=2)

    def test_balance_feed(self):
        feed = convert_mixture(dict(NO=0.003, Ar='*', CO=0.005))
        assert feed == dict(Ar=0.992, NO=0.003, CO=0.005)

    def test_balance_feed_single_species(self):
        feed = convert_mixture(dict(N2='*'))
        assert feed == dict(N2=1.0)

    def test_balance_feed_fails_on_total(self):
        with pytest.raises(ValueError):
            convert_mixture(dict(NO=1.003, Ar='*'))

    def test_fails_on_multiple_balance_species(self):
        with pytest.raises(ValueError):
            convert_mixture(dict(Ar='*', N2='*', NO=0.003))


class TestSupply:
    def test_create_with_init(self):
        mfc = Supply('carrier', dict(N2=0.79, O2=0.21))
        assert mfc.name == 'carrier'
        assert mfc.feed == dict(N2=0.79, O2=0.21)

    def test_create_with_balanced_feed(self):
        mfc = Supply('carrier', dict(N2='*', O2=0.21))
        assert mfc.name == 'carrier'
        assert mfc.feed == dict(N2=0.79, O2=0.21)

    def test_requires_name(self):
        with pytest.raises(ValueError):
            Supply('')

    def test_names_must_be_str(self):
        with pytest.raises(TypeError):
            Supply(1.0)

    def test_synthesize_name(self):
        supply = Supply.from_kws(NO=0.003, Ar='*')
        assert supply.name == 'NO|Ar'

    def test_invalid_feed_total(self):
        with pytest.raises(ValueError):
            Supply('some gas', dict(Ar=0.8, O2=0.15, H2=0.2))

    def test_from_kws(self):
        mfc = Supply.from_kws(N2=0.79, O2=0.21, name='carrier')
        assert mfc.name == 'carrier'
        assert mfc.feed == dict(N2=0.79, O2=0.21)

    def test_conversion_factor(self):
        mfc = Supply.from_kws(N2=0.79, O2=0.21)
        assert mfc.feed.cf == pytest.approx(0.9974, abs=0.0001)


class TestProportionsForMixture:
    def test_single_supply(self):
        x = supply_proportions_for_mixture(
            [Supply.from_kws(name='carrier', N2='*')],
            Mixture.from_kws(N2=1.0),
        )
        assert x == pytest.approx([1.0])

    def test_complex_sources(self):
        sources = [
            Supply.from_kws(Ar=1.0),
            Supply.from_kws(O2=1.0),
            Supply.from_kws(CO=0.1492, Ar='*'),
            Supply.from_kws(NO=0.002959, Ar='*'),
            Supply.from_kws(H2='*'),
            Supply.from_kws(NO2=0.01072, N2O=0.0, Ar='*'),
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
        sources = [Supply.from_kws(O2=0.21, N2='*'), Supply.from_kws(NO=0.003, N2='*')]

        with pytest.warns(UserWarning, match=r'Missing species in supply.'):
            supply_proportions_for_mixture(
                sources,
                dict(CO=0.0004, N2='*'),
            )

    def test_warn_on_invalid_sum(self):
        sources = [
            Supply.from_kws(Ar=1.0),
            Supply.from_kws(O2=1.0),
            Supply.from_kws(CO=0.1492, Ar='*'),
            Supply.from_kws(NO=0.002959, Ar='*'),
            Supply.from_kws(H2='*'),
            Supply.from_kws(NO2=0.01072, N2O=0.0, Ar='*'),
        ]

        with pytest.warns(UserWarning, match=r'Inconsistent mixture composition.'):
            supply_proportions_for_mixture(
                sources,
                dict(N2='*', NO=400e-6, CO=400e-6),
            )
