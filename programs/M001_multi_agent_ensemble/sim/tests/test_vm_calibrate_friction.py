"""Structural tests for the VM-side friction-calibration script.

The script ships to run on the Windows VM; this Mac-side test suite
exercises three things so the structural plumbing doesn't drift:

1. **Module imports cleanly.** Catches accidental Windows-only deps or
   stray top-level side effects.
2. **`--dry-run` writes nothing.** The default output path is
   `sim/core/friction_calibration_2026-06.json`; the dry-run flag
   must leave the path absent (or untouched if it already exists).
3. **Empty log root → n_orders=0 per symbol, exit 0.** This is the
   deferred-data path documented in `sim/core/friction.py`; running
   the script on a host with no logs must return cleanly and not
   write a partial calibration file (writing zeros would silently
   mask the deferred path on the next sim run).
4. **Synthetic log root → file written, calibration parameters present.**
   Builds a tiny per-symbol log tree under `tmp_path`, runs the
   script with `--out tmp_path/cal.json`, and asserts the JSON is
   readable and carries the symbols we asked for.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def vm_calibrate():
    return importlib.import_module(
        "programs.M001_multi_agent_ensemble.scripts.vm_calibrate_friction"
    )


# ---------------------------------------------------------------------------
# Helpers — synthesise the production-style text log on disk
# ---------------------------------------------------------------------------

def _write_synthetic_log(sym_dir: Path, symbol: str) -> None:
    """Build a minimal day-log with 3 fills + 1 reject + 1 partial event."""
    log_path = sym_dir / f"{symbol}_2026-06-20.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "2026-06-20T10:00:00.000 [SIGNAL] {sym} H4 zone_d1_against LONG "
        "entry=1.08500 soft_sl=1.08300 tp=1.08900 conviction=0.70",
        "2026-06-20T10:00:00.200 [TRADE OPENED] {sym} H4 zone_d1_against LONG "
        "ticket=1 entry=1.08505 lots=0.10 soft_sl=1.08300 (20p) "
        "catastrophe_sl=1.08200 (30p) tp_mech=1.08900 (1.9R, +40p) "
        "risk=0.50%",
        "2026-06-20T11:00:00.000 [SIGNAL] {sym} H4 zone_d1_against LONG "
        "entry=1.08600 soft_sl=1.08400 tp=1.09000 conviction=0.70",
        "2026-06-20T11:00:00.300 [TRADE OPENED] {sym} H4 zone_d1_against LONG "
        "ticket=2 entry=1.08610 lots=0.10 soft_sl=1.08400 (20p) "
        "catastrophe_sl=1.08300 (30p) tp_mech=1.09000 (1.9R, +40p) "
        "risk=0.50%",
        "2026-06-20T12:00:00.000 [SIGNAL] {sym} H4 zone_d1_against LONG "
        "entry=1.08700 soft_sl=1.08500 tp=1.09100 conviction=0.70",
        "2026-06-20T12:00:00.500 [TRADE OPENED] {sym} H4 zone_d1_against LONG "
        "ticket=3 entry=1.08720 lots=0.10 soft_sl=1.08500 (20p) "
        "catastrophe_sl=1.08400 (30p) tp_mech=1.09100 (1.9R, +40p) "
        "risk=0.50%",
        "2026-06-20T13:00:00.000 [SIGNAL] {sym} H4 zone_d1_against SHORT "
        "entry=1.08800 soft_sl=1.09000 tp=1.08400 conviction=0.60",
        "2026-06-20T13:00:00.300 [ORDER REJECTED] {sym} H4 zone_d1_against — "
        "broker rejected (no quote)",
    ]
    log_path.write_text(
        "\n".join(line.format(sym=symbol) for line in lines) + "\n",
        encoding="utf-8",
    )
    (sym_dir / "near_misses").mkdir(parents=True, exist_ok=True)
    (sym_dir / "losses").mkdir(parents=True, exist_ok=True)
    (sym_dir / "ladders").mkdir(parents=True, exist_ok=True)


def _build_synthetic_log_root(root: Path, symbols=("EURUSD", "GBPUSD", "USDCAD")):
    for sym in symbols:
        _write_synthetic_log(root / sym, sym)


# ---------------------------------------------------------------------------
# Smoke / import
# ---------------------------------------------------------------------------

def test_module_imports(vm_calibrate):
    """Module imports without raising on a Mac host."""
    assert hasattr(vm_calibrate, "main")
    assert hasattr(vm_calibrate, "run")
    assert hasattr(vm_calibrate, "discover_log_root")
    assert hasattr(vm_calibrate, "build_parser")
    assert vm_calibrate.SYMBOLS == ("EURUSD", "GBPUSD", "USDCAD")
    # The well-known VM paths are pathlib.Path objects (no string roots).
    assert all(isinstance(p, Path) for p in vm_calibrate.CANDIDATE_LOG_ROOTS)


def test_argparser_accepts_dry_run_and_log_root(vm_calibrate):
    parser = vm_calibrate.build_parser()
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True
    args = parser.parse_args(["D:/TradingAgentLogs"])
    assert args.log_root == "D:/TradingAgentLogs"
    assert args.dry_run is False


# ---------------------------------------------------------------------------
# Path discovery
# ---------------------------------------------------------------------------

def test_discover_log_root_with_explicit_argv(vm_calibrate, tmp_path: Path):
    p, note = vm_calibrate.discover_log_root(str(tmp_path))
    assert p == tmp_path
    assert "explicit" in note


def test_discover_log_root_picks_first_existing(vm_calibrate, tmp_path: Path):
    existing = tmp_path / "alpha"
    existing.mkdir()
    missing = tmp_path / "beta"
    p, note = vm_calibrate.discover_log_root(
        None, candidates=[missing, existing, tmp_path / "gamma"],
    )
    assert p == existing
    assert "auto-detected" in note


def test_discover_log_root_falls_back_when_nothing_exists(
    vm_calibrate, tmp_path: Path,
):
    missing_a = tmp_path / "a"
    missing_b = tmp_path / "b"
    missing_c = tmp_path / "c"
    p, note = vm_calibrate.discover_log_root(
        None, candidates=[missing_a, missing_b, missing_c],
    )
    # Second candidate is the cross-platform fallback per spec.
    assert p == missing_b
    assert "deferred-data" in note


# ---------------------------------------------------------------------------
# Behaviour — empty log root → n_orders=0 across symbols
# ---------------------------------------------------------------------------

def test_run_with_empty_log_root_reports_zero_orders(
    vm_calibrate, tmp_path: Path,
):
    """Deferred-data path: every symbol comes back with n_orders=0
    and no file is written."""
    out = tmp_path / "out.json"
    results, summary, next_steps = vm_calibrate.run(
        explicit_log_root=str(tmp_path),
        out_path=out,
        dry_run=False,
    )
    assert set(results) == {"EURUSD", "GBPUSD", "USDCAD"}
    for sym, result in results.items():
        assert result.n_orders == 0, (
            f"{sym}: expected n_orders=0 on empty root, got {result.n_orders}"
        )
        assert result.notes  # deferred-data note must be present
    # File must NOT be written when every symbol has n_orders=0.
    assert not out.exists()
    # Deferred-data path: next-steps must explain *why* nothing was
    # written (so the user doesn't think the script silently failed).
    assert "deferred" in next_steps.lower() or "n_orders=0" in next_steps


def test_main_with_empty_log_root_exits_zero(vm_calibrate, tmp_path: Path, capsys):
    rc = vm_calibrate.main([
        str(tmp_path),
        "--out", str(tmp_path / "cal.json"),
        "--no-atr-parquet",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    # Paste-friendly per-symbol block present for all three symbols.
    for sym in ("EURUSD", "GBPUSD", "USDCAD"):
        assert sym in captured.out
    # The deferred-data note from `calibrate_against_fills` must appear.
    assert "n_orders" in captured.out


# ---------------------------------------------------------------------------
# Behaviour — --dry-run never writes
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write_file(vm_calibrate, tmp_path: Path):
    """Even when fills exist, --dry-run must leave `--out` absent."""
    log_root = tmp_path / "logs"
    log_root.mkdir()
    _build_synthetic_log_root(log_root)
    out = tmp_path / "cal_dry.json"
    results, summary, next_steps = vm_calibrate.run(
        explicit_log_root=str(log_root),
        out_path=out,
        dry_run=True,
        use_atr_parquet=False,
    )
    assert not out.exists()
    assert results["EURUSD"].n_orders >= 1
    assert "dry run" in next_steps.lower() or "no file written" in next_steps


# ---------------------------------------------------------------------------
# Behaviour — synthetic log root → JSON written with all symbols
# ---------------------------------------------------------------------------

def test_run_with_synthetic_log_root_writes_calibration(
    vm_calibrate, tmp_path: Path,
):
    log_root = tmp_path / "logs"
    log_root.mkdir()
    _build_synthetic_log_root(log_root)
    out = tmp_path / "cal.json"
    results, summary, next_steps = vm_calibrate.run(
        explicit_log_root=str(log_root),
        out_path=out,
        dry_run=False,
        use_atr_parquet=False,  # avoid touching production parquet in CI
    )
    assert out.exists(), "expected calibration JSON to be written"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert "calibrations" in payload
    for sym in ("EURUSD", "GBPUSD", "USDCAD"):
        assert sym in payload["calibrations"], f"missing {sym} in JSON"
        sym_entry = payload["calibrations"][sym]
        assert sym_entry["n_orders"] == 3
        assert sym_entry["n_rejections"] == 1
    # Aggregate summary contains per-symbol context the user can paste.
    assert "median_spread" in summary
    assert "p95_spread" in summary
    # Next-steps block carries the git commit instructions.
    assert "git add" in next_steps
    assert "git commit" in next_steps


def test_thin_symbol_emits_warning(vm_calibrate, tmp_path: Path):
    """3 orders/symbol < MIN_ORDERS_FOR_RELIABLE → warning lines present."""
    log_root = tmp_path / "logs"
    log_root.mkdir()
    _build_synthetic_log_root(log_root)
    out = tmp_path / "cal.json"
    _, summary, _ = vm_calibrate.run(
        explicit_log_root=str(log_root),
        out_path=out,
        dry_run=True,
        use_atr_parquet=False,
    )
    assert "thin" in summary.lower() or "n_orders=3" in summary
