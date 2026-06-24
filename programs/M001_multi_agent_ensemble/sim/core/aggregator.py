"""Minimal aggregator stub for Phi2.5.

The full HRP allocator + chemical-reaction branch lands in Phi3+
(architecture sections 4 + 5; foundations F3 / F11 / F13). This stub
implements just enough of architecture section 5 to prove the
end-to-end protocol works:

* Same direction, same pair -> single OrderIntent. Size = sum of
  proposed sizes (capped to 1.0 in this stub — no Kelly / HRP).
* Opposing direction, same pair -> highest-conviction wins; loser is
  journalled in the OrderIntent's `rationale.vetoed`.
* Different symbols -> independent OrderIntents.

The chemical-reaction layer is **not wired** in Phi2.5; the size
multiplier from F11 stays as a unit (1.0x). When Phi3 lands HRP +
chemical reactions, this module becomes ~3x its current size.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from .types import AgentProposal, OrderIntent


def _intent_id(symbol: str, tick_id: int, direction: str) -> str:
    return f"intent:{tick_id}:{symbol}:{direction}"


def aggregate(
    proposals: Iterable[AgentProposal],
    *,
    tick_id: int,
    timestamp: datetime,
) -> list[OrderIntent]:
    """Phi2.5 aggregator: minimal union with conflict resolution.

    Returns at most one OrderIntent per (symbol, direction) pair on
    this tick. Conflicts (opposing directions on same symbol) resolve
    by highest conviction; the loser is journalled.
    """
    proposals = [p for p in proposals if p is not None and p.direction != "flat"]
    if not proposals:
        return []

    # Group by (symbol, direction).
    by_sym_dir: dict[tuple[str, str], list[AgentProposal]] = defaultdict(list)
    by_sym: dict[str, list[AgentProposal]] = defaultdict(list)
    for p in proposals:
        by_sym_dir[(p.symbol, p.direction)].append(p)
        by_sym[p.symbol].append(p)

    intents: list[OrderIntent] = []
    handled: set[str] = set()

    for symbol, plist in by_sym.items():
        directions = {p.direction for p in plist}
        if directions == {"long"} or directions == {"short"}:
            # Same direction -> union ticket.
            d = next(iter(directions))
            members = by_sym_dir[(symbol, d)]
            winner = members[0]
            size = min(1.0, sum(m.conviction for m in members))
            intent = OrderIntent(
                intent_id=_intent_id(symbol, tick_id, d),
                tick_id=tick_id,
                timestamp=timestamp,
                symbol=symbol,
                direction=d,
                entry=winner.entry,
                stop=_tightest_stop(members, d),
                size=size,
                ladder=winner.ladder,
                contributing_thought_ids=[m.source_thought_id for m in members],
                contributing_proposal_ids=[
                    f"{m.agent_id}:{m.tick_id}" for m in members
                ],
                rationale={
                    "rule": "same_direction_union",
                    "n_contributors": len(members),
                    "conviction_sum": float(
                        sum(m.conviction for m in members)
                    ),
                },
            )
            intents.append(intent)
            handled.add(symbol)
        else:
            # Opposing -> highest conviction wins.
            winner = max(plist, key=lambda p: p.conviction)
            losers = [p for p in plist if p is not winner]
            intent = OrderIntent(
                intent_id=_intent_id(symbol, tick_id, winner.direction),
                tick_id=tick_id,
                timestamp=timestamp,
                symbol=symbol,
                direction=winner.direction,
                entry=winner.entry,
                stop=winner.stop,
                size=min(1.0, winner.conviction),
                ladder=winner.ladder,
                contributing_thought_ids=[winner.source_thought_id],
                contributing_proposal_ids=[f"{winner.agent_id}:{winner.tick_id}"],
                rationale={
                    "rule": "opposing_highest_conviction",
                    "winner_agent": winner.agent_id,
                    "winner_conviction": float(winner.conviction),
                    "vetoed": [
                        {
                            "agent_id": p.agent_id,
                            "direction": p.direction,
                            "conviction": float(p.conviction),
                        }
                        for p in losers
                    ],
                },
            )
            intents.append(intent)
            handled.add(symbol)
    return intents


def _tightest_stop(props: list[AgentProposal], direction: str) -> float:
    """Tightest stop wins (architecture section 5 rule 1)."""
    if direction == "long":
        # Stop is below entry; tightest = largest stop value.
        return max(p.stop for p in props)
    elif direction == "short":
        # Stop is above entry; tightest = smallest stop value.
        return min(p.stop for p in props)
    return props[0].stop
