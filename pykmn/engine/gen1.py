"""Battle simulation for Generation I."""
from _pkmn_engine_bindings import lib, ffi  # type: ignore
from pykmn.engine.common import Result, Player, BattleChoiceType, Softlock, BattleChoice
from pykmn.engine.rng import ShowdownRNG
from pykmn.data.gen1 import Gen1StatData, LIBPKMN_MOVE_IDS, LIBPKMN_SPECIES_IDS, \
    SPECIES, TYPES, MOVES

from typing import List, Tuple
from bitstring import Bits  # type: ignore
import random
from enum import Enum
import math


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

    def _to_bits(self) -> Bits:
        """Pack the move into a bitstring."""
        return Bits(uintne=self.id, length=8)

    def _to_slot_bits(self, pp: int | None = None) -> Bits:
        """Pack the move into a bitstring with PP."""
        if pp is None:
            pp = math.trunc(MOVES[self.name] * 8 / 5)
        return Bits().join([
            self._to_bits(),
            Bits(uintne=pp, length=8)
        ])

    def __repr__(self) -> str:
        """Return a string representation of the move."""
        return f"Move({self.name}, id={self.id})"


def statcalc(
    base_value: int,
    is_HP: bool = False,
    level: int = 100,
    dv: int = 15,
    experience: int = 65535
) -> int:
    """Calculate a Pokémon's stats based on its level, base stats, and so forth.

    Args:
        base_value (int): The base value of the stat for this species.
        dv (int): The Pokémon's DV for this stat.
        level (int): The level of the Pokémon.
        is_HP (bool, optional): Whether the stat is HP or not. Defaults to False.

    Returns:
        int: The value of the stat
    """
    # 64 = std.math.sqrt(exp) / 4 when exp = 65535 (0xFFFF)
    # const core: u32 = (2 *% (@as(u32, base) +% dv)) +% @as(u32, (std.math.sqrt(exp) / 4));
    core = (2 * (base_value + dv)) + math.trunc(math.sqrt(experience) / 4)
    # const factor: u32 = if (std.mem.eql(u8, stat, "hp")) level + 10 else 5;
    factor = (level + 10) if is_HP else 5
    # return @truncate(T, core *% @as(u32, level) / 100 +% factor);
    return (core * math.trunc(level / 100) + factor) % 2**16


# TODO: make all these classes simple wrappers around binary and have staticmethods to generate them
class Pokemon:
    """A Pokémon in a Generation I battle."""

    def __init__(
        self,
        name: str,
        moves: List[Move],
        level: int = 100,
        hp: int | None = None,
        status: Status = Status.healthy(),
        dvs: Gen1StatData = {'hp': 0, 'atk': 0, 'def': 0, 'spc': 0, 'spe': 0},
        experience: Gen1StatData = {
            'hp': 65535, 'atk': 65535, 'def': 65535, 'spc': 65535, 'spe': 65535,
        },
    ):
        """Construct a new Pokemon object.

        Args:
            name (str): The Pokémon's name. Throws an exception if this isn't a valid Pokémon name.
            moves (List[MoveSlot]): The Pokémon's moves. Must be <= 4.
            level (int, optional): The Pokémon's level. Defaults to 100.
            hp (int, optional): The amount of HP the Pokémon has. Defaults to 0.
            status (Status, optional): The Pokémon's status condition. Defaults to Status.Healthy.
        """
        # TODO: do we have to deal with None-species?
        # ha ha left pokemon none species
        if name not in SPECIES and name != 'None':
            raise ValueError(f"'{name}' is not a valid Pokémon name in Generation I.")

        self.stats: Gen1StatData = {'hp': 0, 'atk': 0, 'def': 0, 'spc': 0, 'spe': 0}
        if name != 'None':
            self.types = SPECIES[name]['types']
            for stat in SPECIES[name]['stats']:
                self.stats[stat] = statcalc(  # type: ignore
                    base_value=SPECIES[name]['stats'][stat],  # type: ignore
                    level=level,
                    dv=dvs[stat],  # type: ignore
                    is_HP=stat == 'hp',
                )
        else:
            self.types = ['Normal', 'Normal']

        self.name = name
        self.moves = moves
        self.level = level
        self.hp = self.stats['hp'] if hp is None else hp
        self.status = status

    def _to_bits(self) -> Bits:
        """Pack the Pokémon into a bitstring."""
        first_type = TYPES.index(self.types[0])
        try:
            second_type = TYPES.index(self.types[1])
        except IndexError:
            # this is how single-type Pokémon are represented in libpkmn
            # https://github.com/pkmn/engine/blob/main/src/lib/gen1/data/species.zig#L451-L455
            second_type = first_type  # this

        # TODO: see if we can combine Move + MoveSlot?
        stats = _pack_stats(self.stats)
        bits = Bits().join(
            [stats] + [move._to_slot_bits() for move in self.moves] + [
                Bits(uintne=self.hp, length=16),
                Bits(uintne=self.status.to_int(), length=8),
                Bits(uintne=LIBPKMN_SPECIES_IDS[self.name], length=8),
                Bits(uint=first_type, length=4),
                Bits(uint=second_type, length=4),
                Bits(uintne=self.level, length=8),
            ]
        )

        assert bits.length == 24 * 8, \
            f"Pokemon._to_bits() returned a bitstring of length {bits.length}, expected {24 * 8}"
        return bits


