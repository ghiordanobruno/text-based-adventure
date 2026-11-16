import json

import pytest

from adventure.world import (
    DEFAULT_WORLD_PATH,
    WorldError,
    load_world,
    parse_world,
    validate,
)


def _problems(data):
    return validate(parse_world(data))


def _has(problems, text):
    return any(text in problem for problem in problems)


# --- the real data file --------------------------------------------------------


def test_real_world_file_loads_and_is_valid():
    world = load_world()
    assert world.start in world.rooms
    assert len(world.rooms) >= 6


def test_real_world_file_is_utf8_json_with_expected_shape():
    data = json.loads(DEFAULT_WORLD_PATH.read_text(encoding="utf-8"))
    assert {"start", "rooms", "player", "progression", "endings"} <= data.keys()


def test_real_world_places_known_items_in_rooms():
    world = load_world()
    placed = [item for room in world.rooms.values() for item in room.items]
    assert "old_key" in placed
    assert set(placed) <= set(world.items)


def test_real_world_has_a_locked_door_a_final_monster_and_both_endings():
    world = load_world()
    assert any(room.locks for room in world.rooms.values())
    assert any(monster.final for monster in world.monsters.values())
    assert set(world.endings) == {"victory", "defeat"}


def test_real_world_has_safe_rooms_and_a_shop_selling_healing_items():
    world = load_world()
    assert sum(room.safe for room in world.rooms.values()) >= 2
    sold = [item for room in world.rooms.values() for item in room.sells]
    assert sold
    assert all(world.items[item].consumable for item in sold)


def test_real_world_has_at_least_five_distinct_monsters_in_rooms():
    world = load_world()
    monsters = [r.monster for r in world.rooms.values() if r.monster]
    assert len(monsters) >= 5
    assert len(set(monsters)) == len(monsters)


# --- consistency checks --------------------------------------------------------


def test_small_world_with_unreachable_room_reports_it(small_world_data):
    # "pit" has no way in.
    assert _problems(small_world_data) == ["room 'pit' is unreachable from the start"]


def test_valid_world_has_no_problems(small_world_data):
    del small_world_data["rooms"]["pit"]
    assert _problems(small_world_data) == []


def test_missing_start_room_is_reported(small_world_data):
    small_world_data["start"] = "nowhere"
    assert _has(_problems(small_world_data), "start room 'nowhere'")


def test_exit_to_missing_room_is_reported(small_world_data):
    small_world_data["rooms"]["hall"]["exits"]["east"] = "ghost"
    assert _has(_problems(small_world_data), "missing room 'ghost'")


def test_unknown_direction_is_reported(small_world_data):
    small_world_data["rooms"]["hall"]["exits"]["up"] = "garden"
    assert _has(_problems(small_world_data), "unknown direction 'up'")


def test_non_reciprocal_exit_is_reported(small_world_data):
    small_world_data["rooms"]["garden"]["exits"] = {}
    assert _has(_problems(small_world_data), "not reciprocal")


def test_one_way_exit_does_not_need_a_way_back(small_world_data):
    del small_world_data["rooms"]["pit"]
    del small_world_data["rooms"]["garden"]["exits"]["south"]
    small_world_data["rooms"]["hall"]["one_way"] = ["north"]
    assert _problems(small_world_data) == []


def test_unknown_item_in_room_is_reported(small_world_data):
    small_world_data["rooms"]["garden"]["items"] = ["ghost"]
    assert _has(_problems(small_world_data), "unknown item 'ghost'")


def test_unique_item_placed_in_two_rooms_is_reported(small_world_data):
    small_world_data["rooms"]["garden"]["items"] = ["lamp"]
    assert _has(_problems(small_world_data), "placed in both")


def test_consumable_may_be_placed_in_several_rooms(small_world_data):
    del small_world_data["rooms"]["pit"]
    small_world_data["rooms"]["garden"]["items"] = ["blue_potion"]
    small_world_data["rooms"]["cellar"]["items"] = ["blue_potion"]
    assert _problems(small_world_data) == []


