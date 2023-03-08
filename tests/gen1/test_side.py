"""Tests the Gen 1 Side class."""

import unittest
import random
from typing import List
from _pkmn_engine_bindings import ffi # type: ignore
from pykmn.engine.gen1 import Side, PokemonData
from pykmn.data.gen1 import MOVES, SPECIES, LAYOUT_SIZES

no_moves = ('None', 'None', 'None', 'None')
zero_stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}

def new_side(
    team: List[PokemonData],
    last_selected_move: str = 'None',
    last_used_move: str = 'None'
) -> Side:
    """Creates a new Side with the given team and last move."""
    bytes = ffi.new('uint8_t[]', LAYOUT_SIZES['Side'])
    side = Side(bytes)
    side.initialize(team, last_selected_move, last_used_move)
    return side

class TestGen1Side(unittest.TestCase):
    def test_pokemon(self):
        """Tests that the Pokemon are stored/loaded correctly."""
        for length in range(1, 7):
            for _ in range(10):
                random_moves = tuple(random.choices(list(MOVES.keys()), k=4))
                pkmn: List[PokemonData] = tuple(
                    ((random.choice(list(SPECIES.keys())), random_moves)) \
                        for _ in range(length)
                ) # type: ignore
                side = new_side(pkmn)
                for idx, pkmn in enumerate(pkmn):
                    self.assertEqual(side.team[idx].species(), pkmn[0])
                    self.assertEqual(side.team[idx].moves(), pkmn[1])

    def test_last_move(self) -> None:
        """Tests that the last selected move is stored/loaded correctly."""
        last_selected_move = random.choice(list(MOVES.keys()))
        last_used_move = random.choice(list(MOVES.keys()))

        side = new_side([('Mew', no_moves)], last_selected_move, last_used_move)
        self.assertEqual(side.last_selected_move(), last_selected_move)
        self.assertEqual(side.last_used_move(), last_used_move)
