"""Battle simulation for Generation I."""
from _pkmn_engine_bindings import lib, ffi  # type: ignore
from pykmn.engine.common import Result, Player, ChoiceType, Softlock, Choice, \
    pack_u16_as_bytes, unpack_u16_from_bytes, pack_two_u4s, unpack_two_u4s, \
    pack_two_i4s, unpack_two_i4s, insert_unsigned_int_at_offset, extract_unsigned_int_at_offset \
    # noqa: F401
from pykmn.engine.rng import ShowdownRNG
from pykmn.data.gen1 import Gen1StatData, MOVE_IDS, SPECIES_IDS, PartialGen1StatData, \
    SPECIES, TYPES, MOVES, LAYOUT_OFFSETS, LAYOUT_SIZES, MOVE_ID_LOOKUP, SPECIES_ID_LOOKUP

from typing import List, Tuple, cast, TypedDict, Literal
from enum import Enum, IntEnum
import math
import random

# optimization possible here: don't copy in intialization if it's all 0 anyway?
# optimization possible: use indices for LAYOUT_* instead of dict keys

MovePP = Tuple[str, int]
FullMoveset = Tuple[str, str, str, str]
Moveset = FullMoveset | Tuple[str] | Tuple[str, str] | Tuple[str, str, str]

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


SpeciesName = str
ExtraPokemonData = TypedDict('ExtraPokemonData', {
    'hp': int, 'status': int, 'level': int, 'stats': Gen1StatData,
    'types': Tuple[str, str], 'move_pp': Tuple[int, int, int, int],
    'dvs': Gen1StatData, 'exp': Gen1StatData,
}, total=False)
PokemonData = Tuple[SpeciesName, Moveset] | Tuple[SpeciesName, Moveset, ExtraPokemonData]

