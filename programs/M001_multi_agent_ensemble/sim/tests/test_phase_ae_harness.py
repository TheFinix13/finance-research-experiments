"""Phase AE harness tests — driver equivalence + event-tick builder.

The load-bearing test is the BASELINE EQUIVALENCE check: the
AE-specialised driver (``_drive_squad_replay_ae`` with ``sae=None``)
must reproduce ``_drive_squad_replay`` (sentinel_blocks=True,
use_workspace=True, phi41, no shadow) trade-for-trade on a real
2-year EURUSD slice from the production cache. This is the guard
that makes the Phase AE baseline arm comparable to the sealed
g7retry2 lineage. Marked slow: needs the production parquet cache
on PYTHONPATH (same requirement as the other gate harness tests).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import SimNewsEvent
from programs.M001_multi_agent_ensemble.sim.scoring.run_phase_ae_compute import (
    build_ae_roster,
    build_sae_event_ticks,
)

UTC = timezone.utc


class TestEventTickBuilder:
    def test_two_ticks_per_event_sorted_deduped(self):
        t1 = datetime(2024, 3, 8, 13, 30, tzinfo=UTC)
        t2 = datetime(2024, 3, 12, 12, 30, tzinfo=UTC)
        events = [
            SimNewsEvent(time_utc=t2, currency="USD", impact="High", title="CPI"),
            SimNewsEvent(time_utc=t1, currency="USD", impact="High", title="NFP"),
            SimNewsEvent(time_utc=t1, currency="EUR", impact="High", title="ECB"),
            SimNewsEvent(time_utc=t1, currency="USD", impact="Low", title="minor"),
        ]
        ticks = build_sae_event_ticks(
            events,
            panel_start=datetime(2024, 1, 1, tzinfo=UTC),
            panel_end=datetime(2024, 12, 31, tzinfo=UTC),
        )
        assert ticks == [
            t1 + timedelta(minutes=15), t1 + timedelta(minutes=30),
            t2 + timedelta(minutes=15), t2 + timedelta(minutes=30),
        ]

    def test_out_of_panel_events_excluded(self):
        t = datetime(2030, 1, 1, 13, 30, tzinfo=UTC)
        events = [SimNewsEvent(time_utc=t, currency="USD", impact="High",
                               title="future")]
        assert build_sae_event_ticks(
            events,
            panel_start=datetime(2024, 1, 1, tzinfo=UTC),
            panel_end=datetime(2024, 12, 31, tzinfo=UTC),
        ) == []


@pytest.mark.slow
class TestBaselineEquivalence:
    """AE driver with sae=None == original driver, real-cache slice."""

    def test_equivalence_two_year_eurusd_slice(self):
        from programs.M001_multi_agent_ensemble.sim._cross_repo import (
            ensure_production_repo_on_path,
        )
        ensure_production_repo_on_path()
        from programs.M001_multi_agent_ensemble.sim.core.ledger import (
            FullLedger,
        )
        from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (  # noqa: E501
            _load_production_bars,
        )
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phase_ae_compute import (  # noqa: E501
            _drive_squad_replay_ae,
        )
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (  # noqa: E501
            _drive_squad_replay,
        )

        start = datetime(2023, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        bars = {"EURUSD": _load_production_bars("EURUSD", start, end)}
        assert bars["EURUSD"], "production cache unavailable"

        # Fresh roster per run: agents are stateful.
        agents_a, isagi_a, barou_a, kuni_a = build_ae_roster()
        agents_b, isagi_b, barou_b, kuni_b = build_ae_roster()
        for roster, isagi in ((agents_a, isagi_a), (agents_b, isagi_b)):
            bachira, rin, chigiri = roster[1], roster[2], roster[3]
            barou = roster[6]
            for agent in (isagi, bachira, rin, chigiri, barou):
                if hasattr(agent, "prepare") and "EURUSD" in agent.symbols:
                    agent.prepare("EURUSD", bars["EURUSD"])

        ref = _drive_squad_replay(
            agents=agents_a, isagi=isagi_a, barou=barou_a, kunigami=kuni_a,
            bars_by_symbol=bars, ledger=FullLedger(),
            sentinel_blocks=True, use_workspace=True,
            use_shadow_ledger=False, aggregator_arm="phi41",
        )
        ae, sae_meta = _drive_squad_replay_ae(
            agents=agents_b, isagi=isagi_b, barou=barou_b, kunigami=kuni_b,
            bars_by_symbol=bars, ledger=FullLedger(),
            sae=None,
        )

        assert sae_meta == []

        def _trade_key(t):
            return (
                t.agent_id, t.symbol, t.entry_time, t.exit_time,
                t.direction, round(t.entry, 8), round(t.exit_price, 8),
                round(t.pnl_pips, 6), t.exit_reason,
                round(t.tqs_components.get("tqs", 0.0), 10),
            )

        assert len(ae.trades) == len(ref.trades)
        assert [_trade_key(t) for t in ae.trades] == [
            _trade_key(t) for t in ref.trades
        ]
        assert len(ae.proposals_all) == len(ref.proposals_all)
        assert len(ae.proposals_accepted) == len(ref.proposals_accepted)
        assert len(ae.proposals_rejected) == len(ref.proposals_rejected)
        assert len(ae.sentinel_log) == len(ref.sentinel_log)
        assert ae.workspace_publish_counts == ref.workspace_publish_counts
        assert ae.workspace_read_counts == ref.workspace_read_counts
