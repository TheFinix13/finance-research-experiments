#!/usr/bin/env python3
"""News calendar backfill CLI (Phase 6b, 2026-07-03).

Composes the Phase 6a Dukascopy fetcher + the Phase 6b parquet writer
+ manifest builder into a one-shot ``python ... backfill_news_calendar.py``
command. Default posture: DK primary, per-year/per-currency parquet
partitions, SHA256 manifest, no external dependencies beyond the
production venv.

FF / FRED / TE sources are stubbed here -- passing ``--sources FF`` etc
raises ``NotImplementedError`` with a clear pointer to where the real
fetcher will land (Phase 6b-followup).

Usage (see spec §4 + data/news_calendar/README.md)::

    python programs/M001_multi_agent_ensemble/scripts/backfill_news_calendar.py \
        --start 2007-01-01 --end 2026-01-01 \
        --currencies USD,EUR,GBP,JPY,CAD,AUD,NZD,CHF \
        --sources DK \
        --out programs/M001_multi_agent_ensemble/data/news_calendar

For CI-only smoke checks the ``--dry-run`` flag skips real HTTP and
just writes an empty manifest to confirm the wiring end-to-end.

Design notes:

- One CLI invocation writes one source's archive (default DK). Multi-
  source parallel runs are the user's job (they may want different
  rate limits per source).
- Backfill iterates ``year * currency`` combinations sequentially, one
  parquet per combination. Each parquet is written before moving to
  the next -- if the process dies mid-backfill, the parquets so far
  are still usable; the manifest is written last so its file listing
  reflects reality.
- Rate limiting is enforced inside ``dukascopy_fetch.fetch_events``
  (500 ms polite gap by default). Overriding via ``--min-interval``
  is exposed for advanced users who verified their local IP isn't
  throttled.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

# ------------------------------------------------------------------
# Path setup: make the M001 package importable when the script is
# executed directly (not as ``-m ...``).
# ------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.regime import dukascopy_fetch
from programs.M001_multi_agent_ensemble.sim.regime.dukascopy_fetch import (
    DEFAULT_CHUNK_DAYS,
    DEFAULT_MIN_INTERVAL_SEC,
    DukascopyFetchStats,
    RateLimiter,
    fetch_events,
)
from programs.M001_multi_agent_ensemble.sim.regime.news_calendar_writer import (
    PARSER_VERSION,
    BackfillMetadata,
    ManifestFile,
    _current_git_sha,
    compute_file_sha256,
    events_to_dataframe,
    write_events_partition,
    write_manifest,
)


log = logging.getLogger("backfill_news_calendar")


DEFAULT_CURRENCIES: tuple[str, ...] = (
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF",
)
DEFAULT_START: str = "2007-01-01"
DEFAULT_END_FALLBACK_YEARS: int = 0  # today by default
SUPPORTED_SOURCES: tuple[str, ...] = ("DK",)  # FF/FRED are Phase 6b-followup


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _parse_csv(s: str) -> tuple[str, ...]:
    return tuple(
        p.strip().upper() for p in s.split(",") if p.strip()
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="backfill_news_calendar",
        description=(
            "Backfill the M001 news-calendar archive from Dukascopy "
            "freeserv JSON (Phase 6b). Writes per-year/per-currency "
            "parquet partitions + a SHA256'd manifest."
        ),
    )
    p.add_argument(
        "--start", default=DEFAULT_START,
        help="Backfill start date UTC (YYYY-MM-DD). Default 2007-01-01 per D-Q7.",
    )
    p.add_argument(
        "--end", default=None,
        help="Backfill end date UTC (YYYY-MM-DD). Defaults to today midnight.",
    )
    p.add_argument(
        "--currencies", default=",".join(DEFAULT_CURRENCIES),
        type=_parse_csv,
        help=("Comma-separated ISO-3 currency codes. "
              f"Default: {','.join(DEFAULT_CURRENCIES)}."),
    )
    p.add_argument(
        "--sources", default="DK", type=_parse_csv,
        help=(f"Comma-separated source ids. "
              f"Supported in Phase 6b: {','.join(SUPPORTED_SOURCES)}. "
              f"FF/FRED/TE raise NotImplementedError -- follow-up work."),
    )
    p.add_argument(
        "--out", required=True, type=Path,
        help="Archive root directory (e.g. data/news_calendar).",
    )
    p.add_argument(
        "--importance", default="any",
        choices=("any", "low", "medium", "high"),
        help="Server-side importance filter. Default 'any'.",
    )
    p.add_argument(
        "--chunk-days", default=DEFAULT_CHUNK_DAYS, type=int,
        help="Days per HTTP request. Default 1 (safest).",
    )
    p.add_argument(
        "--min-interval", default=DEFAULT_MIN_INTERVAL_SEC, type=float,
        help=("Min seconds between requests. "
              f"Default {DEFAULT_MIN_INTERVAL_SEC} (2 req/sec)."),
    )
    p.add_argument(
        "--max-retries", default=4, type=int,
        help="Max retries on 5xx / 408 / 425 / 429. Default 4.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help=("Skip real HTTP. Emit an empty manifest to prove the "
              "wiring end-to-end. Used by CI smoke tests."),
    )
    p.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Verbosity: -v for INFO, -vv for DEBUG.",
    )
    return p


# ---------------------------------------------------------------------------
# Backfill core
# ---------------------------------------------------------------------------

def _iter_year_currency(
    start: datetime,
    end: datetime,
    currencies: tuple[str, ...],
):
    """Yield ``(year, currency, chunk_start, chunk_end)`` tuples, one per
    (year, currency) combination clipped to ``[start, end)``.
    """
    if end <= start:
        raise ValueError(f"end ({end}) must be strictly after start ({start})")
    year = start.year
    while year <= end.year:
        year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        clip_start = max(year_start, start)
        clip_end = min(year_end, end)
        if clip_end <= clip_start:
            year += 1
            continue
        for cur in currencies:
            yield year, cur, clip_start, clip_end
        year += 1


def run_backfill(
    *,
    start: datetime,
    end: datetime,
    currencies: tuple[str, ...],
    source: str,
    out_root: Path,
    importance: str = "any",
    chunk_days: int = DEFAULT_CHUNK_DAYS,
    min_interval_sec: float = DEFAULT_MIN_INTERVAL_SEC,
    max_retries: int = 4,
    dry_run: bool = False,
    fetcher: Callable | None = None,
) -> Path:
    """Execute one full backfill for ``source``. Returns the manifest path.

    ``fetcher`` (optional) overrides the real HTTP fetcher; the CLI
    smoke tests inject a deterministic stub. When ``None``, the default
    behaviour is to call the real
    ``dukascopy_fetch.fetch_events`` (source=DK) -- other sources raise
    ``NotImplementedError`` in Phase 6b.
    """
    if source != "DK":
        raise NotImplementedError(
            f"source {source!r} is not wired in Phase 6b; DK only. "
            f"FF/FRED live fetchers land in a follow-up commit."
        )
    if dry_run and fetcher is not None:
        raise ValueError("--dry-run and fetcher= are mutually exclusive")

    if fetcher is None and not dry_run:
        fetcher = fetch_events

    started_at = datetime.now(tz=timezone.utc)
    log.info(
        "backfill start: source=%s start=%s end=%s currencies=%s out=%s "
        "chunk_days=%d min_interval=%.2fs importance=%s dry_run=%s",
        source, start.date(), end.date(), currencies, out_root,
        chunk_days, min_interval_sec, importance, dry_run,
    )

    limiter = RateLimiter(min_interval_sec=min_interval_sec)
    aggregate_stats = DukascopyFetchStats()
    files_written: list[ManifestFile] = []
    caveats: list[str] = []

    for year, cur, chunk_start, chunk_end in _iter_year_currency(
        start, end, currencies,
    ):
        log.info(
            "fetching source=%s year=%d currency=%s window=%s..%s",
            source, year, cur, chunk_start.date(), chunk_end.date(),
        )
        if dry_run:
            events = []
            local_stats = DukascopyFetchStats()
        else:
            local_stats = DukascopyFetchStats()
            events = fetcher(
                chunk_start, chunk_end, [cur],
                importance=importance,
                rate_limiter=limiter,
                chunk_days=chunk_days,
                max_retries=max_retries,
                stats=local_stats,
            ) if fetcher is fetch_events else fetcher(
                start=chunk_start, end=chunk_end, currencies=[cur],
            )

        aggregate_stats.n_chunks += local_stats.n_chunks
        aggregate_stats.n_events += local_stats.n_events
        aggregate_stats.n_dropped += local_stats.n_dropped
        aggregate_stats.n_retries += local_stats.n_retries
        aggregate_stats.n_transport_errors += local_stats.n_transport_errors

        df = events_to_dataframe(events)
        if df.empty and not dry_run and local_stats.n_transport_errors > 0:
            caveats.append(
                f"empty parquet for {source}/{year}/{cur} (transport errors "
                f"= {local_stats.n_transport_errors}); rerun after "
                f"investigating"
            )
        target = write_events_partition(
            df, root=out_root, source=source, year=year, currency=cur,
        )
        sha = compute_file_sha256(target)
        rel_path = target.relative_to(out_root / source).as_posix()
        files_written.append(ManifestFile(
            path=rel_path,
            sha256=sha,
            n_events=len(df),
            year=year,
            currency=cur,
        ))

    finished_at = datetime.now(tz=timezone.utc)
    total_events = int(sum(f.n_events for f in files_written))
    metadata = BackfillMetadata(
        source=source,
        source_url=(
            dukascopy_fetch.DUKASCOPY_BASE_URL % {
                "path": dukascopy_fetch.DUKASCOPY_EVENTS_PATH,
            }
            if source == "DK" else source
        ),
        parser_version=PARSER_VERSION,
        parser_git_sha=_current_git_sha(),
        backfill_start_utc=started_at,
        backfill_end_utc=finished_at,
        total_events=total_events,
        total_dropped=aggregate_stats.n_dropped,
        total_retries=aggregate_stats.n_retries,
        total_transport_errors=aggregate_stats.n_transport_errors,
        n_chunks=aggregate_stats.n_chunks,
        caveats=caveats,
    )
    manifest_path = write_manifest(
        root=out_root, source=source, files=files_written, metadata=metadata,
    )
    log.info(
        "backfill complete: source=%s files=%d events=%d transport_errors=%d "
        "elapsed=%.1fs manifest=%s",
        source, len(files_written), total_events,
        aggregate_stats.n_transport_errors,
        (finished_at - started_at).total_seconds(), manifest_path,
    )
    return manifest_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    level = (
        logging.DEBUG if args.verbose >= 2
        else logging.INFO if args.verbose >= 1
        else logging.WARNING
    )
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )

    start = _parse_date(args.start)
    end = (
        _parse_date(args.end) if args.end
        else datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
    )
    args.out.mkdir(parents=True, exist_ok=True)

    for source in args.sources:
        if source not in SUPPORTED_SOURCES:
            log.error(
                "source %s is not wired in Phase 6b; supported: %s",
                source, SUPPORTED_SOURCES,
            )
            return 2
        run_backfill(
            start=start,
            end=end,
            currencies=args.currencies,
            source=source,
            out_root=args.out,
            importance=args.importance,
            chunk_days=args.chunk_days,
            min_interval_sec=args.min_interval,
            max_retries=args.max_retries,
            dry_run=args.dry_run,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
