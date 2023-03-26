"""
A implementation of the @pkmn/engine benchmark for PyKMN.

See: https://github.com/pkmn/engine/blob/main/src/test/benchmark/
"""

import sys
import time
import random
from typing import List, Set, cast
from pykmn.engine.rng import ShowdownRNG
from pykmn.engine.common import ResultType, Choice, Player
from pykmn.engine.gen1 import Battle, PokemonData, Moveset
from pykmn.data.gen1 import SPECIES_IDS, Gen1StatData, MOVES
from pykmn.engine.libpkmn import libpkmn_no_trace, libpkmn_trace, libpkmn_showdown_trace, \
    libpkmn_showdown_no_trace, LibpkmnBinding

# https://github.com/pkmn/engine/blob/main/src/test/blocklist.json
MOVES_BANISHED_TO_THE_SHADOW_REALM: Set[str] = set([
    "Bind",
    "Wrap",
    "Counter"
    "Fire Spin",
    "Rage",
    "Mimic",
    "Bide",
    "Metronome",
    "Mirror Move",
    "Clamp",
    "Transform",
])

species_list: List[str] = list(SPECIES_IDS)
assert len(species_list) == 151 + 1
moves_list: List[str] = list(MOVES)
assert len(moves_list) == 165

# big endian
def u64_to_4_u16s(seed: int):
    return ",".join([str(x) for x in[
        (seed >> 48) & 0xFFFF,
        (seed >> 32) & 0xFFFF,
        (seed >> 16) & 0xFFFF,
        seed & 0xFFFF,
    ]])

def new_seed(prng: ShowdownRNG) -> int:
    # print(f"in newseed: {u64_to_4_u16s(prng.seed())}")
    # https://github.com/pkmn/engine/blob/main/src/test/integration/common.ts#L505-L507
    return (
        (prng.in_range(0, 0x10000) << 48) |
        (prng.in_range(0, 0x10000) << 32) |
        (prng.in_range(0, 0x10000) << 16) |
        prng.in_range(0, 0x10000)
    )

def generate_team(prng: ShowdownRNG) -> List[PokemonData]:
    # print(f"before genteam: {u64_to_4_u16s(prng.seed())}")
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

def random_pick(prng: ShowdownRNG, choices: list):
    return choices[prng.in_range(0, len(choices))]

try:
    battles = int(sys.argv[1])
    rng_seed = int(sys.argv[2])
except IndexError:
    print(f"Usage: python3 {sys.argv[0]} <number of battles> <RNG seed>")
    sys.exit(1)

def run(battles: int, rng_seed: int, libpkmn: LibpkmnBinding):
    duration = 0
    turns = 0
    prng = ShowdownRNG.from_seed(rng_seed)
    # print(f"RNG seed: {rng_seed}")

    for i in range(battles):
        battle_seed = new_seed(prng)
        p1_team = generate_team(prng)
        p2_team = generate_team(prng)
        battle = Battle(
            p1_team=p1_team,
            p2_team=p2_team,
            rng_seed=battle_seed if libpkmn.lib.IS_SHOWDOWN_COMPATIBLE else \
                [prng.in_range(0, 256) for _ in range(10)],
            libpkmn=libpkmn,
        )
        # print(f"TEAM1: {p1_team}")
        # print(f"TEAM2: {p2_team}")

        # slots = (
        #     [x[0] for x in p1_team],
        #     [x[0] for x in p2_team],
        # )
        c1 = Choice.PASS()
        c2 = Choice.PASS()

        p1seed = new_seed(prng)
        # print(f"p1seed: {u64_to_4_u16s(p1seed)}")
        p1_prng = ShowdownRNG.from_seed(p1seed)
        p2_prng = ShowdownRNG.from_seed(new_seed(prng))

        # print(f"----- BEGINNING BATTLE {i}-----")
        begin = time.process_time_ns()
        (result, trace) = battle.update(c1, c2)
        # print("\n".join(parse_protocol(trace, slots)))
        while result.type() == ResultType.NONE:
            p1_choice = random_pick(p1_prng, battle.possible_choices_raw(Player.P1, result))
            p2_choice = random_pick(p2_prng, battle.possible_choices_raw(Player.P2, result))
            (result, trace) = battle.update_raw(p1_choice, p2_choice)
            # print("\n".join(parse_protocol(trace, slots)))
            # print(f"original PRNG seed: {prng.seed()}")
        turns += battle.turn()
        duration += time.process_time_ns() - begin
        # TODO: do we need to fix the PRNG seed since it's a passed-by-value Python int?

    bps = int((battles / duration) * 10**9)
    if len(sys.argv) > 3 and sys.argv[3] == '--benchmark':
        print('[{"name":"PyKMN FFI Benchmark","unit":"battles/second","value":' + str(bps) + '}]')
    else:
        print(
            f"=> Ran {battles} battles in {duration} ns ({bps} battles/sec). " +
            f"There were a total of {turns} turns, and the final PRNG seed was {prng.seed()}."
        )

# import cProfile
# cProfile.run('run(battles, rng_seed)', sort='cumtime')
libpkmns = [
    libpkmn_showdown_no_trace,
    libpkmn_showdown_trace,
    libpkmn_trace, libpkmn_no_trace,
]
random.shuffle(libpkmns)
for libpkmn in libpkmns:
    print(f"Using libpkmn: {libpkmn}")
    run(battles, rng_seed, libpkmn)
