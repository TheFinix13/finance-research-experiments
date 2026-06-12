"""Data access: main-repo parquet cache bridge + synthetic bars for tests."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def load_frames(symbol: str, timeframes: list[str], *,
                days: int = 400, start: str | datetime | None = None,
                end: str | datetime | None = None) -> dict[str, pd.DataFrame]:
    """Load OHLCV frames from eurusd-ai-agent's BarLoader/parquet cache.

    Explicit ``start``/``end`` (ISO strings or datetimes) override ``days``
    — used by the staged protocol's split discipline. Requires the main
    repo on PYTHONPATH (see README); raises ImportError otherwise.
    """
    try:
        from agent.config import load_config
        from agent.data.loader import BarLoader
        from agent.types import Timeframe
    except ImportError as e:
        raise ImportError(
            "eurusd-ai-agent not importable. Run with "
            "PYTHONPATH=/path/to/eurusd-ai-agent:. (see README)") from e

    def _to_dt(value, default: datetime) -> datetime:
        if value is None:
            return default
        if isinstance(value, str):
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    end = _to_dt(end, datetime.now(tz=timezone.utc))
    start = _to_dt(start, end - timedelta(days=days))
    frames: dict[str, pd.DataFrame] = {}
    for tf in timeframes:
        df = loader.get(symbol, Timeframe(tf), start, end, refresh=False)
        if df is None or df.empty:
            log.warning("no cached data for %s %s", symbol, tf)
            continue
        frames[tf] = df
    return frames


def synthetic_frame(n: int = 600, *, seed: int = 7, start_price: float = 1.10,
                    tf_hours: int = 4) -> pd.DataFrame:
    """Mean-reverting random walk OHLCV frame for tests/demos."""
    rng = np.random.default_rng(seed)
    drift = rng.normal(0, 0.0012, size=n)
    # Mild mean reversion keeps prices in a realistic band.
    closes = np.empty(n)
    price = start_price
    for i in range(n):
        price += drift[i] - 0.05 * (price - start_price) * 0.01
        closes[i] = price
    opens = np.concatenate([[start_price], closes[:-1]])
    spread = np.abs(rng.normal(0, 0.0006, size=n)) + 0.0002
    highs = np.maximum(opens, closes) + spread
    lows = np.minimum(opens, closes) - spread
    volume = rng.integers(50, 500, size=n).astype(float)
    idx = pd.date_range("2024-01-01", periods=n, freq=f"{tf_hours}h", tz="UTC")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows,
                         "close": closes, "volume": volume}, index=idx)
