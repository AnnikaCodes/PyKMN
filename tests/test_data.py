"""Tests for the pykmn.data package."""

import unittest
from pykmn import data


class TestGen1Data(unittest.TestCase):
    """Tests for Gen I data.

    Args:
        unittest (unittest.TestCase)
    """

    def test_species(self):
        """Gen I species data has stats and 151 species."""
        bulbasaur = data.gen1.SPECIES['Bulbasaur']
        self.assertEqual(bulbasaur['stats']['spc'], 65)
        self.assertListEqual(bulbasaur['types'], ['Grass', 'Poison'])

        self.assertEqual(len(data.gen1.SPECIES), 151)

    def test_moves(self):
        """Gen I has move PP data & right length."""
        self.assertEqual(data.gen1.MOVES['Tackle'], 35)
        self.assertEqual(len(data.gen1.MOVES), 165)

    def test_types(self):
        """Gen I has 15 types."""
        self.assertEqual(len(data.gen1.TYPES), 15)


class TestGen2Data(unittest.TestCase):
    """Tests for Gen II data.

    Args:
        unittest (unittest.TestCase)
    """

    def test_species(self):
        """Gen II species data has stats and 251 species."""
        cyndaquil = data.gen2.SPECIES['Cyndaquil']
        self.assertEqual(cyndaquil['stats']['spa'], 60)
        self.assertListEqual(cyndaquil['types'], ['Fire'])

        self.assertEqual(len(data.gen2.SPECIES), 251)

    def test_moves(self):
        """Gen II has move PP data & right length."""
        self.assertEqual(data.gen2.MOVES['Rock Smash'], 15)
        self.assertEqual(len(data.gen2.MOVES), 251)

    def test_types(self):
        """Gen II has 18 types."""
        self.assertEqual(len(data.gen2.TYPES), 18)

    def test_items(self):
        """Gen II has 251 items."""
        self.assertEqual(len(data.gen2.ITEMS), 195)


if __name__ == '__main__':
    unittest.main()
