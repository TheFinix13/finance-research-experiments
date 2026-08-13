"""Phase AO -- v1 tape review ("big brother review").

Joins v1's live journal (trade_entry/trade_exit day jsonl files) against
the squad's live-shadow tape (proposals_all / proposals_rejected /
trades jsonl) for the same window and writes a corrections ledger:
per v1 trade, what the squad would have done differently and whether
that would actually have helped.

Observation only -- reads two tapes, writes documents. No live
coupling, no statistical claims (descriptive counts and paired deltas;
weekly n is tiny by construction). See PROTOCOL.md in this directory.

Stdlib-only by design so it runs anywhere the tapes can be copied
(including straight off the VM over Tailscale).

Usage:
    python tape_review.py --v1-journal <dir> --squad-live <dir> \
        --start 2026-08-01 --end 2026-08-10 --out results/2026-08-01_to_2026-08-10
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

MATCH_WINDOW_BARS_DEFAULT = 1
H4_SECONDS = 4 * 3600


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_ts(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        ts = value
    else:
        try:
            ts = datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def h4_bar_index(ts: datetime) -> int:
    """Index of the H4 bar (UTC grid 00/04/08/12/16/20) containing ts."""
    return int(ts.timestamp() // H4_SECONDS)


def _bars_apart(a: datetime | None, b: datetime | None) -> int | None:
    if a is None or b is None:
        return None
    return abs(h4_bar_index(a) - h4_bar_index(b))


# ---------------------------------------------------------------------------
# v1 side: live journal day files
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_v1_trades(journal_dir: Path, *, start: str, end: str) -> list[dict]:
    """Closed v1 trades in [start, end] (YYYY-MM-DD, inclusive) from the
    live-journal day files. Entry and exit events are joined by ticket;
    the entry's ``ts`` (write time ~= fill time in live operation) is
    the trade's entry timestamp."""
    entries: dict[str, dict] = {}
    trades: list[dict] = []
    for day_file in sorted(journal_dir.glob("*.jsonl")):
        day = day_file.stem
        if not (start <= day <= end):
            # Entries can precede the window while the exit is inside it;
            # read a little wider on the entry side only.
            if not (day < start):
                continue
        for row in _read_jsonl(day_file):
            event = row.get("event")
            ticket = str(row.get("ticket", ""))
            if event == "trade_entry" and ticket:
                entries[ticket] = row
            elif event == "trade_exit" and ticket:
                exit_day = str(row.get("ts", ""))[:10]
                if not (start <= exit_day <= end):
                    continue
                entry = entries.get(ticket, {})
                entry_ts = _parse_ts(entry.get("ts"))
                exit_ts = _parse_ts(row.get("ts"))
                hold_hours = (
                    round((exit_ts - entry_ts).total_seconds() / 3600.0, 2)
                    if entry_ts and exit_ts else None
                )
                trades.append({
                    "ticket": ticket,
                    "symbol": entry.get("symbol"),
                    "direction": entry.get("direction"),
                    "entry_ts": entry_ts.isoformat() if entry_ts else None,
                    "exit_ts": exit_ts.isoformat() if exit_ts else None,
                    "hold_hours": hold_hours,
                    "entry": entry.get("entry"),
                    "stop": entry.get("stop"),
                    "take_profit": entry.get("take_profit"),
                    "lot": entry.get("lot"),
                    "conviction": row.get("conviction",
                                          entry.get("conviction")),
                    "r_multiple": float(row.get("r_multiple", 0.0) or 0.0),
                    "pnl_pips": row.get("pnl_pips"),
                    "exit_reason": row.get("exit_reason"),
                    "mae_r": row.get("mae_r"),
                    "mfe_r": row.get("mfe_r"),
                    "gave_back_r": row.get("gave_back_r"),
                    "attribution": row.get("attribution"),
                })
    return trades


# ---------------------------------------------------------------------------
# Squad side: live-shadow tape
# ---------------------------------------------------------------------------

