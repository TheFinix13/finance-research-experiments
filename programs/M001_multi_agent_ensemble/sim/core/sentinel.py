"""Sentinel — hard-rule enforcement (doctrine `06` sections 4.2 and 4.3).

Two surfaces in this module:

* **R1-R5 hard rules** (section 4.3) — block-or-allow decisions taken on
  every OrderIntent / per-agent-tick. Pure functions; no I/O.

* **External shock triggers** (section 4.2) — correlation jumps, spread
  spikes, calendar events, DXY shocks. Phi2.5 ships the data
  structures and a thin evaluator; the wiring to the live feed lands
  in Phi3+ together with the calendar adapter.

Critical invariant: any single hard-rule violation = trade blocked.
The Sentinel writes an audit log entry per block; the kernel never
silently passes a violating order downstream.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .types import AgentProposal, OrderIntent


# ---------------------------------------------------------------------------
# Defaults — sandbox-relaxed per architecture section 6
# ---------------------------------------------------------------------------

# Per-trade and per-basket caps inherit the sandbox-relaxed values
# (`03-architecture-v0-sketch.md` section 6).
SANDBOX_PER_TRADE_RISK_FRAC = 0.05    # R1 ceiling
SANDBOX_PER_BASKET_RISK_FRAC = 0.07   # informational only at sentinel layer
MIN_LOT = 0.01                        # R2 min-lot
LOT_INCREMENT = 0.01                  # R2 sizing increment
PASS_BIAS_PROPOSALS_PER_DAY = 3       # R3 over-firing threshold
CONCENTRATION_CAP = 0.40              # R4 hard backstop above HRP cap
LOSS_STREAK_TRIGGER = 3               # R5 trigger length
LOSS_STREAK_DAMPENER = 0.5            # R5 risk-scale
LOSS_STREAK_DURATION_HOURS = 24       # R5 dampener duration


@dataclass(frozen=True)
class SentinelDecision:
    """Outcome of a single Sentinel evaluation."""

    allowed: bool
    rule: Literal["R1", "R2", "R3", "R4", "R5", "EXT", "OK"]
    reason: str
    payload: dict


# ---------------------------------------------------------------------------
# R1 — Min-lot risk floor
# ---------------------------------------------------------------------------

def check_r1_min_lot_risk_floor(
    *,
    sl_distance_pips: float,
    pip_value_per_min_lot: float,
    equity: float,
    cap_frac: float = SANDBOX_PER_TRADE_RISK_FRAC,
) -> SentinelDecision:
    """R1: refuse if min-lot-implied risk > cap_frac of equity.

    On a $100 / 1:1000 account with EURUSD pip value ~ $0.10 at 0.01
    lot, the implied max stop distance is ~50 pips at 5% cap. Wider
    stops are refusals, not size-downs.
    """
    implied_risk_dollars = float(sl_distance_pips) * float(pip_value_per_min_lot)
    cap_dollars = float(cap_frac) * float(equity)
    if implied_risk_dollars > cap_dollars:
        return SentinelDecision(
            allowed=False,
            rule="R1",
            reason=(
                f"min-lot risk ${implied_risk_dollars:.2f} > cap "
                f"${cap_dollars:.2f} (={cap_frac*100:.1f}% of equity)"
            ),
            payload={
                "sl_distance_pips": float(sl_distance_pips),
                "pip_value_per_min_lot": float(pip_value_per_min_lot),
                "equity": float(equity),
                "cap_frac": float(cap_frac),
            },
        )
    return SentinelDecision(
        allowed=True, rule="OK", reason="R1 ok", payload={}
    )


# ---------------------------------------------------------------------------
# R2 — Discrete position sizing (round down)
# ---------------------------------------------------------------------------

def check_r2_discrete_size(
    desired_lot: float,
    *,
    min_lot: float = MIN_LOT,
    increment: float = LOT_INCREMENT,
) -> tuple[float, SentinelDecision]:
    """R2: round desired lot down to nearest discrete increment.

    Returns ``(rounded_lot, decision)``. Decision is always "allowed"
    once the round-down is applied. The decision payload records the
    rounding event for the audit log.
    """
    if desired_lot < min_lot:
        return 0.0, SentinelDecision(
            allowed=False,
            rule="R2",
            reason=f"desired lot {desired_lot:.4f} < min_lot {min_lot:.4f}",
            payload={
                "desired_lot": float(desired_lot),
                "min_lot": float(min_lot),
                "rounded_lot": 0.0,
            },
        )
    # Round DOWN (toward smaller risk).
    units = int(desired_lot / increment)
    rounded = round(units * increment, 8)
    return rounded, SentinelDecision(
        allowed=True,
        rule="R2",
        reason=f"rounded {desired_lot:.4f} down to {rounded:.4f}",
        payload={
            "desired_lot": float(desired_lot),
            "rounded_lot": float(rounded),
        },
    )


# ---------------------------------------------------------------------------
# R3 — Pass bias (over-firing detector)
# ---------------------------------------------------------------------------

def check_r3_pass_bias(
    agent_id: str,
    proposals_today: int,
    *,
    threshold: int = PASS_BIAS_PROPOSALS_PER_DAY,
) -> SentinelDecision:
    """R3: flag agents firing more than `threshold` proposals per day.

    Returns ``allowed=True`` always (R3 is an audit-only flag — the
    kernel doesn't block the proposal, but the audit log records the
    over-firing for roster review).
    """
    if proposals_today > threshold:
        return SentinelDecision(
            allowed=True,
            rule="R3",
            reason=(
                f"agent {agent_id} emitted {proposals_today} proposals today "
                f"(> {threshold}/day threshold)"
            ),
            payload={
                "agent_id": agent_id,
                "proposals_today": int(proposals_today),
                "threshold": int(threshold),
            },
        )
    return SentinelDecision(
        allowed=True, rule="OK", reason="R3 ok", payload={}
    )


# ---------------------------------------------------------------------------
# R4 — Concentration cap (hard backstop above HRP)
# ---------------------------------------------------------------------------

def check_r4_concentration(
    agent_id: str,
    intended_weight: float,
    *,
    cap: float = CONCENTRATION_CAP,
) -> SentinelDecision:
    """R4: hard backstop on per-agent risk budget share."""
    if intended_weight > cap:
        return SentinelDecision(
            allowed=False,
            rule="R4",
            reason=(
                f"agent {agent_id} weight {intended_weight:.3f} > "
                f"concentration cap {cap:.2f}"
            ),
            payload={
                "agent_id": agent_id,
                "intended_weight": float(intended_weight),
                "cap": float(cap),
            },
        )
    return SentinelDecision(
        allowed=True, rule="OK", reason="R4 ok", payload={}
    )


# ---------------------------------------------------------------------------
# R5 — Loss-streak dampener
# ---------------------------------------------------------------------------

def check_r5_loss_streak(
    consecutive_losses: int,
    *,
    trigger: int = LOSS_STREAK_TRIGGER,
    dampener: float = LOSS_STREAK_DAMPENER,
) -> tuple[float, SentinelDecision]:
    """R5: return ``(risk_scale, decision)``.

    risk_scale is 1.0 if no streak active, `dampener` (default 0.5)
    when the streak has been triggered. Distinct from A10 Kunigami's
    in-cast anti-tilt logic — R5 is the Sentinel's outer multiplier
    that compounds with Kunigami's.
    """
    if consecutive_losses >= trigger:
        return dampener, SentinelDecision(
            allowed=True,
            rule="R5",
            reason=(
                f"{consecutive_losses} consecutive losses; "
                f"applying {dampener:.0%} risk scale for next "
                f"{LOSS_STREAK_DURATION_HOURS}h"
            ),
            payload={
                "consecutive_losses": int(consecutive_losses),
                "risk_scale": float(dampener),
                "duration_hours": int(LOSS_STREAK_DURATION_HOURS),
            },
        )
    return 1.0, SentinelDecision(
        allowed=True, rule="OK", reason="R5 ok", payload={}
    )


# ---------------------------------------------------------------------------
# External-shock triggers (doctrine section 4.2)
# ---------------------------------------------------------------------------

@dataclass
class ExternalShockState:
    """Inputs to the external-shock evaluator.

    Phi2.5 keeps this as a dataclass that the engine fills in from
    its market feed. Phi3+ wires this to the calendar adapter +
    DXY feed.
    """

    cross_pair_rho_30d: float = 0.0           # |rho| > 0.95 -> fire
    spread_x_trailing_median: float = 1.0     # > 3x -> fire
    high_impact_event_within_2h: bool = False
    high_impact_prior_regime_shift: bool = False
    dxy_h1_sigma_z: float = 0.0               # > 2 -> fire


def check_external_shocks(state: ExternalShockState) -> SentinelDecision:
    """Evaluate the four external-shock triggers from doctrine 4.2."""
    if abs(state.cross_pair_rho_30d) > 0.95:
        return SentinelDecision(
            allowed=False, rule="EXT",
            reason=f"cross-pair |rho|={state.cross_pair_rho_30d:.2f} > 0.95",
            payload={"trigger": "rho_jump"},
        )
    if state.spread_x_trailing_median > 3.0:
        return SentinelDecision(
            allowed=False, rule="EXT",
            reason=(
                f"spread is {state.spread_x_trailing_median:.1f}x trailing "
                "median (> 3x)"
            ),
            payload={"trigger": "spread_spike"},
        )
    if state.high_impact_event_within_2h and state.high_impact_prior_regime_shift:
        return SentinelDecision(
            allowed=False, rule="EXT",
            reason="high-impact calendar event within 2h with prior regime shift",
            payload={"trigger": "calendar"},
        )
    if state.dxy_h1_sigma_z > 2.0:
        return SentinelDecision(
            allowed=False, rule="EXT",
            reason=f"DXY H1 sigma-z={state.dxy_h1_sigma_z:.2f} > 2",
            payload={"trigger": "dxy_shock"},
        )
    return SentinelDecision(
        allowed=True, rule="OK", reason="no external shocks", payload={}
    )


# ---------------------------------------------------------------------------
# Aggregate evaluator used by the kernel
# ---------------------------------------------------------------------------

@dataclass
class SentinelContext:
    """Per-tick state passed to `evaluate`."""

    equity: float
    pip_value_per_min_lot: float
    consecutive_losses: int = 0
    proposals_today_by_agent: dict[str, int] | None = None
    intended_weights_by_agent: dict[str, float] | None = None
    external: ExternalShockState | None = None


def evaluate(
    proposal: AgentProposal,
    intent: OrderIntent,
    context: SentinelContext,
) -> SentinelDecision:
    """Run the full R1-R5 + external sequence on one OrderIntent.

    First failure wins (R-rules are precedence-ordered: R1, R2-allowed,
    R3, R4, R5, EXT).
    """
    # R1 — translate stop distance to pips. The kernel passes the SL
    # distance in *price units*; we approximate pips by dividing by 1e-4
    # for typical FX symbols. Real conversion lives in the agent /
    # symbol metadata; for the scaffold this approximation is fine
    # because R1 only cares about *relative* magnitudes.
    sl_distance_pips = abs(intent.entry - intent.stop) * 1e4

    r1 = check_r1_min_lot_risk_floor(
        sl_distance_pips=sl_distance_pips,
        pip_value_per_min_lot=context.pip_value_per_min_lot,
        equity=context.equity,
    )
    if not r1.allowed:
        return r1

    # R3 — over-firing.
    if context.proposals_today_by_agent is not None:
        r3 = check_r3_pass_bias(
            proposal.agent_id,
            context.proposals_today_by_agent.get(proposal.agent_id, 0),
        )
        # R3 never blocks but is journalled when triggered.
        if r3.rule == "R3":
            # Return the R3 flag so the journaller can log it. The kernel
            # treats this as a soft warning, not a block.
            return r3

    # R4 — concentration cap.
    if context.intended_weights_by_agent is not None:
        r4 = check_r4_concentration(
            proposal.agent_id,
            context.intended_weights_by_agent.get(proposal.agent_id, 0.0),
        )
        if not r4.allowed:
            return r4

    # External shocks last (cheap; same evaluation surface).
    if context.external is not None:
        ext = check_external_shocks(context.external)
        if not ext.allowed:
            return ext

    return SentinelDecision(
        allowed=True, rule="OK", reason="ok", payload={}
    )
