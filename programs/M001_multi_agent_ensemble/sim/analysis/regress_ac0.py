"""AC.0-v2 regression + verdict rendering.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        AMENDMENT_2026-07-20_ac0_methodology_switch.md §6, §7, §9

What this does
--------------

Consumes the per-movable-agent walk-forward telemetry produced by
``sim/scoring/run_ac0_compute.py`` (one ``<agent>_walkforward.json``
per movable), joins it with the FROZEN ``pair_character.json`` from
the original AC.0 fire (`PROTOCOL.md` §4), and runs one univariate
OLS regression per movable × feature with a percentile bootstrap
95 % CI (n = 10 000 by default, window-level resample, seed pinned).

Applies the PROTOCOL §5 AC.0 pass criterion unchanged:

1. ≥ 2 of {Chigiri, Rin, Kunigami} produce a feature whose bootstrap
   95 % CI lower bound on |β| > 0.
2. ≥ 1 of those (agent, feature) pairs respects the §3 pre-locked
   direction (§3 map unchanged by the amendment).

Emits two artefacts:
- ``ac0_regression_v2.json`` — machine-readable full regression output
  (β / CI / R² / n_unique_x per movable × feature + per-observation
  rows).
- ``ac0_verdict_v2.md`` — narrative pass/fail + coverage tables +
  per-agent tables + verdict language.

Statistical honesty guarantees
------------------------------

- The OLS + bootstrap primitives (``_ols_beta``, ``_bootstrap_beta_ci``)
  are copies of the sealed-verdict logic from
  ``experiments/phase_ac_pitch_assignment/run_ac0_regression.py``.
  This is deliberate: the sealed AC.0-v1 verdict must be reproducible
  from the frozen banked telemetry using the same primitives, and the
  AC.0-v2 verdict must be a strict methodology switch on the y-axis
  only. Any drift between the two would break the amendment §6 lock.
- The frozen-file drift sentinel (amendment §8) applies: if the caller
  hands us a ``pair_character.json`` whose values differ from the
  sealed file bytewise (feature values only), we refuse to run.
- The random seed is pinned to ``20260720`` by default; a test locks
  reproducibility.
- Bootstrap resamples that collapse to a single unique x are re-drawn
  (up to 10 attempts per resample) rather than silently dropped; the
  count of valid resamples is recorded per fit.

CLI
---

::

    PYTHONPATH=../multi-pair-trading-agent:. \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.analysis.regress_ac0 \\
        --telemetry-dir programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/ac0_compute/ \\
        --pair-character programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/pair_character.json \\
        --out-regression programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/ac0_regression_v2.json \\
        --out-verdict programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/ac0_verdict_v2.md
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Locked constants (mirror the AC.0-v1 module; do NOT change without amend)
# ---------------------------------------------------------------------------

MOVABLE_AGENTS: tuple[str, ...] = (
    "chigiri_hyoma", "itoshi_rin", "kunigami_rensuke",
)

FEATURE_KEYS: tuple[str, ...] = (
    "d1_ac1",
    "h4_atr_percentile",
    "max_session_impulse",
    "d1_chop_fraction",
    # "dxy_beta" — DROPPED per §4 fallback (DXY not in production parquet).
)

# Pre-locked directional priors per PROTOCOL §3. Unchanged by the amendment.
PRELOCKED_DIRECTIONS: dict[tuple[str, str], str] = {
    ("chigiri_hyoma", "max_session_impulse"): "+",
    ("chigiri_hyoma", "d1_chop_fraction"): "-",
    ("itoshi_rin", "h4_atr_percentile"): "-",
    ("kunigami_rensuke", "d1_chop_fraction"): "+",
}

DEFAULT_N_BOOT: int = 10_000
DEFAULT_SEED: int = 20260720


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    symbol: str
    window_idx: int
    x_feature: float
    y_mean_tqs: float
    n_trades: int


@dataclass
class FeatureFit:
    """One movable × one feature regression result."""

    n: int
    beta: Optional[float]
    r2: Optional[float]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    abs_ci_lower: Optional[float]
    n_boot_valid: int
    n_observations: int
    n_unique_x: int
    prelocked_direction: Optional[str]
    direction_respected: Optional[bool]
    degenerate_reason: Optional[str]
    observations: list[Observation]

    def to_jsonable(self) -> dict:
        return {
            "n": int(self.n),
            "beta": None if self.beta is None else float(self.beta),
            "r2": None if self.r2 is None else float(self.r2),
            "ci_lower": None if self.ci_lower is None else float(self.ci_lower),
            "ci_upper": None if self.ci_upper is None else float(self.ci_upper),
            "abs_ci_lower": (
                None if self.abs_ci_lower is None
                else float(self.abs_ci_lower)
            ),
            "n_boot_valid": int(self.n_boot_valid),
            "n_observations": int(self.n_observations),
            "n_unique_x": int(self.n_unique_x),
            "prelocked_direction": self.prelocked_direction,
            "direction_respected": self.direction_respected,
            "degenerate_reason": self.degenerate_reason,
            "observations": [asdict(o) for o in self.observations],
        }


@dataclass
class MovableAgentRegressions:
    agent_id: str
    symbols_present: tuple[str, ...]
    n_symbols_present: int
    n_windows_present: int
    n_trades_movable: int
    features: dict[str, FeatureFit]
    include_kunigami_unretired: Optional[bool] = None
    aggregator_arm: Optional[str] = None
    telemetry_source: Optional[str] = None

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "symbols_present": list(self.symbols_present),
            "n_symbols_present": int(self.n_symbols_present),
            "n_windows_present": int(self.n_windows_present),
            "n_trades_movable": int(self.n_trades_movable),
            "include_kunigami_unretired": self.include_kunigami_unretired,
            "aggregator_arm": self.aggregator_arm,
            "telemetry_source": self.telemetry_source,
            "features": {
                fk: fit.to_jsonable() for fk, fit in self.features.items()
            },
        }


@dataclass
class Ac0VerdictReport:
    verdict: str                          # "PASS" or "FAIL"
    n_movables_passing: int
    passing_features_per_movable: dict[str, list[str]]
    passing_directional_pairs: list[dict]  # [{agent, feature}]
    condition_1_met: bool
    condition_2_met: bool
    regressions: dict[str, MovableAgentRegressions]
    pair_character_source: str
    telemetry_dir: str
    n_bootstrap: int
    rng_seed: int
    fired_at_utc: str = ""

    def to_jsonable(self) -> dict:
        return {
            "verdict": {
                "verdict": self.verdict,
                "condition_1_two_of_three_movables_with_ci_lower_on_abs_beta_gt_0": {
                    "required": True,
                    "observed": self.condition_1_met,
                    "n_movables_passing": self.n_movables_passing,
                    "per_agent_passing_features": self.passing_features_per_movable,
                },
                "condition_2_at_least_one_direction_respected": {
                    "required": True,
                    "observed": self.condition_2_met,
                    "passing_directional_pairs": self.passing_directional_pairs,
                },
            },
            "regressions": {
                "movable_agents": {
                    aid: r.to_jsonable() for aid, r in self.regressions.items()
                },
            },
            "pair_character_source": self.pair_character_source,
            "telemetry_dir": self.telemetry_dir,
            "n_bootstrap": int(self.n_bootstrap),
            "rng_seed": int(self.rng_seed),
            "fired_at_utc": self.fired_at_utc,
        }


# ---------------------------------------------------------------------------
# Loaders (with frozen-file drift sentinel)
# ---------------------------------------------------------------------------

def load_pair_character(path: Path) -> dict[str, dict[str, Any]]:
    """Load the frozen ``pair_character.json``. Returns dict[symbol -> features].

    Symbols with an ``error`` key (e.g. NEEDS CACHE PULL) are kept in
    the map but will be filtered out at regression time because their
    feature values are strings, not floats. This mirrors the AC.0-v1
    behaviour so v1 and v2 share the same x-axis semantics.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"AC.0-v2: pair_character.json not found at {path}. Amendment "
            "§4 requires the frozen file from the sealed AC.0-v1 fire."
        )
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            f"AC.0-v2: pair_character.json at {path} is empty or not a dict"
        )
    return raw


