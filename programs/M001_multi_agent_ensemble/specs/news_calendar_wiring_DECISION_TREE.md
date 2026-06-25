# News calendar wiring — fallback decision tree

| Field | Value |
|---|---|
| **Date** | 2026-06-25 |
| **Status** | `pre-spec, awaiting approval` |
| **Sibling spec** | [`news_calendar_wiring.md`](news_calendar_wiring.md) (the main spec; this file is the if-then-else companion) |
| **Audience** | Tomorrow's worker, when something breaks during backfill |

This file answers exactly one question: **"if the primary source fails,
what's plan B / C / D?"** The main spec already names the recommended
primary (Dukascopy), fallback (FF community archive), and cross-check
(FRED). This file expands that into the contingency tree so the worker
doesn't have to re-derive it under pressure.

---

## 0. Conventions

- **PASS** = source returns ≥ 1 event per high-impact-event day for the
  requested window, schema parses cleanly, manifest writes successfully.
- **DEGRADED** = source returns data but with gaps (some days empty when
  they shouldn't be) OR with schema warnings (unrecognised importance
  strings, missing currency on some rows).
- **FAIL** = source is unreachable (HTTP 5xx for > 3 consecutive
  attempts at 30-sec backoff), or returns 0 events for a 1-month window
  that is known to contain ≥ 20 high-impact events (e.g. any
  NFP-containing month).

---

## 1. Top-level flow

```
[ Start backfill — Dukascopy primary ]
              │
              ▼
        ┌─────────────┐
        │ Dukascopy   │   PASS  ──►  [ Done — write DK/ partition, run FRED cross-check ]
        │ 2010-2026   │
        └─────┬───────┘   DEGRADED ─►  Branch A — Partial DK + FF fill-in
              │
              │ FAIL
              ▼
        ┌─────────────┐
        │ Try DK with │   PASS    ─►  [ Done — DK with retries ]
        │ retries +   │
        │ slower rate │   FAIL    ─►  Branch B — FF fallback as primary
        └─────────────┘
```

### 1.1 Trigger conditions for DEGRADED vs FAIL

| Trigger | Class |
|---|---|
| HTTP 503 or 429 (rate-limited) on > 25 % of requests in a 1-hour window | DEGRADED — slow down, retry with backoff |
| HTTP 4xx (URL changed, schema changed) on any request | FAIL — escalate to Branch B |
| Network timeout > 30 s × 3 consecutive | FAIL |
| Returned JSON missing required field (`id`, `ts`, `country`, `importance`) | FAIL — schema drift, escalate |
| `len(events) == 0` for a month known to contain NFP, FOMC, CPI, etc. (look up against FRED) | DEGRADED — fall through to Branch A for that month only |
| `len(events) == 0` for 3+ consecutive months in 2010-2026 backfill | FAIL — escalate to Branch B |

---

## 2. Branch A — Partial Dukascopy + FF fill-in

**Scenario.** Dukascopy returns data but with month-sized gaps (e.g.
2014-08, 2016-Q2 empty when they shouldn't be — flagged by FRED
cross-check).

**Plan.**

