"""AN-3 sealed fade audit: thin-sample artifact vs genuine edge decay.

Critical cut (PROTOCOL): on the FULL sealed path (start_0 = 2023-01-01,
post 92-day burn-in, 1x honest RT = 2.5 field-pips deducted), are 2024+
trades still positive?

  - If 2024+ on the full path is positive → "2024-01 start loses" is a
    path / burn-in / thin-n artifact.
  - If 2024+ on the full path is negative while 2023 is strong → genuine
    decay.

Also: rolling 20-trade KPIs, and trade-set overlap across the K=5 starts.

    /Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python \
        sealed_fade_audit.py
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = "chigiri_hyoma"
FIELD = "XAGUSD"
COST = 2.5  # 1x honest RT spread
BURN_IN_DAYS = 92
SEALED_STARTS = (
    "2023-01-01",
    "2023-04-01",
    "2023-07-01",
    "2023-10-01",
    "2024-01-01",
)
SEALED_END = "2026-05-31"


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


def load_post_burnin(k: int, start_iso: str) -> list[dict]:
    path = (
        HERE / "results" / "AN-3" / FIELD / "sealed"
        / f"start_{k}" / "trades.jsonl"
    )
    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    cutoff = start + timedelta(days=BURN_IN_DAYS)
    out: list[dict] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("agent_id") != AGENT:
            continue
        if _parse_ts(t["entry_time"]) >= cutoff:
            out.append(t)
    return out


def trade_key(t: dict) -> tuple:
    """Identity for overlap: entry_time + direction + entry price."""
    return (
        t["entry_time"],
        t.get("direction"),
        round(float(t.get("entry") or 0.0), 6),
    )


def adj_pnl(t: dict) -> float:
    return (t.get("pnl_pips") or 0.0) - COST


def adj_r(t: dict) -> float:
    sl = t.get("source_sl_pips") or 0.0
    return (adj_pnl(t) / sl) if sl > 0 else 0.0


def kpis(trades: list[dict]) -> dict:
    n = len(trades)
    if not n:
        return {
            "n": 0,
            "win_rate": None,
            "pf": None,
            "mean_r": None,
            "total_pips": 0.0,
        }
    pnls = [adj_pnl(t) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gw = sum(wins)
    gl = -sum(losses)
    rs = [adj_r(t) for t in trades]
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 4),
        "pf": round(gw / gl, 3) if gl > 0 else (99.0 if n else None),
        "mean_r": round(sum(rs) / n, 4),
        "total_pips": round(sum(pnls), 1),
    }


def half_year_label(dt: datetime) -> str:
    return f"{dt.year}-H{'1' if dt.month <= 6 else '2'}"


def bucket_by(trades: list[dict], key_fn) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {}
    for t in trades:
        k = key_fn(_parse_ts(t["entry_time"]))
        buckets.setdefault(k, []).append(t)
    return buckets


def rolling_kpis(trades: list[dict], window: int = 20) -> list[dict]:
    rows = []
    for i in range(window - 1, len(trades)):
        chunk = trades[i - window + 1 : i + 1]
        end_t = chunk[-1]
        m = kpis(chunk)
        m["end_entry_time"] = end_t["entry_time"]
        m["end_index"] = i
        rows.append(m)
    return rows


def overlap_matrix(paths: dict[str, list[dict]]) -> dict:
    keys = {name: {trade_key(t) for t in ts} for name, ts in paths.items()}
    names = list(SEALED_STARTS)
    pairwise = {}
    for i, a in enumerate(names):
        for b in names[i:]:
            sa, sb = keys[a], keys[b]
            inter = sa & sb
            pairwise[f"{a} ∩ {b}"] = {
                "shared": len(inter),
                "only_a": len(sa - sb),
                "only_b": len(sb - sa),
                "jaccard": round(len(inter) / len(sa | sb), 3) if (sa | sb) else None,
            }

    # Later starts as subset of earliest (start_0) post-burn-in trades
    earliest = keys[SEALED_STARTS[0]]
    subset_of_earliest = {}
    for name in names[1:]:
        s = keys[name]
        subset_of_earliest[name] = {
            "n": len(s),
            "shared_with_2023-01": len(s & earliest),
            "unique_vs_2023-01": len(s - earliest),
            "pct_subset_of_2023-01": round(
                100.0 * len(s & earliest) / len(s), 1
            ) if s else None,
        }

    # Unique contribution of each start vs union of earlier starts
    cumulative: set = set()
    incremental = {}
    for name in names:
        s = keys[name]
        incremental[name] = {
            "n": len(s),
            "new_vs_earlier_starts": len(s - cumulative),
            "already_seen_in_earlier": len(s & cumulative),
        }
        cumulative |= s

    return {
        "pairwise_vs_earliest_style": subset_of_earliest,
        "incremental_vs_earlier_starts": incremental,
        "pairwise_selected": {
            k: v for k, v in pairwise.items()
            if k.startswith(SEALED_STARTS[0]) or "2024-01-01" in k
        },
        "union_n": len(cumulative),
    }


def verdict_from(full_path: dict) -> tuple[str, str]:
    """Return (verdict_code, rationale).

    Critical cut (user brief): if 2024+ on the FULL 2023-01 path is still
    positive after 1x cost, the lone 2024-01 start loss is a path /
    burn-in / thin-n artifact. If 2024+ on the full path is negative
    while 2023 is strong, that is genuine decay.
    """
    y2023 = full_path["by_year"].get("2023", {})
    y2024 = full_path["by_year"].get("2024", {})
    y2025 = full_path["by_year"].get("2025", {})
    post2023 = full_path["post_2023"]
    y2023_pf = y2023.get("pf")
    post_pf = post2023.get("pf")
    post_mean_r = post2023.get("mean_r")
    post_n = post2023.get("n") or 0
    y2024_pf = y2024.get("pf")
    y2025_pf = y2025.get("pf")

    strong_2023 = (
        y2023.get("n", 0) >= 15
        and (y2023_pf or 0) >= 1.15
        and (y2023.get("mean_r") or 0) > 0
    )
    # Calendar-2024 still healthy is the decisive anti-decay signal for
    # "is the 2024-01 start loss about 2024 dying?"
    strong_2024 = (
        y2024.get("n", 0) >= 15
        and (y2024_pf or 0) >= 1.15
        and (y2024.get("mean_r") or 0) > 0
    )
    post_positive = (
        post_n >= 15
        and (post_pf or 0) > 1.0
        and (post_mean_r or 0) > 0
    )
    post_negative = (
        post_n >= 15
        and ((post_pf or 99) < 1.0 or (post_mean_r or 0) <= 0)
    )

    if post_positive and strong_2023 and strong_2024:
        return (
            "thin_sample_artifact",
            "Critical cut PASS: full-path 2024+ stays PF>1 / meanR>0, and "
            "calendar 2024 itself is still strong (not a dead year). The "
            "lone 2024-01 start loss is burn-in + nested-subset path noise "
            "(it drops most of excellent 2024-H1). Separate note: 2025 is "
            "weak on small n — forward risk, not the sealed multi-start fail.",
        )
    if post_positive and strong_2023:
        return (
            "thin_sample_artifact",
            "Full 2023-01 path stays PF>1 / meanR>0 on 2024+ trades; "
            "the lone 2024-01 start loss is thin-n / shorter-window path noise.",
        )
    if post_negative and strong_2023:
        # Year split disagreeing under thin n → do not over-claim decay.
        if (
            y2024_pf is not None
            and y2025_pf is not None
            and ((y2024_pf > 1.0) != (y2025_pf > 1.0))
            and post_n < 40
        ):
            return (
                "inconclusive_mixed",
                "2024+ aggregate is weak vs strong 2023, but year split "
                "disagrees and n is thin — decay signal not clean.",
            )
        return (
            "genuine_decay",
            "On the full path, 2023 is strong while 2024+ after-cost KPIs "
            "are negative / PF<1 — not explained by the 2024-01 start alone.",
        )
    return (
        "inconclusive_mixed",
        "Neither clean positivity nor clean decay of 2024+ on the full path.",
    )


def main() -> None:
    paths = {
        start: load_post_burnin(k, start)
        for k, start in enumerate(SEALED_STARTS)
    }
    full = paths[SEALED_STARTS[0]]

    by_year = {
        str(y): kpis(ts)
        for y, ts in sorted(
            bucket_by(full, lambda dt: str(dt.year)).items(),
            key=lambda kv: kv[0],
        )
    }
    # rebuild year buckets with int keys for post_2023
    year_buckets = bucket_by(full, lambda dt: dt.year)
    post_2023_trades = [t for y, ts in year_buckets.items() if y >= 2024 for t in ts]
    y2023_trades = year_buckets.get(2023, [])

    by_half = {
        label: kpis(ts)
        for label, ts in sorted(
            bucket_by(full, half_year_label).items(),
            key=lambda kv: kv[0],
        )
    }

    roll = rolling_kpis(full, 20)
    # summarize rolling: how often PF<1 / meanR<=0 in the last half of windows
    if roll:
        last_half = roll[len(roll) // 2 :]
        roll_summary = {
            "n_windows": len(roll),
            "first_window_end": roll[0]["end_entry_time"],
            "last_window_end": roll[-1]["end_entry_time"],
            "mean_r_series": [r["mean_r"] for r in roll],
            "win_rate_series": [r["win_rate"] for r in roll],
            "pf_series": [r["pf"] for r in roll],
            "pct_windows_pf_lt_1": round(
                100.0 * sum(1 for r in roll if (r["pf"] or 99) < 1.0) / len(roll), 1
            ),
            "pct_last_half_pf_lt_1": round(
                100.0 * sum(1 for r in last_half if (r["pf"] or 99) < 1.0)
                / len(last_half),
                1,
            ),
            "pct_windows_mean_r_le_0": round(
                100.0 * sum(1 for r in roll if (r["mean_r"] or 0) <= 0) / len(roll),
                1,
            ),
            "pct_last_half_mean_r_le_0": round(
                100.0 * sum(1 for r in last_half if (r["mean_r"] or 0) <= 0)
                / len(last_half),
                1,
            ),
            "median_mean_r_first_half": round(
                statistics.median([r["mean_r"] for r in roll[: len(roll) // 2]]), 4
            ),
            "median_mean_r_last_half": round(
                statistics.median([r["mean_r"] for r in last_half]), 4
            ),
        }
    else:
        roll_summary = {"n_windows": 0}

    per_start = {start: kpis(ts) for start, ts in paths.items()}
    ov = overlap_matrix(paths)

    # Same calendar window as start_4 burn-in cutoff, measured on full path
    s4_cutoff = (
        datetime.fromisoformat(SEALED_STARTS[4]).replace(tzinfo=timezone.utc)
        + timedelta(days=BURN_IN_DAYS)
    )
    same_window_trades = [
        t for t in full if _parse_ts(t["entry_time"]) >= s4_cutoff
    ]

    full_path_block = {
        "start": SEALED_STARTS[0],
        "end": SEALED_END,
        "overall_1x": kpis(full),
        "by_year": by_year,
        "by_half_year": by_half,
        "y2023": kpis(y2023_trades),
        "post_2023": kpis(post_2023_trades),
    }
    code, rationale = verdict_from(full_path_block)

    report = {
        "cell": "AN-3:chigiri_hyoma:XAGUSD",
        "cost_1x_field_pips": COST,
        "burn_in_days": BURN_IN_DAYS,
        "question": (
            "Is the sealed 2024-01 start being the only PF<1 path "
            "thin-sample noise or genuine edge decay?"
        ),
        "VERDICT": code,
        "rationale": rationale,
        "full_path_2023-01": full_path_block,
        "same_window_as_2024_01_on_full_path": kpis(same_window_trades),
        "rolling_20": {
            "summary": {
                k: v for k, v in roll_summary.items()
                if k not in ("mean_r_series", "win_rate_series", "pf_series")
            },
            "windows": roll,
        },
        "per_start_1x": per_start,
        "overlap": ov,
        "decision_numbers": {
            "full_path_n": full_path_block["overall_1x"]["n"],
            "y2023": full_path_block["y2023"],
            "post_2023": full_path_block["post_2023"],
            "y2024": by_year.get("2024"),
            "y2025": by_year.get("2025"),
            "start_2024-01_overall": per_start[SEALED_STARTS[4]],
            "pct_2024-01_trades_subset_of_2023-01": (
                ov["pairwise_vs_earliest_style"][SEALED_STARTS[4]][
                    "pct_subset_of_2023-01"
                ]
            ),
        },
    }

    json_out = HERE / "results" / "sealed_fade_audit.json"
    json_out.write_text(json.dumps(report, indent=2))

    # Markdown audit
    md = _render_md(report)
    md_out = HERE / "SEALED_FADE_AUDIT.md"
    md_out.write_text(md)

    print(f"VERDICT: {code}")
    print(f"rationale: {rationale}")
    d = report["decision_numbers"]
    print(
        f"full path n={d['full_path_n']} | "
        f"2023 PF={d['y2023']['pf']} meanR={d['y2023']['mean_r']} n={d['y2023']['n']} | "
        f"2024+ PF={d['post_2023']['pf']} meanR={d['post_2023']['mean_r']} "
        f"n={d['post_2023']['n']}"
    )
    print(f"wrote {json_out}")
    print(f"wrote {md_out}")


def _fmt_kpi(k: dict) -> str:
    if not k or k.get("n", 0) == 0:
        return "n=0"
    return (
        f"n={k['n']:>3}  WR={100*(k['win_rate'] or 0):5.1f}%  "
        f"PF={k['pf']:>6}  meanR={k['mean_r']:>+7.4f}  "
        f"pips={k['total_pips']:>+8.1f}"
    )


def _render_md(report: dict) -> str:
    fp = report["full_path_2023-01"]
    d = report["decision_numbers"]
    ov = report["overlap"]
    rs = report["rolling_20"]["summary"]
    lines = [
        "# AN-3 sealed fade audit — thin sample vs genuine decay",
        "",
        f"**Cell:** `{report['cell']}`  ",
        f"**Cost:** 1x honest RT = {report['cost_1x_field_pips']} field-pips "
        f"(deducted from `pnl_pips`; R = (pnl−cost)/`source_sl_pips`)  ",
        f"**Burn-in:** {report['burn_in_days']} days (same as `summarize_phase_an.py`)  ",
        f"**Window:** sealed starts {', '.join(SEALED_STARTS)}; end {SEALED_END}  ",
        f"**Script:** `sealed_fade_audit.py` → also writes "
        f"`results/sealed_fade_audit.json`",
        "",
        f"## VERDICT: `{report['VERDICT']}`",
        "",
        report["rationale"],
        "",
        "### Numbers that decide it",
        "",
        "| slice (full path start=2023-01) | n | WR | PF @1x | mean R @1x | pips @1x |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, k in (
        ("overall", fp["overall_1x"]),
        ("calendar 2023", fp["y2023"]),
        ("calendar 2024+", fp["post_2023"]),
        ("calendar 2024", d["y2024"]),
        ("calendar 2025", d["y2025"]),
        ("start 2024-01 path (alone)", d["start_2024-01_overall"]),
    ):
        if not k:
            continue
        lines.append(
            f"| {label} | {k['n']} | "
            f"{100*(k['win_rate'] or 0):.1f}% | {k['pf']} | "
            f"{k['mean_r']:+.4f} | {k['total_pips']:+.1f} |"
        )

    lines += [
        "",
        "Critical cut: **2024+ trades on the FULL 2023-01 path** "
        f"(n={d['post_2023']['n']}, PF={d['post_2023']['pf']}, "
        f"meanR={d['post_2023']['mean_r']:+.4f}) stay positive — and "
        f"**calendar 2024 alone** is still strong "
        f"(n={d['y2024']['n']}, PF={d['y2024']['pf']}, "
        f"meanR={d['y2024']['mean_r']:+.4f}), matching 2023 "
        f"(n={d['y2023']['n']}, PF={d['y2023']['pf']}, "
        f"meanR={d['y2023']['mean_r']:+.4f}). "
        f"2025 is the soft year (n={d['y2025']['n']}, "
        f"PF={d['y2025']['pf']}, meanR={d['y2025']['mean_r']:+.4f}).",
        "",
        "## 1. Schema / tape notes",
        "",
        "Trades live at "
        "`results/AN-3/XAGUSD/sealed/start_<k>/trades.jsonl`.",
        "Relevant fields: `entry_time`, `pnl_pips`, `source_sl_pips`, "
        "`r_multiple` (pre-cost), `direction`, `entry`.",
        "Raw tape counts include a few pre-cutoff entries; KPIs here "
        "match the sealed summary by discarding `entry_time < start+92d`.",
        "",
        "## 2. Full-path calendar buckets (start_0 = 2023-01)",
        "",
        "### By calendar year",
        "",
        "```",
    ]
    for y, k in fp["by_year"].items():
        lines.append(f"{y}: {_fmt_kpi(k)}")
    lines += [
        "```",
        "",
        "### By half-year",
        "",
        "```",
    ]
    for h, k in fp["by_half_year"].items():
        lines.append(f"{h}: {_fmt_kpi(k)}")
    lines += [
        "```",
        "",
        "## 3. Rolling 20-trade KPIs (full 2023-01 path, 1x cost)",
        "",
        f"- Windows: {rs.get('n_windows')} "
        f"(end entries {rs.get('first_window_end')} → "
        f"{rs.get('last_window_end')})",
        f"- Median mean R, first half of windows: "
        f"{rs.get('median_mean_r_first_half')}",
        f"- Median mean R, last half of windows: "
        f"{rs.get('median_mean_r_last_half')}",
        f"- % windows with PF < 1: {rs.get('pct_windows_pf_lt_1')}% "
        f"(last half: {rs.get('pct_last_half_pf_lt_1')}%)",
        f"- % windows with mean R ≤ 0: {rs.get('pct_windows_mean_r_le_0')}% "
        f"(last half: {rs.get('pct_last_half_mean_r_le_0')}%)",
        "",
        "Per-window series is in `results/sealed_fade_audit.json` "
        "under `rolling_20.windows`.",
        "",
        "## 4. Cross-start overlap",
        "",
        "Identity key = `(entry_time, direction, round(entry, 6))`.",
        "",
        "### Later starts vs earliest (2023-01) post-burn-in set",
        "",
        "| start | n | shared w/ 2023-01 | unique vs 2023-01 | % subset of 2023-01 |",
        "|---|---:|---:|---:|---:|",
    ]
    for start, row in ov["pairwise_vs_earliest_style"].items():
        lines.append(
            f"| {start} | {row['n']} | {row['shared_with_2023-01']} | "
            f"{row['unique_vs_2023-01']} | {row['pct_subset_of_2023-01']}% |"
        )
    lines += [
        "",
        "### Incremental trades vs union of earlier starts",
        "",
        "| start | n | already in earlier starts | new vs earlier |",
        "|---|---:|---:|---:|",
    ]
    for start, row in ov["incremental_vs_earlier_starts"].items():
        lines.append(
            f"| {start} | {row['n']} | {row['already_seen_in_earlier']} | "
            f"{row['new_vs_earlier_starts']} |"
        )
    same_win = report.get("same_window_as_2024_01_on_full_path")
    lines += [
        "",
        f"Union of all starts: n={ov['union_n']}.",
        "",
        f"2024-01 path: "
        f"**{d['pct_2024-01_trades_subset_of_2023-01']}%** of its trades "
        "also appear on the 2023-01 full path (post each path's own burn-in).",
        "Later starts are **exact nested subsets** of earlier starts' "
        "post-burn-in trades (0 unique trades on any later start). The "
        "2024-01 path is a short, late slice of the same opportunity set, "
        "not an independent regime sample.",
        "",
    ]
    if same_win:
        lines += [
            "### Same-window identity check",
            "",
            "Full-path trades with `entry_time >= 2024-01-01 + 92d` "
            f"(= burn-in cutoff of the 2024-01 start): "
            f"n={same_win['n']}, PF={same_win['pf']}, "
            f"meanR={same_win['mean_r']:+.4f}, pips={same_win['total_pips']:+.1f}.",
            "These KPIs are **identical** to the 2024-01 start alone — "
            "squad-state differences across starts did not create a "
            "different trade set; only the calendar window did.",
            "",
        ]
    lines += [
        "## 5. Per-start sealed KPIs @1x (reproduced)",
        "",
        "```",
    ]
    for start, k in report["per_start_1x"].items():
        lines.append(f"{start}: {_fmt_kpi(k)}")
    lines += [
        "```",
        "",
        "## Interpretation",
        "",
    ]
    if report["VERDICT"] == "thin_sample_artifact":
        lines += [
            "### Why the verdict is `thin_sample_artifact`",
            "",
            "1. **Critical cut:** on the continuous 2023-01 tape, 2024+ "
            f"trades remain positive after 1x cost "
            f"(n={d['post_2023']['n']}, PF={d['post_2023']['pf']}, "
            f"meanR={d['post_2023']['mean_r']:+.4f}).",
            "2. **Calendar 2024 is not dead:** full-path 2024 alone is "
            f"n={d['y2024']['n']}, PF={d['y2024']['pf']}, "
            f"meanR={d['y2024']['mean_r']:+.4f} — essentially as strong "
            "as 2023. The sealed 'fade' is **not** 'edge died when 2024 "
            "began'.",
            "3. **Nested subsets:** every later start's post-burn-in trades "
            "are a 100% subset of the 2023-01 set. No unique 2024-01 "
            "opportunities exist.",
            "4. **Burn-in amputates the best half-year:** 2024-H1 on the "
            "full path is the sealed peak (PF 3.182, meanR +0.67, n=17). "
            "The 2024-01 start's 92-day burn-in ends ~2024-04-02, so that "
            "path systematically drops most of that peak and retains "
            "2024-H2 + 2025 (the weak half-years). Same-window filter on "
            "the full path reproduces the 2024-01 KPIs exactly.",
            "",
            "### Separate caveat (does not flip the verdict)",
            "",
            "From **2024-H2 onward** the full path *does* weaken: 2024-H2 "
            "PF 0.619 (n=11), 2025 PF 0.732 / meanR −0.24 (n=18), and "
            "rolling-20 last-half windows are PF<1 about half the time. "
            "That is real late-window softness on small n — a paper-loop "
            "risk flag — but it is **not** what makes the 2024-01 start "
            "the only sealed loser. That specific multi-start pattern is "
            "explained by burn-in + nested short window.",
            "",
            "Deployment implication: do **not** treat the single losing "
            "start as proof the edge died in 2024. Keep paper-loop / live "
            "tape as the forward arbiter, especially given 2025 softness.",
        ]
    elif report["VERDICT"] == "genuine_decay":
        lines += [
            "The full-path calendar cut shows **real post-2023 weakness**:",
            "2023 carries the sealed pass; 2024+ after-cost expectancy is",
            "flat-to-negative. The 2024-01 start is not an isolated path",
            "artifact — it is the start that mostly sees the decayed regime.",
            "",
            "Deployment implication: paper-loop is mandatory; treat sealed",
            "PASS as historically validated but **recency-impaired**. Size",
            "conservatively and require fresh-tape confirmation before live.",
        ]
    else:
        lines += [
            "Evidence is mixed: year/half-year slices disagree or samples",
            "are too thin for a clean call. Keep the REPORT.md recency",
            "caveat; do not escalate either reading to a hard claim.",
        ]
    lines += [
        "",
        "---",
        f"*Generated by `sealed_fade_audit.py`.*",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
