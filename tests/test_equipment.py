"""Equipment slots, bonuses and the `equipar` command."""

import pytest

from adventure.equipment import (
    bonus_text,
    equip,
    equipment_bonus,
    is_upgrade,
    total_attack,
    total_defense,
)
from adventure.state import GameState
from adventure.world import parse_world
from helpers import do


@pytest.fixture
def armed_world(small_world_data):
    """The small world, but the character starts with a weapon and a shield."""
    small_world_data["items"]["toy_sword"] = {
        "name": "Espada de Brinquedo",
        "slot": "weapon",
        "attack": 1,
    }
    small_world_data["items"]["card_shield"] = {
        "name": "Broquel de Papelão",
        "slot": "shield",
        "defense": 1,
    }
    small_world_data["player"]["equipment"] = {
        "weapon": "toy_sword",
        "shield": "card_shield",
    }
    return parse_world(small_world_data)


# --- numbers ---------------------------------------------------------------------


def test_without_equipment_totals_equal_the_base_stats(state, world):
    assert equipment_bonus(state, world) == (0, 0)
    assert total_attack(state, world) == state.attack == 10
    assert total_defense(state, world) == state.defense == 0


def test_equipment_adds_to_the_base_stats(state, world):
    state.equipped = {"weapon": "wood_sword", "armor": "leather_armor"}
    assert equipment_bonus(state, world) == (5, 3)
    assert total_attack(state, world) == 15
    assert total_defense(state, world) == 3


def test_level_ups_keep_stacking_on_top_of_equipment(state, world):
    state.equipped = {"weapon": "wood_sword"}
    state.attack += 5  # a level gain raises the base, not the bonus
    assert total_attack(state, world) == 20


def test_bonus_text_lists_what_the_item_adds(world):
    assert bonus_text(world.items["wood_sword"]) == "+5 ataque"
    assert bonus_text(world.items["leather_armor"]) == "+3 defesa"


def test_new_game_wears_the_starting_equipment(armed_world):
    state = GameState.new(armed_world, "Teste")
    assert state.equipped == {"weapon": "toy_sword", "shield": "card_shield"}
    assert total_attack(state, armed_world) == 11
    assert total_defense(state, armed_world) == 1


def test_new_games_do_not_share_the_equipment_dict(armed_world):
    first = GameState.new(armed_world, "A")
    second = GameState.new(armed_world, "B")
    first.equipped["armor"] = "leather_armor"
    assert "armor" not in second.equipped
    assert "armor" not in armed_world.player.equipment


# --- is_upgrade / equip ----------------------------------------------------------


def test_anything_is_an_upgrade_over_an_empty_slot(state, world):
    assert is_upgrade(state, world, "wood_sword")


def test_only_a_stronger_item_is_an_upgrade(state, world):
    state.equipped = {"weapon": "wood_sword"}
    assert is_upgrade(state, world, "copper_sword")
    state.equipped = {"weapon": "copper_sword"}
    assert not is_upgrade(state, world, "wood_sword")


def test_an_item_as_good_as_the_worn_one_is_not_an_upgrade(state, world):
    state.equipped = {"weapon": "wood_sword"}
    assert not is_upgrade(state, world, "wood_sword")


def test_equip_moves_the_item_from_the_inventory_to_its_slot(state, world):
    state.inventory = ["wood_sword"]
    text = equip(state, world, "wood_sword")
    assert state.equipped == {"weapon": "wood_sword"}
    assert state.inventory == []
    assert "Você equipou Espada de Madeira" in text
    assert "Arma: +5 ataque" in text


def test_equip_sends_the_replaced_item_back_to_the_inventory(state, world):
    state.equipped = {"weapon": "wood_sword"}
    state.inventory = ["copper_sword"]
    text = equip(state, world, "copper_sword")
    assert state.equipped == {"weapon": "copper_sword"}
    assert state.inventory == ["wood_sword"]
    assert "Espada de Madeira voltou para o inventário" in text


# --- the equipar command ---------------------------------------------------------


def test_equipar_wears_a_found_item(state, game):
    do(state, game, "pegar couro")
    message = do(state, game, "equipar couro")
    assert "Você equipou Armadura de Couro" in message
    assert state.equipped == {"armor": "leather_armor"}
    assert "leather_armor" not in state.inventory


