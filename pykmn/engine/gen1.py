"""Battle simulation for Generation I."""
from _pkmn_engine_bindings import lib, ffi  # type: ignore
from pykmn.engine.common import Result, Player, BattleChoiceType, Softlock, BattleChoice

from typing import List


class Battle:
    """A Generation I Pokémon battle."""

    def __init__(self):
        """Create a new Battle object."""
        # TODO: figure out how to initialize this; it seems like it's not just a binding:
        # https://github.com/pkmn/engine/blob/main/src/examples/c/example.c#L50-L53
        # also need unit tests!
        self._pkmn_battle = ffi.new("pkmn_gen1_battle*")

    def update(self, p1_choice: BattleChoice, p2_choice: BattleChoice) -> Result:
        """Update the battle with the given choice.

        Args:
            choice (BattleChoice): The choice to make.

        Returns:
            Result: The result of the choice.
        """
        # TODO: trace?
        _pkmn_result = lib.pkmn_gen1_battle_update(
            self._pkmn_battle,  # pkmn_gen1_battle *battle
            p1_choice._pkmn_choice,          # pkmn_choice c1
            p2_choice._pkmn_choice,          # pkmn_choice c2
            ffi.NULL,           # uint8_t *buf
            0,                  # size_t len
        )

        result = Result(_pkmn_result)
        if result.is_error():
            # per pkmn.h:
            # This can only happen if libpkmn was built with trace logging enabled and the buffer
            # provided to the update function was not large  enough to hold all of the data
            # (which is only possible if the buffer being used was smaller than the
            # generation in question's MAX_LOGS bytes).
            raise Exception(
                "An error was thrown in libpkmn while updating the battle. " +
                "This should never happen; please file a bug report with PYkmn at " +
                "https://github.com/AnnikaCodes/PYkmn/issues/new"
            )
        return result

    def possible_choices(
        self,
        player: Player,
        requested_kind: BattleChoiceType,
    ) -> List[BattleChoice]:
        """Get the possible choices for the given player.

        Args:
            player (Player): The player to get choices for.
            requested_kind (BattleChoiceKind): The kind of choice to get.

        Returns:
            List[BattleChoice]: The possible choices.
        """
        raw_choices = ffi.new("pkmn_choice[]", lib.PKMN_OPTIONS_SIZE)
        num_choices = lib.pkmn_gen1_battle_choices(
            self._pkmn_battle,      # pkmn_gen1_battle *battle
            player.value,           # pkmn_player player
            requested_kind.value,   # pkmn_choice_kind request
            raw_choices,            # pkmn_choice out[]
            lib.PKMN_OPTIONS_SIZE,  # size_t len
        )

        if num_choices == 0:
            raise Softlock("Zero choices are available.")

        choices: List[BattleChoice] = []
        for i in range(num_choices):
            choices.append(BattleChoice(raw_choices[i]))

        return choices
