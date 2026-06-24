"""Thought Ledger — append-only journal of every agent's reasoning.

Four implementations of the `ThoughtLedger` Protocol:

* `FullLedger`           — Tier-2 read access (doctrine section 3.9).
* `RedactedLedger`       — Tier-3 read access; filters by `agent_id`.
* `FrozenLedger`         — Snapshot as-of `t-1` only (look-ahead test).
* `SyntheticLedger`      — Injected counterfactual Thoughts (stress test).

All concrete implementations share the same look-ahead guard
(`decision_horizon`) and backwards-only references rule (doctrine
section 3.8). Storage is JSONL append-only, one file per agent per UTC
day. Phi2.5 data plane per research-standards section 8.

Switching adapters is a config flip on the manifest, NOT a redeploy —
this is the operational definition of the "Injectable Ledger" pillar
in 09 section 1.3.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Protocol

from .types import Thought


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ThoughtLedger(Protocol):
    """The read/write surface that every agent depends on.

    `append` is write-only and idempotent on `thought_id` (a second
    append with the same id is silently dropped — supports replay
    without duplicating rows).

    `read` always honours the doctrine section 3.8 guards:
    * Thoughts whose `decision_horizon > as_of` are filtered out.
    * Thoughts whose `tick_id >= current_tick` are filtered out
      (backwards-only references).
    * `ttl_ticks` bounds the read window from below.

    Concrete implementations are free to add their own visibility
    rules on top of these (e.g. `RedactedLedger` further restricts to
    `agent_id == owner`).
    """

    mode: str

    def append(self, t: Thought) -> None: ...

    def read(
        self,
        *,
        as_of: datetime,
        current_tick: int,
        symbol: str | None = None,
    ) -> list[Thought]: ...


# ---------------------------------------------------------------------------
# JSONL backend (Phi2.5 data plane)
# ---------------------------------------------------------------------------

def _utc_date_key(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).date().isoformat()


def _thought_from_dict(d: dict) -> Thought:
    from .types import Coordinate

    coord = None
    if d.get("coordinate") is not None:
        c = d["coordinate"]
        coord = Coordinate(
            agent_id=c["agent_id"],
            symbol=c["symbol"],
            price_lo=float(c["price_lo"]),
            price_hi=float(c["price_hi"]),
            time_start=datetime.fromisoformat(c["time_start"]),
            time_end=datetime.fromisoformat(c["time_end"]),
            vol_band=(float(c["vol_band"][0]), float(c["vol_band"][1])),
            regime_predicate=c["regime_predicate"],
            expected_strength=float(c["expected_strength"]),
            direction_bias=c["direction_bias"],
            rationale=dict(c.get("rationale", {})),
        )
    return Thought(
        schema_version=int(d["schema_version"]),
        agent_id=d["agent_id"],
        tick_id=int(d["tick_id"]),
        timestamp=datetime.fromisoformat(d["timestamp"]),
        symbol=d["symbol"],
        narrative=d["narrative"],
        tags=list(d.get("tags", [])),
        confidence_in_thought=float(d["confidence_in_thought"]),
        expected_action=d.get("expected_action"),
        coordinate=coord,
        decision_horizon=datetime.fromisoformat(d["decision_horizon"]),
        ttl_ticks=int(d["ttl_ticks"]),
        references=list(d.get("references", [])),
        thought_id=str(d.get("thought_id") or ""),
    )


def _apply_guards(
    rows: Iterable[Thought],
    *,
    as_of: datetime,
    current_tick: int,
    symbol: str | None,
) -> list[Thought]:
    """Universal read filter: decision_horizon, backwards-only, ttl, symbol."""
    out: list[Thought] = []
    for t in rows:
        if t.tick_id >= current_tick:
            # Backwards-only references (doctrine section 3.8): can't read same/future tick.
            continue
        if t.decision_horizon > as_of:
            # Look-ahead guard: writer says "this thought needs bars up to D";
            # if D is in the future from reader's clock, drop it.
            continue
        if (current_tick - t.tick_id) > t.ttl_ticks > 0:
            # Stale.
            continue
        if symbol is not None and t.symbol != symbol:
            continue
        out.append(t)
    return out


@dataclass
class _JsonlBackend:
    """Append-only JSONL backend keyed by (agent_id, UTC date).

    Reads scan only the files that overlap the requested window.

    Performance notes (Φ4.1 hardening, doctrine sec 3.9 is unchanged):
    Dedup uses a `set` keyed by `thought_id`, and the in-memory mirror
    maintains a per-symbol bucket so that a `read(..., symbol=X)` call
    only scans thoughts on `X` rather than the entire ledger. Both are
    pure performance optimisations -- guard semantics in `_apply_guards`
    are preserved verbatim, and the disk-side JSONL files are byte-
    identical to the pre-optimisation backend.

    The Φ4 squad gate ran with the legacy O(N) append/read fine (12.5k
    bars × 4 agents -> ~50k Thoughts). The Φ4.1 expanded squad runs
    53k bars × ~5 active agents -> ~265k Thoughts; with the old O(N²)
    aggregate cost the harness did not complete inside the user's
    interactive budget. Index keeps the run linear in bar count.
    """

    root: Path
    _in_memory: list[Thought]
    # Indexes (rebuilt incrementally on each append). Keep the list as
    # the source of truth so iteration order across all thoughts is
    # deterministic (insertion order) -- callers that rely on that
    # ordering (e.g. F17 audit replays) see no change.
    _seen_ids: set[str] = field(default_factory=set)
    _by_symbol: dict[str, list[Thought]] = field(default_factory=dict)

    def append(self, t: Thought) -> None:
        # Idempotency: O(1) lookup instead of O(N) scan.
        if t.thought_id in self._seen_ids:
            return
        self._seen_ids.add(t.thought_id)
        self._in_memory.append(t)
        self._by_symbol.setdefault(t.symbol, []).append(t)
        if self.root is None:
            return
        day = _utc_date_key(t.timestamp)
        path = self.root / t.agent_id / f"{day}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(t.to_json() + "\n")

    def iter_all(self) -> Iterator[Thought]:
        # In-memory first (this run); then anything else on disk
        # for replay continuations.
        seen = set()
        for t in self._in_memory:
            seen.add(t.thought_id)
            yield t
        if self.root is None or not self.root.exists():
            return
        for day_file in sorted(self.root.glob("*/*.jsonl")):
            with day_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    t = _thought_from_dict(d)
                    if t.thought_id in seen:
                        continue
                    seen.add(t.thought_id)
                    yield t

    def iter_by_symbol(self, symbol: str) -> Iterator[Thought]:
        """Iterate ONLY the in-memory thoughts matching `symbol`.

        Used by `FullLedger.read` when the caller passes a `symbol`
        filter. The on-disk side is intentionally skipped here: the
        in-memory mirror is authoritative within a single run (replay
        continuations across runs use `iter_all`).
        """
        bucket = self._by_symbol.get(symbol)
        if bucket is None:
            return iter(())
        return iter(bucket)


# ---------------------------------------------------------------------------
# Concrete implementations
# ---------------------------------------------------------------------------

class FullLedger:
    """Tier-2 read access — full ledger subject to section 3.8 guards.

    Used by Tier-2 agents (informed) and by the Aggregator + harness
    (Tier-1, always read). The look-ahead guard still applies.
    """

    mode = "full"

    def __init__(self, root: str | os.PathLike | None = None) -> None:
        self._backend = _JsonlBackend(
            root=Path(root) if root else None,
            _in_memory=[],
        )

    def append(self, t: Thought) -> None:
        self._backend.append(t)

    def read(
        self,
        *,
        as_of: datetime,
        current_tick: int,
        symbol: str | None = None,
    ) -> list[Thought]:
        # Fast path: per-symbol bucket when a `symbol` filter is given.
        # The disk-side replay-continuation source still scans iter_all
        # if no symbol is specified (preserves existing semantics).
        if symbol is not None and (
            self._backend.root is None or not self._backend.root.exists()
        ):
            return _apply_guards(
                self._backend.iter_by_symbol(symbol),
                as_of=as_of,
                current_tick=current_tick,
                symbol=symbol,
            )
        return _apply_guards(
            self._backend.iter_all(),
            as_of=as_of,
            current_tick=current_tick,
            symbol=symbol,
        )


class RedactedLedger:
    """Tier-3 read access — own agent only.

    Wraps a `FullLedger` (or any other source) and filters reads to a
    single `agent_id`. Writes are unrestricted: an agent always sees
    its own writes on the next tick. Doctrine section 3.9.
    """

    mode = "redacted"

    def __init__(self, agent_id: str, source: ThoughtLedger | None = None) -> None:
        self.agent_id = agent_id
        self._source = source or FullLedger()

    def append(self, t: Thought) -> None:
        # Pass through to underlying source.
        self._source.append(t)

    def read(
        self,
        *,
        as_of: datetime,
        current_tick: int,
        symbol: str | None = None,
    ) -> list[Thought]:
        rows = self._source.read(
            as_of=as_of, current_tick=current_tick, symbol=symbol
        )
        return [t for t in rows if t.agent_id == self.agent_id]


class FrozenLedger:
    """Snapshot ledger — reads are pinned to a JSONL snapshot path.

    Used for look-ahead regression tests (engine-side state cannot leak
    in) and for the isolated arm of F17 (DeltaInfo). Writes are accepted
    but never visible on subsequent reads — the snapshot is immutable.
    """

    mode = "frozen"

    def __init__(self, snapshot_path: str | os.PathLike) -> None:
        self.snapshot_path = Path(snapshot_path)
        self._rows: list[Thought] = []
        if self.snapshot_path.exists():
            if self.snapshot_path.is_file():
                files = [self.snapshot_path]
            else:
                files = sorted(self.snapshot_path.rglob("*.jsonl"))
            for f in files:
                with f.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        self._rows.append(_thought_from_dict(json.loads(line)))

    def append(self, t: Thought) -> None:
        # Writes accepted, never visible on reads.
        return None

    def read(
        self,
        *,
        as_of: datetime,
        current_tick: int,
        symbol: str | None = None,
    ) -> list[Thought]:
        return _apply_guards(
            self._rows,
            as_of=as_of,
            current_tick=current_tick,
            symbol=symbol,
        )


class SyntheticLedger:
    """Injected counterfactual ledger for stress tests.

    Construct with a pre-built list of Thoughts representing the
    "null hypothesis" peer landscape. Used in chemical-reaction
    what-ifs and in the F17 control arm where we want to know how an
    agent would react to fully synthetic peers.
    """

    mode = "synthetic"

    def __init__(self, null_hypothesis: list[Thought]) -> None:
        self._rows = list(null_hypothesis)

    def append(self, t: Thought) -> None:
        self._rows.append(t)

    def read(
        self,
        *,
        as_of: datetime,
        current_tick: int,
        symbol: str | None = None,
    ) -> list[Thought]:
        return _apply_guards(
            self._rows,
            as_of=as_of,
            current_tick=current_tick,
            symbol=symbol,
        )