def load_squad_tape(live_dir: Path) -> dict:
    return {
        "proposals": _read_jsonl(live_dir / "proposals_all.jsonl"),
        "rejections": _read_jsonl(live_dir / "proposals_rejected.jsonl"),
        "trades": _read_jsonl(live_dir / "trades.jsonl"),
    }


def _tape_gap(tape: dict) -> bool:
    return not any(tape.values())


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

def _match(rows: list[dict], *, symbol: str, entry_ts: datetime,
           window_bars: int, ts_key: str = "timestamp") -> list[dict]:
    out = []
    for row in rows:
        if str(row.get("symbol", "")).upper() != symbol.upper():
            continue
        apart = _bars_apart(_parse_ts(row.get(ts_key)), entry_ts)
        if apart is not None and apart <= window_bars:
            out.append(row)
    return out


def _win_review(v1: dict) -> dict:
    """Efficiency lens on the v1 trade itself (wins especially)."""
    r = float(v1.get("r_multiple") or 0.0)
    mfe_r = v1.get("mfe_r")
    capture = (round(r / float(mfe_r), 2)
               if mfe_r and float(mfe_r) > 0 and r > 0 else None)
    return {
        "hold_hours": v1.get("hold_hours"),
        "mfe_capture": capture,
        "gave_back_r": v1.get("gave_back_r"),
        "mae_r": v1.get("mae_r"),
    }