def load_movable_telemetry(
    telemetry_dir: Path,
    movable_agents: tuple[str, ...] = MOVABLE_AGENTS,
) -> dict[str, dict[str, Any]]:
    """Load ``<agent>_walkforward.json`` per movable from ``telemetry_dir``.

    Returns dict[agent_id -> parsed JSON payload]. Missing files for a
    movable are surfaced as a WARNING and that movable's regression
    will fail (§5 condition 1 counts it as non-passing) rather than
    silently succeeding on an incomplete study.
    """
    if not telemetry_dir.exists() or not telemetry_dir.is_dir():
        raise FileNotFoundError(
            f"AC.0-v2: telemetry dir not found at {telemetry_dir}. Run "
            "sim/scoring/run_ac0_compute.py first (amendment §10 Step 3b)."
        )
    out: dict[str, dict[str, Any]] = {}
    for aid in movable_agents:
        path = telemetry_dir / f"{aid}_walkforward.json"
        if not path.exists():
            log.warning(
                "AC.0-v2: missing telemetry for %s at %s -- regression "
                "will treat this movable as non-passing", aid, path,
            )
            continue
        try:
            out[aid] = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"AC.0-v2: telemetry file for {aid} is invalid JSON: {exc}"
            ) from exc
    return out


# ---------------------------------------------------------------------------
# OLS + bootstrap (mirror of AC.0-v1 primitives, do NOT drift)
# ---------------------------------------------------------------------------

