"""
A implementation of the @pkmn/engine benchmark for PyKMN.

See: https://github.com/pkmn/engine/blob/main/src/test/benchmark/
"""

import sys
import time
from typing import List, Set, cast, TypeVar, Iterable
from pykmn.engine.rng import ShowdownRNG
from pykmn.engine.common import ResultType, Choice, Player
from pykmn.engine.gen1 import Battle, PokemonData, Moveset
from pykmn.data.gen1 import SPECIES_IDS, Gen1StatData, MOVES

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

def generate_team(prng: ShowdownRNG) -> List[PokemonData]:
    team = []
    less_than_6 = prng.random_chance(1, 100)
    n = prng.in_range(1, 5 + 1) if less_than_6 else 6
    for _ in range(n):
        species = species_list[prng.in_range(0, 151 + 1)]
        level_less_than_100 = prng.random_chance(1, 20)
        level = prng.in_range(1, 99 + 1) if level_less_than_100 else 100
        dvs: Gen1StatData = {'hp': 15, 'atk': 15, 'def': 15, 'spe': 15, 'spc': 15}
        exp: Gen1StatData = {'hp': 65535, 'atk': 65535, 'def': 65535, 'spe': 65535, 'spc': 65535}
        for stat in dvs:
            if prng.random_chance(1, 5):
                dvs[stat] = prng.in_range(1, 15 + 1) # type: ignore
            if prng.random_chance(1, 20):
                # Stat experience is generated like this in @pkmn/engine
                exp[stat] = prng.in_range(0, 255) ** 2 # type: ignore

        # 1% of the time we have <4 moves
        num_moves = prng.in_range(1, 3 + 1) if prng.random_chance(1, 100) else 4
        moves: List[str] = []
        for _ in range(num_moves):
            move = list(MOVES)[prng.in_range(0, 164)] # 164 to exclude Struggle
            if move not in MOVES_BANISHED_TO_THE_SHADOW_REALM and move not in moves:
                moves.append(move)

        assert len(moves) <= 4
        pokemon: PokemonData = (
            species,
            cast(Moveset, tuple(moves)),
            {'level': level, 'dvs': dvs, 'exp': exp}
        )
        team.append(pokemon)
    return team

def random_pick(prng: ShowdownRNG, choices: list):
    return choices[prng.next() % len(choices)]

try:
    battles = int(sys.argv[1])
    rng_seed = int(sys.argv[2])
except IndexError:
    print(f"Usage: python3 {sys.argv[0]} <number of battles> <RNG seed>")
    sys.exit(1)

def run(battles: int, rng_seed: int):
    duration = 0
    turns = 0
    prng = ShowdownRNG.from_seed(rng_seed)
    for i in range(battles):
        battle = Battle(
            p1_team=generate_team(prng),
            p2_team=generate_team(prng),
            rng_seed=prng.seed(),
        )

        c1 = Choice.PASS()
        c2 = Choice.PASS()

        begin = time.process_time_ns()
        (result, _) = battle.update(c1, c2)
        while result.type() == ResultType.NONE:
            p1_choice = random_pick(prng, battle.possible_choices_raw(Player.P1, result))
            p2_choice = random_pick(prng, battle.possible_choices_raw(Player.P2, result))
            (result, _) = battle.update_raw(p1_choice, p2_choice)
        turns += battle.turn()
        duration += time.process_time_ns() - begin
        # TODO: do we need to fix the PRNG seed since it's a passed-by-value Python int?

    print(
        f"Ran {battles} battles in {duration} ns ({int((battles / duration) * 10**9)} battles/sec). " +
        f"There were a total of {turns} turns, and the final PRNG seed was {prng.seed()}."
    )

# import cProfile
# cProfile.run('run(battles, rng_seed)', sort='cumtime')
run(battles, rng_seed)
