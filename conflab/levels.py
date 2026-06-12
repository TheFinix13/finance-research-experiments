"""Level extraction: every source that defines a *price* worth watching.

`extract_levels(df, timeframe)` returns the lab-native levels (computed from
the OHLCV frame alone). `extract_mainrepo_levels` additionally pulls the
validated detectors from eurusd-ai-agent (zones, trendlines, fibs, daily
levels) when that repo is importable — the adapter degrades to [] silently
so the lab stays runnable standalone.

All extraction is causal: only the frame passed in (history up to t) is used.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from conflab import indicators as ind
from conflab.patterns import (
    detect_double_bottoms,
    detect_double_tops,
    detect_sr_flips,
    swing_points,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Level:
    price: float
    source: str       # e.g. swing_high, double_bottom, bb_upper, zone_edge
    timeframe: str
    weight: float = 1.0
    detail: str = ""

    def to_dict(self) -> dict:
        return {"price": self.price, "source": self.source,
                "timeframe": self.timeframe, "weight": self.weight,
                "detail": self.detail}


def extract_levels(df: pd.DataFrame, timeframe: str, *,
                   swing_lookback: int = 5, max_swings: int = 8,
                   pattern_window: int = 200) -> list[Level]:
    """Lab-native levels from one timeframe's history."""
    if len(df) < 60:
        return []
    out: list[Level] = []
    n = len(df)

    # Recent swing highs/lows (resting liquidity).
    swings = swing_points(df, swing_lookback)
    for s in swings[-max_swings:]:
        out.append(Level(s.price, "swing_high" if s.is_high else "swing_low",
                         timeframe, detail=f"bar {s.index - n}"))

    # Double tops/bottoms + necklines and S/R flips on the recent window.
    tail = df.iloc[-pattern_window:]
    offset = n - len(tail)
    for hit in (detect_double_bottoms(tail) + detect_double_tops(tail)):
        out.append(Level(hit.level, hit.kind, timeframe, weight=1.5,
                         detail=f"touches {tuple(i + offset - n for i in hit.indices)}"))
        if hit.neckline is not None:
            out.append(Level(hit.neckline, f"{hit.kind}_neckline", timeframe))
    for hit in detect_sr_flips(tail):
        out.append(Level(hit.level, hit.kind, timeframe, weight=1.5))

    # Indicator bands/levels at the latest bar.
    last = -1
    bb = ind.bollinger(df).iloc[last]
    dc = ind.donchian(df).iloc[last]
    kc = ind.keltner(df).iloc[last]
    singles = {
        "bb_upper": bb["bb_upper"], "bb_lower": bb["bb_lower"],
        "bb_mid": bb["bb_mid"],
        "dc_upper": dc["dc_upper"], "dc_lower": dc["dc_lower"],
        "kc_upper": kc["kc_upper"], "kc_lower": kc["kc_lower"],
        "ema50": ind.ema(df, 50).iloc[last],
        "ema200": ind.ema(df, 200).iloc[last] if len(df) >= 200 else np.nan,
        "vwap": ind.vwap(df).iloc[last],
    }
    for source, price in singles.items():
        if price is not None and np.isfinite(price):
            out.append(Level(float(price), source, timeframe, weight=0.5))

    return out


def extract_mainrepo_levels(df: pd.DataFrame, timeframe: str) -> list[Level]:
    """Optional adapter: zone edges, trendline projections, fib levels and
    daily anchors from eurusd-ai-agent's precompute(). Returns [] when the
    main repo (or its heavier deps) is not importable."""
    try:
        from agent.config import load_config
        from agent.data.loader import df_to_bars
        from agent.rules.engine import precompute
        from agent.types import Direction, Timeframe
    except ImportError:
        log.debug("main repo not importable; skipping adapter levels")
        return []
    try:
        bars = df_to_bars(df, Timeframe(timeframe))
        ctx = precompute(bars, load_config())
        at_index = len(bars) - 1
        out: list[Level] = []
        for z in ctx.zones:
            if getattr(z, "mitigated", False) or z.created_bar_index >= at_index:
                continue
            side = "demand" if z.direction == Direction.LONG else "supply"
            out.append(Level(float(z.top), f"zone_{side}_top", timeframe, weight=1.5))
            out.append(Level(float(z.bottom), f"zone_{side}_bottom", timeframe, weight=1.5))
        for t in ctx.trendlines:
            if getattr(t, "valid", True):
                out.append(Level(float(t.price_at(at_index)), "trendline",
                                 timeframe, weight=1.5))
        fib_keys = [k for k in ctx.fib_by_index if k <= at_index]
        if fib_keys:
            fib = ctx.fib_by_index[max(fib_keys)]
            for pct, price in (fib.levels or {}).items():
                out.append(Level(float(price), "fib", timeframe, weight=0.75,
                                 detail=f"{pct}"))
        if ctx.daily_levels and at_index < len(ctx.daily_levels):
            dl = ctx.daily_levels[at_index]
            if dl is not None:
                for name, price in dl.levels_dict().items():
                    out.append(Level(float(price), "daily_level", timeframe,
                                     detail=name))
        return out
    except Exception as e:  # adapter must never break the lab
        log.warning("main repo adapter failed: %s", e)
        return []


def extract_all_levels(df: pd.DataFrame, timeframe: str,
                       use_mainrepo: bool = True) -> list[Level]:
    levels = extract_levels(df, timeframe)
    if use_mainrepo:
        levels += extract_mainrepo_levels(df, timeframe)
    return levels
