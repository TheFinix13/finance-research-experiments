"""A4 -- Hyoma Chigiri v1 (`chigiri_hyoma`) -- ATR breakout speedster.

Chigiri is the speedster (roster `05-agent-roster-v0.md` section 3.4,
doctrine `06-blue-lock-doctrine.md` section 3.1 -- "speed once
committed"). His canonical weapon is range-break + ATR vol-expansion
momentum. The empirical prior (audit `2026-06-24_E001-E007_audit.md`
section 2.7) is a **negative prior at the retest layer** -- E007 found
0/12 cells alive on impulse-origin retest at Stage 1. The roster
explicitly warns:

> Chigiri's edge must therefore live in the *continuation* of the
> impulse, not in the retest of the origin zone. Up-impulse cells were
> +4 to +14 pips on EURUSD 2015-2021 vs negative H4 down-impulse cells
> -- a symmetric-long-short warning Chigiri must respect at the spec
> level.

Chigiri v1 takes the **continuation** read: M-bar range break on H4
with ATR confirmation. New primitive -- NOT a wrap of the production
zone cell. The agent has no production-repo dependency for its inner
calculation (uses pure-Python OHLC history from `prepare()`).

Signal predicate (locked Φ4.1 v1)
---------------------------------

For bar `i` on a prepared symbol, Chigiri fires iff:

1. `close[i] > max(high[i-N..i-1])` (LONG breakout)   OR
   `close[i] < min(low[i-N..i-1])`  (SHORT breakout)
   with `N = CHIGIRI_V1_BREAKOUT_LOOKBACK = 20` bars.
2. Breakout magnitude (`|close[i] - broken_level|`) ≥
   `CHIGIRI_V1_BREAKOUT_ATR_MULT × ATR_14`.
3. ATR_14[i] > median(ATR_14[i-80..i-1]) -- vol expansion regime.

Conviction (final = base + boost, cap 1.0):

* `base = CHIGIRI_V1_BASE_CONVICTION = 0.70`
* `boost = min(0.25, 0.10 × (magnitude / ATR))` -- magnitude z-score
  proxy, bounded so a single huge bar can't reach 1.0 deterministically.

The base of 0.70 sits exactly at Nagi's `NAGI_V1_CONFIDENCE_FLOOR` so a
clean breakout qualifies as a Nagi peer. The vol-expansion regime
predicate keeps Chigiri honest -- E007's negative prior was on retest,
not on continuation, but we still gate the firing on a positive vol
state to avoid whipsawing in chop.

Trade plan (intend):

* entry = close[i] (the breakout bar's close; the harness opens at the
  next bar's open per its fill model).
* stop = broken_level ∓ 0.25 × ATR  (LONG: broken_level − 0.25 ATR;
  SHORT: broken_level + 0.25 ATR).
* tp   = entry ± 1.5R (matches the squad's standard target_rr=1.5).

Symbols
-------

EURUSD + GBPUSD H4 -- per roster section 3.4 the canonical home is M15
but Φ4 v1 ran everything on H4. v1 ships H4 to align with the squad
home-TF schedule; M15 deployment is a v2 cadence change.

Symbols are intentionally EURUSD + GBPUSD (not USDCAD): Barou owns
USDCAD end-to-end and Chigiri must not contest it.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

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
# Locked Φ4.1 v1 parameters.
# ---------------------------------------------------------------------------
CHIGIRI_V1_BREAKOUT_LOOKBACK: int = 20    # N-bar range
CHIGIRI_V1_ATR_PERIOD: int = 14
CHIGIRI_V1_ATR_VOL_LOOKBACK: int = 80     # median ATR window for vol regime
CHIGIRI_V1_BREAKOUT_ATR_MULT: float = 0.50
CHIGIRI_V1_STOP_ATR_MULT: float = 0.25
CHIGIRI_V1_TARGET_RR: float = 1.5
CHIGIRI_V1_BASE_CONVICTION: float = 0.70
CHIGIRI_V1_MAX_MAGNITUDE_BOOST: float = 0.25
CHIGIRI_V1_MAGNITUDE_BOOST_PER_ATR: float = 0.10
CHIGIRI_V1_CONV_CAP: float = 1.0
CHIGIRI_V1_WARMUP_BARS: int = (
    CHIGIRI_V1_BREAKOUT_LOOKBACK + CHIGIRI_V1_ATR_VOL_LOOKBACK + 5
)

CHIGIRI_V1_SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD")

CHIGIRI_V1_CANON_ROLE = CanonRole(
    canon_player="chigiri_hyoma",
    weapon="speed_atr_breakout_continuation",
    ego=0.80,
    target_hold_hours=24.0,
    narrative_voice="speed_committed_breakaway",
)


@dataclass
class _PreparedSeries:
    """Per-symbol cache of OHLC + precomputed ATR series."""

    bars: list                 # list of objects with .time, .open, .high, .low, .close
    index_by_ts: dict[datetime, int]
    atr: list[float]           # ATR_14 series (same length as bars; NaN where < period)


def _wilder_atr(bars: list, period: int) -> list[float]:
    """Wilder's ATR via EWM-equivalent recurrence.

    Mirrors `conflab/indicators.py:atr` semantics (alpha=1/period). Pure
    Python -- no pandas/numpy dependency -- to keep this agent free of
    production-repo coupling.
    """
    n = len(bars)
    out = [float("nan")] * n
    if n == 0:
        return out
    # True range series.
    tr: list[float] = [0.0] * n
    for i in range(n):
        h = float(bars[i].high)
        l = float(bars[i].low)
        if i == 0:
            tr[i] = h - l
            continue
        pc = float(bars[i - 1].close)
        tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    # Wilder's smoothing (alpha = 1/period, no adjust). First "settled"
    # value at index period-1.
    if n < period:
        return out
    alpha = 1.0 / float(period)
    seed = sum(tr[:period]) / float(period)
    out[period - 1] = seed
    prev = seed
    for i in range(period, n):
        cur = alpha * tr[i] + (1.0 - alpha) * prev
        out[i] = cur
        prev = cur
    return out


class A4ChigiriV1(BaseStriker):
    """A4 Chigiri v1 -- ATR breakout continuation striker.

    Public surface (engine):
      * `observe(market, ledger)` -- always emits a Thought; when the
        breakout predicate fires AND vol-expansion regime is on,
        emits a Coordinate at base + magnitude_boost conviction.
      * `intend(market, my_recent_thought)` -- H4 close only on EURUSD
        / GBPUSD; emits a Proposal whose entry=close, stop = broken
        level +/- 0.25 ATR, tp at 1.5R.

    Harness API:
      * `prepare(symbol, bars)` -- pre-load OHLC bars + compute ATR.
    """

    def __init__(
        self,
        agent_id: str = "chigiri_hyoma",
        canon_role: Optional[CanonRole] = None,
        home_tf: str = "H4",
        symbols: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            canon_role=canon_role or CHIGIRI_V1_CANON_ROLE,
            home_tf=home_tf,
            symbols=list(symbols) if symbols is not None else list(CHIGIRI_V1_SYMBOLS),
            playstyle="speed_momentum",
            tier=2,
        )
        self._prepared: dict[str, _PreparedSeries] = {}

    # ------------------------------------------------------------------
    # Harness API
    # ------------------------------------------------------------------

    def prepare(self, symbol: str, bars: list) -> None:
        if symbol not in self.symbols:
            log.info(
                "A4ChigiriV1.prepare(%s) ignored -- not in symbol whitelist %s",
                symbol, self.symbols,
            )
            return
        atr = _wilder_atr(bars, CHIGIRI_V1_ATR_PERIOD)
        index_by_ts = {b.time: i for i, b in enumerate(bars)}
        self._prepared[symbol] = _PreparedSeries(
            bars=list(bars), index_by_ts=index_by_ts, atr=atr,
        )
        log.info(
            "A4ChigiriV1 prepared %s: %d bars, ATR ready", symbol, len(bars),
        )

    @property
    def prepared_symbols(self) -> tuple[str, ...]:
        return tuple(self._prepared.keys())

    # ------------------------------------------------------------------
    # BlueLockStriker contract
    # ------------------------------------------------------------------

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        if market.symbol not in self.symbols:
            return self._abstain_thought(market, reason="off_symbol")

        prep = self._prepared.get(market.symbol)
        if prep is None:
            return self._abstain_thought(market, reason="unprepared")

        i = prep.index_by_ts.get(market.as_of)
        if i is None:
            return self._abstain_thought(market, reason="timestamp_miss")

        sig = self._detect_breakout(prep, i)
        if sig is None:
            return self._observation_only(market=market, reason="no_breakout")

        direction = sig["direction"]
        magnitude = float(sig["magnitude"])
        atr_at = float(sig["atr"])
        boost = min(
            CHIGIRI_V1_MAX_MAGNITUDE_BOOST,
            CHIGIRI_V1_MAGNITUDE_BOOST_PER_ATR * (magnitude / max(atr_at, 1e-9)),
        )
        final_conv = min(
            CHIGIRI_V1_CONV_CAP, CHIGIRI_V1_BASE_CONVICTION + boost,
        )
        coord = _coordinate_from_breakout(
            sig=sig, agent_id=self.agent_id, symbol=market.symbol,
            as_of=market.as_of, home_tf=self.home_tf,
            target_hold_hours=self.canon_role.target_hold_hours,
            conviction=final_conv,
        )
        tags = [
            "canon:chigiri",
            "weapon:speed",
            "chigiri_speed_breakout",
            "breakout_continuation",
            "momentum",
            f"direction:{direction}",
            f"breakout_level:{sig['broken_level']:.5f}",
            "regime:vol_expansion",
        ]
        narrative = (
            f"[chigiri v1] {market.symbol} H4 close {market.as_of}: "
            f"{direction} breakout of "
            f"{CHIGIRI_V1_BREAKOUT_LOOKBACK}-bar range; "
            f"magnitude={magnitude:.5f} ({magnitude / atr_at:.2f} ATR); "
            f"ATR={atr_at:.5f}; conv "
            f"{CHIGIRI_V1_BASE_CONVICTION:.2f}+{boost:.2f}={final_conv:.2f}."
        )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=narrative,
            tags=tags,
            confidence_in_thought=float(final_conv),
            expected_action=f"{direction}_on_H4_close_breakout",
            coordinate=coord,
            decision_horizon=market.as_of,
            ttl_ticks=6,
            references=[],
        )

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
        **_kwargs: object,
    ) -> AgentProposal | None:
        # ``_kwargs`` absorbs the F21 ``workspace`` kwarg. Chigiri v1
        # focuses on ATR-driven momentum breakouts local to its own
        # observation; peer thoughts do not enter v1 decisioning.
        if market.timeframe != self.home_tf:
            return None
        if market.symbol not in self.symbols:
            return None
        if my_recent_thought.coordinate is None:
            return None
        if "chigiri_speed_breakout" not in my_recent_thought.tags:
            return None
        prep = self._prepared.get(market.symbol)
        if prep is None:
            return None
        i = prep.index_by_ts.get(market.as_of)
        if i is None:
            return None

        rationale = my_recent_thought.coordinate.rationale
        direction = my_recent_thought.coordinate.direction_bias
        if direction not in ("long", "short"):
            return None
        try:
            entry = float(rationale["entry"])
            stop = float(rationale["stop"])
            tp = float(rationale["take_profit"])
        except (KeyError, TypeError, ValueError):
            return None

        ladder = [LadderRung(price=float(tp), fraction=1.0)]
        horizon = market.as_of + timedelta(
            hours=float(self.canon_role.target_hold_hours),
        )
        proposal_rationale: dict[str, Any] = {
            "wrapped": "internal:atr_breakout_continuation_v1",
            "breakout_lookback": CHIGIRI_V1_BREAKOUT_LOOKBACK,
            "atr_period": CHIGIRI_V1_ATR_PERIOD,
            "breakout_atr_mult": CHIGIRI_V1_BREAKOUT_ATR_MULT,
            "stop_atr_mult": CHIGIRI_V1_STOP_ATR_MULT,
            "target_rr": CHIGIRI_V1_TARGET_RR,
            "signal_reason": "chigiri_speed_breakout_continuation",
            "bar_index": int(i),
            "base_conviction": CHIGIRI_V1_BASE_CONVICTION,
            "final_conviction": float(my_recent_thought.confidence_in_thought),
            "doctrine_ref": "06-blue-lock-doctrine.md sec 3.1 (speed)",
            "empirical_prior": (
                "E007 0/12 alive on impulse-origin RETEST; Chigiri v1 "
                "fires on CONTINUATION, not retest"
            ),
        }
        return AgentProposal(
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            source_thought_id=my_recent_thought.thought_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            direction=direction,
            entry=float(entry),
            stop=float(stop),
            ladder=ladder,
            conviction=float(my_recent_thought.confidence_in_thought),
            regime_fit=0.5,
            valid_until=horizon,
            rationale=proposal_rationale,
        )

    # ------------------------------------------------------------------
    # Breakout detector (pure)
    # ------------------------------------------------------------------

    def _detect_breakout(
        self, prep: _PreparedSeries, i: int,
    ) -> dict[str, Any] | None:
        """Return a signal dict or None.

        Predicate (all conditions must hold at bar `i`):
          1. i >= warmup
          2. ATR_14[i] finite and > 0
          3. ATR_14[i] > median of ATR_14[i-vol_lookback..i-1]
          4. close[i] > max(high[i-N..i-1])  (long)  OR
             close[i] < min(low[i-N..i-1])   (short)
          5. |close[i] - broken_level| >= breakout_atr_mult * ATR_14[i]
        """
        if i < CHIGIRI_V1_WARMUP_BARS:
            return None
        bars = prep.bars
        atr_series = prep.atr
        atr_at = atr_series[i]
        if not (atr_at == atr_at) or atr_at <= 0.0:   # NaN check + sanity
            return None
        # Vol-expansion regime: current ATR above the trailing median.
        vol_window_lo = max(0, i - CHIGIRI_V1_ATR_VOL_LOOKBACK)
        atr_history = [
            atr_series[k] for k in range(vol_window_lo, i)
            if atr_series[k] == atr_series[k]
        ]
        if len(atr_history) < CHIGIRI_V1_ATR_VOL_LOOKBACK // 2:
            return None
        atr_median = statistics.median(atr_history)
        if atr_at <= atr_median:
            return None

        lookback_lo = i - CHIGIRI_V1_BREAKOUT_LOOKBACK
        recent_high = max(float(bars[k].high) for k in range(lookback_lo, i))
        recent_low = min(float(bars[k].low) for k in range(lookback_lo, i))
        close_i = float(bars[i].close)
        threshold = CHIGIRI_V1_BREAKOUT_ATR_MULT * atr_at

        if close_i - recent_high >= threshold:
            direction = "long"
            broken_level = recent_high
            magnitude = close_i - recent_high
        elif recent_low - close_i >= threshold:
            direction = "short"
            broken_level = recent_low
            magnitude = recent_low - close_i
        else:
            return None

        if direction == "long":
            stop = broken_level - CHIGIRI_V1_STOP_ATR_MULT * atr_at
            risk = close_i - stop
            tp = close_i + CHIGIRI_V1_TARGET_RR * risk
        else:
            stop = broken_level + CHIGIRI_V1_STOP_ATR_MULT * atr_at
            risk = stop - close_i
            tp = close_i - CHIGIRI_V1_TARGET_RR * risk
        if risk <= 0:
            return None
        return {
            "direction": direction,
            "broken_level": float(broken_level),
            "magnitude": float(magnitude),
            "atr": float(atr_at),
            "atr_median_vol": float(atr_median),
            "close": float(close_i),
            "entry": float(close_i),
            "stop": float(stop),
            "take_profit": float(tp),
            "risk_price": float(risk),
            "recent_high": float(recent_high),
            "recent_low": float(recent_low),
            "bar_index": int(i),
        }

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    def _observation_only(
        self, *, market: MarketState, reason: str,
    ) -> Thought:
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[chigiri v1] {market.symbol} {market.timeframe} @ "
                f"{market.as_of} -- no breakout ({reason}); standing by."
            ),
            tags=[
                "canon:chigiri",
                "weapon:speed",
                "chigiri_observation_clean",
                f"chigiri_reason:{reason}",
            ],
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
        )

    def _abstain_thought(self, market: MarketState, *, reason: str) -> Thought:
        tags = [
            "canon:chigiri",
            "weapon:speed",
            "chigiri_abstain",
            f"abstain_reason:{reason}",
        ]
        if reason == "off_symbol":
            tags.append("chigiri_abstain_symbol")
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[chigiri v1] {market.symbol} {market.timeframe} @ "
                f"{market.as_of} -- abstain ({reason})."
            ),
            tags=tags,
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
        )


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------

def _coordinate_from_breakout(
    *,
    sig: dict[str, Any],
    agent_id: str,
    symbol: str,
    as_of: datetime,
    home_tf: str,
    target_hold_hours: float,
    conviction: float,
) -> Coordinate:
    direction = sig["direction"]
    risk = float(sig["risk_price"])
    band_half = max(risk, 0.0001)
    entry = float(sig["entry"])
    return Coordinate(
        agent_id=agent_id,
        symbol=symbol,
        price_lo=float(entry) - band_half,
        price_hi=float(entry) + band_half,
        time_start=as_of,
        time_end=as_of + timedelta(hours=float(target_hold_hours)),
        vol_band=(1.2, float("inf")),
        regime_predicate="chigiri_speed_breakout_continuation",
        expected_strength=float(conviction),
        direction_bias=direction,
        rationale={
            "entry": float(sig["entry"]),
            "stop": float(sig["stop"]),
            "take_profit": float(sig["take_profit"]),
            "broken_level": float(sig["broken_level"]),
            "magnitude": float(sig["magnitude"]),
            "atr": float(sig["atr"]),
            "atr_median_vol": float(sig["atr_median_vol"]),
            "signal_reason": "chigiri_speed_breakout_continuation",
            "home_tf": home_tf,
            "conviction_final": float(conviction),
        },
    )


# Backwards-compatible alias for roster loaders.
ChigiriHyoma = A4ChigiriV1
