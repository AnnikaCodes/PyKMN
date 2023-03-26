"""Battle simulation for Generation I."""
from pykmn.engine.libpkmn import libpkmn_showdown_trace, LibpkmnBinding
from pykmn.engine.common import Result, Player, ChoiceType, Softlock, Choice, \
    pack_u16_as_bytes, unpack_u16_from_bytes, pack_two_u4s, unpack_two_u4s, \
    pack_two_i4s, unpack_two_i4s, insert_unsigned_int_at_offset, extract_unsigned_int_at_offset \
    # noqa: F401
from pykmn.engine.rng import ShowdownRNG
from pykmn.data.gen1 import Gen1StatData, MOVE_IDS, SPECIES_IDS, PartialGen1StatData, \
    SPECIES, TYPES, MOVES, LAYOUT_OFFSETS, LAYOUT_SIZES, MOVE_ID_LOOKUP, SPECIES_ID_LOOKUP

from typing import List, Tuple, cast, TypedDict, Literal, Union
from enum import IntEnum
from collections import namedtuple
import math
import random

"""Pythonic API to get info about a Pokémon status."""
class Status:
    _SLP = 2
    _PSN = 3
    _BRN = 4
    _FRZ = 5
    _PAR = 6

    def __init__(self, raw_status: int):
        self._value = raw_status

    def asleep(self) -> bool:
        """Returns whether the Pokémon is asleep.

        Returns:
            bool: _description_
        """
        return self.sleep_duration() != 0

    def sleep_duration(self) -> int:
        """Returns the number of turns the Pokémon will be asleep for.

        Returns 0 if the Pokémon isn't asleep.

        Returns:
            int: _description_
        """
        return self._value & 0b111

    def healthy(self) -> bool:
        """Returns whether the Pokémon is healthy.

        Returns:
            bool: _description_
        """
        return self._value == 0

    def burned(self) -> bool:
        """Returns whether the Pokémon is burned.

        Returns:
            bool: _description_
        """
        return ((self._value >> Status._BRN) & 1) != 0

    def frozen(self) -> bool:
        """Returns whether the Pokémon is frozen.

        Returns:
            bool: _description_
        """
        return ((self._value >> Status._FRZ) & 1) != 0

    def paralyzed(self) -> bool:
        """Returns whether the Pokémon is paralyzed.

        Returns:
            bool: _description_
        """
        return ((self._value >> Status._PAR) & 1) != 0

    def poisoned(self) -> bool:
        """Returns whether the Pokémon is poisoned.

        Returns:
            bool: _description_
        """
        return ((self._value >> Status._PSN) & 1) != 0

    @staticmethod
    def SLEEP(duration: int) -> int:
        """Returns the raw status value for a sleeping Pokémon.

        Args:
            duration (int): The duration of the sleep.

        Returns:
            int: _description_
        """
        return duration

    @staticmethod
    def HEALTHY():
        """Returns the raw status value for a healthy Pokémon.

        Returns:
            Status: _description_
        """
        return Status(0)

    @staticmethod
    def POISONED():
        """Returns the raw status value for a poisoned Pokémon.

        Returns:
            Status: _description_
        """
        return Status(1 << Status._PSN)

    @staticmethod
    def BURNED():
        """Returns the raw status value for a burned Pokémon.

        Returns:
            Status: _description_
        """
        return Status(1 << Status._BRN)

    @staticmethod
    def FROZEN():
        """Returns the raw status value for a frozen Pokémon.

        Returns:
            Status: _description_
        """
        return Status(1 << Status._FRZ)

    @staticmethod
    def PARALYZED():
        """Returns the raw status value for a paralyzed Pokémon.

        Returns:
            Status: _description_
        """
        return Status(1 << Status._PAR)

    @staticmethod
    def SELF_INFLICTED_SLEEP(duration: int):
        """Returns the raw status value for a self-inflicted sleep.

        Args:
            duration (int): The duration of the sleep.

        Returns:
            Status: _description_
        """
        return Status(0x80 | duration)

    def __repr__(self) -> str:
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

