"""Test script."""
from pykmn.engine.gen1 import Move, Pokemon, Battle, Side, Player, BattleChoice, ActivePokemon
from pykmn.engine.common import ResultType
import random

team1 = [Pokemon('Gengar', [
    (Move('Psychic'), 60),
    (Move('None'), 60),
    (Move('None'), 60),
    (Move('None'), 60),
])] + [Pokemon('None', [(Move('None'), 60)] * 4)] * 5
team2 = [Pokemon('Gengar', [
    (Move('Psychic'), 60),
    (Move('None'), 60),
    (Move('None'), 60),
    (Move('None'), 60),
])] + [Pokemon('None', [(Move('None'), 60)] * 4)] * 5

print(team1[0].hp)
battle = Battle(
    Side(team1, ActivePokemon('None'), [1, 0, 0, 0, 0, 0]),
    Side(team2, ActivePokemon('None'), [1, 0, 0, 0, 0, 0]),
)

result = battle.update(BattleChoice(0), BattleChoice(0))
print(f"RESULT: {result}")
turn = 1
while True:
    print(f"\n\n------------ TURN {turn} ------------")
    turn += 1
    p1_choice = random.choice(battle.possible_choices(Player.P1, result.p1_choice_type()))
    p2_choice = random.choice(battle.possible_choices(Player.P2, result.p2_choice_type()))
    print(f"p1: {p1_choice}, p2: {p2_choice}")
    result = battle.update(p1_choice, p2_choice)
    print(f"RESULT: {result}")
    if result.type() != ResultType.NONE:
        break
