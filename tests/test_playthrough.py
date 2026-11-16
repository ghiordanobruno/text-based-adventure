"""End to end: the real data/world.json can be won by following the walkthrough."""

from adventure.engine import Game
from adventure.simulate import load_walkthrough, play, simulate
from adventure.world import load_world
from helpers import ScriptedRng, do


def _real_game(rng, saves_dir):
    return Game(load_world(), saves_dir=saves_dir, rng=rng)


def test_the_walkthrough_wins_the_real_world_when_every_strike_hits(tmp_path):
    outcome = play(_real_game(ScriptedRng(0.0), tmp_path), load_walkthrough())
    state = outcome.state
    assert outcome.won
    assert not state.running
    assert state.hp > 0
    assert state.level > 1
    assert state.defeated == [
        "forest_path",
        "clearing",
        "boss_lair",
        "dunes",
        "ruins",
        "mule_clearing",
    ]
    assert any("para o norte se abre" in text for text in outcome.outputs)


def test_the_walkthrough_crafts_both_sets_and_wears_the_copper_one(tmp_path):
    state = play(_real_game(ScriptedRng(0.0), tmp_path), load_walkthrough()).state
    assert state.equipped == {
        "weapon": "copper_sword",
        "shield": "copper_buckler",
        "armor": "copper_armor",
    }
    # The wooden set was worn first and went back to the inventory when replaced.
    for item in ("wooden_sword", "wooden_buckler", "wooden_armor"):
        assert item in state.inventory


def test_the_walkthrough_exhausts_both_resource_nodes_and_has_materials_left(tmp_path):
    outcome = play(_real_game(ScriptedRng(0.0), tmp_path), load_walkthrough())
    state = outcome.state
    assert state.gathered == {"forest_path:chop": 15, "desert_camp:mine": 9}
    # 45 wood - 26 (wooden set) - 13 (copper set), 27 copper - 24.
    assert state.inventory.count("wood") == 6
    assert state.inventory.count("copper") == 3
    assert any("esgotado" in text for text in outcome.outputs)


def test_the_boss_door_cannot_be_opened_without_the_key(tmp_path):
    game = _real_game(ScriptedRng(0.0), tmp_path)
    state = play(game, ["n", "FIGHT", "n", "FIGHT", "n"]).state
    assert state.current_room == "cave_entrance"
    assert "trancada" in do(state, game, "n")
    assert state.current_room == "cave_entrance"


def test_a_careful_player_usually_wins_with_real_randomness():
    """Balance guard: hard enough to need potions, never close to impossible."""
    report = simulate(load_world(), load_walkthrough(), games=200, heal_below=0.35)
    assert report.win_rate >= 0.75


def test_ignoring_potions_makes_the_game_clearly_harder():
    """The shop must matter: never healing should lose noticeably more often."""
    world, lines = load_world(), load_walkthrough()
    careful = simulate(world, lines, games=200, heal_below=0.35)
    reckless = simulate(world, lines, games=200, heal_below=0.0)
    assert careful.wins > reckless.wins + 200 * 0.2


def test_skipping_the_crafting_makes_the_game_much_harder():
    """Crafting must matter: the starting gear alone is not enough."""
    world, lines = load_world(), load_walkthrough()
    geared = simulate(world, lines, games=200, heal_below=0.35, gear=True)
    bare = simulate(world, lines, games=200, heal_below=0.35, gear=False)
    assert geared.wins > bare.wins + 200 * 0.4
