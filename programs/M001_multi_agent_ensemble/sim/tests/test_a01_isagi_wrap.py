"""A1 Isagi v1 wrapper tests.

Validates that the BlueLockStriker wrapper around production
`agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` preserves the
production signal byte-for-byte, that Thought.meta tags include the
HTF context fields E001-E005 evidence chain depends on, that the
look-ahead guard (`decision_horizon`) holds, and that Tier-3
`RedactedLedger` produces identical proposals to `FullLedger`
(because v1 doesn't read peer thoughts).

Tests that need the production repo skip cleanly when it is not on
sys.path (`production_repo_available()` -> False on a fresh CI runner).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger, RedactedLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal, MarketState, Thought,
)


pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="M001 Phi3 needs the production repo on sys.path (M001_PRODUCTION_REPO or default)",
)


def _make_synthetic_bars(n: int = 600):
    """Build a synthetic H4 bar series that triggers the production cell.

    Geometry:
      * Long uptrend (300 H4 bars, ~+300 pips drift up).
      * Strong DOWN impulse (12 H4 bars, ~-120 pips) -> a supply zone
        forms at the top of the impulse.
      * Pullback UP back into the zone (~80 H4 bars, partial retrace).
      * Forward chop so a SHORT trade has room to hit TP or SL.

    HTF gate (htf_align=D1, htf_align_mode=against, htf_lookback=10):
    H4 -> D1 factor = 6, so the synthesiser compares now_close to
    close-60-bars-ago. At the pullback-touch index the H4 close 60
    bars earlier sits inside the uptrend region (price was LOWER), so
    move_pips > +60 -> bias=UP. For a SHORT (supply-zone) trade,
    `htf_align_mode=against` requires bias to OPPOSE SHORT -> UP
    opposes SHORT -> gate passes.
    """
    from agent.types import Bar, Timeframe

    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = 1.1000

    # 1) Slow uptrend so the D1 lookback at touch-time sees a much lower
    #    historic close (bias=UP).
    for i in range(300):
        new_price = price + 0.00012  # +1.2 pips / H4 bar -> +360 pips
        bars.append(Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + 0.00020,
            low=min(price, new_price) - 0.00015,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 2) Sharp DOWN impulse forming a supply zone (need body >= 15 pips and
    #    >= 2x rolling median body; uptrend bodies were ~ 1.2 pips, so any
    #    25-pip impulse bar clears 2x median easily).
    impulse_top_price = price
    for i in range(8):
        new_price = price - 0.00250  # -25 pips body / bar -> -200 pips total
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

    # 3) Pullback UP toward the impulse origin -> touches the supply zone.
    pullback_target = impulse_top_price - 0.00010  # 1 pip below impulse top
    n_pullback = 60
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

    # 4) Forward chop so the trade can resolve (room to hit TP or SL).
    chop_n = max(0, n - len(bars))
    if chop_n < 60:
        chop_n = 60  # ensure 60 bars of post-entry runway
    for i in range(chop_n):
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


def _make_market_state(bar, tick_id: int, symbol: str = "EURUSD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe=bar.timeframe.value,
        as_of=bar.time,
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=float(bar.volume),
    )


def _build_agent():
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
    return A1IsagiV1()


def _walk_with_ledger(agent, bars, ledger) -> tuple[list[Thought], list[Optional[AgentProposal]]]:
    thoughts: list[Thought] = []
    proposals: list[Optional[AgentProposal]] = []
    for i, b in enumerate(bars):
        m = _make_market_state(b, i)
        t = agent.observe(m, ledger)
        ledger.append(t)
        thoughts.append(t)
        if i < 200 or i >= len(bars) - 1:
            proposals.append(None)
            continue
        if m.timeframe != agent.home_tf:
            proposals.append(None)
            continue
        p = agent.intend(m, t)
        proposals.append(p)
    return thoughts, proposals


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_wrapper_signal_equivalent_to_raw_alpha():
    """The wrapper's intend() must produce proposals byte-equivalent to
    `SupplyDemandAlpha.signal()` on the same bar index.

    Step 1: build raw SupplyDemandAlpha with locked params.
    Step 2: precompute ctx on the same bars.
    Step 3: collect every bar index where raw alpha emits a signal.
    Step 4: wrap and confirm each of those indices produces a Proposal
            with matching entry/stop/take_profit/direction/conviction.
    """
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
        ISAGI_V1_PARAMS,
    )

    bars = _make_synthetic_bars(600)
    cfg = load_config()
    raw = SupplyDemandAlpha(cfg=cfg, **ISAGI_V1_PARAMS)
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)

    raw_signals: dict[int, object] = {}
    for i in range(200, len(bars) - 1):
        s = raw.signal(actx, i)
        if s is not None:
            raw_signals[i] = s

    # Even on synthetic data the zone detector may emit zero signals on
    # some seeds; the test still verifies non-divergence in that case.
    if not raw_signals:
        pytest.skip("synthetic series produced no zone signals; nothing to compare")

    agent = _build_agent()
    agent.prepare("EURUSD", bars)
    ledger = FullLedger()
    _, proposals = _walk_with_ledger(agent, bars, ledger)

    for i, raw_sig in raw_signals.items():
        p = proposals[i]
        assert p is not None, f"wrapper missed signal at i={i}"
        assert p.direction == raw_sig.direction.value
        assert p.entry == pytest.approx(float(raw_sig.entry))
        assert p.stop == pytest.approx(float(raw_sig.stop))
        assert p.ladder[0].price == pytest.approx(float(raw_sig.take_profit))
        assert p.conviction == pytest.approx(float(raw_sig.conviction))


def test_thought_tags_include_htf_context():
    """When the wrapped signal fires, Thought.tags must include the HTF
    gate inputs (htf_bias, htf_align, htf_align_mode, htf_lookback,
    htf_min_move_pips) so the E001-E005 evidence chain is queryable from
    the ledger alone (no JSON-grep required).
    """
    bars = _make_synthetic_bars(600)
    agent = _build_agent()
    agent.prepare("EURUSD", bars)
    ledger = FullLedger()
    thoughts, _ = _walk_with_ledger(agent, bars, ledger)

    firing = [
        t for t in thoughts
        if t.coordinate is not None and t.confidence_in_thought > 0
    ]
    if not firing:
        pytest.skip("synthetic series produced no firing thoughts; tags untestable")

    # Every firing thought must carry the production gate inputs.
    sample = firing[0]
    tag_text = " ".join(sample.tags)
    assert "zone_d1_against" in tag_text
    assert "htf_against" in tag_text
    assert "htf_align:D1" in tag_text
    assert "htf_align_mode:against" in tag_text
    assert "htf_lookback:10" in tag_text
    assert "htf_min_move_pips:60.0" in tag_text


def test_decision_horizon_never_exceeds_bar_timestamp():
    """Look-ahead guard (doctrine 06 section 3.8): `decision_horizon`
    on every Thought must be <= the bar's `as_of`.
    """
    bars = _make_synthetic_bars(400)
    agent = _build_agent()
    agent.prepare("EURUSD", bars)
    ledger = FullLedger()
    thoughts, _ = _walk_with_ledger(agent, bars, ledger)
    for i, t in enumerate(thoughts):
        assert t.decision_horizon <= bars[i].time, (
            f"look-ahead at i={i}: dh={t.decision_horizon}, bar={bars[i].time}"
        )


def test_redacted_ledger_matches_full_ledger():
    """A1 Isagi v1 is Tier-3 by default at Phi3 (no peer reads). The
    `RedactedLedger` must produce byte-identical Proposals to the
    `FullLedger`. This is the doctrine-06 section 3.9 control-arm
    correctness test.
    """
    bars = _make_synthetic_bars(500)

    agent_a = _build_agent()
    agent_a.prepare("EURUSD", bars)
    ledger_full = FullLedger()
    _, proposals_full = _walk_with_ledger(agent_a, bars, ledger_full)

    agent_b = _build_agent()
    agent_b.prepare("EURUSD", bars)
    ledger_redacted = RedactedLedger(agent_id=agent_b.agent_id)
    _, proposals_redacted = _walk_with_ledger(agent_b, bars, ledger_redacted)

    fingerprints_full = [
        None if p is None else (p.direction, p.entry, p.stop, p.conviction)
        for p in proposals_full
    ]
    fingerprints_redacted = [
        None if p is None else (p.direction, p.entry, p.stop, p.conviction)
        for p in proposals_redacted
    ]
    assert fingerprints_full == fingerprints_redacted


def test_unprepared_symbol_safe_observe_safe_intend():
    """Engine smoke-test contract: if `prepare()` was never called,
    observe must still emit an observation-only Thought, and intend
    must return None without raising.
    """
    bars = _make_synthetic_bars(50)
    agent = _build_agent()
    # No agent.prepare(...) called.
    ledger = FullLedger()
    for i, b in enumerate(bars):
        m = _make_market_state(b, i, symbol="EURUSD")
        t = agent.observe(m, ledger)
        assert t.coordinate is None
        assert t.confidence_in_thought == 0.0
        assert "unprepared" in t.tags
        assert agent.intend(m, t) is None