1. Identify the gap windows from FRED cross-check
   (`scripts/audit_news_calendar.py` — write this as part of step 12 in
   the main spec's checklist).
2. For each gap window, fetch from ForexFactory community archive:
   1. Try the live FF HTML calendar scrape:
      `https://www.forexfactory.com/calendar?week=<monday-of-gap>` for
      each week in the gap. Throttle ≤ 1 request / 5 s. Use UA string
      `multi-pair-trading-agent/m001-news-backfill (research)`.
   2. Parse the HTML using BeautifulSoup; the table structure has been
      stable since ~2018 (column order: time, currency, impact dot
      colour, event, actual, forecast, previous). Pre-2018 the column
      order matched but the impact indicator was a different class name
      (`high` vs `impact-high`) — handle both.
   3. Write the FF events to
      `data/news_calendar/FF/<year>/<currency>.parquet` with
      `source="FF"`.
3. Dedup at load time: when both DK and FF cover the same `(timestamp ±
   60 s, currency, event_normalised)`, the `source="DK"` row wins (per
   §3.3 main spec). FF rows for gap windows therefore become primary
   for those windows; the dedup logic handles the boundary correctly.
4. Update `data/news_calendar/_dedup_audit.parquet` so the audit trail
   is preserved.
5. Re-run FRED cross-check. If gaps remain → Branch C.

**Risk.** FF live scraping is TOS-grey. Throttle aggressively (≤ 1
req / 5 s) and abort if blocked.

**Time estimate.** ~3 hr for a single year-gap; ~30 min per month-gap.

---

## 3. Branch B — FF fallback as primary

**Scenario.** Dukascopy is fully down (Cloudflare block, freeserv URL
changed, etc.).

**Plan.**

1. Switch `scripts/backfill_news_calendar.py --source FF` (the source
   arg is a chain; passing FF first reorders the chain).
2. Run full 2010-2026 backfill against ForexFactory community archive.
   Either:
   - **Sub-option B.1** (recommended): use a hard-pinned community
     archive commit on GitHub. Example: clone `eladhoffer/forex-news`
     at a specific commit-SHA (lock in `_manifest.json`). Convert their
     CSV → our §3.1 schema. ~30 min. No live FF calls.
   - **Sub-option B.2** (TOS-grey, slower): scrape FF live per Branch A
     step 2.1 above, but across the full 2010-2026 window. Throttle ≤
     1 req / 5 s; total runtime ~6 hr × 52 weeks × 16 years ÷ (3600 s)
     ≈ **5+ days**. ONLY viable if B.1 fails.
3. Write to `data/news_calendar/FF/` partition.
4. Once DK comes back online, run normal incremental update; DK rows
   start winning dedup again automatically.

**Risk.** B.1 depends on a community-archive repo staying alive and
matching the schema we expect. B.2 is TOS-grey at 16-year scale and
will likely trigger Cloudflare blocks.

**Time estimate.** B.1 ~1 hr. B.2 ~5+ days (effectively infeasible).

---

## 4. Branch C — FRED-only US coverage (degraded)

**Scenario.** Both Dukascopy AND ForexFactory are down or blocked. Only
FRED is reachable.

**Plan.**

1. Switch to FRED-only backfill.
2. Backfill `release_dates` for the FRED releases listed in main-spec
   §3.4 (FOMC, NFP/Employment, CPI, PPI, GDP, Retail Sales, ISM, PCE).
3. Promote each FRED `date` to a UTC `timestamp` using the §3.4 map.
   This is mechanical — release times are statutory.
4. Set `source="FRED"` and `currency="USD"` on every row.
5. Write to `data/news_calendar/FRED/` partition.

**Limitations under Branch C.**
- **USD only.** EUR/GBP/JPY events are NOT in FRED. The
  `news_calendar` adapter will return False for every bar driven by
  ECB / BoE / BoJ events. F18 KPIs computed under Branch C are
  USD-event-only.
- **Date-level only.** All FRED-derived events use the §3.4 release-time
  map. If a release happens off-schedule (rare; mostly emergency FOMC
  meetings), it lands at the wrong UTC time. Manual amendment needed.
- **No actual / forecast / previous values** — FRED's `release_dates`
  endpoint gives dates, not values. The `actual` / `forecast` /
  `previous` columns are NaN under Branch C.

**This is a *degraded* mode — not a substitute for primary.** Document
loudly in `_manifest.json:degraded_mode=true` so downstream consumers
know to interpret the news axis cautiously.

**Time estimate.** ~30 min for the 8 main release types.

---

## 5. Branch D — Paid override

**Scenario.** User is willing to pay $75/mo for institutional reliability
(answered Q1 "Override with Trading Economics").

**Plan.**

1. Get API key from Trading Economics ($75/mo Basic tier).
2. Set environment variable `TE_API_KEY` (never commit; `.env` is
   gitignored).
3. Switch to `scripts/backfill_news_calendar.py --source TE`.
4. Run full 2010-2026 backfill. ~30 min (TE's API is faster than the
   free sources).
5. Write to `data/news_calendar/TE/` partition.
6. Optional: keep Dukascopy running in parallel as a free cross-check.

**Schema migration vs main spec.**
- TE's `CalendarId` → our `source_event_id`.
- TE's `Importance ∈ {1, 2, 3}` → our `importance` directly (no
  mapping).
- TE's `Date` is ISO 8601 UTC → our `timestamp` directly.
- TE's `TEForecast` (TE's in-house forecast) is dropped to keep
  schema minimal.

**Cost.** $75/mo recurring. Cancellable any time.

---

## 6. Quick decision flowchart (text)

```
                         Is Dukascopy reachable AND schema valid?
                                       │
                       ┌───────────────┴────────────────┐
                      YES                                NO
                       │                                  │
              Run DK backfill                      Try DK retries (30s × 3)
                       │                                  │
                       │                       ┌──────────┴──────────┐
                       │                      PASS                   FAIL
                       │                       │                       │
                       │                  Done — DK with     Is FF reachable?
                       │                  retries                       │
                       │                                ┌───────────────┴────────────┐
                       │                               YES                            NO
                       │                                │                              │
                       │                       Branch B (FF as primary)   Is FRED reachable?
                       │                                                                │
                       │                                                 ┌──────────────┴──────────┐
                       │                                                YES                         NO
                       │                                                 │                          │
                       │                                       Branch C (FRED-only,         STOP — escalate to
                       │                                       degraded; USD only)          user; backfill cannot
                       │                                                                    proceed; document in
                       │                                                                    new commit message
                       │
              Run FRED cross-check
                       │
        ┌──────────────┴───────────────┐
   PASS (no gaps)             DEGRADED (gaps flagged)
        │                              │
        │                       Branch A (DK + FF fill-in
        │                       for gap windows only)
        │                              │
        └──────────────────────────────┘
                       │
                       ▼
             Done — manifest written,
             integration test green,
             commit + report
```

---

## 7. What this tree does NOT do

- **Does not introduce new sources.** The four sources here (DK, FF,
  FRED, TE) are the four named in the main spec §1. Adding a fifth
  (e.g. Investing.com) is a separate amendment per
  `07-research-standards.md` §5 — and Investing.com remains REJECTED
  for the C&D-precedent reason.
- **Does not change the schema.** Every branch writes to the same §3.1
  schema; only `source` and the partition folder differ.
- **Does not change the `load_news_calendar` adapter signature.** The
  adapter loads whatever's on disk; the source identity is in the
  `source` column, not the function signature.
- **Does not retroactively re-bucket sealed reviews.** The Φ4 and
  Φ4.1 reviews remain sealed at their original verdict. Adding a news
  axis to the Φ4.1 telemetry is a diagnostic addendum, not a verdict
  change (per `07-research-standards.md` §11).

---

## 8. References

- Sibling main spec: [`news_calendar_wiring.md`](news_calendar_wiring.md)
- Verdict-comparator discipline (no silent verdict changes):
  `programs/M001_multi_agent_ensemble/07-research-standards.md` §11
- Amendment protocol (when this tree itself needs editing):
  `programs/M001_multi_agent_ensemble/07-research-standards.md` §5 +
  `docs/methodology/amendments.md`
