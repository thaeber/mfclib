from mfclib import Supply
from mfclib.supply import unify_mixture, unify_mixture_value
import pytest


class TestUnifyMixtureValue:

    def test_with_float(self):
        assert unify_mixture_value(0.9) == 0.9

    def test_with_int(self):
        value = unify_mixture_value(2)
        assert isinstance(value, float)
        assert value == 2.0

    def test_with_str(self):
        value = unify_mixture_value('0.678')
        assert isinstance(value, float)
        assert value == 0.678

    def test_fails_on_invalid_str(self):
        with pytest.raises(ValueError):
            unify_mixture_value('test')

        with pytest.raises(ValueError):
            unify_mixture_value('0,678')

    @pytest.mark.skip(reason='Not implemented yet.')
    def test_with_quantity(self):
        pass


class TestUnifyMixture:

    def test_with_floats(self):
        feed = unify_mixture(dict(Ar=0.9, O2=0.1))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_str(self):
        feed = unify_mixture(dict(Ar="0.9", O2="0.1"))
        assert feed == dict(Ar=0.9, O2=0.1)

    def test_with_mixed_types(self):
        # this might not be meaningful at all, because the mixture fraction should
        # not be greater than 1
        feed = unify_mixture(dict(Ar=0.9, O2="0.1", NO=2))
        assert feed == dict(Ar=0.9, O2=0.1, NO=2)

    def test_balance_feed(self):
        feed = unify_mixture(dict(NO=0.003, Ar='*', CO=0.005))
        assert feed == dict(Ar=0.992, NO=0.003, CO=0.005)

    def test_balance_feed_single_species(self):
        feed = unify_mixture(dict(N2='*'))
        assert feed == dict(N2=1.0)

    def test_balance_feed_fails_on_total(self):
        with pytest.raises(ValueError):
            unify_mixture(dict(NO=1.003, Ar='*'))

    def test_fails_on_multiple_balance_species(self):
        with pytest.raises(ValueError):
            unify_mixture(dict(Ar='*', N2='*', NO=0.003))


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

    def test_invalid_feed_total(self):
        with pytest.raises(ValueError):
            Supply('some gas', dict(Ar=0.8, O2=0.15, H2=0.2))

    def test_from_kws(self):
        mfc = Supply.from_components('carrier', N2=0.79, O2=0.21)
        assert mfc.name == 'carrier'
        assert mfc.feed == dict(N2=0.79, O2=0.21)

    def test_conversion_factor(self):
        mfc = Supply.from_components('carrier', N2=0.79, O2=0.21)
        assert mfc.cf == pytest.approx(0.9974, abs=0.0001)