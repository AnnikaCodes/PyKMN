"""Tests for protocol parsing."""
import unittest
from pykmn.engine.protocol import parse_protocol


class TestHumanReadable(unittest.TestCase):
    """Test parsing protocol to human-readable protocol messages."""

    def test_move(self):
        """Should parse a |move| message."""
        self.assertListEqual(
            parse_protocol([3, 1, 94, 9, 0]),
            ["|move|p1a: Pokémon #1|Psychic|p2a: Pokémon #1"],
        )

    def test_supereffective(self):
        """Should parse a |-supereffective| message."""
        self.assertListEqual(
            parse_protocol([27, 9]),
            ["Super-effective hit on Player 2's Pokémon in slot 1!"],
        )

    def test_damage(self):
        """Should parse a |-damage| message."""
        self.assertListEqual(
            parse_protocol([10, 9, 0, 0, 250, 2, 0, 0]),
            ["Damage dealt to Player 2's Pokémon in slot 1, which now has 0 HP out "
             "of 762 HP and is healthy."],
        )

    def test_faint(self):
        """Should parse a |-faint| message."""
        self.assertListEqual(
            parse_protocol([6, 9]),
            ["Player 2's Pokémon in slot 1 fainted."],
        )

    def test_win(self):
        """Should parse a |win message."""
        self.assertListEqual(
            parse_protocol([8, 0]),
            ["Player 1 won the battle!"],
        )
