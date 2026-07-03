"""Phase 5 -- Shadow-ledger -> HRP inputs adapter for Arm 1 re-sim.

The Phase 5 Arm 1 (Hierarchical Risk Parity, ``hrp.py``) covariance
matrix currently consumes per-OOS-window mean TQS scalars derived
from EXECUTED trades. Under the Phi4/Phi5 single-slot bottleneck,
most agents' executed trade counts are small (Rin, Nagi ~94 each),
which makes the per-window-mean-TQS statistic noisy and the
resulting cov matrix ill-conditioned. Amendment §11.3 to the Phi5
protocol (2026-07-01) formalises that Arm 1 needs an "honest re-
evaluation": arm mechanic unchanged, only the INPUT DISTRIBUTION
changes.

This module ships that input change. It converts a
``list[ShadowTradeRecord]`` (Phase U shadow ledger) into the same
shape ``compute_hrp_weights`` already expects, but derived from
EVERY proposal an agent made (accepted + rejected), so:

- per-agent per-window sample count grows ~5-10x (Phase-V post-
  amendment measurement: Bachira 82 -> 428 shadow trades on the
  post-V panel).
- covariance matrix is better conditioned (per-window means have
  smaller standard error).
- HRP weight decisions reflect the agent's underlying READ, not
  just how often the aggregator let them execute.

The alpha-attribution split (accepted vs rejected shadow-TQS) is
NOT applied here -- Amendment §11.3 says arm mechanic unchanged;
the caller who wants to slice by rejection_reason should pre-filter
the record list before passing it in.

## Contract

``compute_hrp_weights_from_shadow`` is a thin composition:

    shadow_records + windows
        -> per_agent_window_means_from_shadow (dict[str, list[float]])
        + per_agent_shadow_trade_counts     (dict[str, int])
        -> compute_hrp_weights (unchanged Arm 1 mechanic)
        -> HRPWeightSnapshot

All HRP tuning kwargs (``min_trades_per_agent``, ``shrinkage``,
``weight_cap``, ``jitter``, ``max_condition_number``) pass through
verbatim so the arm's parameter surface remains locked at the
Phi5-protocol values.

## Statistical-honesty guard

Shadow-ledger records include the systematic upward bias documented
in ``shadow_ledger.py`` §"Statistical honesty" (no R6 concentration
cap, no R4 correlation cap). Feeding raw shadow means into HRP
inherits that bias; callers who need bias correction should apply
it BEFORE calling this function (recommended: use
``shadow_ledger.aggregate_shadow_by_agent`` to compute the
executed-vs-rejected calibration ratio per agent, then rescale the
shadow means by ratio before this call).

Under the null-result reversion (Phase V-a + V-b), Chigiri/Barou
have no tier promotion, so the shadow-vs-executed calibration is
what it was on the post-F22 panel -- see G7 verdict registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal

import numpy as np

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms.hrp import (
    HRPWeightSnapshot,
    compute_hrp_weights,
)
from programs.M001_multi_agent_ensemble.sim.scoring.shadow_ledger import (
    ShadowTradeRecord,
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ShadowHrpMetric = Literal["tqs", "pnl_pips", "r_multiple"]
"""Which per-record scalar to average within each (agent, window) bucket.

- ``tqs``: composite Trade Quality Score from ``tqs_components['tqs']``.
  Default. Matches the axis the executed-trade HRP uses, so a shadow-
  vs-executed comparison is apples-to-apples.
- ``pnl_pips``: raw pip P&L. Useful for a lot-adjusted covariance
  when F19 variable-lot is wired (per Amendment §11.3 second half).
- ``r_multiple``: R-multiple (pnl / initial_risk). Van Tharp 1998.
  Scale-invariant across symbols; useful when the panel spans
  different pip-value symbols.