def test_unknown_monster_in_room_is_reported(small_world_data):
    small_world_data["rooms"]["garden"]["monster"] = "dragon"
    assert _has(_problems(small_world_data), "unknown monster 'dragon'")


def test_lock_without_exit_is_reported(small_world_data):
    small_world_data["rooms"]["cellar"]["locks"] = {"east": "old_key"}
    assert _has(_problems(small_world_data), "no exit")


def test_lock_with_unknown_key_is_reported(small_world_data):
    small_world_data["rooms"]["garden"]["locks"]["east"] = "ghost"
    assert _has(_problems(small_world_data), "unknown item 'ghost'")


def test_safe_room_with_a_monster_is_reported(small_world_data):
    small_world_data["rooms"]["cellar"]["safe"] = True
    assert _has(_problems(small_world_data), "safe room cannot have")


def test_start_room_with_a_monster_is_reported(small_world_data):
    small_world_data["rooms"]["hall"]["monster"] = "rat"
    assert _has(_problems(small_world_data), "start room cannot have")


def test_world_without_a_final_monster_is_reported(small_world_data):
    small_world_data["monsters"]["ogre"]["final"] = False
    assert _has(_problems(small_world_data), "no final monster")


@pytest.mark.parametrize("ending", ["victory", "defeat"])
def test_missing_ending_is_reported(small_world_data, ending):
    del small_world_data["endings"][ending]
    assert _has(_problems(small_world_data), f"missing ending '{ending}'")


# --- shop, items, progression and stats ------------------------------------------


def test_selling_an_unknown_item_is_reported(small_world_data):
    small_world_data["rooms"]["hall"]["sells"].append("ghost")
    assert _has(_problems(small_world_data), "sells unknown item 'ghost'")


def test_selling_an_item_without_a_price_is_reported(small_world_data):
    small_world_data["rooms"]["hall"]["sells"].append("lamp")
    assert _has(_problems(small_world_data), "sold but has no price")


@pytest.mark.parametrize(
    ("field", "value"), [("heal", 101), ("heal", -1), ("price", -5)]
)
def test_bad_item_numbers_are_reported(small_world_data, field, value):
    small_world_data["items"]["blue_potion"][field] = value
    assert _has(_problems(small_world_data), "item 'blue_potion'")


def test_non_positive_monster_stats_are_reported(small_world_data):
    small_world_data["monsters"]["rat"]["max_hp"] = 0
    assert _has(_problems(small_world_data), "monster 'rat'")


def test_negative_monster_rewards_are_reported(small_world_data):
    small_world_data["monsters"]["rat"]["xp"] = -1
    assert _has(_problems(small_world_data), "xp and gold must be >= 0")


def test_non_positive_player_stats_are_reported(small_world_data):
    small_world_data["player"]["attack"] = 0
    assert any(p.startswith("player:") for p in _problems(small_world_data))


def test_negative_starting_gold_is_reported(small_world_data):
    small_world_data["player"]["gold"] = -1
    assert _has(_problems(small_world_data), "gold must be >= 0")


@pytest.mark.parametrize("thresholds", [[10, 10], [30, 10], [0, 10], [-5]])
def test_bad_xp_thresholds_are_reported(small_world_data, thresholds):
    small_world_data["progression"]["xp_to_level"] = thresholds
    assert _has(_problems(small_world_data), "increasing")


def test_negative_level_gains_are_reported(small_world_data):
    small_world_data["progression"]["attack"] = -1
    assert _has(_problems(small_world_data), "level gains")


def test_a_world_without_levels_is_valid(small_world_data):
    del small_world_data["rooms"]["pit"]
    small_world_data["progression"]["xp_to_level"] = []
    assert _problems(small_world_data) == []


# --- equipment, materials, resource nodes and recipes ------------------------------


