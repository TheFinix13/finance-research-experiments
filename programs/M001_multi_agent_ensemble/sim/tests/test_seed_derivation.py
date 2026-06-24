"""Determinism + collision-freeness of `sim.core.seed`."""
from __future__ import annotations

from programs.M001_multi_agent_ensemble.sim.core.seed import seed, seed_for


def test_seed_is_deterministic():
    assert seed("isagi_yoichi", 0) == seed("isagi_yoichi", 0)
    assert seed("isagi_yoichi", 12345) == seed("isagi_yoichi", 12345)


def test_seed_changes_when_either_input_changes():
    s1 = seed("isagi_yoichi", 0)
    s2 = seed("isagi_yoichi", 1)
    s3 = seed("nagi_seishiro", 0)
    assert s1 != s2
    assert s1 != s3
    assert s2 != s3


def test_seed_is_collision_free_across_agents_x_ticks():
    """4 MVP agents x 1000 ticks must produce 4000 distinct seeds."""
    agents = ["isagi_yoichi", "nagi_seishiro", "barou_shoei", "kunigami_rensuke"]
    seeds = set()
    for a in agents:
        for t in range(1000):
            seeds.add(seed(a, t))
    assert len(seeds) == 4 * 1000


def test_seed_full_canon_collision_free():
    """10-agent canon x 5000 ticks: 50,000 distinct seeds."""
    agents = [
        "isagi_yoichi", "bachira_meguru", "itoshi_rin", "chigiri_hyoma",
        "reo_mikage", "nagi_seishiro", "barou_shoei", "yukimiya_kenyu",
        "aoshi_tokimitsu", "kunigami_rensuke",
    ]
    seeds = set()
    for a in agents:
        for t in range(5000):
            seeds.add(seed(a, t))
    assert len(seeds) == 10 * 5000


def test_seed_for_channels_are_uncorrelated():
    """Different channels at the same (agent, tick) produce distinct values."""
    a, t = "isagi_yoichi", 42
    channels = ["default", "friction.reject", "friction.partial", "size_noise"]
    vals = {c: seed_for(a, t, c) for c in channels}
    assert len(set(vals.values())) == len(channels)


def test_seed_bounds():
    """Returns non-negative 63-bit integers."""
    s = seed("agent", 0)
    assert 0 <= s < (1 << 63)
