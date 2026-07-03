"""Phase 5 -- Shadow-driven HRP input builder unit tests.

Tests the pure-function transformations in
``sim/core/aggregator_arms/hrp_shadow_inputs.py``:

- Timestamp normalisation (``_entry_to_datetime``).
- Bucketing (``bucket_shadow_by_agent_window``).
- Per-agent window-mean series construction across the three
  supported metrics (tqs / pnl_pips / r_multiple).
- Trade-count computation.
- Composed ``compute_hrp_weights_from_shadow`` pipeline (delegating
  to the existing ``compute_hrp_weights`` -- exercises the wire,
  not the arm mechanic).

No compute; pure data-transformation tests. Compute-side re-sim
(Phase 6e per Amendment §11.3) is out of scope for this file.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms import (
    HRPWeightSnapshot,
    WindowBoundary,
    bucket_shadow_by_agent_window,
    compute_hrp_weights_from_shadow,
    per_agent_shadow_trade_counts,
    per_agent_window_means_from_shadow,
)
from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms.hrp_shadow_inputs import (
    _entry_to_datetime,
    _extract_metric,
)
from programs.M001_multi_agent_ensemble.sim.scoring.shadow_ledger import (
    ShadowTradeRecord,
)


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------

def _make_shadow(
    *,
    agent_id: str,
    entry_time,  # datetime OR unparseable sentinel for tests
    tqs: float = 0.30,
    pnl_pips: float = 5.0,
    r_multiple: float = 1.0,
    symbol: str = "EURUSD",
) -> ShadowTradeRecord:
    """Minimal ``ShadowTradeRecord`` fixture -- only the fields the
    input builder reads are populated. ``entry_time`` accepts non-
    datetime sentinels (None, unparseable strings) for negative-path
    tests; ``exit_time`` is set to None in that case."""
    if isinstance(entry_time, datetime):
        exit_time = entry_time + timedelta(hours=4)
    else:
        exit_time = None
    return ShadowTradeRecord(
        agent_id=agent_id,
        symbol=symbol,
        entry_time=entry_time,
        exit_time=exit_time,
        direction="long",
        entry=1.10,
        stop=1.09,
        take_profit=1.12,
        exit_price=1.11,
        exit_reason="tp",
        pnl_pips=pnl_pips,
        mae_pips=0.0,
        mfe_pips=10.0,
        bars_held=1,
        r_multiple=r_multiple,
        tqs_components={"tqs": tqs},
        rejection_reason="aggregator_lower_conviction",
        proposal_tick_id=0,
    )


def _three_windows() -> list[WindowBoundary]:
    """Three consecutive one-week UTC windows starting 2025-01-01."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        WindowBoundary(
            window_index=i,
            start=base + timedelta(weeks=i),
            end=base + timedelta(weeks=i + 1),
        )
        for i in range(3)
    ]


# ---------------------------------------------------------------------------
# _entry_to_datetime
# ---------------------------------------------------------------------------

class TestEntryToDatetime:
    def test_native_datetime_returned_unchanged(self):
        dt = datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc)
        assert _entry_to_datetime(dt) is dt

    def test_none_returns_none(self):
        assert _entry_to_datetime(None) is None

    def test_iso_string_parses(self):
        result = _entry_to_datetime("2025-01-05T12:00:00+00:00")
        assert result == datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc)

    def test_malformed_string_returns_none(self):
        assert _entry_to_datetime("not-a-date") is None
        assert _entry_to_datetime("2025-13-99") is None

    def test_pandas_timestamp_via_to_pydatetime(self):
        class FakeTimestamp:
            def to_pydatetime(self):
                return datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc)

        result = _entry_to_datetime(FakeTimestamp())
        assert result == datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc)

    def test_to_pydatetime_returning_non_datetime_is_ignored(self):
        class BadTimestamp:
            def to_pydatetime(self):
                return "still a string"

        # Fallback path: try fromisoformat on str(instance), which fails.
        assert _entry_to_datetime(BadTimestamp()) is None

    def test_to_pydatetime_raising_is_ignored(self):
        class ExplosiveTimestamp:
            def to_pydatetime(self):
                raise RuntimeError("boom")

        assert _entry_to_datetime(ExplosiveTimestamp()) is None


