"""Tests for the AC.0-v2 regression + verdict module.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        AMENDMENT_2026-07-20_ac0_methodology_switch.md §6 (statistic
        unchanged from AC.0-v1), §7 (bootstrap CI n=10 000 percentile),
        §11 (test surface).

Locked contract:

1. Given synthetic telemetry with a clean linear signal (β = +2),
   the OLS point estimate and bootstrap CI recover the signal within
   tolerance and mark the direction as "respected" iff the sign
   matches the §3 pre-locked map.
2. Given null telemetry (y independent of x), the pass criterion
   cleanly fails (most features have CI straddling 0).
3. Bootstrap is reproducible under a fixed seed (bit-identical CI
   bounds across two invocations).
4. Pass criterion is applied per PROTOCOL §5 exactly (unchanged by
   the amendment): ≥2 of 3 movables with a |β| CI lower > 0 AND
   ≥1 direction-respected pair.
5. A feature that clears the CI gate but violates the pre-locked
   direction is EXCLUDED from the direction-respected count (§5
   condition 2 requires the sign map).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim.analysis import (
    regress_ac0 as ra,
)

# ---------------------------------------------------------------------------
# Frozen §4 features (subset of the real pair_character.json values). Kept
# constant across all tests to make expected-β arithmetic obvious.
# ---------------------------------------------------------------------------

_FEATURES: dict[str, dict[str, float]] = {
    # Symbols spread across a wide x range so β can be estimated
    # cleanly on the small synthetic panel.
    "EURUSD": {
        "d1_ac1": 0.10,
        "h4_atr_percentile": 0.40,
        "max_session_impulse": 1.00,
        "d1_chop_fraction": 0.50,
    },
    "GBPUSD": {
        "d1_ac1": 0.20,
        "h4_atr_percentile": 0.30,
        "max_session_impulse": 2.00,
        "d1_chop_fraction": 0.40,
    },
    "USDCAD": {
        "d1_ac1": 0.30,
        "h4_atr_percentile": 0.20,
        "max_session_impulse": 3.00,
        "d1_chop_fraction": 0.30,
    },
    "AUDUSD": {
        "d1_ac1": 0.40,
        "h4_atr_percentile": 0.10,
        "max_session_impulse": 4.00,
        "d1_chop_fraction": 0.20,
    },
    "NZDUSD": {
        "d1_ac1": 0.50,
        "h4_atr_percentile": 0.05,
        "max_session_impulse": 5.00,
        "d1_chop_fraction": 0.10,
    },
}


def _write_telemetry(
    dir_: Path,
    agent_id: str,
    rows: list[dict],
    *,
    include_kunigami_unretired: bool = False,
    aggregator_arm: str = "phi41",
) -> Path:
    """Serialise a movable's synthetic ``per_pair_window_stats`` payload
    in the exact shape ``run_ac0_compute`` produces."""
    payload = {
        "agent_id": agent_id,
        "requested_symbols": ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "available_symbols": sorted({r["symbol"] for r in rows}),
        "skipped_symbols": [],
        "roster": [],
        "windows": [],
        "per_pair_window_stats": rows,
        "n_thoughts": 0,
        "n_proposals": 0,
        "n_trades_total": sum(int(r["n_trades"]) for r in rows),
        "n_trades_movable": sum(int(r["n_trades"]) for r in rows),
        "aggregator_arm": aggregator_arm,
        "include_kunigami_unretired": include_kunigami_unretired,
        "fired_at_utc": "2026-07-20T00:00:00+00:00",
    }
    p = dir_ / f"{agent_id}_walkforward.json"
    p.write_text(json.dumps(payload, indent=2))
    return p


def _write_pair_character(dir_: Path) -> Path:
    p = dir_ / "pair_character.json"
    p.write_text(json.dumps(_FEATURES, indent=2))
    return p


def _rows_from_signal(
    symbols: list[str],
    feature: str,
    *,
    beta: float,
    intercept: float = 0.5,
    n_windows: int = 4,
    n_trades_per_window: int = 5,
    noise_seed: int = 42,
) -> list[dict]:
    """Produce ``per_pair_window_stats`` rows where
    mean_tqs = intercept + beta * feature(symbol) + tiny noise. Noise is
    RNG-drawn but seed-pinned so the recovered β is deterministic."""
    import random
    rng = random.Random(noise_seed)
    rows = []
    for w in range(n_windows):
        for s in symbols:
            fval = _FEATURES[s][feature]
            y = intercept + beta * fval + rng.uniform(-0.001, 0.001)
            rows.append({
                "symbol": s,
                "window_idx": w,
                "n_trades": n_trades_per_window,
                "mean_tqs": y,
            })
    return rows


# ---------------------------------------------------------------------------
# 1. Positive signal
# ---------------------------------------------------------------------------

def test_regress_ac0_synthetic_positive_signal(tmp_path):
    """Chigiri × ``max_session_impulse`` has pre-locked direction ``+``.
    Feed a clean β = +2 signal; OLS must recover β ≈ +2, CI lower on
    |β| > 0, direction respected."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    rows = _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse",
        beta=2.0,
    )
    _write_telemetry(tel_dir, "chigiri_hyoma", rows)
    # Rin + Kunigami stay silent -- this test focuses on the recover-β
    # assertion, not the verdict aggregation.
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir,
        pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=500, rng_seed=20260720,
    )

    chi = report.regressions["chigiri_hyoma"].features["max_session_impulse"]
    assert chi.beta is not None
    assert 1.95 < chi.beta < 2.05, (
        f"expected β ≈ +2.0 on the clean synthetic signal, got β={chi.beta!r}"
    )
    assert chi.abs_ci_lower is not None and chi.abs_ci_lower > 0.5, (
        f"expected |β| CI lower well above 0, got {chi.abs_ci_lower!r}"
    )
    assert chi.direction_respected is True, (
        "β>0 with prelocked '+' must be direction-respected"
    )
    assert chi.n_unique_x == 5


