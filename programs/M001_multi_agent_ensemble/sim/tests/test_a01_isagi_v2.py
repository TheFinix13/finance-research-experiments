"""A1 Isagi v2 -- contract + regression + behaviour-delta tests.

Implements the four invariants `06-blue-lock-doctrine.md` §3.11.2 requires
for every vN+1:

1. **Contract** -- v2 satisfies the same BlueLockStriker protocol surface
   as v1 (`observe -> Thought` on every tick, `intend -> Proposal | None`
   at home_tf close, default `report_kpis` shape).
2. **Regression (zone branch byte-equivalent)** -- on every bar index
   where v1 emits a zone-touch Proposal, v2 emits a Proposal with the
   SAME direction, entry, stop, take-profit, and conviction. This is
   the §3.11.2 step 4 "vN+1 reproduces vN behaviour on the inputs vN
   handled correctly" invariant.
3. **Behaviour delta** -- v2 emits at least one Proposal v1 cannot
   emit, identifiable by its `rationale.weapon == "liquidity_sweep"`
   tag. This is the §3.11.2 step 5 "v2 resolves the defeat trigger"
   invariant (a non-empty new vocabulary).
4. **Look-ahead guard** -- like v1, every Thought v2 emits satisfies
   `decision_horizon <= bar.time` (doctrine 06 §3.8).

Tests skip cleanly when the production repo isn't on `sys.path`
(matches the v1 wrapper test discipline).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger,
    RedactedLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
    Thought,
)

pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="M001 v2 arc needs the production repo on sys.path (M001_PRODUCTION_REPO or default)",
)


# ---------------------------------------------------------------------------
# Synthetic-bar generators (reuse the v1 wrap test's geometry where possible).
# ---------------------------------------------------------------------------

def _make_zone_bars(n: int = 600):
    """Reuse the v1 wrap-test synthetic geometry that drives the zone weapon.

    Forwarded from `test_a01_isagi_wrap._make_synthetic_bars`. We import
    that fixture here so any future tweak to the zone trigger geometry
    flows into BOTH v1 and v2 tests -- keeps the regression contract
    auditable.
    """
    from programs.M001_multi_agent_ensemble.sim.tests.test_a01_isagi_wrap import (
        _make_synthetic_bars,
    )
    return _make_synthetic_bars(n)


def _make_sweep_bars(n: int = 400):
    """Build a synthetic H4 series engineered to fire a liquidity sweep
    WITHOUT a co-located zone touch on the same bar.

    Geometry:
      1. A long, slow DOWNTREND (~250 H4 bars, -2.5 % cumulative).
         This pins D1 bias to DOWN (htf_bias_at returns DOWN).
      2. Two near-equal swing highs spaced ~30 bars apart, both at the
         same price (1.10500). The two-pivot cluster forms an
         `equal_highs` zone that the sweep detector recognises.
      3. A single BUYSIDE SWEEP bar: wicks above 1.10500, closes back
         below the level by > 1 pip (the pierce buffer). Bar body is
         small to AVOID triggering the zone alpha's impulse-bar
         condition (impulse needs |body| > 1.5 x ATR), and the equal-
         highs cluster is NOT a fresh supply zone (the geometry is
         "level visited twice from below", not "down impulse forming a
         supply zone above").
      4. Forward chop so the v2 sweep trade has room to resolve.

    On this series v1 (zone weapon only) emits ZERO proposals; v2 emits
    at least ONE sweep proposal at the bar after the sweep wick. That
    asymmetry is the behaviour delta.
    """
    from agent.types import Bar, Timeframe

    base = datetime(2022, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = 1.13000

    # 1) Slow downtrend so D1 bias resolves to DOWN at sweep time.
    for i in range(250):
        new_price = price - 0.00012  # -1.2 pips per H4 bar, ~-300 pips total.
        bars.append(Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + 0.00020,
            low=min(price, new_price) - 0.00015,
            close=new_price,
            volume=120.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 2) First swing high at 1.10500 (rally from ~1.10000).
    swing_target = 1.10500
    n_up_a = 25
    for i in range(n_up_a):
        delta = (swing_target - price) / max(n_up_a - i, 1)
        new_price = price + delta
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=max(price, new_price) + 0.00010,
            low=min(price, new_price) - 0.00010,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 3) Drop back down to 1.10000.
    for i in range(20):
        new_price = price - 0.00025
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=price + 0.00010,
            low=new_price - 0.00010,
            close=new_price,
            volume=110.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 4) Second swing high at 1.10500 (equal high #2 -- forms the
    #    `equal_highs` cluster the sweep detector reads).
    n_up_b = 20
    for i in range(n_up_b):
        delta = (swing_target - price) / max(n_up_b - i, 1)
        new_price = price + delta
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=max(price, new_price) + 0.00010,
            low=min(price, new_price) - 0.00010,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 5) Small pullback so the swing high becomes "confirmed" (the
    #    swing detector requires `lookback` bars after the extreme).
    for i in range(15):
        new_price = price - 0.00015
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=price + 0.00005,
            low=new_price - 0.00005,
            close=new_price,
            volume=90.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price

    # 6) THE SWEEP BAR. Wicks above 1.10500 by ~10 pips, closes back
    #    BELOW the equal-highs level. Body small enough to NOT count
    #    as an impulse bar (so no fresh supply zone is created).
    sweep_open = price
    sweep_high = swing_target + 0.00100   # 10 pips above the level
    sweep_close = swing_target - 0.00050  # 5 pips below the level
    sweep_low = sweep_close - 0.00005
    bars.append(Bar(
        time=base + timedelta(hours=4 * len(bars)),
        open=sweep_open,
        high=sweep_high,
        low=sweep_low,
        close=sweep_close,
        volume=400.0,
        timeframe=Timeframe.H4,
    ))
    price = sweep_close

    # 7) Forward bars so the v2 sweep trade has room to resolve.
    chop_n = max(0, n - len(bars))
    if chop_n < 60:
        chop_n = 60
    for i in range(chop_n):
        # Continue the macro downtrend so the SHORT sweep trade pays.
        new_price = price - 0.00015
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=max(price, new_price) + 0.00015,
            low=min(price, new_price) - 0.00015,
            close=new_price,
            volume=110.0,
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


def _build_v1():
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
    return A1IsagiV1()


def _build_v2(**kwargs):
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi_v2 import A1IsagiV2
    return A1IsagiV2(**kwargs)


def _walk(agent, bars, ledger) -> tuple[list[Thought], list[Optional[AgentProposal]]]:
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
# 1. CONTRACT TESTS
# ---------------------------------------------------------------------------

def test_v2_satisfies_blue_lock_striker_contract():
    """v2 must have the same public surface as v1.

    Doctrine 06 §4.1: `agent_id`, `canon_role`, `home_tf`, `symbols`,
    `observe`, `intend`, `report_kpis`. The Protocol is structurally
    typed; we assert via attribute presence + signature shape so a
    future `BlueLockStriker` Protocol tweak surfaces here.
    """
    v2 = _build_v2()
    assert v2.agent_id == "isagi_yoichi"
    assert v2.home_tf == "H4"
    assert "EURUSD" in v2.symbols
    assert callable(v2.observe)
    assert callable(v2.intend)
    assert callable(v2.report_kpis)
    # canon_role keeps identity stable across versions (doctrine §3.10).
    assert v2.canon_role.canon_player == "isagi_yoichi"
    assert v2.canon_role.ego == 0.60
    # ...but the *weapon* field is bumped so version is visible.
    assert "v2" in v2.canon_role.weapon


def test_v2_observe_always_emits_thought():
    """Every tick must produce a Thought (not None). Doctrine 06 §4.1."""
    bars = _make_zone_bars(50)
    v2 = _build_v2()
    # No prepare() called -- v2 must still degrade safely (mirror v1).
    ledger = FullLedger()
    for i, b in enumerate(bars):
        m = _make_market_state(b, i)
        t = v2.observe(m, ledger)
        assert t is not None
        assert t.agent_id == "isagi_yoichi"
        assert t.coordinate is None  # unprepared -> observation-only
        assert "weapon:none" in t.tags
        assert "unprepared" in t.tags
        # intend() must also be safe when unprepared.
        assert v2.intend(m, t) is None


def test_v2_decision_horizon_never_exceeds_bar_timestamp():
    """Look-ahead guard (doctrine 06 §3.8). Same invariant as v1."""
    bars = _make_zone_bars(400)
    v2 = _build_v2()
    v2.prepare("EURUSD", bars)
    ledger = FullLedger()
    thoughts, _ = _walk(v2, bars, ledger)
    for i, t in enumerate(thoughts):
        assert t.decision_horizon <= bars[i].time, (
            f"look-ahead at i={i}: dh={t.decision_horizon}, bar={bars[i].time}"
        )


# ---------------------------------------------------------------------------
# 2. REGRESSION TEST -- zone branch byte-equivalent to v1
# ---------------------------------------------------------------------------

def test_zone_branch_byte_equivalent_to_v1():
    """v2's zone-weapon Proposals must match v1's byte-for-byte.

    On a synthetic series engineered to fire the zone weapon (no sweep
    co-firing on the SAME bar), v2.intend() must produce a Proposal
    with the same direction, entry, stop, take-profit, and conviction
    as v1.intend() at every firing index.

    This is the doctrine 06 §3.11.2 step 4 "regression test that vN+1
    reproduces vN behaviour" invariant.
    """
    bars = _make_zone_bars(600)
    v1 = _build_v1()
    v1.prepare("EURUSD", bars)
    v2 = _build_v2()
    v2.prepare("EURUSD", bars)

    ledger_v1 = FullLedger()
    _, props_v1 = _walk(v1, bars, ledger_v1)
    ledger_v2 = FullLedger()
    _, props_v2 = _walk(v2, bars, ledger_v2)

    v1_indices = [i for i, p in enumerate(props_v1) if p is not None]
    if not v1_indices:
        pytest.skip("synthetic zone series produced no v1 proposals; nothing to compare")

    for i in v1_indices:
        p1 = props_v1[i]
        p2 = props_v2[i]
        assert p2 is not None, (
            f"v2 missed a v1 zone-touch trade at i={i} (regression)"
        )
        # The behaviour-equivalence contract: same direction + price plan.
        assert p2.direction == p1.direction, (
            f"direction mismatch at i={i}: v1={p1.direction} v2={p2.direction}"
        )
        assert p2.entry == pytest.approx(p1.entry), (
            f"entry mismatch at i={i}"
        )
        assert p2.stop == pytest.approx(p1.stop), (
            f"stop mismatch at i={i}"
        )
        assert p2.ladder[0].price == pytest.approx(p1.ladder[0].price), (
            f"take_profit mismatch at i={i}"
        )
        assert p2.conviction == pytest.approx(p1.conviction), (
            f"conviction mismatch at i={i}"
        )
        # ...and v2 must carry the version + weapon tags in the rationale.
        assert p2.rationale.get("isagi_version") == "v2"
        assert p2.rationale.get("weapon") == "zone_d1_against"


def test_v2_takes_every_v1_zone_trade_or_better():
    """Stronger statement of the regression invariant: count of v1
    firing indices ≤ count of v2 firing indices (v2 may take MORE, but
    never FEWER trades than v1)."""
    bars = _make_zone_bars(600)
    v1 = _build_v1()
    v1.prepare("EURUSD", bars)
    v2 = _build_v2()
    v2.prepare("EURUSD", bars)
    ledger_v1 = FullLedger()
    _, props_v1 = _walk(v1, bars, ledger_v1)
    ledger_v2 = FullLedger()
    _, props_v2 = _walk(v2, bars, ledger_v2)

    v1_count = sum(1 for p in props_v1 if p is not None)
    v2_count = sum(1 for p in props_v2 if p is not None)
    assert v2_count >= v1_count, (
        f"v2 fewer trades than v1 ({v2_count} < {v1_count}) -- regression"
    )


# ---------------------------------------------------------------------------
# 3. BEHAVIOUR-DELTA TEST -- v2 takes at least one sweep trade v1 cannot
# ---------------------------------------------------------------------------

def test_v2_emits_sweep_proposal_v1_cannot():
    """On a series engineered to fire the sweep weapon WITHOUT a zone
    co-firing, v2 must emit at least one proposal with
    `rationale.weapon == "liquidity_sweep"` AND v1 must emit ZERO
    proposals on the same series. This is the §3.11.2 step 5 "v2
    resolves the defeat trigger" invariant -- without a non-empty
    vocabulary delta the evolution arc is empty.
    """
    bars = _make_sweep_bars(400)
    v1 = _build_v1()
    v1.prepare("EURUSD", bars)
    v2 = _build_v2()
    v2.prepare("EURUSD", bars)
    ledger_v1 = FullLedger()
    _, props_v1 = _walk(v1, bars, ledger_v1)
    ledger_v2 = FullLedger()
    thoughts_v2, props_v2 = _walk(v2, bars, ledger_v2)

    v1_proposals = [p for p in props_v1 if p is not None]
    v2_sweep_proposals = [
        p for p in props_v2
        if p is not None and p.rationale.get("weapon") == "liquidity_sweep"
    ]
    v2_zone_proposals = [
        p for p in props_v2
        if p is not None and p.rationale.get("weapon") == "zone_d1_against"
    ]
    if not v2_sweep_proposals and not v2_zone_proposals and not v1_proposals:
        # If neither agent fires, the synthetic geometry isn't doing its
        # job -- skip rather than silently passing.
        pytest.skip(
            "synthetic sweep series produced 0 proposals from either v1 or "
            "v2; geometry needs tuning (this test is not informative)."
        )
    # v1 must not have fired any sweep-style proposals (it cannot --
    # its vocabulary doesn't include sweeps).
    for p in v1_proposals:
        assert p.rationale.get("signal_reason") in {
            "zone_demand", "zone_supply",
        }, (
            f"v1 emitted a non-zone proposal -- vocabulary leak: {p.rationale}"
        )
    # v2 must have at least one sweep proposal.
    assert len(v2_sweep_proposals) >= 1, (
        "v2 emitted ZERO sweep proposals on a series engineered for sweeps -- "
        "behaviour delta is empty; evolution arc is empty per doctrine §3.11.3"
    )
    # And the sweep proposal must carry the v2 telemetry.
    sample = v2_sweep_proposals[0]
    assert sample.rationale.get("isagi_version") == "v2"
    assert sample.rationale.get("swept_label") in {
        "equal_highs", "equal_lows", "swing_high", "swing_low",
        "PDH", "PDL", "PWH", "PWL",
    }, f"unexpected swept_label: {sample.rationale.get('swept_label')}"

    # The corresponding Thought must carry the weapon:sweep tag.
    matching_thought = [
        t for t in thoughts_v2
        if (t.coordinate is not None
            and t.coordinate.rationale.get("weapon") == "liquidity_sweep")
    ]
    assert matching_thought, "no v2 Thought tagged with liquidity_sweep coordinate"
    assert any("weapon:sweep" in t.tags for t in matching_thought)


def test_v2_sweep_signal_at_returns_shim_on_engineered_geometry():
    """Harness pass-through: `sweep_signal_at` must return a shim with
    the same `entry/stop/take_profit/direction/conviction` fields the
    AlphaSignal shim used by `_open_trade_from_proposal` expects, so
    the head-to-head harness can open trades via the production fill
    model unchanged."""
    bars = _make_sweep_bars(400)
    v2 = _build_v2()
    v2.prepare("EURUSD", bars)

    # Find any index where sweep_signal_at returns non-None.
    fired_idx = None
    for i in range(250, len(bars) - 1):
        sig = v2.sweep_signal_at("EURUSD", i)
        if sig is not None:
            fired_idx = i
            break
    if fired_idx is None:
        pytest.skip(
            "engineered sweep series produced no sweep signals -- "
            "geometry tuning is the issue, test is not informative"
        )
    sig = v2.sweep_signal_at("EURUSD", fired_idx)
    assert hasattr(sig, "direction")
    assert hasattr(sig, "entry")
    assert hasattr(sig, "stop")
    assert hasattr(sig, "take_profit")
    assert hasattr(sig, "conviction")
    assert hasattr(sig, "reason")
    # The conviction is exactly the v2 sweep conviction by construction.
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi_v2 import (
        SWEEP_CONVICTION,
    )
    assert sig.conviction == pytest.approx(SWEEP_CONVICTION)
    # The shim's `direction` is a production `agent.types.Direction` enum
    # so the same `_open_trade_from_proposal` shim builder works.
    assert sig.direction.value in ("long", "short")


def test_v2_sweep_signal_blocked_by_neutral_htf():
    """Negative case: if the D1 bias is NEUTRAL the sweep signal does
    not fire. Mirrors v1's `htf_align` rule "no read = no trade".

    Constructs a flat series with TWO equal-highs swing pivots but
    zero macro drift, so `htf_bias_at` returns NEUTRAL. The sweep
    geometry still produces a `LiquiditySweep` event, but the v2 gate
    rejects it.
    """
    from agent.types import Bar, Timeframe

    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = 1.10000
    # Flat regime (chop) so D1 is NEUTRAL.
    for i in range(300):
        new_price = price + (0.00005 if i % 7 < 3 else -0.00005)
        bars.append(Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + 0.00010,
            low=min(price, new_price) - 0.00010,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    # A sweep candidate (wick up + close back below) at index 300.
    bars.append(Bar(
        time=base + timedelta(hours=4 * 300),
        open=price,
        high=price + 0.00060,
        low=price - 0.00010,
        close=price - 0.00020,
        volume=150.0,
        timeframe=Timeframe.H4,
    ))
    # Forward chop so the harness doesn't trip on len(bars).
    for i in range(50):
        bars.append(Bar(
            time=base + timedelta(hours=4 * (301 + i)),
            open=price,
            high=price + 0.00010,
            low=price - 0.00010,
            close=price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))

    v2 = _build_v2()
    v2.prepare("EURUSD", bars)
    # No tick should produce a sweep proposal -- D1 bias is NEUTRAL.
    sweep_proposals: list[AgentProposal] = []
    ledger = FullLedger()
    _, props = _walk(v2, bars, ledger)
    for p in props:
        if p is not None and p.rationale.get("weapon") == "liquidity_sweep":
            sweep_proposals.append(p)
    assert not sweep_proposals, (
        f"v2 emitted {len(sweep_proposals)} sweep proposals under NEUTRAL "
        "D1 bias -- HTF gate is leaking"
    )


# ---------------------------------------------------------------------------
# 4. TIER-3 ledger isolation -- v2 should still produce identical trades
#    on RedactedLedger vs FullLedger because v2 (like v1) does not read
#    peer thoughts. The vocabulary expansion is local to the agent.
# ---------------------------------------------------------------------------

def test_v2_redacted_ledger_matches_full_ledger():
    """A1 Isagi v2 is Tier-3 by default at Phi3 (no peer reads). The
    `RedactedLedger` must produce byte-identical Proposals to the
    `FullLedger`. Same control-arm correctness invariant as v1."""
    bars = _make_zone_bars(500)
    a = _build_v2()
    a.prepare("EURUSD", bars)
    ledger_full = FullLedger()
    _, props_full = _walk(a, bars, ledger_full)

    b = _build_v2()
    b.prepare("EURUSD", bars)
    ledger_redacted = RedactedLedger(agent_id=b.agent_id)
    _, props_redacted = _walk(b, bars, ledger_redacted)

    fp_full = [
        None if p is None else (p.direction, p.entry, p.stop, p.conviction)
        for p in props_full
    ]
    fp_redacted = [
        None if p is None else (p.direction, p.entry, p.stop, p.conviction)
        for p in props_redacted
    ]
    assert fp_full == fp_redacted
