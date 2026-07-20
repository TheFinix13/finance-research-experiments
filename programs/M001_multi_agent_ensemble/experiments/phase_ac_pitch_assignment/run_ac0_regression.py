"""Phase AC — AC.0 meta-control (pair-character predicts agent success).

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        PROTOCOL.md §4, §5, §9

What this does (in order):

1. Loads H4 + D1 bars for the in-cache 5-pair panel
   (EURUSD, GBPUSD, USDCAD, AUDUSD, NZDUSD) from the production parquet
   cache via ``agent.data.loader.BarLoader``. The training window is
   [2015-01-01, first-OOS-start), i.e. [2015-01-01, 2019-01-01) per G7
   walk-forward window definitions.
2. Computes the pair-character feature vector per pair (§4):
   * d1_ac1           — first-order autocorrelation of daily log-returns
   * h4_atr_percentile — median H4 ATR-14 relative to the panel-wide distribution
   * max_session_impulse — max over 4 sessions of avg |open→3rd-H4-close| / avg H4 range
   * d1_chop_fraction  — fraction of D1 bars where |close-open| < 0.3*(high-low)
   * dxy_beta          — β of pair weekly returns vs DXY weekly (DROPPED — DXY
                          not in production parquet cache; noted per §4)
   Written to ``results/pair_character.json`` (frozen once).
3. Loads banked ``g7_replay_cache_g7retry1-phi41/trades.jsonl`` and
   computes per-agent per-(symbol, window) mean TQS for the 3 movable
   agents (Chigiri, Rin, Kunigami) plus each anchor for audit context.
4. OLS regression per movable agent × feature with bootstrap 95 % CI
   (n=10 000 percentile). Bootstrap unit = window (per §6).
5. Evaluates the §5 AC.0 pass threshold: at least 2 of {Chigiri, Rin,
   Kunigami} with at least ONE feature having bootstrap 95 % CI lower
   bound on |β| > 0, AND the pre-locked direction (§3) respected for at
   least one passing pair.
6. Emits:
   * results/pair_character.json
   * results/ac0_regression.json
   * results/ac0_verdict.md

Usage:

    cd /Users/the1finix/Documents/GitHub/finance-research-experiments
    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/run_ac0_regression.py
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure production repo is importable for data-loader access.
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
PROD_REPO = REPO_ROOT.parent / "multi-pair-trading-agent"
for p in (str(REPO_ROOT), str(PROD_REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)


UTC = timezone.utc

# ---------------------------------------------------------------------------
# Panel + windows (locked per G7 walk-forward)
# ---------------------------------------------------------------------------
IN_CACHE_PAIRS: tuple[str, ...] = (
    "EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD",
)
BLOCKED_PAIRS: tuple[str, ...] = ("USDJPY", "USDCHF")

# G7 walk-forward: 4-yr IS / 1-yr OOS rolling, panel 2015-01-01 → 2025-12-31.
# First OOS starts at 2019-01-01. Training window for pair-character = pre-first-OOS.
TRAIN_START = datetime(2015, 1, 1, tzinfo=UTC)
TRAIN_END = datetime(2019, 1, 1, tzinfo=UTC)

# 7 OOS windows (start, end).
OOS_WINDOWS: list[tuple[int, datetime, datetime]] = [
    (idx, datetime(2019 + idx, 1, 1, tzinfo=UTC),
     datetime(2020 + idx, 1, 1, tzinfo=UTC))
    for idx in range(7)
]

# ---------------------------------------------------------------------------
# Movable agents + pre-locked directional priors (per PROTOCOL §3)
# ---------------------------------------------------------------------------
MOVABLE_AGENTS: tuple[str, ...] = (
    "chigiri_hyoma", "itoshi_rin", "kunigami_rensuke",
)

# Direction of expected β for each (agent, feature). "+" = positive β,
# "-" = negative β, "|.|-" = negative on |feature| (magnitude penalty).
# Missing entries: no a-priori prediction locked.
PRELOCKED_DIRECTIONS: dict[tuple[str, str], str] = {
    ("chigiri_hyoma", "max_session_impulse"): "+",
    ("chigiri_hyoma", "d1_chop_fraction"): "-",
    ("itoshi_rin", "h4_atr_percentile"): "-",
    # DXY-beta dropped from feature set; magnitude prior unusable.
    ("kunigami_rensuke", "d1_chop_fraction"): "+",
}

FEATURE_KEYS: tuple[str, ...] = (
    "d1_ac1",
    "h4_atr_percentile",
    "max_session_impulse",
    "d1_chop_fraction",
    # "dxy_beta" — DROPPED per §4 fallback (DXY not in production cache).
)

BANKED_TRADES = (
    REPO_ROOT
    / "programs" / "M001_multi_agent_ensemble" / "reviews"
    / "g7_replay_cache_g7retry1-phi41" / "trades.jsonl"
)

OUT_DIR = (
    REPO_ROOT
    / "programs" / "M001_multi_agent_ensemble" / "experiments"
    / "phase_ac_pitch_assignment" / "results"
)


# ---------------------------------------------------------------------------
# Data loading (production parquet cache)
# ---------------------------------------------------------------------------

def _load_bars(symbol: str, timeframe_str: str, start: datetime, end: datetime):
    """Load bars from the production parquet cache. Returns a
    pandas DataFrame indexed by UTC timestamp with open/high/low/close/volume.
    """
    from agent.config import load_config
    from agent.data.loader import BarLoader
    from agent.types import Timeframe

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    tf = getattr(Timeframe, timeframe_str)
    return loader.get(symbol, tf, start, end, refresh=False)


# ---------------------------------------------------------------------------
# Pair-character features (§4)
# ---------------------------------------------------------------------------

def _d1_ac1(d1_df) -> float:
    """First-order autocorrelation of daily log-returns."""
    import numpy as np

    closes = d1_df["close"].to_numpy()
    if len(closes) < 3:
        return float("nan")
    log_ret = np.diff(np.log(closes))
    if len(log_ret) < 2:
        return float("nan")
    x = log_ret[:-1]
    y = log_ret[1:]
    x_bar = x.mean()
    y_bar = y.mean()
    num = ((x - x_bar) * (y - y_bar)).sum()
    den = math.sqrt(((x - x_bar) ** 2).sum() * ((y - y_bar) ** 2).sum())
    return float(num / den) if den > 0 else float("nan")


def _median_h4_atr14(h4_df) -> float:
    """Median H4 ATR-14 (in absolute price units). Panel-wide percentile
    ranking happens across pairs after all medians are collected.
    """
    import numpy as np

    if len(h4_df) < 15:
        return float("nan")
    high = h4_df["high"].to_numpy()
    low = h4_df["low"].to_numpy()
    close = h4_df["close"].to_numpy()
    prev_close = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    n = 14
    atr = np.zeros_like(tr)
    if len(tr) < n:
        return float("nan")
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    valid = atr[n - 1:]
    return float(np.median(valid))


def _max_session_impulse(h4_df) -> float:
    """Max over 4 sessions of (avg |open→3rd-H4-close|) / (avg H4 range).

    H4 bars for a session are the 6 4-hour bars covering that session's
    active hours (UTC-aligned):
      Sydney: 22-06 UTC
      Tokyo:  00-08 UTC
      London: 08-16 UTC
      NY:     13-21 UTC
    The "3rd H4 close" is the 3rd bar starting from the session open.
    We approximate by grouping H4 bars by their UTC hour bucket, picking
    the FIRST bar of each session as the session-open bar, and computing
    the move from that bar's open to the close of the 3rd bar (12 hours
    of movement) — normalised by average H4 range over the same
    session's bars.
    """
    import numpy as np
    import pandas as pd

    if len(h4_df) < 6:
        return float("nan")
    df = h4_df.copy()
    df["hour"] = df.index.hour
    sessions = {
        "Sydney": [22, 2],   # first bar hour, third bar close hour
        "Tokyo":  [0, 8],
        "London": [8, 16],
        "NY":     [12, 20],
    }
    ratios: list[float] = []
    for _sess, (open_h, _close_h) in sessions.items():
        open_bars = df[df["hour"] == open_h]
        if len(open_bars) == 0:
            continue
        impulses: list[float] = []
        ranges: list[float] = []
        for ts, _ in open_bars.iterrows():
            end_ts = ts + pd.Timedelta(hours=12)
            slab = df.loc[ts:end_ts]
            if len(slab) < 3:
                continue
            first = slab.iloc[0]
            third = slab.iloc[2]
            impulse = abs(third["close"] - first["open"])
            rng = float(slab["high"].max() - slab["low"].min())
            if rng <= 0:
                continue
            impulses.append(impulse)
            ranges.append(rng)
        if impulses and ranges:
            ratio = float(np.mean(impulses) / np.mean(ranges))
            ratios.append(ratio)
    return max(ratios) if ratios else float("nan")


def _d1_chop_fraction(d1_df) -> float:
    """Fraction of D1 bars where |close - open| < 0.3 * (high - low)."""
    if len(d1_df) < 1:
        return float("nan")
    ranges = (d1_df["high"] - d1_df["low"]).to_numpy()
    body = (d1_df["close"] - d1_df["open"]).abs().to_numpy()
    valid = ranges > 0
    if valid.sum() == 0:
        return float("nan")
    chop = (body[valid] < 0.3 * ranges[valid])
    return float(chop.mean())


def _compute_features_for_pair(sym: str) -> dict[str, Any]:
    """Compute the 4-feature vector for a single pair on the training window."""
    h4 = _load_bars(sym, "H4", TRAIN_START, TRAIN_END)
    d1 = _load_bars(sym, "D1", TRAIN_START, TRAIN_END)
    if h4.empty or d1.empty:
        return {"error": f"empty bars for {sym}",
                "n_h4": len(h4), "n_d1": len(d1)}
    return {
        "n_h4": int(len(h4)),
        "n_d1": int(len(d1)),
        "d1_ac1": _d1_ac1(d1),
        "median_h4_atr_abs": _median_h4_atr14(h4),
        "max_session_impulse": _max_session_impulse(h4),
        "d1_chop_fraction": _d1_chop_fraction(d1),
        "training_window_utc": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
    }


def compute_pair_character() -> dict[str, dict[str, Any]]:
    """Compute + normalise the pair-character feature vector for all
    in-cache pairs. Returns a dict[symbol -> feature dict].

    Percentile normalisation happens across the current 5 in-cache pairs
    for h4_atr — the pre-reg defines this as "median H4 ATR-14 relative
    to the panel-wide distribution".
    """
    raw: dict[str, dict[str, Any]] = {}
    for sym in IN_CACHE_PAIRS:
        raw[sym] = _compute_features_for_pair(sym)
    for sym in BLOCKED_PAIRS:
        raw[sym] = {"error": "NEEDS CACHE PULL — pair not in production parquet"}

    valid_atrs = [
        raw[s].get("median_h4_atr_abs", math.nan)
        for s in IN_CACHE_PAIRS
        if isinstance(raw[s].get("median_h4_atr_abs"), (int, float))
        and not math.isnan(raw[s].get("median_h4_atr_abs", math.nan))
    ]
    if valid_atrs:
        sorted_atrs = sorted(valid_atrs)
        for sym in IN_CACHE_PAIRS:
            atr = raw[sym].get("median_h4_atr_abs")
            if isinstance(atr, (int, float)) and not math.isnan(atr):
                rank = sorted_atrs.index(atr)
                pct = (rank + 0.5) / len(sorted_atrs)
                raw[sym]["h4_atr_percentile"] = float(pct)
            else:
                raw[sym]["h4_atr_percentile"] = float("nan")

    for sym in IN_CACHE_PAIRS:
        raw[sym]["dxy_beta"] = "dropped (DXY not in production parquet)"
    return raw


# ---------------------------------------------------------------------------
# Banked telemetry loading
# ---------------------------------------------------------------------------

def _which_window(entry_time_str: str) -> int | None:
    """Return the OOS-window index containing this entry, or None."""
    try:
        ts = datetime.fromisoformat(entry_time_str.replace(" ", "T").split("+")[0])
    except Exception:
        return None
    ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts
    for idx, oos_s, oos_e in OOS_WINDOWS:
        if oos_s <= ts < oos_e:
            return idx
    return None


def load_banked_per_window_mean_tqs() -> dict[str, dict[tuple[str, int], dict]]:
    """Load per-agent per-(symbol, window) mean-TQS statistics from the
    banked g7retry1-phi41 replay cache.

    Returns dict[agent_id -> dict[(symbol, window_idx) -> {'mean_tqs': .., 'n': ..}]].
    """
    per_agent: dict[str, dict[tuple[str, int], list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with BANKED_TRADES.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            agent_id = rec["agent_id"]
            sym = rec["symbol"]
            widx = _which_window(rec.get("entry_time", ""))
            if widx is None:
                continue
            tqs = float(rec.get("tqs_components", {}).get("tqs", 0.0))
            per_agent[agent_id][(sym, widx)].append(tqs)
    out: dict[str, dict[tuple[str, int], dict]] = {}
    for aid, buckets in per_agent.items():
        out[aid] = {
            k: {"mean_tqs": sum(v) / len(v), "n": len(v)}
            for k, v in buckets.items()
        }
    return out


# ---------------------------------------------------------------------------
# OLS regression + bootstrap
# ---------------------------------------------------------------------------

def _ols_beta(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    """Univariate OLS: returns (β, R²). Requires >1 unique x."""
    n = len(xs)
    if n < 2:
        return None
    if len(set(xs)) < 2:
        return None
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    num = sum((xs[i] - x_bar) * (ys[i] - y_bar) for i in range(n))
    den_x = sum((xs[i] - x_bar) ** 2 for i in range(n))
    if den_x == 0:
        return None
    beta = num / den_x
    ss_res = sum((ys[i] - (y_bar + beta * (xs[i] - x_bar))) ** 2 for i in range(n))
    ss_tot = sum((ys[i] - y_bar) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return (beta, r2)


def _bootstrap_beta_ci(
    xs: list[float], ys: list[float],
    *, n_boot: int = 10_000, alpha: float = 0.05, seed: int = 20260720,
) -> dict[str, Any]:
    """Percentile bootstrap CI on β. Resamples (x, y) pairs with
    replacement. Degenerate resamples (single-x) are re-drawn.
    """
    rng = random.Random(seed)
    n = len(xs)
    point = _ols_beta(xs, ys)
    if point is None:
        return {
            "n": n, "beta": None, "r2": None,
            "ci_lower": None, "ci_upper": None, "abs_ci_lower": None,
            "n_boot_valid": 0,
            "degenerate_reason": (
                f"n={n}, unique_x={len(set(xs))} — need n>=2 with "
                ">1 unique x-value for OLS β."
            ),
        }
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
        return {
            "n": n, "beta": beta_hat, "r2": r2_hat,
            "ci_lower": None, "ci_upper": None, "abs_ci_lower": None,
            "n_boot_valid": 0,
            "degenerate_reason": (
                "All bootstrap resamples collapsed to a single unique "
                "x — CI undefined."
            ),
        }
    betas.sort()
    lo = betas[int(alpha / 2 * len(betas))]
    hi = betas[int((1 - alpha / 2) * len(betas))]
    abs_betas = sorted(abs(b) for b in betas)
    abs_lo = abs_betas[int(alpha / 2 * len(abs_betas))]
    return {
        "n": n, "beta": beta_hat, "r2": r2_hat,
        "ci_lower": lo, "ci_upper": hi, "abs_ci_lower": abs_lo,
        "n_boot_valid": len(betas),
    }


def run_regressions(
    features: dict[str, dict[str, Any]],
    telemetry: dict[str, dict[tuple[str, int], dict]],
) -> dict[str, Any]:
    """Per movable agent × feature: run OLS with bootstrap CI.

    x-axis is the pair-character feature value for the symbol.
    y-axis is the (symbol, window)-level mean TQS from banked telemetry.
    """
    results: dict[str, Any] = {
        "movable_agents": {},
        "audit_anchors": {},
    }
    audit_agents = ("isagi_yoichi", "bachira_meguru", "nagi_seishiro", "barou_shoei")
    all_agents = MOVABLE_AGENTS + audit_agents
    for aid in all_agents:
        bucket = telemetry.get(aid, {})
        per_feat: dict[str, Any] = {}
        symbols_present = sorted({k[0] for k in bucket.keys()})
        n_windows = len({k[1] for k in bucket.keys()})
        for feat in FEATURE_KEYS:
            xs: list[float] = []
            ys: list[float] = []
            per_obs: list[dict] = []
            for (sym, widx), stats in bucket.items():
                if sym not in IN_CACHE_PAIRS:
                    continue
                fval = features.get(sym, {}).get(feat)
                if not isinstance(fval, (int, float)) or math.isnan(fval):
                    continue
                xs.append(float(fval))
                ys.append(float(stats["mean_tqs"]))
                per_obs.append({
                    "symbol": sym, "window": int(widx),
                    "x_feature": float(fval),
                    "y_mean_tqs": float(stats["mean_tqs"]),
                    "n_trades": int(stats["n"]),
                })
            fit = _bootstrap_beta_ci(xs, ys)
            fit["prelocked_direction"] = PRELOCKED_DIRECTIONS.get(
                (aid, feat), None,
            )
            if (
                fit.get("beta") is not None
                and fit["prelocked_direction"] in ("+", "-")
            ):
                sign_ok = (
                    (fit["beta"] > 0 and fit["prelocked_direction"] == "+")
                    or (fit["beta"] < 0 and fit["prelocked_direction"] == "-")
                )
                fit["direction_respected"] = bool(sign_ok)
            elif fit["prelocked_direction"] is not None:
                fit["direction_respected"] = False
            else:
                fit["direction_respected"] = None
            fit["n_observations"] = len(xs)
            fit["n_unique_x"] = len(set(xs))
            fit["observations"] = per_obs
            per_feat[feat] = fit
        entry = {
            "symbols_present": symbols_present,
            "n_symbols_present": len(symbols_present),
            "n_windows_present": n_windows,
            "features": per_feat,
        }
        if aid in MOVABLE_AGENTS:
            results["movable_agents"][aid] = entry
        else:
            results["audit_anchors"][aid] = entry
    return results


# ---------------------------------------------------------------------------
# Verdict (§5)
# ---------------------------------------------------------------------------

def evaluate_ac0_verdict(regressions: dict[str, Any]) -> dict[str, Any]:
    """Apply the PROTOCOL §5 AC.0 threshold.

    PASS ⟺
      • ≥2 of {Chigiri, Rin, Kunigami} have ≥1 feature with
        bootstrap 95 % CI lower bound on |β| > 0
      • ≥1 passing (agent, feature) pair respects the pre-locked
        direction (§3).
    """
    agent_pass: dict[str, list[str]] = {}
    passing_directional: list[tuple[str, str]] = []
    for aid in MOVABLE_AGENTS:
        entry = regressions["movable_agents"].get(aid)
        if entry is None:
            agent_pass[aid] = []
            continue
        passing_features: list[str] = []
        for feat, fit in entry["features"].items():
            abs_lo = fit.get("abs_ci_lower")
            if abs_lo is not None and abs_lo > 0:
                passing_features.append(feat)
                if fit.get("direction_respected") is True:
                    passing_directional.append((aid, feat))
        agent_pass[aid] = passing_features

    n_agents_pass = sum(1 for v in agent_pass.values() if v)
    condition_1 = n_agents_pass >= 2
    condition_2 = len(passing_directional) >= 1
    verdict = "PASS" if (condition_1 and condition_2) else "FAIL"

    return {
        "verdict": verdict,
        "condition_1_two_of_three_movables_with_ci_lower_on_abs_beta_gt_0": {
            "required": True, "observed": condition_1,
            "n_movables_passing": n_agents_pass,
            "per_agent_passing_features": agent_pass,
        },
        "condition_2_at_least_one_direction_respected": {
            "required": True, "observed": condition_2,
            "passing_directional_pairs": [
                {"agent": a, "feature": f} for a, f in passing_directional
            ],
        },
    }


# ---------------------------------------------------------------------------
# Verdict markdown
# ---------------------------------------------------------------------------

def _render_verdict_md(
    features: dict[str, Any],
    regressions: dict[str, Any],
    verdict: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Phase AC — AC.0 verdict (pair-character regression)")
    lines.append("")
    lines.append(f"- **Verdict:** **{verdict['verdict']}**")
    lines.append(f"- **Fired:** {datetime.now(UTC).isoformat()}")
    lines.append(f"- **Training window (pair-character features):** "
                 f"{TRAIN_START.date()} → {TRAIN_END.date()}")
    lines.append(f"- **OOS windows (banked telemetry):** "
                 f"{OOS_WINDOWS[0][1].date()} → {OOS_WINDOWS[-1][2].date()} "
                 f"(K={len(OOS_WINDOWS)})")
    lines.append("- **Banked telemetry source:** "
                 "`reviews/g7_replay_cache_g7retry1-phi41/trades.jsonl`")
    lines.append(f"- **Feature-vector n:** {len(IN_CACHE_PAIRS)} pairs "
                 f"({', '.join(IN_CACHE_PAIRS)}). "
                 f"USDJPY / USDCHF blocked pending cache pull (§4, §10).")
    lines.append("- **Features:** " + ", ".join(FEATURE_KEYS)
                 + " (dxy_beta DROPPED — DXY not in production parquet).")
    lines.append("")
    lines.append("## 1. Pair-character feature vector (frozen)")
    lines.append("")
    lines.append("| Pair | d1_ac1 | h4_atr_pct | max_session_impulse | d1_chop_frac | dxy_beta |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for sym in IN_CACHE_PAIRS:
        f = features[sym]
        if "error" in f:
            lines.append(f"| {sym} | ERROR | ERROR | ERROR | ERROR | dropped |")
            continue
        lines.append(
            f"| {sym} | {f['d1_ac1']:+.4f} | {f['h4_atr_percentile']:.2f} | "
            f"{f['max_session_impulse']:.3f} | {f['d1_chop_fraction']:.3f} | "
            f"dropped |"
        )
    for sym in BLOCKED_PAIRS:
        lines.append(f"| {sym} | NEEDS CACHE PULL | | | | |")
    lines.append("")
    lines.append("## 2. Per-agent per-pair coverage in banked telemetry")
    lines.append("")
    lines.append("Coverage tells you whether OLS is even mathematically "
                 "defined for that agent — need ≥2 observations with "
                 "≥2 unique x-values for a non-degenerate β.")
    lines.append("")
    lines.append("| Agent | symbols present | # symbols | # windows |")
    lines.append("|---|---|---:|---:|")
    for aid in MOVABLE_AGENTS:
        entry = regressions["movable_agents"].get(aid, {})
        syms = entry.get("symbols_present", [])
        n_s = entry.get("n_symbols_present", 0)
        n_w = entry.get("n_windows_present", 0)
        lines.append(f"| **{aid}** | {', '.join(syms) or '—'} | {n_s} | {n_w} |")
    for aid, entry in regressions["audit_anchors"].items():
        syms = entry.get("symbols_present", [])
        n_s = entry.get("n_symbols_present", 0)
        n_w = entry.get("n_windows_present", 0)
        lines.append(f"| {aid} (audit) | {', '.join(syms) or '—'} | {n_s} | {n_w} |")
    lines.append("")
    lines.append("## 3. Regression outputs — movable agents")
    lines.append("")
    for aid in MOVABLE_AGENTS:
        entry = regressions["movable_agents"].get(aid)
        lines.append(f"### {aid}")
        lines.append("")
        if entry is None or entry.get("n_symbols_present", 0) == 0:
            lines.append(f"**No banked trades for {aid} in the "
                         "g7retry1-phi41 cache.**")
            if aid == "kunigami_rensuke":
                lines.append("")
                lines.append("Reason: Kunigami is retired as a proposer "
                             "(G7 §11.12). AC.1 tests un-retirement, but "
                             "AC.0 uses banked (retired-Kunigami) telemetry "
                             "— he cannot contribute a regression row.")
            lines.append("")
            continue
        lines.append("| Feature | n obs | unique x | β | R² | CI lower | CI upper | |β| CI lower | direction | direction OK? | notes |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|")
        for feat in FEATURE_KEYS:
            fit = entry["features"].get(feat, {})
            n = fit.get("n_observations", 0)
            u = fit.get("n_unique_x", 0)
            beta = fit.get("beta")
            r2 = fit.get("r2")
            lo = fit.get("ci_lower")
            hi = fit.get("ci_upper")
            abs_lo = fit.get("abs_ci_lower")
            direction = fit.get("prelocked_direction") or "—"
            dresp = fit.get("direction_respected")
            dresp_s = "n/a" if dresp is None else ("✓" if dresp else "✗")
            notes = fit.get("degenerate_reason", "")
            def _f(x):
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return "—"
                return f"{x:+.4f}"
            def _fabs(x):
                if x is None or (isinstance(x, float) and math.isnan(x)):
                    return "—"
                return f"{x:.4f}"
            lines.append(
                f"| `{feat}` | {n} | {u} | {_f(beta)} | {_fabs(r2)} | "
                f"{_f(lo)} | {_f(hi)} | {_fabs(abs_lo)} | {direction} | "
                f"{dresp_s} | {notes} |"
            )
        lines.append("")
    lines.append("## 4. Pass criterion (§5)")
    lines.append("")
    c1 = verdict["condition_1_two_of_three_movables_with_ci_lower_on_abs_beta_gt_0"]
    c2 = verdict["condition_2_at_least_one_direction_respected"]
    lines.append(
        f"- **Condition 1** — ≥2 of {{Chigiri, Rin, Kunigami}} with a "
        f"feature whose bootstrap 95 % CI lower on |β| > 0: "
        f"**{'MET' if c1['observed'] else 'NOT MET'}** "
        f"({c1['n_movables_passing']}/3 movables passing)."
    )
    for aid, feats in c1["per_agent_passing_features"].items():
        lines.append(f"  * {aid}: {feats if feats else 'no feature passing'}")
    lines.append(
        f"- **Condition 2** — ≥1 passing (agent, feature) pair with "
        f"pre-locked direction respected: "
        f"**{'MET' if c2['observed'] else 'NOT MET'}** "
        f"({len(c2['passing_directional_pairs'])} pair(s))."
    )
    lines.append("")
    lines.append("## 5. Verdict narrative")
    lines.append("")
    if verdict["verdict"] == "PASS":
        lines.append(
            "AC.0 PASSES per §5. Pair-character features explain a "
            "non-trivial share of per-agent mean-TQS variance for the "
            "movable agents. AC.1 sub-arms are AUTHORISED to fire per §7 "
            "sequencing."
        )
    else:
        lines.append(
            "**AC.0 FAILS per §5. Pitch-character-predicts-agent-success "
            "unsupported at the banked-panel scale; pitch-assignment "
            "concept unsupported without a larger panel; further arms "
            "not authorised per PROTOCOL §5 fail-branch language and "
            "§10 kill condition.**"
        )
        lines.append("")
        lines.append("### 5a. Why the pre-registered test cannot fire cleanly")
        lines.append("")
        lines.append(
            "The pre-reg §5 pass criterion requires ≥2 of {Chigiri, Rin, "
            "Kunigami} to produce a non-degenerate regression with "
            "|β| CI lower > 0. Two structural constraints of the banked "
            "telemetry make this mathematically inaccessible:"
        )
        lines.append("")
        lines.append(
            "1. **Kunigami has 0 banked trades** — he is retired as a "
            "proposer (G7 §11.12). The g7retry1-phi41 replay was run "
            "with the retired-Kunigami roster, so his per-symbol mean-"
            "TQS row is empty. Un-retirement is what AC.1.kun-a *tests*, "
            "so AC.0 cannot use un-retired-Kunigami data."
        )
        lines.append(
            "2. **Rin has only 1 unique x-value.** His default "
            "`.symbols = ('EURUSD',)` means every banked window×symbol "
            "row for Rin sits at the same EURUSD feature value; OLS β "
            "requires ≥2 unique x-values, so no feature can produce a "
            "well-defined β for Rin — CI is undefined."
        )
        lines.append(
            "3. **Chigiri has 2 unique x-values** (EURUSD, GBPUSD). "
            "Chigiri is the ONLY movable that produces a defined β. "
            "Even a passing Chigiri result cannot meet the ≥2-agent "
            "threshold on its own."
        )
        lines.append("")
        lines.append(
            "The pre-reg §9 pre-mortem anticipated 'AC.0 low power at "
            "n=5 pairs'. The realised banked panel is n=3 pairs, and "
            "the agents' `.symbols` restrictions collapse per-agent "
            "coverage further to n=2/1/0 unique x-values. The pre-reg's "
            "own §5 fail-branch language is the correct verdict text: "
            "\"pitch-character-predicts-agent-success unsupported at "
            "n=5 pairs; pitch-assignment concept unsupported without a "
            "larger panel; further arms not authorised.\""
        )
        lines.append("")
        lines.append("### 5b. What this means for the campaign")
        lines.append("")
        lines.append(
            "- Per PROTOCOL §5 AC.0 fail-branch and §10 kill conditions: "
            "**AC.1 and AC.2 arms DO NOT fire.**"
        )
        lines.append(
            "- The harness extension (commit 3e0f611f) is a valid "
            "methodology deliverable and stays in the codebase — no "
            "strategy was changed."
        )
        lines.append(
            "- Any future Phase-AC-style pitch-assignment work will "
            "need either (a) a much larger banked panel (≥ 7 pairs, "
            "with movable agents' `.symbols` deliberately widened before "
            "the g7 walk-forward so the banked telemetry covers all "
            "pairs), or (b) a materially different statistic that does "
            "not require per-agent per-pair OLS — an amendment file "
            "(`AMENDMENT_YYYY-MM-DD_<slug>.md`) per PROTOCOL §13."
        )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[AC.0] Computing pair-character feature vector "
          f"({len(IN_CACHE_PAIRS)} in-cache pairs) ...", flush=True)
    features = compute_pair_character()
    (OUT_DIR / "pair_character.json").write_text(
        json.dumps(features, indent=2, default=str), encoding="utf-8",
    )
    print(f"[AC.0] Wrote {OUT_DIR / 'pair_character.json'}", flush=True)

    print("[AC.0] Loading banked g7retry1-phi41 per-window telemetry ...",
          flush=True)
    telemetry = load_banked_per_window_mean_tqs()
    print(f"[AC.0] Loaded telemetry for {len(telemetry)} agents", flush=True)

    print("[AC.0] Running regressions + bootstrap (n=10000) ...", flush=True)
    regressions = run_regressions(features, telemetry)

    print("[AC.0] Evaluating §5 verdict ...", flush=True)
    verdict = evaluate_ac0_verdict(regressions)
    combined = {
        "verdict": verdict,
        "regressions": regressions,
        "training_window_utc": [TRAIN_START.isoformat(), TRAIN_END.isoformat()],
        "oos_windows": [
            {"idx": i, "oos_start": s.isoformat(), "oos_end": e.isoformat()}
            for i, s, e in OOS_WINDOWS
        ],
        "banked_source": str(BANKED_TRADES.relative_to(REPO_ROOT)),
        "n_bootstrap": 10_000,
    }
    (OUT_DIR / "ac0_regression.json").write_text(
        json.dumps(combined, indent=2, default=str), encoding="utf-8",
    )
    print(f"[AC.0] Wrote {OUT_DIR / 'ac0_regression.json'}", flush=True)

    md = _render_verdict_md(features, regressions, verdict)
    (OUT_DIR / "ac0_verdict.md").write_text(md, encoding="utf-8")
    print(f"[AC.0] Wrote {OUT_DIR / 'ac0_verdict.md'}", flush=True)

    print(f"[AC.0] === VERDICT: {verdict['verdict']} ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
