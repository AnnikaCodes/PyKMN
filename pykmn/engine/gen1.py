"""This is the core of PyKMN's functionality.

It simulates Gen 1 Pokémon battles; the `Battle` class is where you'll want to start.
"""
from pykmn.engine.libpkmn import libpkmn_showdown_trace, LibpkmnBinding
from pykmn.engine.common import Result, Player, ChoiceType, Softlock, Choice, \
    pack_u16_as_bytes, unpack_u16_from_bytes, pack_two_u4s, unpack_two_u4s, \
    pack_two_i4s, unpack_two_i4s, insert_unsigned_int_at_offset, extract_unsigned_int_at_offset \
    # noqa: F401
from pykmn.engine.rng import ShowdownRNG
from pykmn.data.gen1 import Gen1StatData, MOVE_IDS, SPECIES_IDS, PartialGen1StatData, \
    SPECIES, TYPES, MOVES, LAYOUT_OFFSETS, LAYOUT_SIZES, MOVE_ID_LOOKUP, SPECIES_ID_LOOKUP

from typing import cast, TypedDict, Literal, Union, List, Tuple, NewType
from typing import Sequence # noqa: UP035
from enum import IntEnum
from collections import namedtuple
import math
import random

class Status:
    """Represents a Pokémon's status.

    You can get a `Status` from the `Battle.status` method, or by calling one of the static
    methods:

    * `Status.HEALTHY()` to get a `Status` for a healthy Pokémon
    * `Status.SLEEP()` to get a `Status` for a sleeping Pokémon
    * `Status.POISONED()` to get a `Status` for a poisoned Pokémon
    * `Status.BURNED()` to get a `Status` for a burned Pokémon
    * `Status.FROZEN()` to get a `Status` for a frozen Pokémon
    * `Status.PARALYZED()` to get a `Status` for a paralyzed Pokémon
    * `Status.SELF_INFLICTED_SLEEP()` to get a `Status` for a self-inflicted sleep (used to track
       Smogon's [Sleep Clause](https://www.smogon.com/dex/rb/formats/ou/))

    """
    _SLP = 2
    _PSN = 3
    _BRN = 4
    _FRZ = 5
    _PAR = 6

    def __init__(self, raw_status: int) -> None:
        """Creates a new Status object.

        **PyKMN library consumers should use the static methods described in `Status` documentation
        to create Status objects instead**;
        this constructor takes a raw value from `libpkmn`.`

        Args:
            raw_status (`int`): The raw status value from libpkmn.
        """
        self._value = raw_status

    def asleep(self) -> bool:
        """Returns whether this `Status` represents sleep.

        Returns:
            **`bool`**: `True` if this `Status` represents sleep, and `False` otherwise.
        """
        return self.sleep_duration() != 0

    def sleep_duration(self) -> int:
        """Returns the number of turns the Pokémon will be asleep for.

        Returns 0 if this `Status` isn't a sleep status.

        Returns:
            **`int`**: The number of turns the Pokémon will be asleep for.
        """
        return self._value & 0b111

    def healthy(self) -> bool:
        """Returns whether this `Status` represents healthy state (no state).

        Returns:
            **`bool`**: `True` if this `Status` represents a healthy state, and `False` otherwise.
        """
        return self._value == 0

    def burned(self) -> bool:
        """Returns whether this `Status` represents a burn.

        Returns:
            **`bool`**: `True` if this `Status` represents a burn, and `False` otherwise.
        """
        return ((self._value >> Status._BRN) & 1) != 0

    def frozen(self) -> bool:
        """Returns whether this `Status` represents freeze.

        Returns:
            **`bool`**: `True` if this `Status` represents freeze, and `False` otherwise.
        """
        return ((self._value >> Status._FRZ) & 1) != 0

    def paralyzed(self) -> bool:
        """Returns whether this `Status` represents paralysis.

        Returns:
            **`bool`**: `True` if this `Status` represents paralysis, and `False` otherwise.
        """
        return ((self._value >> Status._PAR) & 1) != 0

    def poisoned(self) -> bool:
        """Returns whether this `Status` represents poisoning.

        Returns:
            **`bool`**: `True` if this `Status` represents poisoning, and `False` otherwise.
        """
        return ((self._value >> Status._PSN) & 1) != 0

    @staticmethod
    def SLEEP(duration: int) -> "Status":
        """Returns the raw status value for a sleeping Pokémon.

        Args:
            duration (`int`): The duration of the sleep.

        Returns:
            **`Status`**: The Status
        """
        return Status(duration)

    @staticmethod
    def HEALTHY() -> "Status":
        """Returns the raw status value for a healthy Pokémon.

        Returns:
            **`Status`**: _description_
        """
        return Status(0)

    @staticmethod
    def POISONED() -> "Status":
        """Returns the raw status value for a poisoned Pokémon.

        Returns:
            **`Status`**: _description_
        """
        return Status(1 << Status._PSN)

    @staticmethod
    def BURNED() -> "Status":
        """Returns the raw status value for a burned Pokémon.

        Returns:
            **`Status`**: _description_
        """
        return Status(1 << Status._BRN)

    @staticmethod
    def FROZEN() -> "Status":
        """Returns the raw status value for a frozen Pokémon.

        Returns:
            **`Status`**: _description_
        """
        return Status(1 << Status._FRZ)

    @staticmethod
    def PARALYZED() -> "Status":
        """Returns the raw status value for a paralyzed Pokémon.

        Returns:
            **`Status`**: _description_
        """
        return Status(1 << Status._PAR)

    @staticmethod
    def SELF_INFLICTED_SLEEP(duration: int) -> "Status":
        """Returns the raw status value for a self-inflicted sleep.

        Args:
            duration (`int`): The duration of the sleep.

        Returns:
            **`Status`**: _description_
        """
        return Status(0x80 | duration)

    def __repr__(self) -> str:
        """Returns a human-readable representation of the status.

        Returns:
            **`str`**: A human-readable representation of the status.
        """
        if self.burned():
            return "Status(burned)"
        elif self.frozen():
            return "Status(frozen)"
        elif self.paralyzed():
            return "Status(paralyzed)"
        elif self.poisoned():
            return "Status(poisoned)"
        elif self.healthy():
            return "Status(healthy)"
        else:
            sleep_duration = self.sleep_duration()
            return f"Status(sleeping for {sleep_duration} turns)"

# optimization possible here: don't copy in intialization if it's all 0 anyway?
# optimization possible: use indices for LAYOUT_* instead of dict keys

# enum-izing moves only brings us from 822 battles/sec to 816

MovePP = NewType('MovePP', Tuple[str, int])
"""A `(move name, PP left)` tuple."""
FullMoveset = Tuple[str, str, str, str]
"""The full 4-move moveset of a Pokémon."""
Moveset = Union[FullMoveset, Tuple[str], Tuple[str, str], Tuple[str, str, str]]
"""A Pokémon's moveset, which can be a tuple of move names of any length in [1, 4]."""
SpeciesName = str
"""The name of a Pokémon species."""

