"""A9 Aoshi v2 -- Tier-0 regression + primitive tests.

The §10.6 regression half of the evolution-arc contract for the arc
registered in ``reviews/sae_itoshi_v1_defeat.md`` (forward half lives in
``test_a09_aoshi_v2_resolves_ae2.py``).

**Scope of the byte-identity assertion.** v2 claims to preserve the v1
TRADE GEOMETRY and nothing else, so the regression tests assert
``direction`` / ``entry`` / ``stop`` byte-for-byte and stop there.
``conviction``, ``regime_fit``, the TP ladder beyond its first rung, and
the rationale legitimately differ -- those are the declared Tier-0
divergences (defeat note §2 Tier 0 items 2 and 4). The first ladder rung
is additionally asserted equal to v1's single 1.5R rung, because
"additive" is a claim v2 makes about the bracket, not just about the
entry.

**Tier 0 is not an alpha claim.** Nothing here measures or asserts
performance. Phase AE's `FAIL` stands unrevised.

Fixture conventions (FakeBar, `_market`, the fade / ride bar builders)
are lifted from ``test_a09_sae_sim.py`` so the two suites stay
comparable.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a09_aoshi_v2 import (
    A9AoshiV2,
    AoshiTokimitsu,
    CALIB_CONVICTION,
    CALIB_MINUTES_SINCE_RELEASE,
    CALIB_MOVE_ATR_RATIO,
    CALIB_REGIME_FIT,
    CALIB_WICK_FRAC,
    conviction_from_geometry,
    regime_fit_from_geometry,
)
from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
    A9SaeV1,
    SaeConfig,
    SimNewsEvent,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.lot_intent import (
    playstyle_lot_intent,
)
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
)
from programs.M001_multi_agent_ensemble.sim.core.risk_intent import (
    playstyle_risk_intent,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    AgentProposal,
    Coordinate,
    MarketState,
    Thought,
)

UTC = timezone.utc
EVENT_T = datetime(2024, 3, 8, 13, 30, tzinfo=UTC)
PIP = 0.0001
EQUITY = 100.0


@dataclass
class FakeBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 100.0


def _market(as_of: datetime, tick_id: int = 1) -> MarketState:
    return MarketState(
        tick_id=tick_id, symbol="EURUSD", timeframe="M15", as_of=as_of,
        open=1.10, high=1.11, low=1.09, close=1.105, volume=100.0,
    )


def _provider(bars: list[FakeBar]):
    return lambda sym, start, end: [
        b for b in bars
        if start <= b.time and b.time + timedelta(minutes=15) <= end
    ]


def _events() -> list[SimNewsEvent]:
    return [SimNewsEvent(time_utc=EVENT_T, currency="USD", impact="High",
                         title="Employment Situation (NFP)")]


def _v1(bars: list[FakeBar], events=None) -> A9SaeV1:
    agent = A9SaeV1(config=SaeConfig(sae_enabled=True))
    agent.load_calendar(events=events if events is not None else _events())
    agent.set_bars_provider(_provider(bars))
    return agent


def _v2(bars: list[FakeBar], events=None, **kwargs) -> A9AoshiV2:
    agent = A9AoshiV2(config=SaeConfig(sae_enabled=True), **kwargs)
    agent.load_calendar(events=events if events is not None else _events())
    agent.set_bars_provider(_provider(bars))
    return agent


def _fade_bars() -> list[FakeBar]:
    """Bullish 50-pip event bar with a 56 % upper wick (v1 fixture)."""
    o = 1.1000
    c = o + 50 * PIP
    h = o + 120 * PIP
    lo = o - 5 * PIP
    return [
        FakeBar(time=EVENT_T, open=o, high=h, low=lo, close=c),
        FakeBar(time=EVENT_T + timedelta(minutes=15),
                open=c, high=c + 10 * PIP, low=c - 10 * PIP, close=c),
    ]


def _ride_bars() -> list[FakeBar]:
    """Bullish 50-pip event bar; next bar retains 90 % (v1 fixture)."""
    o = 1.1000
    c = o + 50 * PIP
    nxt_o = o + 40 * PIP
    nxt_c = o + 45 * PIP
    return [
        FakeBar(time=EVENT_T, open=o, high=c + 2 * PIP, low=o - 2 * PIP, close=c),
        FakeBar(time=EVENT_T + timedelta(minutes=15),
                open=nxt_o, high=nxt_c + 2 * PIP, low=nxt_o - 2 * PIP,
                close=nxt_c),
    ]


def _fire(agent, as_of: datetime, *, workspace=None):
    market = _market(as_of)
    thought = agent.observe(market, FullLedger())
    return agent.intend(market, thought, workspace=workspace)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class TestIdentity:
    def test_roster_identity_is_aoshi_not_sae(self):
        agent = A9AoshiV2()
        assert agent.agent_id == "aoshi_tokimitsu"
        assert agent.playstyle == "event_specialist"
        assert agent.tier == 1
        assert agent.home_tf == "M15"
        assert agent.canon_role.canon_player == "aoshi_tokimitsu"

    def test_alias_points_at_the_v2_class(self):
        assert AoshiTokimitsu is A9AoshiV2

    def test_v2_is_a_subclass_so_geometry_is_inherited(self):
        assert issubclass(A9AoshiV2, A9SaeV1)

    def test_trigger_thresholds_are_untouched(self):
        """Tier 0 changes no threshold -- §1.4's retune ban."""
        cfg = A9AoshiV2()._config
        assert cfg.fade_min_move_pips == 40.0
        assert cfg.fade_min_wick_frac == 0.5
        assert cfg.ride_min_retention == 0.7
        assert cfg.target_rr == 1.5
        assert cfg.fade_wait_min == 15
        assert cfg.ride_wait_min == 30
        assert cfg.fade_stop_padding_pips == 5.0