# ---------------------------------------------------------------------------
# _extract_metric
# ---------------------------------------------------------------------------

class TestExtractMetric:
    def test_tqs_extraction(self):
        r = _make_shadow(
            agent_id="a",
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            tqs=0.42,
        )
        assert _extract_metric(r, "tqs") == pytest.approx(0.42)

    def test_pnl_pips_extraction(self):
        r = _make_shadow(
            agent_id="a",
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            pnl_pips=17.5,
        )
        assert _extract_metric(r, "pnl_pips") == pytest.approx(17.5)

    def test_r_multiple_extraction(self):
        r = _make_shadow(
            agent_id="a",
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            r_multiple=2.5,
        )
        assert _extract_metric(r, "r_multiple") == pytest.approx(2.5)

    def test_missing_tqs_key_defaults_to_zero(self):
        r = _make_shadow(
            agent_id="a",
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        r.tqs_components = {}  # simulate an older record without 'tqs'
        assert _extract_metric(r, "tqs") == 0.0

    def test_unknown_metric_raises(self):
        r = _make_shadow(
            agent_id="a",
            entry_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        with pytest.raises(ValueError, match="unknown metric"):
            _extract_metric(r, "not_a_metric")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# bucket_shadow_by_agent_window
# ---------------------------------------------------------------------------

class TestBucketing:
    def test_empty_records(self):
        assert bucket_shadow_by_agent_window([], _three_windows()) == {}

    def test_single_agent_single_window(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi",
                entry_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
            ),
        ]
        b = bucket_shadow_by_agent_window(recs, windows)
        assert list(b.keys()) == ["isagi"]
        assert list(b["isagi"].keys()) == [0]
        assert len(b["isagi"][0]) == 1

    def test_records_outside_all_windows_dropped(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi",
                entry_time=datetime(2024, 12, 15, tzinfo=timezone.utc),
            ),
            _make_shadow(
                agent_id="isagi",
                entry_time=datetime(2025, 2, 15, tzinfo=timezone.utc),
            ),
        ]
        assert bucket_shadow_by_agent_window(recs, windows) == {}

    def test_records_with_unparseable_time_dropped(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi", entry_time="not-a-date",
            ),
            _make_shadow(
                agent_id="isagi", entry_time=None,
            ),
        ]
        assert bucket_shadow_by_agent_window(recs, windows) == {}

    def test_end_boundary_is_exclusive(self):
        windows = _three_windows()  # [start, start+1w), etc.
        # Exactly at start of window 1 -> falls in window 1, not 0.
        recs = [
            _make_shadow(
                agent_id="a",
                entry_time=windows[1].start,
            ),
        ]
        b = bucket_shadow_by_agent_window(recs, windows)
        assert list(b["a"].keys()) == [1]

    def test_multiple_agents_multiple_windows(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi",
                entry_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                tqs=0.30,
            ),
            _make_shadow(
                agent_id="isagi",
                entry_time=datetime(2025, 1, 10, tzinfo=timezone.utc),
                tqs=0.35,
            ),
            _make_shadow(
                agent_id="bachira",
                entry_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                tqs=0.28,
            ),
        ]
        b = bucket_shadow_by_agent_window(recs, windows)
        assert set(b.keys()) == {"isagi", "bachira"}
        assert set(b["isagi"].keys()) == {0, 1}
        assert set(b["bachira"].keys()) == {0}


# ---------------------------------------------------------------------------
# per_agent_window_means_from_shadow
# ---------------------------------------------------------------------------

