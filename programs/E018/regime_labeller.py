"""E018 — causal (past-bars-only) regime labeller for the zone fade.

Implements the FROZEN §2 spec of
``experiments/E018_regime_aware_fade_gating/PROTOCOL.md``:

Regime taxonomy (applied at the fade's signal bar ``i``, using only
``bars[:i+1]``):

* **R1 trend-pullback**   — D1 bias present, no aligned vol-expansion breakout.
* **R2 trend-extension**  — D1 bias present AND a vol-expansion breakout in the
  bias direction is in progress at bar ``i`` (fade would enter into an
  extension).
* **R3 no-bias/range**    — D1 bias is NEUTRAL (the ``htf_against`` gate never
  fires here; the agent already stands aside).

Every threshold is inherited verbatim from a documented prior — nothing is
tuned to the 2026-07 incident:

* D1 bias params (``htf="D1", lookback=10, min_move=60p``) — the deployed
  ``zone_d1_against`` config (``zone_routing.py::alpha_for``).
* Breakout constants (lookback=20, ATR period=14, vol-lookback=80,
  mult=0.50; strict specialist ratios 1.5/1.5) — Φ4.1-locked
  ``CHIGIRI_V1_*`` in ``a04_chigiri.py``.

Pure functions only; no I/O, no production mutation. Reuses the agent's own
``htf_bias_at`` verbatim for the D1 read so the label sees exactly what the
live gate sees.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from agent.alphas.concepts._htf import HTFBias, htf_bias_at
from agent.types import Bar, Direction

# --- Frozen breakout priors (Chigiri Φ4.1; a04_chigiri.py lines 98-130) -----
BREAKOUT_LOOKBACK = 20          # CHIGIRI_V1_BREAKOUT_LOOKBACK
ATR_PERIOD = 14                 # CHIGIRI_V1_ATR_PERIOD
ATR_VOL_LOOKBACK = 80           # CHIGIRI_V1_ATR_VOL_LOOKBACK
BREAKOUT_ATR_MULT = 0.50        # CHIGIRI_V1_BREAKOUT_ATR_MULT
WARMUP_BARS = BREAKOUT_LOOKBACK + ATR_VOL_LOOKBACK + 5   # CHIGIRI_V1_WARMUP_BARS
# Strict specialist ratios — REPORTED ONLY, not part of the primary R2 rule.
REGIME_MIN_MAG_ATR = 1.5        # CHIGIRI_V1_REGIME_MIN_MAG_ATR
REGIME_ATR_MULT = 1.5           # CHIGIRI_V1_REGIME_ATR_MULT

# --- Frozen D1-bias params (deployed zone_d1_against) -----------------------
HTF = "D1"
HTF_LOOKBACK = 10
HTF_MIN_MOVE_PIPS = 60.0

# --- Frozen trend convention (F18 / classifier.py) — REPORTED ONLY ----------
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25.0


class Regime(str, Enum):
    R1_TREND_PULLBACK = "R1"
    R2_TREND_EXTENSION = "R2"
    R3_NO_BIAS = "R3"


@dataclass(frozen=True)
class RegimeResult:
    regime: Regime
    bias: HTFBias
    breakout_dir: Optional[Direction]     # aligned-or-not breakout direction, if any
    breakout_aligned: bool                # breakout dir aligns with D1 bias
    mag_atr_ratio: Optional[float]        # |break| / ATR14
    atr_expansion_ratio: Optional[float]  # ATR14 / median(ATR14 window)
    strict_r2: bool                       # R2 under the stricter 1.5/1.5 ratios
    adx14: Optional[float]                # reported-only trend-context proxy

    def to_dict(self) -> dict:
        return {
            "regime": self.regime.value,
            "bias": self.bias.value,
            "breakout_dir": self.breakout_dir.value if self.breakout_dir else None,
            "breakout_aligned": self.breakout_aligned,
            "mag_atr_ratio": self.mag_atr_ratio,
            "atr_expansion_ratio": self.atr_expansion_ratio,
            "strict_r2": self.strict_r2,
            "adx14": self.adx14,
        }


# ---------------------------------------------------------------------------
# Indicators (Wilder), causal — computed once over the full series.
# ---------------------------------------------------------------------------

def _true_ranges(bars: Sequence[Bar]) -> list[float]:
    tr: list[float] = [float("nan")]
    for k in range(1, len(bars)):
        h, l = bars[k].high, bars[k].low
        pc = bars[k - 1].close
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return tr


def wilder_atr(bars: Sequence[Bar], period: int = ATR_PERIOD) -> list[float]:
    """Wilder ATR series index-aligned to ``bars`` (NaN before warmup).

    ATR[i] uses only bars ``<= i`` (causal). Seeded by the SMA of the first
    ``period`` true ranges, then Wilder-smoothed.
    """
    n = len(bars)
    atr = [float("nan")] * n
    if n <= period:
        return atr
    tr = _true_ranges(bars)
    seed = statistics.fmean(tr[1:period + 1])
    atr[period] = seed
    prev = seed
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + tr[i]) / period
        atr[i] = prev
    return atr


def wilder_adx(bars: Sequence[Bar], period: int = ADX_PERIOD) -> list[float]:
    """Wilder ADX series (causal), index-aligned. Reported-only trend proxy.

    Standard +DM/-DM/TR Wilder smoothing → DI → DX → ADX. NaN before warmup.
    """
    n = len(bars)
    adx = [float("nan")] * n
    if n <= 2 * period:
        return adx
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = _true_ranges(bars)
    for k in range(1, n):
        up = bars[k].high - bars[k - 1].high
        down = bars[k - 1].low - bars[k].low
        plus_dm[k] = up if (up > down and up > 0) else 0.0
        minus_dm[k] = down if (down > up and down > 0) else 0.0

    # Wilder-smoothed sums seeded at index `period`.
    sm_tr = sum(tr[1:period + 1])
    sm_pdm = sum(plus_dm[1:period + 1])
    sm_mdm = sum(minus_dm[1:period + 1])
    dx: list[float] = [float("nan")] * n

    def _dx(sp, sm, st):
        if st <= 0:
            return 0.0
        pdi = 100.0 * sp / st
        mdi = 100.0 * sm / st
        denom = pdi + mdi
        if denom <= 0:
            return 0.0
        return 100.0 * abs(pdi - mdi) / denom

    dx[period] = _dx(sm_pdm, sm_mdm, sm_tr)
    for i in range(period + 1, n):
        sm_tr = sm_tr - sm_tr / period + tr[i]
        sm_pdm = sm_pdm - sm_pdm / period + plus_dm[i]
        sm_mdm = sm_mdm - sm_mdm / period + minus_dm[i]
        dx[i] = _dx(sm_pdm, sm_mdm, sm_tr)

    # ADX = Wilder average of DX, first value at index 2*period.
    first = 2 * period
    if first >= n:
        return adx
    seed = statistics.fmean([dx[j] for j in range(period, first + 1)])
    adx[first] = seed
    prev = seed
    for i in range(first + 1, n):
        prev = (prev * (period - 1) + dx[i]) / period
        adx[i] = prev
    return adx


# ---------------------------------------------------------------------------
# Breakout predicate (Chigiri _detect_breakout logic, verbatim thresholds).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Breakout:
    direction: Direction
    magnitude: float
    mag_atr_ratio: float
    atr_expansion_ratio: float


def breakout_at(
    bars: Sequence[Bar], i: int, atr: Sequence[float],
) -> Optional[_Breakout]:
    """Return the vol-expansion breakout at bar ``i`` or ``None`` (causal)."""
    if i < WARMUP_BARS or i >= len(bars):
        return None
    atr_at = atr[i]
    if not (atr_at == atr_at) or atr_at <= 0.0:  # NaN or non-positive
        return None
    lo = max(0, i - ATR_VOL_LOOKBACK)
    atr_hist = [atr[k] for k in range(lo, i) if atr[k] == atr[k]]
    if len(atr_hist) < ATR_VOL_LOOKBACK // 2:
        return None
    atr_median = statistics.median(atr_hist)
    if atr_median <= 0 or atr_at <= atr_median:
        return None  # no vol expansion → not a breakout regime

    lb_lo = i - BREAKOUT_LOOKBACK
    recent_high = max(bars[k].high for k in range(lb_lo, i))
    recent_low = min(bars[k].low for k in range(lb_lo, i))
    close_i = bars[i].close
    threshold = BREAKOUT_ATR_MULT * atr_at

    if close_i - recent_high >= threshold:
        mag = close_i - recent_high
        direction = Direction.LONG
    elif recent_low - close_i >= threshold:
        mag = recent_low - close_i
        direction = Direction.SHORT
    else:
        return None
    return _Breakout(
        direction=direction,
        magnitude=mag,
        mag_atr_ratio=mag / atr_at,
        atr_expansion_ratio=atr_at / atr_median,
    )


# ---------------------------------------------------------------------------
# Regime decision (§2.3, frozen).
# ---------------------------------------------------------------------------

def _bias_direction(bias: HTFBias) -> Optional[Direction]:
    if bias is HTFBias.UP:
        return Direction.LONG
    if bias is HTFBias.DOWN:
        return Direction.SHORT
    return None


def regime_at(
    bars: Sequence[Bar],
    i: int,
    *,
    atr: Optional[Sequence[float]] = None,
    adx: Optional[Sequence[float]] = None,
) -> RegimeResult:
    """Causal regime label at signal bar ``i`` per PROTOCOL §2.3.

    ``atr`` / ``adx`` may be precomputed (via :func:`wilder_atr` /
    :func:`wilder_adx`) for speed; if omitted they are computed on the fly.
    """
    bias = htf_bias_at(
        list(bars), i, htf=HTF,
        htf_lookback=HTF_LOOKBACK, min_move_pips=HTF_MIN_MOVE_PIPS,
    )
    adx_series = adx if adx is not None else wilder_adx(bars)
    adx_val = adx_series[i] if 0 <= i < len(adx_series) and adx_series[i] == adx_series[i] else None

    if bias is HTFBias.NEUTRAL:
        return RegimeResult(
            regime=Regime.R3_NO_BIAS, bias=bias, breakout_dir=None,
            breakout_aligned=False, mag_atr_ratio=None,
            atr_expansion_ratio=None, strict_r2=False, adx14=adx_val,
        )

    atr_series = atr if atr is not None else wilder_atr(bars)
    bo = breakout_at(bars, i, atr_series)
    bias_dir = _bias_direction(bias)
    aligned = bool(bo is not None and bo.direction == bias_dir)

    if aligned:
        strict = (
            bo.mag_atr_ratio >= REGIME_MIN_MAG_ATR
            and bo.atr_expansion_ratio >= REGIME_ATR_MULT
        )
        return RegimeResult(
            regime=Regime.R2_TREND_EXTENSION, bias=bias,
            breakout_dir=bo.direction, breakout_aligned=True,
            mag_atr_ratio=bo.mag_atr_ratio,
            atr_expansion_ratio=bo.atr_expansion_ratio,
            strict_r2=strict, adx14=adx_val,
        )
    return RegimeResult(
        regime=Regime.R1_TREND_PULLBACK, bias=bias,
        breakout_dir=(bo.direction if bo else None),
        breakout_aligned=False,
        mag_atr_ratio=(bo.mag_atr_ratio if bo else None),
        atr_expansion_ratio=(bo.atr_expansion_ratio if bo else None),
        strict_r2=False, adx14=adx_val,
    )
