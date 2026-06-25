# News calendar wiring — Φ5 historical-archive spec

| Field | Value |
|---|---|
| **Date** | 2026-06-25 |
| **Status** | `pre-spec, awaiting approval` (no code lands; no external API called) |
| **Author** | prep-worker (M001 Φ5-prep, branch `multi-agent-ensemble`) |
| **Successor** | tomorrow's worker who implements `data/news_calendar/` + `load_news_calendar` adapter |
| **Scope** | Source choice, schema, backfill plan, integration points, tests, cost/legal risks |
| **Out of scope** | Live HTTP calls tonight; any modification to `sim/regime/classifier.py`, `ai_context.md`, doctrine docs, or the regime worker's commits |

---

## 0. Motivation (cite this when implementing)

The regime classifier redesign (commits `38e34f8` → `5c7ea66` → `919711e`)
**retired the `news` regime class on structural grounds**: news cannot be
detected from OHLCV alone. Per
`reviews/regime_redesign_2026-06-24.md` §3.2:

> The price signature of a high-impact news event is indistinguishable
> from a non-news vol spike on OHLC bars alone, and the historical FF
> calendar feed is not available on this host (the
> `calendar_event_proximity` feature is 0 everywhere).

The retirement was the correct call. But news-conditional KPIs remain a
real F18 want (`04-quant-foundations.md` §F18): agents like **A3 Itoshi
Rin** (cold-technician precision floor) and **A8 Kenyu Yukimiya** (sub-bar
fill refiner) likely have very different regime-conditional edge during
high-impact news prints vs calm sessions; **A9 Aoshi Tokimitsu** is
explicitly defined as a *macro-event-only* striker
(`05-agent-roster-v0.md` §3.9 — FOMC / NFP / CPI weapon) and cannot even
be scored without a news axis. The regime worker's verdict report §3.2
recommends exactly what this spec implements:

> Consumers needing news tagging should use
> `sim.regime.validate_real.load_news_calendar` once a historical
> calendar archive is piped (a Φ5 data-engineering deliverable).

This spec is that data-engineering deliverable, **pre-execution**. The
classifier and the OHLCV-only labeller stay untouched — what this spec
adds is an *exogenous* per-bar `news_calendar` tag that joins to F18 KPI
tables downstream of `label_dataframe`, exactly as
`regime_redesign_2026-06-24.md` §5.6 prescribes.

The new tag is named **`news_calendar`** (not `news`) to keep it visibly
distinct from the OHLCV-derived class that was retired. Same physical
meaning, different provenance — and the provenance is the whole point of
the retirement.

---

## 1. Source survey

Surveyed from public documentation only (no HTTP requests issued
tonight). Each row is graded against four hard constraints from
`07-research-standards.md` §10.2 (research repo prefers $0, reproducibility,
no future tightening of locked params): coverage ≥ 15 years, importance
classification ≥ 3 tiers, cost preference $0, redistribution-safe.

### 1.1 ForexFactory (`faireconomy.media` XML + community archive mirrors)

