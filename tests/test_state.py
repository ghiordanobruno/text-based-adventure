import pytest

from adventure.state import SAVE_VERSION, Combat, GameState, SaveError


def test_new_game_starts_in_start_room_with_empty_inventory(world):
    state = GameState.new(world, "Maria")
    assert state.player_name == "Maria"
    assert state.current_room == world.start
    assert state.inventory == []
    assert state.running
    assert state.combat is None


def test_new_game_takes_stats_and_gold_from_the_world(world):
    state = GameState.new(world, "Maria")
    assert (state.max_hp, state.hp) == (30, 30)
    assert (state.attack, state.defense) == (10, 0)
    assert state.gold == 20
    assert (state.xp, state.level) == (0, 1)
    assert state.unlocked == []
    assert state.defeated == []
    assert state.gathered == {}
    assert state.equipped == {}  # the small world starts with no equipment


def test_new_game_places_items_where_the_world_says(world):
    state = GameState.new(world, "Maria")
    assert state.room_items == {"hall": ["old_key", "new_key", "lamp", "leather_armor"]}


def test_new_games_do_not_share_item_lists(world):
    first = GameState.new(world, "A")
    second = GameState.new(world, "B")
    first.room_items["hall"].remove("lamp")
    assert "lamp" in second.room_items["hall"]


def test_to_dict_has_version_and_no_session_fields(world):
    data = GameState.new(world, "Maria").to_dict()
    assert data["version"] == SAVE_VERSION
    for session_only in ("running", "combat", "came_from"):
        assert session_only not in data


def test_dict_round_trip_keeps_everything(world):
    state = GameState.new(world, "Maria")
    state.inventory.extend(["lamp", "blue_potion", "blue_potion", "wood", "wood"])
    state.room_items["hall"].remove("lamp")
    state.equipped = {"weapon": "wood_sword"}
    state.current_room = "garden"
    state.hp = 12
    state.gold = 99
    state.xp = 17
    state.level = 2
    state.unlocked.append("garden:north")
    state.defeated.append("cellar")
    state.gathered = {"hall:chop": 2, "garden:mine": 1}
    assert GameState.from_dict(state.to_dict()) == state


def test_a_fight_in_progress_is_not_saved(world):
    state = GameState.new(world, "Maria")
    state.combat = Combat("rat", 7)
    state.came_from = "garden"
    restored = GameState.from_dict(state.to_dict())
    assert restored.combat is None
    assert restored.came_from is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(version=1),  # saves from before M4
        lambda d: d.update(version=2),  # saves from before M5
        lambda d: d.update(version=3),  # saves from before equipment
        lambda d: d.update(version=999),
        lambda d: d.pop("version"),
        lambda d: d.pop("current_room"),
        lambda d: d.pop("inventory"),
        lambda d: d.pop("hp"),
        lambda d: d.pop("gold"),
        lambda d: d.pop("xp"),
        lambda d: d.pop("level"),
        lambda d: d.pop("unlocked"),
        lambda d: d.pop("defeated"),
        lambda d: d.pop("equipped"),
        lambda d: d.pop("gathered"),
        lambda d: d.update(inventory=5),
        lambda d: d.update(room_items=[]),
        lambda d: d.update(equipped=[]),
        lambda d: d.update(gathered=5),
        lambda d: d.update(gathered={"hall:chop": "muito"}),
        lambda d: d.update(hp="muita"),
        lambda d: d.update(gold="rico"),
        lambda d: d.update(attack=None),
    ],
)
def test_from_dict_rejects_bad_data(world, mutate):
    data = GameState.new(world, "Maria").to_dict()
    mutate(data)
    with pytest.raises(SaveError):
        GameState.from_dict(data)


def test_from_dict_rejects_non_dict():
    with pytest.raises(SaveError):
        GameState.from_dict([])  # type: ignore[arg-type]