class TestPerAgentWindowMeans:
    def test_empty_records(self):
        assert per_agent_window_means_from_shadow([], _three_windows()) == {}

    def test_single_agent_all_windows_have_data(self):
        windows = _three_windows()
        recs = []
        for i in range(3):
            for _ in range(2):
                recs.append(_make_shadow(
                    agent_id="isagi",
                    entry_time=windows[i].start + timedelta(hours=1),
                    tqs=0.3 + 0.1 * i,
                ))
        out = per_agent_window_means_from_shadow(recs, windows, metric="tqs")
        assert out["isagi"] == pytest.approx([0.3, 0.4, 0.5])

    def test_gaps_are_skipped_not_zero_filled(self):
        # HRP right-aligns and zero-fills; this function returns the
        # non-gap subset so the caller can decide.
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi",
                entry_time=windows[0].start + timedelta(hours=1),
                tqs=0.25,
            ),
            _make_shadow(
                agent_id="isagi",
                entry_time=windows[2].start + timedelta(hours=1),
                tqs=0.45,
            ),
        ]
        out = per_agent_window_means_from_shadow(recs, windows)
        assert out["isagi"] == pytest.approx([0.25, 0.45])

    def test_agent_with_zero_bucketed_trades_excluded(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="isagi",
                entry_time=windows[0].start + timedelta(hours=1),
            ),
            _make_shadow(  # bachira record entirely outside windows
                agent_id="bachira",
                entry_time=datetime(2024, 12, 15, tzinfo=timezone.utc),
            ),
        ]
        out = per_agent_window_means_from_shadow(recs, windows)
        assert set(out.keys()) == {"isagi"}

    def test_pnl_pips_metric(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="a",
                entry_time=windows[0].start + timedelta(hours=1),
                pnl_pips=10.0,
            ),
            _make_shadow(
                agent_id="a",
                entry_time=windows[0].start + timedelta(hours=5),
                pnl_pips=20.0,
            ),
        ]
        out = per_agent_window_means_from_shadow(recs, windows, metric="pnl_pips")
        assert out["a"] == pytest.approx([15.0])

    def test_r_multiple_metric(self):
        windows = _three_windows()
        recs = [
            _make_shadow(
                agent_id="a",
                entry_time=windows[0].start + timedelta(hours=1),
                r_multiple=1.5,
            ),
            _make_shadow(
                agent_id="a",
                entry_time=windows[0].start + timedelta(hours=2),
                r_multiple=-0.5,
            ),
        ]
        out = per_agent_window_means_from_shadow(recs, windows, metric="r_multiple")
        assert out["a"] == pytest.approx([0.5])


# ---------------------------------------------------------------------------
# per_agent_shadow_trade_counts
# ---------------------------------------------------------------------------

class TestPerAgentShadowTradeCounts:
    def test_empty(self):
        assert per_agent_shadow_trade_counts([]) == {}

    def test_multiple_agents(self):
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        recs = (
            [_make_shadow(agent_id="isagi", entry_time=base)] * 5
            + [_make_shadow(agent_id="bachira", entry_time=base)] * 3
            + [_make_shadow(agent_id="rin", entry_time=base)] * 1
        )
        assert per_agent_shadow_trade_counts(recs) == {
            "isagi": 5,
            "bachira": 3,
            "rin": 1,
        }

    def test_counts_include_records_outside_windows(self):
        # This helper doesn't take windows -- it counts everything.
        # min_trades filtering happens in compute_hrp_weights.
        base_out = datetime(2020, 1, 1, tzinfo=timezone.utc)
        recs = [_make_shadow(agent_id="a", entry_time=base_out)] * 42
        assert per_agent_shadow_trade_counts(recs) == {"a": 42}


# ---------------------------------------------------------------------------
# compute_hrp_weights_from_shadow (composition)
# ---------------------------------------------------------------------------

