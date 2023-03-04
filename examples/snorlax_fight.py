from pykmn.engine.gen1 import Move, Pokemon, Battle, Side, Player, BattleChoice, BattleChoiceType
from pykmn.engine.common import ResultType
import random

team1 = [Pokemon('Snorlax', [
    (Move('Body Slam'), 10),
    (Move('Amnesia'), 10),
    (Move('Rest'), 10),
    (Move('Thunder'), 10),
])] + [Pokemon('None', [(Move('None'), 10)] * 4)] * 5
team2 = [Pokemon('Snorlax', [
    (Move('Tackle'), 10),
    (Move('Ice Beam'), 10),
    (Move('Rest'), 10),
    (Move('Earthquake'), 10),
])] + [Pokemon('None', [(Move('None'), 10)] * 4)] * 5

battle = Battle(Side(team1), Side(team2))

result = battle.update(BattleChoice(0), BattleChoice(0))
while True:
    p1_choice = random.choice(battle.possible_choices(Player.P1, BattleChoiceType.MOVE))
    p2_choice = random.choice(battle.possible_choices(Player.P2, BattleChoiceType.MOVE))
    print(f"p1: {p1_choice}, p2: {p2_choice}")
    result = battle.update(p1_choice, p2_choice)
    if result.type() != ResultType.NONE:
        print(f"RESULT: {result}")
        break
