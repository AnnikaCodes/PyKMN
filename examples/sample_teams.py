"""Test script."""
from pykmn.engine.gen1 import Pokemon, Battle, Side, Player, Choice, ChoiceType
from pykmn.engine.common import ResultType
from pykmn.engine.rng import ShowdownRNG
from pykmn.engine.protocol import parse_protocol

import random


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
    Pokemon.new("Starmie", ("Psychic", "Blizzard", "Thunder Wave", "Recover")),
    Pokemon.new("Exeggutor", ("Sleep Powder", "Psychic", "Double-Edge", "Explosion")),
    Pokemon.new("Alakazam", ("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    Pokemon.new("Chansey", ("Ice Beam", "Thunderbolt", "Thunder Wave", "Soft-Boiled")),
    Pokemon.new("Snorlax", ("Body Slam", "Reflect", "Earthquake", "Rest")),
    Pokemon.new("Tauros", ("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]

# https://pokepast.es/7f1c2e78e6ba3194
team2 = [
    Pokemon.new("Jynx", ("Lovely Kiss", "Blizzard", "Psychic", "Rest")),
    Pokemon.new("Starmie", ("Psychic", "Thunderbolt", "Thunder Wave", "Recover")),
    Pokemon.new("Alakazam", ("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    Pokemon.new("Chansey", ("Seismic Toss", "Reflect", "Thunder Wave", "Soft-Boiled")),
    Pokemon.new("Snorlax", ("Body Slam", "Reflect", "Self-Destruct", "Rest")),
    Pokemon.new("Tauros", ("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]


def run_battle(log=False):
    """Run a battle. Returns # of turns."""
    battle = Battle(
        Side(team1, list(range(1, 7))),
        Side(team2, list(range(1, 7))),
        rng=ShowdownRNG(0),
    )
    # slots = ([p.name for p in team1], [p.name for p in team2])

    # print("Bits() battle data:\n" + hexfmt(battle._bits.bytes))
    # print("Real battle data:\n" + hexfmt(battle._pkmn_battle.bytes))
    (result, trace) = battle.update(Choice(ChoiceType.PASS), Choice(0))
    # print("---------- Battle setup ----------\nTrace: ")
    # for msg in parse_protocol(trace):
    #     print(f"* {msg}")

    choice = 1
    while result.type() == ResultType.NONE:
        if log:
            print(f"\n------------ Choice {choice} ------------")
        choice += 1
        p1_choice = random.choice(battle.possible_choices(Player.P1, result.p1_choice_type()))
        p2_choice = random.choice(battle.possible_choices(Player.P2, result.p2_choice_type()))
        if log:
            print(f"Player 1: {p1_choice}\nPlayer 2: {p2_choice}")
        (result, trace) = battle.update(p1_choice, p2_choice)
        # print("Bits() battle data:\n" + hexfmt(battle._bits.bytes))
        # print("Real battle data:\n" + hexfmt(battle._pkmn_battle.bytes))
        if log:
            print("\nTrace: ")
            for msg in parse_protocol(trace):
                print(f"* {msg}")

run_battle(log=True)