# ---------------------------------------------------------------------------
# §10.6 regression -- geometry byte-identity
# ---------------------------------------------------------------------------

class TestGeometryRegression:
    def test_fade_geometry_byte_identical_to_v1(self):
        bars = _fade_bars()
        at = EVENT_T + timedelta(minutes=15)
        p1 = _fire(_v1(bars), at)
        p2 = _fire(_v2(bars), at)
        assert isinstance(p1, AgentProposal)
        assert isinstance(p2, AgentProposal)
        assert p2.direction == p1.direction
        assert p2.entry == p1.entry
        assert p2.stop == p1.stop
        assert p2.rationale["mechanic"] == p1.rationale["mechanic"] == "sae_fade"

    def test_ride_geometry_byte_identical_to_v1(self):
        bars = _ride_bars()
        at = EVENT_T + timedelta(minutes=30)
        p1 = _fire(_v1(bars), at)
        p2 = _fire(_v2(bars), at)
        assert isinstance(p1, AgentProposal)
        assert isinstance(p2, AgentProposal)
        assert p2.direction == p1.direction
        assert p2.entry == p1.entry
        assert p2.stop == p1.stop
        assert p2.rationale["mechanic"] == p1.rationale["mechanic"] == "sae_ride"

    def test_primary_target_still_the_inherited_1_5r_rung(self):
        """The ladder is additive: rung 0 IS v1's single rung."""
        bars = _fade_bars()
        at = EVENT_T + timedelta(minutes=15)
        p1 = _fire(_v1(bars), at)
        p2 = _fire(_v2(bars), at)
        assert len(p1.ladder) == 1
        assert len(p2.ladder) > 1
        assert p2.ladder[0].price == pytest.approx(p1.ladder[0].price)
        assert p2.rationale["tp_multiples_r"][0] == pytest.approx(1.5)
        assert sum(r.fraction for r in p2.ladder) == pytest.approx(1.0)

    def test_declared_divergences_are_the_only_divergences(self):
        bars = _fade_bars()
        at = EVENT_T + timedelta(minutes=15)
        p1 = _fire(_v1(bars), at)
        p2 = _fire(_v2(bars), at)
        # v1 emits literals on every proposal; v2 must not.
        assert p1.conviction == pytest.approx(0.85)
        assert p1.regime_fit == pytest.approx(0.6)
        assert p2.rationale["v1_conviction"] == pytest.approx(0.85)
        assert p2.rationale["v1_regime_fit"] == pytest.approx(0.6)
        assert p2.valid_until == p1.valid_until
        assert p2.timestamp == p1.timestamp
        assert p2.rationale["tier0_not_an_alpha_claim"] is True

    def test_v1_thresholds_still_reject_what_they_rejected(self):
        """A sub-floor move must not fire on v2 either."""
        small = FakeBar(time=EVENT_T, open=1.1000, high=1.1010,
                        low=1.0995, close=1.1003)
        bars = [small, _fade_bars()[1]]
        at = EVENT_T + timedelta(minutes=15)
        assert _fire(_v1(bars), at) is None
        assert _fire(_v2(bars), at) is None


