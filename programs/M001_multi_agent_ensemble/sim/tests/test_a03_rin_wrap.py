"""A3 Rin v1 wrap tests.

Asserts:
  * Rin wraps `SupplyDemandAlpha(htf_align=D1, htf_align_mode=against,
    target_rr=2.5)` on EURUSD.
  * Off-symbol abstention (USDCAD/GBPUSD ticks emit observation-only).
  * The precision-stop-floor filter rejects signals with stop_pips <
    RIN_V1_MIN_STOP_PIPS (observation-only, no proposal).
  * When the precision gate passes, conviction lands at base + 0.15
    (above Nagi's 0.7 floor) and `intend()` emits a proposal.
  * Inherited tags include `zone_d1_against` + `htf_against` so Rin
    pairs naturally with Isagi for Nagi confluence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import MarketState


pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="A3 Rin wraps production zone_alpha; requires prod repo on path",
)


def _build_synthetic_eurusd_bars(n: int = 800):
    """Synthetic EURUSD H4 series with a clean D1 trend + counter-trend
    zone touch -- the zone_d1_against gate fires on the pullback.
    """
    from agent.types import Bar, Timeframe
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = 1.1000
    # Strong UPTREND of ~ 150 H4 bars (so D1 sees a clear uptrend).
    for i in range(300):
        new_price = price + 0.00040
        bars.append(Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + 0.00025,
            low=min(price, new_price) - 0.00015,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    impulse_top = price
    # Sharp DOWN impulse (creates supply zone, baseline against the D1 trend).
    for i in range(8):
        new_price = price - 0.00400
        bars.append(Bar(
            time=base + timedelta(hours=4 * (300 + i)),
            open=price,
            high=price + 0.00020,
            low=new_price - 0.00020,
            close=new_price,
            volume=300.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    # Pullback INTO the supply zone (above the D1 trend's recent range).
    pullback_target = impulse_top - 0.00010
    n_pullback = 50
    for i in range(n_pullback):
        delta = (pullback_target - price) / max(n_pullback - i, 1)
        new_price = price + delta
        bars.append(Bar(
            time=base + timedelta(hours=4 * (300 + 8 + i)),
            open=price,
            high=new_price + 0.00010,
            low=price - 0.00005,
            close=new_price,
            volume=120.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    # Chop runway.
    chop = max(60, n - len(bars))
    for i in range(chop):
        new_price = price + (-0.00020 if i % 3 == 0 else 0.00010)
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=max(price, new_price) + 0.00020,
            low=min(price, new_price) - 0.00020,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    return bars


def _bar_to_market(bar, tick_id: int, symbol: str = "EURUSD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe=bar.timeframe.value,
        as_of=bar.time,
        open=float(bar.open), high=float(bar.high),
        low=float(bar.low), close=float(bar.close),
        volume=float(bar.volume),
    )


def _make_rin():
    from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
    return A3RinV1()


# ---------------------------------------------------------------------------
# Off-symbol abstention
# ---------------------------------------------------------------------------

def test_rin_abstains_on_usdcad():
    rin = _make_rin()
    market = MarketState(
        tick_id=0, symbol="USDCAD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.3, high=1.31, low=1.29, close=1.305, volume=100.0,
    )
    ledger = FullLedger()
    t = rin.observe(market, ledger)
    assert t.coordinate is None
    assert "rin_abstain" in t.tags
    assert "rin_abstain_symbol" in t.tags
    assert rin.intend(market, t) is None


def test_rin_abstains_on_gbpusd():
    rin = _make_rin()
    market = MarketState(
        tick_id=0, symbol="GBPUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.25, high=1.26, low=1.24, close=1.255, volume=100.0,
    )
    ledger = FullLedger()
    t = rin.observe(market, ledger)
    assert "rin_abstain" in t.tags
    assert "rin_abstain_symbol" in t.tags
    assert rin.intend(market, t) is None


def test_rin_observation_only_when_unprepared():
    rin = _make_rin()
    market = MarketState(
        tick_id=0, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.1, high=1.11, low=1.09, close=1.105, volume=100.0,
    )
    ledger = FullLedger()
    t = rin.observe(market, ledger)
    assert t.coordinate is None
    assert "rin_abstain" in t.tags
    assert "abstain_reason:unprepared" in t.tags
    assert rin.intend(market, t) is None


# ---------------------------------------------------------------------------
# Inner-alpha wrap parity
# ---------------------------------------------------------------------------

def test_rin_wraps_zone_d1_against_with_higher_rr():
    """Inner alpha must use `target_rr=2.5`; the production cell at
    target_rr=2.5 is a valid SupplyDemandAlpha configuration. Spot-check
    by comparing entry/stop to a raw alpha at the same params.
    """
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute

    bars = _build_synthetic_eurusd_bars(800)
    cfg = load_config()
    raw = SupplyDemandAlpha(
        cfg=cfg, htf_align="D1", htf_align_mode="against",
        htf_lookback=10, htf_min_move_pips=60.0, target_rr=2.5,
    )
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)

    raw_signals: dict[int, object] = {}
    for i in range(200, len(bars) - 1):
        s = raw.signal(actx, i)
        if s is not None:
            raw_signals[i] = s

    if not raw_signals:
        pytest.skip("synthetic series produced no zone_d1_against signals at target_rr=2.5")

    rin = _make_rin()
    rin.prepare("EURUSD", bars)

    for i in list(raw_signals.keys())[:5]:
        sig = rin.inner_signal_at("EURUSD", i)
        raw_sig = raw_signals[i]
        assert sig is not None
        assert sig.direction.value == raw_sig.direction.value
        assert sig.entry == pytest.approx(float(raw_sig.entry))
        assert sig.stop == pytest.approx(float(raw_sig.stop))
        assert sig.take_profit == pytest.approx(float(raw_sig.take_profit))


# ---------------------------------------------------------------------------
# Precision gate behaviour
# ---------------------------------------------------------------------------

def test_rin_precision_lift_applied_when_floor_met():
    """When the synthetic series produces a zone touch with stop_pips
    >= RIN_V1_MIN_STOP_PIPS (20), Rin's observed Thought must carry
    `rin_precision_lift_applied` and conviction >= 0.7 (above Nagi).
    """
    from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import (
        RIN_V1_MIN_STOP_PIPS, RIN_V1_PIP_SIZE,
    )

    bars = _build_synthetic_eurusd_bars(800)
    rin = _make_rin()
    rin.prepare("EURUSD", bars)

    lift_seen = False
    rejected_seen = False
    for i in range(200, len(bars) - 1):
        sig = rin.inner_signal_at("EURUSD", i)
        if sig is None:
            continue
        stop_pips = abs(float(sig.entry) - float(sig.stop)) / RIN_V1_PIP_SIZE
        market = _bar_to_market(bars[i], i, symbol="EURUSD")
        t = rin.observe(market, FullLedger())
        if stop_pips >= RIN_V1_MIN_STOP_PIPS:
            assert t.coordinate is not None
            assert "rin_precision_lift_applied" in t.tags
            # Lift puts conviction above 0.7 (Nagi floor).
            assert t.confidence_in_thought >= 0.70
            assert "zone_d1_against" in t.tags
            assert "htf_against" in t.tags
            lift_seen = True
        else:
            assert t.coordinate is None
            assert "rin_precision_rejected" in t.tags
            rejected_seen = True
        if lift_seen and rejected_seen:
            break
    if not lift_seen:
        pytest.skip(
            "synthetic series produced no qualifying Rin precision-floor "
            "signals; the synthetic stops are too small"
        )


def test_rin_intend_skipped_when_precision_filter_rejects():
    """Even if the inner alpha fires, `intend()` must return None when
    the precision gate rejected the signal (Thought has no lift tag).
    """
    bars = _build_synthetic_eurusd_bars(800)
    rin = _make_rin()
    rin.prepare("EURUSD", bars)

    for i in range(200, len(bars) - 1):
        sig = rin.inner_signal_at("EURUSD", i)
        if sig is None:
            continue
        market = _bar_to_market(bars[i], i, symbol="EURUSD")
        t = rin.observe(market, FullLedger())
        if "rin_precision_rejected" in t.tags:
            p = rin.intend(market, t)
            assert p is None
            return
    pytest.skip("synthetic series produced no precision-rejected zone signals")


def test_rin_intend_emits_proposal_on_qualifying_signal():
    """Full path: precision gate passes -> intend emits a Proposal with
    the lifted conviction carried through.

    Under Phase T-evolve (2026-07-01 evening) Rin's `intend()` now
    applies an additional lone-read lift when no aligned peer thought
    is present. This test passes `workspace=None`, which maps to
    peer_agree=0 -> Rin is the lone reader and lifts by
    `RIN_V1_LONE_READ_LIFT`.
    """
    from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import (
        RIN_V1_CONV_CAP, RIN_V1_LONE_READ_LIFT,
    )

    bars = _build_synthetic_eurusd_bars(800)
    rin = _make_rin()
    rin.prepare("EURUSD", bars)

    for i in range(200, len(bars) - 1):
        sig = rin.inner_signal_at("EURUSD", i)
        if sig is None:
            continue
        market = _bar_to_market(bars[i], i, symbol="EURUSD")
        t = rin.observe(market, FullLedger())
        if "rin_precision_lift_applied" not in t.tags:
            continue
        p = rin.intend(market, t)
        assert p is not None
        assert p.symbol == "EURUSD"
        assert p.direction in ("long", "short")
        # Phase T-evolve: conviction = precision + lone_read (clipped).
        expected = min(
            RIN_V1_CONV_CAP,
            t.confidence_in_thought + RIN_V1_LONE_READ_LIFT,
        )
        assert p.conviction == pytest.approx(expected)
        assert p.rationale["precision_lift_applied"] is True
        assert p.rationale["lone_read_lift_applied"] is True
        assert p.rationale["peer_agree_count"] == 0
        assert p.rationale["wrapped"].endswith("SupplyDemandAlpha")
        assert p.rationale["htf_align"] == "D1"
        assert p.rationale["htf_align_mode"] == "against"
        return
    pytest.skip("synthetic series produced no qualifying Rin precision signals")


# ---------------------------------------------------------------------------
# Phase T-evolve peer-yield-and-lift tests (Rin v1.1, 2026-07-01 evening)
# ---------------------------------------------------------------------------

class TestRinPhaseTEvolve:
    """Rin v1.1 peer-yield-and-lift semantics.

    - When Isagi (or any peer) publishes an aligned Thought on the
      same symbol, Rin YIELDS -- `intend()` returns None so Isagi's
      metavision lift wins the aggregator tie-break.
    - When peers disagree with Rin's direction (or no peers wrote),
      Rin applies `RIN_V1_LONE_READ_LIFT` on top of the precision
      lift, decisively winning the tie-break Isagi can't lift into.
    - Rationale carries the peer_agree/peer_disagree counts + the
      `isagi_would_lift_metavision` boolean for post-hoc attribution.
    """

    def _make_snapshot_with_peer(
        self, tick_id: int, symbol: str, peer_dir: str,
        peer_id: str = "isagi_yoichi",
    ):
        """Build a WorkspaceSnapshot where a named peer published an
        aligned/disagreeing Thought on `symbol` at tick_id-1.
        """
        from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
            ReasoningWorkspace,
        )
        from programs.M001_multi_agent_ensemble.sim.core.types import (
            SCHEMA_VERSION, Coordinate, Thought,
        )
        base = datetime(2020, 5, 1, tzinfo=timezone.utc)
        ws = ReasoningWorkspace()
        peer_t = Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=peer_id,
            tick_id=max(tick_id - 1, 0),
            timestamp=base,
            symbol=symbol,
            narrative="peer_thought",
            tags=["peer_test"],
            confidence_in_thought=0.7,
            expected_action="long_on_H4_close",
            coordinate=Coordinate(
                agent_id=peer_id,
                symbol=symbol,
                price_lo=1.09, price_hi=1.10,
                time_start=base, time_end=base + timedelta(hours=24),
                vol_band=(0.5, 1.0),
                regime_predicate="test",
                expected_strength=0.7,
                direction_bias=peer_dir,
            ),
            decision_horizon=base,
            ttl_ticks=6,
            references=[],
        )
        ws.publish(peer_t)
        return ws.snapshot(
            as_of=base + timedelta(hours=4),
            current_tick=tick_id,
        )

    def test_rin_yields_when_peer_agrees(self):
        """When Isagi (peer) publishes an aligned Thought on the same
        symbol, Rin's `intend()` returns None -> she cedes the shot.
        """
        bars = _build_synthetic_eurusd_bars(800)
        rin = _make_rin()
        rin.prepare("EURUSD", bars)
        for i in range(200, len(bars) - 1):
            sig = rin.inner_signal_at("EURUSD", i)
            if sig is None:
                continue
            market = _bar_to_market(bars[i], i, symbol="EURUSD")
            t = rin.observe(market, FullLedger())
            if "rin_precision_lift_applied" not in t.tags:
                continue
            snap = self._make_snapshot_with_peer(
                tick_id=market.tick_id,
                symbol="EURUSD",
                peer_dir=sig.direction.value,   # aligned with Rin's dir
            )
            p = rin.intend(market, t, workspace=snap)
            assert p is None, (
                "Rin should yield to Isagi's metavision when peers align"
            )
            return
        pytest.skip("synthetic series produced no qualifying Rin signals")

    def test_rin_fires_hard_when_peer_disagrees(self):
        """When a peer disagrees with Rin's direction, Isagi's
        metavision won't fire, so Rin lone-read-lifts to 0.90.
        """
        from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import (
            RIN_V1_CONV_CAP, RIN_V1_LONE_READ_LIFT,
        )
        bars = _build_synthetic_eurusd_bars(800)
        rin = _make_rin()
        rin.prepare("EURUSD", bars)
        for i in range(200, len(bars) - 1):
            sig = rin.inner_signal_at("EURUSD", i)
            if sig is None:
                continue
            market = _bar_to_market(bars[i], i, symbol="EURUSD")
            t = rin.observe(market, FullLedger())
            if "rin_precision_lift_applied" not in t.tags:
                continue
            opposite_dir = (
                "short" if sig.direction.value == "long" else "long"
            )
            snap = self._make_snapshot_with_peer(
                tick_id=market.tick_id,
                symbol="EURUSD",
                peer_dir=opposite_dir,
            )
            p = rin.intend(market, t, workspace=snap)
            assert p is not None
            expected = min(
                RIN_V1_CONV_CAP,
                t.confidence_in_thought + RIN_V1_LONE_READ_LIFT,
            )
            assert p.conviction == pytest.approx(expected)
            assert p.rationale["lone_read_lift_applied"] is True
            assert p.rationale["peer_disagree_count"] == 1
            assert p.rationale["peer_agree_count"] == 0
            assert p.rationale["isagi_would_lift_metavision"] is False
            return
        pytest.skip("synthetic series produced no qualifying Rin signals")

    def test_rin_fires_when_no_workspace(self):
        """Backwards compat: with `workspace=None`, Rin still fires
        (peer counts default to zero -> she is the lone reader).
        """
        from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import (
            RIN_V1_LONE_READ_LIFT,
        )
        bars = _build_synthetic_eurusd_bars(800)
        rin = _make_rin()
        rin.prepare("EURUSD", bars)
        for i in range(200, len(bars) - 1):
            sig = rin.inner_signal_at("EURUSD", i)
            if sig is None:
                continue
            market = _bar_to_market(bars[i], i, symbol="EURUSD")
            t = rin.observe(market, FullLedger())
            if "rin_precision_lift_applied" not in t.tags:
                continue
            p = rin.intend(market, t, workspace=None)
            assert p is not None
            assert p.rationale["lone_read_lift_applied"] is True
            assert p.rationale["peer_seen_count"] == 0
            assert (
                p.conviction >=
                t.confidence_in_thought + RIN_V1_LONE_READ_LIFT - 1e-6
                or p.conviction == 1.0
            )
            return
        pytest.skip("synthetic series produced no qualifying Rin signals")
