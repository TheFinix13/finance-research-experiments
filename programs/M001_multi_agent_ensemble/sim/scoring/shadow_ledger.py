"""Phase U -- Shadow Ledger (counterfactual per-proposal evaluation).

Doctrine 06 v0.5 sec 4.1a extension (2026-07-01 amendment). The
executed trade record captures who WON the aggregator; the shadow
ledger captures what every LOSING proposal WOULD HAVE BEEN, run through
the same fill/exit engine in isolation on its target symbol. Together
they let us separate two questions that Phi4/G7 currently conflate:

1. "Did this agent see a good setup?"  <- shadow-TQS answers this.
2. "Did the squad's routing let them act on it?"  <- executed-TQS.

## Blue Lock frame (canon reference)

In the manga's 2nd/3rd selection matches, players who READ plays that
ended in goals get scouting credit even when they weren't the one who
scored. Bachira's misdirection at the 3rd selection, Nikki's read of
Sae's backspin at U20 -- reading plays is a measurable skill separate
from being the striker who receives the pass. The shadow ledger is
exactly that scouting record for agents whose proposals are
consistently rejected by the aggregator.

## Design

- **`shadow_evaluate_proposal(proposal, symbol_bars, i_open, cfg,
  *, max_lookahead_bars, target_hold_hours) -> ShadowTradeRecord`**
  Runs one proposal through the production fill/exit engine in
  isolation. Never mutates any real trade state. Returns None only
  when the fill itself fails (e.g. gapped open past the SL).
- **`ShadowTradeRecord`** = full `TradeRecord` shape + shadow-only
  fields: `is_shadow`, `rejection_reason`, `proposal_tick_id`,
  `entry_efficiency`, `exit_efficiency`, `friction_ratio`.
- **`aggregate_shadow_by_agent(records) -> dict[str, ShadowAggregate]`**
  Per-agent scouting bit vector: mean shadow-TQS, mean R-multiple,
  win rate, reproducibility CV across windows, correlation between
  each agent's shadow-TQS and executed-TQS on the accepted-trade
  set (systematic-bias check).

## Statistical honesty

- Shadow-TQS is **diagnostic-only** for v1. It informs Phase T Rin
  evolution + Phi5 Arm 4 K=2 promotion; it never itself moves an
  agent's v1 bit vector. §11 amendment on the G7 PROTOCOL
  formalises this.
- Reported alongside executed-TQS on every gate so a systematic
  overstatement (e.g. shadow-Bachira 0.50 vs executed-Bachira 0.38)
  becomes visible and correctable.
- Shadow trades never face the aggregator's R6 per-symbol total-risk
  cap or R4 concentration cap -- they're isolated. This is the
  known upward bias; we correct for it via the shadow-executed
  correlation on agents who DO execute, then apply the correction
  to shadow-only agents.

## Related literature (quality-of-trade metrics we compose from)

- Van Tharp (1998) -- R-multiple expectancy. Baked into `r_multiple`.
- Sweeney (1996), Kaufman (2013) -- MAE/MFE efficiency. Baked into
  the existing `compute_efficiency`. We add explicit
  `entry_efficiency = 1 - MAE / (MAE + initial_risk)` and
  `exit_efficiency = pnl_pips / max(MFE_pips, 1)` for cleaner
  attribution.
- Almgren-Chriss (2001) -- implementation shortfall. We approximate
  as `friction_ratio = commission / max(abs(pnl), 1)` since the
  fill model doesn't model market impact for retail forex.
- Sortino (1994) -- downside deviation. Applied at the agent-level
  aggregate, not per-trade.
"""
from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim.core.types import AgentProposal
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    TradeRecord,
    _check_exit,
    _open_trade_from_proposal,
    _score_trade,
    _update_excursion,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record types
# ---------------------------------------------------------------------------

