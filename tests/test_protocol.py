"""Tests for protocol parsing."""
import unittest
from pykmn.engine.protocol import binary_to_human


class TestHumanReadable(unittest.TestCase):
    """Test parsing protocol to human-readable protocol messages."""

    def test_move(self):
        """Should parse a |move| message."""
        self.assertListEqual(
            binary_to_human([3, 1, 94, 9, 0]),
            ["Player 1's Pokémon in slot 1 used Psychic on Player 2's Pokémon in slot 1."],
        )

    @unittest.skip("Not implemented yet")
    def test_supereffective(self):
        """Should parse a |-supereffective| message."""
        self.assertListEqual(
            binary_to_human([27, 9]),
            ["Super-effective hit on Player 2's Pokémon in slot 1!"],
        )

    @unittest.skip("Not implemented yet")
    def test_damage(self):
        """Should parse a |-damage| message."""
        self.assertListEqual(
            binary_to_human([10, 9, 0, 0, 250, 2, 0, 0]),
            ["Damage dealt to Player 2's Pokémon in slot 1, which now has 0 HP out \
             of 762 HP and no status condition!"],
        )

    @unittest.skip("Not implemented yet")
    def test_faint(self):
        """Should parse a |-faint| message."""
        self.assertListEqual(
            binary_to_human([6, 9]),
            ["Player 2's Pokémon in slot 1 fainted!"],
        )

    @unittest.skip("Not implemented yet")
    def test_win(self):
        """Should parse a |-win message."""
        self.assertListEqual(
            binary_to_human([8, 0]),
            ["Player 1 won the battle!"],
        )
