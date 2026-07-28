"""E027 detector unit tests: hand-built geometry with known labels."""
from __future__ import annotations

import numpy as np
import pandas as pd

from programs.E027.sweep_validity import detect_validity_sweeps

LOOKBACK = 5


def _frame(closes: list[float], spread: float = 0.05) -> pd.DataFrame:
    c = np.asarray(closes, dtype=float)
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) + spread
    lo = np.minimum(o, c) - spread
    idx = pd.date_range("2024-01-01", periods=len(c), freq="1h", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c,
                         "volume": np.ones(len(c))}, index=idx)


def _custom_frame(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """rows = (open, high, low, close)."""
    a = np.asarray(rows, dtype=float)
    idx = pd.date_range("2024-01-01", periods=len(a), freq="1h", tz="UTC")
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1], "low": a[:, 2],
                         "close": a[:, 3],
                         "volume": np.ones(len(a))}, index=idx)


def _bar(price: float, wick: float = 0.02) -> tuple:
    return (price, price + wick, price - wick, price)


def test_valid_sellside_sweep():
    """Swing high at 110, swing low at 100, rally CLOSES above 110 (valid),
    then a wick below 100 that closes back above => valid sellside sweep."""
    rows = []
    rows += [_bar(p) for p in (104, 105, 106, 107, 108)]
    rows += [_bar(110)]                       # swing high @ idx 5
    rows += [_bar(p) for p in (108, 106, 104, 102)]
    rows += [_bar(100)]                       # swing low @ idx 10
    rows += [_bar(p) for p in (103, 105, 108, 111, 112)]  # closes > 110: BOS
    rows += [_bar(p) for p in (111, 110, 109, 108, 107)]
    # sweep bar: low pierces 100 - wick(=99.98), close back above
    rows += [(106, 106.1, 99.90, 105)]
    rows += [_bar(p) for p in (106, 107, 108, 106, 105, 104)]
    df = _custom_frame(rows)
    events = detect_validity_sweeps(df, lookback=LOOKBACK)
    sells = [e for e in events if e.side == "sellside"]
    assert len(sells) == 1
    e = sells[0]
    assert e.valid is True
    assert e.direction == +1
    assert e.swing_index == 10
    assert e.origin_index == 5
    assert df["low"].iloc[e.index] < e.level < df["close"].iloc[e.index]


def test_invalid_sellside_sweep():
    """Same geometry but the bounce NEVER closes above the origin high
    => invalid sellside sweep."""
    rows = []
    rows += [_bar(p) for p in (104, 105, 106, 107, 108)]
    rows += [_bar(110)]                       # swing high @ idx 5
    rows += [_bar(p) for p in (108, 106, 104, 102)]
    rows += [_bar(100)]                       # swing low @ idx 10
    rows += [_bar(p) for p in (103, 105, 107, 108, 107)]  # never closes > 110
    rows += [_bar(p) for p in (106, 105, 104, 103, 102)]
    rows += [(102, 102.1, 99.90, 104)]        # sweep of 100-wick level
    rows += [_bar(p) for p in (104, 105, 104, 103, 104, 105)]
    df = _custom_frame(rows)
    events = detect_validity_sweeps(df, lookback=LOOKBACK)
    sells = [e for e in events if e.side == "sellside"]
    assert len(sells) == 1
    assert sells[0].valid is False


def test_clean_break_kills_level():
    """A CLOSE below the swing low ends the level: no sweep event."""
    rows = []
    rows += [_bar(p) for p in (104, 105, 106, 107, 108)]
    rows += [_bar(110)]
    rows += [_bar(p) for p in (108, 106, 104, 102)]
    rows += [_bar(100)]                       # swing low @ idx 10
    rows += [_bar(p) for p in (103, 105, 107, 105, 104)]
    rows += [_bar(p) for p in (103, 102, 101)]
    rows += [(101, 101.1, 98.5, 98.8)]        # closes THROUGH the level
    rows += [(98.8, 99.9, 97.5, 99.5)]        # would-be sweep, too late
    rows += [_bar(p) for p in (100, 101, 102, 103, 104, 105)]
    df = _custom_frame(rows)
    events = detect_validity_sweeps(df, lookback=LOOKBACK)
    sells = [e for e in events if e.side == "sellside" and e.swing_index == 10]
    assert not sells


def test_buyside_mirror():
    """Swing low at 100 (origin), swing high at 110; drop closes below 100
    (valid), then wick above 110 closing back below => valid buyside."""
    rows = []
    rows += [_bar(p) for p in (106, 105, 104, 103, 102)]
    rows += [_bar(100)]                       # swing low @ idx 5 (origin)
    rows += [_bar(p) for p in (102, 104, 106, 108)]
    rows += [_bar(110)]                       # swing high @ idx 10
    rows += [_bar(p) for p in (107, 105, 102, 99, 98)]   # closes < 100: BOS
    rows += [_bar(p) for p in (99, 100, 101, 102, 103)]
    rows += [(104, 110.15, 103.9, 105)]       # sweep of 110+wick(=110.02)
    rows += [_bar(p) for p in (104, 103, 102, 103, 104, 105)]
    df = _custom_frame(rows)
    events = detect_validity_sweeps(df, lookback=LOOKBACK)
    buys = [e for e in events if e.side == "buyside"]
    assert len(buys) == 1
    e = buys[0]
    assert e.valid is True
    assert e.direction == -1
    assert e.origin_index == 5


def test_events_are_causal():
    """Event index must be >= swing confirmation (swing_index + lookback)."""
    rng = np.random.default_rng(3)
    c = 100 + np.cumsum(rng.normal(0, 0.5, size=500))
    df = _frame(list(c))
    for e in detect_validity_sweeps(df, lookback=LOOKBACK):
        assert e.index >= e.swing_index + LOOKBACK
        assert e.origin_index < e.swing_index
