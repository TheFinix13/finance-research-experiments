"""Dukascopy freeserv economic-calendar HTTP fetcher (Phase 6a, 2026-07-03).

Real network fetcher for the D-Q1 primary source declared in
``specs/news_calendar_wiring.md`` §1.4. Wraps the JSONP endpoint
``https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events``
with:

- Windowed pagination (per-day chunks, epoch-ms boundaries).
- JSONP callback unwrap (``cb(...)``).
- Rate limiter (default 500 ms between requests, per spec §1.4 -- "community
  consensus <= 5 req/sec is safe"; we go 2 req/sec for extra caution).
- Retry with exponential backoff on HTTP 5xx / connection reset.
- Explicit schema normalisation into the Phase M canonical row shape
  documented in ``news_calendar.py`` (columns matching
  ``EVENT_TABLE_COLUMNS``).

Not called at import time; ``scripts/backfill_news_calendar.py`` (Phase 6b)
composes this fetcher with the parquet writer + manifest builder. The
``news_calendar_sources.DukascopyAdapter`` default fetcher is wired here
so ``DukascopyAdapter()`` "just works" post-Phase-6a.

CI never hits the network -- ``sim/tests/test_dukascopy_fetch.py`` injects
a fake HTTP transport via the ``transport=`` kwarg on ``fetch_events``.
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Iterator, Protocol

log = logging.getLogger(__name__)


# Lazy-built SSL context using certifi's CA bundle. macOS ships a
# framework Python whose stdlib urllib does NOT trust system keychain
# roots by default -- freeserv.dukascopy.com's cert (Let's Encrypt /
# DigiCert intermediates) then fails verification with
# ``[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer
# certificate``. Falling back to certifi's bundle (installed via urllib3
# / requests transitively) fixes this without disabling verification.
# Users on Linux (where the stdlib finds `/etc/ssl/certs`) still get
# the certifi-backed context; both paths validate.
_SSL_CONTEXT: ssl.SSLContext | None = None


def _get_ssl_context() -> ssl.SSLContext:
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT
    try:
        import certifi

        _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        # certifi unavailable -- fall back to system default. Under
        # Linux this usually works; on macOS framework Pythons it will
        # fail loudly and the user needs to `pip install certifi` or
        # run the Python.app `Install Certificates.command`.
        log.warning(
            "certifi not installed; falling back to system CA bundle. "
            "macOS framework Python may fail SSL verification."
        )
        _SSL_CONTEXT = ssl.create_default_context()
    return _SSL_CONTEXT


# ---------------------------------------------------------------------------
# Endpoint + polite defaults
# ---------------------------------------------------------------------------

# Spec §1.4 URL template. `%(path)s` is intentionally suffixed so
# ``events/get_events`` (calendar) vs future ``events/get_calendar_v2``
# don't require code churn.
DUKASCOPY_BASE_URL: str = (
    "https://freeserv.dukascopy.com/2.0/"
    "index.php?path=%(path)s"
)
DUKASCOPY_EVENTS_PATH: str = "events/get_events"

# Per spec §1.4: community consensus safe ceiling is 5 req/sec. We go
# 2 req/sec to leave headroom for retries -- ~1 hour to cover the full
# 2007-2026 window at 8 currencies * 20 years * ~day-chunks.
DEFAULT_MIN_INTERVAL_SEC: float = 0.5

# Per-day chunk. Dukascopy's endpoint accepts arbitrarily wide start/end
# but the JSON payload gets awkward > ~10 MB. Per-day is safest and lets
# us checkpoint per-day in the backfill script.
DEFAULT_CHUNK_DAYS: int = 1

# Retry policy for 5xx / timeout. Total worst-case wait:
# 1 + 2 + 4 + 8 = 15 s across 4 retries; the calling code sleeps
# ``retry_backoff_base ** attempt`` between attempts.
DEFAULT_MAX_RETRIES: int = 4
DEFAULT_RETRY_BACKOFF_BASE: float = 2.0

# Polite UA string per spec §1.1 (research-repo pattern).
DEFAULT_USER_AGENT: str = (
    "m001-news-backfill/0.1 "
    "(finance-research-experiments; research use; contact via repo issues)"
)

# Importance mapping (spec §3.3): DK emits lower-case strings.
_DK_IMPORTANCE_MAP: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


# ---------------------------------------------------------------------------
# Transport abstraction (for testability)
# ---------------------------------------------------------------------------

class HttpTransport(Protocol):
    """Structural protocol used by ``fetch_events``.

    Real transport is :func:`_default_urllib_transport` (backed by
    ``urllib.request``). Tests inject a fake transport that returns
    canned response bytes for URL patterns; this keeps the CI test suite
    100 % network-free per D-Q8.
    """

    def __call__(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
    ) -> bytes: ...


def _default_urllib_transport(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
) -> bytes:
    """Standard-library urllib backend, with certifi CA bundle.

    Passes an explicit SSL context built from ``certifi.where()`` so
    macOS framework Pythons (which do NOT trust the system keychain by
    default) can verify freeserv.dukascopy.com's certificate. See
    ``_get_ssl_context()`` for the fallback if certifi is missing.
    """
    req = urllib.request.Request(url, headers=headers)
    ctx = _get_ssl_context()
    with urllib.request.urlopen(  # noqa: S310
        req, timeout=timeout, context=ctx,
    ) as resp:
        raw = resp.read()
        enc = resp.headers.get("Content-Encoding", "") or ""
        if enc.lower() == "gzip":
            raw = gzip.decompress(raw)
    return raw


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

@dataclass
class RateLimiter:
    """Sleep-based rate limiter enforcing a minimum inter-request gap.

    Kept dead-simple so it composes cleanly with a fake ``time_source``
    injected by tests. Not thread-safe -- Dukascopy backfill is a single-
    threaded CLI job by design.
    """

    min_interval_sec: float = DEFAULT_MIN_INTERVAL_SEC
    time_source: Callable[[], float] = field(default=time.monotonic)
    sleep_fn: Callable[[float], None] = field(default=time.sleep)
    # ``None`` sentinel so the very first call does not sleep -- ``0.0``
    # would collide with monotonic clocks that report near-zero at start.
    _last_call: float | None = field(default=None, init=False)

    def wait(self) -> None:
        now = self.time_source()
        if self._last_call is not None:
            gap = now - self._last_call
            if gap < self.min_interval_sec:
                self.sleep_fn(self.min_interval_sec - gap)
        self._last_call = self.time_source()


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------

def build_dukascopy_url(
    start: datetime,
    end: datetime,
    currencies: Iterable[str],
    *,
    importance: str = "any",
    base_url: str = DUKASCOPY_BASE_URL,
    path: str = DUKASCOPY_EVENTS_PATH,
    jsonp_callback: str = "cb",
) -> str:
    """Build a Dukascopy freeserv JSON URL for ``[start, end)``.

    Timestamps are converted to epoch-ms UTC (Dukascopy's native format).
    Both endpoints must be timezone-aware; a naive datetime raises
    ``ValueError`` per spec §3.3 timezone-normalisation rule.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError(
            "start and end must be timezone-aware (UTC); got naive datetimes"
        )
    if end <= start:
        raise ValueError(f"end ({end}) must be strictly after start ({start})")
    imp_norm = importance.strip().lower()
    if imp_norm not in {"any", "low", "medium", "high"}:
        raise ValueError(
            f"importance must be one of any/low/medium/high; got {importance!r}"
        )
    curs = [c.strip().upper() for c in currencies if c and c.strip()]
    if not curs:
        raise ValueError("currencies must be a non-empty iterable")

    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    query = {
        "jsonp": jsonp_callback,
        "start": str(start_ms),
        "end": str(end_ms),
        "group": "news",
        "currencies": ",".join(curs),
        "importance": imp_norm,
    }
    base = base_url % {"path": path}
    return f"{base}&{urllib.parse.urlencode(query)}"


# ---------------------------------------------------------------------------
# JSONP unwrap + payload parser
# ---------------------------------------------------------------------------

# ``cb(<json>)`` or ``cb(<json>);`` -- Dukascopy is inconsistent between
# trailing semicolon and none, so allow both.
_JSONP_RE = re.compile(
    r"^\s*(?P<cb>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<payload>.*)\)\s*;?\s*$",
    re.DOTALL,
)


def unwrap_jsonp(raw: bytes, *, expected_callback: str = "cb") -> Any:
    """Extract the JSON payload from a JSONP-wrapped response.

    Accepts both ``cb({...})`` and ``cb({...});`` shapes. Raises
    ``ValueError`` when the wrapper doesn't match or the callback name
    doesn't match ``expected_callback`` (defence against endpoint drift).
    """
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("empty response body from Dukascopy")
    m = _JSONP_RE.match(text)
    if m is None:
        # Some endpoints occasionally return raw JSON (no callback wrap).
        # Try parsing it directly before failing.
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"response is neither JSONP-wrapped nor plain JSON: "
                f"{text[:120]!r}"
            ) from exc
    got_cb = m.group("cb")
    if got_cb != expected_callback:
        log.warning(
            "Dukascopy JSONP callback drift: expected %r, got %r",
            expected_callback, got_cb,
        )
    payload = m.group("payload")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"failed to parse JSONP payload: {payload[:120]!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Event normalisation (Dukascopy row -> Phase M canonical row)
