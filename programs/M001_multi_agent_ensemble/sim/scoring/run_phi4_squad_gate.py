"""Phi4 squad gate evaluation harness -- 4-agent MVP vs Isagi-alone.

The Phi4 -> Phi5 gate (`09-experiment-architecture.md` G5; doctrine
`06-blue-lock-doctrine.md` sec 5) asks whether the 4-agent squad
(Isagi + Nagi + Barou + Kunigami) beats A1 Isagi alone on TQS. The
honest framing: G5 wants squad TQS >= 1.10 x Isagi-alone. PARTIAL is
1.00..1.10. FAIL means the squad LOST edge by adding agents.

What this script does (in order):

1.  Load EURUSD H4 + USDCAD H4 bars 2015-01-01 -> 2025-12-31 from the
    production parquet cache via the cross-repo loader. 11-year span;
    walk-forward 4 yr IS / 1 yr OOS rolling (7 OOS windows, matches
    E004 + Phi3).
2.  Instantiate the four agents:
        A1IsagiV1 (`isagi_yoichi`)           -- E004 wrapper
        A6NagiV1  (`nagi_seishiro`)          -- confluence-only
        A7BarouV1 (`barou_shoei`)            -- USDCAD baseline zone
        A10KunigamiV1 (`kunigami_rensuke`)   -- anti-tilt observer
3.  Interleave the two symbols' bars by timestamp (global tick_id).
    Drive the engine with the two-phase tick order from `engine.py`:
        Phase 1 -- every eligible striker observe()
        Phase 2 -- every eligible striker intend()
    Same-tick reads forbidden by ledger guards (doctrine sec 3.8). The
    chemical-reaction layer therefore lags by one bar at minimum --
    INTENTIONAL per doctrine.
4.  Aggregator (Phi4 squad rule, OVERRIDE of `sim/core/aggregator.py`
    same-direction union): per (symbol, bar), pick the highest-
    conviction proposal. All losers are written to
    `rejected_proposals.jsonl` so the rejection-analysis harness can
    consume them later.
5.  Per-symbol single-position rule (preserves E004 contract): one
    open trade per symbol at a time. New proposals while a trade is
    open are logged but not entered.
6.  Trade lifecycle uses the production fill model
    (`agent.alphas.backtest._open` + `_check_exit`) -- byte-comparable
    to Phi3.
7.  Closed trades are pushed into Kunigami via `record_closed_trade`
    so his loss-streak warning can fire on the SQUAD-wide outcome
    stream (not per-agent).
8.  Score every closed trade with F12 TQS. Slice trades by the 7 OOS
    windows + by agent_id.
9.  ALSO run isolated arms for Nagi + Barou (Tier-2 candidates) on
    a sampled subset of OOS windows (default 3 of 7 for compute
    economy) so F17 DeltaInfo can be reported.
10. Write two reports:
        reviews/phi4_squad_v1.md             -- the gate verdict
        reviews/phi4_isagi_rejection_analysis.md
                                              -- cross-striker rejection lookup

CLI

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate
        [--start 2015-01-01] [--end 2025-12-31]
        [--out-dir reviews/]
        [--delta-info-windows 3]  # how many of the 7 OOS windows to
                                  # use for F17 (default 3, max 7)

Notes
-----

* The harness ONLY runs the two-symbol stream documented above. GBPUSD
  is intentionally skipped -- Barou is USDCAD-only, and the EURUSD
  evidence chain (Isagi/Nagi/Kunigami) is the apples-to-apples
  comparator vs Phi3. GBPUSD would dilute the squad-vs-alone comparison.
* If the squad TQS regresses (FAIL verdict), this script reports FAIL
  honestly. It does NOT silently retune anything. A FAIL is
  information.
"""
from __future__ import annotations

