"""Equipment: three slots whose items add to the character's base attack and
defense. Pure: state in, numbers or text out.
"""

from adventure.state import GameState
from adventure.world import Item, World

SLOT_LABELS = {"weapon": "Arma", "shield": "Escudo", "armor": "Armadura"}


def bonus_text(item: Item) -> str:
    """'+5 ataque', '+1 defesa' or both, e.g. for lists and messages."""
    parts = []
    if item.attack:
        parts.append(f"+{item.attack} ataque")
    if item.defense:
        parts.append(f"+{item.defense} defesa")
    return ", ".join(parts)


def equipment_bonus(state: GameState, world: World) -> tuple[int, int]:
    """(attack, defense) added by everything the character wears."""
    worn = [world.items[item_id] for item_id in state.equipped.values()]
    return sum(i.attack for i in worn), sum(i.defense for i in worn)


def total_attack(state: GameState, world: World) -> int:
    return state.attack + equipment_bonus(state, world)[0]


def total_defense(state: GameState, world: World) -> int:
    return state.defense + equipment_bonus(state, world)[1]


def is_upgrade(state: GameState, world: World, item_id: str) -> bool:
    """Whether the item beats what is worn in its slot (an empty slot: always)."""
    item = world.items[item_id]
    worn_id = state.equipped.get(item.slot or "")
    if worn_id is None:
        return True
    worn = world.items[worn_id]
    return item.attack + item.defense > worn.attack + worn.defense


def equip(state: GameState, world: World, item_id: str) -> str:
    """Wear an item from the inventory; what it replaces goes back to the inventory."""
    item = world.items[item_id]
    assert item.slot is not None, "only equipment items can be worn"
    state.inventory.remove(item_id)
    previous = state.equipped.get(item.slot)
    state.equipped[item.slot] = item_id
    text = f"Você equipou {item.name} ({SLOT_LABELS[item.slot]}: {bonus_text(item)})."
    if previous is not None:
        state.inventory.append(previous)
        text += f" {world.items[previous].name} voltou para o inventário."
    return text