def review_trade(v1: dict, tape: dict, *,
                 window_bars: int = MATCH_WINDOW_BARS_DEFAULT) -> dict:
    """One corrections-ledger row for one closed v1 trade."""
    row: dict = {
        "ticket": v1["ticket"],
        "symbol": v1["symbol"],
        "v1_direction": v1["direction"],
        "v1_entry_ts": v1["entry_ts"],
        "v1_r": float(v1.get("r_multiple") or 0.0),
        "v1_exit_reason": v1.get("exit_reason"),
        "v1_conviction": v1.get("conviction"),
        "v1_lot": v1.get("lot"),
        "v1_attribution": v1.get("attribution"),
        "efficiency": _win_review(v1),
    }
    if _tape_gap(tape):
        row.update({"verdict": "tape_gap", "advice_delta_r": None,
                    "note": "squad tape missing/empty for this window -- "
                            "excluded from advice totals, never guessed"})
        return row
    entry_ts = _parse_ts(v1.get("entry_ts"))
    symbol = str(v1.get("symbol") or "")
    if entry_ts is None or not symbol:
        row.update({"verdict": "tape_gap", "advice_delta_r": None,
                    "note": "v1 record lacks entry timestamp/symbol"})
        return row

    v1_dir = str(v1.get("direction") or "").lower()
    v1_r = row["v1_r"]

    proposals = _match(tape["proposals"], symbol=symbol, entry_ts=entry_ts,
                       window_bars=window_bars)
    same = [p for p in proposals
            if str(p.get("direction", "")).lower() == v1_dir]
    opposite = [p for p in proposals
                if str(p.get("direction", "")).lower() not in ("", v1_dir)]
    fills = _match(tape["trades"], symbol=symbol, entry_ts=entry_ts,
                   window_bars=window_bars, ts_key="entry_time")
    same_fills = [t for t in fills
                  if str(t.get("direction", "")).lower() == v1_dir]
    opp_fills = [t for t in fills
                 if str(t.get("direction", "")).lower() not in ("", v1_dir)]
    blocks = _match(tape["rejections"], symbol=symbol, entry_ts=entry_ts,
                    window_bars=window_bars)
    same_blocks = [
        b for b in blocks
        if str(b.get("loser_direction", b.get("winner_direction", "")))
        .lower() == v1_dir
    ]

    if same_fills:
        squad = max(same_fills,
                    key=lambda t: float(t.get("r_multiple", 0.0) or 0.0))
        squad_r = float(squad.get("r_multiple", 0.0) or 0.0)
        delta = round(squad_r - v1_r, 2)
        row.update({
            "verdict": "agreed_and_filled",
            "squad_agent": squad.get("agent_id"),
            "squad_r": squad_r,
            "squad_exit_reason": squad.get("exit_reason"),
            "advice_delta_r": delta,
            "note": (
                f"{squad.get('agent_id', '?')} took the same {v1_dir} and "
                f"closed {squad_r:+.2f}R vs v1 {v1_r:+.2f}R "
                f"({'squad managed it better' if delta > 0 else 'v1 managed it as well or better'})"
            ),
        })
    elif same_blocks:
        blk = same_blocks[0]
        reason = str(blk.get("sentinel_reason")
                     or blk.get("rejection_reason") or "?")
        delta = round(-v1_r, 2)
        helped = v1_r < 0
        row.update({
            "verdict": "agreed_blocked",
            "squad_agent": blk.get("loser_agent_id"),
            "block_reason": reason,
            "advice_delta_r": delta,
            "note": (
                f"a squad {v1_dir} existed but was tackled ({reason}); "
                + (f"skipping would have saved {-v1_r:+.2f}R"
                   if helped else
                   f"listening would have FORFEITED this {v1_r:+.2f}R win "
                   "-- the wall has a price")
            ),
        })
    elif same:
        row.update({
            "verdict": "agreed_unfilled",
            "squad_agent": same[0].get("agent_id"),
            "advice_delta_r": 0.0,
            "note": "same-direction proposal existed but no fill and no "
                    "recorded block (lost aggregation / slot) -- no advice "
                    "on tape",
        })
    elif opposite or opp_fills:
        if opp_fills:
            squad = max(opp_fills,
                        key=lambda t: float(t.get("r_multiple", 0.0) or 0.0))
            squad_r = float(squad.get("r_multiple", 0.0) or 0.0)
            delta = round(squad_r - v1_r, 2)
            note = (f"squad went the OTHER way and closed {squad_r:+.2f}R "
                    f"vs v1 {v1_r:+.2f}R")
        else:
            squad_r = None
            delta = round(-v1_r, 2)
            note = (f"squad proposed the OTHER way (unfilled); at minimum "
                    f"it disagreed with this entry")
        row.update({
            "verdict": "opposed",
            "squad_agent": (opp_fills or opposite)[0].get("agent_id"),
            "squad_r": squad_r,
            "advice_delta_r": delta,
            "note": note,
        })
    else:
        row.update({
            "verdict": "no_opinion",
            "advice_delta_r": 0.0,
            "note": "no squad proposal on this symbol in window -- big "
                    "brother saw nothing here (explicitly NOT evidence "
                    "against the trade)",
        })
    return row


