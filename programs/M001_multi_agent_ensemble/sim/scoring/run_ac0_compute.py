"""Phase AC.0-v2 fresh-compute harness — per-movable-agent walk-forward.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        AMENDMENT_2026-07-20_ac0_methodology_switch.md
    (amends PROTOCOL.md §5 AC.0 and §12 sequencing; §3, §4, §6 unchanged.)

What this does
--------------

For each movable agent in ``movable_agents`` (default: Chigiri, Rin,
Kunigami-un-retired), instantiates the standard 7-proposer roster
(Isagi, Bachira, Rin, Chigiri, Reo, Nagi, Barou) with THAT agent's
``.symbols`` widened to the requested extended panel, then drives
``_drive_squad_replay`` end-to-end over the G7 walk-forward panel
(2015-01-01 → 2025-12-31, 4-yr IS / 1-yr OOS × 7 windows). Kunigami is
included as an active proposer ONLY inside his own run
(``include_kunigami_unretired=True``); in the Chigiri and Rin runs he
stays R5 side-channel only, matching the retired-Kunigami baseline the
sealed g7retry1 verdicts were computed against.

Per-movable trades are sliced by (symbol, window) and reduced to a
mean-TQS statistic (plus trade count). The resulting per-movable
telemetry lands as ``<agent_id>_walkforward.json`` (machine-readable)
and ``<agent_id>_walkforward.md`` (human-readable) in ``out_dir``. A
summary ``summary.json`` is written listing every produced artefact
and the run-time roster composition.

The regression against the frozen ``pair_character.json`` (see
``PROTOCOL.md`` §4) is a separate step and lives in
``sim/analysis/regress_ac0.py``. This module produces the y-axis
inputs only; the frozen x-axis is untouched.

Statistical honesty guarantees
------------------------------

- Every other agent stays at their v1 doctrine defaults on every run.
  Only the movable's ``.symbols`` widens.
- The Kunigami-un-retirement flag applies only to Kunigami's own
  run. In Chigiri's and Rin's runs Kunigami stays R5 side-channel only
  (the retired-Kunigami configuration the g7retry1 baseline used).
- Missing pairs (not in the production parquet cache) are skipped
  with a WARNING log line; they are NOT silently zero-filled. The
  regression module later must join on the frozen ``pair_character.json``
  so a missing pair simply drops out of the x-axis for every movable.
- Each run gets a FRESH set of agent instances -- no state leaks
  between the three movables' walk-forwards.
- Roster composition per movable is recorded in the JSON output for
  audit under `roster` (see the Ac0ComputeReport §10 kill condition).

CLI
---

::

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_ac0_compute \\
        --symbols EURUSD GBPUSD USDCAD AUDUSD NZDUSD \\
        --out-dir programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/ac0_compute/
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
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
    WalkForwardWindow,
    _g7_windows,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    _load_production_bars,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    _drive_squad_replay,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Locked defaults (do NOT change without a further amendment)
# ---------------------------------------------------------------------------

MOVABLE_AGENTS_DEFAULT: tuple[str, ...] = (
    "chigiri_hyoma", "itoshi_rin", "kunigami_rensuke",
)

# Full extended panel per PROTOCOL.md §8 (USDJPY/USDCHF conditional on
# cache pull; skipped at runtime if not in production parquet).
SYMBOLS_EXTENDED: tuple[str, ...] = (
    "EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF",
)

_ALL_MOVABLE_IDS: frozenset[str] = frozenset(MOVABLE_AGENTS_DEFAULT)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WindowSlice:
    """Serializable projection of ``WalkForwardWindow`` (isoformat dates)."""

    idx: int
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str

    @classmethod
    def from_window(cls, w: WalkForwardWindow) -> "WindowSlice":
        return cls(
            idx=int(w.idx),
            is_start=w.is_start.isoformat(),
            is_end=w.is_end.isoformat(),
            oos_start=w.oos_start.isoformat(),
            oos_end=w.oos_end.isoformat(),
        )


@dataclass
class PairWindowStat:
    """Per-(symbol, window) mean-TQS + trade count for one agent."""

    symbol: str
    window_idx: int
    mean_tqs: float
    n_trades: int


@dataclass
class RosterEntry:
    """Roster row recorded for the audit sentinel (§10 kill condition)."""

    agent_id: str
    playstyle: str
    symbols: tuple[str, ...]
    is_proposer: bool
    is_movable_being_widened: bool

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "playstyle": self.playstyle,
            "symbols": list(self.symbols),
            "is_proposer": bool(self.is_proposer),
            "is_movable_being_widened": bool(self.is_movable_being_widened),
        }


@dataclass
class MovableAgentRunTelemetry:
    """Result bundle for one movable-agent fresh walk-forward."""

    agent_id: str
    requested_symbols: tuple[str, ...]
    available_symbols: tuple[str, ...]
    skipped_symbols: tuple[str, ...]
    roster: list[RosterEntry]
    windows: list[WindowSlice]
    per_pair_window_stats: list[PairWindowStat]
    n_thoughts: int
    n_proposals: int
    n_trades_total: int
    n_trades_movable: int
    aggregator_arm: str
    include_kunigami_unretired: bool
    fired_at_utc: str

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "requested_symbols": list(self.requested_symbols),
            "available_symbols": list(self.available_symbols),
            "skipped_symbols": list(self.skipped_symbols),
            "roster": [r.to_jsonable() for r in self.roster],
            "windows": [asdict(w) for w in self.windows],
            "per_pair_window_stats": [asdict(s) for s in self.per_pair_window_stats],
            "n_thoughts": int(self.n_thoughts),
            "n_proposals": int(self.n_proposals),
            "n_trades_total": int(self.n_trades_total),
            "n_trades_movable": int(self.n_trades_movable),
            "aggregator_arm": self.aggregator_arm,
            "include_kunigami_unretired": bool(self.include_kunigami_unretired),
            "fired_at_utc": self.fired_at_utc,
        }


@dataclass
class Ac0ComputeReport:
    """Top-level report bundle for one AC.0-v2 compute session."""

    panel_start_utc: str
    panel_end_utc: str
    requested_symbols: tuple[str, ...]
    available_symbols: tuple[str, ...]
    skipped_symbols: tuple[str, ...]
    movable_agents: tuple[str, ...]
    aggregator_arm: str
    include_kunigami_unretired: bool
    is_years: int
    oos_years: int
    per_movable: dict[str, MovableAgentRunTelemetry] = field(default_factory=dict)
    fired_at_utc: str = ""

    def to_jsonable(self) -> dict:
        return {
            "panel_start_utc": self.panel_start_utc,
            "panel_end_utc": self.panel_end_utc,
            "requested_symbols": list(self.requested_symbols),
            "available_symbols": list(self.available_symbols),
            "skipped_symbols": list(self.skipped_symbols),
            "movable_agents": list(self.movable_agents),
            "aggregator_arm": self.aggregator_arm,
            "include_kunigami_unretired": bool(self.include_kunigami_unretired),
            "is_years": int(self.is_years),
            "oos_years": int(self.oos_years),
            "per_movable": {
                aid: t.to_jsonable() for aid, t in self.per_movable.items()
            },
            "fired_at_utc": self.fired_at_utc,
        }


# ---------------------------------------------------------------------------
# Panel loading (with skip-missing-pair support)
# ---------------------------------------------------------------------------

def _load_bars_or_none(
    symbol: str, panel_start: datetime, panel_end: datetime,
) -> Optional[list]:
    """Try to load bars for ``symbol``. Return the bar list on success,
    ``None`` on any failure (missing parquet, empty cache, IO error).

    ``_load_production_bars`` raises for symbols not in the production
    parquet cache; wrap it here so ``run_ac0_compute`` can decide
    per-symbol whether to skip or fail per ``skip_missing_pairs``.
    """
    try:
        bars = _load_production_bars(symbol, panel_start, panel_end)
    except Exception as exc:  # noqa: BLE001 -- surface reason in the log
        log.warning(
            "AC.0-v2: symbol %s not loadable from production parquet (%s); "
            "will be skipped from the walk-forward panel",
            symbol, exc,
        )
        return None
    if not bars:
        log.warning(
            "AC.0-v2: symbol %s loaded 0 bars for panel %s -> %s; skipping",
            symbol, panel_start.date(), panel_end.date(),
        )
        return None
    return bars


def _filter_available_symbols(
    symbols: tuple[str, ...],
    panel_start: datetime,
    panel_end: datetime,
    skip_missing_pairs: bool,
) -> tuple[dict[str, list], tuple[str, ...], tuple[str, ...]]:
    """Load bars once per symbol; return (bars_by_symbol, available, skipped).

    If ``skip_missing_pairs=False`` and any symbol fails to load, raise
    ``RuntimeError`` immediately (fail-fast for the compute-session
    worker rather than silently continuing on a degraded panel).
    """
    bars_by_symbol: dict[str, list] = {}
    available: list[str] = []
    skipped: list[str] = []
    for sym in symbols:
        bars = _load_bars_or_none(sym, panel_start, panel_end)
        if bars is None:
            if not skip_missing_pairs:
                raise RuntimeError(
                    f"AC.0-v2: symbol {sym!r} unavailable in production "
                    f"parquet cache for panel {panel_start.date()} -> "
                    f"{panel_end.date()}; pass skip_missing_pairs=True to "
                    "run on the reduced panel"
                )
            skipped.append(sym)
            continue
        bars_by_symbol[sym] = bars
        available.append(sym)
    return bars_by_symbol, tuple(available), tuple(skipped)


# ---------------------------------------------------------------------------
# Roster construction
# ---------------------------------------------------------------------------

def _build_movable_roster(
    movable_id: str,
    available_symbols: tuple[str, ...],
    *,
    include_kunigami_unretired: bool,
) -> tuple[list[Any], A1IsagiV1, A7BarouV1, A10KunigamiV1, list[RosterEntry]]:
    """Instantiate one FRESH roster for the movable's own walk-forward.

    Contract (locked by the amendment §3 + §8):
    - Only the movable agent's ``.symbols`` is widened; every other agent
      stays at their v1 doctrine defaults.
    - Kunigami is R5 side-channel-only unless the movable IS Kunigami
      AND ``include_kunigami_unretired=True``, in which case he is
      added to the PROPOSER roster with his default v1 config.
    - Barou is anchor-locked at ``BAROU_V1_SYMBOLS = ("USDCAD",
      "EURUSD", "GBPUSD")`` per Phase AB; he never widens under
      AC.0-v2 (his mid-band vs Isagi/Rin/Nagi already covers three
      pairs and his devour lift is USDCAD-only).

    Returns ``(proposers, isagi, barou, kunigami, roster_entries)``.
    The isagi/barou/kunigami handles are returned separately because
    ``_drive_squad_replay`` requires them as explicit kwargs (Isagi
    for `_cfg` access, Barou for peer-devour, Kunigami for R5).
    """
    if movable_id not in _ALL_MOVABLE_IDS:
        raise ValueError(
            f"AC.0-v2: unknown movable_id {movable_id!r}; expected one of "
            f"{sorted(_ALL_MOVABLE_IDS)}"
        )

    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = (
        A3RinV1(symbols=list(available_symbols))
        if movable_id == "itoshi_rin" else A3RinV1()
    )
    chigiri = (
        A4ChigiriV1(symbols=list(available_symbols))
        if movable_id == "chigiri_hyoma" else A4ChigiriV1()
    )
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = (
        A10KunigamiV1(symbols=list(available_symbols))
        if movable_id == "kunigami_rensuke" else A10KunigamiV1()
    )

    proposers: list[Any] = [isagi, bachira, rin, chigiri, reo, nagi, barou]
    if movable_id == "kunigami_rensuke" and include_kunigami_unretired:
        proposers.append(kunigami)

    proposer_ids = {a.agent_id for a in proposers}
    all_named = [
        isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami,
    ]
    roster_entries: list[RosterEntry] = []
    for agent in all_named:
        roster_entries.append(RosterEntry(
            agent_id=agent.agent_id,
            playstyle=str(getattr(agent, "playstyle", "unknown")),
            symbols=tuple(agent.symbols),
            is_proposer=agent.agent_id in proposer_ids,
            is_movable_being_widened=agent.agent_id == movable_id,
        ))

    return proposers, isagi, barou, kunigami, roster_entries


def _prepare_agents_on_panel(
    proposers: list[Any],
    bars_by_symbol: dict[str, list],
) -> None:
    """Call ``prepare(sym, bars)`` on every proposer that supports it.

    Mirrors ``run_g7_walk_forward`` (5 of 7 proposers prepare: Isagi,
    Bachira, Rin, Chigiri, Barou; Reo/Nagi/Kunigami have no
    ``prepare`` method).
    """
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in proposers:
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)


# ---------------------------------------------------------------------------
# One movable's walk-forward
# ---------------------------------------------------------------------------

def _run_one_movable(
    *,
    movable_id: str,
    bars_by_symbol: dict[str, list],
    available_symbols: tuple[str, ...],
    skipped_symbols: tuple[str, ...],
    requested_symbols: tuple[str, ...],
    windows: list[WalkForwardWindow],
    aggregator_arm: str,
    include_kunigami_unretired: bool,
) -> MovableAgentRunTelemetry:
    proposers, isagi, barou, kunigami, roster = _build_movable_roster(
        movable_id=movable_id,
        available_symbols=available_symbols,
        include_kunigami_unretired=include_kunigami_unretired,
    )
    _prepare_agents_on_panel(proposers, bars_by_symbol)

    ledger = FullLedger()
    log.info(
        "AC.0-v2 [%s]: driving squad replay | roster=%s | symbols=%s "
        "| aggregator=%s | windows=%d",
        movable_id, [a.agent_id for a in proposers],
        list(available_symbols), aggregator_arm, len(windows),
    )
    out = _drive_squad_replay(
        agents=proposers, isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol, ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,
        use_shadow_ledger=False,      # AC.0-v2 does not need shadow ledger.
        aggregator_arm=aggregator_arm,
    )

    # Roster-composition sentinel (§10 kill condition).
    observed_proposer_ids = {a.agent_id for a in proposers}
    expected_ids = {"isagi_yoichi", "bachira_meguru", "itoshi_rin",
                    "chigiri_hyoma", "reo_mikage", "nagi_seishiro",
                    "barou_shoei"}
    if movable_id == "kunigami_rensuke" and include_kunigami_unretired:
        expected_ids.add("kunigami_rensuke")
    if observed_proposer_ids != expected_ids:
        raise RuntimeError(
            f"AC.0-v2 [{movable_id}]: roster composition mismatch. "
            f"expected={sorted(expected_ids)} observed="
            f"{sorted(observed_proposer_ids)}. See amendment §10."
        )

    per_pair_window_stats: list[PairWindowStat] = []
    movable_trade_count = 0
    for w in windows:
        buckets: dict[str, list[float]] = {sym: [] for sym in available_symbols}
        for t in out.trades:
            if t.agent_id != movable_id:
                continue
            if not (w.oos_start <= t.entry_time < w.oos_end):
                continue
            sym = getattr(t, "symbol", None)
            if sym not in buckets:
                continue
            tqs_val = float((t.tqs_components or {}).get("tqs", 0.0))
            buckets[sym].append(tqs_val)
        for sym in available_symbols:
            vals = buckets[sym]
            movable_trade_count += len(vals)
            per_pair_window_stats.append(PairWindowStat(
                symbol=sym,
                window_idx=int(w.idx),
                mean_tqs=(
                    float(statistics.mean(vals)) if vals else 0.0
                ),
                n_trades=len(vals),
            ))

    telemetry = MovableAgentRunTelemetry(
        agent_id=movable_id,
        requested_symbols=tuple(requested_symbols),
        available_symbols=tuple(available_symbols),
        skipped_symbols=tuple(skipped_symbols),
        roster=roster,
        windows=[WindowSlice.from_window(w) for w in windows],
        per_pair_window_stats=per_pair_window_stats,
        n_thoughts=len(out.thoughts),
        n_proposals=len(out.proposals_all),
        n_trades_total=len(out.trades),
        n_trades_movable=movable_trade_count,
        aggregator_arm=aggregator_arm,
        include_kunigami_unretired=include_kunigami_unretired,
        fired_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    log.info(
        "AC.0-v2 [%s]: replay complete | %d thoughts | %d proposals | "
        "%d trades (%d for movable across %d pair-windows)",
        movable_id, len(out.thoughts), len(out.proposals_all),
        len(out.trades), movable_trade_count, len(per_pair_window_stats),
    )
    return telemetry


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_movable_md(telemetry: MovableAgentRunTelemetry) -> str:
    lines: list[str] = []
    lines.append(f"# AC.0-v2 fresh walk-forward — {telemetry.agent_id}")
    lines.append("")
    lines.append(f"- **Fired:** {telemetry.fired_at_utc}")
    lines.append(f"- **Aggregator arm:** `{telemetry.aggregator_arm}`")
    lines.append(f"- **Requested symbols:** {', '.join(telemetry.requested_symbols)}")
    lines.append(f"- **Available symbols:** {', '.join(telemetry.available_symbols) or '(none)'}")
    if telemetry.skipped_symbols:
        lines.append(
            f"- **Skipped (missing from cache):** "
            f"{', '.join(telemetry.skipped_symbols)}"
        )
    lines.append(
        f"- **Kunigami un-retired for this run:** "
        f"{telemetry.include_kunigami_unretired and telemetry.agent_id == 'kunigami_rensuke'}"
    )
    lines.append("")
    lines.append("## Roster (audit; §10 kill condition)")
    lines.append("")
    lines.append("| Agent | Playstyle | Symbols | Proposer? | Widened? |")
    lines.append("|---|---|---|---|---|")
    for r in telemetry.roster:
        lines.append(
            f"| `{r.agent_id}` | {r.playstyle} | "
            f"{', '.join(r.symbols) or '—'} | "
            f"{'yes' if r.is_proposer else 'no'} | "
            f"{'yes' if r.is_movable_being_widened else 'no'} |"
        )
    lines.append("")
    lines.append(
        f"## Per-pair per-window mean-TQS "
        f"(movable = `{telemetry.agent_id}`, "
        f"{len(telemetry.windows)} windows × "
        f"{len(telemetry.available_symbols)} pairs)"
    )
    lines.append("")
    header = "| Symbol \\ Window |" + "".join(
        f" {w.idx} ({w.oos_start[:4]}) |"
        for w in telemetry.windows
    ) + " total |"
    sep = "|---|" + ("---:|" * (len(telemetry.windows) + 1))
    lines.append(header)
    lines.append(sep)
    by_sym: dict[str, dict[int, PairWindowStat]] = {}
    for s in telemetry.per_pair_window_stats:
        by_sym.setdefault(s.symbol, {})[s.window_idx] = s
    for sym in telemetry.available_symbols:
        row = [f"| `{sym}` |"]
        total_n = 0
        for w in telemetry.windows:
            s = by_sym.get(sym, {}).get(w.idx)
            if s is None:
                row.append(" — |")
            else:
                row.append(f" {s.mean_tqs:.3f} (n={s.n_trades}) |")
                total_n += s.n_trades
        row.append(f" n={total_n} |")
        lines.append("".join(row))
    lines.append("")
    lines.append("## Summary counters")
    lines.append("")
    lines.append(f"- Thoughts: {telemetry.n_thoughts}")
    lines.append(f"- Proposals: {telemetry.n_proposals}")
    lines.append(f"- Trades (all agents): {telemetry.n_trades_total}")
    lines.append(f"- Trades (movable `{telemetry.agent_id}`): {telemetry.n_trades_movable}")
    lines.append("")
    lines.append(
        "See `AMENDMENT_2026-07-20_ac0_methodology_switch.md` for the "
        "regression pass criterion this feeds into."
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ac0_compute(
    *,
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    symbols: tuple[str, ...] = SYMBOLS_EXTENDED,
    movable_agents: tuple[str, ...] = MOVABLE_AGENTS_DEFAULT,
    out_dir: Path | str,
    is_years: int = 4,
    oos_years: int = 1,
    aggregator_arm: str = "phi41",
    include_kunigami_unretired: bool = True,
    skip_missing_pairs: bool = True,
) -> Ac0ComputeReport:
    """Run one walk-forward per movable agent, widening that agent's
    ``.symbols`` to the available subset of ``symbols``.

    Other agents stay at their v1 doctrine defaults. Kunigami joins the
    proposer roster only inside his own run when
    ``include_kunigami_unretired=True``. Symbols missing from the
    production parquet cache are skipped (warning) unless
    ``skip_missing_pairs=False``. Returns the full report structure;
    also writes per-movable JSON + MD and a combined summary JSON
    under ``out_dir``.
    """
    ensure_production_repo_on_path()
    symbols = tuple(symbols)
    movable_agents = tuple(movable_agents)
    for aid in movable_agents:
        if aid not in _ALL_MOVABLE_IDS:
            raise ValueError(
                f"AC.0-v2: movable_agents={movable_agents} contains "
                f"unknown id {aid!r}. Expected subset of "
                f"{sorted(_ALL_MOVABLE_IDS)} (see amendment §2)."
            )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info(
        "AC.0-v2 compute session starting | panel %s -> %s | "
        "symbols=%s | movables=%s | aggregator=%s | "
        "include_kunigami_unretired=%s",
        panel_start.date(), panel_end.date(), list(symbols),
        list(movable_agents), aggregator_arm, include_kunigami_unretired,
    )

    bars_by_symbol, available, skipped = _filter_available_symbols(
        symbols, panel_start, panel_end, skip_missing_pairs,
    )
    windows = _g7_windows(panel_start, panel_end, is_years, oos_years)
    if not windows:
        raise RuntimeError(
            f"AC.0-v2: no walk-forward windows produced for panel "
            f"{panel_start.date()} -> {panel_end.date()} at "
            f"is_years={is_years}, oos_years={oos_years}. Widen the panel."
        )

    report = Ac0ComputeReport(
        panel_start_utc=panel_start.isoformat(),
        panel_end_utc=panel_end.isoformat(),
        requested_symbols=symbols,
        available_symbols=available,
        skipped_symbols=skipped,
        movable_agents=movable_agents,
        aggregator_arm=aggregator_arm,
        include_kunigami_unretired=include_kunigami_unretired,
        is_years=is_years,
        oos_years=oos_years,
        fired_at_utc=datetime.now(timezone.utc).isoformat(),
    )

    for movable_id in movable_agents:
        telemetry = _run_one_movable(
            movable_id=movable_id,
            bars_by_symbol=bars_by_symbol,
            available_symbols=available,
            skipped_symbols=skipped,
            requested_symbols=symbols,
            windows=windows,
            aggregator_arm=aggregator_arm,
            include_kunigami_unretired=include_kunigami_unretired,
        )
        report.per_movable[movable_id] = telemetry

        json_path = out_dir / f"{movable_id}_walkforward.json"
        json_path.write_text(
            json.dumps(telemetry.to_jsonable(), indent=2, default=str),
            encoding="utf-8",
        )
        md_path = out_dir / f"{movable_id}_walkforward.md"
        md_path.write_text(_render_movable_md(telemetry), encoding="utf-8")
        log.info("AC.0-v2 [%s]: wrote %s + %s", movable_id, json_path, md_path)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(report.to_jsonable(), indent=2, default=str),
        encoding="utf-8",
    )
    log.info("AC.0-v2: wrote combined summary %s", summary_path)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "AC.0-v2 fresh-compute harness — per-movable-agent walk-forward "
            "over the extended panel. See "
            "programs/M001_multi_agent_ensemble/experiments/"
            "phase_ac_pitch_assignment/AMENDMENT_2026-07-20_"
            "ac0_methodology_switch.md"
        ),
    )
    parser.add_argument("--panel-start", type=_parse_date,
                        default=G7_PANEL_START.isoformat())
    parser.add_argument("--panel-end", type=_parse_date,
                        default=G7_PANEL_END.isoformat())
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS_EXTENDED),
                        help="Extended panel symbols; missing pairs are "
                             "skipped (default: 7-pair extended panel).")
    parser.add_argument("--movable-agents", nargs="+",
                        default=list(MOVABLE_AGENTS_DEFAULT),
                        help="Which movable agents to fire; subset of "
                             "{chigiri_hyoma, itoshi_rin, kunigami_rensuke}.")
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="Output directory (per-movable JSON + MD land "
                             "here; combined summary.json alongside).")
    parser.add_argument("--is-years", type=int, default=4)
    parser.add_argument("--oos-years", type=int, default=1)
    parser.add_argument("--aggregator-arm",
                        choices=("phi41", "arm3", "arm4"), default="phi41")
    parser.add_argument("--no-kunigami-unretired", action="store_true",
                        help="Force Kunigami to stay retired even inside "
                             "his own run (mostly for reproducing the "
                             "banked-baseline configuration).")
    parser.add_argument("--fail-on-missing-pair", action="store_true",
                        help="Refuse to run when any requested symbol is "
                             "missing from the parquet cache "
                             "(default: skip with warning).")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )

    run_ac0_compute(
        panel_start=args.panel_start,
        panel_end=args.panel_end,
        symbols=tuple(args.symbols),
        movable_agents=tuple(args.movable_agents),
        out_dir=args.out_dir,
        is_years=args.is_years,
        oos_years=args.oos_years,
        aggregator_arm=args.aggregator_arm,
        include_kunigami_unretired=not args.no_kunigami_unretired,
        skip_missing_pairs=not args.fail_on_missing_pair,
    )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