def moves(*args):
    """Convert a list of move names into a list of Move objects."""
    return [Move(move) for move in args]

# MAJOR TODO!
# * fix stat calculation
# * reverse it so that there are _from_bits() methods as well
# * write unit tests
# * make this use raw memory and bit twiddling instead of bitstring
#   * each class's constructor just takes bits and then there's a static method for generation
#   * getters should actually parse the bits
# * make all constructors check array lengths, etc, for validity
# * write a LOT of integration tests
# * maybe more documentation?


class Boosts:
    """A Pokémon's stat boosts."""

    attack: int
    defense: int
    speed: int
    special: int
    accuracy: int
    evasion: int

    def __init__(
        self,
        attack: int = 0,
        defense: int = 0,
        speed: int = 0,
        special: int = 0,
        accuracy: int = 0,
        evasion: int = 0,
    ):
        """Construct a new Boosts object."""
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.special = special
        self.accuracy = accuracy
        self.evasion = evasion

    def _to_bits(self) -> Bits:
        """Pack the boosts into a bitstring."""
        return Bits().join([
            Bits(int=self.attack, length=4),
            Bits(int=self.defense, length=4),
            Bits(int=self.speed, length=4),
            Bits(int=self.special, length=4),
            Bits(int=self.accuracy, length=4),
            Bits(int=self.evasion, length=4),
            Bits(intne=0, length=8),  # padding
        ])


