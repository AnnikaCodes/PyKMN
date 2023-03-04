"""Battle simulation for Generation I."""
from _pkmn_engine_bindings import lib, ffi  # type: ignore
from pykmn.engine.common import Result, Player, BattleChoiceType, Softlock, BattleChoice
from pykmn.engine.rng import ShowdownRNG
from pykmn.data.gen1 import Gen1StatData, LIBPKMN_MOVE_IDS, LIBPKMN_SPECIES_IDS, SPECIES, TYPES

from typing import List, Tuple
import bitstring  # type: ignore
import random
from enum import Enum


class _InnerStatusEnum(Enum):
    HEALTHY = 0
    SLEEP = 4
    POISON = 8
    BURN = 16
    FREEZE = 32
    PARALYSIS = 64


class Status:
    """A Pokémon's status condition."""

    value: _InnerStatusEnum
    duration: int | None
    is_self_inflicted: bool | None

    # Tuple is for sleep, (duration, is_self_inflicted)
    def __init__(self, value: _InnerStatusEnum | Tuple[int, bool]):
        """Create a new Status object."""
        if isinstance(value, tuple):
            self.value = _InnerStatusEnum.SLEEP
            self.duration = value[0]
            self.is_self_inflicted = value[1]
        else:
            self.value = value
            self.duration = None
            self.is_self_inflicted = None

    @staticmethod
    def paralyzed():
        """Return a Status object for paralysis."""
        return Status(_InnerStatusEnum.PARALYSIS)

    @staticmethod
    def burned():
        """Return a Status object for burn."""
        return Status(_InnerStatusEnum.BURN)

    @staticmethod
    def poisoned():
        """Return a Status object for poison."""
        return Status(_InnerStatusEnum.POISON)

    @staticmethod
    def frozen():
        """Return a Status object for freeze."""
        return Status(_InnerStatusEnum.FREEZE)

    @staticmethod
    def healthy():
        """Return a Status object for healthy."""
        return Status(_InnerStatusEnum.HEALTHY)

    @staticmethod
    def sleep(duration: int, is_self_inflicted: bool):
        """Return a Status object for sleep."""
        return Status((duration, is_self_inflicted))

    def to_int(self) -> int:
        """Convert to int for libpkmn."""
        if self.duration is not None:
            return (0x80 | self.duration) if self.is_self_inflicted else self.duration
        return self.value.value


# should this not be a class and just a move-to-int function?
class Move:
    """A Pokémon move."""

    def __init__(self, name: str):
        """Create a new Move object."""
        if name not in LIBPKMN_MOVE_IDS:
            raise ValueError(f"'{name}' is not a valid move in Generation I.")
        self.name = name
        self.id = LIBPKMN_MOVE_IDS[name]

    def _to_bits(self) -> bitstring.Bits:
        """Pack the move into a bitstring."""
        return bitstring.Bits(uint=self.id, length=8)

    def __repr__(self) -> str:
        """Return a string representation of the move."""
        return f"Move({self.name}, id={self.id})"


class Pokemon:
    """A Pokémon in a Generation I battle."""

    def __init__(
        self,
        name: str,
        moves: List[Move],
        level: int = 100,
        hp: int = 0,
        status: Status = Status.healthy(),
    ):
        """Construct a new Pokemon object.

        Args:
            name (str): The Pokémon's name. Throws an exception if this isn't a valid Pokémon name.
            moves (List[Move]): The Pokémon's moves. Must be <= 4.
            level (int, optional): The Pokémon's level. Defaults to 100.
            hp (int, optional): The amount of HP the Pokémon has. Defaults to 0.
            status (Status, optional): The Pokémon's status condition. Defaults to Status.Healthy.
        """
        # TODO: do we have to deal with None-species?
        # ha ha left pokemon none species
        if name not in SPECIES:
            raise ValueError(f"'{name}' is not a valid Pokémon name in Generation I.")
        data = SPECIES[name]

        self.stats = data['stats']
        self.types = data['types']
        self.name = name
        self.moves = moves
        self.level = level
        self.hp = hp
        self.status = status

    def _to_bits(self) -> bitstring.Bits:
        """Pack the Pokémon into a bitstring."""
        try:
            second_type = TYPES.index(self.types[1])
        except ValueError:
            second_type = ffi.NULL

        return bitstring.Bits().join(
            [_pack_stats(self.stats)] + [move._to_bits() for move in self.moves] + [
                bitstring.Bits(uint=self.hp, length=16),
                bitstring.Bits(uint=self.status.to_int(), length=8),
                bitstring.Bits(uint=LIBPKMN_SPECIES_IDS[self.name], length=8),  # +1 for None=0
                bitstring.Bits(uint=TYPES.index(self.types[0]), length=4),
                bitstring.Bits(uint=second_type, length=4),
                bitstring.Bits(uint=self.level, length=8),
            ]
        )

# MAJOR TODO!
# * implement ActivePokemon
# * make all constructors check array lengths, etc, for validity
# * write unit tests
# * write a LOT of integration tests
# * maybe more documentation?


