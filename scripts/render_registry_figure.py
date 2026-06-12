"""Render the Stage-1 registry summary figure: effect size vs sample size,
colored by verdict, one panel per timeframe.

Usage:
    python scripts/render_registry_figure.py --registry output/stage1_*.jsonl \
        --out output/stage1_summary.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {"alive": "#2e7d32", "parked_weak_effect": "#f9a825",
          "parked_insufficient_n": "#90a4ae", "dead": "#c62828"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--out", default="output/stage1_summary.png")
    p.add_argument("--title", default="Test A Stage 1 — EURUSD screen split")
    args = p.parse_args()

    rows = [json.loads(line) for line in
            Path(args.registry).read_text().splitlines() if line.strip()]
    tfs = [tf for tf in ("D1", "H4", "H1", "M15")
           if any(r["tf"] == tf for r in rows)]
    fig, axes = plt.subplots(1, len(tfs), figsize=(4.2 * len(tfs), 4.6),
                             sharey=True)
    if len(tfs) == 1:
        axes = [axes]
    for ax, tf in zip(axes, tfs):
        sub = [r for r in rows if r["tf"] == tf]
        for r in sub:
            ax.scatter(r["n"], r["effect"], s=26,
                       color=COLORS[r["verdict"]], alpha=0.85, zorder=3)
        # annotate the most extreme |effect| cells for readability
        for r in sorted(sub, key=lambda r: -abs(r["effect"]))[:4]:
            ax.annotate(r["event_type"], (r["n"], r["effect"]),
                        fontsize=6.5, xytext=(4, 4),
                        textcoords="offset points")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_xscale("log")
        ax.set_title(f"{tf}  ({len(sub)} cells)")
        ax.set_xlabel("n events (log)")
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("effect: mean MFE − control MFE (ATR units)")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=v)
               for v, c in COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False)
    fig.suptitle(args.title)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"figure: {out}")


if __name__ == "__main__":
    main()
