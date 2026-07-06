"""Phi5 aggregator-arm wiring tests (PROTOCOL §11.4, 2026-07-06).

Covers the plumbing that connects `aggregator_arms/` modules into
`_drive_squad_replay`:

  1. Arm validation -- unknown arms rejected; arms 3/4 require
     ``sentinel_blocks=True``.
  2. Arm 3 merge propagates the winner's ``agent_tier`` + journals
     ``arm3_winner_agent_id`` so TQS hold-hours scoring can resolve a
     real playstyle.
  3. `_agent_target_hold_hours` falls back to the merged winner's
     canonical hold when the synthetic ``arm3_merged_*`` id matches no
     roster agent.
  4. ARM4 sandbox risk cap admits realistic two-position stacks that
     the protocol's original 1% cap would have structurally blocked
     (the §11.4 scale fix).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms.same_direction_merge import (
    apply_same_direction_merge,
)
from programs.M001_multi_agent_ensemble.sim.core.sentinel import (
    check_r6_per_symbol_risk_cap,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    LadderRung,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    ARM4_SANDBOX_RISK_CAP_FRAC,
    SANDBOX_EQUITY_DOLLARS,
    SANDBOX_PIP_VALUE_PER_MIN_LOT,
    _agent_target_hold_hours,
    _arm4_proposal_risk_dollars,
    _drive_squad_replay,
)


def _proposal(
    *,
    agent_id: str,
    symbol: str = "EURUSD",
    direction: str = "long",
    conviction: float = 0.7,
    stop: float = 1.0950,
    agent_tier: int = 2,
) -> AgentProposal:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return AgentProposal(
        agent_id=agent_id, tick_id=0,
        source_thought_id=f"{agent_id}:0:{symbol}",
        timestamp=base, symbol=symbol,
        direction=direction,
        entry=1.1000, stop=stop,
        ladder=[LadderRung(price=1.1100, fraction=1.0)],
        conviction=conviction, regime_fit=0.5,
        valid_until=base + timedelta(hours=24),
        rationale={},
        agent_tier=agent_tier,
    )


# ---------------------------------------------------------------------------
# 1. Arm validation
# ---------------------------------------------------------------------------

class TestArmValidation:

    def _kwargs(self):
        """Minimal driver kwargs -- empty bars means the validation
        raise (if any) happens before any replay work."""
        class _StubAgent:
            agent_id = "stub"
            symbols = ()
            _cfg = None

        stub = _StubAgent()
        return dict(
            agents=[], isagi=stub, barou=stub, kunigami=stub,
            bars_by_symbol={}, ledger=None,
        )

    def test_unknown_arm_raises(self):
        with pytest.raises(ValueError, match="unknown aggregator_arm"):
            _drive_squad_replay(
                **self._kwargs(), aggregator_arm="arm99",
            )

    def test_arm3_requires_sentinel_blocks(self):
        with pytest.raises(ValueError, match="requires sentinel_blocks"):
            _drive_squad_replay(
                **self._kwargs(),
                aggregator_arm="arm3", sentinel_blocks=False,
            )

    def test_arm4_requires_sentinel_blocks(self):
        with pytest.raises(ValueError, match="requires sentinel_blocks"):
            _drive_squad_replay(
                **self._kwargs(),
                aggregator_arm="arm4", sentinel_blocks=False,
            )

    def test_phi41_default_accepts_empty_run(self):
        out = _drive_squad_replay(**self._kwargs())
        assert out.trades == []


# ---------------------------------------------------------------------------
# 2. Arm 3 merge metadata
# ---------------------------------------------------------------------------

class TestArm3MergeMetadata:

    def test_merged_proposal_carries_winner_tier(self):
        anchor = _proposal(
            agent_id="isagi_yoichi", conviction=0.9, agent_tier=1,
        )
        peer = _proposal(
            agent_id="barou_shoei", conviction=0.7, agent_tier=2,
        )
        merged = apply_same_direction_merge([anchor, peer], tick_id=1)
        assert len(merged) == 1
        assert merged[0].agent_tier == 1

    def test_merged_proposal_journals_winner_id(self):
        a = _proposal(agent_id="bachira_meguru", conviction=0.9)
        b = _proposal(agent_id="barou_shoei", conviction=0.7)
        merged = apply_same_direction_merge([a, b], tick_id=1)[0]
        assert merged.rationale["arm3_winner_agent_id"] == "bachira_meguru"
        assert merged.agent_id == "arm3_merged_bachira_meguru+barou_shoei"

    def test_singleton_passes_through_untouched(self):
        solo = _proposal(agent_id="barou_shoei")
        merged = apply_same_direction_merge([solo], tick_id=1)
        assert merged == [solo]

    def test_opposite_directions_not_merged(self):
        long_p = _proposal(agent_id="bachira_meguru", direction="long")
        short_p = _proposal(agent_id="barou_shoei", direction="short")
        merged = apply_same_direction_merge([long_p, short_p], tick_id=1)
        assert len(merged) == 2


# ---------------------------------------------------------------------------
# 3. Hold-hours fallback for merged trades
# ---------------------------------------------------------------------------

class _FakeCanonRole:
    def __init__(self, hold: float) -> None:
        self.target_hold_hours = hold


class _FakeAgent:
    def __init__(self, agent_id: str, hold: float) -> None:
        self.agent_id = agent_id
        self.canon_role = _FakeCanonRole(hold)


class _FakeTrade:
    pass


class TestHoldHoursFallback:

    def test_direct_agent_match_unchanged(self):
        t = _FakeTrade()
        t._source_agent_id = "barou_shoei"
        agents = [_FakeAgent("barou_shoei", 48.0)]
        assert _agent_target_hold_hours(t, agents) == 48.0

    def test_merged_id_falls_back_to_winner(self):
        t = _FakeTrade()
        t._source_agent_id = "arm3_merged_bachira_meguru+barou_shoei"
        t._source_winner_agent_id = "bachira_meguru"
        agents = [
            _FakeAgent("bachira_meguru", 12.0),
            _FakeAgent("barou_shoei", 48.0),
        ]
        assert _agent_target_hold_hours(t, agents) == 12.0

    def test_merged_id_without_winner_uses_default(self):
        t = _FakeTrade()
        t._source_agent_id = "arm3_merged_a+b"
        assert _agent_target_hold_hours(t, []) == 24.0


# ---------------------------------------------------------------------------
# 4. Arm 4 sandbox risk-cap scale
# ---------------------------------------------------------------------------

class TestArm4SandboxCap:

    def test_median_stop_proposal_risk_scale(self):
        # 27.5-pip stop @ fixed lot 0.1 => $27.50 risk on $100 equity.
        p = _proposal(agent_id="barou_shoei", stop=1.1000 - 0.00275)
        risk = _arm4_proposal_risk_dollars(
            p, pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
        )
        assert risk == pytest.approx(27.5, abs=0.1)

    def test_two_median_positions_admit_under_sandbox_cap(self):
        # Two median-risk positions (~$55 combined) exceed the 50% cap
        # only marginally; a median + tight pair passes. This verifies
        # the cap is in a REALISTIC band -- neither always-blocking
        # (protocol's original 1%) nor never-blocking.
        median_risk = 27.5
        tight_risk = 15.0
        ok = check_r6_per_symbol_risk_cap(
            symbol="EURUSD",
            current_symbol_risk_dollars=median_risk,
            additional_risk_dollars=tight_risk,
            equity=SANDBOX_EQUITY_DOLLARS,
            cap_frac=ARM4_SANDBOX_RISK_CAP_FRAC,
        )
        assert ok.allowed is True
        blocked = check_r6_per_symbol_risk_cap(
            symbol="EURUSD",
            current_symbol_risk_dollars=median_risk,
            additional_risk_dollars=median_risk,
            equity=SANDBOX_EQUITY_DOLLARS,
            cap_frac=ARM4_SANDBOX_RISK_CAP_FRAC,
        )
        assert blocked.allowed is False

    def test_original_one_percent_cap_blocks_everything(self):
        # Regression documentation: the protocol's literal 1% cap
        # blocks even a single min-risk position, proving the §11.4
        # scale amendment was necessary, not a retune.
        d = check_r6_per_symbol_risk_cap(
            symbol="EURUSD",
            current_symbol_risk_dollars=0.0,
            additional_risk_dollars=6.6,   # smallest stop seen post-V
            equity=SANDBOX_EQUITY_DOLLARS,
            cap_frac=0.01,
        )
        assert d.allowed is False
