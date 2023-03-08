"""Tests the Gen 1 Pokemon class."""

import unittest
import random
from _pkmn_engine_bindings import ffi # type: ignore
from pykmn.engine.gen1 import Pokemon, PokemonData, LAYOUT_SIZES
from pykmn.data.gen1 import MOVES, SPECIES, TYPES

no_moves = ('None', 'None', 'None', 'None')
zero_stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}

def new_pokemon(data: PokemonData) -> Pokemon:
    """Creates a new Pokemon with the given data."""
    bytes = ffi.new('uint8_t[]', LAYOUT_SIZES['Pokemon'])
    pkmn = Pokemon(bytes)
    pkmn.initialize(data)
    return pkmn

class TestGen1Pokemon(unittest.TestCase):
    def test_stats(self):
        """Tests that the stats are stored/loaded correctly."""
        stats = {'hp': 582, 'atk': 92, 'def': 312, 'spe': 484, 'spc': 831}
        pkmn = new_pokemon(('Mew', no_moves, {'stats': stats}))
        self.assertDictEqual(pkmn.stats(), stats)

    def test_hp(self):
        """Tests that the HP is stored/loaded correctly."""
        stats = zero_stats.copy()
        stats['hp'] = 582
        pkmn = new_pokemon(('Mew', no_moves, {'stats': stats}))
        self.assertEqual(pkmn.hp(), 582)

        pkmn = new_pokemon(('Mew', no_moves, {'stats': stats, 'hp': 53}))
        self.assertEqual(pkmn.hp(), 53)

    def test_moves(self):
        """Tests that the moves are stored/loaded correctly."""
        for length in range(1, 5):
            for _ in range(10):
                moves = tuple(random.choices(list(MOVES.keys()), k=length))
                pp = tuple(MOVES[moves[n]] * 8 / 5 for n in range(length))
                pkmn = new_pokemon(('Mew', moves))
                self.assertTupleEqual(pkmn.moves(), moves)
                self.assertTupleEqual(pkmn.pp_left(), pp)
                self.assertTupleEqual(tuple(x[0] for x in pkmn.moves_with_pp()), moves)
                self.assertTupleEqual(tuple(x[1] for x in pkmn.moves_with_pp()), pp)

    def test_species(self):
        """Tests that the species is stored/loaded correctly."""
        for species in SPECIES:
            pkmn = new_pokemon((species, no_moves))
            self.assertEqual(pkmn.species(), species)

    def test_types(self):
        """Tests that the types are stored/loaded correctly."""
        for type1 in TYPES:
            for type2 in TYPES:
                pkmn = new_pokemon(('Mew', no_moves, {'types': (type1, type2)}))
                self.assertTupleEqual(pkmn.types(), (type1, type2))

    def test_level(self):
        """Tests that the level is stored/loaded correctly."""
        for level in range(1, 100):
            pkmn = new_pokemon(('Mew', no_moves, {'level': level}))
            self.assertEqual(pkmn.level(), level)