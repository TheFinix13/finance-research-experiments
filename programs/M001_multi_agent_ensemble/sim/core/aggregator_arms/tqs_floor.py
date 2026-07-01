"""Arm 2 of the Phi5 aggregator experiment -- TQS-conditional conviction floor.

Filters proposals whose conviction falls below the ``P`` = 0.40 quantile of the
agent's historical conviction distribution. Agents with fewer than
``min_n_for_floor`` = 200 historical OOS trades get a free pass (Nagi is
the canonical low-n case with 94 Phi4.1 trades).

Conviction is the pre-trade proxy for TQS (F12). The PROTOCOL phrases the
mechanic as "per-agent historical OOS TQS percentile P" but pre-trade
we only have conviction; the harness (Phase 6c) must map post-trade TQS
back to conviction quantiles when it builds the historical distributions.

Reference: `experiments/phi5_aggregator/PROTOCOL.md` §3.2 Arm 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from ..types import AgentProposal


ARM2_PERCENTILE_P = 0.40
ARM2_MIN_N_FOR_FLOOR = 200


@dataclass(frozen=True)
class TQSFloorDecision:
    """Per-proposal admission decision emitted by ``apply_tqs_floor``."""

    proposal: AgentProposal
    admitted: bool
    reason: str
    p40_conviction: float | None  # None -> free pass; agent below min_n
    n_history: int


def _p40(history: list[float], p: float) -> float:
    """Numpy quantile with linear interpolation."""
    if not history:
        return 0.0
    arr = np.asarray(history, dtype=float)
    return float(np.quantile(arr, p))


def apply_tqs_floor(
    proposals: Iterable[AgentProposal],
    *,
    per_agent_conviction_history: dict[str, list[float]],
    per_agent_trade_counts: dict[str, int],
    p: float = ARM2_PERCENTILE_P,
    min_n_for_floor: int = ARM2_MIN_N_FOR_FLOOR,
) -> tuple[list[AgentProposal], list[TQSFloorDecision]]:
    """Filter proposals below per-agent P-quantile of historical conviction.

    Inputs
    ------
    proposals : iterable of AgentProposal
        Candidate proposals for this tick.

    per_agent_conviction_history : dict[agent_id -> list[float]]
        Historical convictions for each agent from prior OOS windows. Used
        to derive the per-agent P-quantile threshold. The harness (Phase
        6c) populates this walk-forward -- at OOS window W, this dict
        contains agents' conviction values from windows 1..W-1.

    per_agent_trade_counts : dict[agent_id -> int]
        Total historical trade count. Agents below `min_n_for_floor` are
        exempt (free pass) to avoid over-filtering low-n high-TQS agents
        (Nagi's Phi4.1 case: 94 trades).

    Returns
    -------
    (admitted, decisions)
        admitted -- proposals that pass the floor.
        decisions -- per-proposal audit trail (all inputs, including filtered).
    """
    admitted: list[AgentProposal] = []
    decisions: list[TQSFloorDecision] = []
    for prop in proposals:
        if prop is None or prop.direction == "flat":
            continue
        aid = prop.agent_id
        n_hist = per_agent_trade_counts.get(aid, 0)
        history = per_agent_conviction_history.get(aid, [])
        if n_hist < min_n_for_floor:
            decisions.append(TQSFloorDecision(
                proposal=prop, admitted=True,
                reason=f"free_pass_below_min_n({n_hist}<{min_n_for_floor})",
                p40_conviction=None, n_history=n_hist,
            ))
            admitted.append(prop)
            continue
        threshold = _p40(history, p)
        if prop.conviction >= threshold:
            decisions.append(TQSFloorDecision(
                proposal=prop, admitted=True,
                reason=f"conviction_ge_p{int(p*100)}",
                p40_conviction=threshold, n_history=n_hist,
            ))
            admitted.append(prop)
        else:
            decisions.append(TQSFloorDecision(
                proposal=prop, admitted=False,
                reason=f"conviction_below_p{int(p*100)}",
                p40_conviction=threshold, n_history=n_hist,
            ))
    return admitted, decisions


@dataclass
class TQSFloorAggregator:
    """Stateful adapter -- accumulates history and applies the floor.

    The harness updates the history at each OOS window boundary via
    ``update_history`` (walk-forward) then calls ``filter`` per tick.
    """

    p: float = ARM2_PERCENTILE_P
    min_n_for_floor: int = ARM2_MIN_N_FOR_FLOOR
    per_agent_conviction_history: dict[str, list[float]] = field(default_factory=dict)
    per_agent_trade_counts: dict[str, int] = field(default_factory=dict)

    def update_history(
        self,
        agent_id: str,
        convictions: Iterable[float],
    ) -> None:
        """Append (do not replace) an agent's conviction history."""
        vals = [float(v) for v in convictions]
        self.per_agent_conviction_history.setdefault(agent_id, []).extend(vals)
        self.per_agent_trade_counts[agent_id] = (
            self.per_agent_trade_counts.get(agent_id, 0) + len(vals)
        )

    def filter(
        self, proposals: Iterable[AgentProposal],
    ) -> tuple[list[AgentProposal], list[TQSFloorDecision]]:
        return apply_tqs_floor(
            proposals,
            per_agent_conviction_history=self.per_agent_conviction_history,
            per_agent_trade_counts=self.per_agent_trade_counts,
            p=self.p,
            min_n_for_floor=self.min_n_for_floor,
        )
