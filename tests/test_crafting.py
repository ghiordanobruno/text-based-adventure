"""Gathering materials (`cortar`, `minerar`) and crafting equipment."""

import pytest

from helpers import do

# --- gathering -------------------------------------------------------------------


def test_chop_gives_the_nodes_amount_and_spends_one_use(state, game):
    message = do(state, game, "cortar")
    assert "Você cortou 1x e obteve 2x Madeira" in message
    assert "Restam 3 usos" in message
    assert state.inventory == ["wood", "wood"]
    assert state.gathered == {"hall:chop": 1}


def test_chop_several_times_at_once(state, game):
    message = do(state, game, "cortar 3")
    assert "Você cortou 3x e obteve 6x Madeira" in message
    assert "Resta 1 uso" in message
    assert state.inventory.count("wood") == 6


def test_gathering_accepts_a_word_before_the_number(state, game):
    do(state, game, "cortar madeira 2")
    assert state.inventory.count("wood") == 4


def test_asking_for_more_than_is_left_takes_only_what_is_left(state, game):
    message = do(state, game, "cortar 50")
    assert "Você cortou 4x e obteve 8x Madeira" in message
    assert "esgotado" in message
    assert state.gathered == {"hall:chop": 4}


def test_an_exhausted_node_gives_nothing_more(state, game):
    do(state, game, "cortar 4")
    message = do(state, game, "cortar")
    assert "já cortou tudo" in message
    assert state.inventory.count("wood") == 8


@pytest.mark.parametrize("amount", ["0", "100"])
def test_silly_gathering_quantities_are_rejected(state, game, amount):
    assert "Quantidade inválida" in do(state, game, f"cortar {amount}")
    assert state.inventory == []
    assert state.gathered == {}


def test_there_is_nothing_to_chop_where_there_are_no_trees(state, game):
    do(state, game, "n")
    assert "Não há nada para cortar aqui" in do(state, game, "cortar")


def test_there_is_nothing_to_mine_in_the_hall(state, game):
    assert "Não há nada para minerar aqui" in do(state, game, "minerar")


def test_mining_works_in_a_room_with_ore(state, game):
    do(state, game, "n")
    message = do(state, game, "minerar 2")
    assert "Você minerou 2x e obteve 2x Cobre" in message
    assert state.inventory == ["copper", "copper"]
    assert state.gathered == {"garden:mine": 2}


def test_an_exhausted_mine_says_so(state, game):
    do(state, game, "n")
    do(state, game, "minerar 3")
    assert "já minerou tudo" in do(state, game, "minerar")


def test_looking_around_mentions_what_can_be_gathered(state, game):
    assert "Dá para cortar: Madeira (restam 4 usos)." in do(state, game, "olhar")


def test_the_hint_follows_the_remaining_uses_and_disappears(state, game):
    do(state, game, "cortar")
    assert "restam 3 usos" in do(state, game, "olhar")
    do(state, game, "cortar 3")
    assert "Dá para cortar" not in do(state, game, "olhar")


# --- recipes ---------------------------------------------------------------------


def test_recipes_lists_every_recipe_with_what_the_player_has(state, game):
    do(state, game, "cortar")  # 2 wood
    message = do(state, game, "receitas")
    assert "Espada de Madeira (arma, +5 ataque): Madeira 3 (você tem 2)" in message
    assert "Madeira 1 (você tem 2), Cobre 2 (você tem 0)" in message
    assert "Broquel de Madeira (escudo, +5 defesa)" in message


def test_recipes_marks_what_was_already_made(state, game):
    do(state, game, "cortar 2")
    do(state, game, "fabricar espada de madeira")
    assert "já fabricado" in do(state, game, "receitas")


# --- crafting --------------------------------------------------------------------


def test_craft_needs_the_materials(state, game):
    message = do(state, game, "fabricar espada de madeira")
    assert "Faltam materiais: Madeira 0/3" in message
    assert state.inventory == []


def test_craft_reports_every_missing_material(state, game):
    state.inventory = ["wood"]
    message = do(state, game, "fabricar espada de cobre")
    assert "Cobre 0/2" in message
    assert "Madeira" not in message  # the single wood it needs is there


