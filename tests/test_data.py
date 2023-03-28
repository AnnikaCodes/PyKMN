"""Tests for the pykmn.data package."""

import unittest
from pykmn import data
from pykmn.data.gen1 import LAYOUT_SIZES, LAYOUT_OFFSETS


class TestGen1Data(unittest.TestCase):
    """Tests for Gen I data.

    Args:
        unittest (unittest.TestCase)
    """

    def test_species(self) -> None:
        """Gen I species data has stats and 151 species."""
        bulbasaur = data.gen1.SPECIES['Bulbasaur']
        self.assertEqual(bulbasaur['stats']['spc'], 65)
        self.assertListEqual(bulbasaur['types'], ['Grass', 'Poison'])

        self.assertEqual(len(data.gen1.SPECIES), 151)

    def test_moves(self) -> None:
        """Gen I has move PP data & right length."""
        self.assertEqual(data.gen1.MOVES['Tackle'], 35)
        self.assertEqual(len(data.gen1.MOVES), 165)

    def test_types(self) -> None:
        """Gen I has 15 types."""
        self.assertEqual(len(data.gen1.TYPES), 15)

    def test_libpkmn_ids(self) -> None:
        """Gen I libpkmn move IDs."""
        self.assertEqual(data.gen1.MOVE_IDS['Karate Chop'], 2)


class TestGen2Data(unittest.TestCase):
    """Tests for Gen II data.

    Args:
        unittest (unittest.TestCase)
    """

    def test_species(self) -> None:
        """Gen II species data has stats and 251 species."""
        cyndaquil = data.gen2.SPECIES['Cyndaquil']
        self.assertEqual(cyndaquil['stats']['spa'], 60)
        self.assertListEqual(cyndaquil['types'], ['Fire'])

        self.assertEqual(len(data.gen2.SPECIES), 251)

    def test_moves(self) -> None:
        """Gen II has move PP data & right length."""
        self.assertEqual(data.gen2.MOVES['Rock Smash'], 15)
        self.assertEqual(len(data.gen2.MOVES), 251)

    def test_types(self) -> None:
        """Gen II has 18 types."""
        self.assertEqual(len(data.gen2.TYPES), 18)

    def test_items(self) -> None:
        """Gen II has 251 items."""
        self.assertEqual(len(data.gen2.ITEMS), 195)

class TestLayoutData(unittest.TestCase):
    """Tests for Gen I layout data."""

    def test_layout_sizes(self) -> None:
        """Gen I layout sizes."""
        self.assertLess(LAYOUT_SIZES['Side'] * 2, LAYOUT_SIZES['Battle'])
        self.assertGreater(
            LAYOUT_SIZES['Side'],
            LAYOUT_SIZES['Pokemon'] * 6 + LAYOUT_SIZES['ActivePokemon']
        )

    def test_layout_offsets(self) -> None:
        """Gen I layout offsets should make sense."""
        self.assertEqual(
            LAYOUT_OFFSETS['Side']['active'] - LAYOUT_OFFSETS['Side']['pokemon'],
            LAYOUT_SIZES['Pokemon'] * 6
        )
        self.assertEqual(
            LAYOUT_OFFSETS['Side']['order'] - LAYOUT_OFFSETS['Side']['active'],
            LAYOUT_SIZES['ActivePokemon']
        )


if __name__ == '__main__':
    unittest.main()
