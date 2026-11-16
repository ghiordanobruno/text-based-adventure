"""The world: rooms, exits, items, monsters, recipes, progression and endings.

Loaded from JSON and validated. Pure: no I/O besides reading the data file.
"""

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from adventure.directions import LABELS, OPPOSITE

DEFAULT_WORLD_PATH = Path(__file__).resolve().parents[2] / "data" / "world.json"

ENDINGS = ("victory", "defeat")
SLOTS = ("weapon", "shield", "armor")  # equipment slots, in display order
GATHER_KINDS = ("chop", "mine")  # what a room's resource nodes can be


class WorldError(ValueError):
    """The world data is malformed or inconsistent."""


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    heal: int = 0  # % of max life restored when used; 0 means not a consumable
    price: int = 0  # gold; only matters for items a room sells
    slot: str | None = None  # equipment slot; None means not equipment
    attack: int = 0  # equipment bonus
    defense: int = 0  # equipment bonus
    material: bool = False  # crafting ingredient (stacks)

    @property
    def consumable(self) -> bool:
        return self.heal > 0

    @property
    def equipment(self) -> bool:
        return self.slot is not None

    @property
    def stackable(self) -> bool:
        """Stackable items can be carried many times; every other item is unique."""
        return self.consumable or self.material


@dataclass(frozen=True)
class Monster:
    id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    xp: int  # experience given when defeated
    gold: int  # gold given when defeated
    final: bool = False  # defeating the final monster wins the game


@dataclass(frozen=True)
class PlayerStats:
    """What a new character starts with."""

    max_hp: int
    attack: int
    defense: int
    gold: int
    equipment: dict[str, str] = field(default_factory=dict)  # slot -> item id


@dataclass(frozen=True)
class Progression:
    """Experience needed for each level, and what each level adds."""

    xp_to_level: tuple[int, ...]  # xp needed for level 2, level 3, ...
    max_hp: int
    attack: int
    defense: int


@dataclass(frozen=True)
class Gather:
    """A resource node in a room: `uses` times you may gather `amount` of `item`."""

    item: str
    amount: int
    uses: int


@dataclass(frozen=True)
class Recipe:
    """How to craft one equipment item: material id -> how many."""

    result: str
    ingredients: dict[str, int]


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    description: str
    exits: dict[str, str]  # canonical direction -> room id
    one_way: frozenset[str] = frozenset()  # exits that need no way back
    items: tuple[str, ...] = ()  # item ids lying here when a new game starts
    locks: dict[str, str] = field(default_factory=dict)  # direction -> key item id
    safe: bool = False  # the player can rest here
    monster: str | None = None  # monster id waiting here until defeated
    sells: tuple[str, ...] = ()  # item ids for sale here
    gather: dict[str, Gather] = field(default_factory=dict)  # "chop" / "mine" -> node


@dataclass(frozen=True)
class World:
    start: str
    rooms: dict[str, Room]
    player: PlayerStats
    progression: Progression
    endings: dict[str, str]  # "victory" / "defeat" -> text shown at the end
    items: dict[str, Item] = field(default_factory=dict)
    monsters: dict[str, Monster] = field(default_factory=dict)
    recipes: dict[str, Recipe] = field(default_factory=dict)  # keyed by result item


def lock_id(room_id: str, direction: str) -> str:
    """Stable id of a locked exit, as stored in saves."""
    return f"{room_id}:{direction}"


def gather_id(room_id: str, kind: str) -> str:
    """Stable id of a room's resource node, as stored in saves."""
    return f"{room_id}:{kind}"


