"""G7 leave-one-out compute harness (Phase 3, 2026-07-03).

For each of the 8 v1 squad agents, runs one full walk-forward replay
with that agent REMOVED from the ``agents`` list passed to
``_drive_squad_replay``. Compares each replay's per-remaining-agent
TQS + trade count against the same-panel baseline (all 8 agents) to
compute G7 PROTOCOL criteria 2 (positive-sum chemistry) and 3 (non-
cannibalising slot behaviour).

Wall-clock:
- One replay ~42 min on the M001 panel (2015-01-01 -> 2025-12-31,
  3 symbols, ~53k global bars).
- 8 leave-one-outs sequentially -> ~5.6 hours.
- Baseline is REUSED from an on-disk cache (walk-forward-post-V) so
  no extra 42 min is spent re-running it.

Statistical-honesty guards:
- No parameter tuning is triggered by this run. C2/C3 are DIAGNOSTIC
  criteria that fill in the pending stubs in the G7 verdict; they do
  not authorise any code change on their own.
- Every excluded-agent replay dumps trades + shadow to disk BEFORE
  the next replay starts so a mid-run crash preserves partial
  progress.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Package path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
    A2BachiraV1,
)
from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import (
    A4ChigiriV1,
)
from programs.M001_multi_agent_ensemble.sim.agents.a05_reo import A5ReoV1
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    A10KunigamiV1,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    G7_PANEL_END,
    G7_PANEL_START,
    SYMBOLS_G7,
    _load_production_bars,
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    _drive_squad_replay,
)


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent registry -- canonical ordering (matches the G7 verdict layout).
# ---------------------------------------------------------------------------

# Order MATTERS: the CLI progress log iterates in this order so the user
# sees the roster reproduced verbatim.
G7_AGENT_ORDER: tuple[str, ...] = (
    "isagi_yoichi",
    "bachira_meguru",
    "itoshi_rin",
    "chigiri_hyoma",
    "reo_mikage",
    "nagi_seishiro",
    "barou_shoei",
    "kunigami_rensuke",
)


def _instantiate_all_agents():
    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    all_agents = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]
    # Prepare all agents on all symbols they know about.
    return all_agents, isagi, barou, kunigami


def _prepare_agents(agents: list, bars_by_symbol: dict[str, list]) -> None:
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in agents:
            if hasattr(agent, "prepare") and sym in getattr(
                agent, "symbols", (),
            ):
                agent.prepare(sym, bars)


# ---------------------------------------------------------------------------
# Cache-write helpers
# ---------------------------------------------------------------------------

def _cache_dir_for(out_dir: Path, tag: str, exclude: str | None) -> Path:
    """Return the cache directory for one leave-one-out run.

    ``exclude=None`` means the baseline squad (all 8 agents).
    """
    slug = exclude or "baseline"
    return out_dir / f"g7_leave_one_out_{tag}" / f"lo1_{slug}"


def _dump_run_cache(cache_dir: Path, out) -> None:
    """Persist the run's trades + shadow trades + workspace counts.

    Keeps the format identical to
    ``run_g7_v1_checkpoint_gate.run_g7_walk_forward``'s crash-proof
    cache so downstream tooling (aggregator, audit scripts) can read
    either kind uniformly.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    trades_cache = cache_dir / "trades.jsonl"
    with trades_cache.open("w", encoding="utf-8") as fh:
        for t in out.trades:
            fh.write(json.dumps(asdict(t), default=str) + "\n")
    shadow_cache = cache_dir / "shadow_trades.jsonl"
    with shadow_cache.open("w", encoding="utf-8") as fh:
        for s in out.shadow_trades:
            fh.write(json.dumps(asdict(s), default=str) + "\n")
    (cache_dir / "workspace_counts.json").write_text(json.dumps({
        "publish": dict(out.workspace_publish_counts),
        "read": dict(out.workspace_read_counts),
        "n_thoughts": len(out.thoughts),
        "n_proposals": len(out.proposals_all),
    }, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Single leave-one-out replay
# ---------------------------------------------------------------------------

@dataclass
class LeaveOneOutRunResult:
    """Skinny return type for progress/error tracking."""

    excluded_agent_id: str | None
    n_trades: int
    n_shadow: int
    n_proposals: int
    cache_dir: Path
    elapsed_sec: float


def run_single_leave_one_out(
    *,
    exclude_agent_id: str | None,
    all_agents: list,
    isagi: A1IsagiV1,
    barou: A7BarouV1,
    kunigami: A10KunigamiV1,
    bars_by_symbol: dict[str, list],
    out_dir: Path,
    tag: str,
) -> LeaveOneOutRunResult:
    """Run one replay with ``exclude_agent_id`` removed from the
    proposer list. ``exclude_agent_id=None`` runs the full baseline.
    """
    started = time.time()
    if exclude_agent_id is None:
        agents_for_run = list(all_agents)
    else:
        agents_for_run = [
            a for a in all_agents if a.agent_id != exclude_agent_id
        ]
        if len(agents_for_run) == len(all_agents):
            raise ValueError(
                f"exclude_agent_id={exclude_agent_id!r} did not match any "
                f"agent in the roster {[a.agent_id for a in all_agents]}"
            )

    log.info(
        "leave-one-out: excluded=%s agents_in_run=%s",
        exclude_agent_id or "<baseline>",
        [a.agent_id for a in agents_for_run],
    )

    # NB: isagi/barou/kunigami kwargs are passed AS INSTANCES even when
    # they're excluded from the proposer list. This is intentional --
    # the driver uses ``isagi._cfg`` for shared config, calls
    # ``kunigami.record_closed_trade(...)`` for the loss-streak signal,
    # and reads ``kunigami.warning_active_at(...)`` per bar. Those
    # instance-level side channels are not proposals; removing them
    # from ``agents`` alone suffices to prevent proposing.
    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=agents_for_run,
        isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol,
        ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,
        use_shadow_ledger=True,
    )

    cache_dir = _cache_dir_for(out_dir, tag, exclude_agent_id)
    _dump_run_cache(cache_dir, out)
    elapsed = time.time() - started
    result = LeaveOneOutRunResult(
        excluded_agent_id=exclude_agent_id,
        n_trades=len(out.trades),
        n_shadow=len(out.shadow_trades),
        n_proposals=len(out.proposals_all),
        cache_dir=cache_dir,
        elapsed_sec=elapsed,
    )
    log.info(
        "leave-one-out complete: excluded=%s trades=%d shadow=%d "
        "elapsed=%.1fs cache=%s",
        exclude_agent_id or "<baseline>",
        result.n_trades, result.n_shadow, result.elapsed_sec, cache_dir,
    )
    return result


# ---------------------------------------------------------------------------
# Full batch runner (8 replays)
# ---------------------------------------------------------------------------

def run_all_leave_one_outs(
    *,
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    out_dir: Path,
    tag: str = "post-V",
    exclude_agents: Iterable[str] | None = None,
    include_baseline: bool = False,
) -> list[LeaveOneOutRunResult]:
    """Run all 8 leave-one-out replays in canonical order.

    ``include_baseline=True`` also runs the full 8-agent baseline as
    the first replay. Default False -- baseline is expected to be
    reused from an on-disk cache produced by
    ``run_g7_v1_checkpoint_gate.run_g7_walk_forward`` (e.g.
    ``g7_replay_cache_walk-forward-post-V``).
    """
    ensure_production_repo_on_path()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info(
        "leave-one-out batch start: panel=%s..%s out=%s tag=%s",
        panel_start.date(), panel_end.date(), out_dir, tag,
    )

    bars_by_symbol: dict[str, list] = {}
    for sym in SYMBOLS_G7:
        bars_by_symbol[sym] = _load_production_bars(
            sym, panel_start, panel_end,
        )
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    all_agents, isagi, barou, kunigami = _instantiate_all_agents()
    _prepare_agents(all_agents, bars_by_symbol)

    to_exclude: list[str | None] = []
    if include_baseline:
        to_exclude.append(None)
    excludes = (
        tuple(exclude_agents) if exclude_agents is not None else G7_AGENT_ORDER
    )
    to_exclude.extend(excludes)

    results: list[LeaveOneOutRunResult] = []
    for i, ex in enumerate(to_exclude):
        log.info(
            "=== leave-one-out %d/%d: excluded=%s ===",
            i + 1, len(to_exclude), ex or "<baseline>",
        )
        try:
            result = run_single_leave_one_out(
                exclude_agent_id=ex,
                all_agents=all_agents,
                isagi=isagi, barou=barou, kunigami=kunigami,
                bars_by_symbol=bars_by_symbol,
                out_dir=out_dir, tag=tag,
            )
            results.append(result)
        except Exception:                                  # pragma: no cover
            # Crash-proof: log and continue so a bug in one leave-one-out
            # doesn't wipe the completed ones.
            log.exception(
                "leave-one-out failed for excluded=%s -- continuing to next",
                ex,
            )
    log.info(
        "leave-one-out batch complete: %d/%d runs succeeded",
        len(results), len(to_exclude),
    )
    return results


# ---------------------------------------------------------------------------
# C2/C3 aggregation
# ---------------------------------------------------------------------------

def _load_trades_from_jsonl(path: Path) -> list[dict]:
    """Read one ``trades.jsonl`` cache. Empty file -> empty list."""
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _per_agent_stats(trades: list[dict]) -> dict[str, dict[str, float]]:
    """Per-agent (agent_id) mean TQS + trade count from a trades list.

    TQS is per-trade quality score, stored in ``tqs`` field on
    ``TradeRecord``. Trade count includes ALL trades (even those with
    missing/None TQS -- they still executed). Mean TQS is computed
    over the subset of trades with a valid numeric TQS, so missing
    values don't bias the mean toward zero.
    """
    counts: dict[str, int] = {}
    tqs_valid_counts: dict[str, int] = {}
    tqs_sums: dict[str, float] = {}
    for t in trades:
        aid = t.get("agent_id")
        if not aid:
            continue
        counts[aid] = counts.get(aid, 0) + 1
        tqs = t.get("tqs")
        if tqs is None:
            continue
        try:
            v = float(tqs)
        except (TypeError, ValueError):
            continue
        tqs_valid_counts[aid] = tqs_valid_counts.get(aid, 0) + 1
        tqs_sums[aid] = tqs_sums.get(aid, 0.0) + v
    out: dict[str, dict[str, float]] = {}
    for aid, n in counts.items():
        n_valid = tqs_valid_counts.get(aid, 0)
        mean_tqs = (
            tqs_sums.get(aid, 0.0) / n_valid if n_valid > 0 else 0.0
        )
        out[aid] = {"n_trades": float(n), "mean_tqs": mean_tqs}
    return out


@dataclass
class C2C3Result:
    """Aggregate C2/C3 verdict for one excluded agent."""

    excluded_agent_id: str
    # Per-remaining-agent (baseline - lo1) deltas. Positive delta on
    # trade count means the excluded agent's PRESENCE increased that
    # peer's trades. Positive delta on TQS means the excluded agent's
    # PRESENCE raised that peer's mean TQS.
    per_peer_delta_trades: dict[str, float] = field(default_factory=dict)
    per_peer_delta_tqs: dict[str, float] = field(default_factory=dict)
    # C2 pass = at least one remaining agent has strictly positive
    # delta on TQS OR trade count (i.e. removing the excluded agent
    # hurts at least one peer).
    c2_pass: bool = False
    c2_reason: str = ""
    # C3 stat = worst per-peer trade-count reduction ratio caused by
    # the excluded agent's PRESENCE. Positive value means the excluded
    # agent cannibalises that peer. Threshold: reduction > 0.5 (50%)
    # in a peer's trades is a cannibalisation flag.
    c3_worst_reduction_ratio: float = 0.0
    c3_worst_peer: str | None = None
    c3_pass: bool = True
    c3_reason: str = ""


def _compute_reduction_ratio(baseline_n: float, lo1_n: float) -> float:
    """Ratio of peer trade count loss caused by the excluded agent's
    presence. Positive means "excluded agent cost peer trades" (peer
    trades more when excluded agent is absent).

    Returns 0 when the baseline count is 0 (avoids div-by-zero /
    can't reduce below zero).
    """
    if baseline_n <= 0:
        return 0.0
    return (lo1_n - baseline_n) / lo1_n if lo1_n > 0 else 1.0


def compute_c2_c3(
    *,
    baseline_stats: dict[str, dict[str, float]],
    per_excluded_stats: dict[str, dict[str, dict[str, float]]],
    c2_epsilon_tqs: float = 0.005,
    c2_epsilon_trades: float = 1.0,
    c3_reduction_threshold: float = 0.5,
) -> dict[str, C2C3Result]:
    """Compute C2 (positive-sum chemistry) + C3 (non-cannibalising slot).

    ``per_excluded_stats[excluded_id][peer_id]`` = the leave-one-out
    stats when ``excluded_id`` was removed.

    C2 pass condition (per excluded agent X):
        exists peer p such that
            baseline_stats[p]["mean_tqs"] - lo1_stats_without_X[p]["mean_tqs"]
                > c2_epsilon_tqs
        OR
            baseline_stats[p]["n_trades"] - lo1_stats_without_X[p]["n_trades"]
                > c2_epsilon_trades

    C3 fail condition (per excluded agent X):
        exists peer p such that
            (lo1_stats_without_X[p]["n_trades"] - baseline_stats[p]["n_trades"])
                / lo1_stats_without_X[p]["n_trades"]
                > c3_reduction_threshold
        (peer trades > 50% more when X is removed => X cannibalises)
    """
    out: dict[str, C2C3Result] = {}
    for excluded_id, lo1_stats in per_excluded_stats.items():
        result = C2C3Result(excluded_agent_id=excluded_id)
        best_lift_peer: str | None = None
        best_lift_val: float = 0.0
        worst_reduction: float = 0.0
        worst_reduction_peer: str | None = None
        c2_hit_by = None
        for peer_id, peer_lo1 in lo1_stats.items():
            if peer_id == excluded_id:
                continue
            peer_baseline = baseline_stats.get(peer_id, {})
            b_tqs = float(peer_baseline.get("mean_tqs", 0.0))
            b_n = float(peer_baseline.get("n_trades", 0.0))
            l_tqs = float(peer_lo1.get("mean_tqs", 0.0))
            l_n = float(peer_lo1.get("n_trades", 0.0))
            delta_tqs = b_tqs - l_tqs
            delta_trades = b_n - l_n
            result.per_peer_delta_tqs[peer_id] = delta_tqs
            result.per_peer_delta_trades[peer_id] = delta_trades
            lift = max(delta_tqs / max(c2_epsilon_tqs, 1e-9),
                       delta_trades / max(c2_epsilon_trades, 1e-9))
            if lift > best_lift_val:
                best_lift_val = lift
                best_lift_peer = peer_id
            if (delta_tqs > c2_epsilon_tqs or delta_trades > c2_epsilon_trades):
                if c2_hit_by is None:
                    c2_hit_by = (peer_id, delta_tqs, delta_trades)
            red = _compute_reduction_ratio(baseline_n=b_n, lo1_n=l_n)
            if red > worst_reduction:
                worst_reduction = red
                worst_reduction_peer = peer_id
        result.c2_pass = c2_hit_by is not None
        if result.c2_pass and c2_hit_by is not None:
            peer, dt, dn = c2_hit_by
            result.c2_reason = (
                f"peer {peer!r} lifted by presence: "
                f"delta_tqs={dt:+.4f} delta_trades={dn:+.1f}"
            )
        else:
            result.c2_reason = (
                f"no peer lifted by more than epsilon "
                f"(tqs>{c2_epsilon_tqs}, trades>{c2_epsilon_trades}); "
                f"best lift on {best_lift_peer!r} at "
                f"{best_lift_val:.3f} epsilon-units"
            )
        result.c3_worst_reduction_ratio = worst_reduction
        result.c3_worst_peer = worst_reduction_peer
        result.c3_pass = worst_reduction <= c3_reduction_threshold
        if result.c3_pass:
            result.c3_reason = (
                f"worst per-peer reduction "
                f"{worst_reduction:.3f} on {worst_reduction_peer!r}; "
                f"below threshold {c3_reduction_threshold}"
            )
        else:
            result.c3_reason = (
                f"CANNIBALISATION: peer {worst_reduction_peer!r} "
                f"traded {worst_reduction*100:.1f}% more when "
                f"{excluded_id!r} was absent"
            )
        out[excluded_id] = result
    return out


def aggregate_from_disk(
    *,
    baseline_cache_dir: Path,
    lo1_root_dir: Path,
    tag: str,
) -> tuple[dict, dict[str, dict[str, float]], dict[str, C2C3Result]]:
    """Compose the on-disk trades caches into a C2/C3 verdict.

    Returns:
        (baseline_stats, per_excluded_stats_mapping, c2c3_results)
    """
    baseline_trades_path = baseline_cache_dir / "trades.jsonl"
    baseline_trades = _load_trades_from_jsonl(baseline_trades_path)
    baseline_stats = _per_agent_stats(baseline_trades)
    log.info(
        "loaded baseline: %d trades across %d agents",
        len(baseline_trades), len(baseline_stats),
    )

    per_excluded_stats: dict[str, dict[str, dict[str, float]]] = {}
    lo1_dir = lo1_root_dir / f"g7_leave_one_out_{tag}"
    for aid in G7_AGENT_ORDER:
        cache_dir = lo1_dir / f"lo1_{aid}"
        trades = _load_trades_from_jsonl(cache_dir / "trades.jsonl")
        if not trades:
            log.warning(
                "leave-one-out cache for excluded=%s missing or empty at %s",
                aid, cache_dir,
            )
            continue
        per_excluded_stats[aid] = _per_agent_stats(trades)
        log.info(
            "loaded lo1 excluded=%s: %d trades",
            aid, len(trades),
        )
    c2c3 = compute_c2_c3(
        baseline_stats=baseline_stats,
        per_excluded_stats=per_excluded_stats,
    )
    return baseline_stats, per_excluded_stats, c2c3


# ---------------------------------------------------------------------------
# Verdict markdown emitter
# ---------------------------------------------------------------------------

def emit_c2_c3_verdict_md(
    *,
    baseline_stats: dict[str, dict[str, float]],
    per_excluded_stats: dict[str, dict[str, dict[str, float]]],
    c2c3: dict[str, C2C3Result],
    out_path: Path,
    tag: str,
) -> None:
    """Emit a markdown verdict summarising C2/C3 per agent."""
    lines: list[str] = []
    lines.append(f"# G7 leave-one-out C2/C3 verdict ({tag})")
    lines.append("")
    lines.append(
        f"Generated {datetime.now(tz=timezone.utc).isoformat()} from"
        f" baseline + {len(per_excluded_stats)} leave-one-out replays."
    )
    lines.append("")
    lines.append("## Baseline per-agent stats (all 8 agents present)")
    lines.append("")
    lines.append("| Agent | N trades | Mean TQS |")
    lines.append("|---|---:|---:|")
    for aid in G7_AGENT_ORDER:
        s = baseline_stats.get(aid, {})
        lines.append(
            f"| `{aid}` | {int(s.get('n_trades', 0))} | "
            f"{s.get('mean_tqs', 0.0):.4f} |"
        )
    lines.append("")

    lines.append("## Criterion 2 (positive-sum chemistry) per agent")
    lines.append("")
    lines.append(
        "For each excluded agent X, we ask: does removing X hurt at "
        "least one peer? An epsilon-strict positive delta on peer "
        "mean-TQS OR trade count when X is present vs absent = "
        "**C2 PASS**."
    )
    lines.append("")
    lines.append("| Excluded | C2 pass? | Reason |")
    lines.append("|---|:---:|---|")
    for aid in G7_AGENT_ORDER:
        r = c2c3.get(aid)
        if r is None:
            lines.append(f"| `{aid}` | ⏸ | leave-one-out cache missing |")
            continue
        badge = "✅" if r.c2_pass else "❌"
        lines.append(f"| `{aid}` | {badge} | {r.c2_reason} |")
    lines.append("")

    lines.append("## Criterion 3 (non-cannibalising slot behaviour)")
    lines.append("")
    lines.append(
        "Worst per-peer trade-count reduction ratio caused by the "
        "excluded agent's presence. Threshold = 50% (peer trading "
        "more than 50% more when excluded agent is absent = "
        "**C3 FAIL** for that agent -- structural cannibalisation)."
    )
    lines.append("")
    lines.append(
        "| Excluded | Worst peer | Reduction | C3 pass? |"
    )
    lines.append("|---|---|---:|:---:|")
    for aid in G7_AGENT_ORDER:
        r = c2c3.get(aid)
        if r is None:
            lines.append(f"| `{aid}` | -- | -- | ⏸ |")
            continue
        badge = "✅" if r.c3_pass else "❌"
        wp = r.c3_worst_peer or "--"
        lines.append(
            f"| `{aid}` | `{wp}` | "
            f"{r.c3_worst_reduction_ratio*100:.1f}% | {badge} |"
        )
    lines.append("")

    lines.append("## Per-peer delta tables (audit-grade)")
    lines.append("")
    lines.append(
        "For each excluded agent X, delta[p] = "
        "baseline[p].{tqs, n_trades} - lo1_without_X[p].{tqs, n_trades}. "
        "Positive delta means \"X's presence lifts peer p\"."
    )
    lines.append("")
    for aid in G7_AGENT_ORDER:
        r = c2c3.get(aid)
        if r is None:
            continue
        lines.append(f"### Excluded: `{aid}`")
        lines.append("")
        lines.append("| Peer | Δ n_trades | Δ mean_tqs |")
        lines.append("|---|---:|---:|")
        for peer_id in G7_AGENT_ORDER:
            if peer_id == aid:
                continue
            dt = r.per_peer_delta_trades.get(peer_id, 0.0)
            dq = r.per_peer_delta_tqs.get(peer_id, 0.0)
            lines.append(f"| `{peer_id}` | {dt:+.1f} | {dq:+.4f} |")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_path)


