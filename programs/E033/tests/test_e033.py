"""E033 unit tests — window membership, flatten / BE repricing, Stage-0 floor."""
from __future__ import annotations

from datetime import datetime, timezone

from programs._shared.counterfactual_replay.replay import Bar, TradeRecord
from programs.E033.blackout import (
    FAMILY_A,
    FAMILY_B,
    Event,
    entry_in_window,
    family_b_repriced,
    h4_open_at_or_after,
)


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _trade(**over) -> TradeRecord:
    entry = over.pop("entry_time", _ts("2026-08-07T08:00:00"))
    exit_t = over.pop("exit_time", _ts("2026-08-07T16:00:00"))
    path = over.pop("path", [
        Bar(time=_ts("2026-08-07T08:00:00"), open=1.1000, high=1.1010,
            low=1.0990, close=1.1005),
        Bar(time=_ts("2026-08-07T12:00:00"), open=1.1005, high=1.1020,
            low=1.0995, close=1.1010),
        Bar(time=_ts("2026-08-07T16:00:00"), open=1.1010, high=1.1030,
            low=1.0980, close=1.0985),
    ])
    kwargs = dict(
        trade_id="t1", symbol="EURUSD", tf="H4", direction="short",
        entry_time=entry, entry=1.1000, stop=1.1030, soft_stop=1.1030,
        take_profit=1.0955, stop_pips=30.0, tp_pips=45.0, r=-1.0,
        pnl_pips=-30.0, exit_time=exit_t, exit_price=1.1030,
        exit_reason="sl", mfe_pips=10.0, mae_pips=30.0,
        mfe_ts=entry, mae_ts=exit_t, mfe_r=0.33, mae_r=1.0,
        path=path, path_resolution="H4",
    )
    kwargs.update(over)
    return TradeRecord(**kwargs)


NFP = Event(time=_ts("2026-08-07T13:30:00"), title="NFP", currency="USD")


def test_h4_open_at_or_after_snaps_forward():
    assert h4_open_at_or_after(_ts("2026-08-07T09:30:00")) == _ts("2026-08-07T12:00:00")
    assert h4_open_at_or_after(_ts("2026-08-07T12:00:00")) == _ts("2026-08-07T12:00:00")


def test_family_a_30_30_hits_nfp_bar_fill():
    arm = FAMILY_A[0]  # 30/30
    assert entry_in_window(_ts("2026-08-07T13:15:00"), [NFP], arm) is True
    assert entry_in_window(_ts("2026-08-07T12:00:00"), [NFP], arm) is False


def test_family_a_event_day_hits_whole_utc_day():
    arm = FAMILY_A[-1]
    assert entry_in_window(_ts("2026-08-07T00:05:00"), [NFP], arm) is True
    assert entry_in_window(_ts("2026-08-08T00:05:00"), [NFP], arm) is False


def test_flatten_closes_at_h4_open_before_nfp():
    # 4h pre = 09:30 → first H4 open 12:00. Short entered 08:00 @ 1.1000,
    # 12:00 open 1.1005 → small loss.
    alt_r, touched, reason = family_b_repriced(_trade(), [NFP], FAMILY_B[0])
    assert touched is True and reason == "flatten"
    # (1.1000 - 1.1005) / 0.0001 = -5 pips / 30 = -0.166...
    assert abs(alt_r - (-5.0 / 30.0)) < 1e-9


def test_be_not_in_profit_leaves_original():
    # Short, 12:00 open 1.1005 > entry 1.1000 → not in profit.
    alt_r, touched, reason = family_b_repriced(_trade(r=-1.0), [NFP], FAMILY_B[2])
    assert touched is True
    assert reason == "be_not_in_profit"
    assert alt_r == -1.0


def test_be_in_profit_exits_at_entry_on_touch():
    # Short entered 08:00 @ 1.1020; 12:00 open 1.1005 (in profit); 16:00
    # high 1.1030 tags entry → BE exit, r=0.
    trade = _trade(
        entry=1.1020, stop=1.1050, stop_pips=30.0, r=-1.0,
        path=[
            Bar(time=_ts("2026-08-07T08:00:00"), open=1.1020, high=1.1025,
                low=1.1010, close=1.1015),
            Bar(time=_ts("2026-08-07T12:00:00"), open=1.1005, high=1.1010,
                low=1.0995, close=1.1000),
            Bar(time=_ts("2026-08-07T16:00:00"), open=1.1000, high=1.1030,
                low=1.0980, close=1.1025),
        ],
    )
    alt_r, touched, reason = family_b_repriced(trade, [NFP], FAMILY_B[2])
    assert touched is True and reason == "be_touched"
    assert alt_r == 0.0


def test_already_closed_before_window_is_untouched():
    trade = _trade(exit_time=_ts("2026-08-07T08:00:00"))
    alt_r, touched, reason = family_b_repriced(trade, [NFP], FAMILY_B[0])
    assert touched is False and reason == "untouched"
    assert alt_r == trade.r
