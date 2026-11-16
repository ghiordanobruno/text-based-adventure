"""Rewards and levelling. Pure: state in, text out.

Replaces the old bot's `bisect` over an experience table with a plain loop over
the thresholds in the world data.
"""

from adventure.state import GameState
from adventure.world import Monster, World


def xp_to_next_level(state: GameState, world: World) -> int | None:
    """Total xp needed for the next level, or None at the maximum level."""
    thresholds = world.progression.xp_to_level
    if state.level > len(thresholds):
        return None
    return thresholds[state.level - 1]


def award(state: GameState, world: World, monster: Monster) -> list[str]:
    """Give a defeated monster's gold and xp; level up as many times as earned.

    Each level adds the world's per-level gains and restores full life.
    """
    state.gold += monster.gold
    state.xp += monster.xp
    lines = [f"Você ganhou {monster.xp} de experiência e {monster.gold} de ouro."]
    growth = world.progression
    while (needed := xp_to_next_level(state, world)) is not None and state.xp >= needed:
        state.level += 1
        state.max_hp += growth.max_hp
        state.attack += growth.attack
        state.defense += growth.defense
        state.hp = state.max_hp
        lines.append(
            f"PARABÉNS! Você chegou ao nível {state.level}! "
            f"Vida {state.max_hp}, ataque {state.attack}, defesa {state.defense}. "
            "Sua vida foi restaurada."
        )
    return lines
