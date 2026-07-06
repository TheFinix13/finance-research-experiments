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


# Role Registry v1 -- structural falsifiers waived on trade-based
# criteria (C1/C5/C6 in G7 v1 §11.1, C9 in Role Registry v1 §3). These
# agents have intend() -> None by design and cannot be scored on trade
# volume. Must match the STRUCTURAL_FALSIFIERS set in
# ``run_g7_v1_checkpoint_gate.py`` -- kept as a duplicate literal here
# rather than an import to avoid a circular dependency.
_STRUCTURAL_FALSIFIERS: frozenset[str] = frozenset({
    "reo_mikage",
    "kunigami_rensuke",
})


def _instantiate_all_agents(*, barou_v12: bool = False):
    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1(continuation_entry_enabled=barou_v12)
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
    aggregator_arm: str = "phi41",
) -> LeaveOneOutRunResult:
    """Run one replay with ``exclude_agent_id`` removed from the
    proposer list. ``exclude_agent_id=None`` runs the full baseline.

    ``aggregator_arm`` threads through to ``_drive_squad_replay``
    (phi5_aggregator PROTOCOL §11.4/§11.6): pass ``"arm4"`` to measure
    C2/C3 chemistry under the adopted multi-position aggregator.
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
        aggregator_arm=aggregator_arm,
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
    aggregator_arm: str = "phi41",
    retire_kunigami: bool = False,
    barou_v12: bool = False,
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

    all_agents, isagi, barou, kunigami = _instantiate_all_agents(
        barou_v12=barou_v12,
    )
    if barou_v12:
        log.info(
            "Phase W-barou v1.2 H2 continuation-entry ACTIVE "
            "(experiments/phase_w_barou/PROTOCOL_v1.2.md)"
        )
    _prepare_agents(all_agents, bars_by_symbol)

    if retire_kunigami:
        # Kunigami is retired from the proposer/publisher roster
        # (G7 Role Registry v1 §12.1) but his INSTANCE stays wired so
        # the Sentinel R5 loss-streak side channel keeps working --
        # mirrors run_g7_v1_checkpoint_gate.run_g7_walk_forward.
        all_agents = [
            a for a in all_agents
            if getattr(a, "agent_id", None) != "kunigami_rensuke"
        ]

    to_exclude: list[str | None] = []
    if include_baseline:
        to_exclude.append(None)
    default_order: tuple[str, ...] = (
        tuple(a for a in G7_AGENT_ORDER if a != "kunigami_rensuke")
        if retire_kunigami else G7_AGENT_ORDER
    )
    excludes = (
        tuple(exclude_agents) if exclude_agents is not None else default_order
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
                aggregator_arm=aggregator_arm,
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


def _extract_tqs(t: dict) -> float | None:
    """Extract the composite TQS score from a trade dict.

    The on-disk ``TradeRecord`` shape (verified against
    ``g7_replay_cache_walk-forward-post-V/trades.jsonl`` schema
    2026-07-03) nests the composite TQS under ``tqs_components.tqs``,
    not at the top level. Older internal fixtures (e.g. some Phase R
    scratch caches) put ``tqs`` at top level; we accept both to keep
    the aggregator forward-compatible.

    Returns ``None`` for missing / non-numeric values so the caller
    can distinguish "no TQS" from "TQS = 0.0".
    """
    for candidate in (
        t.get("tqs_components", {}).get("tqs") if isinstance(t.get("tqs_components"), dict) else None,
        t.get("tqs"),
    ):
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _per_agent_stats(trades: list[dict]) -> dict[str, dict[str, float]]:
    """Per-agent (agent_id) mean TQS + trade count from a trades list.

    TQS is per-trade quality score. On the production ``TradeRecord``
    the composite score lives at ``tqs_components["tqs"]`` -- see
    ``_extract_tqs`` for the schema-tolerant reader.

    Trade count includes ALL trades (even those with missing/None
    TQS -- they still executed). Mean TQS is computed over the
    subset of trades with a valid numeric TQS, so missing values
    don't bias the mean toward zero.
    """
    counts: dict[str, int] = {}
    tqs_valid_counts: dict[str, int] = {}
    tqs_sums: dict[str, float] = {}
    for t in trades:
        aid = t.get("agent_id")
        if not aid:
            continue
        counts[aid] = counts.get(aid, 0) + 1
        tqs = _extract_tqs(t)
        if tqs is None:
            continue
        tqs_valid_counts[aid] = tqs_valid_counts.get(aid, 0) + 1
        tqs_sums[aid] = tqs_sums.get(aid, 0.0) + tqs
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
        # STRONGEST-lift tracking (not first-hit). We rank peers by
        # the max of their two normalised deltas (delta_tqs / epsilon_tqs
        # OR delta_trades / epsilon_trades), so a peer with a 15x-epsilon
        # TQS lift outranks a peer with a 1x-epsilon trade-count nudge.
        # First-hit picking (the pre-2026-07-03 05:36 UTC bug) produced
        # misleading c2_reason strings when the dict-insertion-order
        # peer barely cleared threshold while another peer had a much
        # larger lift on a different metric.
        best_lift_peer: str | None = None
        best_lift_val: float = 0.0
        best_lift_delta_tqs: float = 0.0
        best_lift_delta_trades: float = 0.0
        best_lift_metric: str = ""
        worst_reduction: float = 0.0
        worst_reduction_peer: str | None = None
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
            # Normalised per-metric lift ratios. Only consider POSITIVE
            # deltas as "lift" -- a negative delta means the excluded
            # agent HURT the peer, which is not a chemistry signal.
            tqs_lift_epsilons = delta_tqs / max(c2_epsilon_tqs, 1e-9)
            trades_lift_epsilons = (
                delta_trades / max(c2_epsilon_trades, 1e-9)
            )
            if tqs_lift_epsilons >= trades_lift_epsilons:
                peer_lift = tqs_lift_epsilons
                peer_metric = "tqs"
            else:
                peer_lift = trades_lift_epsilons
                peer_metric = "trades"
            if peer_lift > best_lift_val:
                best_lift_val = peer_lift
                best_lift_peer = peer_id
                best_lift_delta_tqs = delta_tqs
                best_lift_delta_trades = delta_trades
                best_lift_metric = peer_metric
            red = _compute_reduction_ratio(baseline_n=b_n, lo1_n=l_n)
            if red > worst_reduction:
                worst_reduction = red
                worst_reduction_peer = peer_id
        # C2 pass = strongest peer clears epsilon on AT LEAST ONE metric.
        # Equivalent to best_lift_val > 1.0 (one epsilon-unit).
        result.c2_pass = (
            best_lift_peer is not None and best_lift_val > 1.0
        )
        if result.c2_pass and best_lift_peer is not None:
            # Explicit metric attribution so a marginal trade-count
            # pass with a negative TQS delta doesn't read as generic
            # "lifted by presence".
            result.c2_reason = (
                f"peer {best_lift_peer!r} lifted by presence: "
                f"delta_tqs={best_lift_delta_tqs:+.4f} "
                f"delta_trades={best_lift_delta_trades:+.1f} "
                f"(strongest on {best_lift_metric}, "
                f"{best_lift_val:.1f}x epsilon)"
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


# ---------------------------------------------------------------------------
# Role Registry v1 (companion to G7 v1) -- C7 (incoming chemistry),
# C8 (workspace-signal impact via peer-delta magnitude proxy), C9
# (trade-volume floor), and role-label emission. Pre-registered in
# ``experiments/G7_role_registry_v1/PROTOCOL.md``.
# ---------------------------------------------------------------------------


@dataclass
class RoleRegistryResult:
    """Per-agent Role Registry v1 verdict + role label(s)."""

    agent_id: str

    # C7 -- incoming chemistry (finisher role).
    c7_pass: bool = False
    c7_reason: str = ""
    c7_lifting_peers: dict[str, float] = field(default_factory=dict)
    c7_status: str = "measured"  # measured | waived

    # C8 -- workspace-signal impact (context-provider role, v1 proxy).
    c8_pass: bool = False
    c8_reason: str = ""
    c8_workspace_impact_epsilons: float = 0.0
    c8_top_impacted_peer: str | None = None

    # C9 -- trade-volume floor (anti-dilution).
    c9_pass: bool = False
    c9_reason: str = ""
    c9_volume_share: float = 0.0
    c9_status: str = "measured"  # measured | waived

    # Role labels emitted per §4 of the protocol. Multiple can apply.
    role_labels: list[str] = field(default_factory=list)

    # Retention rule per §5: pass C3 AND at least one of {C2, C7, C8, C9}.
    # Populated by ``compute_retention`` after C2/C3 are known.
    retained: bool = False
    retention_reason: str = ""


def compute_c7(
    *,
    baseline_stats: dict[str, dict[str, float]],
    per_excluded_stats: dict[str, dict[str, dict[str, float]]],
    c7_lift_threshold: float = 0.02,
    c7_min_lifting_peers: int = 2,
) -> dict[str, RoleRegistryResult]:
    """C7 -- incoming chemistry (finisher role) per Role Registry v1 §3.

    For each agent X, iterate over every OTHER agent p and ask: does X's
    mean TQS DROP when p is removed from the squad? If ≥ c7_min_lifting_peers
    peers each lift X by ≥ c7_lift_threshold in mean TQS, X passes C7 as a
    ``finisher`` (chemistry beneficiary).

    Args:
        baseline_stats: per-agent stats when all agents are present.
        per_excluded_stats: outer key = excluded agent, inner key = peer.
            ``per_excluded_stats[p][X]`` = X's stats in the lo1 run
            without p.
        c7_lift_threshold: minimum TQS drop (baseline - lo1) to count p
            as "lifting X". Default 0.02 = 4x C2's epsilon (deliberately
            stricter than C2 because C7 aggregates across multiple peers).
        c7_min_lifting_peers: how many peers must independently lift X
            for C7 to pass. Default 2.

    Returns:
        dict keyed by agent_id -> RoleRegistryResult with C7 fields
        populated only.
    """
    out: dict[str, RoleRegistryResult] = {}
    for x in G7_AGENT_ORDER:
        result = RoleRegistryResult(agent_id=x)
        x_baseline = baseline_stats.get(x, {})
        x_baseline_tqs = float(x_baseline.get("mean_tqs", 0.0))
        x_baseline_n = float(x_baseline.get("n_trades", 0.0))
        # Structural falsifiers with 0 baseline trades cannot be scored
        # on incoming TQS lift -- there is no TQS to lift.
        if x_baseline_n <= 0:
            result.c7_status = "waived"
            result.c7_pass = False
            result.c7_reason = (
                f"waived: 0 baseline trades (structural falsifier)"
            )
            out[x] = result
            continue
        # Iterate all peers p who could theoretically lift X.
        for p in G7_AGENT_ORDER:
            if p == x:
                continue
            # If we lack an lo1 cache for peer p being excluded, we
            # cannot compute incoming_lift honestly -- skip. Treating
            # missing data as "X's TQS went to zero" would produce
            # false positives (baseline_tqs - 0.0 always exceeds the
            # 0.02 threshold when baseline_tqs is > 0.02).
            if p not in per_excluded_stats:
                continue
            lo1_without_p = per_excluded_stats[p]
            x_when_p_absent = lo1_without_p.get(x)
            # If X has no trades in the lo1_without_p cache either
            # (e.g. X's trades all depend on p being present), the
            # denominator collapses. Skip -- there is nothing to
            # compare.
            if x_when_p_absent is None:
                continue
            x_absent_tqs = float(x_when_p_absent.get("mean_tqs", 0.0))
            # incoming_lift = X's TQS was HIGHER when p WAS present.
            # baseline (all present) - lo1_without_p (X's TQS there).
            incoming_lift = x_baseline_tqs - x_absent_tqs
            if incoming_lift >= c7_lift_threshold:
                result.c7_lifting_peers[p] = incoming_lift
        n_lifters = len(result.c7_lifting_peers)
        result.c7_pass = n_lifters >= c7_min_lifting_peers
        if result.c7_pass:
            top = sorted(
                result.c7_lifting_peers.items(),
                key=lambda kv: -kv[1],
            )[:3]
            top_str = ", ".join(f"{p} +{v:.4f}" for p, v in top)
            result.c7_reason = (
                f"{n_lifters} peers lift {x!r} by >= "
                f"{c7_lift_threshold} TQS. Top: {top_str}"
            )
        else:
            if n_lifters == 0:
                result.c7_reason = (
                    f"no peer lifts {x!r} by >= "
                    f"{c7_lift_threshold} TQS"
                )
            else:
                result.c7_reason = (
                    f"only {n_lifters}/{c7_min_lifting_peers} peers "
                    f"lift {x!r} by >= {c7_lift_threshold} TQS"
                )
        out[x] = result
    return out


def compute_c8_proxy(
    *,
    per_excluded_stats: dict[str, dict[str, dict[str, float]]],
    baseline_stats: dict[str, dict[str, float]],
    results: dict[str, RoleRegistryResult],
    c8_epsilon_tqs: float = 0.005,
    c8_epsilon_trades: float = 1.0,
    c8_impact_threshold: float = 50.0,
) -> None:
    """C8 v1 proxy -- workspace-signal impact via peer-delta magnitude.

    True citation counts (F22c ``interpreted_signal_family``) are not
    persisted in post-V walk-forward artifacts; this v1 proxy uses the
    on-disk lo1 caches to compute a strictly weaker but usable signal:
    when X is excluded, how much do peer stats MOVE (in either direction)?
    A workspace ghost like Kunigami produces zero peer movement; a real
    context provider like Reo produces large peer movement (e.g. Nagi
    -135 trades / +0.0719 TQS quality lift on the surviving trades).

    Args:
        per_excluded_stats: outer key = excluded agent X, inner key = peer.
        baseline_stats: per-agent stats when all agents are present.
        results: dict keyed by agent_id -> RoleRegistryResult (C7 already
            populated). This function fills in C8 fields.
        c8_epsilon_tqs, c8_epsilon_trades: same epsilon-normalisation as
            C2's strongest-lift ranking.
        c8_impact_threshold: workspace_impact score >= this floor passes
            C8. Default 50.0 epsilon-units summed across all peers.

    Mutates ``results`` in place.
    """
    for x in G7_AGENT_ORDER:
        result = results.setdefault(x, RoleRegistryResult(agent_id=x))
        # If we lack an lo1 cache for X being excluded, we cannot
        # measure X's workspace impact honestly. Treating missing data
        # as "all peers went to zero" would produce false positives.
        if x not in per_excluded_stats:
            result.c8_workspace_impact_epsilons = 0.0
            result.c8_top_impacted_peer = None
            result.c8_pass = False
            result.c8_reason = (
                f"no lo1 cache for excluded={x!r}; C8 cannot be measured"
            )
            continue
        lo1_without_x = per_excluded_stats[x]
        total_impact = 0.0
        top_peer: str | None = None
        top_peer_impact = 0.0
        for p in G7_AGENT_ORDER:
            if p == x:
                continue
            p_baseline = baseline_stats.get(p, {})
            b_tqs = float(p_baseline.get("mean_tqs", 0.0))
            b_n = float(p_baseline.get("n_trades", 0.0))
            p_lo1 = lo1_without_x.get(p)
            # Skip peer if we lack their stats in the lo1 cache (same
            # data-availability guard as C7).
            if p_lo1 is None:
                continue
            l_tqs = float(p_lo1.get("mean_tqs", 0.0))
            l_n = float(p_lo1.get("n_trades", 0.0))
            impact_tqs = abs(b_tqs - l_tqs) / max(c8_epsilon_tqs, 1e-9)
            impact_trades = (
                abs(b_n - l_n) / max(c8_epsilon_trades, 1e-9)
            )
            peer_impact = impact_tqs + impact_trades
            total_impact += peer_impact
            if peer_impact > top_peer_impact:
                top_peer_impact = peer_impact
                top_peer = p
        result.c8_workspace_impact_epsilons = total_impact
        result.c8_top_impacted_peer = top_peer
        result.c8_pass = total_impact >= c8_impact_threshold
        if result.c8_pass:
            result.c8_reason = (
                f"workspace_impact={total_impact:.1f} epsilon-units "
                f">= {c8_impact_threshold} threshold "
                f"(top-impacted peer: {top_peer!r} at "
                f"{top_peer_impact:.1f})"
            )
        else:
            result.c8_reason = (
                f"workspace_impact={total_impact:.1f} epsilon-units "
                f"< {c8_impact_threshold} threshold "
                f"(no peer visibly affected by {x!r}'s workspace signals)"
            )


def compute_c9(
    *,
    baseline_stats: dict[str, dict[str, float]],
    results: dict[str, RoleRegistryResult],
    c9_volume_share_floor: float = 0.05,
) -> None:
    """C9 -- trade-volume floor (anti-dilution) per Role Registry v1 §3.

    An agent holding >= c9_volume_share_floor of squad trades cannot be
    cut without measurable volume regression, so retains a slot on
    volume grounds even if C2/C7/C8 all fail. Structural falsifiers
    have 0 trades by design and are waived.

    Args:
        baseline_stats: per-agent stats when all agents are present.
        results: dict keyed by agent_id -> RoleRegistryResult (C7/C8
            already populated). This function fills in C9 fields.
        c9_volume_share_floor: minimum share of squad trades. Default
            0.05 (5%).

    Mutates ``results`` in place.
    """
    total_trades = sum(
        float(baseline_stats.get(a, {}).get("n_trades", 0.0))
        for a in G7_AGENT_ORDER
    )
    for x in G7_AGENT_ORDER:
        result = results.setdefault(x, RoleRegistryResult(agent_id=x))
        x_trades = float(baseline_stats.get(x, {}).get("n_trades", 0.0))
        # Structural falsifiers with 0 trades: waived per §3 C9 note.
        if x in _STRUCTURAL_FALSIFIERS and x_trades <= 0:
            result.c9_status = "waived"
            result.c9_pass = False
            result.c9_volume_share = 0.0
            result.c9_reason = (
                f"waived: structural falsifier "
                f"(intend() -> None by design)"
            )
            continue
        share = x_trades / total_trades if total_trades > 0 else 0.0
        result.c9_volume_share = share
        result.c9_pass = share >= c9_volume_share_floor
        if result.c9_pass:
            result.c9_reason = (
                f"volume_share={share*100:.1f}% >= "
                f"{c9_volume_share_floor*100:.0f}% floor "
                f"({int(x_trades)}/{int(total_trades)} trades)"
            )
        else:
            result.c9_reason = (
                f"volume_share={share*100:.1f}% < "
                f"{c9_volume_share_floor*100:.0f}% floor "
                f"({int(x_trades)}/{int(total_trades)} trades)"
            )


def _assign_role_labels(
    *,
    c2c3: dict[str, C2C3Result],
    results: dict[str, RoleRegistryResult],
) -> None:
    """Emit role labels per Role Registry v1 §4.

    Rules (labels are non-exclusive; multiple can apply):
      * C2 pass                         -> ``chemistry_catalyst``
      * C7 pass                         -> ``finisher``
      * C8 pass                         -> ``workspace_catalyst``
      * C9 pass (and C2/C7/C8 all fail) -> ``volume_specialist``
      * all four fail                   -> ``retirement_candidate``
    """
    for x in G7_AGENT_ORDER:
        result = results.setdefault(x, RoleRegistryResult(agent_id=x))
        c2 = c2c3.get(x)
        labels: list[str] = []
        c2_pass = bool(c2 and c2.c2_pass)
        c7_pass = bool(result.c7_pass)
        c8_pass = bool(result.c8_pass)
        c9_pass = bool(result.c9_pass)
        if c2_pass:
            labels.append("chemistry_catalyst")
        if c7_pass:
            labels.append("finisher")
        if c8_pass:
            labels.append("workspace_catalyst")
        # volume_specialist only applies when NONE of the chemistry
        # axes pass -- an agent held on volume floor alone.
        if c9_pass and not (c2_pass or c7_pass or c8_pass):
            labels.append("volume_specialist")
        # retirement_candidate iff none of {C2, C7, C8, C9} pass.
        if not (c2_pass or c7_pass or c8_pass or c9_pass):
            labels.append("retirement_candidate")
        result.role_labels = labels


def compute_retention(
    *,
    c2c3: dict[str, C2C3Result],
    results: dict[str, RoleRegistryResult],
) -> None:
    """Apply the Role Registry v1 §5 retention rule.

    Rule: pass C3 (non-cannibalising) AND at least one of
    {C2, C7, C8, C9}. Structural-falsifier waivers on C9 do NOT count
    toward the OR-gate (waived != pass); C9 must be an actual pass or
    else the agent needs some other axis.
    """
    for x in G7_AGENT_ORDER:
        result = results.setdefault(x, RoleRegistryResult(agent_id=x))
        c2 = c2c3.get(x)
        c3_pass = bool(c2 and c2.c3_pass)
        c2_pass = bool(c2 and c2.c2_pass)
        c7_pass = bool(result.c7_pass)
        c8_pass = bool(result.c8_pass)
        c9_pass = bool(result.c9_pass)
        any_role_axis = c2_pass or c7_pass or c8_pass or c9_pass
        result.retained = bool(c3_pass and any_role_axis)
        axes = []
        if c2_pass:
            axes.append("C2")
        if c7_pass:
            axes.append("C7")
        if c8_pass:
            axes.append("C8")
        if c9_pass:
            axes.append("C9")
        if result.retained:
            result.retention_reason = (
                f"RETAINED: C3 pass AND role axis {axes} "
                f"(labels: {result.role_labels})"
            )
        elif not c3_pass:
            result.retention_reason = (
                f"NOT RETAINED: C3 fail (cannibalises peer)"
            )
        else:
            result.retention_reason = (
                f"NOT RETAINED: C3 pass but no role axis passes "
                f"(C2/C7/C8/C9 all fail)"
            )


def compute_role_registry(
    *,
    baseline_stats: dict[str, dict[str, float]],
    per_excluded_stats: dict[str, dict[str, dict[str, float]]],
    c2c3: dict[str, C2C3Result],
) -> dict[str, RoleRegistryResult]:
    """One-stop composition: C7 + C8 (proxy) + C9 + labels + retention."""
    results = compute_c7(
        baseline_stats=baseline_stats,
        per_excluded_stats=per_excluded_stats,
    )
    compute_c8_proxy(
        per_excluded_stats=per_excluded_stats,
        baseline_stats=baseline_stats,
        results=results,
    )
    compute_c9(
        baseline_stats=baseline_stats,
        results=results,
    )
    _assign_role_labels(c2c3=c2c3, results=results)
    compute_retention(c2c3=c2c3, results=results)
    return results


def aggregate_from_disk(
    *,
    baseline_cache_dir: Path,
    lo1_root_dir: Path,
    tag: str,
) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, dict[str, float]]],
    dict[str, C2C3Result],
    dict[str, RoleRegistryResult],
]:
    """Compose the on-disk trades caches into a C2/C3 + Role Registry verdict.

    Returns:
        (baseline_stats, per_excluded_stats, c2c3_results, role_registry)
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
    role_registry = compute_role_registry(
        baseline_stats=baseline_stats,
        per_excluded_stats=per_excluded_stats,
        c2c3=c2c3,
    )
    return baseline_stats, per_excluded_stats, c2c3, role_registry


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
# Role Registry v1 emitters
# ---------------------------------------------------------------------------

