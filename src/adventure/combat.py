"""Turn-based combat rules. State and rng in, text out; no I/O.

A fight is `GameState.combat`. Each round the player acts first; a monster that
is still alive answers. Dying ends the game, and so does beating the final
monster. Any other victory pays gold and experience (see `progression`).
"""

from random import Random

from adventure.equipment import total_attack, total_defense
from adventure.progression import award
from adventure.state import GameState
from adventure.world import Monster, World

HIT_CHANCE = 0.8
FLEE_CHANCE = 0.6


def roll_damage(attack: int, defense: int, rng: Random) -> int:
    """Damage of one strike: 0 on a miss, otherwise at least 1.

    Defense scales damage down as attack * 100 / (100 + defense), so armor
    always helps but never makes a target immune.
    """
    if rng.random() >= HIT_CHANCE:
        return 0
    raw = attack + rng.randint(-2, 2)
    return max(1, raw * 100 // (100 + defense))


def player_attack(state: GameState, world: World, rng: Random) -> str:
    """One round: the player strikes, then the monster answers if it survives."""
    combat = state.combat
    assert combat is not None, "player_attack needs a fight in progress"
    monster = world.monsters[combat.monster_id]
    dealt = roll_damage(total_attack(state, world), monster.defense, rng)
    combat.monster_hp = max(0, combat.monster_hp - dealt)
    if dealt:
        lines = [
            f"Você acertou {monster.name} e causou {dealt} de dano "
            f"({combat.monster_hp}/{monster.max_hp} de vida)."
        ]
    else:
        lines = [f"Você errou o golpe em {monster.name}."]
    if combat.monster_hp == 0:
        lines += _victory(state, world, monster)
    else:
        lines += monster_turn(state, world, monster, rng)
    return "\n".join(lines)


def try_flee(state: GameState, world: World, rng: Random) -> tuple[bool, str]:
    """Try to run away. Returns (fled, text).

    On a failed attempt the monster gets a free strike. Moving the player to
    the previous room is the engine's job.
    """
    combat = state.combat
    assert combat is not None, "try_flee needs a fight in progress"
    monster = world.monsters[combat.monster_id]
    if rng.random() < FLEE_CHANCE:
        state.combat = None
        return True, f"Você fugiu de {monster.name}!"
    lines = [f"Você tenta fugir, mas {monster.name} te alcança."]
    lines += monster_turn(state, world, monster, rng)
    return False, "\n".join(lines)


def monster_turn(
    state: GameState, world: World, monster: Monster, rng: Random
) -> list[str]:
    """The monster strikes the player. Dying ends the game."""
    dealt = roll_damage(monster.attack, total_defense(state, world), rng)
    state.hp = max(0, state.hp - dealt)
    if dealt:
        lines = [f"{monster.name} te acertou e causou {dealt} de dano."]
    else:
        lines = [f"{monster.name} errou o ataque."]
    if state.hp == 0:
        state.combat = None
        state.running = False
        lines.append(world.endings["defeat"])
    else:
        lines.append(f"Sua vida: {state.hp}/{state.max_hp}.")
    return lines


def _victory(state: GameState, world: World, monster: Monster) -> list[str]:
    state.defeated.append(state.current_room)
    state.combat = None
    lines = [f"Você derrotou {monster.name}!"]
    lines += award(state, world, monster)
    if monster.final:
        state.running = False
        lines.append(world.endings["victory"])
    else:
        lines.append(f"Sua vida: {state.hp}/{state.max_hp}.")
    return lines
