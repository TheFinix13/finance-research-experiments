"""Phase AH: fetch the 87 scheduled FOMC statements from federalreserve.gov.

URL convention: /newsevents/pressreleases/monetary<YYYYMMDD>a.htm
(the 'a' release is the policy statement). Raw HTML archived verbatim;
failures logged, never guessed.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAL = HERE.parent / "phase_ag_event_first_move" / "data" / "news_calendar_frozen_2026-07-24.json"
OUT = HERE / "data" / "statements"
UA = {"User-Agent": "Mozilla/5.0 (research; finance-research-experiments)"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    d = json.loads(CAL.read_text())
    evs = [e for e in (d["events"] if isinstance(d, dict) else d)
           if e["title"].startswith("FOMC Statement")]
    print(f"{len(evs)} FOMC statements in panel")
    failures = []
    for e in evs:
        t = datetime.fromisoformat(e["time_utc"])
        # Statement day in US/Eastern equals the UTC date here (14:00 ET).
        ymd = e["time_local_et"][:10].replace("-", "")
        dest = OUT / f"monetary{ymd}a.htm"
        if dest.exists() and dest.stat().st_size > 5000:
            continue
        url = f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{ymd}a.htm"
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read()
            dest.write_bytes(html)
            print(f"ok   {ymd} ({len(html)} bytes)")
        except Exception as exc:  # noqa: BLE001
            failures.append({"date": ymd, "url": url, "error": str(exc)})
            print(f"FAIL {ymd}: {exc}")
        time.sleep(0.7)
    (HERE / "data" / "fetch_failures.json").write_text(json.dumps(failures, indent=2))
    print(f"done; {len(failures)} failures")


if __name__ == "__main__":
    main()