MovePP = Tuple[str, int]
FullMoveset = Tuple[str, str, str, str]
Moveset = Union[FullMoveset, Tuple[str], Tuple[str, str], Tuple[str, str, str]]
SpeciesName = str
ExtraPokemonData = TypedDict('ExtraPokemonData', {
    'hp': int, 'status': Status, 'level': int, 'stats': Gen1StatData,
    'types': Tuple[str, str], 'move_pp': Tuple[int, int, int, int],
    'dvs': Gen1StatData, 'exp': Gen1StatData,
}, total=False)
PokemonData = Union[Tuple[SpeciesName, Moveset], Tuple[SpeciesName, Moveset, ExtraPokemonData]]
PokemonSlot = Union[Literal[1], Literal[2], Literal[3],Literal[4], Literal[5], Literal[6]]
BoostData = TypedDict('BoostData', {
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
    'accuracy': int,
    'evasion': int,
}) # optimization: is a namedtuple/class faster than a dict?
PartialBoostData = TypedDict('PartialBoostData', {
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
    'accuracy': int,
    'evasion': int,
}, total=False)
DisableData = namedtuple('DisableData', ['move_slot', 'turns_left'])

class VolatileFlag(IntEnum):
    Bide = LAYOUT_OFFSETS['Volatiles']['Bide']
    Thrashing = LAYOUT_OFFSETS['Volatiles']['Thrashing']
    MultiHit = LAYOUT_OFFSETS['Volatiles']['MultiHit']
    Flinch = LAYOUT_OFFSETS['Volatiles']['Flinch']
    Charging = LAYOUT_OFFSETS['Volatiles']['Charging']
    Binding = LAYOUT_OFFSETS['Volatiles']['Binding']
    Invulnerable = LAYOUT_OFFSETS['Volatiles']['Invulnerable']
    Confusion = LAYOUT_OFFSETS['Volatiles']['Confusion']
    Mist = LAYOUT_OFFSETS['Volatiles']['Mist']
    FocusEnergy = LAYOUT_OFFSETS['Volatiles']['FocusEnergy']
    Substitute = LAYOUT_OFFSETS['Volatiles']['Substitute']
    Recharging = LAYOUT_OFFSETS['Volatiles']['Recharging']
    Rage = LAYOUT_OFFSETS['Volatiles']['Rage']
    LeechSeed = LAYOUT_OFFSETS['Volatiles']['LeechSeed']
    Toxic = LAYOUT_OFFSETS['Volatiles']['Toxic']
    LightScreen = LAYOUT_OFFSETS['Volatiles']['LightScreen']
    Reflect = LAYOUT_OFFSETS['Volatiles']['Reflect']
    Transform = LAYOUT_OFFSETS['Volatiles']['Transform']

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
        HP (bool, optional): Whether the stat is HP or not. Defaults to False.

    Returns:
        int: The value of the stat
    """
    core = (2 * (base_value + dv)) + (math.sqrt(experience) // 4)
    factor = (level + 10) if is_HP else 5
    return int((core * (level // 100) + factor) % 2**16)


# MAJOR TODO!
    # * properly handle status
# * write unit tests
# * make all constructors check array lengths, etc, for validity
# * write a LOT of integration tests
# * add support for toggling -Dshowdown & -Dtrace
#    * support non-Showdown RNG
# * investigate performance and optimize
# * simplify typing as needed (and make sure everything's typed)
# * maybe more documentation?

# Optimization: remove debug asserts

Gen1RNGSeed = List[int]

class Battle:
    """A Generation I Pokémon battle."""

    def __init__(
        self,
        p1_team: List[PokemonData],
        p2_team: List[PokemonData],
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
    ):
        """Initialize a new battle.

        Args:
            p1_team (List[PokemonData]): Player 1's team.
            p2_team (List[PokemonData]): Player 2's team.
            p1_last_selected_move (str, optional): Player 1's last selected move. Defaults to None.
            p1_last_used_move (str, optional): Player 1's last used move. Defaults to None.
            p2_last_selected_move (str, optional): Player 2's last selected move. Defaults to None.
            p2_last_used_move (str, optional): Player 2's last used move. Defaults to None.
            start_turn (int, optional): The turn the battle starts on. Defaults to 0.
            last_damage (int, optional): The last damage dealt in the battle. Defaults to 0.
            p1_move_idx (int, optional): The last move index selected by Player 1. Defaults to 0.
            p2_move_idx (int, optional): The last move index selected by Player 2. Defaults to 0.
            rng_seed (int, optional): The seed to initialize the battle's RNG with.
                Defaults to a random seed.
                If a non-Showdown-compatible libpkmn is provided,
                you must provide a list of 10 integers instead.
                If you provide a list of integers and a Showdown-compatible libpkmn,
                or don't specify a libpkmn, an exception will be raised.
            libpkmn (LibpkmnBinding, optional): Defaults to libpkmn_showdown_trace.
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

            ShowdownRNG.initialize(bytes=self._libpkmn.ffi.cast(
                "pkmn_psrng *",
                self._pkmn_battle.bytes[offset:(offset + self._libpkmn.lib.PKMN_PSRNG_SIZE)],
            ), seed=rng_seed, libpkmn=self._libpkmn)
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

    def _initialize_pokemon(self, battle_offset: int, pokemon_data: PokemonData):
        """Initialize a Pokémon in a battle."""

        hp = None
        status = 0
        level = 100
        stats = None
        types = None
        move_pp = None
        dvs: Gen1StatData = {'hp': 15, 'atk': 15, 'def': 15, 'spe': 15, 'spc': 15}
        exp: Gen1StatData = {'hp': 65535, 'atk': 65535, 'def': 65535, 'spe': 65535, 'spc': 65535}
        if len(pokemon_data) == 3:
            species_name, move_names, extra_data = \
                cast(Tuple[SpeciesName, Moveset, ExtraPokemonData], pokemon_data)
            # possible optimization: is it faster to pass this as an array/extra parameters
            # and avoid dict lookups?
            if 'hp' in extra_data:
                hp = extra_data['hp']
            if 'status' in extra_data:
                status = extra_data['status']._value
            if 'level' in extra_data:
                level = extra_data['level']
            if 'stats' in extra_data:
                stats = extra_data['stats']
            if 'types' in extra_data:
                types = extra_data['types']
            if 'move_pp' in extra_data:
                move_pp = extra_data['move_pp']
            if 'dvs' in extra_data:
                dvs = extra_data['dvs']
            if 'exp' in extra_data:
                exp = extra_data['exp']
        else:
            species_name, move_names = cast(Tuple[SpeciesName, Moveset], pokemon_data)

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

    def last_selected_move(self, player: Player) -> str:
        """Get the last move selected by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_selected_move(self, player: Player, move: str):
        """Set the last move selected by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def last_used_move(self, player: Player) -> str:
        """Get the last move used by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_used_move(self, player: Player, move: str):
        """Set the last move used by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def active_pokemon_stats(self, player: Player) -> Gen1StatData:
        """Get the stats of the active Pokémon of a player."""
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
        """Set the stats of the active Pokémon of a player."""
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
        """Get the species of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_active_pokemon_species(self, player: Player, new_species: str) -> None:
        """Set the species of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def active_pokemon_types(self, player: Player) -> Union[Tuple[str, str], Tuple[str]]:
        """Get the types of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1], )

    def boosts(self, player: Player) -> BoostData:
        """Get the boosts of the active Pokémon of a player."""
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
        """Set the boosts of the active Pokémon of a player."""
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
        """Get a volatile of the active Pokémon of a player."""
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

    def set_volatile(self, player: Player, volatile: VolatileFlag, value: bool) -> None:
        """Set a volatile of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        volatile_uint32_ptr = self._libpkmn.ffi.cast(
            "uint32_t *",
            self._pkmn_battle.bytes[offset:(offset + 4)],
        )
        if value:
            volatile_uint32_ptr[0] |= (1 << volatile)
        else:
            volatile_uint32_ptr[0] &= ~(1 << volatile)

    def confusion_turns_left(self, player: Player) -> int:
        """Get the confusion counter of the active Pokémon of a player."""
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
        """Set the confusion counter of the active Pokémon of a player."""
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
        """
        Get the attacks left counter of the active Pokémon.

        This counter is used for Bide and Thrash.
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
        """
        Set the attacks left counter of the active Pokémon.

        This counter is used for Bide and Thrash.
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
        """
        Get the volatile state of the active Pokémon of a player.

        This 16-bit unsigned integer is used to track the amount of damage accumulated for Bide,
        and to store data for certain accuracy-related bugs.

        You can read more in the libpkmn docs:
        https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md#Volatiles
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
        """
        Set the volatile state of the active Pokémon of a player.

        This 16-bit unsigned integer is used to track the amount of damage accumulated for Bide,
        and to store data for certain accuracy-related bugs.

        You can read more in the libpkmn docs:
        https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md#Volatiles
        """
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['state'] // 8)
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_state)

    def substitute_hp(self, player: Player) -> int:
        """Get the HP of the Substitute up on a player's side."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['substitute'] // 8)
        assert LAYOUT_OFFSETS['Volatiles']['substitute'] % 8 == 0
        return self._pkmn_battle.bytes[offset]

    def set_substitute_hp(self, player: Player, new_hp: int) -> None:
        """Set the HP of the Substitute up on a player's side."""
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
        """Set the types of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        self._pkmn_battle.bytes[offset] = pack_two_u4s(
            TYPES.index(new_types[0]),
            TYPES.index(new_types[1 if len(new_types) == 2 else 0]),
        )

    def transformed_into(self, player: Player) -> Tuple[Player, PokemonSlot]:
        """Get the player and slot of the Pokémon that the active Pokémon transformed into."""
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
        slot = cast(PokemonSlot, transform_u4 & 3)
        return (Player.P1 if (transform_u4 >> 3) == 0 else Player.P2, slot)

    def set_transformed_into(
        self,
        player: Player,
        new_transformed_into: Tuple[Player, PokemonSlot]
    ) -> None:
        """Set the player and slot that the active Pokémon transformed into."""
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
        """Get data about a Disabled move of the active Pokémon of a player."""
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
        """Set data about a Disabled move of the active Pokémon of a player."""
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
        """Get the Toxic counter of the active Pokémon of a player."""
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
        """Set the Toxic counter of the active Pokémon of a player."""
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
        """Get the current turn."""
        offset = LAYOUT_OFFSETS['Battle']['turn']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_turn(self, new_turn: int) -> None:
        """Set the current turn."""
        offset = LAYOUT_OFFSETS['Battle']['turn']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_turn)

    def last_damage(self) -> int:
        """Get the last damage dealt."""
        offset = LAYOUT_OFFSETS['Battle']['last_damage']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_last_damage(self, new_last_damage: int) -> None:
        """Set the last damage dealt."""
        offset = LAYOUT_OFFSETS['Battle']['last_damage']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_last_damage)

    def last_used_move_index(self, player: Player) -> int:
        """
        Get the index within the move array of the Pokémon that was active when the move was used
        of the last move used by a given player.
        """
        offset = LAYOUT_OFFSETS['Battle']['last_selected_indexes'] + player
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def current_hp(self, player: Player, pokemon: PokemonSlot) -> int:
        """Get the current HP of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['hp']
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def set_current_hp(self, player: Player, pokemon: PokemonSlot, new_hp: int) -> None:
        """Set the current HP of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['hp']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_hp)

    def stats(self, player: Player, pokemon: PokemonSlot) -> Gen1StatData:
        """Get the stats of a Pokémon."""
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
        pokemon: PokemonSlot,
        new_stats: PartialGen1StatData,
    ) -> None:
        """Set the stats of a Pokémon."""
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
    def moves(self, player: Player, pokemon: Union[PokemonSlot, Literal['Active']]) -> Moveset:
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
        pokemon: Union[PokemonSlot, Literal['Active']]
    ) -> Tuple[int, ...]:
        """Get the PP left of a Pokémon's moves."""
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
        pokemon: Union[PokemonSlot, Literal['Active']]
    ) -> Tuple[MovePP, ...]:
        """Get the moves of a Pokémon with their PP."""
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
        return tuple(
            (MOVE_ID_LOOKUP[bytes[offset + n]], bytes[offset + n + 1]) \
                for n in range(0, 8, 2) \
                if bytes[offset + n] != 0
        )

    def set_moves(
        self,
        player: Player,
        pokemon: Union[PokemonSlot, Literal['Active']],
        new_moves: Tuple[MovePP, MovePP, MovePP, MovePP]
    ) -> None:
        """Set the moves of a Pokémon."""
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

    def status(self, player: Player, pokemon: PokemonSlot) -> Status:
        """Get the status of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        return Status(self._pkmn_battle.bytes[offset])

    def set_status(self, player: Player, pokemon: PokemonSlot, new_status: Status) -> None:
        """Set the status of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        self._pkmn_battle.bytes[offset] = new_status._value
    # optimization: make Species an enum to avoid lookups
    def species(self, player: Player, pokemon: PokemonSlot) -> str:
        """Get the species of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_species(self, player: Player, pokemon: PokemonSlot, new_species: str) -> None:
        """Set the species of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def types(self, player: Player, pokemon: PokemonSlot) -> Union[Tuple[str, str],  Tuple[str]]:
        """Get the types of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1],)

    def set_types(self, player: Player, pokemon: PokemonSlot, new_types: Tuple[str, str]) -> None:
        """Set the types of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['types']
        self._pkmn_battle.bytes[offset] = pack_two_u4s(
            TYPES.index(new_types[0]),
            TYPES.index(new_types[1])
        )

    def level(self, player: Player, pokemon: PokemonSlot) -> int:
        """Get the level of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        return self._pkmn_battle.bytes[offset]

    def set_level(self, player: Player, pokemon: PokemonSlot, new_level: int) -> None:
        """Set the level of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        self._pkmn_battle.bytes[offset] = new_level

    def update(self, p1_choice: Choice, p2_choice: Choice) -> Tuple[Result, List[int]]:
        """Update the battle with the given choice.

        Args:
            p1_choice (Choice): The choice to make for player 1.
            p2_choice (Choice): The choice to make for player 2.

        Returns:
            Tuple[Result, List[int]]: The result of the choice,
            and the trace as a list of protocol bytes
        """
        return self.update_raw(p1_choice._pkmn_choice, p2_choice._pkmn_choice)

    def update_raw(self, p1_choice: int, p2_choice: int) -> Tuple[Result, List[int]]:
        """Update the battle with the given choice.

        This method accepts raw integers for choices instead of Choice objects.
        If you don't get these from possible_choices() with raw=True, things may go wrong.

        Args:
            p1_choice (int): The choice to make for player 1.
            p2_choice (int): The choice to make for player 2.

        Returns:
            Tuple[Result, List[int]]: The result of the choice,
            and the trace as a list of protocol bytes
        """
        _pkmn_result = self._libpkmn.lib.pkmn_gen1_battle_update(
            self._pkmn_battle,          # pkmn_gen1_battle *battle
            p1_choice,     # pkmn_choice c1
            p2_choice,     # pkmn_choice c2
            self.trace_buf,                  # uint8_t *buf
            self._libpkmn.lib.PKMN_GEN1_LOGS_SIZE,     # size_t len
        )

        result = Result(_pkmn_result, libpkmn=self._libpkmn)
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

    def possible_choices(
        self,
        player: Player,
        previous_turn_result: Result,
    ) -> List[Choice]:
        """Get the possible choices for the given player.

            Args:
            player (Player): The player to get choices for.
            previous_turn_result (Result): The result of the previous turn
                (the first turn should be two PASS choices).

        Returns:
            List[Choice]: The possible choices.
        """
        # optimization: it might be faster actually to cache _pkmn_result in the battle??
        # This is equivalent to previous_turn_result.p<n>_choice_type().value but faster.

        num_choices = self._fill_choice_buffer(player, previous_turn_result)
        if num_choices == 0:
            raise Softlock("Zero choices are available.")

        choices: List[Choice] = []
        for i in range(num_choices):
            choices.append(Choice(self._choice_buf[i], libpkmn=self._libpkmn))
        return choices

    def possible_choices_raw(
        self,
        player: Player,
        previous_turn_result: Result,
    ) -> List[int]:
        """Get the possible choices for the given player.

        This method returns raw integers instead of Choice objects.
        If you need to inspect the choice data, use possible_choices() instead.

        You MUST consume the returned choices before calling any possible_choices method again;
        otherwise, the buffer will be overwritten.

        If the buffer is length 0, a softlock has occurred.
        possible_choices() automatically checks for this and raises an exception, but
        possible_choices_raw() does not (for speed).

        Args:
            player (Player): The player to get choices for.
            previous_turn_result (Result): The result of the previous turn
                (the first turn should be two PASS choices).

        Returns:
            List[int]: The possible choices.
        """
        num_choices = self._fill_choice_buffer(player, previous_turn_result)
        return self._choice_buf[0:num_choices]

    def _fill_choice_buffer(self, player: Player, previous_turn_result: Result) -> int:
        """Fills the battle's choice buffer with the possible choices for the given player.

        Probably don't call this.

        Args:
            player (Player): _description_
            previous_turn_result (Result): _description_

        Raises:
            Softlock: _description_

        Returns:
            int: The number of choices
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

