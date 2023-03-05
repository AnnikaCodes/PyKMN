"""Tests for Gen I stat calculation."""

import unittest
from pykmn.engine.gen1 import statcalc
from pykmn.data.gen1 import SPECIES


class TestGen1StatCalculation(unittest.TestCase):
    """Test cases."""

    def test_gengar_matches_ps_calculator(self):
        """Gengar's stats match those calculated by calc.pokemonshowdown.com."""
        gengar_stats = SPECIES['Gengar']['stats']

        self.assertEqual(statcalc(gengar_stats['atk'], dv=15, experience=65535, level=100), 228)
        self.assertEqual(statcalc(gengar_stats['def'], dv=15, experience=65535, level=100), 218)
        self.assertEqual(statcalc(gengar_stats['spc'], dv=15, experience=65535, level=100), 358)
        self.assertEqual(statcalc(gengar_stats['spe'], dv=15, experience=65535, level=100), 318)
        self.assertEqual(
            statcalc(gengar_stats['hp'], dv=15, experience=65535, level=100, is_HP=True),
            323,
        )
