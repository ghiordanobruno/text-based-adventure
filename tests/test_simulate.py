from collections import Counter
from random import Random

import pytest

from adventure.engine import Game
from adventure.simulate import (
    DEFAULT_WALKTHROUGH_PATH,
    FIGHT,
    Report,
    fight,
    format_report,
    load_walkthrough,
    main,
    play,
    simulate,
)
from adventure.world import load_world, parse_world
from helpers import ScriptedRng, do

# Small world: pick the key, beat the rat, open the door, beat the ogre.
ROUTE = ["pegar velha", "n", "l", FIGHT, "o", "usar chave", "n", FIGHT]


# --- the walkthrough file --------------------------------------------------------


def test_load_walkthrough_skips_comments_and_blank_lines(tmp_path):
    path = tmp_path / "walk.txt"
    path.write_text(
        "# a comment\n\nn\n  FIGHT  # inline comment\n\n# another\nusar chave\n",
        encoding="utf-8",
    )
    assert load_walkthrough(path) == ["n", "FIGHT", "usar chave"]


def test_the_real_walkthrough_file_has_commands_and_fights():
    lines = load_walkthrough()
    assert DEFAULT_WALKTHROUGH_PATH.exists()
    assert FIGHT in lines
    assert not any(line.startswith("#") for line in lines)


# --- fight / play ----------------------------------------------------------------


def test_play_follows_the_route_and_wins(game):
    outcome = play(game, ROUTE)
    assert outcome.won
    assert outcome.killed_by is None
    assert outcome.state.defeated == ["cellar", "lair"]
    assert not outcome.state.running


def test_play_collects_the_text_of_non_fight_commands(game):
    outcome = play(game, ROUTE)
    assert len(outcome.outputs) == len(ROUTE) - ROUTE.count(FIGHT)
    assert any("se abre" in text for text in outcome.outputs)


def test_play_reports_who_killed_the_player(small_world_data, tmp_path):
    small_world_data["player"]["max_hp"] = 5  # the ogre's first hit is fatal
    game = Game(parse_world(small_world_data), tmp_path, ScriptedRng(0.0))
    outcome = play(game, ROUTE)
    assert not outcome.won
    assert outcome.killed_by == "Ogro"
    assert outcome.state.hp == 0


def test_play_stops_when_the_game_has_ended(game):
    outcome = play(game, ["sair", "pegar velha"])
    assert not outcome.state.running
    assert outcome.state.inventory == []
    assert len(outcome.outputs) == 1


def test_play_with_an_unfinished_route_is_not_a_win(game):
    assert not play(game, ["n"]).won


def test_fight_without_an_enemy_means_the_walkthrough_is_out_of_date(game):
    with pytest.raises(ValueError, match="walkthrough"):
        play(game, [FIGHT])


def test_play_drinks_potions_when_life_is_low(game):
    outcome = play(game, ["comprar azul 2", *ROUTE], heal_below=0.35)
    assert outcome.won
    assert outcome.state.inventory.count("blue_potion") == 1  # one was drunk


def test_play_never_drinks_with_a_policy_of_zero(game):
    outcome = play(game, ["comprar azul 2", *ROUTE], heal_below=0.0)
    assert outcome.won
    assert outcome.state.inventory.count("blue_potion") == 2


def test_fight_runs_until_the_monster_is_dead(state, game):
    do(state, game, "n")
    do(state, game, "l")
    fight(state, game)
    assert state.combat is None
    assert state.defeated == ["cellar"]


def test_fight_does_nothing_when_there_is_no_fight(state, game):
    fight(state, game)
    assert state.hp == state.max_hp


def test_fight_gives_up_if_it_never_ends(state, game):
    do(state, game, "n")
    do(state, game, "l")
    with pytest.raises(RuntimeError):
        fight(state, game, max_rounds=1)  # the rat needs two hits


# --- many games ------------------------------------------------------------------


def test_simulate_counts_every_game_as_a_win_or_a_death():
    report = simulate(load_world(), load_walkthrough(), games=30, heal_below=0.0)
    assert report.games == 30
    assert report.wins + sum(report.deaths.values()) == 30


def test_simulate_is_reproducible_for_the_same_seed():
    world, lines = load_world(), load_walkthrough()
    first = simulate(world, lines, games=30, heal_below=0.35, seed=7)
    second = simulate(world, lines, games=30, heal_below=0.35, seed=7)
    assert first == second