def emit_role_registry_verdict_md(
    *,
    baseline_stats: dict[str, dict[str, float]],
    c2c3: dict[str, C2C3Result],
    role_registry: dict[str, RoleRegistryResult],
    out_path: Path,
    tag: str,
) -> None:
    """Emit Role Registry v1 verdict markdown."""
    lines: list[str] = []
    lines.append(f"# G7 Role Registry v1 verdict ({tag})")
    lines.append("")
    lines.append(
        f"Generated {datetime.now(tz=timezone.utc).isoformat()} "
        f"from post-{tag} baseline + leave-one-out caches. "
        f"Pre-registered protocol: "
        f"`experiments/G7_role_registry_v1/PROTOCOL.md`."
    )
    lines.append("")
    lines.append(
        "**Companion to G7 v1** — adds three role-differentiating "
        "criteria (C7 incoming chemistry / C8 workspace-signal impact / "
        "C9 trade-volume floor) and role labels. Retention rule (per §5): "
        "C3 pass AND at least one of {C2, C7, C8, C9} pass."
    )
    lines.append("")

    lines.append("## Role Registry summary")
    lines.append("")
    lines.append(
        "| Agent | C2 | C3 | C7 | C8 | C9 | Role labels | Retained |"
    )
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|---|:---:|")
    for aid in G7_AGENT_ORDER:
        c2 = c2c3.get(aid)
        rr = role_registry.get(aid)
        if c2 is None or rr is None:
            lines.append(
                f"| `{aid}` | ⏸ | ⏸ | ⏸ | ⏸ | ⏸ | pending | ⏸ |"
            )
            continue

        def _badge(passed: bool, status: str = "measured") -> str:
            if status == "waived":
                return "W"
            return "✅" if passed else "❌"

        c2b = _badge(c2.c2_pass)
        c3b = _badge(c2.c3_pass)
        c7b = _badge(rr.c7_pass, rr.c7_status)
        c8b = _badge(rr.c8_pass)
        c9b = _badge(rr.c9_pass, rr.c9_status)
        labels = ", ".join(rr.role_labels) if rr.role_labels else "--"
        retained_badge = "✅" if rr.retained else "❌"
        lines.append(
            f"| `{aid}` | {c2b} | {c3b} | {c7b} | {c8b} | {c9b} | "
            f"{labels} | {retained_badge} |"
        )
    lines.append("")

    lines.append("## Criterion 7 — Incoming chemistry (finisher role)")
    lines.append("")
    lines.append(
        "For each agent X, count peers p that lift X's mean TQS by "
        "≥ 0.02 (4× C2's epsilon) when p is present vs absent. "
        "**C7 PASS** if ≥ 2 peers independently lift X."
    )
    lines.append("")
    lines.append(
        "| Agent | Lifting peers | Reason |"
    )
    lines.append("|---|:---:|---|")
    for aid in G7_AGENT_ORDER:
        rr = role_registry.get(aid)
        if rr is None:
            lines.append(f"| `{aid}` | ⏸ | pending |")
            continue
        n_lifters = len(rr.c7_lifting_peers)
        if rr.c7_status == "waived":
            badge = "W"
        else:
            badge = f"{n_lifters} ({'✅' if rr.c7_pass else '❌'})"
        lines.append(f"| `{aid}` | {badge} | {rr.c7_reason} |")
    lines.append("")

    lines.append(
        "## Criterion 8 — Workspace-signal impact (v1 proxy)"
    )
    lines.append("")
    lines.append(
        "Peer-delta magnitude proxy for workspace-signal consumption "
        "(the true `IntentDecision.interpreted_signal_family` citation "
        "count is not persisted in post-V artifacts; see PROTOCOL §12 "
        "amendment note). **C8 PASS** if workspace_impact ≥ 50 "
        "epsilon-units summed across all peers."
    )
    lines.append("")
    lines.append(
        "| Agent | Workspace impact | C8 | Top-impacted peer |"
    )
    lines.append("|---|---:|:---:|---|")
    for aid in G7_AGENT_ORDER:
        rr = role_registry.get(aid)
        if rr is None:
            lines.append(f"| `{aid}` | -- | ⏸ | -- |")
            continue
        badge = "✅" if rr.c8_pass else "❌"
        top = rr.c8_top_impacted_peer or "--"
        lines.append(
            f"| `{aid}` | "
            f"{rr.c8_workspace_impact_epsilons:.1f} | "
            f"{badge} | `{top}` |"
        )
    lines.append("")

    lines.append("## Criterion 9 — Trade-volume floor (anti-dilution)")
    lines.append("")
    lines.append(
        "**C9 PASS** if the agent holds ≥ 5% of squad baseline trades. "
        "Structural falsifiers (Reo, Kunigami) are waived on C9 per "
        "PROTOCOL §3."
    )
    lines.append("")
    lines.append(
        "| Agent | Volume share | C9 | Reason |"
    )
    lines.append("|---|---:|:---:|---|")
    for aid in G7_AGENT_ORDER:
        rr = role_registry.get(aid)
        if rr is None:
            lines.append(f"| `{aid}` | -- | ⏸ | -- |")
            continue
        badge = "W" if rr.c9_status == "waived" else (
            "✅" if rr.c9_pass else "❌"
        )
        lines.append(
            f"| `{aid}` | "
            f"{rr.c9_volume_share*100:.1f}% | "
            f"{badge} | {rr.c9_reason} |"
        )
    lines.append("")

    lines.append("## Retention verdict")
    lines.append("")
    lines.append(
        "Rule (§5): agent retained iff C3 pass AND at least one of "
        "{C2, C7, C8, C9} passes. Waived counts as \"not a pass\" for "
        "the OR-gate; the agent must have real evidence on at least "
        "one axis."
    )
    lines.append("")
    lines.append("| Agent | Retained | Role labels | Reason |")
    lines.append("|---|:---:|---|---|")
    for aid in G7_AGENT_ORDER:
        rr = role_registry.get(aid)
        if rr is None:
            lines.append(f"| `{aid}` | ⏸ | -- | pending |")
            continue
        badge = "✅" if rr.retained else "❌"
        labels = ", ".join(rr.role_labels) if rr.role_labels else "--"
        lines.append(
            f"| `{aid}` | {badge} | {labels} | {rr.retention_reason} |"
        )
    lines.append("")

    retirement_candidates = [
        aid for aid in G7_AGENT_ORDER
        if (
            (rr := role_registry.get(aid)) is not None
            and "retirement_candidate" in rr.role_labels
        )
    ]
    non_retained = [
        aid for aid in G7_AGENT_ORDER
        if (
            (rr := role_registry.get(aid)) is not None and not rr.retained
        )
    ]
    lines.append("## Squad-level verdict")
    lines.append("")
    lines.append(
        f"- Retirement candidates: "
        f"{len(retirement_candidates)} "
        f"({', '.join(f'`{a}`' for a in retirement_candidates) or 'none'})"
    )
    lines.append(
        f"- Agents failing retention: {len(non_retained)} "
        f"({', '.join(f'`{a}`' for a in non_retained) or 'none'})"
    )
    passed = len(retirement_candidates) == 0
    lines.append(
        f"- Squad Role Registry verdict: "
        f"**{'PASS' if passed else 'FAIL'}** "
        f"(threshold: 0 retirement candidates)"
    )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote %s", out_path)