class Volatiles:
    """A Pokémon's volatile statuses."""

    Bide: bool
    Thrashing: bool
    MultiHit: bool
    Flinch: bool
    Charging: bool
    Binding: bool
    Invulnerable: bool
    Confusion: bool

    Mist: bool
    FocusEnergy: bool
    Substitute: bool
    Recharging: bool
    Rage: bool
    LeechSeed: bool
    Toxic: bool
    LightScreen: bool

    Reflect: bool
    Transform: bool

    confusion: int
    attacks: int

    state: int
    substitute: int
    transform: int
    disabled_duration: int
    disabled_move: int
    toxic: int

    def __init__(
        self,
        Bide: bool = False,
        Thrashing: bool = False,
        MultiHit: bool = False,
        Flinch: bool = False,
        Charging: bool = False,
        Binding: bool = False,
        Invulnerable: bool = False,
        Confusion: bool = False,
        Mist: bool = False,
        FocusEnergy: bool = False,
        Substitute: bool = False,
        Recharging: bool = False,
        Rage: bool = False,
        LeechSeed: bool = False,
        Toxic: bool = False,
        LightScreen: bool = False,
        Reflect: bool = False,
        Transform: bool = False,
        confusion: int = 0,
        attacks: int = 0,
        state: int = 0,
        substitute: int = 0,
        transform: int = 0,
        disabled_duration: int = 0,
        disabled_move: int = 0,
        toxic: int = 0,
    ):
        """Construct a new Volatiles object."""
        self.Bide = Bide
        self.Thrashing = Thrashing
        self.MultiHit = MultiHit
        self.Flinch = Flinch
        self.Charging = Charging
        self.Binding = Binding
        self.Invulnerable = Invulnerable
        self.Confusion = Confusion
        self.Mist = Mist
        self.FocusEnergy = FocusEnergy
        self.Substitute = Substitute
        self.Recharging = Recharging
        self.Rage = Rage
        self.LeechSeed = LeechSeed
        self.Toxic = Toxic
        self.LightScreen = LightScreen
        self.Reflect = Reflect
        self.Transform = Transform
        self.confusion = confusion
        self.attacks = attacks
        self.state = state
        self.substitute = substitute
        self.transform = transform
        self.disabled_duration = disabled_duration
        self.disabled_move = disabled_move
        self.toxic = toxic

    def _to_bits(self) -> Bits:
        """Pack the volatiles into a bitstring."""
        bits = Bits().join([
            Bits(bool=self.Bide),
            Bits(bool=self.Thrashing),
            Bits(bool=self.MultiHit),
            Bits(bool=self.Flinch),
            Bits(bool=self.Charging),
            Bits(bool=self.Binding),
            Bits(bool=self.Invulnerable),
            Bits(bool=self.Confusion),
            Bits(bool=self.Mist),
            Bits(bool=self.FocusEnergy),
            Bits(bool=self.Substitute),
            Bits(bool=self.Recharging),
            Bits(bool=self.Rage),
            Bits(bool=self.LeechSeed),
            Bits(bool=self.Toxic),
            Bits(bool=self.LightScreen),
            Bits(bool=self.Reflect),
            Bits(bool=self.Transform),

            Bits(uint=self.confusion, length=3),
            Bits(uint=self.attacks, length=3),
            Bits(uintne=self.state, length=16),
            Bits(uintne=self.substitute, length=8),
            Bits(uint=self.transform, length=4),
            Bits(uint=self.disabled_duration, length=4),
            Bits(uint=self.disabled_move, length=3),
            Bits(uint=self.toxic, length=5),
        ])
        assert bits.length == 8 * 8, \
            f"Volatiles is {bits.length} bits long, but should be 64 bits long."
        return bits


# class ActivePokemon:
#     """idk anymore."""

#     stats: Gen1StatData
#     boosts: Boosts
#     volatiles: Volatiles
#     # int is the amount of PP they have left
#     moveslots: List[MoveSlot]

#     def __init__(
#         self,
#         name: str,
#         boosts: Boosts = Boosts(),
#         volatiles: Volatiles = Volatiles(),
#         moveslots=[(Move('None'), 0)] * 4,
#     ):
#         """Construct a new ActivePokemon object."""
#         if name not in SPECIES and name != 'None':
#             raise Exception(f"'{name}' is not a valid Pokémon name in Generation I.")

#         self.stats: Gen1StatData = {'hp': 0, 'atk': 0, 'def': 0, 'spc': 0, 'spe': 0}
#         if name != 'None':
#             self.types = SPECIES[name]['types']
#             for stat in SPECIES[name]['stats']:
#                 self.stats[stat] = statcalc(  # type: ignore
#                     base_value=SPECIES[name]['stats'][stat],  # type: ignore
#                     level=level,
#                     dv=dvs[stat],  # type: ignore
#                     is_HP=stat == 'hp',
#                 )
#         else:
#             self.types = ['Normal', 'Normal']

#         self.boosts = boosts
#         self.volatiles = volatiles
#         self.moveslots = moveslots


