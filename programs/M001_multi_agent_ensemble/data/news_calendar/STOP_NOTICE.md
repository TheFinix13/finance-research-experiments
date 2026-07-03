# STOP NOTICE — Phase 6c backfill halted

**Date:** 2026-07-03 03:55 UTC
**Status:** `HALTED-DK-ENDPOINT-DEPRECATED`
**Owner:** M001 multi-agent-ensemble
**Blocker of:** Phase 6c (full 2007-2026 news backfill), news-calendar-
opted regime wiring at agent level.

## What happened

Attempted the pre-registered Phase 6c backfill run against the D-Q1
primary source (`https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events`).
All request variants returned either **403 Forbidden** (default UA) or
**204 No Content with `Content-Type: text/html`** (browser UA). The
freeserv endpoint has been retired for anonymous consumption.

Probes (all against a 2024-01-01..2024-01-31 USD-only window):

| # | Variant | Status |
|---|---|---|
| 1 | `path=events/get_calendar_events` (v2 shape) | 204 |
| 2 | `path=events/get_events` (spec §1.4 shape) | 204 |
| 3 | Plain JSON, no `jsonp` param | 204 |
| 4 | `path=events/calendar` | 204 |
| 5 | `countries=US` instead of `currencies=USD` | 204 |
| 6 | Bare `path=events/get_events`, no query | 204 |

The live DK calendar page (`www.dukascopy.com/swiss/english/marketwatch/calendars/`)
now iframes `https://widgets.dukascopy.com/en/economic-calendar`,
a modern Angular SPA whose calendar API is loaded via lazy chunks
(`chunk-*.js`) that don't expose the endpoint via static grep.

## What was NOT written

No parquet or manifest files were written to `data/news_calendar/DK/`
during the aborted attempt. The archive tree is unchanged from the
pre-Phase-6c state (empty besides `README.md` and `.gitignore`).

## What DID land this session

- **Fetcher SSL fix** (`sim/regime/dukascopy_fetch.py`): certifi-
  backed SSL context so macOS framework Python can verify TLS certs.
  Real fix, unrelated to the endpoint deprecation, keeps the fetcher
  useful the moment a working endpoint is identified.
- **Phase 6b writer + manifest + CLI** committed previously (`1b6848c`)
  is untouched — it will work against any conforming fetcher.

## Relaunch prerequisites (Phase 6c-v2)

1. Identify a working current-generation D-Q1 endpoint. Options:
   - **DK widget reverse-engineering** — needs headless browser (Playwright)
     to observe the actual API calls made by the lazy chunk.
   - **ForexFactory (`nfs.faireconomy.media`)** — well-known JSON API,
     may become new D-Q1 primary with historical archive available.
   - **TradingEconomics API** — paid, key required, but comprehensive.
   - **FRED alone** — covers macro releases (D-Q2 already), insufficient
     for high-frequency currency-event coverage.
2. Update `dukascopy_fetch.build_dukascopy_url` (or replace the module
   with `<newsource>_fetch.py`) against the new endpoint, keeping the
   same normalised row schema so downstream (`news_calendar.py`,
   `news_windowing.py`) is unaffected.
3. Update `specs/news_calendar_wiring.md` §1.4 to reflect the new
   D-Q1 primary.
4. Re-verify with a 1-month single-currency live probe before
   committing to the full 2007-2026 backfill.

## Registry entry

Added to top of `data/news_calendar/README.md` as `HALTED-DK-ENDPOINT-
DEPRECATED`. This STOP_NOTICE is the audit record; when Phase 6c
relaunches, the new attempt's PROTOCOL should reference this file
in its "prior attempts" section.

## Do NOT

- Do NOT rerun the current `backfill_news_calendar.py --sources DK`
  against freeserv. It will silently write empty parquets (transport
  errors are recorded in `caveats` but the manifest still lands).
- Do NOT commit fake or synthetic news data to work around the
  deprecation. The archive must reflect real primary-source data.
