"""Φ5 news calendar adapter -- reads the parquet archive shipped by the
backfill script and exposes both a raw event-table (`load_news_events`)
and a per-bar proximity series (`load_news_calendar`).

Specification: `programs/M001_multi_agent_ensemble/specs/news_calendar_wiring.md`
sections 3 + 5. All 8 D-Q decisions from prep doc D are locked and
recited here:

- **D-Q1**: Dukascopy freeserv JSON = primary source. ``sources=("DK",)``
  is the default for both public entry points.
- **D-Q2**: FF community archive + FRED cross-check are documented as
  fallbacks; the actual live HTTP for those sources lives in
  ``news_calendar_sources.py`` (Phase M ships stubs; real fetchers
  land post-G7).
- **D-Q3**: $0/month steady-state. No paid-tier code paths ship in
  Phase M; Trading Economics stays as a documented override only.
- **D-Q4**: The backfill script + manifest are what ships in git; the
  parquet archive under ``data/news_calendar/`` is *not* committed
  (see ``.gitignore``). Adapter tolerates an empty archive.
- **D-Q5**: Per-agent timeframe is exposed via ``pre_event_bars`` +
  ``post_event_bars`` on the adapter surface. The per-agent
  windowing helper (``sim/regime/news_windowing.py``) reads each
  agent's ``home_tf`` and fills these knobs sensibly.
- **D-Q6**: Column name is ``news_calendar`` (never ``news``) --
  keeps this exogenous tag visibly distinct from the OHLCV-derived
  ``news`` regime class that was retired.
- **D-Q7**: 2007-01-01 backfill horizon approved; the adapter accepts
  any start >= 2007-01-01 without complaint.
- **D-Q8**: Integration test #9 runs every CI run. Adapter has no
  ``--slow`` gate.

Non-goals (stay DEFERRED-BEYOND-G7): heavy backfill data download,
data commit, Streamlit hand-labeling UI, F18 KPI join, dashboard panel
updates, per-agent wiring inside ``intend()``, changes to
``sim/regime/classifier.py``, any production-repo modifications.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public schema
# ---------------------------------------------------------------------------

# Spec §3.1 columns, in declared order. The parquet archive uses these
# names verbatim so the adapter and any downstream consumer share one
# canonical schema regardless of source.
EVENT_TABLE_COLUMNS: tuple[str, ...] = (
    "timestamp",           # datetime64[ns, UTC]
    "currency",            # ISO-3 string ("USD", "EUR", ...)
    "event",               # verbatim event name
    "importance",          # int8 in {1, 2, 3}
    "actual",              # float64 or NaN
    "forecast",            # float64 or NaN
    "previous",            # float64 or NaN
    "unit",                # string or NaN
    "source",              # "DK" | "FF" | "FRED" | "TE"
    "source_event_id",     # source-native id or hash-based fallback
    "ingested_at_utc",     # datetime64[ns, UTC]
)

# Importance mapping (§3.3).
IMPORTANCE_LOW = 1
IMPORTANCE_MEDIUM = 2
IMPORTANCE_HIGH = 3

# Source precedence (§3.3 dedup rule: DK > FF > FRED > TE).
SOURCE_PRECEDENCE: dict[str, int] = {"DK": 0, "FF": 1, "FRED": 2, "TE": 3}

# Default archive root -- keeps callers who don't pass an explicit path
# reading from the standard M001 layout.
DEFAULT_ARCHIVE_ROOT = Path(
    "programs/M001_multi_agent_ensemble/data/news_calendar"
)

# Default currencies matching the pre-redesign
# validate_real.load_news_calendar behaviour.
DEFAULT_CURRENCIES: tuple[str, ...] = ("USD", "EUR")

# Default sources per D-Q1 (Dukascopy primary; fallback chain wires
# through news_calendar_sources.resolve_chain).
DEFAULT_SOURCES: tuple[str, ...] = ("DK",)

# Default per-minute window pair for intraday callers (spec §5.4).
DEFAULT_PRE_EVENT_MINUTES = 5
DEFAULT_POST_EVENT_MINUTES = 60


@dataclass(frozen=True)
class NewsEvent:
    """One row of the archive parquet, in dataclass form.

    Kept intentionally distinct from the production
    ``agent/news/calendar.NewsEvent`` schema (which uses
    ``time_utc, currency, impact:str, title, all_day``). This Φ5-flavour
    dataclass is the research adapter's own; the FF fallback adapter
    maps production rows into this schema on the way in.
    """

    timestamp: Optional[datetime]  # None <-> NaT (All-Day / Tentative)
    currency: str
    event: str
    importance: int
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    unit: Optional[str] = None
    source: str = "DK"
    source_event_id: Optional[str] = None
    ingested_at_utc: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.importance not in (IMPORTANCE_LOW, IMPORTANCE_MEDIUM,
                                    IMPORTANCE_HIGH):
            raise ValueError(
                f"importance must be 1/2/3, got {self.importance!r}"
            )
        if self.source not in SOURCE_PRECEDENCE:
            raise ValueError(f"unknown source {self.source!r}; expected "
                             f"one of {tuple(SOURCE_PRECEDENCE)}")
        if self.timestamp is not None and self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware (UTC); got naive datetime"
            )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def load_news_events(
    start: datetime,
    end: datetime,
    *,
    currencies: Iterable[str] = DEFAULT_CURRENCIES,
    sources: Iterable[str] = DEFAULT_SOURCES,
    importance_min: int = IMPORTANCE_HIGH,
    archive_root: Path | str | None = None,
):
    """Load the raw event table from the parquet archive.

    Returns a ``pandas.DataFrame`` with the columns declared in
    ``EVENT_TABLE_COLUMNS``. Empty DataFrame (with the schema) when the
    archive has no matching rows. Returns ``None`` when the archive
    root does not exist -- callers must distinguish this from "archive
    present, no matching events" (spec §3.3 edge case #1).

    Half-open window: rows with ``timestamp >= start AND
    timestamp < end`` are included.
    """
    try:
        import pandas as pd
    except ImportError as exc:      # pragma: no cover -- dev environment
        raise ImportError(
            "pandas is required for load_news_events; install via the "
            "production venv"
        ) from exc

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError(
            "start and end must be timezone-aware (UTC); got naive datetimes"
        )
    if end <= start:
        raise ValueError(f"end ({end}) must be strictly after start ({start})")

    root = Path(archive_root) if archive_root is not None else DEFAULT_ARCHIVE_ROOT
    if not root.exists():
        log.warning(
            "news_calendar archive %s does not exist; returning None", root,
        )
        return None

    cur_filter = _clean_currencies(currencies)
    if cur_filter is None:
        return None
    if not cur_filter:
        # Empty currencies tuple -> defensive None (§3.3 edge case).
        log.warning(
            "load_news_events called with empty currencies tuple; None"
        )
        return None

    src_filter = tuple(str(s).upper() for s in sources)
    imp_min = _clamp_importance(importance_min)

    # Two archive layouts are supported: per-year/per-currency parquet
    # (backfill script default) OR one flat events.parquet in the root
    # (test-fixture layout). Try the flat file first for cheap discovery.
    flat = root / "events.parquet"
    if flat.exists():
        df = pd.read_parquet(flat)
    else:
        pieces = []
        # per-year/per-currency layout: <root>/<yyyy>/<CUR>.parquet
        for year_dir in sorted(root.glob("[0-9][0-9][0-9][0-9]")):
            if not year_dir.is_dir():
                continue
            year = int(year_dir.name)
            if year < start.year - 1 or year > end.year + 1:
                continue
            for cur in cur_filter:
                pq = year_dir / f"{cur}.parquet"
                if pq.exists():
                    pieces.append(pd.read_parquet(pq))
        if not pieces:
            log.warning(
                "news_calendar archive %s has no matching parquet partitions "
                "for %s..%s in %s", root, start.date(), end.date(),
                cur_filter,
            )
            return None
        df = pd.concat(pieces, ignore_index=True)

    if df.empty:
        return _empty_events_frame()

    df = _coerce_schema(df)
    return _filter_events(
        df, start=start, end=end, currencies=cur_filter,
        sources=src_filter, importance_min=imp_min,
    )


def load_news_calendar(
    index,
    *,
    cache_path: Path | str | None = None,
    window_bars: int = 2,
    currencies: Iterable[str] = DEFAULT_CURRENCIES,
    sources: Iterable[str] = DEFAULT_SOURCES,
    importance_min: int = IMPORTANCE_HIGH,
    pre_event_bars: int | None = None,
    post_event_bars: int | None = None,
    pre_event_minutes: int = DEFAULT_PRE_EVENT_MINUTES,
    post_event_minutes: int = DEFAULT_POST_EVENT_MINUTES,
    archive_root: Path | str | None = None,
):
    """Return a per-bar ``pandas.Series[bool]`` aligned to ``index`` where
    each element is True iff at least one event matching the filter falls
    within the bar's proximity window. Spec §5.1 signature.

    ``cache_path`` is accepted for backwards compatibility with the
    legacy ``sim.regime.validate_real.load_news_calendar`` shape. When
    both ``archive_root`` and ``cache_path`` are None, the archive is
    read from :data:`DEFAULT_ARCHIVE_ROOT`.

    Auto-detects intraday vs bar-count windowing (spec §5.4): if the
    inferred bar frequency is <= 1 hour, ``pre_event_minutes`` /
    ``post_event_minutes`` are used; otherwise
    ``pre_event_bars`` / ``post_event_bars`` fall back to
    ``window_bars`` when None.

    Returns ``None`` when the archive is missing or every requested
    source is empty in the window (§3.3 edge case). Returns an
    all-False series when the archive is present but no matching event
    is in the window.
    """
    try:
        import pandas as pd
    except ImportError as exc:      # pragma: no cover
        raise ImportError(
            "pandas is required for load_news_calendar"
        ) from exc

    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(
            f"index must be a pandas.DatetimeIndex, got {type(index)!r}"
        )
    if index.tz is None:
        raise ValueError(
            "index must be timezone-aware; convert with tz_localize('UTC')"
        )
    if len(index) == 0:
        return pd.Series([], dtype=bool, index=index, name="news_calendar")

    # Resolve archive root: cache_path (legacy) -> archive_root -> default.
    root = archive_root if archive_root is not None else cache_path
    if root is None:
        root = DEFAULT_ARCHIVE_ROOT

    # Half-open window over the full index.
    start = index[0].to_pydatetime().astimezone(timezone.utc)
    end = index[-1].to_pydatetime().astimezone(timezone.utc)
    # +1 tick for inclusion of end bar events.
    end_plus = end + (index[-1] - index[-2]).to_pytimedelta() if len(index) >= 2 else end

    events = load_news_events(
        start, end_plus,
        currencies=currencies, sources=sources,
        importance_min=importance_min, archive_root=root,
    )
    if events is None:
        return None

    # Infer bar frequency for windowing mode selection (§5.4).
    freq = _infer_freq_seconds(index)
    if freq is not None and freq <= 3600:
        return _tag_bars_by_minutes(
            index, events,
            pre_minutes=pre_event_minutes, post_minutes=post_event_minutes,
        )
    # H4 / D1 path.
    pre_n = pre_event_bars if pre_event_bars is not None else window_bars
    post_n = post_event_bars if post_event_bars is not None else window_bars
    return _tag_bars_by_count(index, events, pre_bars=pre_n, post_bars=post_n)


def tag_bars_with_news(
    bars_index,
    *,
    symbol_pair: str,
    sources: Iterable[str] = DEFAULT_SOURCES,
    importance_min: int = IMPORTANCE_HIGH,
    archive_root: Path | str | None = None,
    **window_kwargs,
):
    """Convenience wrapper: infer currencies from ``symbol_pair`` and
    forward to ``load_news_calendar``.

    Currency mapping:
    - Standard 6-letter FX pair (e.g. ``"EURUSD"``): first + last 3
      letters -> ``("EUR", "USD")``.
    - Metal-quoted-in-USD (``"XAUUSD"``, ``"XAGUSD"``): USD only per
      spec §5.3 default.
    - 3-letter shorthand assumed USD-quoted (rarely seen; treat as
      that currency + USD).
    - Anything unrecognised: raises ``ValueError``.
    """
    sp = symbol_pair.upper().strip()
    if sp[:3] in ("XAU", "XAG", "XPT", "XPD"):
        currencies = ("USD",)
    elif len(sp) == 6 and sp.isalpha():
        currencies = (sp[:3], sp[3:])
    else:
        raise ValueError(f"unsupported symbol_pair: {symbol_pair!r}")

    return load_news_calendar(
        bars_index, currencies=currencies, sources=sources,
        importance_min=importance_min, archive_root=archive_root,
        **window_kwargs,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_events_frame():
    """Return an empty DataFrame with the canonical schema."""
    import pandas as pd
    return pd.DataFrame({
        "timestamp": pd.Series([], dtype="datetime64[ns, UTC]"),
        "currency": pd.Series([], dtype="string"),
        "event": pd.Series([], dtype="string"),
        "importance": pd.Series([], dtype="int8"),
        "actual": pd.Series([], dtype="float64"),
        "forecast": pd.Series([], dtype="float64"),
        "previous": pd.Series([], dtype="float64"),
        "unit": pd.Series([], dtype="string"),
        "source": pd.Series([], dtype="string"),
        "source_event_id": pd.Series([], dtype="string"),
        "ingested_at_utc": pd.Series([], dtype="datetime64[ns, UTC]"),
    })


def _coerce_schema(df):
    """Normalise dtypes so downstream code doesn't have to defensively cast."""
    import pandas as pd

    df = df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if "ingested_at_utc" in df.columns:
        df["ingested_at_utc"] = pd.to_datetime(df["ingested_at_utc"], utc=True)
    for col in ("currency", "event", "unit", "source", "source_event_id"):
        if col in df.columns:
            df[col] = df[col].astype("string")
    if "importance" in df.columns:
        df["importance"] = df["importance"].astype("int8")
    for col in ("actual", "forecast", "previous"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    # Order columns; ignore extras.
    keep = [c for c in EVENT_TABLE_COLUMNS if c in df.columns]
    return df[keep]


def _filter_events(
    df,
    *,
    start,
    end,
    currencies,
    sources,
    importance_min,
):
    """Apply timestamp / currency / source / importance filters."""
    if df.empty:
        return df
    mask = (df["timestamp"] >= start) & (df["timestamp"] < end)
    mask &= df["currency"].isin(list(currencies))
    if sources:
        mask &= df["source"].isin(list(sources))
    mask &= df["importance"] >= int(importance_min)
    out = df.loc[mask].copy()
    # Preserve deterministic order for reproducibility -- sort by
    # timestamp then source precedence so DK rows appear first when a
    # timestamp collides with FF/FRED cross-sourced rows.
    out["_src_prec"] = out["source"].map(SOURCE_PRECEDENCE).fillna(9)
    out = out.sort_values(
        by=["timestamp", "_src_prec"], kind="mergesort",
    ).drop(columns=["_src_prec"]).reset_index(drop=True)
    return out


def _clean_currencies(currencies) -> tuple[str, ...] | None:
    """Return canonical currency tuple, or None on error/empty."""
    if currencies is None:
        raise ValueError("currencies=None is not allowed; pass a tuple")
    cur = tuple(str(c).upper() for c in currencies)
    return cur


def _clamp_importance(importance_min) -> int:
    """Clamp importance_min to [1, 3] with a warning for out-of-range."""
    v = int(importance_min)
    if v < 1:
        log.warning("importance_min=%d clamped to 1", v)
        return 1
    if v > 3:
        log.warning(
            "importance_min=%d > 3 filters out every event; caller likely "
            "has a bug",
            v,
        )
        return v      # return as-is so downstream returns all-false honestly
    return v


def _infer_freq_seconds(index) -> int | None:
    """Median inter-bar gap in seconds. None when index has < 2 rows."""
    import pandas as pd
    if len(index) < 2:
        return None
    diffs = pd.Series(index).diff().dropna().dt.total_seconds()
    if len(diffs) == 0:
        return None
    return int(diffs.median())


def _tag_bars_by_count(index, events, *, pre_bars: int, post_bars: int):
    """H4 / D1 path: mark a window of pre_bars before + post_bars after
    each event bar as True.
    """
    import pandas as pd
    labels = pd.Series(False, index=index, name="news_calendar")
    if events.empty:
        return labels
    # For each event, find the bar it lands in (searchsorted right-side)
    # and set +/- window.
    idx_arr = index.to_numpy()
    for ts in events["timestamp"].dropna():
        pos = int(index.searchsorted(ts, side="right")) - 1
        if pos < 0:
            continue
        if pos >= len(index):
            continue
        lo = max(0, pos - pre_bars)
        hi = min(len(index), pos + post_bars + 1)
        labels.iloc[lo:hi] = True
    return labels


def _tag_bars_by_minutes(
    index,
    events,
    *,
    pre_minutes: int,
    post_minutes: int,
):
    """Intraday path: mark a bar True iff any event's timestamp falls
    inside [bar_time - pre_minutes, bar_time + post_minutes].
    """
    import pandas as pd
    labels = pd.Series(False, index=index, name="news_calendar")
    if events.empty:
        return labels
    ts_series = events["timestamp"].dropna().sort_values()
    if ts_series.empty:
        return labels
    pre_delta = pd.Timedelta(minutes=int(pre_minutes))
    post_delta = pd.Timedelta(minutes=int(post_minutes))
    # For each event, expand a window and set-True on matching index.
    for ts in ts_series:
        lo = ts - pre_delta
        hi = ts + post_delta
        mask = (index >= lo) & (index <= hi)
        labels.loc[mask] = True
    return labels


__all__ = [
    "NewsEvent",
    "EVENT_TABLE_COLUMNS",
    "IMPORTANCE_LOW",
    "IMPORTANCE_MEDIUM",
    "IMPORTANCE_HIGH",
    "SOURCE_PRECEDENCE",
    "DEFAULT_ARCHIVE_ROOT",
    "DEFAULT_CURRENCIES",
    "DEFAULT_SOURCES",
    "DEFAULT_PRE_EVENT_MINUTES",
    "DEFAULT_POST_EVENT_MINUTES",
    "load_news_events",
    "load_news_calendar",
    "tag_bars_with_news",
]