def build_ledger(v1_trades: list[dict], tape: dict, *,
                 window_bars: int = MATCH_WINDOW_BARS_DEFAULT) -> dict:
    rows = [review_trade(t, tape, window_bars=window_bars)
            for t in sorted(v1_trades, key=lambda t: t.get("entry_ts") or "")]
    counts: dict[str, int] = {}
    saved = 0.0     # advice that would have improved a LOSS
    forfeited = 0.0  # advice that would have cost a WIN
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        d = r.get("advice_delta_r")
        if d is None or r["verdict"] in ("no_opinion", "agreed_unfilled",
                                         "tape_gap"):
            continue
        if d > 0:
            saved += d
        elif d < 0:
            forfeited += -d
    summary = {
        "trades_reviewed": len(rows),
        "verdict_counts": counts,
        "advice_r_saved": round(saved, 2),
        "advice_r_forfeited": round(forfeited, 2),
        "advice_r_net": round(saved - forfeited, 2),
    }
    return {"rows": rows, "summary": summary}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_md(ledger: dict, *, window_label: str, mode_label: str) -> str:
    s = ledger["summary"]
    out = [
        f"# Corrections ledger -- v1 tape review, {window_label}",
        "",
        f"Counterfactual source: {mode_label}. Observation only; "
        "descriptive counts, no statistical claims (Phase AO PROTOCOL "
        "doctrine). Skipped-trade deltas assume flat instead of v1's "
        "fill; they are advice VALUE, not tradable expectancy.",
        "",
        f"- Trades reviewed: **{s['trades_reviewed']}**",
        f"- Verdicts: " + (", ".join(
            f"{k}={v}" for k, v in sorted(s["verdict_counts"].items()))
            or "none"),
        f"- Advice R saved (losses the squad's tape argued against): "
        f"**{s['advice_r_saved']:+.2f}R**",
        f"- Advice R forfeited (wins it argued against): "
        f"**{s['advice_r_forfeited']:+.2f}R**",
        f"- **NET advice value: {s['advice_r_net']:+.2f}R** -- the honest "
        "headline; a positive number means big brother's week genuinely "
        "graded better on THIS tape.",
        "",
        "| Ticket | Sym | Dir | v1 R | Verdict | Delta R | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in ledger["rows"]:
        d = r.get("advice_delta_r")
        out.append(
            f"| {r['ticket']} | {r['symbol']} | {r['v1_direction']} "
            f"| {r['v1_r']:+.2f} | {r['verdict']} "
            f"| {('%+.2f' % d) if d is not None else 'n/a'} "
            f"| {r['note']} |"
        )
    out += ["", "## Efficiency lens (all v1 trades)", "",
            "| Ticket | Hold h | MFE capture | Gave back R | MAE R |",
            "|---|---|---|---|---|"]
    for r in ledger["rows"]:
        e = r["efficiency"]
        out.append(
            f"| {r['ticket']} | {e.get('hold_hours') if e.get('hold_hours') is not None else '?'} "
            f"| {e.get('mfe_capture') if e.get('mfe_capture') is not None else 'n/a'} "
            f"| {e.get('gave_back_r') if e.get('gave_back_r') is not None else 'n/a'} "
            f"| {e.get('mae_r') if e.get('mae_r') is not None else 'n/a'} |"
        )
    out += ["", "## Patterns worth a pre-reg", "",
            "(Filled by the human review; empty is an honest answer.)", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v1-journal", required=True, type=Path,
                    help="directory of v1 live-journal day jsonl files")
    ap.add_argument("--squad-live", required=True, type=Path,
                    help="squad live/replay tape dir (proposals_all.jsonl "
                         "/ proposals_rejected.jsonl / trades.jsonl)")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD inclusive")
    ap.add_argument("--match-window-bars", type=int,
                    default=MATCH_WINDOW_BARS_DEFAULT)
    ap.add_argument("--mode-label", default="M1 live-shadow tape",
                    help="recorded in the ledger header (M1 live tape / "
                         "M2 replay + config)")
    ap.add_argument("--out", required=True, type=Path,
                    help="output directory")
    args = ap.parse_args()

    v1_trades = load_v1_trades(args.v1_journal, start=args.start,
                               end=args.end)
    tape = load_squad_tape(args.squad_live)
    ledger = build_ledger(v1_trades, tape,
                          window_bars=args.match_window_bars)

    args.out.mkdir(parents=True, exist_ok=True)
    window_label = f"{args.start} to {args.end}"
    with (args.out / "corrections_ledger.jsonl").open(
            "w", encoding="utf-8") as fh:
        for row in ledger["rows"]:
            fh.write(json.dumps(row, default=str) + "\n")
    (args.out / "summary.json").write_text(
        json.dumps(ledger["summary"], indent=2), encoding="utf-8")
    (args.out / "REVIEW.md").write_text(
        render_md(ledger, window_label=window_label,
                  mode_label=args.mode_label),
        encoding="utf-8")
    print(json.dumps(ledger["summary"], indent=2))


if __name__ == "__main__":
    main()