import argparse
import bisect
import json
import logging
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    A10KunigamiV1,
    ClosedTradeRecord,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger,
    RedactedLedger,
    ThoughtLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
    WorkspaceSnapshot,
)
from programs.M001_multi_agent_ensemble.sim.core.sentinel import (
    MIN_LOT,
    SANDBOX_PER_TRADE_RISK_FRAC,
    SentinelContext,
    SentinelDecision,
    evaluate_proposal as sentinel_evaluate_proposal,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.scoring.delta_info import (
    DeltaInfoResult,
    delta_info,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    DEFAULT_FULL_END,
    DEFAULT_FULL_START,
    IS_YEARS,
    OOS_YEARS,
    SAE_BASELINE_PIPS_PER_TRADE,
    WARMUP_BARS,
    TradeRecord,
    _bar_to_market_state,
    _check_exit,
    _load_production_bars,
    _open_trade_from_proposal,
    _score_trade,
    _update_excursion,
    _window_starts,
)
from programs.M001_multi_agent_ensemble.sim.scoring.tqs import compute_tqs

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYMBOLS_DEV: tuple[str, ...] = ("EURUSD", "USDCAD")
ISAGI_ALONE_MEDIAN_OOS_PIPS = 11.04        # from reviews/phi3_gate_isagi_v1.md
ISAGI_ALONE_MEDIAN_OOS_TQS = 0.317         # from reviews/phi3_gate_isagi_v1.md
ISAGI_ALONE_OOS_WINDOWS_POSITIVE = 7       # 7/7

# Gate thresholds per user spec + 09 sec 1.5 G5.
SQUAD_PASS_RATIO = 1.10                    # squad TQS >= 1.10 x isagi-alone
SQUAD_PARTIAL_RATIO = 1.00                 # 1.00 .. 1.10 = PARTIAL
# < 1.00 = FAIL

DEFAULT_DELTA_INFO_WINDOWS = 3             # of 7 OOS; user spec compute floor

# Sandbox account profile locked at $100 / 1:1000 demo per M001 charter.
# Sentinel R1 evaluates min-lot risk against this equity; other R-rules
# also inherit these defaults unless overridden by the caller.
SANDBOX_EQUITY_DOLLARS = 100.0
# pip_value_per_lot = 10.0 in agent/config.py (broker constant, TF-invariant).
# min-lot pip value = pip_value_per_lot * MIN_LOT = 10.0 * 0.01 = 0.10.
SANDBOX_PIP_VALUE_PER_MIN_LOT = 0.10


# ---------------------------------------------------------------------------
# Sentinel journal helpers
# ---------------------------------------------------------------------------

def _sentinel_log_entry(
    *,
    tick_id: int,
    proposal: AgentProposal,
    decision: SentinelDecision,
    kunigami_active: bool,
) -> dict[str, Any]:
    """Build a journal row for `out.sentinel_log`."""
    return {
        "tick_id": int(tick_id),
        "timestamp": proposal.timestamp.isoformat(),
        "agent_id": proposal.agent_id,
        "symbol": proposal.symbol,
        "direction": proposal.direction,
        "rule": decision.rule,
        "allowed": bool(decision.allowed),
        "reason": decision.reason,
        "kunigami_loss_streak_active": bool(kunigami_active),
        "payload": dict(decision.payload),
    }


def summarise_sentinel_log(sentinel_log: list[dict]) -> dict[str, int]:
    """Aggregate a sentinel_log list into per-rule trigger counts.

    Includes both blocked and audit-only rules. `OK` decisions are counted
    separately as `ok` so the total equals the number of proposals
    Sentinel evaluated.
    """
    counts: dict[str, int] = {}
    for row in sentinel_log:
        key = row.get("rule", "unknown")
        if not row.get("allowed", True):
            key = f"{key}_block"
        elif key != "OK":
            key = f"{key}_audit"
        else:
            key = "ok"
        counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Per-tick driver state
# ---------------------------------------------------------------------------

@dataclass
class _GlobalBar:
    """Interleaved-stream bar wrapper with global tick_id."""

    tick_id: int
    symbol: str
    bar: Any                          # production Bar
    bar_index_in_symbol: int          # for the per-symbol fill model


def _interleave_bars(bars_by_symbol: dict[str, list]) -> list[_GlobalBar]:
    """Interleave per-symbol bar lists by timestamp.

    Stable on ties: lexicographic on (timestamp, symbol). Returns the
    flat global stream with monotonic `tick_id` assigned in order. The
    bar's `bar_index_in_symbol` is the original (pre-interleave) index
    in its symbol's series -- used by the production fill model to
    look up the NEXT bar at exit time.
    """
    flat: list[tuple[datetime, str, int, Any]] = []
    for sym, bars in bars_by_symbol.items():
        for i, b in enumerate(bars):
            flat.append((b.time, sym, i, b))
    flat.sort(key=lambda x: (x[0], x[1]))
    return [
        _GlobalBar(tick_id=k, symbol=x[1], bar_index_in_symbol=x[2], bar=x[3])
        for k, x in enumerate(flat)
    ]


# ---------------------------------------------------------------------------
# Aggregator + rejection logger (Phi4 squad rule)
# ---------------------------------------------------------------------------

# Aggregator tier-anchor bias (doctrine 4.1a v1 checkpoint,
# amendment 2026-07-01). Tier-1 strikers get their adjusted conviction
# lifted by TIER_BIAS relative to tier-2 peers, so the anchor wins
# same-base-conviction tiebreaks. A peer needs conviction >= (anchor + TIER_BIAS)
# to override -- meaningful override, not accidental.
TIER_BIAS: float = 0.05


def _tier_adjusted_conviction(proposal: AgentProposal) -> float:
    """Return the aggregator-visible conviction after tier-anchor bias."""
    return float(proposal.conviction) - TIER_BIAS * (int(proposal.agent_tier) - 1)


@dataclass
class _AggregationOutcome:
    accepted: list[AgentProposal]
    rejected: list[dict[str, Any]]
    # Full per-symbol ranked list (winner first). Sentinel slot-fallback
    # uses this to try runner-ups when the winner is physically blocked
    # by R1-R6, so the slot doesn't die on a single-agent block.
    ranked_by_symbol: dict[str, list[AgentProposal]] = field(default_factory=dict)


def _phi4_aggregate(
    proposals: list[AgentProposal],
    *,
    tick_id: int,
) -> _AggregationOutcome:
    """Phi4 squad aggregator: per-symbol highest-conviction wins.

    Rejected proposals get a structured journal entry so
    `rejected_proposals.jsonl` can be analysed downstream (the
    cross-striker rejection-analysis harness).

    Sort key is ``(-tier_adjusted_conviction, agent_tier, agent_id)``.
    Tier-1 anchor wins ties over tier-2 peers (doctrine 4.1a); a peer
    needs ``conviction >= anchor.conviction + TIER_BIAS`` to override.

    Note: this overrides `sim/core/aggregator.py` same-direction-union
    behaviour for the Phi4 squad evaluation. The original aggregator
    is preserved for the Phi3 wrapper validation and for the dashboard.
    """
    if not proposals:
        return _AggregationOutcome(
            accepted=[], rejected=[], ranked_by_symbol={},
        )
    by_sym: dict[str, list[AgentProposal]] = {}
    for p in proposals:
        by_sym.setdefault(p.symbol, []).append(p)
    accepted: list[AgentProposal] = []
    rejected: list[dict[str, Any]] = []
    ranked_by_symbol: dict[str, list[AgentProposal]] = {}
    for sym, plist in by_sym.items():
        plist.sort(
            key=lambda p: (
                -_tier_adjusted_conviction(p),
                int(p.agent_tier),
                p.agent_id,
            ),
        )
        ranked_by_symbol[sym] = list(plist)
        winner = plist[0]
        accepted.append(winner)
        for loser in plist[1:]:
            rejected.append({
                "tick_id": int(tick_id),
                "symbol": sym,
                "winner_agent_id": winner.agent_id,
                "winner_conviction": float(winner.conviction),
                "winner_tier": int(winner.agent_tier),
                "loser_agent_id": loser.agent_id,
                "loser_conviction": float(loser.conviction),
                "loser_tier": int(loser.agent_tier),
                "loser_direction": loser.direction,
                "winner_direction": winner.direction,
                "rejection_reason": "lower_conviction_same_symbol",
                "timestamp": loser.timestamp.isoformat(),
            })
    return _AggregationOutcome(
        accepted=accepted, rejected=rejected,
        ranked_by_symbol=ranked_by_symbol,
    )


# ---------------------------------------------------------------------------
# Squad driver
# ---------------------------------------------------------------------------

@dataclass
class SquadRunOutput:
    """Bundle of every artefact produced by `_drive_squad_replay`."""

    thoughts: list[Thought] = field(default_factory=list)
    proposals_all: list[AgentProposal] = field(default_factory=list)
    proposals_accepted: list[AgentProposal] = field(default_factory=list)
    proposals_rejected: list[dict] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    sentinel_log: list[dict] = field(default_factory=list)
    # F21 workspace participation counters (populated when the driver
    # runs with `use_workspace=True`). Zeros in the audit-only path so
    # G7 C4 correctly fails for agents that never read the workspace.
    workspace_publish_counts: dict[str, int] = field(default_factory=dict)
    workspace_read_counts: dict[str, int] = field(default_factory=dict)


class _AgentScopedSnapshot:
    """Read-tracking wrapper around a ``WorkspaceSnapshot``.

    Duck-types the read surface of ``WorkspaceSnapshot`` (``read_for``,
    ``peer_thoughts``, ``latest_by_agent``) so agents that accept
    ``workspace: WorkspaceSnapshot | None`` receive an instance that
    transparently records the read event under the driver-supplied
    ``agent_id``. Used by ``_drive_squad_replay`` when
    ``use_workspace=True`` so G7 criterion 4 (workspace participation)
    can be computed truthfully.

    Note: not a subclass of ``WorkspaceSnapshot`` -- duck-typing lets
    us avoid touching the frozen dataclass and keeps the wrapper local
    to the driver.
    """

    __slots__ = ("_snap", "_agent_id", "_read_counts")

    def __init__(
        self,
        snap: WorkspaceSnapshot,
        agent_id: str,
        read_counts: dict[str, int],
    ) -> None:
        self._snap = snap
        self._agent_id = agent_id
        self._read_counts = read_counts

    def _record(self) -> None:
        self._read_counts[self._agent_id] = (
            self._read_counts.get(self._agent_id, 0) + 1
        )

    def read_for(self, **kwargs: Any) -> tuple[Thought, ...]:
        self._record()
        return self._snap.read_for(**kwargs)

    def peer_thoughts(self, **kwargs: Any) -> tuple[Thought, ...]:
        self._record()
        return self._snap.peer_thoughts(**kwargs)

    def latest_by_agent(self, **kwargs: Any) -> dict[str, Thought]:
        self._record()
        return self._snap.latest_by_agent(**kwargs)

    # Expose the plain snapshot attributes so agents that inspect
    # ``.thoughts`` / ``.as_of`` / ``.current_tick`` still work.
    @property
    def thoughts(self) -> tuple[Thought, ...]:      # pragma: no cover -- passthrough
        return self._snap.thoughts

    @property
    def as_of(self) -> datetime:                     # pragma: no cover
        return self._snap.as_of

    @property
    def current_tick(self) -> int:                   # pragma: no cover
        return self._snap.current_tick


def _drive_squad_replay(
    *,
    agents: list,
    isagi: A1IsagiV1,
    barou: A7BarouV1,
    kunigami: A10KunigamiV1,
    bars_by_symbol: dict[str, list],
    ledger: ThoughtLedger,
    warmup_bars: int = WARMUP_BARS,
    sentinel_blocks: bool = False,
    use_workspace: bool = False,
) -> SquadRunOutput:
    """End-to-end Phi4 squad replay driver.

    Walks the interleaved bar stream once. Two-phase tick order
    (observe-all then intend-all). Per-symbol single open trade. All
    closed trades pushed into Kunigami for the loss-streak signal.

    Sentinel wiring (Phi4.2 mini-sprint, 2026-06-30). Every accepted
    proposal is evaluated against Sentinel R1/R3/R5 and journalled to
    ``out.sentinel_log``. In the default ``sentinel_blocks=False`` mode
    the wiring is AUDIT-ONLY -- Sentinel decisions are recorded but do
    not veto trades, which preserves Phi4 + Phi4.1 replay fidelity for
    the sealed verdicts. Phi5 harnesses (Arms 1-5) pass
    ``sentinel_blocks=True`` so R1/R5 physically block violating trades
    and R6 (per-symbol total-risk cap) gates Arm 4 multi-position.

    F21 workspace threading (2026-07-01, added for G7 gate criterion 4).
    Pass ``use_workspace=True`` to enable per-tick publish + snapshot
    plumbing; each intending agent receives an ``_AgentScopedSnapshot``
    that records read events into ``out.workspace_read_counts``. The
    audit-only default (``use_workspace=False``) preserves Phi4/4.1
    baseline reproduction: sealed verdicts must always run with the
    workspace OFF, otherwise Bachira's peer-confluence lift shifts the
    trade set. G7 harness passes ``use_workspace=True``.
    """
    out = SquadRunOutput()
    global_bars = _interleave_bars(bars_by_symbol)
    if not global_bars:
        return out

    # Open trades keyed by symbol (per-symbol single-position rule).
    open_trades: dict[str, Any] = {}
    cfg = isagi._cfg                       # cfg shared across wrappers

    # Sentinel state (R3/R5 need per-agent counters).
    per_agent_consecutive_losses: dict[str, int] = {}
    per_agent_proposals_today: dict[str, int] = {}
    current_day: Any = None

    # F21 workspace state (only wired when use_workspace=True).
    workspace: ReasoningWorkspace | None = (
        ReasoningWorkspace() if use_workspace else None
    )
    workspace_publish_counts: dict[str, int] = {}
    workspace_read_counts: dict[str, int] = {}

    # Symbol -> sorted timestamps + bar list for next-bar lookup.
    sorted_bars_by_symbol: dict[str, list] = {
        sym: bars for sym, bars in bars_by_symbol.items()
    }
    timestamps_by_symbol: dict[str, list[datetime]] = {
        sym: [b.time for b in bars] for sym, bars in bars_by_symbol.items()
    }

    # Warmup is measured in PER-SYMBOL bar index, not global tick.
    bars_seen_per_sym: dict[str, int] = {sym: 0 for sym in bars_by_symbol}
    n_bars_per_sym: dict[str, int] = {
        sym: len(bars) for sym, bars in bars_by_symbol.items()
    }

    # Progress logging (2026-07-01) -- long replays go silent for
    # 30-60 min otherwise, making it impossible to tell a stuck run
    # from a slow one. Log every ~5 pct of the way through OR every
    # 10 min of wall-clock (whichever is sooner).
    total_bars = len(global_bars)
    progress_interval_bars = max(1, total_bars // 20)      # 5 pct
    progress_interval_seconds = 600                        # 10 min
    _replay_start_ts = time.time()
    _last_progress_ts = _replay_start_ts
    log.info(
        "Squad replay starting: %d global bars across %d symbols "
        "(sentinel_blocks=%s, use_workspace=%s)",
        total_bars, len(bars_by_symbol), sentinel_blocks, use_workspace,
    )

    for i_gb, gb in enumerate(global_bars):
        if (
            i_gb > 0
            and (
                i_gb % progress_interval_bars == 0
                or (time.time() - _last_progress_ts) >= progress_interval_seconds
            )
        ):
            _elapsed = time.time() - _replay_start_ts
            _pct = 100.0 * i_gb / total_bars
            _eta_s = _elapsed * (total_bars - i_gb) / max(i_gb, 1)
            log.info(
                "Squad replay progress: %d/%d bars (%.1f%%), "
                "elapsed=%.1f s, eta=%.1f s, trades=%d, proposals_all=%d",
                i_gb, total_bars, _pct, _elapsed, _eta_s,
                len(out.trades), len(out.proposals_all),
            )
            _last_progress_ts = time.time()
        symbol = gb.symbol
        i_sym = gb.bar_index_in_symbol
        bar = gb.bar
        # Day-rollover: reset R3 proposals-today counter at the first bar
        # of each new UTC day. Deterministic on `bar.time.date()`.
        bar_day = bar.time.date() if bar.time is not None else current_day
        if current_day is None or bar_day != current_day:
            current_day = bar_day
            per_agent_proposals_today.clear()
        market = _bar_to_market_state(bar, tick_id=gb.tick_id)
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
        bars_seen_per_sym[symbol] += 1

        # Trade management on THIS symbol's open trade.
        ot = open_trades.get(symbol)
        if ot is not None:
            _update_excursion(ot, bar)
            closed = _check_exit(ot, bar, cfg)
            if closed:
                # Translate prod Trade -> our TradeRecord; attach the
                # source agent_id (we journal it on `ot` when opening).
                tr = _score_trade(
                    ot, _agent_target_hold_hours(ot, agents),
                )
                tr_with_agent = _annotate_trade_record(
                    tr, ot, gb.tick_id, symbol,
                )
                out.trades.append(tr_with_agent)
                # Push the closed-trade outcome into Kunigami so the
                # loss-streak signal fires on squad-wide outcomes.
                kunigami.record_closed_trade(ClosedTradeRecord(
                    agent_id=tr_with_agent.agent_id,
                    exit_time=tr_with_agent.exit_time,
                    pnl_pips=tr_with_agent.pnl_pips,
                    source_conviction=float(
                        getattr(ot, "_source_conviction", 0.0)
                    ),
                ))
                # Per-agent consecutive-loss counter feeds Sentinel R5
                # directly (independent of Kunigami's window-based warning).
                _aid = tr_with_agent.agent_id
                if tr_with_agent.pnl_pips <= 0:
                    per_agent_consecutive_losses[_aid] = (
                        per_agent_consecutive_losses.get(_aid, 0) + 1
                    )
                else:
                    per_agent_consecutive_losses[_aid] = 0
                open_trades.pop(symbol, None)

        # Determine eligible agents on this bar.
        eligible = sorted(
            [a for a in agents if symbol in a.symbols],
            key=lambda a: a.agent_id,
        )

        # ---- Phase 1: observe -----------------------------------------
        my_thought: dict[str, Thought] = {}
        for agent in eligible:
            t = agent.observe(market, ledger)
            ledger.append(t)
            out.thoughts.append(t)
            my_thought[agent.agent_id] = t
            if workspace is not None:
                if workspace.publish(t):
                    workspace_publish_counts[agent.agent_id] = (
                        workspace_publish_counts.get(agent.agent_id, 0) + 1
                    )

        # Skip warmup (per-symbol) -- production wrapper needs
        # warmup_bars zones/swings to be cooked.
        if bars_seen_per_sym[symbol] <= warmup_bars:
            continue
        if i_sym >= n_bars_per_sym[symbol] - 1:
            # last bar of the symbol's series: no "next bar" available
            # to open a trade; skip intend phase to mirror Phi3.
            continue

        # Snapshot the workspace at the tick barrier (Phase 1 -> Phase 2).
        # The snapshot's look-ahead guards filter out this tick's own
        # writes, so every agent sees only Thoughts from tick_id < gb.tick_id.
        base_snapshot: WorkspaceSnapshot | None = None
        if workspace is not None:
            base_snapshot = workspace.snapshot(
                as_of=bar.time,
                current_tick=int(gb.tick_id),
            )

        # ---- Phase 2: intend ------------------------------------------
        proposals_this_tick: list[AgentProposal] = []
        for agent in eligible:
            if market.timeframe != agent.home_tf:
                continue
            t = my_thought[agent.agent_id]
            if base_snapshot is not None:
                scoped = _AgentScopedSnapshot(
                    base_snapshot, agent.agent_id, workspace_read_counts,
                )
                p = agent.intend(market, t, workspace=scoped)
            else:
                p = agent.intend(market, t)
            if p is None:
                continue
            proposals_this_tick.append(p)
            out.proposals_all.append(p)
            # R3 pass-bias counter (per-agent, per-UTC-day).
            per_agent_proposals_today[p.agent_id] = (
                per_agent_proposals_today.get(p.agent_id, 0) + 1
            )

        if not proposals_this_tick:
            continue

        outcome = _phi4_aggregate(
            proposals_this_tick, tick_id=gb.tick_id,
        )
        out.proposals_accepted.extend(outcome.accepted)
        out.proposals_rejected.extend(outcome.rejected)

        # Sentinel wiring (Phi4.2 + Phase N slot-fallback, 2026-07-01).
        # In audit-only mode (sentinel_blocks=False) we evaluate the
        # single per-symbol winner and never open anything the sentinel
        # would veto -- preserves Phi4/Phi4.1 replay fidelity.
        # In physical mode (sentinel_blocks=True) we iterate the FULL
        # ranked list for the symbol, so a sentinel-blocked winner
        # cedes the slot to the next-ranked proposal instead of the
        # slot dying. Bounded by the aggregator's own ordering; the
        # per-symbol single-position guard still applies once anything
        # opens.
        kuni_active = bool(kunigami.warning_active_at(bar.time))
        if sentinel_blocks:
            symbol_candidates = outcome.ranked_by_symbol.get(symbol, [])
        else:
            symbol_candidates = [
                p for p in outcome.accepted if p.symbol == symbol
            ]
        for rank_idx, proposal in enumerate(symbol_candidates):
            if proposal.symbol != symbol:
                continue
            sentinel_ctx = SentinelContext(
                equity=SANDBOX_EQUITY_DOLLARS,
                pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
                consecutive_losses=per_agent_consecutive_losses.get(
                    proposal.agent_id, 0,
                ),
                proposals_today_by_agent=dict(per_agent_proposals_today),
                kunigami_loss_streak_active=kuni_active,
            )
            decision = sentinel_evaluate_proposal(proposal, sentinel_ctx)
            out.sentinel_log.append(_sentinel_log_entry(
                tick_id=gb.tick_id,
                proposal=proposal,
                decision=decision,
                kunigami_active=kuni_active,
            ))
            if sentinel_blocks and not decision.allowed:
                # Physical enforcement path: record the veto and cede
                # the slot to the next-ranked proposal (Phase N
                # fallback). If no next-ranked exists, slot dies.
                out.proposals_rejected.append({
                    "tick_id": int(gb.tick_id),
                    "symbol": symbol,
                    "winner_agent_id": proposal.agent_id,
                    "winner_conviction": float(proposal.conviction),
                    "loser_agent_id": proposal.agent_id,
                    "loser_conviction": float(proposal.conviction),
                    "loser_direction": proposal.direction,
                    "winner_direction": proposal.direction,
                    "rejection_reason": f"sentinel_{decision.rule}_block",
                    "sentinel_reason": decision.reason,
                    "rank_at_block": int(rank_idx),
                    "timestamp": proposal.timestamp.isoformat(),
                })
                continue
            if symbol in open_trades:
                # Per-symbol single-position rule: log winner as
                # rejected-by-execution.
                out.proposals_rejected.append({
                    "tick_id": int(gb.tick_id),
                    "symbol": symbol,
                    "winner_agent_id": proposal.agent_id,
                    "winner_conviction": float(proposal.conviction),
                    "loser_agent_id": proposal.agent_id,
                    "loser_conviction": float(proposal.conviction),
                    "loser_direction": proposal.direction,
                    "winner_direction": proposal.direction,
                    "rejection_reason": "open_position_concurrency_limit",
                    "timestamp": proposal.timestamp.isoformat(),
                })
                continue
            # Open the trade at next bar's open via prod fill model.
            next_bar = sorted_bars_by_symbol[symbol][i_sym + 1]
            try:
                trade = _open_trade_from_proposal(proposal, next_bar, cfg)
                trade._source_agent_id = proposal.agent_id   # type: ignore[attr-defined]
                trade._source_conviction = float(proposal.conviction)  # type: ignore[attr-defined]
                trade._source_regime_fit = float(proposal.regime_fit)  # type: ignore[attr-defined]
                trade._source_sl_pips = abs(proposal.entry - proposal.stop) * 10000.0  # type: ignore[attr-defined]
                # atr_pips + h1_swing_pips are best-effort: only some
                # agents publish them via proposal.rationale; fall back
                # to None so C6 default (30.0/60.0) still applies.
                _rat = proposal.rationale or {}
                trade._source_atr_pips = _rat.get("atr_pips")  # type: ignore[attr-defined]
                trade._source_h1_swing_pips = _rat.get("h1_swing_pips")  # type: ignore[attr-defined]
                trade._source_tick_id = int(gb.tick_id)      # type: ignore[attr-defined]
                trade._source_proposal_rationale = dict(proposal.rationale)  # type: ignore[attr-defined]
                open_trades[symbol] = trade
                # Slot filled -- runner-ups for this symbol are moot.
                break
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Failed to open trade from proposal at tick=%d (%s/%s): %s",
                    gb.tick_id, symbol, proposal.agent_id, exc,
                )

    # Close any remaining open trades on the final bar of each symbol.
    for symbol, ot in list(open_trades.items()):
        if ot.exit_time is None:
            last = bars_by_symbol[symbol][-1]
            ot.exit_time = last.time
            ot.exit_price = last.close
            ot.exit_reason = "end_of_data"
            if ot.direction.value == "long":
                pip = (last.close - ot.entry_price) * 10000.0
            else:
                pip = (ot.entry_price - last.close) * 10000.0
            ot.pnl_pips = pip
            ot.pnl = (
                pip * ot.lot_size * cfg.backtest.pip_value_per_lot
                - ot.commission
            )
            tr = _score_trade(ot, _agent_target_hold_hours(ot, agents))
            out.trades.append(
                _annotate_trade_record(tr, ot, gb.tick_id, symbol),
            )
            open_trades.pop(symbol, None)

    # F21 workspace participation counters flushed once at end (avoids
    # per-tick dict copy).
    if workspace is not None:
        out.workspace_publish_counts = dict(workspace_publish_counts)
        out.workspace_read_counts = dict(workspace_read_counts)

    _replay_elapsed = time.time() - _replay_start_ts
    log.info(
        "Squad replay complete: %d bars in %.1f s (%.0f bars/s), "
        "trades=%d, proposals_all=%d, sentinel_blocks=%s, use_workspace=%s",
        total_bars, _replay_elapsed,
        total_bars / max(_replay_elapsed, 1e-6),
        len(out.trades), len(out.proposals_all),
        sentinel_blocks, use_workspace,
    )

    return out


def _agent_target_hold_hours(prod_trade, agents) -> float:
    aid = getattr(prod_trade, "_source_agent_id", None)
    if not aid:
        return 24.0
    for a in agents:
        if a.agent_id == aid:
            return float(a.canon_role.target_hold_hours)
    return 24.0


def _annotate_trade_record(
    tr: TradeRecord, prod_trade, tick_id: int, symbol: str,
) -> TradeRecord:
    """Override the generic Phi3 TradeRecord with squad provenance.

    Populates F19/F20 source-* fields from the prod_trade attributes
    attached at open time so the G7 C5/C6 evaluators can call
    ``agent.lot_intent`` / ``risk_intent`` with the ACTUAL per-trade
    conviction + regime_fit + sl_pips (not the default 0.5/0.5/40).
    """
    aid = getattr(prod_trade, "_source_agent_id", "isagi_yoichi")
    return TradeRecord(
        agent_id=aid,
        symbol=symbol,
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
        source_conviction=getattr(prod_trade, "_source_conviction", None),
        source_regime_fit=getattr(prod_trade, "_source_regime_fit", None),
        source_sl_pips=getattr(prod_trade, "_source_sl_pips", None),
        source_atr_pips=getattr(prod_trade, "_source_atr_pips", None),
        source_h1_swing_pips=getattr(
            prod_trade, "_source_h1_swing_pips", None,
        ),
    )


# ---------------------------------------------------------------------------
# Window slicing
# ---------------------------------------------------------------------------

@dataclass
class SquadWindowStats:
    """Per-window per-agent + squad-level KPIs."""

    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    # Per-agent OOS slice {agent_id: (n, mean_pips, median_pips, mean_tqs, win_rate)}
    per_agent_oos: dict[str, tuple[int, float, float, float, float]] = field(
        default_factory=dict,
    )
    # Squad-level OOS rollup across all agents.
    squad_oos_n: int = 0
    squad_oos_mean_pips: float = 0.0
    squad_oos_median_pips: float = 0.0
    squad_oos_mean_tqs: float = 0.0
    squad_oos_win_rate: float = 0.0


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


def _compute_squad_windows(
    trades: list[TradeRecord],
    *,
    full_start: datetime,
    full_end: datetime,
    all_agent_ids: tuple[str, ...],
) -> list[SquadWindowStats]:
    out: list[SquadWindowStats] = []
    for ws in _window_starts(full_start, full_end):
        is_start = ws
        is_end = datetime(ws.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > full_end:
            oos_end = full_end
        oos_tr = [t for t in trades if oos_start <= t.entry_time < oos_end]
        per_agent: dict[str, tuple[int, float, float, float, float]] = {}
        for aid in all_agent_ids:
            slice_ = [t for t in oos_tr if t.agent_id == aid]
            mean_p, med_p, mean_tqs, wr, n = _summarise(slice_)
            per_agent[aid] = (n, mean_p, med_p, mean_tqs, wr)
        sq_mean, sq_med, sq_tqs, sq_wr, sq_n = _summarise(oos_tr)
        out.append(SquadWindowStats(
            is_start=is_start, is_end=is_end,
            oos_start=oos_start, oos_end=oos_end,
            per_agent_oos=per_agent,
            squad_oos_n=sq_n,
            squad_oos_mean_pips=sq_mean,
            squad_oos_median_pips=sq_med,
            squad_oos_mean_tqs=sq_tqs,
            squad_oos_win_rate=sq_wr,
        ))
    return out


# ---------------------------------------------------------------------------
# F17 DeltaInfo (isolated arms for Nagi + Barou)
# ---------------------------------------------------------------------------

def _run_isolated_window(
    *,
    agent_class,
    agent_kwargs: dict,
    bars_by_symbol: dict[str, list],
    is_start: datetime,
    is_end: datetime,
    oos_start: datetime,
    oos_end: datetime,
    isagi_for_prep: A1IsagiV1,
    barou_for_prep: A7BarouV1,
    kunigami_for_prep: A10KunigamiV1,
) -> list[TradeRecord]:
    """Run ONE OOS window with a single Tier-2 agent isolated.

    The isolated arm replaces the FullLedger with a RedactedLedger(self_only)
    so the candidate agent reads only its own past Thoughts. We still
    drive the WHOLE 4-agent squad through the engine -- isolation is a
    LEDGER property, not a roster trim, per `09 sec 1.3` injectable-
    ledger binding rule. Only the candidate's `intend()` outputs are
    scored.
    """
    # NB. Compute economy: the isolated arm trades are tiny in volume
    # vs the full squad run. Keeping the run scope a single OOS window
    # keeps the F17 measurement tractable in the user spec's 3-windows
    # cap.
    sub_bars = {
        sym: [b for b in bars if is_start <= b.time < oos_end]
        for sym, bars in bars_by_symbol.items()
    }
    if not any(sub_bars.values()):
        return []
    candidate_id = agent_kwargs.get("agent_id")
    # Re-instantiate the four-agent squad. The candidate uses a Tier-3
    # redacted view of the ledger -- effectively self-only reads.
    isagi = isagi_for_prep
    barou = barou_for_prep
    kunigami = kunigami_for_prep
    candidate = agent_class(**agent_kwargs)
    nagi = candidate if candidate_id == "nagi_seishiro" else A6NagiV1()
    if candidate_id == "barou_shoei":
        barou = candidate
    agents_list = [isagi, nagi, barou, kunigami]

    # NB. RedactedLedger has its OWN source; the squad's FullLedger
    # writes are still seen by non-isolated agents. The user spec's
    # F17 arm uses `RedactedLedger(self_only)` per `09 sec 1.3`:
    # candidate reads only own past thoughts.
    inner = FullLedger()
    isolated_view = RedactedLedger(agent_id=candidate_id, source=inner)
    # We need a way for OTHER agents to read the full ledger AND for
    # the candidate to read the redacted view. Doing this cleanly
    # requires injecting per-agent ledger views into observe(); the
    # current engine passes a single ledger. For Phi4 v1 we approximate
    # by GIVING THE CANDIDATE ALONE the redacted view via a custom
    # driver below.
    out = _drive_squad_replay_with_isolated_candidate(
        agents=agents_list,
        candidate_id=candidate_id,
        full_ledger=inner,
        isolated_ledger=isolated_view,
        bars_by_symbol=sub_bars,
        isagi=isagi,
        barou=barou,
        kunigami=kunigami,
    )
    return [
        t for t in out.trades
        if t.agent_id == candidate_id
        and oos_start <= t.entry_time < oos_end
    ]


def _drive_squad_replay_with_isolated_candidate(
    *,
    agents: list,
    candidate_id: str,
    full_ledger: FullLedger,
    isolated_ledger: RedactedLedger,
    bars_by_symbol: dict[str, list],
    isagi: A1IsagiV1,
    barou: A7BarouV1,
    kunigami: A10KunigamiV1,
) -> SquadRunOutput:
    """Variant of `_drive_squad_replay` for the F17 isolated arm.

    The candidate agent observes against the RedactedLedger; everyone
    else observes against the FullLedger. WRITES go through the
    FullLedger so the other agents see the candidate's own past
    thoughts (mirroring the doctrine -- isolation restricts READS only).
    """
    out = SquadRunOutput()
    global_bars = _interleave_bars(bars_by_symbol)
    if not global_bars:
        return out

    cfg = isagi._cfg
    open_trades: dict[str, Any] = {}
    sorted_bars_by_symbol: dict[str, list] = dict(bars_by_symbol)
    bars_seen_per_sym: dict[str, int] = {sym: 0 for sym in bars_by_symbol}
    n_bars_per_sym: dict[str, int] = {
        sym: len(bars) for sym, bars in bars_by_symbol.items()
    }

    # Progress logging (2026-07-01) -- see _drive_squad_replay for
    # rationale. Isolated-arm replays are the biggest single time sink
    # in Phi4.1 physical rerun (one arm per candidate agent).
    total_bars = len(global_bars)
    progress_interval_bars = max(1, total_bars // 10)      # 10 pct
    progress_interval_seconds = 600                        # 10 min
    _isolated_start_ts = time.time()
    _isolated_last_progress = _isolated_start_ts
    log.info(
        "Isolated-arm replay starting [%s]: %d global bars",
        candidate_id, total_bars,
    )

    for i_gb, gb in enumerate(global_bars):
        if (
            i_gb > 0
            and (
                i_gb % progress_interval_bars == 0
                or (time.time() - _isolated_last_progress)
                >= progress_interval_seconds
            )
        ):
            _elapsed = time.time() - _isolated_start_ts
            _pct = 100.0 * i_gb / total_bars
            _eta_s = _elapsed * (total_bars - i_gb) / max(i_gb, 1)
            log.info(
                "Isolated-arm [%s] progress: %d/%d bars (%.1f%%), "
                "elapsed=%.1f s, eta=%.1f s, trades=%d",
                candidate_id, i_gb, total_bars, _pct, _elapsed, _eta_s,
                len(out.trades),
            )
            _isolated_last_progress = time.time()

        symbol = gb.symbol
        i_sym = gb.bar_index_in_symbol
        bar = gb.bar
        market = MarketState(
            tick_id=gb.tick_id, symbol=symbol,
            timeframe=bar.timeframe.value, as_of=bar.time,
            open=float(bar.open), high=float(bar.high),
            low=float(bar.low), close=float(bar.close),
            volume=float(bar.volume),
        )
        bars_seen_per_sym[symbol] += 1
        ot = open_trades.get(symbol)
        if ot is not None:
            _update_excursion(ot, bar)
            closed = _check_exit(ot, bar, cfg)
            if closed:
                tr = _score_trade(ot, _agent_target_hold_hours(ot, agents))
                out.trades.append(
                    _annotate_trade_record(tr, ot, gb.tick_id, symbol),
                )
                open_trades.pop(symbol, None)

        eligible = sorted(
            [a for a in agents if symbol in a.symbols],
            key=lambda a: a.agent_id,
        )
        my_thought: dict[str, Thought] = {}
        for agent in eligible:
            ledger_for_agent = (
                isolated_ledger if agent.agent_id == candidate_id
                else full_ledger
            )
            t = agent.observe(market, ledger_for_agent)
            full_ledger.append(t)
            out.thoughts.append(t)
            my_thought[agent.agent_id] = t

        if bars_seen_per_sym[symbol] <= WARMUP_BARS:
            continue
        if i_sym >= n_bars_per_sym[symbol] - 1:
            continue

        proposals_this_tick: list[AgentProposal] = []
        for agent in eligible:
            if market.timeframe != agent.home_tf:
                continue
            t = my_thought[agent.agent_id]
            p = agent.intend(market, t)
            if p is None:
                continue
            proposals_this_tick.append(p)
            out.proposals_all.append(p)
        if not proposals_this_tick:
            continue
        outcome = _phi4_aggregate(proposals_this_tick, tick_id=gb.tick_id)
        out.proposals_accepted.extend(outcome.accepted)
        out.proposals_rejected.extend(outcome.rejected)
        for proposal in outcome.accepted:
            if symbol in open_trades:
                continue
            next_bar = sorted_bars_by_symbol[symbol][i_sym + 1]
            try:
                trade = _open_trade_from_proposal(proposal, next_bar, cfg)
                trade._source_agent_id = proposal.agent_id
                trade._source_conviction = float(proposal.conviction)
                open_trades[symbol] = trade
            except Exception as exc:  # noqa: BLE001
                log.warning("isolated arm open failed: %s", exc)

    _isolated_elapsed = time.time() - _isolated_start_ts
    log.info(
        "Isolated-arm [%s] complete: %d bars in %.1f s (%.0f bars/s), trades=%d",
        candidate_id, total_bars, _isolated_elapsed,
        total_bars / max(_isolated_elapsed, 1e-6), len(out.trades),
    )
    return out


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

@dataclass
class SquadGateReport:
    full_start: datetime
    full_end: datetime
    symbols: tuple[str, ...]
    n_thoughts: int
    n_proposals_all: int
    n_proposals_accepted: int
    n_proposals_rejected: int
    n_trades: int
    per_agent_trade_counts: dict[str, int]
    per_agent_overall_kpis: dict[str, dict[str, float]]
    squad_median_oos_window_mean_pips: float
    squad_mean_oos_window_mean_pips: float
    squad_median_oos_window_mean_tqs: float
    squad_oos_windows_positive: int
    squad_oos_windows_total: int
    isagi_alone_median_oos_pips: float
    isagi_alone_median_oos_tqs: float
    squad_vs_isagi_tqs_ratio: float
    verdict: str
    verdict_reason: str
    windows: list[SquadWindowStats] = field(default_factory=list)
    delta_info_results: dict[str, DeltaInfoResult] = field(default_factory=dict)
    sentinel_trigger_counts: dict[str, int] = field(default_factory=dict)
    devour_fired_count: int = 0
    nagi_fired_count: int = 0
    kunigami_warning_count: int = 0


def _decide_squad_verdict(report: SquadGateReport) -> tuple[str, str]:
    """Phi4 -> Phi5 gate per `09-experiment-architecture.md` G5 + user spec."""
    if report.n_trades < 30:
        return (
            "PROVISIONAL",
            f"only {report.n_trades} squad trades; below the 30-trade "
            "floor for a statistical gate claim",
        )
    ratio = report.squad_vs_isagi_tqs_ratio
    if ratio >= SQUAD_PASS_RATIO:
        return (
            "PASS",
            f"squad median OOS-window mean TQS "
            f"{report.squad_median_oos_window_mean_tqs:.3f} is "
            f"{ratio:.2f}x Isagi-alone "
            f"({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}); G5 threshold 1.10x",
        )
    if ratio >= SQUAD_PARTIAL_RATIO:
        return (
            "PARTIAL",
            f"squad TQS {report.squad_median_oos_window_mean_tqs:.3f} "
            f"is {ratio:.2f}x Isagi-alone ({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}) "
            "-- positive lift but below 1.10x G5 floor",
        )
    return (
        "FAIL",
        f"squad TQS {report.squad_median_oos_window_mean_tqs:.3f} is "
        f"{ratio:.2f}x Isagi-alone ({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}) "
        "-- adding agents LOST edge; reported honestly",
    )


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def render_squad_report(report: SquadGateReport) -> str:
    lines: list[str] = []
    lines.append("# Phi4 squad gate -- 4-agent MVP vs A1 Isagi-alone\n")
    lines.append(f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(
        f"**Window:** {report.full_start.date()} -> {report.full_end.date()} "
        f"on **{', '.join(report.symbols)}** (H4)\n"
    )
    lines.append(
        "**Agents:** A1 Isagi v1, A6 Nagi v1 (confluence), "
        "A7 Barou v1 (USDCAD baseline-zone), A10 Kunigami v1 (anti-tilt).\n"
    )
    lines.append("---\n")
    lines.append("## Verdict\n")
    lines.append(f"**Phi4 -> Phi5 gate (G5): `{report.verdict}`**\n")
    lines.append(f"_{report.verdict_reason}_\n")
    lines.append(
        "Honest framing: PASS = squad TQS >= 1.10 x Isagi-alone (G5 "
        "in `09-experiment-architecture.md`). PARTIAL = positive lift "
        "below 1.10x. FAIL = adding agents LOST edge. Reported "
        "verbatim; no silent retuning per user constraint.\n"
    )
    lines.append("---\n")
    lines.append("## Squad TQS vs Isagi-alone\n")
    lines.append("")
    lines.append("| Metric | Squad (Phi4) | Isagi-alone (Phi3) | Ratio |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| Median OOS-window mean pips/trade | "
        f"**{report.squad_median_oos_window_mean_pips:+.2f}** | "
        f"+{ISAGI_ALONE_MEDIAN_OOS_PIPS:.2f} | "
        f"{report.squad_median_oos_window_mean_pips / ISAGI_ALONE_MEDIAN_OOS_PIPS:.2f}x |"
    )
    lines.append(
        f"| Median OOS-window mean TQS (F12) | "
        f"**{report.squad_median_oos_window_mean_tqs:.3f}** | "
        f"{ISAGI_ALONE_MEDIAN_OOS_TQS:.3f} | "
        f"**{report.squad_vs_isagi_tqs_ratio:.2f}x** |"
    )
    lines.append(
        f"| OOS windows positive | "
        f"{report.squad_oos_windows_positive} / "
        f"{report.squad_oos_windows_total} | "
        f"{ISAGI_ALONE_OOS_WINDOWS_POSITIVE} / 7 | -- |"
    )
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-agent KPIs (full dev window)\n")
    lines.append("")
    lines.append(
        "| Agent | Trades | Mean pips | Median pips | Mean TQS | Win % |"
    )
    lines.append("|---|---|---|---|---|---|")
    for aid in sorted(report.per_agent_overall_kpis):
        kpi = report.per_agent_overall_kpis[aid]
        lines.append(
            f"| `{aid}` | {int(kpi['n'])} | "
            f"{kpi['mean_pips']:+.2f} | {kpi['median_pips']:+.2f} | "
            f"{kpi['mean_tqs']:.3f} | {kpi['win_rate']*100:.1f}% |"
        )
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-window walk-forward (squad-level)\n")
    lines.append("(4 yr IS / 1 yr OOS rolling -- matches E004 + Phi3)\n")
    lines.append("")
    header_cols = ["IS window", "OOS yr"] + [
        col
        for aid in sorted(report.per_agent_overall_kpis)
        for col in [f"{aid} n", f"{aid} mean pips"]
    ] + ["Squad n", "Squad mean pips", "Squad mean TQS"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")
    sorted_agent_ids = sorted(report.per_agent_overall_kpis)
    for w in report.windows:
        row = [
            f"{w.is_start.year}-{w.is_end.year - 1}",
            f"{w.oos_start.year}",
        ]
        for aid in sorted_agent_ids:
            n, mean_p, _, _, _ = w.per_agent_oos.get(aid, (0, 0.0, 0.0, 0.0, 0.0))
            row.append(str(int(n)))
            row.append(f"{mean_p:+.2f}")
        row.extend([
            str(int(w.squad_oos_n)),
            f"{w.squad_oos_mean_pips:+.2f}",
            f"{w.squad_oos_mean_tqs:.3f}",
        ])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("---\n")
    lines.append("## F17 DeltaInfo (Tier-2 candidates: Nagi, Barou)\n")
    lines.append("")
    lines.append(
        "| Agent | n informed | n isolated | Median TQS informed | "
        "Median TQS isolated | DeltaInfo | 95% CI | Tier | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for aid in sorted(report.delta_info_results):
        di = report.delta_info_results[aid]
        underpowered = (di.n_informed < 30) or (di.n_isolated < 30)
        notes = "[underpowered]" if underpowered else ""
        lines.append(
            f"| `{aid}` | {di.n_informed} | {di.n_isolated} | "
            f"{di.median_informed:.3f} | {di.median_isolated:.3f} | "
            f"{di.delta_info:+.3f} | "
            f"[{di.ci_low:+.3f}, {di.ci_high:+.3f}] | "
            f"{di.tier} | {notes} |"
        )
    lines.append("")
    lines.append(
        "_F17 ΔInfo measures whether each Tier-2 candidate's edge "
        "depends on reading the ledger. Tier-2 = ΔInfo > 0 AND "
        "bootstrap CI lower bound > 0._\n"
    )
    lines.append("")
    lines.append("---\n")
    lines.append("## Engine telemetry\n")
    lines.append("")
    lines.append(f"- Symbols: {', '.join(report.symbols)} (H4)")
    lines.append(f"- Thoughts emitted (squad-wide): {report.n_thoughts}")
    lines.append(f"- Proposals (all): {report.n_proposals_all}")
    lines.append(f"- Proposals accepted: {report.n_proposals_accepted}")
    lines.append(f"- Proposals rejected: {report.n_proposals_rejected}")
    lines.append(f"- Trades opened+closed: {report.n_trades}")
    lines.append(f"- Nagi confluence-firing thoughts: {report.nagi_fired_count}")
    lines.append(f"- Barou devour lifts applied: {report.devour_fired_count}")
    lines.append(
        f"- Kunigami warning thoughts: {report.kunigami_warning_count}"
    )
    lines.append("")
    if report.sentinel_trigger_counts:
        lines.append(
            "Sentinel R1-R6 audit counts (wired 2026-06-30, Phi4.2 "
            "mini-sprint; audit-only in Phi4 / Phi4.1 harnesses, "
            "physical enforcement in Phi5+ via `sentinel_blocks=True`):"
        )
        for k in sorted(report.sentinel_trigger_counts):
            lines.append(
                f"  - {k}: {report.sentinel_trigger_counts[k]}"
            )
    else:
        lines.append(
            "Sentinel R1-R6 audit block: no proposals evaluated "
            "(harness ran with zero accepted proposals)."
        )
    lines.append("")
    # Auto-generated diagnostic notes when the gate fails -- the
    # user spec requires honest reporting of WHY a FAIL happened.
    if report.verdict in ("FAIL", "PARTIAL"):
        lines.append("## Diagnosis -- why the squad did not PASS\n")
        lines.append(
            f"The {report.verdict} verdict is information, not a "
            "problem to hide. Per-agent telemetry above:\n"
        )
        lines.append(
            f"- **Nagi confluence thoughts emitted: "
            f"{report.nagi_fired_count}**. Confluence requires >= 2 "
            "OTHER strikers with conviction > 0.7, shared tags, "
            "overlapping coordinate bands, and matching direction "
            "at tick T-1. With an MVP squad of two tradable strikers "
            "(Isagi + Barou) the 2-distinct-peer floor is structurally "
            "rare on USDCAD and unreachable on EURUSD (Isagi only). "
            "The one-bar lag is NOT the bottleneck; the predicate is.\n"
            f"- **Barou devour lifts applied: "
            f"{report.devour_fired_count}**. Lifts fire only when "
            "Isagi at tick T-1 disagrees directionally with Barou's "
            "current USDCAD signal at conviction >= 0.7. A low count "
            "indicates Isagi was either silent or directionally "
            "aligned on most USDCAD ticks where Barou fired.\n"
            f"- **Kunigami warning thoughts: "
            f"{report.kunigami_warning_count}**. Zero warnings "
            "means the squad never hit 3-of-5 high-confidence-loss "
            "streaks within the rolling window. Either the squad's "
            "loss rate stayed below the predicate (good news), or the "
            "predicate is too tight in the run's volatility regime.\n"
        )
        lines.append(
            "See per-agent KPI table above for trade-mix and TQS "
            "breakdown. A common driver of squad TQS regression: an "
            "agent with HIGH mean pips but LOW median pips (fat right "
            "tail) drags down the median-of-OOS-window-means TQS "
            "even when its cumulative pips are positive. Φ5 wires HRP "
            "allocation to size such agents DOWN automatically.\n"
        )
        lines.append("")

    lines.append("## Honest caveats\n")
    lines.append(
        "1. **One-bar chemical-reaction lag is intentional** -- "
        "doctrine sec 3.8 forbids same-tick reads. Nagi sees peers "
        "at tick T-1 (or earlier within ttl_ticks). Reported as a "
        "design choice, not a bug.\n"
        "2. **Per-symbol single-position rule** preserves the E004 "
        "execution contract; cross-symbol concurrency is allowed.\n"
        "3. **Risk Conductor: equal risk-budget per agent** for v1 "
        "(no HRP). Φ5 wires HRP-driven reweighting.\n"
        "4. **`regime_fit = 0.5` placeholder** on every Proposal -- "
        "regime classifier (F1=0.496 weak-label) not yet wired into "
        "the conviction stream. See `sim/regime/validation_2024_eurusd_h4.json`.\n"
        "5. **F17 ΔInfo sampled** on a subset of OOS windows for "
        "compute economy; underpowered arms flagged `[underpowered]` "
        "in the table above per user spec.\n"
        "6. **No Φ4.1 chemical-reaction beauty bonus.** F12 still "
        "scores trades with `entry_inside_chemical_reaction=False` "
        "because the Aggregator does not yet flag entry-inside-CR. "
        "Wiring lands in Phi4.1.\n"
        "7. **Squad-vs-baseline comparator caveat.** The Phi3 baseline "
        "ran on EURUSD ONLY. The Phi4 squad ran on EURUSD + USDCAD "
        "because Barou is USDCAD-only. The TQS ratio is calculated "
        "against EURUSD-only Isagi-alone -- an apples-to-apples "
        "Isagi-also-on-USDCAD comparator was deemed redundant by the "
        "user spec.\n"
    )
    lines.append("")
    lines.append("## References\n")
    lines.append(
        "- Phi3 gate (Isagi-alone): `reviews/phi3_gate_isagi_v1.md`\n"
        "- Doctrine: `06-blue-lock-doctrine.md` sec 3.3 / 3.4 / 4.2 / 4.3\n"
        "- Roster (MVP Phi4 v1): `05-agent-roster-v0.md` sec 1.1\n"
        "- Experiment architecture: `09-experiment-architecture.md` sec 1.5 (G5)\n"
        "- E005 USDCAD baseline-zone prior: `audits/2026-06-24_E001-E007_audit.md` sec 4.3\n"
        "- E006 equal_highs_pool prior: same audit sec 2.6 + 4.3\n"
        "- Rejection analysis (companion): `reviews/phi4_isagi_rejection_analysis.md`\n"
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Cross-striker rejection analysis
# ---------------------------------------------------------------------------

@dataclass
class _RejectionBucketCounts:
    same_direction: int = 0
    opposite_direction: int = 0
    silent: int = 0
    own_setup_elsewhere: int = 0


def render_rejection_analysis(
    *,
    isagi_rejections: list[dict],
    thoughts_by_tick: dict[int, list[Thought]],
    proposals_by_tick: dict[int, list[AgentProposal]],
    full_start: datetime,
    full_end: datetime,
) -> tuple[str, _RejectionBucketCounts]:
    """Build the cross-striker rejection-analysis report.

    Buckets per user spec (observational, NOT a backtest of an
    alternative policy):

      * "Squad would have traded same direction" --
        ANY non-Isagi striker had a Proposal in Isagi's direction at
        the same tick (on any symbol).
      * "Squad would have traded opposite direction"
      * "Squad stayed silent"
      * "Squad had own setup elsewhere" (proposal but different symbol)
    """
    buckets = _RejectionBucketCounts()
    detail_rows: list[dict] = []

    for rej in isagi_rejections:
        tick_id = int(rej["tick_id"])
        symbol = rej["symbol"]
        direction = rej["loser_direction"]
        peer_props = [
            p for p in proposals_by_tick.get(tick_id, [])
            if p.agent_id != "isagi_yoichi"
        ]
        same_sym_peers = [p for p in peer_props if p.symbol == symbol]
        other_sym_peers = [p for p in peer_props if p.symbol != symbol]
        if any(p.direction == direction for p in same_sym_peers):
            bucket = "same_direction"
            buckets.same_direction += 1
        elif any(p.direction != direction for p in same_sym_peers):
            bucket = "opposite_direction"
            buckets.opposite_direction += 1
        elif other_sym_peers:
            bucket = "own_setup_elsewhere"
            buckets.own_setup_elsewhere += 1
        else:
            bucket = "silent"
            buckets.silent += 1
        detail_rows.append({
            "tick_id": tick_id,
            "symbol": symbol,
            "isagi_direction": direction,
            "bucket": bucket,
            "peer_proposals": [
                {
                    "agent_id": p.agent_id,
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "conviction": float(p.conviction),
                }
                for p in peer_props
            ],
        })

    lines: list[str] = []
    lines.append(
        "# Phi4 cross-striker rejection analysis -- Isagi v1 rejected proposals\n"
    )
    lines.append(
        f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n"
    )
    lines.append(
        f"**Window:** {full_start.date()} -> {full_end.date()} on "
        "EURUSD + USDCAD H4.\n"
    )
    lines.append(
        "**Companion to:** `reviews/phi4_squad_v1.md`. The squad gate "
        "report is the verdict; this doc is the per-rejection diagnostic.\n"
    )
    lines.append("---\n")
    lines.append("## Honest framing (read this first)\n")
    lines.append(
        "This is an **observational counterfactual analysis**, NOT a "
        "backtest of an alternative policy. For each Isagi v1 rejected "
        "proposal (the proposal would have opened a trade if Isagi were "
        "the sole striker, but the squad's per-symbol single-position "
        "rule or the aggregator's highest-conviction-wins rule blocked "
        "it), we look up what the other strikers thought at the EXACT "
        "same tick.\n"
    )
    lines.append(
        "Biases that make this NOT a tradable signal:\n"
        "- The peer thought was emitted at the same tick; in a counterfactual "
        "  policy where the peer's proposal HAD been taken, downstream ticks "
        "  would have produced different ledger state -- the rejection set "
        "  itself would be different.\n"
        "- No slippage feedback from the alternative-policy trades.\n"
        "- Survivor bias on the squad's other proposals (we only observe "
        "  what made it to the proposal layer; sub-conviction-floor "
        "  thoughts are not counted).\n"
        "- 'Counterfactual TQS' would require a re-run with the alternative "
        "  proposal acted on -- out of scope for the v1 diagnostic.\n"
    )
    lines.append("---\n")
    lines.append("## Bucket distribution\n")
    total = (
        buckets.same_direction
        + buckets.opposite_direction
        + buckets.silent
        + buckets.own_setup_elsewhere
    )
    def _pct(n: int) -> str:
        return f"{(100.0 * n / total):.1f}%" if total else "n/a"
    lines.append("")
    lines.append("| Bucket | n | % |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Squad would have traded SAME direction | "
        f"{buckets.same_direction} | {_pct(buckets.same_direction)} |"
    )
    lines.append(
        f"| Squad would have traded OPPOSITE direction | "
        f"{buckets.opposite_direction} | {_pct(buckets.opposite_direction)} |"
    )
    lines.append(
        f"| Squad stayed silent | "
        f"{buckets.silent} | {_pct(buckets.silent)} |"
    )
    lines.append(
        f"| Squad had own setup elsewhere | "
        f"{buckets.own_setup_elsewhere} | {_pct(buckets.own_setup_elsewhere)} |"
    )
    lines.append(f"| **Total Isagi rejections analysed** | **{total}** | 100% |")
    lines.append("")
    lines.append("---\n")
    lines.append("## What this tells us\n")
    lines.append(
        "- The **same-direction bucket** is the population where the "
        "squad COULD HAVE LEARNT from Isagi's reasoning: the other "
        "strikers had a coherent read going the same way. Without "
        "Isagi, the squad would have taken the trade anyway.\n"
        "- The **opposite-direction bucket** is the population where "
        "the squad COUNTERED Isagi's read. A high count here would "
        "argue for a diversity benefit -- Isagi was vetoed by peers.\n"
        "- The **silent bucket** is where Isagi was alone -- the "
        "squad added nothing to the deliberation on that tick.\n"
        "- The **own-setup-elsewhere bucket** is where Isagi's "
        "rejection coincided with the squad allocating attention to a "
        "different symbol. Cross-pair drag, in the audit's phrasing.\n"
    )
    lines.append("---\n")
    lines.append("## References\n")
    lines.append(
        "- Squad gate report: `reviews/phi4_squad_v1.md`\n"
        "- Per-trade JSONL: `reviews/phi3_gate_isagi_v1_trades.jsonl`\n"
        "- Doctrine: `06-blue-lock-doctrine.md` sec 3.9 (Tier model) + 5 (the opponent)\n"
        "- Source: this run's `proposals_all.jsonl` + `rejected_proposals.jsonl`\n"
    )
    return "\n".join(lines) + "\n", buckets


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_squad_gate(
    *,
    full_start: datetime = DEFAULT_FULL_START,
    full_end: datetime = DEFAULT_FULL_END,
    out_dir: Path | str | None = None,
    delta_info_windows: int = DEFAULT_DELTA_INFO_WINDOWS,
    write_jsonl: bool = True,
) -> SquadGateReport:
    """Run the Phi4 squad gate end-to-end and write both reviews."""
    ensure_production_repo_on_path()
    log.info(
        "Loading squad bars %s -> %s on EURUSD + USDCAD H4",
        full_start.date(), full_end.date(),
    )
    bars_by_symbol: dict[str, list] = {}
    for sym in SYMBOLS_DEV:
        bars_by_symbol[sym] = _load_production_bars(sym, full_start, full_end)
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    # Construct the 4-agent squad.
    isagi = A1IsagiV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    for sym, bars in bars_by_symbol.items():
        if bars and sym in isagi.symbols:
            isagi.prepare(sym, bars)
        if bars and sym in barou.symbols:
            barou.prepare(sym, bars)
    agents = [isagi, nagi, barou, kunigami]

    # Full squad run on the FullLedger.
    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=agents,
        isagi=isagi,
        barou=barou,
        kunigami=kunigami,
        bars_by_symbol=bars_by_symbol,
        ledger=ledger,
    )
    log.info(
        "Squad run done -- %d thoughts, %d proposals, %d trades",
        len(out.thoughts), len(out.proposals_all), len(out.trades),
    )

    # Per-agent stats.
    all_agent_ids = tuple(sorted(a.agent_id for a in agents))
    per_agent_overall: dict[str, dict[str, float]] = {}
    per_agent_trade_counts: dict[str, int] = {}
    for aid in all_agent_ids:
        ag_trades = [t for t in out.trades if t.agent_id == aid]
        mean_p, med_p, mean_tqs, wr, n = _summarise(ag_trades)
        per_agent_overall[aid] = {
            "n": float(n),
            "mean_pips": float(mean_p),
            "median_pips": float(med_p),
            "mean_tqs": float(mean_tqs),
            "win_rate": float(wr),
        }
        per_agent_trade_counts[aid] = int(n)

    # Walk-forward windows.
    windows = _compute_squad_windows(
        out.trades,
        full_start=full_start, full_end=full_end,
        all_agent_ids=all_agent_ids,
    )
    oos_mean_pips = [w.squad_oos_mean_pips for w in windows if w.squad_oos_n > 0]
    oos_mean_tqs = [w.squad_oos_mean_tqs for w in windows if w.squad_oos_n > 0]
    median_oos_pips = (
        statistics.median(oos_mean_pips) if oos_mean_pips else 0.0
    )
    mean_oos_pips = (
        statistics.mean(oos_mean_pips) if oos_mean_pips else 0.0
    )
    median_oos_tqs = (
        statistics.median(oos_mean_tqs) if oos_mean_tqs else 0.0
    )
    oos_positive = sum(
        1 for w in windows
        if w.squad_oos_n > 0 and w.squad_oos_mean_pips > 0
    )
    ratio = (
        median_oos_tqs / ISAGI_ALONE_MEDIAN_OOS_TQS
        if ISAGI_ALONE_MEDIAN_OOS_TQS > 0 else 0.0
    )

    # F17 ΔInfo: sample `delta_info_windows` of the 7 OOS windows.
    delta_results: dict[str, DeltaInfoResult] = {}
    sampled_windows = _sample_windows(windows, n=delta_info_windows)
    for candidate_id, candidate_class in (
        ("nagi_seishiro", A6NagiV1),
        ("barou_shoei", A7BarouV1),
    ):
        informed = [
            t.tqs_components["tqs"]
            for t in out.trades if t.agent_id == candidate_id
        ]
        isolated_tqs: list[float] = []
        for w in sampled_windows:
            log.info(
                "F17 isolated arm: %s on %d-%d",
                candidate_id, w.is_start.year, w.oos_end.year,
            )
            iso_trades = _run_isolated_window(
                agent_class=candidate_class,
                agent_kwargs={"agent_id": candidate_id},
                bars_by_symbol=bars_by_symbol,
                is_start=w.is_start, is_end=w.is_end,
                oos_start=w.oos_start, oos_end=w.oos_end,
                isagi_for_prep=isagi,
                barou_for_prep=barou,
                kunigami_for_prep=kunigami,
            )
            isolated_tqs.extend(
                t.tqs_components["tqs"] for t in iso_trades
            )
        di = delta_info(
            candidate_id,
            informed,
            isolated_tqs,
            n_resamples=1000,
            block_size=5,
            seed=4242,
        )
        delta_results[candidate_id] = di

    # Engine-stream telemetry counts.
    nagi_fired = sum(
        1 for t in out.thoughts
        if "nagi_confluence" in t.tags
    )
    devour_fired = sum(
        1 for t in out.thoughts
        if "barou_devour_applied" in t.tags
    )
    kuni_warned = sum(
        1 for t in out.thoughts
        if "kunigami_loss_streak_warning" in t.tags
        or "kunigami_overconfidence_warning" in t.tags
    )
    # Sentinel counts wired 2026-06-30 (Phi4.2 mini-sprint). Audit-only in
    # the Phi4 harness -- decisions journalled to out.sentinel_log but do
    # not block trades. Phi5 harnesses pass sentinel_blocks=True.
    sentinel_counts: dict[str, int] = summarise_sentinel_log(out.sentinel_log)

    verdict, reason = "PENDING", ""
    report = SquadGateReport(
        full_start=full_start, full_end=full_end,
        symbols=SYMBOLS_DEV,
        n_thoughts=len(out.thoughts),
        n_proposals_all=len(out.proposals_all),
        n_proposals_accepted=len(out.proposals_accepted),
        n_proposals_rejected=len(out.proposals_rejected),
        n_trades=len(out.trades),
        per_agent_trade_counts=per_agent_trade_counts,
        per_agent_overall_kpis=per_agent_overall,
        squad_median_oos_window_mean_pips=median_oos_pips,
        squad_mean_oos_window_mean_pips=mean_oos_pips,
        squad_median_oos_window_mean_tqs=median_oos_tqs,
        squad_oos_windows_positive=oos_positive,
        squad_oos_windows_total=len(windows),
        isagi_alone_median_oos_pips=ISAGI_ALONE_MEDIAN_OOS_PIPS,
        isagi_alone_median_oos_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS,
        squad_vs_isagi_tqs_ratio=float(ratio),
        verdict=verdict,
        verdict_reason=reason,
        windows=windows,
        delta_info_results=delta_results,
        sentinel_trigger_counts=sentinel_counts,
        nagi_fired_count=int(nagi_fired),
        devour_fired_count=int(devour_fired),
        kunigami_warning_count=int(kuni_warned),
    )
    report.verdict, report.verdict_reason = _decide_squad_verdict(report)
    log.info(
        "Phi4 squad gate verdict: %s (squad TQS %.3f, ratio %.2fx)",
        report.verdict, report.squad_median_oos_window_mean_tqs, ratio,
    )

    # Resolve out_dir.
    if out_dir is None:
        out_dir = (
            Path(__file__).resolve().parents[2] / "reviews"
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist artefacts.
    (out_dir / "phi4_squad_v1.md").write_text(
        render_squad_report(report), encoding="utf-8",
    )
    log.info("Wrote squad gate report to %s", out_dir / "phi4_squad_v1.md")

    if write_jsonl:
        with (out_dir / "phi4_squad_v1_trades.jsonl").open("w", encoding="utf-8") as fh:
            for t in out.trades:
                fh.write(json.dumps({
                    "agent_id": t.agent_id,
                    "symbol": t.symbol,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "direction": t.direction,
                    "entry": t.entry, "stop": t.stop,
                    "take_profit": t.take_profit, "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pnl_pips": t.pnl_pips,
                    "mae_pips": t.mae_pips, "mfe_pips": t.mfe_pips,
                    "r_multiple": t.r_multiple,
                    "tqs": t.tqs_components,
                }, sort_keys=True) + "\n")
        with (out_dir / "phi4_squad_v1_rejected_proposals.jsonl").open("w", encoding="utf-8") as fh:
            for row in out.proposals_rejected:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
        with (out_dir / "phi4_squad_v1_proposals_all.jsonl").open("w", encoding="utf-8") as fh:
            for p in out.proposals_all:
                fh.write(json.dumps(p.to_jsonable(), sort_keys=True) + "\n")
        log.info("Wrote squad trades + proposals JSONL")

    # Rejection analysis -- companion report.
    proposals_by_tick: dict[int, list[AgentProposal]] = {}
    for p in out.proposals_all:
        proposals_by_tick.setdefault(int(p.tick_id), []).append(p)
    thoughts_by_tick: dict[int, list[Thought]] = {}
    for t in out.thoughts:
        thoughts_by_tick.setdefault(int(t.tick_id), []).append(t)
    isagi_rejections = [
        r for r in out.proposals_rejected
        if r.get("loser_agent_id") == "isagi_yoichi"
    ]
    rej_md, rej_buckets = render_rejection_analysis(
        isagi_rejections=isagi_rejections,
        thoughts_by_tick=thoughts_by_tick,
        proposals_by_tick=proposals_by_tick,
        full_start=full_start, full_end=full_end,
    )
    (out_dir / "phi4_isagi_rejection_analysis.md").write_text(
        rej_md, encoding="utf-8",
    )
    log.info(
        "Rejection analysis: same=%d, opposite=%d, silent=%d, elsewhere=%d",
        rej_buckets.same_direction, rej_buckets.opposite_direction,
        rej_buckets.silent, rej_buckets.own_setup_elsewhere,
    )

    return report


def _sample_windows(
    windows: list[SquadWindowStats], *, n: int,
) -> list[SquadWindowStats]:
    """Deterministic subsampling of `n` windows for the F17 isolated arm.

    Pick windows with the largest squad OOS trade count first (gives
    the F17 bootstrap the most samples per window). If `n >= len(windows)`,
    returns all windows.
    """
    if n >= len(windows):
        return list(windows)
    sorted_w = sorted(
        windows, key=lambda w: w.squad_oos_n, reverse=True,
    )
    chosen = sorted_w[:n]
    return sorted(chosen, key=lambda w: w.oos_start)


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the M001 Phi4 squad gate (4-agent MVP vs Isagi-alone).",
    )
    parser.add_argument(
        "--start", type=_parse_date,
        default=DEFAULT_FULL_START.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end", type=_parse_date,
        default=DEFAULT_FULL_END.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="Output directory (default: <repo>/programs/.../reviews/)",
    )
    parser.add_argument(
        "--delta-info-windows", type=int, default=DEFAULT_DELTA_INFO_WINDOWS,
        help="How many of the 7 OOS windows to use for F17 (default 3).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    start = args.start if isinstance(args.start, datetime) else _parse_date(args.start)
    end = args.end if isinstance(args.end, datetime) else _parse_date(args.end)
    report = run_squad_gate(
        full_start=start, full_end=end,
        out_dir=args.out_dir,
        delta_info_windows=int(args.delta_info_windows),
    )
    print(
        f"Phi4 squad gate verdict: {report.verdict} "
        f"({report.n_trades} trades; squad TQS "
        f"{report.squad_median_oos_window_mean_tqs:.3f} vs Isagi-alone "
        f"{ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}; ratio "
        f"{report.squad_vs_isagi_tqs_ratio:.2f}x)"
    )
    return 0 if report.verdict in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
