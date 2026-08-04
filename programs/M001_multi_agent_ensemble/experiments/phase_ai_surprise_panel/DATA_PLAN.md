# Phase AI — S1 surprise panel: data acquisition plan

Status: 2026-08-04 — TOOLING READY, DATA PENDING (needs one run on the
trading VM). The S1 protocol will be registered only after the panel
lands and its coverage is audited; registering floors before knowing
event coverage would be theatre.

## Why the panel doesn't exist yet

The live ForexFactory feed carries `forecast`/`previous` but no
`actual`, and serves ONLY the current week (probed 2026-08-04: no
historical week parameter; `ff_calendar_lastweek.xml` is 404). The
Phase AE frozen calendar has primary-source TIMESTAMPS only.
Scraping forexfactory.com's calendar archive is Cloudflare-protected
and TOS-hostile. FRED/ALFRED gives first-release ACTUALS but no
consensus.

## Chosen source: MetaQuotes economic calendar (MT5 terminal)

The Exness demo MT5 terminal on the trading VM ships the MQL5
economic calendar with full history — event timestamps, ACTUAL,
FORECAST, PREVIOUS, revised — via `CalendarValueHistory()`. This is
already licensed, already installed, and machine-readable without
scraping.

Plan:
1. Copy `ExportCalendarHistory.mq5` (this folder) into the terminal's
   `MQL5/Scripts/`, compile in MetaEditor, run once on any chart.
   It writes `calendar_history_usd.csv` into `MQL5/Files/` covering
   2015-01-01 → today, USD high-impact events.
2. Pull the CSV back to this folder as `data/calendar_history_usd.csv`
   (runbook: same scp/shared-folder path as report bundles).
3. Run `normalize_panel.py` to join it against the frozen 349-event
   panel (by timestamp proximity ±30 min + event-name mapping) and
   emit `data/surprise_panel.json` with per-event
   {actual, forecast, previous, surprise, surprise_z}.
4. Audit coverage: every one of the 349 events must either match or
   be listed in `data/panel_gaps.json` with a reason. THEN register
   the S1 protocol (grid + floors) as PROTOCOL.md in this folder.

## S1 hypothesis preview (not yet registered)

From Phase AG's registered near-miss: continuation edge concentrates
in ≥8×ATR reactions (~4/year, +14–19 pips/trade IS) but is
n-starved and only identifiable K bars AFTER the release. S1 tests
whether |surprise_z| ≥ threshold identifies those movers AT t0,
recovering entry price and expanding usable sample via lower-m arms
conditioned on surprise instead of realized impulse.