def test_craft_with_a_partial_stock_changes_nothing(state, game):
    state.inventory = ["wood", "wood"]
    do(state, game, "fabricar espada de madeira")
    assert state.inventory == ["wood", "wood"]
    assert state.equipped == {}


def test_craft_consumes_exactly_the_recipe_and_wears_the_result(state, game):
    state.inventory = ["wood"] * 5
    message = do(state, game, "fabricar espada de madeira")
    assert "Você fabricou Espada de Madeira!" in message
    assert "Você equipou" in message
    assert state.inventory == ["wood", "wood"]
    assert state.equipped == {"weapon": "wood_sword"}


def test_craft_with_two_materials(state, game):
    state.inventory = ["wood", "copper", "copper"]
    do(state, game, "fabricar espada de cobre")
    assert state.inventory == []
    assert state.equipped == {"weapon": "copper_sword"}


def test_a_crafted_upgrade_replaces_the_worn_item_and_keeps_it(state, game):
    state.equipped = {"weapon": "wood_sword"}
    state.inventory = ["wood", "copper", "copper"]
    message = do(state, game, "fabricar espada de cobre")
    assert state.equipped == {"weapon": "copper_sword"}
    assert state.inventory == ["wood_sword"]
    assert "Espada de Madeira voltou para o inventário" in message


def test_a_crafted_downgrade_is_kept_but_not_worn(state, game):
    state.equipped = {"weapon": "copper_sword"}
    state.inventory = ["wood"] * 3
    message = do(state, game, "fabricar espada de madeira")
    assert "Ele não é melhor" in message
    assert state.equipped == {"weapon": "copper_sword"}
    assert state.inventory == ["wood_sword"]


def test_crafting_the_same_item_twice_is_refused(state, game):
    state.inventory = ["wood"] * 6
    do(state, game, "fabricar espada de madeira")
    message = do(state, game, "fabricar espada de madeira")
    assert "já foi fabricado" in message
    assert state.inventory == ["wood"] * 3  # nothing was spent the second time


def test_crafting_is_refused_while_the_item_is_in_the_inventory(state, game):
    state.equipped = {"weapon": "copper_sword"}
    state.inventory = ["wood"] * 3
    do(state, game, "fabricar espada de madeira")  # kept in the inventory
    state.inventory += ["wood"] * 3
    assert "já foi fabricado" in do(state, game, "fabricar espada de madeira")


def test_crafting_is_refused_even_if_the_item_was_dropped_somewhere(state, game):
    state.inventory = ["wood"] * 6
    do(state, game, "fabricar espada de madeira")
    do(state, game, "n")
    state.equipped = {}
    state.room_items.setdefault("garden", []).append("wood_sword")
    assert "já foi fabricado" in do(state, game, "fabricar espada de madeira")


def test_crafting_an_unknown_recipe_points_to_the_list(state, game):
    message = do(state, game, "fabricar canhão")
    assert "Não conheço a receita 'canhão'" in message
    assert "receitas" in message


def test_craft_without_a_name_asks_what(state, game):
    assert "Fabricar o quê" in do(state, game, "fabricar")


def test_crafting_with_an_ambiguous_name_asks_which(state, game):
    message = do(state, game, "fabricar espada")
    assert "Qual deles" in message
    assert "Espada de Madeira" in message
    assert "Espada de Cobre" in message


def test_craft_ignores_accents_and_case(state, game):
    state.inventory = ["wood"] * 4
    do(state, game, "fabricar BROQUEL de madeira")
    assert state.equipped == {"shield": "wood_shield"}


def test_a_full_chain_gather_craft_upgrade(state, game):
    do(state, game, "cortar 4")  # 8 wood
    do(state, game, "fabricar espada de madeira")  # -3 wood, worn
    do(state, game, "n")  # the garden has ore
    do(state, game, "minerar 3")  # 3 copper
    message = do(state, game, "fabricar espada de cobre")  # -1 wood, -2 copper
    assert "Você fabricou Espada de Cobre!" in message
    assert state.equipped == {"weapon": "copper_sword"}
    assert state.inventory.count("wood") == 4
    assert state.inventory.count("copper") == 1
    assert "wood_sword" in state.inventory
