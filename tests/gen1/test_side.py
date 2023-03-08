"""Tests the Gen 1 Side class."""

import unittest
import random
from typing import List
from pykmn.engine.gen1 import Side, PokemonInitializer
from pykmn.data.gen1 import MOVES, SPECIES

no_moves = ('None', 'None', 'None', 'None')
zero_stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}

class TestGen1Side(unittest.TestCase):
    def test_pokemon(self):
        """Tests that the Pokemon are stored/loaded correctly."""
        for length in range(1, 7):
            for _ in range(10):
                random_moves = tuple(random.choices(list(MOVES.keys()), k=4))
                # TODO: Simplify types here so they suck less
                pkmn: List[PokemonInitializer] = tuple(
                    ((random.choice(list(SPECIES.keys())), random_moves)) \
                        for _ in range(length)
                ) # type: ignore # TODO: should we avoid tuples & do a list + len() check instead?
                side = Side.new(pkmn)
                for idx, pkmn in enumerate(pkmn):
                    self.assertEqual(side.team[idx].species(), pkmn[0])
                    self.assertEqual(side.team[idx].moves(), pkmn[1])

    def test_last_move(self) -> None:
        """Tests that the last selected move is stored/loaded correctly."""
        last_selected_move = random.choice(list(MOVES.keys()))
        last_used_move = random.choice(list(MOVES.keys()))
        side = Side.new({
            'team': [('Mew', no_moves)],
            'last_selected_move': last_selected_move,
            'last_used_move': last_used_move,
        })
        self.assertEqual(side.last_selected_move(), last_selected_move)
        self.assertEqual(side.last_used_move(), last_used_move)