"""


@dataclass(frozen=True)
class WindowBoundary:
    """One OOS window's ``[start, end)`` interval.

    Windows are non-overlapping and chronologically ordered by
    ``window_index``. ``window_index`` is 0-based so ``windows[0]``
    is the earliest.
    """
    window_index: int
    start: datetime
    end: datetime


# ---------------------------------------------------------------------------
# Timestamp normalisation
# ---------------------------------------------------------------------------

def _entry_to_datetime(entry_time) -> datetime | None:
    """Coerce ``ShadowTradeRecord.entry_time`` (typed ``Any``) to a
    ``datetime``. Accepts:

    - Native ``datetime``.
    - Objects with a ``to_pydatetime`` method (pandas ``Timestamp``).
    - ISO 8601 strings.

    Returns ``None`` for anything else, which drops the record from
    all downstream buckets. Silent-drop is deliberate: shadow
    records with malformed timestamps are a data-quality signal, not
    a HRP-input concern.
    """
    if entry_time is None:
        return None
    if isinstance(entry_time, datetime):
        return entry_time
    to_py = getattr(entry_time, "to_pydatetime", None)
    if callable(to_py):
        try:
            result = to_py()
            if isinstance(result, datetime):
                return result
        except Exception:  # noqa: BLE001 -- pandas can raise generic Exception
            return None
    try:
        return datetime.fromisoformat(str(entry_time))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------

def bucket_shadow_by_agent_window(
    shadow_records: Iterable[ShadowTradeRecord],
    windows: list[WindowBoundary],
) -> dict[str, dict[int, list[ShadowTradeRecord]]]:
    """Group shadow trades into ``(agent_id, window_index)`` buckets.

    Records whose ``entry_time`` is unparseable or falls outside all
    provided window intervals are dropped. Bucket order preserves
    input order within each ``(agent, window)`` cell -- useful for
    deterministic downstream aggregation.
    """
    out: dict[str, dict[int, list[ShadowTradeRecord]]] = {}
    for r in shadow_records:
        et = _entry_to_datetime(r.entry_time)
        if et is None:
            continue
        # Linear scan; windows list is expected to be O(10) for M001
        # panels so an interval tree is overkill.
        idx: int | None = None
        for w in windows:
            if w.start <= et < w.end:
                idx = w.window_index
                break
        if idx is None:
            continue
        out.setdefault(r.agent_id, {}).setdefault(idx, []).append(r)
    return out


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def _extract_metric(
    r: ShadowTradeRecord, metric: ShadowHrpMetric,
) -> float:
    if metric == "tqs":
        return float(r.tqs_components.get("tqs", 0.0))
    if metric == "pnl_pips":
        return float(r.pnl_pips)
    if metric == "r_multiple":
        return float(r.r_multiple)
    raise ValueError(
        f"unknown metric {metric!r}; expected one of tqs/pnl_pips/r_multiple"
    )


# ---------------------------------------------------------------------------
# Per-agent window-mean series builder
# ---------------------------------------------------------------------------

def per_agent_window_means_from_shadow(
    shadow_records: Iterable[ShadowTradeRecord],
    windows: list[WindowBoundary],
    *,
    metric: ShadowHrpMetric = "tqs",
) -> dict[str, list[float]]:
    """Convert shadow trades into per-agent per-window mean series.

    Returns ``dict[agent_id -> list[float]]`` where the list is
    chronologically ordered and its length is the number of windows
    in which the agent has at least one shadow trade. Empty windows
    are SKIPPED (list has variable length across agents), matching
    the shape ``compute_hrp_weights`` accepts (it right-aligns the
    ``agents x windows`` matrix, zero-filling missing history).
    """
    buckets = bucket_shadow_by_agent_window(shadow_records, windows)
    out: dict[str, list[float]] = {}
    for aid, by_window in buckets.items():
        series: list[float] = []
        for w in windows:
            recs = by_window.get(w.window_index, [])
            if not recs:
                continue
            values = [_extract_metric(r, metric) for r in recs]
            series.append(float(np.mean(values)))
        if series:
            out[aid] = series
    return out


def per_agent_shadow_trade_counts(
    shadow_records: Iterable[ShadowTradeRecord],
) -> dict[str, int]:
    """Total shadow-trade count per agent across all windows.

    Consumed by ``compute_hrp_weights`` for the ``min_trades_per_agent``
    eligibility filter. Note this counts ALL shadow trades regardless
    of rejection_reason -- accepted shadow trades (which coincide
    with executed trades) are included by design so the filter has
    the same n as the shadow ledger itself.
    """
    counts: dict[str, int] = {}
    for r in shadow_records:
        counts[r.agent_id] = counts.get(r.agent_id, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Composed HRP entry point
# ---------------------------------------------------------------------------

def compute_hrp_weights_from_shadow(
    shadow_records: Iterable[ShadowTradeRecord],
    windows: list[WindowBoundary],
    *,
    window_start: datetime,
    window_end: datetime,
    metric: ShadowHrpMetric = "tqs",
    **hrp_kwargs,
) -> HRPWeightSnapshot:
    """Compose shadow-ledger inputs with the Phase 5 Arm 1 HRP function.

    Arm mechanic (``compute_hrp_weights``) is unchanged; only the
    input signal source changes from executed-trade window means to
    shadow-ledger window means. All HRP tuning kwargs
    (``min_trades_per_agent``, ``shrinkage``, ``weight_cap``,
    ``jitter``, ``max_condition_number``) pass through verbatim so
    the arm's parameter surface remains locked at the Phi5-protocol
    values.

    Parameters
    ----------
    shadow_records:
        The shadow ledger for the fit horizon. Typically
        ``ShadowTradeRecord`` list emitted by
        ``run_phi4_squad_gate._drive_squad_replay`` when
        ``use_shadow_ledger=True``.
    windows:
        OOS window boundaries covering the fit horizon. Typically 7
        windows for the Phi5 panel.
    window_start, window_end:
        Boundaries of the CURRENT window being fit (passed to the
        resulting ``HRPWeightSnapshot`` for provenance). NOT the same
        as ``windows`` above (which is the full lookback).
    metric:
        Which scalar to average within each ``(agent, window)``
        bucket. See ``ShadowHrpMetric``. Default ``tqs``.
    **hrp_kwargs:
        Passed verbatim to ``compute_hrp_weights``.
    """
    series_by_agent = per_agent_window_means_from_shadow(
        shadow_records, windows, metric=metric,
    )
    counts_by_agent = per_agent_shadow_trade_counts(shadow_records)
    return compute_hrp_weights(
        per_agent_window_tqs=series_by_agent,
        per_agent_trade_counts=counts_by_agent,
        window_start=window_start,
        window_end=window_end,
        **hrp_kwargs,
    )