class ExtraPokemon(TypedDict, total=False):
    """A dictionary containing extra, optional data about a Pokémon.

    The following keys may be specified, but are all optional:
    * `'hp'` (**`int`**): The Pokémon's current HP. Defaults to the Pokémon's maximum HP.
    * `'status'` (**`Status`**): The Pokémon's status condition, if any. Defaults to no status.
    * `'level'` (**`int`**): The Pokémon's level. Defaults to `100`.
    * `'stats'` (**`pykmn.data.loader.Gen1StatData`**): The Pokémon's stats.
        Defaults are calculated with `statcalc` from the Pokémon's base stats.
    * `'types'` (**`Tuple[str, str]`**): The Pokémon's types.
        Defaults to the Pokémon's species' types.
    * `'move_pp'` (**`Tuple[int, int, int, int]`**): The PP of each of the Pokémon's moves.
       Defaults to the maximum PP (with PP Ups) of each move.
    * `'dvs'` (**`pykmn.data.loader.Gen1StatData`**): The Pokémon's DVs.
        Defaults to 15 in each stat.
    * `'exp'` (**`pykmn.data.loader.Gen1StatData`**): The Pokémon's stat experience.
       Defaults to 65535 in each stat.
    """
    hp: int
    status: Status
    level: int
    stats: Gen1StatData
    types: Tuple[str, str]
    move_pp: Tuple[int, int, int, int]
    dvs: Gen1StatData
    exp: Gen1StatData

Pokemon = namedtuple('Pokemon', ['species', 'moves', 'extra'], defaults=[None])
"""The data data for a Pokémon.

Optionally, an `ExtraPokemon` dictionary can be specified for the `extra` element.

Examples:
```python
pikachu = Pokemon((
    species='Pikachu',
    moves=('Thunderbolt', 'Thunder', 'Quick Attack', 'Growl')
)
mew = Pokemon((
    species='Mew',
    moves=('Psychic', 'Recover'),
    extra={'level': 63, 'status': Status.PARALYZED()}
))
```
"""


# TODO: should this be an IntEnum?
class Slot(IntEnum):
    """A Pokémon slot, which can be any integer in [1, 6]."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6

BoostData = TypedDict('BoostData', {
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
    'accuracy': int,
    'evasion': int,
}) # optimization: is a namedtuple/class faster than a dict?
"""A dictionary representing a Pokémon's stat boosts.
Returned from `Battle.boosts()`.

The following keys are present:
* `'atk'` (**`int`**): The Pokémon's Attack stat stage boosts, as an integer in [-6, 6].
* `'def'` (**`int`**): The Pokémon's Defense stat stage boosts, as an integer in [-6, 6].
* `'spe'` (**`int`**): The Pokémon's Speed stat stage boosts, as an integer in [-6, 6].
* `'spc'` (**`int`**): The Pokémon's Special stat stage boosts, as an integer in [-6, 6].
* `'accuracy'` (**`int`**): The Pokémon's accuracy stat stage boosts, as an integer in [-6, 6].
* `'evasion'` (**`int`**): The Pokémon's evasion stat stage boosts, as an integer in [-6, 6].
"""

PartialBoostData = TypedDict('PartialBoostData', {
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
    'accuracy': int,
    'evasion': int,
}, total=False)
"""Like `BoostData`, but with all keys optional,
so you can specify only the stats you want to change to `Battle.set_boosts()`.

Example:
```python
from pykmn.engine.common import Player

# `battle` is a `Battle` object where Player 1 has +1 to Speed
print(battle.boosts(Player.P1))
# {'atk': 0, 'def': 0, 'spe': 1, 'spc': 0, 'accuracy': 0, 'evasion': 0}

battle.set_boosts(Player.P1, {'atk': -2})
print(battle.boosts(Player.P1))
# {'atk': -2, 'def': 0, 'spe': 1, 'spc': 0, 'accuracy': 0, 'evasion': 0}
```
"""

DisableData = namedtuple('DisableData', ['move_slot', 'turns_left'])
"""Represents information about a Pokémon's Disabled move."""
DisableData.move_slot.__doc__ = """The slot of the move that's been Disabled."""
DisableData.turns_left.__doc__ = \
    """The number of turns left until the Disabled move is usable again."""

class VolatileFlag(IntEnum):
    """Flags for Pokémon's volatile statuses.

    These status afflictions disappear when the Pokémon switches out.
    """
    Bide = LAYOUT_OFFSETS['Volatiles']['Bide']
    """Flag for when the move Bide is active."""
    Thrashing = LAYOUT_OFFSETS['Volatiles']['Thrashing']
    """Flag for when a Pokémon is 'thrashing about'."""
    MultiHit = LAYOUT_OFFSETS['Volatiles']['MultiHit']
    Flinch = LAYOUT_OFFSETS['Volatiles']['Flinch']
    """Flag for when a Pokémon flinched."""
    Charging = LAYOUT_OFFSETS['Volatiles']['Charging']
    """Flag for when a Pokémon is charging power for a 2-turn move."""
    Binding = LAYOUT_OFFSETS['Volatiles']['Binding']
    Invulnerable = LAYOUT_OFFSETS['Volatiles']['Invulnerable']
    Confusion = LAYOUT_OFFSETS['Volatiles']['Confusion']
    """Flag for when a Pokémon is confused."""
    Mist = LAYOUT_OFFSETS['Volatiles']['Mist']
    """Flag for when a Pokémon is protected by Mist."""
    FocusEnergy = LAYOUT_OFFSETS['Volatiles']['FocusEnergy']
    """Flag for when a Pokémon is under the effect of Focus Energy."""
    Substitute = LAYOUT_OFFSETS['Volatiles']['Substitute']
    """Flag for when a Pokémon has a Substitute."""
    Recharging = LAYOUT_OFFSETS['Volatiles']['Recharging']
    """Flag for when a Pokémon is recharging after a move."""
    Rage = LAYOUT_OFFSETS['Volatiles']['Rage']
    """Flag for when a Pokémon is Rage-ing."""
    LeechSeed = LAYOUT_OFFSETS['Volatiles']['LeechSeed']
    """Flag for when a Pokémon has been seeded by Leech Seed."""
    Toxic = LAYOUT_OFFSETS['Volatiles']['Toxic']
    """Flag for when a Pokémon is badly poisoned."""
    LightScreen = LAYOUT_OFFSETS['Volatiles']['LightScreen']
    """Flag for when a Pokémon is protected by Light Screen."""
    Reflect = LAYOUT_OFFSETS['Volatiles']['Reflect']
    """Flag for when a Pokémon is protected by Reflect."""
    Transform = LAYOUT_OFFSETS['Volatiles']['Transform']
    """Flag for when a Pokémon has Transformed."""

