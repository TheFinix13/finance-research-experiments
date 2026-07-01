"""Arm 1 of the Phi5 aggregator experiment -- Hierarchical Risk Parity.

Ported from production ``agent/alphas/allocator.py`` (KEEP-AND-INHERIT per
``docs/audits/2026-06-24_unclear_resolutions.md``). See
``experiments/phi5_aggregator/HRP_NOTES.md`` for the design decisions
behind the changes below.

## Contract deltas from production

- **Score axis:** per-OOS-window mean TQS (F12) instead of daily pip P&L.
  Covariance is over ``agents x windows`` (n=7 windows on the Phi5 panel)
  rather than ``alphas x days``.
- **Min-N filter:** ``min_trades_per_agent = 30`` (trades, not days). Rin
  and Nagi are borderline at 94 trades each; the filter is generous
  enough to include both. Excluded agents get zero weight (no fallback
  bucket inclusion).
- **Weight cap:** ``weight_cap = 0.5`` (no agent > 50 % of the risk
  budget) prevents a single positive-TQS agent from dominating early.
- **Numerical jitter:** ``1e-7 * I`` on the covariance diagonal (vs
  production's ``1e-9``) -- small-n covariance is unstable; a wider
  jitter dampens the inverse.
- **Fallback:** if ``raw.sum() <= 0`` (no positive-edge combination),
  equal-weight over positive-TQS agents. If ALL agents have zero or
  negative mean TQS, equal-weight over ALL eligible agents (never NaN).

## Stateful adapter

Weights re-fit at OOS window boundaries (per Phi5 walk-forward cadence),
NOT per tick. ``HRPAggregator`` caches the current snapshot and exposes
``get_weight(agent_id)`` for the harness to consume when the aggregator
scores admission or computes conviction ranking.

The consumption semantic (multiply proposal conviction? scale pnl_pips?
scale a synthetic risk_scale?) is DECIDED BY THE CALLER -- this module
returns weights only. The Phi5 harness (Phase 6c) picks the semantic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


# ---------------------------------------------------------------------------
# Locked Arm 1 parameters (from experiments/phi5_aggregator/PROTOCOL.md §3.2)
# ---------------------------------------------------------------------------

HRP_LOOKBACK_WINDOWS = 3        # OOS windows of TQS history for covariance
HRP_SHRINKAGE = 0.2             # Ledoit-Wolf toward diagonal (matches prod)
HRP_MIN_TRADES_PER_AGENT = 30   # F6 minimum-n rule; excluded if below
HRP_WEIGHT_FLOOR = 0.0
HRP_WEIGHT_CAP = 0.5            # No agent gets > 50 % of risk budget
HRP_JITTER = 1e-7               # Small-n covariance stabiliser
HRP_MAX_CONDITION_NUMBER = 1e8  # Above this the tangency is unreliable ->
                                # fall back to equal-weight-on-positive-mean.
                                # Common with small-n low-variance TQS
                                # histories (e.g. clean synthetic replays).


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HRPWeightSnapshot:
    """Weights at a specific OOS window boundary.

    Immutable so callers can safely stash + compare across windows without
    mutation risk. ``weights`` sums to 1.0 (post-normalisation).
    """

    window_start: datetime
    window_end: datetime
    weights: dict[str, float]
    included_agents: list[str]
    excluded_agents: list[str]
    excluded_reasons: dict[str, str]
    fallback_triggered: bool
    fallback_reason: str
    condition_number: float

    def to_jsonable(self) -> dict:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "weights": {k: float(v) for k, v in self.weights.items()},
            "included_agents": list(self.included_agents),
            "excluded_agents": list(self.excluded_agents),
            "excluded_reasons": dict(self.excluded_reasons),
            "fallback_triggered": bool(self.fallback_triggered),
            "fallback_reason": self.fallback_reason,
            "condition_number": float(self.condition_number),
        }


# ---------------------------------------------------------------------------
# Pure-function core
# ---------------------------------------------------------------------------

def compute_hrp_weights(
    per_agent_window_tqs: dict[str, list[float]],
    per_agent_trade_counts: dict[str, int],
    *,
    window_start: datetime,
    window_end: datetime,
    min_trades_per_agent: int = HRP_MIN_TRADES_PER_AGENT,
    shrinkage: float = HRP_SHRINKAGE,
    weight_cap: float = HRP_WEIGHT_CAP,
    jitter: float = HRP_JITTER,
    max_condition_number: float = HRP_MAX_CONDITION_NUMBER,
) -> HRPWeightSnapshot:
    """Compute HRP allocation snapshot for a given OOS window boundary.

    Inputs
    ------
    per_agent_window_tqs : dict[agent_id -> list[float]]
        Per-agent history of *per-OOS-window mean TQS* values (one scalar
        per window, ordered chronologically). Length is the number of
        completed OOS windows available at this fit time; the Phi5 panel
        has 7 windows total, so at the third window this list has length
        2 for agents that traded in both prior windows.

    per_agent_trade_counts : dict[agent_id -> int]
        Total trade count for each agent across the history. Agents with
        counts below `min_trades_per_agent` are excluded.

    Returns
    -------
    HRPWeightSnapshot with normalised weights (sum = 1.0), agent inclusion
    lists, and diagnostic fields (condition number, fallback trigger).
    """
    # Eligibility filter -- min-trades gate.
    eligible = []
    excluded_reasons: dict[str, str] = {}
    for agent_id in per_agent_window_tqs:
        n_trades = per_agent_trade_counts.get(agent_id, 0)
        if n_trades < min_trades_per_agent:
            excluded_reasons[agent_id] = f"min_trades ({n_trades} < {min_trades_per_agent})"
            continue
        if not per_agent_window_tqs[agent_id]:
            excluded_reasons[agent_id] = "no_tqs_history"
            continue
        eligible.append(agent_id)

    excluded = [a for a in per_agent_window_tqs if a not in eligible]

    # Degenerate cases.
    if not eligible:
        return HRPWeightSnapshot(
            window_start=window_start,
            window_end=window_end,
            weights={},
            included_agents=[],
            excluded_agents=excluded,
            excluded_reasons=excluded_reasons,
            fallback_triggered=True,
            fallback_reason="no_eligible_agents",
            condition_number=float("inf"),
        )

    if len(eligible) == 1:
        # Single-agent degenerate: full weight to the survivor.
        aid = eligible[0]
        return HRPWeightSnapshot(
            window_start=window_start,
            window_end=window_end,
            weights={aid: 1.0},
            included_agents=[aid],
            excluded_agents=excluded,
            excluded_reasons=excluded_reasons,
            fallback_triggered=True,
            fallback_reason="singleton_eligible",
            condition_number=1.0,
        )

    # Build the agent x window matrix. Windows may have different lengths
    # across agents (an agent traded window 1+2 but not window 3). We
    # zero-fill for windows the agent didn't trade in, matching the
    # production allocator's zero-fill treatment.
    max_windows = max(len(per_agent_window_tqs[a]) for a in eligible)
    mat = np.zeros((len(eligible), max_windows), dtype=float)
    for i, aid in enumerate(eligible):
        series = per_agent_window_tqs[aid]
        # Right-align so the most recent windows are at the tail (chronological).
        mat[i, -len(series):] = series

    # Per-agent mean and covariance across windows.
    mu = mat.mean(axis=1)
    if max_windows < 2:
        # Not enough windows for a covariance; fallback to equal-weight on
        # positive-mean agents.
        return _fallback_equal_weight(
            eligible=eligible,
            mu=mu,
            weight_cap=weight_cap,
            window_start=window_start,
            window_end=window_end,
            excluded=excluded,
            excluded_reasons=excluded_reasons,
            reason="insufficient_windows_for_covariance",
        )

    cov = np.cov(mat, ddof=1)
    cov = np.atleast_2d(cov)

    # Ledoit-Wolf shrinkage toward diagonal + jitter for numerical solve.
    target = np.diag(np.diag(cov))
    cov_s = (1 - shrinkage) * cov + shrinkage * target
    cov_s = cov_s + np.eye(len(eligible)) * jitter

    condition_number = float(np.linalg.cond(cov_s))

    if condition_number > max_condition_number:
        # Covariance is effectively singular -- the tangency direction is
        # noise. Fall back rather than emit near-arbitrary weights.
        return _fallback_equal_weight(
            eligible=eligible,
            mu=mu,
            weight_cap=weight_cap,
            window_start=window_start,
            window_end=window_end,
            excluded=excluded,
            excluded_reasons=excluded_reasons,
            reason="ill_conditioned_covariance",
            condition_number=condition_number,
        )

    try:
        raw = np.linalg.solve(cov_s, mu)
    except np.linalg.LinAlgError:
        raw = mu.copy()

    # Long-only clip.
    raw = np.clip(raw, 0.0, None)

    if raw.sum() <= 0:
        # No positive-edge tangency -- production fallback path.
        return _fallback_equal_weight(
            eligible=eligible,
            mu=mu,
            weight_cap=weight_cap,
            window_start=window_start,
            window_end=window_end,
            excluded=excluded,
            excluded_reasons=excluded_reasons,
            reason="no_positive_edge_tangency",
            condition_number=condition_number,
        )

    weights_arr = raw / raw.sum()

    # Apply weight cap (production has no cap; M001 adds this).
    weights_arr = _apply_weight_cap(weights_arr, weight_cap)

    weights = {aid: float(w) for aid, w in zip(eligible, weights_arr)}

    return HRPWeightSnapshot(
        window_start=window_start,
        window_end=window_end,
        weights=weights,
        included_agents=list(eligible),
        excluded_agents=excluded,
        excluded_reasons=excluded_reasons,
        fallback_triggered=False,
        fallback_reason="",
        condition_number=condition_number,
    )


def _fallback_equal_weight(
    *,
    eligible: list[str],
    mu: np.ndarray,
    weight_cap: float,
    window_start: datetime,
    window_end: datetime,
    excluded: list[str],
    excluded_reasons: dict[str, str],
    reason: str,
    condition_number: float = float("inf"),
) -> HRPWeightSnapshot:
    """Production-matched fallback: equal-weight over positive-mean agents,
    else equal-weight over all eligible agents. Never returns NaN."""
    positive_mask = mu > 0
    if positive_mask.any():
        raw = positive_mask.astype(float)
    else:
        raw = np.ones(len(eligible))
    weights_arr = raw / raw.sum()
    weights_arr = _apply_weight_cap(weights_arr, weight_cap)
    weights = {aid: float(w) for aid, w in zip(eligible, weights_arr)}
    return HRPWeightSnapshot(
        window_start=window_start,
        window_end=window_end,
        weights=weights,
        included_agents=list(eligible),
        excluded_agents=excluded,
        excluded_reasons=excluded_reasons,
        fallback_triggered=True,
        fallback_reason=reason,
        condition_number=condition_number,
    )


def _apply_weight_cap(weights: np.ndarray, cap: float) -> np.ndarray:
    """Cap each weight at ``cap`` and redistribute the excess proportionally.

    Iterative because a single pass can push previously-uncapped weights
    above the cap after redistribution.
    """
    if cap >= 1.0 or weights.sum() <= 0:
        return weights
    w = weights.astype(float).copy()
    for _ in range(20):    # bounded loop; typically converges in 2-3 iters
        excess_mask = w > cap
        if not excess_mask.any():
            break
        excess = (w[excess_mask] - cap).sum()
        w[excess_mask] = cap
        uncapped = ~excess_mask
        uncapped_sum = w[uncapped].sum()
        if uncapped_sum <= 0:
            break
        w[uncapped] += excess * (w[uncapped] / uncapped_sum)
    # Renormalise (cap-and-redistribute preserves sum in theory but
    # floating-point drift is possible).
    total = w.sum()
    if total > 0:
        w = w / total
    return w


# ---------------------------------------------------------------------------
# Stateful adapter
# ---------------------------------------------------------------------------

@dataclass
class HRPAggregator:
    """Stateful HRP adapter refitting at OOS-window boundaries.

    Usage (from the Phi5 harness):

        hrp = HRPAggregator()
        for window in windows:
            snap = hrp.refit(
                per_agent_window_tqs=<TQS history up to this window>,
                per_agent_trade_counts=<counts up to this window>,
                window_start=window.oos_start, window_end=window.oos_end,
            )
            # Consume snap.weights during the window's tick loop.
    """

    min_trades_per_agent: int = HRP_MIN_TRADES_PER_AGENT
    shrinkage: float = HRP_SHRINKAGE
    weight_cap: float = HRP_WEIGHT_CAP
    jitter: float = HRP_JITTER
    current_snapshot: HRPWeightSnapshot | None = None
    history: list[HRPWeightSnapshot] = field(default_factory=list)

    def refit(
        self,
        per_agent_window_tqs: dict[str, list[float]],
        per_agent_trade_counts: dict[str, int],
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> HRPWeightSnapshot:
        snap = compute_hrp_weights(
            per_agent_window_tqs=per_agent_window_tqs,
            per_agent_trade_counts=per_agent_trade_counts,
            window_start=window_start,
            window_end=window_end,
            min_trades_per_agent=self.min_trades_per_agent,
            shrinkage=self.shrinkage,
            weight_cap=self.weight_cap,
            jitter=self.jitter,
        )
        self.current_snapshot = snap
        self.history.append(snap)
        return snap

    def get_weight(self, agent_id: str, *, default: float = 0.0) -> float:
        """Return the agent's current HRP weight, or ``default`` if missing."""
        if self.current_snapshot is None:
            return default
        return self.current_snapshot.weights.get(agent_id, default)

    @property
    def has_snapshot(self) -> bool:
        return self.current_snapshot is not None
