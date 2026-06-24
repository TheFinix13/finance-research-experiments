"""Scoring + evaluation harness.

* `tqs` — F12 Trade Quality Score (the doctrine's fitness function).
* `delta_info` — F17 marginal information value (Tier-2 vs Tier-3 decider).
* `regime_kpis` — F18 regime-conditional KPI buckets.
"""
from .tqs import TQSComponents, compute_tqs  # noqa: F401
