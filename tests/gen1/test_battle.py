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

    def test_last_selected_move(self):
        """Tests that the last selected move is stored/loaded correctly."""
        battle = Battle(
            [('Mew', ('Swords Dance', 'Amnesia'))],
            [('Mew', ('Amnesia',))],
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        self.assertEqual(battle.p1.last_selected_move(), battle.last_selected_move(Player.P1))
        self.assertEqual(battle.p2.last_selected_move(), battle.last_selected_move(Player.P2))
        self.assertEqual(battle.p1.last_used_move(), battle.last_used_move(Player.P1))
        self.assertEqual(battle.p2.last_used_move(), battle.last_used_move(Player.P2))

        self.assertEqual(battle.last_selected_move(Player.P1), 'None')
        self.assertEqual(battle.last_selected_move(Player.P2), 'None')
        self.assertEqual(battle.last_used_move(Player.P1), 'None')
        self.assertEqual(battle.last_used_move(Player.P2), 'None')

        run_first_choice(battle, result)
        self.assertEqual(battle.p1.last_selected_move(), battle.last_selected_move(Player.P1))
        self.assertEqual(battle.p2.last_selected_move(), battle.last_selected_move(Player.P2))
        self.assertEqual(battle.p1.last_used_move(), battle.last_used_move(Player.P1))
        self.assertEqual(battle.p2.last_used_move(), battle.last_used_move(Player.P2))

        # TODO: create a case were last selected and last used are different
        # optimization: put moves in an enum to remove dict lookups?
        self.assertEqual(battle.last_selected_move(Player.P1), 'Swords Dance')
        self.assertEqual(battle.last_selected_move(Player.P2), 'Amnesia')
        self.assertEqual(battle.last_used_move(Player.P1), 'Swords Dance')
        self.assertEqual(battle.last_used_move(Player.P2), 'Amnesia')

        battle.set_last_used_move(Player.P1, 'Thunderbolt')
        self.assertEqual(battle.last_used_move(Player.P1), 'Thunderbolt')
        battle.set_last_selected_move(Player.P2, 'Gust')
        self.assertEqual(battle.last_selected_move(Player.P2), 'Gust')

