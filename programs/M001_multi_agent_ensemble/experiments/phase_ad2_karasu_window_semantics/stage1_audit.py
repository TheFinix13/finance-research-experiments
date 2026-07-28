"""Phase AD.2 Stage 1 — Karasu window anchor semantics disagreement audit.

Pre-registered in PROTOCOL.md (incl. the 1b pre-run amendment). Computes,
for every H4 evaluation point on the phi41 physical panel and for the
5,236 actually-admitted trades, the R7 ladder outcome under three anchor
semantics:

  A (current):  as_of = bar OPEN label            (what the engine does)
  B (entry):    as_of = bar close = open + 4 h    (the real entry moment)
  C (forward):  protect [entry, entry + 4 h]      (the holding bar)

Window rule replicated from the trading agent's
``agent/squad/agents/a08_karasu.py`` (NOT imported — the research repo
never imports agent code): an event gates ``as_of`` iff
``event - 15 min <= as_of <= event + 15 min``. Fixture is High-impact
USD only, so the outcome is binary (block / none).

Outputs ``results_stage1.json`` next to this file. Locked gate (§2):
S1 < 1 % of evaluation points AND S2 == 0 flipped admissions -> NULL
verdict, stop; otherwise Stage 2 opens.
"""
from __future__ import annotations

import bisect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
M001 = HERE.parents[1]

FIXTURE = M001 / "data" / "news_calendar_frozen_2026-07-24.json"
TRADES = M001 / "reviews" / "phi41_squad_v1_physical_trades.jsonl"
PROPOSALS = M001 / "reviews" / "phi41_squad_v1_physical_proposals_all.jsonl"

WINDOW = timedelta(minutes=15)   # Phase AD locked knob (+/- around event)
BAR = timedelta(hours=4)
SYMBOLS = ("EURUSD", "GBPUSD", "USDCAD")  # all USD pairs -> every USD event relevant


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def load_events() -> list[datetime]:
    doc = json.loads(FIXTURE.read_text())
    assert doc["n_events"] == len(doc["events"])
    return sorted(_parse(e["time_utc"]) for e in doc["events"])


def gated_at(events: list[datetime], as_of: datetime) -> bool:
    """True iff any event window (event +/- 15 min) covers ``as_of``."""
    i = bisect.bisect_left(events, as_of - WINDOW)
    return i < len(events) and events[i] <= as_of + WINDOW


def gated_span(events: list[datetime], start: datetime, end: datetime) -> bool:
    """True iff any event window intersects [start, end]."""
    i = bisect.bisect_left(events, start - WINDOW)
    return i < len(events) and events[i] <= end + WINDOW


def outcomes(events: list[datetime], open_label: datetime) -> tuple[bool, bool, bool]:
    entry = open_label + BAR
    a = gated_at(events, open_label)
    b = gated_at(events, entry)
    c = gated_span(events, entry, entry + BAR)
    return a, b, c


def h4_grid(start: datetime, end: datetime):
    t = start
    while t <= end:
        if t.weekday() < 5:  # panel tape has no Sat/Sun bars
            yield t
        t += BAR


def main() -> None:
    events = load_events()

    # --- S1: full evaluation grid ---------------------------------
    props = [json.loads(l) for l in PROPOSALS.open()]
    lo = min(_parse(p["timestamp"]) for p in props)
    hi = max(_parse(p["timestamp"]) for p in props)

    n_points = 0
    s1_ab = s1_ac = 0
    fires = {"A": 0, "B": 0, "C": 0}
    for label in h4_grid(lo, hi):
        a, b, c = outcomes(events, label)
        n_points += len(SYMBOLS)
        fires["A"] += a * len(SYMBOLS)
        fires["B"] += b * len(SYMBOLS)
        fires["C"] += c * len(SYMBOLS)
        s1_ab += (a != b) * len(SYMBOLS)
        s1_ac += (a != c) * len(SYMBOLS)

    # --- S2: actually-admitted trades ------------------------------
    trades = [json.loads(l) for l in TRADES.open()]
    s2_flips_ab = []
    s2_flips_ac = []
    for t in trades:
        entry = _parse(t["entry_time"])
        a, b, c = outcomes(events, entry - BAR)
        if a != b:
            s2_flips_ab.append({"symbol": t["symbol"], "agent": t["agent_id"],
                                "entry_time": t["entry_time"], "A": a, "B": b,
                                "pnl_pips": t["pnl_pips"]})
        if a != c:
            s2_flips_ac.append({"symbol": t["symbol"], "agent": t["agent_id"],
                                "entry_time": t["entry_time"], "A": a, "C": c,
                                "pnl_pips": t["pnl_pips"]})

    s1_rate = s1_ab / n_points
    gate_opens = not (s1_rate < 0.01 and len(s2_flips_ab) == 0)

    results = {
        "phase": "AD.2 Stage 1",
        "run_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "fixture": FIXTURE.name,
        "n_events": len(events),
        "panel_window": [lo.isoformat(), hi.isoformat()],
        "n_evaluation_points": n_points,
        "fires": fires,
        "S1_disagreement_A_vs_B": {"count": s1_ab, "rate": s1_rate},
        "S1_audit_A_vs_C": {"count": s1_ac, "rate": s1_ac / n_points},
        "n_admitted_trades": len(trades),
        "S2_flipped_admissions_A_vs_B": {"count": len(s2_flips_ab),
                                         "flips": s2_flips_ab},
        "S2_audit_flips_A_vs_C": {"count": len(s2_flips_ac),
                                  "flips": s2_flips_ac[:50],
                                  "truncated": len(s2_flips_ac) > 50},
        "gate_rule": "Stage 2 opens iff S1 >= 1% OR S2 > 0 (locked, PROTOCOL sec 2)",
        "stage2_gate_opens": gate_opens,
    }
    out = HERE / "results_stage1.json"
    out.write_text(json.dumps(results, indent=2) + "\n")

    print(f"events={len(events)}  points={n_points}  "
          f"fires A/B/C = {fires['A']}/{fires['B']}/{fires['C']}")
    print(f"S1 (A vs B): {s1_ab} ({s1_rate:.4%})   [audit A vs C: {s1_ac}]")
    print(f"S2 flips on {len(trades)} admitted trades: "
          f"A-vs-B={len(s2_flips_ab)}  [A-vs-C={len(s2_flips_ac)}]")
    print(f"STAGE 2 GATE {'OPENS' if gate_opens else 'CLOSED -> NULL verdict'}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
