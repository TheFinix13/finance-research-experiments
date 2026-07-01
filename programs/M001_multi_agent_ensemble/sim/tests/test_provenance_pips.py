"""Tests for sim/core/provenance_pips.py (Phase P, 2026-07-01).

These are pure/synthetic tests -- no production-repo dependency, no
market data. They lock the ATR + swing-pips semantics so an agent's
G7 C6 evaluator sees deterministic non-zero dispersion inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from programs.M001_multi_agent_ensemble.sim.core.provenance_pips import (
    atr_pips_at,
    isagi_metavision_lift,
    regime_fit_from_atr,
    stamp_provenance_pips,
    swing_pips_from_bars,
)


@dataclass
class _Bar:
    """Minimal bar shim for helper testing."""
    high: float
    low: float
    close: float


def _flat_bars(n: int) -> list[_Bar]:
    """Bars where every price is 1.1000 -> ATR must be 0."""
    return [_Bar(1.1000, 1.1000, 1.1000) for _ in range(n)]


def _linear_range_bars(n: int, span_pips: float = 20.0) -> list[_Bar]:
    """Bars with a fixed intra-bar span_pips high-low range each; close = mid."""
    span = span_pips * 1e-4
    out: list[_Bar] = []
    for i in range(n):
        base = 1.1000 + i * 5e-4       # 5 pip drift per bar
        out.append(_Bar(base + span, base, base + span * 0.5))
    return out


# ---------------------------------------------------------------------------
# atr_pips_at
# ---------------------------------------------------------------------------


def test_atr_returns_none_when_index_below_settled_window():
    bars = _flat_bars(20)
    assert atr_pips_at(bars, i=5, period=14) is None
    # Exactly one bar short of the settled index -> still None.
    assert atr_pips_at(bars, i=12, period=14) is None


def test_atr_returns_zero_pips_on_flat_series():
    bars = _flat_bars(30)
    v = atr_pips_at(bars, i=15, period=14)
    assert v == pytest.approx(0.0, abs=1e-9)


def test_atr_returns_positive_finite_on_ranged_series():
    bars = _linear_range_bars(30, span_pips=20.0)
    v = atr_pips_at(bars, i=20, period=14)
    assert v is not None
    # 20-pip intra-bar range + 5-pip drift -> ATR is in the 20-25 pip
    # neighbourhood after 14-period Wilder smoothing settles.
    assert 15.0 < v < 35.0


def test_atr_pip_size_scaling_matches_expected():
    bars = _linear_range_bars(30, span_pips=20.0)
    v_default = atr_pips_at(bars, i=20, period=14)
    v_yen = atr_pips_at(bars, i=20, period=14, pip_size=1e-2)
    assert v_default is not None
    assert v_yen is not None
    # Yen-style pip is 100x larger price step -> pips value is 100x smaller.
    assert v_yen == pytest.approx(v_default / 100.0, rel=1e-6)


# ---------------------------------------------------------------------------
# swing_pips_from_bars
# ---------------------------------------------------------------------------


def test_swing_pips_returns_none_when_lookback_not_available():
    bars = _linear_range_bars(10)
    assert swing_pips_from_bars(bars, i=5, lookback=20) is None


def test_swing_pips_captures_high_low_span():
    # 20 bars with 20-pip intra-bar range + 5-pip drift per bar.
    # Total range over 20 bars = 20 (bar span) + 5 * 19 (drift) = 115 pips.
    bars = _linear_range_bars(25, span_pips=20.0)
    v = swing_pips_from_bars(bars, i=20, lookback=20)
    assert v is not None
    assert 100.0 < v < 130.0


def test_swing_pips_flat_series_is_zero():
    bars = _flat_bars(25)
    v = swing_pips_from_bars(bars, i=20, lookback=20)
    assert v == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# stamp_provenance_pips (convenience wrapper)
# ---------------------------------------------------------------------------


def test_stamp_provenance_pips_populates_both_keys():
    bars = _linear_range_bars(30, span_pips=20.0)
    rationale: dict = {"existing_key": "preserved"}
    stamp_provenance_pips(rationale, bars=bars, i=25)
    assert rationale["existing_key"] == "preserved"
    assert rationale["atr_pips"] is not None
    assert rationale["h1_swing_pips"] is not None
    assert 15.0 < rationale["atr_pips"] < 35.0
    assert 100.0 < rationale["h1_swing_pips"] < 130.0


def test_stamp_provenance_pips_sets_none_when_window_short():
    bars = _linear_range_bars(5)
    rationale: dict = {}
    stamp_provenance_pips(rationale, bars=bars, i=3)
    assert rationale["atr_pips"] is None
    assert rationale["h1_swing_pips"] is None


# ---------------------------------------------------------------------------
# regime_fit_from_atr (Phase S, 2026-07-01)
# ---------------------------------------------------------------------------


def test_regime_fit_neutral_when_atr_unavailable():
    bars = _flat_bars(5)      # not enough for period=14
    assert regime_fit_from_atr(bars, i=3) == 0.5


def test_regime_fit_flat_series_clips_to_lower_bound():
    bars = _flat_bars(30)
    v = regime_fit_from_atr(bars, i=20)
    # Flat series -> ATR = 0 -> raw = 0 -> clipped to lo_bound (0.2).
    assert v == pytest.approx(0.2)


def test_regime_fit_at_mean_atr_is_half():
    # Build a synthetic series whose ATR settles at exactly `mean_atr`.
    # 30 pip range every bar, no drift -> ATR14 -> 30 pips.
    span = 30e-4
    bars = [_Bar(1.1000 + span, 1.1000, 1.1000 + span * 0.5) for _ in range(30)]
    v = regime_fit_from_atr(bars, i=20, mean_atr=30.0)
    # r_raw = 0.5 * 30 / 30 = 0.5 -> within [0.2, 0.8] band -> 0.5.
    assert v == pytest.approx(0.5, abs=0.01)


def test_regime_fit_active_tape_clips_to_upper_bound():
    # 100-pip bars: ATR ~= 100 -> raw = 0.5 * 100 / 30 = 1.67 -> clipped to 0.8.
    span = 100e-4
    bars = [_Bar(1.1000 + span, 1.1000, 1.1000 + span * 0.5) for _ in range(30)]
    v = regime_fit_from_atr(bars, i=20, mean_atr=30.0)
    assert v == pytest.approx(0.8)


def test_regime_fit_quiet_tape_clips_to_lower_bound():
    # 5-pip bars: ATR ~= 5 -> raw = 0.5 * 5 / 30 = 0.083 -> clipped to 0.2.
    span = 5e-4
    bars = [_Bar(1.1000 + span, 1.1000, 1.1000 + span * 0.5) for _ in range(30)]
    v = regime_fit_from_atr(bars, i=20, mean_atr=30.0)
    assert v == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# isagi_metavision_lift (Phase S, 2026-07-01)
# ---------------------------------------------------------------------------


def test_metavision_lift_zero_when_no_peers():
    assert isagi_metavision_lift(0, 0) == 0.0


def test_metavision_lift_single_peer_confluence():
    assert isagi_metavision_lift(1, 0) == pytest.approx(0.05)


def test_metavision_lift_multi_peer_confluence():
    assert isagi_metavision_lift(2, 0) == pytest.approx(0.10)
    assert isagi_metavision_lift(5, 0) == pytest.approx(0.10)


def test_metavision_lift_disagreement_dampens():
    assert isagi_metavision_lift(0, 1) == pytest.approx(-0.05)
    assert isagi_metavision_lift(1, 2) == pytest.approx(-0.05)


def test_metavision_lift_multi_peer_beats_disagreement():
    # 2 agree still fires the double-lift even with 1 disagree.
    assert isagi_metavision_lift(2, 1) == pytest.approx(0.10)