def test_simulate_games_use_different_seeds():
    world, lines = load_world(), load_walkthrough()
    report = simulate(world, lines, games=60, heal_below=0.0)
    assert 0 < report.wins < 60  # never-heal is neither a sure win nor a sure loss


def test_each_simulated_game_gets_its_own_random_generator():
    # Same seed -> same outcome, so seed + n must be what drives game n.
    world, lines = load_world(), load_walkthrough()
    alone = play(Game(world, rng=Random(5)), lines, 0.0)
    report = simulate(world, lines, games=1, heal_below=0.0, seed=5)
    assert report.wins == alone.won


# --- report text -----------------------------------------------------------------


def test_format_report_for_a_policy_that_never_heals():
    text = format_report(0.0, Report(10, 4, Counter({"Mula sem Cabeça": 6})))
    assert text.startswith("Nunca bebe poção: 40.0% de vitórias (4/10)")
    assert "derrotas para: Mula sem Cabeça 6" in text


def test_format_report_for_a_healing_threshold():
    text = format_report(0.35, Report(20, 19, Counter({"Bixo Papão": 1})))
    assert text.startswith("Bebe poção abaixo de 35% da vida: 95.0%")


def test_format_report_without_deaths_has_one_line():
    assert "\n" not in format_report(0.5, Report(5, 5, Counter()))


# --- gear lines ------------------------------------------------------------------

GEAR_ROUTE = ["@gear cortar 2", "@gear fabricar espada de madeira", *ROUTE]


def test_play_runs_the_gear_lines_by_default(game):
    outcome = play(game, GEAR_ROUTE)
    assert outcome.state.equipped == {"weapon": "wood_sword"}
    assert outcome.state.gathered == {"hall:chop": 2}
    assert outcome.won


def test_play_skips_the_gear_lines_when_asked(game):
    outcome = play(game, GEAR_ROUTE, gear=False)
    assert outcome.state.equipped == {}
    assert outcome.state.gathered == {}
    assert outcome.state.inventory.count("wood") == 0


def test_a_gear_line_can_be_any_command(game):
    outcome = play(game, ["@gear   cortar 1"])
    assert outcome.state.inventory.count("wood") == 2


def test_gear_can_be_the_difference_in_a_fight(small_world_data, tmp_path):
    small_world_data["player"]["max_hp"] = 12  # the rat and the ogre are deadly
    world = parse_world(small_world_data)
    with_gear = play(Game(world, tmp_path, ScriptedRng(0.0)), GEAR_ROUTE, gear=True)
    without = play(Game(world, tmp_path, ScriptedRng(0.0)), GEAR_ROUTE, gear=False)
    assert with_gear.state.hp >= without.state.hp


def test_format_report_marks_runs_without_equipment():
    text = format_report(0.35, Report(10, 1, Counter()), gear=False)
    assert "abaixo de 35% da vida, sem equipamento" in text


# --- command line ----------------------------------------------------------------


def test_main_prints_one_line_group_per_policy(capsys):
    assert main(["10"]) == 0
    out = capsys.readouterr().out
    assert "Nunca bebe poção" in out
    assert "Bebe poção abaixo de 35% da vida" in out
    assert "Bebe poção abaixo de 50% da vida" in out


def test_main_accepts_custom_policies(capsys):
    assert main(["10", "0.2"]) == 0
    out = capsys.readouterr().out
    assert "abaixo de 20% da vida" in out
    assert out.count("vitórias") == 1


def test_main_by_default_also_runs_one_game_set_without_equipment(capsys):
    assert main(["5"]) == 0
    assert capsys.readouterr().out.count("sem equipamento") == 1


def test_main_flag_removes_the_equipment_from_every_policy(capsys):
    assert main(["5", "--sem-equipamento"]) == 0
    assert capsys.readouterr().out.count("sem equipamento") == 3


def test_main_flag_works_with_a_custom_policy(capsys):
    assert main(["5", "0.2", "--sem-equipamento"]) == 0
    out = capsys.readouterr().out
    assert "abaixo de 20% da vida, sem equipamento" in out
    assert out.count("vitórias") == 1


@pytest.mark.parametrize(
    "args", [["abc"], ["0"], ["10", "2"], ["10", "x"], ["10", "--foo"]]
)
def test_main_rejects_bad_arguments(capsys, args):
    assert main(args) == 2
    assert "Uso:" in capsys.readouterr().out
