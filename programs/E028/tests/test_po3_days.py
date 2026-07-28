"""E028 day-classifier unit tests: one synthetic day with known structure."""
from __future__ import annotations

import numpy as np
import pandas as pd

from programs.E028.po3_days import analyze_days, wilson_ci


def _day(asia_range=(1.1000, 1.1050), london_path=None, ny_path=None,
         date="2024-01-02"):
    """Build one UTC day of M15 bars. Paths are lists of (h, l) per bar;
    open/close are midpoints, so class/touch logic is driven by h/l."""
    rows, times = [], []
    t0 = pd.Timestamp(f"{date} 00:00", tz="UTC")
    lo_a, hi_a = asia_range
    n_asia = 28
    for i in range(n_asia):                       # 00:00–06:45
        h = hi_a if i == 10 else hi_a - 0.0005
        lo = lo_a if i == 20 else lo_a + 0.0005
        rows.append((h, lo))
        times.append(t0 + pd.Timedelta(minutes=15 * i))
    lp = london_path or [(hi_a - 0.001, lo_a + 0.001)] * 24
    for i, (h, lo) in enumerate(lp):              # 07:00–12:45
        rows.append((h, lo))
        times.append(t0 + pd.Timedelta(hours=7, minutes=15 * i))
    np_ = ny_path or [(hi_a - 0.001, lo_a + 0.001)] * 32
    for i, (h, lo) in enumerate(np_):             # 13:00–20:45
        rows.append((h, lo))
        times.append(t0 + pd.Timedelta(hours=13, minutes=15 * i))
    a = np.asarray(rows)
    mid = (a[:, 0] + a[:, 1]) / 2
    df = pd.DataFrame({"open": mid, "high": a[:, 0], "low": a[:, 1],
                       "close": mid, "volume": np.ones(len(a))},
                      index=pd.DatetimeIndex(times))
    return df


def test_low_only_completed_day():
    """London sweeps Asia lows; NY runs to Asia high => LOW_ONLY, completed,
    long trade hits TP."""
    london = [(1.1040, 1.1005)] * 8 + [(1.1010, 1.0980)] * 8 \
        + [(1.1015, 1.0995)] * 8                          # takes lows only
    ny = [(1.1010, 1.0996)] * 4 + [(1.1030, 1.1005)] * 8 \
        + [(1.1052, 1.1020)] * 20                          # touches asia high
    df = _day(london_path=london, ny_path=ny)
    days = analyze_days(df, cost_pips_side=0.3)
    assert len(days) == 1
    d = days[0]
    assert d.klass == "LOW_ONLY"
    assert d.completed is True
    assert d.trade is not None
    assert d.trade["direction"] == +1
    assert d.trade["exit_reason"] == "tp"
    assert d.trade["net_pips"] > 0


def test_both_day_no_trade():
    london = [(1.1060, 1.0990)] * 24                       # takes both sides
    df = _day(london_path=london)
    days = analyze_days(df, cost_pips_side=0.3)
    assert days[0].klass == "BOTH"
    assert days[0].trade is None
    assert days[0].completed is None


def test_neither_day():
    df = _day()                                            # default inside range
    days = analyze_days(df, cost_pips_side=0.3)
    assert days[0].klass == "NEITHER"


def test_fake_detection():
    """NY first extends below London's low (fake), then completes to the
    Asia high."""
    london = [(1.1040, 1.0980)] * 24                       # takes lows
    ny = [(1.1000, 1.0970)] * 4 + [(1.1052, 1.0990)] * 28  # new low, then TP
    df = _day(london_path=london, ny_path=ny)
    d = analyze_days(df, cost_pips_side=0.3)[0]
    assert d.klass == "LOW_ONLY"
    assert d.fake is True
    assert d.completed is True


def test_tp_touched_pre_entry_skips():
    """If NY reaches the opposite extreme before 13:30, no trade."""
    london = [(1.1040, 1.0980)] * 24
    ny = [(1.1052, 1.1000)] * 32                           # touches TP at 13:00
    df = _day(london_path=london, ny_path=ny)
    d = analyze_days(df, cost_pips_side=0.3)[0]
    assert d.trade is None
    assert d.skip_reason == "tp_touched_pre_entry"


def test_wilson_ci_sane():
    p, lo, hi = wilson_ci(50, 100)
    assert abs(p - 0.5) < 1e-9
    assert lo < 0.5 < hi
    assert 0.40 < lo and hi < 0.60