# ---------------------------------------------------------------------------
# (f) Event selection -- nearest, not earliest
# ---------------------------------------------------------------------------

class TestEventSelection:
    """v1 prefers the EARLIEST candidate in the window, so a 45-minute
    stale release outranks one printing in 5 minutes. v2 picks nearest."""

    STALE = EVENT_T
    IMMINENT = EVENT_T + timedelta(minutes=50)
    AS_OF = EVENT_T + timedelta(minutes=45)

    def _two_events(self) -> list[SimNewsEvent]:
        return [
            SimNewsEvent(time_utc=self.STALE, currency="USD", impact="High",
                         title="stale release"),
            SimNewsEvent(time_utc=self.IMMINENT, currency="USD", impact="High",
                         title="imminent release"),
        ]

    def test_v1_picks_the_earliest_candidate(self):
        agent = _v1(_fade_bars(), events=self._two_events())
        chosen = agent._nearest_scheduled_event(self.AS_OF)
        assert chosen is not None
        assert chosen.time_utc == self.STALE

    def test_v2_picks_the_release_nearest_to_as_of(self):
        agent = _v2(_fade_bars(), events=self._two_events())
        chosen = agent._nearest_scheduled_event(self.AS_OF)
        assert chosen is not None
        assert chosen.time_utc == self.IMMINENT

    def test_single_candidate_is_unchanged(self):
        at = EVENT_T + timedelta(minutes=15)
        assert (
            _v2(_fade_bars())._nearest_scheduled_event(at).time_utc
            == _v1(_fade_bars())._nearest_scheduled_event(at).time_utc
        )

    def test_equidistant_tie_falls_back_to_v1_rule(self):
        events = [
            SimNewsEvent(time_utc=EVENT_T - timedelta(minutes=10),
                         currency="USD", impact="High", title="earlier"),
            SimNewsEvent(time_utc=EVENT_T + timedelta(minutes=10),
                         currency="USD", impact="High", title="later"),
        ]
        agent = _v2(_fade_bars(), events=events)
        chosen = agent._nearest_scheduled_event(EVENT_T)
        assert chosen.time_utc == EVENT_T - timedelta(minutes=10)


# ---------------------------------------------------------------------------
# (d) Conviction / regime-fit calibration
# ---------------------------------------------------------------------------

