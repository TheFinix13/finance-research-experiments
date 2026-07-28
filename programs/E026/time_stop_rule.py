"""E026 low-MFE time-stop rule (PROTOCOL §3, frozen).

Fires a ``close_at(bar.close)`` on the FIRST completed path bar where

    bars_held (= bar_index + 1) >= B   AND   mfe_r_so_far < P

A trade whose running MFE has EVER touched ``P`` is permanently exempt
("get going or get out" gate, not a trail). The engine updates MFE from
the current bar's extremes BEFORE calling the rule, so a bar that
touches TP raises ``mfe_r_so_far`` past any ``P <= 0.75`` and the rule
cannot fire on a TP bar (PROTOCOL §0). Same-bar hard SL outranks the
rule via the SPEC §4.3 priority order.

The ``e026_time_stop`` reason tag is not in the engine's priority map,
so it lands in the default ``PRIORITY_E024_STALL`` slot — above broker
TP (moot, see above) and below hard SL, exactly the pre-registered
semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from programs._shared.counterfactual_replay.replay import (
    Bar,
    ExitAction,
    TradeState,
)

REASON_E026_TIME_STOP = "e026_time_stop"

# Frozen §4.1 grid.
P_GRID: tuple[float, ...] = (0.25, 0.50, 0.75)
B_GRID: tuple[int, ...] = (12, 18, 24, 30, 42)

# Amendment 2 — PRE-0 path resolution → fraction of one H4 bar. The age
# clock is defined in completed H4-equivalents so the rule is identical
# across symbols regardless of path granularity.
RESOLUTION_TO_H4_FRACTION: dict[str, float] = {
    "M5": 1.0 / 48.0,
    "M15": 1.0 / 16.0,
    "H1": 1.0 / 4.0,
    "H4": 1.0,
}


@dataclass
class FireDetails:
    """Diagnostics captured on the trade where the rule fired."""

    bar_index: int
    bar_time: datetime
    fire_price: float
    bars_held_h4: float
    mfe_r_at_fire: float
    mfe_pips_at_fire: float


class E026TimeStopRule:
    """Stateful callable rule for one E026 stage-1 arm.

    Usage::

        rule = E026TimeStopRule(progress_r=0.50, age_bars=30)
        for t in trades:
            rule.reset(path_resolution=t.path_resolution)
            alt = replay(t, rule=rule)
            if rule.fired_details is not None:
                ...  # this trade was time-stopped
    """

    def __init__(self, progress_r: float, age_bars: int) -> None:
        if progress_r <= 0:
            raise ValueError(f"progress_r must be > 0, got {progress_r}")
        if age_bars < 1:
            raise ValueError(f"age_bars must be >= 1, got {age_bars}")
        self.progress_r = float(progress_r)
        self.age_bars = int(age_bars)         # in H4-equivalents (Amendment 2)
        self._h4_fraction = RESOLUTION_TO_H4_FRACTION["H4"]
        self.fired_details: Optional[FireDetails] = None

    def reset(self, path_resolution: str = "H4") -> None:
        if path_resolution not in RESOLUTION_TO_H4_FRACTION:
            raise ValueError(f"Unknown path resolution {path_resolution!r}")
        self._h4_fraction = RESOLUTION_TO_H4_FRACTION[path_resolution]
        self.fired_details = None

    def __call__(self, state: TradeState, bar: Bar) -> Optional[ExitAction]:
        # Permanent exemption: mfe_r_so_far is monotone, so a single check
        # per bar suffices — once >= P it stays >= P forever.
        if state.mfe_r_so_far >= self.progress_r:
            return None
        bars_held_h4 = (state.bar_index + 1) * self._h4_fraction
        if bars_held_h4 < self.age_bars:
            return None
        if self.fired_details is None:
            self.fired_details = FireDetails(
                bar_index=state.bar_index,
                bar_time=state.now,
                fire_price=bar.close,
                bars_held_h4=bars_held_h4,
                mfe_r_at_fire=state.mfe_r_so_far,
                mfe_pips_at_fire=state.mfe_pips_so_far,
            )
        return ExitAction(
            kind="close_at",
            price=bar.close,
            reason=REASON_E026_TIME_STOP,
        )


def make_arm_grid(
    p_grid: tuple[float, ...] = P_GRID,
    b_grid: tuple[int, ...] = B_GRID,
) -> list[dict]:
    """The frozen 15-arm stage-1 grid (PROTOCOL §4.1). Order: P-major."""
    grid: list[dict] = []
    for p in p_grid:
        for b in b_grid:
            grid.append({
                "arm_id": f"P{p:.2f}_B{b}",
                "progress_r": float(p),
                "age_bars": int(b),
            })
    return grid
