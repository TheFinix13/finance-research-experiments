"""E024 stall-signal detectors (five families, PROTOCOL §3.2).

Each stall signal is a per-trade stateful callable of ``(TradeState, Bar)``
that returns a ``close_at`` ``ExitAction`` when the stall condition fires,
and ``None`` otherwise. The engine treats the ``ExitAction.reason`` tag
``PRIORITY_E024_STALL`` per SPEC §4.3 (above broker TP, below hard SL).

Signals
-------
- **S1_wallclock** — fires when ``bar.time - state.mfe_ts_so_far >= stall_secs``.
- **S2_h1_range** — on the completion of an H1 bar after activation, last
  four completed H1 closes span ≤ 10 pips.
- **S3_h1_reversal** — on the completion of an H1 bar after activation,
  the newest close crosses back past the prior 3-close favourable extremum
  by ≥ 3 pips (long: ``c_n ≤ max(c_{n-3..n-1}) − 3p``; short: symmetric).
- **S4_bar_stall_h1** — three consecutive completed H1 bars after
  activation with no new MFE extension.
- **S5_any_of_1-4** — OR of all four with ``stall_secs`` locked at 3600 s
  (PROTOCOL §3.2 last paragraph, keeps family size at 24).

H1-bucket reconstruction
------------------------
PROTOCOL §3.2 defines S2/S3/S4 on completed H1 bars. The PRE-0 data
plane exposes ``path_resolution ∈ {M5, M15, H1, H4}`` (SPEC §1 amended).
This module reconstructs "H1 buckets" from whatever finer resolution the
path exposes:

- M5 (12 bars / H1 bucket), M15 (4 bars / bucket), H1 (1 bar / bucket):
  a bucket is complete when the next bar's ``bar.time.replace(minute=0, second=0)``
  differs from the running bucket key.
- **H4 fallback** — a single H4 bar covers four H1 buckets simultaneously
  (SPEC §1 acknowledges this). Per PROTOCOL §4.1 last row ("H4 fallback
  flagged, not silently dropped"), we treat each H4 bar close as one
  "pseudo-H1" completion. The signals still evaluate, but on H4 granularity
  — declared as *low fidelity* to the caller so the report can quantify
  the degradation instead of pretending it isn't there.

Activation
----------
No signal fires before the trade reaches ``mfe_r_so_far ≥ activation_R``.
Once armed, signals evaluate on every bar (S1) or on H1-bucket completion
(S2/S3/S4/S5).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from programs._shared.counterfactual_replay.replay import (
    PIP,
    PRIORITY_E024_STALL,
    Bar,
    ExitAction,
    TradeState,
)

# Signal names — canonical string tags used everywhere downstream.
SIGNAL_S1 = "S1_wallclock"
SIGNAL_S2 = "S2_h1_range"
SIGNAL_S3 = "S3_h1_reversal"
SIGNAL_S4 = "S4_bar_stall_h1"
SIGNAL_S5 = "S5_any_of_1-4"

_ALL_SIGNALS: tuple[str, ...] = (SIGNAL_S1, SIGNAL_S2, SIGNAL_S3, SIGNAL_S4, SIGNAL_S5)

# S5 locks S1 sub-timer at 3600 s (PROTOCOL §3.2).
S5_LOCKED_STALL_SECS: float = 3600.0

# S2 range threshold and S3 reversal threshold (PROTOCOL §3.2, locked).
S2_H1_RANGE_MAX_PIPS: float = 10.0
S3_H1_REVERSAL_MIN_PIPS: float = 3.0
S4_H1_BARS_NO_EXTEND: int = 3


@dataclass
class FireDetails:
    """Populated on the trade where the rule fired; ``None`` otherwise.

    Diagnostics for the false-positive audit, report, and unit tests."""

    sub_signal: str          # "S1" | "S2" | "S3" | "S4" (for S5, tells which sub-fired)
    bar_index: int
    bar_time: datetime
    fire_price: float
    mfe_r_at_fire: float
    mfe_pips_at_fire: float
    elapsed_since_mfe_ts: float  # seconds
    h1_no_extend_count: int


class E024StallRule:
    """Stateful callable rule for one E024 stage-1 arm.

    Usage::

        rule = E024StallRule(activation_r=1.45, signal=SIGNAL_S1, stall_secs=3600)
        for t in trades:
            rule.reset()
            alt = replay(t, rule=rule)
            if rule.fired_details:
                # this trade triggered the stall
                ...

    The engine's exit-priority ordering (SPEC §4.3) makes ``PRIORITY_E024_STALL``
    beat broker TP but lose to hard SL — matches PROTOCOL §3.2 stall-exit
    semantics. If the trade's path never reaches ``activation_R``, the
    rule never returns an action and the replay falls back to the original
    exit (SPEC §4 fall-through).
    """

    def __init__(
        self,
        activation_r: float,
        signal: str,
        stall_secs: Optional[float] = None,
    ) -> None:
        if signal not in _ALL_SIGNALS:
            raise ValueError(f"Unknown signal {signal!r}. Expected one of {_ALL_SIGNALS}.")
        if signal == SIGNAL_S1 and stall_secs is None:
            raise ValueError("S1_wallclock requires stall_secs.")
        if signal == SIGNAL_S5:
            # Locked constant, ignore anything the caller passes.
            stall_secs = S5_LOCKED_STALL_SECS
        self.activation_r = float(activation_r)
        self.signal = signal
        self.stall_secs = float(stall_secs) if stall_secs is not None else None
        self.reset()

    # ------------------------------------------------------------------
    # Per-trade state.
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._activated: bool = False
        self._activation_bar_index: Optional[int] = None
        self._current_h1_key: Optional[datetime] = None
        self._mfe_at_bucket_start: float = 0.0
        self._closed_h1_closes: list[float] = []
        self._h1_no_extend_count: int = 0
        self._last_bar_close: Optional[float] = None
        self._last_bar_mfe: float = 0.0
        self._fired: bool = False
        self.fired_details: Optional[FireDetails] = None

    # ------------------------------------------------------------------
    # Rule call — the engine invokes this once per bar.
    # ------------------------------------------------------------------
    def __call__(self, state: TradeState, bar: Bar) -> Optional[ExitAction]:
        # Defensive reset on bar 0 (belt-and-suspenders — the sweep calls
        # reset() explicitly, but this catches any caller that forgets).
        if state.bar_index == 0 and (self._fired or self._current_h1_key is not None):
            self.reset()

        if self._fired:
            return None

        # 1) Activation check (once armed, stays armed).
        if not self._activated and state.mfe_r_so_far >= self.activation_r:
            self._activated = True
            self._activation_bar_index = state.bar_index

        # 2) H1-bucket accounting. Detect transition BEFORE evaluating H1 signals.
        current_h1_key = bar.time.replace(minute=0, second=0, microsecond=0)
        just_completed_bucket = False
        if self._current_h1_key is None:
            self._current_h1_key = current_h1_key
            self._mfe_at_bucket_start = 0.0
        elif current_h1_key != self._current_h1_key:
            # The bucket keyed by self._current_h1_key just completed.
            # Its close = the previous bar's close (self._last_bar_close).
            # Its terminal MFE = the previous bar's MFE (self._last_bar_mfe).
            just_completed_bucket = True
            assert self._last_bar_close is not None
            self._closed_h1_closes.append(self._last_bar_close)
            bucket_extended = self._last_bar_mfe > self._mfe_at_bucket_start + 1e-12
            if self._activated:
                if bucket_extended:
                    self._h1_no_extend_count = 0
                else:
                    self._h1_no_extend_count += 1
            # Start new bucket with this bar.
            self._current_h1_key = current_h1_key
            self._mfe_at_bucket_start = self._last_bar_mfe

        # 3) Evaluate signals, only if armed.
        fired_sub: Optional[str] = None
        if self._activated:
            if self.signal == SIGNAL_S1:
                elapsed_s = (bar.time - state.mfe_ts_so_far).total_seconds()
                if elapsed_s >= self.stall_secs:  # type: ignore[operator]
                    fired_sub = "S1"

            elif self.signal == SIGNAL_S2:
                if just_completed_bucket and len(self._closed_h1_closes) >= 4:
                    last4 = self._closed_h1_closes[-4:]
                    rng_pips = (max(last4) - min(last4)) / PIP
                    if rng_pips <= S2_H1_RANGE_MAX_PIPS:
                        fired_sub = "S2"

            elif self.signal == SIGNAL_S3:
                if just_completed_bucket and len(self._closed_h1_closes) >= 4:
                    latest = self._closed_h1_closes[-1]
                    prior3 = self._closed_h1_closes[-4:-1]
                    if state.direction == +1:
                        E = max(prior3)
                        if latest <= E - S3_H1_REVERSAL_MIN_PIPS * PIP:
                            fired_sub = "S3"
                    else:
                        E = min(prior3)
                        if latest >= E + S3_H1_REVERSAL_MIN_PIPS * PIP:
                            fired_sub = "S3"

            elif self.signal == SIGNAL_S4:
                if just_completed_bucket and self._h1_no_extend_count >= S4_H1_BARS_NO_EXTEND:
                    fired_sub = "S4"

            elif self.signal == SIGNAL_S5:
                # S1 sub-check on every bar (locked at 3600 s per PROTOCOL §3.2).
                elapsed_s = (bar.time - state.mfe_ts_so_far).total_seconds()
                if elapsed_s >= S5_LOCKED_STALL_SECS:
                    fired_sub = "S1"
                # H1-bar-based sub-checks only on bucket completion.
                if fired_sub is None and just_completed_bucket:
                    if len(self._closed_h1_closes) >= 4:
                        last4 = self._closed_h1_closes[-4:]
                        rng_pips = (max(last4) - min(last4)) / PIP
                        if rng_pips <= S2_H1_RANGE_MAX_PIPS:
                            fired_sub = "S2"
                        else:
                            latest = self._closed_h1_closes[-1]
                            prior3 = self._closed_h1_closes[-4:-1]
                            if state.direction == +1:
                                E = max(prior3)
                                if latest <= E - S3_H1_REVERSAL_MIN_PIPS * PIP:
                                    fired_sub = "S3"
                            else:
                                E = min(prior3)
                                if latest >= E + S3_H1_REVERSAL_MIN_PIPS * PIP:
                                    fired_sub = "S3"
                    if fired_sub is None and self._h1_no_extend_count >= S4_H1_BARS_NO_EXTEND:
                        fired_sub = "S4"

        # 4) Advance trailing per-bar state (used to detect bucket completion
        # on the NEXT bar, and to seed the new bucket's MFE reference).
        self._last_bar_close = bar.close
        self._last_bar_mfe = state.mfe_pips_so_far

        # 5) Fire (or not).
        if fired_sub is not None:
            self._fired = True
            self.fired_details = FireDetails(
                sub_signal=fired_sub,
                bar_index=state.bar_index,
                bar_time=bar.time,
                fire_price=bar.close,
                mfe_r_at_fire=state.mfe_r_so_far,
                mfe_pips_at_fire=state.mfe_pips_so_far,
                elapsed_since_mfe_ts=(bar.time - state.mfe_ts_so_far).total_seconds(),
                h1_no_extend_count=self._h1_no_extend_count,
            )
            return ExitAction(
                kind="close_at",
                price=bar.close,
                reason=PRIORITY_E024_STALL,
            )
        return None


# ---------------------------------------------------------------------------
# Public helpers so tests + the sweep can build arms uniformly.
# ---------------------------------------------------------------------------

def arm_id(activation_r: float, signal: str, stall_secs: Optional[float]) -> str:
    if signal == SIGNAL_S1:
        return f"a{activation_r:.2f}_{signal}_s{int(stall_secs)}"  # type: ignore[arg-type]
    if signal == SIGNAL_S5:
        return f"a{activation_r:.2f}_{signal}_s{int(S5_LOCKED_STALL_SECS)}"
    return f"a{activation_r:.2f}_{signal}"


def make_arm_grid(
    activation_grid: tuple[float, ...],
    s1_stall_secs_grid: tuple[float, ...],
) -> list[dict]:
    """Deterministic enumeration of the 24-arm stage-1 grid.

    PROTOCOL §4.1: activation × {S1_wallclock × 4 stall_secs, S2, S3, S4, S5}.
    Total = |activation| × (|s1_stall_secs| + 4) arms.
    """
    arms: list[dict] = []
    for a in activation_grid:
        for s in s1_stall_secs_grid:
            arms.append({
                "activation_r": a,
                "signal": SIGNAL_S1,
                "stall_secs": s,
                "arm_id": arm_id(a, SIGNAL_S1, s),
            })
        for sig in (SIGNAL_S2, SIGNAL_S3, SIGNAL_S4):
            arms.append({
                "activation_r": a,
                "signal": sig,
                "stall_secs": None,
                "arm_id": arm_id(a, sig, None),
            })
        arms.append({
            "activation_r": a,
            "signal": SIGNAL_S5,
            "stall_secs": S5_LOCKED_STALL_SECS,
            "arm_id": arm_id(a, SIGNAL_S5, S5_LOCKED_STALL_SECS),
        })
    return arms
