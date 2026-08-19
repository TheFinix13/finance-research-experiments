"""E033 deterministic blackout / de-risking operators.

Pure functions over the PRE-0 ``TradeRecord`` + the Phase AE frozen
calendar. No I/O, no scoring — scoring lives in ``run_e033_validation.py``.

Family A: entry-fill timestamp ∈ a window around any event → suppress.
Family B: position still open at ``T − pre`` → flatten at the next H4
open, or tighten the stop to entry if already in profit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

from programs._shared.counterfactual_replay.replay import Bar, TradeRecord

H4_SECONDS = 4 * 3600
PIP = 0.0001
STAGE0_FLOOR = 30  # PROTOCOL §5 — pooled touched trades per (arm, symbol)


@dataclass(frozen=True)
class Event:
    time: datetime
    title: str
    currency: str


@dataclass(frozen=True)
class ArmA:
    name: str
    pre_min: Optional[int]  # None → event_day
    post_min: Optional[int]


@dataclass(frozen=True)
class ArmB:
    name: str
    action: str  # "flatten" | "be"
    pre_hours: int


FAMILY_A: tuple[ArmA, ...] = (
    ArmA("A_30_30", 30, 30),
    ArmA("A_60_60", 60, 60),
    ArmA("A_120_60", 120, 60),
    ArmA("A_120_120", 120, 120),
    ArmA("A_240_120", 240, 120),
    ArmA("A_event_day", None, None),
)

FAMILY_B: tuple[ArmB, ...] = (
    ArmB("B_flatten_4h", "flatten", 4),
    ArmB("B_flatten_8h", "flatten", 8),
    ArmB("B_be_4h", "be", 4),
    ArmB("B_be_8h", "be", 8),
)


def parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        ts = value
    else:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def load_calendar(path: Path | str) -> list[Event]:
    raw = json.loads(Path(path).read_text())
    events = raw["events"] if isinstance(raw, dict) else raw
    out: list[Event] = []
    for row in events:
        out.append(Event(
            time=parse_ts(row["time_utc"]),
            title=str(row.get("title") or ""),
            currency=str(row.get("currency") or "USD"),
        ))
    out.sort(key=lambda e: e.time)
    return out


def h4_open_at_or_after(ts: datetime) -> datetime:
    """First UTC H4 grid open (00/04/08/12/16/20) at or after ``ts``."""
    epoch = ts.timestamp()
    slot = int(epoch // H4_SECONDS)
    on_grid = slot * H4_SECONDS
    if epoch > on_grid:
        on_grid += H4_SECONDS
    return datetime.fromtimestamp(on_grid, tz=timezone.utc)


def entry_in_window(entry: datetime, events: Sequence[Event], arm: ArmA) -> bool:
    if arm.pre_min is None:
        day = entry.date()
        return any(e.time.date() == day for e in events)
    pre = timedelta(minutes=arm.pre_min)
    post = timedelta(minutes=arm.post_min or 0)
    for e in events:
        if e.time - pre <= entry <= e.time + post:
            return True
    return False


def _r_from_exit(trade: TradeRecord, exit_price: float) -> float:
    if trade.stop_pips <= 0:
        return 0.0
    if trade.direction == "long":
        pnl_pips = (exit_price - trade.entry) / PIP
    else:
        pnl_pips = (trade.entry - exit_price) / PIP
    return pnl_pips / trade.stop_pips


def _first_bar_at_or_after(path: Sequence[Bar], ts: datetime) -> Optional[int]:
    for i, bar in enumerate(path):
        if bar.time >= ts:
            return i
    return None


def _open_into_event(
    trade: TradeRecord, events: Sequence[Event], pre_hours: int,
) -> Optional[datetime]:
    """Earliest ``T − pre`` the trade is still open into, else None."""
    pre = timedelta(hours=pre_hours)
    hits: list[datetime] = []
    for e in events:
        t_pre = e.time - pre
        if trade.entry_time < t_pre < trade.exit_time:
            hits.append(t_pre)
    return min(hits) if hits else None


def family_b_repriced(
    trade: TradeRecord, events: Sequence[Event], arm: ArmB,
) -> tuple[float, bool, str]:
    """Return ``(alt_r, touched, reason)``.

    ``touched`` is True iff the position was open into at least one
    window (Stage-0 engagement), even if the action then left R unchanged
    (BE arm, not yet in profit).
    """
    t_pre = _open_into_event(trade, events, arm.pre_hours)
    if t_pre is None:
        return float(trade.r), False, "untouched"
    decision = h4_open_at_or_after(t_pre)
    if not (trade.entry_time < decision <= trade.exit_time):
        return float(trade.r), True, "window_but_closed_before_h4_open"
    idx = _first_bar_at_or_after(trade.path, decision)
    if idx is None:
        return float(trade.r), True, "path_gap"
    bar = trade.path[idx]
    if arm.action == "flatten":
        return _r_from_exit(trade, bar.open), True, "flatten"
    # tighten_to_be
    in_profit = ((bar.open - trade.entry) * trade.dir_sign) > 0
    if not in_profit:
        return float(trade.r), True, "be_not_in_profit"
    for later in trade.path[idx:]:
        if trade.direction == "long":
            if later.low <= trade.entry:
                return 0.0, True, "be_touched"
        else:
            if later.high >= trade.entry:
                return 0.0, True, "be_touched"
    return float(trade.r), True, "be_held_original"


def winners_eaten_family_a(
    trades: Iterable[TradeRecord], suppressed: Sequence[bool],
) -> tuple[int, float]:
    n = 0
    total = 0.0
    for t, sup in zip(trades, suppressed):
        if sup and t.r > 0:
            n += 1
            total += float(t.r)
    return n, total


def winners_eaten_family_b(
    trades: Sequence[TradeRecord],
    alt_r: Sequence[float],
    touched: Sequence[bool],
) -> tuple[int, float]:
    """Original path hit TP after the de-risk, and alt R < original R."""
    n = 0
    given_back = 0.0
    for t, a, hit in zip(trades, alt_r, touched):
        if not hit:
            continue
        if t.exit_reason == "tp" and a < t.r:
            n += 1
            given_back += float(t.r) - float(a)
    return n, given_back