def test_equipar_swaps_with_what_is_worn(state, game):
    state.inventory = ["wood_sword", "copper_sword"]
    do(state, game, "equipar espada de madeira")
    do(state, game, "equipar espada de cobre")
    assert state.equipped["weapon"] == "copper_sword"
    assert state.inventory == ["wood_sword"]


def test_equipar_can_go_back_to_a_weaker_item(state, game):
    state.equipped = {"weapon": "copper_sword"}
    state.inventory = ["wood_sword"]
    do(state, game, "equipar madeira")
    assert state.equipped["weapon"] == "wood_sword"
    assert state.inventory == ["copper_sword"]


def test_equipar_without_a_name_asks_what(state, game):
    assert "Equipar o quê" in do(state, game, "equipar")


def test_equipar_something_not_carried_fails(state, game):
    assert "Você não tem" in do(state, game, "equipar espada")


def test_equipar_with_an_ambiguous_name_asks_which(state, game):
    state.inventory = ["wood_sword", "copper_sword"]
    message = do(state, game, "equipar espada")
    assert "Qual deles" in message
    assert state.equipped == {}


def test_equipar_something_that_is_not_equipment_is_refused(state, game):
    do(state, game, "pegar lanterna")
    message = do(state, game, "equipar lanterna")
    assert "não pode ser equipado" in message
    assert state.inventory == ["lamp"]


def test_worn_items_cannot_be_dropped_while_worn(state, game):
    state.equipped = {"weapon": "wood_sword"}
    assert "Você não tem" in do(state, game, "largar espada")
    assert state.equipped == {"weapon": "wood_sword"}


# --- profile ---------------------------------------------------------------------


def test_profile_lists_the_three_slots(state, game):
    message = do(state, game, "perfil")
    assert "Equipamento:" in message
    assert "Arma: nenhum" in message
    assert "Escudo: nenhum" in message
    assert "Armadura: nenhum" in message


def test_profile_shows_worn_items_and_the_stat_breakdown(state, game):
    state.equipped = {"weapon": "wood_sword", "armor": "leather_armor"}
    message = do(state, game, "perfil")
    assert "Arma: Espada de Madeira (+5 ataque)" in message
    assert "Armadura: Armadura de Couro (+3 defesa)" in message
    assert "Escudo: nenhum" in message
    assert "Ataque: 15 (10+5)" in message
    assert "Defesa: 3 (0+3)" in message


def test_profile_without_bonus_shows_plain_numbers(state, game):
    message = do(state, game, "perfil")
    assert "Ataque: 10 " in message
    assert "(10+" not in message


# --- combat ----------------------------------------------------------------------


def _meet_the_rat(state, game):
    do(state, game, "n")
    do(state, game, "l")  # a rat (20 hp, attack 4) is waiting in the cellar


def test_the_weapon_bonus_is_used_in_combat(state, game):
    state.equipped = {"weapon": "wood_sword"}
    _meet_the_rat(state, game)
    do(state, game, "atacar")
    assert state.combat.monster_hp == 5  # 15 damage, not 10


def test_the_armor_bonus_is_used_in_combat(state, game):
    state.equipped = {"armor": "leather_armor"}
    _meet_the_rat(state, game)
    message = do(state, game, "atacar")
    assert "causou 3 de dano" in message  # 4 * 100 // 103
    assert state.hp == 27


def test_a_better_weapon_wins_a_fight_in_fewer_rounds(state, game):
    state.equipped = {"weapon": "copper_sword"}  # 20 damage kills the rat at once
    _meet_the_rat(state, game)
    message = do(state, game, "atacar")
    assert "Você derrotou Rato" in message
    assert state.hp == 30


@pytest.mark.parametrize(
    "line", ["equipar x", "fabricar x", "receitas", "cortar", "minerar"]
)
def test_equipment_and_crafting_are_blocked_during_a_fight(state, game, line):
    _meet_the_rat(state, game)
    assert "Você está em combate" in do(state, game, line)


def test_a_fight_does_not_change_what_is_worn(state, game):
    state.equipped = {"weapon": "wood_sword"}
    _meet_the_rat(state, game)
    do(state, game, "atacar")
    do(state, game, "atacar")
    assert state.equipped == {"weapon": "wood_sword"}
