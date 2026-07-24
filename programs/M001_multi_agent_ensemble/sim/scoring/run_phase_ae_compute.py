"""Phase AE — Sae Itoshi event-specialist walk-forward harness.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/
        phase_ae_sae_event_specialist/PROTOCOL.md
    (LOCKED 2026-07-24; §0 pre-run amendments cover everything this
    module does that the 2026-07-20 draft's §7 wording didn't.)

What this does
--------------

Runs ONE arm of the Phase AE evaluation over the §11.17 walk-forward
panel (2015-2025, 4-yr IS / 1-yr OOS × 7 windows, symbols
EURUSD/GBPUSD/USDCAD, g7retry2-shaped roster: 7 proposers, Kunigami
retired to the Sentinel R5 side channel, phi41 aggregator,
sentinel_blocks=True, workspace ON, R7 absent by construction):

- ``--sae-enabled`` OFF  → baseline arm (must reproduce the plain
  ``_drive_squad_replay`` stream byte-for-byte; guarded by
  ``tests/test_phase_ae_harness.py`` equivalence test).
- ``--sae-enabled`` ON   → treatment arm: Sae (sim port
  ``sim/agents/a09_sae.py``) is evaluated at M15 event ticks
  (T+15 / T+30 around each frozen-calendar event) injected into the
  H4 replay in strict wall-clock order. Sae trades open and manage
  on M15 bars; they share the per-symbol single-position slot with
  the H4 squad in BOTH directions (PROTOCOL §0 amendment 4).

Driver-copy honesty note
------------------------

``_drive_squad_replay_ae`` is a phi41-specialised adaptation of
``run_phi4_squad_gate._drive_squad_replay`` (fixed flags:
sentinel_blocks=True, use_workspace=True, aggregator_arm="phi41",
no shadow ledger, no kunigami wildcard gate — exactly the g7retry2
verdict-bearing configuration). All ``# AE:``-marked blocks are the
only additions. With ``sae=None`` every AE block is inert and the
trade/proposal/rejection stream must equal the original driver's —
the pre-run equivalence test enforces this; do NOT edit one driver
without re-running that test.

CLI
---

::

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_phase_ae_compute \\
        [--sae-enabled] --tag ae-baseline \\
        --out-dir programs/M001_multi_agent_ensemble/experiments/\\
phase_ae_sae_event_specialist/results/
"""
from __future__ import annotations

import argparse
import bisect
import itertools
import json
import logging
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
from programs.M001_multi_agent_ensemble.sim.agents.a05_reo import A5ReoV1
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
    A9SaeV1,
    SaeConfig,
    SimNewsEvent,
    load_frozen_calendar,
)
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    A10KunigamiV1,
    ClosedTradeRecord,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
    WorkspaceSnapshot,
)
from programs.M001_multi_agent_ensemble.sim.core.sentinel import (
    SentinelContext,
    evaluate_proposal as sentinel_evaluate_proposal,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    MarketState,
    Thought,
    YieldReason,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    G7_PANEL_END,
    G7_PANEL_START,
    WalkForwardWindow,
    _g7_windows,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    WARMUP_BARS,
    TradeRecord,
    _bar_to_market_state,
    _check_exit,
    _load_production_bars,
    _open_trade_from_proposal,
    _score_trade,
    _update_excursion,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    SANDBOX_EQUITY_DOLLARS,
    SANDBOX_PIP_VALUE_PER_MIN_LOT,
    SquadRunOutput,
    _AgentScopedSnapshot,
    _agent_target_hold_hours,
    _annotate_trade_record,
    _interleave_bars,
    _phi4_aggregate,
    _sentinel_log_entry,
)

log = logging.getLogger(__name__)

SYMBOLS_AE: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
SAE_SYMBOL = "EURUSD"
# Sae M15 event ticks get their own tick-id namespace so they can never
# collide with global H4 tick ids (~50k on the full panel).
SAE_TICK_ID_BASE = 50_000_000
_M15 = timedelta(minutes=15)
_H4 = timedelta(hours=4)

