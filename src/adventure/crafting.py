"""Gathering materials and crafting equipment. Pure: state in, text out.

Resource nodes are finite (`uses` per node), like monsters and gold: the old
bot's real-time cooldowns are replaced by what the world holds.
"""

from adventure.equipment import SLOT_LABELS, bonus_text, equip, is_upgrade
from adventure.state import GameState
from adventure.world import Room, World, gather_id

# kind -> (verb the player types, past tense used in messages)
GATHER_VERBS = {"chop": ("cortar", "cortou"), "mine": ("minerar", "minerou")}


def uses_left(state: GameState, room: Room, kind: str) -> int:
    """How many times the room's node of this kind can still be gathered."""
    spent = state.gathered.get(gather_id(room.id, kind), 0)
    return room.gather[kind].uses - spent


def uses_text(left: int) -> str:
    """'resta 1 uso' / 'restam 3 usos'."""
    return "resta 1 uso" if left == 1 else f"restam {left} usos"


def gather(state: GameState, world: World, kind: str, times: int) -> str:
    """Gather from the current room's node, up to `times` uses."""
    infinitive, past = GATHER_VERBS[kind]
    room = world.rooms[state.current_room]
    if kind not in room.gather:
        return f"Não há nada para {infinitive} aqui."
    left = uses_left(state, room, kind)
    if left <= 0:
        return f"Você já {past} tudo o que dava aqui."
    node = room.gather[kind]
    count = min(times, left)
    key = gather_id(room.id, kind)
    state.gathered[key] = state.gathered.get(key, 0) + count
    gained = node.amount * count
    state.inventory.extend([node.item] * gained)
    remaining = left - count
    if remaining == 0:
        tail = "O local está esgotado."
    else:
        tail = f"{uses_text(remaining).capitalize()} aqui."
    return (
        f"Você {past} {count}x e obteve {gained}x {world.items[node.item].name}. {tail}"
    )


def already_exists(state: GameState, item_id: str) -> bool:
    """Unique items exist once: carried, worn or lying anywhere."""
    return (
        item_id in state.inventory
        or item_id in state.equipped.values()
        or any(item_id in items for items in state.room_items.values())
    )


def craft(state: GameState, world: World, result_id: str) -> str:
    """Craft one equipment item; wear it right away if it beats what is worn."""
    item = world.items[result_id]
    recipe = world.recipes[result_id]
    if already_exists(state, result_id):
        return f"{item.name} já foi fabricado."
    missing = [
        f"{world.items[material].name} {state.inventory.count(material)}/{needed}"
        for material, needed in recipe.ingredients.items()
        if state.inventory.count(material) < needed
    ]
    if missing:
        return "Faltam materiais: " + ", ".join(missing) + "."
    for material, needed in recipe.ingredients.items():
        for _ in range(needed):
            state.inventory.remove(material)
    state.inventory.append(result_id)
    text = f"Você fabricou {item.name}!"
    if is_upgrade(state, world, result_id):
        return f"{text}\n{equip(state, world, result_id)}"
    return (
        f"{text} Ele não é melhor que o que você veste; "
        f"use 'equipar {item.name.lower()}' para trocar."
    )


def describe_recipes(state: GameState, world: World) -> str:
    """Every recipe with what it needs and how much of it the player has."""
    if not world.recipes:
        return "Não há receitas."
    lines = ["Receitas (use 'fabricar <item>'):"]
    for result_id, recipe in world.recipes.items():
        item = world.items[result_id]
        needs = ", ".join(
            f"{world.items[material].name} {needed} "
            f"(você tem {state.inventory.count(material)})"
            for material, needed in recipe.ingredients.items()
        )
        done = " - já fabricado" if already_exists(state, result_id) else ""
        slot = SLOT_LABELS[item.slot or ""].lower()
        lines.append(f"  {item.name} ({slot}, {bonus_text(item)}): {needs}{done}")
    return "\n".join(lines)
