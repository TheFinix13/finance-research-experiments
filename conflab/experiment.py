"""Walk-forward experiment harness: confluence bands vs random controls.

This is the falsification machine for the lab's research question. At every
rebuild step it constructs bands from history only, generates matched random
control levels, and scores both with the *identical* touch/reaction code over
the next ``stride`` bars. Analysis then asks:

1. Spearman: does reaction strength increase with confluence density?
2. Permutation test: do multi-member bands out-react random controls?
3. Per-source ablation (BH-FDR corrected): which sources, if any, carry the
   effect?

Outputs are hypothesis-generating evidence about confluence itself; they
confer zero authority over the live agent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from conflab.confluence import ConfluenceBand, cluster_levels
from conflab.indicators import atr
from conflab.levels import Level, extract_all_levels
from conflab.reaction import find_touches

log = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    eval_tf: str = "H4"
    warmup: int = 250            # bars of history before the first rebuild
    stride: int = 24             # rebuild cadence (bars of eval TF)
    horizon: int = 12            # reaction horizon (bars)
    tol_atr_mult: float = 0.5    # cluster tolerance = mult × ATR(eval TF)
    n_controls: int = 10         # random control levels per rebuild
    control_range_bars: int = 100
    use_mainrepo: bool = False   # adapter levels (slow); off by default
    seed: int = 42
    min_band_members: int = 2    # "high confluence" = at least 2 levels


def run_experiment(frames: dict[str, pd.DataFrame],
                   cfg: ExperimentConfig | None = None) -> list[dict]:
    """``frames`` maps timeframe -> OHLCV DataFrame (UTC DatetimeIndex).
    Returns one record per touch (band touches and control touches alike).
    """
    cfg = cfg or ExperimentConfig()
    rng = np.random.default_rng(cfg.seed)
    eval_df = frames[cfg.eval_tf]
    eval_atr = atr(eval_df).to_numpy()
    n = len(eval_df)
    records: list[dict] = []

    for t in range(cfg.warmup, n - cfg.horizon, cfg.stride):
        ts = eval_df.index[t]
        tol = cfg.tol_atr_mult * eval_atr[t]
        if not np.isfinite(tol) or tol <= 0:
            continue

        # Causal level extraction on every timeframe.
        levels: list[Level] = []
        for tf, df in frames.items():
            hist = df[df.index <= ts]
            if len(hist) >= 60:
                levels.extend(extract_all_levels(hist, tf,
                                                 use_mainrepo=cfg.use_mainrepo))
        if not levels:
            continue
        bands = cluster_levels(levels, tolerance=tol)

        # Matched random controls: same tolerance width, uniform inside the
        # recent price range, scored by the identical code path.
        window = eval_df.iloc[max(0, t - cfg.control_range_bars):t]
        lo, hi = float(window["low"].min()), float(window["high"].max())
        control_centers = rng.uniform(lo, hi, size=cfg.n_controls)

        scan_end = min(t + cfg.stride, n)
        for band in bands:
            half = max((band.high - band.low) / 2, tol / 2)
            for touch in find_touches(eval_df, band.center - half,
                                      band.center + half, t, scan_end,
                                      horizon=cfg.horizon):
                records.append({
                    "ts": str(eval_df.index[touch.index]),
                    "is_control": False,
                    "score": band.score,
                    "n_members": band.n_members,
                    "n_sources": band.n_sources,
                    "n_timeframes": band.n_timeframes,
                    "sources": sorted({m.source for m in band.members}),
                    "reaction_atr": touch.reaction_atr,
                    "held": touch.held,
                    "from_above": touch.from_above,
                })
        for center in control_centers:
            for touch in find_touches(eval_df, center - tol / 2,
                                      center + tol / 2, t, scan_end,
                                      horizon=cfg.horizon):
                records.append({
                    "ts": str(eval_df.index[touch.index]),
                    "is_control": True,
                    "score": 0.0, "n_members": 0, "n_sources": 0,
                    "n_timeframes": 0, "sources": [],
                    "reaction_atr": touch.reaction_atr,
                    "held": touch.held,
                    "from_above": touch.from_above,
                })
    return records


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _permutation_pvalue(a: np.ndarray, b: np.ndarray, n_perm: int,
                        rng: np.random.Generator) -> float:
    """One-sided p for mean(a) > mean(b) under label exchange."""
    observed = a.mean() - b.mean()
    pooled = np.concatenate([a, b])
    n_a = len(a)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        if pooled[:n_a].mean() - pooled[n_a:].mean() >= observed:
            count += 1
    return (count + 1) / (n_perm + 1)


def benjamini_hochberg(pvals: list[float], alpha: float = 0.05) -> list[bool]:
    """BH-FDR: returns a keep/reject-H0 flag per p-value (True = significant)."""
    m = len(pvals)
    if m == 0:
        return []
    order = np.argsort(pvals)
    flags = [False] * m
    max_k = -1
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= alpha * rank / m:
            max_k = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= max_k:
            flags[idx] = True
    return flags


def analyze(records: list[dict], *, min_band_members: int = 2,
            n_perm: int = 2000, alpha: float = 0.05,
            seed: int = 42) -> dict:
    """Run the pre-registered analysis over experiment records."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(records)
    out: dict = {"n_records": len(df)}
    if df.empty:
        return out

    bands = df[~df["is_control"]]
    controls = df[df["is_control"]]
    high = bands[bands["n_members"] >= min_band_members]
    out["n_band_touches"] = len(bands)
    out["n_high_band_touches"] = len(high)
    out["n_control_touches"] = len(controls)
    out["mean_reaction_high"] = float(high["reaction_atr"].mean()) if len(high) else None
    out["mean_reaction_control"] = float(controls["reaction_atr"].mean()) if len(controls) else None
    out["held_rate_high"] = float(high["held"].mean()) if len(high) else None
    out["held_rate_control"] = float(controls["held"].mean()) if len(controls) else None

    # 1) density -> reaction monotonicity (bands only)
    if len(bands) >= 10:
        out["spearman_score_vs_reaction"] = float(
            bands[["score", "reaction_atr"]].corr(method="spearman")
            .iloc[0, 1])

    # 2) high-confluence vs random controls
    if len(high) >= 10 and len(controls) >= 10:
        out["permutation_p_high_vs_control"] = float(_permutation_pvalue(
            high["reaction_atr"].to_numpy().copy(),
            controls["reaction_atr"].to_numpy().copy(),
            n_perm, rng))

    # 3) per-source ablation with BH-FDR
    source_rows = []
    all_sources = sorted({s for row in bands["sources"] for s in row})
    for src in all_sources:
        mask = bands["sources"].apply(lambda lst: src in lst)
        with_src = bands[mask]["reaction_atr"].to_numpy()
        without = bands[~mask]["reaction_atr"].to_numpy()
        if len(with_src) < 10 or len(without) < 10:
            continue
        p = float(_permutation_pvalue(with_src.copy(), without.copy(),
                                      n_perm, rng))
        source_rows.append({
            "source": src, "n": int(len(with_src)),
            "mean_reaction": float(with_src.mean()),
            "mean_reaction_without": float(without.mean()),
            "p_value": p,
        })
    flags = benjamini_hochberg([r["p_value"] for r in source_rows], alpha)
    for row, sig in zip(source_rows, flags):
        row["significant_fdr"] = bool(sig)
    out["per_source"] = sorted(source_rows, key=lambda r: r["p_value"])
    return out


