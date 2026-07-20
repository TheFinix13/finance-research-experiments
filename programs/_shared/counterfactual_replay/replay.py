"""PRE-0 deterministic counterfactual-replay engine.

Consumes the path-augmented trade ledgers produced by
``export_ledger_with_paths.py`` and applies user-defined exit rules to
each trade's intraday OHLC path, producing an ``AltTradeRecord`` that
carries the alternative-rule outcome (``exit_time``, ``exit_price``,
``pnl_pips``, ``r``, ``exit_reason``) alongside the original trade.

Invariants (unit-tested in ``tests/``):

1. ``replay(trade, rule=None)`` reproduces the original trade byte-for-byte
   on the decision fields (SPEC §4.1).
2. Stop-authority monotonicity — rules may only tighten a stop, never
   loosen it (SPEC §4.2).
3. Exit-priority ordering — on the same bar the priority is
   ``hard_SL → E024_stall_close → E021_partial → broker_TP → E020_ratchet →
   E023_structure_trail`` (SPEC §4.3).
4. No look-ahead — a rule's decision on bar ``i`` may only depend on bars
   ≤ ``i``.
5. Determinism — for a fixed trade + rule + seed, output is identical
   across runs.

Usage::

    from programs._shared.counterfactual_replay.replay import (
        load_paths_ledger, replay, RuleFn, TradeState, ExitAction,
    )

    trades = load_paths_ledger("EURUSD")
    def my_rule(state, bar):
        if state.mfe_r_so_far >= 1.2:
            return ExitAction(kind="adjust_stop",
                              price=state.entry + state.direction * 0.5 * state.mfe_pips_so_far * PIP,
                              reason="E020_ratchet")
        return None
    alt_trades = [replay(t, rule=my_rule) for t in trades]
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Iterator, Literal, Optional

# ---------------------------------------------------------------------------
# Constants (locked to production semantics on the deployed cell).
# ---------------------------------------------------------------------------

# Pip factor for 4-decimal FX majors (EURUSD / GBPUSD / USDCAD).
# 0.0001 price move = 1 pip. If a JPY pair is ever added, this changes.
PIP: float = 0.0001

# BE migration fires the first bar MFE crosses this R-multiple.
# Locked at 1.0 per production (`LiveConfig.move_be_at_r = 1.0`).
BE_TRIGGER_R: float = 1.0

# Exit-priority tokens (SPEC §4.3). Rules that need to arbitrate ties
# use these string tags in their ExitAction.reason field.
PRIORITY_HARD_SL = "hard_sl"
PRIORITY_E024_STALL = "e024_stall_exit"
PRIORITY_E021_PARTIAL = "e021_partial_close"
PRIORITY_TP = "broker_tp_hit"
PRIORITY_E020_RATCHET = "e020_mfe_ratchet_stop"
PRIORITY_E023_STRUCT_TRAIL = "e023_structure_trail"

_DEFAULT_EXIT_PRIORITY: tuple[str, ...] = (
    PRIORITY_HARD_SL,
    PRIORITY_E024_STALL,
    PRIORITY_E021_PARTIAL,
    PRIORITY_TP,
    PRIORITY_E020_RATCHET,
    PRIORITY_E023_STRUCT_TRAIL,
)


# ---------------------------------------------------------------------------
# Data classes (mirror the PRE-0 JSONL schema).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TradeRecord:
    """One row from the PRE-0 JSONL ledger, deserialised."""

    trade_id: str
    symbol: str
    tf: str
    direction: str  # "long" | "short"
    entry_time: datetime
    entry: float
    stop: float           # BE-migrated final stop from the base backtest
    soft_stop: float      # original entry-time catastrophic SL
    take_profit: float
    stop_pips: float
    tp_pips: float
    r: float
    pnl_pips: float
    exit_time: datetime
    exit_price: float
    exit_reason: str
    mfe_pips: float
    mae_pips: float
    mfe_ts: datetime
    mae_ts: datetime
    mfe_r: float
    mae_r: float
    path: list[Bar]
    path_resolution: str

    @property
    def dir_sign(self) -> int:
        return +1 if self.direction == "long" else -1


@dataclass
class TradeState:
    """Mutable state passed to rules at each bar.

    The rule sees only causal information (no bars > current bar). All
    fields are updated by the engine BEFORE the rule is called on bar i,
    so the rule sees the state AS OF the end of bar i.
    """

    entry: float
    direction: int                          # +1 long, -1 short
    stop_pips: float
    tp: float
    original_stop: float                    # entry-time catastrophic SL
    current_stop: float                     # after all monotonic tightenings
    be_migrated: bool
    mfe_pips_so_far: float                  # monotone non-decreasing
    mfe_ts_so_far: datetime
    mae_pips_so_far: float
    bar_index: int
    now: datetime
    remaining_fraction: float               # 1.0 - sum(partial_close.fraction)

    @property
    def mfe_r_so_far(self) -> float:
        return self.mfe_pips_so_far / self.stop_pips if self.stop_pips > 0 else 0.0

    @property
    def mae_r_so_far(self) -> float:
        return self.mae_pips_so_far / self.stop_pips if self.stop_pips > 0 else 0.0


@dataclass(frozen=True)
class ExitAction:
    """One action from a rule at one bar.

    The engine may drop or re-order actions to satisfy invariants (SPEC
    §4.2 stop monotonicity, §4.3 exit priority)."""

    kind: Literal["close_at", "adjust_stop", "adjust_tp", "partial_close"]
    price: Optional[float] = None       # for close_at, adjust_stop, adjust_tp
    fraction: Optional[float] = None    # for partial_close (0 < f ≤ 1)
    reason: str = ""                    # for the exit_reason log


RuleFn = Callable[[TradeState, Bar], Optional[ExitAction]]


@dataclass
class Fill:
    """One partial-close fill within a trade."""

    time: datetime
    price: float
    fraction: float
    reason: str


@dataclass(frozen=True)
class AltTradeRecord:
    """Original trade + alternative-rule outcome + partial-fill audit."""

    original: TradeRecord
    exit_time: datetime
    exit_price: float
    exit_reason: str
    pnl_pips: float                     # fraction-weighted across all fills + final
    r: float                            # pnl_pips / stop_pips
    fills: list[Fill] = field(default_factory=list)
    mfe_pips_at_exit: float = 0.0
    mae_pips_at_exit: float = 0.0


# ---------------------------------------------------------------------------
# Loader.
# ---------------------------------------------------------------------------

_DEFAULT_DATA_DIR = Path(__file__).parent / "data"


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _bar_from_dict(d: dict) -> Bar:
    return Bar(
        time=_parse_dt(d["ts"]),
        open=float(d["o"]),
        high=float(d["h"]),
        low=float(d["l"]),
        close=float(d["c"]),
    )


def _trade_from_dict(d: dict) -> TradeRecord:
    return TradeRecord(
        trade_id=d["trade_id"],
        symbol=d["symbol"],
        tf=d["tf"],
        direction=d["direction"],
        entry_time=_parse_dt(d["entry_time"]),
        entry=float(d["entry"]),
        stop=float(d["stop"]),
        soft_stop=float(d["soft_stop"]),
        take_profit=float(d["take_profit"]),
        stop_pips=float(d["stop_pips"]),
        tp_pips=float(d["tp_pips"]),
        r=float(d["r"]),
        pnl_pips=float(d["pnl_pips"]),
        exit_time=_parse_dt(d["exit_time"]),
        exit_price=float(d["exit_price"]),
        exit_reason=d["exit_reason"],
        mfe_pips=float(d["mfe_pips"]),
        mae_pips=float(d["mae_pips"]),
        mfe_ts=_parse_dt(d["mfe_ts"]),
        mae_ts=_parse_dt(d["mae_ts"]),
        mfe_r=float(d["mfe_r"]),
        mae_r=float(d["mae_r"]),
        path=[_bar_from_dict(b) for b in d["path"]],
        path_resolution=d["path_resolution"],
    )


def load_paths_ledger(
    symbol: str,
    tf: str = "H4",
    data_dir: Path | str = _DEFAULT_DATA_DIR,
) -> tuple[dict, list[TradeRecord]]:
    """Load the PRE-0 JSONL ledger for ``symbol`` at ``tf``. Returns
    ``(meta, trades)`` where ``meta`` is the header dict and ``trades`` is
    a list of deserialised ``TradeRecord``.

    Raises ``FileNotFoundError`` if the ledger does not exist — consumer
    studies should not silently degrade to no-ledger behaviour."""
    path = Path(data_dir) / f"{symbol}_{tf}_paths.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"PRE-0 ledger missing: {path}. Run "
            f"programs/_shared/counterfactual_replay/export_ledger_with_paths.py "
            f"--symbol {symbol} first."
        )
    meta: dict = {}
    trades: list[TradeRecord] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# meta:"):
                meta = json.loads(line[len("# meta:"):].strip())
                continue
            trades.append(_trade_from_dict(json.loads(line)))
    return meta, trades


def stream_paths_ledger(
    symbol: str,
    tf: str = "H4",
    data_dir: Path | str = _DEFAULT_DATA_DIR,
) -> Iterator[TradeRecord]:
    """Same as ``load_paths_ledger`` but yields one trade at a time. Use
    for memory-bound sweeps over large ledgers (EURUSD is 26 MB)."""
    path = Path(data_dir) / f"{symbol}_{tf}_paths.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"PRE-0 ledger missing: {path}")
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("# meta:"):
                continue
            yield _trade_from_dict(json.loads(line))


# ---------------------------------------------------------------------------
# Replay engine.
# ---------------------------------------------------------------------------

def _to_pips(price_diff: float) -> float:
    """Convert a signed price delta to pips (4-decimal majors)."""
    return price_diff / PIP


def _pips_to_price(pips: float) -> float:
    return pips * PIP


def _tighten(
    current_stop: float, proposed_stop: float, direction: int,
) -> tuple[float, bool]:
    """Apply the monotone-tightening invariant (SPEC §4.2).

    Returns ``(new_stop, was_tightened)``. If the proposed stop would
    loosen (larger for long / smaller for short), the current stop is
    kept and ``was_tightened=False``."""
    if direction == +1:
        if proposed_stop > current_stop:
            return proposed_stop, True
    else:
        if proposed_stop < current_stop:
            return proposed_stop, True
    return current_stop, False


def _bar_hits_stop(bar: Bar, stop: float, direction: int) -> bool:
    """Long: bar's low crosses stop from above. Short: bar's high crosses
    stop from below."""
    if direction == +1:
        return bar.low <= stop
    return bar.high >= stop


def _bar_hits_tp(bar: Bar, tp: float, direction: int) -> bool:
    if direction == +1:
        return bar.high >= tp
    return bar.low <= tp


def _bar_hits_price(bar: Bar, price: float, direction: int, side: str) -> bool:
    """side='favorable' → high (long) / low (short); 'adverse' → low / high."""
    if side == "favorable":
        return (bar.high >= price) if direction == +1 else (bar.low <= price)
    return (bar.low <= price) if direction == +1 else (bar.high >= price)


def _finalize(
    trade: TradeRecord,
    exit_time: datetime,
    exit_price: float,
    exit_reason: str,
    fills: list[Fill],
    mfe_pips_at_exit: float,
    mae_pips_at_exit: float,
) -> AltTradeRecord:
    """Aggregate partial + final fills into a single pnl_pips and r."""
    direction = trade.dir_sign
    # Final leg: whatever fraction is left after all partial closes.
    total_partial = sum(f.fraction for f in fills)
    final_fraction = max(0.0, 1.0 - total_partial)

    # Fraction-weighted pnl in pips.
    pips_from_partials = sum(
        direction * _to_pips(f.price - trade.entry) * f.fraction for f in fills
    )
    pips_from_final = direction * _to_pips(exit_price - trade.entry) * final_fraction
    pnl_pips = pips_from_partials + pips_from_final

    r = pnl_pips / trade.stop_pips if trade.stop_pips > 0 else 0.0
    return AltTradeRecord(
        original=trade,
        exit_time=exit_time,
        exit_price=exit_price,
        exit_reason=exit_reason,
        pnl_pips=round(pnl_pips, 4),
        r=round(r, 4),
        fills=fills,
        mfe_pips_at_exit=round(mfe_pips_at_exit, 4),
        mae_pips_at_exit=round(mae_pips_at_exit, 4),
    )


def replay(
    trade: TradeRecord,
    rule: RuleFn | None = None,
    exit_priority: tuple[str, ...] = _DEFAULT_EXIT_PRIORITY,
) -> AltTradeRecord:
    """Deterministically replay one trade with an optional alternative
    rule (SPEC §4).

    The engine walks ``trade.path`` bar-by-bar, updating MFE/MAE/BE state,
    calling the rule (if provided), then checking exits in the SPEC §4.3
    priority order. Rules may only tighten stops (SPEC §4.2); loosen
    actions are silently dropped.

    When ``rule is None``, the engine reproduces the base trade's exit
    exactly (SPEC §4.1 null-rule invariant) — a fast path that skips path
    replay entirely.
    """
    # Null-rule fast path (invariant §4.1).
    if rule is None:
        return AltTradeRecord(
            original=trade,
            exit_time=trade.exit_time,
            exit_price=trade.exit_price,
            exit_reason=trade.exit_reason,
            pnl_pips=trade.pnl_pips,
            r=trade.r,
            fills=[],
            mfe_pips_at_exit=trade.mfe_pips,
            mae_pips_at_exit=trade.mae_pips,
        )

    direction = trade.dir_sign
    entry = trade.entry
    stop_pips = trade.stop_pips
    tp = trade.take_profit
    original_stop = trade.soft_stop

    # One-R price (BE trigger).
    one_r_price = entry + direction * stop_pips * PIP

    current_stop = original_stop
    be_migrated = False
    mfe_pips_so_far = 0.0
    mfe_ts_so_far = trade.entry_time
    mae_pips_so_far = 0.0
    remaining_fraction = 1.0
    fills: list[Fill] = []
    # BE migration fires the FIRST bar MFE ≥ 1R, but the tighter stop
    # only becomes effective on the NEXT bar (production semantics — see
    # scripts/run_walk_forward_ab.py::_check_exit_ab, BE side-effect after
    # the exit check).
    be_migration_pending = False

    # Priority map for tie-breaking on the same bar.
    priority_index = {tag: i for i, tag in enumerate(exit_priority)}

    for i, bar in enumerate(trade.path):
        # Apply BE tightening deferred from the previous bar BEFORE checking exits.
        if be_migration_pending and not be_migrated:
            be_migrated = True
            current_stop, _ = _tighten(current_stop, entry, direction)
            be_migration_pending = False

        # Update MFE/MAE (strict >; earliest-bar wins on ties per SPEC §1).
        if direction == +1:
            fav_pips = _to_pips(bar.high - entry)
            adv_pips = _to_pips(entry - bar.low)
        else:
            fav_pips = _to_pips(entry - bar.low)
            adv_pips = _to_pips(bar.high - entry)

        if fav_pips > mfe_pips_so_far:
            mfe_pips_so_far = fav_pips
            mfe_ts_so_far = bar.time
        if adv_pips > mae_pips_so_far:
            mae_pips_so_far = adv_pips

        # BE migration trigger check (arms the deferred update for next bar).
        if not be_migrated and mfe_pips_so_far >= stop_pips * BE_TRIGGER_R:
            be_migration_pending = True

        # Ask the rule (state as-of end-of-bar-i).
        state = TradeState(
            entry=entry,
            direction=direction,
            stop_pips=stop_pips,
            tp=tp,
            original_stop=original_stop,
            current_stop=current_stop,
            be_migrated=be_migrated,
            mfe_pips_so_far=mfe_pips_so_far,
            mfe_ts_so_far=mfe_ts_so_far,
            mae_pips_so_far=mae_pips_so_far,
            bar_index=i,
            now=bar.time,
            remaining_fraction=remaining_fraction,
        )
        action = rule(state, bar)

        # -----------------------------------------------------------------
        # Exit checks in SPEC §4.3 priority. Any candidate close at this
        # bar competes; ties broken by exit_priority index.
        # -----------------------------------------------------------------
        candidates: list[tuple[int, str, float, str]] = []  # (prio_idx, kind, price, reason)

        if _bar_hits_stop(bar, current_stop, direction):
            candidates.append((
                priority_index.get(PRIORITY_HARD_SL, 0),
                "close_at", current_stop,
                "sl" if not be_migrated else "sl_be",
            ))
        if _bar_hits_tp(bar, tp, direction):
            candidates.append((
                priority_index.get(PRIORITY_TP, 3),
                "close_at", tp, "tp",
            ))

        # Rule-driven exit (E024 stall close, or E020 could theoretically
        # emit close_at but is designed as adjust_stop).
        rule_close: Optional[ExitAction] = None
        rule_partial: Optional[ExitAction] = None
        rule_stop_adjust: Optional[ExitAction] = None
        rule_tp_adjust: Optional[ExitAction] = None
        if action is not None:
            if action.kind == "close_at":
                rule_close = action
                # Map reason → priority (default E024 stall bucket).
                prio = priority_index.get(action.reason, priority_index.get(PRIORITY_E024_STALL, 1))
                candidates.append((prio, "close_at", action.price, action.reason))
            elif action.kind == "partial_close":
                rule_partial = action
            elif action.kind == "adjust_stop":
                rule_stop_adjust = action
            elif action.kind == "adjust_tp":
                rule_tp_adjust = action

        if candidates:
            # Lowest priority index wins.
            candidates.sort(key=lambda c: c[0])
            _, _, exit_price, exit_reason = candidates[0]

            # If we closed at a rule action but partial_close was also
            # requested on same bar, apply partial FIRST (E021 fires
            # before broker TP per §4.3). Partial-then-full-close means
            # the partial is booked and the remaining is closed at exit_price.
            if rule_partial is not None and exit_reason in ("tp", PRIORITY_TP):
                _apply_partial(rule_partial, bar, direction, remaining_fraction, fills)
                remaining_fraction -= rule_partial.fraction  # type: ignore[operator]

            return _finalize(
                trade=trade,
                exit_time=bar.time,
                exit_price=exit_price,
                exit_reason=exit_reason,
                fills=fills,
                mfe_pips_at_exit=mfe_pips_so_far,
                mae_pips_at_exit=mae_pips_so_far,
            )

        # No exit this bar — apply non-closing actions (partial fill, stop tighten).
        if rule_partial is not None:
            _apply_partial(rule_partial, bar, direction, remaining_fraction, fills)
            remaining_fraction -= rule_partial.fraction  # type: ignore[operator]
            if remaining_fraction <= 1e-9:
                # Fully closed by partials.
                return _finalize(
                    trade=trade,
                    exit_time=bar.time,
                    exit_price=fills[-1].price,
                    exit_reason=fills[-1].reason,
                    fills=fills,
                    mfe_pips_at_exit=mfe_pips_so_far,
                    mae_pips_at_exit=mae_pips_so_far,
                )
        if rule_stop_adjust is not None and rule_stop_adjust.price is not None:
            current_stop, _ = _tighten(current_stop, rule_stop_adjust.price, direction)
        if rule_tp_adjust is not None and rule_tp_adjust.price is not None:
            # TP-adjust is loose semantics — allow move-toward-favorable
            # (widen or tighten) but only at bar 0 (order placement). E022
            # uses this. After bar 0, we ignore.
            if i == 0:
                tp = rule_tp_adjust.price

    # ---------------------------------------------------------------------
    # Path exhausted without a rule-driven exit. Fall back to the ORIGINAL
    # exit (§4.1 spirit: if the alternative rule never fires, don't
    # invent a synthetic exit). Any partials that fired stay booked.
    # ---------------------------------------------------------------------
    return _finalize(
        trade=trade,
        exit_time=trade.exit_time,
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        fills=fills,
        mfe_pips_at_exit=mfe_pips_so_far,
        mae_pips_at_exit=mae_pips_so_far,
    )


def _apply_partial(
    action: ExitAction,
    bar: Bar,
    direction: int,
    remaining_fraction: float,
    fills: list[Fill],
) -> None:
    """Book a partial close. Fill price is ``action.price`` if provided,
    else the bar's ``open`` (conservative)."""
    if action.fraction is None or action.fraction <= 0:
        return
    frac = min(action.fraction, remaining_fraction)
    price = action.price if action.price is not None else bar.open
    fills.append(Fill(
        time=bar.time,
        price=price,
        fraction=frac,
        reason=action.reason or "partial",
    ))


# ---------------------------------------------------------------------------
# Batch replay.
# ---------------------------------------------------------------------------

def replay_all(
    trades: Iterable[TradeRecord],
    rule: RuleFn | None = None,
    exit_priority: tuple[str, ...] = _DEFAULT_EXIT_PRIORITY,
) -> list[AltTradeRecord]:
    """Convenience: replay a batch of trades under one rule."""
    return [replay(t, rule=rule, exit_priority=exit_priority) for t in trades]
