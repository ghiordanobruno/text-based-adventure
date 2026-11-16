"""Console entry point: the only module that talks to the terminal."""

from adventure.engine import Game, describe_room, execute
from adventure.parser import parse
from adventure.saves import load_game, slugify
from adventure.state import GameState, SaveError
from adventure.world import WorldError, load_world

WELCOME = "=== Aventura de Texto ===\nDigite 'ajuda' para ver os comandos.\n"


def ask_name() -> str | None:
    """Ask for the character name until it is valid. None if input ends."""
    while True:
        try:
            name = input("Nome do personagem: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not name:
            continue
        try:
            slugify(name)
        except SaveError as error:
            print(error)
            continue
        return name


def main() -> int:
    try:
        world = load_world()
    except WorldError as error:
        print(f"Erro ao carregar o mundo:\n{error}")
        return 1
    game = Game(world)
    print(WELCOME)
    name = ask_name()
    if name is None:
        return 0
    try:
        state = load_game(name, world, game.saves_dir)
    except SaveError as error:
        print(f"Não foi possível carregar o personagem: {error}")
        return 1
    if state is None:
        state = GameState.new(world, name)
        print(f"Bem-vindo, {name}!\n")
    else:
        print(f"Bem-vindo de volta, {state.player_name}!\n")
    print(describe_room(state, world))
    while state.running:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        command = parse(line)
        if command is None:
            continue
        print(execute(state, command, game))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