def emit_role_registry_verdict_json(
    *,
    baseline_stats: dict[str, dict[str, float]],
    c2c3: dict[str, C2C3Result],
    role_registry: dict[str, RoleRegistryResult],
    out_path: Path,
    tag: str,
) -> None:
    """JSON companion to the Role Registry markdown verdict."""
    payload = {
        "tag": tag,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "baseline_stats": baseline_stats,
        "c2_c3": {
            aid: {
                "c2_pass": r.c2_pass,
                "c2_reason": r.c2_reason,
                "c3_pass": r.c3_pass,
                "c3_reason": r.c3_reason,
            }
            for aid, r in c2c3.items()
        },
        "role_registry": {
            aid: {
                "agent_id": rr.agent_id,
                "c7_pass": rr.c7_pass,
                "c7_reason": rr.c7_reason,
                "c7_lifting_peers": rr.c7_lifting_peers,
                "c7_status": rr.c7_status,
                "c8_pass": rr.c8_pass,
                "c8_reason": rr.c8_reason,
                "c8_workspace_impact_epsilons": (
                    rr.c8_workspace_impact_epsilons
                ),
                "c8_top_impacted_peer": rr.c8_top_impacted_peer,
                "c9_pass": rr.c9_pass,
                "c9_reason": rr.c9_reason,
                "c9_volume_share": rr.c9_volume_share,
                "c9_status": rr.c9_status,
                "role_labels": rr.role_labels,
                "retained": rr.retained,
                "retention_reason": rr.retention_reason,
            }
            for aid, rr in role_registry.items()
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
    p.add_argument(
        "--no-aggregate", action="store_true",
        help=("Compute only -- skip the C2/C3 aggregation step. Use "
              "when running per-agent lo1 replays in parallel processes "
              "(each with a single --exclude); aggregate once at the "
              "end with --aggregate-only."),
    )
    p.add_argument(
        "--aggregator-arm", default="phi41",
        choices=("phi41", "arm3", "arm4"),
        help=("Aggregator arm threaded into _drive_squad_replay for "
              "every lo1 replay (phi5_aggregator PROTOCOL §11.6)."),
    )
    p.add_argument(
        "--retire-kunigami", action="store_true",
        help=("Drop Kunigami from the proposer roster (Role Registry "
              "v1 §12.1) and from the default lo1 exclusion order; his "
              "instance stays wired for the Sentinel R5 side channel."),
    )
    p.add_argument(
        "--barou-v12", action="store_true",
        help=("Phase W-barou v1.2 H2 continuation-entry (experiments/"
              "phase_w_barou/PROTOCOL_v1.2.md)."),
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
            aggregator_arm=args.aggregator_arm,
            retire_kunigami=args.retire_kunigami,
            barou_v12=args.barou_v12,
        )

    if args.no_aggregate:
        return 0

    baseline_stats, per_excluded_stats, c2c3, role_registry = (
        aggregate_from_disk(
            baseline_cache_dir=args.baseline_cache_dir,
            lo1_root_dir=args.out_dir,
            tag=args.tag,
        )
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
    role_md_path = (
        args.out_dir / f"g7_role_registry_verdict_{args.tag}.md"
    )
    role_json_path = (
        args.out_dir / f"g7_role_registry_verdict_{args.tag}.json"
    )
    emit_role_registry_verdict_md(
        baseline_stats=baseline_stats,
        c2c3=c2c3,
        role_registry=role_registry,
        out_path=role_md_path, tag=args.tag,
    )
    emit_role_registry_verdict_json(
        baseline_stats=baseline_stats,
        c2c3=c2c3,
        role_registry=role_registry,
        out_path=role_json_path, tag=args.tag,
    )
    return 0


if __name__ == "__main__":                                 # pragma: no cover
    sys.exit(main())
