"""Tests for RNGs."""

import unittest
import random
from pykmn.engine.rng import ShowdownRNG


class TestShowdownRNG(unittest.TestCase):
    """Tests for the ShowdownRNG class.

    Args:
        unittest (unittest.TestCase)
    """

    def test_accepts_64bit_seed(self) -> None:
        """Tests that the RNG accepts 64-bit numbers as seeds."""
        for seed in [0, 1, 2**32, 2**64 - 1]:
            rng = ShowdownRNG.from_seed(seed)
            self.assertIn(rng.next(), range(0, 2**32))

    def test_seed(self) -> None:
        """Tests that the RNG returns the correct seed."""
        for _ in range(1000):
            seed = random.randint(0, 2**64 - 1)
            rng = ShowdownRNG.from_seed(seed)
            self.assertEqual(rng.seed(), seed)


if __name__ == '__main__':
    unittest.main()