# ---------------------------------------------------------------------------
# 2. Null signal
# ---------------------------------------------------------------------------

def test_regress_ac0_synthetic_null_signal(tmp_path):
    """Degenerate-x null: every movable has telemetry on only EURUSD
    (single unique x per feature). OLS β is mathematically undefined
    for a single-x fit; ``_bootstrap_beta_ci`` returns
    ``beta=None, abs_ci_lower=None``, which per §5 is NON-passing.
    This mirrors the exact failure pattern the sealed AC.0-v1 hit
    on Rin (unique_x=1) and Kunigami (unique_x=0).

    Rationale for degenerate-x rather than noisy-random-y: the frozen
    §5 semantic is literally ``abs_ci_lower > 0`` (see PROTOCOL.md §5
    + AMENDMENT §8's explicit re-lock). Because that criterion has no
    floor on the CI magnitude, floating-point noise from a
    finite-precision bootstrap on non-degenerate x can leave
    ``abs_ci_lower`` at ~1e-32 — technically "passing". The AC.0-v1
    sealed verdict shows this is a known lax edge of the semantic;
    the test picks a construction (degenerate x) that fails
    unambiguously through the ``beta=None`` code path."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    for aid in ra.MOVABLE_AGENTS:
        rows = []
        for w in range(4):
            rows.append({
                "symbol": "EURUSD",
                "window_idx": w,
                "n_trades": 5,
                "mean_tqs": 0.30 + 0.05 * w,
            })
        _write_telemetry(tel_dir, aid, rows)
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir,
        pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=200, rng_seed=20260720,
    )
    assert report.verdict == "FAIL", (
        f"degenerate-x null panel should FAIL AC.0 pass criterion; got "
        f"{report.verdict}. cond_1_met={report.condition_1_met}, "
        f"cond_2_met={report.condition_2_met}, "
        f"passing_directional={report.passing_directional_pairs}"
    )
    assert report.condition_1_met is False
    # Every fit must be degenerate (beta = None, abs_ci_lower = None).
    for aid, entry in report.regressions.items():
        for feat, fit in entry.features.items():
            assert fit.beta is None, (
                f"{aid} × {feat}: expected degenerate fit (single unique "
                f"x), got beta={fit.beta!r}"
            )
            assert fit.abs_ci_lower is None
            assert fit.degenerate_reason is not None


# ---------------------------------------------------------------------------
# 3. Bootstrap reproducibility
# ---------------------------------------------------------------------------

def test_regress_ac0_bootstrap_reproducibility(tmp_path):
    """Same seed → bit-identical CI bounds across two runs. Locks the
    seed-pinning contract of §7."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    rows = _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse", beta=2.0,
    )
    _write_telemetry(tel_dir, "chigiri_hyoma", rows)
    pc_path = _write_pair_character(tmp_path)

    r1 = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "r1.json",
        out_verdict=tmp_path / "v1.md",
        n_boot=300, rng_seed=20260720,
    )
    r2 = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "r2.json",
        out_verdict=tmp_path / "v2.md",
        n_boot=300, rng_seed=20260720,
    )
    for feat in ra.FEATURE_KEYS:
        f1 = r1.regressions["chigiri_hyoma"].features[feat]
        f2 = r2.regressions["chigiri_hyoma"].features[feat]
        assert f1.ci_lower == f2.ci_lower, (
            f"CI lower differs across runs on {feat}: {f1.ci_lower} vs "
            f"{f2.ci_lower} — seed pin broken"
        )
        assert f1.ci_upper == f2.ci_upper, (
            f"CI upper differs across runs on {feat}: {f1.ci_upper} vs "
            f"{f2.ci_upper} — seed pin broken"
        )


