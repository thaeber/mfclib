import pytest

from mfclib import Mixture, MixtureCollection


class TestMixtureCollection:
    def test_create_empty(self):
        mixtures = MixtureCollection()
        assert len(mixtures) == 0

    def test_create_with_mixtures(self, unit_registry):
        source = [
            Mixture(composition=dict(Ar='*')),
            Mixture(composition=dict(CH4='5%', N2='*')),
        ]
        mixtures = MixtureCollection(mixtures=source.copy())
        assert len(mixtures) == 2
        assert list(mixtures) == source

    def test_add_mixture(self, unit_registry):
        collection = MixtureCollection()
        collection.append(Mixture.from_kws(Ar=1.0))
        assert len(collection) == 1
        assert collection[0] == Mixture.from_kws(Ar=1.0)

    def test_delete_mixture(self, unit_registry):
        mixtures = MixtureCollection(
            mixtures=[
                Mixture(composition=dict(Ar='*')),
                Mixture(composition=dict(CH4='5%', N2='*')),
                Mixture(composition=dict(NO='5000ppm', N2='*')),
            ]
        )
        assert len(mixtures) == 3

        del mixtures[1]
        assert len(mixtures) == 2
        assert list(mixtures) == [
            Mixture(composition=dict(Ar='*')),
            Mixture(composition=dict(NO='5000ppm', N2='*')),
        ]
