"""Game engine: applies a Command to the GameState. No print/input.

The only disk access is the `salvar` command, which goes through `saves`.
"""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

from adventure.combat import monster_turn, player_attack, try_flee
from adventure.crafting import (
    GATHER_VERBS,
    craft,
    describe_recipes,
    gather,
    uses_left,
    uses_text,
)
from adventure.directions import LABELS, ORDER
from adventure.equipment import (
    SLOT_LABELS,
    bonus_text,
    equip,
    equipment_bonus,
    total_attack,
    total_defense,
)
from adventure.parser import Command
from adventure.progression import xp_to_next_level
from adventure.saves import DEFAULT_SAVES_DIR, save_game
from adventure.state import Combat, GameState, SaveError
from adventure.world import SLOTS, World, lock_id

HELP_TEXT = (
    "Comandos disponíveis:\n"
    "  olhar              - descreve o local atual\n"
    "  ir <direção>       - anda (norte, sul, leste, oeste ou n, s, l, o)\n"
    "  pegar <item>       - pega um item do local\n"
    "  largar <item>      - larga um item no local\n"
    "  usar <item>        - usa uma chave numa porta ou um item de cura\n"
    "  inventario         - mostra o que você carrega\n"
    "  perfil             - mostra nível, vida, atributos, equipamento e ouro\n"
    "  cortar [vezes]     - corta madeira (onde houver árvores)\n"
    "  minerar [vezes]    - minera minério (onde houver veios)\n"
    "  receitas           - lista o que dá para fabricar\n"
    "  fabricar <item>    - fabrica um equipamento\n"
    "  equipar <item>     - veste um equipamento do inventário\n"
    "  loja               - lista o que está à venda (só em lojas)\n"
    "  comprar <item> [n] - compra um item da loja\n"
    "  atacar             - ataca o inimigo (só em combate)\n"
    "  fugir              - tenta fugir do combate\n"
    "  descansar          - recupera a vida (só em locais seguros)\n"
    "  salvar             - salva o personagem\n"
    "  ajuda              - mostra esta lista\n"
    "  sair               - encerra o jogo (sem salvar)"
)

# The only commands that work while a fight is on.
COMBAT_VERBS = frozenset(
    {"attack", "flee", "use", "help", "quit", "inventory", "profile", "look"}
)

MAX_QUANTITY = 99


@dataclass(frozen=True)
class Game:
    """Everything the engine reads but never changes during play."""

    world: World
    saves_dir: Path = DEFAULT_SAVES_DIR
    rng: Random = field(default_factory=Random)


def describe_room(state: GameState, world: World) -> str:
    """Name, description, items, resources, shop, danger and exits of the room."""
    room = world.rooms[state.current_room]
    lines = [room.name, room.description]
    here = state.room_items.get(state.current_room, [])
    if here:
        lines.append("Você vê: " + ", ".join(world.items[i].name for i in here))
    for kind, node in room.gather.items():
        left = uses_left(state, room, kind)
        if left > 0:
            verb = GATHER_VERBS[kind][0]
            name = world.items[node.item].name
            lines.append(f"Dá para {verb}: {name} ({uses_text(left)}).")
    if room.sells:
        lines.append("Loja: digite 'loja' para ver o que está à venda.")
    if state.combat is not None:
        monster = world.monsters[state.combat.monster_id]
        lines.append(
            f"Perigo: {monster.name} ({state.combat.monster_hp}/{monster.max_hp} "
            "de vida)"
        )
    exits = ", ".join(LABELS[d] for d in ORDER if d in room.exits) or "nenhuma"
    lines.append(f"Saídas: {exits}")
    return "\n".join(lines)


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore")
    return ascii_text.decode().lower().strip()


def _find_items(noun: str, item_ids: list[str], world: World) -> list[str]:
    """Distinct items whose name matches what the player typed (exact wins)."""
    wanted = _normalize(noun)
    distinct = list(dict.fromkeys(item_ids))  # a stack of potions is one match
    names = {i: _normalize(world.items[i].name) for i in distinct}
    exact = [i for i in distinct if names[i] == wanted]
    return exact or [i for i in distinct if wanted in names[i]]


def _which_one(matches: list[str], world: World) -> str:
    return "Qual deles? " + ", ".join(world.items[i].name for i in matches)


def _split_quantity(noun: str) -> tuple[str, int | None]:
    """'poção de vida 2' -> ('poção de vida', 2); no number means 1.

    Returns a quantity of None when the number is not a valid amount.
    """
    words = noun.split()
    if words and words[-1].isdigit():
        quantity = int(words[-1])
        valid = 1 <= quantity <= MAX_QUANTITY
        return " ".join(words[:-1]), quantity if valid else None
    return noun, 1


def _bad_quantity() -> str:
    return f"Quantidade inválida (de 1 a {MAX_QUANTITY})."


def _help(state: GameState, command: Command, game: Game) -> str:
    return HELP_TEXT


