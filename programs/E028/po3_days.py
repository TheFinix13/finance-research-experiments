"""E028 Power-of-Three day construction — frozen at pre-registration.

PROTOCOL §1/§2 exactly: fixed UTC windows (Asia 00–06, London 07–12,
NY 13–20 inclusive hours), day = UTC calendar date, ≥16 Asia bars,
adverse-first intrabar tie-break, entry at the close of the first M15
bar with open time ≥ 13:30 UTC.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PIP = 0.0001
MIN_ASIA_BARS = 16
ENTRY_MINUTES = 13 * 60 + 30      # 13:30 UTC


@dataclass
class DayRecord:
    date: str
    asia_high: float
    asia_low: float
    n_asia_bars: int
    klass: str                    # HIGH_ONLY | LOW_ONLY | BOTH | NEITHER
    ny_touch_high: bool
    ny_touch_low: bool
    completed: bool | None        # one-side days only
    fake: bool | None             # one-side days only
    completion_bar: int | None    # NY bar offset of first opposite touch
    trade: dict | None = None
    skip_reason: str | None = None
    extra: dict = field(default_factory=dict)


def _simulate_trade(day_bars: pd.DataFrame, entry_pos: int, direction: int,
                    entry: float, sl: float, tp: float,
                    cost_pips_side: float) -> dict:
    """Bar-by-bar from the bar AFTER entry; adverse-first intrabar."""
    highs = day_bars["high"].to_numpy()
    lows = day_bars["low"].to_numpy()
    closes = day_bars["close"].to_numpy()
    exit_price, exit_reason = None, "time"
    for t in range(entry_pos + 1, len(day_bars)):
        if direction > 0:
            if lows[t] <= sl:
                exit_price, exit_reason = sl, "sl"
                break
            if highs[t] >= tp:
                exit_price, exit_reason = tp, "tp"
                break
        else:
            if highs[t] >= sl:
                exit_price, exit_reason = sl, "sl"
                break
            if lows[t] <= tp:
                exit_price, exit_reason = tp, "tp"
                break
    if exit_price is None:
        exit_price = float(closes[-1])
    gross = (exit_price - entry) / PIP * direction
    net = gross - 2.0 * cost_pips_side
    return {"direction": direction, "entry": entry, "sl": sl, "tp": tp,
            "exit": float(exit_price), "exit_reason": exit_reason,
            "gross_pips": round(float(gross), 2),
            "net_pips": round(float(net), 2)}


def analyze_days(df: pd.DataFrame, cost_pips_side: float) -> list[DayRecord]:
    out: list[DayRecord] = []
    for date, day in df.groupby(df.index.date):
        h = day.index.hour.to_numpy()
        mod = (day.index.hour * 60 + day.index.minute).to_numpy()
        asia = day[(h >= 0) & (h < 7)]
        if len(asia) < MIN_ASIA_BARS:
            continue
        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())
        london = day[(h >= 7) & (h < 13)]
        ny = day[(h >= 13) & (h < 21)]
        if london.empty or ny.empty:
            continue
        took_high = bool((london["high"] > asia_high).any())
        took_low = bool((london["low"] < asia_low).any())
        klass = ("BOTH" if took_high and took_low else
                 "HIGH_ONLY" if took_high else
                 "LOW_ONLY" if took_low else "NEITHER")
        ny_touch_high = bool((ny["high"] >= asia_high).any())
        ny_touch_low = bool((ny["low"] <= asia_low).any())

        completed = fake = None
        completion_bar = None
        rec = DayRecord(str(date), asia_high, asia_low, len(asia), klass,
                        ny_touch_high, ny_touch_low, completed, fake,
                        completion_bar)

        if klass in ("HIGH_ONLY", "LOW_ONLY"):
            # opposite extreme + London's own manipulation extreme
            if klass == "LOW_ONLY":
                target = asia_high
                london_ext = float(london["low"].min())
                nh, nl = ny["high"].to_numpy(), ny["low"].to_numpy()
                completed = False
                fake = False
                for t in range(len(ny)):
                    beyond = nl[t] < london_ext      # continuation beyond London low
                    touch = nh[t] >= target
                    if beyond and not completed:
                        fake = True                  # adverse-first on same bar
                    if touch:
                        completed = True
                        completion_bar = t
                        break
            else:
                target = asia_low
                london_ext = float(london["high"].max())
                nh, nl = ny["high"].to_numpy(), ny["low"].to_numpy()
                completed = False
                fake = False
                for t in range(len(ny)):
                    beyond = nh[t] > london_ext
                    touch = nl[t] <= target
                    if beyond and not completed:
                        fake = True
                    if touch:
                        completed = True
                        completion_bar = t
                        break
            rec.completed, rec.fake, rec.completion_bar = completed, fake, completion_bar

            # --- mechanical rule (PROTOCOL §2) ---
            day_mod = mod
            entry_mask = (day_mod >= ENTRY_MINUTES) & (h >= 13) & (h < 21)
            if not entry_mask.any():
                rec.skip_reason = "no_entry_bar"
            else:
                entry_pos = int(np.argmax(entry_mask))
                entry_ts_pos = entry_pos
                pre_entry_ny = day[(h >= 13) & (h < 21) &
                                   (np.arange(len(day)) < entry_ts_pos)]
                direction = +1 if klass == "LOW_ONLY" else -1
                tp = asia_high if direction > 0 else asia_low
                # TP already touched before entry?
                if direction > 0 and not pre_entry_ny.empty and \
                        (pre_entry_ny["high"] >= tp).any():
                    rec.skip_reason = "tp_touched_pre_entry"
                elif direction < 0 and not pre_entry_ny.empty and \
                        (pre_entry_ny["low"] <= tp).any():
                    rec.skip_reason = "tp_touched_pre_entry"
                else:
                    manip = day[(h >= 7) & (np.arange(len(day)) < entry_ts_pos)]
                    if manip.empty:
                        rec.skip_reason = "no_manipulation_window"
                    else:
                        sl = float(manip["low"].min()) if direction > 0 \
                            else float(manip["high"].max())
                        entry = float(day["close"].iloc[entry_pos])
                        if (direction > 0 and not (sl < entry < tp)) or \
                           (direction < 0 and not (tp < entry < sl)):
                            rec.skip_reason = "degenerate_geometry"
                        else:
                            ny_slice = day[(h >= 13) & (h < 21)]
                            ny_entry_pos = int(np.argmax(
                                (ny_slice.index == day.index[entry_pos])))
                            rec.trade = _simulate_trade(
                                ny_slice, ny_entry_pos, direction, entry,
                                sl, tp, cost_pips_side)
        out.append(rec)
    return out


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(p_hat, lo, hi) Wilson score interval."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(p, 4), round(center - half, 4), round(center + half, 4)