# ---------------------------------------------------------------------------

def _coerce_float(v: Any) -> float | None:
    """Dukascopy sometimes emits ``""``, ``None``, or a raw string with
    unit suffix (e.g. ``"200K"``). We return a float when parseable and
    ``None`` otherwise; the unit is captured separately in ``unit``.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # Strip common unit suffixes for graceful degradation. Full
        # parsing lives in the audit script; here we just care whether
        # the numeric core is recoverable.
        stripped = re.sub(r"[^\d\.\-eE]", "", s)
        try:
            return float(stripped) if stripped else None
        except ValueError:
            return None
    return None


def _extract_unit(v: Any) -> str | None:
    """Return the non-numeric suffix (unit) from a stringy value."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    unit = re.sub(r"[\d\.\-eE\s\+]", "", s).strip()
    return unit or None


def normalize_dukascopy_event(
    raw: dict[str, Any],
    *,
    ingested_at_utc: datetime | None = None,
) -> dict[str, Any] | None:
    """Convert one DK JSON row to the Phase M canonical row schema.

    Returns ``None`` for rows we cannot represent (missing required
    fields) rather than raising -- the caller decides whether to skip
    or log. Required fields: ``id``, ``ts`` OR (``date`` + ``time``),
    ``country``, ``title``, ``importance``. All others degrade to NaN.
    """
    if not isinstance(raw, dict):
        return None

    ts_val = raw.get("ts")
    timestamp: datetime | None
    if isinstance(ts_val, (int, float)) and ts_val > 0:
        # Dukascopy sends epoch ms.
        timestamp = datetime.fromtimestamp(
            float(ts_val) / 1000.0, tz=timezone.utc,
        )
    elif isinstance(ts_val, str) and ts_val:
        # Some downstream mirror formats emit ISO strings; be tolerant.
        try:
            parsed = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            timestamp = (
                parsed if parsed.tzinfo is not None
                else parsed.replace(tzinfo=timezone.utc)
            )
        except ValueError:
            timestamp = None
    else:
        # No parseable timestamp -> tentative / all-day. Keep the row.
        timestamp = None

    country = raw.get("country") or raw.get("currency")
    title = raw.get("title") or raw.get("event")
    imp_raw = raw.get("importance")
    if country is None or title is None or imp_raw is None:
        return None
    country = str(country).strip().upper()
    title = str(title).strip()
    imp_norm = str(imp_raw).strip().lower()
    importance = _DK_IMPORTANCE_MAP.get(imp_norm)
    if importance is None:
        # Numeric already? DK sometimes emits 1/2/3.
        try:
            imp_int = int(imp_raw)
            if imp_int in (1, 2, 3):
                importance = imp_int
        except (TypeError, ValueError):
            pass
    if importance is None:
        log.warning(
            "unrecognised Dukascopy importance %r on event %r; dropping",
            imp_raw, title,
        )
        return None

    event_id_val = raw.get("id") or raw.get("event_id")
    event_id: str | None
    if event_id_val is None:
        event_id = None
    else:
        event_id = str(event_id_val)

    actual = _coerce_float(raw.get("actual"))
    forecast = _coerce_float(raw.get("forecast"))
    previous = _coerce_float(raw.get("previous"))
    unit = raw.get("unit")
    if unit is None:
        unit = _extract_unit(raw.get("actual")) or _extract_unit(
            raw.get("forecast"),
        )
    unit_str = str(unit).strip() if unit else None

    return {
        "timestamp": timestamp,
        "currency": country,
        "event": title,
        "importance": importance,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "unit": unit_str,
        "source": "DK",
        "source_event_id": event_id,
        "ingested_at_utc": (
            ingested_at_utc if ingested_at_utc is not None
            else datetime.now(tz=timezone.utc)
        ),
    }


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------

