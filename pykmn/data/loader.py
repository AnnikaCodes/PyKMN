"""Loads data from JSON."""
import json
import os
from typing import TypedDict, List, Dict

our_directory = os.path.dirname(__file__)

data_json_path = os.path.join(our_directory, "data.json")
data_json = json.load(open(data_json_path))

protocol_json_path = os.path.join(our_directory, "protocol.json")
protocol_json = json.load(open(protocol_json_path))

layout_json_path = os.path.join(our_directory, "layout.json")
layout_json = json.load(open(layout_json_path))

Gen1StatData = TypedDict(
    'Gen1StatData',
    {'hp': int, 'atk': int, 'def': int, 'spe': int, 'spc': int},
)
"""Data about Pokémon stats in Generation I.

This is a dictionary with the following keys:
* `hp` (`int`): the Pokémon's HP stat
* `atk` (`int`): the Pokémon's Attack stat
* `def` (`int`): the Pokémon's Defense stat
* `spe` (`int`): the Pokémon's Speed stat
* `spc` (`int`): the Pokémon's Special stat
"""

PartialGen1StatData = TypedDict(
    'PartialGen1StatData',
    {'hp': int, 'atk': int, 'def': int, 'spe': int, 'spc': int},
    total=False,
)
"""Like `Gen1StatData`, but with optional keys."""

class Gen1SpeciesData(TypedDict):
    """Data about Pokémon species in Generation I.

    This is a dictionary with the following keys:
    * `stats`: a `Gen1StatData` dictionary
    * `types`: a list of the Pokémon's types
    """
    stats: Gen1StatData
    types: List[str]


Gen2StatData = TypedDict(
    'Gen2StatData',
    {'hp': int, 'atk': int, 'def': int, 'spe': int, 'spa': int, 'spd': int},
)
"""Data about Pokémon stats in Generation II.

This is a dictionary with the following keys:
* `hp` (`int`): the Pokémon's HP stat
* `atk` (`int`): the Pokémon's Attack stat
* `def` (`int`): the Pokémon's Defense stat
* `spe` (`int`): the Pokémon's Speed stat
* `spa` (`int`): the Pokémon's Special Attack stat
* `spd` (`int`): the Pokémon's Special Defense stat
"""

class Gen2SpeciesData(TypedDict):
    """Data about Pokémon species in Generation II.

    This is a dictionary with the following keys:
    * `stats`: a `Gen2StatData` dictionary
    * `types`: a list of the Pokémon's types
    * `gender`: the Pokémon's % female (as a proportion out of 254) or 255 if genderless
    """
    stats: Gen2StatData
    types: List[str]
    gender: int

class SizeData(TypedDict):
    """A dictionary containing sizes for various libpkmn data structures.

    Keys:
    * `Battle` (`int`): the size of a `Battle` struct
    * `Side` (`int`): the size of a `Side` struct
    * `ActivePokemon` (`int`): the size of an `ActivePokemon` struct
    * `Pokemon` (`int`): the size of a `Pokemon` struct
    """
    Battle: int
    Side: int
    ActivePokemon: int
    Pokemon: int

class BattleOffsets(TypedDict):
    """A dictionary of offsets for Battle data structures."""
    sides: int
    turn: int
    last_damage: int
    last_selected_indexes: int
    rng: int

class SideOffsets(TypedDict):
    """A dictionary of offsets for Side data structures."""
    pokemon: int
    active: int
    order: int
    last_selected_move: int
    last_used_move: int

class PokemonOffsets(TypedDict):
    """A dictionary of offsets for Pokemon data structures."""
    stats: int
    moves: int
    hp: int
    status: int
    species: int
    types: int
    level: int

class ActivePokemonOffsets(TypedDict):
    """A dictionary of offsets for ActivePokemon data structures."""
    stats: int
    species: int
    types: int
    boosts: int
    volatiles: int
    moves: int

StatsOffsets = TypedDict('StatsOffsets', {
    'hp': int,
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
})

BoostsOffsets = TypedDict('BoostsOffsets', {
    'atk': int,
    'def': int,
    'spe': int,
    'spc': int,
    'accuracy': int,
    'evasion': int,
})
"""A dictionary of offsets for stat boosts within libpkmn's data."""

class VolatilesOffsets(TypedDict):
    """A dictionary of volatile statuses and their offsets within libpkmn's data."""
    Bide: int
    Thrashing: int
    MultiHit: int
    Flinch: int
    Charging: int
    Binding: int
    Invulnerable: int
    Confusion: int
    Mist: int
    FocusEnergy: int
    Substitute: int
    Recharging: int
    Rage: int
    LeechSeed: int
    Toxic: int
    LightScreen: int
    Reflect: int
    Transform: int
    confusion: int
    attacks: int
    state: int
    substitute: int
    transform: int
    disabled_duration: int
    disabled_move: int
    toxic: int

class OffsetData(TypedDict):
    """A dictionary of offsets for various libpkmn data structures."""
    Battle: BattleOffsets
    Side: SideOffsets
    Pokemon: PokemonOffsets
    ActivePokemon: ActivePokemonOffsets
    Stats: StatsOffsets
    Boosts: BoostsOffsets
    Volatiles: VolatilesOffsets

GEN1_TYPES: List[str] = data_json[0]["types"]
"""A list of Pokémon type names."""

GEN1_SPECIES: Dict[str, Gen1SpeciesData] = data_json[0]["species"]
"""
A dictionary of Pokémon species data.

Species names are keys.
"""

GEN1_SPECIES_IDS: Dict[str, int] = {'None': 0}
"""
A dictionary of Pokémon species data.

Species names are keys, and values are libpkmn species IDs.
"""

for (index, species_name) in enumerate(list(GEN1_SPECIES.keys())):
    GEN1_SPECIES_IDS[species_name] = index + 1

GEN1_SPECIES_ID_LOOKUP: Dict[int, str] = {v: k for k, v in GEN1_SPECIES_IDS.items()}
"""A speciesID:speciesName lookup table."""

GEN1_MOVES: Dict[str, int] = data_json[0]["moves"]
"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""

GEN1_MOVE_IDS: Dict[str, int] = {'None': 0}
"""
A dictionary of Pokémon move data.

Move names are keys, and values are libpkmn move IDs.
"""
for (index, move_name) in enumerate(list(GEN1_MOVES.keys())):
    GEN1_MOVE_IDS[move_name] = index + 1

GEN1_MOVE_ID_LOOKUP: Dict[int, str] = {v: k for k, v in GEN1_MOVE_IDS.items()}
"""A moveID:moveName lookup table."""

GEN2_TYPES: List[str] = data_json[1]["types"]
"""A list of Pokémon type names."""

GEN2_SPECIES: Dict[str, Gen2SpeciesData] = data_json[1]["species"]
"""
A dictionary of Pokémon species data.

Species names are keys.
"""

GEN2_MOVES: Dict[str, int] = data_json[1]["moves"]
"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""

GEN2_ITEMS: List[str] = data_json[1]["items"]
"""A list of Pokémon item names."""

PROTOCOL_MESSAGES: List[str] = protocol_json["ArgType"]
"""A list of protocol message names. Indices are what the binary protocol uses."""""

del protocol_json["ArgType"]
PROTOCOL_REASONS: Dict[str, List[str]] = protocol_json
"""
A dictionary whose keys are protocol message names,
and values are lists of possible values for Reason.
"""

GEN1_LAYOUT_SIZES: SizeData = layout_json[0]["sizes"]
GEN1_LAYOUT_OFFSETS: OffsetData = layout_json[0]["offsets"]
