#!/usr/bin/env python3
"""Barou v1.x USDJPY loss autopsy (READ-ONLY on AN-5 design tapes).

Reads the already-generated AN-5 single-agent isolation tapes for
barou_shoei on USDJPY H4 (K=5 staggered starts, DESIGN split) and screens
his loss distribution for candidate single-mechanism balance patches.

Methodology (matches parent AN-5 study):
  - filter agent_id == barou_shoei, symbol == USDJPY
  - burn-in: discard trades entering before start_date + 92 days
  - honest cost: pnl_c = pnl_pips - 1.0; r_c = pnl_c / source_sl_pips
  - primary analysis on start_0; other starts are stability checks
    (a candidate must show the same direction of effect in >= 4/5 starts)

All numbers are IN-SAMPLE (design data, already consumed). No replays are
run; no verdicts re-judged. Output: results.json next to this script.
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
TAPES = os.path.join(
    HERE, "..", "phase_an_field_followups", "results", "AN-5", "USDJPY", "design"
)
START_DATES = {
    "start_0": "2015-01-01",
    "start_1": "2015-04-01",
    "start_2": "2015-07-01",
    "start_3": "2015-10-01",
    "start_4": "2016-01-01",
}
BURN_IN_DAYS = 92
COST_PIPS = 1.0
PF_FLOOR = 1.15
MIN_MEDIAN_N = 60
MIN_MEAN_R = 0.05


def load_start(start_key):
    path = os.path.join(TAPES, start_key, "trades.jsonl")
    cutoff = datetime.fromisoformat(START_DATES[start_key]).replace(
        tzinfo=timezone.utc
    ) + timedelta(days=BURN_IN_DAYS)
    trades = []
    with open(path) as f:
        for line in f:
            t = json.loads(line)
            if t["agent_id"] != "barou_shoei" or t["symbol"] != "USDJPY":
                continue
            et = datetime.fromisoformat(t["entry_time"])
            if et < cutoff:
                continue
            sl = t.get("source_sl_pips")
            if sl is None:
                sl = abs(t["entry"] - t["stop"]) * 100.0
            t["_entry_dt"] = et
            t["_pnl_c"] = t["pnl_pips"] - COST_PIPS
            t["_r_c"] = t["_pnl_c"] / sl if sl > 0 else 0.0
            t["_sl_pips"] = sl
            t["_stop_atr"] = sl / t["source_atr_pips"] if t["source_atr_pips"] else None
            trades.append(t)
    return trades


def kpis(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0, "pf": None, "mean_r": None, "win_rate": None,
                "sum_pips": None}
    wins = [t["_pnl_c"] for t in trades if t["_pnl_c"] > 0]
    losses = [t["_pnl_c"] for t in trades if t["_pnl_c"] <= 0]
    gp, gl = sum(wins), abs(sum(losses))
    pf = (gp / gl) if gl > 0 else math.inf
    return {
        "n": n,
        "pf": round(pf, 4),
        "mean_r": round(sum(t["_r_c"] for t in trades) / n, 4),
        "win_rate": round(len(wins) / n, 4),
        "sum_pips": round(sum(t["_pnl_c"] for t in trades), 1),
    }


# ---------------------------------------------------------------- slicers

SESSIONS = {"asia": range(0, 7), "london": range(7, 13),
            "ny": range(13, 19), "rollover": range(19, 24)}


def session_of(t):
    h = t["_entry_dt"].hour
    for name, rng in SESSIONS.items():
        if h in rng:
            return name
    return "?"


def dow_of(t):
    return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][t["_entry_dt"].weekday()]


def bars_bucket(t):
    b = t["bars_held"]
    if b <= 5:
        return "0-5"
    if b <= 15:
        return "6-15"
    if b <= 30:
        return "16-30"
    return ">30"


def quartile_edges(values):
    v = sorted(values)
    n = len(v)
    return [v[n // 4], v[n // 2], v[(3 * n) // 4]]


def quartile_slicer(field_getter, edges):
    def f(t):
        x = field_getter(t)
        if x is None:
            return "na"
        if x <= edges[0]:
            return "q1"
        if x <= edges[1]:
            return "q2"
        if x <= edges[2]:
            return "q3"
        return "q4"
    return f


def main():
    data = {k: load_start(k) for k in START_DATES}
    s0 = data["start_0"]

    out = {
        "meta": {
            "experiment": "barou_v1x_usdjpy_autopsy",
            "source": "AN-5 USDJPY design tapes (IN-SAMPLE, already consumed)",
            "cost_pips": COST_PIPS,
            "burn_in_days": BURN_IN_DAYS,
            "quartile_edges_from": "start_0 post-burn-in (fixed thresholds "
                                   "applied to all starts, i.e. deployable)",
        },
        "overall": {k: kpis(v) for k, v in data.items()},
    }

    # ---- 1. loss anatomy (start_0 primary)
    losers = [t for t in s0 if t["_pnl_c"] <= 0]
    winners = [t for t in s0 if t["_pnl_c"] > 0]
    r_vals = sorted(t["_r_c"] for t in s0)
    n = len(r_vals)
    full_stop = [t for t in losers if t["r_multiple"] <= -0.99]
    exit_reasons = defaultdict(lambda: {"n": 0, "pips": 0.0})
    for t in s0:
        er = exit_reasons[t["exit_reason"]]
        er["n"] += 1
        er["pips"] += t["_pnl_c"]
    loser_mfe_r = [t["mfe_pips"] / t["_sl_pips"] for t in losers]
    out["loss_anatomy_start0"] = {
        "n": n,
        "win_rate": round(len(winners) / n, 4),
        "r_percentiles": {p: round(r_vals[int(p / 100 * (n - 1))], 3)
                          for p in (5, 10, 25, 50, 75, 90, 95)},
        "losers": {
            "n": len(losers),
            "full_stop_share": round(len(full_stop) / len(losers), 4),
            "mean_loss_r": round(sum(t["_r_c"] for t in losers) / len(losers), 4),
            "mfe_over_sl_mean": round(sum(loser_mfe_r) / len(loser_mfe_r), 4),
            "losers_with_mfe_ge_0.5R": round(
                sum(1 for x in loser_mfe_r if x >= 0.5) / len(loser_mfe_r), 4),
            "losers_with_mfe_ge_1.0R": round(
                sum(1 for x in loser_mfe_r if x >= 1.0) / len(loser_mfe_r), 4),
        },
        "exit_reasons": {k: {"n": v["n"], "sum_pips": round(v["pips"], 1)}
                         for k, v in sorted(exit_reasons.items())},
        "bars_held_distribution": {
            b: sum(1 for t in s0 if bars_bucket(t) == b)
            for b in ("0-5", "6-15", "16-30", ">30")
        },
    }

    # ---- 2. slicers (quartile edges fixed on start_0)
    edges = {
        "regime_fit": quartile_edges([t["source_regime_fit"] for t in s0]),
        "conviction": quartile_edges([t["source_conviction"] for t in s0]),
        "atr": quartile_edges([t["source_atr_pips"] for t in s0]),
        "stop_atr": quartile_edges([t["_stop_atr"] for t in s0]),
    }
    out["quartile_edges_start0"] = {k: [round(x, 4) for x in v]
                                    for k, v in edges.items()}

    slicers = {
        "session": session_of,
        "day_of_week": dow_of,
        "regime_fit_q": quartile_slicer(lambda t: t["source_regime_fit"],
                                        edges["regime_fit"]),
        "conviction_q": quartile_slicer(lambda t: t["source_conviction"],
                                        edges["conviction"]),
        "atr_q": quartile_slicer(lambda t: t["source_atr_pips"], edges["atr"]),
        "stop_atr_q": quartile_slicer(lambda t: t["_stop_atr"],
                                      edges["stop_atr"]),
        "direction": lambda t: t["direction"],
        "bars_held_b": bars_bucket,
    }

    out["slices_start0"] = {}
    for sname, fn in slicers.items():
        groups = defaultdict(list)
        for t in s0:
            groups[fn(t)].append(t)
        out["slices_start0"][sname] = {g: kpis(v)
                                       for g, v in sorted(groups.items())}

    # MFE-first analysis on losers, per start (informational, exit-mechanism
    # evidence rather than an entry filter)
    out["loser_mfe_by_start"] = {}
    for k, trades in data.items():
        ls = [t for t in trades if t["_pnl_c"] <= 0]
        mfe_r = [t["mfe_pips"] / t["_sl_pips"] for t in ls]
        out["loser_mfe_by_start"][k] = {
            "n_losers": len(ls),
            "share_mfe_ge_0.5R": round(
                sum(1 for x in mfe_r if x >= 0.5) / len(ls), 4),
            "share_mfe_ge_1.0R": round(
                sum(1 for x in mfe_r if x >= 1.0) / len(ls), 4),
        }

    # ---- 3. counterfactual filters: drop each single slice value, all starts
    candidates = []
    n_screened = 0
    for sname, fn in slicers.items():
        values = sorted({fn(t) for t in s0})
        for val in values:
            n_screened += 1
            per_start = {}
            improves = 0
            for k, trades in data.items():
                base = kpis(trades)
                kept = [t for t in trades if fn(t) != val]
                cf = kpis(kept)
                per_start[k] = {
                    "base_pf": base["pf"], "cf_pf": cf["pf"],
                    "cf_n": cf["n"], "cf_mean_r": cf["mean_r"],
                    "removed_n": base["n"] - cf["n"],
                }
                if cf["pf"] is not None and cf["pf"] > base["pf"]:
                    improves += 1
            pooled_kept = [t for k, trades in data.items() for t in trades
                           if fn(t) != val]
            pooled = kpis(pooled_kept)
            cf_pfs = sorted(v["cf_pf"] if v["cf_pf"] is not None else -1.0
                            for v in per_start.values())
            cf_ns = sorted(v["cf_n"] for v in per_start.values())
            median_cf_pf = cf_pfs[2]
            median_cf_n = cf_ns[2]
            passes = (pooled["pf"] is not None
                      and median_cf_pf > PF_FLOOR and pooled["pf"] > PF_FLOOR
                      and median_cf_n >= MIN_MEDIAN_N
                      and pooled["mean_r"] >= MIN_MEAN_R)
            candidates.append({
                "filter": f"drop {sname}={val}",
                "slice": sname, "value": val,
                "pooled_cf": pooled,
                "median_cf_pf": median_cf_pf,
                "median_cf_n": median_cf_n,
                "improves_starts": improves,
                "stable_4of5": improves >= 4,
                "passes_charter_gate": passes,
                "per_start": per_start,
            })

    candidates.sort(key=lambda c: (c["passes_charter_gate"],
                                   c["stable_4of5"],
                                   c["median_cf_pf"] or 0), reverse=True)
    out["n_filters_screened"] = n_screened
    out["candidate_filters"] = candidates

    # ---- 3b. diagnostic: is regime_fit just a transform of ATR?
    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0] * len(vals)
        for pos, i in enumerate(order):
            r[i] = pos
        return r

    rf = [t["source_regime_fit"] for t in s0]
    at = [t["source_atr_pips"] for t in s0]
    ra, rb = rank(rf), rank(at)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((a - ma) * (b - mb) for a, b in zip(ra, rb))
    sda = math.sqrt(sum((a - ma) ** 2 for a in ra))
    sdb = math.sqrt(sum((b - mb) ** 2 for b in rb))
    out["regime_fit_vs_atr_spearman_start0"] = round(cov / (sda * sdb), 4)

    # ---- 3c. monotonic threshold rule: drop stop_dist > 2.28x ATR
    # (start_0 median of stop/ATR; more plausible than dropping just q3)
    thr = edges["stop_atr"][1]
    combo = {"threshold_stop_atr": round(thr, 4), "per_start": {}}
    improves = 0
    for k, trades in data.items():
        base = kpis(trades)
        kept = [t for t in trades if t["_stop_atr"] is not None
                and t["_stop_atr"] <= thr]
        cf = kpis(kept)
        combo["per_start"][k] = {"base_pf": base["pf"], "cf_pf": cf["pf"],
                                 "cf_n": cf["n"], "cf_mean_r": cf["mean_r"]}
        if cf["pf"] and cf["pf"] > base["pf"]:
            improves += 1
    pooled = kpis([t for tr in data.values() for t in tr
                   if t["_stop_atr"] is not None and t["_stop_atr"] <= thr])
    combo["pooled_cf"] = pooled
    combo["improves_starts"] = improves
    out["combined_filter_stop_le_median_atr"] = combo

    # ---- 3d. breakeven-at-1R-MFE upper-bound counterfactual.
    # Losers whose MFE reached >= 1.0R are converted to a breakeven exit
    # (0 pips gross, so -COST_PIPS net). Winners are left UNTOUCHED — this
    # is an OPTIMISTIC upper bound, because a real BE stop would also
    # convert some eventual TP winners (that retraced to entry after +1R)
    # into breakeven exits. The tape has no intrabar path beyond MAE/MFE,
    # so the true counterfactual is NOT computable here; a replay is needed.
    be = {"per_start": {}, "note": "upper bound only; winners' retrace "
          "timing unknown from tapes"}
    improves = 0
    for k, trades in data.items():
        base = kpis(trades)
        adj = []
        n_converted = 0
        for t in trades:
            t2 = dict(t)
            if t["_pnl_c"] <= 0 and t["mfe_pips"] / t["_sl_pips"] >= 1.0:
                t2["_pnl_c"] = -COST_PIPS
                t2["_r_c"] = -COST_PIPS / t["_sl_pips"]
                n_converted += 1
            adj.append(t2)
        cf = kpis(adj)
        be["per_start"][k] = {"base_pf": base["pf"], "cf_pf": cf["pf"],
                              "cf_n": cf["n"], "cf_mean_r": cf["mean_r"],
                              "losers_converted": n_converted}
        if cf["pf"] and cf["pf"] > base["pf"]:
            improves += 1
    be["improves_starts"] = improves
    out["breakeven_at_1R_upper_bound"] = be

    # ---- 3e. stop/ATR threshold sensitivity sweep (is the gate a
    # knife-edge artifact of the in-sample median, or robust to threshold?)
    sweep = {}
    for thr2 in (1.75, 2.0, 2.25, 2.5, 2.75, 3.0):
        sweep[str(thr2)] = {
            k: kpis([t for t in trades if t["_stop_atr"] <= thr2])
            for k, trades in data.items()
        }
    out["stop_atr_threshold_sweep"] = sweep

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(out, f, indent=1)

    # ---- console report
    print("=== overall (1x cost) ===")
    for k, v in out["overall"].items():
        print(f"  {k}: {v}")
    print("\n=== loss anatomy start_0 ===")
    print(json.dumps(out["loss_anatomy_start0"], indent=1))
    print("\n=== quartile edges (start_0) ===")
    print(json.dumps(out["quartile_edges_start0"], indent=1))
    print("\n=== slices start_0 ===")
    for sname, groups in out["slices_start0"].items():
        print(f"\n-- {sname} --")
        for g, kp in groups.items():
            print(f"  {g:10s} {kp}")
    print("\n=== loser MFE by start ===")
    print(json.dumps(out["loser_mfe_by_start"], indent=1))
    print(f"\n=== candidate filters (screened {n_screened}) ===")
    for c in candidates:
        if not (c["passes_charter_gate"] or c["stable_4of5"]):
            continue
        print(f"\n{c['filter']}: pooled {c['pooled_cf']}, "
              f"median_cf_pf={c['median_cf_pf']}, "
              f"improves {c['improves_starts']}/5, "
              f"gate={'PASS' if c['passes_charter_gate'] else 'fail'}")
        for k, v in c["per_start"].items():
            print(f"   {k}: base_pf={v['base_pf']} -> cf_pf={v['cf_pf']} "
                  f"(n={v['cf_n']}, meanR={v['cf_mean_r']}, "
                  f"removed={v['removed_n']})")

    print("\n=== regime_fit vs atr spearman (start_0) ===")
    print(out["regime_fit_vs_atr_spearman_start0"])
    print("\n=== combined filter: stop <= median(stop/ATR) ===")
    print(json.dumps(out["combined_filter_stop_le_median_atr"], indent=1))
    print("\n=== breakeven-at-1R upper bound ===")
    print(json.dumps(out["breakeven_at_1R_upper_bound"], indent=1))


if __name__ == "__main__":
    main()
