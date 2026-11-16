"""Small helpers shared by the tests."""

from collections.abc import Sequence

from adventure.engine import Game, execute
from adventure.parser import parse
from adventure.state import GameState


class ScriptedRng:
    """Stand-in for random.Random with predictable rolls.

    `random()` returns the given rolls in order, then repeats the last one.
    `randint(a, b)` always returns 0 clamped into [a, b], so there is no damage
    variance. With the default roll 0.0 every strike hits and every flee works;
    a roll of 0.99 is a miss / a failed flee.
    """

    def __init__(self, *rolls: float) -> None:
        self._rolls: Sequence[float] = rolls or (0.0,)
        self._index = 0

    def random(self) -> float:
        roll = self._rolls[min(self._index, len(self._rolls) - 1)]
        self._index += 1
        return roll

    def randint(self, a: int, b: int) -> int:
        return min(max(0, a), b)


def do(state: GameState, game: Game, line: str) -> str:
    """Parse a line the way the player would type it and run it."""
    command = parse(line)
    assert command is not None, f"blank line: {line!r}"
    return execute(state, command, game)
