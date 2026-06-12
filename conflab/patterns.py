"""Chart and candlestick pattern detection (causal — uses bars up to t only).

Three families:

* swing-derived price patterns: double tops / double bottoms (with necklines),
  support/resistance polarity flips;
* per-bar candlestick events: doji, hammer, shooting star, bullish/bearish
  engulfing, pin bars;
* swing points themselves (shared primitive).

Pattern *levels* (double-bottom low, neckline, flip level) feed the
confluence engine. Candlestick *events* are tags only — they have no
persistent price level, so counting them as levels would inflate density
(see README anti-fooling rules).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from conflab.indicators import atr


@dataclass(frozen=True)
class SwingPoint:
    index: int          # positional index into the DataFrame
    price: float
    is_high: bool


@dataclass(frozen=True)
class PatternHit:
    kind: str           # double_bottom | double_top | sr_flip_support | sr_flip_resistance
    level: float        # the tradeable price level the pattern defines
    neckline: float | None
    indices: tuple[int, ...] = field(default_factory=tuple)


def swing_points(df: pd.DataFrame, lookback: int = 5) -> list[SwingPoint]:
    """Local extrema: bar i is a swing high if its high is the maximum of
    [i-lookback, i+lookback] (strictly causal callers should only use swings
    with index <= t - lookback, which `detect_*` below respect)."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)
    out: list[SwingPoint] = []
    for i in range(lookback, n - lookback):
        win_h = highs[i - lookback:i + lookback + 1]
        win_l = lows[i - lookback:i + lookback + 1]
        if highs[i] >= win_h.max():
            out.append(SwingPoint(i, float(highs[i]), True))
        elif lows[i] <= win_l.min():
            out.append(SwingPoint(i, float(lows[i]), False))
    return out


def _double_pattern(df: pd.DataFrame, swings: list[SwingPoint], *,
                    bottoms: bool, tol_atr: float, min_gap: int,
                    max_gap: int) -> list[PatternHit]:
    a = atr(df).to_numpy()
    pts = [s for s in swings if s.is_high != bottoms]
    opposite = [s for s in swings if s.is_high == bottoms]
    hits: list[PatternHit] = []
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        gap = p2.index - p1.index
        if not (min_gap <= gap <= max_gap):
            continue
        tol = tol_atr * float(a[p2.index]) if np.isfinite(a[p2.index]) else 0.0
        if tol <= 0 or abs(p1.price - p2.price) > tol:
            continue
        # Neckline: the intervening opposite swing between the two touches.
        mids = [s for s in opposite if p1.index < s.index < p2.index]
        if not mids:
            continue
        neck = (max(mids, key=lambda s: s.price) if bottoms
                else min(mids, key=lambda s: s.price))
        # Neckline must actually separate from the touches.
        if bottoms and neck.price <= max(p1.price, p2.price):
            continue
        if not bottoms and neck.price >= min(p1.price, p2.price):
            continue
        level = min(p1.price, p2.price) if bottoms else max(p1.price, p2.price)
        hits.append(PatternHit(
            kind="double_bottom" if bottoms else "double_top",
            level=float(level), neckline=float(neck.price),
            indices=(p1.index, p2.index),
        ))
    return hits


def detect_double_bottoms(df: pd.DataFrame, lookback: int = 5,
                          tol_atr: float = 0.5, min_gap: int = 5,
                          max_gap: int = 60) -> list[PatternHit]:
    return _double_pattern(df, swing_points(df, lookback), bottoms=True,
                           tol_atr=tol_atr, min_gap=min_gap, max_gap=max_gap)


def detect_double_tops(df: pd.DataFrame, lookback: int = 5,
                       tol_atr: float = 0.5, min_gap: int = 5,
                       max_gap: int = 60) -> list[PatternHit]:
    return _double_pattern(df, swing_points(df, lookback), bottoms=False,
                           tol_atr=tol_atr, min_gap=min_gap, max_gap=max_gap)


def detect_sr_flips(df: pd.DataFrame, lookback: int = 5,
                    break_atr: float = 0.25,
                    retest_atr: float = 0.5) -> list[PatternHit]:
    """Support-turned-resistance (and mirror): a swing low whose level is
    later broken by a close more than ``break_atr``×ATR below it, then
    retested from below within ``retest_atr``×ATR — the user's hand-drawn
    'support turned resistance' on the daily, made causal and mechanical.
    """
    a = atr(df).to_numpy()
    closes = df["close"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)
    hits: list[PatternHit] = []
    for s in swing_points(df, lookback):
        level = s.price
        broken_at = None
        for j in range(s.index + 1, n):
            buf = break_atr * a[j] if np.isfinite(a[j]) else 0.0
            if buf <= 0:
                continue
            if s.is_high:        # resistance: broken by close above
                if closes[j] > level + buf:
                    broken_at = j
                    break
            else:                # support: broken by close below
                if closes[j] < level - buf:
                    broken_at = j
                    break
        if broken_at is None:
            continue
        for j in range(broken_at + 1, n):
            buf = retest_atr * a[j] if np.isfinite(a[j]) else 0.0
            if buf <= 0:
                continue
            if s.is_high and lows[j] <= level + buf and closes[j] > level:
                # old resistance retested from above -> new support
                hits.append(PatternHit("sr_flip_support", float(level), None,
                                       (s.index, broken_at, j)))
                break
            if (not s.is_high) and highs[j] >= level - buf and closes[j] < level:
                # old support retested from below -> new resistance
                hits.append(PatternHit("sr_flip_resistance", float(level), None,
                                       (s.index, broken_at, j)))
                break
    return hits


# ---------------------------------------------------------------------------
# Candlestick events (tags, not levels)
# ---------------------------------------------------------------------------

def candle_events(df: pd.DataFrame, doji_body_frac: float = 0.1,
                  wick_body_ratio: float = 2.0) -> pd.DataFrame:
    """Boolean event columns per bar: doji, hammer, shooting_star,
    bull_engulfing, bear_engulfing, bull_pin, bear_pin."""
    o, h, lo, c = (df[k] for k in ("open", "high", "low", "close"))
    body = (c - o).abs()
    rng = (h - lo).replace(0.0, np.nan)
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    lower = pd.concat([o, c], axis=1).min(axis=1) - lo

    doji = (body / rng) < doji_body_frac
    hammer = (lower > wick_body_ratio * body) & (upper < body)
    shooting = (upper > wick_body_ratio * body) & (lower < body)

    prev_o, prev_c = o.shift(1), c.shift(1)
    bull_engulf = (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)
    bear_engulf = (prev_c > prev_o) & (c < o) & (c <= prev_o) & (o >= prev_c)

    # Pin bars: dominant single wick (>=2/3 of range), close back inside.
    bull_pin = (lower / rng > 2 / 3) & (c > (h + lo) / 2)
    bear_pin = (upper / rng > 2 / 3) & (c < (h + lo) / 2)

    return pd.DataFrame({
        "doji": doji.fillna(False),
        "hammer": hammer.fillna(False),
        "shooting_star": shooting.fillna(False),
        "bull_engulfing": bull_engulf.fillna(False),
        "bear_engulfing": bear_engulf.fillna(False),
        "bull_pin": bull_pin.fillna(False),
        "bear_pin": bear_pin.fillna(False),
    }, index=df.index)