class TestConvictionCalibration:
    def test_returns_v1_constants_at_the_calibration_point(self):
        """The change must be CENTRED, not a shift: at v1's own trigger
        boundary (impulse ratio 4.0, wick 0.50, T+15) the functions
        reproduce v1's hard-coded 0.85 / 0.60 exactly."""
        assert conviction_from_geometry(
            CALIB_MOVE_ATR_RATIO, CALIB_WICK_FRAC, CALIB_MINUTES_SINCE_RELEASE,
        ) == pytest.approx(CALIB_CONVICTION)
        assert regime_fit_from_geometry(
            CALIB_MOVE_ATR_RATIO, CALIB_MINUTES_SINCE_RELEASE,
        ) == pytest.approx(CALIB_REGIME_FIT)

    def test_monotone_increasing_in_impulse_ratio(self):
        vals = [
            conviction_from_geometry(r, 0.55, 20.0)
            for r in (2.0, 3.0, 4.0, 5.0, 6.0)
        ]
        assert all(b > a for a, b in zip(vals, vals[1:])), vals

    def test_monotone_increasing_in_wick_fraction(self):
        vals = [
            conviction_from_geometry(4.0, w, 20.0)
            for w in (0.40, 0.50, 0.60, 0.70)
        ]
        assert all(b > a for a, b in zip(vals, vals[1:])), vals

    def test_monotone_decreasing_in_minutes_since_release(self):
        vals = [
            conviction_from_geometry(4.0, 0.55, m)
            for m in (10.0, 20.0, 30.0, 45.0)
        ]
        assert all(b < a for a, b in zip(vals, vals[1:])), vals

    @pytest.mark.parametrize(
        "ratio,wick,mins",
        [
            (20.0, 1.00, 0.0),     # saturating high
            (0.5, 0.00, 200.0),    # saturating low
            (4.0, 0.50, 15.0),     # calibration point
            (0.0, 0.50, 15.0),     # degenerate ATR ratio
        ],
    )
    def test_clipped_to_the_declared_band(self, ratio, wick, mins):
        c = conviction_from_geometry(ratio, wick, mins)
        assert 0.50 <= c <= 0.95

    def test_clip_actually_binds_at_both_ends(self):
        assert conviction_from_geometry(20.0, 1.0, 0.0) == pytest.approx(0.95)
        assert conviction_from_geometry(0.5, 0.0, 200.0) == pytest.approx(0.50)

    def test_regime_fit_mirrors_conviction_for_the_sizing_channel(self):
        """F19 has no time input, so window proximity reaches sizing
        only through regime_fit -- which therefore falls as the print
        gets closer and more violent (defeat note §2 Tier 0 item 2)."""
        fresh_violent = regime_fit_from_geometry(9.0, 15.0)
        settled_modest = regime_fit_from_geometry(2.5, 60.0)
        assert fresh_violent < CALIB_REGIME_FIT < settled_modest
        assert 0.30 <= fresh_violent <= 0.90
        assert 0.30 <= settled_modest <= 0.90

    def test_live_proposal_is_centred_near_the_calibration_point(self):
        p = _fire(_v2(_fade_bars()), EVENT_T + timedelta(minutes=15))
        assert p.rationale["atr_source"] == "fallback"
        assert p.conviction == pytest.approx(0.862, abs=0.01)
        assert p.regime_fit == pytest.approx(0.55, abs=0.01)


# ---------------------------------------------------------------------------
# (a)/(b) Primitive dispersion -- G7 C5 / C6 measured directly
# ---------------------------------------------------------------------------

def _cv(xs: list[float]) -> float:
    """Sample CV -- same estimator as ``run_g7_v1_checkpoint_gate._cv``."""
    if len(xs) < 2:
        return 0.0
    m = statistics.mean(xs)
    return 0.0 if m == 0.0 else statistics.stdev(xs) / m


def _plausible_event_geometries():
    """A spread of post-release geometries the inherited trigger admits.

    ``sl_pips`` is derived from the fade construction rather than
    invented: for a rejection wick fraction ``w`` on an impulse of
    ``move`` pips, the stop sits ``w × move / (1 − w)`` pips beyond the
    close, plus 5 pips of padding.
    """
    for atr in (6.0, 10.0, 16.0, 24.0):
        for move in (45.0, 60.0, 90.0):
            for wick in (0.50, 0.55, 0.62):
                for mins in (15.0, 30.0, 45.0):
                    swing = move / (1.0 - wick)
                    sl = wick * move / (1.0 - wick) + 5.0
                    yield {
                        "atr_pips": atr,
                        "h1_swing_pips": swing,
                        "sl_pips": sl,
                        "conviction": conviction_from_geometry(
                            move / atr, wick, mins,
                        ),
                        "regime_fit": regime_fit_from_geometry(
                            move / atr, mins,
                        ),
                    }


