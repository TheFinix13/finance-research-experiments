"""Per-agent news-calendar windowing helper (D-Q5).

Each M001 agent has a ``home_tf`` attribute (``"H4"``, ``"H1"``,
``"M15"``, ``"M5"``, ``"D1"``, ...). Bachira's chemical-reaction path
means she may execute on ``M5`` while consuming Isagi's ``H4`` peer
confluence -- so the news-window sizing must respect the CALLER'S TF,
not a global default. This module maps each timeframe to spec §5.4
window sizes and exposes ``window_for_agent`` / ``tag_bars_for_agent``
so agents opt in with a single-line call at the F18 join site.

Non-goal: this module does NOT change any agent's ``intend()`` logic.
Wiring inside ``intend`` lands post-G7 alongside the F18 KPI module.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

from .news_calendar import (
    DEFAULT_POST_EVENT_MINUTES,
    DEFAULT_PRE_EVENT_MINUTES,
    DEFAULT_SOURCES,
    IMPORTANCE_HIGH,
    tag_bars_with_news,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TF -> (pre, post) window tables
# ---------------------------------------------------------------------------

# Bar-count windows apply to H4 and D1 (spec §5.4). The pre/post pair
# is (bars-before, bars-after).
BAR_COUNT_WINDOWS: dict[str, tuple[int, int]] = {
    "H4": (2, 2),      # ±8 hours -- matches legacy validate_real default
    "D1": (1, 1),      # ±1 day
    "H1": (4, 8),      # ±4 h before, ±8 h after (2h + 8h ~= 60min post)
}

# Minute-based windows apply to intraday TFs (M1/M5/M15). Per spec §5.4
# defaults: pre=5 min, post=60 min.
MINUTE_WINDOWS: dict[str, tuple[int, int]] = {
    "M1":  (DEFAULT_PRE_EVENT_MINUTES, DEFAULT_POST_EVENT_MINUTES),
    "M5":  (DEFAULT_PRE_EVENT_MINUTES, DEFAULT_POST_EVENT_MINUTES),
    "M15": (DEFAULT_PRE_EVENT_MINUTES, DEFAULT_POST_EVENT_MINUTES),
    "M30": (DEFAULT_PRE_EVENT_MINUTES, DEFAULT_POST_EVENT_MINUTES),
}


def window_for_agent(agent: Any) -> dict[str, int]:
    """Return the news-window kwargs appropriate for ``agent.home_tf``.

    Output shape:
    - Intraday agents (M1/M5/M15/M30): ``{"pre_event_minutes": N, "post_event_minutes": M}``
      -- adapter auto-selects the intraday windowing path.
    - H4 / H1 / D1 agents: ``{"pre_event_bars": N, "post_event_bars": M}``
      -- adapter uses bar-count windowing.

    Falls back to the H4 default when the agent's TF is unknown, with
    a WARNING (defensive so tests never explode on a mislabelled agent).
    """
    tf = getattr(agent, "home_tf", None)
    if tf is None:
        log.warning(
            "%s has no home_tf attribute; using H4 window defaults",
            getattr(agent, "agent_id", "<unknown-agent>"),
        )
        pre, post = BAR_COUNT_WINDOWS["H4"]
        return {"pre_event_bars": pre, "post_event_bars": post}
    tf_key = str(tf).upper()
    if tf_key in MINUTE_WINDOWS:
        pre_min, post_min = MINUTE_WINDOWS[tf_key]
        return {
            "pre_event_minutes": pre_min,
            "post_event_minutes": post_min,
        }
    if tf_key in BAR_COUNT_WINDOWS:
        pre, post = BAR_COUNT_WINDOWS[tf_key]
        return {"pre_event_bars": pre, "post_event_bars": post}
    log.warning(
        "%s home_tf=%r not in windowing tables; using H4 defaults",
        getattr(agent, "agent_id", "<unknown-agent>"), tf,
    )
    pre, post = BAR_COUNT_WINDOWS["H4"]
    return {"pre_event_bars": pre, "post_event_bars": post}


def tag_bars_for_agent(
    bars_index,
    agent: Any,
    *,
    symbol_pair: str | None = None,
    sources: Iterable[str] = DEFAULT_SOURCES,
    importance_min: int = IMPORTANCE_HIGH,
    **extra_kwargs,
):
    """Convenience: window kwargs auto-inferred from ``agent.home_tf``
    then forwarded to ``tag_bars_with_news``. Caller only needs to
    provide the bar index + agent + symbol pair.

    If ``symbol_pair`` is None, tries ``agent.primary_symbol`` /
    ``agent.symbols[0]`` (in that order). Raises ``ValueError`` when
    neither the argument nor an agent attribute resolves.
    """
    if symbol_pair is None:
        sp = getattr(agent, "primary_symbol", None)
        if sp is None:
            syms = getattr(agent, "symbols", None)
            if syms:
                sp = next(iter(syms))
        if sp is None:
            raise ValueError(
                f"symbol_pair not provided and {agent!r} has no "
                f"primary_symbol / symbols attribute"
            )
        symbol_pair = sp

    window_kwargs = window_for_agent(agent)
    window_kwargs.update(extra_kwargs)      # caller override wins
    return tag_bars_with_news(
        bars_index,
        symbol_pair=symbol_pair,
        sources=sources,
        importance_min=importance_min,
        **window_kwargs,
    )


__all__ = [
    "BAR_COUNT_WINDOWS",
    "MINUTE_WINDOWS",
    "window_for_agent",
    "tag_bars_for_agent",
]