def parse_world(data: dict[str, Any]) -> World:
    """Build a World from decoded JSON. Does not check consistency."""
    try:
        rooms = {
            room_id: Room(
                id=room_id,
                name=raw["name"],
                description=raw["description"],
                exits=dict(raw.get("exits", {})),
                one_way=frozenset(raw.get("one_way", ())),
                items=tuple(raw.get("items", ())),
                locks=dict(raw.get("locks", {})),
                safe=bool(raw.get("safe", False)),
                monster=raw.get("monster"),
                sells=tuple(raw.get("sells", ())),
                gather={
                    str(kind): Gather(
                        item=str(node["item"]),
                        amount=int(node["amount"]),
                        uses=int(node["uses"]),
                    )
                    for kind, node in raw.get("gather", {}).items()
                },
            )
            for room_id, raw in data["rooms"].items()
        }
        items = {
            item_id: Item(
                id=item_id,
                name=raw["name"],
                heal=int(raw.get("heal", 0)),
                price=int(raw.get("price", 0)),
                slot=raw.get("slot"),
                attack=int(raw.get("attack", 0)),
                defense=int(raw.get("defense", 0)),
                material=bool(raw.get("material", False)),
            )
            for item_id, raw in data.get("items", {}).items()
        }
        monsters = {
            monster_id: Monster(
                id=monster_id,
                name=raw["name"],
                max_hp=int(raw["max_hp"]),
                attack=int(raw["attack"]),
                defense=int(raw["defense"]),
                xp=int(raw["xp"]),
                gold=int(raw["gold"]),
                final=bool(raw.get("final", False)),
            )
            for monster_id, raw in data.get("monsters", {}).items()
        }
        recipes = {
            result: Recipe(
                result=result,
                ingredients={str(i): int(n) for i, n in ingredients.items()},
            )
            for result, ingredients in data.get("recipes", {}).items()
        }
        raw_player = data["player"]
        player = PlayerStats(
            max_hp=int(raw_player["max_hp"]),
            attack=int(raw_player["attack"]),
            defense=int(raw_player["defense"]),
            gold=int(raw_player["gold"]),
            equipment={
                str(s): str(i) for s, i in raw_player.get("equipment", {}).items()
            },
        )
        raw_progression = data["progression"]
        progression = Progression(
            xp_to_level=tuple(int(xp) for xp in raw_progression["xp_to_level"]),
            max_hp=int(raw_progression["max_hp"]),
            attack=int(raw_progression["attack"]),
            defense=int(raw_progression["defense"]),
        )
        endings = {str(key): str(text) for key, text in data["endings"].items()}
        return World(
            start=data["start"],
            rooms=rooms,
            player=player,
            progression=progression,
            endings=endings,
            items=items,
            monsters=monsters,
            recipes=recipes,
        )
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise WorldError(f"malformed world data: {error!r}") from error


def validate(world: World) -> list[str]:
    """Return a list of problems found in the world (empty if it is valid)."""
    problems: list[str] = []
    if world.start not in world.rooms:
        problems.append(f"start room '{world.start}' does not exist")
    problems += _stat_problems("player", world.player)
    if world.player.gold < 0:
        problems.append("player: gold must be >= 0")
    for monster in world.monsters.values():
        problems += _stat_problems(f"monster '{monster.id}'", monster)
        if monster.xp < 0 or monster.gold < 0:
            problems.append(f"monster '{monster.id}': xp and gold must be >= 0")
    for item in world.items.values():
        problems += _item_problems(item)
    problems += _starting_equipment_problems(world)
    problems += _recipe_problems(world)
    problems += _progression_problems(world.progression)
    for ending in ENDINGS:
        if ending not in world.endings:
            problems.append(f"missing ending '{ending}'")
    placed: dict[str, str] = {}
    for room in world.rooms.values():
        problems += _exit_problems(world, room)
        problems += _content_problems(world, room, placed)
    for item_id in world.player.equipment.values():
        if item_id in placed:
            problems.append(f"item '{item_id}' is worn at the start and lies in a room")
    if not any(
        room.monster in world.monsters and world.monsters[room.monster].final
        for room in world.rooms.values()
    ):
        problems.append("no final monster is placed in any room")
    if world.start in world.rooms:
        for room_id in sorted(set(world.rooms) - _reachable(world)):
            problems.append(f"room '{room_id}' is unreachable from the start")
    return problems


def _stat_problems(label: str, stats: PlayerStats | Monster) -> list[str]:
    if stats.max_hp <= 0 or stats.attack <= 0 or stats.defense < 0:
        return [f"{label}: max_hp and attack must be > 0, defense >= 0"]
    return []


def _item_problems(item: Item) -> list[str]:
    label = f"item '{item.id}'"
    problems: list[str] = []
    if not 0 <= item.heal <= 100 or item.price < 0:
        problems.append(f"{label}: heal must be 0-100, price >= 0")
    if item.attack < 0 or item.defense < 0:
        problems.append(f"{label}: equipment bonuses must be >= 0")
    if item.slot is not None and item.slot not in SLOTS:
        problems.append(f"{label}: unknown slot '{item.slot}'")
    if item.slot is None and (item.attack or item.defense):
        problems.append(f"{label}: has an attack/defense bonus but no slot")
    if item.slot is not None and (item.consumable or item.material):
        problems.append(f"{label}: equipment cannot be a consumable or a material")
    if item.consumable and item.material:
        problems.append(f"{label}: cannot be both a consumable and a material")
    return problems


def _starting_equipment_problems(world: World) -> list[str]:
    problems: list[str] = []
    for slot, item_id in world.player.equipment.items():
        item = world.items.get(item_id)
        if item is None or item.slot != slot:
            problems.append(f"player: starting {slot} must be an item for that slot")
    return problems


