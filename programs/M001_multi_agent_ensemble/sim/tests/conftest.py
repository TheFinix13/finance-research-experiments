"""Shared pytest helpers for sim/tests/."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Ensure the repo root is on sys.path so the package imports resolve.
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.core.types import (  # noqa: E402
    MarketState,
)


def make_bar(
    *,
    tick_id: int,
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    ts: datetime | None = None,
    open_: float = 1.0900,
    high: float = 1.0915,
    low: float = 1.0890,
    close: float = 1.0905,
    volume: float = 100.0,
    bid_low: float | None = 1.0888,
    ask_high: float | None = 1.0917,
) -> MarketState:
    if ts is None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MarketState(
        tick_id=int(tick_id),
        symbol=symbol,
        timeframe=timeframe,
        as_of=ts,
        open=float(open_),
        high=float(high),
        low=float(low),
        close=float(close),
        volume=float(volume),
        bid_low=bid_low,
        ask_high=ask_high,
    )


def make_bars(
    *,
    n: int,
    symbol: str = "EURUSD",
    timeframe: str = "H1",
) -> list[MarketState]:
    from datetime import timedelta
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        make_bar(
            tick_id=i,
            symbol=symbol,
            timeframe=timeframe,
            ts=base + timedelta(hours=i),
            close=1.0900 + i * 0.0001,
        )
        for i in range(n)
    ]