def _quit(state: GameState, command: Command, game: Game) -> str:
    state.running = False
    return "Até a próxima aventura!"


def _look(state: GameState, command: Command, game: Game) -> str:
    return describe_room(state, game.world)


def _go(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Ir para onde? Use 'ir <direção>' (norte, sul, leste, oeste)."
    if command.noun not in LABELS:
        return f"Não conheço a direção '{command.noun}'."
    world = game.world
    room = world.rooms[state.current_room]
    target = room.exits.get(command.noun)
    if target is None:
        return f"Não há caminho para o {LABELS[command.noun]}."
    if command.noun in room.locks and lock_id(room.id, command.noun) not in (
        state.unlocked
    ):
        return f"A passagem para o {LABELS[command.noun]} está trancada."
    state.came_from = state.current_room
    state.current_room = target
    monster_id = world.rooms[target].monster
    if monster_id is None or target in state.defeated:
        return describe_room(state, world)
    monster = world.monsters[monster_id]
    state.combat = Combat(monster.id, monster.max_hp)
    return (
        f"{describe_room(state, world)}\n\n"
        f"{monster.name} aparece! Use 'atacar' ou 'fugir'."
    )


def _take(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Pegar o quê?"
    here = state.room_items.get(state.current_room, [])
    matches = _find_items(command.noun, here, game.world)
    if not matches:
        return f"Não há '{command.noun}' aqui."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    here.remove(matches[0])
    state.inventory.append(matches[0])
    return f"Você pegou: {game.world.items[matches[0]].name}."


def _drop(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Largar o quê?"
    matches = _find_items(command.noun, state.inventory, game.world)
    if not matches:
        return f"Você não tem '{command.noun}'."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    state.inventory.remove(matches[0])
    state.room_items.setdefault(state.current_room, []).append(matches[0])
    return f"Você largou: {game.world.items[matches[0]].name}."


def _use(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Usar o quê?"
    matches = _find_items(command.noun, state.inventory, game.world)
    if not matches:
        return f"Você não tem '{command.noun}'."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    item_id = matches[0]
    if game.world.items[item_id].consumable:
        return _use_consumable(state, item_id, game)
    return _use_key(state, item_id, game)


def _use_consumable(state: GameState, item_id: str, game: Game) -> str:
    """Heal with an item. In a fight this takes the turn: the monster answers."""
    item = game.world.items[item_id]
    if state.hp >= state.max_hp:
        return "Sua vida já está cheia."
    gained = min(state.max_hp - state.hp, state.max_hp * item.heal // 100)
    state.hp += gained
    state.inventory.remove(item_id)
    lines = [
        f"Você usa {item.name} e recupera {gained} de vida. "
        f"Vida: {state.hp}/{state.max_hp}."
    ]
    if state.combat is not None:
        monster = game.world.monsters[state.combat.monster_id]
        lines += monster_turn(state, game.world, monster, game.rng)
    return "\n".join(lines)


def _use_key(state: GameState, item_id: str, game: Game) -> str:
    name = game.world.items[item_id].name
    room = game.world.rooms[state.current_room]
    opened = [
        d
        for d in ORDER
        if room.locks.get(d) == item_id and lock_id(room.id, d) not in state.unlocked
    ]
    if not opened:
        return f"Não dá para usar {name} aqui."
    state.unlocked.extend(lock_id(room.id, d) for d in opened)
    where = ", ".join(f"para o {LABELS[d]}" for d in opened)
    return f"Você usa {name}: a passagem {where} se abre."


def _inventory(state: GameState, command: Command, game: Game) -> str:
    if not state.inventory:
        return "Você não carrega nada."
    lines = []
    for item_id in dict.fromkeys(state.inventory):
        count = state.inventory.count(item_id)
        suffix = f" x{count}" if count > 1 else ""
        lines.append(f"  - {game.world.items[item_id].name}{suffix}")
    return "Você carrega:\n" + "\n".join(lines)


def _stat_line(label: str, total: int, bonus: int) -> str:
    """'Ataque: 15 (10+5)' when equipment helps, plain 'Ataque: 10' otherwise."""
    return (
        f"{label}: {total} ({total - bonus}+{bonus})" if bonus else f"{label}: {total}"
    )


def _profile(state: GameState, command: Command, game: Game) -> str:
    world = game.world
    needed = xp_to_next_level(state, world)
    xp = f"{state.xp}/{needed}" if needed is not None else f"{state.xp} (nível máximo)"
    bonus_attack, bonus_defense = equipment_bonus(state, world)
    gear = []
    for slot in SLOTS:
        item_id = state.equipped.get(slot)
        if item_id is None:
            gear.append(f"  {SLOT_LABELS[slot]}: nenhum")
        else:
            item = world.items[item_id]
            gear.append(f"  {SLOT_LABELS[slot]}: {item.name} ({bonus_text(item)})")
    return (
        f"{state.player_name} - nível {state.level}\n"
        f"Experiência: {xp}\n"
        f"Vida: {state.hp}/{state.max_hp}   "
        f"{_stat_line('Ataque', total_attack(state, world), bonus_attack)}   "
        f"{_stat_line('Defesa', total_defense(state, world), bonus_defense)}\n"
        "Equipamento:\n" + "\n".join(gear) + f"\nOuro: {state.gold}"
    )


def _gatherer(kind: str) -> Callable[[GameState, Command, Game], str]:
    """Handler for `cortar` / `minerar`: an optional number says how many times."""

    def handler(state: GameState, command: Command, game: Game) -> str:
        _, times = _split_quantity(command.noun)
        if times is None:
            return _bad_quantity()
        return gather(state, game.world, kind, times)

    return handler


def _recipes(state: GameState, command: Command, game: Game) -> str:
    return describe_recipes(state, game.world)


def _craft(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Fabricar o quê? Use 'receitas' para ver as opções."
    matches = _find_items(command.noun, list(game.world.recipes), game.world)
    if not matches:
        return f"Não conheço a receita '{command.noun}'. Use 'receitas'."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    return craft(state, game.world, matches[0])


def _equip(state: GameState, command: Command, game: Game) -> str:
    if not command.noun:
        return "Equipar o quê?"
    matches = _find_items(command.noun, state.inventory, game.world)
    if not matches:
        return f"Você não tem '{command.noun}'."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    item = game.world.items[matches[0]]
    if not item.equipment:
        return f"{item.name} não pode ser equipado."
    return equip(state, game.world, item.id)


def _shop(state: GameState, command: Command, game: Game) -> str:
    room = game.world.rooms[state.current_room]
    if not room.sells:
        return "Não há nada à venda aqui."
    lines = [f"À venda (seu ouro: {state.gold}):"]
    for item_id in room.sells:
        item = game.world.items[item_id]
        lines.append(f"  {item.name} - {item.price} de ouro")
    lines.append("Use 'comprar <item> [quantidade]'.")
    return "\n".join(lines)


def _buy(state: GameState, command: Command, game: Game) -> str:
    room = game.world.rooms[state.current_room]
    if not room.sells:
        return "Não há nada à venda aqui."
    name, quantity = _split_quantity(command.noun)
    if not name:
        return "Comprar o quê? Use 'comprar <item> [quantidade]'."
    if quantity is None:
        return _bad_quantity()
    matches = _find_items(name, list(room.sells), game.world)
    if not matches:
        return f"Não vendemos '{name}' aqui."
    if len(matches) > 1:
        return _which_one(matches, game.world)
    item = game.world.items[matches[0]]
    total = item.price * quantity
    if state.gold < total:
        return f"Você precisa de {total} de ouro, mas só tem {state.gold}."
    state.gold -= total
    state.inventory.extend([item.id] * quantity)
    return (
        f"Você comprou {quantity}x {item.name} por {total} de ouro. "
        f"Ouro restante: {state.gold}."
    )


def _attack(state: GameState, command: Command, game: Game) -> str:
    if state.combat is None:
        return "Não há nada para atacar aqui."
    return player_attack(state, game.world, game.rng)


def _flee(state: GameState, command: Command, game: Game) -> str:
    if state.combat is None:
        return "Você não está lutando."
    if state.came_from is None:
        return "Não há para onde fugir."
    fled, text = try_flee(state, game.world, game.rng)
    if not fled:
        return text
    state.current_room = state.came_from
    return f"{text}\n\n{describe_room(state, game.world)}"


def _rest(state: GameState, command: Command, game: Game) -> str:
    if not game.world.rooms[state.current_room].safe:
        return "Aqui não é seguro para descansar."
    state.hp = state.max_hp
    return f"Você descansa e recupera as forças. Vida: {state.hp}/{state.max_hp}."


def _save(state: GameState, command: Command, game: Game) -> str:
    try:
        save_game(state, game.saves_dir)
    except (SaveError, OSError) as error:
        return f"Não foi possível salvar: {error}"
    return f"Jogo salvo ({state.player_name})."


HANDLERS: dict[str, Callable[[GameState, Command, Game], str]] = {
    "help": _help,
    "quit": _quit,
    "look": _look,
    "go": _go,
    "take": _take,
    "drop": _drop,
    "use": _use,
    "inventory": _inventory,
    "profile": _profile,
    "chop": _gatherer("chop"),
    "mine": _gatherer("mine"),
    "recipes": _recipes,
    "craft": _craft,
    "equip": _equip,
    "shop": _shop,
    "buy": _buy,
    "attack": _attack,
    "flee": _flee,
    "rest": _rest,
    "save": _save,
}


def execute(state: GameState, command: Command, game: Game) -> str:
    """Run a command against the state and return the text to show the player."""
    if state.combat is not None and command.verb not in COMBAT_VERBS:
        return "Você está em combate! Use 'atacar' ou 'fugir'."
    handler = HANDLERS.get(command.verb)
    if handler is None:
        return f"Não entendi '{command.verb}'. Digite 'ajuda' para ver os comandos."
    return handler(state, command, game)
