"""Test script."""
from pykmn.engine.gen1 import moves, Pokemon, Battle, Side, Player, BattleChoice
from pykmn.engine.common import ResultType
import random

# https://pokepast.es/cc9b111c9f81f6a4
team1 = [
    Pokemon("Starmie", moves("Psychic", "Blizzard", "Thunder Wave", "Recover")),
    Pokemon("Exeggutor", moves("Sleep Powder", "Psychic", "Double-Edge", "Explosion")),
    Pokemon("Alakazam", moves("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    Pokemon("Chansey", moves("Ice Beam", "Thunderbolt", "Thunder Wave", "Soft-Boiled")),
    Pokemon("Snorlax", moves("Body Slam", "Reflect", "Earthquake", "Rest")),
    Pokemon("Tauros", moves("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]

# https://pokepast.es/7f1c2e78e6ba3194
team2 = [
    Pokemon("Jynx", moves("Lovely Kiss", "Blizzard", "Psychic", "Rest")),
    Pokemon("Starmie", moves("Psychic", "Thunderbolt", "Thunder Wave", "Recover")),
    Pokemon("Alakazam", moves("Psychic", "Seismic Toss", "Thunder Wave", "Recover")),
    Pokemon("Chansey", moves("Seismic Toss", "Reflect", "Thunder Wave", "Soft-Boiled")),
    Pokemon("Snorlax", moves("Body Slam", "Reflect", "Self-Destruct", "Rest")),
    Pokemon("Tauros", moves("Body Slam", "Hyper Beam", "Blizzard", "Earthquake")),
]


def run_battle(log=False) -> int:
    """Run a battle. Returns # of turns."""
    battle = Battle(Side(team1, list(range(1, 7))), Side(team2, list(range(1, 7))))

    (result, _) = battle.update(BattleChoice(0), BattleChoice(0))
    if log:
        print(f"RESULT: {result}")
    turn = 1
    while True:
        if log:
            print(f"\n\n------------ TURN {turn} ------------")
        turn += 1
        p1_choice = random.choice(battle.possible_choices(Player.P1, result.p1_choice_type()))
        p2_choice = random.choice(battle.possible_choices(Player.P2, result.p2_choice_type()))
        if log:
            print(f"Player 1: {p1_choice}\nPlayer 2: {p2_choice}")
        (result, _) = battle.update(p1_choice, p2_choice)
        if result.type() != ResultType.NONE:
            if log:
                print(f"RESULT: {result}")
            return turn


turns_taken = []
for i in range(1000):
    turns_taken.append(run_battle())

n = len(turns_taken)
avg = round(sum(turns_taken) / n)
print(f"played {n} battles — average turns taken: {avg}")