def statcalc(
    base_value: int,
    is_HP: bool = False,
    level: int = 100,
    dv: int = 15,
    experience: int = 65535
) -> int:
    """Calculate a Pokémon's stats in Gen I based on its level, base stats, and so forth.

    This function is based on the
    [formula used by libpkmn](https://github.com/pkmn/engine/blob/48372d4ae7474a78b06a248f35d2763fc6d421f6/src/lib/gen1/data.zig#L411-L418).

    Args:
        base_value (`int`): The base value of the stat for this species.
        is_HP (`bool`, optional): Whether the stat is HP (Hit Points) or not. Defaults to `False`.
        level (`int`): The level of the Pokémon.
        dv (`int`): The Pokémon's DV for this stat.
        experience (`int`): The Pokémon's stat experience for this stat.

    Returns:
        **`int`**: The calculated value of the stat.
    """ # noqa: E501 (for the link)
    evs = min(255, math.ceil(math.sqrt(experience)))
    core = (2 * (base_value + dv)) + (evs // 4)
    factor = (level + 10) if is_HP else 5
    return int(((core * level) // 100) + factor) % 2**16

# MAJOR TODO!
# * make all constructors check array lengths, etc, for validity
# * write a LOT of integration tests
# * investigate performance and optimize

Gen1RNGSeed = List[int]
"""The RNG seed used for non-Showdown-compatible RNG in Generation I.

It should be a list of 4 16-bit unsigned integers. You only need to use this if you're using an
alternate `pykmn.engine.libpkmn.LibpkmnBinding` that doesn't have Showdown compatibility mode.
"""

class Battle:
    """A Generation I Pokémon battle.

    The most important methods here are `possible_choices()` and `update()`;
    all the others are either for increased performance or managing the battle state.
    """

    def __init__(
        self,
        p1_team: Sequence[Pokemon],
        p2_team: Sequence[Pokemon],
        p1_last_selected_move: str = 'None',
        p1_last_used_move: str = 'None',
        p2_last_selected_move: str = 'None',
        p2_last_used_move: str = 'None',
        start_turn: int = 0,
        last_damage: int = 0,
        p1_move_idx: int = 0,
        p2_move_idx: int = 0,
        rng_seed: Union[int, Gen1RNGSeed, None] = None,
        libpkmn: LibpkmnBinding = libpkmn_showdown_trace,
    ) -> None:
        """Creates a new Gen I `Battle` object.

        The only required parameters are `p1_team` and `p2_team`, which are both
        lists of `Pokemon` — you must provide at least 1 and not more than 6 elements in each.

        All the other parameters have sensible defaults, but can be specified to preconfigure
        the battle state to your liking.

        You can specify an alternate `pykmn.engine.libpkmn.LibpkmnBinding`
        via the `libpkmn` parameter; that module's documentation has more information,
        but essentially you can use this to turn off protocol logging (for better performance)
        or to enable cartridge compatibility (instead of Pokémon Showdown compatibility).

        Args:
            p1_team (`Sequence[pykmn.engine.gen1.Pokemon]`): Player 1's team.
            p2_team (`Sequence[pykmn.engine.gen1.Pokemon]`): Player 2's team.
            p1_last_selected_move (`str`, optional):
              Player 1's last selected move. Defaults to none.
            p1_last_used_move (`str`, optional):
              Player 1's last used move. Defaults to none.
            p2_last_selected_move (`str`, optional):
              Player 2's last selected move. Defaults to none.
            p2_last_used_move (`str`, optional): Player 2's last used move. Defaults to none.
            start_turn (`int`, optional): The turn the battle starts on.
                Defaults to `0` (i.e. before players send out their Pokémon),
            last_damage (`int`, optional): The last damage dealt in the battle.
            p1_move_idx (`int`, optional): The last move index selected by Player 1.
            p2_move_idx (`int`, optional): The last move index selected by Player 2.
            rng_seed (`int`, optional): The seed to initialize the battle's RNG with.
                Defaults to a random seed.
                If a non-Showdown-compatible libpkmn is provided,
                you must provide a list of 10 integers instead.
                If you provide a list of integers and a Showdown-compatible libpkmn,
                or don't specify a libpkmn, an exception will be raised.
            libpkmn (`pykmn.engine.libpkmn.LibpkmnBinding`, optional): The libpkmn build to use.
                Defaults to `pykmn.engine.libpkmn.libpkmn_showdown_trace`.
        """
        # optimization: is it faster to not put this on the Battle class?
        self._libpkmn = libpkmn
        self._pkmn_battle = self._libpkmn.ffi.new("pkmn_gen1_battle *")

        if self._libpkmn.lib.HAS_TRACE:
            self.trace_buf = self._libpkmn.ffi.new(
                "uint8_t[]",
                self._libpkmn.lib.PKMN_GEN1_LOGS_SIZE,
            )
        else:
            self.trace_buf = self._libpkmn.ffi.NULL
        self._choice_buf = self._libpkmn.ffi.new(
            "pkmn_choice[]",
            self._libpkmn.lib.PKMN_OPTIONS_SIZE,
        )

        # Initialize the sides
        p1_side_start = LAYOUT_OFFSETS['Battle']['sides']
        p2_side_start = LAYOUT_OFFSETS['Battle']['sides'] + LAYOUT_SIZES['Side']
        pokemon_size = LAYOUT_SIZES['Pokemon']
        for (side_start, last_selected_move, last_used_move, team) in (
            # p1's side
            (p1_side_start, p1_last_selected_move, p1_last_used_move, p1_team),
            # p2's side
            (p2_side_start, p2_last_selected_move, p2_last_used_move, p2_team),
        ):
            self._pkmn_battle.bytes[side_start + LAYOUT_OFFSETS['Side']['last_selected_move']] = \
                MOVE_IDS[last_selected_move]
            self._pkmn_battle.bytes[side_start + LAYOUT_OFFSETS['Side']['last_used_move']] = \
                MOVE_IDS[last_used_move]
            for (i, pkmn) in enumerate(team):
                self._initialize_pokemon(
                    (side_start + LAYOUT_OFFSETS['Side']['pokemon'] + (i * pokemon_size)),
                    pkmn,
                )
            for i in range(len(team)):
                self._pkmn_battle.bytes[side_start + LAYOUT_OFFSETS['Side']['order'] + i] = i + 1

        offset = LAYOUT_OFFSETS['Battle']['turn']

        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(start_turn)
        offset += 2
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(last_damage)
        offset += 2

        if self._libpkmn.lib.IS_SHOWDOWN_COMPATIBLE == 1:
            # Showdown-compatible initialization for move indexes and RNG
            self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(p1_move_idx)
            offset += 2
            self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(p2_move_idx)
            offset += 2

            if rng_seed is None:
                rng_seed = random.randrange(2**64)
            elif isinstance(rng_seed, list):
                raise Exception(
                    "Cannot provide a list as RNG seed to a Showdown-compatible libpkmn."
                )

            ShowdownRNG._initialize(bytes=self._libpkmn.ffi.cast(
                "pkmn_psrng *",
                self._pkmn_battle.bytes[offset:(offset + self._libpkmn.lib.PKMN_PSRNG_SIZE)],
            ), seed=rng_seed, _libpkmn=self._libpkmn)
        else:
            # libpkmn (no Showdown compatibility) initialization for move indexes RNG
            self._pkmn_battle.bytes[offset] = pack_two_u4s(p1_move_idx, p2_move_idx)
            offset += 1
            # assert offset == LAYOUT_OFFSETS['Battle']['rng'], \
            #     f"offset {offset} != {LAYOUT_OFFSETS['Battle']['rng']}"

            if rng_seed is None:
                for i in range(10):
                    self._pkmn_battle.bytes[offset + i] = random.randrange(2**8)
            elif isinstance(rng_seed, int):
                raise Exception(
                    "Cannot provide an integer as RNG seed to a non-Showdown-compatible libpkmn."
                )
            else:
                for (i, seed) in enumerate(rng_seed):
                    self._pkmn_battle.bytes[offset + i] = seed

    def _initialize_pokemon(self, battle_offset: int, pokemon_data: Pokemon) -> None:
        """Initialize a Pokémon in a battle."""
        hp = None
        status = 0
        level = 100
        stats = None
        types = None
        move_pp = None
        dvs: Gen1StatData = {'hp': 15, 'atk': 15, 'def': 15, 'spe': 15, 'spc': 15}
        exp: Gen1StatData = {'hp': 65535, 'atk': 65535, 'def': 65535, 'spe': 65535, 'spc': 65535}
        species_name = pokemon_data.species
        move_names = pokemon_data.moves
        if pokemon_data.extra is not None:
            # possible optimization: is it faster to pass this as an array/extra parameters
            # and avoid dict lookups?
            if 'hp' in pokemon_data.extra:
                hp = pokemon_data.extra['hp']
            if 'status' in pokemon_data.extra:
                status = pokemon_data.extra['status']._value
            if 'level' in pokemon_data.extra:
                level = pokemon_data.extra['level']
            if 'stats' in pokemon_data.extra:
                stats = pokemon_data.extra['stats']
            if 'types' in pokemon_data.extra:
                types = pokemon_data.extra['types']
            if 'move_pp' in pokemon_data.extra:
                move_pp = pokemon_data.extra['move_pp']
            if 'dvs' in pokemon_data.extra:
                dvs = pokemon_data.extra['dvs']
            if 'exp' in pokemon_data.extra:
                exp = pokemon_data.extra['exp']


        if species_name == 'None':
            if stats is None:
                stats = {'hp': 0, 'atk': 0, 'def': 0, 'spe': 0, 'spc': 0}
            if types is None:
                types = ('Normal', 'Normal')
        elif species_name in SPECIES:
            if stats is None:
                # optimization possible here:
                # skip the copy and just mandate that callers supply base stats
                stats = SPECIES[species_name]['stats'].copy()
                for stat in stats:
                    stats[stat] = statcalc(  # type: ignore
                        base_value=stats[stat],  # type: ignore
                        is_HP=(stat == 'hp'),
                        level=level,
                        dv=dvs[stat], # type: ignore
                        experience=exp[stat], # type: ignore
                    )
            if types is None:
                first_type = SPECIES[species_name]['types'][0]
                second_type = SPECIES[species_name]['types'][1] \
                    if len(SPECIES[species_name]['types']) > 1 else first_type
                types = (first_type, second_type)
        else:
            raise ValueError(f"'{species_name}' is not a valid species in Generation I.")

        if hp is None:
            hp = stats['hp']

        offset = battle_offset + LAYOUT_OFFSETS['Pokemon']['stats']
        # pack stats
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            self._pkmn_battle.bytes[offset:offset + 2] = \
                pack_u16_as_bytes(stats[stat]) # type: ignore
            offset += 2
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['moves']

        # pack moves
        for move_index in range(4):
            if move_index >= len(move_names):
                move_id = 0
                pp = 0
            else:
                move_id = MOVE_IDS[move_names[move_index]]
                if move_pp is None:
                    if move_id == 0:  # None move
                        pp = 0
                    else:
                        pp = min(math.floor(MOVES[move_names[move_index]] * 8 / 5), 61)
                else:
                    pp = move_pp[move_index]
            self._pkmn_battle.bytes[offset] = move_id
            offset += 1
            self._pkmn_battle.bytes[offset] = pp
            offset += 1
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['hp']

        # pack HP
        self._pkmn_battle.bytes[offset:offset + 2] = pack_u16_as_bytes(hp)
        offset += 2
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['status']

        # pack status
        self._pkmn_battle.bytes[offset] = status
        offset += 1
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['species']

        # pack species
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[species_name]
        offset += 1
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['types']

        # pack types
        self._pkmn_battle.bytes[offset] = pack_two_u4s(TYPES.index(types[0]), TYPES.index(types[1]))
        offset += 1
        # assert offset == battle_offset + LAYOUT_OFFSETS['Pokemon']['level']

        # pack level
        self._pkmn_battle.bytes[offset] = level
        offset += 1
        # assert offset == battle_offset + LAYOUT_SIZES['Pokemon']

    def possible_choices(
        self,
        player: Player,
        previous_turn_result: Result,
    ) -> List[Choice]:
        """Gets the possible choices for the given player, which can then be passed to `update()`.

        The returned choice list should only be used until the next call to this function,
        since each call reuses the same array of memory to keep PyKMN performant.

        Args:
            player (`pykmn.engine.common.Player`): The player to get choices for.
            previous_turn_result (`pykmn.engine.common.Result`): The result of the previous turn
                (if it's the first turn, pass two `pykmn.engine.common.Choice.PASS()`es to tell the
                simulator to send out the players' first Pokémon).

        Raises:
            `pykmn.engine.common.Softlock`: If no choices are available,
                meaning that the battle has softlocked.

        Returns:
            **`List[pykmn.engine.common.Choice]`**: The choices that this player can make.
        """
        # optimization: it might be faster actually to cache _pkmn_result in the battle??
        # This is equivalent to previous_turn_result.p<n>_choice_type().value but faster.

        num_choices = self._fill_choice_buffer(player, previous_turn_result)
        if num_choices == 0:
            raise Softlock("Zero choices are available.")

        choices: List[Choice] = []
        for i in range(num_choices):
            choices.append(Choice(self._choice_buf[i], _libpkmn=self._libpkmn))
        return choices

    def update(self, p1_choice: Choice, p2_choice: Choice) -> Tuple[Result, List[int]]:
        """Update the battle with the given choices.

        Choices must be obtained by calling `possible_choices()`
        after the last `update()` call;
        otherwise, your choices may be invalid and cause bugs.

        Calling `update()` will advance the simulation and update the battle state.

        Args:
            p1_choice (`pykmn.engine.common.Choice`): The choice to make for player 1.
            p2_choice (`pykmn.engine.common.Choice`): The choice to make for player 2.

        Returns:
            **`Tuple[pykmn.engine.common.Result, List[int]]`**: The result of the choice,
            and the trace as a list of
            [libpkmn protocol bytes](https://github.com/pkmn/engine/blob/main/docs/PROTOCOL.md).
            You can feed the trace into `pykmn.engine.protocol.parse_protocol` to get
            Pokémon Showdown-style protocol out of it, which is often easier to work with.
        """
        return self.update_raw(p1_choice._pkmn_choice, p2_choice._pkmn_choice)

    def possible_choices_raw(
        self,
        player: Player,
        previous_turn_result: Result,
    ) -> List[int]:
        """Get the possible choices in raw format for the given player.

        This method returns raw integers instead of `pykmn.engine.common.Choice` objects;
        these integers can be passed directly to `update_raw()`.
        If you need to inspect the choice data, use `possible_choices()` instead.

        Like with `possible_choices()`, you MUST consume the returned choices
        before calling any possible_choices method again
        (even if you mix and match raw and regular); otherwise, the buffer will be overwritten.

        If the returned list is length 0, a softlock has occurred.
        possible_choices() automatically checks for this and raises an exception, but
        possible_choices_raw() does not (for speed).

        Args:
            player (`pykmn.engine.common.Player`): The player to get choices for.
            previous_turn_result (`pykmn.engine.common.Result`): The result of the previous turn
                (the first turn should be two PASS choices — pass `0`s into `update_raw()`).

        Returns:
            **`List[int]`**: The possible choices.
        """
        num_choices = self._fill_choice_buffer(player, previous_turn_result)
        return self._choice_buf[0:num_choices]

    def update_raw(self, p1_choice: int, p2_choice: int) -> Tuple[Result, List[int]]:
        """Update the battle with the given choice.

        This method accepts raw integers for choices
        instead of `pykmn.engine.common.Choice` objects.

        If you don't get these from `possible_choices_raw()`, things may go wrong.
        Please don't just supply arbitrary numbers to this function.

        The return values for this function are the same as for `update()`.

        Args:
            p1_choice (`int`): The choice to make for player 1.
            p2_choice (`int`): The choice to make for player 2.

        Returns:
            **`Tuple[pykmn.engine.common.Result, List[int]]`**: The result of the choice,
            and the trace as a list of protocol bytes.
        """
        _pkmn_result = self._libpkmn.lib.pkmn_gen1_battle_update(
            self._pkmn_battle,          # pkmn_gen1_battle *battle
            p1_choice,     # pkmn_choice c1
            p2_choice,     # pkmn_choice c2
            self.trace_buf,                  # uint8_t *buf
            self._libpkmn.lib.PKMN_GEN1_LOGS_SIZE,     # size_t len
        )

        result = Result(_pkmn_result, _libpkmn=self._libpkmn)
        if result.is_error():
            # per pkmn.h:
            # This can only happen if libpkmn was built with trace logging enabled and the buffer
            # provided to the update function was not large  enough to hold all of the data
            # (which is only possible if the buffer being used was smaller than the
            # generation in question's MAX_LOGS bytes).
            raise Exception(
                "An error was thrown in libpkmn while updating the battle. " +
                "This should never happen; please file a bug report with PyKMN at " +
                "https://github.com/AnnikaCodes/PyKMN/issues/new"
            )
        return (result, self.trace_buf)


    def last_selected_move(self, player: Player) -> str:
        """Get the last move selected by a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the last move for.

        Returns:
            **`str`**: The name of the last move selected by the player.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_selected_move(self, player: Player, move: str) -> None:
        """Set the last move selected by a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the last move for.
            move (`str`): The name of the move to set.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def last_used_move(self, player: Player) -> str:
        """Get the last move used by a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the last move for.

        Returns:
            **`str`**: The name of the last move used by the player.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_used_move(self, player: Player, move: str) -> None:
        """Set the last move used by a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the last move for.
            move (`str`): The name of the move to be set as the last move.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def active_pokemon_stats(self, player: Player) -> Gen1StatData:
        """Get the stats of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the stats for.

        Returns:
            **`pykmn.engine.gen1.common.Gen1StatData`**: The stats of the active Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['stats']
        stats = {}
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            stats[stat] = unpack_u16_from_bytes(
                self._pkmn_battle.bytes[offset],
                self._pkmn_battle.bytes[offset + 1],
            )
            offset += 2
        return cast(Gen1StatData, stats)

    def set_active_pokemon_stats(self, player: Player, new_stats: PartialGen1StatData) -> None:
        """Set the stats of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the stats for.
            new_stats (`pykmn.engine.gen1.common.PartialGen1StatData`): The new stats to set.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['stats']

        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            if stat in new_stats:
                self._pkmn_battle.bytes[offset:(offset + 2)] = \
                    pack_u16_as_bytes(new_stats[stat]) # type: ignore
            offset += 2

    def active_pokemon_species(self, player: Player) -> str:
        """Get the species of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the species for.

        Returns:
            **`str`**: The name of the species of the active Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_active_pokemon_species(self, player: Player, new_species: str) -> None:
        """Set the species of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the species for.
            new_species (`str`): The name of the species to be set.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def active_pokemon_types(self, player: Player) -> Union[Tuple[str, str], Tuple[str]]:
        """Get the types of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the types for.

        Returns:
            **`Tuple[str, str]` | `Tuple[str]`**: The type(s) of the active Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1], )

    def boosts(self, player: Player) -> BoostData:
        """Get the boosts of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the boosts for.

        Returns:
            **`pykmn.engine.gen1.common.BoostData`**: The boosts of that player's active Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['boosts']
        (attack, defense) = unpack_two_i4s(self._pkmn_battle.bytes[offset])
        (speed, special) = unpack_two_i4s(self._pkmn_battle.bytes[offset + 1])
        (accuracy, evasion) = unpack_two_i4s(self._pkmn_battle.bytes[offset + 2])
        return {
            'atk': attack,
            'def': defense,
            'spe': speed,
            'spc': special,
            'accuracy': accuracy,
            'evasion': evasion,
        }

    def set_boosts(self, player: Player, new_boosts: PartialBoostData) -> None:
        """Set the boosts of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the boosts for.
            new_boosts (`pykmn.engine.gen1.common.PartialBoostData`): The new boosts to set.
            You can omit any stats whose stat stage boosts you want to leave unchanged.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['boosts']
        old_boosts = self.boosts(player)
        self._pkmn_battle.bytes[offset] = pack_two_i4s(
            new_boosts['atk'] if 'atk' in new_boosts else old_boosts['atk'],
            new_boosts['def'] if 'def' in new_boosts else old_boosts['def'],
        )
        self._pkmn_battle.bytes[offset + 1] = pack_two_i4s(
            new_boosts['spe'] if 'spe' in new_boosts else old_boosts['spe'],
            new_boosts['spc'] if 'spc' in new_boosts else old_boosts['spc'],
        )
        self._pkmn_battle.bytes[offset + 2] = pack_two_i4s(
            new_boosts['accuracy'] if 'accuracy' in new_boosts else old_boosts['accuracy'],
            new_boosts['evasion'] if 'evasion' in new_boosts else old_boosts['evasion'],
        )

    def volatile(self, player: Player, volatile: VolatileFlag) -> bool:
        """Get the value of a volatile-status flag of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the volatile flag for.
            volatile (`pykmn.engine.common.VolatileFlag`): The volatile-status flag to get.

        Returns:
            **`bool`**: `True` if the volatile-status flag is set and `False` otherwise.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        volatile_uint32_ptr = self._libpkmn.ffi.cast(
            "uint32_t *",
            self._pkmn_battle.bytes[offset:(offset + 4)],
        )
        # https://stackoverflow.com/questions/9298865/get-n-th-bit-of-an-integer
        return not not(volatile_uint32_ptr[0] & (1 << volatile))

    def set_volatile(self, player: Player, flag: VolatileFlag, value: bool) -> None:
        """Set a volatile-status flag of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the volatile flag for.
            flag (`pykmn.engine.common.VolatileFlag`): The volatile-status flag to set.
            value (`bool`): `True` if the flag should be set, or `False` if it should be unset.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        volatile_uint32_ptr = self._libpkmn.ffi.cast(
            "uint32_t *",
            self._pkmn_battle.bytes[offset:(offset + 4)],
        )
        if value:
            volatile_uint32_ptr[0] |= (1 << flag)
        else:
            volatile_uint32_ptr[0] &= ~(1 << flag)

    def confusion_turns_left(self, player: Player) -> int:
        """Get the number of turns left in Confusion of a player's active Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the confusion counter for.

        Returns:
            **`int`**: The number of turns left in Confusion.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['confusion']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        # get the u3
        return extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=3,
        )

    def set_confusion_turns_left(self, player: Player, new_turns_left: int) -> None:
        """Set the number of turns left in Confusion of a player's active Pokémon.

        If the Pokémon isn't already confused, or if you're setting the number of turns left to 0,
        you should probably also set the Confusion volatile-status flag with `set_volatile()`.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the confusion counter for.
            new_turns_left (`int`): The new number of turns left in Confusion.

        Raises:
            `AssertionError`: If `new_turns_left` is not an unsigned 3-bit integer.
        """
        assert new_turns_left <= (2**3) and new_turns_left >= 0, \
            "new_turns_left must be an unsigned 3-bit integer"

        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['confusion']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            n=new_turns_left,
            offset=bit_offset,
            length=3,
        )

    def attacks_left(self, player: Player) -> int:
        """Get the attacks left counter of the active Pokémon.

        This counter is used for the moves Bide and Thrash.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the counter for.

        Returns:
            **`int`**: The attacks left counter.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['attacks']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        return extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=3,
        )

    def set_attacks_left(self, player: Player, new_attacks_left: int) -> None:
        """Set the attacks left counter of the active Pokémon.

        This counter is used for Bide and Thrash.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the counter for.
            new_attacks_left (`int`): The new value of the attacks left counter.

        Raises:
            `AssertionError`: If `new_attacks_left` is not an unsigned 3-bit integer.
        """
        assert new_attacks_left <= (2**3) and new_attacks_left >= 0, \
            "new_attacks_left must be an unsigned 3-bit integer"

        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['attacks']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            n=new_attacks_left,
            offset=bit_offset,
            length=3,
        )

    def volatile_state(self, player: Player) -> int:
        """Get the volatile state of the active Pokémon of a player.

        This 16-bit unsigned integer is used to track the amount of damage accumulated for Bide,
        and to store data for certain accuracy-related bugs.

        You can read more in the libpkmn docs:
        https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md#Volatiles

        Args:
            player (`pykmn.engine.common.Player`): The player to get the volatile state for.

        Returns:
            **`int`**: The volatile state.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['state'] // 8)
        # we don't need a bit_offset because the state is byte-aligned
        assert LAYOUT_OFFSETS['Volatiles']['state'] % 8 == 0
        bytes = self._pkmn_battle.bytes
        return unpack_u16_from_bytes(bytes[offset], bytes[offset + 1])

    def set_volatile_state(self, player: Player, new_state: int) -> None:
        """Set the volatile state of the active Pokémon of a player.

        This 16-bit unsigned integer is used to track the amount of damage accumulated for Bide,
        and to store data for certain accuracy-related bugs.

        You can read more in the libpkmn docs:
        https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md#Volatiles

        Args:
            player (`pykmn.engine.common.Player`): The player to set the volatile state for.
            new_state (`int`): The new value of the volatile state.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['state'] // 8)
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_state)

    def substitute_hp(self, player: Player) -> int:
        """Get the HP of the Substitute up on a player's side.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the Substitute HP for.

        Returns:
            **`int`**: The number of Hit Points the Substitute has.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['substitute'] // 8)
        assert LAYOUT_OFFSETS['Volatiles']['substitute'] % 8 == 0
        return self._pkmn_battle.bytes[offset]

    def set_substitute_hp(self, player: Player, new_hp: int) -> None:
        """Set the HP of the Substitute up on a player's side.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the Substitute HP for.
            new_hp (`int`): The new number of HP to give the Substitute.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['substitute'] // 8)
        assert LAYOUT_OFFSETS['Volatiles']['substitute'] % 8 == 0
        self._pkmn_battle.bytes[offset] = new_hp

    def set_active_pokemon_types(
        self,
        player: Player,
        new_types: Union[Tuple[str, str], Tuple[str]]
    ) -> None:
        """Set the types of the active Pokémon of a player.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the types for.
            new_types (`Tuple[str, str]` | `Tuple[str]`): The new type(s) of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        self._pkmn_battle.bytes[offset] = pack_two_u4s(
            TYPES.index(new_types[0]),
            TYPES.index(new_types[1 if len(new_types) == 2 else 0]),
        )

    def transformed_into(self, player: Player) -> Tuple[Player, Slot]:
        """Get the player and slot of the Pokémon that the active Pokémon transformed into.

        If the active Pokémon has not transformed, this will probably return zeroes, but
        you shouldn't rely on that.
        Check the `VolatileFlag.Transform` with `volatile` first.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the transformed Pokémon for.

        Returns:
            **`Tuple[Player, Slot]`**: The player and slot of the Pokémon that the active
            Pokémon has transformed into.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['transform']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        transform_u4 = extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=4,
        )
        slot = cast(Slot, transform_u4 & 3)
        return (Player.P1 if (transform_u4 >> 3) == 0 else Player.P2, slot)

    def set_transformed_into(
        self,
        player: Player,
        new_transformed_into: Tuple[Player, Slot]
    ) -> None:
        """Set the player and slot that the active Pokémon transformed into.

        This won't set the `VolatileFlag.Transform` flag, so you'll need to do that yourself.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the transformed Pokémon for.
            new_transformed_into (`Tuple[Player, Slot]`): The player and slot of the
                Pokémon that the active Pokémon has transformed into.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['transform']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        transform_u4 = (((new_transformed_into[0]) << 3) | new_transformed_into[1])
        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=4,
            n=transform_u4,
        )

    def disable_data(self, player: Player) -> DisableData:
        """Get data about a Disabled move of the active Pokémon of a player.

        If the active Pokémon doesn't have a Disabled move, this will probably return zeroes, but
        you shouldn't rely on that.
        Check the `VolatileFlag.Disable` with `volatile()` first.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the Disabled move data for.

        Returns:
            **`DisableData`**: The data about the Disabled move.
        """
        base = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']

        duration_byte_offset = base + (LAYOUT_OFFSETS['Volatiles']['disabled_duration'] // 8)
        duration_bit_offset = LAYOUT_OFFSETS['Volatiles']['disabled_duration'] % 8
        duration = extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[duration_byte_offset],
            offset=duration_bit_offset,
            length=4,
        )

        move_byte_offset = base + (LAYOUT_OFFSETS['Volatiles']['disabled_move'] // 8)
        move_bit_offset = LAYOUT_OFFSETS['Volatiles']['disabled_move'] % 8
        move = extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[move_byte_offset],
            offset=move_bit_offset,
            length=3,
        )

        return DisableData(move_slot=move, turns_left=duration)

    def set_disable_data(self, player: Player, new_disable_data: DisableData) -> None:
        """Set data about a Disabled move of the active Pokémon of a player.

        This won't set or unset the `VolatileFlag.Disable` flag, so you'll need to do that yourself.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the Disabled move data for.
            new_disable_data (`DisableData`): The data about the Disabled move.
        """
        base = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']

        duration_byte_offset = base + (LAYOUT_OFFSETS['Volatiles']['disabled_duration'] // 8)
        duration_bit_offset = LAYOUT_OFFSETS['Volatiles']['disabled_duration'] % 8
        self._pkmn_battle.bytes[duration_byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[duration_byte_offset],
            offset=duration_bit_offset,
            length=4,
            n=new_disable_data.turns_left,
        )

        move_byte_offset = base + (LAYOUT_OFFSETS['Volatiles']['disabled_move'] // 8)
        move_bit_offset = LAYOUT_OFFSETS['Volatiles']['disabled_move'] % 8
        self._pkmn_battle.bytes[move_byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[move_byte_offset],
            offset=move_bit_offset,
            length=3,
            n=new_disable_data.move_slot,
        )

    def toxic_severity(self, player: Player) -> int:
        """Get the Toxic counter of the active Pokémon of a player.

        If the active Pokémon isn't poisoned with Toxic, this will probably return zero, but you
        shouldn't rely on that. Check the `VolatileFlag.Toxic` with `volatile()` first.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the Toxic counter for.

        Returns:
            **`int`**: The number of turns that damage from Toxic has accumulated for.

        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['toxic']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        return extract_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=5,
        )

    def set_toxic_severity(self, player: Player, new_toxic_counter: int) -> None:
        """Set the Toxic counter of the active Pokémon of a player.

        This won't set or unset the `VolatileFlag.Toxic` flag, so you'll need to do that yourself.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the Toxic counter for.
            new_toxic_counter (`int`): The number of turns that damage from Toxic has accumulated
                for.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['toxic']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            offset=bit_offset,
            length=5,
            n=new_toxic_counter,
        )


    def turn(self) -> int:
        """Get the current turn of the battle.

        Returns:
            **`int`**: The current turn of the battle.
        """
        offset = LAYOUT_OFFSETS['Battle']['turn']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_turn(self, new_turn: int) -> None:
        """Set the current turn of the battle.

        Args:
            new_turn (`int`): The new turn of the battle.
        """
        offset = LAYOUT_OFFSETS['Battle']['turn']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_turn)

    def last_damage(self) -> int:
        """Get the last damage dealt.

        Returns:
            **`int`**: The last damage dealt.
        """
        offset = LAYOUT_OFFSETS['Battle']['last_damage']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_last_damage(self, new_last_damage: int) -> None:
        """Set the last damage dealt.

        Args:
            new_last_damage (`int`): The new last damage dealt.
        """
        offset = LAYOUT_OFFSETS['Battle']['last_damage']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_last_damage)

    def last_used_move_index(self, player: Player) -> int:
        """Get the index within the move array of the last move used by a given player.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the last used move index for.

        Returns:
            **`int`**: The index within the move array of the last move used by the given player.
        """
        offset = LAYOUT_OFFSETS['Battle']['last_selected_indexes'] + player
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def current_hp(self, player: Player, pokemon: Slot) -> int:
        """Get the current HP of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player to get the Pokémon's HP for.
            pokemon (`Slot`): The slot number of the Pokémon to get the HP for.

        Returns:
            **`int`**: The current HP of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['hp']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_current_hp(self, player: Player, pokemon: Slot, new_hp: int) -> None:
        """Set the current HP of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player to set the Pokémon's HP for.
            pokemon (`Slot`): The slot number of the Pokémon to set the HP for.
            new_hp (`int`): The new current HP value for the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['hp']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_hp)

    def stats(self, player: Player, pokemon: Slot) -> Gen1StatData:
        """Get the stats of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's stats to get.
            pokemon (`Slot`): The slot number of the Pokémon to get the stats for.

        Returns:
            **`pykmn.data.loader.Gen1StatData`**: The stats of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['stats']
        stats = {}
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            stats[stat] = unpack_u16_from_bytes(
                self._pkmn_battle.bytes[offset],
                self._pkmn_battle.bytes[offset + 1],
            )
            offset += 2
        return cast(Gen1StatData, stats)

    def set_stats(
        self,
        player: Player,
        pokemon: Slot,
        new_stats: PartialGen1StatData,
    ) -> None:
        """Set the stats of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's stats to set.
            pokemon (`Slot`): The slot number of the Pokémon to set the stats for.
            new_stats (`pykmn.data.loader.PartialGen1StatData`): The new stats for the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['stats']

        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            if stat in new_stats:
                self._pkmn_battle.bytes[offset:(offset + 2)] = \
                    pack_u16_as_bytes(new_stats[stat]) # type: ignore
            offset += 2

    # TODO: is this the most performant way to do this? Maybe an enum or separate method?
    def moves(self, player: Player, pokemon: Union[Slot, Literal["Active"]]) -> Moveset:
        """Get the moves of a Pokémon."""
        if not isinstance(pokemon, int):
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['active'] + \
                LAYOUT_OFFSETS['ActivePokemon']['moves']
        else:
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['pokemon'] + \
                LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
                LAYOUT_OFFSETS['Pokemon']['moves']

        moves = tuple(
            MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset + n]] \
                for n in range(0, 8, 2) \
                if self._pkmn_battle.bytes[offset + n] != 0
        )
        return cast(Moveset, moves)


    def pp_left(
        self,
        player: Player,
        pokemon: Union[Slot, Literal["Active"]]
    ) -> Tuple[int, ...]:
        """Get the PP left of a Pokémon's moves.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's moves to get.
            pokemon (`Slot` | `"Active"`):
                The slot number of the Pokémon to get the moves for.
                Specify `"Active"` to get the moves of that player's active Pokémon.

        Returns:
            **`Tuple[int, ...]`**: The PP left of the Pokémon's moves.
            The tuple's length is the number of moves the Pokémon has.
        """
        if not isinstance(pokemon, int):
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['active'] + \
                LAYOUT_OFFSETS['ActivePokemon']['moves']
        else:
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['pokemon'] + \
                LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
                LAYOUT_OFFSETS['Pokemon']['moves']
        return tuple(
            self._pkmn_battle.bytes[offset + n] \
                for n in range(1, 9, 2) \
                if self._pkmn_battle.bytes[offset + n - 1] != 0 # if move exists
        )

    def moves_with_pp(
        self,
        player: Player,
        pokemon: Union[Slot, Literal["Active"]]
    ) -> Tuple[MovePP, ...]:
        """Get the moves of a Pokémon with their PP.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's moves to get.
            pokemon (`Slot` | `"Active"`):
                The slot number of the Pokémon to get the moves for.
            Specify `"Active"` to get the moves of that player's active Pokémon.

        Returns:
            **`Tuple[MovePP, ...]`**: The moves of the Pokémon with their PP.
            The tuple's length is the number of moves the Pokémon has.
        """
        if not isinstance(pokemon, int):
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['active'] + \
                LAYOUT_OFFSETS['ActivePokemon']['moves']
        else:
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['pokemon'] + \
                LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
                LAYOUT_OFFSETS['Pokemon']['moves']
        bytes = self._pkmn_battle.bytes
        return cast(Tuple[MovePP, ...], tuple(
            (MOVE_ID_LOOKUP[bytes[offset + n]], bytes[offset + n + 1]) \
                for n in range(0, 8, 2) \
                if bytes[offset + n] != 0
        ))

    def set_moves(
        self,
        player: Player,
        pokemon: Union[Slot, Literal["Active"]],
        new_moves: Tuple[MovePP, MovePP, MovePP, MovePP]
    ) -> None:
        """Set the moves of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's moves to set.
            pokemon (`Slot` | `"Active"`):
                The slot number of the Pokémon to set the moves for.
                Specify `"Active"` to set the moves of that player's active Pokémon.
            new_moves (`Tuple[MovePP, MovePP, MovePP, MovePP]`):
                The new move names and PP values of the Pokémon.

        """
        if not isinstance(pokemon, int):
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['active'] + \
                LAYOUT_OFFSETS['ActivePokemon']['moves']
        else:
            offset = LAYOUT_OFFSETS['Battle']['sides'] + \
                LAYOUT_SIZES['Side'] * player + \
                LAYOUT_OFFSETS['Side']['pokemon'] + \
                LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
                LAYOUT_OFFSETS['Pokemon']['moves']

        for i, (move, pp) in enumerate(new_moves):
            self._pkmn_battle.bytes[offset + i*2] = MOVE_IDS[move]
            self._pkmn_battle.bytes[offset + i*2 + 1] = pp

    def status(self, player: Player, pokemon: Slot) -> Status:
        """Get the status of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's status to get.
            pokemon (`Slot`): The slot number of the Pokémon to get the status for.

        Returns:
            **`Status`**: The status of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        return Status(self._pkmn_battle.bytes[offset])

    def set_status(self, player: Player, pokemon: Slot, new_status: Status) -> None:
        """Set the status condition of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's status to set.
            pokemon (`Slot`): The slot number of the Pokémon to set the status for.
            new_status (`Status`): The new status condition of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        self._pkmn_battle.bytes[offset] = new_status._value

    # optimization: make Species an enum to avoid lookups?
    def species(self, player: Player, pokemon: Slot) -> str:
        """Get the species of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's species to get.
            pokemon (`Slot`): The slot number of the Pokémon to get the species for.

        Returns:
            **`str`**: The species of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_species(self, player: Player, pokemon: Slot, new_species: str) -> None:
        """Set the species of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's species to set.
            pokemon (`Slot`): The slot number of the Pokémon to set the species for.
            new_species (`str`): The new species of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def types(self, player: Player, pokemon: Slot) -> Union[Tuple[str, str], Tuple[str]]:
        """Get the types of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's types to get.
            pokemon (`Slot`): The slot number of the Pokémon to get the types for.

        Returns:
            **`Tuple[str, str]` | `Tuple[str]`**: The type(s) of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1],)

    def set_types(self, player: Player, pokemon: Slot, new_types: Tuple[str, str]) -> None:
        """Set the types of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's types to set.
            pokemon (`Slot`): The slot number of the Pokémon to set the types for.
            new_types (`Tuple[str, str]`): The new types of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['types']
        self._pkmn_battle.bytes[offset] = pack_two_u4s(
            TYPES.index(new_types[0]),
            TYPES.index(new_types[1])
        )

    def level(self, player: Player, pokemon: Slot) -> int:
        """Get the level of a Pokémon.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's level to get.
            pokemon (`Slot`): The slot number of the Pokémon to get the level for.

        Returns:
            **`int`**: The level of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        return self._pkmn_battle.bytes[offset]

    def set_level(self, player: Player, pokemon: Slot, new_level: int) -> None:
        """Set the level of a Pokémon.

        This won't rebalance the Pokémon's stats.

        Args:
            player (`pykmn.engine.common.Player`): The player whose Pokémon's level to set.
            pokemon (`Slot`): The slot number of the Pokémon to set the level for.
            new_level (`int`): The new level of the Pokémon.
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        self._pkmn_battle.bytes[offset] = new_level

    def _fill_choice_buffer(self, player: Player, previous_turn_result: Result) -> int:
        """Fills the battle's choice buffer with the possible choices for the given player.

        Probably don't call this.

        Args:
            player (`Player`): _description_
            previous_turn_result (`Result`): _description_

        Raises:
            Softlock: _description_

        Returns:
            **`int`**: The number of choices
        """
        last_result = previous_turn_result._pkmn_result
        requested_kind = self._libpkmn.lib.pkmn_result_p1(last_result) if player == Player.P1 \
            else self._libpkmn.lib.pkmn_result_p2(last_result)
        num_choices = self._libpkmn.lib.pkmn_gen1_battle_choices(
            self._pkmn_battle,      # pkmn_gen1_battle *battle
            player,           # pkmn_player player
            # optimization: is IntEnum more performant?
            requested_kind,   # pkmn_choice_kind request
            self._choice_buf,            # pkmn_choice out[]
            self._libpkmn.lib.PKMN_OPTIONS_SIZE,  # size_t len
        )

        return num_choices
