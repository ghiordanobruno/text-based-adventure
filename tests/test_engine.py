from adventure.engine import HELP_TEXT, describe_room, execute
from adventure.parser import Command
from adventure.saves import load_game, save_path
from adventure.state import GameState


def test_help_lists_commands_and_keeps_game_running(state, game):
    assert execute(state, Command("help"), game) == HELP_TEXT
    assert state.running


def test_quit_stops_the_game(state, game):
    execute(state, Command("quit"), game)
    assert not state.running


def test_unknown_verb_reports_it_without_changing_state(state, game):
    message = execute(state, Command("dançar"), game)
    assert "dançar" in message
    assert state.running
    assert state.current_room == "hall"


# --- look / go ---------------------------------------------------------------


def test_look_describes_room_with_name_description_and_exits(state, game):
    message = execute(state, Command("look"), game)
    assert "Salão" in message
    assert "Um salão vazio." in message
    assert "Saídas: norte" in message


def test_look_lists_items_lying_in_the_room(state, game):
    message = execute(state, Command("look"), game)
    assert "Você vê: Chave Velha, Chave Nova, Lanterna" in message


def test_room_without_items_has_no_items_line(state, game):
    message = execute(state, Command("go", "north"), game)
    assert "Você vê" not in message


def test_room_without_exits_says_there_are_none(world):
    assert "Saídas: nenhuma" in describe_room(GameState(current_room="pit"), world)


def test_go_moves_player_and_describes_new_room(state, game):
    message = execute(state, Command("go", "north"), game)
    assert state.current_room == "garden"
    assert "Jardim" in message
    assert "Saídas: norte, sul, leste" in message


def test_go_there_and_back_returns_to_the_same_room(state, game):
    execute(state, Command("go", "north"), game)
    execute(state, Command("go", "south"), game)
    assert state.current_room == "hall"


def test_go_without_exit_blocks_and_keeps_room(state, game):
    message = execute(state, Command("go", "west"), game)
    assert state.current_room == "hall"
    assert "Não há caminho para o oeste" in message


def test_go_without_direction_asks_where(state, game):
    message = execute(state, Command("go"), game)
    assert "Ir para onde" in message
    assert state.current_room == "hall"


def test_go_with_unknown_direction_reports_it(state, game):
    message = execute(state, Command("go", "cima"), game)
    assert "cima" in message
    assert state.current_room == "hall"


# --- take / drop / inventory ---------------------------------------------------


def test_take_moves_item_from_room_to_inventory(state, game):
    message = execute(state, Command("take", "lanterna"), game)
    assert "Lanterna" in message
    assert state.inventory == ["lamp"]
    assert "lamp" not in state.room_items["hall"]


def test_take_accepts_part_of_the_name(state, game):
    execute(state, Command("take", "velha"), game)
    assert state.inventory == ["old_key"]


def test_take_with_ambiguous_name_asks_which_and_takes_nothing(state, game):
    message = execute(state, Command("take", "chave"), game)
    assert "Qual deles" in message
    assert "Chave Velha" in message
    assert "Chave Nova" in message
    assert state.inventory == []


def test_take_unknown_item_reports_it(state, game):
    message = execute(state, Command("take", "espada"), game)
    assert "espada" in message
    assert state.inventory == []


def test_take_without_noun_asks_what(state, game):
    assert "Pegar o quê" in execute(state, Command("take"), game)


def test_take_item_that_is_in_another_room_fails(state, game):
    execute(state, Command("go", "north"), game)
    message = execute(state, Command("take", "lanterna"), game)
    assert "Não há" in message
    assert state.inventory == []


def test_taken_item_no_longer_shows_in_room(state, game):
    execute(state, Command("take", "lanterna"), game)
    assert "Lanterna" not in execute(state, Command("look"), game)


def test_drop_puts_item_in_the_current_room(state, game):
    execute(state, Command("take", "lanterna"), game)
    execute(state, Command("go", "north"), game)
    message = execute(state, Command("drop", "lanterna"), game)
    assert "Lanterna" in message
    assert state.inventory == []
    assert state.room_items["garden"] == ["lamp"]
    assert "Você vê: Lanterna" in execute(state, Command("look"), game)


def test_drop_item_not_carried_fails(state, game):
    message = execute(state, Command("drop", "lanterna"), game)
    assert "Você não tem" in message


def test_drop_without_noun_asks_what(state, game):
    assert "Largar o quê" in execute(state, Command("drop"), game)


def test_inventory_when_empty(state, game):
    assert execute(state, Command("inventory"), game) == "Você não carrega nada."


def test_inventory_lists_carried_items(state, game):
    execute(state, Command("take", "lanterna"), game)
    execute(state, Command("take", "velha"), game)
    message = execute(state, Command("inventory"), game)
    assert "Lanterna" in message
    assert "Chave Velha" in message


# --- save ----------------------------------------------------------------------


def test_save_writes_the_character_file(state, game):
    message = execute(state, Command("save"), game)
    assert "Jogo salvo" in message
    assert save_path("Teste", game.saves_dir).exists()


def test_saved_game_can_be_loaded_with_progress_intact(state, game, world):
    execute(state, Command("take", "lanterna"), game)
    execute(state, Command("go", "north"), game)
    execute(state, Command("save"), game)
    loaded = load_game("Teste", world, game.saves_dir)
    # `came_from` is session-only, so compare what actually gets saved.
    assert loaded.to_dict() == state.to_dict()


def test_save_without_character_name_reports_error(game):
    state = GameState(current_room="hall")
    assert "Não foi possível salvar" in execute(state, Command("save"), game)
