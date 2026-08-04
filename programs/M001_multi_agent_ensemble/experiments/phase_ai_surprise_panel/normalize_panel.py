"""Phase AI: join the MT5 calendar export against the frozen 349-event panel.

Input : data/calendar_history_usd.csv  (from ExportCalendarHistory.mq5;
        times are MT5 SERVER time -- pass --server-utc-offset to shift)
Output: data/surprise_panel.json  (one row per matched frozen event)
        data/panel_gaps.json      (every unmatched frozen event + reason)

Matching: nearest MT5 calendar row of a mapped event family within
±30 minutes of the frozen event's UTC timestamp.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CAL = HERE.parent / "phase_ag_event_first_move" / "data" / "news_calendar_frozen_2026-07-24.json"

# Frozen-panel title -> substrings expected in the MT5 event name.
FAMILY_MAP = {
    "Employment Situation (NFP)": ["nonfarm payrolls"],
    "Consumer Price Index": ["cpi", "consumer price index"],
    "FOMC Statement (scheduled)": ["fomc", "fed interest rate", "federal funds rate"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-utc-offset", type=float, default=0.0,
                    help="hours to SUBTRACT from MT5 times to get UTC")
    args = ap.parse_args()

    csv = HERE / "data" / "calendar_history_usd.csv"
    df = pd.read_csv(csv)
    df["time_utc"] = (pd.to_datetime(df["time_utc"])
                      - timedelta(hours=args.server_utc_offset))
    df["name_lower"] = df["event_name"].str.lower()

    frozen = json.loads(CAL.read_text())
    events = frozen["events"] if isinstance(frozen, dict) else frozen

    panel, gaps = [], []
    for e in events:
        t = datetime.fromisoformat(e["time_utc"]).replace(tzinfo=None)
        subs = FAMILY_MAP.get(e["title"])
        if subs is None:
            gaps.append({**e, "reason": "no family mapping"})
            continue
        cand = df[df["name_lower"].str.contains("|".join(subs), regex=True)]
        cand = cand[(cand["time_utc"] >= t - timedelta(minutes=30))
                    & (cand["time_utc"] <= t + timedelta(minutes=30))]
        cand = cand[cand["actual"] != "EMPTY_VALUE"]
        if cand.empty:
            gaps.append({**e, "reason": "no MT5 row within ±30min with actual"})
            continue
        # NFP: prefer the headline payrolls row if several match.
        row = cand.iloc[(cand["time_utc"] - t).abs().argsort().iloc[0]]
        panel.append({
            "time_utc": e["time_utc"], "title": e["title"],
            "mt5_event": row["event_name"],
            "actual": float(row["actual"]),
            "forecast": None if row["forecast"] in ("EMPTY_VALUE", "") else float(row["forecast"]),
            "previous": None if row["previous"] in ("EMPTY_VALUE", "") else float(row["previous"]),
        })

    # Surprise + per-family z-score (std of surprises within the family).
    pdf = pd.DataFrame(panel)
    if not pdf.empty:
        pdf["surprise"] = pdf["actual"] - pdf["forecast"]
        pdf["surprise_z"] = pdf.groupby("title")["surprise"].transform(
            lambda s: (s - 0) / s.std(ddof=1))
        panel = json.loads(pdf.to_json(orient="records"))

    (HERE / "data" / "surprise_panel.json").write_text(json.dumps(panel, indent=1))
    (HERE / "data" / "panel_gaps.json").write_text(json.dumps(gaps, indent=1))
    print(f"matched {len(panel)} / {len(events)}; gaps {len(gaps)}")


if __name__ == "__main__":
    main()