def _ols_beta(xs: list[float], ys: list[float]) -> Optional[tuple[float, float]]:
    """Univariate OLS: returns (β, R²). Requires >1 unique x."""
    n = len(xs)
    if n < 2 or len(set(xs)) < 2:
        return None
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    num = sum((xs[i] - x_bar) * (ys[i] - y_bar) for i in range(n))
    den_x = sum((xs[i] - x_bar) ** 2 for i in range(n))
    if den_x == 0:
        return None
    beta = num / den_x
    ss_res = sum(
        (ys[i] - (y_bar + beta * (xs[i] - x_bar))) ** 2 for i in range(n)
    )
    ss_tot = sum((ys[i] - y_bar) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return (beta, r2)


def _bootstrap_beta_ci(
    xs: list[float],
    ys: list[float],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    alpha: float = 0.05,
    seed: int = DEFAULT_SEED,
) -> FeatureFit:
    """Percentile bootstrap CI on β. Resamples (x, y) pairs with
    replacement. Degenerate resamples (single-x) are re-drawn up to
    10 times per outer draw; if all attempts collapse, that draw is
    skipped and ``n_boot_valid`` reflects the shortfall.
    """
    rng = random.Random(seed)
    n = len(xs)
    unique_x = len(set(xs))
    point = _ols_beta(xs, ys)
    if point is None:
        return FeatureFit(
            n=n, beta=None, r2=None,
            ci_lower=None, ci_upper=None, abs_ci_lower=None,
            n_boot_valid=0,
            n_observations=n, n_unique_x=unique_x,
            prelocked_direction=None,
            direction_respected=None,
            degenerate_reason=(
                f"n={n}, unique_x={unique_x} — need n>=2 with >1 unique "
                "x-value for OLS β."
            ),
            observations=[],
        )
    beta_hat, r2_hat = point
    betas: list[float] = []
    for _ in range(n_boot):
        for _try in range(10):
            idx = [rng.randrange(n) for _ in range(n)]
            xr = [xs[i] for i in idx]
            yr = [ys[i] for i in idx]
            fit = _ols_beta(xr, yr)
            if fit is not None:
                betas.append(fit[0])
                break
    if not betas:
        return FeatureFit(
            n=n, beta=beta_hat, r2=r2_hat,
            ci_lower=None, ci_upper=None, abs_ci_lower=None,
            n_boot_valid=0,
            n_observations=n, n_unique_x=unique_x,
            prelocked_direction=None,
            direction_respected=None,
            degenerate_reason=(
                "All bootstrap resamples collapsed to a single unique x "
                "— CI undefined."
            ),
            observations=[],
        )
    betas.sort()
    lo = betas[int(alpha / 2 * len(betas))]
    hi = betas[int((1 - alpha / 2) * len(betas))]
    abs_betas = sorted(abs(b) for b in betas)
    abs_lo = abs_betas[int(alpha / 2 * len(abs_betas))]
    return FeatureFit(
        n=n, beta=beta_hat, r2=r2_hat,
        ci_lower=lo, ci_upper=hi, abs_ci_lower=abs_lo,
        n_boot_valid=len(betas),
        n_observations=n, n_unique_x=unique_x,
        prelocked_direction=None,
        direction_respected=None,
        degenerate_reason=None,
        observations=[],
    )


# ---------------------------------------------------------------------------
# Regression + verdict
# ---------------------------------------------------------------------------

def _rows_from_telemetry(
    telemetry_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert one movable's ``<agent>_walkforward.json`` payload into a
    flat list of {symbol, window_idx, mean_tqs, n_trades} rows.

    Rows with ``n_trades == 0`` are DROPPED (per amendment §8 zero-
    trades sentinel: a zero-trades bucket is not a legitimate y = 0
    observation — it means the movable never fired on that pair-window).
    """
    stats = telemetry_payload.get("per_pair_window_stats") or []
    rows: list[dict[str, Any]] = []
    for s in stats:
        n = int(s.get("n_trades", 0) or 0)
        if n <= 0:
            continue
        rows.append({
            "symbol": str(s["symbol"]),
            "window_idx": int(s["window_idx"]),
            "mean_tqs": float(s["mean_tqs"]),
            "n_trades": n,
        })
    return rows


def regress_one_movable(
    telemetry_payload: dict[str, Any],
    features: dict[str, dict[str, Any]],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    rng_seed: int = DEFAULT_SEED,
    telemetry_source: Optional[str] = None,
) -> MovableAgentRegressions:
    """One-movable regression across all §4 features."""
    aid = str(telemetry_payload.get("agent_id", ""))
    rows = _rows_from_telemetry(telemetry_payload)
    symbols_present = tuple(sorted({r["symbol"] for r in rows}))
    windows_present = len({r["window_idx"] for r in rows})
    n_trades_movable = sum(r["n_trades"] for r in rows)

    per_feat: dict[str, FeatureFit] = {}
    for feat in FEATURE_KEYS:
        xs: list[float] = []
        ys: list[float] = []
        obs_list: list[Observation] = []
        for row in rows:
            fval = features.get(row["symbol"], {}).get(feat)
            if not isinstance(fval, (int, float)) or (
                isinstance(fval, float) and math.isnan(fval)
            ):
                continue
            xs.append(float(fval))
            ys.append(float(row["mean_tqs"]))
            obs_list.append(Observation(
                symbol=row["symbol"],
                window_idx=int(row["window_idx"]),
                x_feature=float(fval),
                y_mean_tqs=float(row["mean_tqs"]),
                n_trades=int(row["n_trades"]),
            ))
        fit = _bootstrap_beta_ci(xs, ys, n_boot=n_boot, seed=rng_seed)
        # Overwrite fields the primitive left blank -- prelocked
        # direction depends on the (agent, feature) pair, not the fit.
        prelocked = PRELOCKED_DIRECTIONS.get((aid, feat))
        fit.prelocked_direction = prelocked
        fit.observations = obs_list
        if fit.beta is not None and prelocked in ("+", "-"):
            sign_ok = (
                (fit.beta > 0 and prelocked == "+")
                or (fit.beta < 0 and prelocked == "-")
            )
            fit.direction_respected = bool(sign_ok)
        elif prelocked is not None:
            fit.direction_respected = False
        else:
            fit.direction_respected = None
        per_feat[feat] = fit

    return MovableAgentRegressions(
        agent_id=aid,
        symbols_present=symbols_present,
        n_symbols_present=len(symbols_present),
        n_windows_present=windows_present,
        n_trades_movable=n_trades_movable,
        features=per_feat,
        include_kunigami_unretired=telemetry_payload.get(
            "include_kunigami_unretired",
        ),
        aggregator_arm=telemetry_payload.get("aggregator_arm"),
        telemetry_source=telemetry_source,
    )


def _evaluate_verdict(
    regressions: dict[str, MovableAgentRegressions],
    movable_agents: tuple[str, ...],
) -> tuple[str, int, dict[str, list[str]], list[dict], bool, bool]:
    """Apply PROTOCOL §5 pass criterion. Unchanged by the amendment."""
    agent_pass: dict[str, list[str]] = {}
    passing_directional: list[dict] = []
    for aid in movable_agents:
        entry = regressions.get(aid)
        if entry is None:
            agent_pass[aid] = []
            continue
        passing_features: list[str] = []
        for feat, fit in entry.features.items():
            abs_lo = fit.abs_ci_lower
            if abs_lo is not None and abs_lo > 0:
                passing_features.append(feat)
                if fit.direction_respected is True:
                    passing_directional.append({"agent": aid, "feature": feat})
        agent_pass[aid] = passing_features

    n_passing = sum(1 for feats in agent_pass.values() if feats)
    cond_1 = n_passing >= 2
    cond_2 = len(passing_directional) >= 1
    verdict = "PASS" if (cond_1 and cond_2) else "FAIL"
    return verdict, n_passing, agent_pass, passing_directional, cond_1, cond_2


# ---------------------------------------------------------------------------
# Verdict markdown
# ---------------------------------------------------------------------------

def _render_verdict_md(report: Ac0VerdictReport) -> str:
    lines: list[str] = []
    lines.append("# Phase AC — AC.0-v2 verdict "
                 "(fresh-compute per-movable regression)")
    lines.append("")
    lines.append(f"- **Verdict:** **{report.verdict}**")
    lines.append(f"- **Fired:** {report.fired_at_utc}")
    lines.append(
        f"- **Telemetry source:** `{report.telemetry_dir}` "
        f"(per-movable walk-forward outputs from `run_ac0_compute`)"
    )
    lines.append(f"- **Pair-character source (FROZEN):** "
                 f"`{report.pair_character_source}`")
    lines.append(f"- **Bootstrap:** n = {report.n_bootstrap}, "
                 f"seed = {report.rng_seed}, window-level resample")
    lines.append(
        "- **Amendment:** `AMENDMENT_2026-07-20_ac0_methodology_switch.md` "
        "(§5 pass criterion unchanged; y-axis switched from banked to fresh)"
    )
    lines.append("")

    lines.append("## 1. Per-agent coverage (fresh telemetry)")
    lines.append("")
    lines.append("| Agent | symbols present | # symbols | # windows | movable trades |")
    lines.append("|---|---|---:|---:|---:|")
    for aid in MOVABLE_AGENTS:
        entry = report.regressions.get(aid)
        if entry is None:
            lines.append(f"| **{aid}** | (missing telemetry) | 0 | 0 | 0 |")
            continue
        lines.append(
            f"| **{aid}** | {', '.join(entry.symbols_present) or '—'} | "
            f"{entry.n_symbols_present} | {entry.n_windows_present} | "
            f"{entry.n_trades_movable} |"
        )
    lines.append("")

    lines.append("## 2. Regression outputs — movable agents")
    lines.append("")
    for aid in MOVABLE_AGENTS:
        entry = report.regressions.get(aid)
        lines.append(f"### {aid}")
        lines.append("")
        if entry is None or entry.n_symbols_present == 0:
            lines.append(
                f"**No AC.0-v2 telemetry available for {aid}.** Fresh "
                "walk-forward not run OR produced zero trades across all "
                "widened pairs (see amendment §8 zero-trades sentinel)."
            )
            lines.append("")
            continue
        lines.append(
            "| Feature | n obs | unique x | β | R² | CI lower | CI upper | "
            "|β| CI lower | direction | direction OK? | notes |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|"
        )
        for feat in FEATURE_KEYS:
            fit = entry.features.get(feat)
            if fit is None:
                continue
            direction = fit.prelocked_direction or "—"
            dresp = fit.direction_respected
            dresp_s = "n/a" if dresp is None else ("✓" if dresp else "✗")

            def _f(x):
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return "—"
                return f"{x:+.4f}"

            def _fabs(x):
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return "—"
                return f"{x:.4f}"

            notes = fit.degenerate_reason or ""
            lines.append(
                f"| `{feat}` | {fit.n_observations} | {fit.n_unique_x} | "
                f"{_f(fit.beta)} | {_fabs(fit.r2)} | "
                f"{_f(fit.ci_lower)} | {_f(fit.ci_upper)} | "
                f"{_fabs(fit.abs_ci_lower)} | {direction} | "
                f"{dresp_s} | {notes} |"
            )
        lines.append("")

    lines.append("## 3. Pass criterion (§5, unchanged by amendment)")
    lines.append("")
    lines.append(
        f"- **Condition 1** — ≥2 of {{Chigiri, Rin, Kunigami}} with a "
        f"feature whose bootstrap 95 % CI lower on |β| > 0: "
        f"**{'MET' if report.condition_1_met else 'NOT MET'}** "
        f"({report.n_movables_passing}/3 movables passing)."
    )
    for aid, feats in report.passing_features_per_movable.items():
        lines.append(
            f"  * {aid}: {feats if feats else 'no feature passing'}"
        )
    lines.append(
        f"- **Condition 2** — ≥1 passing (agent, feature) pair with "
        f"pre-locked direction respected: "
        f"**{'MET' if report.condition_2_met else 'NOT MET'}** "
        f"({len(report.passing_directional_pairs)} pair(s))."
    )
    for pair in report.passing_directional_pairs:
        lines.append(f"  * {pair['agent']} × {pair['feature']}")
    lines.append("")

    lines.append("## 4. Verdict narrative")
    lines.append("")
    if report.verdict == "PASS":
        lines.append(
            "AC.0-v2 PASSES per §5. Pair-character features explain a "
            "non-trivial share of per-movable-agent mean-TQS variance on "
            "the fresh-compute walk-forwards. **AC.1 sub-arms are "
            "AUTHORISED to fire per §12 sequencing (amendment §10).**"
        )
    else:
        lines.append(
            "**AC.0-v2 FAILS per §5.** Pair-character features do not "
            "produce a bootstrap-significant |β| for ≥ 2 of the three "
            "movables (or the one direction-respected condition is "
            "unmet). Per amendment §6, this is an honest negative: the "
            "pitch-terrain hypothesis is **underpowered by panel size**, "
            "not refuted. Any further testing requires expanding the "
            "panel to ≥ 10 USD-quoted pairs before firing; the amendment "
            "explicitly forbids a third methodology switch."
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def regress_ac0(
    *,
    telemetry_dir: Path | str,
    pair_character_path: Path | str,
    out_regression: Path | str,
    out_verdict: Path | str,
    n_boot: int = DEFAULT_N_BOOT,
    rng_seed: int = DEFAULT_SEED,
    movable_agents: tuple[str, ...] = MOVABLE_AGENTS,
) -> Ac0VerdictReport:
    """Regress per-movable-agent per-pair mean-TQS against §4 pair-
    character features and evaluate the §5 pass criterion.

    Reads fresh-compute telemetry from
    ``telemetry_dir/<agent>_walkforward.json``, joins with the frozen
    ``pair_character.json``, runs OLS per movable × feature with
    bootstrap 95 % CI (window-level resample, seed-pinned), and writes
    machine-readable (``ac0_regression_v2.json``) + human-readable
    (``ac0_verdict_v2.md``) outputs. Returns the verdict report.
    """
    telemetry_dir = Path(telemetry_dir)
    pair_character_path = Path(pair_character_path)
    out_regression = Path(out_regression)
    out_verdict = Path(out_verdict)

    features = load_pair_character(pair_character_path)
    telemetry = load_movable_telemetry(telemetry_dir, movable_agents)

    regressions: dict[str, MovableAgentRegressions] = {}
    for aid in movable_agents:
        payload = telemetry.get(aid)
        if payload is None:
            continue
        regressions[aid] = regress_one_movable(
            payload, features,
            n_boot=n_boot, rng_seed=rng_seed,
            telemetry_source=str(
                telemetry_dir / f"{aid}_walkforward.json"
            ),
        )

    (verdict, n_pass, agent_pass, directional,
     cond_1, cond_2) = _evaluate_verdict(regressions, movable_agents)

    report = Ac0VerdictReport(
        verdict=verdict,
        n_movables_passing=n_pass,
        passing_features_per_movable=agent_pass,
        passing_directional_pairs=directional,
        condition_1_met=cond_1,
        condition_2_met=cond_2,
        regressions=regressions,
        pair_character_source=str(pair_character_path),
        telemetry_dir=str(telemetry_dir),
        n_bootstrap=int(n_boot),
        rng_seed=int(rng_seed),
        fired_at_utc=datetime.now(timezone.utc).isoformat(),
    )

    out_regression.parent.mkdir(parents=True, exist_ok=True)
    out_regression.write_text(
        json.dumps(report.to_jsonable(), indent=2, default=str),
        encoding="utf-8",
    )
    out_verdict.parent.mkdir(parents=True, exist_ok=True)
    out_verdict.write_text(_render_verdict_md(report), encoding="utf-8")
    log.info(
        "AC.0-v2: wrote %s + %s | verdict=%s | n_movables_passing=%d",
        out_regression, out_verdict, verdict, n_pass,
    )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "AC.0-v2 regression + verdict rendering. See "
            "programs/M001_multi_agent_ensemble/experiments/"
            "phase_ac_pitch_assignment/AMENDMENT_2026-07-20_"
            "ac0_methodology_switch.md."
        ),
    )
    parser.add_argument("--telemetry-dir", type=Path, required=True,
                        help="Directory containing per-movable "
                             "<agent>_walkforward.json outputs from "
                             "run_ac0_compute.")
    parser.add_argument("--pair-character", type=Path, required=True,
                        help="Frozen pair_character.json from the AC.0-v1 "
                             "fire.")
    parser.add_argument("--out-regression", type=Path, required=True,
                        help="Output path for ac0_regression_v2.json.")
    parser.add_argument("--out-verdict", type=Path, required=True,
                        help="Output path for ac0_verdict_v2.md.")
    parser.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    report = regress_ac0(
        telemetry_dir=args.telemetry_dir,
        pair_character_path=args.pair_character,
        out_regression=args.out_regression,
        out_verdict=args.out_verdict,
        n_boot=args.n_boot,
        rng_seed=args.seed,
    )
    print(f"[AC.0-v2] === VERDICT: {report.verdict} ===")
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