@dataclass
class ShadowTradeRecord:
    """One counterfactual trade -- what a rejected proposal would have been.

    Mirrors ``TradeRecord`` field-for-field so downstream reporting can
    treat shadow and executed trades uniformly, then adds three shadow-
    only fields for attribution + three research-grade quality metrics
    on top of the existing TQS decomposition.
    """
    agent_id: str
    symbol: str
    entry_time: Any
    exit_time: Any
    direction: str
    entry: float
    stop: float
    take_profit: float
    exit_price: float
    exit_reason: str
    pnl_pips: float
    mae_pips: float
    mfe_pips: float
    bars_held: int
    r_multiple: float
    tqs_components: dict

    # Shadow-only provenance -- lets us join back to the exact proposal.
    is_shadow: bool = True
    proposal_tick_id: int = 0
    rejection_reason: Optional[str] = None

    # F19/F20 source-fields mirror TradeRecord's extension.
    source_conviction: float | None = None
    source_regime_fit: float | None = None
    source_sl_pips: float | None = None
    source_atr_pips: float | None = None
    source_h1_swing_pips: float | None = None

    # Research-grade per-trade quality metrics (Phase U additions).
    entry_efficiency: float | None = None   # 1 - MAE / (MAE + initial_risk)
    exit_efficiency: float | None = None    # pnl_pips / max(MFE, 1)
    friction_ratio: float | None = None     # commission / max(|pnl|, 1)


@dataclass
class ShadowAggregate:
    """Per-agent scouting summary of the shadow ledger.

    Reported alongside the executed-side C1-C6 bit vector. Doctrine
    v0.5 §11 amendment (Phase U): these numbers are diagnostic-only
    until Phi5 Arm 4 (K=2 multi-position) lands.

    Key attribution split (2026-07-01 refinement): shadow-TQS is
    partitioned into two subsets:

    - ``mean_shadow_tqs_when_accepted`` -- shadow score for the
      agent's proposals that ALSO won the aggregator. Equals
      executed-TQS by construction (same simulation), so this is a
      calibration proof of the shadow simulator, not a new signal.
    - ``mean_shadow_tqs_when_rejected`` -- shadow score for the
      agent's proposals that LOST the aggregator tie-break. THIS is
      the alpha-attribution signal. Compare to
      ``mean_shadow_tqs_when_accepted`` for the same agent to see
      whether their rejected proposals are systematically worse (the
      aggregator did its job) or comparable (a crowding-out routing
      bug, e.g. Rin post-Phase-S).
    """
    agent_id: str
    n_shadow_trades: int
    n_shadow_wins: int
    mean_shadow_tqs: float
    mean_shadow_r_multiple: float
    win_rate: float
    # Reproducibility signals -- per-window and per-symbol dispersion.
    per_window_mean_tqs: dict[int, float] = field(default_factory=dict)
    per_window_cv_tqs: float = 0.0
    per_symbol_mean_tqs: dict[str, float] = field(default_factory=dict)
    # Attribution split -- the actual alpha signal for Phase T + Phi5.
    n_shadow_accepted: int = 0
    n_shadow_rejected: int = 0
    mean_shadow_tqs_when_accepted: float | None = None
    mean_shadow_tqs_when_rejected: float | None = None
    # Legacy calibration field -- pearson between shadow and executed on
    # paired ticks. Always ~1.0 by construction (kept for backwards
    # compatibility with the first Phase U dry-run; not a real signal).
    shadow_executed_pearson: float | None = None
    n_paired_ticks: int = 0
    # Aggregated quality dispersion.
    mean_entry_efficiency: float | None = None
    mean_exit_efficiency: float | None = None
    mean_friction_ratio: float | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "n_shadow_trades": int(self.n_shadow_trades),
            "n_shadow_wins": int(self.n_shadow_wins),
            "mean_shadow_tqs": float(self.mean_shadow_tqs),
            "mean_shadow_r_multiple": float(self.mean_shadow_r_multiple),
            "win_rate": float(self.win_rate),
            "per_window_mean_tqs": {
                int(k): float(v) for k, v in self.per_window_mean_tqs.items()
            },
            "per_window_cv_tqs": float(self.per_window_cv_tqs),
            "per_symbol_mean_tqs": {
                str(k): float(v) for k, v in self.per_symbol_mean_tqs.items()
            },
            "n_shadow_accepted": int(self.n_shadow_accepted),
            "n_shadow_rejected": int(self.n_shadow_rejected),
            "mean_shadow_tqs_when_accepted": (
                None if self.mean_shadow_tqs_when_accepted is None
                else float(self.mean_shadow_tqs_when_accepted)
            ),
            "mean_shadow_tqs_when_rejected": (
                None if self.mean_shadow_tqs_when_rejected is None
                else float(self.mean_shadow_tqs_when_rejected)
            ),
            "shadow_executed_pearson": (
                None if self.shadow_executed_pearson is None
                else float(self.shadow_executed_pearson)
            ),
            "n_paired_ticks": int(self.n_paired_ticks),
            "mean_entry_efficiency": (
                None if self.mean_entry_efficiency is None
                else float(self.mean_entry_efficiency)
            ),
            "mean_exit_efficiency": (
                None if self.mean_exit_efficiency is None
                else float(self.mean_exit_efficiency)
            ),
            "mean_friction_ratio": (
                None if self.mean_friction_ratio is None
                else float(self.mean_friction_ratio)
            ),
        }


