"""Pre-registered lever audits for the g7retry2 campaign (§11.17).

Computes, from the on-disk baseline replay caches ONLY (no new replays):

- Z2  : Bachira/Barou same-tick same-symbol fired-proposal overlap (must be 0).
- Z4 / AB5 / AA4 : squad mean-of-window-mean OOS TQS, g7retry1 vs g7retry2,
  both arms (tolerance -0.02).
- AA-M: Chigiri mean entry-efficiency TQS component, g7retry1 vs g7retry2.
- AB audit: Barou per-symbol n / mean TQS split (EURUSD slice vs E001 prior).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_final_verdict import (
    _g7_windows,
    load_oos_trades,
)

REV = Path("programs/M001_multi_agent_ensemble/reviews")
WINDOWS = _g7_windows()


def _load(tag: str) -> list[dict]:
    return load_oos_trades(REV / f"g7_replay_cache_{tag}" / "trades.jsonl", WINDOWS)


def squad_mean_of_window_means(trades: list[dict]) -> tuple[float, list[float]]:
    # load_oos_trades already attaches _window_idx to every kept trade.
    by_w: dict[int, list[float]] = defaultdict(list)
    for t in trades:
        by_w[t["_window_idx"]].append(t["tqs_components"]["tqs"])
    means = [sum(v) / len(v) for _, v in sorted(by_w.items()) if v]
    return sum(means) / len(means), [round(m, 4) for m in means]


def z2_overlap(tag: str) -> int:
    """Fired-proposal overlap Bachira x Barou on (tick_id, symbol)."""
    seen: dict[str, set[tuple[int, str]]] = {"bachira_meguru": set(), "barou_shoei": set()}
    with open(REV / f"g7_replay_cache_{tag}" / "proposals_all.jsonl") as fh:
        for line in fh:
            p = json.loads(line)
            a = p.get("agent_id")
            if a in seen:
                seen[a].add((p["tick_id"], p["symbol"]))
    return len(seen["bachira_meguru"] & seen["barou_shoei"])


def agent_slice(trades: list[dict], agent: str) -> list[dict]:
    return [t for t in trades if t["agent_id"] == agent]


def main() -> None:
    out: dict = {}
    for arm in ("phi41", "arm4"):
        t1 = _load(f"g7retry1-{arm}")
        t2 = _load(f"g7retry2-{arm}")
        m1, w1 = squad_mean_of_window_means(t1)
        m2, w2 = squad_mean_of_window_means(t2)
        out[f"squad_tqs_{arm}"] = {
            "g7retry1_mean_of_window_means": round(m1, 4),
            "g7retry2_mean_of_window_means": round(m2, 4),
            "delta": round(m2 - m1, 4),
            "tolerance": -0.02,
            "pass": (m2 - m1) >= -0.02,
            "g7retry1_window_means": w1,
            "g7retry2_window_means": w2,
        }
        # AA-M: Chigiri mean entry-efficiency component
        eff1 = [t["tqs_components"]["efficiency"] for t in agent_slice(t1, "chigiri_hyoma")]
        eff2 = [t["tqs_components"]["efficiency"] for t in agent_slice(t2, "chigiri_hyoma")]
        out[f"aam_chigiri_efficiency_{arm}"] = {
            "g7retry1_mean": round(sum(eff1) / len(eff1), 4) if eff1 else None,
            "g7retry2_mean": round(sum(eff2) / len(eff2), 4) if eff2 else None,
            "n1": len(eff1),
            "n2": len(eff2),
            "pass_strict_increase": bool(eff1 and eff2 and (sum(eff2) / len(eff2)) > (sum(eff1) / len(eff1))),
        }
        # AB audit: Barou per-symbol split
        sym: dict[str, list[float]] = defaultdict(list)
        for t in agent_slice(t2, "barou_shoei"):
            sym[t["symbol"]].append(t["tqs_components"]["tqs"])
        out[f"ab_barou_symbol_split_{arm}"] = {
            s: {"n": len(v), "mean_tqs": round(sum(v) / len(v), 4)} for s, v in sorted(sym.items())
        }
        # Nagi volume context for Z5
        out[f"z5_nagi_n_{arm}"] = {
            "g7retry1_n": len(agent_slice(t1, "nagi_seishiro")),
            "g7retry2_n": len(agent_slice(t2, "nagi_seishiro")),
        }
        # Bachira volume for Z3 floor context
        out[f"z3_bachira_n_{arm}"] = {
            "g7retry1_n": len(agent_slice(t1, "bachira_meguru")),
            "g7retry2_n": len(agent_slice(t2, "bachira_meguru")),
        }
        out[f"z2_overlap_{arm}"] = z2_overlap(f"g7retry2-{arm}")

    dest = REV / "g7retry2_lever_audits.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
