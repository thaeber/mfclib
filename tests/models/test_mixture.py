import pint
import pytest

from mfclib.models import Mixture, supply_proportions_for_mixture
import mfclib


class TestConvertValue:
    def test_with_float(self):
        assert Mixture._convert_value(0.9) == 0.9

    def test_with_int(self):
        value = Mixture._convert_value(2)
        assert value == 2.0

    def test_with_str(self):
        value = Mixture._convert_value('0.678')
        assert value == 0.678

    def test_fails_on_invalid_str(self):
        with pytest.raises((ValueError, pint.UndefinedUnitError)):
            Mixture._convert_value('test')

    @pytest.mark.skip(
        reason='Currently pint treats strings with commas in an inconsistent way'
    )
    def test_fail_on_thousands_separator(self):
        with pytest.raises(ValueError):
            Mixture._convert_value('0,678')

    def test_with_pint_quantity(self):
        assert Mixture._convert_value(pint.Quantity('2.0%')) == pytest.approx(0.02)
        assert Mixture._convert_value(pint.Quantity('235.1ppm')) == pytest.approx(
            0.0002351
        )

    def test_with_pint_str(self):
        assert Mixture._convert_value('2.0%') == pytest.approx(0.02)
        assert Mixture._convert_value('2.0percent') == pytest.approx(0.02)
        assert Mixture._convert_value('200ppm') == pytest.approx(0.0002)


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

    def test_create_with_balance_species(self):
        mfc = Mixture(composition=dict(N2='*', O2='21%'), name='carrier')

        ureg = mfclib.unit_registry()
        assert mfc.name == 'carrier'
        assert mfc.composition == dict(N2='*', O2=21.0 * ureg.percent)
        assert mfc.mole_fractions == dict(N2=0.79, O2=0.21)

    def test_fails_on_multiple_balance_species(self):
        with pytest.raises(ValueError):
            mfc = Mixture(composition=dict(Ar='*', N2='*', NO=0.003))

    def test_with_balance_species_and_units(self):
        ureg = mfclib.unit_registry()
        feed = Mixture(composition=dict(Ar='*', NO='3000ppm'))
        assert feed.composition == dict(Ar='*', NO=ureg.Quantity(3000.0, 'ppm'))
        assert feed.mole_fractions == dict(Ar=0.997, NO=0.003)

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

    def test_model_dump_with_units(self):
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

    def test_model_dump_roundtrip_with_validation(self):
        original = Mixture(composition=dict(N2=0.79, O2=0.21), name='air')
        data = original.model_dump()
        mfc = Mixture.model_validate(data)
        assert mfc.name == 'air'
        assert mfc.composition == dict(N2=0.79, O2=0.21)
        assert dict(mfc) == dict(N2=0.79, O2=0.21)

    def test_model_dump_roundtrip_with_units(self):
        ureg = mfclib.unit_registry()

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

    def test_unbalanced_mixture_not_allowed(self):
        with pytest.raises(ValueError):
            _ = Mixture(composition=dict(NO='3000ppm', Ar='*', He='*'))

    class TestMixtureCreate:
        def test_create_with_dict(self):
            mixture = Mixture.create({'N2': 0.79, 'O2': 0.21})
            assert mixture.composition == {'N2': 0.79, 'O2': 0.21}
            assert mixture.name == 'N2/O2'

        def test_create_with_mixture_instance(self):
            original = Mixture(composition={'N2': 0.79, 'O2': 0.21}, name='air')
            mixture = Mixture.create(original)
            assert mixture.composition == {'N2': 0.79, 'O2': 0.21}
            assert mixture.name == 'air'

        def test_create_with_name_and_composition(self):
            mixture = Mixture.create(
                {'name': 'air', 'composition': {'N2': 0.79, 'O2': 0.21}}
            )
            assert mixture.composition == {'N2': 0.79, 'O2': 0.21}
            assert mixture.name == 'air'

        def test_create_with_composition_only(self):
            mixture = Mixture.create({'composition': {'N2': 0.79, 'O2': 0.21}})
            assert mixture.composition == {'N2': 0.79, 'O2': 0.21}
            assert mixture.name == 'N2/O2'

    class TestMixtureFractions:
        def test_fractions_with_simple_composition(self):
            mfc = Mixture(composition=dict(N2=0.79, O2=0.21))
            fractions = mfc.fractions
            assert isinstance(fractions, dict)
            assert all(isinstance(f, pint.Quantity) for f in fractions.values())
            assert fractions == dict(N2=pint.Quantity(0.79), O2=pint.Quantity(0.21))

        def test_fractions_with_units(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2=0.79, O2='21%'))
            fractions = mfc.fractions
            assert isinstance(fractions, dict)
            assert all(isinstance(f, pint.Quantity) for f in fractions.values())
            assert fractions == dict(
                N2=pint.Quantity(0.79), O2=pint.Quantity(21, ureg.percent)
            )

        def test_fractions_with_balance_species(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2='*', O2='21%'))
            fractions = mfc.fractions
            assert isinstance(fractions, dict)
            assert all(isinstance(f, pint.Quantity) for f in fractions.values())
            assert fractions == dict(
                N2=pint.Quantity(79, ureg.percent),
                O2=pint.Quantity(21, ureg.percent),
            )

        def test_fractions_with_multiple_species(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2=0.78, O2='21%', CO2='1%'))
            fractions = mfc.fractions
            assert isinstance(fractions, dict)
            assert all(isinstance(f, pint.Quantity) for f in fractions.values())
            assert fractions == dict(
                N2=pint.Quantity(0.78),
                O2=pint.Quantity(21, ureg.percent),
                CO2=pint.Quantity(1, ureg.percent),
            )

        def test_fractions_with_invalid_composition(self):
            with pytest.raises(ValueError):
                Mixture(composition=dict(N2='*', O2='*'))

    class TestMixtureGetItem:
        def test_getitem_with_simple_composition(self):
            mfc = Mixture(composition=dict(N2=0.79, O2=0.21))
            assert mfc['N2'] == 0.79
            assert mfc['O2'] == 0.21

        def test_getitem_with_units(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2=0.79, O2='21%'))
            assert mfc['N2'] == ureg('0.79')
            assert mfc['O2'] == ureg('21%')

        def test_getitem_with_balance_species(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2='*', O2='21%'))
            assert mfc['N2'] == ureg('79%')
            assert mfc['O2'] == ureg('21%')

        def test_getitem_with_multiple_species(self):
            ureg = mfclib.unit_registry()
            mfc = Mixture(composition=dict(N2=0.78, O2='21%', CO2='1%'))
            assert mfc['N2'] == 0.78
            assert mfc['O2'] == ureg('21%')
            assert mfc['CO2'] == ureg('1%')


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

    def test_warn_on_invalid_sum(self):
        sources = [
            Mixture.from_kws(Ar=1.0),
            Mixture.from_kws(O2=1.0),
            Mixture.from_kws(CO=0.1492, Ar='*'),
            Mixture.from_kws(NO=0.002959, Ar='*'),
            Mixture.from_kws(H2='*'),
            Mixture.from_kws(NO2=0.01072, N2O=0.0, Ar='*'),
        ]

        with pytest.warns(UserWarning, match=r'Inconsistent mixture composition.'):
            supply_proportions_for_mixture(
                sources,
                dict(N2='*', NO=400e-6, CO=400e-6),
            )

    def test_call_with_unbalanced_source(self):
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

    def test_calculate_with_unbalanced_mixture(self):
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

    def test_calculate_with_missing_species_in_mixture(self):
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
