"""Phase AH (Sae v2 S3): FOMC statement tone -> post-release EURUSD drift.

Dictionary and floors are pre-registered in PROTOCOL.md. Run:

    python run_phase_ah.py --window is
    python run_phase_ah.py --window validation   # only if IS-alive
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
CAL = HERE.parent / "phase_ag_event_first_move" / "data" / "news_calendar_frozen_2026-07-24.json"
STATEMENTS = HERE / "data" / "statements"
PARQUET = "/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/data/parquet/EURUSD_M15.parquet"
PIP = 1e4

HAWKISH = [
    "inflation pressures", "elevated inflation", "upside risks",
    "tighten", "tightening", "restrictive",
    "raise the target range", "increase the target range",
    "strong labor market", "robust", "solid pace", "above 2 percent",
    "persistent inflation", "further rate increases",
    "reducing its holdings", "balance sheet reduction",
]
DOVISH = [
    "accommodative", "accommodation",
    "lower the target range", "reduce the target range",
    "cut", "easing", "downside risks", "weak", "weakness", "slowed",
    "softening", "muted inflation", "below 2 percent", "patient",
    "moderate pace", "supporting the flow of credit",
    "asset purchases", "maintain the target range at 0",
]

WINDOWS = {"is": ("2015-01-01", "2021-12-31"),
           "validation": ("2022-01-01", "2025-12-31")}


def _statement_text(ymd: str) -> str | None:
    p = STATEMENTS / f"monetary{ymd}a.htm"
    if not p.exists():
        return None
    html = p.read_text(errors="ignore")
    # Whole-page text: the naive article-div regex truncated at the first
    # nested </div> (bug found 2026-08-04, disclosed in REPORT). Page
    # boilerplate is near-constant across statements, so it contributes
    # ~0 to the ΔTone difference that the test actually uses.
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _count(text: str, terms: list[str]) -> int:
    total = 0
    for t in terms:
        total += len(re.findall(r"\b" + re.escape(t) + r"\b", text))
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("is", "validation"), required=True)
    args = ap.parse_args()

    d = json.loads(CAL.read_text())
    evs = sorted(
        (e for e in (d["events"] if isinstance(d, dict) else d)
         if e["title"].startswith("FOMC Statement")),
        key=lambda e: e["time_utc"],
    )

    # Score ALL statements in panel order (ΔTone needs the previous one,
    # including across the IS/validation boundary).
    scored = []
    for e in evs:
        ymd = e["time_local_et"][:10].replace("-", "")
        text = _statement_text(ymd)
        if text is None:
            continue
        nh, nd = _count(text, HAWKISH), _count(text, DOVISH)
        score = (nh - nd) / (nh + nd) if (nh + nd) else 0.0
        scored.append({
            "time_utc": e["time_utc"], "ymd": ymd,
            "n_hawk": nh, "n_dove": nd, "score": round(score, 4),
        })
    for i, s in enumerate(scored):
        s["delta_tone"] = None if i == 0 else round(
            s["score"] - scored[i - 1]["score"], 4)

    df_px = pd.read_parquet(PARQUET)
    idx = df_px.index
    c = df_px["close"].to_numpy()

    rows = []
    for s in scored:
        t = datetime.fromisoformat(s["time_utc"])
        i0 = idx.searchsorted(t)
        if i0 <= 1 or i0 + 16 >= len(c) or s["delta_tone"] is None:
            continue
        ref = c[i0 - 1]
        rows.append({
            **s,
            "pips_1h": (c[i0 + 3] - ref) * PIP,
            "pips_4h": (c[i0 + 15] - ref) * PIP,
        })
    all_df = pd.DataFrame(rows)
    scores_csv = HERE / "results" / "statement_scores.csv"
    scores_csv.parent.mkdir(exist_ok=True)
    all_df.to_csv(scores_csv, index=False)

    lo, hi = WINDOWS[args.window]
    w = all_df[(all_df["time_utc"] >= lo) & (all_df["time_utc"] <= hi + "T23:59:59")]
    usable = w[w["delta_tone"] != 0]
    n = len(usable)
    res = {"window": [lo, hi], "n_statements_in_window": len(w),
           "n_usable_nonzero_delta": n,
           "n_zero_delta_excluded": int((w["delta_tone"] == 0).sum())}
    for hz in ("pips_1h", "pips_4h"):
        # Hawkish shift (ΔTone>0) predicts EURUSD DOWN: agreement when
        # sign(pips) == -sign(ΔTone).
        agree = (np.sign(usable[hz]) == -np.sign(usable["delta_tone"])).mean()
        rho, p = spearmanr(usable["delta_tone"], usable[hz])
        res[hz] = {"sign_agreement": round(float(agree), 4),
                   "spearman_rho": round(float(rho), 4),
                   "spearman_p": round(float(p), 4)}
    if args.window == "is":
        r1 = res["pips_1h"]
        res["is_alive"] = bool(
            n >= 35 and r1["sign_agreement"] >= 0.58
            and r1["spearman_rho"] <= -0.20)
    else:
        r1 = res["pips_1h"]
        res["validation_pass"] = bool(
            r1["sign_agreement"] >= 0.55 and r1["spearman_rho"] < 0)

    dest = HERE / "results" / f"tone_test_{args.window}.json"
    dest.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
