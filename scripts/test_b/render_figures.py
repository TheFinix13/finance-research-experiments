"""Render Test B diagnostic figures into output/test_b/figures/.

Produces:
  fig1_reach_curves_per_cell.png          — event vs control reach probability
                                            at thresholds {0.5,1,1.5,2,3,4}R,
                                            faceted by (TF, direction).
  fig2_direction_split_headline.png       — up vs down reach curves on the
                                            lowest-raw-p cell (annotated as
                                            "best raw cell, NOT a survivor").
  fig3_cross_pair_replication.png         — placeholder note (Stage 3 stopped).
  fig4_friction_conditional.png           — placeholder note (Stage 4 stopped).
  fig5_verdict_registry.png               — verdict bar chart over the 12 cells
                                            (effect_pips with verdict colour).

Usage:
    python scripts/test_b/render_figures.py \
        --stage1-registry output/test_b/stage1_EURUSD_screen_<stamp>.jsonl \
        --events output/test_b/stage1_EURUSD_screen_<stamp>_events.jsonl \
        --out output/test_b/figures
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.test_b._lib import REACH_THRESHOLDS, read_jsonl

VERDICT_COLOURS = {
    "alive": "#2e7d32",
    "parked_weak_effect": "#f9a825",
    "parked_insufficient_n": "#90a4ae",
    "dead": "#c62828",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stage1-registry", required=True)
    p.add_argument("--events", required=False, default=None)
    p.add_argument("--out", default="output/test_b/figures")
    p.add_argument("--stage3-stop", default=None,
                   help="Stage 3 stop-record JSON (if Stage 3 didn't run).")
    p.add_argument("--stage4-stop", default=None)
    return p.parse_args()


def fig1_reach_curves_per_cell(rows: list[dict], out_path: Path) -> None:
    cells = sorted(rows, key=lambda r: (r["tf"], -r["direction"], r["M_atr"]))
    n = len(cells)
    cols = 4
    rws = (n + cols - 1) // cols
    fig, axes = plt.subplots(rws, cols, figsize=(4 * cols, 3.2 * rws),
                             sharey=True)
    axes = np.array(axes).ravel()
    thr = list(REACH_THRESHOLDS)
    for ax, r in zip(axes, cells):
        ev = [r["reach_event"][f"{k}R"] for k in thr]
        ct = [r["reach_control"][f"{k}R"] for k in thr]
        ax.plot(thr, ev, marker="o", color="#1565c0", lw=1.6,
                label="events")
        ax.plot(thr, ct, marker="s", color="#9e9e9e", lw=1.4, ls="--",
                label="controls")
        # subtle verdict tint
        ax.set_facecolor({**VERDICT_COLOURS,
                          "stopped": "#ffffff"}.get(r["verdict"],
                                                    "#ffffff") + "10")
        ax.set_title(f"{r['cell_id']}\nn={r['n_events']}  p={r['p_value']:.3f}  "
                     f"{r['verdict']}", fontsize=9)
        ax.set_xlabel("threshold (R-multiples)")
        ax.set_ylabel("P(reach)")
        ax.set_ylim(0.0, 1.0)
        ax.grid(True, alpha=0.25)
    for ax in axes[len(cells):]:
        ax.set_visible(False)
    axes[0].legend(loc="lower left", fontsize=8, frameon=False)
    fig.suptitle("Test B Stage 1 — reach probabilities, event vs hour-matched "
                 "controls (EURUSD screen 2015-2021)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig2_direction_split_headline(rows: list[dict], out_path: Path) -> None:
    powered = [r for r in rows if r["n_events"] >= 30]
    if not powered:
        return
    headline = min(powered, key=lambda r: r["p_value"])
    tf = headline["tf"]; M_atr = headline["M_atr"]
    pair = [r for r in rows
            if r["tf"] == tf and r["M_atr"] == M_atr and r["n_events"] >= 30]
    if len(pair) < 2:
        pair = sorted(
            [r for r in rows if r["tf"] == tf and r["n_events"] >= 30],
            key=lambda r: r["p_value"])[:2]
    thr = list(REACH_THRESHOLDS)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for r in pair:
        label = f"{r['cell_id']}  (n={r['n_events']}, p={r['p_value']:.3f})"
        ev = [r["reach_event"][f"{k}R"] for k in thr]
        ax.plot(thr, ev, marker="o", lw=1.8, label=label)
        ct = [r["reach_control"][f"{k}R"] for k in thr]
        ax.plot(thr, ct, marker="s", lw=1.2, ls="--", alpha=0.6,
                label=f"  control  ({r['cell_id']})")
    ax.set_xlabel("threshold (R-multiples; R = impulse height ÷ 4)")
    ax.set_ylabel("P(reach)")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, alpha=0.25)
    ax.set_title(
        f"Headline cell direction split  ({tf}, M_atr={M_atr}) — "
        "best raw p, NOT a survivor under BH-FDR", fontsize=10)
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig3_cross_pair_placeholder(out_path: Path, stop_record: dict | None
                                ) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.axis("off")
    msg = "Stage 3 cross-pair replication did NOT run."
    if stop_record:
        msg += "\n\nReason recorded in stop-record:\n" + json.dumps(
            {k: v for k, v in stop_record.items() if k != "upstream_stop"},
            indent=2)
    msg += "\n\nProtocol §3.7 stop rule: H1 (main) failed Stage 1 BH-FDR."
    ax.text(0.02, 0.98, msg, va="top", ha="left", fontsize=10,
            family="monospace")
    fig.suptitle("Test B Stage 3 — cross-pair replication (skipped)",
                 fontsize=12)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig4_friction_placeholder(out_path: Path, stop_record: dict | None
                              ) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.axis("off")
    msg = "Stage 4 friction conditioning did NOT run."
    if stop_record:
        msg += "\n\nReason recorded in stop-record:\n" + json.dumps(
            {k: v for k, v in stop_record.items() if k != "upstream_stop"},
            indent=2)
    msg += ("\n\nFriction quartile cutoffs are still frozen, available "
            "under output/test_b/stage1_friction_reference_*.json, for "
            "any future pre-registered re-look.")
    ax.text(0.02, 0.98, msg, va="top", ha="left", fontsize=10,
            family="monospace")
    fig.suptitle("Test B Stage 4 — friction conditioning (skipped)",
                 fontsize=12)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def fig5_verdict_registry(rows: list[dict], out_path: Path) -> None:
    rows = sorted(rows, key=lambda r: (r["tf"], -r["direction"], r["M_atr"]))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    cells = [r["cell_id"] for r in rows]
    effects = [r["effect_pips"] for r in rows]
    colours = [VERDICT_COLOURS.get(r["verdict"], "#aaaaaa") for r in rows]
    ax1.barh(cells, effects, color=colours)
    ax1.axvline(0, color="black", lw=0.7)
    ax1.set_xlabel("effect_pips (event MFE − control MFE)")
    ax1.set_title("Per-cell effect", fontsize=10)
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.25, axis="x")

    ev_p = [r["headline_reach_event"] * 100 for r in rows]
    ct_p = [r["headline_reach_control"] * 100 for r in rows]
    y = np.arange(len(rows))
    ax2.barh(y - 0.18, ev_p, 0.36, color="#1565c0", label="events")
    ax2.barh(y + 0.18, ct_p, 0.36, color="#9e9e9e", label="controls")
    ax2.set_yticks(y); ax2.set_yticklabels(cells)
    ax2.invert_yaxis()
    ax2.set_xlabel("P(MFE ≥ 0.5R within W bars)  (%)")
    ax2.set_title("Headline reach probability", fontsize=10)
    ax2.set_xlim(0, 100)
    ax2.grid(True, alpha=0.25, axis="x")
    ax2.legend(loc="lower right", fontsize=9)

    handles = [plt.Line2D([], [], marker="s", ls="", color=c, label=v)
               for v, c in VERDICT_COLOURS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Test B Stage 1 verdict registry — EURUSD screen 2015-2021",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    rows = read_jsonl(Path(args.stage1_registry))

    s3_stop = (json.loads(Path(args.stage3_stop).read_text())
               if args.stage3_stop else None)
    s4_stop = (json.loads(Path(args.stage4_stop).read_text())
               if args.stage4_stop else None)

    fig1_reach_curves_per_cell(rows, out / "fig1_reach_curves_per_cell.png")
    fig2_direction_split_headline(rows,
                                  out / "fig2_direction_split_headline.png")
    fig3_cross_pair_placeholder(out / "fig3_cross_pair_replication.png",
                                s3_stop)
    fig4_friction_placeholder(out / "fig4_friction_conditional.png",
                              s4_stop)
    fig5_verdict_registry(rows, out / "fig5_verdict_registry.png")

    print(f"figures written to {out}/")
    for p in sorted(out.iterdir()):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