def test_equipment_item_properties(world):
    sword = world.items["wood_sword"]
    assert sword.equipment
    assert sword.slot == "weapon"
    assert not sword.stackable
    assert world.items["wood"].stackable
    assert world.items["blue_potion"].stackable
    assert not world.items["old_key"].equipment


def test_unknown_slot_is_reported(small_world_data):
    small_world_data["items"]["wood_sword"]["slot"] = "hat"
    assert _has(_problems(small_world_data), "unknown slot 'hat'")


def test_bonus_without_a_slot_is_reported(small_world_data):
    small_world_data["items"]["lamp"]["attack"] = 3
    assert _has(_problems(small_world_data), "no slot")


def test_negative_bonus_is_reported(small_world_data):
    small_world_data["items"]["wood_sword"]["attack"] = -1
    assert _has(_problems(small_world_data), "bonuses must be >= 0")


@pytest.mark.parametrize("extra", [{"heal": 50}, {"material": True}])
def test_equipment_that_is_also_consumable_or_material_is_reported(
    small_world_data, extra
):
    small_world_data["items"]["wood_sword"].update(extra)
    assert _has(_problems(small_world_data), "cannot be a consumable or a material")


def test_item_that_is_both_consumable_and_material_is_reported(small_world_data):
    small_world_data["items"]["wood"]["heal"] = 10
    assert _has(_problems(small_world_data), "both a consumable and a material")


def test_materials_may_be_placed_in_several_rooms(small_world_data):
    del small_world_data["rooms"]["pit"]
    small_world_data["rooms"]["garden"]["items"] = ["wood"]
    small_world_data["rooms"]["cellar"]["items"] = ["wood"]
    assert _problems(small_world_data) == []


def test_starting_equipment_must_exist_and_fit_its_slot(small_world_data):
    small_world_data["player"]["equipment"] = {"weapon": "wood_shield"}
    assert _has(_problems(small_world_data), "starting weapon must be")
    small_world_data["player"]["equipment"] = {"weapon": "ghost"}
    assert _has(_problems(small_world_data), "starting weapon must be")


def test_starting_equipment_cannot_also_lie_in_a_room(small_world_data):
    small_world_data["player"]["equipment"] = {"armor": "leather_armor"}
    assert _has(_problems(small_world_data), "worn at the start and lies in a room")


def test_gather_node_with_an_unknown_kind_is_reported(small_world_data):
    node = small_world_data["rooms"]["hall"]["gather"].pop("chop")
    small_world_data["rooms"]["hall"]["gather"]["fish"] = node
    assert _has(_problems(small_world_data), "unknown gather kind 'fish'")


def test_gather_node_must_give_a_material(small_world_data):
    small_world_data["rooms"]["hall"]["gather"]["chop"]["item"] = "lamp"
    assert _has(_problems(small_world_data), "must give a material")
    small_world_data["rooms"]["hall"]["gather"]["chop"]["item"] = "ghost"
    assert _has(_problems(small_world_data), "must give a material")


@pytest.mark.parametrize("field", ["amount", "uses"])
def test_gather_node_numbers_must_be_positive(small_world_data, field):
    small_world_data["rooms"]["hall"]["gather"]["chop"][field] = 0
    assert _has(_problems(small_world_data), "amount and uses must be > 0")


def test_recipe_result_must_be_equipment(small_world_data):
    small_world_data["recipes"]["lamp"] = {"wood": 1}
    assert _has(_problems(small_world_data), "result must be an equipment item")


def test_recipe_with_an_unknown_result_is_reported(small_world_data):
    small_world_data["recipes"]["ghost"] = {"wood": 1}
    assert _has(_problems(small_world_data), "result must be an equipment item")


def test_recipe_ingredients_must_be_materials(small_world_data):
    small_world_data["recipes"]["wood_sword"] = {"lamp": 1}
    assert _has(_problems(small_world_data), "'lamp' must be a material")


