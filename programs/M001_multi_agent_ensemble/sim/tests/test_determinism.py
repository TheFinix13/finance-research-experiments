"""Determinism contract — same inputs -> same Thoughts and ledger bytes.

09 section 1.2:
    Given identical inputs (market_state_t, ledger_snapshot_t, seed)
    every agent emits an identical Thought on tick t.

If replay diverges on a second pass with the same manifest, the run
is **invalid** (09 section 1.2).
"""
from __future__ import annotations

from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import IsagiYoichi
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import NagiSeishiro
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import BarouShoei
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    KunigamiRensuke,
)
from programs.M001_multi_agent_ensemble.sim.agents.placeholder import (
    PlaceholderAgent,
)
from programs.M001_multi_agent_ensemble.sim.core.engine import run_replay
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import CanonRole
from programs.M001_multi_agent_ensemble.sim.tests.conftest import make_bars


def _mvp_agents():
    rosters = [
        (IsagiYoichi, "isagi_yoichi", "metavision", 0.60, "H1"),
        (NagiSeishiro, "nagi_seishiro", "perfect trap", 0.45, "H1"),
        (BarouShoei, "barou_shoei", "lone wolf", 1.00, "H4"),
        (KunigamiRensuke, "kunigami_rensuke", "anti-tilt", 0.00, "H1"),
    ]
    out = []
    for klass, aid, weapon, ego, tf in rosters:
        out.append(
            klass(
                agent_id=aid,
                canon_role=CanonRole(
                    canon_player=aid,
                    weapon=weapon,
                    ego=ego,
                    target_hold_hours=24.0,
                    narrative_voice="phi2 stub",
                ),
                home_tf=tf,
                symbols=["EURUSD"] if aid != "barou_shoei" else ["USDCAD"],
            )
        )
    return out


def test_run_replay_is_deterministic_5_cases():
    """Five (5) independent rosters x bar sequences -> byte-identical Thoughts."""
    cases = [
        {"n": 10, "symbol": "EURUSD", "tf": "H1"},
        {"n": 24, "symbol": "EURUSD", "tf": "H1"},
        {"n": 48, "symbol": "EURUSD", "tf": "H4"},
        {"n": 96, "symbol": "EURUSD", "tf": "H1"},
        {"n": 144, "symbol": "EURUSD", "tf": "H1"},
    ]
    for case in cases:
        agents_a = _mvp_agents()
        agents_b = _mvp_agents()
        bars_a = make_bars(n=case["n"], symbol=case["symbol"], timeframe=case["tf"])
        bars_b = make_bars(n=case["n"], symbol=case["symbol"], timeframe=case["tf"])
        out_a = run_replay(bars_a, agents_a, FullLedger())
        out_b = run_replay(bars_b, agents_b, FullLedger())
        ja = [t.to_json() for t in out_a.thoughts]
        jb = [t.to_json() for t in out_b.thoughts]
        assert ja == jb, f"divergence in case {case}"


def test_thought_ids_are_stable_across_runs():
    agents_a = _mvp_agents()
    agents_b = _mvp_agents()
    bars = make_bars(n=12, symbol="EURUSD", timeframe="H1")
    out_a = run_replay(bars, agents_a, FullLedger())
    out_b = run_replay(bars, agents_b, FullLedger())
    ids_a = [t.thought_id for t in out_a.thoughts]
    ids_b = [t.thought_id for t in out_b.thoughts]
    assert ids_a == ids_b
    # And no duplicates.
    assert len(set(ids_a)) == len(ids_a)


def test_placeholder_agents_also_deterministic():
    canon = CanonRole(
        canon_player="x", weapon="y", ego=0.5,
        target_hold_hours=12.0, narrative_voice="z",
    )
    a1 = PlaceholderAgent("ghost", canon, "H1", ["EURUSD"])
    a2 = PlaceholderAgent("ghost", canon, "H1", ["EURUSD"])
    bars = make_bars(n=8, symbol="EURUSD", timeframe="H1")
    j1 = [t.to_json() for t in run_replay(bars, [a1], FullLedger()).thoughts]
    j2 = [t.to_json() for t in run_replay(bars, [a2], FullLedger()).thoughts]
    assert j1 == j2
