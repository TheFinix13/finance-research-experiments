"""Annotated confluence charts (headless mplfinance, vault-snapshot style)."""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # must precede any pyplot import

import mplfinance as mpf  # noqa: E402
import pandas as pd  # noqa: E402

from conflab.confluence import ConfluenceBand  # noqa: E402

log = logging.getLogger(__name__)


def render_confluence_chart(
    df: pd.DataFrame,
    bands: list[ConfluenceBand],
    out_path: Path | str,
    *,
    title: str,
    lookback: int = 120,
    max_bands: int = 8,
) -> Path | None:
    """Render the last ``lookback`` candles with the top confluence bands as
    shaded zones + centre lines. Never raises; returns None on failure."""
    try:
        window = df.iloc[-lookback:]
        if len(window) < 2:
            return None
        plot_df = window.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume"})

        lo, hi = float(window["low"].min()), float(window["high"].max())
        pad = (hi - lo) * 0.15
        visible = [b for b in bands[:max_bands]
                   if lo - pad <= b.center <= hi + pad]

        hlines = [b.center for b in visible]
        # Stronger bands drawn more prominently.
        max_score = max((b.score for b in visible), default=1.0) or 1.0
        widths = [0.8 + 1.6 * (b.score / max_score) for b in visible]

        kwargs: dict = {
            "type": "candle",
            "style": "yahoo",
            "title": title,
            "ylabel": "",
            "figsize": (14, 8),
            "tight_layout": True,
            "savefig": {"fname": str(out_path), "dpi": 110},
        }
        if hlines:
            kwargs["hlines"] = {
                "hlines": hlines,
                "colors": ["purple"] * len(hlines),
                "linestyle": "--",
                "linewidths": widths,
            }
        if visible:
            kwargs["fill_between"] = [
                {"y1": b.low, "y2": b.high, "alpha": 0.12, "color": "purple"}
                for b in visible
            ]
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        mpf.plot(plot_df, **kwargs)
        return out
    except Exception as e:
        log.warning("confluence chart render failed for %s: %s", out_path, e)
        return None
