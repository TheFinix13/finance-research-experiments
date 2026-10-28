"""SPEC §4 invariant tests for the PRE-0 replay engine.

Each test corresponds to one of the pre-registered invariants:

- §4.1 null-rule reproduces the base trade exactly
- §4.2 stop-authority monotonicity (rules may only tighten)
- §4.3 exit-priority ordering
- §4.4 no look-ahead
- §4.5 determinism

Also covers the exporter's SPEC §1 MFE/MAE recovery on a synthetic
hand-computed path.
"""
from __future__ import annotations

import copy
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[3]))  # repo root

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    Bar,
    ExitAction,
    Fill,
    PIP,
    PRIORITY_E020_RATCHET,
    PRIORITY_E021_PARTIAL,
    PRIORITY_E024_STALL,
    PRIORITY_HARD_SL,
    PRIORITY_TP,
    TradeRecord,
    TradeState,
    _tighten,
    load_paths_ledger,
    replay,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers to build a synthetic TradeRecord (no dependency on the exporter).
# ---------------------------------------------------------------------------

def _bars(prices: list[tuple[float, float, float, float]], start_hour: int = 8) -> list[Bar]:
    """Build a list of Bars at 5-minute cadence from (o, h, l, c) tuples."""
    from datetime import timedelta
    t0 = datetime(2020, 1, 1, start_hour, 0, tzinfo=UTC)
    return [
        Bar(
            time=t0 + timedelta(minutes=5 * i),
            open=o, high=h, low=l, close=c,
        )
        for i, (o, h, l, c) in enumerate(prices)
    ]


def _synthetic_trade(
    direction: str = "long",
    entry: float = 1.1000,
    stop_pips: float = 20.0,
    tp_r: float = 1.5,
    path_prices: list[tuple[float, float, float, float]] | None = None,
    exit_time: datetime | None = None,
    exit_price: float | None = None,
    exit_reason: str = "tp",
    pnl_pips: float | None = None,
) -> TradeRecord:
    d = +1 if direction == "long" else -1
    soft_stop = entry - d * stop_pips * PIP
    take_profit = entry + d * tp_r * stop_pips * PIP
    tp_pips = tp_r * stop_pips

    if path_prices is None:
        # Trivial: entry bar with a small favorable move.
        path_prices = [(entry, entry + d * 5 * PIP, entry - d * 2 * PIP, entry + d * 3 * PIP)]

    path = _bars(path_prices)

    if exit_time is None:
        exit_time = path[-1].time
    if exit_price is None:
        exit_price = take_profit if exit_reason == "tp" else soft_stop
    if pnl_pips is None:
        pnl_pips = d * (exit_price - entry) / PIP

    r = pnl_pips / stop_pips if stop_pips > 0 else 0.0

    # Compute mfe/mae/mfe_ts/mae_ts from the path for the base ledger.
    mfe_pips = 0.0
    mae_pips = 0.0
    mfe_ts = path[0].time
    mae_ts = path[0].time
    for b in path:
        fav = (b.high - entry) / PIP if d == +1 else (entry - b.low) / PIP
        adv = (entry - b.low) / PIP if d == +1 else (b.high - entry) / PIP
        if fav > mfe_pips:
            mfe_pips, mfe_ts = fav, b.time
        if adv > mae_pips:
            mae_pips, mae_ts = adv, b.time

    return TradeRecord(
        trade_id="SYN_H4_00000",
        symbol="EURUSD",
        tf="H4",
        direction=direction,
        entry_time=path[0].time,
        entry=entry,
        stop=soft_stop,
        soft_stop=soft_stop,
        take_profit=take_profit,
        stop_pips=stop_pips,
        tp_pips=tp_pips,
        r=r,
        pnl_pips=pnl_pips,
        exit_time=exit_time,
        exit_price=exit_price,
        exit_reason=exit_reason,
        mfe_pips=mfe_pips,
        mae_pips=mae_pips,
        mfe_ts=mfe_ts,
        mae_ts=mae_ts,
        mfe_r=mfe_pips / stop_pips,
        mae_r=mae_pips / stop_pips,
        path=path,
        path_resolution="M5",
    )


# ---------------------------------------------------------------------------
# §4.1 — null-rule invariant.
# ---------------------------------------------------------------------------

def test_null_rule_reproduces_original_tp_exit() -> None:
    trade = _synthetic_trade(
        path_prices=[
            (1.1000, 1.1005, 1.0998, 1.1003),   # bar 0: small fav
            (1.1003, 1.1035, 1.1003, 1.1033),   # bar 1: TP-adjacent
        ],
        exit_reason="tp",
    )
    alt = replay(trade, rule=None)
    assert alt.exit_time == trade.exit_time
    assert alt.exit_price == trade.exit_price
    assert alt.exit_reason == trade.exit_reason
    assert alt.pnl_pips == trade.pnl_pips
    assert alt.r == trade.r
    assert alt.fills == []


