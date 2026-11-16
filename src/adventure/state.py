"""Game state: everything that changes while the game is played."""

from dataclasses import dataclass, field
from typing import Any, Self

from adventure.world import World

SAVE_VERSION = 4


class SaveError(ValueError):
    """A save is unreadable, corrupt or does not match the world.

    The message is shown to the player, so it is in pt-BR.
    """


@dataclass
class Combat:
    """A fight in progress. Never saved: saving is not allowed during a fight."""

    monster_id: str
    monster_hp: int


@dataclass
class GameState:
    """Mutable state of one play session.

    `attack` and `defense` are the character's *base* stats (they grow with
    levels); equipment bonuses are added on top (see `equipment`). The stat
    defaults are placeholders: `GameState.new` takes the real starting values
    from the world data.
    """

    current_room: str
    player_name: str = ""
    inventory: list[str] = field(default_factory=list)  # stackables may repeat
    room_items: dict[str, list[str]] = field(default_factory=dict)  # room -> item ids
    equipped: dict[str, str] = field(default_factory=dict)  # slot -> item id
    max_hp: int = 100
    hp: int = 100
    attack: int = 10
    defense: int = 0
    gold: int = 0
    xp: int = 0
    level: int = 1
    unlocked: list[str] = field(default_factory=list)  # lock ids (see world.lock_id)
    defeated: list[str] = field(default_factory=list)  # rooms whose monster is dead
    gathered: dict[str, int] = field(default_factory=dict)  # node id -> uses spent
    # Session-only (not saved):
    combat: Combat | None = None
    came_from: str | None = None  # where to run to when fleeing
    running: bool = True

    @classmethod
    def new(cls, world: World, player_name: str) -> Self:
        """A fresh game: start room, starting gear, items placed by the world."""
        return cls(
            current_room=world.start,
            player_name=player_name,
            room_items={
                room_id: list(room.items)
                for room_id, room in world.rooms.items()
                if room.items
            },
            equipped=dict(world.player.equipment),
            max_hp=world.player.max_hp,
            hp=world.player.max_hp,
            attack=world.player.attack,
            defense=world.player.defense,
            gold=world.player.gold,
        )

    def to_dict(self) -> dict[str, Any]:
        """What gets saved. Session-only fields are left out."""
        return {
            "version": SAVE_VERSION,
            "player_name": self.player_name,
            "current_room": self.current_room,
            "inventory": list(self.inventory),
            "room_items": {
                room: list(items) for room, items in self.room_items.items()
            },
            "equipped": dict(self.equipped),
            "max_hp": self.max_hp,
            "hp": self.hp,
            "attack": self.attack,
            "defense": self.defense,
            "gold": self.gold,
            "xp": self.xp,
            "level": self.level,
            "unlocked": list(self.unlocked),
            "defeated": list(self.defeated),
            "gathered": dict(self.gathered),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild a state from saved data. Raises SaveError if it is malformed.

        Does not check the data against a world; see `saves.load_game`.
        """
        try:
            version = data["version"]
        except (KeyError, TypeError) as error:
            raise SaveError("arquivo de save corrompido") from error
        if version != SAVE_VERSION:
            raise SaveError("versão de save não suportada")
        try:
            return cls(
                current_room=str(data["current_room"]),
                player_name=str(data["player_name"]),
                inventory=[str(item) for item in data["inventory"]],
                room_items={
                    str(room): [str(item) for item in items]
                    for room, items in data["room_items"].items()
                },
                equipped={str(s): str(i) for s, i in data["equipped"].items()},
                max_hp=int(data["max_hp"]),
                hp=int(data["hp"]),
                attack=int(data["attack"]),
                defense=int(data["defense"]),
                gold=int(data["gold"]),
                xp=int(data["xp"]),
                level=int(data["level"]),
                unlocked=[str(lock) for lock in data["unlocked"]],
                defeated=[str(room) for room in data["defeated"]],
                gathered={str(node): int(n) for node, n in data["gathered"].items()},
            )
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            raise SaveError("arquivo de save corrompido") from error
