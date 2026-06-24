"""Ledger look-ahead guard + RedactedLedger filtering tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FrozenLedger,
    FullLedger,
    RedactedLedger,
    SyntheticLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Thought,
)


def _mk_thought(
    agent_id: str,
    tick_id: int,
    ts: datetime,
    *,
    decision_horizon: datetime | None = None,
    ttl_ticks: int = 24,
    symbol: str = "EURUSD",
) -> Thought:
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent_id,
        tick_id=tick_id,
        timestamp=ts,
        symbol=symbol,
        narrative=f"{agent_id} @ {tick_id}",
        tags=["t"],
        confidence_in_thought=0.5,
        expected_action=None,
        coordinate=None,
        decision_horizon=decision_horizon or ts,
        ttl_ticks=ttl_ticks,
        references=[],
    )


def test_full_ledger_returns_appended_thoughts():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    L = FullLedger()
    L.append(_mk_thought("a", 0, base))
    L.append(_mk_thought("b", 1, base + timedelta(hours=1)))
    out = L.read(as_of=base + timedelta(hours=10), current_tick=5)
    ids = {t.thought_id for t in out}
    assert "a:0:EURUSD" in ids
    assert "b:1:EURUSD" in ids


def test_redacted_ledger_filters_by_agent_id():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    full = FullLedger()
    full.append(_mk_thought("isagi_yoichi", 0, base))
    full.append(_mk_thought("nagi_seishiro", 0, base))
    r = RedactedLedger("isagi_yoichi", source=full)
    out = r.read(as_of=base + timedelta(hours=2), current_tick=5)
    assert all(t.agent_id == "isagi_yoichi" for t in out)
    assert len(out) == 1


def test_look_ahead_guard_drops_future_decision_horizon():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    L = FullLedger()
    # decision_horizon is in the FUTURE of as_of -> must be filtered out.
    future_dh = base + timedelta(hours=24)
    L.append(_mk_thought("a", 0, base, decision_horizon=future_dh))
    out = L.read(as_of=base + timedelta(hours=1), current_tick=5)
    assert len(out) == 0


def test_backwards_only_references_drops_same_tick():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    L = FullLedger()
    L.append(_mk_thought("a", 5, base))
    # Reader at tick 5 must not see thoughts at tick 5.
    out = L.read(as_of=base + timedelta(hours=1), current_tick=5)
    assert len(out) == 0


def test_ttl_drops_stale_thoughts():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    L = FullLedger()
    L.append(_mk_thought("a", 0, base, ttl_ticks=3))
    # Reader at tick 10 — TTL=3 -> dropped.
    out = L.read(as_of=base + timedelta(hours=20), current_tick=10)
    assert len(out) == 0
    # Reader at tick 2 — within TTL, survives.
    out2 = L.read(as_of=base + timedelta(hours=2), current_tick=2)
    assert len(out2) == 1


def test_frozen_ledger_writes_are_noops_for_reads():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    L = FrozenLedger("/nonexistent/snapshot/path/xyz")
    L.append(_mk_thought("a", 0, base))
    out = L.read(as_of=base, current_tick=5)
    assert len(out) == 0


def test_synthetic_ledger_returns_injected_null_hypothesis():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    null = [_mk_thought("ghost", 0, base)]
    L = SyntheticLedger(null)
    out = L.read(as_of=base + timedelta(hours=1), current_tick=5)
    assert {t.agent_id for t in out} == {"ghost"}
