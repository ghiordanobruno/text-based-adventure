import copy

import pytest

from adventure.engine import Game
from adventure.state import GameState
from adventure.world import World, parse_world
from helpers import ScriptedRng

# Layout:   cellar (rat) -- garden -- hall (safe, shop, start)
#                              |
#                         lair (ogre, final)  <- locked, needs old_key
#
# Progression: 10 xp for level 2, 30 xp for level 3. The rat gives 5 xp (no level
# up); the ogre gives 40 (two levels at once).
# Gathering: the hall has trees (chop wood), the garden has ore (mine copper).
# The player starts with NO equipment, so base stats are the fighting stats.
_SMALL_WORLD = {
    "start": "hall",
    "player": {"max_hp": 30, "attack": 10, "defense": 0, "gold": 20},
    "progression": {
        "xp_to_level": [10, 30],
        "max_hp": 10,
        "attack": 5,
        "defense": 1,
    },
    "endings": {"victory": "VITÓRIA", "defeat": "DERROTA"},
    "items": {
        "old_key": {"name": "Chave Velha"},
        "new_key": {"name": "Chave Nova"},
        "lamp": {"name": "Lanterna"},
        "blue_potion": {"name": "Poção Azul", "heal": 50, "price": 10},
        "red_potion": {"name": "Poção Vermelha", "heal": 100, "price": 30},
        "wood": {"name": "Madeira", "material": True},
        "copper": {"name": "Cobre", "material": True},
        "wood_sword": {"name": "Espada de Madeira", "slot": "weapon", "attack": 5},
        "copper_sword": {"name": "Espada de Cobre", "slot": "weapon", "attack": 10},
        "wood_shield": {"name": "Broquel de Madeira", "slot": "shield", "defense": 5},
        "leather_armor": {"name": "Armadura de Couro", "slot": "armor", "defense": 3},
    },
    "recipes": {
        "wood_sword": {"wood": 3},
        "copper_sword": {"wood": 1, "copper": 2},
        "wood_shield": {"wood": 4},
    },
    "monsters": {
        "rat": {
            "name": "Rato",
            "max_hp": 20,
            "attack": 4,
            "defense": 0,
            "xp": 5,
            "gold": 7,
        },
        "ogre": {
            "name": "Ogro",
            "max_hp": 30,
            "attack": 10,
            "defense": 0,
            "xp": 40,
            "gold": 25,
            "final": True,
        },
    },
    "rooms": {
        "hall": {
            "name": "Salão",
            "description": "Um salão vazio.",
            "exits": {"north": "garden"},
            "items": ["old_key", "new_key", "lamp", "leather_armor"],
            "safe": True,
            "sells": ["blue_potion", "red_potion"],
            "gather": {"chop": {"item": "wood", "amount": 2, "uses": 4}},
        },
        "garden": {
            "name": "Jardim",
            "description": "Um jardim silencioso.",
            "exits": {"south": "hall", "east": "cellar", "north": "lair"},
            "locks": {"north": "old_key"},
            "gather": {"mine": {"item": "copper", "amount": 1, "uses": 3}},
        },
        "cellar": {
            "name": "Porão",
            "description": "Um porão úmido.",
            "exits": {"west": "garden"},
            "monster": "rat",
        },
        "lair": {
            "name": "Covil",
            "description": "O covil do ogro.",
            "exits": {"south": "garden"},
            "monster": "ogre",
        },
        "pit": {
            "name": "Fosso",
            "description": "Sem saída.",
            "exits": {},
        },
    },
}


@pytest.fixture
def small_world_data() -> dict:
    """Raw data of a tiny hand-made world (room 'pit' is unreachable on purpose).

    Returns a fresh copy, so tests can mutate it freely.
    """
    return copy.deepcopy(_SMALL_WORLD)


@pytest.fixture
def world(small_world_data: dict) -> World:
    """The tiny world, independent of data/world.json."""
    return parse_world(small_world_data)


@pytest.fixture
def game(world: World, tmp_path) -> Game:
    """Engine context: saves go to a temp folder, and every roll is a hit."""
    return Game(world, saves_dir=tmp_path / "saves", rng=ScriptedRng(0.0))


@pytest.fixture
def state(world: World) -> GameState:
    return GameState.new(world, "Teste")
