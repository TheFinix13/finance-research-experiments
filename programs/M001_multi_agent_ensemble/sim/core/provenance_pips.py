"""Shared per-agent provenance helpers (F19/F20 dispersion inputs).

Phase P (2026-07-01, doctrine amendment "provenance-pips") adds two
functions that every agent's ``intend()`` can call to stamp real
``atr_pips`` and ``h1_swing_pips`` values on its ``proposal.rationale``
dict. These are consumed at trade-open time via
``_annotate_trade_record`` in ``run_phi4_squad_gate.py`` and flow into
``TradeRecord.source_atr_pips`` / ``TradeRecord.source_h1_swing_pips``,
which the G7 C6 evaluator (``_evaluate_criterion_6``) uses to compute
per-agent risk-shape dispersion.

Design:

- Zero external dependencies (stdlib only).
- Pure functions: no I/O, no logging.
- Robust to short bar histories: return ``None`` when the requested
  window is not available (never NaN, never a mis-scaled float).
- H1 swing is approximated by the H4 lookback high-low range for
  agents that don't have H1 bar access -- honest proxy, not a fake H1
  fetch. Agents whose home_tf IS H1 can call ``swing_pips_from_bars``
  directly on their H1 series.

Doctrine reference: 06-blue-lock-doctrine.md sec 4.1a (v1 chemistry
primitives -- F20 risk-intent inputs).
"""
from __future__ import annotations

from typing import Any


# Standard pip size for the majors we currently trade. Callers should
# pass their own pip_size for exotic instruments.
DEFAULT_PIP_SIZE_MAJOR: float = 1e-4


def atr_pips_at(
    bars: list[Any],
    i: int,
    *,
    period: int = 14,
    pip_size: float = DEFAULT_PIP_SIZE_MAJOR,
) -> float | None:
    """Wilder-smoothed ATR(``period``) at bar index ``i``, expressed in pips.

    Uses the classic Wilder smoothing (alpha = 1/period, no adjust).
    Returns ``None`` when ``i`` is outside the settled window (fewer
    than ``period`` bars of history available).

    ``bars`` must be a list of bar-like objects with ``.high``, ``.low``,
    ``.close`` attributes (production ``Bar`` or a dataclass shim both
    work).
    """
    if i < period - 1 or i >= len(bars):
        return None
    # True-range series over the settled window.
    tr: list[float] = []
    for k in range(max(0, i - period), i + 1):
        h = float(bars[k].high)
        lo = float(bars[k].low)
        if k == 0:
            tr.append(h - lo)
            continue
        pc = float(bars[k - 1].close)
        tr.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    # Wilder smoothing bootstrapped from the first `period` TR values.
    if len(tr) < period:
        return None
    alpha = 1.0 / float(period)
    smoothed = sum(tr[:period]) / float(period)
    for j in range(period, len(tr)):
        smoothed = alpha * tr[j] + (1.0 - alpha) * smoothed
    return smoothed / pip_size


def swing_pips_from_bars(
    bars: list[Any],
    i: int,
    *,
    lookback: int = 20,
    pip_size: float = DEFAULT_PIP_SIZE_MAJOR,
) -> float | None:
    """Lookback-window (high - low) range at bar index ``i``, in pips.

    Used as a same-timeframe swing-structure proxy: for an H4 agent the
    20-bar range approximates ~3-4 trading days of structural volatility,
    which is the operationally-relevant "recent swing" for a Phi4-style
    stop-placement decision.

    Returns ``None`` when fewer than ``lookback`` bars are available.
    """
    lo_bound = i - lookback
    if lo_bound < 0 or i >= len(bars):
        return None
    highs = [float(bars[k].high) for k in range(lo_bound, i + 1)]
    lows = [float(bars[k].low) for k in range(lo_bound, i + 1)]
    return (max(highs) - min(lows)) / pip_size


def stamp_provenance_pips(
    rationale: dict[str, Any],
    *,
    bars: list[Any],
    i: int,
    atr_period: int = 14,
    swing_lookback: int = 20,
    pip_size: float = DEFAULT_PIP_SIZE_MAJOR,
) -> None:
    """Mutate ``rationale`` in place: add ``atr_pips`` + ``h1_swing_pips``.

    Convenience for the common agent pattern: compute both values from
    the same bar series and stash under the standard key names that
    ``_annotate_trade_record`` reads. Sets keys to ``None`` when the
    window is not settled (never raises).
    """
    rationale["atr_pips"] = atr_pips_at(
        bars, i, period=atr_period, pip_size=pip_size,
    )
    rationale["h1_swing_pips"] = swing_pips_from_bars(
        bars, i, lookback=swing_lookback, pip_size=pip_size,
    )