def test_null_rule_reproduces_sl_exit() -> None:
    trade = _synthetic_trade(exit_reason="sl_close")
    alt = replay(trade, rule=None)
    assert alt.exit_reason == "sl_close"
    assert alt.pnl_pips == trade.pnl_pips


# ---------------------------------------------------------------------------
# §4.2 — stop authority monotonicity.
# ---------------------------------------------------------------------------

def test_tighten_helper_long() -> None:
    # Long: only larger stop values are allowed to replace.
    new, tightened = _tighten(current_stop=1.1000, proposed_stop=1.1010, direction=+1)
    assert (new, tightened) == (1.1010, True)
    new, tightened = _tighten(current_stop=1.1010, proposed_stop=1.1000, direction=+1)
    assert (new, tightened) == (1.1010, False)


def test_tighten_helper_short() -> None:
    # Short: only smaller stop values are allowed to replace.
    new, tightened = _tighten(current_stop=1.1050, proposed_stop=1.1030, direction=-1)
    assert (new, tightened) == (1.1030, True)
    new, tightened = _tighten(current_stop=1.1030, proposed_stop=1.1050, direction=-1)
    assert (new, tightened) == (1.1030, False)


def test_rule_cannot_loosen_stop() -> None:
    """A rule that requests adjust_stop with a looser price is ignored;
    the trade must still exit at the tighter existing stop when price
    reaches it."""
    trade = _synthetic_trade(
        direction="long",
        entry=1.1000,
        stop_pips=20.0,
        path_prices=[
            (1.1000, 1.1015, 1.0995, 1.1010),   # bar 0: MFE 15 pips
            (1.1010, 1.1015, 1.0970, 1.0975),   # bar 1: low 1.0970 crosses SL 1.0980
        ],
        exit_time=datetime(2020, 1, 1, 8, 5, tzinfo=UTC),
        exit_price=1.0980,
        exit_reason="sl",
        pnl_pips=-20.0,
    )

    def bad_rule(state: TradeState, bar: Bar) -> ExitAction | None:
        # Try to move stop DOWN (looser for a long) — must be dropped.
        return ExitAction(kind="adjust_stop", price=state.current_stop - 5 * PIP,
                          reason=PRIORITY_E020_RATCHET)

    alt = replay(trade, rule=bad_rule)
    # SL must still fire at the original 1.0980, not the "loosened" 1.0975 level.
    assert alt.exit_reason.startswith("sl"), f"expected sl exit, got {alt.exit_reason}"
    assert abs(alt.exit_price - 1.0980) < 1e-9, f"expected sl at 1.0980, got {alt.exit_price}"


# ---------------------------------------------------------------------------
# §4.3 — exit priority ordering.
# ---------------------------------------------------------------------------

def test_sl_beats_tp_when_both_fire_same_bar() -> None:
    """SPEC §4.3: hard_SL beats broker_TP on the same bar."""
    trade = _synthetic_trade(
        direction="long",
        entry=1.1000, stop_pips=20.0,
        path_prices=[
            # Bar 0 spans both SL (1.0980) and TP (1.1030) intra-bar.
            (1.1000, 1.1035, 1.0975, 1.1000),
        ],
    )
    alt = replay(trade, rule=lambda s, b: None)
    # Priority says SL wins even though the bar also touched TP.
    assert alt.exit_reason.startswith("sl")


def test_e024_stall_beats_tp_same_bar() -> None:
    """E024 stall exit beats broker TP if both fire the same bar."""
    trade = _synthetic_trade(
        direction="long",
        entry=1.1000, stop_pips=20.0,
        path_prices=[
            (1.1000, 1.1035, 1.0998, 1.1030),   # TP touched
        ],
    )
    def stall_rule(state, bar):
        # Force-close at bar 0 at entry+15 pips (stall exit price).
        return ExitAction(
            kind="close_at",
            price=state.entry + 15 * PIP,
            reason=PRIORITY_E024_STALL,
        )
    alt = replay(trade, rule=stall_rule)
    assert alt.exit_reason == PRIORITY_E024_STALL
    assert abs(alt.exit_price - 1.1015) < 1e-9


# ---------------------------------------------------------------------------
# §4.4 — no look-ahead (mutation test).
# ---------------------------------------------------------------------------

