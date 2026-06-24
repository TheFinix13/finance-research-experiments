"""A1 -- Yoichi Isagi v2 (`isagi_yoichi`) -- metavision sharpens (sweep + zone).

A1 Isagi v2 is the *vocabulary-expanded* successor to v1
(`sim/agents/a01_isagi.py`). It satisfies the same BlueLockStriker
contract (`06-blue-lock-doctrine.md` section 4.1) and the §3.11.2
evolution-arc contract:

* **Defeat trigger** documented in `reviews/isagi_yoichi_v1_defeat.md`
  -- 1579 / 52.7 % of v1's Φ4 squad-gate rejections were *redundant*
  with the rest of the squad (same direction); v1's `zone_d1_against`
  vocabulary leaves the rest of the dimensional space unused.
* **Evolution hypothesis** stated *before* this module landed: v2
  preserves the v1 zone-touch core (so the regression test passes
  byte-for-byte on the zone branch) and adds a **second weapon** --
  liquidity-sweep entries read from the production
  `agent.detectors.liquidity_sweep.detect_liquidity_sweeps` causal
  detector. This is a NEW setup vocabulary v1 cannot express (sweeps
  are not zone touches; they cluster around session opens / news /
  equal-highs formations).
* **Doctrine `§3.11.3` sketch alignment** -- the canonical sketch
  promises `equal_highs / equal_lows / liquidity_sweep_high /
  liquidity_sweep_low` + FVG / OB and an H4 → H1 cadence move. v2
  ships the liquidity-sweep half *only*; the H1 cadence move and the
  FVG / OB primitives are **deferred to v3** so the §3.11.2 step 4
  regression contract has a clean byte-equivalent comparator. This is
  declared explicitly in the defeat note §3.

Architecture (two-weapon stack)
-------------------------------

* **Weapon A -- `zone_d1_against` (v1 baseline preserved).** Same
  `SupplyDemandAlpha` instance constructed with `ISAGI_V1_PARAMS`
  (cross-repo import). Same `prepare()` precompute path. Same
  `observe` / `intend` codepath for the zone branch. When the
  production cell fires, v2's proposal is byte-identical to v1's
  (same direction, entry, stop, take-profit, conviction = 0.65).
* **Weapon B -- `liquidity_sweep` (new in v2).** At each H4
  `intend()` call, scan the production `liquidity_sweep` events for
  any sweep whose `sweep_bar_index` falls in
  `(i − SWEEP_MAX_AGE_BARS, i]`. For the freshest such sweep:
    - Direction = `sweep.direction` (LONG for sellside,
      SHORT for buyside) -- this is the *fade-the-extreme* read.
    - HTF gate: require `htf_bias_at(bars, i, htf="D1",
      htf_lookback=10, min_move_pips=60)` to AGREE with the sweep
      direction (D1 already wants the same way as the sweep's
      reaction). NEUTRAL bias blocks the entry (same "no read = no
      trade" rule as v1's zone gate; mirror of the v1 logic but
      flipped because the sweep is a confirmation of the D1 trend
      whereas a zone touch is a fade against it).
    - Entry at `bars[i].close` (the H4 close driving `intend`).
    - Stop at the sweep wick extreme +/- `STOP_ATR_MULT * ATR(14)`
      (0.5x ATR buffer; matches v1's `stop_atr_mult`).
    - Take-profit at `target_rr * stop_distance` from entry
      (1.5R; matches v1's `target_rr`).
    - Conviction `SWEEP_CONVICTION = 0.55` (deliberately lower than
      v1's 0.65 zone-touch conviction so that any cross-weapon
      aggregator prefers the zone-touch proposal; this preserves
      the regression contract "v2 takes every v1 trade").
* **Cross-weapon tiebreaker.** If both weapons fire on the same H4
  bar, v2 returns the zone-touch proposal (legacy-first). The sweep
  proposal is journalled in the Thought's `coordinate.rationale` so
  the behaviour-delta test can still see it.

Public surface (called from the engine)
---------------------------------------

* `observe(market, ledger) -> Thought` -- always emits a Thought
  tagged with `weapon:<zone|sweep|none>` to identify which vocabulary
  fired (or `none` for observation-only).
* `intend(market, my_recent_thought) -> AgentProposal | None` --
  only at H4 close; fires when EITHER weapon's gate passes.

Harness-only surface (mirrors v1 for compatibility with
`run_isagi_phi3_gate._drive_replay`):

* `prepare(symbol, bars)` -- pre-load bars + precompute detector
  context (zones) AND H4 liquidity sweeps (since the production
  `precompute` skips H4 sweeps, we call `detect_liquidity_sweeps`
  directly here).
* `inner_signal_at(symbol, i)` -- direct pass-through to the wrapped
  `SupplyDemandAlpha.signal` for the byte-equivalence regression
  test (`tests/test_a01_isagi_v2.py`).
* `sweep_signal_at(symbol, i)` -- direct pass-through to the v2
  sweep weapon for the behaviour-delta test.

Doctrine traceability
---------------------

`06-blue-lock-doctrine.md` §3.11.2 step 3: "New code surface, cleanly
named. `sim/agents/aXX_<name>_v2.py` sits next to
`sim/agents/aXX_<name>_v1.py`. No in-place mutation of vN's module.
The diff is *additive* at the file-system level." This file is the
additive surface; `sim/agents/a01_isagi.py` is **untouched**.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
    ISAGI_V1_PARAMS,
    ISAGI_V1_SYMBOLS,
    _coordinate_from_signal,
    _meta_to_tags,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import ThoughtLedger
from programs.M001_multi_agent_ensemble.sim.core.striker import BaseStriker
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    AgentProposal,
    CanonRole,
    Coordinate,
    LadderRung,
    MarketState,
    Thought,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# v2 sweep-weapon parameters. See the defeat note for justification.
# ---------------------------------------------------------------------------

# How far back (in H4 bars) a sweep stays "fresh" enough to trade.
# 6 H4 bars = ~1 trading day. Matches v1's zone freshness intuition.
SWEEP_MAX_AGE_BARS: int = 6

# 0.5x ATR(14) buffer behind the sweep wick. Matches v1's stop_atr_mult.
STOP_ATR_MULT: float = 0.5

# 1.5R take-profit. Matches v1's target_rr.
TARGET_RR: float = 1.5

# Sweep conviction is intentionally LOWER than zone conviction (0.65) so any
# cross-weapon aggregator prefers the zone. Preserves the regression contract.
SWEEP_CONVICTION: float = 0.55
ZONE_CONVICTION_FALLBACK: float = 0.65  # mirrors zone_alpha's hard-coded default

# HTF gate -- same params as v1 (D1 lookback=10, min_move_pips=60). v2 inverts
# the *interpretation*: for a sweep entry the D1 bias must AGREE with the
# sweep's reaction direction (sweep IS the confirmation of the D1 trend), so
# we use `bias.matches(direction)` not `bias.opposes(direction)`.
HTF_TF: str = "D1"
HTF_LOOKBACK: int = 10
HTF_MIN_MOVE_PIPS: float = 60.0

# Default canon role -- inherits v1's identity, bumps weapon name to mark v2.
# canon_player and ego stay fixed per doctrine 06 §3.10 (identity vs version).
ISAGI_V2_CANON_ROLE = CanonRole(
    canon_player="isagi_yoichi",
    weapon="metavision_v2_zone_plus_liquidity_sweep",
    ego=0.60,
    target_hold_hours=24.0,
    narrative_voice="field_general_metavision_evolving",
)


@dataclass
class _PreparedSeries:
    """Per-symbol cache populated by `prepare()`. Mirrors v1's container
    but adds the H4 liquidity-sweep event list."""

    bars: list  # production Bar list
    ctx: Any   # PrecomputedContext from agent.rules.engine.precompute
    index_by_ts: dict[datetime, int]
    sweeps: list  # list[LiquiditySweep] from detect_liquidity_sweeps on H4


@dataclass
class _SweepSignalShim:
    """Minimal value object that mirrors `AlphaSignal` for the v2 sweep
    weapon. Same fields the production fill model
    (`agent.alphas.backtest._open`) reads, so the harness can open trades
    from this shim through the SAME codepath v1 uses for zone signals --
    no v2-specific fill model. The byte-equivalence of the zone branch
    is therefore preserved end-to-end.
    """

    direction: Any  # production agent.types.Direction
    entry: float
    stop: float
    take_profit: float
    reason: str
    conviction: float
    meta: dict


class A1IsagiV2(BaseStriker):
    """A1 Isagi v2 -- two-weapon striker (zone_d1_against + liquidity_sweep).

    Inherits from `BaseStriker` (same as v1) -- the contract is the same.
    The diff is *additive*: v2 *adds* the liquidity-sweep vocabulary on
    top of v1's preserved zone-touch core.

    Public surface (engine-driven):
      * `observe(market, ledger) -> Thought` -- every tick; tagged
        `weapon:<zone|sweep|none>`.
      * `intend(market, my_recent_thought) -> AgentProposal | None` --
        only at H4 close.

    Harness-only surface:
      * `prepare(symbol, bars)` -- pre-load bars + precompute zones AND
        H4 liquidity sweeps (the prod `precompute` skips H4 sweeps).
      * `inner_signal_at(symbol, i)` -- raw v1 zone signal pass-through.
      * `sweep_signal_at(symbol, i)` -- raw v2 sweep signal pass-through.
    """

    def __init__(
        self,
        agent_id: str = "isagi_yoichi",
        canon_role: Optional[CanonRole] = None,
        home_tf: str = "H4",
        symbols: Optional[list[str]] = None,
        *,
        production_cfg: Any | None = None,
        sweep_max_age_bars: int = SWEEP_MAX_AGE_BARS,
        sweep_conviction: float = SWEEP_CONVICTION,
        stop_atr_mult: float = STOP_ATR_MULT,
        target_rr: float = TARGET_RR,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            canon_role=canon_role or ISAGI_V2_CANON_ROLE,
            home_tf=home_tf,
            symbols=list(symbols) if symbols is not None else list(ISAGI_V1_SYMBOLS),
        )
        ensure_production_repo_on_path()
        from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha  # noqa: E402
        from agent.config import load_config  # noqa: E402

        self._cfg = production_cfg if production_cfg is not None else load_config()
        # The zone weapon is the production SupplyDemandAlpha at locked v1 params.
        # NO new params, NO retune -- per the §3.11.1 distinction "if vN could
        # express the new behaviour by changing a hyperparameter, the answer
        # is to retune vN, not to ship vN+1". v2 is the *additive* sweep
        # weapon; the zone weapon stays untouched.
        self._inner = SupplyDemandAlpha(cfg=self._cfg, **ISAGI_V1_PARAMS)
        self._prepared: dict[str, _PreparedSeries] = {}

        self._sweep_max_age_bars = int(sweep_max_age_bars)
        self._sweep_conviction = float(sweep_conviction)
        self._stop_atr_mult = float(stop_atr_mult)
        self._target_rr = float(target_rr)

    # ------------------------------------------------------------------
    # Harness API
    # ------------------------------------------------------------------

    def prepare(self, symbol: str, bars: list) -> None:
        """Pre-load bars + precompute detector context for `symbol`.

        Mirrors v1's prepare() (same zones precompute) and *additionally*
        computes the H4 liquidity-sweep list via the production
        `detect_liquidity_sweeps` causal detector. The production
        `precompute` skips H4 sweeps (it gates on TF in `("M1", "M3",
        "M5", "M15", "H1")`), so v2 calls the detector directly here. The
        detector is fully causal in its default `require_reversal_
        confirmation=False` mode (see
        `agent/detectors/liquidity_sweep.py` module docstring).
        """
        ensure_production_repo_on_path()
        from agent.detectors.liquidity_sweep import detect_liquidity_sweeps  # noqa: E402
        from agent.rules.engine import precompute  # noqa: E402

        ctx = precompute(list(bars), self._cfg)
        index_by_ts = {b.time: i for i, b in enumerate(bars)}
        sweeps = detect_liquidity_sweeps(
            list(bars),
            swing_lookback=self._cfg.detectors.swing_lookback,
            pierce_buffer_pips=1.0,
            require_reversal_confirmation=False,
        )
        self._prepared[symbol] = _PreparedSeries(
            bars=list(bars),
            ctx=ctx,
            index_by_ts=index_by_ts,
            sweeps=list(sweeps),
        )
        log.info(
            "A1IsagiV2 prepared %s: %d bars, %d zones, %d swings, %d H4 sweeps",
            symbol, len(bars), len(ctx.zones), len(ctx.swings), len(sweeps),
        )

    def inner_signal_at(self, symbol: str, i: int):
        """Pass-through to the wrapped `SupplyDemandAlpha.signal`.

        Identical to v1's `inner_signal_at`. Used by
        `tests/test_a01_isagi_v2.py::test_zone_branch_byte_equivalent_to_v1`
        to assert byte-for-byte equivalence on the zone branch.
        """
        prep = self._prepared.get(symbol)
        if prep is None:
            return None
        from agent.alphas.base import AlphaContext  # noqa: E402
        actx = AlphaContext(bars=prep.bars, ctx=prep.ctx, cfg=self._cfg)
        return self._inner.signal(actx, i)

    def sweep_signal_at(self, symbol: str, i: int) -> Optional[_SweepSignalShim]:
        """Raw v2 sweep-weapon signal at bar index `i`.

        Looks up sweeps in `(i - sweep_max_age_bars, i]` on `symbol`.
        Returns the freshest qualifying sweep (HTF-aligned, sweep
        direction agrees with D1 bias) as a `_SweepSignalShim`. Returns
        None if no sweep qualifies.

        Causality: `detect_liquidity_sweeps` is fully causal in its
        default mode; we further enforce `sweep.sweep_bar_index <= i`
        (the sweep is already "known" at decision time).
        """
        prep = self._prepared.get(symbol)
        if prep is None:
            return None
        if i < 0 or i >= len(prep.bars):
            return None
        return self._select_sweep_signal(prep=prep, i=i)

    @property
    def prepared_symbols(self) -> tuple[str, ...]:
        return tuple(self._prepared.keys())

    # ------------------------------------------------------------------
    # BlueLockStriker contract
    # ------------------------------------------------------------------

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        prep = self._prepared.get(market.symbol)
        base_tags = [
            "zone_d1_against",
            "htf_against",
            "canon:isagi",
            "weapon:metavision_v2",
            "isagi_v2",
        ]

        if prep is None:
            return Thought(
                schema_version=SCHEMA_VERSION,
                agent_id=self.agent_id,
                tick_id=market.tick_id,
                timestamp=market.as_of,
                symbol=market.symbol,
                narrative=(
                    f"[isagi v2] {market.symbol} {market.timeframe} @ "
                    f"{market.as_of} -- wrapper not prepared; observation-only."
                ),
                tags=base_tags + ["weapon:none", "unprepared"],
                confidence_in_thought=0.0,
                expected_action="wait",
                coordinate=None,
                decision_horizon=market.as_of,
                ttl_ticks=1,
                references=[],
            )

        i = prep.index_by_ts.get(market.as_of)
        if i is None:
            return Thought(
                schema_version=SCHEMA_VERSION,
                agent_id=self.agent_id,
                tick_id=market.tick_id,
                timestamp=market.as_of,
                symbol=market.symbol,
                narrative=(
                    f"[isagi v2] {market.symbol} {market.timeframe} @ "
                    f"{market.as_of} -- timestamp not in prepared index; observation-only."
                ),
                tags=base_tags + ["weapon:none", "timestamp_miss"],
                confidence_in_thought=0.0,
                expected_action="wait",
                coordinate=None,
                decision_horizon=market.as_of,
                ttl_ticks=1,
                references=[],
            )

        zone_sig = self.inner_signal_at(market.symbol, i)
        sweep_sig = self._select_sweep_signal(prep=prep, i=i)

        # Cross-weapon tiebreaker: zone first (legacy-first ordering).
        if zone_sig is not None:
            return self._zone_firing_thought(
                market=market, sig=zone_sig, base_tags=base_tags,
                sweep_observed=sweep_sig is not None,
            )
        if sweep_sig is not None:
            return self._sweep_firing_thought(
                market=market, sig=sweep_sig, base_tags=base_tags,
            )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[isagi v2] {market.symbol} H4 close {market.as_of}: "
                "no zone-touch + D1-counter alignment AND no fresh "
                "liquidity-sweep with D1 agreement; waiting."
            ),
            tags=base_tags + ["weapon:none"],
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
        )

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        if market.timeframe != self.home_tf:
            return None
        prep = self._prepared.get(market.symbol)
        if prep is None:
            return None
        i = prep.index_by_ts.get(market.as_of)
        if i is None:
            return None

        # Weapon A -- zone (v1-byte-identical). Legacy-first.
        zone_sig = self.inner_signal_at(market.symbol, i)
        if zone_sig is not None:
            return self._proposal_from_zone(
                market=market,
                my_recent_thought=my_recent_thought,
                sig=zone_sig,
                bar_index=i,
            )

        # Weapon B -- liquidity sweep (NEW in v2).
        sweep_sig = self._select_sweep_signal(prep=prep, i=i)
        if sweep_sig is None:
            return None
        return self._proposal_from_sweep(
            market=market,
            my_recent_thought=my_recent_thought,
            sig=sweep_sig,
            bar_index=i,
        )

    # ------------------------------------------------------------------
    # Sweep weapon -- private builder
    # ------------------------------------------------------------------

    def _select_sweep_signal(
        self, *, prep: _PreparedSeries, i: int,
    ) -> Optional[_SweepSignalShim]:
        """Find the freshest qualifying sweep within
        `(i − sweep_max_age_bars, i]` whose direction is HTF-aligned.

        Returns a `_SweepSignalShim` with direction / entry / stop /
        take-profit / conviction filled, or None if no sweep qualifies.

        Tiebreaker (multiple sweeps in window): pick the **freshest**
        (highest `sweep_bar_index`). Deterministic; no randomness.
        """
        from agent.alphas.concepts._htf import HTFBias, htf_bias_at  # noqa: E402
        from agent.types import Direction  # noqa: E402

        bars = prep.bars
        atr = prep.ctx.atr_by_index.get(i, 0.0)
        if atr <= 0:
            return None
        if i <= 0 or i >= len(bars):
            return None

        # Find the freshest sweep in the window. The sweeps list is in
        # chronological order (detector emits in bar-index order), so
        # walking backwards gives us "freshest first".
        cutoff_lo = i - int(self._sweep_max_age_bars)
        candidate = None
        for sweep in reversed(prep.sweeps):
            if sweep.sweep_bar_index > i:
                continue   # future event -- never read
            if sweep.sweep_bar_index <= cutoff_lo:
                break      # past the window; chronological short-circuit
            candidate = sweep
            break
        if candidate is None:
            return None

        # HTF gate: D1 bias must AGREE with the sweep's reaction
        # direction. (Sweeps are confirmations of the macro trend that
        # ran the stops; we ride that confirmation, not fade it.) This
        # is the mirror flip of v1's `htf_align_mode="against"` zone
        # logic -- zone touches are fades against D1; sweeps are
        # confirmations of D1.
        bias = htf_bias_at(
            bars, i, htf=HTF_TF,
            htf_lookback=HTF_LOOKBACK,
            min_move_pips=HTF_MIN_MOVE_PIPS,
        )
        if not bias.matches(candidate.direction):
            return None  # NEUTRAL also blocks (matches() returns False)

        # Entry/SL/TP construction. Direction-specific.
        bar = bars[i]
        entry = float(bar.close)
        atr_buf = self._stop_atr_mult * float(atr)

        if candidate.direction == Direction.LONG:
            # Sellside sweep: wick below the level, close back above.
            # Stop sits below the sweep's low wick by atr_buf.
            stop = float(candidate.sweep_low) - atr_buf
            if not (stop < entry):
                return None
            risk = entry - stop
            tp = entry + self._target_rr * risk
            reason = "liquidity_sweep_long"
        else:
            stop = float(candidate.sweep_high) + atr_buf
            if not (stop > entry):
                return None
            risk = stop - entry
            tp = entry - self._target_rr * risk
            reason = "liquidity_sweep_short"

        meta = {
            "weapon": "liquidity_sweep",
            "swept_label": candidate.swept_label,
            "swept_price": float(candidate.swept_price),
            "sweep_bar_index": int(candidate.sweep_bar_index),
            "sweep_age_bars": int(i - candidate.sweep_bar_index),
            "sweep_side": candidate.side,
            "htf_bias": bias.value,
            "htf_align": HTF_TF,
            "htf_align_mode": "with",   # v2 sweep is *with* the D1 trend
            "htf_lookback": HTF_LOOKBACK,
            "htf_min_move_pips": HTF_MIN_MOVE_PIPS,
        }
        return _SweepSignalShim(
            direction=candidate.direction,
            entry=entry,
            stop=stop,
            take_profit=tp,
            reason=reason,
            conviction=self._sweep_conviction,
            meta=meta,
        )

    # ------------------------------------------------------------------
    # Proposal builders -- shared with v1 in spirit, weapon-specific tags
    # ------------------------------------------------------------------

    def _proposal_from_zone(
        self,
        *,
        market: MarketState,
        my_recent_thought: Thought,
        sig,                   # production AlphaSignal
        bar_index: int,
    ) -> AgentProposal:
        """Zone-touch proposal -- byte-identical to v1 by construction.

        The only delta vs v1's `intend()` is the `rationale.weapon` and
        `rationale.isagi_version` tags (so downstream ledgers can join
        on agent version). Trade fields (direction / entry / stop / tp /
        conviction) come straight from the wrapped `AlphaSignal` and
        are byte-equivalent to v1's output.
        """
        direction = sig.direction.value
        ladder = [LadderRung(price=float(sig.take_profit), fraction=1.0)]
        horizon = market.as_of + timedelta(
            hours=float(self.canon_role.target_hold_hours),
        )
        meta = getattr(sig, "meta", {}) or {}
        rationale: dict[str, Any] = {
            "wrapped": "agent.alphas.concepts.zone_alpha.SupplyDemandAlpha",
            "isagi_version": "v2",
            "weapon": "zone_d1_against",
            "params": dict(ISAGI_V1_PARAMS),
            "signal_reason": sig.reason,
            "htf_bias": meta.get("htf_bias"),
            "htf_align": meta.get("htf_align"),
            "htf_align_mode": meta.get("htf_align_mode"),
            "htf_lookback": meta.get("htf_lookback"),
            "htf_min_move_pips": meta.get("htf_min_move_pips"),
            "bar_index": int(bar_index),
        }
        return AgentProposal(
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            source_thought_id=my_recent_thought.thought_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            direction=direction,
            entry=float(sig.entry),
            stop=float(sig.stop),
            ladder=ladder,
            conviction=float(sig.conviction),
            regime_fit=0.5,
            valid_until=horizon,
            rationale=rationale,
        )

    def _proposal_from_sweep(
        self,
        *,
        market: MarketState,
        my_recent_thought: Thought,
        sig: _SweepSignalShim,
        bar_index: int,
    ) -> AgentProposal:
        """Sweep-weapon proposal -- the NEW vocabulary v2 adds.

        Uses the same `AgentProposal` schema as v1; the rationale carries
        the sweep telemetry (swept_label, sweep_age_bars, side) so the
        rejection-analysis and behaviour-delta tests can identify sweep
        trades from a single field lookup.
        """
        direction = sig.direction.value
        ladder = [LadderRung(price=float(sig.take_profit), fraction=1.0)]
        horizon = market.as_of + timedelta(
            hours=float(self.canon_role.target_hold_hours),
        )
        rationale: dict[str, Any] = {
            "wrapped": "agent.detectors.liquidity_sweep.detect_liquidity_sweeps",
            "isagi_version": "v2",
            "weapon": "liquidity_sweep",
            "params": {
                "sweep_max_age_bars": int(self._sweep_max_age_bars),
                "stop_atr_mult": float(self._stop_atr_mult),
                "target_rr": float(self._target_rr),
                "sweep_conviction": float(self._sweep_conviction),
            },
            "signal_reason": sig.reason,
            "bar_index": int(bar_index),
            **{k: v for k, v in sig.meta.items()
               if k not in ("weapon",)},
        }
        return AgentProposal(
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            source_thought_id=my_recent_thought.thought_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            direction=direction,
            entry=float(sig.entry),
            stop=float(sig.stop),
            ladder=ladder,
            conviction=float(sig.conviction),
            regime_fit=0.5,
            valid_until=horizon,
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Thought builders
    # ------------------------------------------------------------------

    def _zone_firing_thought(
        self,
        *,
        market: MarketState,
        sig,
        base_tags: list[str],
        sweep_observed: bool,
    ) -> Thought:
        """Build the firing Thought for the zone weapon. Tag set mirrors
        v1's tags so the Φ3 wrapper tests stay green if a future test
        re-uses v2 in v1's place via the `IsagiYoichi` alias."""
        meta_tags = _meta_to_tags(getattr(sig, "meta", {}) or {})
        coord = _coordinate_from_signal(
            sig=sig,
            agent_id=self.agent_id,
            symbol=market.symbol,
            as_of=market.as_of,
            home_tf=self.home_tf,
            target_hold_hours=self.canon_role.target_hold_hours,
        )
        # Annotate the rationale with the v2 marker so downstream
        # consumers can distinguish v1- and v2-emitted zone trades.
        rationale = dict(coord.rationale)
        rationale.update({"isagi_version": "v2", "weapon": "zone"})
        if sweep_observed:
            rationale["sweep_co_observed"] = True
        coord = Coordinate(
            agent_id=coord.agent_id,
            symbol=coord.symbol,
            price_lo=coord.price_lo,
            price_hi=coord.price_hi,
            time_start=coord.time_start,
            time_end=coord.time_end,
            vol_band=coord.vol_band,
            regime_predicate=coord.regime_predicate,
            expected_strength=coord.expected_strength,
            direction_bias=coord.direction_bias,
            rationale=rationale,
        )
        direction = sig.direction.value
        tags = list(base_tags) + meta_tags + [
            f"signal_reason:{sig.reason}",
            "weapon:zone",
        ]
        if sweep_observed:
            tags.append("co_observed:sweep")
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[isagi v2/zone] {market.symbol} H4 close {market.as_of}: "
                f"zone-touch {direction} fade against D1 bias; "
                f"entry={sig.entry:.5f} stop={sig.stop:.5f} tp={sig.take_profit:.5f}."
                + ("  (sweep co-observed; zone wins tiebreaker)" if sweep_observed else "")
            ),
            tags=tags,
            confidence_in_thought=float(sig.conviction),
            expected_action=f"{direction}_on_H4_close",
            coordinate=coord,
            decision_horizon=market.as_of,
            ttl_ticks=6,
            references=[],
        )

    def _sweep_firing_thought(
        self,
        *,
        market: MarketState,
        sig: _SweepSignalShim,
        base_tags: list[str],
    ) -> Thought:
        """Build the firing Thought for the v2 sweep weapon. Tags carry
        the sweep telemetry so the behaviour-delta test can filter on
        `weapon:sweep` alone.
        """
        direction = sig.direction.value
        stop_dist = abs(float(sig.entry) - float(sig.stop))
        band_half = max(stop_dist, 0.0001)
        coord = Coordinate(
            agent_id=self.agent_id,
            symbol=market.symbol,
            price_lo=float(sig.entry) - band_half,
            price_hi=float(sig.entry) + band_half,
            time_start=market.as_of,
            time_end=market.as_of + timedelta(
                hours=float(self.canon_role.target_hold_hours),
            ),
            vol_band=(0.5, 2.0),
            regime_predicate="D1_trend_with_sweep",
            expected_strength=float(sig.conviction),
            direction_bias=direction,
            rationale={
                "isagi_version": "v2",
                "weapon": "liquidity_sweep",
                "swept_label": sig.meta.get("swept_label"),
                "swept_price": float(sig.meta.get("swept_price", 0.0)),
                "sweep_side": sig.meta.get("sweep_side"),
                "sweep_age_bars": int(sig.meta.get("sweep_age_bars", -1)),
                "entry": float(sig.entry),
                "stop": float(sig.stop),
                "take_profit": float(sig.take_profit),
                "signal_reason": sig.reason,
                "home_tf": self.home_tf,
            },
        )
        sweep_tags = [
            "weapon:sweep",
            f"sweep_side:{sig.meta.get('sweep_side')}",
            f"swept_label:{sig.meta.get('swept_label')}",
            f"htf_bias:{sig.meta.get('htf_bias')}",
            f"signal_reason:{sig.reason}",
        ]
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[isagi v2/sweep] {market.symbol} H4 close {market.as_of}: "
                f"liquidity sweep {direction} with D1 bias "
                f"({sig.meta.get('htf_bias')}); swept "
                f"{sig.meta.get('swept_label')} @ "
                f"{sig.meta.get('swept_price', 0.0):.5f}; "
                f"entry={sig.entry:.5f} stop={sig.stop:.5f} tp={sig.take_profit:.5f}."
            ),
            tags=list(base_tags) + sweep_tags,
            confidence_in_thought=float(sig.conviction),
            expected_action=f"{direction}_on_H4_close",
            coordinate=coord,
            decision_horizon=market.as_of,
            ttl_ticks=6,
            references=[],
        )


# Backwards-compatible alias for the version-agnostic identity (matches the
# v1 module's pattern). Roster loaders and ablation configs can keep using
# the same canonical name; the underlying class is v2.
IsagiYoichiV2 = A1IsagiV2
