"""This file includes common functionality like bindings for pkmn_result."""
from enum import Enum
from typing import Tuple
from _pkmn_engine_bindings import lib  # type: ignore

# This file needs some testing, but I think it makes sense to test it
# along with the battle simulation tests.


class BattleChoiceType(Enum):
    """An enum representing the types of choice players can make in a Pokémon battle.

    Python version of pkmn_choice_kind.
    """

    PASS = 0
    MOVE = 1
    SWITCH = 2


class ResultType(Enum):
    """An enum representing the result of a move in a Pokémon battle.

    Python version of pkmn_result_kind.
    """

    NONE = 0
    PLAYER_1_WIN = 1
    PLAYER_2_WIN = 2
    TIE = 3
    ERROR = 4


class Player(Enum):
    """An enum representing the players in a Pokémon battle.

    Python version of pkmn_player.
    """

    P1 = 0
    P2 = 1


class Result:
    """Represents the result of updating a Pokémon battle.

    Python version of pkmn_result.

    Consumers of the pykmn library shouldn't need to construct this class themselves.
    """

    def __init__(self, _pkmn_result: int):
        """Create a new Result object.

        Args:
            _pkmn_result (int): The value of the C pkmn_result type.
        """
        self._pkmn_result = _pkmn_result

    def type(self) -> ResultType:
        """Get the type of result.

        Python version of pkmn_result_type.
        """
        return ResultType(lib.pkmn_result_type(self._pkmn_result))

    def p1_choice_type(self) -> BattleChoiceType:
        """Get the type of choice the first player made.

        Python version of pkmn_result_p1.
        """
        return BattleChoiceType(lib.pkmn_result_p1(self._pkmn_result))

    def p2_choice_type(self) -> BattleChoiceType:
        """Get the type of choice the second player made.

        Python version of pkmn_result_p2.
        """
        return BattleChoiceType(lib.pkmn_result_p2(self._pkmn_result))

    def is_error(self) -> bool:
        """Check if the result is an error.

        Python version of pkmn_error.
        """
        return lib.pkmn_error(self._pkmn_result)

    def __repr__(self) -> str:
        """Provide a string representation of the Result."""
        return (
            f"Result(type: {self.type()}, player 1 choice: {self.p1_choice_type()}, "
            f"player 2 choice: {self.p2_choice_type()})"
        )


class BattleChoice:
    """Represents a choice a player makes in a Pokémon battle.

    Python version of pkmn_choice.

    Consumers of the pykmn library should not construct this class themselves, but instead
    use the `possible_choices` method of the Battle class for the generation they are simulating.
    """

    def __init__(self, _pkmn_choice: int):
        """
        DON'T CALL THIS CONSTRUCTOR.

        If you pass an invalid choice to libpkmn, it may behave unpredictably or cause errors.

        Use the `possible_choices` method of the Battle class to get BattleChoice objects.
        """
        self._pkmn_choice = _pkmn_choice  # uint8_t

    def type(self) -> BattleChoiceType:
        """Get the type of the choice (pass/move/switch).

        Python version of pkmn_choice_type.
        """
        return BattleChoiceType(lib.pkmn_choice_type(self._pkmn_choice))

    def data(self) -> int | None:
        """Get the data associated with the choice.

        Returns:
            int | None: slot number for a switch or move index for a move
        """
        if self.type() == BattleChoiceType.PASS:
            return None
        return lib.pkmn_choice_data(self._pkmn_choice)

    def __repr__(self) -> str:
        """Provide a string representation of the BattleChoice."""
        type = self.type()
        if type == BattleChoiceType.MOVE:
            data = self.data()
            if data == 0:
                return "BattleChoice(can't select a move)"
            return f"BattleChoice(move #{self.data()})"
        elif type == BattleChoiceType.SWITCH:
            return f"BattleChoice(switch to slot #{self.data()})"
        else:
            return "BattleChoice(pass)"


class Softlock(Exception):
    """This exception may be raised when a battle has softlocked."""

    pass


def pack_u16_as_bytes(n: int) -> Tuple[int, int]:
    """Pack an unsigned 16-bit integer into a pair of bytes.

    Args:
        n (int): The unsigned 16-bit integer to pack.

    Returns:
        Tuple[int, int]: The pair of bytes.
    """
    return (n & 0xFF, (n >> 8))

def pack_two_u4s(a: int, b: int) -> int:
    """Pack two unsigned 4-bit integers into a single byte.

    Args:
        a (int): The first unsigned 4-bit integer to pack.
        b (int): The second unsigned 4-bit integer to pack.

    Returns:
        int: The single byte.
    """
    return (a & 0x0F) | ((b & 0x0F) << 4)

