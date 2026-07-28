"""E030 continuation-day unit tests: synthetic days with known drift."""
from __future__ import annotations

import numpy as np
import pandas as pd

from programs.E030.continuation_days import analyze_continuation_days


def _day(asia_range=(1.1000, 1.1050), london_path=None, ny_closes=None,
         date="2024-01-02"):
    """One UTC day of M15 bars. london_path = (high, low) per bar;
    ny_closes = close per NY bar (h/l hug the close so no take flips)."""
    rows, times = [], []
    t0 = pd.Timestamp(f"{date} 00:00", tz="UTC")
    lo_a, hi_a = asia_range
    for i in range(28):                               # 00:00–06:45
        h = hi_a if i == 10 else hi_a - 0.0005
        lo = lo_a if i == 20 else lo_a + 0.0005
        c = (h + lo) / 2
        rows.append((c, h, lo, c))
        times.append(t0 + pd.Timedelta(minutes=15 * i))
    lp = london_path or [(hi_a - 0.001, lo_a + 0.001)] * 24
    for i, (h, lo) in enumerate(lp):                  # 07:00–12:45
        c = (h + lo) / 2
        rows.append((c, h, lo, c))
        times.append(t0 + pd.Timedelta(hours=7, minutes=15 * i))
    nc = ny_closes or [1.1030] * 32
    for i, c in enumerate(nc):                        # 13:00–20:45
        rows.append((c, c + 0.0001, c - 0.0001, c))
        times.append(t0 + pd.Timedelta(hours=13, minutes=15 * i))
    a = np.asarray(rows)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3], "volume": np.ones(len(a))},
                        index=pd.DatetimeIndex(times))


def test_high_only_long_continuation_wins():
    """London takes highs; NY drifts up 20 pips from the 13:30 bar."""
    london = [(1.1060, 1.1020)] * 24                  # breaks asia high only
    ny = [1.1030, 1.1030] + [1.1030 + 0.0002 * i for i in range(30)]
    df = _day(london_path=london, ny_closes=ny)
    days = analyze_continuation_days(df, cost_pips_side=0.3)
    assert len(days) == 1
    d = days[0]
    assert d.klass == "HIGH_ONLY"
    assert d.direction == +1
    # entry = close of 13:30 bar (index 2 of NY) = 1.1030; exit = last close
    expected_gross = (ny[-1] - ny[2]) / 0.0001
    assert abs(d.gross_pips - expected_gross) < 0.01
    assert abs(d.net_pips_base - (expected_gross - 0.6)) < 0.01
    assert d.placebo_long_gross is None


def test_low_only_short_continuation():
    london = [(1.1040, 1.0980)] * 24                  # breaks asia low only
    ny = [1.1000, 1.1000] + [1.1000 - 0.0002 * i for i in range(30)]
    df = _day(london_path=london, ny_closes=ny)
    d = analyze_continuation_days(df, cost_pips_side=0.3)[0]
    assert d.klass == "LOW_ONLY"
    assert d.direction == -1
    assert d.gross_pips > 0                           # short in a falling NY
    assert d.net_pips_base == d.gross_pips - 0.6


def test_placebo_on_both_day():
    london = [(1.1060, 1.0990)] * 24                  # takes both sides
    ny = [1.1020, 1.1020] + [1.1020 + 0.0001 * i for i in range(30)]
    df = _day(london_path=london, ny_closes=ny)
    d = analyze_continuation_days(df, cost_pips_side=0.3)[0]
    assert d.klass == "BOTH"
    assert d.direction is None and d.net_pips_base is None
    assert d.placebo_long_gross is not None
    assert d.placebo_short_gross is not None
    assert abs(d.placebo_long_gross + d.placebo_short_gross) < 1e-6


def test_class_rule_matches_e028():
    """Same day classified identically by E028's analyze_days."""
    from programs.E028.po3_days import analyze_days
    london = [(1.1060, 1.1020)] * 24
    df = _day(london_path=london)
    assert analyze_days(df, 0.3)[0].klass == \
        analyze_continuation_days(df, 0.3)[0].klass == "HIGH_ONLY"