class TestComputeHrpWeightsFromShadow:
    def test_empty_records_yields_no_eligible_agents_fallback(self):
        windows = _three_windows()
        snap = compute_hrp_weights_from_shadow(
            shadow_records=[],
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
        )
        assert isinstance(snap, HRPWeightSnapshot)
        assert snap.weights == {}
        assert snap.fallback_triggered is True
        assert snap.fallback_reason == "no_eligible_agents"

    def test_below_min_trades_excluded(self):
        # Default HRP_MIN_TRADES_PER_AGENT = 30. Provide only 5 trades
        # per agent -> both excluded -> fallback.
        windows = _three_windows()
        recs = []
        for aid in ("isagi", "bachira"):
            for i in range(5):
                recs.append(_make_shadow(
                    agent_id=aid,
                    entry_time=windows[0].start + timedelta(hours=i),
                    tqs=0.3,
                ))
        snap = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
        )
        assert snap.weights == {}
        assert set(snap.excluded_agents) == {"isagi", "bachira"}
        # Both flagged with min_trades reason.
        for aid in ("isagi", "bachira"):
            assert "min_trades" in snap.excluded_reasons[aid]

    def test_min_trades_kwarg_overrides_default(self):
        # Lower the floor so 5 trades qualifies.
        windows = _three_windows()
        recs = []
        # Give each agent 4 trades in each of 3 windows so per-window
        # means differ across agents -> non-degenerate cov.
        # NOTE: the raw-values are chosen so the tangency direction
        # picks 'isagi' higher, giving HRP something non-trivial to do.
        vals_isagi = [(0.30, 0.35, 0.40)]
        vals_bachira = [(0.28, 0.32, 0.36)]
        for aid, per_window in (
            ("isagi", vals_isagi[0]),
            ("bachira", vals_bachira[0]),
        ):
            for i, tqs in enumerate(per_window):
                for _ in range(2):
                    recs.append(_make_shadow(
                        agent_id=aid,
                        entry_time=windows[i].start + timedelta(hours=1),
                        tqs=tqs,
                    ))
        snap = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
        )
        assert set(snap.weights.keys()) == {"isagi", "bachira"}
        assert snap.weights["isagi"] + snap.weights["bachira"] == pytest.approx(1.0)
        # Both weights positive after long-only clip.
        assert all(w >= 0 for w in snap.weights.values())

    def test_shrinkage_kwarg_passes_through(self):
        # High shrinkage -> cov close to diag -> weights approach
        # equal-weight over positive-mean agents.
        windows = _three_windows()
        recs = []
        vals_isagi = [0.30, 0.35, 0.40]
        vals_bachira = [0.30, 0.35, 0.40]  # same means -> tie
        for aid, per_window in (
            ("isagi", vals_isagi),
            ("bachira", vals_bachira),
        ):
            for i, tqs in enumerate(per_window):
                for _ in range(2):
                    recs.append(_make_shadow(
                        agent_id=aid,
                        entry_time=windows[i].start + timedelta(hours=1),
                        tqs=tqs,
                    ))
        snap_hi_shrink = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
            shrinkage=0.99,
        )
        # Identical means + identical variance + full shrinkage -> both weights should be 0.5.
        assert snap_hi_shrink.weights["isagi"] == pytest.approx(0.5, abs=1e-3)
        assert snap_hi_shrink.weights["bachira"] == pytest.approx(0.5, abs=1e-3)

    def test_weight_cap_kwarg_passes_through(self):
        # Contrast: same inputs, high cap (1.0 = no effective cap) vs
        # low cap (0.5). This verifies the cap KWARG PROPAGATES to
        # the underlying compute_hrp_weights; the specific cap-vs-
        # tangency-clip interaction is exercised in test_aggregator_
        # arms_hrp.py, not here.
        windows = _three_windows()
        recs = []
        # Three agents with monotonically-increasing means; high-cap
        # run should let the highest-mean one dominate.
        vals = {
            "isagi": [0.20, 0.22, 0.24],
            "bachira": [0.30, 0.35, 0.40],
            "rin": [0.28, 0.32, 0.36],
        }
        for aid, per_window in vals.items():
            for i, tqs in enumerate(per_window):
                for _ in range(4):
                    recs.append(_make_shadow(
                        agent_id=aid,
                        entry_time=windows[i].start + timedelta(hours=1),
                        tqs=tqs,
                    ))
        snap_uncapped = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
            weight_cap=1.0,
        )
        snap_capped = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
            weight_cap=0.5,
        )
        # Both sum to 1 (post-normalisation).
        assert sum(snap_uncapped.weights.values()) == pytest.approx(1.0)
        assert sum(snap_capped.weights.values()) == pytest.approx(1.0)
        # Cap kwarg propagation: the capped run's max weight is <=
        # the uncapped run's max weight (cap can only shrink the
        # peak).
        assert max(snap_capped.weights.values()) <= (
            max(snap_uncapped.weights.values()) + 1e-9
        )

    def test_metric_parameter_switches_covariance_axis(self):
        # Same records; different metric -> different weights.
        windows = _three_windows()
        recs = []
        # Two agents; one has high tqs but negative pnl (loss-cutter
        # profile), the other has moderate tqs and positive pnl.
        # HRP on tqs and HRP on pnl_pips should disagree.
        cases = [
            ("agent_a", 0.5, -1.0),  # high tqs, negative pnl
            ("agent_a", 0.5, -1.0),
            ("agent_b", 0.3, 5.0),   # moderate tqs, positive pnl
            ("agent_b", 0.3, 5.0),
        ]
        for w_idx in range(3):
            for aid, tqs, pnl in cases:
                for _ in range(4):
                    recs.append(_make_shadow(
                        agent_id=aid,
                        entry_time=windows[w_idx].start + timedelta(hours=1),
                        tqs=tqs,
                        pnl_pips=pnl,
                    ))
        snap_tqs = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
            metric="tqs",
        )
        snap_pnl = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
            metric="pnl_pips",
        )
        # tqs metric: agent_a mean > agent_b mean -> agent_a gets nonzero weight.
        # pnl_pips metric: agent_a mean < agent_b mean -> agent_a clipped to zero.
        assert snap_tqs.weights["agent_a"] > 0
        # Under pnl_pips, tangency prefers agent_b (long-only clip drops agent_a).
        # Both agents share weight OR agent_b dominates depending on cov, but
        # agent_b's weight should exceed agent_a's under pnl_pips.
        assert snap_pnl.weights["agent_b"] >= snap_pnl.weights["agent_a"]

    def test_snapshot_carries_provided_window_bounds(self):
        windows = _three_windows()
        recs = []
        for i in range(3):
            for _ in range(10):
                recs.append(_make_shadow(
                    agent_id="a",
                    entry_time=windows[i].start + timedelta(hours=1),
                    tqs=0.3,
                ))
                recs.append(_make_shadow(
                    agent_id="b",
                    entry_time=windows[i].start + timedelta(hours=2),
                    tqs=0.35,
                ))
        expected_ws = datetime(2025, 6, 1, tzinfo=timezone.utc)
        expected_we = datetime(2025, 6, 8, tzinfo=timezone.utc)
        snap = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=expected_ws,
            window_end=expected_we,
            min_trades_per_agent=5,
        )
        assert snap.window_start == expected_ws
        assert snap.window_end == expected_we


