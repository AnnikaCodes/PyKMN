"""Loads data from JSON."""
import json
import os
from typing import List, TypedDict, Dict

our_directory = os.path.dirname(__file__)
json_path = os.path.join(our_directory, "..", "..", "engine", "src", "data", "data.json")
raw_json = json.load(open(json_path))

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

"""A list of Pokémon type names."""
GEN1_TYPES: List[str] = raw_json[0]["types"]

"""
A dictionary of Pokémon species data.

Species names are keys.
"""
GEN1_SPECIES: Dict[str, Gen1SpeciesData] = raw_json[0]["species"]

"""
A dictionary of Pokémon species data.

Species names are keys, and values are libpkmn species IDs.
"""
GEN1_LIBPKMN_SPECIES_IDS: Dict[str, int] = {'None': 0}
for (index, species_name) in enumerate(list(GEN1_SPECIES.keys())):
    GEN1_LIBPKMN_SPECIES_IDS[species_name] = index + 1

"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""
GEN1_MOVES: Dict[str, int] = raw_json[0]["moves"]

"""
A dictionary of Pokémon move data.

Move names are keys, and values are libpkmn move IDs.
"""
GEN1_LIBPKMN_MOVE_IDS: Dict[str, int] = {'None': 0}
for (index, move_name) in enumerate(list(GEN1_MOVES.keys())):
    GEN1_LIBPKMN_MOVE_IDS[move_name] = index + 1

"""A list of Pokémon type names."""
GEN2_TYPES: List[str] = raw_json[1]["types"]

"""
A dictionary of Pokémon species data.

Species names are keys.
"""
GEN2_SPECIES: Dict[str, Gen2SpeciesData] = raw_json[1]["species"]

"""
A dictionary of Pokémon move data.

Move names are keys, and values are PP.
"""
GEN2_MOVES: Dict[str, int] = raw_json[1]["moves"]

"""A list of Pokémon item names."""
GEN2_ITEMS: List[str] = raw_json[1]["items"]
