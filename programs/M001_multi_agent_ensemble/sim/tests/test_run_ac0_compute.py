"""Tests for the AC.0-v2 fresh-compute harness.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        AMENDMENT_2026-07-20_ac0_methodology_switch.md §11

Behaviour under test (all methodology-side, no strategy):

1. Per-movable ``.symbols`` widening — only the movable agent under
   test has its ``.symbols`` widened; every other agent stays at
   doctrine defaults.
2. Missing-pair skip — ``_load_production_bars`` raising for a symbol
   drops that symbol from the walk-forward with a WARNING; the
   driver runs on the reduced panel.
3. Output schema — per-movable JSON + MD + combined ``summary.json``
   land under ``out_dir``; JSON conforms to the frozen
   ``Ac0ComputeReport`` shape.
4. Kunigami un-retirement — with ``include_kunigami_unretired=True``
   and movable=``kunigami_rensuke``, Kunigami is in the proposer
   roster passed to ``_drive_squad_replay``.
5. Per-movable roster isolation — running Chigiri then Rin uses fresh
   agent instances per movable; state does NOT bleed across runs.

The heavy compute call (``_drive_squad_replay``) is stubbed to keep
these tests fast; the same pattern is used by
``test_run_g7_v1_checkpoint_gate.py``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_ac0_compute as compute,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Stub replay driver
# ---------------------------------------------------------------------------

@dataclass
class _StubReplayOut:
    """Minimal duck-typed stand-in for ``_drive_squad_replay`` return."""

    thoughts: list = field(default_factory=list)
    proposals_all: list = field(default_factory=list)
    proposals_rejected: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    shadow_trades: list = field(default_factory=list)
    workspace_publish_counts: dict = field(default_factory=dict)
    workspace_read_counts: dict = field(default_factory=dict)


def _make_call_recording_driver() -> tuple[Any, list[dict]]:
    """Return ``(driver_fn, calls_log)``.

    Each call to the driver appends a dict capturing ``agents``,
    ``bars_by_symbol`` keys, and ``aggregator_arm`` so tests can
    assert per-movable roster + panel composition.
    """
    calls: list[dict] = []

    def _driver(**kwargs: Any) -> _StubReplayOut:
        agents = kwargs.get("agents") or []
        calls.append({
            "agent_ids": [a.agent_id for a in agents],
            "agents_by_id": {a.agent_id: a for a in agents},
            "symbols": tuple(sorted(kwargs.get("bars_by_symbol", {}).keys())),
            "aggregator_arm": kwargs.get("aggregator_arm"),
            "sentinel_blocks": kwargs.get("sentinel_blocks"),
            "use_workspace": kwargs.get("use_workspace"),
            "use_shadow_ledger": kwargs.get("use_shadow_ledger"),
            "kunigami_id": (
                kwargs.get("kunigami").agent_id
                if kwargs.get("kunigami") is not None else None
            ),
            "kunigami_symbols": (
                tuple(kwargs.get("kunigami").symbols)
                if kwargs.get("kunigami") is not None else None
            ),
        })
        return _StubReplayOut()

    return _driver, calls


def _make_symbol_availability_stub(available: set[str]):
    """Return a ``_load_production_bars`` stub that returns a dummy bar
    list for symbols in ``available`` and raises ``FileNotFoundError``
    for anything else. Matches how the real loader signals a missing
    parquet."""
    def _stub(symbol: str, start: datetime, end: datetime):
        if symbol not in available:
            raise FileNotFoundError(
                f"stub loader: parquet missing for {symbol}"
            )
        # Return a single dummy bar object -- prepare() is called with
        # this but prepare methods are also stubbed via ``bars`` truthiness
        # in the harness so any non-empty list works.
        return [object()]

    return _stub


@pytest.fixture
def _patched_env(monkeypatch):
    """Neutralise the three side-effects that require live data or the
    production repo: cross-repo path check, bar loading, and per-agent
    ``prepare(sym, bars)`` (the last requires real ``Bar`` objects to
    run ``precompute``). Callers override ``_load_production_bars``
    further per-test."""
    monkeypatch.setattr(compute, "ensure_production_repo_on_path",
                        lambda: None)
    # Default loader: everything succeeds. Individual tests override.
    monkeypatch.setattr(compute, "_load_production_bars",
                        _make_symbol_availability_stub(
                            {"EURUSD", "GBPUSD", "USDCAD",
                             "AUDUSD", "NZDUSD", "USDJPY", "USDCHF"}))
    # prepare() requires production ``Bar`` dataclasses with a real
    # ``timeframe`` attribute; the stub loader returns opaque sentinels
    # instead, so skip the prepare pass in unit tests. Real fires call
    # the un-patched version.
    monkeypatch.setattr(compute, "_prepare_agents_on_panel",
                        lambda proposers, bars_by_symbol: None)
    yield monkeypatch


# ---------------------------------------------------------------------------
# 1. Widening
# ---------------------------------------------------------------------------

def test_run_ac0_compute_widens_movable_symbols(tmp_path, _patched_env):
    """Each movable's ``.symbols`` on its own run must be exactly the
    available-symbols tuple; every OTHER agent stays at their v1
    doctrine defaults."""
    driver, calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)

    requested = ("EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD")
    compute.run_ac0_compute(
        panel_start=datetime(2015, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 12, 31, tzinfo=UTC),
        symbols=requested,
        movable_agents=("chigiri_hyoma", "itoshi_rin"),
        out_dir=tmp_path,
    )

    assert len(calls) == 2, (
        f"expected 2 driver calls (one per movable), got {len(calls)}"
    )

    chi_call, rin_call = calls  # ordered by movable_agents kwarg
    chi_agents = chi_call["agents_by_id"]
    rin_agents = rin_call["agents_by_id"]

    # Chigiri call: Chigiri widened, Rin default (EURUSD only), Isagi
    # default, etc.
    assert tuple(chi_agents["chigiri_hyoma"].symbols) == requested, (
        "chigiri widening failed: expected symbols="
        f"{requested}, got {tuple(chi_agents['chigiri_hyoma'].symbols)!r}"
    )
    assert tuple(rin_agents["chigiri_hyoma"].symbols) == ("EURUSD", "GBPUSD"), (
        "in Rin's run, Chigiri must stay at his v1 default "
        f"(EURUSD, GBPUSD); got {tuple(rin_agents['chigiri_hyoma'].symbols)!r}"
    )

    # Rin call: Rin widened, Chigiri default.
    assert tuple(rin_agents["itoshi_rin"].symbols) == requested, (
        "rin widening failed: expected symbols="
        f"{requested}, got {tuple(rin_agents['itoshi_rin'].symbols)!r}"
    )
    assert tuple(chi_agents["itoshi_rin"].symbols) == ("EURUSD",), (
        "in Chigiri's run, Rin must stay at her v1 default (EURUSD,)"
        f"; got {tuple(chi_agents['itoshi_rin'].symbols)!r}"
    )

    # Anchors always stay at their v1 defaults in every run.
    for call in (chi_call, rin_call):
        by_id = call["agents_by_id"]
        assert tuple(by_id["isagi_yoichi"].symbols) == (
            "EURUSD", "GBPUSD", "USDCAD",
        )
        assert tuple(by_id["bachira_meguru"].symbols) == (
            "EURUSD", "GBPUSD", "USDCAD",
        )
        assert tuple(by_id["barou_shoei"].symbols) == (
            "USDCAD", "EURUSD", "GBPUSD",
        )


# ---------------------------------------------------------------------------
# 2. Skip missing pairs
# ---------------------------------------------------------------------------

def test_run_ac0_compute_skips_missing_pairs(tmp_path, monkeypatch, caplog):
    """USDJPY missing from the parquet cache must be dropped from the
    walk-forward with a WARNING; the driver runs on the reduced panel;
    ``skipped_symbols`` records the drop."""
    monkeypatch.setattr(compute, "ensure_production_repo_on_path",
                        lambda: None)
    monkeypatch.setattr(
        compute, "_load_production_bars",
        _make_symbol_availability_stub({"EURUSD", "GBPUSD", "AUDUSD"}),
    )
    monkeypatch.setattr(compute, "_prepare_agents_on_panel",
                        lambda proposers, bars_by_symbol: None)
    driver, calls = _make_call_recording_driver()
    monkeypatch.setattr(compute, "_drive_squad_replay", driver)

    with caplog.at_level("WARNING", logger="programs.M001_multi_agent_ensemble.sim.scoring.run_ac0_compute"):
        report = compute.run_ac0_compute(
            panel_start=datetime(2015, 1, 1, tzinfo=UTC),
            panel_end=datetime(2025, 12, 31, tzinfo=UTC),
            symbols=("EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "USDJPY"),
            movable_agents=("chigiri_hyoma",),
            out_dir=tmp_path,
        )

    assert set(report.skipped_symbols) == {"USDCAD", "USDJPY"}, (
        f"skipped={report.skipped_symbols!r} — expected {{USDCAD, USDJPY}} "
        "because loader stub returned data only for EURUSD/GBPUSD/AUDUSD"
    )
    assert set(report.available_symbols) == {"EURUSD", "GBPUSD", "AUDUSD"}
    assert "USDJPY" in caplog.text and "USDCAD" in caplog.text, (
        "loader failures must be surfaced via WARNING lines"
    )
    # Driver was only fed the available symbols.
    assert calls[0]["symbols"] == ("AUDUSD", "EURUSD", "GBPUSD"), (
        f"driver received symbols={calls[0]['symbols']!r} — expected only "
        "the available subset"
    )


def test_run_ac0_compute_fail_on_missing_pair_when_disabled(tmp_path, monkeypatch):
    """``skip_missing_pairs=False`` must fail-fast on the first missing
    symbol — the compute worker should never proceed on a silently
    degraded panel unless the caller opts in."""
    monkeypatch.setattr(compute, "ensure_production_repo_on_path",
                        lambda: None)
    monkeypatch.setattr(
        compute, "_load_production_bars",
        _make_symbol_availability_stub({"EURUSD", "GBPUSD"}),
    )
    monkeypatch.setattr(compute, "_prepare_agents_on_panel",
                        lambda proposers, bars_by_symbol: None)
    driver, _calls = _make_call_recording_driver()
    monkeypatch.setattr(compute, "_drive_squad_replay", driver)

    with pytest.raises(RuntimeError, match="USDJPY"):
        compute.run_ac0_compute(
            panel_start=datetime(2015, 1, 1, tzinfo=UTC),
            panel_end=datetime(2025, 12, 31, tzinfo=UTC),
            symbols=("EURUSD", "GBPUSD", "USDJPY"),
            movable_agents=("chigiri_hyoma",),
            out_dir=tmp_path,
            skip_missing_pairs=False,
        )


# ---------------------------------------------------------------------------
# 3. Output schema
# ---------------------------------------------------------------------------

def test_run_ac0_compute_writes_expected_outputs(tmp_path, _patched_env):
    """After a run over a small synthetic panel, per-movable JSON + MD
    and combined summary.json must exist with the expected schema."""
    driver, _calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)

    report = compute.run_ac0_compute(
        panel_start=datetime(2020, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 1, 1, tzinfo=UTC),
        symbols=("EURUSD", "GBPUSD"),
        movable_agents=("chigiri_hyoma",),
        out_dir=tmp_path,
    )

    json_path = tmp_path / "chigiri_hyoma_walkforward.json"
    md_path = tmp_path / "chigiri_hyoma_walkforward.md"
    summary_path = tmp_path / "summary.json"
    assert json_path.exists(), f"missing {json_path}"
    assert md_path.exists(), f"missing {md_path}"
    assert summary_path.exists(), f"missing {summary_path}"

    payload = json.loads(json_path.read_text())
    for key in (
        "agent_id", "requested_symbols", "available_symbols",
        "skipped_symbols", "roster", "windows", "per_pair_window_stats",
        "n_thoughts", "n_proposals", "n_trades_total", "n_trades_movable",
        "aggregator_arm", "include_kunigami_unretired", "fired_at_utc",
    ):
        assert key in payload, f"per-movable JSON missing {key!r}"
    assert payload["agent_id"] == "chigiri_hyoma"
    assert payload["available_symbols"] == ["EURUSD", "GBPUSD"]

    md_body = md_path.read_text()
    assert "chigiri_hyoma" in md_body
    assert "Roster (audit;" in md_body

    summary = json.loads(summary_path.read_text())
    assert summary["movable_agents"] == ["chigiri_hyoma"]
    assert set(summary["per_movable"].keys()) == {"chigiri_hyoma"}
    # Report returned by the function is byte-consistent with summary.json.
    assert report.per_movable["chigiri_hyoma"].agent_id == "chigiri_hyoma"


# ---------------------------------------------------------------------------
# 4. Kunigami un-retirement
# ---------------------------------------------------------------------------

def test_run_ac0_compute_kunigami_unretired(tmp_path, _patched_env):
    """When ``include_kunigami_unretired=True`` and movable is
    ``kunigami_rensuke``, Kunigami must appear in the proposer roster
    passed to ``_drive_squad_replay`` (his ``intend()`` will be
    called by the real driver on every tick). His ``.symbols`` must
    equal the widened tuple.

    In the ``include_kunigami_unretired=False`` mode the run must
    STILL succeed (Kunigami stays R5 side-channel only, matching the
    banked baseline) — but he must NOT be in the proposer roster.
    """
    driver, calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)

    requested = ("EURUSD", "GBPUSD", "USDCAD", "AUDUSD")
    compute.run_ac0_compute(
        panel_start=datetime(2015, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 12, 31, tzinfo=UTC),
        symbols=requested,
        movable_agents=("kunigami_rensuke",),
        out_dir=tmp_path,
        include_kunigami_unretired=True,
    )
    (kun_call,) = calls
    assert "kunigami_rensuke" in kun_call["agent_ids"], (
        "with include_kunigami_unretired=True, Kunigami must be in the "
        f"proposer roster; got {kun_call['agent_ids']!r}"
    )
    # Verify he was widened, not left at his v1 default.
    kun_agent = kun_call["agents_by_id"]["kunigami_rensuke"]
    assert tuple(kun_agent.symbols) == requested, (
        f"Kunigami .symbols must be widened to {requested}; got "
        f"{tuple(kun_agent.symbols)!r}"
    )

    # Now the retired-baseline mode.
    calls.clear()
    compute.run_ac0_compute(
        panel_start=datetime(2015, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 12, 31, tzinfo=UTC),
        symbols=requested,
        movable_agents=("kunigami_rensuke",),
        out_dir=tmp_path,
        include_kunigami_unretired=False,
    )
    (kun_call_retired,) = calls
    assert "kunigami_rensuke" not in kun_call_retired["agent_ids"], (
        "with include_kunigami_unretired=False, Kunigami must NOT be in "
        "the proposer roster (retained R5 side-channel only)"
    )
    # The ``kunigami`` kwarg (R5 side-channel) is still passed.
    assert kun_call_retired["kunigami_id"] == "kunigami_rensuke"


# ---------------------------------------------------------------------------
# 5. Per-movable roster isolation
# ---------------------------------------------------------------------------

def test_run_ac0_compute_isolated_movables(tmp_path, _patched_env):
    """The three movables' walk-forwards must each use FRESH agent
    instances. Mutating (or widening) one run's roster must not leak
    into the next."""
    driver, calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)

    requested = ("EURUSD", "GBPUSD", "USDCAD")
    compute.run_ac0_compute(
        panel_start=datetime(2015, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 12, 31, tzinfo=UTC),
        symbols=requested,
        movable_agents=("chigiri_hyoma", "itoshi_rin", "kunigami_rensuke"),
        out_dir=tmp_path,
    )
    assert len(calls) == 3

    # Distinct agent instances across runs — same agent_id, different
    # Python object identity.
    for aid in ("isagi_yoichi", "bachira_meguru", "itoshi_rin",
                "chigiri_hyoma", "reo_mikage", "nagi_seishiro",
                "barou_shoei"):
        instances = [
            c["agents_by_id"][aid] for c in calls
            if aid in c["agents_by_id"]
        ]
        # Each per-movable run must construct its own instance.
        ids = {id(x) for x in instances}
        assert len(ids) == len(instances), (
            f"{aid} was reused across per-movable runs (identity ids="
            f"{ids!r}); each movable must get a fresh agent instance"
        )

    # Cross-check: Chigiri's widened symbols do not appear on Rin's
    # roster snapshot (proves the widening did not mutate a shared class
    # attribute).
    chi_call, rin_call, kun_call = calls
    assert tuple(chi_call["agents_by_id"]["itoshi_rin"].symbols) == (
        "EURUSD",
    ), "Rin defaults leaked into Chigiri's run"
    assert tuple(rin_call["agents_by_id"]["chigiri_hyoma"].symbols) == (
        "EURUSD", "GBPUSD",
    ), "Chigiri defaults leaked into Rin's run"
    assert tuple(kun_call["agents_by_id"]["itoshi_rin"].symbols) == (
        "EURUSD",
    ), "Rin defaults leaked into Kunigami's run"


# ---------------------------------------------------------------------------
# Bonus: aggregator-arm plumbing
# ---------------------------------------------------------------------------

def test_run_ac0_compute_aggregator_arm_forwarded(tmp_path, _patched_env):
    """Non-default aggregator arms must propagate to the driver. Default
    per the amendment is `phi41` (matches the sealed g7retry1
    baseline)."""
    driver, calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)

    compute.run_ac0_compute(
        panel_start=datetime(2015, 1, 1, tzinfo=UTC),
        panel_end=datetime(2025, 12, 31, tzinfo=UTC),
        symbols=("EURUSD", "GBPUSD"),
        movable_agents=("chigiri_hyoma",),
        out_dir=tmp_path,
        aggregator_arm="arm4",
    )
    assert calls[0]["aggregator_arm"] == "arm4"


def test_run_ac0_compute_rejects_unknown_movable(tmp_path, _patched_env):
    """Guard against typos / misconfigured movable ids -- reject early
    rather than silently produce empty telemetry."""
    driver, _calls = _make_call_recording_driver()
    _patched_env.setattr(compute, "_drive_squad_replay", driver)
    with pytest.raises(ValueError, match="unknown id"):
        compute.run_ac0_compute(
            panel_start=datetime(2015, 1, 1, tzinfo=UTC),
            panel_end=datetime(2025, 12, 31, tzinfo=UTC),
            symbols=("EURUSD",),
            movable_agents=("isagi_yoichi",),  # anchor, not a movable
            out_dir=tmp_path,
        )