def _recipe_problems(world: World) -> list[str]:
    problems: list[str] = []
    gatherable = {
        node.item for room in world.rooms.values() for node in room.gather.values()
    }
    for result_id, recipe in world.recipes.items():
        label = f"recipe '{result_id}'"
        result = world.items.get(result_id)
        if result is None or not result.equipment:
            problems.append(f"{label}: the result must be an equipment item")
        if not recipe.ingredients:
            problems.append(f"{label}: needs at least one ingredient")
        for ingredient_id, count in recipe.ingredients.items():
            ingredient = world.items.get(ingredient_id)
            if count <= 0:
                problems.append(f"{label}: amounts must be > 0")
            if ingredient is None or not ingredient.material:
                problems.append(f"{label}: '{ingredient_id}' must be a material")
            elif ingredient_id not in gatherable:
                problems.append(
                    f"{label}: '{ingredient_id}' cannot be gathered anywhere"
                )
    return problems


def _progression_problems(progression: Progression) -> list[str]:
    problems: list[str] = []
    thresholds = progression.xp_to_level
    if any(xp <= 0 for xp in thresholds) or any(
        later <= earlier
        for earlier, later in zip(thresholds, thresholds[1:], strict=False)
    ):
        problems.append("progression: xp_to_level must be positive and increasing")
    if min(progression.max_hp, progression.attack, progression.defense) < 0:
        problems.append("progression: level gains must be >= 0")
    return problems


def _exit_problems(world: World, room: Room) -> list[str]:
    problems: list[str] = []
    for direction, target in room.exits.items():
        if direction not in LABELS:
            problems.append(f"{room.id}: unknown direction '{direction}'")
        elif target not in world.rooms:
            problems.append(
                f"{room.id}: exit {direction} points to missing room '{target}'"
            )
        elif direction not in room.one_way:
            back = world.rooms[target].exits.get(OPPOSITE[direction])
            if back != room.id:
                problems.append(
                    f"{room.id}: exit {direction} to '{target}' is not reciprocal"
                )
    return problems


def _content_problems(world: World, room: Room, placed: dict[str, str]) -> list[str]:
    """Items, locks, shop, resource nodes, monsters and safety of one room.

    `placed` maps item id -> room id and is updated as items are found.
    """
    problems: list[str] = []
    for item_id in room.items:
        if item_id not in world.items:
            problems.append(f"{room.id}: unknown item '{item_id}'")
        elif item_id in placed and not world.items[item_id].stackable:
            problems.append(
                f"item '{item_id}' is placed in both '{placed[item_id]}' "
                f"and '{room.id}'"
            )
        else:
            placed[item_id] = room.id
    for item_id in room.sells:
        if item_id not in world.items:
            problems.append(f"{room.id}: sells unknown item '{item_id}'")
        elif world.items[item_id].price <= 0:
            problems.append(f"{room.id}: item '{item_id}' is sold but has no price")
    for kind, node in room.gather.items():
        if kind not in GATHER_KINDS:
            problems.append(f"{room.id}: unknown gather kind '{kind}'")
        material = world.items.get(node.item)
        if material is None or not material.material:
            problems.append(f"{room.id}: '{kind}' must give a material item")
        if node.amount <= 0 or node.uses <= 0:
            problems.append(f"{room.id}: '{kind}' amount and uses must be > 0")
    for direction, key_item in room.locks.items():
        if direction not in room.exits:
            problems.append(f"{room.id}: lock on '{direction}' but there is no exit")
        if key_item not in world.items:
            problems.append(f"{room.id}: lock needs unknown item '{key_item}'")
    if room.monster is not None:
        if room.monster not in world.monsters:
            problems.append(f"{room.id}: unknown monster '{room.monster}'")
        if room.safe:
            problems.append(f"{room.id}: a safe room cannot have a monster")
        if room.id == world.start:
            problems.append(f"{room.id}: the start room cannot have a monster")
    return problems


def _reachable(world: World) -> set[str]:
    seen = {world.start}
    queue = deque([world.start])
    while queue:
        room = world.rooms[queue.popleft()]
        for target in room.exits.values():
            if target in world.rooms and target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def load_world(path: Path = DEFAULT_WORLD_PATH) -> World:
    """Read, parse and validate the world file. Raises WorldError on any problem."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorldError(f"cannot read world file {path}: {error}") from error
    world = parse_world(data)
    problems = validate(world)
    if problems:
        raise WorldError("\n".join(problems))
    return world