# ---------------------------------------------------------------------------
# Single-proposal shadow evaluation
# ---------------------------------------------------------------------------

# Maximum bars we simulate a shadow trade forward before force-closing at
# end_of_data. Aligned with the agents' target_hold_hours ranges (H4 * 24
# = 4 days) so we don't leave zombie trades open indefinitely.
DEFAULT_MAX_LOOKAHEAD_BARS: int = 30


def shadow_evaluate_proposal(
    proposal: AgentProposal,
    symbol_bars: list,
    i_open: int,
    cfg: Any,
    *,
    max_lookahead_bars: int = DEFAULT_MAX_LOOKAHEAD_BARS,
    target_hold_hours: float = 24.0,
    rejection_reason: Optional[str] = None,
) -> Optional[ShadowTradeRecord]:
    """Simulate one proposal to close in isolation on its symbol.

    ``symbol_bars`` is the full production Bar list for the proposal's
    symbol; ``i_open`` is the index of the bar AT WHICH THE PROPOSAL
    FIRED. The shadow trade opens on ``symbol_bars[i_open + 1]``
    (next-bar-open, same as the executed-side driver) and walks forward
    until TP/SL hit or ``max_lookahead_bars`` reached.

    Never mutates the real ``open_trades`` map or the executed
    TradeRecord list; produces a stand-alone ShadowTradeRecord.

    Returns None if:

    - The next bar doesn't exist (proposal was on the last bar).
    - ``_open_trade_from_proposal`` raises (production fill model
      rejected the entry, e.g. gapped past stop).

    Callers should treat None as "shadow simulation not possible" and
    NOT count it against the agent -- it's a fill-side failure, not a
    trade-quality failure.
    """
    if i_open + 1 >= len(symbol_bars):
        return None

    next_bar = symbol_bars[i_open + 1]
    try:
        prod_trade = _open_trade_from_proposal(proposal, next_bar, cfg)
    except Exception as exc:      # noqa: BLE001 -- production API is broad
        log.debug(
            "shadow_evaluate: _open_trade failed for %s at i=%d: %s",
            proposal.agent_id, i_open, exc,
        )
        return None

    # Walk forward. `_check_exit` mutates the trade in place. We stop
    # when the trade closes OR we hit `max_lookahead_bars`.
    j_start = i_open + 1
    j_end = min(len(symbol_bars), j_start + max_lookahead_bars)
    for j in range(j_start, j_end):
        bar = symbol_bars[j]
        _update_excursion(prod_trade, bar)
        if _check_exit(prod_trade, bar, cfg):
            break

    # If the trade never closed within lookahead, force-close at the
    # last bar in the window (matches the executed-side "end_of_data"
    # convention).
    if prod_trade.exit_time is None:
        last = symbol_bars[j_end - 1] if j_end > j_start else next_bar
        prod_trade.exit_time = last.time
        prod_trade.exit_price = last.close
        prod_trade.exit_reason = "end_of_lookahead"
        if prod_trade.direction.value == "long":
            pip = (last.close - prod_trade.entry_price) * 10000.0
        else:
            pip = (prod_trade.entry_price - last.close) * 10000.0
        prod_trade.pnl_pips = pip
        prod_trade.pnl = (
            pip * prod_trade.lot_size * cfg.backtest.pip_value_per_lot
            - prod_trade.commission
        )

    tr = _score_trade(prod_trade, target_hold_hours=target_hold_hours)

    # Compute additional research-grade quality metrics.
    initial_risk_pips = float(abs(proposal.entry - proposal.stop)) * 10000.0
    entry_eff = _entry_efficiency(tr.mae_pips, initial_risk_pips)
    exit_eff = _exit_efficiency(tr.pnl_pips, tr.mfe_pips)
    friction = _friction_ratio(
        commission=float(getattr(prod_trade, "commission", 0.0)),
        pnl=float(getattr(prod_trade, "pnl", tr.pnl_pips)),
    )

    return ShadowTradeRecord(
        agent_id=proposal.agent_id,
        symbol=proposal.symbol,
        entry_time=tr.entry_time,
        exit_time=tr.exit_time,
        direction=tr.direction,
        entry=tr.entry,
        stop=tr.stop,
        take_profit=tr.take_profit,
        exit_price=tr.exit_price,
        exit_reason=tr.exit_reason,
        pnl_pips=tr.pnl_pips,
        mae_pips=tr.mae_pips,
        mfe_pips=tr.mfe_pips,
        bars_held=tr.bars_held,
        r_multiple=tr.r_multiple,
        tqs_components=tr.tqs_components,
        is_shadow=True,
        proposal_tick_id=int(proposal.tick_id),
        rejection_reason=rejection_reason,
        source_conviction=float(proposal.conviction),
        source_regime_fit=float(proposal.regime_fit),
        source_sl_pips=initial_risk_pips,
        source_atr_pips=proposal.rationale.get("atr_pips") if proposal.rationale else None,
        source_h1_swing_pips=(
            proposal.rationale.get("h1_swing_pips") if proposal.rationale else None
        ),
        entry_efficiency=entry_eff,
        exit_efficiency=exit_eff,
        friction_ratio=friction,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_shadow_by_agent(
    shadow_records: list[ShadowTradeRecord],
    *,
    executed_by_agent_tick: dict[tuple[str, int], float] | None = None,
    window_of_tick: dict[int, int] | None = None,
) -> dict[str, ShadowAggregate]:
    """Per-agent scouting aggregate.

    - ``executed_by_agent_tick`` maps ``(agent_id, tick_id) -> tqs``
      for accepted trades. Passing it enables the systematic-bias
      shadow-vs-executed Pearson correlation.
    - ``window_of_tick`` maps ``tick_id -> window_index`` for the
      walk-forward. Passing it enables reproducibility CV across the
      OOS windows.
    """
    if executed_by_agent_tick is None:
        executed_by_agent_tick = {}
    if window_of_tick is None:
        window_of_tick = {}

    by_agent: dict[str, list[ShadowTradeRecord]] = {}
    for rec in shadow_records:
        by_agent.setdefault(rec.agent_id, []).append(rec)

    out: dict[str, ShadowAggregate] = {}
    for aid, recs in by_agent.items():
        tqs_values = [
            float(r.tqs_components.get("tqs", 0.0)) for r in recs
        ]
        r_values = [float(r.r_multiple) for r in recs]
        wins = sum(1 for r in recs if float(r.pnl_pips) > 0)

        # Per-window TQS averages -- reproducibility signal.
        per_window: dict[int, list[float]] = {}
        for r in recs:
            w = window_of_tick.get(int(r.proposal_tick_id))
            if w is not None:
                per_window.setdefault(int(w), []).append(
                    float(r.tqs_components.get("tqs", 0.0))
                )
        per_window_mean = {
            w: statistics.mean(vals) for w, vals in per_window.items() if vals
        }
        window_cv = _coeff_of_variation(list(per_window_mean.values()))

        # Per-symbol TQS averages -- symbol-robustness signal.
        per_symbol: dict[str, list[float]] = {}
        for r in recs:
            per_symbol.setdefault(r.symbol, []).append(
                float(r.tqs_components.get("tqs", 0.0))
            )
        per_symbol_mean = {
            s: statistics.mean(vals) for s, vals in per_symbol.items() if vals
        }

        # Attribution split: shadow-TQS conditional on aggregator outcome.
        # "accepted" = this agent's proposal on this tick was also
        # executed; "rejected" = shadow-only (aggregator picked someone
        # else). Rejection tag comes from _drive_squad_replay's Phase U
        # wiring.
        accepted_tqs: list[float] = []
        rejected_tqs: list[float] = []
        for r in recs:
            score = float(r.tqs_components.get("tqs", 0.0))
            if r.rejection_reason == "accepted_by_aggregator":
                accepted_tqs.append(score)
            else:
                rejected_tqs.append(score)

        # Shadow-vs-executed correlation on paired (accepted) ticks --
        # calibration proof, not a signal. Expected ~1.0 by construction.
        shadow_series: list[float] = []
        exec_series: list[float] = []
        for r in recs:
            key = (aid, int(r.proposal_tick_id))
            if key in executed_by_agent_tick:
                shadow_series.append(
                    float(r.tqs_components.get("tqs", 0.0))
                )
                exec_series.append(float(executed_by_agent_tick[key]))
        pearson = (
            _pearson(shadow_series, exec_series)
            if len(shadow_series) >= 5 else None
        )

        # Research-grade quality means.
        entry_effs = [
            r.entry_efficiency for r in recs
            if r.entry_efficiency is not None
        ]
        exit_effs = [
            r.exit_efficiency for r in recs
            if r.exit_efficiency is not None
        ]
        friction_ratios = [
            r.friction_ratio for r in recs
            if r.friction_ratio is not None
        ]

        out[aid] = ShadowAggregate(
            agent_id=aid,
            n_shadow_trades=len(recs),
            n_shadow_wins=int(wins),
            mean_shadow_tqs=(
                statistics.mean(tqs_values) if tqs_values else 0.0
            ),
            mean_shadow_r_multiple=(
                statistics.mean(r_values) if r_values else 0.0
            ),
            win_rate=(
                float(wins) / len(recs) if recs else 0.0
            ),
            per_window_mean_tqs=per_window_mean,
            per_window_cv_tqs=window_cv,
            per_symbol_mean_tqs=per_symbol_mean,
            n_shadow_accepted=len(accepted_tqs),
            n_shadow_rejected=len(rejected_tqs),
            mean_shadow_tqs_when_accepted=(
                statistics.mean(accepted_tqs) if accepted_tqs else None
            ),
            mean_shadow_tqs_when_rejected=(
                statistics.mean(rejected_tqs) if rejected_tqs else None
            ),
            shadow_executed_pearson=pearson,
            n_paired_ticks=len(shadow_series),
            mean_entry_efficiency=(
                statistics.mean(entry_effs) if entry_effs else None
            ),
            mean_exit_efficiency=(
                statistics.mean(exit_effs) if exit_effs else None
            ),
            mean_friction_ratio=(
                statistics.mean(friction_ratios) if friction_ratios else None
            ),
        )
    return out


# ---------------------------------------------------------------------------
# Quality metric helpers
# ---------------------------------------------------------------------------

def _entry_efficiency(mae_pips: float, initial_risk_pips: float) -> float:
    """1 - MAE / (MAE + initial_risk).

    In [0, 1]. 1.0 = never went against you (entered at the low for a
    long); 0.0 = trade immediately underwater by more than the initial
    risk. Kaufman/Sweeney entry-quality proxy without needing a
    reference swing range.

    Guards: return 0.5 when both are zero (undefined ratio).
    """
    mae = max(0.0, float(mae_pips))
    risk = max(0.0, float(initial_risk_pips))
    total = mae + risk
    if total <= 0:
        return 0.5
    return float(max(0.0, min(1.0, 1.0 - (mae / total))))


def _exit_efficiency(pnl_pips: float, mfe_pips: float) -> float:
    """pnl / max(MFE, 1).

    In (-inf, 1]. 1.0 = captured the peak; 0.0 = closed at breakeven
    despite peak; negative = closed at loss despite favourable
    excursion. The classic Kaufman exit-quality proxy.
    """
    denom = max(1.0, float(mfe_pips))
    return float(pnl_pips) / denom


def _friction_ratio(commission: float, pnl: float) -> float:
    """|commission| / max(|pnl|, 1).

    A small friction ratio (< 0.05) means execution costs are
    negligible relative to trade result. Large ratios (> 0.20)
    mean the trade barely covered its own costs -- a real signal that
    the setup is too small-edge to trade under sandbox friction.
    """
    denom = max(1.0, abs(float(pnl)))
    return float(abs(commission)) / denom


def _coeff_of_variation(values: list[float]) -> float:
    """CV = stdev / mean. Returns 0 if insufficient data or mean is 0."""
    if len(values) < 2:
        return 0.0
    m = statistics.mean(values)
    if m == 0.0:
        return 0.0
    return float(statistics.stdev(values) / m)


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation of xs and ys. Zero if any std is zero.

    Guards: requires at least 5 paired points (matches the
    aggregate_shadow_by_agent caller's threshold).
    """
    n = len(xs)
    if n < 5 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [v - mx for v in xs]
    dy = [v - my for v in ys]
    sxx = sum(v * v for v in dx)
    syy = sum(v * v for v in dy)
    sxy = sum(a * b for a, b in zip(dx, dy))
    denom = math.sqrt(sxx * syy)
    if denom == 0.0:
        return 0.0
    return float(sxy / denom)


__all__ = [
    "ShadowTradeRecord",
    "ShadowAggregate",
    "DEFAULT_MAX_LOOKAHEAD_BARS",
    "shadow_evaluate_proposal",
    "aggregate_shadow_by_agent",
]
