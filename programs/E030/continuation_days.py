"""E030 London-continuation day construction — frozen at pre-registration.

Day classification is delegated to E028's frozen classifier
(`programs/E028/po3_days.py::analyze_days`) so the class rule is
byte-identical. The continuation trade (PROTOCOL §1) is new: on
one-side days, enter WITH London's take direction at the close of the
first M15 bar >= 13:30 UTC, exit at the last M15 close before 21:00
UTC. Time exit only — no SL, no TP.

Placebo arms: on BOTH and NEITHER days the same 13:30->21:00 drift is
computed in both directions (PROTOCOL §1 placebo contrast).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from programs.E028.po3_days import ENTRY_MINUTES, PIP, analyze_days


@dataclass
class ContinuationDay:
    date: str
    klass: str
    direction: int | None      # +1 HIGH_ONLY, -1 LOW_ONLY, None otherwise
    net_pips_base: float | None
    gross_pips: float | None
    placebo_long_gross: float | None   # BOTH/NEITHER days only
    placebo_short_gross: float | None
    skip_reason: str | None = None


def _drift(day: pd.DataFrame, direction: int) -> float | None:
    """Gross pips of the 13:30->21:00 UTC drift in `direction`."""
    h = day.index.hour.to_numpy()
    mod = (day.index.hour * 60 + day.index.minute).to_numpy()
    entry_mask = (mod >= ENTRY_MINUTES) & (h >= 13) & (h < 21)
    if not entry_mask.any():
        return None
    entry_pos = int(np.argmax(entry_mask))
    ny = np.where((h >= 13) & (h < 21))[0]
    exit_pos = int(ny[-1])
    if exit_pos <= entry_pos:
        return None
    entry = float(day["close"].iloc[entry_pos])
    exit_ = float(day["close"].iloc[exit_pos])
    return (exit_ - entry) / PIP * direction


def analyze_continuation_days(df: pd.DataFrame,
                              cost_pips_side: float) -> list[ContinuationDay]:
    klass_by_date = {d.date: d.klass for d in analyze_days(df, cost_pips_side)}
    out: list[ContinuationDay] = []
    for date, day in df.groupby(df.index.date):
        klass = klass_by_date.get(str(date))
        if klass is None:            # day failed E028's asia/session guards
            continue
        rec = ContinuationDay(str(date), klass, None, None, None, None, None)
        if klass in ("HIGH_ONLY", "LOW_ONLY"):
            rec.direction = +1 if klass == "HIGH_ONLY" else -1
            gross = _drift(day, rec.direction)
            if gross is None:
                rec.skip_reason = "no_entry_or_exit_bar"
            else:
                rec.gross_pips = round(float(gross), 2)
                rec.net_pips_base = round(float(gross - 2.0 * cost_pips_side), 2)
        else:
            gl = _drift(day, +1)
            gs = _drift(day, -1)
            rec.placebo_long_gross = None if gl is None else round(float(gl), 2)
            rec.placebo_short_gross = None if gs is None else round(float(gs), 2)
        out.append(rec)
    return out
