"""E022 rescorer — apply the ``snap_tp`` rule and score the alt outcome.

PROTOCOL:
  experiments/E022_structure_aware_tp_snap/PROTOCOL.md
  §3.1 (snap_tp), §3.2 (direction invariant), §4.2 (fill decision rule).

Two exposed functions:

* :func:`snap_tp` — pure formula, PROTOCOL §3.1 verbatim. Takes the
  historical trade's ``entry``, mechanical ``tp``, ``direction``, a level
  set ``L`` (list of floats), and the arm's ``(snap_distance, snap_offset)``.
  Returns the new TP price. If no snap fires, returns ``tp`` unchanged
  (null-rule identity).

* :func:`rescore_trade` — the fill-decision helper. Takes a PRE-0
  :class:`TradeRecord` and a ``new_tp`` price and returns an
  ``AltOutcome`` (``exit_time`` / ``exit_price`` / ``exit_reason`` /
  ``pnl_pips`` / ``r`` / ``fired``) using the PROTOCOL §4.2 fill rule.

Why we don't reuse ``programs/_shared/counterfactual_replay/replay.py``
for E022 (design note):

The shared replay engine's ``adjust_tp`` action applies the new TP AFTER
bar 0's own exit check runs (replay.py L560-565: ``if i == 0: tp =
rule_tp_adjust.price``). PROTOCOL §4.2 explicitly says the new TP fills
on any bar between ``entry_time`` and the original ``exit_time`` (inclusive)
— **including bar 0**. Bar 0 must count. So E022 does the fill scan
directly against ``trade.path``, which is the cleaner architecture for an
order-placement rule anyway (no lifetime-side effect, no intra-bar exit
semantics — just a modified target that the same path either touches
before the original exit or does not).

Fill scan semantics (PROTOCOL §4.2 verbatim):

1. If ``new_tp == tp``, snap did not fire — the alt outcome is byte-for-
   byte identical to the historical trade (null-rule identity).

2. Otherwise iterate ``trade.path`` bar-by-bar in order. For every path
   bar, check whether the bar's high/low touches ``new_tp`` (long:
   ``bar.high >= new_tp``; short: ``bar.low <= new_tp``). The first
   touching bar is the alt fill; ``exit_time`` = that bar's time,
   ``exit_price`` = ``new_tp``, ``exit_reason`` = ``"e022_snap_tp"``.

3. If the path exhausts without a hit, fall back to the ORIGINAL exit
   (baseline identity — no synthetic fill invented).

Scan-window design note (mismatch with prompt spec, deliberate). The
task prompt suggested the strict-less-than form
``bar.time < trade.exit_time``. That form silently drops legitimate
fills in two cases specific to how the PRE-0 exporter records exits:

* Same-bar-TP trades. When a trade opens and hits TP inside the same
  H4 bar, the PRE-0 exporter records ``exit_time == entry_time`` (H4
  bar start), while ``trade.path`` is the M5 sub-bars *within* that
  H4 bar (per ``export_ledger_with_paths.py::_extract_path_and_excursions``).
  Under ``bar.time < exit_time``, ZERO M5 sub-bars would be scanned
  and the snap could never fire on same-bar TP trades — 134 / 411 =
  33 % of EURUSD winners on the deployed cell. Concrete example:
  ``EURUSD_H4_00000`` (2015-02-17 long, entry+TP inside the 08:00 H4
  bar; M5 sub-bar at 10:50 hits TP).

* Diff-bar TP trades where ``exit_time`` is the H4 bar START (not the
  actual M5 fill moment). Concrete example: ``EURUSD_H4_00001`` has
  ``exit_time = 2015-02-23 00:00 UTC`` (H4 bar start) but the TP fill
  is on the M5 bar at 00:15 UTC — after ``exit_time``. Under
  ``bar.time < exit_time`` we would miss the fill bar even though it
  IS between entry_time and the original exit *H4 bar*.

PROTOCOL §4.2 explicitly says "on any bar between ``entry_time`` and
the original ``exit_time`` (inclusive), evaluated on M5 path bars if
available". The natural reading is: on any M5 sub-bar of the trade's
recorded window, including sub-bars *within* the exit H4 bar. The
PRE-0 exporter builds ``trade.path`` to be exactly that window
(``[entry_time, exit_time + trade_tf_duration)``), so this
implementation scans the full ``trade.path``. This matches PROTOCOL
§4.2 "inclusive on M5 path bars" and gives same-bar TP trades a
chance to fire the snap.

Direction consistency guarantee. Because the snap is inward-only
(§3.2 direction invariant), ``new_tp`` is strictly closer to entry
than the original ``tp`` on the trade's directed axis. For any bar
that hits the original ``tp``, the same bar's high/low MUST have
already crossed ``new_tp`` — so on winning trades the alt fill fires
at or before the original TP timestamp, never after. For SL-hit
trades, whether ``new_tp`` fires at all depends on the intra-trade
path; if the path never favours enough to touch ``new_tp``, we
correctly fall back to the original SL exit.

The trade's ``r`` under the alt fill is
``direction_sign * (exit_price - entry) / (stop_pips * PIP)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

# Import from the shared replay data plane (TradeRecord dataclass) — we do
# NOT invoke ``replay()`` itself (see module docstring); we only use the
# TradeRecord schema so callers can pass the same PRE-0 objects they use
# for E020/E021/E024.
from programs._shared.counterfactual_replay.replay import (
    Bar,
    PIP,
    TradeRecord,
)


SNAP_EXIT_REASON = "e022_snap_tp"


# ---------------------------------------------------------------------------
# The rule — PROTOCOL §3.1 verbatim.
# ---------------------------------------------------------------------------

def snap_tp(
    entry: float,
    tp: float,
    direction: str | int,
    L: Sequence[float],
    snap_distance_pips: float,
    snap_offset_pips: float,
    *,
    pip: float = PIP,
) -> float:
    """Return the new TP price after applying the E022 snap rule.

    Parameters mirror PROTOCOL §3.1 argument order:

    - ``entry``: trade entry price.
    - ``tp``: mechanical take-profit price (``entry ± target_rr·stop_pips``).
    - ``direction``: ``"long"``/``"short"`` string, or ``+1``/``-1``.
    - ``L``: level set — an iterable of candidate prices (already deduped;
      the strict-between filter is enforced HERE per §3.2 to keep the rule
      self-contained even if callers pre-filter).
    - ``snap_distance_pips``: arm's distance threshold (5 / 10 / 15).
    - ``snap_offset_pips``: pinned as ``min(3, snap_distance/2)`` — never
      an arm.
    - ``pip``: pip factor (default 4-decimal FX).

    Invariants (unit-tested in ``tests/test_e022_rule.py``):

    - Never widens: ``abs(new_tp − entry) <= abs(tp − entry)`` for all inputs.
    - Idempotent: ``snap_tp(entry, snap_tp(entry, tp, ...), ...) == snap_tp(...)``.
    - Direction-safe: only fires on levels strictly between entry and tp
      (§3.2). A level at exactly ``tp`` or exactly ``entry`` does not fire.
    """
    sign = _direction_sign(direction)
    lo, hi = (entry, tp) if entry < tp else (tp, entry)
    candidates = [float(lvl) for lvl in L if lo < float(lvl) < hi]
    if not candidates:
        return tp

    nearest = min(candidates, key=lambda x: abs(x - tp))
    d_pips = abs(nearest - tp) / pip
    if d_pips > snap_distance_pips:
        return tp

    new_tp = nearest - sign * snap_offset_pips * pip
    return new_tp


def _direction_sign(direction: str | int) -> int:
    if isinstance(direction, str):
        if direction == "long":
            return +1
        if direction == "short":
            return -1
        raise ValueError(f"Unknown direction string: {direction!r}")
    if direction in (+1, -1):
        return int(direction)
    raise ValueError(f"direction must be 'long'/'short' or ±1, got {direction!r}")


# ---------------------------------------------------------------------------
# The fill scan — PROTOCOL §4.2.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AltOutcome:
    """Result of rescoring one trade under a modified TP.

    ``fired`` = True if the snap actually moved the TP (``new_tp != tp``);
    used to compute ``snap_fire_rate`` in the sweep.

    ``filled_at_snap`` = True if the alt fill was the new_tp (as opposed
    to the original exit); used for the ``Δ P(TP fills)`` sanity gate
    (PROTOCOL §6.5).
    """

    exit_time: datetime
    exit_price: float
    exit_reason: str
    pnl_pips: float
    r: float
    fired: bool
    filled_at_snap: bool


def _bar_hits_tp(bar: Bar, tp: float, direction_sign: int) -> bool:
    """Long: bar.high >= tp. Short: bar.low <= tp. Mirrors
    replay._bar_hits_tp — see there for the bar convention."""
    if direction_sign == +1:
        return bar.high >= tp
    return bar.low <= tp


def rescore_trade(trade: TradeRecord, new_tp: float) -> AltOutcome:
    """Apply PROTOCOL §4.2 fill decision and return the alt outcome.

    Scan window: the full ``trade.path`` (i.e. M5 sub-bars over
    ``[entry_time, exit_time + trade_tf_duration)`` per the PRE-0
    exporter). See the module docstring "Scan-window design note" for
    why this differs from a strict ``bar.time < exit_time`` filter.

    Bar 0 counts by construction — path[0] is the M5 sub-bar starting
    at ``entry_time``. Same-bar TP trades (which are ~33 % of EURUSD
    winners under the deployed cell) get the M5-resolution fill scan
    they need to fire the snap.

    Because the snap is direction-inward (§3.2), ``new_tp`` is strictly
    between entry and the original TP — so any bar that would hit the
    original TP has already crossed ``new_tp``. The alt fill therefore
    fires at or before the original TP timestamp on winning trades.
    For SL-hit trades, the alt fires only if the intra-trade favourable
    excursion touched ``new_tp``; else we fall back to the original SL.
    """
    direction_sign = +1 if trade.direction == "long" else -1
    entry = trade.entry
    tp = trade.take_profit
    stop_pips = trade.stop_pips
    original_exit_time = trade.exit_time

    fired = (new_tp != tp)

    # Null-rule fast path — snap did not fire, alt outcome = baseline.
    if not fired:
        return AltOutcome(
            exit_time=original_exit_time,
            exit_price=trade.exit_price,
            exit_reason=trade.exit_reason,
            pnl_pips=trade.pnl_pips,
            r=trade.r,
            fired=False,
            filled_at_snap=False,
        )

    # Scan the full intra-trade path (PROTOCOL §4.2 "inclusive on M5 path
    # bars"). See module docstring "Scan-window design note" for the
    # rationale — the naive ``bar.time < exit_time`` form drops
    # same-bar-TP trades and diff-bar-TP trades where exit_time is the
    # H4 bar START.
    for bar in trade.path:
        if _bar_hits_tp(bar, new_tp, direction_sign):
            pnl_pips = direction_sign * (new_tp - entry) / PIP
            r = pnl_pips / stop_pips if stop_pips > 0 else 0.0
            return AltOutcome(
                exit_time=bar.time,
                exit_price=new_tp,
                exit_reason=SNAP_EXIT_REASON,
                pnl_pips=round(pnl_pips, 4),
                r=round(r, 4),
                fired=True,
                filled_at_snap=True,
            )

    # Path exhausted without ``new_tp`` firing — fall back to the ORIGINAL
    # exit (baseline identity; no synthetic fill invented).
    return AltOutcome(
        exit_time=original_exit_time,
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        pnl_pips=trade.pnl_pips,
        r=trade.r,
        fired=True,
        filled_at_snap=False,
    )


__all__ = [
    "snap_tp",
    "rescore_trade",
    "AltOutcome",
    "SNAP_EXIT_REASON",
]
