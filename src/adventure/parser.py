"""Turn a raw input line into a Command. Pure: no I/O."""

from dataclasses import dataclass

from adventure import directions

# User-facing words (pt-BR) mapped to canonical verbs used by the engine.
ALIASES: dict[str, str] = {
    "ajuda": "help",
    "?": "help",
    "sair": "quit",
    "q": "quit",
    "olhar": "look",
    "ver": "look",
    "ir": "go",
    "andar": "go",
    "pegar": "take",
    "pegue": "take",
    "largar": "drop",
    "soltar": "drop",
    "usar": "use",
    "cortar": "chop",
    "minerar": "mine",
    "receitas": "recipes",
    "fabricar": "craft",
    "equipar": "equip",
    "perfil": "profile",
    "status": "profile",
    "p": "profile",
    "loja": "shop",
    "comprar": "buy",
    "inventario": "inventory",
    "inventário": "inventory",
    "inv": "inventory",
    "i": "inventory",
    "atacar": "attack",
    "fugir": "flee",
    "descansar": "rest",
    "salvar": "save",
}


@dataclass(frozen=True)
class Command:
    verb: str
    noun: str = ""


def parse(line: str) -> Command | None:
    """Parse a line into a Command, or None if the line is blank.

    A bare direction ("norte", "n") means "go". Directions are turned into
    their canonical ids. Unknown verbs are kept as typed so the engine can
    report them.
    """
    words = line.strip().lower().split()
    if not words:
        return None
    verb, *rest = words
    if verb in directions.ALIASES:
        return Command("go", directions.ALIASES[verb])
    verb = ALIASES.get(verb, verb)
    noun = " ".join(rest)
    if verb == "go":
        noun = directions.ALIASES.get(noun, noun)
    return Command(verb, noun)
