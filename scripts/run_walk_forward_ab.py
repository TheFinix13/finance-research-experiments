"""A/B walk-forward driver for E013 safety-layer contribution study.

Runs `SupplyDemandAlpha` (`zone_d1_against` / H4 / all) across the standard
7-window walk-forward grid, with independent toggles for the three live-side
safety layers whose contribution we want to isolate:

  * ``wick_proof_enabled``  - Stop-loss triggers only when a bar CLOSES beyond
    the level (not on an intrabar wick). Mirrors production
    ``SoftStopConfig.confirm_on_close``. Panic-exit is preserved when price
    runs past the level by ``panic_mult`` * soft_dist intrabar, so a genuine
    breakdown is not held through the whole H4 bar.
  * ``be_migration_enabled`` - Stop-loss migrates to entry price when price
    reaches +1R intrabar. Mirrors ``LiveConfig.move_be_at_r = 1.0``.
  * ``plg_enabled`` - Post-loss cooldown: after a loss, skip the next
    ``cooldown_bars`` entries; after ``max_consecutive_losses`` in a UTC day,
    halt for the rest of the day. Mirrors ``PostLossGuard`` in a bar-driven
    harness.

Each toggle-combination is an ARM. For every (arm, walk-forward window) pair
we record: n_trades, hit_rate, median pips/trade, Sharpe (annualised over
trade P&L), and per-window pips list.

For arms with PLG enabled, we ALSO record every PLG-BLOCKED signal and walk
its would-be outcome forward under the SAME arm's other toggles (excluding
PLG itself). Aggregating outcomes over blocked signals yields the PLG
false-negative rate (blocks that would have won) and false-positive rate
(blocks that correctly averted a loss).

CLI
---

::

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        scripts/run_walk_forward_ab.py \
        --symbol EURUSD --output output/E013_safety_layer_contribution/results.json

The driver reads bars from the production parquet cache (via
``BarLoader``) and reuses production types + detectors read-only (no
production strategy code is mutated). This repo never trades; it measures.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import statistics
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

# Production repo (read-only) is on PYTHONPATH via
#   PYTHONPATH=../multi-pair-trading-agent:.
from agent.alphas.backtest import _CausalFVGTracker, FIXED_LOT
from agent.alphas.base import Alpha, AlphaContext
from agent.alphas.concepts import SupplyDemandAlpha
from agent.config import Config, load_config
from agent.data.loader import BarLoader, df_to_bars
from agent.rules.engine import precompute
from agent.types import Bar, Direction, Setup, Timeframe, Trade
from agent.utils import to_pips

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Walk-forward window definition (inherited from
# multi-pair-trading-agent/scripts/run_walk_forward.py so windows are directly
# comparable to the deployed cell verdict).
# ---------------------------------------------------------------------------

FULL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
FULL_END = datetime(2025, 12, 1, tzinfo=timezone.utc)
IS_YEARS = 4
OOS_YEARS = 1
WINDOW_STARTS = [
    datetime(y, 1, 1, tzinfo=timezone.utc)
    for y in range(2015, 2025 - IS_YEARS - OOS_YEARS + 2)
]


# ---------------------------------------------------------------------------
# Arm definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Arm:
    """One (wick, BE, PLG) toggle combination."""

    name: str
    wick_proof_enabled: bool
    be_migration_enabled: bool
    plg_enabled: bool

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "wick_proof_enabled": self.wick_proof_enabled,
            "be_migration_enabled": self.be_migration_enabled,
            "plg_enabled": self.plg_enabled,
        }


ARMS_LEAVE_ONE_OUT = (
    Arm("all_on", True, True, True),
    Arm("wick_off", False, True, True),
    Arm("be_off", True, False, True),
    Arm("all_off", False, False, False),
)


# ---------------------------------------------------------------------------
# Bar-driven Post-Loss Guard (simplified for the harness)
# ---------------------------------------------------------------------------

@dataclass
class PlgConfig:
    """Bar-driven PLG tunables. Defaults match LiveConfig where translatable."""

    cooldown_bars: int = 2  # H4: 2 bars ~= 8 hours, close to live's 60 min band
    max_consecutive_losses: int = 3
    catastrophic_loss_frac: float = 0.10


class BarPlg:
    """Pure-Python state machine mirroring ``PostLossGuard`` in a bar loop."""

    def __init__(self, cfg: PlgConfig, *, enabled: bool = True):
        self.cfg = cfg
        self.enabled = enabled
        self.reset()

    def reset(self) -> None:
        self.consecutive_losses = 0
        self.cooldown_until_bar: int | None = None
        self.day_halted = False
        self._day: date | None = None
        self.blocked_events: list[dict] = []

    def _maybe_roll_day(self, now: datetime) -> None:
        today = now.date()
        if self._day is None:
            self._day = today
            return
        if today != self._day:
            self._day = today
            self.consecutive_losses = 0
            self.cooldown_until_bar = None
            self.day_halted = False

    def pre_trade_check(self, *, bar_index: int, now: datetime) -> tuple[bool, str]:
        """Returns (allowed, reason). Reason non-empty only on blocks."""
        if not self.enabled:
            return True, ""
        self._maybe_roll_day(now)
        if self.day_halted:
            return False, "circuit_breaker"
        if (self.cooldown_until_bar is not None
                and bar_index < self.cooldown_until_bar):
            return False, "cooldown"
        return True, ""

    def register_close(
        self,
        *,
        pnl_pips: float,
        pnl_currency: float,
        account_balance: float,
        bar_index: int,
        now: datetime,
    ) -> None:
        if not self.enabled:
            return
        self._maybe_roll_day(now)
        if pnl_pips < 0:
            self.consecutive_losses += 1
            if self.cfg.cooldown_bars > 0:
                self.cooldown_until_bar = bar_index + self.cfg.cooldown_bars
            if (account_balance > 0
                    and abs(pnl_currency)
                    >= self.cfg.catastrophic_loss_frac * account_balance):
                self.day_halted = True
            if self.consecutive_losses >= self.cfg.max_consecutive_losses:
                self.day_halted = True
        elif pnl_pips > 0:
            self.consecutive_losses = 0


# ---------------------------------------------------------------------------
# Modified backtest with per-arm toggles
# ---------------------------------------------------------------------------

@dataclass
class ArmToggles:
    """Runtime toggles + tunables threaded into `_run_alpha_ab`."""

    wick_proof_enabled: bool = False
    be_migration_enabled: bool = False
    plg_enabled: bool = False
    panic_mult: float = 1.0
    plg_cfg: PlgConfig = field(default_factory=PlgConfig)
    # When True, PLG-blocked signals are simulated as-if-not-blocked and
    # recorded to `plg_blocked_events` for false-neg/pos analysis.
    record_plg_blocks: bool = True


@dataclass
class ArmRunResult:
    """Output of one (arm, window-span) run."""

    trades: list[Trade]
    plg_blocked_events: list[dict]


def _open_at_next_bar(
    signal, entry_bar: Bar, cfg: Config,
) -> Trade:
    """Reuse production's _open recipe: market fill at next bar open with
    spread + slippage, then re-anchor stop/TP to the fill."""
    spread_p, slip_p, commission = cfg.backtest.cost_for(entry_bar.timeframe.value)
    spread = spread_p * 0.0001
    slip = slip_p * 0.0001
    if signal.direction == Direction.LONG:
        fill = entry_bar.open + spread / 2 + slip
    else:
        fill = entry_bar.open - spread / 2 - slip

    stop_dist = abs(signal.entry - signal.stop)
    tp_dist = abs(signal.take_profit - signal.entry)
    if signal.direction == Direction.LONG:
        stop_price = fill - stop_dist
        tp_price = fill + tp_dist
    else:
        stop_price = fill + stop_dist
        tp_price = fill - tp_dist

    setup = Setup(
        direction=signal.direction, timeframe=entry_bar.timeframe,
        detected_at=entry_bar.time, detected_bar_index=0,
        entry=fill, stop=stop_price, take_profit=tp_price,
    )
    return Trade(
        setup=setup, direction=signal.direction, entry_time=entry_bar.time,
        entry_price=fill, stop_price=stop_price, tp_price=tp_price,
        lot_size=FIXED_LOT, commission=FIXED_LOT * commission,
    )


def _finalise_exit(
    trade: Trade, bar: Bar, exit_price: float, reason: str, cfg: Config,
) -> None:
    trade.exit_time = bar.time
    trade.exit_price = exit_price
    trade.exit_reason = reason
    if trade.direction == Direction.LONG:
        pip = to_pips(exit_price - trade.entry_price)
    else:
        pip = to_pips(trade.entry_price - exit_price)
    trade.pnl_pips = pip
    trade.pnl = (
        pip * trade.lot_size * cfg.backtest.pip_value_per_lot - trade.commission
    )


def _check_exit_ab(
    trade: Trade,
    bar: Bar,
    cfg: Config,
    toggles: ArmToggles,
    original_stop: float,
    original_entry: float,
    be_migrated: bool,
) -> tuple[bool, bool]:
    """Evaluate exit on ``bar`` under the arm's toggles.

    Returns ``(closed, new_be_migrated)``.

    Exit ordering:
      1. Take-profit: intrabar wick fill (aspirational; matches production).
      2. Wick-proof panic: intrabar price blew past soft stop by
         ``panic_mult`` * soft_dist -> exit at panic level.
      3. Wick-proof close: bar closed beyond stop -> exit at stop.
      4. Baseline (not wick-proof): intrabar SL wick -> exit at stop
         (worst-case straddle behaviour, identical to production
         `run_alpha`).
      5. BE migration side-effect: when trade reaches +1R intrabar and BE
         is enabled, migrate stop to entry from the *next* bar onward.
         (We do not close on the same bar as migration; that only happens
         if the bar also closed below entry, which the exit checks above
         already caught.)
    """
    long = trade.direction == Direction.LONG
    stop = trade.stop_price
    tp = trade.tp_price

    hit_tp = (bar.high >= tp) if long else (bar.low <= tp)
    if hit_tp:
        _finalise_exit(trade, bar, tp, "tp", cfg)
        return True, be_migrated

    if toggles.wick_proof_enabled:
        soft_dist = abs(original_entry - original_stop)
        panic_level = (
            stop - toggles.panic_mult * soft_dist if long
            else stop + toggles.panic_mult * soft_dist
        )
        breached_panic = (bar.low <= panic_level) if long else (bar.high >= panic_level)
        if breached_panic:
            _finalise_exit(trade, bar, panic_level, "sl_panic", cfg)
            return True, be_migrated
        breached_close = (bar.close < stop) if long else (bar.close > stop)
        if breached_close:
            _finalise_exit(trade, bar, stop, "sl_close", cfg)
            return True, be_migrated
    else:
        hit_sl = (bar.low <= stop) if long else (bar.high >= stop)
        if hit_sl:
            _finalise_exit(trade, bar, stop, "sl", cfg)
            return True, be_migrated

    if toggles.be_migration_enabled and not be_migrated:
        r_dist = abs(original_entry - original_stop)
        one_r_price = (
            original_entry + r_dist if long else original_entry - r_dist
        )
        touched_one_r = (bar.high >= one_r_price) if long else (bar.low <= one_r_price)
        if touched_one_r:
            trade.stop_price = original_entry
            be_migrated = True

    return False, be_migrated


def _run_alpha_ab(
    alpha: Alpha,
    bars: list[Bar],
    cfg: Config,
    *,
    ctx=None,
    start_index: int = 0,
    toggles: ArmToggles,
    initial_balance: float | None = None,
) -> ArmRunResult:
    """Version of `run_alpha` with arm-level toggles + PLG event recording."""
    if ctx is None:
        ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)
    fvg_tracker = _CausalFVGTracker(ctx.fvgs) if getattr(ctx, "fvgs", None) else None

    trades: list[Trade] = []
    open_trade: Trade | None = None
    open_original_stop: float | None = None
    open_original_entry: float | None = None
    be_migrated = False

    plg = BarPlg(toggles.plg_cfg, enabled=toggles.plg_enabled)
    balance = initial_balance if initial_balance is not None else cfg.backtest.initial_balance
    running_balance = float(balance)

    plg_blocked_events: list[dict] = []

    for i, bar in enumerate(bars):
        if fvg_tracker is not None:
            fvg_tracker.advance_to(i, bars)

        if open_trade is not None:
            closed, be_migrated = _check_exit_ab(
                open_trade, bar, cfg, toggles,
                original_stop=open_original_stop,
                original_entry=open_original_entry,
                be_migrated=be_migrated,
            )
            if closed:
                trades.append(open_trade)
                plg.register_close(
                    pnl_pips=open_trade.pnl_pips or 0.0,
                    pnl_currency=open_trade.pnl or 0.0,
                    account_balance=running_balance,
                    bar_index=i,
                    now=bar.time,
                )
                running_balance += open_trade.pnl or 0.0
                open_trade = None
                open_original_stop = None
                open_original_entry = None
                be_migrated = False

        if open_trade is None and start_index <= i < len(bars) - 1:
            sig = alpha.signal(actx, i)
            if sig is not None and sig.stop_pips > 0:
                allowed, block_reason = plg.pre_trade_check(
                    bar_index=i, now=bar.time,
                )
                if not allowed:
                    if toggles.record_plg_blocks:
                        # Simulate the trade under the same non-PLG toggles to
                        # capture the would-be outcome (false-neg/pos rate).
                        shadow_toggles = ArmToggles(
                            wick_proof_enabled=toggles.wick_proof_enabled,
                            be_migration_enabled=toggles.be_migration_enabled,
                            plg_enabled=False,
                            panic_mult=toggles.panic_mult,
                            plg_cfg=toggles.plg_cfg,
                            record_plg_blocks=False,
                        )
                        shadow = _open_at_next_bar(sig, bars[i + 1], cfg)
                        shadow_orig_stop = shadow.stop_price
                        shadow_orig_entry = shadow.entry_price
                        shadow_be = False
                        for j in range(i + 1, len(bars)):
                            closed_s, shadow_be = _check_exit_ab(
                                shadow, bars[j], cfg, shadow_toggles,
                                original_stop=shadow_orig_stop,
                                original_entry=shadow_orig_entry,
                                be_migrated=shadow_be,
                            )
                            if closed_s:
                                break
                        else:
                            # End-of-data fallback.
                            last = bars[-1]
                            _finalise_exit(
                                shadow, last, last.close, "end_of_data", cfg,
                            )
                        plg_blocked_events.append({
                            "entry_time": sig.entry_bar_time.isoformat()
                                if hasattr(sig, "entry_bar_time") and sig.entry_bar_time
                                else bar.time.isoformat(),
                            "block_reason": block_reason,
                            "direction": sig.direction.value,
                            "stop_pips": float(sig.stop_pips),
                            "would_be_pnl_pips": float(shadow.pnl_pips or 0.0),
                            "would_be_exit_reason": shadow.exit_reason,
                        })
                    continue
                open_trade = _open_at_next_bar(sig, bars[i + 1], cfg)
                open_original_stop = open_trade.stop_price
                open_original_entry = open_trade.entry_price
                be_migrated = False

    if open_trade is not None and open_trade.exit_time is None:
        last = bars[-1]
        _finalise_exit(open_trade, last, last.close, "end_of_data", cfg)
        trades.append(open_trade)

    return ArmRunResult(trades=trades, plg_blocked_events=plg_blocked_events)


# ---------------------------------------------------------------------------
# Per-window metric aggregation
# ---------------------------------------------------------------------------

def _sharpe(pips: list[float]) -> float | None:
    """Annualised Sharpe over trade P&L (H4 -> ~1500 bars/yr / ~66 trades/yr,
    scale by sqrt(66) for annualisation)."""
    if len(pips) < 2:
        return None
    mean = statistics.fmean(pips)
    stdev = statistics.pstdev(pips)
    if stdev == 0:
        return None
    return (mean / stdev) * math.sqrt(66.0)


def _summarise_trades(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "n_trades": 0, "hit_rate": None, "median_pips": None,
            "mean_pips": None, "sharpe": None, "sum_pips": 0.0,
        }
    pips = [(t.pnl_pips or 0.0) for t in trades]
    wins = sum(1 for p in pips if p > 0)
    return {
        "n_trades": len(trades),
        "hit_rate": wins / len(trades),
        "median_pips": statistics.median(pips),
        "mean_pips": statistics.fmean(pips),
        "sharpe": _sharpe(pips),
        "sum_pips": sum(pips),
    }


def _summarise_plg_blocks(events: list[dict]) -> dict:
    if not events:
        return {
            "n_blocks": 0, "false_neg_rate": None, "false_pos_rate": None,
            "median_would_be_pips": None,
        }
    would_be = [e["would_be_pnl_pips"] for e in events]
    wins = sum(1 for p in would_be if p > 0)
    losses = sum(1 for p in would_be if p < 0)
    return {
        "n_blocks": len(events),
        "false_neg_rate": wins / len(events),  # blocks that would have won
        "false_pos_rate": losses / len(events),  # blocks that correctly averted a loss
        "median_would_be_pips": statistics.median(would_be),
        "mean_would_be_pips": statistics.fmean(would_be),
    }


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def _slice_trades(
    trades: list[Trade], lo: datetime, hi: datetime,
) -> list[Trade]:
    return [
        t for t in trades
        if t.exit_time is not None and lo <= t.entry_time < hi
    ]


def _slice_events(events: list[dict], lo: datetime, hi: datetime) -> list[dict]:
    def _t(e):
        return datetime.fromisoformat(e["entry_time"])
    return [e for e in events if lo <= _t(e) < hi]


def _make_alpha(cfg: Config, alpha_name: str) -> Alpha:
    if alpha_name == "zone_d1_against":
        return SupplyDemandAlpha(
            cfg, htf_align="D1", htf_align_mode="against",
            htf_lookback=10, htf_min_move_pips=60.0,
        )
    if alpha_name == "zone":
        return SupplyDemandAlpha(cfg)
    raise ValueError(f"unknown alpha: {alpha_name}")


def run_ab_grid(
    *,
    symbol: str,
    timeframe: Timeframe,
    alpha_name: str,
    arms: Iterable[Arm],
    cfg: Config,
    output_path: Path,
    log_progress: Callable[[str], None] = print,
) -> dict:
    """Run every (arm, window) combination and return the payload written to disk."""
    loader = BarLoader(cache_root=cfg.data_dir)
    log_progress(f"Loading {symbol} {timeframe.value} bars {FULL_START.year}-{FULL_END.year} ...")
    df = loader.get(symbol, timeframe, FULL_START, FULL_END, refresh=False)
    bars = df_to_bars(df, timeframe)
    log_progress(f"  {len(bars):,} bars")

    log_progress("Precomputing detector context (single pass over full series)...")
    ctx = precompute(bars, cfg)
    log_progress(
        f"  zones={len(ctx.zones)} fvgs={len(getattr(ctx, 'fvgs', []) or [])} "
        f"sweeps={len(getattr(ctx, 'liquidity_sweeps', []) or [])}"
    )

    payload = {
        "meta": {
            "symbol": symbol,
            "timeframe": timeframe.value,
            "alpha": alpha_name,
            "full_start": FULL_START.isoformat(),
            "full_end": FULL_END.isoformat(),
            "is_years": IS_YEARS,
            "oos_years": OOS_YEARS,
            "n_windows": len(WINDOW_STARTS),
            "arms": [a.as_dict() for a in arms],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "harness": "run_walk_forward_ab.py",
        },
        "arms": {},
    }

    for arm in arms:
        log_progress(f"\nArm {arm.name}: {arm.as_dict()}")
        toggles = ArmToggles(
            wick_proof_enabled=arm.wick_proof_enabled,
            be_migration_enabled=arm.be_migration_enabled,
            plg_enabled=arm.plg_enabled,
            record_plg_blocks=arm.plg_enabled,
        )
        alpha = _make_alpha(cfg, alpha_name)
        run = _run_alpha_ab(
            alpha, bars, cfg, ctx=ctx, start_index=200, toggles=toggles,
        )
        log_progress(
            f"  full-series trades: {len(run.trades):,}  "
            f"plg-blocked: {len(run.plg_blocked_events):,}"
        )

        per_window = []
        for w_idx, is_start in enumerate(WINDOW_STARTS):
            is_end = datetime(is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
            oos_start = is_end
            oos_end = datetime(oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
            if oos_end > FULL_END:
                oos_end = FULL_END

            is_trades = _slice_trades(run.trades, is_start, is_end)
            oos_trades = _slice_trades(run.trades, oos_start, oos_end)
            oos_blocks = _slice_events(run.plg_blocked_events, oos_start, oos_end)

            per_window.append({
                "window": w_idx + 1,
                "is_start": is_start.isoformat(),
                "is_end": is_end.isoformat(),
                "oos_start": oos_start.isoformat(),
                "oos_end": oos_end.isoformat(),
                "is": _summarise_trades(is_trades),
                "oos": _summarise_trades(oos_trades),
                "oos_plg_blocks": _summarise_plg_blocks(oos_blocks),
            })

        arm_full = _summarise_trades(run.trades)
        arm_blocks_full = _summarise_plg_blocks(run.plg_blocked_events)

        payload["arms"][arm.name] = {
            "toggles": arm.as_dict(),
            "full_series": arm_full,
            "full_series_plg_blocks": arm_blocks_full,
            "windows": per_window,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str))
    log_progress(f"\nWrote {output_path}")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H4",
                        choices=[tf.value for tf in Timeframe])
    parser.add_argument("--alpha", default="zone_d1_against",
                        choices=["zone", "zone_d1_against"])
    parser.add_argument(
        "--output", default="output/E013_safety_layer_contribution/results.json",
        help="Path to JSON payload (relative to research repo root).",
    )
    parser.add_argument(
        "--arms", default="leave_one_out",
        choices=["leave_one_out", "full_grid"],
        help="leave_one_out = 4 arms (matches E013 pre-registration); "
             "full_grid = all 2^3 = 8 arms (exploratory).",
    )
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper())
    cfg = load_config()
    tf = Timeframe(args.timeframe)

    if args.arms == "leave_one_out":
        arms = ARMS_LEAVE_ONE_OUT
    else:
        arms = tuple(
            Arm(
                name=(
                    ("w" if w else "-")
                    + ("b" if b else "-")
                    + ("p" if p else "-")
                ),
                wick_proof_enabled=w,
                be_migration_enabled=b,
                plg_enabled=p,
            )
            for w in (False, True)
            for b in (False, True)
            for p in (False, True)
        )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent.parent / output_path

    run_ab_grid(
        symbol=args.symbol,
        timeframe=tf,
        alpha_name=args.alpha,
        arms=arms,
        cfg=cfg,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
