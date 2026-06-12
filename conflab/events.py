"""Stage-0 event framework: directional events + detector registry.

An Event is one occurrence of a pattern/level interaction at a specific bar,
carrying its PRE-REGISTERED directional hypothesis:

    +1  price expected to rise after the event
    -1  price expected to fall after the event

Conventions (fixed in PROTOCOL.md):
* touch-type events hypothesise the bounce (against the approach),
* break-type events (BOS/CHoCH, neckline completion) the continuation,
* magnet-type events (liquidity pools) the draw toward the level.

Causality rule: an event at bar t may only use information from bars <= t.
Swing points count as confirmed ``lookback`` bars after their extreme; all
detectors here respect that.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class Event:
    index: int        # positional bar index (the bar at which it is KNOWN)
    time: str         # ISO timestamp of that bar
    type: str         # registry key, e.g. "bos_bullish"
    direction: int    # +1 / -1 directional hypothesis
    level: float      # the price the event is anchored to
    detail: str = ""

    def to_dict(self) -> dict:
        return {"index": self.index, "time": self.time, "type": self.type,
                "direction": self.direction, "level": self.level,
                "detail": self.detail}


# A detector takes an OHLCV frame and returns events (possibly of several
# related types — screening groups by Event.type).
Detector = Callable[[pd.DataFrame], list[Event]]


def all_detectors() -> dict[str, Detector]:
    """The Test-A registry: family-prefixed detector callables.

    Built lazily to avoid import cycles. Families still in the build queue
    are listed in PROTOCOL.md Stage 0 and appended here as they land.
    """
    from conflab.detectors_chartpatterns import (
        detect_chart_pattern_events,
        detect_flag_events,
        detect_rectangle_events,
    )
    from conflab.detectors_fib import detect_fib_events
    from conflab.detectors_levels import (
        detect_ntouch_level_events,
        detect_pdh_pdl_touches,
        detect_pwh_pwl_touches,
        detect_round_number_touches,
        detect_sr_flip_events,
    )
    from conflab.detectors_liquidity import detect_liquidity_events
    from conflab.detectors_patterns import (
        detect_candle_pattern_events,
        detect_double_pattern_completions,
        detect_multibar_candle_events,
    )
    from conflab.detectors_sessions import detect_session_sweeps
    from conflab.detectors_structure import (
        detect_bos_choch,
        detect_premium_discount_events,
    )
    from conflab.detectors_trendlines import detect_trendline_events
    from conflab.detectors_zones import detect_fvg_events, detect_zone_events

    return {
        "structure": detect_bos_choch,
        "structure_pd": detect_premium_discount_events,
        "liquidity": detect_liquidity_events,
        "sessions": detect_session_sweeps,
        "levels_round": detect_round_number_touches,
        "levels_srflip": detect_sr_flip_events,
        "levels_pdhl": detect_pdh_pdl_touches,
        "levels_pwhl": detect_pwh_pwl_touches,
        "levels_ntouch": detect_ntouch_level_events,
        "zones": detect_zone_events,
        "fvg": detect_fvg_events,
        "trendlines": detect_trendline_events,
        "fib": detect_fib_events,
        "patterns_double": detect_double_pattern_completions,
        "patterns_chart": detect_chart_pattern_events,
        "patterns_flag": detect_flag_events,
        "patterns_rect": detect_rectangle_events,
        "patterns_candle": detect_candle_pattern_events,
        "patterns_candle_multi": detect_multibar_candle_events,
    }
