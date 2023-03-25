"""Test script."""
from pykmn.engine.gen1 import Battle, Player, Choice, statcalc
from pykmn.engine.common import ResultType
from pykmn.engine.protocol import parse_protocol
import random
import cProfile

def hexfmt(b):
    """Format bytes as hex."""
    battle_hex = ""
    n = 0
    for x in b:
        battle_hex += f"{x:0>2x} "
        if n % 32 == 31:
            battle_hex += "\n"
        n += 1
    return battle_hex


# https://pokepast.es/cc9b111c9f81f6a4
team1 = [
    ("Starmie", ("Psychic", "Blizzard", "Thunder Wave", "Recover")),
    ("Exeggutor", ("Sleep Powder", "Psychic", "Double-Edge", "Explosion")),
    ("Alakazam", ("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    ("Chansey", ("Ice Beam", "Thunderbolt", "Thunder Wave", "Soft-Boiled")),
    ("Snorlax", ("Body Slam", "Reflect", "Earthquake", "Rest")),
    ("Tauros", ("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]

# https://pokepast.es/7f1c2e78e6ba3194
team2 = [
    ("Jynx", ("Lovely Kiss", "Blizzard", "Psychic", "Rest")),
    ("Starmie", ("Psychic", "Thunderbolt", "Thunder Wave", "Recover")),
    ("Alakazam", ("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    ("Chansey", ("Seismic Toss", "Reflect", "Thunder Wave", "Soft-Boiled")),
    ("Snorlax", ("Body Slam", "Reflect", "Self-Destruct", "Rest")),
    ("Tauros", ("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]


def run_battle(log=False):
    """Run a battle. Returns # of turns."""
    battle = Battle(
        p1_team=team1,
        p2_team=team2,
    )
    # slots = ([p.name for p in team1], [p.name for p in team2])

    # print("Bits() battle data:\n" + hexfmt(battle._bits.bytes))
    # print("Real battle data:\n" + hexfmt(battle._pkmn_battle.bytes))
    (result, trace) = battle.update(Choice.PASS(), Choice.PASS())
    # print("---------- Battle setup ----------\nTrace: ")
    # for msg in parse_protocol(trace):
    #     print(f"* {msg}")

    choice = 1
    while result.type() == ResultType.NONE:
        if log:
            print(f"\n------------ Choice {choice} ------------")
        choice += 1
        def choices():
            for _ in range(1000):
                battle.possible_choices(Player.P1, result)


        p1_choices = battle.possible_choices_raw(Player.P1, result)
        p1_choice = p1_choices[random.randrange(len(p1_choices))]
        p2_choices = battle.possible_choices_raw(Player.P2, result)
        p2_choice = p2_choices[random.randrange(len(p2_choices))]
        # if log:
        #     print(f"Player 1: {p1_choice}\nPlayer 2: {p2_choice}")
        (result, trace) = battle.update_raw(p1_choice, p2_choice)
        # print("Bits() battle data:\n" + hexfmt(battle._bits.bytes))
        # print("Real battle data:\n" + hexfmt(battle._pkmn_battle.bytes))
        if log:
            print("\nTrace:")
            for msg in parse_protocol(trace):
                print("* " + msg)

def battle_loop(n: int) -> None:
    for _ in range(n):
        run_battle(log=False)

# battle_loop(1000)

def pchoices():
    battle = Battle(
        p1_team=team1,
        p2_team=team2,
        rng_seed=0,
    )
    (result, _) = battle.update(Choice.PASS(), Choice.PASS())
    for _ in range(100000):
        battle.possible_choices(Player.P1, result)

def statcalc_loop(n: int) -> None:
    for _ in range(n):
        statcalc(235)
cProfile.run("battle_loop(5000)", sort='cumtime')
# battle_loop(10000)
# run_battle(log=True)