def iter_chunks(
    start: datetime,
    end: datetime,
    *,
    chunk_days: int = DEFAULT_CHUNK_DAYS,
) -> Iterator[tuple[datetime, datetime]]:
    """Yield half-open ``[chunk_start, chunk_end)`` pairs of ``chunk_days``
    each, so a full-year backfill lands as ~365 requests per currency
    (well within Dukascopy's tolerance ceiling).
    """
    if chunk_days < 1:
        raise ValueError("chunk_days must be >= 1")
    cur = start
    step = timedelta(days=chunk_days)
    while cur < end:
        nxt = min(cur + step, end)
        yield cur, nxt
        cur = nxt


# ---------------------------------------------------------------------------
# Top-level fetcher
# ---------------------------------------------------------------------------

@dataclass
class DukascopyFetchStats:
    """Per-run telemetry -- consumed by manifest writer + audit script."""

    n_chunks: int = 0
    n_events: int = 0
    n_dropped: int = 0
    n_retries: int = 0
    n_transport_errors: int = 0
    started_at_utc: datetime | None = None
    finished_at_utc: datetime | None = None


def fetch_events(
    start: datetime,
    end: datetime,
    currencies: Iterable[str],
    *,
    importance: str = "any",
    transport: HttpTransport | None = None,
    rate_limiter: RateLimiter | None = None,
    chunk_days: int = DEFAULT_CHUNK_DAYS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_base: float = DEFAULT_RETRY_BACKOFF_BASE,
    request_timeout_sec: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    ingested_at_utc: datetime | None = None,
    stats: DukascopyFetchStats | None = None,
) -> list[dict[str, Any]]:
    """Fetch and normalise Dukascopy freeserv events across ``[start, end)``.

    Returns a flat list of canonical event dicts (schema =
    ``EVENT_TABLE_COLUMNS`` in ``news_calendar.py``). Dedup is NOT done
    here -- the caller (backfill script) dedupes across sources via
    ``dedup_events`` in ``news_calendar.py``.

    Injectable arguments make this fetcher fully testable without touching
    the network:

    - ``transport``: overrides the urllib backend. Signature matches
      :func:`_default_urllib_transport`.
    - ``rate_limiter``: overrides the default 500 ms polite gap; tests
      inject a no-op limiter with ``sleep_fn=lambda _: None``.
    - ``stats``: consumed in-place; caller can inspect after the run.
    """
    transport = transport or _default_urllib_transport
    limiter = rate_limiter or RateLimiter()
    ingested = ingested_at_utc or datetime.now(tz=timezone.utc)
    stats = stats if stats is not None else DukascopyFetchStats()
    stats.started_at_utc = ingested

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/javascript, application/json, */*",
        "Accept-Encoding": "gzip, deflate",
    }

    out: list[dict[str, Any]] = []
    for chunk_start, chunk_end in iter_chunks(
        start, end, chunk_days=chunk_days,
    ):
        stats.n_chunks += 1
        url = build_dukascopy_url(
            chunk_start, chunk_end, currencies,
            importance=importance,
        )
        raw: bytes | None = None
        for attempt in range(max_retries + 1):
            limiter.wait()
            try:
                raw = transport(
                    url, headers=headers, timeout=request_timeout_sec,
                )
                break
            except (urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, ConnectionError, OSError) as exc:
                is_5xx = isinstance(
                    exc, urllib.error.HTTPError,
                ) and 500 <= exc.code < 600
                if attempt >= max_retries or (
                    isinstance(exc, urllib.error.HTTPError) and not is_5xx
                    and exc.code not in (408, 425, 429)
                ):
                    stats.n_transport_errors += 1
                    log.warning(
                        "Dukascopy fetch giving up on %s..%s after "
                        "%d retries: %s",
                        chunk_start.date(), chunk_end.date(), attempt, exc,
                    )
                    raw = None
                    break
                stats.n_retries += 1
                sleep_sec = retry_backoff_base ** attempt
                log.info(
                    "Dukascopy fetch retry %d/%d for %s..%s in %.1fs: %s",
                    attempt + 1, max_retries,
                    chunk_start.date(), chunk_end.date(), sleep_sec, exc,
                )
                limiter.sleep_fn(sleep_sec)
        if raw is None:
            continue

        try:
            payload = unwrap_jsonp(raw)
        except ValueError as exc:
            stats.n_transport_errors += 1
            log.warning(
                "Dukascopy chunk %s..%s returned unparseable body: %s",
                chunk_start.date(), chunk_end.date(), exc,
            )
            continue

        # DK sometimes wraps events in {"events": [...]}, sometimes returns
        # a bare list. Handle both.
        if isinstance(payload, dict):
            events_iter = payload.get("events", [])
        elif isinstance(payload, list):
            events_iter = payload
        else:
            stats.n_transport_errors += 1
            log.warning(
                "Dukascopy chunk %s..%s: unexpected payload type %s",
                chunk_start.date(), chunk_end.date(), type(payload).__name__,
            )
            continue

        for raw_event in events_iter:
            row = normalize_dukascopy_event(
                raw_event, ingested_at_utc=ingested,
            )
            if row is None:
                stats.n_dropped += 1
                continue
            stats.n_events += 1
            out.append(row)

    stats.finished_at_utc = datetime.now(tz=timezone.utc)
    log.info(
        "Dukascopy fetch complete: %d events across %d chunks "
        "(dropped=%d, retries=%d, transport_errors=%d)",
        stats.n_events, stats.n_chunks, stats.n_dropped,
        stats.n_retries, stats.n_transport_errors,
    )
    return out


# ---------------------------------------------------------------------------
# Convenience: default fetcher for DukascopyAdapter.fetcher=
# ---------------------------------------------------------------------------

def default_dukascopy_fetcher(
    *,
    start: datetime,
    end: datetime,
    currencies: Iterable[str],
) -> list[dict[str, Any]]:
    """Zero-config wrapper -- passes only network defaults.

    Wired into ``news_calendar_sources.DukascopyAdapter.fetcher`` so
    ``DukascopyAdapter()`` "just works" without further ceremony. Bespoke
    backfill scripts should call :func:`fetch_events` directly for finer
    control over rate limits + chunk sizes.
    """
    return fetch_events(start, end, currencies)
