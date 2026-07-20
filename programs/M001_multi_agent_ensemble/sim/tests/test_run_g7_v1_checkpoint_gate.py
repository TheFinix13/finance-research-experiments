"""Tests for the G7 v1 checkpoint gate harness (Phase AC extension).

Covers only the Phase AC harness extension (methodology-only):
promotion of ``SYMBOLS_G7`` from a module-level constant to a runtime
parameter on ``run_g7_walk_forward`` / ``run_g7_dry_run`` plus the
``--symbols`` CLI arg. The rest of the harness (replay driver, criteria
evaluators, aggregators) has its own coverage in
``test_g7_criteria_evaluators.py``, ``test_run_g7_final_verdict.py``,
etc.

Full end-to-end replay through ``_drive_squad_replay`` is a compute
job (~30-90 min per invocation) and cannot run inside the unit-test
suite; the tests below stub the two heavy calls
(``_load_production_bars`` + ``_drive_squad_replay``) so the plumbing
gets exercised end-to-end deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_g7_v1_checkpoint_gate as gate,
)


UTC = timezone.utc


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


def _stub_load_bars_factory():
    """Return a stub ``_load_production_bars`` plus its call log."""
    calls: list[tuple[str, datetime, datetime]] = []

    def _stub(symbol: str, start: datetime, end: datetime):
        calls.append((symbol, start, end))
        return []

    return _stub, calls


def _stub_drive_squad_replay(**kwargs: Any) -> _StubReplayOut:
    return _StubReplayOut()


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

def test_g7_walk_forward_honours_custom_symbols(tmp_path):
    """Passing ``symbols=("EURUSD","AUDUSD")`` must drive the panel
    loader for exactly those two — the default (EURUSD/GBPUSD/USDCAD)
    must NOT bleed in."""
    stub_load, load_calls = _stub_load_bars_factory()
    with (
        patch.object(gate, "_load_production_bars", stub_load),
        patch.object(gate, "_drive_squad_replay", _stub_drive_squad_replay),
        patch.object(gate, "ensure_production_repo_on_path", lambda: None),
    ):
        gate.run_g7_walk_forward(
            panel_start=datetime(2020, 1, 1, tzinfo=UTC),
            panel_end=datetime(2025, 1, 1, tzinfo=UTC),
            symbols=("EURUSD", "AUDUSD"),
            out_dir=None,
            tag="unit-custom-symbols",
        )

    loaded_syms = [c[0] for c in load_calls]
    assert loaded_syms == ["EURUSD", "AUDUSD"], (
        f"walk-forward loaded {loaded_syms!r} — expected exactly the "
        "override tuple (EURUSD, AUDUSD)"
    )


def test_g7_walk_forward_default_unchanged(tmp_path):
    """No ``symbols`` kwarg must fall through to ``SYMBOLS_G7`` — the
    G7 default panel remains byte-identical to every sealed cache."""
    stub_load, load_calls = _stub_load_bars_factory()
    with (
        patch.object(gate, "_load_production_bars", stub_load),
        patch.object(gate, "_drive_squad_replay", _stub_drive_squad_replay),
        patch.object(gate, "ensure_production_repo_on_path", lambda: None),
    ):
        gate.run_g7_walk_forward(
            panel_start=datetime(2020, 1, 1, tzinfo=UTC),
            panel_end=datetime(2025, 1, 1, tzinfo=UTC),
            out_dir=None,
            tag="unit-default",
        )

    loaded_syms = tuple(c[0] for c in load_calls)
    assert loaded_syms == gate.SYMBOLS_G7, (
        f"default walk-forward loaded {loaded_syms!r} — must match "
        f"SYMBOLS_G7 = {gate.SYMBOLS_G7!r}"
    )


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def test_g7_dry_run_honours_custom_symbols(tmp_path):
    """Same symbols-override contract must hold for the dry-run entry
    point (Phase AC uses dry-run for the AC.0 feature-vector fixture
    setup on the reduced panel)."""
    stub_load, load_calls = _stub_load_bars_factory()
    with (
        patch.object(gate, "_load_production_bars", stub_load),
        patch.object(gate, "_drive_squad_replay", _stub_drive_squad_replay),
        patch.object(gate, "ensure_production_repo_on_path", lambda: None),
    ):
        gate.run_g7_dry_run(
            panel_start=datetime(2023, 1, 1, tzinfo=UTC),
            panel_end=datetime(2024, 12, 31, tzinfo=UTC),
            symbols=("NZDUSD",),
            out_dir=None,
            tag="unit-dry-nzd",
        )

    loaded_syms = [c[0] for c in load_calls]
    assert loaded_syms == ["NZDUSD"], (
        f"dry-run loaded {loaded_syms!r} — expected exactly (NZDUSD,)"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_g7_cli_symbols_arg_walk_forward(monkeypatch):
    """``--mode walk-forward --symbols EURUSD GBPUSD`` must be parsed
    and forwarded to ``run_g7_walk_forward``."""
    captured: dict[str, Any] = {}

    def _capture_walk_forward(**kwargs: Any):
        captured.update(kwargs)
        return None

    def _capture_dry_run(**kwargs: Any):
        raise AssertionError(
            "walk-forward CLI must not fall through to run_g7_dry_run"
        )

    monkeypatch.setattr(gate, "run_g7_walk_forward", _capture_walk_forward)
    monkeypatch.setattr(gate, "run_g7_dry_run", _capture_dry_run)

    rc = gate.main([
        "--mode", "walk-forward",
        "--symbols", "EURUSD", "GBPUSD",
        "--tag", "unit-cli-wf",
        "--out-dir", "/tmp/unit-cli-wf",
    ])
    assert rc == 0
    assert captured.get("symbols") == ("EURUSD", "GBPUSD"), (
        f"CLI passed symbols={captured.get('symbols')!r} — expected "
        "tuple ('EURUSD', 'GBPUSD')"
    )


def test_g7_cli_symbols_default_is_g7(monkeypatch):
    """No ``--symbols`` on the CLI must forward the default
    ``SYMBOLS_G7`` tuple, not ``None``."""
    captured: dict[str, Any] = {}

    def _capture_dry_run(**kwargs: Any):
        captured.update(kwargs)
        return None

    monkeypatch.setattr(gate, "run_g7_dry_run", _capture_dry_run)

    rc = gate.main([
        "--mode", "dry-run",
        "--tag", "unit-cli-default",
        "--out-dir", "/tmp/unit-cli-default",
    ])
    assert rc == 0
    assert captured.get("symbols") == gate.SYMBOLS_G7, (
        f"CLI default passed symbols={captured.get('symbols')!r} — "
        f"expected SYMBOLS_G7 = {gate.SYMBOLS_G7!r}"
    )
