"""F19 -- Agent-owned lot-size cognition.

Doctrine 06 v0.5 section 4.1a. Each v1 agent implements a non-trivial
`lot_intent(conviction, sl_pips, equity, regime_fit) -> lot_size`. Sizing
is part of the "beautiful goal" equation (TP + SL + smoothness + speed +
size), not a global constant.

## The three shipped implementations

- ``default_lot_intent``: returns ``FIXED_LOT = 0.1``. Used only by
  agents that pre-date F19 or in the G7 dry-run baseline. Any agent
  still using this after G7 fires FAILS §3.11.5 criterion #5.
- ``conviction_scaled_lot_intent``: lot linearly scales with conviction.
  Baseline for Isagi (conservative-metavision) and Nagi (confluence-only).
- ``playstyle_lot_intent``: table-lookup on ``playstyle`` + per-agent
  parameter overrides. Isagi/Nagi/Barou etc. call this with their
  own playstyle constants.

## Sentinel interaction

R1 (min-lot floor, 5 % equity risk cap) and R6 (per-symbol total-risk
cap) apply AFTER `lot_intent` returns. `lot_intent` is the first line
of risk decision; Sentinel is the last line. See doctrine §4.3 +
`sim/core/sentinel.py`.

## Sandbox constants ($100 / 1:1000 demo per doctrine §6)

- ``FIXED_LOT = 0.1`` — 10× the broker min-lot (0.01).
- ``MIN_LOT = 0.01`` — broker minimum for MT5 forex.
- ``PIP_VALUE_PER_MIN_LOT = 0.10`` — dollars per pip at 0.01 lot for
  USD-quoted majors (EURUSD / GBPUSD).

All implementations here return lots in units of 0.01 (min-lot
multiples). Callers should round DOWN to `MIN_LOT` before submission
per Sentinel R2 (discrete sizing rule).
"""
from __future__ import annotations

from typing import Callable, Literal

# Sandbox pitch constants (doctrine §6). These are the CONSTRAINT the
# sim harness enforces; agent-side cognition operates below them.
FIXED_LOT = 0.1
MIN_LOT = 0.01
PIP_VALUE_PER_MIN_LOT = 0.10        # USD/pip at 0.01 lot for USD-quoted majors.

# Named playstyles referenced by the roster (doctrine §4.1a playstyle
# mapping). Kept as string literals rather than an enum to keep the
# public surface JSON-serialisable for roster.yaml.
Playstyle = Literal[
    "conservative_metavision",     # A1 Isagi
    "rebel_tight",                 # A2 Bachira
    "analytical_precision",        # A3 Rin
    "speed_momentum",              # A4 Chigiri
    "copier_hrp",                  # A5 Reo
    "confluence_only",             # A6 Nagi
    "solo_king",                   # A7 Barou
    "defensive",                   # A10 Kunigami
]


LotIntent = Callable[[float, float, float, float], float]
"""F19 callable signature: (conviction, sl_pips, equity, regime_fit) -> lot."""


# ---------------------------------------------------------------------------
# Default (fixed-lot) -- v1 checkpoint FALLBACK, not a valid v1 implementation
# ---------------------------------------------------------------------------

def default_lot_intent(
    conviction: float,           # noqa: ARG001 -- interface signature
    sl_pips: float,              # noqa: ARG001
    equity: float,               # noqa: ARG001
    regime_fit: float,           # noqa: ARG001
) -> float:
    """Returns FIXED_LOT unconditionally.

    Present for backwards compatibility. Any agent still using this
    after G7 fires FAILS §3.11.5 criterion #5 (owned lot-size
    cognition, CV >= 0.10).
    """
    return FIXED_LOT


# ---------------------------------------------------------------------------
# Shared building block: conviction-scaled lot
# ---------------------------------------------------------------------------

