import pytest

from adventure.parser import Command, parse


def test_blank_line_returns_none():
    assert parse("") is None
    assert parse("   ") is None


@pytest.mark.parametrize(
    ("line", "verb"),
    [
        ("ajuda", "help"),
        ("?", "help"),
        ("sair", "quit"),
        ("q", "quit"),
        ("olhar", "look"),
        ("ver", "look"),
        ("inventario", "inventory"),
        ("inventário", "inventory"),
        ("inv", "inventory"),
        ("i", "inventory"),
        ("salvar", "save"),
        ("atacar", "attack"),
        ("fugir", "flee"),
        ("descansar", "rest"),
        ("perfil", "profile"),
        ("status", "profile"),
        ("p", "profile"),
        ("loja", "shop"),
        ("receitas", "recipes"),
    ],
)
def test_aliases_map_to_canonical_verbs(line, verb):
    assert parse(line) == Command(verb)


@pytest.mark.parametrize(
    ("line", "command"),
    [
        ("pegar lanterna", Command("take", "lanterna")),
        ("pegue chave velha", Command("take", "chave velha")),
        ("largar lanterna", Command("drop", "lanterna")),
        ("soltar chave velha", Command("drop", "chave velha")),
        ("usar chave velha", Command("use", "chave velha")),
        ("comprar poção de vida 2", Command("buy", "poção de vida 2")),
        ("cortar", Command("chop", "")),
        ("cortar 5", Command("chop", "5")),
        ("minerar 9", Command("mine", "9")),
        ("fabricar espada de cobre", Command("craft", "espada de cobre")),
        ("equipar armadura de madeira", Command("equip", "armadura de madeira")),
    ],
)
def test_take_and_drop_keep_the_item_name_as_noun(line, command):
    assert parse(line) == command


@pytest.mark.parametrize(
    ("line", "direction"),
    [
        ("ir norte", "north"),
        ("andar sul", "south"),
        ("ir l", "east"),
        ("ir oeste", "west"),
        ("norte", "north"),
        ("n", "north"),
        ("s", "south"),
        ("l", "east"),
        ("o", "west"),
    ],
)
def test_movement_is_parsed_to_canonical_direction(line, direction):
    assert parse(line) == Command("go", direction)


def test_go_without_direction_has_empty_noun():
    assert parse("ir") == Command("go", "")


def test_go_keeps_unknown_direction_as_typed():
    assert parse("ir cima") == Command("go", "cima")


def test_parse_splits_verb_and_noun_and_normalizes_case():
    assert parse("  DANÇAR  Chave Velha ") == Command("dançar", "chave velha")


def test_unknown_verb_is_kept_as_typed():
    assert parse("dançar") == Command("dançar")
