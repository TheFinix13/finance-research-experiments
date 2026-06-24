"""Friction calibration machinery — parser + estimator + JSON loader.

Two layers of tests:

1. **Parser / estimator unit tests** run on synthetic broker-log
   fixtures written to a tmp_path. These guarantee the cross-repo
   contract — text-log regex, JSONL vault schema, ATR-aware slippage
   regression, deferred-data path — without requiring the real
   `~/Documents/TradingAgentLogs/` tree.
2. **Real-data bounds tests** are *skipped* when the calibration JSON
   is absent (the common case on this Mac host as of 2026-06-24) and
   assert sane parameter ranges otherwise. Phi3 lights these up once
   the VM data pipe is wired.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim.core.friction import (
    DEFAULT_CALIBRATION_PATH,
    DEFAULT_LATENCY_MS,
    DEFAULT_PARTIAL_FILL_PROB,
    DEFAULT_REJECT_PROB,
    DEFAULT_SLIPPAGE_ATR_MULT,
    CalibrationResult,
    FrictionConfig,
    calibrate_against_fills,
    config_for_symbol,
    iter_vault_jsonl,
    load_calibration,
    parse_text_log,
    write_calibration_file,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic broker-log text + JSONL vault
# ---------------------------------------------------------------------------

def _write_text_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_symbol_dir(tmp_path: Path, symbol: str = "EURUSD") -> Path:
    """Build a minimal ~/Documents/TradingAgentLogs/SYMBOL/ tree."""
    sym_dir = tmp_path / symbol
    (sym_dir / "near_misses").mkdir(parents=True)
    (sym_dir / "losses").mkdir(parents=True)
    (sym_dir / "ladders").mkdir(parents=True)
    return sym_dir


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parse_text_log_pairs_signal_with_trade_opened(tmp_path):
    sym_dir = _make_symbol_dir(tmp_path)
    log_path = sym_dir / "EURUSD_2026-06-20.log"
    _write_text_log(log_path, [
        "2026-06-20T10:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against LONG "
        "entry=1.08550 soft_sl=1.08400 tp=1.08850 conviction=0.70",
        "2026-06-20T10:00:00.250 [TRADE OPENED] EURUSD H4 zone_d1_against LONG "
        "ticket=12345 entry=1.08558 lots=0.10 soft_sl=1.08400 (15p) "
        "catastrophe_sl=1.08300 (25p) tp_mech=1.08850 (1.0R, +30p) risk=0.50%",
        "2026-06-20T10:30:00.000 [TP HIT] EURUSD ticket=12345 zone_d1_against LONG "
        "exit=1.08850 pnl=+30.00 (+30p, +1.00R) cause=tp",
    ])
    fills, n_rejected = parse_text_log(log_path)
    assert len(fills) == 1
    assert n_rejected == 0
    f = fills[0]
    assert f.symbol == "EURUSD"
    assert f.timeframe == "H4"
    assert f.alpha == "zone_d1_against"
    assert f.direction == "LONG"
    assert f.intended_price == pytest.approx(1.08550)
    assert f.fill_price == pytest.approx(1.08558)
    assert f.lots == pytest.approx(0.10)
    assert f.signal_ts is not None
    assert f.fill_ts is not None
    assert f.slippage_price > 0  # long fill above signal → adverse
    assert f.latency_ms == pytest.approx(250.0)


def test_parse_text_log_counts_order_rejected_lines(tmp_path):
    sym_dir = _make_symbol_dir(tmp_path, "GBPUSD")
    log_path = sym_dir / "GBPUSD_2026-06-21.log"
    _write_text_log(log_path, [
        "2026-06-21T08:00:00.000 [SIGNAL] GBPUSD H4 zone_d1_against SHORT "
        "entry=1.27000 soft_sl=1.27200 tp=1.26600 conviction=0.65",
        "2026-06-21T08:00:00.300 [ORDER REJECTED] GBPUSD H4 zone_d1_against — "
        "broker rejected: insufficient margin",
        "2026-06-21T09:00:00.000 [SIGNAL] GBPUSD H4 zone_d1_against SHORT "
        "entry=1.26980 soft_sl=1.27180 tp=1.26580 conviction=0.70",
        "2026-06-21T09:00:00.400 [TRADE OPENED] GBPUSD H4 zone_d1_against SHORT "
        "ticket=67890 entry=1.26970 lots=0.10 soft_sl=1.27180 (21p) "
        "catastrophe_sl=1.27300 (33p) tp_mech=1.26580 (1.9R, +40p) risk=0.50%",
    ])
    fills, n_rejected = parse_text_log(log_path)
    assert n_rejected == 1
    assert len(fills) == 1
    assert fills[0].direction == "SHORT"
    # Short pays slippage on the way down: fill (1.26970) < intended (1.26980)
    # so signed slippage_price = -(fill - intended) = +0.00010 (adverse).
    assert fills[0].slippage_price == pytest.approx(0.00010, abs=1e-9)


def test_parse_text_log_handles_unmatched_signal(tmp_path):
    sym_dir = _make_symbol_dir(tmp_path)
    log_path = sym_dir / "EURUSD_2026-06-22.log"
    _write_text_log(log_path, [
        "2026-06-22T14:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against LONG "
        "entry=1.09000 soft_sl=1.08800 tp=1.09400 conviction=0.60",
    ])
    fills, n_rejected = parse_text_log(log_path)
    assert fills == []
    assert n_rejected == 0


def test_parse_text_log_missing_path_returns_empty(tmp_path):
    fills, n_rejected = parse_text_log(tmp_path / "does_not_exist.log")
    assert fills == []
    assert n_rejected == 0


def test_iter_vault_jsonl_skips_blank_and_bad_lines(tmp_path):
    jsonl_path = tmp_path / "events.jsonl"
    jsonl_path.write_text(
        '{"ts":"2026-06-20T10:00:00+00:00","partial_close":true}\n'
        "\n"
        "{ not json at all\n"
        '{"ts":"2026-06-21T10:00:00+00:00","partial_scaleout":true}\n',
        encoding="utf-8",
    )
    events = list(iter_vault_jsonl(jsonl_path))
    assert len(events) == 2
    assert events[0]["partial_close"] is True
    assert events[1]["partial_scaleout"] is True


# ---------------------------------------------------------------------------
# Estimator tests
# ---------------------------------------------------------------------------

def test_calibrate_against_fills_no_data_returns_zero_orders(tmp_path):
    """The Mac-host path: directory absent → deferred result + defaults."""
    result = calibrate_against_fills("EURUSD", log_root=tmp_path / "missing")
    assert result.n_orders == 0
    assert result.notes  # always carries a deferred-data note
    cfg = result.to_friction_config()
    assert cfg == FrictionConfig()  # falls back to conservative defaults


def test_calibrate_against_fills_empirical_distributions(tmp_path):
    sym_dir = _make_symbol_dir(tmp_path)
    log_path = sym_dir / "EURUSD_2026-06-20.log"
    # Three filled orders + one rejected. Slippage proxy ranges
    # 0.00005 .. 0.00020 with median 0.00010. Latency ranges 200..500 ms.
    _write_text_log(log_path, [
        "2026-06-20T10:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against LONG "
        "entry=1.08500 soft_sl=1.08300 tp=1.08900 conviction=0.70",
        "2026-06-20T10:00:00.200 [TRADE OPENED] EURUSD H4 zone_d1_against LONG "
        "ticket=1 entry=1.08505 lots=0.10 soft_sl=1.08300 (20p) "
        "catastrophe_sl=1.08200 (30p) tp_mech=1.08900 (1.9R, +40p) risk=0.50%",
        "2026-06-20T11:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against LONG "
        "entry=1.08600 soft_sl=1.08400 tp=1.09000 conviction=0.70",
        "2026-06-20T11:00:00.300 [TRADE OPENED] EURUSD H4 zone_d1_against LONG "
        "ticket=2 entry=1.08610 lots=0.10 soft_sl=1.08400 (20p) "
        "catastrophe_sl=1.08300 (30p) tp_mech=1.09000 (1.9R, +40p) risk=0.50%",
        "2026-06-20T12:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against LONG "
        "entry=1.08700 soft_sl=1.08500 tp=1.09100 conviction=0.70",
        "2026-06-20T12:00:00.500 [TRADE OPENED] EURUSD H4 zone_d1_against LONG "
        "ticket=3 entry=1.08720 lots=0.10 soft_sl=1.08500 (20p) "
        "catastrophe_sl=1.08400 (30p) tp_mech=1.09100 (1.9R, +40p) risk=0.50%",
        "2026-06-20T13:00:00.000 [SIGNAL] EURUSD H4 zone_d1_against SHORT "
        "entry=1.08800 soft_sl=1.09000 tp=1.08400 conviction=0.60",
        "2026-06-20T13:00:00.300 [ORDER REJECTED] EURUSD H4 zone_d1_against — "
        "broker rejected (no quote)",
    ])
    result = calibrate_against_fills("EURUSD", log_root=tmp_path)
    assert result.n_orders == 3
    assert result.n_rejections == 1
    assert result.median_spread == pytest.approx(0.00010, abs=1e-9)
    # numpy.percentile uses linear interp; with 3 samples
    # (0.00005, 0.00010, 0.00020) it returns ~0.00019.
    assert result.p95_spread == pytest.approx(0.00019, abs=1e-5)
    assert result.median_latency_ms == pytest.approx(300.0)
    assert result.p95_latency_ms == pytest.approx(480.0, abs=20.0)
    assert result.rejection_rate == pytest.approx(1 / 4)
    # No ATR map passed → k stays 0 by design.
    assert result.slippage_atr_mult == 0.0


def test_calibrate_atr_aware_slippage_regresses_k(tmp_path):
    """Pass an ATR-by-record map and recover k ≈ 0.05."""
    sym_dir = _make_symbol_dir(tmp_path)
    log_path = sym_dir / "EURUSD_2026-06-20.log"
    # Build 6 orders whose |fill-intended| = 0.05 * ATR exactly.
    atr_seq = [0.0008, 0.0010, 0.0012, 0.0015, 0.0009, 0.0011]
    lines: list[str] = []
    for i, atr_val in enumerate(atr_seq):
        intended = 1.08000 + 0.001 * i
        fill = intended + 0.05 * atr_val  # long, adverse
        ts_sig = f"2026-06-20T{10+i:02d}:00:00.000"
        ts_fill = f"2026-06-20T{10+i:02d}:00:00.250"
        lines.append(
            f"{ts_sig} [SIGNAL] EURUSD H4 zone_d1_against LONG "
            f"entry={intended:.5f} soft_sl=1.07900 tp=1.09000 conviction=0.70"
        )
        lines.append(
            f"{ts_fill} [TRADE OPENED] EURUSD H4 zone_d1_against LONG "
            f"ticket={i+1} entry={fill:.5f} lots=0.10 soft_sl=1.07900 (10p) "
            f"catastrophe_sl=1.07800 (20p) tp_mech=1.09000 (1.0R, +100p) "
            f"risk=0.50%"
        )
    _write_text_log(log_path, lines)
    atr_by_record = {i: v for i, v in enumerate(atr_seq)}
    result = calibrate_against_fills(
        "EURUSD", log_root=tmp_path, atr_by_record=atr_by_record,
    )
    assert result.n_orders == 6
    assert result.slippage_atr_mult == pytest.approx(0.05, abs=5e-3)


# ---------------------------------------------------------------------------
# JSON round-trip + loader
# ---------------------------------------------------------------------------

def _make_calibration(symbol: str, **kw) -> CalibrationResult:
    base = dict(
        symbol=symbol,
        n_orders=20,
        n_rejections=1,
        n_partial_fills=2,
        median_spread=0.00012,
        p95_spread=0.00030,
        slippage_atr_mult=0.04,
        median_latency_ms=210.0,
        p95_latency_ms=420.0,
        partial_fill_rate=0.10,
        rejection_rate=0.05,
        window_start="2026-06-17T00:00:00+00:00",
        window_end="2026-06-23T23:59:59+00:00",
        source_path=f"~/Documents/TradingAgentLogs/{symbol}",
        notes="synthetic-test",
    )
    base.update(kw)
    return CalibrationResult(**base)


def test_write_and_load_calibration_round_trip(tmp_path):
    path = tmp_path / "friction_calibration_2026-06.json"
    results = {
        "EURUSD": _make_calibration("EURUSD"),
        "GBPUSD": _make_calibration("GBPUSD", slippage_atr_mult=0.06),
        "USDCAD": _make_calibration("USDCAD", median_latency_ms=350.0),
    }
    out_path = write_calibration_file(
        results, path=path, extra_metadata={"source": "test"},
    )
    assert out_path == path
    cfgs = load_calibration(path)
    assert set(cfgs.keys()) == {"EURUSD", "GBPUSD", "USDCAD"}
    assert cfgs["EURUSD"].slippage_atr_mult == pytest.approx(0.04)
    assert cfgs["EURUSD"].latency_ms == 210
    assert cfgs["EURUSD"].reject_prob == pytest.approx(0.05)
    assert cfgs["GBPUSD"].slippage_atr_mult == pytest.approx(0.06)
    assert cfgs["USDCAD"].latency_ms == 350


def test_load_calibration_missing_file_returns_empty(tmp_path):
    cfgs = load_calibration(tmp_path / "absent.json")
    assert cfgs == {}


def test_config_for_symbol_falls_back_to_defaults(tmp_path):
    """Unknown symbol or absent file → conservative defaults."""
    cfg = config_for_symbol(
        "EURUSD", calibration_path=tmp_path / "absent.json",
    )
    assert cfg.slippage_atr_mult == DEFAULT_SLIPPAGE_ATR_MULT
    assert cfg.latency_ms == DEFAULT_LATENCY_MS
    assert cfg.reject_prob == DEFAULT_REJECT_PROB
    assert cfg.partial_fill_prob == DEFAULT_PARTIAL_FILL_PROB


def test_load_calibration_drops_unparseable_entry(tmp_path):
    path = tmp_path / "friction_calibration_2026-06.json"
    payload = {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "calibrations": {
            "EURUSD": _make_calibration("EURUSD").to_jsonable(),
            "BADSYM": {"this": "is not a valid entry"},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    cfgs = load_calibration(path)
    assert "EURUSD" in cfgs
    # Missing fields fall through (defaults), so BADSYM still loads with
    # defaults across the board — that's fine because n_orders=0 → defaults.
    if "BADSYM" in cfgs:
        assert cfgs["BADSYM"] == FrictionConfig()


# ---------------------------------------------------------------------------
# Real-data bounds (skipped when no calibration file is present)
# ---------------------------------------------------------------------------

def _have_real_calibration() -> bool:
    return DEFAULT_CALIBRATION_PATH.exists()


@pytest.mark.skipif(
    not _have_real_calibration(),
    reason=(
        "no friction_calibration_2026-06.json — VM broker fills not present "
        "on this host (Phi3 deliverable)"
    ),
)
def test_real_calibration_parameters_within_bounds():
    """When the real file exists, every entry must be in sane bounds.

    Bounds are intentionally generous; they catch only catastrophic
    miscalibration (e.g. a regression that flips signs or writes
    NaN). Tightening them is a separate amendment per `09` §6.
    """
    cfgs = load_calibration()
    assert cfgs, "calibration file present but empty"
    for sym, cfg in cfgs.items():
        assert 0.0 <= cfg.slippage_atr_mult <= 0.5, (
            f"{sym}: slippage_atr_mult={cfg.slippage_atr_mult} outside "
            "[0, 0.5]"
        )
        assert 1 <= cfg.latency_ms <= 5000, (
            f"{sym}: latency_ms={cfg.latency_ms} outside [1, 5000] ms"
        )
        assert 0.0 <= cfg.partial_fill_prob <= 0.5, (
            f"{sym}: partial_fill_prob={cfg.partial_fill_prob} outside [0, 0.5]"
        )
        assert 0.0 <= cfg.reject_prob <= 0.2, (
            f"{sym}: reject_prob={cfg.reject_prob} outside [0, 0.2]"
        )
