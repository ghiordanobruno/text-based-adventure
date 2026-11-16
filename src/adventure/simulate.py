"""Balance simulator: replays the walkthrough many times with real randomness.

    python -m adventure.simulate [games [heal_below ...]] [--sem-equipamento]

`heal_below` is the fraction of max life under which the simulated player drinks
a healing item (0 means never). `--sem-equipamento` skips the walkthrough's
`@gear` lines (gathering, crafting, equipping). Use it after changing numbers in
`data/world.json` to see how hard the game really is. A developer tool: like
`__main__`, it is allowed to print.
"""

import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from random import Random

from adventure.engine import Game, execute
from adventure.parser import parse
from adventure.state import GameState
from adventure.world import World, WorldError, load_world

DEFAULT_WALKTHROUGH_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "walkthrough.txt"
)
FIGHT = "FIGHT"
GEAR_PREFIX = "@gear "
NO_GEAR_FLAG = "--sem-equipamento"
DEFAULT_GAMES = 500
DEFAULT_HEAL_POLICIES = (0.0, 0.35, 0.5)
USAGE = (
    "Uso: python -m adventure.simulate [partidas [limite_de_cura ...]] "
    f"[{NO_GEAR_FLAG}]"
)


@dataclass
class Outcome:
    """How one simulated game ended."""

    state: GameState
    won: bool
    killed_by: str | None  # name of the monster that killed the player, if any
    outputs: list[str]  # text of every non-FIGHT command


@dataclass
class Report:
    """Results of many simulated games."""

    games: int
    wins: int
    deaths: Counter[str]  # monster name -> times it killed the player

    @property
    def win_rate(self) -> float:
        return self.wins / self.games


def load_walkthrough(path: Path = DEFAULT_WALKTHROUGH_PATH) -> list[str]:
    """Commands of a walkthrough file; `#` starts a comment, blank lines are skipped."""
    text = path.read_text(encoding="utf-8")
    lines = (raw.split("#", 1)[0].strip() for raw in text.splitlines())
    return [line for line in lines if line]


def _run(state: GameState, game: Game, line: str) -> str:
    command = parse(line)
    assert command is not None, f"blank command: {line!r}"
    return execute(state, command, game)


def fight(
    state: GameState, game: Game, heal_below: float = 0.35, max_rounds: int = 300
) -> None:
    """Attack until the fight (or the game) ends, like a careful player would.

    Drinks a healing item whenever life drops below `heal_below` of the maximum.
    """
    for _ in range(max_rounds):
        if state.combat is None or not state.running:
            return
        if state.hp < state.max_hp * heal_below:
            heal = next(
                (i for i in state.inventory if game.world.items[i].consumable), None
            )
            if heal is not None:
                _run(state, game, f"usar {game.world.items[heal].name}")
                continue
        _run(state, game, "atacar")
    raise RuntimeError("the fight never ended")


def play(
    game: Game,
    lines: Sequence[str],
    heal_below: float = 0.35,
    gear: bool = True,
) -> Outcome:
    """Play a new character through `lines`; stop early if the game ends.

    With `gear` False the lines marked `@gear` are skipped.
    """
    state = GameState.new(game.world, "Simulador")
    outputs: list[str] = []
    killed_by = None
    for line in lines:
        if not state.running:
            break
        if line.startswith(GEAR_PREFIX):
            if not gear:
                continue
            line = line.removeprefix(GEAR_PREFIX).strip()
        if line == FIGHT:
            if state.combat is None:
                raise ValueError(
                    "FIGHT without an enemy: the walkthrough does not match the world"
                )
            monster = game.world.monsters[state.combat.monster_id].name
            fight(state, game, heal_below)
            if state.hp == 0:
                killed_by = monster
        else:
            outputs.append(_run(state, game, line))
    won = state.hp > 0 and not state.running
    return Outcome(state, won, killed_by, outputs)


def simulate(
    world: World,
    lines: Sequence[str],
    games: int,
    heal_below: float = 0.35,
    seed: int = 0,
    gear: bool = True,
) -> Report:
    """Play `games` games, each with its own seed (`seed`, `seed + 1`, ...)."""
    wins = 0
    deaths: Counter[str] = Counter()
    for n in range(games):
        outcome = play(Game(world, rng=Random(seed + n)), lines, heal_below, gear)
        wins += outcome.won
        if outcome.killed_by is not None:
            deaths[outcome.killed_by] += 1
    return Report(games, wins, deaths)


def format_report(heal_below: float, report: Report, gear: bool = True) -> str:
    """One policy's results as text for the player or developer."""
    if heal_below == 0:
        policy = "Nunca bebe poção"
    else:
        policy = f"Bebe poção abaixo de {heal_below:.0%} da vida"
    if not gear:
        policy += ", sem equipamento"
    text = f"{policy}: {report.win_rate:.1%} de vitórias ({report.wins}/{report.games})"
    if report.deaths:
        killers = ", ".join(f"{name} {n}" for name, n in report.deaths.most_common())
        text += f"\n  derrotas para: {killers}"
    return text


def _parse_args(args: Sequence[str]) -> tuple[int, list[tuple[float, bool]]] | None:
    """(games, [(heal_below, gear), ...]) from the command line, or None if invalid."""
    flags = [arg for arg in args if arg.startswith("--")]
    numbers = [arg for arg in args if not arg.startswith("--")]
    if any(flag != NO_GEAR_FLAG for flag in flags):
        return None
    try:
        games = int(numbers[0]) if numbers else DEFAULT_GAMES
        heals = [float(arg) for arg in numbers[1:]]
    except ValueError:
        return None
    if games < 1 or not all(0 <= heal <= 1 for heal in heals):
        return None
    if heals or flags:
        gear = NO_GEAR_FLAG not in flags
        return games, [(heal, gear) for heal in heals or DEFAULT_HEAL_POLICIES]
    # Default: every healing policy with equipment, plus the best one without it.
    runs = [(heal, True) for heal in DEFAULT_HEAL_POLICIES]
    return games, [*runs, (0.35, False)]


def main(argv: Sequence[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    parsed = _parse_args(args)
    if parsed is None:
        print(USAGE)
        return 2
    games, runs = parsed
    try:
        world = load_world()
        lines = load_walkthrough()
    except (WorldError, OSError) as error:
        print(f"Erro ao carregar os dados:\n{error}")
        return 1
    for heal_below, gear in runs:
        report = simulate(world, lines, games, heal_below, gear=gear)
        print(format_report(heal_below, report, gear))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
