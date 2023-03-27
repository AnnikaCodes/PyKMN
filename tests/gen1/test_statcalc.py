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

    def test_vulpix_hp(self):
        """Vulpix's HP stat is calculated correctly."""
        vulpix_stats = SPECIES['Vulpix']['stats']
        self.assertEqual(
            statcalc(vulpix_stats['hp'], level=97, dv=5, is_HP=True),
            251,
        )

    def test_porygon_hp(self):
        """Porygon's HP stat is calculated = to JS."""
        porygon_stats = SPECIES['Porygon']['stats']
        self.assertEqual(
            statcalc(porygon_stats['hp'], level=100, is_HP=True, experience=25590),
            310,
        )

    def test_psyduck_hp(self):
        """Psyduck's HP stat is calculated = to JS."""
        psyduck_stats = SPECIES['Psyduck']['stats']
        self.assertEqual(
            statcalc(psyduck_stats['hp'], level=10, is_HP=True),
            39,
        )

    def test_from_pkmn(self):
        """Stat calculation tests from the pkmn project."""
        gyarados_stats = SPECIES['Gyarados']['stats']
        self.assertEqual(
            127,
            statcalc(gyarados_stats['hp'], dv=0, level=38, experience=5120, is_HP=True),
        )

        pidgeot_stats = SPECIES['Pidgeot']['stats']
        self.assertEqual(
            279,
            statcalc(pidgeot_stats['spe'], dv=15, level=100, experience=63001, is_HP=False),
        )
