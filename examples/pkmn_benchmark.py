"""A implementation of the @pkmn/engine benchmark for PyKMN.

See: https://github.com/pkmn/engine/blob/main/src/test/benchmark/
"""

import sys
import time
import random
from typing import cast, TypeVar, List
from pykmn.engine.rng import ShowdownRNG
from pykmn.engine.common import ResultType, Player
from pykmn.engine.gen1 import Battle, PokemonData, Moveset
from pykmn.data.gen1 import SPECIES_IDS, Gen1StatData, MOVES
from pykmn.engine.libpkmn import libpkmn_no_trace, libpkmn_trace, libpkmn_showdown_trace, \
    libpkmn_showdown_no_trace, LibpkmnBinding

# https://github.com/pkmn/engine/blob/main/src/test/blocklist.json
MOVES_BANISHED_TO_THE_SHADOW_REALM: List[str] = [
    "Bind",
    "Wrap",
    "Counter",
    "Fire Spin",
    "Rage",
    "Mimic",
    "Bide",
    "Metronome",
    "Mirror Move",
    "Clamp",
    "Transform",
]

species_list: List[str] = list(SPECIES_IDS)
assert len(species_list) == 151 + 1
moves_list: List[str] = list(MOVES)
assert len(moves_list) == 165

def new_seed(prng: ShowdownRNG) -> int:
    """Creates a new seed from an existing RNG, like the @pkmn/engine benchmark.

    Args:
        prng (`ShowdownRNG`): The RNG to use.

    Returns:
        **`int`**: A new 64-bit RNG seed.
    """
    return (
        (prng.in_range(0, 0x10000) << 48) |
        (prng.in_range(0, 0x10000) << 32) |
        (prng.in_range(0, 0x10000) << 16) |
        prng.in_range(0, 0x10000)
    )

def generate_team(prng: ShowdownRNG) -> List[PokemonData]:
    """Generates a random team of Pokémon, like the @pkmn/engine benchmark.

    Args:
        prng (`ShowdownRNG`): The RNG to use.

    Returns:
        **`List[PokemonData]`**: A list of Pokémon data.
    """
    team = []
    n = 6
    if prng.random_chance(1, 100):
        n = prng.in_range(1, 5 + 1)

    for _ in range(n):
        species = species_list[prng.in_range(1, 151 + 1)]
        level = 100
        if prng.random_chance(1, 20):
            level = prng.in_range(1, 99 + 1)

        dvs: Gen1StatData = {'hp': 15, 'atk': 15, 'def': 15, 'spe': 15, 'spc': 15}
        exp: Gen1StatData = {'hp': 65535, 'atk': 65535, 'def': 65535, 'spe': 65535, 'spc': 65535}
        for stat in ['atk', 'def', 'spe', 'spc']:
            if prng.random_chance(1, 5):
                dvs[stat] = prng.in_range(1, 15 + 1) # type: ignore
        dvs['hp'] = ((dvs['atk'] % 2) * 8) + \
            ((dvs['def'] % 2) * 4) + \
            ((dvs['spe'] % 2) * 2) + \
            (dvs['spc'] % 2)
        for stat in ['hp', 'atk', 'def', 'spe', 'spc']:
            if prng.random_chance(1, 20):
                exp[stat] = prng.in_range(0, 0xFFFF + 1) # type: ignore

        # 1% of the time we have <4 moves
        num_moves = 4
        if prng.random_chance(1, 100):
            num_moves = prng.in_range(1, 3 + 1)
        moves: List[str] = []
        # print(f"before moveloop: {u64_to_4_u16s(prng.seed())}")
        while len(moves) < num_moves:
            move = list(MOVES)[prng.in_range(1, 164 + 1) - 1] # 164 to exclude Struggle
            if move not in MOVES_BANISHED_TO_THE_SHADOW_REALM and move not in moves:
                moves.append(move)
                # print(f"adding move: {move.replace(' ', '').lower()}")
        # print(f"after moveloop: {u64_to_4_u16s(prng.seed())}")
        assert len(moves) <= 4
        pokemon: PokemonData = (
            species,
            cast(Moveset, tuple(moves)),
            {'level': level, 'dvs': dvs, 'exp': exp}
        )
        team.append(pokemon)
    # print(f"after genteam: {u64_to_4_u16s(prng.seed())}")
    return team

T = TypeVar('T')
def random_pick(prng: ShowdownRNG, choices: List[T]) -> T:
    """Picks a random element from a list with a ShowdownRNG.

    Args:
        prng (`ShowdownRNG`): The RNG to use.
        choices (`List[T]`): The list to pick from.

    Returns:
        **`T`**: The randomly chosen element.
    """
    return choices[prng.in_range(0, len(choices))]

try:
    battles = int(sys.argv[1])
    rng_seed = int(sys.argv[2])
except IndexError:
    print(f"Usage: python3 {sys.argv[0]} <number of battles> <RNG seed>")
    sys.exit(1)

def run(battles: int, rng_seed: int, libpkmn: LibpkmnBinding) -> None:
    """Runs the libpkmn-style benchmark.

    Args:
        battles (`int`): The number of battles to run.
        rng_seed (`int`): The initial seed to use for the RNG.
        libpkmn (`LibpkmnBinding`): The libpkmn binding to use.
    """
    duration = 0
    turns = 0
    prng = ShowdownRNG.from_seed(rng_seed)

    for _ in range(battles):
        p1_team = generate_team(prng)
        p2_team = generate_team(prng)
        battle_seed = new_seed(prng)

        battle = Battle(
            p1_team=p1_team,
            p2_team=p2_team,
            rng_seed=battle_seed if libpkmn.lib.IS_SHOWDOWN_COMPATIBLE else \
                [prng.in_range(0, 256) for _ in range(10)],
            libpkmn=libpkmn,
        )

        c1 = 0
        c2 = 0

        p1seed = new_seed(prng)
        p1_prng = ShowdownRNG.from_seed(p1seed)
        p2_prng = ShowdownRNG.from_seed(new_seed(prng))

        begin = time.process_time_ns()
        (result, _) = battle.update_raw(c1, c2)
        while result.type() == ResultType.NONE:
            c1 = random_pick(p1_prng, battle.possible_choices_raw(Player.P1, result))
            c2 = random_pick(p2_prng, battle.possible_choices_raw(Player.P2, result))
            (result, _) = battle.update_raw(c1, c2)
        turns += battle.turn()
        duration += time.process_time_ns() - begin

    bps = int((battles / duration) * 10**9)
    if len(sys.argv) > 3 and sys.argv[3] == '--benchmark':
        print('[{"name":"PyKMN FFI Benchmark","unit":"battles/second","value":' + str(bps) + '}]')
    else:
        print(
            f"=> Ran {battles} battles in {duration} ns ({bps} battles/sec). " +
            f"There were a total of {turns} turns, and the final PRNG seed was {prng.seed()}."
        )

libpkmns = [
    libpkmn_showdown_no_trace,
    libpkmn_showdown_trace,
    libpkmn_trace, libpkmn_no_trace,
]
random.shuffle(libpkmns)
for libpkmn in libpkmns:
    print(f"Using libpkmn: {libpkmn}")
    run(battles, rng_seed, libpkmn)
