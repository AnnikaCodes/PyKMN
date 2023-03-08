"""Tests the Gen 1 Pokemon class."""

import unittest
import random
from pykmn.engine.gen1 import Pokemon
from pykmn.data.gen1 import MOVES, SPECIES, TYPES

no_moves = ('None', 'None', 'None', 'None')
zero_stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}

class TestGen1Pokemon(unittest.TestCase):
    def test_stats(self):
        """Tests that the stats are stored/loaded correctly."""
        stats = {'hp': 582, 'atk': 92, 'def': 312, 'spe': 484, 'spc': 831}
        pkmn = Pokemon.new(('Mew', no_moves, {'stats': stats}))
        self.assertDictEqual(pkmn.stats(), stats)

    def test_hp(self):
        """Tests that the HP is stored/loaded correctly."""
        stats = zero_stats.copy()
        stats['hp'] = 582
        pkmn = Pokemon.new(('Mew', no_moves, {'stats': stats}))
        self.assertEqual(pkmn.hp(), 582)

        pkmn = Pokemon.new(('Mew', no_moves, {'stats': stats, 'hp': 53}))
        self.assertEqual(pkmn.hp(), 53)

    def test_moves(self):
        """Tests that the moves are stored/loaded correctly."""
        for length in range(1, 5):
            for _ in range(10):
                moves = tuple(random.choices(list(MOVES.keys()), k=length))
                pp = tuple(MOVES[moves[n]] * 8 / 5 for n in range(length))
                pkmn = Pokemon.new(('Mew', moves))
                self.assertTupleEqual(pkmn.moves(), moves)
                self.assertTupleEqual(pkmn.pp_left(), pp)
                self.assertTupleEqual(tuple(x[0] for x in pkmn.moves_with_pp()), moves)
                self.assertTupleEqual(tuple(x[1] for x in pkmn.moves_with_pp()), pp)

    def test_species(self):
        """Tests that the species is stored/loaded correctly."""
        for species in SPECIES:
            pkmn = Pokemon.new((species, no_moves))
            self.assertEqual(pkmn.species(), species)

    def test_types(self):
        """Tests that the types are stored/loaded correctly."""
        for type1 in TYPES:
            for type2 in TYPES:
                pkmn = Pokemon.new(('Mew', no_moves, {'types': (type1, type2)}))
                self.assertTupleEqual(pkmn.types(), (type1, type2))

    def test_level(self):
        """Tests that the level is stored/loaded correctly."""
        for level in range(1, 100):
            pkmn = Pokemon.new(('Mew', no_moves, {'level': level}))
            self.assertEqual(pkmn.level(), level)