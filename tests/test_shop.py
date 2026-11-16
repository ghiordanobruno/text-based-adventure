"""Shop, healing items and the player profile."""

import pytest

from helpers import do


def test_shop_lists_wares_and_gold(state, game):
    message = do(state, game, "loja")
    assert "Poção Azul - 10 de ouro" in message
    assert "Poção Vermelha - 30 de ouro" in message
    assert "seu ouro: 20" in message


def test_looking_around_a_shop_mentions_it(state, game):
    assert "Loja:" in do(state, game, "olhar")


def test_there_is_no_shop_elsewhere(state, game):
    do(state, game, "n")
    assert "Não há nada à venda" in do(state, game, "loja")
    assert "Não há nada à venda" in do(state, game, "comprar azul")
    assert "Loja:" not in do(state, game, "olhar")


# --- buying ------------------------------------------------------------------


def test_buy_one_item(state, game):
    message = do(state, game, "comprar poção azul")
    assert "1x Poção Azul por 10 de ouro" in message
    assert "Ouro restante: 10" in message
    assert state.inventory == ["blue_potion"]
    assert state.gold == 10


def test_buy_a_quantity(state, game):
    do(state, game, "comprar pocao azul 2")
    assert state.inventory == ["blue_potion", "blue_potion"]
    assert state.gold == 0


def test_buy_accepts_part_of_the_name_and_ignores_accents(state, game):
    do(state, game, "comprar azul")
    assert state.inventory == ["blue_potion"]


def test_buy_with_an_ambiguous_name_asks_which(state, game):
    message = do(state, game, "comprar pocao")
    assert "Qual deles" in message
    assert state.inventory == []
    assert state.gold == 20


def test_buy_without_enough_gold_changes_nothing(state, game):
    message = do(state, game, "comprar vermelha")
    assert "precisa de 30" in message
    assert "só tem 20" in message
    assert state.inventory == []
    assert state.gold == 20


def test_buying_many_checks_the_total_price(state, game):
    assert "precisa de 30" in do(state, game, "comprar azul 3")
    assert state.gold == 20


def test_buy_something_not_for_sale(state, game):
    assert "Não vendemos 'espada'" in do(state, game, "comprar espada")


def test_buy_without_a_name_asks_what(state, game):
    assert "Comprar o quê" in do(state, game, "comprar")
    assert "Comprar o quê" in do(state, game, "comprar 2")


@pytest.mark.parametrize("quantity", ["0", "100"])
def test_buy_rejects_silly_quantities(state, game, quantity):
    assert "Quantidade inválida" in do(state, game, f"comprar azul {quantity}")
    assert state.gold == 20


def test_inventory_groups_a_stack_of_potions(state, game):
    do(state, game, "comprar azul 2")
    message = do(state, game, "inventario")
    assert "Poção Azul x2" in message
    assert message.count("Poção Azul") == 1


def test_inventory_shows_a_single_item_without_a_count(state, game):
    do(state, game, "comprar azul")
    assert "x1" not in do(state, game, "inventario")


# --- using healing items ---------------------------------------------------------


def test_using_a_potion_heals_by_a_percentage_and_uses_it_up(state, game):
    do(state, game, "comprar azul")
    state.hp = 10
    message = do(state, game, "usar azul")
    assert "recupera 15 de vida" in message  # 50% of 30
    assert state.hp == 25
    assert state.inventory == []


def test_healing_never_goes_over_the_maximum(state, game):
    do(state, game, "comprar azul")
    state.hp = 25
    assert "recupera 5 de vida" in do(state, game, "usar azul")
    assert state.hp == 30


def test_using_a_potion_at_full_life_is_refused_and_keeps_it(state, game):
    do(state, game, "comprar azul")
    message = do(state, game, "usar azul")
    assert "já está cheia" in message
    assert state.inventory == ["blue_potion"]


def test_using_one_potion_from_a_stack_leaves_the_others(state, game):
    do(state, game, "comprar azul 2")
    state.hp = 1
    do(state, game, "usar poção azul")
    assert state.inventory == ["blue_potion"]


def test_dropping_one_potion_from_a_stack_does_not_ask_which(state, game):
    do(state, game, "comprar azul 2")
    do(state, game, "largar azul")
    assert state.inventory == ["blue_potion"]
    assert state.room_items["hall"][-1] == "blue_potion"


def test_a_potion_can_be_used_during_a_fight_and_the_monster_answers(state, game):
    do(state, game, "comprar azul")
    do(state, game, "n")
    do(state, game, "l")  # a rat (attack 4) is waiting in the cellar
    state.hp = 10
    message = do(state, game, "usar azul")
    assert "recupera 15 de vida" in message
    assert "Rato te acertou e causou 4 de dano" in message
    assert state.hp == 21
    assert state.combat is not None


def test_a_potion_can_save_the_player_in_a_fight_but_not_always(state, game):
    do(state, game, "comprar azul")
    do(state, game, "n")
    do(state, game, "l")
    state.hp = 2  # +15 from the potion, then the rat hits for 4: survives
    do(state, game, "usar azul")
    assert state.running
    assert state.hp == 13


def test_a_key_is_not_a_consumable(state, game):
    do(state, game, "pegar velha")
    assert "Não dá para usar" in do(state, game, "usar velha")
    assert state.inventory == ["old_key"]


# --- profile ---------------------------------------------------------------------


def test_profile_shows_level_xp_stats_and_gold(state, game):
    message = do(state, game, "perfil")
    assert "Teste - nível 1" in message
    assert "Experiência: 0/10" in message
    assert "Vida: 30/30" in message
    assert "Ataque: 10" in message
    assert "Defesa: 0" in message
    assert "Ouro: 20" in message


def test_profile_at_the_maximum_level(state, game):
    state.level = 3
    state.xp = 99
    assert "99 (nível máximo)" in do(state, game, "perfil")


@pytest.mark.parametrize("line", ["perfil", "status", "p"])
def test_profile_aliases_work_during_a_fight(state, game, line):
    do(state, game, "n")
    do(state, game, "l")
    assert "Você está em combate" not in do(state, game, line)