class TestPrimitiveDispersion:
    def test_c5_lot_intent_cv_at_or_above_threshold(self):
        agent = A9AoshiV2()
        lots = [
            agent.lot_intent(
                g["conviction"], g["sl_pips"], EQUITY, g["regime_fit"],
            )
            for g in _plausible_event_geometries()
        ]
        assert all(lot > 0 for lot in lots)
        assert _cv(lots) >= 0.10, f"lot CV {_cv(lots):.4f} < 0.10"

    def test_c6_risk_intent_cv_at_or_above_threshold(self):
        agent = A9AoshiV2()
        sls, tp1s = [], []
        for g in _plausible_event_geometries():
            sl, ladder = agent.risk_intent(
                g["conviction"], g["atr_pips"], g["h1_swing_pips"],
            )
            sls.append(sl)
            tp1s.append(ladder[0])
        assert max(_cv(sls), _cv(tp1s)) >= 0.10, (
            f"sl CV {_cv(sls):.4f}, tp1 CV {_cv(tp1s):.4f}"
        )

    def test_primitives_are_no_longer_the_invalid_fallback(self):
        """Before registration `event_specialist` was absent from both
        dispatch tables, so A9 silently took the fixed-lot / (40, [80])
        fallbacks the module headers label 'not a valid v1
        implementation' (defeat note §1.5, G7 C5 + C6)."""
        agent = A9AoshiV2()
        assert agent.lot_intent(0.85, 45.0, EQUITY, 0.60) != 0.1
        sl, ladder = agent.risk_intent(0.85, 22.0, 130.0)
        assert (sl, ladder) != (40.0, [80.0])
        assert len(ladder) == 2
        assert ladder[0] == pytest.approx(1.5 * sl)

    def test_violent_print_sizes_down_not_up(self):
        """Defeat note §2 Tier 0 item 2, verbatim: 'a violent print is a
        wider-stop, SMALLER-lot trade, not a bigger one'."""
        agent = A9AoshiV2()
        atr, wick, mins = 15.0, 0.50, 15.0

        def lot_for(move: float) -> float:
            ratio = move / atr
            return agent.lot_intent(
                conviction_from_geometry(ratio, wick, mins),
                wick * move / (1.0 - wick) + 5.0,
                EQUITY,
                regime_fit_from_geometry(ratio, mins),
            )

        assert lot_for(140.0) < lot_for(45.0)

    def test_narrow_pre_release_window_sizes_down(self):
        """Second half of the same clause: size down as the pre-release
        window narrows. Freshest tape is the most hazardous to carry."""
        agent = A9AoshiV2()
        ratio, wick = 4.0, 0.50

        def lot_at(mins: float) -> float:
            return agent.lot_intent(
                conviction_from_geometry(ratio, wick, mins),
                50.0,
                EQUITY,
                regime_fit_from_geometry(ratio, mins),
            )

        assert lot_at(15.0) < lot_at(75.0)


# ---------------------------------------------------------------------------
# (c) F21 -- workspace read and defensive abstention
# ---------------------------------------------------------------------------

def _incumbent_thought(
    *, direction: str, as_of: datetime, live: bool = True,
    agent_id: str = "isagi_yoichi",
) -> Thought:
    published = as_of - timedelta(hours=1)
    end = as_of + timedelta(hours=6) if live else as_of - timedelta(minutes=1)
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent_id,
        tick_id=0,
        timestamp=published,
        symbol="EURUSD",
        narrative=f"[isagi v1] holding EURUSD {direction}.",
        tags=["zone_d1_against"],
        confidence_in_thought=0.65,
        expected_action=f"{direction}_on_H4_close",
        coordinate=Coordinate(
            agent_id=agent_id,
            symbol="EURUSD",
            price_lo=1.0990,
            price_hi=1.1010,
            time_start=published,
            time_end=end,
            vol_band=(0.5, 2.0),
            regime_predicate="ranging",
            expected_strength=0.65,
            direction_bias=direction,
        ),
        decision_horizon=published,
        ttl_ticks=6,
        references=[],
    )


