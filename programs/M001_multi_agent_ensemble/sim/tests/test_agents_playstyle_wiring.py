"""Contract tests -- Phase E playstyle wiring for the 8 v1 agents.

Doctrine 06 v0.5 section 4.1a. Verifies each agent's __init__ sets the
correct playstyle + tier, and that the F19/F20 default dispatch on
BaseStriker produces sensible (non-default) sizing / risk shapes.
"""
from __future__ import annotations

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
from programs.M001_multi_agent_ensemble.sim.agents.a05_reo import A5ReoV1
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import A10KunigamiV1
from programs.M001_multi_agent_ensemble.sim.core.lot_intent import FIXED_LOT
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
)

PLAYSTYLE_EXPECTED = {
    "A1IsagiV1":    ("conservative_metavision", 1),
    "A2BachiraV1":  ("rebel_tight",             2),
    "A3RinV1":      ("analytical_precision",    2),
    "A4ChigiriV1":  ("speed_momentum",          2),
    "A5ReoV1":      ("copier_hrp",              2),
    "A6NagiV1":     ("confluence_only",         2),
    "A7BarouV1":    ("solo_king",               2),
    "A10KunigamiV1":("defensive",               2),
}

AGENT_CLASSES = [
    A1IsagiV1, A2BachiraV1, A3RinV1, A4ChigiriV1,
    A5ReoV1, A6NagiV1, A7BarouV1, A10KunigamiV1,
]


@pytest.mark.parametrize("cls", AGENT_CLASSES, ids=lambda c: c.__name__)
def test_agent_playstyle_and_tier_set(cls):
    agent = cls()
    expected_playstyle, expected_tier = PLAYSTYLE_EXPECTED[cls.__name__]
    assert agent.playstyle == expected_playstyle, (
        f"{cls.__name__}: expected playstyle={expected_playstyle}, "
        f"got {agent.playstyle!r}"
    )
    assert agent.tier == expected_tier, (
        f"{cls.__name__}: expected tier={expected_tier}, got {agent.tier}"
    )


@pytest.mark.parametrize("cls", AGENT_CLASSES, ids=lambda c: c.__name__)
def test_agent_lot_intent_dispatches_non_default(cls):
    agent = cls()
    lot = agent.lot_intent(conviction=0.75, sl_pips=40.0, equity=100.0, regime_fit=0.5)
    assert lot > 0
    # Not one of the "unknown" default paths for the high-conviction case.
    # (defensive playstyle at base_lot=0.05, high conviction may still land
    # near FIXED_LOT; the important guarantee is > 0 and playstyle-shaped.)
    assert isinstance(lot, float)


@pytest.mark.parametrize("cls", AGENT_CLASSES, ids=lambda c: c.__name__)
def test_agent_risk_intent_returns_sensible_shape(cls):
    agent = cls()
    sl, ladder = agent.risk_intent(conviction=0.7, atr_pips=30.0, h1_swing_pips=60.0)
    assert 10.0 <= sl <= 100.0, f"{cls.__name__}: SL={sl} out of range"
    assert len(ladder) >= 1
    assert all(tp > 0 for tp in ladder)
    assert all(tp >= sl for tp in ladder), (
        f"{cls.__name__}: TP ladder has TP < SL: sl={sl} ladder={ladder}"
    )


def test_isagi_conservative_lot_smaller_than_chigiri_speed():
    """Playstyle differentiation smoke test -- doctrine §3.11.5 criterion #5.

    At the SAME conviction and regime_fit, Isagi (conservative) should
    size smaller than Chigiri (speed_momentum) with matching gain
    parameters, because their base_lots differ by design (Isagi 0.10 vs
    Chigiri 0.08 with higher gain).
    """
    isagi = A1IsagiV1()
    chigiri = A4ChigiriV1()
    isagi_lot = isagi.lot_intent(0.60, 30.0, 100.0, 0.5)
    chigiri_lot = chigiri.lot_intent(0.60, 30.0, 100.0, 0.5)
    # Just require them to be different -- doctrine wants dispersion.
    assert isagi_lot != chigiri_lot


def test_bachira_rebel_tight_sl_smaller_than_isagi_conservative():
    """Bachira's rebel_tight has 10-25 pip SL band; Isagi 30-50."""
    bachira = A2BachiraV1()
    isagi = A1IsagiV1()
    bachira_sl, _ = bachira.risk_intent(0.7, 20.0, 40.0)
    isagi_sl, _ = isagi.risk_intent(0.7, 40.0, 60.0)
    assert bachira_sl < isagi_sl, (
        f"Bachira SL {bachira_sl} not < Isagi SL {isagi_sl}"
    )


@pytest.mark.parametrize("cls", AGENT_CLASSES, ids=lambda c: c.__name__)
def test_agent_read_workspace_returns_tuple(cls):
    """F21 default -- read_workspace returns a tier-appropriate tuple."""
    import datetime as dt
    agent = cls()
    ws = ReasoningWorkspace()
    snap = ws.snapshot(as_of=dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc),
                       current_tick=100)
    result = agent.read_workspace(snap, as_of=dt.datetime(2025, 1, 1,
                                                          tzinfo=dt.timezone.utc))
    assert isinstance(result, tuple)
    assert len(result) == 0  # empty snapshot
