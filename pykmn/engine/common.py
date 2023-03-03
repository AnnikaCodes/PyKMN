"""This file includes common functionality like bindings for pkmn_result."""
from enum import Enum
from _pkmn_engine_bindings import lib  # type: ignore

# This file needs some testing, but I think it makes sense to test it
# along with the battle simulation tests.


class BattleChoiceKind(Enum):
    """An enum representing the kinds of choice players can make in a Pokémon battle.

    Python version of pkmn_choice_kind.
    """

    PASS = 0
    MOVE = 1
    SWITCH = 2


class ResultKind(Enum):
    """An enum representing the result of a move in a Pokémon battle.

    Python version of pkmn_result_kind.
    """

    NONE = 0
    WIN = 1
    LOSE = 2
    TIE = 3
    ERROR = 4


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

    def kind(self) -> ResultKind:
        """Get the kind of result.

        Python version of pkmn_result_type.
        """
        return ResultKind(lib.pkmn_result_type(self._pkmn_result))

    def p1_choice_kind(self) -> BattleChoiceKind:
        """Get the kind of choice the first player made.

        Python version of pkmn_result_p1.
        """
        return BattleChoiceKind(lib.pkmn_result_p1(self._pkmn_result))

    def p2_choice_kind(self) -> BattleChoiceKind:
        """Get the kind of choice the second player made.

        Python version of pkmn_result_p2.
        """
        return BattleChoiceKind(lib.pkmn_result_p2(self._pkmn_result))

    def is_error(self) -> bool:
        """Check if the result is an error.

        Python version of pkmn_error.
        """
        return lib.pkmn_error(self._pkmn_result)
