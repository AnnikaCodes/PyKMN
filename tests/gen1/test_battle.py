"""Tests the Gen 1 Battle class."""

import unittest
from pykmn.engine.gen1 import Battle, Choice, Player, Result, VolatileFlag
from pykmn.data.gen1 import Gen1StatData
# from pykmn.engine.protocol import parse_protocol

def run_first_choice(battle: Battle, result: Result) -> Result:
    """Runs the first choice of a battle."""
    p1choice = battle.possible_choices(Player.P1, result)[0]
    p2choice = battle.possible_choices(Player.P2, result)[0]
    (result, _) = battle.update(p1choice, p2choice)
    return result

zero_dvs: Gen1StatData = {'hp': 0, 'atk': 0, 'def': 0, 'spc': 0, 'spe': 0}

class TestBattle(unittest.TestCase):
    def test_active_pokemon_stats(self):
        """Tests stat-boosting moves."""
        battle = Battle([('Mew', ('Swords Dance', ))], [('Mew', ('Screech', ))], rng_seed=0)
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        no_boosts = {'atk': 0, 'def': 0, 'spe': 0, 'spc': 0, 'accuracy': 0, 'evasion': 0}
        self.assertDictEqual(battle.p1.active_pokemon_stats(), battle.p2.active_pokemon_stats())
        self.assertDictEqual(battle.p1.active_pokemon_stats(), battle.p1.team[0].stats())
        self.assertDictEqual(battle.p1.team[0].stats(), battle.active_pokemon_stats(Player.P1))
        self.assertDictEqual(battle.p2.team[0].stats(), battle.active_pokemon_stats(Player.P2))

        self.assertDictEqual(battle.boosts(Player.P1), no_boosts)
        self.assertDictEqual(battle.boosts(Player.P2), no_boosts)

        result = run_first_choice(battle, result) # P1: Swords Dance, P2: Screech
        self.assertDictEqual(
            battle.boosts(Player.P1),
            {'atk': 2, 'def': -2, 'spe': 0, 'spc': 0, 'accuracy': 0, 'evasion': 0},
        )
        self.assertDictEqual(battle.boosts(Player.P2), no_boosts)

        p1_active_stats = battle.p1.active_pokemon_stats()
        p1_original_stats = battle.p1.team[0].stats()
        p2_active_stats = battle.p2.active_pokemon_stats()

        p2_original_stats = battle.p2.team[0].stats()

        self.assertEqual(p1_active_stats['atk'], p1_original_stats['atk'] * 2)
        self.assertEqual(p1_active_stats['spc'], p2_original_stats['spc'])

        self.assertEqual(p1_active_stats['def'], p1_original_stats['def'] / 2)

        for unchanged_stat in ['hp', 'spc', 'spe']:
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

        battle.set_boosts(Player.P2, {'evasion': -1})
        self.assertDictEqual(
            battle.boosts(Player.P2),
            {'atk': 0, 'def': 0, 'spe': 0, 'spc': 0, 'accuracy': 0, 'evasion': -1},
        )

    def test_active_pokemon_species(self) -> None:
        """ActivePokemon.species test."""
        battle = Battle(
            [('Starmie', ('None',)), ('Kangaskhan', ('Tackle', ))],
            [('Articuno', ('Amnesia',))],
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        self.assertEqual(battle.active_pokemon_species(Player.P1), 'Starmie')
        self.assertEqual(battle.active_pokemon_species(Player.P2), 'Articuno')

        run_first_choice(battle, result) # P1: switch Starmie -> Kangaskhan, P2: use move Amnesia
        self.assertEqual(battle.active_pokemon_species(Player.P1), 'Kangaskhan')
        self.assertEqual(battle.active_pokemon_species(Player.P2), 'Articuno')

        battle.set_active_pokemon_species(Player.P2, 'Goldeen')
        self.assertEqual(battle.active_pokemon_species(Player.P2), 'Goldeen')

    def test_active_pokemon_types(self) -> None:
        """ActivePokemon.types test."""
        battle = Battle([('Charizard', ('Swords Dance', ))], [('Blastoise', ('Amnesia', 'Fly'))])
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        self.assertTupleEqual(battle.active_pokemon_types(Player.P1), ('Fire', 'Flying'))
        self.assertTupleEqual(battle.active_pokemon_types(Player.P2), ('Water', ))

        # Transform is tested elsewhere
        battle.set_active_pokemon_types(Player.P1, ('Normal', ))
        self.assertTupleEqual(battle.active_pokemon_types(Player.P1), ('Normal', ))


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

    def test_turn(self) -> None:
        """Test turn storage."""
        battle = Battle([('Mew', ('Swords Dance', 'Surf'))], [('Mew', ('Amnesia', 'Fly'))])
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())

        self.assertEqual(battle.turn(), 1)
        run_first_choice(battle, result)
        self.assertEqual(battle.turn(), 2)

        battle.set_turn(5)
        self.assertEqual(battle.turn(), 5)

    def test_last_damage(self) -> None:
        """Test last damage variable."""
        battle = Battle(
            p1_team=[('Mew', ('Amnesia', ))],
            p2_team=[('Mew', ('Surf', ))],
            rng_seed=0
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())
        self.assertEqual(battle.last_damage(), 0)

        run_first_choice(battle, result)
        self.assertEqual(battle.last_damage(), 134)

        battle.set_last_damage(65)
        self.assertEqual(battle.last_damage(), 65)

    def test_stats(self) -> None:
        """Tests that the stats are stored/loaded correctly."""
        stats: Gen1StatData = {'hp': 582, 'atk': 92, 'def': 312, 'spe': 484, 'spc': 831}
        battle = Battle(
            p1_team=[('Bulbasaur', ('Tackle',)), ('Mew', ('Amnesia', ), {'stats': stats})],
            p2_team=[('Mew', ('Surf', ))],
        )
        self.assertDictEqual(battle.stats(Player.P1, 2), stats)
        self.assertDictEqual(battle.stats(Player.P1, 2), battle.p1.team[1].stats())
        self.assertDictEqual(battle.stats(Player.P2, 1), battle.p2.team[0].stats())

        battle.set_stats(Player.P1, 2, {'hp': 89, 'atk': 35, 'spe': 12})
        self.assertDictEqual(
            battle.stats(Player.P1, 2),
            {'hp': 89, 'atk': 35, 'def': stats['def'], 'spe': 12, 'spc': stats['spc']},
        )

    def test_moves(self) -> None:
        """Tests that the moves are stored/loaded correctly."""
        battle = Battle(
            p1_team=[('Mew', ('Amnesia', 'Surf', 'Thunderbolt', 'Fly'))],
            p2_team=[('Mew', ('Surf', 'Hyper Beam'), {'move_pp': (28, 63, 0, 0)})],
        )
        self.assertTupleEqual(battle.moves(Player.P1, 1), ('Amnesia', 'Surf', 'Thunderbolt', 'Fly'))
        self.assertTupleEqual(battle.moves(Player.P2, 1), ('Surf', 'Hyper Beam'))
        self.assertTupleEqual(battle.pp_left(Player.P2, 1), (28, 63))
        self.assertTupleEqual(
            battle.moves_with_pp(Player.P2, 1),
            (('Surf', 28), ('Hyper Beam', 63)),
        )

        battle.set_moves(Player.P1, 1, (
            ('Flash', 10), ('High Jump Kick', 15), ('None', 0), ('None', 0),
        ))
        self.assertTupleEqual(battle.moves(Player.P1, 1), ('Flash', 'High Jump Kick'))
        self.assertTupleEqual(battle.pp_left(Player.P1, 1), (10, 15))
        self.assertTupleEqual(
            battle.moves_with_pp(Player.P1, pokemon=1),
            (('Flash', 10), ('High Jump Kick', 15))
        )

    def test_status(self) -> None:
        """Tests that the status is stored/loaded correctly."""
        battle = Battle(
            p1_team=[('Muk', ('Toxic', ))],
            p2_team=[('Mew', ('Tackle', ))],
            rng_seed=0,
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())
        self.assertEqual(battle.status(Player.P1, 1), 0)
        self.assertEqual(battle.status(Player.P2, 1), 0)

        run_first_choice(battle, result)
        self.assertEqual(battle.status(Player.P2, 1), 8) # Toxic
        self.assertEqual(battle.status(Player.P1, 1), 0) # No status

        battle.set_status(Player.P1, 1, 32)
        self.assertEqual(battle.status(Player.P1, 1), 32)
        self.assertEqual(battle.status(Player.P2, 1), 8)

    def test_species(self) -> None:
        """Tests that the species is stored/loaded correctly."""
        battle = Battle(
            p1_team=[('Mew', ('Amnesia', ))],
            p2_team=[('Blastoise', ('Surf', ))],
        )
        self.assertEqual(battle.species(Player.P1, 1), 'Mew')
        self.assertEqual(battle.species(Player.P2, 1), 'Blastoise')

        battle.set_species(Player.P2, 1, 'Eevee')
        self.assertEqual(battle.species(Player.P1, 1), 'Mew')
        self.assertEqual(battle.species(Player.P2, 1), 'Eevee')

    def test_transform(self) -> None:
        """Tests that the type storage and Transform are correct."""
        battle = Battle(
            p1_team=[('Charizard', ('Splash', ))],
            p2_team=[('Ditto', ('Transform', ))],
            rng_seed=0,
        )
        self.assertTupleEqual(battle.types(Player.P1, 1), ('Fire', 'Flying'))
        self.assertTupleEqual(battle.types(Player.P2, 1), ('Normal',))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Transform))

        # Transform should change active pokemon's types but not in the team
        run_first_choice(battle, battle.update(Choice.PASS(), Choice.PASS())[0])
        self.assertTrue(battle.volatile(Player.P2, VolatileFlag.Transform))
        self.assertTupleEqual(battle.transformed_into(Player.P2), (Player.P1, 1))

        self.assertTupleEqual(battle.types(Player.P1, 1), ('Fire', 'Flying'))
        self.assertTupleEqual(battle.active_pokemon_types(Player.P2), ('Fire', 'Flying'))
        self.assertTupleEqual(battle.types(Player.P2, 1), ('Normal',))

        battle.set_types(Player.P2, 1, ('Grass', 'Poison'))
        self.assertTupleEqual(battle.types(Player.P1, 1), ('Fire', 'Flying'))
        self.assertTupleEqual(battle.types(Player.P2, 1), ('Grass', 'Poison'))

        battle.set_transformed_into(Player.P2, (Player.P2, 3))
        self.assertTupleEqual(battle.transformed_into(Player.P2), (Player.P2, 3))

        battle.set_volatile(Player.P2, VolatileFlag.Transform, False)
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Transform))

    def test_level(self) -> None:
        battle = Battle([("Mew", ("Amnesia", ))], [("Mew", ("Surf", ), {'level': 47})])
        self.assertEqual(battle.level(Player.P1, 1), 100)
        self.assertEqual(battle.level(Player.P2, 1), 47)

        battle.set_level(Player.P1, 1, 12)
        self.assertEqual(battle.level(Player.P1, 1), 12)
        self.assertEqual(battle.level(Player.P2, 1), 47)

        battle.set_level(Player.P2, 1, 87)
        self.assertEqual(battle.level(Player.P1, 1), 12)
        self.assertEqual(battle.level(Player.P2, 1), 87)

    def test_40pp_moves(self) -> None:
        """Moves with 40 PP should have 61 after PP Ups."""
        # https://github.com/pkmn/engine/blob/main/src/lib/gen1/helpers.zig#L145
        battle = Battle([('Bulbasaur', ('Growth', ))], [('Grimer', ('Poison Gas', ))])
        self.assertEqual(battle.pp_left(Player.P1, 1), (61, ))
        self.assertEqual(battle.pp_left(Player.P2, 1), (61, ))

    def test_confusion(self) -> None:
        """Tests confusion mechanics."""
        battle = Battle(
            [("Mew", ("Amnesia", ))],
            [("Mew", ("Confuse Ray", ))],
            # this seed makes the confusion last 3 turns on ShowdownRNG
            rng_seed=412, # 1/256 miss chance my behated :(
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())
        self.assertEqual(battle.confusion_turns_left(Player.P1), 0)
        self.assertEqual(battle.confusion_turns_left(Player.P2), 0)
        self.assertFalse(battle.volatile(Player.P1, VolatileFlag.Confusion))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Confusion))

        result = run_first_choice(battle, result) # P1: Amnesia, P2: Confuse Ray
        self.assertTrue(battle.volatile(Player.P1, VolatileFlag.Confusion))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Confusion))
        p1_confusion_turns = battle.confusion_turns_left(Player.P1)
        self.assertEqual(p1_confusion_turns, 3)
        self.assertEqual(battle.confusion_turns_left(Player.P2), 0)

        run_first_choice(battle, result) # P1: Amnesia, P2: Confuse Ray
        self.assertEqual(battle.confusion_turns_left(Player.P1), p1_confusion_turns - 1)

        battle.set_confusion_turns_left(Player.P1, 5) # never happens naturally!
        self.assertEqual(battle.confusion_turns_left(Player.P1), 5)
        self.assertEqual(battle.confusion_turns_left(Player.P2), 0)

    def test_bide(self) -> None:
        """Tests volatile data storage by using the move Bide."""
        battle = Battle(
            [("Mew", ("Bide", ))],
            # zero DVs so that it goes last
            [("Mew", ("Swift", ), {'dvs': zero_dvs})],
            rng_seed=0,
        )
        p1_full_hp = battle.stats(Player.P1, 1)['hp']

        (result, _) = battle.update(Choice.PASS(), Choice.PASS())
        self.assertFalse(battle.volatile(Player.P1, VolatileFlag.Bide))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Bide))
        self.assertEqual(battle.attacks_left(Player.P1), 0)
        self.assertEqual(battle.attacks_left(Player.P2), 0)
        self.assertEqual(battle.volatile_state(Player.P1), 0)

        result = run_first_choice(battle, result) # P1: Bide, P2: Swift
        self.assertTrue(battle.volatile(Player.P1, VolatileFlag.Bide))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Bide))
        # 2 Bide turns on this seed with ShowdownRNG
        self.assertEqual(battle.attacks_left(Player.P1), 2)
        self.assertEqual(battle.attacks_left(Player.P2), 0)
        turn1_damage = p1_full_hp - battle.current_hp(Player.P1, 1)

        run_first_choice(battle, result) # P1: Bide (fails), P2: Swift
        # the Bide damage counter updates at the start of *this* turn with *last* turn's damage
        self.assertEqual(battle.volatile_state(Player.P1), turn1_damage)

        self.assertTrue(battle.volatile(Player.P1, VolatileFlag.Bide))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Bide))
        self.assertEqual(battle.attacks_left(Player.P1), 1)
        self.assertEqual(battle.attacks_left(Player.P2), 0)
        # the Bide damage counter should be equal to the ACCUMULATED damage dealt to the Bide user

        battle.set_attacks_left(Player.P1, 5)
        self.assertEqual(battle.attacks_left(Player.P1), 5)
        self.assertEqual(battle.attacks_left(Player.P2), 0)

        battle.set_volatile_state(Player.P1, 7832)
        self.assertEqual(battle.volatile_state(Player.P1), 7832)

    def test_substitute(self) -> None:
        """Tests Substitute mechanics."""
        battle = Battle(
            # zero DVs so it goes last and doesn't have the sub take damage the turn it goes up
            [("Squirtle", ("Substitute", ), {'dvs': zero_dvs})],
            [("Squirtle", ("Tackle", ))],
        )
        (result, _) = battle.update(Choice.PASS(), Choice.PASS())
        sub_hp = battle.stats(Player.P1, 1)['hp'] // 4 + 1
        self.assertFalse(battle.volatile(Player.P1, VolatileFlag.Substitute))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Substitute))
        self.assertEqual(battle.substitute_hp(Player.P1), 0)
        self.assertEqual(battle.substitute_hp(Player.P2), 0)

        result = run_first_choice(battle, result) # P2: Tackle, P1: Substitute
        self.assertTrue(battle.volatile(Player.P1, VolatileFlag.Substitute))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Substitute))
        self.assertEqual(battle.substitute_hp(Player.P1), sub_hp)

        run_first_choice(battle, result) # P2: Tackle, P1: Substitute (fails)
        self.assertTrue(battle.volatile(Player.P1, VolatileFlag.Substitute))
        self.assertFalse(battle.volatile(Player.P2, VolatileFlag.Substitute))
        self.assertEqual(battle.substitute_hp(Player.P1), sub_hp - battle.last_damage())

        battle.set_substitute_hp(Player.P1, 200)
        self.assertEqual(battle.substitute_hp(Player.P1), 200)