class Pokemon:
    """A Pokémon in a Generation I battle."""

    def __init__(self, _bytes):
        """Construct a new Pokemon object.

        Users shouldn't use this, but instead use the Battle constructor.
        """
        assert len(_bytes) == LAYOUT_SIZES['Pokemon'], \
            f"Pokemon data bytes must be {LAYOUT_SIZES['Pokemon']} long."
        self._bytes = _bytes

    def initialize(self, data: PokemonData):
        """Initializes the Pokémon's data, overwriting its data buffer with new values.

        Stats, types, and move PP are inferred based on the provided species and move names,
        but can optionally be specified.

        Args:
            data (PokemonData): The data to initialize the Pokémon with.
                The first value should be the species name,
                and the second value should be a Moveset with the Pokémon's moves.
                Optionally, a third value can be specified,
                a dictionary with any of the following keys:
                    * hp (int): The amount of HP the Pokémon has; defaults to its max HP.
                    * status (int): The Pokémon's status code. Defaults to healthy.
                    * level (int): The Pokémon's level. Defaults to 100.
                    * stats (Gen1StatData): The Pokémon's stats.
                        By default, will be determined based on its species & level.
                    * types (Tuple[str, str]): The Pokémon's types.
                        By default, determined by its species.
                    * move_pp (Tuple[int, int, int, int]): PP values for each move.
                        By default, determined by the move's max PP.
                    * dvs (Gen1StatData): The Pokémon's DVs. Defaults to 15 in all stats.
                    * exp (Gen1StatData): The Pokémon's stat experience. Defaults to 65535 in all.
        """

        hp = None
        status = 0
        level = 100
        stats = None
        types = None
        move_pp = None
        dvs: Gen1StatData = {'hp': 15, 'atk': 15, 'def': 15, 'spe': 15, 'spc': 15}
        exp: Gen1StatData = {'hp': 65535, 'atk': 65535, 'def': 65535, 'spe': 65535, 'spc': 65535}
        if len(data) == 3:
            species_name, move_names, extra_data = \
                cast(Tuple[SpeciesName, Moveset, ExtraPokemonData], data)
            # possible optimization: is it faster to pass this as an array/extra parameters
            # and avoid dict lookups?
            if 'hp' in extra_data:
                hp = extra_data['hp']
            if 'status' in extra_data:
                status = extra_data['status']
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
            species_name, move_names = cast(Tuple[SpeciesName, Moveset], data)

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
                        stats[stat],  # type: ignore
                        stat == 'hp',
                        level,
                        dvs[stat], # type: ignore
                        exp[stat], # type: ignore
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

        offset = LAYOUT_OFFSETS['Pokemon']['stats']
        # pack stats
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            self._bytes[offset:offset + 2] = pack_u16_as_bytes(stats[stat]) # type: ignore
            offset += 2
        assert offset == LAYOUT_OFFSETS['Pokemon']['moves']

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
            self._bytes[offset] = move_id
            offset += 1
            self._bytes[offset] = pp
            offset += 1
        assert offset == LAYOUT_OFFSETS['Pokemon']['hp']

        # pack HP
        self._bytes[offset:offset + 2] = pack_u16_as_bytes(hp)
        offset += 2
        assert offset == LAYOUT_OFFSETS['Pokemon']['status']

        # pack status
        self._bytes[offset] = status
        offset += 1
        assert offset == LAYOUT_OFFSETS['Pokemon']['species']

        # pack species
        self._bytes[offset] = SPECIES_IDS[species_name]
        offset += 1
        assert offset == LAYOUT_OFFSETS['Pokemon']['types']

        # pack types
        self._bytes[offset] = pack_two_u4s(TYPES.index(types[0]), TYPES.index(types[1]))
        offset += 1
        assert offset == LAYOUT_OFFSETS['Pokemon']['level']

        # pack level
        self._bytes[offset] = level
        offset += 1
        assert offset == LAYOUT_SIZES['Pokemon']

    def stats(self) -> Gen1StatData:
        """Get the Pokémon's current stats.

        Returns:
            Gen1StatData: The current stats.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['stats']
        stats = {}
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            (byte1, byte2) = self._bytes[offset:offset + 2]
            stats[stat] = unpack_u16_from_bytes(byte1, byte2)
            offset += 2
        return cast(Gen1StatData, stats)

    def moves(self) -> Moveset:
        """
        Get the Pokémon's moves.

        Returns:
            Tuple[str, str, str, str]: The Pokémon's moves.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['moves']
        return tuple(
            MOVE_ID_LOOKUP[self._bytes[offset + n]] \
                for n in range(0, 8, 2) \
                if self._bytes[offset + n] != 0
        ) # type: ignore

    def pp_left(self) -> Tuple[int, ...]:
        """Get the Pokémon's PP left for each move.

        Returns:
            Tuple[int, ...]: The PP left for each move. Length is equal to the number of moves.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['moves']
        return tuple(
            self._bytes[offset + n] \
                for n in range(1, 9, 2) \
                if self._bytes[offset + n - 1] != 0 # if move exists
        )

    def moves_with_pp(self) -> Tuple[MovePP, ...]:
        """Get the Pokémon's moves with their PP left.

        Returns:
            Tuple[MovePP, MovePP, MovePP, MovePP]: The moves with their PP left.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['moves']
        return tuple(
            (MOVE_ID_LOOKUP[self._bytes[offset + n]], cast(int, self._bytes[offset + n + 1])) \
                for n in range(0, 8, 2) \
                if self._bytes[offset + n] != 0
        )


    def hp(self) -> int:
        """Get the Pokémon's current HP.

        Returns:
            int: The current HP.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['hp']
        (byte1, byte2) = self._bytes[offset:offset + 2]
        return unpack_u16_from_bytes(byte1, byte2)

    def status(self) -> int:
        """Get the Pokémon's status.

        Returns:
            int: The status.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['status']
        return self._bytes[offset]

    def species(self) -> str:
        """Get the Pokémon's species.

        Returns:
            str: The species.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['species']
        return SPECIES_ID_LOOKUP[self._bytes[offset]]

    def types(self) -> Tuple[str, str]:
        """Get the Pokémon's types.

        Returns:
            Tuple[str, str]: The types.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['types']
        (type1, type2) = unpack_two_u4s(self._bytes[offset])
        return (TYPES[type1], TYPES[type2])

    def level(self) -> int:
        """Get the Pokémon's level.

        Returns:
            int: The level.
        """
        offset = LAYOUT_OFFSETS['Pokemon']['level']
        return self._bytes[offset]


# MAJOR TODO!
# * incorporate ActivePokemon stuff into Battle methods
#   https://github.com/pkmn/engine/blob/main/src/lib/gen1/data.zig#L99-L105
# * remove subclasses and put all initialization into the Battle class for s p e e d
# * properly handle status
# * write unit tests
# * make all constructors check array lengths, etc, for validity
# * write a LOT of integration tests
# * add support for toggling -Dshowdown & -Dtrace
#    * support non-Showdown RNG
# * investigate performance and optimize
# * simplify typing as needed (and make sure everything's typed)
# * maybe more documentation?

