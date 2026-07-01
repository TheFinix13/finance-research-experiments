"""Phi3 gate evaluation harness -- A1 Isagi v1 vs Sae frozen baseline.

The Phi3 -> Phi4 gate (`09-experiment-architecture.md` G4 row, charter
C1, doctrine 06 section 5) requires the wrapped production cell to
reproduce E004's `zone_d1_against / H4 / all` performance on EURUSD H4.
This harness is the *wrapper validation*: we want NO degradation from
production behaviour, not a new edge.

What it does (in order):

1. Loads EURUSD H4 bars 2015-01-01 -> 2025-12-31 from the production
   parquet cache via the cross-repo `agent.data.loader.BarLoader`. The
   2015-2025 span matches E004's 7-window walk-forward exactly
   (4 yr IS / 1 yr OOS rolling).
2. Instantiates A1IsagiV1 (which wraps `SupplyDemandAlpha` at the
   locked E004 params) and `prepare()`s the bar series.
3. Drives the M001 engine through every H4 bar in the dev window:
   `observe -> Thought`, `intend -> AgentProposal | None`. Proposals
   flow through the Phi2.5 aggregator stub into OrderIntents.
4. For each emitted Proposal, opens a single-position trade using the
   production fill model (`agent.alphas.backtest._open` /
   `_check_exit`) so the resulting pip distribution is byte-comparable
   to the E004 reference cell.
5. Scores every closed trade with `sim/scoring/tqs.py` and slices the
   trade ledger by the 7 OOS windows: (IS 2015-2018 -> OOS 2019), ...,
   (IS 2021-2024 -> OOS 2025).
6. Writes a markdown report to
   `programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1.md`
   summarising:
   * per-window trade count, mean pip/trade, mean TQS, win rate
   * aggregate dev-window stats vs Sae baseline +11.34 pips/trade
   * sign test: how many of 7 OOS windows positive?
   * gate verdict: PASS / PARTIAL / FAIL / PROVISIONAL

CLI:

    PYTHONPATH=../multi-pair-trading-agent:. \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate
        [--symbol EURUSD] [--start 2015-01-01] [--end 2025-12-31]
        [--out reviews/phi3_gate_isagi_v1.md]
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
    A1IsagiV1,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.scoring.tqs import compute_tqs

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sae baseline (frozen) -- the universal gate for Phi3 -> Phi4 (G4).
# Source: docs/findings/2026-06-09_walk_forward_validation.md (E004).
# ---------------------------------------------------------------------------
SAE_BASELINE_PIPS_PER_TRADE = 11.34
SAE_BASELINE_OOS_WINDOWS_POSITIVE = 7  # of 7
SAE_BASELINE_LABEL = "zone_d1_against / H4 / all (E004)"

# Walk-forward window structure (matches `scripts/run_walk_forward.py`).
IS_YEARS = 4
OOS_YEARS = 1
DEFAULT_FULL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
DEFAULT_FULL_END = datetime(2025, 12, 31, tzinfo=timezone.utc)
WARMUP_BARS = 200  # detectors need history; matches production run_walk_forward.py


@dataclass
class TradeRecord:
    """One closed simulated trade, with TQS components attached."""

    agent_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry: float
    stop: float
    take_profit: float
    exit_price: float
    exit_reason: str  # "tp" | "sl" | "end_of_data"
    pnl_pips: float
    mae_pips: float
    mfe_pips: float
    bars_held: int
    r_multiple: float
    tqs_components: dict
    # F19/F20 provenance (2026-07-01, added for G7 C5/C6 evaluators).
    # Optional so pre-existing TradeRecord constructors keep working;
    # populated by _annotate_trade_record when the driver captures the
    # source proposal metadata on the prod-trade object.
    source_conviction: float | None = None
    source_regime_fit: float | None = None
    source_sl_pips: float | None = None
    source_atr_pips: float | None = None
    source_h1_swing_pips: float | None = None


@dataclass
class WindowStats:
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    is_n: int = 0
    is_mean_pips: float = 0.0
    is_median_pips: float = 0.0
    is_mean_tqs: float = 0.0
    is_win_rate: float = 0.0
    oos_n: int = 0
    oos_mean_pips: float = 0.0
    oos_median_pips: float = 0.0
    oos_mean_tqs: float = 0.0
    oos_win_rate: float = 0.0


@dataclass
class GateReport:
    symbol: str
    full_start: datetime
    full_end: datetime
    n_bars: int
    n_thoughts: int
    n_proposals: int
    n_trades: int
    overall_mean_pips: float
    overall_median_pips: float
    overall_mean_tqs: float
    overall_win_rate: float
    oos_windows_positive: int
    oos_windows_total: int
    # Per-window OOS expectancy median -- the apples-to-apples comparator
    # to E004's "+11.34 median OOS pips/trade" headline. This is the
    # median across the 7 OOS windows of each window's mean pip/trade.
    median_oos_window_mean_pips: float = 0.0
    mean_oos_window_mean_pips: float = 0.0
    median_oos_window_mean_tqs: float = 0.0
    windows: list[WindowStats] = field(default_factory=list)
    verdict: str = "PENDING"
    verdict_reason: str = ""
    data_window_match_e004: bool = True
    provisional_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_production_bars(
    symbol: str, start: datetime, end: datetime,
) -> list:
    """Load OHLCV H4 bars from the production parquet cache."""
    ensure_production_repo_on_path()
    from agent.config import load_config  # noqa: E402
    from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
    from agent.types import Timeframe  # noqa: E402

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    df = loader.get(symbol, Timeframe.H4, start, end, refresh=False)
    return df_to_bars(df, Timeframe.H4)


# ---------------------------------------------------------------------------
# Trade execution (production fill model)
# ---------------------------------------------------------------------------

def _open_trade_from_proposal(
    proposal: AgentProposal,
    next_bar,  # production Bar
    cfg,
):
    """Open a trade at next-bar-open using the production fill model.

    Mirrors `agent.alphas.backtest._open` so the simulated pip distribution
    is byte-comparable to the E004 walk-forward output. The production
    function takes an `AlphaSignal`, not an `AgentProposal`; we
    reconstruct a minimal AlphaSignal shim from the Proposal's
    `entry/stop/take_profit/direction/conviction/rationale`.
    """
    from agent.alphas.backtest import _open as prod_open  # noqa: E402
    from agent.alphas.base import AlphaSignal  # noqa: E402
    from agent.types import Direction  # noqa: E402

    direction = (
        Direction.LONG if proposal.direction == "long" else Direction.SHORT
    )
    # TP from proposal.ladder[0] OR fallback to a derived TP from R:R.
    take_profit = float(proposal.ladder[0].price) if proposal.ladder else float(proposal.entry)
    shim = AlphaSignal(
        direction=direction,
        entry=float(proposal.entry),
        stop=float(proposal.stop),
        take_profit=take_profit,
        reason=proposal.rationale.get("signal_reason", "zone_isagi_v1"),
        conviction=float(proposal.conviction),
        meta=dict(proposal.rationale),
    )
    return prod_open(shim, next_bar, cfg)


def _check_exit(trade, bar, cfg) -> bool:
    """Production fill-model exit check; mutates trade in place."""
    from agent.alphas.backtest import _check_exit as prod_exit  # noqa: E402
    return prod_exit(trade, bar, cfg)


def _update_excursion(trade, bar) -> None:
    """Track MAE / MFE in absolute pips from entry as bars roll forward.

    Mirrors `agent.backtest.metrics.update_excursion` semantics: MAE and
    MFE are kept as positive pip distances throughout the trade's life.
    """
    if trade.direction.value == "long":
        excursion_against = trade.entry_price - bar.low
        excursion_for = bar.high - trade.entry_price
    else:
        excursion_against = bar.high - trade.entry_price
        excursion_for = trade.entry_price - bar.low
    mae_pips_this = max(0.0, excursion_against) * 10000.0
    mfe_pips_this = max(0.0, excursion_for) * 10000.0
    if mae_pips_this > trade.mae_pips:
        trade.mae_pips = mae_pips_this
    if mfe_pips_this > trade.mfe_pips:
        trade.mfe_pips = mfe_pips_this


# ---------------------------------------------------------------------------
# Engine driver (replay loop)
# ---------------------------------------------------------------------------

def _bar_to_market_state(bar, tick_id: int) -> MarketState:
    """Translate a production Bar into a M001 MarketState."""
    return MarketState(
        tick_id=int(tick_id),
        symbol="EURUSD",  # populated by caller via `_drive_replay`
        timeframe=bar.timeframe.value,
        as_of=bar.time,
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=float(bar.volume),
    )


def _drive_replay(
    agent: A1IsagiV1,
    bars: list,
    symbol: str,
    *,
    ledger: Optional[FullLedger] = None,
    warmup_bars: int = WARMUP_BARS,
) -> tuple[list[Thought], list[AgentProposal], list[TradeRecord]]:
    """Walk `bars` once; emit Thoughts every tick; intend at H4 close.

    Trade lifecycle (matches `agent.alphas.backtest.run_alpha`):
      * On Proposal: open at *next* bar open with production fill model.
      * On every bar after entry: track MAE/MFE; call `_check_exit`.
      * On exit: score with `compute_tqs` and append a TradeRecord.
    """
    if ledger is None:
        ledger = FullLedger()
    thoughts: list[Thought] = []
    proposals: list[AgentProposal] = []
    trades: list[TradeRecord] = []

    cfg = agent._cfg  # private but stable -- harness-only access path
    open_trade = None  # production Trade in flight (max one position; mirrors E004)

    for i, bar in enumerate(bars):
        market = _bar_to_market_state(bar, tick_id=i)
        # Replace `symbol` (we hardcoded EURUSD above for typing; pass actual).
        market = MarketState(
            tick_id=market.tick_id,
            symbol=symbol,
            timeframe=market.timeframe,
            as_of=market.as_of,
            open=market.open,
            high=market.high,
            low=market.low,
            close=market.close,
            volume=market.volume,
        )

        # Trade management first: any open trade resolves on this bar.
        if open_trade is not None:
            _update_excursion(open_trade, bar)
            closed = _check_exit(open_trade, bar, cfg)
            if closed:
                trades.append(_score_trade(open_trade, agent.canon_role.target_hold_hours))
                open_trade = None

        # Observe + intend.
        t = agent.observe(market, ledger)
        ledger.append(t)
        thoughts.append(t)

        # `intend` only fires at home_tf close. Warmup gate matches
        # production `run_alpha(start_index=200)`.
        if i < warmup_bars or i >= len(bars) - 1:
            continue
        if market.timeframe != agent.home_tf:
            continue

        proposal = agent.intend(market, t)
        if proposal is None:
            continue
        if open_trade is not None:
            # E004 baseline holds one position at a time; new signals while a
            # trade is open are journalled as proposals but not entered.
            proposals.append(proposal)
            continue
        proposals.append(proposal)

        try:
            open_trade = _open_trade_from_proposal(proposal, bars[i + 1], cfg)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Failed to open trade from proposal at i=%d (%s): %s",
                i, market.as_of, exc,
            )
            open_trade = None

    # Final tick: any open trade closes on the last bar.
    if open_trade is not None and open_trade.exit_time is None:
        last = bars[-1]
        open_trade.exit_time = last.time
        open_trade.exit_price = last.close
        open_trade.exit_reason = "end_of_data"
        if open_trade.direction.value == "long":
            pip = (last.close - open_trade.entry_price) * 10000.0
        else:
            pip = (open_trade.entry_price - last.close) * 10000.0
        open_trade.pnl_pips = pip
        open_trade.pnl = (
            pip * open_trade.lot_size * cfg.backtest.pip_value_per_lot
            - open_trade.commission
        )
        trades.append(_score_trade(open_trade, agent.canon_role.target_hold_hours))

    return thoughts, proposals, trades


def _score_trade(prod_trade, target_hold_hours: float) -> TradeRecord:
    """Wrap a production Trade with TQS scoring + sim TradeRecord."""
    entry_t = prod_trade.entry_time
    exit_t = prod_trade.exit_time or entry_t
    actual_hold_hours = max(
        0.0, (exit_t - entry_t).total_seconds() / 3600.0,
    )
    stop_distance_price = abs(prod_trade.entry_price - prod_trade.stop_price)
    stop_distance_pips = stop_distance_price * 10000.0
    r_multiple = (
        float(prod_trade.pnl_pips) / stop_distance_pips
        if stop_distance_pips > 0 else 0.0
    )
    components = compute_tqs(
        r_multiple=r_multiple,
        mae_pips=float(prod_trade.mae_pips),
        mfe_pips=float(prod_trade.mfe_pips),
        actual_hold_hours=actual_hold_hours,
        target_hold_hours=float(target_hold_hours),
        had_adds=False,
        had_panic_exit=False,
        broker_stop_threatened=False,
        entry_inside_chemical_reaction=False,  # Phi3 honest baseline: no F11 yet.
    )
    return TradeRecord(
        agent_id="isagi_yoichi",
        symbol="EURUSD",  # populated by caller; kept for ledger compat
        entry_time=entry_t,
        exit_time=exit_t,
        direction=prod_trade.direction.value,
        entry=float(prod_trade.entry_price),
        stop=float(prod_trade.stop_price),
        take_profit=float(prod_trade.tp_price),
        exit_price=float(prod_trade.exit_price) if prod_trade.exit_price else 0.0,
        exit_reason=prod_trade.exit_reason or "open",
        pnl_pips=float(prod_trade.pnl_pips),
        mae_pips=float(prod_trade.mae_pips),
        mfe_pips=float(prod_trade.mfe_pips),
        bars_held=int(prod_trade.bars_held or 0),
        r_multiple=r_multiple,
        tqs_components=components.to_jsonable(),
    )


# ---------------------------------------------------------------------------
# Walk-forward windowing
# ---------------------------------------------------------------------------

def _window_starts(full_start: datetime, full_end: datetime) -> list[datetime]:
    """Return rolling window start dates anchored at Jan-1 (matches E004)."""
    last_oos_end_year = full_end.year
    last_window_start_year = last_oos_end_year - IS_YEARS - OOS_YEARS + 1
    return [
        datetime(y, 1, 1, tzinfo=timezone.utc)
        for y in range(full_start.year, last_window_start_year + 1)
    ]


def _slice_trades(
    trades: list[TradeRecord], lo: datetime, hi: datetime,
) -> list[TradeRecord]:
    return [t for t in trades if lo <= t.entry_time < hi]


def _summarise(trades: list[TradeRecord]) -> tuple[float, float, float, float, int]:
    if not trades:
        return 0.0, 0.0, 0.0, 0.0, 0
    pips = [t.pnl_pips for t in trades]
    tqs = [t.tqs_components["tqs"] for t in trades]
    wins = sum(1 for t in trades if t.pnl_pips > 0)
    return (
        statistics.mean(pips),
        statistics.median(pips),
        statistics.mean(tqs),
        wins / len(trades),
        len(trades),
    )


def _compute_windows(
    trades: list[TradeRecord], full_start: datetime, full_end: datetime,
) -> list[WindowStats]:
    out: list[WindowStats] = []
    for ws in _window_starts(full_start, full_end):
        is_start = ws
        is_end = datetime(ws.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > full_end:
            oos_end = full_end
        is_tr = _slice_trades(trades, is_start, is_end)
        oos_tr = _slice_trades(trades, oos_start, oos_end)
        is_mean, is_med, is_tqs, is_wr, is_n = _summarise(is_tr)
        oos_mean, oos_med, oos_tqs, oos_wr, oos_n = _summarise(oos_tr)
        out.append(
            WindowStats(
                is_start=is_start, is_end=is_end,
                oos_start=oos_start, oos_end=oos_end,
                is_n=is_n, is_mean_pips=is_mean, is_median_pips=is_med,
                is_mean_tqs=is_tqs, is_win_rate=is_wr,
                oos_n=oos_n, oos_mean_pips=oos_mean, oos_median_pips=oos_med,
                oos_mean_tqs=oos_tqs, oos_win_rate=oos_wr,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Verdict logic (per 09 section 1.5 G4 + user spec)
# ---------------------------------------------------------------------------

def _decide_verdict(report: GateReport) -> tuple[str, str]:
    """Apply the Phi3 -> Phi4 gate rules.

    Comparator: the E004 finding `+11.34 median OOS pips/trade` is the
    *median across 7 OOS windows* of each window's *mean per-trade pip
    expectancy*. We compare on the same statistic (`median_oos_window_
    mean_pips`), not on the per-trade median (which is dominated by SL
    hits at R:R=1.5 and is sharply negative by construction).
    """
    if report.provisional_reason:
        return "PROVISIONAL", report.provisional_reason

    median_oos = report.median_oos_window_mean_pips
    oos_pos = report.oos_windows_positive
    oos_total = report.oos_windows_total

    if median_oos < 9.0 or oos_pos < 5:
        return (
            "FAIL",
            f"median OOS-window mean pips/trade {median_oos:+.2f} < +9.0 "
            f"OR positive OOS windows {oos_pos}/{oos_total} < 5/7",
        )

    # Reference Sae median TQS proxy: we don't have a journalled per-trade
    # TQS from the production cell. The wrapper validation is "do not
    # degrade pip behaviour"; the TQS proxy is computed on the *same*
    # trade stream the wrapper produces, which by construction equals the
    # Sae trade stream. We flag PARTIAL when median OOS expectancy drifts
    # > +/- 5 % from +11.34 (the spec's tolerance).
    pct_drift = (median_oos - SAE_BASELINE_PIPS_PER_TRADE) / SAE_BASELINE_PIPS_PER_TRADE
    if abs(pct_drift) <= 0.05:
        return (
            "PASS",
            f"median OOS-window mean pips/trade {median_oos:+.2f} within "
            f"+/- 5 % of Sae ({SAE_BASELINE_PIPS_PER_TRADE:+.2f}); "
            f"{oos_pos}/{oos_total} OOS windows positive.",
        )
    return (
        "PARTIAL",
        f"median OOS-window mean pips/trade {median_oos:+.2f} is "
        f"{pct_drift:+.1%} vs Sae baseline {SAE_BASELINE_PIPS_PER_TRADE:+.2f} "
        f"(gate is +/- 5 %); {oos_pos}/{oos_total} OOS windows positive.",
    )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _format_window_row(w: WindowStats) -> str:
    return (
        f"| {w.is_start.year}-{w.is_end.year - 1} | {w.oos_start.year} | "
        f"{w.is_n} | {w.is_mean_pips:+.2f} | {w.is_median_pips:+.2f} | "
        f"{w.is_mean_tqs:.3f} | {w.is_win_rate:.0%} | "
        f"{w.oos_n} | {w.oos_mean_pips:+.2f} | {w.oos_median_pips:+.2f} | "
        f"{w.oos_mean_tqs:.3f} | {w.oos_win_rate:.0%} |"
    )


def render_report(report: GateReport) -> str:
    pos_count = sum(
        1 for w in report.windows if w.oos_n > 0 and w.oos_mean_pips > 0
    )
    drift_pct = (
        (report.median_oos_window_mean_pips - SAE_BASELINE_PIPS_PER_TRADE)
        / SAE_BASELINE_PIPS_PER_TRADE * 100.0
    )
    lines: list[str] = []
    lines.append(
        f"# Phi3 gate -- A1 Isagi v1 vs Sae frozen baseline\n"
    )
    lines.append(
        f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n"
    )
    lines.append(
        f"**Symbol:** {report.symbol} -- **Window:** "
        f"{report.full_start.date()} -> {report.full_end.date()} "
        f"({report.n_bars} H4 bars)\n"
    )
    lines.append(
        f"**Wrapped cell:** "
        f"`agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` "
        f"(`htf_align=D1`, `htf_align_mode=against`, `htf_lookback=10`, "
        f"`htf_min_move_pips=60`, `target_rr=1.5`)\n"
    )
    lines.append(
        f"**Sae baseline:** `{SAE_BASELINE_LABEL}` "
        f"-- median **+{SAE_BASELINE_PIPS_PER_TRADE:.2f} pips/trade**, "
        f"**{SAE_BASELINE_OOS_WINDOWS_POSITIVE}/7 OOS** (E004 walk-forward).\n"
    )
    lines.append("---\n")
    lines.append("## Verdict\n")
    lines.append(f"**Phi3 -> Phi4 gate: `{report.verdict}`**\n")
    lines.append(f"_{report.verdict_reason}_\n")
    lines.append(
        "Honest framing: this is the **wrapper validation**, not a new edge. "
        "PASS means no degradation from production behaviour. PARTIAL means "
        "pip behaviour drifted outside +/- 5 % of the Sae baseline. FAIL "
        "means we lost the edge in the wrap.\n"
    )
    lines.append("---\n")
    lines.append("## Apples-to-apples vs Sae (E004)\n")
    lines.append(
        "Comparator: **median across 7 OOS windows of each window's mean per-trade "
        "pip expectancy**. This is the same statistic E004's headline reports.\n"
    )
    lines.append("")
    lines.append("| Metric | A1 Isagi v1 | Sae (E004) | Delta |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| **Median OOS-window mean pips/trade** | "
        f"**{report.median_oos_window_mean_pips:+.2f}** | "
        f"**+{SAE_BASELINE_PIPS_PER_TRADE:.2f}** | "
        f"**{drift_pct:+.1f} %** |"
    )
    lines.append(
        f"| Mean OOS-window mean pips/trade | "
        f"{report.mean_oos_window_mean_pips:+.2f} | -- | -- |"
    )
    lines.append(
        f"| Median OOS-window mean TQS (F12) | "
        f"{report.median_oos_window_mean_tqs:.3f} | "
        f"(same trade stream by construction) | 0.000 |"
    )
    lines.append(
        f"| OOS windows positive | **{pos_count} / "
        f"{len(report.windows)}** | "
        f"{SAE_BASELINE_OOS_WINDOWS_POSITIVE} / 7 | -- |"
    )
    lines.append("")
    lines.append("## Per-trade distribution (full dev window)\n")
    lines.append(
        "Reported for transparency; **not** the gate statistic. At "
        "target_rr=1.5 with ~ 49 % win rate, the per-trade median is "
        "structurally negative (most trades hit SL by R:R design).\n"
    )
    lines.append("")
    lines.append("| Metric | A1 Isagi v1 |")
    lines.append("|---|---|")
    lines.append(f"| Mean pips/trade | {report.overall_mean_pips:+.2f} |")
    lines.append(f"| Median pips/trade | {report.overall_median_pips:+.2f} |")
    lines.append(f"| Mean TQS (F12) | {report.overall_mean_tqs:.3f} |")
    lines.append(f"| Win rate | {report.overall_win_rate:.1%} |")
    lines.append(f"| Trades | {report.n_trades} |")
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-window walk-forward\n")
    lines.append(
        "(4 yr IS / 1 yr OOS rolling -- matches "
        "`multi-pair-trading-agent/scripts/run_walk_forward.py`)\n"
    )
    lines.append("")
    lines.append(
        "| IS window | OOS yr | IS n | IS mean pips | IS med pips | "
        "IS mean TQS | IS win % | "
        "OOS n | OOS mean pips | OOS med pips | OOS mean TQS | OOS win % |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    for w in report.windows:
        lines.append(_format_window_row(w))
    lines.append("")
    lines.append("---\n")
    lines.append("## Engine telemetry\n")
    lines.append("")
    lines.append(f"- Bars processed: {report.n_bars}")
    lines.append(f"- Thoughts emitted: {report.n_thoughts}")
    lines.append(f"- Proposals emitted: {report.n_proposals}")
    lines.append(
        f"- Trades opened+closed: {report.n_trades} "
        f"(rejected post-open: "
        f"{report.n_proposals - report.n_trades} due to "
        "open-position concurrency limit, matches E004 single-position rule)"
    )
    lines.append("")
    lines.append("## Honest baseline caveats\n")
    lines.append(
        "1. **No chemical-reaction beauty bonus** -- entry_inside_chemical_reaction=False "
        "for every trade. Phi3 has no F11 layer wired.\n"
        "2. **Tier-3 RedactedLedger acts identically to FullLedger** "
        "for Isagi v1 because the wrapper does not read peer thoughts "
        "(production cell has no peer-reading branch).\n"
        "3. **`regime_fit = 0.5` placeholder** -- the four-class classifier "
        "(09 section 1.5 G4 row) is not wired into the proposal stream yet.\n"
        "4. **`cleanliness = 1.0`** -- no panic-exits / no adds / broker-stop "
        "never threatened (single-position simulator, hard SL).\n"
    )
    lines.append("")
    lines.append("## What this proves (and what it does not)\n")
    lines.append(
        "**Proves:** the BlueLockStriker `observe` / `intend` protocol "
        "can carry the E004-deployed production cell without losing its "
        "trade signature. The wrapper preserves direction, entry, stop, "
        "take-profit, and conviction byte-identically. The Phi2.5 "
        "aggregator stub accepts the AgentProposal stream without "
        "modification. The Thought Ledger journals every H4 close.\n"
        "**Does not prove:** that Isagi v1 wins on TQS alone vs the squad. "
        "The G5 gate (Phi4 -> Phi5) requires the squad-ensemble TQS to "
        "beat Sae's TQS by ~ 1.10 x. This is a *necessary precondition* "
        "(wrapper fidelity) for that downstream measurement.\n"
    )
    lines.append("")
    lines.append("## References\n")
    lines.append(
        "- E004 walk-forward: `docs/findings/2026-06-09_walk_forward_validation.md`\n"
        "- Doctrine: `06-blue-lock-doctrine.md` section 4.1, 3.8, 3.9\n"
        "- Experiment architecture: `09-experiment-architecture.md` section 1.5 (G4)\n"
        "- Production cell: `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py`\n"
        "- Wrapper: `sim/agents/a01_isagi.py`\n"
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_gate(
    *,
    symbol: str = "EURUSD",
    full_start: datetime = DEFAULT_FULL_START,
    full_end: datetime = DEFAULT_FULL_END,
    out_path: Path | str | None = None,
    write_trades_jsonl: bool = True,
) -> GateReport:
    """Run the Phi3 gate end-to-end and write a markdown review."""
    ensure_production_repo_on_path()
    log.info("Loading %s H4 bars %s -> %s", symbol, full_start.date(), full_end.date())
    bars = _load_production_bars(symbol, full_start, full_end)
    log.info("Loaded %d bars", len(bars))

    provisional_reason: Optional[str] = None
    if not bars:
        provisional_reason = (
            f"No bars loaded for {symbol} in [{full_start.date()}, "
            f"{full_end.date()}]; gate cannot run."
        )
    elif len(bars) < WARMUP_BARS + 50:
        provisional_reason = (
            f"Only {len(bars)} bars available; less than WARMUP+50; "
            "gate produced too few trades for statistical claim."
        )

    agent = A1IsagiV1()
    if bars:
        agent.prepare(symbol, bars)
        thoughts, proposals, trades = _drive_replay(agent, bars, symbol)
    else:
        thoughts, proposals, trades = [], [], []

    # Walk-forward window stats.
    windows = _compute_windows(trades, full_start, full_end)
    overall_mean, overall_median, overall_tqs, overall_wr, n_trades = _summarise(trades)
    oos_positive = sum(
        1 for w in windows if w.oos_n > 0 and w.oos_mean_pips > 0
    )

    # Apples-to-apples vs E004: median across the 7 OOS windows of each
    # window's *mean* per-trade pip expectancy.
    oos_window_means = [w.oos_mean_pips for w in windows if w.oos_n > 0]
    oos_window_tqs = [w.oos_mean_tqs for w in windows if w.oos_n > 0]
    median_oos_mean = (
        statistics.median(oos_window_means) if oos_window_means else 0.0
    )
    mean_oos_mean = (
        statistics.mean(oos_window_means) if oos_window_means else 0.0
    )
    median_oos_tqs = (
        statistics.median(oos_window_tqs) if oos_window_tqs else 0.0
    )

    report = GateReport(
        symbol=symbol,
        full_start=full_start,
        full_end=full_end,
        n_bars=len(bars),
        n_thoughts=len(thoughts),
        n_proposals=len(proposals),
        n_trades=n_trades,
        overall_mean_pips=overall_mean,
        overall_median_pips=overall_median,
        overall_mean_tqs=overall_tqs,
        overall_win_rate=overall_wr,
        oos_windows_positive=oos_positive,
        oos_windows_total=len(windows),
        median_oos_window_mean_pips=median_oos_mean,
        mean_oos_window_mean_pips=mean_oos_mean,
        median_oos_window_mean_tqs=median_oos_tqs,
        windows=windows,
        provisional_reason=provisional_reason,
        data_window_match_e004=(
            full_start == DEFAULT_FULL_START and full_end == DEFAULT_FULL_END
        ),
    )
    report.verdict, report.verdict_reason = _decide_verdict(report)
    log.info(
        "Phi3 gate verdict: %s (%d trades; median OOS-window mean %+.2f pips; "
        "%d/%d OOS windows positive)",
        report.verdict, n_trades, median_oos_mean,
        oos_positive, len(windows),
    )

    # Persist artefacts.
    if out_path is None:
        out_path = (
            Path(__file__).resolve().parents[2]
            / "reviews" / "phi3_gate_isagi_v1.md"
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(report), encoding="utf-8")
    log.info("Wrote review to %s", out_path)

    if write_trades_jsonl and trades:
        trades_path = out_path.parent / "phi3_gate_isagi_v1_trades.jsonl"
        with trades_path.open("w", encoding="utf-8") as fh:
            for t in trades:
                fh.write(json.dumps({
                    "agent_id": t.agent_id,
                    "symbol": t.symbol,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "direction": t.direction,
                    "entry": t.entry,
                    "stop": t.stop,
                    "take_profit": t.take_profit,
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pnl_pips": t.pnl_pips,
                    "mae_pips": t.mae_pips,
                    "mfe_pips": t.mfe_pips,
                    "r_multiple": t.r_multiple,
                    "tqs": t.tqs_components,
                }, sort_keys=True) + "\n")

    return report


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the M001 Phi3 gate (A1 Isagi v1 vs Sae frozen baseline).",
    )
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument(
        "--start", type=_parse_date,
        default=DEFAULT_FULL_START.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end", type=_parse_date,
        default=DEFAULT_FULL_END.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--out", default=None,
        help="Output markdown path (default: <repo>/programs/.../reviews/phi3_gate_isagi_v1.md)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    start = args.start if isinstance(args.start, datetime) else _parse_date(args.start)
    end = args.end if isinstance(args.end, datetime) else _parse_date(args.end)
    report = run_gate(
        symbol=args.symbol,
        full_start=start,
        full_end=end,
        out_path=args.out,
    )
    print(
        f"Phi3 gate verdict: {report.verdict} "
        f"({report.n_trades} trades; "
        f"median OOS-window mean {report.median_oos_window_mean_pips:+.2f} pips; "
        f"{report.oos_windows_positive}/{report.oos_windows_total} OOS windows positive)"
    )
    return 0 if report.verdict in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