def emit_c2_c3_verdict_json(
    *,
    baseline_stats,
    per_excluded_stats,
    c2c3,
    out_path: Path,
    tag: str,
) -> None:
    """JSON companion to the markdown verdict."""
    payload = {
        "tag": tag,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "baseline_stats": baseline_stats,
        "per_excluded_stats": per_excluded_stats,
        "c2_c3": {
            aid: {
                "excluded_agent_id": r.excluded_agent_id,
                "per_peer_delta_trades": r.per_peer_delta_trades,
                "per_peer_delta_tqs": r.per_peer_delta_tqs,
                "c2_pass": r.c2_pass,
                "c2_reason": r.c2_reason,
                "c3_worst_reduction_ratio": r.c3_worst_reduction_ratio,
                "c3_worst_peer": r.c3_worst_peer,
                "c3_pass": r.c3_pass,
                "c3_reason": r.c3_reason,
            }
            for aid, r in c2c3.items()
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8",
    )
    log.info("wrote %s", out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_g7_leave_one_out",
        description=(
            "G7 leave-one-out compute + aggregate. Runs 8 replays "
            "sequentially (~5.6h total), each with one agent removed, "
            "then computes G7 criteria 2 (positive-sum chemistry) and "
            "3 (non-cannibalising slot behaviour) against an on-disk "
            "baseline cache produced by run_g7_v1_checkpoint_gate."
        ),
    )
    p.add_argument("--tag", default="post-V",
                   help="Tag suffix on output caches / verdict files.")
    p.add_argument("--out-dir", type=Path,
                   default=Path("programs/M001_multi_agent_ensemble/reviews"),
                   help="Root dir for lo1 caches + verdict.")
    p.add_argument("--baseline-cache-dir", type=Path,
                   default=Path(
                       "programs/M001_multi_agent_ensemble/reviews/"
                       "g7_replay_cache_walk-forward-post-V"
                   ),
                   help="Existing baseline trades.jsonl location.")
    p.add_argument(
        "--include-baseline", action="store_true",
        help=("Also run the full 8-agent baseline as a leave-one-out "
              "step. Default off -- baseline is reused from an on-disk "
              "cache (see --baseline-cache-dir)."),
    )
    p.add_argument(
        "--exclude", action="append", default=None,
        help=("Restrict the leave-one-out set to specific agent IDs; "
              "repeatable. Default runs all 8."),
    )
    p.add_argument(
        "--aggregate-only", action="store_true",
        help=("Skip compute -- assume all lo1 caches already exist and "
              "just aggregate the C2/C3 verdict from disk."),
    )
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    level = (
        logging.DEBUG if args.verbose >= 2
        else logging.INFO if args.verbose >= 1
        else logging.WARNING
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )

    if not args.aggregate_only:
        run_all_leave_one_outs(
            out_dir=args.out_dir,
            tag=args.tag,
            exclude_agents=args.exclude,
            include_baseline=args.include_baseline,
        )

    baseline_stats, per_excluded_stats, c2c3 = aggregate_from_disk(
        baseline_cache_dir=args.baseline_cache_dir,
        lo1_root_dir=args.out_dir,
        tag=args.tag,
    )
    md_path = args.out_dir / f"g7_leave_one_out_verdict_{args.tag}.md"
    json_path = args.out_dir / f"g7_leave_one_out_verdict_{args.tag}.json"
    emit_c2_c3_verdict_md(
        baseline_stats=baseline_stats,
        per_excluded_stats=per_excluded_stats,
        c2c3=c2c3,
        out_path=md_path, tag=args.tag,
    )
    emit_c2_c3_verdict_json(
        baseline_stats=baseline_stats,
        per_excluded_stats=per_excluded_stats,
        c2c3=c2c3,
        out_path=json_path, tag=args.tag,
    )
    return 0


if __name__ == "__main__":                                 # pragma: no cover
    sys.exit(main())
