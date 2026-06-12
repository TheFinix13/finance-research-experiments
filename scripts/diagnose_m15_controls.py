"""Diagnostic: is the Stage-1 uniform-random control exchangeable with
events on M15 with respect to time-of-day?

Two checks:
1. Mean ATR-normalised forward MFE of RANDOM times, grouped by hour-of-day.
   If this varies materially by hour, any event family that clusters in
   particular hours inherits a mechanical advantage/disadvantage.
2. Hour-of-day distribution of events for a few high-n M15 families vs the
   uniform-bar distribution.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import load_frames
from conflab.events import all_detectors
from conflab.indicators import atr
from conflab.screening import directional_outcome

SCREEN_START, SCREEN_END = "2015-01-01", "2021-12-31"


def main() -> None:
    df = load_frames("EURUSD", ["M15"], start=SCREEN_START,
                     end=SCREEN_END)["M15"]
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    a = atr(df).to_numpy()
    hours = df.index.hour.to_numpy()
    n = len(df)
    rng = np.random.default_rng(7)

    print("=== 1. control MFE by hour-of-day (random times, horizon 16) ===")
    idxs = rng.integers(60, n - 17, size=60000)
    dirs = rng.choice([-1, 1], size=len(idxs))
    by_hour: dict[int, list[float]] = {h: [] for h in range(24)}
    for i, d in zip(idxs, dirs):
        out = directional_outcome(highs, lows, closes, a, int(i), int(d), 16)
        if out is not None:
            by_hour[int(hours[i])].append(out[0])
    overall = np.mean([v for vals in by_hour.values() for v in vals])
    print(f"overall control MFE: {overall:.3f} ATR")
    for h in range(24):
        vals = by_hour[h]
        if vals:
            print(f"  hour {h:02d}: n={len(vals):>5} mfe={np.mean(vals):.3f} "
                  f"({np.mean(vals)/overall-1:+.1%} vs overall)")

    print("\n=== 2. event hour distribution vs uniform bars ===")
    uniform = np.bincount(hours, minlength=24) / n
    detectors = all_detectors()
    events_by_type: dict[str, list[int]] = {}
    for det in detectors.values():
        for e in det(df):
            events_by_type.setdefault(e.type, []).append(e.index)
    for etype in ("channel_top_touch", "fib_50_tag", "asia_high_sweep",
                  "bullish_fvg_touch", "tweezer_top"):
        if etype not in events_by_type:
            continue
        eh = np.bincount(hours[events_by_type[etype]], minlength=24)
        eh = eh / eh.sum()
        top = np.argsort(eh)[::-1][:4]
        print(f"  {etype:<24} top hours: "
              + ", ".join(f"{h:02d}h={eh[h]:.1%}(unif {uniform[h]:.1%})"
                          for h in top))


if __name__ == "__main__":
    main()