def _snapshot(thoughts: list[Thought], as_of: datetime, tick_id: int = 1):
    ws = ReasoningWorkspace()
    for t in thoughts:
        ws.publish(t)
    return ws.snapshot_at_barrier(as_of=as_of, current_tick=tick_id)


class TestWorkspaceAbstention:
    AT = EVENT_T + timedelta(minutes=15)

    def test_fires_when_workspace_is_empty(self):
        p = _fire(_v2(_fade_bars()), self.AT, workspace=_snapshot([], self.AT))
        assert isinstance(p, AgentProposal)
        assert p.rationale["workspace_read_ok"] is True

    def test_fires_when_workspace_is_absent(self):
        assert isinstance(_fire(_v2(_fade_bars()), self.AT), AgentProposal)

    def test_abstains_against_an_opposing_tier1_incumbent(self):
        """v2's fade on a bullish rejection is SHORT; a Tier-1 incumbent
        holding LONG owns the slot, so Aoshi stands down."""
        snap = _snapshot(
            [_incumbent_thought(direction="long", as_of=self.AT)], self.AT,
        )
        assert _fire(_v2(_fade_bars()), self.AT, workspace=snap) is None

    def test_fires_when_the_incumbent_agrees(self):
        snap = _snapshot(
            [_incumbent_thought(direction="short", as_of=self.AT)], self.AT,
        )
        p = _fire(_v2(_fade_bars()), self.AT, workspace=snap)
        assert isinstance(p, AgentProposal)
        assert p.direction == "short"

    def test_expired_claim_releases_the_slot(self):
        snap = _snapshot(
            [_incumbent_thought(direction="long", as_of=self.AT, live=False)],
            self.AT,
        )
        assert isinstance(
            _fire(_v2(_fade_bars()), self.AT, workspace=snap), AgentProposal,
        )

    def test_non_tier1_peer_does_not_block(self):
        snap = _snapshot(
            [_incumbent_thought(
                direction="long", as_of=self.AT, agent_id="chigiri_hyoma",
            )],
            self.AT,
        )
        assert isinstance(
            _fire(_v2(_fade_bars()), self.AT, workspace=snap), AgentProposal,
        )

    def test_read_workspace_is_backwards_only_and_peer_scoped(self):
        agent = _v2(_fade_bars())
        snap = _snapshot(
            [_incumbent_thought(direction="long", as_of=self.AT)], self.AT,
        )
        peers = agent.read_workspace(snap, self.AT)
        assert isinstance(peers, tuple)
        assert [t.agent_id for t in peers] == ["isagi_yoichi"]
        assert all(t.timestamp <= self.AT for t in peers)
        assert agent.read_workspace(None, self.AT) == ()

    def test_opposing_incumbent_names_the_blocker(self):
        agent = _v2(_fade_bars())
        snap = _snapshot(
            [_incumbent_thought(direction="long", as_of=self.AT)], self.AT,
        )
        assert agent.opposing_incumbent(
            workspace=snap, symbol="EURUSD", direction="short", as_of=self.AT,
        ) == ("isagi_yoichi", "long")
        assert agent.opposing_incumbent(
            workspace=snap, symbol="EURUSD", direction="long", as_of=self.AT,
        ) is None


# ---------------------------------------------------------------------------
# Playstyle registration purity -- the addition changed nothing else
# ---------------------------------------------------------------------------

LOT_PROBES = [
    (0.50, 20.0, 100.0, 0.30),
    (0.65, 30.0, 100.0, 0.50),
    (0.85, 45.0, 250.0, 0.70),
    (0.95, 60.0, 500.0, 0.90),
]
RISK_PROBES = [
    (0.50, 10.0, 50.0),
    (0.65, 20.0, 90.0),
    (0.85, 30.0, 140.0),
    (0.95, 45.0, 200.0),
]

