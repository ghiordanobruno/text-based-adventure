import json

import pytest

from adventure.saves import load_game, save_game, save_path, slugify
from adventure.state import GameState, SaveError


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("João da Silva", "joao-da-silva"),
        ("  Ana  ", "ana"),
        ("A/B\\..", "a-b"),
        ("MAGO_2", "mago-2"),
    ],
)
def test_slugify_makes_safe_ascii_names(name, slug):
    assert slugify(name) == slug


@pytest.mark.parametrize("name", ["", "   ", "!!!", "日本"])
def test_slugify_rejects_names_without_letters_or_digits(name):
    with pytest.raises(SaveError):
        slugify(name)


def test_save_path_avoids_windows_reserved_names(tmp_path):
    assert save_path("con", tmp_path).name == "character-con.json"


def test_save_then_load_returns_the_same_state(world, tmp_path):
    state = GameState.new(world, "Maria")
    state.inventory.append("lamp")
    state.room_items["hall"].remove("lamp")
    state.current_room = "garden"
    state.hp = 12
    state.unlocked.append("garden:north")
    state.defeated.append("cellar")
    state.gold = 99
    state.xp = 17
    state.level = 2
    state.inventory.extend(["blue_potion", "blue_potion"])  # a stack is fine
    state.inventory.extend(["wood"] * 5)  # so are materials
    state.equipped = {"weapon": "wood_sword", "armor": "leather_armor"}
    state.room_items["hall"].remove("leather_armor")
    state.gathered = {"hall:chop": 4, "garden:mine": 2}
    save_game(state, tmp_path)
    assert load_game("Maria", world, tmp_path) == state


def test_save_creates_missing_folder_and_leaves_no_temp_file(world, tmp_path):
    folder = tmp_path / "nested" / "saves"
    save_game(GameState.new(world, "Maria"), folder)
    assert [p.name for p in folder.iterdir()] == ["character-maria.json"]


def test_save_overwrites_the_previous_save(world, tmp_path):
    state = GameState.new(world, "Maria")
    save_game(state, tmp_path)
    state.current_room = "garden"
    save_game(state, tmp_path)
    assert load_game("Maria", world, tmp_path).current_room == "garden"


def test_save_file_is_readable_utf8_json_with_accents(world, tmp_path):
    path = save_game(GameState.new(world, "João"), tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["player_name"] == "João"


def test_names_with_same_slug_share_a_character(world, tmp_path):
    save_game(GameState.new(world, "João"), tmp_path)
    assert load_game("Joao", world, tmp_path).player_name == "João"


def test_load_returns_none_when_character_has_no_save(world, tmp_path):
    assert load_game("Ninguém", world, tmp_path) is None


def test_load_rejects_broken_json(world, tmp_path):
    save_path("Maria", tmp_path).write_text("{oops", encoding="utf-8")
    with pytest.raises(SaveError):
        load_game("Maria", world, tmp_path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(current_room="nowhere"),
        lambda d: d["room_items"].update(nowhere=[]),
        lambda d: d["inventory"].append("ghost"),
        lambda d: d["inventory"].append("lamp"),  # also still lying in the hall
        lambda d: d.update(hp=0),
        lambda d: d.update(hp=31),  # more than max_hp (30)
        lambda d: d["unlocked"].append("hall:north"),  # not a locked exit
        lambda d: d["defeated"].append("hall"),  # no monster there
        lambda d: d["defeated"].append("nowhere"),
        lambda d: d.update(gold=-1),
        lambda d: d.update(xp=-1),
        lambda d: d.update(level=0),
        lambda d: d.update(level=4),  # the small world has 3 levels
        lambda d: d["inventory"].extend(["lamp", "lamp"]),  # a unique item twice
        lambda d: d["equipped"].update(weapon="ghost"),
        lambda d: d["equipped"].update(armor="wood_sword"),  # a sword is no armor
        lambda d: d["equipped"].update(weapon="wood_sword", shield="wood_sword"),
        lambda d: (
            d["inventory"].append("wood_sword")
            or d["equipped"].update(weapon="wood_sword")
        ),  # worn and carried
        lambda d: d["gathered"].update({"nowhere:chop": 1}),
        lambda d: d["gathered"].update({"hall:mine": 1}),  # no ore in the hall
        lambda d: d["gathered"].update({"hall:chop": 5}),  # the node has 4 uses
        lambda d: d["gathered"].update({"hall:chop": -1}),
    ],
)
def test_load_rejects_saves_that_do_not_match_the_world(world, tmp_path, mutate):
    data = GameState.new(world, "Maria").to_dict()
    mutate(data)
    save_path("Maria", tmp_path).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SaveError):
        load_game("Maria", world, tmp_path)