class Side:
    """A side in a Generation I battle."""

    def __init__(self, _bytes):
        """Construct a new Side object.

        Users shouldn't use this, but instead use the Battle constructor.
        """
        self._bytes = _bytes
        team = []
        offset = LAYOUT_OFFSETS['Side']['pokemon']
        for _ in range(6):
            team.append(Pokemon(self._bytes[offset:(offset + LAYOUT_SIZES['Pokemon'])]))
            offset += LAYOUT_SIZES['Pokemon']
        assert offset == LAYOUT_OFFSETS['Side']['active']
        self.team = tuple(team)

    def initialize(
        self,
        team: List[PokemonData],
        last_selected_move: str = 'None',
        last_used_move: str = 'None'
    ):
        """Initializes the side with fresh data.

        Args:
            team (List[PokemonData]): Must be <= 6.
            last_selected_move (str, optional): Name of the last move selected. Defaults to 'None'.
            last_used_move (str, optional): Name of the last move used. Defaults to 'None'.
        """
        self._bytes[LAYOUT_OFFSETS['Side']['last_selected_move']] = MOVE_IDS[last_selected_move]
        self._bytes[LAYOUT_OFFSETS['Side']['last_used_move']] = MOVE_IDS[last_used_move]

        order = []
        # optimization: is enumerate() slow?
        assert len(team) <= 6
        for i, pokemon_data in enumerate(team):
            self.team[i].initialize(pokemon_data)
            order.append(i + 1)

        for i, slot in enumerate(order):
            self._bytes[LAYOUT_OFFSETS['Side']['order'] + i] = slot

    def last_used_move(self) -> str:
        """Gets the last move used by the side."""
        return MOVE_ID_LOOKUP[self._bytes[LAYOUT_OFFSETS['Side']['last_used_move']]]

    def last_selected_move(self) -> str:
        """Gets the last move selected by the side."""
        return MOVE_ID_LOOKUP[self._bytes[LAYOUT_OFFSETS['Side']['last_selected_move']]]

    def active_pokemon_stats(self) -> Gen1StatData:
        """Gets the stats of the active Pokémon on this side."""
        offset = LAYOUT_OFFSETS['Side']['active']
        stats = {}
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            stats[stat] = unpack_u16_from_bytes(
                self._bytes[offset],
                self._bytes[offset + 1]
            )
            offset += 2
        return cast(Gen1StatData, stats)

# Optimization: remove debug asserts