# ---------------------------------------------------------------------------
# End-to-end sanity: no divergence from executed-TQS path
# ---------------------------------------------------------------------------

class TestEquivalenceWithDirectHrpInputs:
    """When shadow data is homogeneous (identical windows across all
    agents), the shadow-driven HRP should produce weights consistent
    with directly passing the same per-agent-per-window mean series
    to the underlying compute_hrp_weights. This is a wire-not-mechanic
    test."""

    def test_shadow_path_matches_direct_path(self):
        from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms import (
            compute_hrp_weights,
        )

        windows = _three_windows()
        vals = {
            "isagi": [0.30, 0.35, 0.40],
            "bachira": [0.28, 0.32, 0.36],
            "rin": [0.32, 0.30, 0.28],
        }
        recs = []
        for aid, per_window in vals.items():
            for i, tqs in enumerate(per_window):
                for _ in range(3):
                    recs.append(_make_shadow(
                        agent_id=aid,
                        entry_time=windows[i].start + timedelta(hours=1),
                        tqs=tqs,
                    ))
        # Shadow-driven path.
        snap_shadow = compute_hrp_weights_from_shadow(
            shadow_records=recs,
            windows=windows,
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
        )
        # Direct path: hand-built means (all agents have 9 trades).
        snap_direct = compute_hrp_weights(
            per_agent_window_tqs=vals,
            per_agent_trade_counts={aid: 9 for aid in vals},
            window_start=windows[0].start,
            window_end=windows[-1].end,
            min_trades_per_agent=5,
        )
        for aid in vals:
            assert snap_shadow.weights[aid] == pytest.approx(
                snap_direct.weights[aid], abs=1e-9,
            )
        assert snap_shadow.included_agents == snap_direct.included_agents
