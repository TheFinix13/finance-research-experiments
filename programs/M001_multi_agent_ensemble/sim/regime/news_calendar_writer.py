"""News calendar archive writer (Phase 6b, 2026-07-03).

Companion to ``dukascopy_fetch.py`` (Phase 6a) and ``news_calendar.py``
(Phase M read side). Consumes the flat list-of-dict rows emitted by any
source fetcher and writes them to the per-source / per-year / per-
currency parquet partition documented in spec §4.3, plus a SHA256'd
``_manifest.json`` for reproducibility (§4.7).

The writer is intentionally source-agnostic: it takes rows already
normalised to the ``EVENT_TABLE_COLUMNS`` schema declared in
``news_calendar.py``. Dukascopy-specific parsing lives in
``dukascopy_fetch.normalize_dukascopy_event``; FF / FRED / TE will get
their own normalisers in Phase 6b-followups.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from programs.M001_multi_agent_ensemble.sim.regime.news_calendar import (
    EVENT_TABLE_COLUMNS,
    SOURCE_PRECEDENCE,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFrame construction
# ---------------------------------------------------------------------------

def events_to_dataframe(events: Iterable[Mapping[str, Any]]):
    """Convert canonical event dicts to a pandas DataFrame with the
    exact ``EVENT_TABLE_COLUMNS`` schema + dtypes documented in
    ``news_calendar.py``.

    Missing optional columns are filled with NaN / NaT. Extra columns
    in the input are dropped silently. Empty input returns an empty
    frame with the correct schema (mirrors ``_empty_events_frame``
    behaviour in the read side).
    """
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:                       # pragma: no cover
        raise ImportError(
            "pandas + numpy required for events_to_dataframe"
        ) from exc

    rows = list(events)
    if not rows:
        # Empty schema shell so callers can .to_parquet() without
        # branching. dtypes preserved exactly.
        return pd.DataFrame({
            "timestamp": pd.Series(
                pd.array([], dtype="datetime64[ns, UTC]"),
            ),
            "currency": pd.Series([], dtype="string"),
            "event": pd.Series([], dtype="string"),
            "importance": pd.Series([], dtype="int8"),
            "actual": pd.Series([], dtype="float64"),
            "forecast": pd.Series([], dtype="float64"),
            "previous": pd.Series([], dtype="float64"),
            "unit": pd.Series([], dtype="string"),
            "source": pd.Series([], dtype="string"),
            "source_event_id": pd.Series([], dtype="string"),
            "ingested_at_utc": pd.Series(
                pd.array([], dtype="datetime64[ns, UTC]"),
            ),
        })

    df = pd.DataFrame(rows)
    # Fill any missing columns with NaN so the schema is stable.
    for col in EVENT_TABLE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[list(EVENT_TABLE_COLUMNS)]

    # Coerce dtypes explicitly (mirrors _coerce_schema in the read side
    # but does it at ingest time so the parquet is already canonical).
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["currency"] = df["currency"].astype("string").str.upper()
    df["event"] = df["event"].astype("string")
    # importance must be within {1,2,3}; anything else -> drop the row
    # with a warning (caller normalisers should have caught this, but
    # defensive belt-and-braces).
    imp = pd.to_numeric(df["importance"], errors="coerce")
    valid = imp.isin([1, 2, 3])
    if not valid.all():
        n_bad = int((~valid).sum())
        log.warning(
            "events_to_dataframe dropped %d rows with out-of-range importance",
            n_bad,
        )
        df = df.loc[valid].copy()
        imp = imp.loc[valid]
    df["importance"] = imp.astype("int8")
    for float_col in ("actual", "forecast", "previous"):
        df[float_col] = pd.to_numeric(df[float_col], errors="coerce")
    df["unit"] = df["unit"].astype("string")
    df["source"] = df["source"].astype("string").str.upper()
    df["source_event_id"] = df["source_event_id"].astype("string")
    df["ingested_at_utc"] = pd.to_datetime(
        df["ingested_at_utc"], utc=True, errors="coerce",
    )

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Parquet partition writer
# ---------------------------------------------------------------------------

def write_events_partition(
    df,
    *,
    root: Path | str,
    source: str,
    year: int,
    currency: str,
    compression: str = "snappy",
) -> Path:
    """Write ``df`` to ``<root>/<SOURCE>/<year>/<CURRENCY>.parquet``.

    Creates parent dirs. Overwrites atomically via ``pyarrow`` write
    (which itself falls back to fsync-then-rename). Returns the written
    path.
    """
    src = str(source).upper()
    if src not in SOURCE_PRECEDENCE:
        raise ValueError(
            f"unknown source {source!r}; expected one of "
            f"{tuple(SOURCE_PRECEDENCE)}"
        )
    if year < 1900 or year > 2100:
        raise ValueError(f"year {year} looks wrong; sanity-check the caller")
    cur = str(currency).upper().strip()
    if not cur:
        raise ValueError("currency must be a non-empty string")

    root_path = Path(root)
    target = root_path / src / str(year) / f"{cur}.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target, compression=compression, index=False)
    log.info(
        "Wrote %s (%d events, %s compression)",
        target, len(df), compression,
    )
    return target


# ---------------------------------------------------------------------------
# SHA256 checksum
# ---------------------------------------------------------------------------

def compute_file_sha256(path: Path | str, *, chunk_bytes: int = 65536) -> str:
    """Hex SHA-256 for ``path``. Streams the file in chunks so this is
    safe on multi-GB archives.
    """
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

@dataclass
class ManifestFile:
    """One parquet partition in the manifest."""

    path: str                       # relative to source root, POSIX slashes
    sha256: str
    n_events: int
    year: int
    currency: str


@dataclass
class BackfillMetadata:
    """Provenance fields written into the manifest header."""

    source: str                     # "DK", "FF", "FRED", "TE"
    source_url: str
    parser_version: str
    parser_git_sha: str | None
    backfill_start_utc: datetime
    backfill_end_utc: datetime
    total_events: int
    total_dropped: int = 0
    total_retries: int = 0
    total_transport_errors: int = 0
    n_chunks: int = 0
    caveats: list[str] = field(default_factory=list)


def _current_git_sha(repo_root: Path | None = None) -> str | None:
    """Return HEAD SHA of the repo the writer is running in (best-
    effort; returns None on failure since a manifest is still useful
    without it).
    """
    try:
        cwd = str(repo_root) if repo_root is not None else None
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, cwd=cwd,
            timeout=5.0,
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired):
        return None


def write_manifest(
    *,
    root: Path | str,
    source: str,
    files: Iterable[ManifestFile],
    metadata: BackfillMetadata,
    now_utc: datetime | None = None,
) -> Path:
    """Write ``<root>/<SOURCE>/_manifest.json``.

    Existing manifests are overwritten. Callers are expected to run the
    backfill in "add-only" mode -- an updater CLI that re-fetches only
    the tail is a Phase 6b-followup.
    """
    src = str(source).upper()
    root_path = Path(root)
    target = root_path / src / "_manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    file_list = sorted(
        list(files), key=lambda f: (f.year, f.currency),
    )
    payload = {
        "source": src,
        "written_at_utc": (now_utc or datetime.now(tz=timezone.utc)).isoformat(),
        "metadata": {
            "source_url": metadata.source_url,
            "parser_version": metadata.parser_version,
            "parser_git_sha": metadata.parser_git_sha,
            "backfill_start_utc": metadata.backfill_start_utc.isoformat(),
            "backfill_end_utc": metadata.backfill_end_utc.isoformat(),
            "total_events": int(metadata.total_events),
            "total_dropped": int(metadata.total_dropped),
            "total_retries": int(metadata.total_retries),
            "total_transport_errors": int(metadata.total_transport_errors),
            "n_chunks": int(metadata.n_chunks),
            "caveats": list(metadata.caveats),
        },
        "files": [
            {
                "path": f.path,
                "sha256": f.sha256,
                "n_events": int(f.n_events),
                "year": int(f.year),
                "currency": f.currency,
            }
            for f in file_list
        ],
        "file_count": len(file_list),
    }
    with target.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")
    log.info(
        "Wrote %s (%d file entries, %d total events)",
        target, len(file_list), metadata.total_events,
    )
    return target


def verify_manifest(
    manifest_path: Path | str,
    *,
    strict: bool = True,
) -> list[str]:
    """Verify every file in the manifest still hashes to its recorded
    SHA256. Returns a list of anomaly strings (empty when everything
    matches). If ``strict``, raises on the first anomaly.

    Used by the audit script + integration tests as the "cache still
    valid?" heartbeat.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    root = manifest_path.parent
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    anomalies: list[str] = []
    for entry in data.get("files", []):
        # Manifest paths are relative to the source root (the manifest's
        # parent directory).
        rel = entry["path"]
        fpath = root / rel
        if not fpath.exists():
            anomalies.append(f"missing file: {rel}")
            if strict:
                raise FileNotFoundError(f"manifest references missing {rel}")
            continue
        got = compute_file_sha256(fpath)
        want = entry["sha256"]
        if got != want:
            msg = f"sha256 mismatch on {rel}: got {got[:16]}..., want {want[:16]}..."
            anomalies.append(msg)
            if strict:
                raise ValueError(msg)
    return anomalies


# ---------------------------------------------------------------------------
# Reference "parser version" string bumped alongside schema changes.
# ---------------------------------------------------------------------------

# Phase 6b initial cut. Bump when EVENT_TABLE_COLUMNS or the normaliser
# changes shape so downstream tooling can detect stale archives.
PARSER_VERSION: str = "phase_6b/2026-07-03"
