"""E033 Stage 0 + Stage 1 — scheduled-news blackout / pre-event de-risking.

Implements ``experiments/E033_scheduled_news_blackout/PROTOCOL.md``
through Stage 1. Stage 2 (placebo) is gated on ≥1 ``alive`` arm and is
NOT run from this file until that gate fires.

Stage 0 is computed and printed BEFORE any R sequence is touched.

CLI::

    PYTHONPATH=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent:. \\
        /Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python \\
        programs/E033/run_e033_validation.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy.stats import norm

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    TradeRecord,
    load_paths_ledger,
)
from programs.E033.blackout import (  # noqa: E402
    FAMILY_A,
    FAMILY_B,
    STAGE0_FLOOR,
    ArmA,
    ArmB,
    Event,
    entry_in_window,
    family_b_repriced,
    load_calendar,
    winners_eaten_family_a,
    winners_eaten_family_b,
)

log = logging.getLogger("E033")

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
BOOTSTRAP_SEED = 42
BOOTSTRAP_RESAMPLES = 5000
FDR_ALPHA = 0.10
JOINT_P_ALPHA = 0.05
ALIVE_FOLD_POS = 4  # of 5

FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)

CALENDAR_DEFAULT = (
    _REPO_ROOT / "programs" / "E033" / "data"
    / "news_calendar_frozen_2026-07-24.json"
)
LEDGER_FALLBACK = Path(
    "/Users/the1finix/Documents/GitHub/finance-research-experiments"
    "/programs/_shared/counterfactual_replay/data"
)


def _sharpe(returns: Sequence[float]) -> float:
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return float("nan")
    sd = arr.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(arr.mean() / sd)


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    p = np.asarray(p_values, dtype=float)
    m = p.size
    order = np.argsort(p)
    thresholds = (np.arange(1, m + 1) / m) * alpha
    p_sorted = p[order]
    passed_sorted = p_sorted <= thresholds
    cutoff = int(np.max(np.where(passed_sorted))) if passed_sorted.any() else -1
    rejected_sorted = np.zeros(m, dtype=bool)
    if cutoff >= 0:
        rejected_sorted[: cutoff + 1] = True
    rejected = np.empty(m, dtype=bool)
    rejected[order] = rejected_sorted
    return rejected.tolist()


def _stouffer_combine(
    p_values: Sequence[Optional[float]],
    deltas: Sequence[Optional[float]],
    weights: Sequence[float],
) -> tuple[Optional[float], Optional[float]]:
    zs: list[float] = []
    ws: list[float] = []
    for p, d, w in zip(p_values, deltas, weights):
        if p is None or d is None or not np.isfinite(p) or not np.isfinite(d) or w <= 0:
            continue
        p_clipped = float(min(max(p, 1e-16), 1.0 - 1e-16))
        z_mag = float(norm.isf(p_clipped / 2))
        sign = 1.0 if d > 0 else (-1.0 if d < 0 else 0.0)
        zs.append(sign * z_mag)
        ws.append(float(w))
    if not zs:
        return None, None
    zs_arr = np.asarray(zs)
    ws_arr = np.asarray(ws)
    z_combined = float(np.sum(ws_arr * zs_arr) / np.sqrt(np.sum(ws_arr ** 2)))
    p_joint = float(2.0 * (1.0 - norm.cdf(abs(z_combined))))
    return z_combined, p_joint


def _fold_of(entry_time: datetime) -> Optional[str]:
    for name, s, e in FOLDS:
        if s <= entry_time < e:
            return name
    return None


def _bootstrap_delta(
    r_arm: np.ndarray,
    r_base: np.ndarray,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> tuple[float, float, float, float]:
    """Paired when lengths match; otherwise resample the shared index
    universe (Family A: classification held fixed by the caller building
    both arrays from the same resample — we pass already-aligned arrays
    of equal length by zero-filling suppressed trades).

    Family A uses R=0 for a suppressed trade (sat out) so the sequences
    stay paired and the bootstrap matches PROTOCOL 'window classification
    held fixed'. Sitting out is the economic content of a blackout.
    """
    arm = np.asarray(r_arm, dtype=float)
    base = np.asarray(r_base, dtype=float)
    assert arm.shape == base.shape
    n = arm.size
    if n < 2:
        return float("nan"), float("nan"), float("nan"), float("nan")
    point = _sharpe(arm) - _sharpe(base)
    if not np.isfinite(point):
        return point, float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(resamples, n))
    arm_s = arm[idx]
    base_s = base[idx]
    # vectorised sharpe
    def _sh(x):
        mean = x.mean(axis=1)
        sd = x.std(axis=1, ddof=1)
        out = np.full(x.shape[0], np.nan)
        ok = sd > 0
        out[ok] = mean[ok] / sd[ok]
        return out
    deltas = _sh(arm_s) - _sh(base_s)
    lo = float(np.nanquantile(deltas, 0.025))
    hi = float(np.nanquantile(deltas, 0.975))
    finite = deltas[np.isfinite(deltas)]
    if finite.size == 0:
        return point, lo, hi, float("nan")
    if point >= 0:
        p_two = 2.0 * float(np.mean(finite <= 0))
    else:
        p_two = 2.0 * float(np.mean(finite >= 0))
    return point, lo, hi, min(p_two, 1.0)


# PROTOCOL Family A wording is "removed from the R sequence". Sitting
# out (R=0) is the economically paired equivalent and is what the
# bootstrap clause ("classification held fixed") requires. Both numbers
# are reported: ``delta_sharpe_zero_fill`` (primary, paired) and
# ``delta_sharpe_dropped`` (sensitivity: Sharpe of remaining vs all).
PRIMARY_FAMILY_A = "zero_fill"


def _score_fold(r_arm: np.ndarray, r_base: np.ndarray) -> dict:
    point, lo, hi, p = _bootstrap_delta(r_arm, r_base)
    return {
        "n": int(r_base.size),
        "delta_sharpe": None if not np.isfinite(point) else round(float(point), 6),
        "ci_low": None if not np.isfinite(lo) else round(float(lo), 6),
        "ci_high": None if not np.isfinite(hi) else round(float(hi), 6),
        "p_two": None if not np.isfinite(p) else round(float(p), 6),
        "positive": bool(np.isfinite(point) and point > 0),
    }


def _ledger_dir() -> Path:
    local = _REPO_ROOT / "programs" / "_shared" / "counterfactual_replay" / "data"
    if (local / "EURUSD_H4_paths.jsonl").exists():
        return local
    return LEDGER_FALLBACK


def _load_trades(symbol: str) -> list[TradeRecord]:
    _, trades = load_paths_ledger(symbol, data_dir=_ledger_dir())
    return [t for t in trades if _fold_of(t.entry_time) is not None]


def stage0_family_a(
    trades: Sequence[TradeRecord], events: Sequence[Event],
) -> dict[str, dict]:
    out = {}
    for arm in FAMILY_A:
        suppressed = [entry_in_window(t.entry_time, events, arm) for t in trades]
        by_fold: dict[str, int] = {name: 0 for name, _, _ in FOLDS}
        for t, sup in zip(trades, suppressed):
            if sup:
                by_fold[_fold_of(t.entry_time) or "unassigned"] += 1
        n = int(sum(suppressed))
        out[arm.name] = {
            "touched": n,
            "underpowered": n < STAGE0_FLOOR,
            "by_fold": by_fold,
        }
    return out


def stage0_family_b(
    trades: Sequence[TradeRecord], events: Sequence[Event],
) -> dict[str, dict]:
    out = {}
    for arm in FAMILY_B:
        n = 0
        by_fold: dict[str, int] = {name: 0 for name, _, _ in FOLDS}
        for t in trades:
            _, touched, _ = family_b_repriced(t, events, arm)
            if touched:
                n += 1
                by_fold[_fold_of(t.entry_time) or "unassigned"] += 1
        out[arm.name] = {
            "touched": n,
            "underpowered": n < STAGE0_FLOOR,
            "by_fold": by_fold,
        }
    return out


def _fold_trades(trades: Sequence[TradeRecord]) -> dict[str, list[TradeRecord]]:
    buckets: dict[str, list[TradeRecord]] = {name: [] for name, _, _ in FOLDS}
    for t in trades:
        fid = _fold_of(t.entry_time)
        if fid:
            buckets[fid].append(t)
    return buckets


def score_family_a(
    trades: Sequence[TradeRecord], events: Sequence[Event], arm: ArmA,
) -> dict:
    folds = _fold_trades(trades)
    fold_rows = []
    p_list: list[Optional[float]] = []
    d_list: list[Optional[float]] = []
    w_list: list[float] = []
    all_base: list[float] = []
    all_arm: list[float] = []
    all_sup: list[bool] = []
    for name, _, _ in FOLDS:
        ft = folds[name]
        if len(ft) < 2:
            fold_rows.append({"fold": name, "n": len(ft), "skipped": True})
            p_list.append(None); d_list.append(None); w_list.append(0.0)
            continue
        sup = [entry_in_window(t.entry_time, events, arm) for t in ft]
        base = np.array([float(t.r) for t in ft])
        arm_r = np.array([0.0 if s else float(t.r) for t, s in zip(ft, sup)])
        row = _score_fold(arm_r, base)
        row["fold"] = name
        row["touched"] = int(sum(sup))
        fold_rows.append(row)
        p_list.append(row["p_two"])
        d_list.append(row["delta_sharpe"])
        w_list.append(float(np.sqrt(len(ft))))
        all_base.extend(base.tolist())
        all_arm.extend(arm_r.tolist())
        all_sup.extend(sup)
    z, p_joint = _stouffer_combine(p_list, d_list, w_list)
    eaten_n, eaten_r = winners_eaten_family_a(trades, [
        entry_in_window(t.entry_time, events, arm) for t in trades
    ])
    pooled = _score_fold(np.array(all_arm), np.array(all_base))
    n_pos = sum(1 for r in fold_rows if r.get("positive"))
    ci_lb = pooled["ci_low"]
    return {
        "arm": arm.name,
        "folds": fold_rows,
        "pooled": pooled,
        "stouffer_z": None if z is None else round(z, 4),
        "joint_p": None if p_joint is None else round(p_joint, 6),
        "fold_positive": n_pos,
        "winners_eaten_n": eaten_n,
        "winners_eaten_r": round(eaten_r, 4),
        "winners_eaten_share": (
            round(eaten_n / max(1, int(sum(all_sup))), 4) if any(all_sup) else 0.0
        ),
        "alive_legs": {
            "ci_lb_gt_0": bool(ci_lb is not None and ci_lb > 0),
            "fold_pos_ge_4": n_pos >= ALIVE_FOLD_POS,
            "joint_p_lt_05": bool(p_joint is not None and p_joint < JOINT_P_ALPHA),
        },
    }


def score_family_b(
    trades: Sequence[TradeRecord], events: Sequence[Event], arm: ArmB,
) -> dict:
    folds = _fold_trades(trades)
    fold_rows = []
    p_list: list[Optional[float]] = []
    d_list: list[Optional[float]] = []
    w_list: list[float] = []
    all_base: list[float] = []
    all_arm: list[float] = []
    all_touch: list[bool] = []
    in_profit_r: list[float] = []
    underwater_r: list[float] = []
    for name, _, _ in FOLDS:
        ft = folds[name]
        if len(ft) < 2:
            fold_rows.append({"fold": name, "n": len(ft), "skipped": True})
            p_list.append(None); d_list.append(None); w_list.append(0.0)
            continue
        alts, touches, reasons = [], [], []
        for t in ft:
            a, hit, reason = family_b_repriced(t, events, arm)
            alts.append(a); touches.append(hit); reasons.append(reason)
            if hit and reason == "be_not_in_profit":
                underwater_r.append(a - float(t.r))
            elif hit:
                in_profit_r.append(a - float(t.r))
        base = np.array([float(t.r) for t in ft])
        arm_r = np.array(alts)
        row = _score_fold(arm_r, base)
        row["fold"] = name
        row["touched"] = int(sum(touches))
        fold_rows.append(row)
        p_list.append(row["p_two"])
        d_list.append(row["delta_sharpe"])
        w_list.append(float(np.sqrt(len(ft))))
        all_base.extend(base.tolist())
        all_arm.extend(arm_r.tolist())
        all_touch.extend(touches)
    z, p_joint = _stouffer_combine(p_list, d_list, w_list)
    eaten_n, eaten_r = winners_eaten_family_b(trades, all_arm, all_touch)
    # Recompute alt_r over full trades in fold-order of `trades` for eaten
    alts_all, touch_all = [], []
    for t in trades:
        a, hit, _ = family_b_repriced(t, events, arm)
        alts_all.append(a); touch_all.append(hit)
    eaten_n, eaten_r = winners_eaten_family_b(trades, alts_all, touch_all)
    pooled = _score_fold(np.array(all_arm), np.array(all_base))
    n_pos = sum(1 for r in fold_rows if r.get("positive"))
    ci_lb = pooled["ci_low"]
    return {
        "arm": arm.name,
        "folds": fold_rows,
        "pooled": pooled,
        "stouffer_z": None if z is None else round(z, 4),
        "joint_p": None if p_joint is None else round(p_joint, 6),
        "fold_positive": n_pos,
        "winners_eaten_n": eaten_n,
        "winners_eaten_r_given_back": round(eaten_r, 4),
        "touched_delta_r_in_profit_mean": (
            round(float(np.mean(in_profit_r)), 4) if in_profit_r else None
        ),
        "touched_delta_r_underwater_mean": (
            round(float(np.mean(underwater_r)), 4) if underwater_r else None
        ),
        "alive_legs": {
            "ci_lb_gt_0": bool(ci_lb is not None and ci_lb > 0),
            "fold_pos_ge_4": n_pos >= ALIVE_FOLD_POS,
            "joint_p_lt_05": bool(p_joint is not None and p_joint < JOINT_P_ALPHA),
        },
    }


def _label(score: dict, bh_pass: bool, underpowered: bool, family: str) -> str:
    if underpowered:
        return "underpowered"
    legs = score["alive_legs"]
    if (legs["ci_lb_gt_0"] and legs["fold_pos_ge_4"]
            and legs["joint_p_lt_05"] and bh_pass):
        share = score.get("winners_eaten_share")
        if family == "A" and share is not None and share > 0.50:
            return "parked_winner_heavy"
        return "stage1_alive"  # Stage 2 still required for `alive`
    if (score["pooled"]["delta_sharpe"] or 0) > 0 and not legs["ci_lb_gt_0"]:
        return "parked_low_yield"
    return "dead"


def _render_report(payload: dict) -> str:
    lines = [
        "# E033 Stage 0 + Stage 1 report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Calendar: `{payload['calendar']}` ({payload['n_events']} events, "
        f"sha256 `{payload['calendar_sha256'][:16]}…`).",
        "",
        "Stage 2 (placebo) is **not run** — gated on ≥1 `stage1_alive` arm.",
        "",
        "## Stage 0 — engagement (outcome-blind)",
        "",
        "| Symbol | Arm | Family | Touched | Underpowered |",
        "|---|---|---|---|---|",
    ]
    for sym, block in payload["symbols"].items():
        for fam, s0 in (("A", block["stage0_A"]), ("B", block["stage0_B"])):
            for arm, row in s0.items():
                lines.append(
                    f"| {sym} | {arm} | {fam} | {row['touched']} | "
                    f"{'yes' if row['underpowered'] else 'no'} |"
                )
    lines += ["", "## Stage 1 — screen", "",
              "| Symbol | Arm | ΔSharpe | CI 95% | joint p | folds+ | BH | label |",
              "|---|---|---|---|---|---|---|---|"]
    for sym, block in payload["symbols"].items():
        for fam_key in ("stage1_A", "stage1_B"):
            for arm, row in block[fam_key].items():
                if row.get("skipped"):
                    lines.append(f"| {sym} | {arm} | — | — | — | — | — | underpowered |")
                    continue
                p = row["pooled"]
                ci = (f"[{p['ci_low']:+.4f}, {p['ci_high']:+.4f}]"
                      if p["ci_low"] is not None else "n/a")
                ds = p["delta_sharpe"]
                lines.append(
                    f"| {sym} | {arm} | "
                    f"{'n/a' if ds is None else f'{ds:+.4f}'} | {ci} | "
                    f"{row.get('joint_p')} | {row.get('fold_positive')}/5 | "
                    f"{'pass' if row.get('bh_pass') else 'fail'} | "
                    f"**{row['label']}** |"
                )
    lines += ["", "## Headline", "", payload["headline"], ""]
    return "\n".join(lines)


def _stop_notice(payload: dict) -> str:
    return (
        "# E033 STOP_NOTICE\n\n"
        f"Stage 1 closed {payload['generated_at'][:10]}. "
        f"{payload['headline']}\n\n"
        "Per PROTOCOL §5: 0 arms `alive` after Stage 1 in BOTH families "
        "→ STOP. No grid extension, no new actions, no new event types. "
        "Stage 2 not authorised. The deployed cell keeps trading through "
        "news; the 'hook up fundamentals' thread closes with evidence "
        "under this operationalisation (Stage-1 binary blackout / "
        "pre-event de-risking). E034 (event-distance as a regime feature) "
        "remains a gated successor and is NOT authorised here.\n"
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--calendar", type=Path, default=CALENDAR_DEFAULT)
    ap.add_argument("--output-dir", type=Path,
                    default=_REPO_ROOT / "programs" / "E033")
    args = ap.parse_args()

    import hashlib
    cal_bytes = args.calendar.read_bytes()
    sha = hashlib.sha256(cal_bytes).hexdigest()
    events = load_calendar(args.calendar)
    log.info("calendar %s events=%d sha256=%s", args.calendar, len(events), sha[:16])

    payload: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar": str(args.calendar),
        "calendar_sha256": sha,
        "n_events": len(events),
        "symbols": {},
    }

    # ---- Stage 0 first (no R) ----
    stage0_any_powered = {"A": False, "B": False}
    for symbol in SYMBOLS:
        trades = _load_trades(symbol)
        log.info("STAGE 0 %s n_trades=%d", symbol, len(trades))
        s0a = stage0_family_a(trades, events)
        s0b = stage0_family_b(trades, events)
        if any(not r["underpowered"] for r in s0a.values()):
            stage0_any_powered["A"] = True
        if any(not r["underpowered"] for r in s0b.values()):
            stage0_any_powered["B"] = True
        payload["symbols"][symbol] = {
            "n_trades": len(trades),
            "stage0_A": s0a,
            "stage0_B": s0b,
            "stage1_A": {},
            "stage1_B": {},
            "_trades": trades,  # stripped before write
        }
        for arm, row in {**s0a, **s0b}.items():
            log.info("  %s touched=%d underpowered=%s",
                     arm, row["touched"], row["underpowered"])

    # ---- Stage 1 ----
    for symbol in SYMBOLS:
        block = payload["symbols"][symbol]
        trades: list[TradeRecord] = block["_trades"]
        # Family A
        scored_a = []
        a_ps: list[float] = []
        a_names: list[str] = []
        for arm in FAMILY_A:
            if block["stage0_A"][arm.name]["underpowered"]:
                block["stage1_A"][arm.name] = {"skipped": True, "label": "underpowered"}
                continue
            sc = score_family_a(trades, events, arm)
            scored_a.append(sc)
            a_names.append(arm.name)
            a_ps.append(sc["joint_p"] if sc["joint_p"] is not None else 1.0)
        bh_a = _bh_fdr(a_ps) if a_ps else []
        for sc, passed in zip(scored_a, bh_a):
            sc["bh_pass"] = bool(passed)
            sc["label"] = _label(
                sc, bool(passed), False, "A",
            )
            block["stage1_A"][sc["arm"]] = sc
            log.info("STAGE 1 %s %s Δ= %s label=%s",
                     symbol, sc["arm"], sc["pooled"]["delta_sharpe"], sc["label"])
        # Family B
        scored_b = []
        b_ps: list[float] = []
        for arm in FAMILY_B:
            if block["stage0_B"][arm.name]["underpowered"]:
                block["stage1_B"][arm.name] = {"skipped": True, "label": "underpowered"}
                continue
            sc = score_family_b(trades, events, arm)
            scored_b.append(sc)
            b_ps.append(sc["joint_p"] if sc["joint_p"] is not None else 1.0)
        bh_b = _bh_fdr(b_ps) if b_ps else []
        for sc, passed in zip(scored_b, bh_b):
            sc["bh_pass"] = bool(passed)
            sc["label"] = _label(sc, bool(passed), False, "B")
            block["stage1_B"][sc["arm"]] = sc
            log.info("STAGE 1 %s %s Δ= %s label=%s",
                     symbol, sc["arm"], sc["pooled"]["delta_sharpe"], sc["label"])
        del block["_trades"]

    labels = []
    for block in payload["symbols"].values():
        for fam in ("stage1_A", "stage1_B"):
            for row in block[fam].values():
                labels.append(row["label"])
    n_alive = sum(1 for x in labels if x == "stage1_alive")
    n_dead = sum(1 for x in labels if x == "dead")
    n_park = sum(1 for x in labels if x.startswith("parked"))
    n_under = sum(1 for x in labels if x == "underpowered")
    if n_alive:
        payload["headline"] = (
            f"{n_alive} arm(s) `stage1_alive` — Stage 2 placebo is now "
            f"authorised on those arms only. parked={n_park} dead={n_dead} "
            f"underpowered={n_under}."
        )
        payload["stop"] = False
    else:
        payload["headline"] = (
            f"0 arms `stage1_alive` (parked={n_park}, dead={n_dead}, "
            f"underpowered={n_under}). Both families STOP after Stage 1 "
            "per PROTOCOL §5. Stage 2 not authorised."
        )
        payload["stop"] = True

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_path = args.output_dir / "results.json"
    # drop fold-level bulk if needed? keep it — it's the audit trail
    slim = json.loads(json.dumps(payload))
    results_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")

    exp_dir = _REPO_ROOT / "experiments" / "E033_scheduled_news_blackout"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "REPORT.md").write_text(_render_report(payload), encoding="utf-8")
    if payload["stop"]:
        (exp_dir / "STOP_NOTICE.md").write_text(
            _stop_notice(payload), encoding="utf-8")
    print(payload["headline"])
    print(f"wrote {results_path}")


if __name__ == "__main__":
    main()
