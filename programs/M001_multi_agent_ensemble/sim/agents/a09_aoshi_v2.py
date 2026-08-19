"""A9 -- Aoshi Tokimitsu v2 (`aoshi_tokimitsu`) -- Tier-0 v1-readiness.

This module is the **Tier 0** landing of the evolution arc registered in
``reviews/sae_itoshi_v1_defeat.md`` §2. Tier 0 is v1-readiness plumbing:
it makes the A9 striker a *measurable* player against the G7 v1
checkpoint. **It is not an alpha claim and must never be reported as
one.** Phase AE's `FAIL` verdict stands unrevised; no trigger threshold,
no mechanic and no primary target changed here.

Naming (operator decision, 2026-08-19)
--------------------------------------

The Phase AE striker shipped under the id ``sae_itoshi``, but
``05-agent-roster-v0.md`` assigns the A9 slot to **Aoshi Tokimitsu**
("Macro-event-only vol-breakout (FOMC / NFP / CPI)" -- verbatim what
this agent does), while "Sae Itoshi (foil)" is the frozen adversarial
OPPONENT (`opponent_sae`, also "Frozen-Sae" in
``07-research-standards.md`` §4.2). Keeping both as "Sae" makes every
future report ambiguous between a player and a benchmark, so the
striker takes its rightful roster name from this module onward.

Sealed Phase AE artifacts (``experiments/phase_ae_sae_event_specialist/``
and ``reviews/phase_ae_verdict.md``) legitimately continue to say
``sae_itoshi`` / ``sae_fade`` / ``sae_ride``; they are history and are
byte-untouched. ``sim/agents/a09_sae.py`` is likewise untouched, per
``07-research-standards.md`` §10.6 ("vN untouched").

What v2 inherits UNCHANGED (subclass, not copy-paste)
-----------------------------------------------------

:class:`A9AoshiV2` subclasses :class:`~.a09_sae.A9SaeV1` so the trigger
and mechanic geometry are *provably* identical rather than
transcribed: same ``fade_min_move_pips=40``, ``fade_min_wick_frac=0.5``,
``ride_min_retention=0.7``, same fade/ride entry and stop construction,
same one-proposal-per-event guard, same 1.5R primary target. ``intend``
delegates to ``super().intend`` and only *decorates* the returned
proposal, so direction / entry / stop cannot drift by construction.
``sim/tests/test_a09_aoshi_v2_regression.py`` pins that.

What v2 ADDS (Tier 0 only -- defeat note §2)
--------------------------------------------

1. **F19 ``lot_intent``** via the newly registered ``event_specialist``
   playstyle (``sim/core/lot_intent.py``). Before this landing the
   playstyle was absent from the dispatch table and A9 silently took
   the fallback the module header labels "not a valid v1
   implementation" -- G7 C5 fail by missing code, not by measurement.
2. **F20 ``risk_intent``** likewise (``sim/core/risk_intent.py``),
   replacing the single hard-coded 1.5R rung with a ladder whose FIRST
   rung is still 1.5R. Additive: the inherited bracket is preserved.
3. **F21 ``read_workspace``** + directional abstention: v2 stands down
   when a Tier-1 incumbent already holds the slot the other way. This
   is the only route by which Aoshi affects a peer, and it is
   defensive, which suits the role (defeat note §2 Tier 0 item 3).
4. **Conviction / regime-fit functions** replacing v1's literal
   ``conviction=0.85`` / ``regime_fit=0.6`` on every proposal, which
   pinned C5/C6 dispersion at zero the same way Nagi's did in G7
   §11.13.
5. **Hard time stop** at ``target_hold_hours`` (6.0). v1 has none:
   ``valid_until`` is advisory and observed holds reached 6,675 minutes
   (111 h) against a median of 15.
6. **Event selection fix.** v1's ``_nearest_scheduled_event`` returns
   the EARLIEST candidate in the window, so a 60-minute-stale release
   can be preferred over one about to print. v2 picks the release
   NEAREST to ``as_of``.

Still open after Tier 0: G7 **C1** (quality -- the AE2 alpha defeat)
and **C2** (lifts a peer). Tier 1 (the volatility-normalised trigger)
and Tier 2 (the surprise panel) are pre-registered separately and are
NOT implemented here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
    A9SaeV1,
    BarsProvider,
    SaeConfig,
    SimNewsEvent,
    _ensure_utc,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import ThoughtLedger
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    WorkspaceSnapshot,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    CanonRole,
    LadderRung,
    MarketState,
    Thought,
)

log = logging.getLogger(__name__)


AOSHI_V2_CANON_ROLE = CanonRole(
    canon_player="aoshi_tokimitsu",
    weapon="event_release_impulse",
    ego=0.75,
    target_hold_hours=6.0,
    narrative_voice="berserker_event_mode",
)

# Tier-1 peers whose live directional claim makes Aoshi stand down
# (F21 abstention). Only A1 Isagi is Tier-1 in the current roster; the
# tuple is constructor-overridable so a roster change is config, not a
# code edit.
AOSHI_TIER1_INCUMBENTS: tuple[str, ...] = ("isagi_yoichi",)


# ---------------------------------------------------------------------------
# Conviction / regime-fit calibration (defeat note §3)
# ---------------------------------------------------------------------------
#
# CALIBRATION POINT -- the whole design constraint for these two
# functions is that they must return v1's literal constants at v1's
# TYPICAL trade, so Tier 0 re-centres nothing. The point chosen is v1's
# own TRIGGER BOUNDARY at the fade wait, because every number in it is
# a `SaeConfig` constant rather than a panel measurement:
#
#   move_atr_ratio         = 4.0   (see the honesty note below)
#   wick_frac              = 0.50  == SaeConfig.fade_min_wick_frac
#   minutes_since_release  = 15    == SaeConfig.fade_wait_min
#     -> conviction  == 0.85       == v1's hard-coded value
#     -> regime_fit  == 0.60       == v1's hard-coded value
#
# HONESTY NOTE on the 4.0. v1's trigger has NO volatility term at all
# (that absence is precisely the structural defeat in §1.4), so no
# impulse-to-ATR reference can be read off v1. 4.0 is therefore a
# DECLARED reference, not a fitted one: it is v1's 40-pip trigger floor
# over a 10-pip nominal M15 EURUSD ATR. It was NOT tuned against the
# Phase AE panel -- doing so would be a retune of a spent panel, which
# AE PROTOCOL §5.1 pre-bans. Tier 1 pre-registers its own `m` from
# Phase AG's shape; this constant has no bearing on that.
CALIB_MOVE_ATR_RATIO: float = 4.0
CALIB_WICK_FRAC: float = 0.50
CALIB_MINUTES_SINCE_RELEASE: float = 15.0
CALIB_CONVICTION: float = 0.85
CALIB_REGIME_FIT: float = 0.60

CONVICTION_MIN: float = 0.50
CONVICTION_MAX: float = 0.95

# z-score sensitivities. Sized so plausible event geometry spans roughly
# z in [-0.9, +1.0] -- real dispersion, with the clip as a guard rather
# than the usual operating point.
CONVICTION_RATIO_GAIN: float = 0.35
CONVICTION_WICK_GAIN: float = 0.60
CONVICTION_STALENESS_GAIN: float = 0.40
# Staleness is normalised by the post-release half of the fire window
# (`SaeConfig.fire_window_after_min`), so "fully stale" == "about to
# fall out of the window".
STALENESS_SCALE_MIN: float = 60.0

REGIME_FIT_MIN: float = 0.30
REGIME_FIT_MAX: float = 0.90
REGIME_FIT_RATIO_GAIN: float = 0.20
REGIME_FIT_STALENESS_GAIN: float = 0.20

# ATR context for the impulse ratio. 96 M15 bars = 24 h, the ATR96
# convention Phase AG used. Read strictly from bars that CLOSED before
# the event bar opened -- no look-ahead.
ATR_LOOKBACK_BARS: int = 96
ATR_MIN_BARS: int = 8
ATR_FLOOR_PIPS: float = 1.0
# Used when the bars provider cannot supply enough pre-event history
# (short synthetic fixtures, warmup). Same 10-pip nominal M15 EURUSD ATR
# as the calibration point, so a fallback lands the agent exactly on its
# calibration conviction rather than somewhere arbitrary.
ATR_FALLBACK_PIPS: float = 10.0

# Ladder split for the F20-shaped rungs. Rung 0 is v1's 1.5R target and
# carries the majority so the inherited bracket remains the primary exit.
LADDER_FRACTIONS: tuple[float, ...] = (0.6, 0.4)

# Doctrine §6 sandbox equity. Only used to stamp an auditable lot on the
# rationale; the harness's own equity is authoritative at scoring time.
REF_EQUITY_DOLLARS: float = 100.0


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def conviction_from_geometry(
    move_atr_ratio: float,
    wick_frac: float,
    minutes_since_release: float,
    *,
    wick_ref: float = CALIB_WICK_FRAC,
) -> float:
    """Conviction as f(impulse/ATR, wick fraction, staleness).

    Defeat note §3: "monotone increasing in the first two, decreasing in
    the third, clipped to [0.5, 0.95]". Strictly monotone in each input
    inside the clip band, and equal to :data:`CALIB_CONVICTION` (0.85)
    at the calibration point documented above.

    ``wick_ref`` exists because the two inherited mechanics express
    "quality of the read" through different fractions with different
    trigger floors: the fade uses the rejection wick (floor 0.50) and
    the ride uses impulse retention (floor 0.70). Passing each
    mechanic's own floor keeps BOTH centred at 0.85 at their own
    trigger boundary. The note names only ``wick_frac`` because it
    sketches a fade-only Tier 1; Tier 0 still carries the ride, so the
    reference is parameterised rather than hard-coded.
    """
    z = (
        CONVICTION_RATIO_GAIN
        * (move_atr_ratio - CALIB_MOVE_ATR_RATIO) / CALIB_MOVE_ATR_RATIO
        + CONVICTION_WICK_GAIN * (wick_frac - wick_ref)
        - CONVICTION_STALENESS_GAIN
        * (minutes_since_release - CALIB_MINUTES_SINCE_RELEASE)
        / STALENESS_SCALE_MIN
    )
    # Asymmetric slopes so z = +1 lands on the ceiling and z = -1 on the
    # floor; continuous and strictly increasing through z = 0.
    if z >= 0.0:
        raw = CALIB_CONVICTION + (CONVICTION_MAX - CALIB_CONVICTION) * z
    else:
        raw = CALIB_CONVICTION + (CALIB_CONVICTION - CONVICTION_MIN) * z
    return _clip(raw, CONVICTION_MIN, CONVICTION_MAX)


def regime_fit_from_geometry(
    move_atr_ratio: float,
    minutes_since_release: float,
) -> float:
    """Execution-regime fit -- the risk-budget channel into F19.

    Deliberately the MIRROR of conviction in both inputs, and that is
    the point. Defeat note §2 Tier 0 item 2 requires the agent to "size
    **down** as the pre-release window narrows and as the
    impulse-to-ATR ratio grows", while §3 requires conviction to rise
    with impulse and freshness. F19's signature
    ``(conviction, sl_pips, equity, regime_fit)`` carries no time term,
    so ``regime_fit`` is the only channel through which window
    proximity can reach sizing.

    Reading it as *execution*-regime fit rather than directional
    confidence makes the sign self-consistent: the freshest, most
    violent post-release tape is where real NFP spreads are
    "catastrophically wider" (Phase AE REPORT §4.3), i.e. the worst
    regime to carry size in, whatever the directional read says.

    Returns :data:`CALIB_REGIME_FIT` (0.60) at the calibration point;
    clipped to [0.30, 0.90].
    """
    raw = (
        CALIB_REGIME_FIT
        - REGIME_FIT_RATIO_GAIN
        * (move_atr_ratio - CALIB_MOVE_ATR_RATIO) / CALIB_MOVE_ATR_RATIO
        + REGIME_FIT_STALENESS_GAIN
        * (minutes_since_release - CALIB_MINUTES_SINCE_RELEASE)
        / STALENESS_SCALE_MIN
    )
    return _clip(raw, REGIME_FIT_MIN, REGIME_FIT_MAX)


@dataclass(frozen=True)
class EventExit:
    """Resolution of one v2 bracket, including the Tier-0 time stop."""

    reason: str            # "stop" | "target" | "time_stop"
    time: datetime
    price: float
    hold_minutes: float


class A9AoshiV2(A9SaeV1):
    """A9 Aoshi Tokimitsu v2 -- event striker, Tier-0 v1-readiness.

    Subclass of :class:`A9SaeV1`; every trigger threshold and mechanic
    is inherited untouched. See the module docstring for what Tier 0
    adds and what it explicitly does not claim.
    """

    def __init__(
        self,
        agent_id: str = "aoshi_tokimitsu",
        canon_role: Optional[CanonRole] = None,
        home_tf: str = "M15",
        symbols: Optional[Iterable[str]] = None,
        *,
        config: SaeConfig | None = None,
        bars_provider: BarsProvider | None = None,
        tier1_incumbents: Iterable[str] = AOSHI_TIER1_INCUMBENTS,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            canon_role=canon_role or AOSHI_V2_CANON_ROLE,
            home_tf=home_tf,
            # Universe stays v1's EURUSD-only. The EURUSD/GBPUSD/USDCAD
            # expansion in defeat note §3 is a Tier-1 n-expansion axis;
            # widening it here would change what fires, which Tier 0
            # forbids.
            symbols=symbols,
            config=config,
            bars_provider=bars_provider,
        )
        self._tier1_incumbents: tuple[str, ...] = tuple(
            a for a in tier1_incumbents if a != agent_id
        )
        self._atr_cache: dict[tuple[str, datetime], tuple[float, str]] = {}

    # ------------------------------------------------------------------
    # (f) Event selection -- nearest release, not earliest candidate
    # ------------------------------------------------------------------

    def _nearest_scheduled_event(self, as_of: datetime) -> SimNewsEvent | None:
        """Pick the release NEAREST to ``as_of`` within the fire window.

        v1 collects the same candidate set and then returns
        ``candidates[0]`` after sorting ascending by time -- i.e. the
        EARLIEST. On a dense calendar day that lets a release up to 60
        minutes stale outrank one about to print. The window bounds,
        the USD filter and the high-impact filter are all inherited
        unchanged; only the choice among candidates differs.

        Ties (two releases equidistant from ``as_of``) fall back to the
        earlier one, which is v1's rule -- so the fix is a strict
        refinement and stays deterministic.
        """
        as_of = _ensure_utc(as_of)
        earliest = as_of - timedelta(minutes=self._config.fire_window_after_min)
        latest = as_of + timedelta(minutes=self._config.fire_window_before_min)
        candidates: list[SimNewsEvent] = []
        for e in self._events:
            if e.currency.upper() != "USD":
                continue
            if e.impact.lower() != "high":
                continue
            if earliest <= e.time_utc <= latest:
                candidates.append(e)
        if not candidates:
            return None
        candidates.sort(
            key=lambda e: (abs((e.time_utc - as_of).total_seconds()), e.time_utc),
        )
        return candidates[0]

    # ------------------------------------------------------------------
    # (c) F21 -- workspace read + defensive abstention
    # ------------------------------------------------------------------

    def read_workspace(
        self,
        workspace: WorkspaceSnapshot | None,
        as_of: datetime,
    ) -> tuple[Thought, ...]:
        """F21 -- backwards-only peer read scoped to Aoshi's symbols.

        v1 accepted ``workspace=`` and discarded it ("v1 Sae reads no
        peers"), which is G7 C4's read-side failure. The snapshot has
        already applied the §3.8 look-ahead guards; this override adds
        the agent-specific filters (peers only, own symbols only) and
        re-asserts the ``timestamp <= as_of`` bound defensively.

        Returns a tuple, matching :class:`BaseStriker` and every other
        shipped agent. (Doctrine §4.1a's prose says ``list[Thought]``;
        the shipped ``BlueLockStriker`` Protocol and all eight v1 agents
        return tuples, and ``test_agents_playstyle_wiring`` asserts it,
        so the code convention is the binding one.)
        """
        if workspace is None:
            return ()
        peers = workspace.read_for(agent_id=self.agent_id, tier=self.tier)
        cutoff = _ensure_utc(as_of)
        return tuple(
            t for t in peers
            if t.agent_id != self.agent_id
            and t.symbol in self.symbols
            and _ensure_utc(t.timestamp) <= cutoff
        )

    def opposing_incumbent(
        self,
        *,
        workspace: WorkspaceSnapshot | None,
        symbol: str,
        direction: str,
        as_of: datetime,
    ) -> tuple[str, str] | None:
        """Return ``(agent_id, bias)`` of a Tier-1 peer holding the slot
        the OTHER way, else ``None``.

        A peer "holds the slot" when its latest Thought on ``symbol``
        carries a directional read. A Thought with a
        :class:`Coordinate` whose ``time_end`` has already passed is
        treated as a released slot, not a live claim.
        """
        peers = self.read_workspace(workspace, as_of)
        latest: dict[str, Thought] = {}
        for t in peers:
            if t.symbol != symbol:
                continue
            if t.agent_id not in self._tier1_incumbents:
                continue
            cur = latest.get(t.agent_id)
            if cur is None or (t.tick_id, t.timestamp) > (cur.tick_id, cur.timestamp):
                latest[t.agent_id] = t

        cutoff = _ensure_utc(as_of)
        for agent_id in sorted(latest):          # deterministic order
            t = latest[agent_id]
            if t.coordinate is not None:
                if _ensure_utc(t.coordinate.time_end) < cutoff:
                    continue                     # stale claim; slot free
                bias = str(t.coordinate.direction_bias)
            elif t.read is not None:
                bias = str(t.read.direction_bias)
            else:
                continue
            if bias in ("long", "short") and bias != direction:
                return agent_id, bias
        return None

    # ------------------------------------------------------------------
    # Observation -- inherited logic, Aoshi-branded surface
    # ------------------------------------------------------------------

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        """Inherited v1 observation, re-tagged under the A9 roster name.

        Delegates entirely to v1 and rewrites only the narrative prefix
        and the canon tag, so a Thought emitted by ``aoshi_tokimitsu``
        is not labelled ``[sae v1]`` / ``canon:sae``. No gate, no
        confidence and no read changes.
        """
        thought = super().observe(market, ledger)
        tags = [
            "canon:aoshi" if tag == "canon:sae" else tag
            for tag in thought.tags
        ] + ["aoshi_v2", "tier0"]
        return replace(
            thought,
            narrative=thought.narrative.replace("[sae v1]", "[aoshi v2]", 1),
            tags=tags,
        )

    # ------------------------------------------------------------------
    # Intent -- v1 geometry, Tier-0 decoration
    # ------------------------------------------------------------------

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
        *,
        workspace: WorkspaceSnapshot | None = None,
        **_kwargs: object,
    ) -> AgentProposal | None:
        """Fire v1's proposal, then abstain-or-decorate it.

        The geometry comes from ``super().intend`` verbatim, so
        ``direction`` / ``entry`` / ``stop`` are byte-identical to v1's
        by construction rather than by transcription. Only conviction,
        regime fit and the TP ladder are rewritten -- the declared
        Tier-0 divergences.

        **Abstention is terminal for the event.** ``super().intend``
        has already consumed the one-proposal-per-event guard by the
        time the direction is known, and that is left in place on
        purpose: standing down for a release means standing down for
        that release, not re-attempting it on the next mechanic.
        """
        base = super().intend(market, my_recent_thought)
        if base is None:
            return None

        blocker = self.opposing_incumbent(
            workspace=workspace,
            symbol=market.symbol,
            direction=str(base.direction),
            as_of=market.as_of,
        )
        if blocker is not None:
            log.info(
                "A9AoshiV2: abstaining on %s %s -- Tier-1 %s holds the slot %s.",
                market.symbol, base.direction, blocker[0], blocker[1],
            )
            return None

        return self._decorate(
            market=market,
            base=base,
            workspace_read_ok=workspace is not None,
        )

    # ------------------------------------------------------------------
    # (e) Hard time stop
    # ------------------------------------------------------------------

    def time_stop_at(self, proposal: AgentProposal) -> datetime:
        """Wall-clock instant at which an unresolved bracket is closed."""
        return _ensure_utc(proposal.timestamp) + timedelta(
            hours=float(self.canon_role.target_hold_hours),
        )

    def resolve_exit(
        self,
        proposal: AgentProposal,
        bars: list,
    ) -> EventExit | None:
        """Walk closed M15 ``bars`` and resolve the bracket, or time-stop.

        v1 has **no** time stop: ``valid_until`` is advisory, exits are
        SL/TP only, and observed holds reached 6,675 minutes (111 h)
        against a 15-minute median (defeat note §1.5). This resolver
        adds the missing leg -- the first bar that closes at or after
        :meth:`time_stop_at` closes the trade at that bar's close.

        Conventions, stated because they are choices:

        * Bar-granular. Exit timestamps are bar CLOSE times, so a time
          stop can overshoot ``target_hold_hours`` by at most one M15
          bar; it cannot overshoot by more.
        * Pessimistic within a bar: if a bar touches both the stop and
          the first TP rung, the stop wins.
        * Agent-side cognition, not a replacement for the harness fill
          model (``agent.alphas.backtest._check_exit``). The harness
          remains authoritative at scoring time.

        Returns ``None`` if the bars run out before anything resolves.
        """
        entry_t = _ensure_utc(proposal.timestamp)
        stop_t = self.time_stop_at(proposal)
        stop_price = float(proposal.stop)
        first_tp = float(proposal.ladder[0].price)
        is_long = str(proposal.direction) == "long"

        for bar in sorted(bars, key=lambda b: _ensure_utc(b.time)):
            bar_open_t = _ensure_utc(bar.time)
            if bar_open_t < entry_t:
                continue
            bar_close_t = bar_open_t + timedelta(minutes=15)
            if is_long:
                hit_stop = float(bar.low) <= stop_price
                hit_tp = float(bar.high) >= first_tp
            else:
                hit_stop = float(bar.high) >= stop_price
                hit_tp = float(bar.low) <= first_tp
            if hit_stop:
                return self._exit(entry_t, "stop", bar_close_t, stop_price)
            if hit_tp:
                return self._exit(entry_t, "target", bar_close_t, first_tp)
            if bar_close_t >= stop_t:
                return self._exit(
                    entry_t, "time_stop", bar_close_t, float(bar.close),
                )
        return None

    @staticmethod
    def _exit(
        entry_t: datetime, reason: str, at: datetime, price: float,
    ) -> EventExit:
        return EventExit(
            reason=reason,
            time=at,
            price=float(price),
            hold_minutes=(at - entry_t).total_seconds() / 60.0,
        )

    # ------------------------------------------------------------------
    # Tier-0 proposal decoration
    # ------------------------------------------------------------------

    def _decorate(
        self,
        *,
        market: MarketState,
        base: AgentProposal,
        workspace_read_ok: bool,
    ) -> AgentProposal:
        """Rewrite conviction / regime fit / TP ladder on v1's geometry.

        Everything that identifies the TRADE (direction, entry, stop,
        timestamp, validity) is copied through untouched.
        """
        cfg = self._config
        pip = cfg.pip_size
        rationale: dict[str, Any] = dict(base.rationale)

        entry = float(base.entry)
        stop = float(base.stop)
        risk = abs(entry - stop)
        sl_pips = risk / pip

        event_time = _ensure_utc(
            datetime.fromisoformat(str(rationale["event_time"])),
        )
        minutes_since_release = (
            _ensure_utc(market.as_of) - event_time
        ).total_seconds() / 60.0

        atr_pips, atr_source = self._atr_pips_before(market.symbol, event_time)
        move_pips = float(rationale.get("move_pips", 0.0))
        move_atr_ratio = move_pips / atr_pips if atr_pips > 0 else 0.0

        # Each mechanic reports its quality through its own fraction and
        # is centred on its own trigger floor -- see
        # `conviction_from_geometry`.
        if "wick_frac" in rationale:
            quality_frac = float(rationale["wick_frac"])
            quality_ref = float(cfg.fade_min_wick_frac)
            quality_kind = "wick_frac"
        else:
            quality_frac = float(rationale.get("retention_frac", 0.0))
            quality_ref = float(cfg.ride_min_retention)
            quality_kind = "retention_frac"

        conviction = conviction_from_geometry(
            move_atr_ratio, quality_frac, minutes_since_release,
            wick_ref=quality_ref,
        )
        regime_fit = regime_fit_from_geometry(
            move_atr_ratio, minutes_since_release,
        )

        # The event bar's own range stands in for the H1 swing: it is
        # the only structural extent the mechanic actually measured.
        h1_swing_pips = self._event_bar_range_pips(rationale)

        # F20 supplies the ladder's SHAPE (R multiples); the inherited
        # geometry supplies the R. Rung 0 therefore lands exactly on
        # v1's 1.5R price -- the bracket is preserved, the deeper rung
        # is the additive part.
        f20_sl_pips, f20_ladder_pips = self.risk_intent(
            conviction, atr_pips, h1_swing_pips,
        )
        multiples = self._ladder_multiples(f20_sl_pips, list(f20_ladder_pips))
        ladder = self._price_ladder(
            entry=entry, risk=risk, is_long=str(base.direction) == "long",
            multiples=multiples,
        )

        lot_at_ref_equity = self.lot_intent(
            conviction, sl_pips, REF_EQUITY_DOLLARS, regime_fit,
        )

        rationale.update({
            "aoshi_version": "v2_tier0",
            "renamed_from_agent_id": "sae_itoshi",
            "tier0_not_an_alpha_claim": True,
            "atr_pips": float(atr_pips),
            "atr_source": atr_source,
            "h1_swing_pips": float(h1_swing_pips),
            "move_atr_ratio": float(move_atr_ratio),
            "minutes_since_release": float(minutes_since_release),
            "quality_kind": quality_kind,
            "quality_frac": float(quality_frac),
            "quality_ref": float(quality_ref),
            "v1_conviction": float(base.conviction),
            "v1_regime_fit": float(base.regime_fit),
            "sl_pips": float(sl_pips),
            "f20_sl_pips": float(f20_sl_pips),
            "f20_tp_ladder_pips": [float(x) for x in f20_ladder_pips],
            "tp_multiples_r": [float(m) for m in multiples],
            "f19_lot_at_ref_equity": float(lot_at_ref_equity),
            "time_stop_utc": self.time_stop_at(base).isoformat(),
            "target_hold_hours": float(self.canon_role.target_hold_hours),
            "workspace_read_ok": bool(workspace_read_ok),
            "workspace_abstained": False,
        })

        return AgentProposal(
            agent_id=self.agent_id,
            tick_id=int(base.tick_id),
            source_thought_id=base.source_thought_id,
            timestamp=base.timestamp,
            symbol=base.symbol,
            direction=base.direction,
            entry=entry,
            stop=stop,
            ladder=ladder,
            conviction=float(conviction),
            regime_fit=float(regime_fit),
            valid_until=base.valid_until,
            rationale=rationale,
            agent_tier=int(base.agent_tier),
        )

    def _ladder_multiples(
        self, f20_sl_pips: float, f20_ladder_pips: list[float],
    ) -> tuple[float, ...]:
        """Convert F20's pip ladder into R multiples of the real stop."""
        if f20_sl_pips <= 0 or not f20_ladder_pips:
            return (float(self._config.target_rr),)
        return tuple(float(tp) / float(f20_sl_pips) for tp in f20_ladder_pips)

    @staticmethod
    def _price_ladder(
        *, entry: float, risk: float, is_long: bool,
        multiples: tuple[float, ...],
    ) -> list[LadderRung]:
        n = min(len(multiples), len(LADDER_FRACTIONS))
        used = multiples[:n]
        fractions = list(LADDER_FRACTIONS[:n])
        # Fractions must sum to 1.0 exactly (AgentProposal validation).
        fractions[-1] = 1.0 - sum(fractions[:-1])
        sign = 1.0 if is_long else -1.0
        return [
            LadderRung(price=entry + sign * m * risk, fraction=f)
            for m, f in zip(used, fractions)
        ]

    def _event_bar_range_pips(self, rationale: dict[str, Any]) -> float:
        """Event-bar extent in pips -- the only structural swing the
        mechanic actually measured. The ride rationale carries no
        high/low, so it legitimately reports 0.0 and F20 falls back to
        its ATR term alone."""
        hi = rationale.get("event_bar_high")
        lo = rationale.get("event_bar_low")
        if hi is None or lo is None:
            return 0.0
        return abs(float(hi) - float(lo)) / self._config.pip_size

    # ------------------------------------------------------------------
    # ATR context (backwards-only)
    # ------------------------------------------------------------------

    def _atr_pips_before(
        self, symbol: str, event_time: datetime,
    ) -> tuple[float, str]:
        """Mean true range over M15 bars that CLOSED before the event bar.

        Returns ``(atr_pips, source)`` where ``source`` is
        ``"measured"`` or ``"fallback"``. Never raises and never blocks
        a proposal: ATR feeds conviction and sizing only, never the
        trigger, so a missing history degrades the *measurement*, not
        the agent's behaviour.
        """
        key = (symbol, event_time)
        cached = self._atr_cache.get(key)
        if cached is not None:
            return cached

        result = (ATR_FALLBACK_PIPS, "fallback")
        provider = self._bars_provider
        if provider is not None:
            start = event_time - timedelta(
                minutes=15 * (ATR_LOOKBACK_BARS + 1),
            )
            try:
                bars = provider(symbol, start, event_time)
            except Exception as exc:                      # noqa: BLE001
                log.warning(
                    "A9AoshiV2: ATR bars_provider raised (%s) for %s -- "
                    "falling back to %.1f pips.",
                    exc, symbol, ATR_FALLBACK_PIPS,
                )
                bars = []
            usable = [
                b for b in sorted(bars, key=lambda b: _ensure_utc(b.time))
                if _ensure_utc(b.time) + timedelta(minutes=15) <= event_time
            ][-ATR_LOOKBACK_BARS:]
            if len(usable) >= ATR_MIN_BARS:
                trs: list[float] = []
                prev_close: float | None = None
                for b in usable:
                    tr = float(b.high) - float(b.low)
                    if prev_close is not None:
                        tr = max(
                            tr,
                            abs(float(b.high) - prev_close),
                            abs(float(b.low) - prev_close),
                        )
                    trs.append(tr)
                    prev_close = float(b.close)
                atr = (sum(trs) / len(trs)) / self._config.pip_size
                result = (max(atr, ATR_FLOOR_PIPS), "measured")

        self._atr_cache[key] = result
        return result


AoshiTokimitsu = A9AoshiV2


__all__ = [
    "A9AoshiV2",
    "AOSHI_TIER1_INCUMBENTS",
    "AOSHI_V2_CANON_ROLE",
    "ATR_FALLBACK_PIPS",
    "ATR_LOOKBACK_BARS",
    "AoshiTokimitsu",
    "CALIB_CONVICTION",
    "CALIB_MINUTES_SINCE_RELEASE",
    "CALIB_MOVE_ATR_RATIO",
    "CALIB_REGIME_FIT",
    "CALIB_WICK_FRAC",
    "EventExit",
    "LADDER_FRACTIONS",
    "conviction_from_geometry",
    "regime_fit_from_geometry",
]
