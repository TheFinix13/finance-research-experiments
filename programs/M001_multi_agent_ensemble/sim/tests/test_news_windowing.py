"""Tests for the per-agent news-window helper (spec §5.4 + D-Q5).

Covers ``window_for_agent`` mapping across every TF in the roster and
``tag_bars_for_agent`` end-to-end using the DK 2024 sample fixture.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from programs.M001_multi_agent_ensemble.sim.regime.news_calendar import (
    DEFAULT_POST_EVENT_MINUTES,
    DEFAULT_PRE_EVENT_MINUTES,
)
from programs.M001_multi_agent_ensemble.sim.regime.news_windowing import (
    BAR_COUNT_WINDOWS,
    MINUTE_WINDOWS,
    tag_bars_for_agent,
    window_for_agent,
)


FIXTURES = Path(__file__).parent / "fixtures" / "news_calendar"
DK_SAMPLE = FIXTURES / "dk_2024_sample.parquet"


class _StubAgent:
    """Duck-type an M001 agent for the windowing tests."""

    def __init__(self, home_tf: str, symbols=(), agent_id="stub_agent"):
        self.home_tf = home_tf
        self.symbols = tuple(symbols)
        self.agent_id = agent_id


class TestWindowForAgent:

    def test_h4_agent_returns_bar_count(self):
        agent = _StubAgent(home_tf="H4")
        w = window_for_agent(agent)
        assert w == {"pre_event_bars": 2, "post_event_bars": 2}

    def test_d1_agent_returns_bar_count(self):
        agent = _StubAgent(home_tf="D1")
        w = window_for_agent(agent)
        assert w == {"pre_event_bars": 1, "post_event_bars": 1}

    def test_h1_agent_returns_bar_count(self):
        agent = _StubAgent(home_tf="H1")
        assert set(window_for_agent(agent)) == {
            "pre_event_bars", "post_event_bars",
        }

    def test_m15_agent_returns_minute_window(self):
        agent = _StubAgent(home_tf="M15")
        w = window_for_agent(agent)
        assert w == {
            "pre_event_minutes": DEFAULT_PRE_EVENT_MINUTES,
            "post_event_minutes": DEFAULT_POST_EVENT_MINUTES,
        }

    def test_m5_agent_returns_minute_window(self):
        agent = _StubAgent(home_tf="M5")
        w = window_for_agent(agent)
        assert "pre_event_minutes" in w
        assert w["post_event_minutes"] == DEFAULT_POST_EVENT_MINUTES

    def test_missing_home_tf_defaults_to_h4(self):
        class NoTf:
            agent_id = "no_tf"
        agent = NoTf()
        w = window_for_agent(agent)
        assert w == {"pre_event_bars": 2, "post_event_bars": 2}

    def test_unknown_home_tf_defaults_to_h4(self):
        agent = _StubAgent(home_tf="WEEKLY")   # not in either table
        w = window_for_agent(agent)
        assert w == {"pre_event_bars": 2, "post_event_bars": 2}

    def test_windowing_tables_shape(self):
        # All bar-count windows are (int, int) tuples with positive
        # values.
        for tf, (pre, post) in BAR_COUNT_WINDOWS.items():
            assert isinstance(pre, int) and pre > 0, tf
            assert isinstance(post, int) and post > 0, tf
        # All minute windows too.
        for tf, (pre, post) in MINUTE_WINDOWS.items():
            assert isinstance(pre, int) and pre > 0, tf
            assert isinstance(post, int) and post > 0, tf


class TestTagBarsForAgent:

    def _make_h4_index(self, start: str, end: str) -> pd.DatetimeIndex:
        return pd.date_range(start=start, end=end, freq="4h", tz="UTC")

    def _make_archive_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "news_calendar"
        root.mkdir(parents=True, exist_ok=True)
        pd.read_parquet(DK_SAMPLE).to_parquet(
            root / "events.parquet", index=False,
        )
        return root

    def test_h4_agent_full_pipeline(self, tmp_path):
        agent = _StubAgent(home_tf="H4", symbols=("EURUSD",))
        idx = self._make_h4_index("2024-07-05 00:00", "2024-07-06 04:00")
        s = tag_bars_for_agent(
            idx, agent, symbol_pair="EURUSD",
            archive_root=self._make_archive_root(tmp_path),
        )
        assert s.name == "news_calendar"
        assert bool(s.loc[pd.Timestamp("2024-07-05 12:00", tz="UTC")])

    def test_symbol_pair_auto_from_agent_symbols(self, tmp_path):
        agent = _StubAgent(home_tf="H4", symbols=("EURUSD",))
        idx = self._make_h4_index("2024-07-05 00:00", "2024-07-06 04:00")
        s = tag_bars_for_agent(
            idx, agent,
            archive_root=self._make_archive_root(tmp_path),
        )
        assert s.name == "news_calendar"

    def test_missing_symbol_pair_raises(self, tmp_path):
        agent = _StubAgent(home_tf="H4", symbols=())  # empty tuple
        idx = self._make_h4_index("2024-01-01", "2024-01-02")
        with pytest.raises(ValueError, match="symbol_pair"):
            tag_bars_for_agent(
                idx, agent,
                archive_root=self._make_archive_root(tmp_path),
            )

    def test_caller_override_wins(self, tmp_path):
        agent = _StubAgent(home_tf="H4", symbols=("EURUSD",))
        idx = self._make_h4_index("2024-07-05 00:00", "2024-07-06 04:00")
        # Override window_bars to 0 -- only the containing bar should
        # be True.
        s = tag_bars_for_agent(
            idx, agent, symbol_pair="EURUSD",
            archive_root=self._make_archive_root(tmp_path),
            pre_event_bars=0, post_event_bars=0,
        )
        assert bool(s.loc[pd.Timestamp("2024-07-05 12:00", tz="UTC")])
        # ±1 bar should be False now.
        assert not bool(s.loc[pd.Timestamp("2024-07-05 08:00", tz="UTC")])


class TestRosterCoverage:
    """Every agent in the M001 roster returns a valid window (D-Q5)."""

    @pytest.mark.parametrize("agent_module_name,agent_class_name", [
        ("a01_isagi", "A1IsagiV1"),
        ("a02_bachira", "A2BachiraV1"),
        ("a03_rin", "A3RinV1"),
        ("a04_chigiri", "A4ChigiriV1"),
        ("a05_reo", "A5ReoV1"),
        ("a06_nagi", "A6NagiV1"),
        ("a07_barou", "A7BarouV1"),
        ("a10_kunigami", "A10KunigamiV1"),
    ])
    def test_agent_produces_valid_window(
        self, agent_module_name, agent_class_name,
    ):
        module = __import__(
            f"programs.M001_multi_agent_ensemble.sim.agents.{agent_module_name}",
            fromlist=[agent_class_name],
        )
        klass = getattr(module, agent_class_name)
        agent = klass()
        w = window_for_agent(agent)
        # Every returned window has at least one of the two window
        # families, and the value is a positive int.
        assert isinstance(w, dict)
        assert len(w) == 2
        for key, val in w.items():
            assert isinstance(val, int) and val >= 0, (agent, key, val)
