"""F21 -- Reasoning Workspace (per-tick shared blackboard).

Doctrine 06 v0.5 section 4.1a. First-class v1 primitive that closes the
"chemical reaction" loop from section 3.3 -- reactions no longer require
the Aggregator to detect confluence AFTER proposals ship; agents can
anticipate confluence during their own decisioning by reading peers'
prior-tick Thoughts from a shared workspace.

## What it is

A per-tick immutable snapshot of the Thought Ledger, exposing a
uniform read surface to every agent's `intend()` phase. The workspace
is *published to* by agents during `observe()`, and *read by* agents
during `intend()`. Same-tick reads across agents are forbidden by the
doctrine section 3.8 references guard: an agent at tick T can only
read Thoughts published at ticks < T. The workspace enforces that
guard at read time.

## Why not just use `ThoughtLedger`?

The ledger IS the persistent journal (JSONL append-only, one file per
agent per day). The workspace is the *live* per-tick view used during
decisioning. Two reasons for the split:

1. **Snapshot semantics.** The workspace snapshots the ledger at a
   specific `as_of` time and returns the same view to every reader
   regardless of publish order in the current tick. The ledger's
   `read()` method returns whatever has been appended so far -- which
   would leak same-tick publish ordering into decisions.
2. **Read-only surface.** Agents cannot mutate other agents' Thoughts
   through the workspace. The workspace is a `frozen` (immutable)
   projection of what has been *published as of the tick barrier*.

## Not a replacement for section 3.9 tier system

Tier-3 agents (per doctrine section 3.9) still receive a redacted
workspace where `agent_id != self` is filtered out. The workspace
respects the same tier semantics as the `ThoughtLedger`; it does NOT
grant blanket access.

## Semantics summary

- `publish(thought)` is idempotent on `thought_id` and appends to the
  workspace's internal buffer.
- `snapshot(as_of, current_tick)` returns an immutable view of all
  Thoughts published with `timestamp <= as_of` AND `tick_id <
  current_tick`. Same-tick Thoughts are excluded.
- `read_for(agent_id, tier, symbol=None, tag=None)` on a snapshot
  applies the tier filter and optional symbol / tag filters, returning
  a `tuple[Thought, ...]` (immutable) sorted by `(tick_id, timestamp)`.

Reference: doctrine section 4.1a (F21 primitive definition), section
3.8 (Thought Ledger + look-ahead guards), section 3.9 (tier system).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from .types import Symbol, Thought

# Tier semantics reused from doctrine section 3.9. Kept as string literals
# rather than importing an enum -- keeps the workspace primitive free of
# adapter dependencies.
Tier = Literal[1, 2, 3]


@dataclass
class ReasoningWorkspace:
    """Per-tick shared blackboard.

    Stateful during a tick -- agents publish into it as they run
    `observe()`. Snapshot at the tick barrier is what every agent's
    `intend()` reads. New workspace instantiated per tick group by the
    harness driver.

    The class is NOT frozen because it is populated incrementally; the
    *snapshots* it produces via `snapshot()` are immutable tuples.
    """

    thoughts: list[Thought] = field(default_factory=list)
    _thought_ids: set[str] = field(default_factory=set, init=False, repr=False)

    def publish(self, thought: Thought) -> bool:
        """Append `thought` to the workspace. Idempotent on `thought_id`.

        Returns True if the Thought was newly appended, False if it was
        a duplicate id (silently dropped -- supports replay).
        """
        if thought.thought_id in self._thought_ids:
            return False
        self._thought_ids.add(thought.thought_id)
        self.thoughts.append(thought)
        return True

    def snapshot(
        self,
        *,
        as_of: datetime,
        current_tick: int,
    ) -> "WorkspaceSnapshot":
        """Immutable projection of all backwards-visible Thoughts.

        Applies the doctrine section 3.8 look-ahead guards:

        - `t.timestamp <= as_of` (no future Thoughts)
        - `t.tick_id < current_tick` (no same-tick reads)
        - `t.decision_horizon <= as_of` (writer's own look-ahead guard)

        The returned snapshot is a frozen dataclass; mutating it is
        impossible. The caller applies tier + symbol + tag filters via
        `snapshot.read_for(...)`.
        """
        visible = tuple(
            t for t in self.thoughts
            if t.timestamp <= as_of
            and t.tick_id < current_tick
            and t.decision_horizon <= as_of
        )
        return WorkspaceSnapshot(
            thoughts=visible,
            as_of=as_of,
            current_tick=current_tick,
        )


@dataclass(frozen=True)
class WorkspaceSnapshot:
    """Immutable per-tick view returned by `ReasoningWorkspace.snapshot()`.

    Agents receive this in their `intend()` phase and call
    `read_for()` to apply the tier filter appropriate to their
    assigned tier (doctrine section 3.9).
    """

    thoughts: tuple[Thought, ...]
    as_of: datetime
    current_tick: int

    def read_for(
        self,
        *,
        agent_id: str,
        tier: Tier = 2,
        symbol: Symbol | None = None,
        tag: str | None = None,
    ) -> tuple[Thought, ...]:
        """Return Thoughts visible to `agent_id` under `tier`.

        Tier-1 and Tier-2 see the full backwards-only slice; Tier-3
        sees only their own past Thoughts (agent_id match). Optional
        `symbol` filter matches `t.symbol == symbol`; optional `tag`
        filter matches `tag in t.tags`.

        Result is a tuple sorted by (tick_id, timestamp) ascending --
        oldest first, so agents can walk the chronology.
        """
        if tier == 3:
            filtered = tuple(t for t in self.thoughts if t.agent_id == agent_id)
        else:
            filtered = self.thoughts

        if symbol is not None:
            filtered = tuple(t for t in filtered if t.symbol == symbol)
        if tag is not None:
            filtered = tuple(t for t in filtered if tag in t.tags)

        return tuple(sorted(filtered, key=lambda t: (t.tick_id, t.timestamp)))

    def peer_thoughts(
        self,
        *,
        agent_id: str,
        symbol: Symbol | None = None,
        tag: str | None = None,
    ) -> tuple[Thought, ...]:
        """Read-my-peers convenience -- Tier-2 view minus own Thoughts.

        Used by F19/F20 default implementations that want to see what
        OTHER agents said (for confluence-lift, peer-silence gates,
        etc.) without also seeing their own prior Thoughts.
        """
        peers = tuple(t for t in self.thoughts if t.agent_id != agent_id)
        if symbol is not None:
            peers = tuple(t for t in peers if t.symbol == symbol)
        if tag is not None:
            peers = tuple(t for t in peers if tag in t.tags)
        return tuple(sorted(peers, key=lambda t: (t.tick_id, t.timestamp)))

    def latest_by_agent(
        self,
        *,
        symbol: Symbol | None = None,
    ) -> dict[str, Thought]:
        """For each agent, return their most recent Thought in the snapshot.

        Convenience for F19/F20 defaults that want to check "does peer
        X have an active claim on symbol S?" without walking the full
        chronology. Excludes flat direction Thoughts (`coordinate is
        None`) unless explicitly requested by the caller (not
        supported here -- Thoughts without coordinates are commentary
        only).
        """
        latest: dict[str, Thought] = {}
        for t in self.thoughts:
            if symbol is not None and t.symbol != symbol:
                continue
            existing = latest.get(t.agent_id)
            if existing is None or t.tick_id > existing.tick_id:
                latest[t.agent_id] = t
            elif t.tick_id == existing.tick_id and t.timestamp > existing.timestamp:
                latest[t.agent_id] = t
        return latest


__all__ = ["ReasoningWorkspace", "WorkspaceSnapshot", "Tier"]
