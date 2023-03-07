"""Loads data from JSON."""
import json
import os
from typing import List, TypedDict, Dict

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
Gen1SpeciesData = TypedDict('Gen1SpeciesData', {'stats': Gen1StatData, 'types': List[str]})

Gen2StatData = TypedDict(
    'Gen2StatData',
    {'hp': int, 'atk': int, 'def': int, 'spe': int, 'spa': int, 'spd': int},
)
Gen2SpeciesData = TypedDict(
    'Gen2SpeciesData',
    {'stats': Gen2StatData, 'types': List[str], 'gender': int},
)

SizeData = TypedDict('SizeData', {'Battle': int, 'Side': int, 'ActivePokemon': int, 'Pokemon': int})
BattleOffsets = TypedDict('BattleOffsets', {
    'sides': int,
    'turn': int,
    'last_damage': int,
    'last_selected_indexes': int,
    'rng': int,
})

SideOffsets = TypedDict('SideOffsets', {
    'pokemon': int,
    'active': int,
    'order': int,
    'last_selected_move': int,
    'last_used_move': int,
})

PokemonOffsets = TypedDict('PokemonOffsets', {
    'stats': int,
    'moves': int,
    'hp': int,
    'status': int,
    'species': int,
    'types': int,
    'level': int,
})

ActivePokemonOffsets = TypedDict('ActivePokemonOffsets', {
    'stats': int,
    'species': int,
    'types': int,
    'boosts': int,
    'volatiles': int,
    'moves': int,
})

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

VolatilesOffsets = TypedDict('VolatilesOffsets', {
    'Bide': int,
    'Thrashing': int,
    'MultiHit': int,
    'Flinch': int,
    'Charging': int,
    'Binding': int,
    'Invulnerable': int,
    'Confusion': int,
    'Mist': int,
    'FocusEnergy': int,
    'Substitute': int,
    'Recharging': int,
    'Rage': int,
    'LeechSeed': int,
    'Toxic': int,
    'LightScreen': int,
    'Reflect': int,
    'Transform': int,
    'confusion': int,
    'attacks': int,
    'state': int,
    'substitute': int,
    'transform': int,
    'disabled_duration': int,
    'disabled_move': int,
    'toxic': int,
})

OffsetData = TypedDict('OffsetData', {
    'Battle': BattleOffsets,
    'Side': SideOffsets,
    'Pokemon': PokemonOffsets,
    'ActivePokemon': ActivePokemonOffsets,
    'Stats': StatsOffsets,
    'Boosts': BoostsOffsets,
    'Volatiles': VolatilesOffsets,
})

"""A list of Pokémon type names."""
GEN1_TYPES: List[str] = data_json[0]["types"]

"""
A dictionary of Pokémon species data.

Species names are keys.
"""
GEN1_SPECIES: Dict[str, Gen1SpeciesData] = data_json[0]["species"]

"""
A dictionary of Pokémon species data.

Species names are keys, and values are libpkmn species IDs.
"""
GEN1_SPECIES_IDS: Dict[str, int] = {'None': 0}
for (index, species_name) in enumerate(list(GEN1_SPECIES.keys())):
    GEN1_SPECIES_IDS[species_name] = index + 1

GEN1_SPECIES_ID_LOOKUP: Dict[int, str] = {v: k for k, v in GEN1_SPECIES_IDS.items()}

"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""
GEN1_MOVES: Dict[str, int] = data_json[0]["moves"]

"""
A dictionary of Pokémon move data.

Move names are keys, and values are libpkmn move IDs.
"""
GEN1_MOVE_IDS: Dict[str, int] = {'None': 0}
for (index, move_name) in enumerate(list(GEN1_MOVES.keys())):
    GEN1_MOVE_IDS[move_name] = index + 1

GEN1_MOVE_ID_LOOKUP: Dict[int, str] = {v: k for k, v in GEN1_MOVE_IDS.items()}


"""A list of Pokémon type names."""
GEN2_TYPES: List[str] = data_json[1]["types"]

"""
A dictionary of Pokémon species data.

Species names are keys.
"""
GEN2_SPECIES: Dict[str, Gen2SpeciesData] = data_json[1]["species"]

"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""
GEN2_MOVES: Dict[str, int] = data_json[1]["moves"]

"""A list of Pokémon item names."""
GEN2_ITEMS: List[str] = data_json[1]["items"]

"""A list of protocol message names. Indices are what the binary protocol uses."""""
PROTOCOL_MESSAGES: List[str] = protocol_json["ArgType"]

del protocol_json["ArgType"]
"""
A dictionary whose keys are protocol message names,
and values are lists of possible values for Reason.
"""
PROTOCOL_REASONS: Dict[str, List[str]] = protocol_json

GEN1_LAYOUT_SIZES: SizeData = layout_json[0]["sizes"]
GEN1_LAYOUT_OFFSETS: OffsetData = layout_json[0]["offsets"]
