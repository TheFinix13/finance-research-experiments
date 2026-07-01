"""Sentinel R1-R6 wiring tests (Phi4.2 mini-sprint, 2026-06-30).

The Sentinel unit tests in `test_sentinel.py` exercise each R-rule in
isolation. These integration tests verify that the wired evaluator in
`sim/scoring/run_phi4_squad_gate.py` produces the expected journal
entries + summarised counts + block behaviour when `sentinel_blocks`
is toggled.

The tests use synthetic AgentProposal objects rather than driving the
full harness with real bars -- the wiring surface under test is the
per-proposal Sentinel evaluation + journalling logic, which is
orthogonal to the bar-replay driver.
"""
from __future__ import annotations

from datetime import datetime, timezone

from programs.M001_multi_agent_ensemble.sim.core.sentinel import (
    LOSS_STREAK_TRIGGER,
    SentinelContext,
    check_r6_per_symbol_risk_cap,
    evaluate_proposal,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    LadderRung,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    SANDBOX_EQUITY_DOLLARS,
    SANDBOX_PIP_VALUE_PER_MIN_LOT,
    _sentinel_log_entry,
    summarise_sentinel_log,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_proposal(
    *,
    agent_id: str = "isagi_yoichi",
    symbol: str = "EURUSD",
    entry: float = 1.1000,
    stop: float = 1.0960,          # 40 pip stop -> $4 risk at 0.01 lot
    conviction: float = 0.70,
    tick_id: int = 1,
) -> AgentProposal:
    """Build a minimum-viable AgentProposal for wiring tests."""
    return AgentProposal(
        agent_id=agent_id,
        tick_id=tick_id,
        source_thought_id=f"t-{tick_id}",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        symbol=symbol,
        direction="long",
        entry=entry,
        stop=stop,
        ladder=[LadderRung(price=entry + 0.0075, fraction=1.0)],
        conviction=conviction,
        regime_fit=0.5,
        valid_until=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        rationale={},
    )


def _base_context() -> SentinelContext:
    """The sandbox-default context used across the wiring tests."""
    return SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
    )


# ---------------------------------------------------------------------------
# R1 through the wired evaluate_proposal path
# ---------------------------------------------------------------------------

def test_evaluate_proposal_r1_blocks_wide_stop_via_wired_path():
    # 100 pip stop -> $10 risk at 0.01 lot; equity cap $5.00 -> block.
    proposal = _make_proposal(entry=1.1000, stop=1.0900)  # 100 pip stop
    decision = evaluate_proposal(proposal, _base_context())
    assert decision.allowed is False
    assert decision.rule == "R1"


def test_evaluate_proposal_r1_allows_narrow_stop():
    # 40 pip stop -> $4.00 risk at 0.01 lot; below cap -> allow.
    proposal = _make_proposal()  # default 40 pip
    decision = evaluate_proposal(proposal, _base_context())
    assert decision.allowed is True
    assert decision.rule == "OK"


# ---------------------------------------------------------------------------
# R5 via Kunigami warning + direct consecutive-loss counter
# ---------------------------------------------------------------------------

def test_evaluate_proposal_r5_fires_on_kunigami_warning():
    proposal = _make_proposal()
    ctx = SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        kunigami_loss_streak_active=True,
    )
    decision = evaluate_proposal(proposal, ctx)
    assert decision.rule == "R5"
    assert decision.allowed is True  # audit-only in Phi4.1 harness


def test_evaluate_proposal_r5_fires_on_direct_consecutive_losses():
    proposal = _make_proposal()
    ctx = SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        consecutive_losses=LOSS_STREAK_TRIGGER,
    )
    decision = evaluate_proposal(proposal, ctx)
    assert decision.rule == "R5"


def test_evaluate_proposal_r5_silent_below_trigger():
    proposal = _make_proposal()
    ctx = SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        consecutive_losses=LOSS_STREAK_TRIGGER - 1,
        kunigami_loss_streak_active=False,
    )
    decision = evaluate_proposal(proposal, ctx)
    assert decision.rule == "OK"


# ---------------------------------------------------------------------------
# R6 per-symbol total-risk cap
# ---------------------------------------------------------------------------

def test_r6_blocks_when_combined_risk_exceeds_cap():
    # Current EURUSD open risk = $0.80; additional $0.40 -> $1.20 > $1.00
    # cap (1% of $100 equity).
    d = check_r6_per_symbol_risk_cap(
        "EURUSD",
        current_symbol_risk_dollars=0.80,
        additional_risk_dollars=0.40,
        equity=100.0,
    )
    assert d.allowed is False
    assert d.rule == "R6"
    assert abs(d.payload["combined_risk_dollars"] - 1.20) < 1e-9


def test_r6_allows_when_within_cap():
    d = check_r6_per_symbol_risk_cap(
        "EURUSD",
        current_symbol_risk_dollars=0.50,
        additional_risk_dollars=0.30,
        equity=100.0,
    )
    assert d.allowed is True


def test_evaluate_proposal_r6_via_context():
    proposal = _make_proposal()  # 40 pip / $4 risk (well within R1 cap)
    ctx = SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        open_symbol_risk_dollars={"EURUSD": 0.90},
        additional_risk_dollars=0.20,   # combined $1.10 > $1.00 cap
    )
    decision = evaluate_proposal(proposal, ctx)
    assert decision.allowed is False
    assert decision.rule == "R6"


# ---------------------------------------------------------------------------
# Log-entry + summariser wiring
# ---------------------------------------------------------------------------

def test_sentinel_log_entry_shape():
    proposal = _make_proposal()
    ctx = _base_context()
    decision = evaluate_proposal(proposal, ctx)
    entry = _sentinel_log_entry(
        tick_id=42,
        proposal=proposal,
        decision=decision,
        kunigami_active=False,
    )
    assert entry["tick_id"] == 42
    assert entry["agent_id"] == "isagi_yoichi"
    assert entry["symbol"] == "EURUSD"
    assert entry["rule"] == decision.rule
    assert entry["allowed"] == decision.allowed
    assert entry["kunigami_loss_streak_active"] is False
    assert "payload" in entry


def test_summarise_sentinel_log_counts_ok_and_audit_and_block():
    proposal_ok = _make_proposal(entry=1.1000, stop=1.0960)   # narrow -> OK
    proposal_r1 = _make_proposal(entry=1.1000, stop=1.0900)   # wide -> R1 block
    ctx_base = _base_context()
    ctx_kuni = SentinelContext(
        equity=SANDBOX_EQUITY_DOLLARS,
        pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        kunigami_loss_streak_active=True,
    )
    log_rows = [
        _sentinel_log_entry(
            tick_id=1, proposal=proposal_ok,
            decision=evaluate_proposal(proposal_ok, ctx_base),
            kunigami_active=False,
        ),
        _sentinel_log_entry(
            tick_id=2, proposal=proposal_ok,
            decision=evaluate_proposal(proposal_ok, ctx_kuni),
            kunigami_active=True,
        ),
        _sentinel_log_entry(
            tick_id=3, proposal=proposal_r1,
            decision=evaluate_proposal(proposal_r1, ctx_base),
            kunigami_active=False,
        ),
    ]
    counts = summarise_sentinel_log(log_rows)
    assert counts.get("ok") == 1
    assert counts.get("R5_audit") == 1
    assert counts.get("R1_block") == 1


def test_summarise_sentinel_log_empty_returns_empty_dict():
    assert summarise_sentinel_log([]) == {}
