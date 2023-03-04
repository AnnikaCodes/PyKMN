"""This file includes common functionality like bindings for pkmn_result."""
from enum import Enum
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


class Softlock(Exception):
    """This exception may be raised when a battle has softlocked."""

    pass
