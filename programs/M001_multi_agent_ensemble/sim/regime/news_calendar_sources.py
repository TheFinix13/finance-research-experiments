"""Φ5 news calendar source-fallback chain.

Implements the DEC-TREE Branch A / B / C fallthrough from
``specs/news_calendar_wiring_DECISION_TREE.md`` §3: Dukascopy freeserv
JSON is primary (D-Q1), ForexFactory community archive is the second
best, FRED release-date map is the US-macro cross-check, Trading
Economics stays as a documented ``--paid`` override for post-G7 upgrades.

**Phase M ships stubs only.** No live HTTP fires from this module.
The real ``fetch`` implementations for DK / FF / FRED land in a
follow-up commit after G7 clears (D-Q2 + D-Q7 backfill horizon 2007+).
Attempting to call an un-implemented fetcher raises ``NotImplementedError``
with a clear pointer to where the code will land, so accidental
CI invocation fails loudly instead of silently returning empty data.

The one real fetcher that DOES land in Phase M is the fixture-only
mini-fetch used by ``sim/tests/test_news_calendar.py`` integration
test #9 to produce the committed 2024 USD DK snapshot. That call lives
in ``scripts/backfill_news_calendar.py`` under the ``--fixture-only``
flag, NOT here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable, Protocol

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source adapter protocol
# ---------------------------------------------------------------------------

class SourceAdapter(Protocol):
    """Structural protocol every calendar source adapter must satisfy.

    The DI pattern mirrors production ``agent/news/calendar.fetch_calendar``:
    a ``fetcher`` callable is injected on construction so tests can
    substitute a deterministic stub for the real HTTP GET.
    """

    source_id: str

    def fetch(
        self,
        start: datetime,
        end: datetime,
        currencies: Iterable[str],
    ) -> list:
        """Fetch events in [start, end] for the given currencies.

        Returns a list of ``NewsEvent`` (imported lazily to avoid the
        circular dep between the two modules -- ``news_calendar`` owns
        the dataclass, ``news_calendar_sources`` owns the plumbing).
        """
        ...


# ---------------------------------------------------------------------------
# Dukascopy adapter (D-Q1 primary)
# ---------------------------------------------------------------------------

@dataclass
class DukascopyAdapter:
    """Dukascopy freeserv JSON events (D-Q1 primary, D-Q3 free-tier).

    Live endpoint format (per spec §1.4, wired 2026-07-03 Phase 6a):
        https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events
        &jsonp=<cb>&start=<epoch_ms>&end=<epoch_ms>&group=news
        &currencies=<CUR>&importance=<any|low|medium|high>

    Default behaviour: ``fetcher`` defaults to
    ``dukascopy_fetch.default_dukascopy_fetcher`` which fires real HTTP.
    Tests inject a fake ``fetcher=`` to keep CI network-free (per D-Q8).
    """
    source_id: str = "DK"
    fetcher: Callable[..., list] | None = None

    def fetch(
        self,
        start: datetime,
        end: datetime,
        currencies: Iterable[str],
    ) -> list:
        if self.fetcher is None:
            # Lazy import to keep pandas/urllib pull-in off the import
            # path unless the adapter is actually used with defaults.
            from programs.M001_multi_agent_ensemble.sim.regime import (
                dukascopy_fetch,
            )
            fetcher_fn: Callable[..., list] = (
                dukascopy_fetch.default_dukascopy_fetcher
            )
        else:
            fetcher_fn = self.fetcher
        return list(fetcher_fn(
            start=start, end=end, currencies=tuple(currencies),
        ))


# ---------------------------------------------------------------------------
# ForexFactory community archive (D-Q2 first fallback)
# ---------------------------------------------------------------------------

@dataclass
class ForexFactoryArchiveAdapter:
    """FF community-archive JSON dumps (D-Q2 fallback #1).

    Wraps community-mirror parquet/JSON dumps rather than scraping FF
    directly (TOS-safer per spec §1.1). No live HTTP in Phase M --
    real archive-fetcher lands post-G7.
    """
    source_id: str = "FF"
    fetcher: Callable[..., list] | None = None

    def fetch(
        self,
        start: datetime,
        end: datetime,
        currencies: Iterable[str],
    ) -> list:
        if self.fetcher is None:
            raise NotImplementedError(
                "ForexFactoryArchiveAdapter.fetch is a Phase M stub; "
                "real community-mirror fetcher lands post-G7"
            )
        return list(self.fetcher(
            start=start, end=end, currencies=tuple(currencies),
        ))


# ---------------------------------------------------------------------------
# FRED cross-check (D-Q2 fallback #2)
# ---------------------------------------------------------------------------

@dataclass
class FREDAdapter:
    """FRED release-date proxy for US macro events (D-Q2 fallback #2).

    Uses the release-date map documented in spec §3.4 (FOMC 14:00 ET,
    NFP/CPI/PPI/GDP 08:30 ET, ISM 10:00 ET) to promote FRED date-only
    releases to UTC datetimes. US-only by construction; the returned
    events all carry ``currency="USD"`` and ``importance=3``.

    Phase M stub raises NotImplementedError; real FRED API wrapper
    lands post-G7 with ``fredapi`` (or a minimal requests wrapper).
    """
    source_id: str = "FRED"
    fetcher: Callable[..., list] | None = None

    def fetch(
        self,
        start: datetime,
        end: datetime,
        currencies: Iterable[str],
    ) -> list:
        # FRED is USD-only; silently return [] for non-USD requests.
        if "USD" not in tuple(c.upper() for c in currencies):
            return []
        if self.fetcher is None:
            raise NotImplementedError(
                "FREDAdapter.fetch is a Phase M stub; real FRED wrapper "
                "lands post-G7 in scripts/audit_news_calendar.py"
            )
        return list(self.fetcher(start=start, end=end))


# ---------------------------------------------------------------------------
# Trading Economics (D-Q3 documented override, never live in Phase M)
# ---------------------------------------------------------------------------

@dataclass
class TradingEconomicsAdapter:
    """Trading Economics REST wrapper (D-Q3 documented override).

    Per D-Q3 the $0 tier ships; this adapter is intentionally
    unimplemented in Phase M. If a caller passes ``sources=("TE",)``
    they get a NotImplementedError describing the paid-tier upgrade
    path so the requirement is surfaced explicitly, not silently
    fallen through to.
    """
    source_id: str = "TE"

    def fetch(
        self,
        start: datetime,
        end: datetime,
        currencies: Iterable[str],
    ) -> list:
        raise NotImplementedError(
            "TradingEconomicsAdapter requires a paid API key ($75/mo "
            "Basic tier or above). Not wired in Phase M per D-Q3 ($0 "
            "steady state). Upgrade path: set TE_API_KEY env var + "
            "swap this adapter for the licensed client"
        )


# ---------------------------------------------------------------------------
# Chain resolver
# ---------------------------------------------------------------------------

SOURCE_REGISTRY: dict[str, type] = {
    "DK": DukascopyAdapter,
    "FF": ForexFactoryArchiveAdapter,
    "FRED": FREDAdapter,
    "TE": TradingEconomicsAdapter,
}


def resolve_chain(
    sources_requested: Iterable[str],
    *,
    fetchers: dict[str, Callable[..., list]] | None = None,
    availability_probe: Callable[[str], bool] | None = None,
) -> list[SourceAdapter]:
    """Build an ordered list of adapters for a fallback fetch chain.

    ``sources_requested`` is the user-declared preference order (default
    ``("DK",)`` per D-Q1). ``fetchers`` is an optional per-source
    dict of injected fetch callables (tests supply stubs here).
    ``availability_probe(source_id) -> bool`` optionally skips sources
    that fail a cheap health check before fetch (post-G7 wiring).

    Per DEC-TREE §3:
    - Branch A (DK healthy): only DK adapter returned.
    - Branch B (DK gaps): DK + FF chain returned; caller iterates and
      merges by (timestamp ± 60s, currency, event) key.
    - Branch C (DK+FF gaps in US macro range): DK + FF + FRED cross-check.
    """
    fetchers = fetchers or {}
    chain: list[SourceAdapter] = []
    for src in sources_requested:
        sid = src.upper()
        cls = SOURCE_REGISTRY.get(sid)
        if cls is None:
            log.warning("Unknown source %r in requested chain; skipping", src)
            continue
        if availability_probe is not None and not availability_probe(sid):
            log.info("Source %s failed availability probe; skipping", sid)
            continue
        if sid == "TE":
            chain.append(cls())            # TE has no fetcher slot in stub
            continue
        chain.append(cls(fetcher=fetchers.get(sid)))
    return chain


__all__ = [
    "SourceAdapter",
    "DukascopyAdapter",
    "ForexFactoryArchiveAdapter",
    "FREDAdapter",
    "TradingEconomicsAdapter",
    "SOURCE_REGISTRY",
    "resolve_chain",
]
