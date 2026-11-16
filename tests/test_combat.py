from dataclasses import replace

import pytest

from adventure.combat import roll_damage
from helpers import ScriptedRng, do


def _fight_rat(state, game):
    """Walk to the cellar, where a rat (20 hp, attack 4) is waiting."""
    do(state, game, "n")
    return do(state, game, "l")


def _beat_rat(state, game):
    _fight_rat(state, game)
    do(state, game, "atacar")
    do(state, game, "atacar")


# --- damage rule ---------------------------------------------------------------


def test_roll_damage_is_zero_on_a_miss():
    assert roll_damage(10, 0, ScriptedRng(0.99)) == 0


def test_roll_damage_without_defense_equals_attack():
    assert roll_damage(10, 0, ScriptedRng(0.0)) == 10


def test_roll_damage_is_reduced_by_defense():
    assert roll_damage(10, 100, ScriptedRng(0.0)) == 5


def test_roll_damage_is_at_least_one_on_a_hit():
    assert roll_damage(1, 1000, ScriptedRng(0.0)) == 1


def test_roll_damage_uses_the_random_variance():
    class Plus2(ScriptedRng):
        def randint(self, a, b):
            return b

    assert roll_damage(10, 0, Plus2(0.0)) == 12


# --- starting and gating a fight -----------------------------------------------


def test_entering_a_monster_room_starts_the_fight(state, game):
    message = _fight_rat(state, game)
    assert state.combat is not None
    assert state.combat.monster_hp == 20
    assert "Rato aparece" in message
    assert "Perigo: Rato (20/20 de vida)" in message


def test_rooms_without_a_monster_do_not_start_a_fight(state, game):
    do(state, game, "n")
    assert state.combat is None


@pytest.mark.parametrize(
    "line", ["o", "pegar x", "largar x", "comprar x", "descansar", "salvar", "dançar"]
)
def test_most_commands_are_blocked_during_a_fight(state, game, line):
    _fight_rat(state, game)
    message = do(state, game, line)
    assert "Você está em combate" in message
    assert state.current_room == "cellar"


@pytest.mark.parametrize("line", ["ajuda", "inv", "olhar"])
def test_help_inventory_and_look_work_during_a_fight(state, game, line):
    _fight_rat(state, game)
    assert "Você está em combate" not in do(state, game, line)


def test_look_during_a_fight_shows_the_monster(state, game):
    _fight_rat(state, game)
    assert "Perigo: Rato" in do(state, game, "olhar")


def test_attack_without_a_fight_does_nothing(state, game):
    assert "nada para atacar" in do(state, game, "atacar")


def test_flee_without_a_fight_does_nothing(state, game):
    assert "não está lutando" in do(state, game, "fugir")


# --- rounds ----------------------------------------------------------------------


def test_attack_hurts_the_monster_and_it_answers(state, game):
    _fight_rat(state, game)
    message = do(state, game, "atacar")
    assert "causou 10 de dano (10/20 de vida)" in message
    assert "Rato te acertou e causou 4 de dano" in message
    assert state.combat.monster_hp == 10
    assert state.hp == 26


def test_a_miss_hurts_nobody(state, game):
    _fight_rat(state, game)
    missing = replace(game, rng=ScriptedRng(0.99))
    message = do(state, missing, "atacar")
    assert "errou o golpe" in message
    assert "errou o ataque" in message
    assert state.combat.monster_hp == 20
    assert state.hp == 30


def test_beating_a_monster_ends_the_fight_and_it_does_not_answer(state, game):
    _beat_rat(state, game)
    assert state.combat is None
    assert state.defeated == ["cellar"]
    assert state.hp == 26  # only the first round was answered
    assert state.running


def test_beating_a_monster_pays_gold_and_xp(state, game):
    _beat_rat(state, game)
    assert state.xp == 5
    assert state.gold == 27  # 20 to start with + 7


