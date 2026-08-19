"""A9 Aoshi v2 -- Tier-0 forward test: the missing time stop.

The §10.6 forward half of the evolution-arc contract for the arc
registered in ``reviews/sae_itoshi_v1_defeat.md`` (regression half lives
in ``test_a09_aoshi_v2_regression.py``).

**Which named defeat this file resolves.** Defeat note §1.5, third gap:

    "A third gap, cheap and unambiguous: **there is no time stop.**
    ``valid_until`` is ``timestamp + 6 h`` per the canon
    ``target_hold_hours=6.0``, but exits are SL/TP only, and observed
    holds run to **6,675 minutes ≈ 111 hours** (median 15 min)."

The 6,675-minute hold is the explicit fixture below: a bracket that
neither leg touches for 111 hours. Under v1's SL/TP-only exit model the
position simply stays open; v2 closes it at the first M15 bar that
closes on or after ``target_hold_hours``.

**Which defeat this file does NOT resolve.** Not AE2, and not the §1.1
ride asymmetry. Those are the *alpha* defeat and belong to Tier 1 (the
volatility-normalised, fade-only trigger), which is pre-registered
separately and is not implemented in this module. Nothing here is
evidence of improved performance, and Phase AE's `FAIL` verdict stands
unrevised. The filename follows the §4 naming convention the defeat
note fixed; the scope is the Tier-0 subset stated above.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a09_aoshi_v2 import (
    A9AoshiV2,
    EventExit,
)
from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
    A9SaeV1,
    SaeConfig,
    SimNewsEvent,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
)

UTC = timezone.utc
EVENT_T = datetime(2024, 3, 8, 13, 30, tzinfo=UTC)
PIP = 0.0001

# The observed v1 tail, verbatim from defeat note §1.5.
V1_OBSERVED_MAX_HOLD_MINUTES = 6675.0
TARGET_HOLD_MINUTES = 6.0 * 60.0
M15_MINUTES = 15.0


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


def _fade_bars() -> list[FakeBar]:
    """Bullish 50-pip event bar with a 56 % upper wick -> SHORT fade.

    entry 1.1050, stop 1.1125 (high + 5 pip pad), 1.5R target 1.09375.
    """
    o = 1.1000
    c = o + 50 * PIP
    return [
        FakeBar(time=EVENT_T, open=o, high=o + 120 * PIP,
                low=o - 5 * PIP, close=c),
        FakeBar(time=EVENT_T + timedelta(minutes=15),
                open=c, high=c + 10 * PIP, low=c - 10 * PIP, close=c),
    ]


def _stalled_bars(n_bars: int) -> list[FakeBar]:
    """``n_bars`` M15 bars that touch NEITHER bracket leg.

    Oscillate between 1.1000 and 1.1100 -- comfortably inside the stop
    at 1.1125 and the 1.5R target at 1.09375. This is the shape of the
    v1 hold tail: a trade the SL/TP-only exit model can never close.
    """
    bars: list[FakeBar] = []
    start = EVENT_T + timedelta(minutes=30)
    for i in range(n_bars):
        mid = 1.1050 + (10 * PIP if i % 2 else -10 * PIP)
        bars.append(FakeBar(
            time=start + timedelta(minutes=15 * i),
            open=mid, high=1.1100, low=1.1000, close=mid,
        ))
    return bars


def _bars_for_111_hours() -> list[FakeBar]:
    n = int(V1_OBSERVED_MAX_HOLD_MINUTES // 15) + 1     # 446 bars > 111 h
    return _fade_bars() + _stalled_bars(n)


def _agent(cls, bars: list[FakeBar]):
    agent = cls(config=SaeConfig(sae_enabled=True))
    agent.load_calendar(events=[SimNewsEvent(
        time_utc=EVENT_T, currency="USD", impact="High",
        title="Employment Situation (NFP)",
    )])
    agent.set_bars_provider(_provider(bars))
    return agent


def _fire(agent, as_of: datetime):
    market = _market(as_of)
    return agent.intend(market, agent.observe(market, FullLedger()))


def _v1_style_exit(proposal: AgentProposal, bars: list[FakeBar]):
    """v1's exit model: stop-loss or take-profit, and nothing else.

    Deliberately has no time leg -- that absence IS the defeat under
    test. Returns the exit bar or ``None`` if the bracket never
    resolves.
    """
    entry_t = proposal.timestamp
    stop = float(proposal.stop)
    tp = float(proposal.ladder[0].price)
    is_long = proposal.direction == "long"
    for bar in bars:
        if bar.time < entry_t:
            continue
        if is_long and (bar.low <= stop or bar.high >= tp):
            return bar
        if not is_long and (bar.high >= stop or bar.low <= tp):
            return bar
    return None


# ---------------------------------------------------------------------------
# The named defeat: the 111-hour hold
# ---------------------------------------------------------------------------

class TestTimeStopResolvesThe111HourHold:
    AT = EVENT_T + timedelta(minutes=15)

    def test_fixture_reproduces_the_v1_hold_tail(self):
        """Sanity-check the fixture before asserting anything about v2:
        over 111 hours the bracket is never touched, so v1's SL/TP-only
        model holds the position the whole way."""
        bars = _bars_for_111_hours()
        p1 = _fire(_agent(A9SaeV1, bars), self.AT)
        assert isinstance(p1, AgentProposal)
        assert _v1_style_exit(p1, bars) is None
        span = (bars[-1].time - p1.timestamp).total_seconds() / 60.0
        assert span >= V1_OBSERVED_MAX_HOLD_MINUTES

    def test_v1_exposes_no_time_stop_surface_at_all(self):
        v1 = _agent(A9SaeV1, _fade_bars())
        assert not hasattr(v1, "resolve_exit")
        assert not hasattr(v1, "time_stop_at")

    def test_v2_closes_the_same_trade_at_the_time_stop(self):
        bars = _bars_for_111_hours()
        v2 = _agent(A9AoshiV2, bars)
        p2 = _fire(v2, self.AT)
        assert isinstance(p2, AgentProposal)

        exit_ = v2.resolve_exit(p2, bars)
        assert isinstance(exit_, EventExit)
        assert exit_.reason == "time_stop"
        assert exit_.hold_minutes == pytest.approx(TARGET_HOLD_MINUTES)
        assert exit_.hold_minutes < V1_OBSERVED_MAX_HOLD_MINUTES

    def test_hold_cannot_exceed_target_by_more_than_one_bar(self):
        """Bar-granular by construction: the resolver acts at bar close,
        so the overshoot bound is exactly one M15 bar."""
        bars = _bars_for_111_hours()
        v2 = _agent(A9AoshiV2, bars)
        p2 = _fire(v2, self.AT)
        exit_ = v2.resolve_exit(p2, bars)
        assert exit_.hold_minutes <= TARGET_HOLD_MINUTES + M15_MINUTES

    def test_time_stop_instant_is_stamped_on_the_proposal(self):
        v2 = _agent(A9AoshiV2, _bars_for_111_hours())
        p2 = _fire(v2, self.AT)
        assert p2.rationale["target_hold_hours"] == pytest.approx(6.0)
        assert (
            datetime.fromisoformat(p2.rationale["time_stop_utc"])
            == v2.time_stop_at(p2)
        )
        # v1 already carried an advisory `valid_until`; v2's time stop
        # is the enforcement the note says was missing, at the same
        # instant -- not a new horizon.
        assert v2.time_stop_at(p2) == p2.valid_until


# ---------------------------------------------------------------------------
# The time stop is a LAST resort, not a replacement for the bracket
# ---------------------------------------------------------------------------

class TestBracketStillWins:
    AT = EVENT_T + timedelta(minutes=15)

    def _resolve(self, extra: list[FakeBar]):
        bars = _fade_bars() + extra
        v2 = _agent(A9AoshiV2, bars)
        p2 = _fire(v2, self.AT)
        return v2.resolve_exit(p2, bars)

    def test_stop_loss_still_resolves_first(self):
        hit = FakeBar(time=EVENT_T + timedelta(minutes=30),
                      open=1.1050, high=1.1130, low=1.1040, close=1.1120)
        exit_ = self._resolve([hit])
        assert exit_.reason == "stop"
        assert exit_.price == pytest.approx(1.1125)
        assert exit_.hold_minutes == pytest.approx(30.0)

    def test_target_still_resolves_first(self):
        hit = FakeBar(time=EVENT_T + timedelta(minutes=30),
                      open=1.1050, high=1.1055, low=1.0930, close=1.0940)
        exit_ = self._resolve([hit])
        assert exit_.reason == "target"
        assert exit_.price == pytest.approx(1.09375)

    def test_stop_beats_target_within_the_same_bar(self):
        """Pessimistic intra-bar ordering, stated in the resolver."""
        both = FakeBar(time=EVENT_T + timedelta(minutes=30),
                       open=1.1050, high=1.1130, low=1.0930, close=1.1000)
        assert self._resolve([both]).reason == "stop"

    def test_returns_none_when_the_bars_run_out_early(self):
        exit_ = self._resolve(_stalled_bars(4))     # only ~1 h of tape
        assert exit_ is None
