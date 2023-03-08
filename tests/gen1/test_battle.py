"""Tests the Gen 1 Pokemon class."""

import unittest
from pykmn.engine.gen1 import Battle, Choice, Player, Result
# from pykmn.engine.protocol import parse_protocol

def run_first_choice(battle: Battle, result: Result) -> Result:
    """Runs the first choice of a battle."""
    p1choice = battle.possible_choices(Player.P1, result)[0]
    p2choice = battle.possible_choices(Player.P2, result)[0]
    (result, _) = battle.update(p1choice, p2choice)
    return result

class TestBattleData(unittest.TestCase):
    def test_active_pokemon_stats(self):
        """Tests stat-boosting moves."""
        battle = Battle(
            [('Mew', ('Swords Dance',))],
            [('Mew', ('Amnesia',))],
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        self.assertDictEqual(battle.p1.active_pokemon_stats(), battle.p2.active_pokemon_stats())
        self.assertDictEqual(battle.p1.active_pokemon_stats(), battle.p1.team[0].stats())
        self.assertDictEqual(battle.p1.team[0].stats(), battle.active_pokemon_stats(Player.P1))
        self.assertDictEqual(battle.p2.team[0].stats(), battle.active_pokemon_stats(Player.P2))

        result = run_first_choice(battle, result)
        p1_active_stats = battle.p1.active_pokemon_stats()
        p1_original_stats = battle.p1.team[0].stats()
        p2_active_stats = battle.p2.active_pokemon_stats()

        p2_original_stats = battle.p2.team[0].stats()

        self.assertEqual(p1_active_stats['atk'], p1_original_stats['atk'] * 2)
        self.assertEqual(p1_active_stats['spc'], p2_original_stats['spc'])

        self.assertEqual(p2_active_stats['spc'], p2_original_stats['spc'] * 2)
        self.assertEqual(p2_active_stats['atk'], p2_original_stats['atk'])

        for unchanged_stat in ['hp', 'def', 'spe']:
            self.assertEqual(p1_active_stats[unchanged_stat], p1_original_stats[unchanged_stat])
            self.assertEqual(p2_active_stats[unchanged_stat], p2_original_stats[unchanged_stat])

        self.assertDictEqual(
            battle.p1.active_pokemon_stats(),
            battle.active_pokemon_stats(Player.P1),
        )
        self.assertDictEqual(
            battle.p2.active_pokemon_stats(),
            battle.active_pokemon_stats(Player.P2),
        )
        battle.set_active_pokemon_stats(Player.P1, {'spc': 52, 'def': 97})
        new_active_stats = battle.p1.active_pokemon_stats()
        self.assertEqual(new_active_stats['spc'], 52)
        self.assertEqual(new_active_stats['def'], 97)
        for unchanged_stat in ['hp', 'atk', 'spe']:
            self.assertEqual(new_active_stats[unchanged_stat], p1_active_stats[unchanged_stat])

    def test_last_selected_move(self):
        """Tests that the last selected move is stored/loaded correctly."""
        battle = Battle([('Mew', ('Swords Dance', 'Surf'))], [('Mew', ('Amnesia', 'Fly'))])
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

    def test_current_hp(self):
        """Test current HP storage."""
        # Swift chosen so that we don't have to worry about misses
        battle = Battle([('Mew', ('Swift',))], [('Mew', ('Swift',))])
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        initial_hp = battle.current_hp(Player.P2, 1)
        self.assertEqual(initial_hp, battle.p2.team[0].stats()['hp'])
        self.assertEqual(initial_hp, battle.p2.team[0].hp())
        self.assertEqual(initial_hp, battle.current_hp(Player.P1, 1))
        self.assertNotEqual(initial_hp, 200)

        battle.set_current_hp(Player.P2, 1, 200)
        self.assertEqual(battle.current_hp(Player.P2, 1), 200)

        # make them FIGHT!
        run_first_choice(battle, result)
        self.assertLess(battle.current_hp(Player.P2, 1), 200)
        self.assertLess(battle.current_hp(Player.P1, 1), initial_hp)

