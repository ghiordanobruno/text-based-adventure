from adventure.progression import award, xp_to_next_level
from adventure.state import GameState


def test_award_gives_gold_and_xp(state, world):
    lines = award(state, world, world.monsters["rat"])
    assert state.gold == 27  # 20 to start with + 7
    assert state.xp == 5
    assert "5 de experiência e 7 de ouro" in lines[0]


def test_below_the_threshold_there_is_no_level_up(state, world):
    lines = award(state, world, world.monsters["rat"])
    assert state.level == 1
    assert len(lines) == 1


def test_level_up_adds_the_per_level_gains_and_restores_life(state, world):
    state.xp = 6
    state.hp = 1
    lines = award(state, world, world.monsters["rat"])  # 11 xp: level 2 at 10
    assert state.level == 2
    assert (state.max_hp, state.attack, state.defense) == (40, 15, 1)
    assert state.hp == state.max_hp
    assert "nível 2" in lines[1]
    assert "Vida 40, ataque 15, defesa 1" in lines[1]


def test_a_big_reward_can_level_up_more_than_once(state, world):
    lines = award(state, world, world.monsters["ogre"])  # 40 xp: levels 2 and 3
    assert state.level == 3
    assert (state.max_hp, state.attack, state.defense) == (50, 20, 2)
    assert len(lines) == 3


def test_the_maximum_level_is_a_cap(state, world):
    state.level = 3
    state.xp = 30
    max_hp = state.max_hp
    award(state, world, world.monsters["ogre"])
    assert state.level == 3
    assert state.max_hp == max_hp
    assert state.xp == 70


def test_xp_to_next_level_follows_the_thresholds(state, world):
    assert xp_to_next_level(state, world) == 10
    state.level = 2
    assert xp_to_next_level(state, world) == 30
    state.level = 3
    assert xp_to_next_level(state, world) is None


def test_levels_use_a_plain_loop_over_the_thresholds(world):
    """Huge xp ends at the top level, whatever the table length."""
    state = GameState.new(world, "Teste")
    state.xp = 10**9
    award(state, world, world.monsters["rat"])
    assert state.level == len(world.progression.xp_to_level) + 1