# Captured from the dispatch tables BEFORE `event_specialist` was added
# (2026-08-19). Any diff here means the Tier-0 registration was not a
# pure addition.
GOLDEN_LOT = {
    "conservative_metavision": [0.15, 0.14, 0.13, 0.12],
    "rebel_tight": [0.02, 0.03, 0.03, 0.04],
    "analytical_precision": [0.03, 0.05, 0.09, 0.12],
    "speed_momentum": [0.07, 0.12, 0.20, 0.25],
    "copier_hrp": [0.08, 0.11, 0.15, 0.15],
    "confluence_only": [0.03, 0.06, 0.08, 0.09],
    "solo_king": [0.13, 0.11, 0.09, 0.08],
    "defensive": [0.08, 0.11, 0.14, 0.15],
}
GOLDEN_RISK = {
    "conservative_metavision": [
        (30.0, [45.0]), (30.0, [45.0]), (39.0, [58.5]), (50.0, [75.0]),
    ],
    "rebel_tight": [
        (15.0, [45.0]), (16.0, [48.0]), (24.0, [72.0]), (25.0, [75.0]),
    ],
    "analytical_precision": [
        (15.0, [30.0, 60.0, 90.0]), (18.0, [36.0, 72.0, 108.0]),
        (28.0, [56.0, 112.0, 168.0]), (35.0, [70.0, 140.0, 210.0]),
    ],
    "speed_momentum": [
        (20.0, [60.0]), (24.0, [72.0]), (36.0, [108.0]), (40.0, [120.0]),
    ],
    "copier_hrp": [
        (20.0, [40.0]), (26.0, [52.0]), (39.0, [78.0]), (45.0, [90.0]),
    ],
    "confluence_only": [
        (20.0, [30.0, 60.0, 90.0]), (26.0, [39.0, 78.0, 117.0]),
        (39.0, [58.5, 117.0, 175.5]), (40.0, [60.0, 120.0, 180.0]),
    ],
    "solo_king": [
        (20.0, [30.0, 60.0]), (22.5, [33.75, 67.5]),
        (35.0, [52.5, 105.0]), (35.0, [52.5, 105.0]),
    ],
    "defensive": [
        (25.0, [37.5]), (30.0, [45.0]), (45.0, [67.5]), (45.0, [67.5]),
    ],
}


class TestPlaystyleAdditionPurity:
    @pytest.mark.parametrize("playstyle", sorted(GOLDEN_LOT))
    def test_existing_lot_intent_outputs_unchanged(self, playstyle):
        got = [
            playstyle_lot_intent(*probe, playstyle=playstyle)
            for probe in LOT_PROBES
        ]
        assert got == pytest.approx(GOLDEN_LOT[playstyle])

    @pytest.mark.parametrize("playstyle", sorted(GOLDEN_RISK))
    def test_existing_risk_intent_outputs_unchanged(self, playstyle):
        for probe, (want_sl, want_ladder) in zip(
            RISK_PROBES, GOLDEN_RISK[playstyle],
        ):
            sl, ladder = playstyle_risk_intent(*probe, playstyle=playstyle)
            assert sl == pytest.approx(want_sl)
            assert ladder == pytest.approx(want_ladder)

    def test_event_specialist_no_longer_hits_the_unknown_fallback(self):
        assert playstyle_lot_intent(
            0.85, 45.0, EQUITY, 0.60, playstyle="event_specialist",
        ) != 0.1
        assert playstyle_risk_intent(
            0.85, 22.0, 130.0, playstyle="event_specialist",
        ) != (40.0, [80.0])

    def test_unknown_playstyle_still_falls_back(self):
        assert playstyle_lot_intent(
            0.85, 45.0, EQUITY, 0.60, playstyle="not_a_playstyle",  # type: ignore[arg-type]
        ) == 0.1
