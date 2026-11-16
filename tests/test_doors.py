from helpers import do


def test_a_locked_exit_blocks_the_way(state, game):
    do(state, game, "n")
    message = do(state, game, "n")
    assert "trancada" in message
    assert state.current_room == "garden"


def test_looking_at_a_locked_exit_still_lists_it(state, game):
    do(state, game, "n")
    assert "Saídas: norte, sul, leste" in do(state, game, "olhar")


def test_using_the_right_key_opens_the_exit(state, game):
    do(state, game, "pegar velha")
    do(state, game, "n")
    message = do(state, game, "usar chave velha")
    assert "se abre" in message
    assert "norte" in message
    assert state.unlocked == ["garden:north"]
    do(state, game, "n")
    assert state.current_room == "lair"


def test_the_key_stays_in_the_inventory_after_use(state, game):
    do(state, game, "pegar velha")
    do(state, game, "n")
    do(state, game, "usar velha")
    assert state.inventory == ["old_key"]


def test_using_the_key_twice_does_nothing_the_second_time(state, game):
    do(state, game, "pegar velha")
    do(state, game, "n")
    do(state, game, "usar velha")
    assert "Não dá para usar" in do(state, game, "usar velha")
    assert state.unlocked == ["garden:north"]


def test_the_wrong_key_does_not_open_the_exit(state, game):
    do(state, game, "pegar nova")
    do(state, game, "n")
    assert "Não dá para usar" in do(state, game, "usar chave nova")
    assert "trancada" in do(state, game, "n")


def test_using_a_key_where_it_fits_nothing_does_nothing(state, game):
    do(state, game, "pegar velha")
    assert "Não dá para usar" in do(state, game, "usar velha")
    assert state.unlocked == []


def test_using_something_not_carried_fails(state, game):
    assert "Você não tem" in do(state, game, "usar lanterna")


def test_use_without_noun_asks_what(state, game):
    assert "Usar o quê" in do(state, game, "usar")


def test_using_an_ambiguous_name_asks_which(state, game):
    do(state, game, "pegar velha")
    do(state, game, "pegar nova")
    assert "Qual deles" in do(state, game, "usar chave")