def test_recipe_ingredient_must_be_gatherable_somewhere(small_world_data):
    small_world_data["items"]["gold_dust"] = {"name": "Pó de Ouro", "material": True}
    small_world_data["recipes"]["wood_sword"] = {"gold_dust": 1}
    assert _has(_problems(small_world_data), "cannot be gathered anywhere")


def test_recipe_amounts_must_be_positive(small_world_data):
    small_world_data["recipes"]["wood_sword"] = {"wood": 0}
    assert _has(_problems(small_world_data), "amounts must be > 0")


def test_recipe_without_ingredients_is_reported(small_world_data):
    small_world_data["recipes"]["wood_sword"] = {}
    assert _has(_problems(small_world_data), "at least one ingredient")


def test_real_world_starts_with_a_full_set_of_gear():
    world = load_world()
    assert set(world.player.equipment) == {"weapon", "shield", "armor"}
    assert all(world.items[i].equipment for i in world.player.equipment.values())


def test_real_world_has_enough_materials_for_every_recipe_at_once():
    """Crafting the whole set (wood and copper) must be possible in one game."""
    world = load_world()
    available: dict[str, int] = {}
    for room in world.rooms.values():
        for node in room.gather.values():
            available[node.item] = available.get(node.item, 0) + node.amount * node.uses
    needed: dict[str, int] = {}
    for recipe in world.recipes.values():
        for material, count in recipe.ingredients.items():
            needed[material] = needed.get(material, 0) + count
    assert needed
    for material, count in needed.items():
        assert available[material] >= count, material


def test_real_world_better_gear_costs_more_and_gives_more():
    world = load_world()
    wood = world.items["wooden_sword"].attack
    copper = world.items["copper_sword"].attack
    assert world.items["toy_sword"].attack < wood < copper
    assert (
        world.items["cardboard_buckler"].defense < world.items["wooden_buckler"].defense
    )
    assert world.items["wooden_armor"].defense < world.items["copper_armor"].defense


def test_real_world_recipe_results_are_not_lying_around():
    world = load_world()
    placed = {item for room in world.rooms.values() for item in room.items}
    assert not placed & set(world.recipes)


# --- parsing and loading ---------------------------------------------------------


@pytest.mark.parametrize("section", ["player", "progression", "endings"])
def test_missing_required_section_raises_world_error(small_world_data, section):
    del small_world_data[section]
    with pytest.raises(WorldError):
        parse_world(small_world_data)


@pytest.mark.parametrize(
    "path",
    [
        ("monsters", "rat", "attack"),
        ("monsters", "rat", "xp"),
        ("player", "gold"),
        ("items", "blue_potion", "price"),
        ("items", "wood_sword", "attack"),
        ("recipes", "wood_sword", "wood"),
        ("rooms", "hall", "gather", "chop", "uses"),
    ],
)
def test_non_numeric_value_raises_world_error(small_world_data, path):
    *parents, key = path
    node = small_world_data
    for parent in parents:
        node = node[parent]
    node[key] = "muito"
    with pytest.raises(WorldError):
        parse_world(small_world_data)


def test_monster_without_rewards_raises_world_error(small_world_data):
    del small_world_data["monsters"]["rat"]["gold"]
    with pytest.raises(WorldError):
        parse_world(small_world_data)


def test_malformed_room_raises_world_error():
    with pytest.raises(WorldError):
        parse_world({"start": "a", "rooms": {"a": {"name": "A"}}})


def test_load_world_rejects_invalid_world(tmp_path, small_world_data):
    path = tmp_path / "world.json"
    path.write_text(json.dumps(small_world_data), encoding="utf-8")
    with pytest.raises(WorldError, match="unreachable"):
        load_world(path)


def test_load_world_rejects_missing_or_broken_file(tmp_path):
    with pytest.raises(WorldError):
        load_world(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(WorldError):
        load_world(broken)
