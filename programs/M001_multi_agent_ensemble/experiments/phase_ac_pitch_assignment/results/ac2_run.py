"""AC.2 arm runner — fresh walk-forward per squad-composition arm.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        PROTOCOL.md §5 AC.2 (four arms A1/A2/B1-hard/B1-soft)
        AMENDMENT_2026-07-20_ac0_methodology_switch.md

What this does
--------------

Runs one full G7-style walk-forward for a given squad-composition arm,
with per-agent ``.symbols`` overrides applied at instantiation. The
walk-forward drives ``_drive_squad_replay`` end-to-end (F21 workspace
threading, Sentinel enforcement, phi41 aggregator) over the standard
G7 4-yr-IS / 1-yr-OOS × 7-window panel on the extended 7-pair panel.

Post-replay, per-agent per-window mean-TQS and trade counts are
computed and dumped as an arm-specific JSON so the AC.2 evaluator
can compute AC2.1 (anchor lock), AC2.2 (squad-TQS lift), AC2.3
(Nagi volume floor).

Scope note
----------

Resumer-session write-scope forbids code changes outside `results/**`.
This script duplicates the essential per-arm driver pattern from
``sim/scoring/run_g7_v1_checkpoint_gate.run_g7_walk_forward`` so per-
agent widening (A2: Rin widened to (EURUSD, USDCHF)) can be expressed
without modifying the sealed harness. Every reused primitive
(``_drive_squad_replay``, ``_load_production_bars``, ``_g7_windows``)
is imported from the sealed modules — no strategy or aggregator
change.

**B1-hard / B1-soft not implemented in this script.** Those arms
require (a) roster subsets that break `_drive_squad_replay`'s
`isagi/barou/kunigami` special-role kwargs (e.g. Manshine City
excludes Isagi and Barou from proposers) and (b) for B1-soft, a
pitch-preferred routing modification to the aggregator that is out
of the resumer session's write-scope. STOP_NOTICE recorded in
`ac2_verdicts.md` §6.

CLI
---

::

    ../multi-pair-trading-agent/.venv/bin/python \\
        programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/results/ac2_run.py \\
        --arm-id A1 \\
        --out-dir programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/results/ac2/ \\
        --symbols EURUSD GBPUSD USDCAD AUDUSD NZDUSD USDJPY USDCHF
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

# Ensure the trading-agent production repo is importable (bars).
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
    G7_AGENT_ORDER,
    G7_PANEL_END,
    G7_PANEL_START,
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
# Pre-registered AC.2 arm specifications (locked per §5 + AC.1 §6 output)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    description: str
    # Per-agent ``.symbols`` overrides. Absent agents use their v1 defaults.
    agent_symbols_overrides: dict[str, tuple[str, ...]]
    # Kunigami participates as proposer? Per pre-reg §5 both A1 and A2
    # keep him retired (v1 default; his AC.1 wiring failed, so no
    # widening was authorised in AC.1).
    include_kunigami: bool


ARM_A1 = ArmSpec(
    arm_id="A1",
    description=(
        "Baseline (control): current wiring on the extended 7-pair "
        "panel. Anchors at canon home (Isagi, Bachira, Barou), "
        "movables at v1 doctrine defaults (Rin EURUSD only, Chigiri "
        "EURUSD+GBPUSD, Kunigami retired). Reproduces the current "
        "3/7 verdict on the extended panel for shared reference."
    ),
    agent_symbols_overrides={},
    include_kunigami=False,
)

ARM_A2 = ArmSpec(
    arm_id="A2",
    description=(
        "Single-squad widened: anchors unchanged; Rin's .symbols "
        "widened to (EURUSD, USDCHF) per AC.1.rin-a pass (BH-adjusted "
        "q=0.10). Chigiri and Kunigami unchanged (no AC.1 widening "
        "authorised for them). One SquadRoster, one workspace, one "
        "thought stream. Kunigami stays retired (matches v1 default; "
        "AC.1 kun sub-arms un-testable due to wiring bug)."
    ),
    agent_symbols_overrides={
        "itoshi_rin": ("EURUSD", "USDCHF"),
    },
    include_kunigami=False,
)

ARMS_IMPLEMENTED: dict[str, ArmSpec] = {"A1": ARM_A1, "A2": ARM_A2}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PerAgentWindowSlice:
    agent_id: str
    window_idx: int
    n_trades: int
    mean_tqs: float
    per_pair: list[dict]        # [{symbol, mean_tqs, n_trades}, ...]


@dataclass
class ArmRunReport:
    arm_id: str
    description: str
    fired_at_utc: str
    panel_start_utc: str
    panel_end_utc: str
    symbols: tuple[str, ...]
    aggregator_arm: str
    include_kunigami: bool
    agent_symbols_overrides: dict[str, tuple[str, ...]]
    roster_actual: list[dict]                      # [{agent_id, playstyle, symbols}]
    n_windows: int
    windows_meta: list[dict]
    per_agent_window: list[PerAgentWindowSlice]
    workspace_publish_counts: dict[str, int]
    workspace_read_counts: dict[str, int]
    n_thoughts: int
    n_proposals: int
    n_trades: int

    def to_jsonable(self) -> dict:
        return {
            "arm_id": self.arm_id,
            "description": self.description,
            "fired_at_utc": self.fired_at_utc,
            "panel_start_utc": self.panel_start_utc,
            "panel_end_utc": self.panel_end_utc,
            "symbols": list(self.symbols),
            "aggregator_arm": self.aggregator_arm,
            "include_kunigami": bool(self.include_kunigami),
            "agent_symbols_overrides": {
                aid: list(syms)
                for aid, syms in self.agent_symbols_overrides.items()
            },
            "roster_actual": self.roster_actual,
            "n_windows": int(self.n_windows),
            "windows_meta": self.windows_meta,
            "per_agent_window": [
                {
                    "agent_id": p.agent_id,
                    "window_idx": int(p.window_idx),
                    "n_trades": int(p.n_trades),
                    "mean_tqs": (
                        None if p.n_trades == 0 else float(p.mean_tqs)
                    ),
                    "per_pair": p.per_pair,
                }
                for p in self.per_agent_window
            ],
            "workspace_publish_counts": {
                aid: int(v) for aid, v in self.workspace_publish_counts.items()
            },
            "workspace_read_counts": {
                aid: int(v) for aid, v in self.workspace_read_counts.items()
            },
            "n_thoughts": int(self.n_thoughts),
            "n_proposals": int(self.n_proposals),
            "n_trades": int(self.n_trades),
        }


# ---------------------------------------------------------------------------
# Roster construction with per-agent overrides
# ---------------------------------------------------------------------------

def _instantiate_agent(
    agent_id: str, overrides: dict[str, tuple[str, ...]],
) -> Any:
    """Fresh agent instance honoring per-agent .symbols override.

    Every A*V1 constructor accepts a ``symbols=`` kwarg (see agent
    files). Absent from overrides → default constructor path.
    """
    override = overrides.get(agent_id)
    kwargs = {"symbols": list(override)} if override is not None else {}
    if agent_id == "isagi_yoichi":
        return A1IsagiV1(**kwargs)
    if agent_id == "bachira_meguru":
        return A2BachiraV1(**kwargs)
    if agent_id == "itoshi_rin":
        return A3RinV1(**kwargs)
    if agent_id == "chigiri_hyoma":
        return A4ChigiriV1(**kwargs)
    if agent_id == "reo_mikage":
        return A5ReoV1()
    if agent_id == "nagi_seishiro":
        return A6NagiV1()
    if agent_id == "barou_shoei":
        return A7BarouV1(**kwargs)
    if agent_id == "kunigami_rensuke":
        return A10KunigamiV1(**kwargs)
    raise ValueError(f"unknown agent_id {agent_id!r}")


def _build_arm_roster(
    spec: ArmSpec,
) -> tuple[list[Any], A1IsagiV1, A7BarouV1, A10KunigamiV1, list[dict]]:
    """Instantiate ALL 8 named agents; return proposer list + special-role
    handles + audit roster payload.

    For A1/A2, all named agents exist as instances (Kunigami retired →
    kept out of the proposer list but instance still needed for R5
    side-channel wiring).
    """
    isagi = _instantiate_agent("isagi_yoichi", spec.agent_symbols_overrides)
    bachira = _instantiate_agent("bachira_meguru", spec.agent_symbols_overrides)
    rin = _instantiate_agent("itoshi_rin", spec.agent_symbols_overrides)
    chigiri = _instantiate_agent("chigiri_hyoma", spec.agent_symbols_overrides)
    reo = _instantiate_agent("reo_mikage", spec.agent_symbols_overrides)
    nagi = _instantiate_agent("nagi_seishiro", spec.agent_symbols_overrides)
    barou = _instantiate_agent("barou_shoei", spec.agent_symbols_overrides)
    kunigami = _instantiate_agent("kunigami_rensuke", spec.agent_symbols_overrides)

    proposers: list[Any] = [isagi, bachira, rin, chigiri, reo, nagi, barou]
    if spec.include_kunigami:
        proposers.append(kunigami)

    proposer_ids = {a.agent_id for a in proposers}
    all_named = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]
    roster_payload = [
        {
            "agent_id": a.agent_id,
            "playstyle": str(getattr(a, "playstyle", "unknown")),
            "symbols": list(a.symbols),
            "is_proposer": a.agent_id in proposer_ids,
        }
        for a in all_named
    ]
    return proposers, isagi, barou, kunigami, roster_payload


def _prepare_agents(
    proposers: list[Any], bars_by_symbol: dict[str, list],
) -> None:
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in proposers:
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)


# ---------------------------------------------------------------------------
# One-arm walk-forward driver
# ---------------------------------------------------------------------------

def run_arm(
    *,
    spec: ArmSpec,
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    symbols: tuple[str, ...],
    out_dir: Path,
    is_years: int = 4,
    oos_years: int = 1,
    aggregator_arm: str = "phi41",
) -> ArmRunReport:
    ensure_production_repo_on_path()
    symbols = tuple(symbols)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info(
        "AC.2 [%s]: firing arm | panel %s -> %s | symbols=%s | "
        "aggregator=%s | overrides=%s | include_kunigami=%s",
        spec.arm_id, panel_start.date(), panel_end.date(), list(symbols),
        aggregator_arm,
        {aid: list(syms) for aid, syms in spec.agent_symbols_overrides.items()},
        spec.include_kunigami,
    )

    # Load bars per symbol (missing pairs raise; A1/A2 assume full 7-pair panel).
    bars_by_symbol: dict[str, list] = {}
    for sym in symbols:
        bars = _load_production_bars(sym, panel_start, panel_end)
        if not bars:
            raise RuntimeError(
                f"AC.2 [{spec.arm_id}]: 0 bars loaded for {sym} — cannot "
                "run the arm; the extended panel must be fully cached."
            )
        bars_by_symbol[sym] = bars
        log.info("Loaded %d %s bars", len(bars), sym)

    proposers, isagi, barou, kunigami, roster_actual = _build_arm_roster(spec)
    _prepare_agents(proposers, bars_by_symbol)

    windows = _g7_windows(panel_start, panel_end, is_years, oos_years)
    log.info(
        "AC.2 [%s]: %d walk-forward windows; proposers=%s",
        spec.arm_id, len(windows), [a.agent_id for a in proposers],
    )
    for w in windows:
        log.info(
            "  window %d: IS %s -> %s | OOS %s -> %s",
            w.idx, w.is_start.date(), w.is_end.date(),
            w.oos_start.date(), w.oos_end.date(),
        )

    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=proposers, isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol, ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,
        use_shadow_ledger=False,       # AC.2 doesn't need shadow.
        aggregator_arm=aggregator_arm,
    )
    log.info(
        "AC.2 [%s]: replay complete | %d thoughts | %d proposals | %d trades",
        spec.arm_id, len(out.thoughts), len(out.proposals_all), len(out.trades),
    )

    # Slice per-agent per-window with per-pair breakdown.
    per_agent_window: list[PerAgentWindowSlice] = []
    for w in windows:
        oos_trades = [
            t for t in out.trades
            if w.oos_start <= t.entry_time < w.oos_end
        ]
        for aid in G7_AGENT_ORDER:
            ag_trades = [t for t in oos_trades if t.agent_id == aid]
            per_pair: dict[str, list[float]] = {}
            for t in ag_trades:
                sym = getattr(t, "symbol", "?")
                per_pair.setdefault(sym, []).append(
                    float((t.tqs_components or {}).get("tqs", 0.0))
                )
            per_pair_rows = [
                {
                    "symbol": sym,
                    "n_trades": len(vals),
                    "mean_tqs": (
                        float(statistics.mean(vals)) if vals else 0.0
                    ),
                }
                for sym, vals in sorted(per_pair.items())
            ]
            all_tqs = [
                float((t.tqs_components or {}).get("tqs", 0.0))
                for t in ag_trades
            ]
            per_agent_window.append(PerAgentWindowSlice(
                agent_id=aid, window_idx=int(w.idx),
                n_trades=len(ag_trades),
                mean_tqs=(
                    float(statistics.mean(all_tqs)) if all_tqs else 0.0
                ),
                per_pair=per_pair_rows,
            ))

    report = ArmRunReport(
        arm_id=spec.arm_id,
        description=spec.description,
        fired_at_utc=datetime.now(timezone.utc).isoformat(),
        panel_start_utc=panel_start.isoformat(),
        panel_end_utc=panel_end.isoformat(),
        symbols=symbols,
        aggregator_arm=aggregator_arm,
        include_kunigami=spec.include_kunigami,
        agent_symbols_overrides={
            aid: tuple(syms)
            for aid, syms in spec.agent_symbols_overrides.items()
        },
        roster_actual=roster_actual,
        n_windows=len(windows),
        windows_meta=[
            {
                "idx": int(w.idx),
                "is_start": w.is_start.isoformat(),
                "is_end": w.is_end.isoformat(),
                "oos_start": w.oos_start.isoformat(),
                "oos_end": w.oos_end.isoformat(),
            }
            for w in windows
        ],
        per_agent_window=per_agent_window,
        workspace_publish_counts=dict(out.workspace_publish_counts),
        workspace_read_counts=dict(out.workspace_read_counts),
        n_thoughts=len(out.thoughts),
        n_proposals=len(out.proposals_all),
        n_trades=len(out.trades),
    )

    json_path = out_dir / f"ac2_arm_{spec.arm_id}.json"
    json_path.write_text(
        json.dumps(report.to_jsonable(), indent=2, default=str),
        encoding="utf-8",
    )
    log.info("AC.2 [%s]: wrote %s", spec.arm_id, json_path)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AC.2 arm runner (A1 baseline / A2 single-squad widened).",
    )
    parser.add_argument("--arm-id", choices=list(ARMS_IMPLEMENTED.keys()),
                        required=True)
    parser.add_argument("--panel-start", type=_parse_date,
                        default=G7_PANEL_START.isoformat())
    parser.add_argument("--panel-end", type=_parse_date,
                        default=G7_PANEL_END.isoformat())
    parser.add_argument(
        "--symbols", nargs="+",
        default=["EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD",
                 "USDJPY", "USDCHF"],
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--is-years", type=int, default=4)
    parser.add_argument("--oos-years", type=int, default=1)
    parser.add_argument("--aggregator-arm",
                        choices=("phi41", "arm3", "arm4"), default="phi41")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    spec = ARMS_IMPLEMENTED[args.arm_id]
    report = run_arm(
        spec=spec,
        panel_start=args.panel_start,
        panel_end=args.panel_end,
        symbols=tuple(args.symbols),
        out_dir=args.out_dir,
        is_years=args.is_years,
        oos_years=args.oos_years,
        aggregator_arm=args.aggregator_arm,
    )
    print(
        f"[AC.2 {report.arm_id}] === replay complete: {report.n_trades} "
        f"trades, {report.n_windows} windows, "
        f"{len(report.per_agent_window)} agent-window slices ==="
    )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
