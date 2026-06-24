"""F18 — Regime-conditional KPI buckets.

Foundations F18 + research-standards section 4.3. Every per-agent KPI
from doctrine section 3.6 is reported **per regime**, not pooled.

Regime taxonomy: `trending`, `chop`, `vol_spike`, `news`.

Aggregation rules (matches the doctrine's pooled aggregations):

| KPI               | Aggregation     |
|-------------------|-----------------|
| TQS               | median          |
| assertion_rate    | count-ratio     |
| coexistence_rate  | count-ratio     |
| devour_rate       | count-ratio     |
| goal_rate         | count-ratio     |
| beauty_rate       | mean            |
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

import numpy as np

RegimeLabel = Literal["trending", "chop", "vol_spike", "news"]
REGIMES: tuple[RegimeLabel, ...] = ("trending", "chop", "vol_spike", "news")


@dataclass(frozen=True)
class TradeRow:
    """One closed trade — the minimal F18 input row.

    `regime` is the regime label at *entry bar* time (foundations
    F18). Tied multi-labels are pre-resolved upstream by the
    classifier per F18 priority.
    """

    agent_id: str
    regime: RegimeLabel
    tqs: float
    is_proposal_emitted: bool = True
    is_order_taken: bool = True
    is_confluence_participation: bool = False
    is_collision_win: bool = False
    is_collision: bool = False
    is_profitable: bool = False


@dataclass(frozen=True)
class RegimeKPI:
    """Per-(agent, regime) KPI vector emitted by `compute_regime_kpis`."""

    agent_id: str
    regime: RegimeLabel
    n: int
    median_tqs: float
    assertion_rate: float
    coexistence_rate: float
    devour_rate: float
    goal_rate: float
    beauty_rate: float

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "regime": self.regime,
            "n": int(self.n),
            "median_tqs": float(self.median_tqs),
            "assertion_rate": float(self.assertion_rate),
            "coexistence_rate": float(self.coexistence_rate),
            "devour_rate": float(self.devour_rate),
            "goal_rate": float(self.goal_rate),
            "beauty_rate": float(self.beauty_rate),
        }


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den > 0 else 0.0


def compute_regime_kpis(rows: Iterable[TradeRow]) -> list[RegimeKPI]:
    """Group trade rows by (agent, regime) and emit one KPI per group."""
    grouped: dict[tuple[str, RegimeLabel], list[TradeRow]] = defaultdict(list)
    for r in rows:
        if r.regime not in REGIMES:
            continue
        grouped[(r.agent_id, r.regime)].append(r)

    out: list[RegimeKPI] = []
    for (agent_id, regime), bucket in grouped.items():
        n = len(bucket)
        if n == 0:
            continue
        tqs_vec = np.array([t.tqs for t in bucket], dtype=float)
        n_proposals = sum(1 for t in bucket if t.is_proposal_emitted)
        n_orders = sum(1 for t in bucket if t.is_order_taken)
        n_confluence = sum(1 for t in bucket if t.is_confluence_participation)
        n_collisions = sum(1 for t in bucket if t.is_collision)
        n_collision_wins = sum(1 for t in bucket if t.is_collision_win)
        n_wins = sum(1 for t in bucket if t.is_profitable)
        out.append(RegimeKPI(
            agent_id=agent_id,
            regime=regime,
            n=int(n),
            median_tqs=float(np.median(tqs_vec)) if n else 0.0,
            assertion_rate=_safe_div(n_orders, n_proposals),
            coexistence_rate=_safe_div(n_confluence, n_proposals),
            devour_rate=_safe_div(n_collision_wins, n_collisions),
            goal_rate=_safe_div(n_wins, n_orders),
            beauty_rate=float(tqs_vec.mean()) if n else 0.0,
        ))
    return out


def bucket_dominance(
    kpis: Sequence[RegimeKPI],
    *,
    ratio: float = 1.5,
    n_floor: int = 30,
) -> tuple[RegimeLabel | None, float]:
    """Per F18 'dominated-by-one-bucket' rule.

    Returns `(dominant_regime, ratio_to_runner_up)` if the agent's
    top regime is at least ``ratio`` times the second-best AND has
    n >= ``n_floor`` trades. Otherwise `(None, 0.0)`.
    """
    eligible = [k for k in kpis if k.n >= n_floor]
    if not eligible:
        return None, 0.0
    sorted_by_tqs = sorted(eligible, key=lambda k: k.median_tqs, reverse=True)
    if len(sorted_by_tqs) == 1:
        return sorted_by_tqs[0].regime, float("inf")
    top, runner = sorted_by_tqs[0], sorted_by_tqs[1]
    if runner.median_tqs <= 0:
        # Avoid division by zero/negatives; treat as dominance.
        return (top.regime, float("inf")) if top.median_tqs > 0 else (None, 0.0)
    ratio_observed = top.median_tqs / runner.median_tqs
    if ratio_observed >= ratio:
        return top.regime, float(ratio_observed)
    return None, float(ratio_observed)