def test_the_victory_message_reports_the_reward(state, game):
    _fight_rat(state, game)
    do(state, game, "atacar")
    message = do(state, game, "atacar")
    assert "5 de experiência e 7 de ouro" in message


def test_victory_message_names_the_monster(state, game):
    _fight_rat(state, game)
    do(state, game, "atacar")
    assert "Você derrotou Rato!" in do(state, game, "atacar")


def test_a_defeated_monster_does_not_come_back(state, game):
    _beat_rat(state, game)
    do(state, game, "o")
    message = do(state, game, "l")
    assert "aparece" not in message
    assert state.combat is None


def test_the_player_can_move_again_after_the_fight(state, game):
    _beat_rat(state, game)
    do(state, game, "o")
    assert state.current_room == "garden"


# --- fleeing ---------------------------------------------------------------------


def test_successful_flee_goes_back_to_the_previous_room(state, game):
    _fight_rat(state, game)
    message = do(state, game, "fugir")
    assert "fugiu" in message
    assert "Jardim" in message
    assert state.current_room == "garden"
    assert state.combat is None
    assert state.hp == 30


def test_failed_flee_costs_a_monster_strike_and_keeps_the_fight(state, game):
    _fight_rat(state, game)
    flaky = replace(game, rng=ScriptedRng(0.99, 0.0))  # flee fails, rat hits
    message = do(state, flaky, "fugir")
    assert "te alcança" in message
    assert state.current_room == "cellar"
    assert state.combat is not None
    assert state.hp == 26


def test_a_monster_that_was_fled_from_is_still_there(state, game):
    _fight_rat(state, game)
    do(state, game, "atacar")
    do(state, game, "fugir")
    message = do(state, game, "l")
    assert "Rato aparece" in message
    assert state.combat.monster_hp == 20  # it healed


# --- dying -----------------------------------------------------------------------


def test_dying_ends_the_game_with_the_defeat_text(state, game):
    _fight_rat(state, game)
    state.hp = 3
    message = do(state, game, "atacar")
    assert "DERROTA" in message
    assert state.hp == 0
    assert not state.running
    assert state.combat is None


def test_dying_while_fleeing_also_ends_the_game(state, game):
    _fight_rat(state, game)
    state.hp = 3
    flaky = replace(game, rng=ScriptedRng(0.99, 0.0))
    assert "DERROTA" in do(state, flaky, "fugir")
    assert not state.running


# --- the boss and the door -------------------------------------------------------


def _to_the_lair(state, game):
    do(state, game, "pegar velha")
    do(state, game, "n")
    do(state, game, "usar chave velha")
    return do(state, game, "n")


def test_beating_the_boss_wins_the_game(state, game):
    _to_the_lair(state, game)
    assert state.combat.monster_id == "ogre"
    do(state, game, "atacar")
    do(state, game, "atacar")
    message = do(state, game, "atacar")
    assert "Você derrotou Ogro!" in message
    assert "VITÓRIA" in message
    assert not state.running
    assert state.hp > 0


def test_beating_the_final_monster_still_pays_and_levels_up(state, game):
    _to_the_lair(state, game)
    for _ in range(3):
        message = do(state, game, "atacar")
    assert "nível 3" in message
    assert state.level == 3
    assert state.gold == 20 + 25


def test_a_monster_that_is_not_final_does_not_end_the_game(state, game):
    _beat_rat(state, game)
    assert state.running


def test_the_boss_can_win_too(state, game):
    _to_the_lair(state, game)
    state.hp = 5
    assert "DERROTA" in do(state, game, "atacar")
    assert not state.running


# --- resting ---------------------------------------------------------------------


def test_resting_in_a_safe_room_restores_life(state, game):
    state.hp = 5
    message = do(state, game, "descansar")
    assert state.hp == state.max_hp == 30
    assert "30/30" in message


def test_resting_in_an_unsafe_room_is_refused(state, game):
    do(state, game, "n")
    state.hp = 5
    message = do(state, game, "descansar")
    assert "não é seguro" in message
    assert state.hp == 5