def format_report(analysis: dict) -> str:
    lines = ["confluence-lab experiment report", "=" * 40]
    for key in ("n_records", "n_band_touches", "n_high_band_touches",
                "n_control_touches", "mean_reaction_high",
                "mean_reaction_control", "held_rate_high",
                "held_rate_control", "spearman_score_vs_reaction",
                "permutation_p_high_vs_control"):
        if key in analysis and analysis[key] is not None:
            val = analysis[key]
            lines.append(f"{key:<32} "
                         f"{val:.4f}" if isinstance(val, float) else
                         f"{key:<32} {val}")
    rows = analysis.get("per_source") or []
    if rows:
        lines.append("")
        lines.append(f"{'source':<26} {'n':>5} {'mean R':>8} {'others':>8} "
                     f"{'p':>8}  FDR")
        lines.append("-" * 62)
        for r in rows:
            lines.append(
                f"{r['source']:<26} {r['n']:>5} {r['mean_reaction']:>8.3f} "
                f"{r['mean_reaction_without']:>8.3f} {r['p_value']:>8.4f}  "
                f"{'*' if r.get('significant_fdr') else ''}")
    lines.append("")
    lines.append("CAVEAT: hypothesis-generating evidence only. Zero authority")
    lines.append("over the live agent without its own validation pipeline.")
    return "\n".join(lines)
