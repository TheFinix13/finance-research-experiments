"""Replay engine — the deterministic tick loop.

Pure simulator: loads a roster YAML, walks historical bars in tick
order, calls `observe` every tick, calls `intend` at the home_tf close
for each agent, writes Thoughts to the ledger JSONL, collects
Proposals, and runs the aggregator + Sentinel.

Phi2.5 scope is **scaffolding** — the engine successfully drives a
small synthetic bar sequence with stub agents and produces a valid
JSONL ledger + aggregator output. Real bar loading and home_tf
schedule mapping land in Phi3 (G3 data manifest deliverable).

Determinism contract: given the same manifest (`seed`, roster hash,
data slice), the engine emits byte-identical JSONL.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import yaml

from .aggregator import aggregate
from .ledger import FullLedger, ThoughtLedger
from .sentinel import SentinelContext, evaluate
from .striker import BaseStriker
from .types import AgentProposal, MarketState, OrderIntent, Thought


@dataclass
class ReplayManifest:
    """Replay manifest — the only authority on what a run did.

    Mirrors `07-research-standards.md` section 5.2 fields plus the
    M001-specific roster/ledger fields. Written next to the run
    output as `manifest.json`.
    """

    run_id: str
    seed: int
    roster_path: str
    ledger_mode: str
    data_window: tuple[datetime, datetime]
    git_sha: str = ""
    data_sha: str = ""

    def to_jsonable(self) -> dict:
        return {
            "run_id": self.run_id,
            "seed": int(self.seed),
            "roster_path": self.roster_path,
            "ledger_mode": self.ledger_mode,
            "data_window": [
                self.data_window[0].isoformat(),
                self.data_window[1].isoformat(),
            ],
            "git_sha": self.git_sha,
            "data_sha": self.data_sha,
        }


@dataclass
class ReplayOutput:
    """Per-run output collection (in-memory mirror of the JSONL bundle)."""

    thoughts: list[Thought] = field(default_factory=list)
    proposals: list[AgentProposal] = field(default_factory=list)
    intents: list[OrderIntent] = field(default_factory=list)
    sentinel_log: list[dict] = field(default_factory=list)


def load_roster_yaml(path: str | Path) -> list[dict]:
    """Read a roster YAML and return the `agents` list.

    The YAML schema is documented in `sim/roster/mvp_phi4.yaml`. The
    engine here does NOT instantiate concrete agent classes — Phi2.5
    callers pass in already-instantiated `BaseStriker` instances.
    """
    with Path(path).open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return list(data.get("agents", []))


def _is_home_tf_close(market: MarketState, agent: BaseStriker) -> bool:
    """Phi2.5 simplification: every tick whose timeframe matches the
    agent's home_tf counts as a close. Phi3 lands the proper
    home_tf-aware scheduler that maps M1 ticks to H1/H4/D1 close
    events.
    """
    return market.timeframe == agent.home_tf


def run_replay(
    bars: Iterable[MarketState],
    agents: list[BaseStriker],
    ledger: ThoughtLedger | None = None,
    *,
    sentinel_context_factory=None,
) -> ReplayOutput:
    """Walk `bars` once, call `observe`/`intend`, return the run output.

    Phi4 two-phase tick order (`doctrine 06 sec 3.8 + 09 sec 1.2`):

      Phase 1: every eligible striker `observe()` at tick T -- all
               Thoughts at tick T appended to the ledger (the writes
               are visible to readers ONLY on tick >= T+1 because the
               ledger's `_apply_guards` filters `tick_id >= current_tick`).
      Phase 2: every eligible striker `intend()` -- reads only
               `tick_id < T` Thoughts. Same-tick reads forbidden by
               doctrine; the ledger guard enforces this whether or
               not we split the phases. The explicit split is for
               READABILITY and ordering symmetry across agents.

    Agents are visited in lexicographic `agent_id` order on every
    tick so the run is byte-deterministic when the roster's instance
    list is permuted.
    """
    if ledger is None:
        ledger = FullLedger()
    out = ReplayOutput()
    bars = list(bars)

    for bar in bars:
        eligible = sorted(
            [a for a in agents if bar.symbol in a.symbols],
            key=lambda a: a.agent_id,
        )

        # Phase 1 -- everyone observes; writes land in the ledger but
        # are not visible to peers until next tick (guard rule).
        my_thought: dict[str, Thought] = {}
        for agent in eligible:
            t = agent.observe(bar, ledger)
            ledger.append(t)
            out.thoughts.append(t)
            my_thought[agent.agent_id] = t

        # Phase 2 -- everyone intends; reads only tick_id < T.
        proposals_this_tick: list[AgentProposal] = []
        for agent in eligible:
            if not _is_home_tf_close(bar, agent):
                continue
            t = my_thought[agent.agent_id]
            p = agent.intend(bar, t)
            if p is not None:
                proposals_this_tick.append(p)
                out.proposals.append(p)
        if proposals_this_tick:
            intents = aggregate(
                proposals_this_tick,
                tick_id=bar.tick_id,
                timestamp=bar.as_of,
            )
            if sentinel_context_factory is not None:
                ctx: SentinelContext = sentinel_context_factory(bar, out)
                kept = []
                for intent in intents:
                    matching = next(
                        p for p in proposals_this_tick if p.symbol == intent.symbol
                    )
                    decision = evaluate(matching, intent, ctx)
                    out.sentinel_log.append(
                        {
                            "tick_id": int(bar.tick_id),
                            "timestamp": bar.as_of.isoformat(),
                            "intent_id": intent.intent_id,
                            "allowed": bool(decision.allowed),
                            "rule": decision.rule,
                            "reason": decision.reason,
                            "payload": decision.payload,
                        }
                    )
                    if decision.allowed:
                        kept.append(intent)
                out.intents.extend(kept)
            else:
                out.intents.extend(intents)
    return out


def write_run_artefacts(
    output: ReplayOutput,
    *,
    run_dir: str | Path,
    manifest: ReplayManifest,
) -> None:
    """Persist the run output to the Phi2.5 JSONL+parquet layout."""
    rd = Path(run_dir)
    rd.mkdir(parents=True, exist_ok=True)
    with (rd / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest.to_jsonable(), fh, indent=2, sort_keys=True)
    with (rd / "thoughts.jsonl").open("w", encoding="utf-8") as fh:
        for t in output.thoughts:
            fh.write(t.to_json() + "\n")
    with (rd / "proposals.jsonl").open("w", encoding="utf-8") as fh:
        for p in output.proposals:
            fh.write(json.dumps(p.to_jsonable(), sort_keys=True) + "\n")
    with (rd / "intents.jsonl").open("w", encoding="utf-8") as fh:
        for i in output.intents:
            fh.write(json.dumps(i.to_jsonable(), sort_keys=True) + "\n")
    with (rd / "sentinel_log.jsonl").open("w", encoding="utf-8") as fh:
        for row in output.sentinel_log:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
