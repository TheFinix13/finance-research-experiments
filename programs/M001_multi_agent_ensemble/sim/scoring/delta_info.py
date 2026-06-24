"""F17 — Marginal information value of inter-agent observability (DeltaInfo).

Doctrine `06-blue-lock-doctrine.md` section 3.9 + foundations F17 in
`04-quant-foundations.md`.

    DeltaInfo(agent_i) = median(TQS | full ledger) - median(TQS | isolated)

Tier assignment rule:
    * DeltaInfo > 0 AND bootstrap lower bound > 0  -> Tier 2 (informed)
    * Else                                          -> Tier 3 (isolated)

The bootstrap is **pairwise block** (block size = 5 trades) to absorb
the agent's own autocorrelation. Sample-size floor: 30 trades per arm
(F17 + F6 DSR floor).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class DeltaInfoResult:
    """Output of `delta_info` — point estimate + CI + tier assignment."""

    agent_id: str
    n_informed: int
    n_isolated: int
    median_informed: float
    median_isolated: float
    delta_info: float
    ci_low: float
    ci_high: float
    tier: int                    # 2 or 3 (Tier 1 is non-agent consumers)
    significant: bool

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "n_informed": int(self.n_informed),
            "n_isolated": int(self.n_isolated),
            "median_informed": float(self.median_informed),
            "median_isolated": float(self.median_isolated),
            "delta_info": float(self.delta_info),
            "ci_low": float(self.ci_low),
            "ci_high": float(self.ci_high),
            "tier": int(self.tier),
            "significant": bool(self.significant),
        }


def _block_bootstrap_medians(
    arr: np.ndarray,
    *,
    block_size: int,
    n_resamples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Pairwise-block bootstrap of the median (F17 procedure)."""
    n = len(arr)
    if n == 0:
        return np.array([])
    n_blocks = max(1, n // block_size)
    out = np.empty(n_resamples)
    for i in range(n_resamples):
        # Sample blocks with replacement.
        starts = rng.integers(0, max(1, n - block_size + 1), size=n_blocks)
        sample = np.concatenate(
            [arr[s:s + block_size] for s in starts]
        )[:n]
        out[i] = float(np.median(sample))
    return out


def delta_info(
    agent_id: str,
    tqs_informed: Sequence[float],
    tqs_isolated: Sequence[float],
    *,
    n_resamples: int = 2000,
    block_size: int = 5,
    alpha: float = 0.05,
    n_floor: int = 30,
    seed: int = 1729,
) -> DeltaInfoResult:
    """Compute F17 DeltaInfo with a pairwise-block bootstrap CI.

    Returns a `DeltaInfoResult` carrying the tier assignment per the
    F17 rule. If either arm has fewer than `n_floor` trades, the
    tier defaults to 3 (information-isolated) and `significant=False`.
    """
    informed = np.asarray(tqs_informed, dtype=float)
    isolated = np.asarray(tqs_isolated, dtype=float)
    rng = np.random.default_rng(seed)

    if len(informed) < n_floor or len(isolated) < n_floor:
        return DeltaInfoResult(
            agent_id=agent_id,
            n_informed=len(informed),
            n_isolated=len(isolated),
            median_informed=float(np.median(informed)) if len(informed) else 0.0,
            median_isolated=float(np.median(isolated)) if len(isolated) else 0.0,
            delta_info=0.0,
            ci_low=0.0,
            ci_high=0.0,
            tier=3,
            significant=False,
        )

    med_i = float(np.median(informed))
    med_o = float(np.median(isolated))
    point = med_i - med_o

    boot_i = _block_bootstrap_medians(
        informed, block_size=block_size, n_resamples=n_resamples, rng=rng,
    )
    boot_o = _block_bootstrap_medians(
        isolated, block_size=block_size, n_resamples=n_resamples, rng=rng,
    )
    diffs = boot_i - boot_o
    lo = float(np.quantile(diffs, alpha / 2.0))
    hi = float(np.quantile(diffs, 1 - alpha / 2.0))
    significant = (point > 0.0) and (lo > 0.0)
    tier = 2 if significant else 3
    return DeltaInfoResult(
        agent_id=agent_id,
        n_informed=len(informed),
        n_isolated=len(isolated),
        median_informed=med_i,
        median_isolated=med_o,
        delta_info=point,
        ci_low=lo,
        ci_high=hi,
        tier=tier,
        significant=significant,
    )