DEFAULT_CALENDAR_PATH = (
    Path("programs/M001_multi_agent_ensemble/data")
    / "news_calendar_frozen_2026-07-24.json"
)


def _load_production_bars_m15(
    symbol: str, start: datetime, end: datetime,
) -> list:
    """Load OHLCV M15 bars from the production parquet cache (read-only)."""
    ensure_production_repo_on_path()
    from agent.config import load_config  # noqa: E402
    from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
    from agent.types import Timeframe  # noqa: E402

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    df = loader.get(symbol, Timeframe.M15, start, end, refresh=False)
    return df_to_bars(df, Timeframe.M15)


def build_sae_event_ticks(
    events: list[SimNewsEvent],
    *,
    panel_start: datetime,
    panel_end: datetime,
    fade_wait_min: int = 15,
    ride_wait_min: int = 30,
) -> list[datetime]:
    """T+15 / T+30 M15 tick instants for every high-impact USD event."""
    ticks: set[datetime] = set()
    for e in events:
        if e.currency.upper() != "USD" or e.impact.lower() != "high":
            continue
        if not (panel_start <= e.time_utc <= panel_end):
            continue
        ticks.add(e.time_utc + timedelta(minutes=fade_wait_min))
        ticks.add(e.time_utc + timedelta(minutes=ride_wait_min))
    return sorted(ticks)


# ---------------------------------------------------------------------------
# AE driver (phi41-specialised copy of _drive_squad_replay + AE blocks)
# ---------------------------------------------------------------------------

