"""Tests the Gen 1 Pokemon class."""

import unittest
from pykmn.engine.gen1 import Battle, Choice, Player, Result


def run_first_choice(battle: Battle, result: Result) -> Result:
    """Runs the first choice of a battle."""
    p1choice = battle.possible_choices(Player.P1, result)[0]
    p2choice = battle.possible_choices(Player.P2, result)[0]
    (result, _) = battle.update(p1choice, p2choice)
    return result

class TestBattle(unittest.TestCase):
    def test_stat_boosts(self):
        """Tests stat-boosting moves."""
        attack_stats_battle = Battle(
            [('Mew', ('Swords Dance',))],
            [('Mew', ('Amnesia',))],
        )
        (result, _) = attack_stats_battle.update(Choice.PASS(), Choice.PASS())

        self.assertDictEqual(
            attack_stats_battle.p1.active_pokemon_stats(),
            attack_stats_battle.p2.active_pokemon_stats(),
        )
        self.assertDictEqual(
            attack_stats_battle.p1.active_pokemon_stats(),
            attack_stats_battle.p1.team[0].stats(),
        )

        run_first_choice(attack_stats_battle, result)
        p1_active_stats = attack_stats_battle.p1.active_pokemon_stats()
        p1_original_stats = attack_stats_battle.p1.team[0].stats()
        p2_active_stats = attack_stats_battle.p2.active_pokemon_stats()
        p2_original_stats = attack_stats_battle.p2.team[0].stats()

        self.assertEqual(p1_active_stats['atk'], p1_original_stats['atk'] * 2)
        self.assertEqual(p1_active_stats['spc'], p2_original_stats['spc'])

        self.assertEqual(p2_active_stats['spc'], p2_original_stats['spc'] * 2)
        self.assertEqual(p2_active_stats['atk'], p2_original_stats['atk'])

        for unchanged_stat in ['hp', 'def', 'spe']:
            self.assertEqual(p1_active_stats[unchanged_stat], p1_original_stats[unchanged_stat])
            self.assertEqual(p2_active_stats[unchanged_stat], p2_original_stats[unchanged_stat])