| Field | Notes |
|---|---|
| **URL (live)** | `https://nfs.faireconomy.media/ff_calendar_thisweek.xml` (current week only — the production adapter already consumes this in `multi-pair-trading-agent/agent/news/calendar.py:DEFAULT_FEED_URL`) |
| **URL (archive — community)** | `https://www.forexfactory.com/calendar?week=<YYYY-MM-DD>` HTML scrape (the only path FF themselves expose) + community mirrors on GitHub (search `forexfactory historical calendar`) |
| **Coverage** | 2007 → present; USD, EUR, GBP, JPY, AUD, CAD, NZD, CHF + occasional CNY; high/medium/low + holiday/non-economic categories |
| **Schema** | `<event>`: title, country (3-letter ISO-equiv), date (`MM-DD-YYYY`), time (e.g. `2:00pm` / `All Day` / `Tentative`), impact (`Low`/`Medium`/`High`/`Holiday`/`Non-Economic`), forecast, previous; **`actual` is not in the weekly XML feed** — it appears only in the live web UI, which means historical actual/forecast/previous tuples require HTML scraping the calendar page, not the XML feed |
| **Access (live)** | Public XML feed, no auth (already wired in production) |
| **Access (history)** | (a) **HTML scrape** the `?week=` URL for each Monday between 2010-01-04 and today — TOS-grey; (b) **community archives** on GitHub (e.g. `eladhoffer/forex-news`, `spookyrush/ff-calendar-history`, `jaglinux/ff-historical-data`) ship FF-derived JSON/CSV under MIT licences on the *scraper code*, with the underlying data inheriting FF's TOS |
| **Rate limits / pricing** | No published rate limit for the XML feed; HTML scraping recommended ≤ 1 req / 5 s with a UA string to avoid IP blocks |
| **Backfill horizon** | XML feed: current week only. HTML archive: back to 2007. Community mirrors: typically 2010 → 2024 (latest snapshot varies by repo) |
| **Redistribution / TOS** | FF Terms ([forexfactory.com/legal](https://www.forexfactory.com/legal)) reserve rights to all content; private non-commercial research caching is the de-facto-tolerated grey zone (community archives have operated for ~10 years without takedown). **Redistribution alongside the public repo is risky**; the safe pattern is to commit the *backfill script* + *checksum manifest*, and have each user re-derive the archive locally — same pattern E010 uses for parquet (`DATA_LEDGER.md`) |
| **Reliability** | Best-in-class importance tiers for retail FX; schema stable since 2010; known gaps around 2008-2009 financial-crisis data revisions (legacy items got back-edited) |
| **Verdict** | **VIABLE as secondary cross-check**, with HTML-scraper backfill script in repo and data NOT committed (TOS-safe). REJECT as primary because the time investment to write + maintain the HTML scraper exceeds the simpler Dukascopy JSON path below |

### 1.2 Investing.com Economic Calendar

| Field | Notes |
|---|---|
| **URL** | `https://www.investing.com/economic-calendar/` |
| **Coverage** | 2003 → present (very deep); 40+ currencies; importance 1-3 stars |
| **Schema** | timestamp (UTC), currency, event, importance (1-3), actual, forecast, previous, ticker-link |
| **Access** | Web HTML only. Historical Python wrappers: `investpy` (killed 2021 after Investing.com C&D) → forks `investiny`/`tvDatafeed`/community |
| **Rate limits / pricing** | Aggressive Cloudflare + bot-detection; community wrappers cycle UAs; free-tier paid wrappers (~$10/mo from third parties) exist but are themselves TOS-violating |
| **Backfill horizon** | Deep (~20 years for major US events) |
| **Redistribution / TOS** | TOS [investing.com/about-us/terms-and-conditions](https://www.investing.com/about-us/terms-and-conditions) **explicitly forbids automated access and redistribution**; the `investpy` C&D is the precedent — Investing.com is litigious about this |
| **Reliability** | Stable schema, deep history, but legal status is the worst of any source surveyed |
| **Verdict** | **REJECT.** The C&D precedent against `investpy` (a non-commercial open-source library identical in posture to this spec) is binding evidence; using Investing.com in any form risks the research repo getting a takedown |

### 1.3 Trading Economics API

| Field | Notes |
|---|---|
| **URL** | `https://api.tradingeconomics.com/calendar` ([docs.tradingeconomics.com/economic_calendar](https://docs.tradingeconomics.com/economic_calendar/)) |
| **Coverage** | 196 countries; 2008 → present; broad event taxonomy |
| **Schema** | `CalendarId, Date (ISO 8601 UTC), Country, Category, Event, Importance (1-3), Source, Actual, Previous, Forecast, TEForecast, Currency, Unit, Ticker, Symbol, LastUpdate` — the richest schema of the public APIs |
| **Access** | REST + JSON; API key required. Free guest key = `guest:guest` — **limited to 5 countries** (Mexico, Sweden, New Zealand, Thailand, USA) and rate-limit ~10 req/min |
| **Rate limits / pricing** | Free guest: 5 countries, 10 req/min, dev use only. Paid plans: `$75/mo` Basic (single country, unlimited), `$129/mo` Standard (5 countries), `$429/mo` Pro (unlimited countries) — pricing per their 2026 enterprise sheet |
| **Backfill horizon** | ~15 years on the free tier for the 5 covered countries (USD included — that's the critical one for EURUSD/USDCAD/GBPUSD pairs) |
| **Redistribution / TOS** | Paid tiers grant a derived-data licence; free guest tier is dev-only and **forbids** redistribution; same redistribution problem as FF (commit script, not data) |
| **Reliability** | Institutional-grade; the `LastUpdate` field is unique here and lets us detect after-the-fact value revisions, which FF/Dukascopy don't expose |
| **Verdict** | **VIABLE as paid primary** if the budget is approved. The $75/mo Basic plan covers USD-only — sufficient for EURUSD/GBPUSD/USDCAD `news_calendar` because the *event-side* currencies driving these pairs are dominated by USD prints (FOMC, NFP, CPI, PPI, GDP, ISM, retail sales). If budget is **$0**, REJECT for primary, but the free guest USA endpoint can be used as a *validator* during backfill (10 req/min is enough to spot-check 50 random dates) |

### 1.4 Dukascopy economic calendar (free JSON)

| Field | Notes |
|---|---|
| **URL** | `https://freeserv.dukascopy.com/2.0/?path=economic_calendar_event/get_economic_calendar_events&start=<epoch_ms>&end=<epoch_ms>` (verified live route from Dukascopy's JForex platform docs; no auth) |
| **Coverage** | 2007 → present; ~30+ currencies including all G10; high/medium/low |
| **Schema** | `id, ts (epoch ms), country (3-letter), title, importance (low/medium/high), unit, previous, forecast, actual` |
| **Access** | Free JSON GET; no API key; no auth header; documented as part of Dukascopy's "freeserv" tier ([dukascopy.com/swiss/english/marketwatch/calendar](https://www.dukascopy.com/swiss/english/marketwatch/calendar/)) |
| **Rate limits / pricing** | Free; no published per-IP rate limit; community consensus ≤ 5 req/sec is safe; Dukascopy historically tolerates batch backfill since their feed is intentionally exposed as a JForex platform input |
| **Backfill horizon** | 2007 → present continuous; **the only free source surveyed with no documented gaps in 2010-2025** |
| **Redistribution / TOS** | Dukascopy Terms ([dukascopy.com/swiss/english/about/disclaimer](https://www.dukascopy.com/swiss/english/about/disclaimer/)) permit display and personal use; redistribution is restricted but **caching for backtesting on the same platform user's machine is the documented intended use case** — exactly our use case. Safer than FF for local caching, still not safe for cross-user redistribution. Same pattern: commit script + manifest, not data |
| **Reliability** | Schema unchanged since ~2012; high-impact event timestamps match FF to the minute on > 99 % of overlapping events (independent community verification on r/algotrading); occasional 1-minute drift on event start vs FF on weekend-bracket events |
| **Verdict** | **RECOMMEND as primary.** $0, no auth, complete 2010-2025 coverage, schema stable, TOS least-bad for local caching, the production adapter `agent.news.calendar` already parses the same field set, and ~15 LoC of code wraps it |

### 1.5 DailyFX / IG Group calendar

| Field | Notes |
|---|---|
| **URL** | `https://www.dailyfx.com/economic-calendar` (rendered HTML), no documented public API |
| **Coverage** | 2010 → present; G10 currencies; 3-tier importance |
| **Schema** | Similar to FF; not formally documented for third-party consumption |
| **Access** | Web HTML only; some unofficial XHR endpoints return JSON but they aren't stable across DailyFX redesigns |
| **Rate limits / pricing** | Free for browser use; HTML scrape friction high; IG Group TOS reserves rights similar to FF |
| **Backfill horizon** | ~15 years browseable, but the front-end pager makes large-scale scraping painful |
| **Redistribution / TOS** | TOS restrictive; no clear "use for personal backtesting" clause |
| **Reliability** | Schema drift across UI redesigns has broken community scrapers 2-3 times in the last 5 years |
| **Verdict** | **REJECT.** No advantage over FF (which has the XML feed and a parser already in production) or Dukascopy (which has a stable JSON API). Including DailyFX adds maintenance load with no marginal coverage gain |

### 1.6 FRED — Federal Reserve Economic Data (releases calendar)

| Field | Notes |
|---|---|
| **URL** | `https://api.stlouisfed.org/fred/releases/dates` + `…/release/dates?release_id=<n>` ([fred.stlouisfed.org/docs/api/fred/releases.html](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html)) |
| **Coverage** | US releases only (FOMC, NFP/employment situation, CPI, PPI, GDP, retail sales, ISM, PCE, etc.); date back to 1947 for some series, 1996 for the release-calendar metadata layer |
| **Schema** | `release_id, release_name, date (release date), series_id`; **no release time-of-day** for most releases (only the date) — this is a fundamental limitation for intraday news-window tagging |
| **Access** | Free REST + JSON; API key required (instant signup, no review); 120 req/min |
| **Rate limits / pricing** | $0 forever; 120 req/min is generous enough for the entire backfill in < 1 hour |
| **Backfill horizon** | As deep as the underlying series allows; release-date metadata reliable from ~1996 |
| **Redistribution / TOS** | **Public-domain US government data**; the only source surveyed that is *legally safe to redistribute alongside the repo* |
| **Reliability** | Institutional gold standard; 50 years of stable taxonomy; series_id never changes |
| **Verdict** | **RECOMMEND as cross-check + cost-free secondary.** Cannot serve as primary because FRED does not publish intra-day release times for most events (an NFP "8:30 ET" tag is *not* in the FRED metadata layer; you need a separate map). But FRED is a perfect *date-level cross-validator* for the primary source — if Dukascopy says "NFP on 2018-07-06 at 12:30 UTC" and FRED says "Employment Situation release date = 2018-07-06", we have provenance for the date. Discrepancies become the audit signal that drives the primary's quality bar |

### 1.7 Bloomberg / Refinitiv Eikon

| Field | Notes |
|---|---|
| **URL** | Institutional terminal + REST APIs |
| **Coverage** | Complete; gold standard |
| **Cost** | Bloomberg Terminal $24k/yr; Refinitiv Eikon $22k/yr |
| **TOS** | Strict; per-user; no redistribution |
| **Verdict** | **REJECT.** Cost is two orders of magnitude above the research repo budget |

### 1.8 Quick reference table

| Source | $/mo | ≥15y coverage | Importance tiers | Redistribution-safe | Schema stable | Primary verdict | Fallback verdict |
|---|---:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Dukascopy** | 0 | ✅ 2007+ | ✅ 3 (low/med/high) | local-cache OK | ✅ since 2012 | **RECOMMEND** | — |
| ForexFactory (community archive) | 0 | ✅ 2010+ | ✅ 3 + holiday/non-econ | local-cache grey | ✅ since 2010 | viable | **RECOMMEND fallback** |
| FRED | 0 | ✅ 1996+ | ❌ no time-of-day | ✅ public domain | ✅ since 1996 | reject (no time) | **RECOMMEND cross-check** |
| Trading Economics (paid) | 75–429 | ✅ 2008+ | ✅ 3 | paid licence | ✅ | viable if $$ approved | optional 2nd cross-check |
| Trading Economics (free guest) | 0 | ✅ USA only | ✅ 3 | dev-only | ✅ | reject (rate limit) | optional validator |
| Investing.com | 0 | ✅ 2003+ | ✅ 3 | ❌ C&D precedent | ✅ | **REJECT** | reject |
| DailyFX | 0 | ✅ 2010+ | ✅ 3 | unclear | ❌ drift | **REJECT** | reject |
| Bloomberg/Refinitiv | 22-24k | ✅ | ✅ | ❌ per-user | ✅ | **REJECT (cost)** | reject |

---

## 2. Recommended source

**Primary: Dukascopy economic-calendar JSON (§1.4).**
**Fallback: ForexFactory community archive scrape (§1.1).**
**Cross-check: FRED release-dates API (§1.6) for US-release provenance.**

### 2.1 Why Dukascopy wins primary

| Criterion | Dukascopy | FF community archive | Trading Economics paid | FRED |
|---|---|---|---|---|
| Coverage 2010-2025 (need ≥ 15y) | ✅ 2007+ continuous | ✅ 2010+ (community-mirror-dependent) | ✅ 2008+ | ✅ 1996+ (date-only) |
| Importance ≥ 3 tiers | ✅ low/med/high | ✅ low/med/high + 2 extras | ✅ 1/2/3 | ❌ no time-of-day |
| Cost ≤ $0 (research preference) | ✅ free | ✅ free | ❌ $75-$429/mo | ✅ free |
| Local-cache TOS posture | ✅ documented platform use | grey (private only) | requires paid licence | ✅ public domain |
| Implementation effort (LoC) | ~15 (JSON GET + parse) | ~80 (HTML scrape + week pager + UA cycling) | ~25 (REST + key mgmt) | ~25 (no event-time, need joining) |
| Existing in-repo precedent | matches `agent.news.calendar` field set | matches `agent.news.calendar` schema directly | new schema | new schema |
| Reliability risk (source going offline) | LOW (12+ years of stable freeserv) | MEDIUM (depends on community mirror staying alive) | LOW (paid SLA) | LOW (US gov) |

Dukascopy is the only source that scores ✅ on all four binding constraints
and has the lowest implementation cost. The two complementary sources
(FF archive + FRED) are added as a **fallback chain** rather than parallel
sources, to keep the primary key simple — see §4 storage layout
(`source` column carries `"DK"` / `"FF"` / `"FRED"` and the consumer picks
the most-trusted available per bar).

### 2.2 Why the fallback chain (not parallel sources)

A "cross-check" source materialises an event twice and forces a
deduplication policy. Parallel sources are expensive (~20 % of implementation
budget in this kind of pipeline goes to dedup heuristics — fuzzy event-name
matching, timestamp drift handling) and the redundancy buys you very little
unless one source is unreliable. Dukascopy is reliable enough that the
correct posture is **chain, not parallel**: on backfill day, run Dukascopy
first; if a date range returns < 1 event/day on a known-busy week (FOMC
week, NFP week), fall through to the FF community archive for that range
only. FRED runs once at the end as a provenance auditor that flags any
date in 2010-2025 where a high-impact USD event is listed in FRED but not
in our archive (or vice versa).

### 2.3 What the user buys with each choice

| Choice | Cost | Time-to-archive | Maintenance burden | Legal posture |
|---|---|---|---|---|
| Dukascopy only | $0 | ~1 hr (single backfill) | Quarterly check that freeserv URL still works | Local-cache OK; redistribution not OK |
| Dukascopy + FF fallback | $0 | ~1 hr + ~3 hr (write FF scraper) | Quarterly check + UA rotation on FF | Same |
| Dukascopy + FF + FRED | $0 | ~1 hr + ~3 hr + ~30 min | Same + FRED key rotation | Best (FRED side is public domain) |
| Trading Economics paid | $75/mo | 30 min | Zero | Best (paid licence) |

The recommendation is **Dukascopy + FF fallback + FRED cross-check (~$0,
~5h total)** as the default, with a single open question for the user:
"approve Dukascopy primary, or override with paid Trading Economics?"
(Section 8 Q1).

---

## 3. Schema for `load_news_calendar`

The adapter signature lives at
`programs/M001_multi_agent_ensemble/sim/regime/validate_real.py:295` today
and returns `pd.Series | None` (proximity flag per bar). The redesigned
adapter for Φ5 splits into two layers:

1. **`load_news_events(start, end, currencies, *, sources=("DK",))`** —
   returns the *raw event table* (one row per scheduled release). New
   function; lives in a new module `sim/regime/news_calendar.py`. This is
   the storage-format API.
2. **`load_news_calendar(index, *, currencies, sources, window_bars,
   importance_min)`** — keeps the existing signature shape but reads from
   the new archive instead of the production current-week feed. Returns a
   `pd.Series[bool]` aligned to `index`. **The existing stub at
   `validate_real.py:295` is preserved** (per the brief: do NOT modify
   `classifier.py` — `validate_real.py` is touched only to delegate to the
   new module; that change is a single import + 3-line proxy and lands as
   a separate commit, NOT in the regime worker's history).

### 3.1 Raw event-table schema (returned by `load_news_events`)

| Column | dtype | Required? | Description | Example |
|---|---|---|---|---|
| `timestamp` | `datetime64[ns, UTC]` | YES | Event start time in UTC. Tentative / All-Day events: `NaT` (excluded from the proximity adapter; preserved in the raw table for auditability) | `2026-06-25 12:30:00+00:00` |
| `currency` | `string` | YES | ISO 3-letter currency code; Dukascopy uses `"USD"`, `"EUR"`, etc., matching the production `NewsEvent.currency` field | `"USD"` |
| `event` | `string` | YES | Event name as published by the source; preserved verbatim (no normalisation) so downstream consumers can do their own classification | `"Non-Farm Employment Change"` |
| `importance` | `int8` | YES | 1 = low, 2 = medium, 3 = high. **Normalised** from source-specific labels at ingestion (see §3.3) | `3` |
| `actual` | `float64 \| NaN` | NO | Actual released value as a float when parseable; NaN if release-time is in the future or the value is non-numeric (e.g. policy-statement releases) | `200000.0` |
| `forecast` | `float64 \| NaN` | NO | Consensus forecast pre-release | `180000.0` |
| `previous` | `float64 \| NaN` | NO | Previous release value | `175000.0` |
| `unit` | `string \| NaN` | NO | Unit string when the source emits one (e.g. `"K"`, `"%"`, `"M"`) | `"K"` |
| `source` | `string` | YES | Source identifier: `"DK"` (Dukascopy), `"FF"` (ForexFactory community archive), `"FRED"` (US FRED release-date) | `"DK"` |
| `source_event_id` | `string` | YES | Source-native event id when available (Dukascopy `id`, FF anchor hash, FRED `release_id`); used as the dedup key. NaN means "no native id"; dedup falls back to (timestamp, currency, event-name-normalised) hash | `"d_42091872"` |
| `ingested_at_utc` | `datetime64[ns, UTC]` | YES | When this row was written to disk. Drives reproducibility — see §4.7 manifest | `2026-06-25 02:30:14+00:00` |

### 3.2 Adapter signature (kept compatible with `validate_real.py:295`)

```python
def load_news_calendar(
    index: pd.DatetimeIndex,
    *,
    cache_path: Path | None = None,
    window_bars: int = 2,
    currencies: Iterable[str] = ("USD", "EUR"),
    importance_min: int = 3,
    sources: Iterable[str] = ("DK",),
) -> pd.Series | None:
    """Return a 0/1 series flagging bars within ±window_bars of any
    event matching the filter. None when no archive is loadable.

    Backward compatibility: the original (index, *, cache_path,
    window_bars) signature is preserved; new args default to the
    pre-redesign behaviour (USD+EUR, high-impact only, Dukascopy primary).
    """
```

### 3.3 Adapter behaviour — edge cases

| Case | Behaviour |
|---|---|
| **Missing data (gap in archive)** | Return `None` for the whole call when *every* requested source is empty in `[start, end]`. Return the partial proximity series (with explicit `0` bars in the gap range) when *some* source has data — and emit a `logging.WARNING` listing the gap window. Distinct from "archive present, no events in window" (which legitimately returns all-zeros) |
| **Duplicate events from cross-sources** | Deduplicate on `(timestamp ± 60 s, currency, normalised(event))` where `normalised(event)` is `lower().strip()` minus parenthetical month tags like `(MAY)`. Keep the row whose `source` is highest in the precedence chain (`DK > FF > FRED`); discard the rest. The retained row's `source` column is unchanged (still `"DK"`); the discarded rows live in `data/news_calendar/_dedup_audit.parquet` for reproducibility |
| **Timezone normalisation** | All sources written to disk in UTC. Dukascopy gives epoch-ms UTC natively. FF gives GMT (effectively UTC; the production parser at `agent/news/calendar.py:139` already tags GMT as UTC). FRED gives date-only (US/Eastern release-time assumed; `08:30 ET` for employment, `14:00 ET` for FOMC — table in §3.4). Anything ambiguous → `NaT` and the proximity adapter ignores those rows |
| **Importance mapping** | Dukascopy: `low → 1`, `medium → 2`, `high → 3`. FF: same mapping; `Holiday` and `Non-Economic` excluded from the on-disk table (they live in `data/news_calendar/_holidays.parquet` for the F18 chop-during-holiday slicer). FRED: every release is `3` (FRED only tracks high-impact macro by default) |
| **All-Day / Tentative events** | Preserved in the raw archive with `timestamp = NaT`. Excluded from `load_news_calendar` proximity tagging (no defensible window). A separate `load_news_all_day(date_range, currencies)` helper exists for callers that want full-day tagging (Φ5+, not in this spec) |
| **Future events** | When `index.max()` is in the future relative to the latest archive row, the bars past the archive end return `0` (no tagging — the caller has the freshest available data and the adapter does not pretend otherwise). A warning is emitted naming the staleness window |
| **Empty currencies filter** | `currencies=()` → return `None` (defensive — likely a caller bug; raises `ValueError` only on explicit `None`) |
| **`importance_min` out of range** | `< 1` → coerced to `1` with warning. `> 3` → return all-zeros (filter excludes everything) |

### 3.4 FRED release-time map (for the date → datetime promotion)

| FRED release | Series proxy | Currency | Release time (US/Eastern) | UTC offset (winter / summer) |
|---|---|---|---|---|
| FOMC Statement | `DFEDTAR` proxy | USD | 14:00 ET | 19:00 / 18:00 UTC |
| FOMC Press Conference | n/a | USD | 14:30 ET | 19:30 / 18:30 UTC |
| Employment Situation (NFP) | `PAYEMS` | USD | 08:30 ET | 13:30 / 12:30 UTC |
| CPI (consumer price index) | `CPIAUCSL` | USD | 08:30 ET | 13:30 / 12:30 UTC |
| PPI (producer price index) | `PPIACO` | USD | 08:30 ET | 13:30 / 12:30 UTC |
| Retail Sales | `RSAFS` | USD | 08:30 ET | 13:30 / 12:30 UTC |
| GDP (advance estimate) | `GDP` | USD | 08:30 ET | 13:30 / 12:30 UTC |
| ISM Manufacturing | `NAPM` | USD | 10:00 ET | 15:00 / 14:00 UTC |
| ISM Non-Manufacturing | `NMFCI` | USD | 10:00 ET | 15:00 / 14:00 UTC |

Same map applies for ECB / BoE / BoJ scheduled events (handled by Dukascopy
primary; FRED is US-only and is the cross-check, not the primary, for
non-USD events).

---

## 4. Backfill strategy

### 4.1 One-time backfill (script `scripts/backfill_news_calendar.py`)

```text
For each year y in [2010, 2026]:
    For each currency-pair-relevant currency c in {USD, EUR, GBP, JPY, CAD, AUD, NZD, CHF}:
        events = dukascopy_fetch(
            start=epoch_ms(y, 01, 01), end=epoch_ms(y+1, 01, 01),
            currencies=[c], importance="any",
        )
        write_parquet(events, path=f"data/news_calendar/DK/{y}/{c}.parquet")
    # Sleep 1s between currency calls to be polite to freeserv.
After all years:
    write_manifest("data/news_calendar/DK/_manifest.json")
```

### 4.2 Storage format — Parquet, partitioned

**Format:** Parquet (snappy compression). Justification: Parquet's
column-oriented layout is ~5-10× faster than CSV for the typical
`load_news_calendar` call (filter on `timestamp` range + `currency` ∈
{USD, EUR} + `importance == 3`) because only the relevant columns +
row-groups are read. CSV would force a full-file scan per call.

### 4.3 Folder structure

```text
data/
└── news_calendar/
    ├── DK/                          # Dukascopy primary
    │   ├── _manifest.json           # SHA256 of every file + backfill metadata
    │   ├── 2010/
    │   │   ├── USD.parquet
    │   │   ├── EUR.parquet
    │   │   ├── GBP.parquet
    │   │   └── ... (one per currency)
    │   ├── 2011/
    │   │   └── ...
    │   └── ... (one per year, 2010 → current)
    ├── FF/                          # ForexFactory community-archive fallback
    │   ├── _manifest.json
    │   └── <same year/currency partition layout>
    ├── FRED/                        # FRED cross-check
    │   ├── _manifest.json
    │   └── <same year/currency partition layout, currency always USD>
    ├── _dedup_audit.parquet         # Discarded duplicates (kept for repro)
    ├── _holidays.parquet            # Holiday / Non-Economic entries (FF only)
    └── _unified.parquet             # Optional: dedup-merged single-file view
                                     # for fast bulk loads; rebuilt from per-
                                     # year/currency parquets by the
                                     # update script
```

The unified parquet is **derived** from the per-year files via a single
pyarrow `dataset.write_dataset` call at the end of the backfill, so the
authoritative artefacts are the per-year files and the unified file is a
cache. Deleting `_unified.parquet` always recoverable; deleting a
per-year file requires re-fetching from the source.

### 4.4 Initial backfill window

**2010-01-01 to current date.** Justification:

| Window | Rationale |
|---|---|
| 2010-01-01 start | Matches the parquet cache's earliest EURUSD H4 bar (verified via `multi-pair-trading-agent/data/parquet/EURUSD_H4.parquet`; the production agent's E004 walk-forward also uses 2010+ — `docs/findings/2026-06-09_walk_forward_validation.md`). Pre-2010 FF data has documented value-revision gaps from the 2008-2009 crisis |
| through today | Φ5 wants real-time roll-forward |
| Total span | ~16 years; > 15-year hard floor |

### 4.5 Incremental update — `scripts/update_news_calendar.py`

A cron-friendly script that:

1. Reads `data/news_calendar/DK/_manifest.json:latest_ingested_event_ts`.
2. Fetches Dukascopy for `[latest - 7 days, now]` (7-day overlap window
   to catch back-edits of `actual` values; common 1-3 days after release).
3. Upserts into the relevant `data/news_calendar/DK/<year>/<currency>.parquet`
   files (Parquet append + dedup on `source_event_id`).
4. Rebuilds `_unified.parquet` from the per-year files.
5. Updates `_manifest.json` with the new `latest_ingested_event_ts` and
   bumps `manifest.run_count`.

Run cadence: **daily at 23:00 UTC** (Sunday-Friday) once Φ5 is live.
Pre-Φ5, the script runs ad-hoc when a backtest needs current data.

### 4.6 Storage size estimate

| Quantity | Value | Source |
|---|---|---|
| Events per day (high+med+low, all currencies) | ~30 | Dukascopy empirical (community-reported on r/algotrading) |
| Days per year | 365 |
| Years backfilled | 16 (2010-2026) |
| Total events | ~30 × 365 × 16 ≈ **175 000** |
| Bytes per event (parquet snappy) | ~120 (10 columns × 12 bytes avg after compression) |
| **Total on-disk** | **~21 MB** unified + per-year partitions (rounded up: 50 MB including dedup audit + holidays) |

This is small enough that `data/news_calendar/` could plausibly be
committed to the repo. **It will not be**, per §5.3 of the redistribution
discussion below — the script and manifest are committed, the data is
re-derived locally. A 50 MB binary in git history is not the issue; the
TOS / redistribution risk is.

### 4.7 Reproducibility — manifest

`data/news_calendar/DK/_manifest.json` schema:

```json
{
  "source": "DK",
  "source_url": "https://freeserv.dukascopy.com/2.0/?path=economic_calendar_event/get_economic_calendar_events",
  "parser_version": "news_calendar.py @ <git-sha-at-write-time>",
  "backfill_start_iso": "2010-01-01T00:00:00+00:00",
  "backfill_end_iso": "2026-06-25T00:00:00+00:00",
  "first_ingested_at_utc": "2026-06-26T09:14:32+00:00",
  "latest_ingested_at_utc": "2026-06-26T09:32:18+00:00",
  "latest_ingested_event_ts": "2026-06-25T18:00:00+00:00",
  "total_events": 174523,
  "currencies_covered": ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF"],
  "year_files_sha256": {
    "2010/USD.parquet": "<hex-sha256>",
    "2010/EUR.parquet": "<hex-sha256>",
    "...": "..."
  },
  "run_count": 1,
  "_note": "Manifest is rewritten by every update; older manifests live in git history of this file."
}
```

The git-tracked manifest gives every reproducer (CI, a teammate, future
me) a checksum-verifiable target. The data is local; the manifest is
shared.

---

## 5. Integration with the regime classifier (and downstream)

### 5.1 New module: `sim/regime/news_calendar.py`

The adapter lives in a **new file** (not `validate_real.py`) to keep the
news machinery cohesive. Path: `programs/M001_multi_agent_ensemble/sim/regime/news_calendar.py`.

Public API:

```python
def load_news_events(
    start: datetime, end: datetime, *,
    currencies: Iterable[str] = ("USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF"),
    sources: Iterable[str] = ("DK", "FF", "FRED"),
    importance_min: int = 1,
    archive_root: Path = Path("data/news_calendar"),
) -> pd.DataFrame: ...

def load_news_calendar(
    index: pd.DatetimeIndex, *,
    currencies: Iterable[str] = ("USD", "EUR"),
    sources: Iterable[str] = ("DK", "FF", "FRED"),
    window_bars: int = 2,
    pre_event_bars: int | None = None,    # falls back to window_bars when None
    post_event_bars: int | None = None,
    importance_min: int = 3,
    archive_root: Path = Path("data/news_calendar"),
) -> pd.Series | None: ...

def tag_bars_with_news(
    bars: pd.DataFrame, *,
    symbol_pair: str,   # e.g. "EURUSD" → currencies = ("EUR", "USD")
    **kwargs,
) -> pd.DataFrame:
    """Convenience wrapper: returns `bars` with a `news_calendar` boolean
    column added. Used by F18 KPI consumers."""
    ...
```

### 5.2 Backward-compat proxy in `validate_real.py`

The existing `load_news_calendar` at
`sim/regime/validate_real.py:295` is **rewritten as a 5-line proxy**
that imports the new module and forwards the call. Caller signatures
(used by `run_validation`) are unchanged. This is the ONLY change to
`validate_real.py` and lands as its own commit (so the diff is auditable
in isolation from the regime worker's prior commits).

```python
# sim/regime/validate_real.py:295 (new body)
def load_news_calendar(
    index: pd.DatetimeIndex, *,
    cache_path: Path | None = None,   # legacy arg, ignored; kept for compat
    window_bars: int = 2,
) -> pd.Series | None:
    from programs.M001_multi_agent_ensemble.sim.regime.news_calendar import (
        load_news_calendar as _load,
    )
    return _load(index, currencies=("USD", "EUR"), window_bars=window_bars)
```

`cache_path` is honoured silently (passes through as `archive_root` if
the caller really wants to point at a non-default location, but
production callers leave it unset).

### 5.3 Where the news tag is *joined*, not produced

Per the regime redesign report (`reviews/regime_redesign_2026-06-24.md`
§5.6):

> `label_dataframe`'s `calendar_proximity` arg is now a no-op. … A future
> caller wiring a real calendar adapter must join the news tag
> *downstream* of `label_dataframe`, not by passing it in.

The integration respects this hard constraint. The classifier emits the
2-class OHLCV label (`trending` / `chop`). The news tag is *added as an
additional column* on the F18 KPI input frame, not folded into the
classifier's output:

```python
labels_2class = classifier.label_dataframe(bars)           # trending / chop
news_flag = news_calendar.load_news_calendar(bars.index)   # bool series
f18_input = bars.assign(regime=labels_2class, news_calendar=news_flag.fillna(False))
```

`f18_input` is then sliced by F18 KPI machinery on **both** `regime` and
`news_calendar`. The 4-class taxonomy stays — just produced by two
separate functions instead of one.

### 5.4 Window-of-influence definition

A bar `t` is `news_calendar=True` iff at least one event matching the
filter (`currency`, `importance_min`) has timestamp in
`[t_start - N min, t_end + M min]`.

| Parameter | Default | Rationale |
|---|---|---|
| `pre_event_bars` (N) | **5 minutes** | Matches the production blackout window at `multi-pair-trading-agent/agent/news/blackout.py` (±15 min default; FF's own pre-event window guidance). Pre-event window is short because spreads widen ~5-10 min before a print; we want the bar containing the print AND the bar before |
| `post_event_bars` (M) | **60 minutes** | Empirical post-FOMC / post-NFP price-impact decay studies (Bauer 2015; Faust et al. 2007) — 95 % of the abnormal-return half-life is gone by t+60 min on G10 currencies. Long enough to capture the algo-driven mean-revert that follows the initial spike; short enough that the next bar's "true regime" (trending vs chop) is recoverable |
| `window_bars` (legacy fallback) | 2 H4 bars | Used when `pre_event_bars` / `post_event_bars` are None; matches the original `validate_real.load_news_calendar` default. Approximately 8 hours before + 8 hours after — much wider than the per-minute window, intended for OHLCV-coarse callers |

The per-minute window applies to **intraday timeframes (M1/M5/M15/H1)**;
the bar-count window applies to **H4/D1**. Auto-detection: if
`(index[1] - index[0]).total_seconds() <= 3600` use per-minute; else use
bar-count.

### 5.5 Multi-event handling

When multiple events fall in the same bar's window:

- `news_calendar` column: **OR** — True if any matches.
- A separate optional column `news_calendar_importance_max` carries
  the max importance (1/2/3) of any active event, for F18 callers that
  want per-importance bucketing.
- A separate optional column `news_calendar_n_events` carries the count,
  for diagnostics.

These extra columns are populated by `tag_bars_with_news(...,
verbose=True)` — the default `load_news_calendar` returns only the bool
series.

### 5.6 The new column name: `news_calendar` (not `news`)

Per the regime redesign report §3.2: the OHLCV `news` class was retired.
The new tag is named **`news_calendar`** to make its provenance visible
in every downstream consumer's code: anywhere `news_calendar` appears in
F18 tables, dashboards, or agent KPI columns, the reader knows this is
*not* the retired OHLCV-derived class — it's the exogenous calendar
adapter the regime worker explicitly named as the path forward.

The 4-class `REGIMES` tuple in `sim/regime/classifier.py:67` stays
unchanged (the brief forbids modifying the classifier). The `news` slot
in that tuple remains the retired-OHLCV class and stays empty (per
§6.2 of the redesign report). F18 KPI tables may *render* the
`news_calendar` column under a "news" header in the dashboard for human
readability — that's a presentation concern, not a label-set change.

### 5.7 Where `news_calendar` is consumed (concrete touchpoints)

1. **`sim/scoring/regime_kpis.py`** (Φ5 deliverable, not yet existing) —
   joins `news_calendar` as an extra bucket axis alongside the 2-class
   regime label. **Not modified by this spec.**
2. **`sim/scoring/run_phi*_squad_gate.py`** — when computing per-agent
   regime-conditional KPIs, calls `tag_bars_with_news(bars, symbol_pair=...)`
   and forwards the augmented frame to the KPI module. **Not modified
   by this spec — tomorrow's worker writes the change as a follow-up
   commit after the adapter lands.**
3. **`sim/dashboard/`** (panel 3 — regime-by-agent KPI heatmap, per
   `08-dashboard-spec.md`) — adds `news_calendar` as a third bucket
   column. **Not modified by this spec.**

The dependency direction is intentional: **this spec only delivers the
adapter + archive**. Every downstream consumer change is a separate
deliverable so each lands with its own gate / test surface.

---

## 6. F18 KPI consumer changes

Per `04-quant-foundations.md` §F18 today, the regime taxonomy is:

> r ∈ {trending, chop, vol_spike, news}

After Φ5 wiring, the F18 KPI input axis becomes:

> r_regime ∈ {trending, chop}                  (from `classifier.label_dataframe`)
> r_news ∈ {news_calendar=False, news_calendar=True}   (from `news_calendar.load_news_calendar`)
> r_vol_spike ∈ {False, True}                  (optional opt-in from `redesign_v2.detect_vol_spike_v2b`)

KPI rows are computed on the **Cartesian product** of live axes, with
small cells (n < 30 trades) folded into `unclassified_residual` per the
F18 §"Failure mode" paragraph.

### 6.1 Live classes set transition

| Before this spec | After this spec | F18 column status |
|---|---|---|
| `trending` (live) | `trending` | populated by classifier |
| `chop` (live) | `chop` | populated by classifier |
| `vol_spike` (retired OHLCV) | `vol_spike` | empty (opt-in via `detect_vol_spike_v2b`) |
| `news` (retired OHLCV) | `news_calendar` (NEW) | populated by `news_calendar.load_news_calendar` |

The F18 table goes from **2 populated regimes per agent** (today) to **3
populated buckets per agent** (after this spec lands and the per-agent
KPI module joins the news axis). Hold-out cell:
`(trending=True, news_calendar=True, vol_spike=True)` is a rare but
legitimate combination — F18 must permit per-bar multi-tag and report
the join.

### 6.2 Backward-compat re-bucketing of Φ4.1 telemetry

The Φ4.1 telemetry (`reviews/phi41_squad_v1_trades.jsonl`,
`phi41_squad_v1_proposals_all.jsonl`) carries the bar timestamp of every
trade decision. Once the news archive is loaded, the existing telemetry
can be retroactively re-bucketed by news axis without re-running the
squad gate:

```python
trades = pd.read_json("reviews/phi41_squad_v1_trades.jsonl", lines=True)
trades["bar_ts"] = pd.to_datetime(trades["bar_ts"], utc=True)
news_flag = news_calendar.load_news_calendar(
    pd.DatetimeIndex(trades["bar_ts"]),
    currencies=("USD", "EUR", "CAD"),   # union over all pairs in the run
)
trades["news_calendar"] = news_flag.fillna(False).values
# now re-aggregate TQS by (regime, news_calendar)
```

This unlocks a "Φ4.1 cross-stat addendum on the news axis" report that
adds news bucketing to the Φ4 squad gate verdict **without** re-running
the gate or modifying any of the sealed Φ4 commits — the regime-comparator-
discipline rule (`07-research-standards.md` §11) is preserved because the
gate verdict statistic (median OOS TQS) is unchanged; the news axis is
purely diagnostic.

### 6.3 What does NOT change

- `REGIMES = ("trending", "chop", "vol_spike", "news")` in
  `sim/regime/classifier.py:67` — untouched.
- `label_rule_based` — untouched.
- `label_dataframe` — untouched (its `calendar_proximity` arg stays a
  no-op).
- `redesign_v2.detect_news_ohlcv` (always-False placeholder) —
  untouched. Its retirement reason is structural; this spec adds an
  *exogenous* parallel detector, not a re-opening of the OHLCV detector.
- The G4 gate definition in `09-experiment-architecture.md` §1.5 —
  this spec does not close G4. G4 still requires hand-labelled
  validation bars.

---

## 7. Tests required

Tests live in `programs/M001_multi_agent_ensemble/sim/tests/test_news_calendar.py`
(new file). Total: **8 unit tests + 1 integration test**.

| # | Test name | What it checks | Fixture |
|---|---|---|---|
| 1 | `test_load_news_calendar_schema` | Returned DataFrame matches the §3.1 schema: column names, dtypes, NaN policy, `importance ∈ {1,2,3}` | Synthetic fixture `fixtures/news_calendar/dk_2024_sample.parquet` (20 rows hand-rolled) |
| 2 | `test_load_news_calendar_timezone` | All `timestamp` values carry tz=UTC; tz-naive input → `ValueError` | Same fixture |
| 3 | `test_load_news_calendar_window_filter` | `start`/`end` honored exactly: events at `start - 1ns` excluded, at `end - 1ns` included | Same fixture |
| 4 | `test_load_news_calendar_currency_filter` | `currencies=("USD",)` returns only USD rows; `currencies=("USD","EUR")` returns USD ∪ EUR | Same fixture |
| 5 | `test_news_label_high_importance` | A 2024 NFP release (synthetic ts `2024-07-05 12:30 UTC`) labels the EURUSD H4 bar containing it AND the bar 1-prior AND the bar 1-after as `news_calendar=True` (window_bars=2) | Same fixture + EURUSD H4 2024-07 slice from production parquet |
| 6 | `test_news_label_no_event` | A bar deep inside the Sun-night/Mon-morning gap (synthetic ts `2024-08-04 18:00 UTC`) returns `news_calendar=False` | Same fixture |
| 7 | `test_backfill_idempotency` | Re-running the backfill script over a range that's already cached produces zero new rows and zero diffs in `_manifest.json` other than `run_count += 1` and `latest_ingested_at_utc` | Mock fetcher returning a fixed event list; tmp_path archive |
| 8 | `test_dedup_cross_sources` | A synthetic event emitted by both DK and FF at the same timestamp ± 30 s is deduped to one row with `source="DK"`; the FF row appears in `_dedup_audit.parquet` | Two synthetic fixtures |
| 9 (integration) | `test_2024_nfp_releases_tag_eurusd_h4` | Load real Dukascopy-backed 2024 archive (via committed fixture, NOT live fetch); confirm all 12 monthly NFP release dates land `news_calendar=True` on the corresponding EURUSD H4 bar; confirm cardinality: > 200 `news_calendar=True` H4 bars in 2024 EURUSD (USD+EUR high-impact events, ±2 bar window) | Committed `fixtures/news_calendar/dk_2024_USD.parquet` (~5 KB, real Dukascopy snapshot taken at backfill time) |

### 7.1 Fixture file policy

- Tests 1-7 use **hand-rolled synthetic fixtures** of < 1 KB each.
  Committed under
  `programs/M001_multi_agent_ensemble/sim/tests/fixtures/news_calendar/`.
- Test 8 uses two synthetic fixtures (DK + FF flavour) of < 1 KB each.
- Test 9 (integration) uses **one real Dukascopy snapshot for 2024 USD
  events only** — ~5 KB after parquet compression. This is committed
  because (a) the size is trivial, (b) the snapshot is timestamped in
  the manifest so reproducibility is auditable, and (c) the integration
  test would otherwise require a live fetch every CI run.

This is the same fixture pattern the production repo uses for
`agent/news/calendar.py`'s test suite
(`fixtures/news/ff_calendar_sample.xml`).

### 7.2 Determinism

All tests are deterministic:
- No `datetime.now()` outside test setUp.
- No live HTTP — the backfill script's fetcher is injected via
  dependency injection (same pattern as `agent.news.calendar.fetch_calendar`'s
  `fetcher=` arg).
- Random seeds where needed: `42` (matching the rest of the lab).

---

## 8. Cost + risk + open questions

### 8.1 Estimated cost

| Component | Cost |
|---|---|
| Primary source (Dukascopy) | $0 |
| Fallback source (FF community archive) | $0 |
| Cross-check (FRED) | $0 (key is free, no rate-limit issue) |
| Storage (local) | $0 (~50 MB on disk) |
| Engineering time (tomorrow's first session) | ~5 hours |
| **Monthly steady-state** | **$0** |
| **One-time backfill** | **$0** (~1 hr fetch + 1 hr validation) |

**Override path**: if the user prefers institutional reliability and
approves $75/mo, swap primary to Trading Economics Basic (USD-only).
The schema migration is one column rename (`CalendarId` → `source_event_id`)
and the rest of the spec is unchanged. ~30 min migration.

### 8.2 Legal risk

| Risk | Mitigation |
|---|---|
| FF / Dukascopy TOS forbid redistribution | **Data is not committed.** Only the fetch script + manifest live in git. Each user / CI runner derives the local cache from the source themselves. Documented in `data/news_calendar/README.md` (tomorrow's worker writes this) |
| FF community archives have unclear data licensing | We use Dukascopy as primary; FF is fallback only. When FF is used, the script fetches from FF directly (or from a single hard-pinned community-archive commit-sha), not from a mirror with unknown provenance |
| Source TOS changes | Manifest carries source URL + parser version; if a TOS-driven URL change breaks the fetch, the manifest is the audit trail for "when did we last confirm this URL was valid" |
| Investing.com C&D precedent | Hard rule: Investing.com is REJECTED. Not in the source set |

**Overall legal risk: LOW** for the spec-as-designed (local cache only,
script + manifest committed, data re-derived per user).

### 8.3 Reliability risk

| Risk | Mitigation |
|---|---|
| Dukascopy freeserv goes offline | Fallback chain: FF community archive (§1.1) becomes primary. The script's `--source-order` flag lets a user swap chains without code change |
| Dukascopy schema drift | Parser version is in `_manifest.json`; schema-mismatch detection in `load_news_events` (raise on unexpected field set, not silent-coerce) |
| Network unavailable at backfill time | Backfill is one-time; resume-from-last-success is built in via the manifest's `latest_ingested_event_ts` |
| Event-timestamp drift between DK and FF | < 1 % of overlapping events drift ≥ 1 min (community-verified); the dedup uses ± 60 s window which absorbs this. Document in `news_calendar.py` docstring |
| FRED release-time map (§3.4) goes stale | FRED publishes release schedules in advance; the map is static for known event categories. If a new release category enters our scope, add a row to the map — a 1-line PR change |

**Overall reliability risk: LOW-MEDIUM.** Dukascopy has 12+ years of
freeserv uptime; the fallback chain handles the worst case.

### 8.4 Open questions for the user (**REQUIRED** before tomorrow's worker starts)

**Q1.** Approve **Dukascopy freeserv JSON API** as the primary backfill
source? (Free, 2007+, low effort, local-cache-OK TOS.)
**Yes / No / Override with Trading Economics ($75/mo).**

**Q2.** Approve **ForexFactory community archive** as fallback (TOS-grey
for local caching, no redistribution)?
**Yes / No / Skip fallback and use Dukascopy alone.**

**Q3.** Approve $0/month steady-state cost?
**Yes / Approve up to $X/month for a paid source.**

**Q4.** Accept the **legal posture** of committing the fetch script +
manifest but NOT the data itself (each user re-derives locally)?
**Yes / No / Commit a public-domain-only archive (FRED-only, US-only,
no time-of-day, severely limits coverage).**

**Q5.** Approve the window-of-influence defaults — **pre 5 min, post
60 min** (intraday) and **±2 bars** (H4/D1)?
**Yes / No (specify alternative).**

**Q6.** Approve the new column name **`news_calendar`** (kept distinct
from the retired `news` regime class to make provenance visible in every
downstream consumer)?
**Yes / No (rename to: ___).**

**Q7.** Pre-2010 coverage — Dukascopy goes back to 2007 but the parquet
cache only starts ~2010 for most pairs. Backfill **2007-01-01** (gives a
~3-year news head start for any future deep-history experiment) or
**2010-01-01** (matches the parquet cache exactly)?
**2007 / 2010 / other.**

**Q8.** Run the **integration test (test #9) on every CI run** (~5 KB
fixture committed), or gate it behind a `pytest --slow` marker?
**Every run / `--slow` only.**

---

## 9. Tomorrow's first-15-minutes execution checklist

Precise sequence. Each step is independent and verifiable.

1. **(0-2 min) Read this spec end-to-end.** Confirm the user has answered
   Q1-Q8. **If any answer is missing, stop and surface the gap.**
2. **(2-5 min) Verify branch + tree.** `git status` on
   `multi-agent-ensemble`; clean tree; pull latest.
3. **(5-7 min) Create `data/news_calendar/` folder skeleton.**
   `mkdir -p data/news_calendar/{DK,FF,FRED}`. Write
   `data/news_calendar/README.md` explaining the no-redistribution
   policy and pointing back to this spec.
4. **(7-15 min) Write `scripts/backfill_news_calendar.py` skeleton.**
   Argparse: `--source DK --start 2010-01-01 --end <today>
   --currencies USD,EUR,GBP,JPY,CAD,AUD,NZD,CHF --out data/news_calendar/`.
   Inject the fetcher (default: real Dukascopy GET; test: stub returning
   fixed events). Keep < 200 LoC.

(Subsequent steps continue after the 15-min marker — listed here so the
worker doesn't have to re-derive the plan.)

5. **(15-30 min) Run backfill for 2024 only** as smoke test:
   `python scripts/backfill_news_calendar.py --start 2024-01-01 --end 2025-01-01`.
   Verify ~6 000 events on disk; check `_manifest.json` populated.
6. **(30-45 min) Write `sim/regime/news_calendar.py`** with the §3.2 API.
   Implement `load_news_events` + `load_news_calendar` reading from the
   parquet partitions.
7. **(45-60 min) Write the 8 unit tests + 1 integration test from §7.**
   Run `pytest -q sim/tests/test_news_calendar.py` — target green.
8. **(60-75 min) Validate the §3.1 schema** by loading the 2024 backfill
   and asserting columns / dtypes match. This is the first real-data
   check.
9. **(75-90 min) Write the `validate_real.py:295` proxy** (5-line change,
   §5.2). Commit separately as `M001 Φ5: news_calendar — proxy
   validate_real.load_news_calendar to new module`.
10. **(90-120 min) Smoke-test against an existing F18 caller.** Pick
    `reviews/phi41_squad_v1_trades.jsonl` (3000+ EURUSD/USDCAD H4 trades);
    join the news axis (§6.2 snippet); verify the resulting frame has
    `news_calendar` column and ~10-15 % True rate on 2024 H4 bars.
11. **(120-150 min) Full 2010-2026 backfill** in the background (~1 hr).
    While running, write `data/news_calendar/README.md` + update
    `DATA_LEDGER.md` with a row for the news archive.
12. **(150-180 min) Re-run regime evaluation** with the news axis joined
    downstream. **Do NOT modify `classifier.py`.** The expected output is
    that `news_calendar=True` bars show up in F18-shaped tables (verify
    by manual `groupby` on the augmented frame; the F18 module itself
    isn't built yet — that's a follow-up).
13. **(180-210 min) Commit + report.** Two or three commits per the
    `M001 prep: <subject>` pattern (one for the script + folder + tests,
    one for `news_calendar.py`, one for the `validate_real.py` proxy).
14. **(210+ min)** Open a follow-up issue / TODO for: (a) F18 module
    consumption of `news_calendar`, (b) `news_calendar` panel in the
    Streamlit dashboard, (c) cron wiring of `update_news_calendar.py`.

---

## 10. Appendix: API quick-reference (Dukascopy endpoint shape)

For the implementer — this is what tomorrow's GET should look like once
the spec is approved. **Not called tonight.**

```text
GET https://freeserv.dukascopy.com/2.0/?path=economic_calendar_event/get_economic_calendar_events
    &start=1704067200000           # epoch ms; 2024-01-01 00:00 UTC
    &end=1735689600000             # epoch ms; 2025-01-01 00:00 UTC
    &countries=USD,EUR,GBP         # comma-separated; subset of supported
Headers:
    User-Agent: multi-pair-trading-agent/m001-news-backfill (research)

Expected response (JSON array):
[
  {
    "id": "d_42091872",
    "ts": 1720196100000,           # epoch ms UTC
    "country": "USD",
    "title": "Non-Farm Employment Change",
    "importance": "high",
    "unit": "K",
    "previous": 218.0,
    "forecast": 190.0,
    "actual": 206.0
  },
  ...
]
```

The implementer maps `country → currency`, `importance` (`low|medium|high`)
→ `int8 ∈ {1,2,3}`, and writes to the §3.1 schema. ~10 LoC.

---

## 11. References

- Motivation: `programs/M001_multi_agent_ensemble/reviews/regime_redesign_2026-06-24.md` §3.2 + §5.6
- Retired classifier: `programs/M001_multi_agent_ensemble/sim/regime/classifier.py:35-42` + `124-148`
- Existing adapter stub: `programs/M001_multi_agent_ensemble/sim/regime/validate_real.py:295-344`
- F18 consumer: `programs/M001_multi_agent_ensemble/04-quant-foundations.md` §F18 (lines 748-815)
- Verdict-comparator discipline: `programs/M001_multi_agent_ensemble/07-research-standards.md` §11
- Pre-registered protocol style (E010): `experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md`
- Production calendar adapter (pattern source): `multi-pair-trading-agent/agent/news/calendar.py`
- Production blackout consumer: `multi-pair-trading-agent/agent/news/blackout.py`
- Doctrine link to news-window agents:
  - A3 Itoshi Rin (precision floor): `05-agent-roster-v0.md` §3.3
  - A8 Kenyu Yukimiya (timing refiner): `05-agent-roster-v0.md` §3.8
  - A9 Aoshi Tokimitsu (macro-event-only): `05-agent-roster-v0.md` §3.9
- Sibling decision tree: `news_calendar_wiring_DECISION_TREE.md` (this folder)
