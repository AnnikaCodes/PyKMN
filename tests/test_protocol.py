"""Tests for protocol parsing."""
import unittest
from pykmn.engine.protocol import parse_protocol
from pykmn.data.gen1 import LIBPKMN_SPECIES_IDS, LIBPKMN_MOVE_IDS
from pykmn.data.protocol import MESSAGES
from typing import List


class TestHumanReadable(unittest.TestCase):
    """Test parsing protocol to human-readable protocol messages."""

    def case(self, protocol: List[int], expected: List[str]):
        """Assert that the protocol parses to the expected message."""
        self.assertListEqual(parse_protocol(protocol), expected)

    def test_move(self):
        """Should parse a |move| message."""
        self.case(
            [MESSAGES.index('Move'), 1, 94, 9, 0],
            ["|move|p1a: Pokémon #1|Psychic|p2a: Pokémon #1"],
        )
        self.case(
            [MESSAGES.index('Move'), 3, 126, 9, 1, 118],
            ["|move|p1a: Pokémon #3|Fire Blast|p2a: Pokémon #1|[from] Metronome"],
        )

    def test_switch(self):
        """Should parse a |switch| message."""
        self.case([
            MESSAGES.index('Switch'), 3, LIBPKMN_SPECIES_IDS['Charizard'], 73,
            189 & 0xFF, 189 >> 8, 314 & 0xFF, 314 >> 8, 128
        ], ["|switch|p1a: Pokémon #3|Charizard, L73|189/314 tox"])

    def test_cant(self):
        """Should parse a |cant| message."""
        self.case([MESSAGES.index('Cant'), 9, 7], ["|cant|p2a: Pokémon #1|nopp"])
        # Disable case
        self.case(
            [MESSAGES.index('Cant'), 9, 5, LIBPKMN_MOVE_IDS['Acid Armor']],
            ["|cant|p2a: Pokémon #1|Disable|Acid Armor"]
        )

    def test_faint(self):
        """Should parse a |faint| message."""
        self.case([MESSAGES.index('Faint'), 13], ["|faint|p2a: Pokémon #5"])

    def test_turn(self):
        """Should parse a |turn| message."""
        for turn in [0, 1, 50, 27453]:
            self.case([MESSAGES.index('Turn'), turn & 0xFF, turn >> 8], [f"|turn|{turn}"])

    def test_win(self):
        """Should parse a |win message."""
        self.case([MESSAGES.index('Win'), 0], ["|win|p1"])

    def test_tie(self):
        """Should parse a |tie message."""
        self.case([MESSAGES.index('Tie')], ["|tie"])

    def test_damage(self):
        """Should parse a |-damage| message."""
        self.case(
            [MESSAGES.index('Damage'), 9, 0, 0, 250, 2, 0, 0],
            ["|-damage|p2a: Pokémon #1|0/762"],
        )
        self.case(
            [MESSAGES.index('Damage'), 4, 63 & 0xFF, 63 >> 8, 250, 2, 16, 3],
            ["|-damage|p1a: Pokémon #4|63/762 brn|[from] confusion"],
        )
        # Recoil case
        self.case(
            [MESSAGES.index('Damage'), 4, 382 & 0xFF, 382 >> 8, 30, 2, 64, 5, 10],
            ["|-damage|p1a: Pokémon #4|382/542 par|[from] recoil|[of] p2a: Pokémon #2"],
        )

    def test_heal(self):
        """Should parse a |-heal| message."""
        # base case
        self.case(
            [MESSAGES.index('Heal'), 9, 91, 0, 30, 1, 8, 0],
            ["|-heal|p2a: Pokémon #1|91/286 psn"]
        )
        # silent case
        self.case(
            [MESSAGES.index('Heal'), 9, 91, 0, 30, 1, 4, 1],
            ["|-heal|p2a: Pokémon #1|91/286 slp|[silent]"],
        )
        # from drain case
        self.case(
            [MESSAGES.index('Heal'), 2, 91, 0, 30, 1, 16, 2, 12],
            ["|-heal|p1a: Pokémon #2|91/286 brn|[from] drain|[of] p2a: Pokémon #4"],
        )

    def test_supereffective(self):
        """Should parse a |-supereffective| message."""
        self.case([MESSAGES.index('SuperEffective'), 9], ["|-supereffective|p2a: Pokémon #1"])
