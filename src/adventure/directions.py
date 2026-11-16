"""Compass directions: canonical ids, pt-BR labels and the words players type."""

# Canonical ids (used in data files and the engine), in display order.
ORDER: tuple[str, ...] = ("north", "south", "east", "west")

LABELS: dict[str, str] = {
    "north": "norte",
    "south": "sul",
    "east": "leste",
    "west": "oeste",
}

OPPOSITE: dict[str, str] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}

# What the player may type (pt-BR) -> canonical id.
ALIASES: dict[str, str] = {
    "norte": "north",
    "n": "north",
    "sul": "south",
    "s": "south",
    "leste": "east",
    "l": "east",
    "oeste": "west",
    "o": "west",
}