# ---------------------------------------------------------------------------
# 4. Pass criterion mechanics
# ---------------------------------------------------------------------------

def test_regress_ac0_pass_criterion_two_movables_pass(tmp_path):
    """Chigiri and Rin both get clean prelocked-direction signals; Kunigami
    gets pure noise. Expected: PASS (condition 1 met, condition 2 met)."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _write_telemetry(tel_dir, "chigiri_hyoma", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse", beta=+2.0,   # pre-locked '+'
    ))
    _write_telemetry(tel_dir, "itoshi_rin", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "h4_atr_percentile", beta=-2.0,     # pre-locked '-'
    ))
    # Kunigami: null noise.
    import random
    rng = random.Random(7)
    kun_rows = []
    for w in range(4):
        for s in ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"]:
            kun_rows.append({
                "symbol": s, "window_idx": w, "n_trades": 5,
                "mean_tqs": rng.uniform(-0.5, 0.5),
            })
    _write_telemetry(tel_dir, "kunigami_rensuke", kun_rows)
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=500, rng_seed=20260720,
    )
    assert report.verdict == "PASS", (
        f"expected PASS: 2 movables with strong signals; got "
        f"{report.verdict} — cond_1_met={report.condition_1_met}, "
        f"cond_2_met={report.condition_2_met}"
    )
    assert report.n_movables_passing >= 2
    assert report.condition_1_met is True
    assert report.condition_2_met is True


def test_regress_ac0_pass_criterion_one_movable_fails(tmp_path):
    """Only Chigiri has multi-x telemetry; Rin and Kunigami have
    single-symbol (degenerate) fits. Expected: FAIL (condition 1 not
    met — only 1 of 3 movables passes)."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _write_telemetry(tel_dir, "chigiri_hyoma", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse", beta=+2.0,
    ))
    for aid in ("itoshi_rin", "kunigami_rensuke"):
        rows = []
        for w in range(4):
            rows.append({
                "symbol": "EURUSD", "window_idx": w, "n_trades": 5,
                "mean_tqs": 0.30 + 0.05 * w,
            })
        _write_telemetry(tel_dir, aid, rows)
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=200, rng_seed=20260720,
    )
    assert report.verdict == "FAIL", (
        f"expected FAIL: only 1 movable with a signal; got {report.verdict}. "
        f"n_movables_passing={report.n_movables_passing}"
    )
    assert report.n_movables_passing == 1


# ---------------------------------------------------------------------------
# 5. Direction gate — sign wrong → does not count
# ---------------------------------------------------------------------------

def test_regress_ac0_direction_gate_rejects_wrong_sign(tmp_path):
    """Chigiri × ``max_session_impulse`` has pre-locked ``+``. Feed a
    β = -2 signal. The |β| CI must clear zero (magnitude is strong),
    but ``direction_respected`` must be ``False`` and the pair must NOT
    appear in ``passing_directional_pairs``."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _write_telemetry(tel_dir, "chigiri_hyoma", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse", beta=-2.0,
    ))
    _write_telemetry(tel_dir, "itoshi_rin", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "h4_atr_percentile", beta=-2.0,
    ))
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=500, rng_seed=20260720,
    )
    chi = report.regressions["chigiri_hyoma"].features["max_session_impulse"]
    assert chi.abs_ci_lower is not None and chi.abs_ci_lower > 0.5, (
        "|β| CI must still clear zero — wrong-sign signal is still a "
        "strong signal in magnitude"
    )
    assert chi.direction_respected is False, (
        "β<0 with prelocked '+' must NOT be direction-respected"
    )
    # Chigiri × max_session_impulse must NOT be in the passing-
    # directional list.
    for pair in report.passing_directional_pairs:
        assert not (
            pair["agent"] == "chigiri_hyoma"
            and pair["feature"] == "max_session_impulse"
        ), (
            "wrong-sign passing feature must be excluded from the "
            "direction-respected count"
        )


# ---------------------------------------------------------------------------
# 6. Zero-trades filter (amendment §8 sentinel)
# ---------------------------------------------------------------------------

def test_regress_ac0_drops_zero_trade_rows(tmp_path):
    """Rows with n_trades == 0 must be dropped (they are missing data, not
    a legitimate y = 0 observation). Verifies amendment §8 sentinel."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    rows = _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD"],
        "max_session_impulse", beta=+2.0, n_windows=2,
    )
    # Inject a zero-trades row that would ruin the fit if not dropped.
    rows.append({
        "symbol": "AUDUSD", "window_idx": 0,
        "n_trades": 0, "mean_tqs": 999.0,
    })
    _write_telemetry(tel_dir, "chigiri_hyoma", rows)
    pc_path = _write_pair_character(tmp_path)

    report = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=tmp_path / "reg.json",
        out_verdict=tmp_path / "vd.md",
        n_boot=200, rng_seed=20260720,
    )
    chi = report.regressions["chigiri_hyoma"].features["max_session_impulse"]
    assert 1.95 < (chi.beta or 0.0) < 2.05, (
        f"β={chi.beta!r} — zero-trade row was NOT dropped; the 999.0 y "
        "outlier corrupted the fit"
    )
    # Explicit: no observation on AUDUSD.
    assert all(o.symbol != "AUDUSD" for o in chi.observations)