class Side:
    """A side in a Generation I battle."""

    team: List[Pokemon]
    # active: ActivePokemon
    order: List[int]
    last_selected_move: Move
    last_used_move: Move

    def __init__(
        self,
        team: List[Pokemon],
        # active: ActivePokemon | None = None,
        order: List[int] = [0, 0, 0, 0, 0, 0],
        last_selected_move: Move = Move('None'),
        last_used_move: Move = Move('None'),
    ):
        """Construct a new Side object.

        Args:
            team (List[Pokemon]): The Pokémon on the side.
            order (List[int]): The order of the Pokémon on the side.
            last_selected_move (Move): The last move selected by the player.
            last_used_move (Move): The last move used by the player.
        """
        assert len(order) == 6, f"Order must be 6, not {len(order)}, elements long."
        self.team = team
        # self.active = active
        self.order = order
        self.last_selected_move = last_selected_move
        self.last_used_move = last_used_move

    def _to_bits(self) -> Bits:
        """
        Pack the side data into a bitstring.

        Use the Battle() constructor instead.
        """
        bits = Bits().join(
            [pokemon._to_bits() for pokemon in self.team] +  # 6 Pokemon
            # an all-zeroes region to be later replaced with ActivePokemon
            [Bits(uint=0, length=32 * 8)] +
            [Bits(uintne=n, length=8) for n in self.order] + [  # order: 6 u8s
                self.last_selected_move._to_bits(),
                self.last_used_move._to_bits(),
            ]
        )
        assert bits.length == 184 * 8, f"Side length is {bits.length} bits, not {184 * 8} bits."
        return bits


def _pack_stats(stats: Gen1StatData) -> Bits:
    """
    Pack the stats into a bitstring.

    Use the Battle() constructor instead.
    """
    bits = Bits().join([
        Bits(uintne=stats['hp'], length=16),
        Bits(uintne=stats['atk'], length=16),
        Bits(uintne=stats['def'], length=16),
        Bits(uintne=stats['spe'], length=16),
        Bits(uintne=stats['spc'], length=16),
    ])
    assert bits.length == 10 * 8, f"Stats length is {bits.length} bits, not {10 * 8} bits."
    return bits


def _pack_move_indexes(p1: int, p2: int) -> List[Bits]:
    """
    Pack the move indexes into a bitstring.

    Use the Battle() constructor instead.
    """
    length = 16  # TODO: support non -Dshowdown here
    return Bits().join([
        Bits(uintne=p1, length=length),
        Bits(uintne=p2, length=length),
    ])


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
        battle_data = Bits().join([
            p2_side._to_bits(),                             # side 1
            p2_side._to_bits(),                             # side 2
            Bits(uintne=start_turn, length=16),     # turn
            Bits(uintne=last_damage, length=16),    # last damage
            _pack_move_indexes(p1_move_idx, p2_move_idx),   # move indices
            rng._to_bits(),                                 # rng
        ])
        # gbattle_data.ad
        assert battle_data.length == (lib.PKMN_GEN1_BATTLE_SIZE * 8), (
            f"The battle data should be {lib.PKMN_GEN1_BATTLE_SIZE * 8} bits long, "
            f"but it's {battle_data.length} bits long."
        )
        # uintne == unsigned integer, native endian
        self._pkmn_battle = ffi.new("pkmn_gen1_battle*")
        self._pkmn_battle.bytes = battle_data.tobytes()

    def update(self, p1_choice: BattleChoice, p2_choice: BattleChoice) -> Tuple[Result, List[int]]:
        """Update the battle with the given choice.

        Args:
            choice (BattleChoice): The choice to make.

        Returns:
            Tuple[Result, List[int]]: The result of the choice,
            and the trace as a list of protocol bytes
        """
        # TODO: protocol parser?
        trace_buf = ffi.new("uint8_t[]", lib.PKMN_GEN1_LOG_SIZE)
        _pkmn_result = lib.pkmn_gen1_battle_update(
            self._pkmn_battle,          # pkmn_gen1_battle *battle
            p1_choice._pkmn_choice,     # pkmn_choice c1
            p2_choice._pkmn_choice,     # pkmn_choice c2
            trace_buf,                  # uint8_t *buf
            lib.PKMN_GEN1_LOG_SIZE,     # size_t len
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
        return (result, trace_buf)

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