PokemonSlot = Literal[1] | Literal[2] | Literal[3] | Literal[4] | Literal[5] | Literal[6]
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
        rng_seed: int = random.randrange(0, 2**64),
    ):
        """Create a new Battle object."""
        self._pkmn_battle = ffi.new("pkmn_gen1_battle *")

        offset = LAYOUT_OFFSETS['Battle']['sides']
        self.p1 = Side(self._pkmn_battle.bytes[offset:(offset + LAYOUT_SIZES['Side'])])
        self.p1.initialize(p1_team, p1_last_selected_move, p1_last_used_move)
        offset += LAYOUT_SIZES['Side']

        self.p2 = Side(self._pkmn_battle.bytes[offset:(offset + LAYOUT_SIZES['Side'])])
        self.p2.initialize(p2_team, p2_last_selected_move, p2_last_used_move)
        offset += LAYOUT_SIZES['Side']
        assert offset == LAYOUT_OFFSETS['Battle']['turn']

        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(start_turn)
        offset += 2
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(last_damage)
        offset += 2

        # TODO: support non -Dshowdown here
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(p1_move_idx)
        offset += 2
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(p2_move_idx)
        offset += 2

        self.rng = ShowdownRNG(ffi.cast(
            "pkmn_psrng *",
            self._pkmn_battle.bytes[offset:(offset + lib.PKMN_PSRNG_SIZE)],
        ), rng_seed)

    def last_selected_move(self, player: Player) -> str:
        """Get the last move selected by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_selected_move(self, player: Player, move: str):
        """Set the last move selected by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['last_selected_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def last_used_move(self, player: Player) -> str:
        """Get the last move used by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        return MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_last_used_move(self, player: Player, move: str):
        """Set the last move used by a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['last_used_move']
        self._pkmn_battle.bytes[offset] = MOVE_IDS[move]

    def active_pokemon_stats(self, player: Player) -> Gen1StatData:
        """Get the stats of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_active_pokemon_species(self, player: Player, new_species: str) -> None:
        """Set the species of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def active_pokemon_types(self, player: Player) -> Tuple[str, str] | Tuple[str]:
        """Get the types of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1], )

    def boosts(self, player: Player) -> BoostData:
        """Get the boosts of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        volatile_uint32_ptr = ffi.cast("uint32_t *", self._pkmn_battle.bytes[offset:(offset + 4)])
        # https://stackoverflow.com/questions/9298865/get-n-th-bit-of-an-integer
        return not not(volatile_uint32_ptr[0] & (1 << volatile))

    def set_volatile(self, player: Player, volatile: VolatileFlag, value: bool) -> None:
        """Set a volatile of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        volatile_uint32_ptr = ffi.cast("uint32_t *", self._pkmn_battle.bytes[offset:(offset + 4)])
        if value:
            volatile_uint32_ptr[0] |= (1 << volatile)
        else:
            volatile_uint32_ptr[0] &= ~(1 << volatile)

    def confusion_turns_left(self, player: Player) -> int:
        """Get the confusion counter of the active Pokémon of a player."""
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['confusion']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            n=new_turns_left,
            bit_offset=bit_offset,
            n_len_bits=3,
        )

    def attacks_left(self, player: Player) -> int:
        """
        Get the attacks left counter of the active Pokémon.

        This counter is used for Bide and Thrash.
        """
        byte_offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles']
        bit_offset = LAYOUT_OFFSETS['Volatiles']['attacks']
        byte_offset += bit_offset // 8
        bit_offset %= 8

        self._pkmn_battle.bytes[byte_offset] = insert_unsigned_int_at_offset(
            byte=self._pkmn_battle.bytes[byte_offset],
            n=new_attacks_left,
            bit_offset=bit_offset,
            n_len_bits=3,
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
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['state'] // 8)
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_state)

    def substitute_hp(self, player: Player) -> int:
        """Get the HP of the Substitute up on a player's side."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['substitute'] // 8)
        assert LAYOUT_OFFSETS['Volatiles']['substitute'] % 8 == 0
        return self._pkmn_battle.bytes[offset]

    def set_substitute_hp(self, player: Player, new_hp: int) -> None:
        """Set the HP of the Substitute up on a player's side."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['volatiles'] + \
            (LAYOUT_OFFSETS['Volatiles']['substitute'] // 8)
        assert LAYOUT_OFFSETS['Volatiles']['substitute'] % 8 == 0
        self._pkmn_battle.bytes[offset] = new_hp

    def set_active_pokemon_types(
        self,
        player: Player,
        new_types: Tuple[str, str] | Tuple[str]
    ) -> None:
        """Set the types of the active Pokémon of a player."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['active'] + \
            LAYOUT_OFFSETS['ActivePokemon']['types']
        self._pkmn_battle.bytes[offset] = pack_two_u4s(
            TYPES.index(new_types[0]),
            TYPES.index(new_types[1 if len(new_types) == 2 else 0]),
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
        offset = LAYOUT_OFFSETS['Battle']['last_selected_indexes'] + player.value
        return unpack_u16_from_bytes(
            self._pkmn_battle.bytes[offset],
            self._pkmn_battle.bytes[offset + 1],
        )

    def current_hp(self, player: Player, pokemon: PokemonSlot) -> int:
        """Get the current HP of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['hp']
        self._pkmn_battle.bytes[offset:(offset + 2)] = pack_u16_as_bytes(new_hp)

    def stats(self, player: Player, pokemon: PokemonSlot) -> Gen1StatData:
        """Get the stats of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['stats']

        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            if stat in new_stats:
                self._pkmn_battle.bytes[offset:(offset + 2)] = \
                    pack_u16_as_bytes(new_stats[stat]) # type: ignore
            offset += 2

    def moves(self, player: Player, pokemon: PokemonSlot) -> Moveset:
        """Get the moves of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['moves']
        moves = tuple(
            MOVE_ID_LOOKUP[self._pkmn_battle.bytes[offset + n]] \
                for n in range(0, 8, 2) \
                if self._pkmn_battle.bytes[offset + n] != 0
        )
        return cast(Moveset, moves)

    def pp_left(self, player: Player, pokemon: PokemonSlot) -> Tuple[int, ...]:
        """Get the PP left of a Pokémon's moves."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['moves']
        return tuple(
            self._pkmn_battle.bytes[offset + n] \
                for n in range(1, 9, 2) \
                if self._pkmn_battle.bytes[offset + n - 1] != 0 # if move exists
        )

    def moves_with_pp(self, player: Player, pokemon: PokemonSlot) -> Tuple[MovePP, ...]:
        """Get the moves of a Pokémon with their PP."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
        pokemon: PokemonSlot,
        new_moves: Tuple[MovePP, MovePP, MovePP, MovePP]
    ) -> None:
        """Set the moves of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['moves']

        for i, (move, pp) in enumerate(new_moves):
            self._pkmn_battle.bytes[offset + i*2] = MOVE_IDS[move]
            self._pkmn_battle.bytes[offset + i*2 + 1] = pp

    def status(self, player: Player, pokemon: PokemonSlot) -> int:
        """Get the status of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        return self._pkmn_battle.bytes[offset]

    def set_status(self, player: Player, pokemon: PokemonSlot, new_status: int) -> None:
        """Set the status of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['status']
        self._pkmn_battle.bytes[offset] = new_status

    # optimization: make Species an enum to avoid lookups
    def species(self, player: Player, pokemon: PokemonSlot) -> str:
        """Get the species of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        return SPECIES_ID_LOOKUP[self._pkmn_battle.bytes[offset]]

    def set_species(self, player: Player, pokemon: PokemonSlot, new_species: str) -> None:
        """Set the species of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['species']
        self._pkmn_battle.bytes[offset] = SPECIES_IDS[new_species]

    def types(self, player: Player, pokemon: PokemonSlot) -> Tuple[str, str] | Tuple[str]:
        """Get the types of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['types']
        (type1, type2) = unpack_two_u4s(self._pkmn_battle.bytes[offset])
        return (TYPES[type1], TYPES[type2]) if type2 != type1 else (TYPES[type1],)

    def set_types(self, player: Player, pokemon: PokemonSlot, new_types: Tuple[str, str]) -> None:
        """Set the types of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
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
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        return self._pkmn_battle.bytes[offset]

    def set_level(self, player: Player, pokemon: PokemonSlot, new_level: int) -> None:
        """Set the level of a Pokémon."""
        offset = LAYOUT_OFFSETS['Battle']['sides'] + \
            LAYOUT_SIZES['Side'] * player.value + \
            LAYOUT_OFFSETS['Side']['pokemon'] + \
            LAYOUT_SIZES['Pokemon'] * (pokemon - 1) + \
            LAYOUT_OFFSETS['Pokemon']['level']
        self._pkmn_battle.bytes[offset] = new_level


    def update(self, p1_choice: Choice, p2_choice: Choice) -> Tuple[Result, List[int]]:
        """Update the battle with the given choice.

        Args:
            choice (Choice): The choice to make.

        Returns:
            Tuple[Result, List[int]]: The result of the choice,
            and the trace as a list of protocol bytes
        """
        trace_buf = ffi.new("uint8_t[]", lib.PKMN_GEN1_LOGS_SIZE)
        _pkmn_result = lib.pkmn_gen1_battle_update(
            self._pkmn_battle,          # pkmn_gen1_battle *battle
            p1_choice._pkmn_choice,     # pkmn_choice c1
            p2_choice._pkmn_choice,     # pkmn_choice c2
            trace_buf,                  # uint8_t *buf
            lib.PKMN_GEN1_LOGS_SIZE,     # size_t len
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
                "This should never happen; please file a bug report with PyKMN at " +
                "https://github.com/AnnikaCodes/PyKMN/issues/new"
            )
        return (result, trace_buf)

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
        raw_choices = ffi.new("pkmn_choice[]", lib.PKMN_OPTIONS_SIZE)
        requested_kind = previous_turn_result.p1_choice_type() if player == Player.P1 \
            else previous_turn_result.p2_choice_type()
        num_choices = lib.pkmn_gen1_battle_choices(
            self._pkmn_battle,      # pkmn_gen1_battle *battle
            player.value,           # pkmn_player player
            # optimization: is IntEnum more performant?
            requested_kind.value,   # pkmn_choice_kind request
            raw_choices,            # pkmn_choice out[]
            lib.PKMN_OPTIONS_SIZE,  # size_t len
        )

        if num_choices == 0:
            raise Softlock("Zero choices are available.")

        choices: List[Choice] = []
        for i in range(num_choices):
            choices.append(Choice(raw_choices[i]))
        return choices
