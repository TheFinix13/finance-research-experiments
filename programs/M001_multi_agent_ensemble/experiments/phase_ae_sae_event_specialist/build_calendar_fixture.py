"""Phase AE frozen calendar fixture builder (run ONCE, 2026-07-24).

Builds ``programs/M001_multi_agent_ensemble/data/
news_calendar_frozen_2026-07-24.json`` — the frozen high-impact-USD
event calendar shared by Phase AD / Phase AE (Phase AD PROTOCOL §7).

Background: the pre-registered Dukascopy backfill (Phase 6c) was
HALTED 2026-07-03 (endpoint deprecated; see
``data/news_calendar/STOP_NOTICE.md``), so the archive is empty and
the AD §7 fixture was never frozen. This builder derives the fixture
from PRIMARY official sources instead (US-government public domain —
committable, unlike the DK/FF TOS-restricted feeds):

1. **BLS Employment Situation** (NFP) release schedule — official BLS
   schedule pages ``schedule/news_release/empsit.htm``, fetched via
   pinned Internet Archive snapshots (BLS blocks bot fetches of the
   live page; the snapshots are byte-archived copies of the official
   page, provenance recorded per snapshot).
2. **BLS Consumer Price Index** release schedule — same mechanism,
   ``schedule/news_release/cpi.htm``.
3. **FOMC scheduled-meeting statements** — federalreserve.gov meeting
   calendars (live fetch works). Historical year pages 2015-2020 are
   parsed from their ``<h5>`` panel headings and entries marked
   ``(unscheduled)`` / ``(cancelled)`` / ``(notation vote)`` are
   EXCLUDED (rule-based, no manual editing); 2021+ scheduled
   statements are taken from the statement links on
   ``fomccalendars.htm``. Statement release time is 14:00 ET (Fed
   standard for scheduled meetings since 2013).

Scope note (disclosed in the Phase AE pre-run amendment): this is a
CONSERVATIVE SUBSET of "high-impact USD" (NFP + CPI + FOMC only,
~32 events/yr ≈ 2.7/month vs the protocol's 4-8/month prior for the
full ForexFactory High set). GDP/ISM/retail-sales prints are not
included because no TOS-clean primary source with reliable historical
timestamps was available at freeze time.

All times converted ET → UTC via zoneinfo("America/New_York") (DST
correct). Window: 2015-01-01 .. 2025-12-31 (the §11.17 panel).

2025 shutdown handling (rule-based, no manual date edits): the
Oct-Nov 2025 US government shutdown suspended BLS releases (Sep NFP
delayed to Nov 20; Oct NFP never released standalone; Oct CPI never
published; several prints rescheduled). Early-2025 snapshots assert
the ORIGINAL schedule, the Dec-2025 snapshots retroactively assert
the ACTUAL release dates. Resolution rule: a later snapshot
SUPERSEDES earlier ones over its parsed coverage span — a date
asserted only by an earlier snapshot is dropped when a later
snapshot's span covers that date but does not list it. Expected 2025
counts are therefore 11/11/8 (empsit/cpi/fomc), not 12/12/8.
The FOMC calendar parse likewise excludes meeting blocks whose date
cell carries ``(notation vote)`` / ``(unscheduled)`` / ``(cancelled)``
(e.g. the 2025-08-22 notation-vote Statement on Longer-Run Goals).

NEVER refetch / regenerate after the freeze commit. The fixture file
carries a manifest with the sha256 of every fetched page.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PANEL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
PANEL_END = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)

# Pinned Internet Archive snapshots of the official BLS schedule pages.
# Chosen so consecutive snapshots' ~14-month forward tables chain over
# 2015-2025 with overlap (overlaps dedupe on release date).
BLS_SNAPSHOTS: dict[str, list[str]] = {
    "empsit": [
        "20150112110626", "20151108140129", "20161102205218",
        "20170712082328", "20180403044014", "20180709171127",
        "20190109020429", "20191216030043", "20201210210550",
        "20220110090111", "20230101123540", "20240104231820",
        "20250104044052", "20251218182154",
    ],
    "cpi": [
        "20150106084259", "20151104144625", "20161113011116",
        "20170712123245", "20180910095325", "20190109024228",
        "20191216023559", "20201223200317", "20220109075526",
        "20230104040906", "20240104231820", "20250104044048",
        "20251201084332",
    ],
}
BLS_TITLES = {"empsit": "Employment Situation (NFP)", "cpi": "Consumer Price Index"}

FOMC_HISTORICAL_YEARS = [2015, 2016, 2017, 2018, 2019, 2020]
FOMC_CALENDARS_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


def _fetch(url: str, attempts: int = 4) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            return (
                raw.decode("utf-8", errors="replace"),
                hashlib.sha256(raw).hexdigest(),
            )
        except Exception as err:  # archive.org rate-limits burst fetches
            last_err = err
            if i < attempts - 1:
                time.sleep(15 * (i + 1))
    raise RuntimeError(f"fetch failed after {attempts} attempts: {url}") from last_err


def _month_num(name: str) -> int:
    key = name.strip().rstrip(".").lower()
    if key not in MONTHS:
        raise ValueError(f"unknown month name: {name!r}")
    return MONTHS[key]


def parse_bls_schedule(html: str) -> list[tuple[datetime, str]]:
    """Extract (release_datetime_ET, time_string) rows from a BLS page.

    Rows look like ``|Nov. 05, 2021|  |08:30 AM|`` after tag-stripping.
    """
    text = re.sub(r"<[^>]+>", "|", html)
    text = re.sub(r"[|\s]+", "|", text)
    rows: list[tuple[datetime, str]] = []
    pat = re.compile(
        r"\|([A-Z][a-z]+)\.?\|?(\d{1,2}),\|?(\d{4})\|(\d{2}):(\d{2})\|([AP]M)\|"
    )
    for m in pat.finditer(text):
        mon, day, year, hh, mm, ap = m.groups()
        hour = int(hh) % 12 + (12 if ap == "PM" else 0)
        dt = datetime(int(year), _month_num(mon), int(day), hour, int(mm), tzinfo=ET)
        rows.append((dt, f"{hh}:{mm} {ap}"))
    return rows


def parse_fomc_historical(html: str, year: int) -> list[datetime]:
    """Scheduled-meeting statement datetimes (14:00 ET) from an
    ``fomchistoricalYYYY.htm`` page's <h5> panel headings.

    Keeps only plain ``<Month> <D>[-D2] Meeting - YYYY`` headings;
    ``(unscheduled)`` / ``(cancelled)`` / ``(notation vote)`` panels
    are excluded by the regex (no parenthetical allowed).
    """
    out: list[datetime] = []
    for h in re.findall(r"<h5[^>]*>(.*?)</h5>", html, re.S):
        h = re.sub(r"<[^>]+>", "", h).strip()
        m = re.match(
            rf"^([A-Z][a-z]+)(?:/[A-Z][a-z]+)?\s+(\d{{1,2}})(?:-(\d{{1,2}}))?\s+Meeting\s+-\s+{year}$",
            h,
        )
        if not m:
            continue
        mon_name, d1, d2 = m.groups()
        # For a cross-month "January/February 31-1" style range the end
        # day belongs to the SECOND month.
        month = _month_num(mon_name)
        end_day = int(d2) if d2 else int(d1)
        if d2 and int(d2) < int(d1):
            month += 1
        slash = re.match(r"^([A-Z][a-z]+)/([A-Z][a-z]+)", h)
        if slash and d2:
            month = _month_num(slash.group(2))
        out.append(datetime(year, month, end_day, 14, 0, tzinfo=ET))
    return out


def parse_fomc_calendars(html: str) -> list[datetime]:
    """Statement dates (14:00 ET) for SCHEDULED meetings on fomccalendars.htm.

    The page is a sequence of ``fomc-meeting`` blocks; a block whose
    date cell carries ``(notation vote)`` / ``(unscheduled)`` /
    ``(cancelled)`` is excluded — same rule as the historical pages
    (e.g. the 2025-08-22 notation-vote Statement on Longer-Run Goals).
    """
    out: list[datetime] = []
    # NB: the Fed page emits a stray attribute after class
    # (``<div class="row fomc-meeting" ">``), so match any tag tail.
    for block in re.split(r'<div class="[^"]*\bfomc-meeting"[^>]*>', html)[1:]:
        date_m = re.search(r"fomc-meeting__date[^>]*>(.*?)</div>", block, re.S)
        if date_m and re.search(
            r"\((?:notation vote|unscheduled|cancell?ed)\)", date_m.group(1), re.I
        ):
            continue
        for d in re.findall(r"monetary(\d{8})a\.htm", block):
            out.append(
                datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), 14, 0, tzinfo=ET)
            )
    return sorted(set(out))


def main() -> int:
    m001 = Path(__file__).resolve().parents[2]  # .../M001_multi_agent_ensemble
    out_path = m001 / "data" / "news_calendar_frozen_2026-07-24.json"
    if out_path.exists():
        print(f"REFUSING to overwrite frozen fixture: {out_path}", file=sys.stderr)
        return 1

    manifest: list[dict] = []
    events: dict[tuple[str, str], dict] = {}

    # --- BLS (NFP + CPI) -------------------------------------------------
    # Later snapshots SUPERSEDE earlier ones over their parsed coverage
    # span (min..max release date on the page): a date asserted only by
    # an earlier snapshot is dropped when a later snapshot covers that
    # date but does not list it. This resolves the Oct-Nov 2025 shutdown
    # reschedules rule-based (no manual date edits).
    for series, snaps in BLS_SNAPSHOTS.items():
        parsed: list[tuple[str, dict]] = []  # (snapshot_ts, {date: (dt_et,)})
        for ts in snaps:
            url = (
                f"http://web.archive.org/web/{ts}/"
                f"https://www.bls.gov/schedule/news_release/{series}.htm"
            )
            html, sha = _fetch(url)
            rows = parse_bls_schedule(html)
            manifest.append({
                "source": f"BLS {series} schedule (official page via "
                          f"Internet Archive snapshot {ts})",
                "url": url, "sha256": sha, "rows_parsed": len(rows),
            })
            if not rows:
                print(f"WARNING: 0 rows parsed from {url}", file=sys.stderr)
            parsed.append((ts, {dt.date(): dt for dt, _ in rows}))
        parsed.sort(key=lambda p: p[0])
        for ts, by_date in parsed:
            for date, dt_et in by_date.items():
                superseded = any(
                    ts2 > ts
                    and later
                    and min(later) <= date <= max(later)
                    and date not in later
                    for ts2, later in parsed
                )
                if superseded:
                    continue
                dt_utc = dt_et.astimezone(timezone.utc)
                if not (PANEL_START <= dt_utc <= PANEL_END):
                    continue
                key = (series, dt_utc.date().isoformat())
                events[key] = {
                    "time_utc": dt_utc.isoformat(),
                    "currency": "USD",
                    "impact": "High",
                    "title": BLS_TITLES[series],
                    "time_local_et": dt_et.isoformat(),
                    "source": f"BLS official schedule (snapshot {ts})",
                }

    # --- FOMC ------------------------------------------------------------
    fomc: list[tuple[datetime, str]] = []
    for y in FOMC_HISTORICAL_YEARS:
        url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm"
        html, sha = _fetch(url)
        dts = parse_fomc_historical(html, y)
        manifest.append({
            "source": f"Federal Reserve FOMC historical calendar {y} "
                      "(scheduled meetings only; unscheduled/cancelled/"
                      "notation-vote panels excluded)",
            "url": url, "sha256": sha, "rows_parsed": len(dts),
        })
        fomc.extend((d, url) for d in dts)
    html, sha = _fetch(FOMC_CALENDARS_URL)
    cal_dts = [d for d in parse_fomc_calendars(html) if d.year >= 2021]
    manifest.append({
        "source": "Federal Reserve fomccalendars.htm (2021+ scheduled "
                  "statement links)",
        "url": FOMC_CALENDARS_URL, "sha256": sha, "rows_parsed": len(cal_dts),
    })
    fomc.extend((d, FOMC_CALENDARS_URL) for d in cal_dts)
    for dt_et, src in fomc:
        dt_utc = dt_et.astimezone(timezone.utc)
        if not (PANEL_START <= dt_utc <= PANEL_END):
            continue
        key = ("fomc", dt_utc.date().isoformat())
        events[key] = {
            "time_utc": dt_utc.isoformat(),
            "currency": "USD",
            "impact": "High",
            "title": "FOMC Statement (scheduled)",
            "time_local_et": dt_et.isoformat(),
            "source": src,
        }

    # --- Validate --------------------------------------------------------
    per_year: dict[int, dict[str, int]] = {}
    for (series, _), ev in events.items():
        y = int(ev["time_utc"][:4])
        per_year.setdefault(y, {}).setdefault(series, 0)
        per_year[y][series] += 1
    problems = []
    for y in range(2015, 2026):
        c = per_year.get(y, {})
        # 2025: Oct-Nov government shutdown — Oct NFP & Oct CPI never
        # released standalone, several prints rescheduled → 11 actual
        # releases for each BLS series that calendar year.
        want_bls = 11 if y == 2025 else 12
        if c.get("empsit", 0) != want_bls:
            problems.append(f"{y}: empsit={c.get('empsit', 0)} (want {want_bls})")
        if c.get("cpi", 0) != want_bls:
            problems.append(f"{y}: cpi={c.get('cpi', 0)} (want {want_bls})")
        want_fomc = 7 if y == 2020 else 8   # 2020: March meeting cancelled
        if c.get("fomc", 0) != want_fomc:
            problems.append(f"{y}: fomc={c.get('fomc', 0)} (want {want_fomc})")
    print(json.dumps(per_year, indent=2, sort_keys=True))
    if problems:
        print("VALIDATION FAILURES:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 2

    ev_list = sorted(events.values(), key=lambda e: e["time_utc"])
    payload = {
        "fixture_name": "news_calendar_frozen_2026-07-24",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "window": [PANEL_START.isoformat(), PANEL_END.isoformat()],
        "event_types": ["Employment Situation (NFP)", "Consumer Price Index",
                        "FOMC Statement (scheduled)"],
        "scope_note": (
            "Conservative subset of high-impact USD (NFP+CPI+FOMC only); "
            "~2.7 events/month vs the FF-High 4-8/month prior. See Phase "
            "AE PROTOCOL pre-run amendment 2026-07-24."
        ),
        "n_events": len(ev_list),
        "manifest": manifest,
        "events": ev_list,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"WROTE {out_path} ({len(ev_list)} events) sha256={sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
