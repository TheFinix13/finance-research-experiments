"""Test B detector — impulse-origin return events.

Per `protocols/TEST_B_PROTOCOL.md` §3 (frozen 2026-06-16):

1. **Impulse leg.** A bar `t` is an impulse-end bar iff the K-bar window
   `[t-K+1, t]` produces a net move
       up:   high[t] − low[t-K+1] ≥ M_atr × ATR(20, t)  AND ≥ M_pips
       down: high[t-K+1] − low[t] ≥ M_atr × ATR(20, t)  AND ≥ M_pips
   AND the worst intra-leg retrace ≤ 30% of the leg height.
2. **Origin zone.** Two candidates evaluated at `t-K`:
       A: range of the last opposite-direction bar in [t-K-5, t-K]
          (red bar before an up-impulse, green bar before a down-impulse).
          If none exists, fall back to bar `t-K` itself.
       B: [min(low), max(high)] over [t-K-4, t-K] (last 5 bars consol).
   Pick whichever has the larger pip span.
3. **Return-touch.** First bar `s ∈ [t+1, t+N]` where
       up:   low[s]  ≤ origin_zone_top
       down: high[s] ≥ origin_zone_bottom
4. **Inter-event spacing.** Consecutive impulse-end bars are separated by
   ≥ K bars to prevent rolling-trend overcounting.

The detector is NOT registered in `conflab.events.all_detectors` — Test B
is a separate experiment family per protocol §2. Output rows are dicts
(richer schema than the Test A `Event` dataclass) suitable for direct
JSONL serialisation; friction COMPONENTS (raw, pre-z-score) are computed
once per event so the Stage-4 friction analysis can fit its reference
distribution post-hoc on the EURUSD screen split.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from conflab.friction import components as friction_components
from conflab.indicators import atr

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImpulseReturnConfig:
    """Locked-by-TF detector knobs (protocol §3)."""
    M_atr: float = 1.5      # gridded in {1.0, 1.5, 2.0} at Stage 1
    M_pips: float = 40.0    # H4 default; H1 uses 20
    K: int = 3              # max bars to complete impulse
    max_retrace_frac: float = 0.30
    N: int = 40             # validity window for return-touch
    consol_lookback: int = 5
    pip_size: float = 0.0001  # USD-quoted majors; JPY pairs would use 0.01


def _pip(value: float, pip_size: float) -> float:
    return value / pip_size


def _impulse_leg(highs: np.ndarray, lows: np.ndarray, t: int, K: int,
                 direction: int) -> tuple[bool, float, float]:
    """Return (valid, leg_top, leg_bottom). For up-impulse, leg_top is the
    final-bar high and leg_bottom is the start-bar low; the worst-retrace
    check uses bar-by-bar drawdown from the running maximum.
    """
    start = t - K + 1
    if start < 0:
        return False, 0.0, 0.0
    if direction > 0:
        leg_top = float(highs[t])
        leg_bottom = float(lows[start])
        leg_height = leg_top - leg_bottom
        if leg_height <= 0:
            return False, 0.0, 0.0
        running_max = -np.inf
        for j in range(start, t + 1):
            running_max = max(running_max, float(highs[j]))
            drawdown = running_max - float(lows[j])
            if drawdown / leg_height > 0.30 + 1e-9:
                return False, 0.0, 0.0
        return True, leg_top, leg_bottom
    else:
        leg_top = float(highs[start])
        leg_bottom = float(lows[t])
        leg_height = leg_top - leg_bottom
        if leg_height <= 0:
            return False, 0.0, 0.0
        running_min = np.inf
        for j in range(start, t + 1):
            running_min = min(running_min, float(lows[j]))
            run_up = float(highs[j]) - running_min
            if run_up / leg_height > 0.30 + 1e-9:
                return False, 0.0, 0.0
        return True, leg_top, leg_bottom


def _origin_zone(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                 closes: np.ndarray, impulse_start: int,
                 direction: int, lookback: int) -> tuple[float, float]:
    """Pick the better of (A) last-opposite-bar range and (B) last-N-bar
    consolidation range — whichever has the larger pip span."""
    n = len(highs)

    cand_a_top = float(highs[impulse_start])
    cand_a_bot = float(lows[impulse_start])
    look_start = max(0, impulse_start - lookback)
    for k in range(impulse_start - 1, look_start - 1, -1):
        body_dir = +1 if closes[k] > opens[k] else (-1 if closes[k] < opens[k] else 0)
        if body_dir != 0 and body_dir != direction:
            cand_a_top = float(highs[k])
            cand_a_bot = float(lows[k])
            break

    cb_lo = max(0, impulse_start - (lookback - 1))
    cb_hi = impulse_start + 1
    cand_b_top = float(np.max(highs[cb_lo:cb_hi]))
    cand_b_bot = float(np.min(lows[cb_lo:cb_hi]))

    span_a = cand_a_top - cand_a_bot
    span_b = cand_b_top - cand_b_bot
    if span_b > span_a:
        return cand_b_top, cand_b_bot
    return cand_a_top, cand_a_bot


def detect_impulse_origin_return_events(
        df: pd.DataFrame, *, direction: int,
        cfg: ImpulseReturnConfig | None = None,
        timeframe: str | None = None) -> list[dict]:
    """Detect impulse-origin return events in one direction (+1 / −1).

    Returns a list of plain dicts with the schema specified in protocol
    §"Code" / "detector output schema":

        ts, tf, event_type, impulse_top, impulse_bottom, impulse_height_pips,
        origin_zone_top, origin_zone_bottom, impulse_end_idx, touch_bar_idx,
        touch_low, touch_high, R_pips, validity_window_bars,
        friction_components: {...}

    The MFE outcome itself is computed downstream (in the screen runner),
    NOT in the detector — keeping the detector responsible for "events
    happened" and the runner for "what happened next."
    """
    if direction not in (-1, +1):
        raise ValueError("direction must be -1 or +1")
    cfg = cfg or ImpulseReturnConfig()
    n = len(df)
    if n < cfg.K + cfg.N + 5:
        return []
    o = df["open"].to_numpy()
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    c = df["close"].to_numpy()
    a = atr(df, period=20).to_numpy()
    idx = df.index
    pip_size = cfg.pip_size
    event_type = ("impulse_origin_return_up" if direction > 0
                  else "impulse_origin_return_down")
    out: list[dict] = []
    last_emit_t = -1
    for t in range(cfg.K, n - 1):
        if t - last_emit_t < cfg.K:
            continue
        if not (np.isfinite(a[t]) and a[t] > 0):
            continue

        valid, leg_top, leg_bottom = _impulse_leg(h, l, t, cfg.K, direction)
        if not valid:
            continue
        leg_height = leg_top - leg_bottom
        leg_height_pips = _pip(leg_height, pip_size)
        if leg_height < cfg.M_atr * float(a[t]):
            continue
        if leg_height_pips < cfg.M_pips:
            continue

        impulse_start = t - cfg.K + 1
        zone_top, zone_bot = _origin_zone(o, h, l, c, impulse_start,
                                          direction, cfg.consol_lookback)
        zone_top = float(zone_top)
        zone_bot = float(zone_bot)
        if zone_top <= zone_bot:
            continue

        touch_idx = -1
        s_end = min(n - 1, t + cfg.N)
        for s in range(t + 1, s_end + 1):
            if direction > 0:
                if l[s] <= zone_top:
                    touch_idx = s
                    break
            else:
                if h[s] >= zone_bot:
                    touch_idx = s
                    break
        if touch_idx < 0:
            continue

        zone_mid = 0.5 * (zone_top + zone_bot)
        comp = friction_components(
            df, impulse_end_idx=t, touch_idx=touch_idx,
            impulse_top=leg_top, impulse_bottom=leg_bottom,
            direction=direction, origin_zone_mid=zone_mid)

        R_pips = leg_height_pips / 4.0
        out.append({
            "ts": str(idx[touch_idx]),
            "impulse_end_ts": str(idx[t]),
            "tf": timeframe or "",
            "event_type": event_type,
            "direction": int(direction),
            "impulse_top": float(leg_top),
            "impulse_bottom": float(leg_bottom),
            "impulse_height_pips": float(round(leg_height_pips, 4)),
            "origin_zone_top": float(zone_top),
            "origin_zone_bottom": float(zone_bot),
            "impulse_end_idx": int(t),
            "impulse_start_idx": int(impulse_start),
            "touch_bar_idx": int(touch_idx),
            "touch_low": float(l[touch_idx]),
            "touch_high": float(h[touch_idx]),
            "R_pips": float(round(R_pips, 4)),
            "validity_window_bars": int(touch_idx - t),
            "friction_components": comp.as_dict(),
            "M_atr_setting": float(cfg.M_atr),
            "M_pips_setting": float(cfg.M_pips),
            "K_setting": int(cfg.K),
            "N_setting": int(cfg.N),
        })
        last_emit_t = t
    return out


def detect_both_directions(df: pd.DataFrame, *,
                           cfg: ImpulseReturnConfig | None = None,
                           timeframe: str | None = None) -> list[dict]:
    """Convenience: detect up + down events on one frame."""
    cfg = cfg or ImpulseReturnConfig()
    return (detect_impulse_origin_return_events(
                df, direction=+1, cfg=cfg, timeframe=timeframe)
            + detect_impulse_origin_return_events(
                df, direction=-1, cfg=cfg, timeframe=timeframe))
