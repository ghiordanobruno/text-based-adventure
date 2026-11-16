"""Save and load named characters as JSON files (one file per character)."""

import json
import re
import unicodedata
from itertools import chain
from pathlib import Path

from adventure.state import GameState, SaveError
from adventure.world import World, gather_id, lock_id

DEFAULT_SAVES_DIR = Path(__file__).resolve().parents[2] / "saves"


def slugify(name: str) -> str:
    """Turn a character name into a safe file-name part. Raises SaveError if empty."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:40]
    if not slug:
        raise SaveError("nome inválido: use letras ou números")
    return slug


def save_path(name: str, saves_dir: Path = DEFAULT_SAVES_DIR) -> Path:
    # The "character-" prefix avoids Windows reserved names such as "con" or "nul".
    return saves_dir / f"character-{slugify(name)}.json"


def save_game(state: GameState, saves_dir: Path = DEFAULT_SAVES_DIR) -> Path:
    """Write the state to its character file and return the path."""
    path = save_path(state.player_name, saves_dir)
    saves_dir.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file first so a crash never leaves a half-written save.
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp.replace(path)
    return path


def load_game(
    name: str, world: World, saves_dir: Path = DEFAULT_SAVES_DIR
) -> GameState | None:
    """Load a character, or return None if it has no save yet.

    Raises SaveError if the file is unreadable, corrupt or inconsistent with the
    world (unknown room, item, door, monster or resource node; a unique item in
    two places; wrong equipment slot; life, gold, xp, level or uses out of range).
    """
    path = save_path(name, saves_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SaveError("não foi possível ler o arquivo de save") from error
    state = GameState.from_dict(data)
    _check_against_world(state, world)
    return state


def _check_against_world(state: GameState, world: World) -> None:
    _check_items(state, world)
    if state.current_room not in world.rooms:
        raise SaveError(f"sala desconhecida no save: '{state.current_room}'")
    if not 0 < state.hp <= state.max_hp:
        raise SaveError("vida inválida no save")
    if state.gold < 0 or state.xp < 0:
        raise SaveError("ouro ou experiência inválidos no save")
    if not 1 <= state.level <= len(world.progression.xp_to_level) + 1:
        raise SaveError("nível inválido no save")
    known_locks = {
        lock_id(room.id, direction)
        for room in world.rooms.values()
        for direction in room.locks
    }
    for lock in state.unlocked:
        if lock not in known_locks:
            raise SaveError(f"porta desconhecida no save: '{lock}'")
    for room_id in state.defeated:
        room = world.rooms.get(room_id)
        if room is None or room.monster is None:
            raise SaveError(f"monstro desconhecido no save: '{room_id}'")
    uses = {
        gather_id(room.id, kind): node.uses
        for room in world.rooms.values()
        for kind, node in room.gather.items()
    }
    for node_id, spent in state.gathered.items():
        if node_id not in uses or not 0 <= spent <= uses[node_id]:
            raise SaveError(f"ponto de coleta inválido no save: '{node_id}'")


def _check_items(state: GameState, world: World) -> None:
    unknown_rooms = sorted(set(state.room_items) - set(world.rooms))
    if unknown_rooms:
        raise SaveError(f"sala desconhecida no save: '{unknown_rooms[0]}'")
    located = [
        *state.inventory,
        *chain.from_iterable(state.room_items.values()),
        *state.equipped.values(),
    ]
    unknown_items = sorted(set(located) - set(world.items))
    if unknown_items:
        raise SaveError(f"item desconhecido no save: '{unknown_items[0]}'")
    # Stackables (potions, materials) can be carried many times; every other item is
    # a unique object that exists exactly once.
    unique = [item for item in located if not world.items[item].stackable]
    duplicates = sorted({item for item in unique if unique.count(item) > 1})
    if duplicates:
        raise SaveError(f"item repetido no save: '{duplicates[0]}'")
    for slot, item_id in state.equipped.items():
        if world.items[item_id].slot != slot:
            raise SaveError(f"equipamento no lugar errado no save: '{item_id}'")
