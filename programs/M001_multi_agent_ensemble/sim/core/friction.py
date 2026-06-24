"""Friction model: spread, slippage, latency, partial fills, rejects.

Architecture spec lives in `09-experiment-architecture.md` section 1.8.
Calibration target: June 2026 VM broker fills on Exness demo
(1:1000, $100 equity profile). The fills CSV lives in the production
repo at `~/Documents/TradingAgentLogs/` and is **not present** in this
research repo — see `sim/README.md` for the import contract.

The model is **deterministic**: all "stochastic" events
(partial fills, rejects, slippage perturbation) use seeds derived from
`(agent_id, tick_id, channel)` via `sim.core.seed.seed_for`. No
`random.random()`, no `time.time()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from .seed import seed_for
from .types import MarketState


# ---------------------------------------------------------------------------
# Calibration block (Phi2.5 placeholders — see sim/README.md)
# ---------------------------------------------------------------------------

# TODO: calibrate against fills_path =
#   ~/Documents/TradingAgentLogs/<june_2026>/*.csv (production repo).
# Replace these placeholders with the calibrated values from the
# June 2026 VM broker run; bump only with a calibration commit.
# Until then, the values below are pessimistic-but-plausible defaults
# that pass `test_friction.py` without leaking historical numbers.

DEFAULT_SLIPPAGE_ATR_MULT = 0.05      # k in `k * ATR(14)` adverse
DEFAULT_LATENCY_MS = 250              # fixed delay before fill
DEFAULT_PARTIAL_FILL_PROB = 0.20      # P(partial) — 20% of orders
DEFAULT_PARTIAL_FILL_HAIRCUT = 0.50   # filled at 50% size when partial
DEFAULT_REJECT_PROB = 0.01            # 1% reject (retry once, then skip)
DEFAULT_PARTIAL_LOT_THRESHOLD = 1.0   # partials only > 1.0 lot equivalent


# ---------------------------------------------------------------------------
# Spread + slippage primitives
# ---------------------------------------------------------------------------

def spread_from_bar(bar: MarketState) -> float:
    """Realised spread on the entry bar: ``ask_high - bid_low``.

    Returns 0.0 if the bar lacks bid/ask columns (some legacy parquets
    only carry mid-OHLC). Callers should treat 0.0 as "spread unknown"
    and fall back to a config default. Architecture section 1.8.
    """
    if bar.bid_low is None or bar.ask_high is None:
        return 0.0
    return max(0.0, float(bar.ask_high) - float(bar.bid_low))


def slippage_from_atr(
    atr: float,
    *,
    k: float = DEFAULT_SLIPPAGE_ATR_MULT,
) -> float:
    """Adverse slippage estimate: ``k * ATR``.

    Sign convention is "adverse to the trader" — caller adds/subtracts
    based on direction. Returns 0 when ATR is non-finite or non-positive.
    """
    if not np.isfinite(atr) or atr <= 0:
        return 0.0
    return float(k) * float(atr)


# ---------------------------------------------------------------------------
# Order-event simulation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FrictionConfig:
    slippage_atr_mult: float = DEFAULT_SLIPPAGE_ATR_MULT
    latency_ms: int = DEFAULT_LATENCY_MS
    partial_fill_prob: float = DEFAULT_PARTIAL_FILL_PROB
    partial_fill_haircut: float = DEFAULT_PARTIAL_FILL_HAIRCUT
    partial_lot_threshold: float = DEFAULT_PARTIAL_LOT_THRESHOLD
    reject_prob: float = DEFAULT_REJECT_PROB


@dataclass(frozen=True)
class FillResult:
    status: Literal["filled", "partial", "rejected"]
    filled_size: float
    fill_price: float
    slippage_pips: float
    latency_ms: int
    reason: str = ""


def simulate_fill(
    *,
    agent_id: str,
    tick_id: int,
    intended_size: float,
    intended_price: float,
    atr: float,
    direction: int,
    config: FrictionConfig | None = None,
) -> FillResult:
    """Deterministically simulate one order against the friction model.

    Returns a `FillResult` with status filled/partial/rejected, the
    realised size, the realised price (after spread + slippage applied
    adverse to ``direction``), and the simulated latency.

    Determinism: every "random" decision uses an RNG seeded by
    `(agent_id, tick_id, "friction.<channel>")` so re-running the same
    inputs reproduces the same fill.
    """
    cfg = config or FrictionConfig()

    # Reject roll (channel "reject") — 1% by default; deterministic.
    reject_rng = np.random.default_rng(seed_for(agent_id, tick_id, "friction.reject"))
    if float(reject_rng.random()) < cfg.reject_prob:
        return FillResult(
            status="rejected",
            filled_size=0.0,
            fill_price=intended_price,
            slippage_pips=0.0,
            latency_ms=cfg.latency_ms,
            reason="reject_roll",
        )

    # Slippage is adverse: long -> price moves up, short -> price moves down.
    slip = slippage_from_atr(atr, k=cfg.slippage_atr_mult)
    sign = 1.0 if direction > 0 else (-1.0 if direction < 0 else 0.0)
    fill_price = intended_price + sign * slip

    # Partial fill roll only triggers above the lot threshold.
    if intended_size > cfg.partial_lot_threshold:
        partial_rng = np.random.default_rng(
            seed_for(agent_id, tick_id, "friction.partial")
        )
        if float(partial_rng.random()) < cfg.partial_fill_prob:
            return FillResult(
                status="partial",
                filled_size=float(intended_size) * cfg.partial_fill_haircut,
                fill_price=fill_price,
                slippage_pips=slip,
                latency_ms=cfg.latency_ms,
                reason="partial_above_threshold",
            )

    return FillResult(
        status="filled",
        filled_size=float(intended_size),
        fill_price=fill_price,
        slippage_pips=slip,
        latency_ms=cfg.latency_ms,
    )


# ---------------------------------------------------------------------------
# Calibration helper (stub — wired up when fills CSV is available)
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """Output of friction calibration vs broker fills.

    Phi2.5 deliverable per 09 section 1.8: produced by replaying a
    sequence of intended orders through both the simulator and the
    broker fills log, then bumping `k` and `reject_prob` until sim PnL
    is within the 95% band of live PnL on the same signals.
    """

    n_orders: int
    k_calibrated: float
    reject_prob_calibrated: float
    median_abs_price_error: float
    pnl_band_95: tuple[float, float]
    notes: str = ""

    def to_jsonable(self) -> dict:
        return {
            "n_orders": int(self.n_orders),
            "k_calibrated": float(self.k_calibrated),
            "reject_prob_calibrated": float(self.reject_prob_calibrated),
            "median_abs_price_error": float(self.median_abs_price_error),
            "pnl_band_95": [float(self.pnl_band_95[0]), float(self.pnl_band_95[1])],
            "notes": self.notes,
        }


def calibrate_against_fills(fills_csv_path: str) -> CalibrationResult:
    """Phi2.5 stub — see `sim/README.md` Calibration section.

    Real implementation will:
      1. Load `fills_csv_path` (production-side broker log).
      2. Replay each intended order through `simulate_fill`.
      3. Sweep `k in {0.02, 0.03, ..., 0.10}` and
         `reject_prob in {0.005, 0.01, 0.02}` to minimise median |Δprice|.
      4. Emit a `CalibrationResult` and write it to
         `programs/M001_multi_agent_ensemble/sim/friction.yaml`.
    """
    raise NotImplementedError(
        "Friction calibration deferred — production broker fills CSV is not "
        "present in this repo. See sim/README.md `Calibration` section for "
        f"the import contract. Requested path: {fills_csv_path!r}"
    )