def conviction_scaled_lot_intent(
    conviction: float,
    sl_pips: float,
    equity: float,
    regime_fit: float,
    *,
    base_lot: float = FIXED_LOT,
    min_lot_floor: float = MIN_LOT,
    max_lot_ceiling: float = 0.30,
    conviction_pivot: float = 0.60,
    conviction_gain: float = 2.0,
    regime_fit_gain: float = 0.5,
) -> float:
    """Lot linearly scales with (conviction - pivot) and regime_fit.

    ``base_lot`` is the neutral position at ``conviction == pivot`` and
    ``regime_fit == 0.5``. Above pivot, lot scales up by
    ``conviction_gain × (conviction - pivot)``; below, it scales down
    symmetrically. Regime fit adds an independent multiplier.

    Formula::

        raw = base_lot
              × (1 + conviction_gain × (conviction - conviction_pivot))
              × (1 + regime_fit_gain × (regime_fit - 0.5))
        rounded = round_down_to_min_lot(clip(raw, min_lot_floor, max_lot_ceiling))

    The ceiling is intentionally below Sentinel R4's 40 % concentration
    cap so that a single agent's high-conviction call can never itself
    breach R4 -- concentration limits fire only when multiple agents
    stack on the same tick.

    Sandbox default under $100 / 1:1000: pivot 0.60, conviction gain 2.0
    means a conviction of 0.85 doubles the lot (~0.2), and a conviction
    of 0.35 halves it (~0.05). ``sl_pips`` is not used in this simple
    scaling (see ``kelly_lot_intent`` for the SL-aware variant).
    """
    conviction = _clip01(conviction)
    regime_fit = _clip01(regime_fit)
    raw = base_lot * (
        1.0 + conviction_gain * (conviction - conviction_pivot)
    ) * (1.0 + regime_fit_gain * (regime_fit - 0.5))
    clipped = max(min_lot_floor, min(max_lot_ceiling, raw))
    return _round_down_to_min_lot(clipped, min_lot_floor)


# ---------------------------------------------------------------------------
# Shared building block: Kelly-fraction-aware lot (SL-aware)
# ---------------------------------------------------------------------------

def kelly_lot_intent(
    conviction: float,
    sl_pips: float,
    equity: float,
    regime_fit: float,
    *,
    kelly_fraction_cap: float = 0.02,
    win_prob_from_conviction_slope: float = 0.30,
    payoff_ratio: float = 1.5,
    min_lot_floor: float = MIN_LOT,
    max_lot_ceiling: float = 0.30,
    pip_value_per_min_lot: float = PIP_VALUE_PER_MIN_LOT,
) -> float:
    """Kelly-fraction sizing tied to conviction, SL distance, and equity.

    Converts conviction into a win probability, applies fractional Kelly
    capped at 2 % of equity (a conservative Kelly-fifth), and translates
    the risk into lots given the SL distance in pips.

    win_prob = 0.50 + slope × (conviction - 0.50)
    kelly_fraction = min(kelly_fraction_cap,
                         win_prob - (1 - win_prob) / payoff_ratio)
    dollar_risk = kelly_fraction × equity × (0.5 + regime_fit × 0.5)
    lot_units_of_min_lot = dollar_risk / (sl_pips × pip_value_per_min_lot)

    Regime fit is applied as a 0.5-to-1.0 multiplier on the dollar risk
    (so poor regime fit halves risk; perfect fit uses full Kelly).

    Guard: ``sl_pips <= 0`` returns ``min_lot_floor`` (defensive).
    """
    conviction = _clip01(conviction)
    regime_fit = _clip01(regime_fit)
    if sl_pips <= 0 or equity <= 0:
        return min_lot_floor
    win_prob = 0.50 + win_prob_from_conviction_slope * (conviction - 0.50)
    win_prob = _clip01(win_prob)
    kelly = min(
        kelly_fraction_cap,
        max(0.0, win_prob - (1.0 - win_prob) / payoff_ratio),
    )
    regime_scale = 0.5 + 0.5 * regime_fit
    dollar_risk = kelly * equity * regime_scale
    per_min_lot_dollar_risk = sl_pips * pip_value_per_min_lot
    if per_min_lot_dollar_risk <= 0:
        return min_lot_floor
    lot_multiples_of_min = dollar_risk / per_min_lot_dollar_risk
    # Lot = multiples × MIN_LOT; clip to sandbox ceiling and floor.
    lot = lot_multiples_of_min * min_lot_floor
    lot = max(min_lot_floor, min(max_lot_ceiling, lot))
    return _round_down_to_min_lot(lot, min_lot_floor)


