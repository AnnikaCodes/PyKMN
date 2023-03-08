"""Tests for RNGs."""

import unittest
from pykmn.engine.rng import ShowdownRNG


class TestShowdownRNG(unittest.TestCase):
    """Tests for the ShowdownRNG class.

    Args:
        unittest (unittest.TestCase)
    """

    def test_accepts_64bit_seed(self):
        """Tests that the RNG accepts 64-bit numbers as seeds."""
        for seed in [0, 1, 2**32, 2**64 - 1]:
            rng = ShowdownRNG.from_seed(seed)
            self.assertIn(rng.next(), range(0, 2**32))


if __name__ == '__main__':
    unittest.main()
