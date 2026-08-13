"""Unit tests for the Phase AO corrections-ledger harness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tape_review import (  # noqa: E402
    build_ledger,
    h4_bar_index,
    load_squad_tape,
    load_v1_trades,
    render_md,
    review_trade,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _v1_trade(**over) -> dict:
    base = {
        "ticket": "101",
        "symbol": "EURUSD",
        "direction": "sell",
        "entry_ts": "2026-08-07T13:15:00+00:00",
        "exit_ts": "2026-08-07T20:00:00+00:00",
        "hold_hours": 6.75,
        "r_multiple": -1.53,
        "exit_reason": "sl",
        "conviction": 0.65,
        "lot": 0.04,
        "mae_r": 1.0,
        "mfe_r": 0.2,
        "gave_back_r": None,
        "attribution": "bad_setup",
    }
    base.update(over)
    return base


def _tape(proposals=(), rejections=(), trades=()) -> dict:
    return {"proposals": list(proposals), "rejections": list(rejections),
            "trades": list(trades)}


# ---------------------------------------------------------------------------
# Journal loading
# ---------------------------------------------------------------------------

def test_load_v1_trades_joins_entry_and_exit_by_ticket(tmp_path):
    day = tmp_path / "2026-08-07.jsonl"
    _write_jsonl(day, [
        {"ts": "2026-08-07T13:15:00+00:00", "event": "trade_entry",
         "ticket": 101, "symbol": "EURUSD", "direction": "sell",
         "entry": 1.0930, "stop": 1.0960, "take_profit": 1.0860,
         "lot": 0.04, "conviction": 0.65},
        {"ts": "2026-08-07T20:00:00+00:00", "event": "trade_exit",
         "ticket": 101, "exit_price": 1.0960, "exit_reason": "sl",
         "pnl": -6.1, "pnl_pips": -30.0, "r_multiple": -1.0,
         "mae_pips": 31.0, "mfe_pips": 4.0, "mae_r": 1.03, "mfe_r": 0.13,
         "attribution": "bad_setup", "conviction": 0.65},
    ])
    trades = load_v1_trades(tmp_path, start="2026-08-01", end="2026-08-10")
    assert len(trades) == 1
    t = trades[0]
    assert t["symbol"] == "EURUSD" and t["direction"] == "sell"
    assert t["r_multiple"] == -1.0
    assert t["hold_hours"] == 6.75


def test_load_v1_trades_entry_before_window_still_joins(tmp_path):
    _write_jsonl(tmp_path / "2026-07-31.jsonl", [
        {"ts": "2026-07-31T09:00:00+00:00", "event": "trade_entry",
         "ticket": 7, "symbol": "GBPUSD", "direction": "buy",
         "entry": 1.28, "stop": 1.275, "take_profit": 1.29, "lot": 0.02,
         "conviction": 0.7},
    ])
    _write_jsonl(tmp_path / "2026-08-01.jsonl", [
        {"ts": "2026-08-01T09:00:00+00:00", "event": "trade_exit",
         "ticket": 7, "exit_price": 1.29, "exit_reason": "tp", "pnl": 20.0,
         "pnl_pips": 100.0, "r_multiple": 2.0, "mae_pips": 5.0,
         "mfe_pips": 100.0, "conviction": 0.7},
    ])
    trades = load_v1_trades(tmp_path, start="2026-08-01", end="2026-08-10")
    assert len(trades) == 1
    assert trades[0]["symbol"] == "GBPUSD"


def test_exit_outside_window_excluded(tmp_path):
    _write_jsonl(tmp_path / "2026-08-11.jsonl", [
        {"ts": "2026-08-11T09:00:00+00:00", "event": "trade_exit",
         "ticket": 9, "exit_price": 1.0, "exit_reason": "tp", "pnl": 1.0,
         "pnl_pips": 10.0, "r_multiple": 1.0},
    ])
    assert load_v1_trades(tmp_path, start="2026-08-01",
                          end="2026-08-10") == []


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def test_loss_with_same_direction_sentinel_block_is_agreed_blocked():
    tape = _tape(rejections=[{
        "symbol": "EURUSD", "timestamp": "2026-08-07T12:00:00+00:00",
        "loser_agent_id": "nagi", "loser_direction": "sell",
        "winner_direction": "sell",
        "rejection_reason": "sentinel_R1_block",
        "sentinel_reason": "min-lot risk floor",
    }])
    row = review_trade(_v1_trade(r_multiple=-1.53), tape)
    assert row["verdict"] == "agreed_blocked"
    assert row["advice_delta_r"] == 1.53
    assert "saved" in row["note"]


def test_win_with_same_direction_block_counts_as_forfeit():
    tape = _tape(rejections=[{
        "symbol": "EURUSD", "timestamp": "2026-08-07T12:00:00+00:00",
        "loser_agent_id": "nagi", "loser_direction": "sell",
        "rejection_reason": "sentinel_R1_block",
        "sentinel_reason": "min-lot risk floor",
    }])
    row = review_trade(_v1_trade(r_multiple=1.5, exit_reason="tp"), tape)
    assert row["verdict"] == "agreed_blocked"
    assert row["advice_delta_r"] == -1.5
    assert "FORFEITED" in row["note"]


def test_same_direction_fill_compares_outcomes():
    tape = _tape(trades=[{
        "symbol": "EURUSD", "direction": "sell", "agent_id": "bachira",
        "entry_time": "2026-08-07T12:00:00+00:00", "r_multiple": 1.5,
        "exit_reason": "tp",
    }])
    row = review_trade(_v1_trade(r_multiple=-1.53), tape)
    assert row["verdict"] == "agreed_and_filled"
    assert row["squad_r"] == 1.5
    assert row["advice_delta_r"] == 3.03


def test_opposite_proposal_without_fill_is_opposed():
    tape = _tape(proposals=[{
        "symbol": "EURUSD", "direction": "buy", "agent_id": "isagi",
        "timestamp": "2026-08-07T12:00:00+00:00", "conviction": 0.8,
    }])
    row = review_trade(_v1_trade(r_multiple=-1.0), tape)
    assert row["verdict"] == "opposed"
    assert row["advice_delta_r"] == 1.0


def test_no_activity_is_no_opinion_with_zero_delta():
    tape = _tape(proposals=[{
        "symbol": "USDCAD", "direction": "sell", "agent_id": "bachira",
        "timestamp": "2026-08-07T12:00:00+00:00",
    }])
    row = review_trade(_v1_trade(), tape)
    assert row["verdict"] == "no_opinion"
    assert row["advice_delta_r"] == 0.0


def test_out_of_window_proposal_does_not_match():
    tape = _tape(proposals=[{
        "symbol": "EURUSD", "direction": "sell", "agent_id": "nagi",
        "timestamp": "2026-08-08T12:00:00+00:00",
    }])
    row = review_trade(_v1_trade(), tape, window_bars=1)
    assert row["verdict"] == "no_opinion"


def test_empty_tape_marks_tape_gap():
    row = review_trade(_v1_trade(), _tape())
    assert row["verdict"] == "tape_gap"
    assert row["advice_delta_r"] is None


def test_h4_bar_index_groups_intra_bar_fill_with_bar_open():
    from datetime import datetime, timezone
    fill = datetime(2026, 8, 7, 13, 15, tzinfo=timezone.utc)
    bar_open = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    assert h4_bar_index(fill) == h4_bar_index(bar_open)


# ---------------------------------------------------------------------------
# Ledger aggregation and rendering
# ---------------------------------------------------------------------------

def test_summary_nets_saved_against_forfeited():
    tape = _tape(rejections=[
        {"symbol": "EURUSD", "timestamp": "2026-08-07T12:00:00+00:00",
         "loser_direction": "sell", "sentinel_reason": "R1"},
        {"symbol": "GBPUSD", "timestamp": "2026-08-05T12:00:00+00:00",
         "loser_direction": "buy", "sentinel_reason": "R1"},
    ])
    trades = [
        _v1_trade(ticket="1", r_multiple=-2.0),
        _v1_trade(ticket="2", symbol="GBPUSD", direction="buy",
                  entry_ts="2026-08-05T12:30:00+00:00", r_multiple=1.5,
                  exit_reason="tp"),
        _v1_trade(ticket="3", symbol="USDJPY",
                  entry_ts="2026-08-06T08:10:00+00:00", r_multiple=-1.0),
    ]
    ledger = build_ledger(trades, tape)
    s = ledger["summary"]
    assert s["trades_reviewed"] == 3
    assert s["advice_r_saved"] == 2.0
    assert s["advice_r_forfeited"] == 1.5
    assert s["advice_r_net"] == 0.5
    assert s["verdict_counts"]["no_opinion"] == 1


def test_render_md_contains_headline_and_rows():
    tape = _tape(rejections=[{
        "symbol": "EURUSD", "timestamp": "2026-08-07T12:00:00+00:00",
        "loser_direction": "sell", "sentinel_reason": "R1",
    }])
    ledger = build_ledger([_v1_trade(r_multiple=-1.53)], tape)
    md = render_md(ledger, window_label="2026-08-01 to 2026-08-10",
                   mode_label="M1 live-shadow tape")
    assert "NET advice value: +1.53R" in md
    assert "agreed_blocked" in md
    assert "Efficiency lens" in md


def test_win_efficiency_fields_present():
    row = review_trade(
        _v1_trade(r_multiple=1.0, mfe_r=2.0, gave_back_r=1.0,
                  exit_reason="tp"),
        _tape(proposals=[{"symbol": "USDCAD", "direction": "sell",
                          "timestamp": "2026-08-07T12:00:00+00:00"}]),
    )
    eff = row["efficiency"]
    assert eff["mfe_capture"] == 0.5
    assert eff["gave_back_r"] == 1.0
    assert eff["hold_hours"] == 6.75


def test_load_squad_tape_reads_three_files(tmp_path):
    _write_jsonl(tmp_path / "proposals_all.jsonl", [{"a": 1}])
    _write_jsonl(tmp_path / "proposals_rejected.jsonl", [{"b": 2}])
    _write_jsonl(tmp_path / "trades.jsonl", [{"c": 3}])
    tape = load_squad_tape(tmp_path)
    assert (len(tape["proposals"]), len(tape["rejections"]),
            len(tape["trades"])) == (1, 1, 1)