# ---------------------------------------------------------------------------
# Playstyle dispatch
# ---------------------------------------------------------------------------

def playstyle_lot_intent(
    conviction: float,
    sl_pips: float,
    equity: float,
    regime_fit: float,
    *,
    playstyle: Playstyle,
) -> float:
    """Table-lookup on ``playstyle`` -> shared building block.

    Per doctrine §4.1a playstyle mapping. Each playstyle chooses one
    of the shared building blocks with playstyle-specific parameters.
    Locked at v0.5; any parameter change is a §11 amendment.

    Runtime dispatch is intentional -- keeps roster.yaml the source of
    truth for playstyle assignment. Agents may override this method
    entirely with weapon-specific logic.
    """
    if playstyle == "conservative_metavision":
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=FIXED_LOT, conviction_pivot=0.60, conviction_gain=1.5,
            max_lot_ceiling=0.20,
        )
    if playstyle == "rebel_tight":
        # Bachira: SMALL lot when rebel-lift gate blocked (peer-silence
        # failure). Callers pass conviction reduced-by-gate-decision;
        # this fn just implements the scaling.
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=0.05, conviction_pivot=0.65, conviction_gain=2.5,
            max_lot_ceiling=0.15, regime_fit_gain=0.3,
        )
    if playstyle == "analytical_precision":
        # Rin: larger lot on peer-disagreement (callers pass conviction
        # elevated by the gate).
        return kelly_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            kelly_fraction_cap=0.025, payoff_ratio=2.0,
        )
    if playstyle == "speed_momentum":
        # Chigiri: larger lot on multi-TF ADX confluence.
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=FIXED_LOT, conviction_pivot=0.55, conviction_gain=2.5,
            max_lot_ceiling=0.25, regime_fit_gain=0.8,
        )
    if playstyle == "copier_hrp":
        # Reo: HRP-mixture computed OUTSIDE this fn; Reo's own
        # `lot_intent` on the agent class computes the mixture and
        # calls this fn with the pre-mixed conviction.
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=FIXED_LOT, conviction_pivot=0.55, conviction_gain=1.5,
            max_lot_ceiling=0.15,
        )
    if playstyle == "confluence_only":
        # Nagi: larger lot on 2+ peer overlap, else refuses. Refusal is
        # handled by returning 0.0 in the agent class before this fn
        # is called; when called here, the conviction is already
        # confluence-lifted.
        return kelly_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            kelly_fraction_cap=0.025, payoff_ratio=1.5,
        )
    if playstyle == "solo_king":
        # Barou: standard lot on all trades; single-symbol devour lift.
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=FIXED_LOT, conviction_pivot=0.55, conviction_gain=1.0,
            max_lot_ceiling=0.18, regime_fit_gain=0.4,
        )
    if playstyle == "defensive":
        # Kunigami: 0.5× lot when warning_active_at fires. The 0.5x is
        # applied by the agent class BEFORE calling this fn; here we
        # just do the standard conviction scaling.
        return conviction_scaled_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            base_lot=FIXED_LOT, conviction_pivot=0.55, conviction_gain=1.0,
            max_lot_ceiling=0.15, regime_fit_gain=0.5,
        )
    # Unknown playstyle -> falls back to default (fixed lot). Not a
    # ValueError -- the doctrine says agents may override entirely, so
    # unknown values here are a signal the roster is asking for a
    # weapon-specific implementation.
    return default_lot_intent(conviction, sl_pips, equity, regime_fit)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _round_down_to_min_lot(lot: float, min_lot: float) -> float:
    """Sentinel R2 discrete-sizing rule: round DOWN to min_lot multiples."""
    if lot <= 0:
        return 0.0
    n_units = int(lot / min_lot)
    return n_units * min_lot


__all__ = [
    "FIXED_LOT",
    "MIN_LOT",
    "PIP_VALUE_PER_MIN_LOT",
    "Playstyle",
    "LotIntent",
    "default_lot_intent",
    "conviction_scaled_lot_intent",
    "kelly_lot_intent",
    "playstyle_lot_intent",
]