def _drive_squad_replay_ae(
    *,
    agents: list,
    isagi: A1IsagiV1,
    barou: A7BarouV1,
    kunigami: A10KunigamiV1,
    bars_by_symbol: dict[str, list],
    ledger,
    warmup_bars: int = WARMUP_BARS,
    sae: A9SaeV1 | None = None,
    sae_m15_bars: list | None = None,
    sae_event_ticks: list[datetime] | None = None,
) -> tuple[SquadRunOutput, list[dict]]:
    """phi41 squad replay with optional Sae M15 event-tick injection.

    Behaviour with ``sae=None`` is REQUIRED to be identical to
    ``_drive_squad_replay(sentinel_blocks=True, use_workspace=True,
    use_shadow_ledger=False, aggregator_arm="phi41",
    kunigami_wildcard_gate=False)`` — see the equivalence test.

    Returns ``(SquadRunOutput, sae_trade_meta)`` where the second
    element is one dict per closed Sae trade (mechanic, event, TQS).
    """
    out = SquadRunOutput()
    sae_trade_meta: list[dict] = []
    global_bars = _interleave_bars(bars_by_symbol)
    if not global_bars:
        return out, sae_trade_meta

    open_trades: dict[str, Any] = {}
    cfg = isagi._cfg                       # cfg shared across wrappers

    per_agent_consecutive_losses: dict[str, int] = {}
    per_agent_proposals_today: dict[str, int] = {}
    current_day: Any = None

    workspace = ReasoningWorkspace()
    workspace_publish_counts: dict[str, int] = {}
    workspace_read_counts: dict[str, int] = {}

    sorted_bars_by_symbol: dict[str, list] = {
        sym: bars for sym, bars in bars_by_symbol.items()
    }

    bars_seen_per_sym: dict[str, int] = {sym: 0 for sym in bars_by_symbol}
    n_bars_per_sym: dict[str, int] = {
        sym: len(bars) for sym, bars in bars_by_symbol.items()
    }

    # AE: hold-hours lookup must resolve Sae (he is NOT in ``agents`` --
    # he never participates in the H4 observe/intend phases).
    agents_for_hold = list(agents) + ([sae] if sae is not None else [])

    def _finalise_closed_trade(ot, *, tick_id: int, sym: str) -> None:
        """Score + journal one closed trade (identical to the original
        driver's closure, plus the AE Sae-meta capture)."""
        tr = _score_trade(
            ot, _agent_target_hold_hours(ot, agents_for_hold),
        )
        tr_with_agent = _annotate_trade_record(
            tr, ot, tick_id, sym,
        )
        out.trades.append(tr_with_agent)
        kunigami.record_closed_trade(ClosedTradeRecord(
            agent_id=tr_with_agent.agent_id,
            exit_time=tr_with_agent.exit_time,
            pnl_pips=tr_with_agent.pnl_pips,
            source_conviction=float(
                getattr(ot, "_source_conviction", 0.0)
            ),
        ))
        _aid = tr_with_agent.agent_id
        if tr_with_agent.pnl_pips <= 0:
            per_agent_consecutive_losses[_aid] = (
                per_agent_consecutive_losses.get(_aid, 0) + 1
            )
        else:
            per_agent_consecutive_losses[_aid] = 0
        # AE: capture mechanic split metadata for AE3.
        if sae is not None and _aid == sae.agent_id:
            rat = dict(getattr(ot, "_source_proposal_rationale", {}) or {})
            sae_trade_meta.append({
                "mechanic": rat.get("mechanic", "unknown"),
                "event_title": rat.get("event_title"),
                "event_time": rat.get("event_time"),
                "entry_time": tr_with_agent.entry_time.isoformat(),
                "exit_time": tr_with_agent.exit_time.isoformat(),
                "direction": tr_with_agent.direction,
                "exit_reason": tr_with_agent.exit_reason,
                "pnl_pips": float(tr_with_agent.pnl_pips),
                "r_multiple": float(tr_with_agent.r_multiple),
                "tqs": float(tr_with_agent.tqs_components.get("tqs", 0.0)),
            })

    # ------------------------------------------------------------------
    # AE: Sae M15 timeline state + advance function
    # ------------------------------------------------------------------
    sae_active = bool(sae is not None and sae_m15_bars)
    m15_bars: list = sae_m15_bars or []
    m15_times: list[datetime] = [b.time for b in m15_bars]
    event_ticks: list[datetime] = list(sae_event_ticks or [])
    sae_open_trades: dict[str, Any] = {}
    sae_state = {"mgmt_idx": 0, "event_i": 0}
    sae_tick_counter = itertools.count(start=SAE_TICK_ID_BASE)

    def _sae_journal_reject(p, tick_id: int, reason: str, **extra) -> None:
        out.proposals_rejected.append({
            "tick_id": int(tick_id),
            "symbol": p.symbol,
            "winner_agent_id": p.agent_id,
            "winner_conviction": float(p.conviction),
            "loser_agent_id": p.agent_id,
            "loser_conviction": float(p.conviction),
            "loser_direction": p.direction,
            "winner_direction": p.direction,
            "rejection_reason": reason,
            "timestamp": p.timestamp.isoformat(),
            **extra,
        })

    def _sae_process_event_tick(t: datetime) -> None:
        """One Sae M15 event tick at wall-clock instant ``t``.

        Mirrors the H4 loop's observe → publish → snapshot → intend →
        aggregate → sentinel → single-position-slot → open sequence,
        specialised to the one-agent one-symbol case.
        """
        tick_id = next(sae_tick_counter)
        j = bisect.bisect_left(m15_times, t)   # index of the bar OPENING at t
        if j == 0:
            return                             # no closed M15 bar yet
        prev_bar = m15_bars[j - 1]
        market = MarketState(
            tick_id=tick_id,
            symbol=SAE_SYMBOL,
            timeframe="M15",
            # as_of = the tick INSTANT (M15 close time), not the sim's
            # H4 label-by-open convention -- Sae's mechanics compare
            # as_of against T+15/T+30 wall-clock (PROTOCOL §0 am. 4).
            as_of=t,
            open=float(prev_bar.open),
            high=float(prev_bar.high),
            low=float(prev_bar.low),
            close=float(prev_bar.close),
            volume=float(prev_bar.volume),
        )
        thought = sae.observe(market, ledger)
        ledger.append(thought)
        out.thoughts.append(thought)
        if workspace.publish(thought):
            workspace_publish_counts[sae.agent_id] = (
                workspace_publish_counts.get(sae.agent_id, 0) + 1
            )
        snapshot = workspace.snapshot_at_barrier(
            as_of=t, current_tick=int(tick_id),
        )
        scoped = _AgentScopedSnapshot(
            snapshot, sae.agent_id, workspace_read_counts,
        )
        decision = sae.intend(market, thought, workspace=scoped)
        if decision is None:
            return
        p = decision
        out.proposals_all.append(p)
        per_agent_proposals_today[p.agent_id] = (
            per_agent_proposals_today.get(p.agent_id, 0) + 1
        )
        outcome = _phi4_aggregate([p], tick_id=tick_id)
        out.proposals_accepted.extend(outcome.accepted)
        out.proposals_rejected.extend(outcome.rejected)

        kuni_active = bool(kunigami.warning_active_at(t))
        sentinel_ctx = SentinelContext(
            equity=SANDBOX_EQUITY_DOLLARS,
            pip_value_per_min_lot=SANDBOX_PIP_VALUE_PER_MIN_LOT,
            consecutive_losses=per_agent_consecutive_losses.get(
                p.agent_id, 0,
            ),
            proposals_today_by_agent=dict(per_agent_proposals_today),
            kunigami_loss_streak_active=kuni_active,
        )
        s_decision = sentinel_evaluate_proposal(p, sentinel_ctx)
        out.sentinel_log.append(_sentinel_log_entry(
            tick_id=tick_id,
            proposal=p,
            decision=s_decision,
            kunigami_active=kuni_active,
        ))
        if not s_decision.allowed:
            _sae_journal_reject(
                p, tick_id, f"sentinel_{s_decision.rule}_block",
                sentinel_reason=s_decision.reason,
            )
            return
        # Per-symbol single-position rule -- BOTH books count
        # (PROTOCOL §0 amendment 4: shared slot, both directions).
        if SAE_SYMBOL in open_trades or SAE_SYMBOL in sae_open_trades:
            _sae_journal_reject(
                p, tick_id, "open_position_concurrency_limit",
            )
            return
        if j >= len(m15_bars) or m15_bars[j].time != t:
            # M15 gap right after the tick (holiday/weekend edge):
            # no honest next-bar fill exists; journal + skip.
            _sae_journal_reject(p, tick_id, "sae_no_next_m15_bar")
            return
        next_bar = m15_bars[j]
        try:
            trade = _open_trade_from_proposal(p, next_bar, cfg)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Failed to open Sae trade at tick=%d (%s): %s",
                tick_id, SAE_SYMBOL, exc,
            )
            return
        trade._source_agent_id = p.agent_id                       # type: ignore[attr-defined]
        trade._source_conviction = float(p.conviction)            # type: ignore[attr-defined]
        trade._source_regime_fit = float(p.regime_fit)            # type: ignore[attr-defined]
        trade._source_sl_pips = abs(p.entry - p.stop) * 10000.0   # type: ignore[attr-defined]
        trade._source_atr_pips = None                             # type: ignore[attr-defined]
        trade._source_h1_swing_pips = None                        # type: ignore[attr-defined]
        trade._source_tick_id = int(tick_id)                      # type: ignore[attr-defined]
        trade._source_proposal_rationale = dict(p.rationale)      # type: ignore[attr-defined]
        sae_open_trades[SAE_SYMBOL] = trade
        sae_state["mgmt_idx"] = j

    def _sae_advance(until: datetime | None) -> None:
        """Process pending Sae M15 items in wall-clock order.

        ``until`` is EXCLUSIVE (items at exactly ``until`` wait so the
        H4 bar closing at that instant is processed first — keeps the
        baseline stream untouched on ties). ``None`` = drain fully.
        Management closes beat event ticks on equal timestamps (exits
        before entries, same as the H4 loop).
        """
        if not sae_active:
            return
        while True:
            t_mgmt: datetime | None = None
            if sae_open_trades and sae_state["mgmt_idx"] < len(m15_bars):
                t_mgmt = m15_bars[sae_state["mgmt_idx"]].time + _M15
            t_evt: datetime | None = None
            if sae_state["event_i"] < len(event_ticks):
                t_evt = event_ticks[sae_state["event_i"]]
            candidates: list[tuple[datetime, int]] = []
            if t_mgmt is not None:
                candidates.append((t_mgmt, 0))
            if t_evt is not None:
                candidates.append((t_evt, 1))
            if not candidates:
                return
            t, kind = min(candidates)
            if until is not None and t >= until:
                return
            if kind == 0:
                bar = m15_bars[sae_state["mgmt_idx"]]
                ot = sae_open_trades.get(SAE_SYMBOL)
                _update_excursion(ot, bar)
                if _check_exit(ot, bar, cfg):
                    _finalise_closed_trade(
                        ot,
                        tick_id=int(getattr(ot, "_source_tick_id", 0) or 0),
                        sym=SAE_SYMBOL,
                    )
                    sae_open_trades.pop(SAE_SYMBOL, None)
                else:
                    sae_state["mgmt_idx"] += 1
            else:
                _sae_process_event_tick(t)
                sae_state["event_i"] += 1

    # ------------------------------------------------------------------
    # Main replay loop (verbatim from _drive_squad_replay, phi41 paths,
    # plus the two marked AE lines)
    # ------------------------------------------------------------------
    total_bars = len(global_bars)
    progress_interval_bars = max(1, total_bars // 20)      # 5 pct
    progress_interval_seconds = 600                        # 10 min
    _replay_start_ts = time.time()
    _last_progress_ts = _replay_start_ts
    log.info(
        "Phase AE squad replay starting: %d global bars across %d symbols "
        "(sae_active=%s, %d event ticks)",
        total_bars, len(bars_by_symbol), sae_active, len(event_ticks),
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
                "Phase AE replay progress: %d/%d bars (%.1f%%), "
                "elapsed=%.1f s, eta=%.1f s, trades=%d, proposals_all=%d",
                i_gb, total_bars, _pct, _elapsed, _eta_s,
                len(out.trades), len(out.proposals_all),
            )
            _last_progress_ts = time.time()
        symbol = gb.symbol
        i_sym = gb.bar_index_in_symbol
        bar = gb.bar

        # AE: bring Sae's M15 timeline up to (but excluding) this H4
        # bar's close instant. Inert when sae is None.
        _sae_advance(bar.time + _H4)

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
                _finalise_closed_trade(ot, tick_id=gb.tick_id, sym=symbol)
                open_trades.pop(symbol, None)

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
            if workspace.publish(t):
                workspace_publish_counts[agent.agent_id] = (
                    workspace_publish_counts.get(agent.agent_id, 0) + 1
                )

        if bars_seen_per_sym[symbol] <= warmup_bars:
            continue
        if i_sym >= n_bars_per_sym[symbol] - 1:
            continue

        base_snapshot: WorkspaceSnapshot | None = workspace.snapshot_at_barrier(
            as_of=bar.time,
            current_tick=int(gb.tick_id),
        )

        # ---- Phase 2: intend ------------------------------------------
        proposals_this_tick = []
        for agent in eligible:
            if market.timeframe != agent.home_tf:
                continue
            t = my_thought[agent.agent_id]
            scoped = _AgentScopedSnapshot(
                base_snapshot, agent.agent_id, workspace_read_counts,
            )
            decision = agent.intend(market, t, workspace=scoped)
            if isinstance(decision, YieldReason):
                out.yields.append(decision)
                continue
            if decision is None:
                continue
            p = decision
            proposals_this_tick.append(p)
            out.proposals_all.append(p)
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

        kuni_active = bool(kunigami.warning_active_at(bar.time))
        symbol_candidates = outcome.ranked_by_symbol.get(symbol, [])
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
            if not decision.allowed:
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
            # AE: the single-position guard also counts Sae's M15 book
            # (empty whenever sae is None -> baseline byte-identical).
            if symbol in open_trades or symbol in sae_open_trades:
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
            next_bar = sorted_bars_by_symbol[symbol][i_sym + 1]
            try:
                trade = _open_trade_from_proposal(proposal, next_bar, cfg)
                trade._source_agent_id = proposal.agent_id   # type: ignore[attr-defined]
                trade._source_conviction = float(proposal.conviction)  # type: ignore[attr-defined]
                trade._source_regime_fit = float(proposal.regime_fit)  # type: ignore[attr-defined]
                trade._source_sl_pips = abs(proposal.entry - proposal.stop) * 10000.0  # type: ignore[attr-defined]
                _rat = proposal.rationale or {}
                trade._source_atr_pips = _rat.get("atr_pips")  # type: ignore[attr-defined]
                trade._source_h1_swing_pips = _rat.get("h1_swing_pips")  # type: ignore[attr-defined]
                trade._source_tick_id = int(gb.tick_id)      # type: ignore[attr-defined]
                trade._source_proposal_rationale = dict(proposal.rationale)  # type: ignore[attr-defined]
                _winner_aid = _rat.get("arm3_winner_agent_id")
                if _winner_aid:
                    trade._source_winner_agent_id = str(_winner_aid)  # type: ignore[attr-defined]
                open_trades[symbol] = trade
                break
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "Failed to open trade from proposal at tick=%d (%s/%s): %s",
                    gb.tick_id, symbol, proposal.agent_id, exc,
                )

    # AE: drain any remaining Sae items past the final H4 bar.
    _sae_advance(None)

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
            tr = _score_trade(ot, _agent_target_hold_hours(ot, agents_for_hold))
            out.trades.append(
                _annotate_trade_record(tr, ot, gb.tick_id, symbol),
            )
            open_trades.pop(symbol, None)

    # AE: same end-of-data close for a still-open Sae trade (managed on
    # M15 bars, so the last M15 bar is its final mark).
    for symbol, ot in list(sae_open_trades.items()):
        if ot.exit_time is None and m15_bars:
            last = m15_bars[-1]
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
            tr = _score_trade(ot, _agent_target_hold_hours(ot, agents_for_hold))
            tr_final = _annotate_trade_record(
                tr, ot, int(getattr(ot, "_source_tick_id", 0) or 0), symbol,
            )
            out.trades.append(tr_final)
            rat = dict(getattr(ot, "_source_proposal_rationale", {}) or {})
            sae_trade_meta.append({
                "mechanic": rat.get("mechanic", "unknown"),
                "event_title": rat.get("event_title"),
                "event_time": rat.get("event_time"),
                "entry_time": tr_final.entry_time.isoformat(),
                "exit_time": tr_final.exit_time.isoformat(),
                "direction": tr_final.direction,
                "exit_reason": tr_final.exit_reason,
                "pnl_pips": float(tr_final.pnl_pips),
                "r_multiple": float(tr_final.r_multiple),
                "tqs": float(tr_final.tqs_components.get("tqs", 0.0)),
            })
            sae_open_trades.pop(symbol, None)

    out.workspace_publish_counts = dict(workspace_publish_counts)
    out.workspace_read_counts = dict(workspace_read_counts)

    _replay_elapsed = time.time() - _replay_start_ts
    log.info(
        "Phase AE replay complete: %d bars in %.1f s (%.0f bars/s), "
        "trades=%d, proposals_all=%d, sae_trades=%d",
        total_bars, _replay_elapsed,
        total_bars / max(_replay_elapsed, 1e-6),
        len(out.trades), len(out.proposals_all), len(sae_trade_meta),
    )
    return out, sae_trade_meta


