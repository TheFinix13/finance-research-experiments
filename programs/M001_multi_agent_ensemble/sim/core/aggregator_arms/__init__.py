"""Phi5 aggregator arms package.

Each arm in the Phi5 selection experiment (`experiments/phi5_aggregator/
PROTOCOL.md`) is an independent strategy that composes with the base
per-symbol-highest-conviction rule. This package holds the mechanic-
specific code:

- `hrp` -- Arm 1: Hierarchical Risk Parity weighting from agent OOS-window
  TQS covariance, ported from production `agent/alphas/allocator.py`.
- `tqs_floor` -- Arm 2: per-agent P=0.40 percentile filter on conviction
  (Nagi-style low-n agents get a free pass below 200 historical trades).
- `same_direction_merge` -- Arm 3: merge N same-direction proposals per
  symbol into one intent (tightest SL, median TP, max conviction).
- `multi_position` -- Arm 4: admit up to K=2 concurrent positions per
  symbol subject to distinct agents + Sentinel R6 total-risk cap.
- `combined` -- Arm 5: stacked pipeline
  (TQS floor -> merge -> multi-position -> HRP) per PROTOCOL §3.6.

Arm 0 (control) is `_phi4_aggregate` in `sim/scoring/run_phi4_squad_gate.
py` and preserves the Phi4 / Phi4.1 behaviour verbatim -- this package
does NOT touch it.

Path deviation (§11.2 amendment 2026-06-30): PROTOCOL §7 planned
``sim/core/aggregator/`` as the package path, but the existing
``sim/core/aggregator.py`` (Phi2.5 stub, preserved per "DO NOT MODIFY"
directive) blocks that layout. This package is therefore at
``sim/core/aggregator_arms/`` instead; behaviour and locked parameters
are unchanged.
"""
from __future__ import annotations

from .combined import CombinedAggregator, CombinedDecision
from .hrp import (
    HRPAggregator,
    HRPWeightSnapshot,
    compute_hrp_weights,
)
from .multi_position import (
    Arm4Decision,
    MultiPositionAggregator,
    OpenPosition,
    admit_proposals,
)
from .same_direction_merge import apply_same_direction_merge
from .tqs_floor import (
    TQSFloorAggregator,
    TQSFloorDecision,
    apply_tqs_floor,
)

__all__ = [
    "Arm4Decision",
    "CombinedAggregator",
    "CombinedDecision",
    "HRPAggregator",
    "HRPWeightSnapshot",
    "MultiPositionAggregator",
    "OpenPosition",
    "TQSFloorAggregator",
    "TQSFloorDecision",
    "admit_proposals",
    "apply_same_direction_merge",
    "apply_tqs_floor",
    "compute_hrp_weights",
]