# ---------------------------------------------------------------------------
# 7. Missing movable telemetry
# ---------------------------------------------------------------------------

def test_regress_ac0_missing_movable_marks_as_non_passing(tmp_path, caplog):
    """If one movable's <agent>_walkforward.json is missing, it counts
    as non-passing (§5 condition 1). Verdict must FAIL when 2+ movables
    are missing."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _write_telemetry(tel_dir, "chigiri_hyoma", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD"],
        "max_session_impulse", beta=+2.0,
    ))
    # Rin + Kunigami absent.
    pc_path = _write_pair_character(tmp_path)

    with caplog.at_level("WARNING"):
        report = ra.regress_ac0(
            telemetry_dir=tel_dir, pair_character_path=pc_path,
            out_regression=tmp_path / "reg.json",
            out_verdict=tmp_path / "vd.md",
            n_boot=200, rng_seed=20260720,
        )
    assert report.verdict == "FAIL"
    assert "itoshi_rin" in caplog.text
    assert "kunigami_rensuke" in caplog.text
    # Regression payload only contains chigiri.
    assert set(report.regressions.keys()) == {"chigiri_hyoma"}


# ---------------------------------------------------------------------------
# 8. Output schema
# ---------------------------------------------------------------------------

def test_regress_ac0_writes_json_and_md(tmp_path):
    """Verify machine + human-readable outputs both land on disk with
    the expected top-level keys, and the JSON round-trips."""
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _write_telemetry(tel_dir, "chigiri_hyoma", _rows_from_signal(
        ["EURUSD", "GBPUSD", "USDCAD"],
        "max_session_impulse", beta=+2.0, n_windows=2,
    ))
    pc_path = _write_pair_character(tmp_path)
    reg_path = tmp_path / "sub" / "reg.json"
    vd_path = tmp_path / "sub" / "vd.md"

    report = ra.regress_ac0(
        telemetry_dir=tel_dir, pair_character_path=pc_path,
        out_regression=reg_path, out_verdict=vd_path,
        n_boot=200, rng_seed=20260720,
    )
    assert reg_path.exists() and vd_path.exists()
    payload = json.loads(reg_path.read_text())
    for key in ("verdict", "regressions", "pair_character_source",
                "telemetry_dir", "n_bootstrap", "rng_seed",
                "fired_at_utc"):
        assert key in payload, f"regression JSON missing key {key!r}"
    assert payload["verdict"]["verdict"] == report.verdict
    md = vd_path.read_text()
    assert "AC.0-v2 verdict" in md
    assert "chigiri_hyoma" in md
    assert "Pass criterion" in md


# ---------------------------------------------------------------------------
# 9. Guardrail: missing telemetry dir / pair_character
# ---------------------------------------------------------------------------

def test_regress_ac0_raises_on_missing_pair_character(tmp_path):
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="pair_character.json"):
        ra.regress_ac0(
            telemetry_dir=tel_dir,
            pair_character_path=tmp_path / "does_not_exist.json",
            out_regression=tmp_path / "r.json",
            out_verdict=tmp_path / "v.md",
        )


def test_regress_ac0_raises_on_missing_telemetry_dir(tmp_path):
    pc_path = _write_pair_character(tmp_path)
    with pytest.raises(FileNotFoundError, match="telemetry dir"):
        ra.regress_ac0(
            telemetry_dir=tmp_path / "does_not_exist",
            pair_character_path=pc_path,
            out_regression=tmp_path / "r.json",
            out_verdict=tmp_path / "v.md",
        )