def test_no_lookahead() -> None:
    """A rule's decision on bar i must not depend on bars > i. Verified
    by mutating bar i+1's high and confirming bar i's rule call sees the
    unchanged state (mfe as of bar i only)."""
    trade = _synthetic_trade(
        direction="long",
        entry=1.1000, stop_pips=20.0,
        path_prices=[
            (1.1000, 1.1010, 1.0995, 1.1005),
            (1.1005, 1.1020, 1.1000, 1.1015),
            (1.1015, 1.1030, 1.1010, 1.1025),
        ],
    )
    seen: list[float] = []
    def recording_rule(state, bar):
        seen.append(state.mfe_pips_so_far)
        return None

    replay(trade, rule=recording_rule)
    seen_a = list(seen)
    seen.clear()

    # Mutate bar 2's high — should not change bar 0's or bar 1's state.
    mutated = copy.deepcopy(trade)
    mutated.path[2] = Bar(
        time=mutated.path[2].time,
        open=mutated.path[2].open,
        high=1.1500,   # radically different
        low=mutated.path[2].low,
        close=mutated.path[2].close,
    )
    replay(mutated, rule=recording_rule)
    seen_b = list(seen)

    assert seen_a[:2] == seen_b[:2], (
        f"look-ahead detected: bar[0..1] mfe changed after mutating bar 2 "
        f"({seen_a[:2]} vs {seen_b[:2]})"
    )


# ---------------------------------------------------------------------------
# §4.5 — determinism.
# ---------------------------------------------------------------------------

def test_determinism_repeatable_runs() -> None:
    trade = _synthetic_trade(direction="short", entry=1.3000, stop_pips=30.0)
    def r(state, bar):
        if state.mfe_r_so_far >= 0.5:
            return ExitAction(kind="adjust_stop",
                              price=state.entry - state.direction * 5 * PIP,
                              reason=PRIORITY_E020_RATCHET)
        return None
    a = replay(trade, rule=r)
    b = replay(trade, rule=r)
    assert (a.exit_time, a.exit_price, a.exit_reason, a.pnl_pips, a.r) == (
        b.exit_time, b.exit_price, b.exit_reason, b.pnl_pips, b.r
    )


# ---------------------------------------------------------------------------
# §1 — MFE/MAE recovery on hand-computed path.
# ---------------------------------------------------------------------------

def test_mfe_mae_recovery_long() -> None:
    """Hand-computed MFE/MAE on a synthetic long. Entry 1.1000, stop
    1.0980 (20 pips). Path:
      bar0: h=1.1010 l=1.0995 → MFE=10, MAE=5
      bar1: h=1.1025 l=1.0990 → MFE=25, MAE=10 (bar0 MAE was 5)
      bar2: h=1.1020 l=1.0985 → MFE=25 (unchanged), MAE=15
    Earliest-bar-wins: mfe_ts = bar1, mae_ts = bar2.
    """
    trade = _synthetic_trade(
        direction="long",
        entry=1.1000, stop_pips=20.0,
        path_prices=[
            (1.1000, 1.1010, 1.0995, 1.1005),
            (1.1005, 1.1025, 1.0990, 1.1020),
            (1.1020, 1.1020, 1.0985, 1.1000),
        ],
        exit_reason="path_end",
        exit_price=1.1000,
        pnl_pips=0.0,
    )
    def track(state, bar):
        return None
    alt = replay(trade, rule=track)
    assert abs(alt.mfe_pips_at_exit - 25.0) < 0.01
    assert abs(alt.mae_pips_at_exit - 15.0) < 0.01


def test_mfe_mae_recovery_short() -> None:
    """Mirror of the long test, short direction."""
    trade = _synthetic_trade(
        direction="short",
        entry=1.3000, stop_pips=20.0,
        path_prices=[
            (1.3000, 1.3005, 1.2990, 1.2995),   # fav=10 (low crossed 1.2990), adv=5 (high 1.3005)
            (1.2995, 1.3010, 1.2975, 1.2980),   # fav=25 (1.2975), adv=10 (1.3010)
            (1.2980, 1.3015, 1.2985, 1.3000),   # fav=25 unchanged, adv=15 (1.3015)
        ],
        exit_reason="path_end",
        exit_price=1.3000,
        pnl_pips=0.0,
    )
    def track(state, bar):
        return None
    alt = replay(trade, rule=track)
    assert abs(alt.mfe_pips_at_exit - 25.0) < 0.01
    assert abs(alt.mae_pips_at_exit - 15.0) < 0.01


# ---------------------------------------------------------------------------
# Real-ledger sanity: null-rule over PRE-0 EURUSD ledger reproduces the
# base ledger's pnl_pips exactly for every trade.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("symbol", ["EURUSD", "GBPUSD", "USDCAD"])
def test_null_rule_reproduces_base_ledger(symbol: str) -> None:
    """The null-rule fast path must byte-for-byte reproduce the base
    ledger's exit fields across the full production population."""
    try:
        meta, trades = load_paths_ledger(symbol)
    except FileNotFoundError:
        pytest.skip(f"{symbol} PRE-0 ledger not generated (run exporter first)")

    assert len(trades) > 0
    for t in trades:
        alt = replay(t, rule=None)
        assert alt.exit_time == t.exit_time, t.trade_id
        assert alt.exit_price == t.exit_price, t.trade_id
        assert alt.exit_reason == t.exit_reason, t.trade_id
        assert abs(alt.pnl_pips - t.pnl_pips) < 1e-9, t.trade_id
        assert abs(alt.r - t.r) < 1e-9, t.trade_id
