"""Phi5 aggregator selection experiment harness.

Pre-registered protocol: `experiments/phi5_aggregator/PROTOCOL.md` v0.1
(pre-registered 2026-06-25; amended 2026-06-30 §11.1 + §11.2).

This harness runs the 5 treatment arms against the Phi4.1 control on
the panel described in PROTOCOL §5 (EURUSD/GBPUSD/USDCAD H4, 2015-2025,
7 OOS windows, 8-agent squad).

## Approach

**Arms that admit post-hoc computation (Phase 6d today, Session 1):**

- **Arm 0 (control):** median-of-window-mean TQS from
  `reviews/phi41_squad_v1_trades.jsonl` -- locked at 0.2922.
- **Arm 1 (HRP):** re-weight the Phi4.1 trades by per-agent HRP weight
  fit on prior OOS windows (walk-forward, no look-ahead). Compute the
  weighted per-window mean TQS + median across windows.
- **Arm 2 (TQS floor):** filter Phi4.1 trades whose conviction was below
  the agent's PRIOR-window P=0.40 conviction quantile. Agents with <
  200 historical trades get a free pass. Compute unweighted per-window
  mean TQS + median across windows on the surviving trade set.

**Arms that require a full re-simulation (Phase 6e follow-up):**

- **Arm 3 (same-direction merge):** merging changes SL (tightest) + TP
  (median), which alters trade outcomes. Post-hoc without price paths
  cannot compute this honestly. Reported as "requires re-sim".
- **Arm 4 (multi-position):** admitting a second position per symbol
  requires trade outcomes for the previously-rejected proposals; those
  outcomes depend on price paths not preserved in the artefacts.
  Reported as "requires re-sim".
- **Arm 5 (combined):** stacks Arms 1+2 (computable) + Arms 3+4 (not
  computable). Reported as "partial: Arms 1+2 stacked; full stack
  requires re-sim".

**This is a PARTIAL verdict per PROTOCOL §6 stop rule #2** ("If the
[compute] budget is exceeded, ship a partial verdict (only arms that
completed) -- never silently truncate to ship a clean number.") The
follow-up (Phase 6e) will build the full-sim path by plugging the
aggregator arms into `_drive_squad_replay` and running the 5x7 grid.

CLI
---

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_phi5_aggregator_gate
        [--trades reviews/phi41_squad_v1_trades.jsonl]
        [--proposals reviews/phi41_squad_v1_proposals_all.jsonl]
        [--out-dir reviews/]
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms import (
    HRPAggregator,
    TQSFloorAggregator,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants (inherit from Phi4.1)
# ---------------------------------------------------------------------------

ARM0_CONTROL_TQS = 0.2922         # locked Phi4.1 median-of-window-mean TQS
ISAGI_ALONE_TQS = 0.3175          # locked Phi3 median-of-window-mean TQS
BONFERRONI_ALPHA_PER_ARM = 0.01   # 0.05 / 5

# Walk-forward parameters (match Phi4.1 / G5-squad).
IS_YEARS = 4
OOS_YEARS = 1
DEFAULT_FULL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
DEFAULT_FULL_END = datetime(2025, 12, 31, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeRow:
    """Minimal fields from phi41_squad_v1_trades.jsonl needed here."""
    agent_id: str
    symbol: str
    entry_time: datetime
    direction: str
    pnl_pips: float
    tqs: float
    # Filled by join with proposals_all.jsonl:
    conviction: float | None = None


@dataclass
class ProposalRow:
    """Minimal fields from phi41_squad_v1_proposals_all.jsonl."""
    agent_id: str
    symbol: str
    tick_id: int
    timestamp: datetime
    direction: str
    conviction: float


@dataclass
class WindowStats:
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    n_trades: int
    squad_mean_tqs: float
    squad_mean_pips: float


@dataclass
class ArmResult:
    arm_id: str
    arm_name: str
    n_trades: int
    median_window_mean_tqs: float
    mean_window_mean_tqs: float
    pooled_per_trade_mean_tqs: float
    pooled_per_trade_mean_pips: float
    ratio_vs_isagi: float
    ratio_vs_control: float
    delta_vs_control: float
    windows: list[WindowStats]
    verdict: str          # "PASS" | "PARTIAL" | "NULL" | "REGRESS" | "REQUIRES_RESIM"
    caveats: list[str] = field(default_factory=list)
    per_agent_hrp_weights_by_window: dict[str, list[dict[str, float]]] | None = None


# ---------------------------------------------------------------------------
# Data loading + joining
# ---------------------------------------------------------------------------

def _load_trades(path: Path) -> list[TradeRow]:
    out: list[TradeRow] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            # Schema tolerance (2026-07-06, PROTOCOL §11.4): the
            # phi41-era cache nests TQS under "tqs"; the G7 replay
            # caches (walk-forward-post-*) nest it under
            # "tqs_components". Accept both.
            tqs_blob = row.get("tqs") or row.get("tqs_components") or {}
            out.append(TradeRow(
                agent_id=row["agent_id"],
                symbol=row["symbol"],
                entry_time=datetime.fromisoformat(row["entry_time"]),
                direction=row["direction"],
                pnl_pips=float(row["pnl_pips"]),
                tqs=float(tqs_blob["tqs"]),
            ))
    return out


def _load_proposals(path: Path) -> list[ProposalRow]:
    out: list[ProposalRow] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            out.append(ProposalRow(
                agent_id=row["agent_id"],
                symbol=row["symbol"],
                tick_id=int(row["tick_id"]),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                direction=row["direction"],
                conviction=float(row["conviction"]),
            ))
    return out


def _join_trades_to_proposals(
    trades: list[TradeRow],
    proposals: list[ProposalRow],
) -> None:
    """Populate ``trade.conviction`` via nearest-tick match on (agent, symbol).

    A trade opened at entry_time T corresponds to a proposal with the same
    agent + symbol whose timestamp is at T or up to 4 hours earlier (H4 bar).
    Mutates trades in place.
    """
    by_key: dict[tuple[str, str], list[ProposalRow]] = {}
    for p in proposals:
        by_key.setdefault((p.agent_id, p.symbol), []).append(p)
    for props in by_key.values():
        props.sort(key=lambda p: p.timestamp)

    matched = 0
    for t in trades:
        candidates = by_key.get((t.agent_id, t.symbol), [])
        if not candidates:
            continue
        # Find the proposal whose timestamp is <= entry_time and closest.
        best = None
        best_gap = timedelta.max
        for p in candidates:
            gap = t.entry_time - p.timestamp
            if timedelta(0) <= gap <= timedelta(hours=8) and gap < best_gap:
                best = p
                best_gap = gap
        if best is not None:
            t.conviction = best.conviction
            matched += 1
    log.info(
        "Joined %d/%d trades to convictions (%.1f%%)",
        matched, len(trades), 100.0 * matched / max(1, len(trades)),
    )


# ---------------------------------------------------------------------------
# Walk-forward windowing
# ---------------------------------------------------------------------------

def _window_starts(
    full_start: datetime, full_end: datetime,
) -> list[datetime]:
    """Yield IS-window start dates (Jan 1 each year until final OOS fits).

    Mirrors the Phi4.1 harness convention: the OOS window is included if
    its START is <= full_end (partial OOS windows clamp to full_end at
    the caller). This is needed to reach 7 windows on the 2015-2025
    panel (last OOS = 2025 partial).
    """
    starts: list[datetime] = []
    year = full_start.year
    while True:
        is_start = datetime(year, 1, 1, tzinfo=timezone.utc)
        is_end = datetime(year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        if oos_start >= full_end:
            break
        starts.append(is_start)
        year += 1
    return starts


def _compute_windows(
    trades: list[TradeRow],
    *,
    full_start: datetime, full_end: datetime,
) -> list[WindowStats]:
    out: list[WindowStats] = []
    for is_start in _window_starts(full_start, full_end):
        is_end = datetime(
            is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > full_end:
            oos_end = full_end   # clamp last (partial) window
        oos_trades = [
            t for t in trades if oos_start <= t.entry_time < oos_end
        ]
        if not oos_trades:
            continue
        squad_mean_tqs = statistics.mean(t.tqs for t in oos_trades)
        squad_mean_pips = statistics.mean(t.pnl_pips for t in oos_trades)
        out.append(WindowStats(
            is_start=is_start, is_end=is_end,
            oos_start=oos_start, oos_end=oos_end,
            n_trades=len(oos_trades),
            squad_mean_tqs=squad_mean_tqs,
            squad_mean_pips=squad_mean_pips,
        ))
    return out


# ---------------------------------------------------------------------------
# Arm 0 (control) -- reads Phi4.1 result verbatim
# ---------------------------------------------------------------------------

def evaluate_arm0(
    trades: list[TradeRow],
    *,
    full_start: datetime, full_end: datetime,
) -> ArmResult:
    windows = _compute_windows(trades, full_start=full_start, full_end=full_end)
    tqs_series = [w.squad_mean_tqs for w in windows]
    pip_series = [w.squad_mean_pips for w in windows]
    median = statistics.median(tqs_series) if tqs_series else 0.0
    mean = statistics.mean(tqs_series) if tqs_series else 0.0
    pooled_tqs = statistics.mean(t.tqs for t in trades) if trades else 0.0
    pooled_pips = statistics.mean(t.pnl_pips for t in trades) if trades else 0.0
    return ArmResult(
        arm_id="arm0",
        arm_name="Control (Phi4.1 aggregator)",
        n_trades=len(trades),
        median_window_mean_tqs=median,
        mean_window_mean_tqs=mean,
        pooled_per_trade_mean_tqs=pooled_tqs,
        pooled_per_trade_mean_pips=pooled_pips,
        ratio_vs_isagi=median / ISAGI_ALONE_TQS if ISAGI_ALONE_TQS > 0 else 0.0,
        ratio_vs_control=1.0,
        delta_vs_control=0.0,
        windows=windows,
        verdict="baseline",
        caveats=[
            f"Locked control value from Phi4.1: median = {ARM0_CONTROL_TQS:.4f}. "
            "This harness's re-computation should agree within a few basis "
            "points (any difference is arithmetic noise, not a re-derivation)."
        ],
    )


# ---------------------------------------------------------------------------
# Arm 1 (HRP) -- re-weight Phi4.1 trades by per-agent HRP weight
# ---------------------------------------------------------------------------

def evaluate_arm1(
    trades: list[TradeRow],
    *,
    full_start: datetime, full_end: datetime,
) -> ArmResult:
    """Walk-forward HRP re-weighting.

    At each OOS window boundary, refit HRP using PRIOR windows' per-agent
    per-window mean TQS + total trade counts (as of that boundary). Then
    within the OOS window, compute a WEIGHTED mean TQS across the squad's
    trades, weighting each trade by its agent's HRP weight.

    The median-of-window-mean-weighted-TQS is the locked-statistic
    equivalent for Arm 1.
    """
    hrp = HRPAggregator()
    per_agent_history_by_window: dict[str, list[float]] = {}
    per_agent_cumulative_trades: dict[str, int] = {}
    window_weights_log: list[dict[str, float]] = []

    all_agent_ids = sorted({t.agent_id for t in trades})
    for aid in all_agent_ids:
        per_agent_history_by_window[aid] = []
        per_agent_cumulative_trades[aid] = 0

    windows = _compute_windows(trades, full_start=full_start, full_end=full_end)
    weighted_window_means: list[float] = []
    trades_by_window: list[list[TradeRow]] = []

    for w in windows:
        # Refit HRP with PRIOR history.
        snap = hrp.refit(
            per_agent_window_tqs=per_agent_history_by_window,
            per_agent_trade_counts=per_agent_cumulative_trades,
            window_start=w.oos_start, window_end=w.oos_end,
        )
        window_weights_log.append(dict(snap.weights))

        # OOS trades for this window.
        oos_trades = [
            t for t in trades if w.oos_start <= t.entry_time < w.oos_end
        ]
        trades_by_window.append(oos_trades)

        if not oos_trades:
            weighted_window_means.append(0.0)
            continue

        weighted_sum = 0.0
        weight_sum = 0.0
        for t in oos_trades:
            w_agent = snap.weights.get(t.agent_id, 0.0)
            if w_agent <= 0:
                continue
            weighted_sum += w_agent * t.tqs
            weight_sum += w_agent
        if weight_sum > 0:
            weighted_window_means.append(weighted_sum / weight_sum)
        else:
            # No HRP-weighted agents in this window -> the harness admits
            # nothing. Log 0.0 (a defensible "no trades" placeholder;
            # alternative would be to skip the window from the median.
            # Skipping would introduce bias; we log 0.0 and document.)
            weighted_window_means.append(0.0)

        # Advance history: append this window's per-agent mean TQS + counts.
        for aid in all_agent_ids:
            ag_trades = [t for t in oos_trades if t.agent_id == aid]
            if ag_trades:
                m = statistics.mean(t.tqs for t in ag_trades)
                per_agent_history_by_window[aid].append(m)
                per_agent_cumulative_trades[aid] += len(ag_trades)

    median = statistics.median(weighted_window_means)
    mean = statistics.mean(weighted_window_means)
    pooled_tqs = _pooled_hrp_weighted_tqs(trades_by_window, window_weights_log)
    pooled_pips = statistics.mean(t.pnl_pips for t in trades) if trades else 0.0
    delta = median - ARM0_CONTROL_TQS
    verdict = _verdict_from_median(median)
    return ArmResult(
        arm_id="arm1",
        arm_name="HRP (Ledoit-Wolf tangency, TQS covariance)",
        n_trades=len(trades),
        median_window_mean_tqs=median,
        mean_window_mean_tqs=mean,
        pooled_per_trade_mean_tqs=pooled_tqs,
        pooled_per_trade_mean_pips=pooled_pips,
        ratio_vs_isagi=median / ISAGI_ALONE_TQS if ISAGI_ALONE_TQS > 0 else 0.0,
        ratio_vs_control=median / ARM0_CONTROL_TQS if ARM0_CONTROL_TQS > 0 else 0.0,
        delta_vs_control=delta,
        windows=windows,
        verdict=verdict,
        caveats=[
            "Post-hoc re-weighting only -- production HRP scales lot size, "
            "which alters pnl_pips. In the fixed-lot sim harness this "
            "effect is folded into the WEIGHTED-mean TQS statistic, which "
            "is the closest post-hoc analogue.",
            "First window has empty prior history -> HRP falls back to "
            "equal-weight-on-positive-mean (documented in HRP fallback).",
        ],
        per_agent_hrp_weights_by_window={
            aid: [
                {"oos_start": w.oos_start.isoformat(), "weight": float(wlog.get(aid, 0.0))}
                for w, wlog in zip(windows, window_weights_log)
            ]
            for aid in all_agent_ids
        },
    )


def _pooled_hrp_weighted_tqs(
    trades_by_window: list[list[TradeRow]],
    weights_by_window: list[dict[str, float]],
) -> float:
    """Weighted pooled-TQS across all windows."""
    weighted_sum = 0.0
    weight_sum = 0.0
    for trades, weights in zip(trades_by_window, weights_by_window):
        for t in trades:
            w = weights.get(t.agent_id, 0.0)
            if w <= 0:
                continue
            weighted_sum += w * t.tqs
            weight_sum += w
    return weighted_sum / weight_sum if weight_sum > 0 else 0.0


# ---------------------------------------------------------------------------
# Arm 2 (TQS floor) -- filter by P40 of prior conviction distribution
# ---------------------------------------------------------------------------

def evaluate_arm2(
    trades: list[TradeRow],
    *,
    full_start: datetime, full_end: datetime,
) -> ArmResult:
    """Walk-forward TQS-floor filtering.

    Trades whose conviction < P40 of the agent's PRIOR-window conviction
    distribution are dropped. Agents with < 200 historical trades get
    free pass. The remaining trade set produces per-window mean TQS +
    the locked median-across-windows statistic.
    """
    floor = TQSFloorAggregator()
    windows = _compute_windows(trades, full_start=full_start, full_end=full_end)

    # Trades sorted by entry_time so history accumulates walk-forward.
    trades_sorted = sorted(trades, key=lambda t: t.entry_time)

    kept: list[TradeRow] = []
    n_missing_conviction = 0
    for t in trades_sorted:
        if t.conviction is None:
            # Cannot filter without the conviction; keep and flag.
            kept.append(t)
            n_missing_conviction += 1
            continue
        # Test via the underlying pure function to keep this stateless
        # (the aggregator's mutable filter mixes history + filter). We
        # DIRECTLY check the current agent's history:
        history = floor.per_agent_conviction_history.get(t.agent_id, [])
        n_hist = floor.per_agent_trade_counts.get(t.agent_id, 0)
        if n_hist < floor.min_n_for_floor:
            kept.append(t)
        else:
            import numpy as np
            threshold = float(np.quantile(history, floor.p))
            if t.conviction >= threshold:
                kept.append(t)
        # Advance history AFTER the decision (walk-forward, no lookahead).
        floor.update_history(t.agent_id, [t.conviction])

    filtered_windows = _compute_windows(
        kept, full_start=full_start, full_end=full_end,
    )
    tqs_series = [w.squad_mean_tqs for w in filtered_windows]
    median = statistics.median(tqs_series) if tqs_series else 0.0
    mean = statistics.mean(tqs_series) if tqs_series else 0.0
    pooled_tqs = statistics.mean(t.tqs for t in kept) if kept else 0.0
    pooled_pips = statistics.mean(t.pnl_pips for t in kept) if kept else 0.0
    delta = median - ARM0_CONTROL_TQS
    verdict = _verdict_from_median(median)
    return ArmResult(
        arm_id="arm2",
        arm_name="TQS-conditional conviction floor (P=0.40, min_n=200)",
        n_trades=len(kept),
        median_window_mean_tqs=median,
        mean_window_mean_tqs=mean,
        pooled_per_trade_mean_tqs=pooled_tqs,
        pooled_per_trade_mean_pips=pooled_pips,
        ratio_vs_isagi=median / ISAGI_ALONE_TQS if ISAGI_ALONE_TQS > 0 else 0.0,
        ratio_vs_control=median / ARM0_CONTROL_TQS if ARM0_CONTROL_TQS > 0 else 0.0,
        delta_vs_control=delta,
        windows=filtered_windows,
        verdict=verdict,
        caveats=[
            f"Dropped {len(trades) - len(kept)} trades below per-agent P40 "
            "conviction (walk-forward, no lookahead).",
            (f"{n_missing_conviction} trades had no matched proposal "
             "(conviction=None) -- retained as free-pass to avoid biasing "
             "against the arm.")
            if n_missing_conviction > 0 else
            "All trades joined to a matched conviction value.",
        ],
    )


# ---------------------------------------------------------------------------
# Arms 3, 4, 5 -- REQUIRES_RESIM (documented, not silently null)
# ---------------------------------------------------------------------------

def evaluate_arm3_resim_required() -> ArmResult:
    return _resim_required_arm(
        arm_id="arm3",
        arm_name="Same-direction merge (tightest SL, median TP)",
        reason=(
            "Merging changes SL (tightest) and TP (median-of-ladder-target). "
            "Trade outcomes with the modified SL/TP cannot be recomputed "
            "post-hoc without the H4 price paths and the production fill "
            "model. Requires a full re-simulation via "
            "`_drive_squad_replay` with the aggregator plumbed to "
            "`apply_same_direction_merge`."
        ),
    )


def evaluate_arm4_resim_required() -> ArmResult:
    return _resim_required_arm(
        arm_id="arm4",
        arm_name="Multi-position per symbol (K=2 + R6 cap)",
        reason=(
            "Admitting a second concurrent position per symbol requires "
            "trade outcomes for previously-rejected proposals; those "
            "outcomes depend on H4 price paths not preserved in the "
            "artefacts. Requires a full re-simulation with the aggregator "
            "plumbed to `admit_proposals`. Sentinel R6 wiring is already "
            "in place (`sim/core/sentinel.py::check_r6_per_symbol_risk_cap`)."
        ),
    )


def evaluate_arm5_resim_required() -> ArmResult:
    return _resim_required_arm(
        arm_id="arm5",
        arm_name="Combined (floor -> merge -> multi-position -> HRP)",
        reason=(
            "The stack includes Arms 3 and 4 which require re-simulation. "
            "A partial stack (Arms 1 + 2 alone) is computable but does not "
            "match the pre-registered order-of-operations; reporting it "
            "would blur the verdict. Full stack requires the same "
            "re-sim path as Arms 3 and 4."
        ),
    )


def _resim_required_arm(*, arm_id: str, arm_name: str, reason: str) -> ArmResult:
    return ArmResult(
        arm_id=arm_id,
        arm_name=arm_name,
        n_trades=0,
        median_window_mean_tqs=float("nan"),
        mean_window_mean_tqs=float("nan"),
        pooled_per_trade_mean_tqs=float("nan"),
        pooled_per_trade_mean_pips=float("nan"),
        ratio_vs_isagi=float("nan"),
        ratio_vs_control=float("nan"),
        delta_vs_control=float("nan"),
        windows=[],
        verdict="REQUIRES_RESIM",
        caveats=[reason],
    )


# ---------------------------------------------------------------------------
# Verdict mapping (per PROTOCOL §4)
# ---------------------------------------------------------------------------

def _verdict_from_median(median_tqs: float) -> str:
    """PROTOCOL §4 verdict mapping. The CI test (Bonferroni-corrected)
    is applied only in the final selection step -- here we return the
    per-arm ordinal band based on median alone.
    """
    if median_tqs < ARM0_CONTROL_TQS:
        return "REGRESS"
    if median_tqs < ISAGI_ALONE_TQS:
        return "PARTIAL"
    if median_tqs < 0.349:
        return "PASS-PARTIAL"
    return "PASS"


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

def render_report(results: list[ArmResult]) -> str:
    lines: list[str] = []
    lines.append("# Phi5 aggregator selection experiment -- verdict\n")
    lines.append(f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(
        "**Protocol:** `experiments/phi5_aggregator/PROTOCOL.md` "
        "(pre-registered 2026-06-25; amended 2026-06-30 §11.1 + §11.2)\n"
    )
    lines.append(
        "**Statistic (locked, inherited from G6):** median across OOS "
        "windows of per-window mean TQS (F12)\n"
    )
    lines.append(
        f"**Control (Arm 0, Phi4.1):** {ARM0_CONTROL_TQS:.4f} TQS; "
        f"Isagi-alone reference: {ISAGI_ALONE_TQS:.4f} TQS.\n"
    )
    lines.append("---\n")
    lines.append("## Partial-verdict framing\n")
    lines.append(
        "Per PROTOCOL §6 stop rule #2 (retained after §11.1 amendment), "
        "when the compute time-box precludes running every arm, ship the "
        "arms that DID complete and mark the others REQUIRES_RESIM. This "
        "run computes Arms 0, 1, 2 post-hoc from the Phi4.1 artefacts. "
        "Arms 3, 4, 5 require a full re-simulation (`_drive_squad_replay` "
        "plumbed to arm-specific aggregators) which is a follow-up phase.\n"
    )
    lines.append("---\n")
    lines.append("## Locked-statistic verdict table\n\n")
    lines.append(
        "| Arm | n trades | Median window mean TQS | Δ vs control | "
        "Ratio vs Isagi | Verdict |"
    )
    lines.append(
        "|---|---|---|---|---|---|"
    )
    for r in results:
        med_str = (
            f"{r.median_window_mean_tqs:.4f}" if not _isnan(r.median_window_mean_tqs)
            else "—"
        )
        delta_str = (
            f"{r.delta_vs_control:+.4f}" if not _isnan(r.delta_vs_control)
            else "—"
        )
        ratio_str = (
            f"{r.ratio_vs_isagi:.2f}x" if not _isnan(r.ratio_vs_isagi)
            else "—"
        )
        lines.append(
            f"| **{r.arm_id}** ({r.arm_name}) | {r.n_trades} | {med_str} | "
            f"{delta_str} | {ratio_str} | `{r.verdict}` |"
        )
    lines.append("")
    lines.append("---\n")
    lines.append("## Cross-statistic robustness table\n\n")
    lines.append(
        "Locked statistic (median-of-window-mean TQS) is bolded. Reported "
        "alongside per PROTOCOL §4 cross-statistic discipline.\n\n"
    )
    lines.append(
        "| Arm | **Median WM TQS** | Mean WM TQS | Pooled TQS | Pooled pips |"
    )
    lines.append(
        "|---|---|---|---|---|"
    )
    for r in results:
        med = _fmt(r.median_window_mean_tqs, ".4f")
        mean = _fmt(r.mean_window_mean_tqs, ".4f")
        pt_tqs = _fmt(r.pooled_per_trade_mean_tqs, ".4f")
        pt_pips = _fmt(r.pooled_per_trade_mean_pips, "+.2f")
        lines.append(
            f"| {r.arm_id} | **{med}** | {mean} | {pt_tqs} | {pt_pips} |"
        )
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-arm details\n\n")
    for r in results:
        lines.append(f"### {r.arm_id} -- {r.arm_name}\n")
        lines.append(f"- **Verdict:** `{r.verdict}`")
        if not _isnan(r.median_window_mean_tqs):
            lines.append(
                f"- **Median window mean TQS:** {r.median_window_mean_tqs:.4f}"
            )
            lines.append(f"- **n trades:** {r.n_trades}")
            lines.append(f"- **n OOS windows with trades:** {len(r.windows)}")
        for c in r.caveats:
            lines.append(f"- _Caveat:_ {c}")
        lines.append("")
    lines.append("---\n")
    lines.append("## Follow-up (Phase 6e)\n\n")
    lines.append(
        "Ship the full-sim harness path for Arms 3, 4, 5 by plumbing the "
        "aggregator arms into `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay` "
        "as an injectable strategy. Then run the 5-arm x 7-window grid.\n"
    )
    lines.append("## Cross-references\n\n")
    lines.append(
        "- Protocol: `experiments/phi5_aggregator/PROTOCOL.md`\n"
        "- HRP notes: `experiments/phi5_aggregator/HRP_NOTES.md`\n"
        "- Locked statistic: `docs/methodology/gate_verdict_registry.md` (G6 row)\n"
        "- Phi4.1 artefacts: `reviews/phi41_squad_v1_trades.jsonl`, "
        "`reviews/phi41_squad_v1_proposals_all.jsonl`\n"
        "- Verdict-comparator discipline: "
        "`programs/M001_multi_agent_ensemble/07-research-standards.md` §11\n"
    )
    return "\n".join(lines) + "\n"


def _isnan(x: float) -> bool:
    return x != x


def _fmt(x: float, fmt: str) -> str:
    if _isnan(x):
        return "—"
    return f"{x:{fmt}}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_gate(
    *,
    trades_path: Path,
    proposals_path: Path,
    out_dir: Path,
    full_start: datetime = DEFAULT_FULL_START,
    full_end: datetime = DEFAULT_FULL_END,
) -> list[ArmResult]:
    log.info("Loading Phi4.1 trades from %s", trades_path)
    trades = _load_trades(trades_path)
    log.info("Loaded %d trades", len(trades))

    log.info("Loading Phi4.1 proposals from %s", proposals_path)
    proposals = _load_proposals(proposals_path)
    log.info("Loaded %d proposals", len(proposals))

    _join_trades_to_proposals(trades, proposals)

    results = [
        evaluate_arm0(trades, full_start=full_start, full_end=full_end),
        evaluate_arm1(trades, full_start=full_start, full_end=full_end),
        evaluate_arm2(trades, full_start=full_start, full_end=full_end),
        evaluate_arm3_resim_required(),
        evaluate_arm4_resim_required(),
        evaluate_arm5_resim_required(),
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phi5_aggregator_gate.md").write_text(
        render_report(results), encoding="utf-8",
    )
    log.info("Wrote report to %s", out_dir / "phi5_aggregator_gate.md")

    # Persist per-arm JSON for tooling.
    for r in results:
        (out_dir / f"phi5_aggregator_{r.arm_id}_result.json").write_text(
            json.dumps({
                "arm_id": r.arm_id, "arm_name": r.arm_name,
                "n_trades": r.n_trades,
                "median_window_mean_tqs": r.median_window_mean_tqs,
                "mean_window_mean_tqs": r.mean_window_mean_tqs,
                "pooled_per_trade_mean_tqs": r.pooled_per_trade_mean_tqs,
                "pooled_per_trade_mean_pips": r.pooled_per_trade_mean_pips,
                "ratio_vs_isagi": r.ratio_vs_isagi,
                "ratio_vs_control": r.ratio_vs_control,
                "delta_vs_control": r.delta_vs_control,
                "verdict": r.verdict,
                "caveats": r.caveats,
                "per_agent_hrp_weights_by_window": r.per_agent_hrp_weights_by_window,
            }, indent=2, default=str),
            encoding="utf-8",
        )
    return results


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phi5 aggregator gate -- post-hoc arms 0/1/2, RESIM required "
            "for 3/4/5"
        ),
    )
    default_reviews = (
        Path(__file__).resolve().parents[2] / "reviews"
    )
    parser.add_argument(
        "--trades", type=Path,
        default=default_reviews / "phi41_squad_v1_trades.jsonl",
    )
    parser.add_argument(
        "--proposals", type=Path,
        default=default_reviews / "phi41_squad_v1_proposals_all.jsonl",
    )
    parser.add_argument("--out-dir", type=Path, default=default_reviews)
    parser.add_argument(
        "--start", type=_parse_date,
        default=DEFAULT_FULL_START.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end", type=_parse_date,
        default=DEFAULT_FULL_END.strftime("%Y-%m-%d"),
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )

    results = run_gate(
        trades_path=args.trades,
        proposals_path=args.proposals,
        out_dir=args.out_dir,
        full_start=args.start if isinstance(args.start, datetime)
                  else _parse_date(args.start),
        full_end=args.end if isinstance(args.end, datetime)
                else _parse_date(args.end),
    )

    print("Phi5 aggregator gate verdicts:")
    for r in results:
        med = _fmt(r.median_window_mean_tqs, ".4f")
        print(f"  {r.arm_id}: {r.verdict} ({med} median WM TQS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