# ---------------------------------------------------------------------------
# Walk-forward runner
# ---------------------------------------------------------------------------

def build_ae_roster() -> tuple[list, A1IsagiV1, A7BarouV1, A10KunigamiV1]:
    """g7retry2-shaped roster: 7 proposers, Kunigami retired to the
    Sentinel R5 side channel (G7 §11.12). Phase Z / AA / AB / Y-v1.3
    weapons are the committed constructor defaults."""
    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    agents = [isagi, bachira, rin, chigiri, reo, nagi, barou]
    return agents, isagi, barou, kunigami


def run_phase_ae_arm(
    *,
    sae_enabled: bool,
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    symbols: tuple[str, ...] = SYMBOLS_AE,
    calendar_path: Path = DEFAULT_CALENDAR_PATH,
    out_dir: Path | str | None = None,
    tag: str = "ae-arm",
) -> dict:
    """Run one Phase AE arm end-to-end; write results JSON + trade cache."""
    ensure_production_repo_on_path()
    windows = _g7_windows(panel_start, panel_end)
    log.info(
        "Phase AE arm '%s': sae_enabled=%s | panel %s -> %s | %d windows",
        tag, sae_enabled, panel_start.date(), panel_end.date(), len(windows),
    )

    bars_by_symbol: dict[str, list] = {}
    for sym in symbols:
        bars_by_symbol[sym] = _load_production_bars(sym, panel_start, panel_end)
        log.info("Loaded %d %s H4 bars", len(bars_by_symbol[sym]), sym)

    agents, isagi, barou, kunigami = build_ae_roster()
    # Same explicit prepare set as run_g7_walk_forward (baseline fidelity).
    bachira, rin, chigiri = agents[1], agents[2], agents[3]
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in (isagi, bachira, rin, chigiri, barou):
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)
    agents_by_id = {a.agent_id: a for a in agents}

    sae: A9SaeV1 | None = None
    sae_m15_bars: list | None = None
    sae_event_ticks: list[datetime] | None = None
    n_events = 0
    if sae_enabled:
        events = load_frozen_calendar(calendar_path)
        n_events = len(events)
        sae = A9SaeV1(config=SaeConfig(sae_enabled=True))
        sae.load_calendar(events=events)
        sae_m15_bars = _load_production_bars_m15(
            SAE_SYMBOL, panel_start, panel_end,
        )
        log.info(
            "Loaded %d EURUSD M15 bars + %d calendar events",
            len(sae_m15_bars), n_events,
        )
        m15_times = [b.time for b in sae_m15_bars]

        def _m15_provider(
            symbol: str, start: datetime, end: datetime,
        ) -> list:
            """Closed-bar M15 provider (Sae calls with end=as_of+1min).

            Only bars FULLY CLOSED by ``end`` are returned -- the
            forming bar is never visible (no look-ahead)."""
            if symbol != SAE_SYMBOL:
                return []
            lo = bisect.bisect_left(m15_times, start)
            hi = bisect.bisect_right(m15_times, end)
            return [
                b for b in sae_m15_bars[lo:hi]
                if b.time + _M15 <= end
            ]

        sae.set_bars_provider(_m15_provider)
        sae_event_ticks = build_sae_event_ticks(
            events, panel_start=panel_start, panel_end=panel_end,
        )
        log.info("Built %d Sae M15 event ticks", len(sae_event_ticks))

    ledger = FullLedger()
    out, sae_trade_meta = _drive_squad_replay_ae(
        agents=agents, isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol, ledger=ledger,
        sae=sae, sae_m15_bars=sae_m15_bars, sae_event_ticks=sae_event_ticks,
    )

    # Crash-proof trade dump BEFORE any aggregation (G7 lesson 2026-07-01).
    results: dict[str, Any] = {}
    odir: Path | None = Path(out_dir) if out_dir is not None else None
    if odir is not None:
        cache_dir = odir / f"ae_replay_cache_{tag}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        with (cache_dir / "trades.jsonl").open("w", encoding="utf-8") as fh:
            for t in out.trades:
                fh.write(json.dumps(asdict(t), default=str) + "\n")
        (cache_dir / "sae_trade_meta.json").write_text(
            json.dumps(sae_trade_meta, indent=2), encoding="utf-8",
        )
        log.info("AE replay cache written: %s (%d trades)",
                 cache_dir, len(out.trades))

    # Per-agent per-window OOS stats (+ Sae, when present).
    agent_ids = list(agents_by_id.keys()) + (
        [sae.agent_id] if sae is not None else []
    )
    per_window: list[dict] = []
    for w in windows:
        oos_trades = [
            t for t in out.trades
            if w.oos_start <= t.entry_time < w.oos_end
        ]
        row: dict[str, Any] = {
            "window_idx": w.idx,
            "oos_start": w.oos_start.isoformat(),
            "oos_end": w.oos_end.isoformat(),
            "agents": {},
        }
        for aid in agent_ids:
            ag = [t for t in oos_trades if t.agent_id == aid]
            tqs_vals = [float(t.tqs_components.get("tqs", 0.0)) for t in ag]
            row["agents"][aid] = {
                "n_trades": len(ag),
                "mean_tqs": statistics.mean(tqs_vals) if tqs_vals else None,
            }
        per_window.append(row)

    union_oos: dict[str, Any] = {}
    oos_union_trades = [
        t for t in out.trades
        if any(w.oos_start <= t.entry_time < w.oos_end for w in windows)
    ]
    for aid in agent_ids:
        ag = [t for t in oos_union_trades if t.agent_id == aid]
        tqs_vals = [float(t.tqs_components.get("tqs", 0.0)) for t in ag]
        union_oos[aid] = {
            "n_trades": len(ag),
            "mean_tqs": statistics.mean(tqs_vals) if tqs_vals else None,
            "tqs_values": tqs_vals if aid == (sae.agent_id if sae else "") else None,
        }

    results = {
        "tag": tag,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "sae_enabled": bool(sae_enabled),
        "panel": {
            "start": panel_start.isoformat(),
            "end": panel_end.isoformat(),
            "symbols": list(symbols),
            "n_windows": len(windows),
        },
        "roster": sorted(agents_by_id.keys()),
        "config": {
            "aggregator_arm": "phi41",
            "sentinel_blocks": True,
            "use_workspace": True,
            "kunigami": "retired_r5_side_channel",
            "r7": "absent_from_research_sim (PROTOCOL §0 amendment 5)",
            "calendar_fixture": str(calendar_path),
            "n_calendar_events": n_events,
        },
        "totals": {
            "n_trades": len(out.trades),
            "n_proposals_all": len(out.proposals_all),
            "n_rejections": len(out.proposals_rejected),
            "n_thoughts": len(out.thoughts),
        },
        "workspace_publish_counts": dict(out.workspace_publish_counts),
        "workspace_read_counts": dict(out.workspace_read_counts),
        "per_window": per_window,
        "union_oos": union_oos,
        "sae_trade_meta": sae_trade_meta,
    }

    if odir is not None:
        odir.mkdir(parents=True, exist_ok=True)
        results_path = odir / f"results_{tag}.json"
        results_path.write_text(
            json.dumps(results, indent=2, default=str), encoding="utf-8",
        )
        log.info("Wrote %s", results_path)
    return results


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase AE Sae event-specialist walk-forward arm runner.",
    )
    parser.add_argument("--sae-enabled", action="store_true",
                        help="Treatment arm: add Sae at M15 event ticks.")
    parser.add_argument("--start", type=_parse_date,
                        default=G7_PANEL_START.isoformat())
    parser.add_argument("--end", type=_parse_date,
                        default=G7_PANEL_END.isoformat())
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR_PATH)
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path("programs/M001_multi_agent_ensemble/experiments/"
                     "phase_ae_sae_event_specialist/results"))
    parser.add_argument("--tag", type=str, default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    tag = args.tag or ("ae-treatment" if args.sae_enabled else "ae-baseline")
    run_phase_ae_arm(
        sae_enabled=bool(args.sae_enabled),
        panel_start=args.start, panel_end=args.end,
        calendar_path=args.calendar,
        out_dir=args.out_dir, tag=tag,
    )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