class ActivePokemon:
    """idk anymore."""

    stats: Gen1StatData
    boosts: Boosts
    volatiles: Volatiles
    moves: MoveSlot

    def __init__(self, name: str):
        """Construct a new ActivePokemon object."""
        if name not in SPECIES and name != 'None':
            raise Exception(f"'{name}' is not a valid Pokémon name in Generation I.")
        self.name = name
        if name != 'None':
            self.stats = SPECIES[name]['stats']
            self.types = SPECIES[name]['types']
        else:
            self.stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}
            # this is the None-type
            # https://github.com/pkmn/engine/blob/main/src/lib/gen1/data/types.zig#L107-L108
            self.types = ['Normal', 'Normal']

    def _to_bits(self) -> bitstring.Bits:
        """Pack the active Pokémon into a bitstring."""
        try:
            second_type = TYPES.index(self.types[1])
        except ValueError:
            second_type = ffi.NULL

        return bitstring.Bits().join([
            _pack_stats(self.stats),
            bitstring.Bits(uint=LIBPKMN_SPECIES_IDS[self.name], length=8),
            bitstring.Bits(uint=TYPES.index(self.types[0]), length=4),
            bitstring.Bits(uint=second_type, length=4),
            # TODO
        ])


class Side:
    """A side in a Generation I battle."""

    team: List[Pokemon]
    active: ActivePokemon
    order: List[int]
    last_selected_move: Move
    last_used_move: Move

    def __init__(
        self,
        team: List[Pokemon],
        active: ActivePokemon = ActivePokemon('None'),
        order: List[int] = [0, 0, 0, 0, 0, 0],
        last_selected_move: Move = Move('None'),
        last_used_move: Move = Move('None'),
    ):
        """Construct a new Side object.

        Args:
            team (List[Pokemon]): The Pokémon on the side.
            active (ActivePokemon): The active Pokémon on the side.
            order (List[int]): The order of the Pokémon on the side.
            last_selected_move (Move): The last move selected by the player.
            last_used_move (Move): The last move used by the player.
        """
        assert len(order) == 6, f"Order must be 6, not {len(order)}, elements long."
        self.team = team
        self.active = active
        self.order = order
        self.last_selected_move = last_selected_move
        self.last_used_move = last_used_move

    def _to_bits(self) -> bitstring.Bits:
        """
        Pack the side data into a bitstring.

        Use the Battle() constructor instead.
        """
        bits = bitstring.Bits().join(
            [pokemon._to_bits() for pokemon in self.team] +  # 6 Pokemon
            [self.active._to_bits()] +  # ActivePokemon
            [bitstring.Bits(uint=n, length=8) for n in self.order] +  # order: 6 u8s
            self.last_selected_move._to_bits() +
            self.last_used_move._to_bits()
        )
        assert bits.length == 184 * 8, f"Side length is {bits.length} bits, not {184 * 8} bits."
        return bits


def _pack_stats(stats: Gen1StatData) -> bitstring.Bits:
    """
    Pack the stats into a bitstring.

    Use the Battle() constructor instead.
    """
    return bitstring.Bits().join([
        bitstring.Bits(uint=stats['hp'], length=16),
        bitstring.Bits(uint=stats['atk'], length=16),
        bitstring.Bits(uint=stats['def'], length=16),
        bitstring.Bits(uint=stats['spe'], length=16),
        bitstring.Bits(uint=stats['spc'], length=16),
    ])


def _pack_move_indexes(p1: int, p2: int) -> List[bitstring.Bits]:
    """
    Pack the move indexes into a bitstring.

    Use the Battle() constructor instead.
    """
    length = 4  # TODO: support -Dshowdown here
    return [
        bitstring.Bits(uint=p1, length=length),
        bitstring.Bits(uint=p2, length=length),
    ]


class Battle:
    """A Generation I Pokémon battle."""

    def __init__(
        self,
        p1_side: Side,
        p2_side: Side,
        start_turn: int = 0,
        last_damage: int = 0,
        p1_move_idx: int = 0,
        p2_move_idx: int = 0,
        # TODO: support non-Showdown RNGs
        rng: ShowdownRNG = ShowdownRNG(random.randrange(0, 2**64)),
    ):
        """Create a new Battle object."""
        # TODO: unit tests!
        # TODO: verify initial values
        # OK, let's initialize a battle.
        # https://github.com/pkmn/engine/blob/main/src/data/layout.json gives us the layout.
        # https://github.com/pkmn/engine/blob/main/src/lib/gen1/data.zig#L40-L48 also
        battle_data = bitstring.Bits().join([
            p2_side._to_bits(),                             # side 1
            p2_side._to_bits(),                             # side 2
            bitstring.Bits(uint=start_turn, length=16),     # turn
            bitstring.Bits(uint=last_damage, length=16),    # last damage
            _pack_move_indexes(p1_move_idx, p1_move_idx),   # move indices
            rng._to_bits(),                                 # rng
        ])
        # gbattle_data.ad
        assert battle_data.length == (lib.PKMN_GEN1_BATTLE_SIZE * 8), (
            f"The battle data should be {lib.PKMN_GEN1_BATTLE_SIZE * 8} bits long, "
            f"but it's {battle_data.length} bits long."
        )
        # uintne == unsigned integer, native endian
        self._pkmn_battle = ffi.new("pkmn_gen1_battle*", battle_data.uintne)

    @staticmethod
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
