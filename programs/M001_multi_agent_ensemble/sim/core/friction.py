"""Friction model: spread, slippage, latency, partial fills, rejects.

Architecture spec lives in `09-experiment-architecture.md` section 1.8.
Calibration target: June 2026 VM broker fills on Exness demo
(1:1000, $100 equity profile). The fills source lives in the production
repo at `~/Documents/TradingAgentLogs/{SYMBOL}/` and may or may not be
present on the current host — see `sim/README.md` for the import contract.

The model is **deterministic**: all "stochastic" events
(partial fills, rejects, slippage perturbation) use seeds derived from
`(agent_id, tick_id, channel)` via `sim.core.seed.seed_for`. No
`random.random()`, no `time.time()`.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

import numpy as np

from .seed import seed_for
from .types import MarketState

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Calibration block (Phi2.5 placeholders — see sim/README.md)
# ---------------------------------------------------------------------------

# TODO: calibrate against fills_path =
#   ~/Documents/TradingAgentLogs/{SYMBOL}/ (production repo).
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

DEFAULT_CALIBRATION_PATH = (
    Path(__file__).resolve().parent / "friction_calibration_2026-06.json"
)
DEFAULT_LIVE_LOG_ROOT = Path.home() / "Documents" / "TradingAgentLogs"


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
# Calibration — parser + estimator for June 2026 VM broker fills
# ---------------------------------------------------------------------------
#
# Cross-repo data contract (production: `multi-pair-trading-agent`):
#
#   ~/Documents/TradingAgentLogs/
#     {SYMBOL}/
#       {SYMBOL}_YYYY-MM-DD.log        # text log; bracketed events
#       near_misses/events.jsonl       # one JSON event per line
#       losses/events.jsonl            # one JSON event per line
#       ladders/events.jsonl           # one JSON event per line
#
# The text log carries [SIGNAL], [TRADE OPENED], [ORDER REJECTED],
# [PARTIAL TP], [TP HIT], [SOFT SL], [CATASTROPHE SL] lines emitted by
# `agent/live/trade_events.py` (production). The JSONL vaults carry
# structured per-event records. Per-fill spread/slippage/latency are
# reconstructed by pairing a [SIGNAL] (intended_price + ts) with the
# next matching [TRADE OPENED] (fill_price + ts) on the same alpha+TF.
#
# On hosts where ~/Documents/TradingAgentLogs/{SYMBOL}/ is empty (this
# Mac research host as of 2026-06-24 — only the daily-summary text
# file exists), `calibrate_against_fills` returns an empty
# CalibrationResult with `n_orders == 0` and the friction model falls
# back to conservative defaults.

# Regex contracts for the production text-log event lines. Each one
# pulls only the fields the calibration estimator needs; unknown
# fields are tolerated. Kept verbose so a `grep -E` on the source
# rebuilds the same set in shell.
_RE_SIGNAL = re.compile(
    r"\[SIGNAL\]\s+(?P<symbol>\S+)\s+(?P<tf>\S+)\s+(?P<alpha>\S+)\s+"
    r"(?P<direction>LONG|SHORT)\s+entry=(?P<entry>[0-9.]+)"
)
_RE_TRADE_OPENED = re.compile(
    r"\[TRADE OPENED\]\s+(?P<symbol>\S+)\s+(?P<tf>\S+)\s+(?P<alpha>\S+)\s+"
    r"(?P<direction>LONG|SHORT)\s+ticket=(?P<ticket>\d+)\s+"
    r"entry=(?P<fill_price>[0-9.]+)\s+lots=(?P<lots>[0-9.]+)"
)
_RE_ORDER_REJECTED = re.compile(r"\[ORDER REJECTED\]")
_RE_TIMESTAMP_PREFIX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
)


@dataclass
class CalibrationResult:
    """Output of friction calibration vs broker fills.

    Phi3 deliverable per 09 section 1.8: produced by replaying a
    sequence of intended orders through both the simulator and the
    broker fills log, then estimating empirical spread / slippage /
    latency / partial / reject distributions per symbol.

    Fields are the inputs needed to seed `FrictionConfig` on the next
    sim run. `n_orders == 0` means "no data on this host — defaults
    apply"; callers must check this before treating the values as
    calibrated.
    """

    symbol: str
    n_orders: int
    n_rejections: int
    n_partial_fills: int
    median_spread: float
    p95_spread: float
    slippage_atr_mult: float       # k in `k * ATR`; 0.0 when undefined
    median_latency_ms: float
    p95_latency_ms: float
    partial_fill_rate: float
    rejection_rate: float
    window_start: str = ""
    window_end: str = ""
    source_path: str = ""
    notes: str = ""

    def to_jsonable(self) -> dict:
        return {
            "symbol": str(self.symbol),
            "n_orders": int(self.n_orders),
            "n_rejections": int(self.n_rejections),
            "n_partial_fills": int(self.n_partial_fills),
            "median_spread": float(self.median_spread),
            "p95_spread": float(self.p95_spread),
            "slippage_atr_mult": float(self.slippage_atr_mult),
            "median_latency_ms": float(self.median_latency_ms),
            "p95_latency_ms": float(self.p95_latency_ms),
            "partial_fill_rate": float(self.partial_fill_rate),
            "rejection_rate": float(self.rejection_rate),
            "window_start": str(self.window_start),
            "window_end": str(self.window_end),
            "source_path": str(self.source_path),
            "notes": str(self.notes),
        }

    def to_friction_config(self) -> "FrictionConfig":
        """Promote a calibration row to a usable FrictionConfig.

        Falls back to the conservative defaults on any field where the
        calibration could not estimate a value (`n_orders == 0`,
        non-finite, or negative). The simulator never sees a NaN.
        """
        if self.n_orders == 0:
            return FrictionConfig()
        return FrictionConfig(
            slippage_atr_mult=(
                float(self.slippage_atr_mult)
                if np.isfinite(self.slippage_atr_mult)
                and self.slippage_atr_mult > 0
                else DEFAULT_SLIPPAGE_ATR_MULT
            ),
            latency_ms=int(
                self.median_latency_ms
                if np.isfinite(self.median_latency_ms)
                and self.median_latency_ms > 0
                else DEFAULT_LATENCY_MS
            ),
            partial_fill_prob=(
                float(self.partial_fill_rate)
                if np.isfinite(self.partial_fill_rate)
                else DEFAULT_PARTIAL_FILL_PROB
            ),
            reject_prob=(
                float(self.rejection_rate)
                if np.isfinite(self.rejection_rate)
                else DEFAULT_REJECT_PROB
            ),
        )


# ---------------------------------------------------------------------------
# JSONL vault parser (production schema)
# ---------------------------------------------------------------------------

def iter_vault_jsonl(jsonl_path: Path) -> Iterable[dict]:
    """Yield one event dict per non-empty line of a vault `events.jsonl`.

    Tolerates bad lines (logged at DEBUG, never raised) so a single
    corrupt entry does not poison the calibration.
    """
    if not jsonl_path.exists():
        return
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                log.debug("Skipping bad JSONL line in %s: %s", jsonl_path, e)


# ---------------------------------------------------------------------------
# Text-log parser (production schema; pairs SIGNAL -> TRADE OPENED)
# ---------------------------------------------------------------------------

def _parse_ts_prefix(line: str) -> datetime | None:
    m = _RE_TIMESTAMP_PREFIX.match(line)
    if not m:
        return None
    raw = m.group("ts").replace(",", ".").replace(" ", "T")
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass(frozen=True)
class FillRecord:
    """One (signal -> fill) pair reconstructed from a text log."""

    symbol: str
    timeframe: str
    alpha: str
    direction: str
    intended_price: float
    fill_price: float
    lots: float
    signal_ts: datetime | None
    fill_ts: datetime | None

    @property
    def slippage_price(self) -> float:
        """Adverse slippage in price units, sign-aligned to direction.

        Positive value means the broker filled worse than asked. The
        slippage estimator regresses |slippage_price| on ATR so the
        sign does not matter, but the dataclass keeps the signed
        figure for downstream auditing.
        """
        sign = 1.0 if self.direction.upper() == "LONG" else -1.0
        return sign * (self.fill_price - self.intended_price)

    @property
    def latency_ms(self) -> float | None:
        if self.signal_ts is None or self.fill_ts is None:
            return None
        delta = (self.fill_ts - self.signal_ts).total_seconds() * 1000.0
        return float(delta) if delta >= 0 else None


def parse_text_log(log_path: Path) -> tuple[list[FillRecord], int]:
    """Walk a per-day text log; pair [SIGNAL] -> [TRADE OPENED].

    Returns (fills, n_order_rejected). Pairing is by (symbol, timeframe,
    alpha, direction): the first [TRADE OPENED] after a [SIGNAL] with
    matching key consumes that signal. Unmatched signals are dropped
    (the trade was never filled, or the log rolled over).
    """
    if not log_path.exists():
        return [], 0
    pending: dict[tuple, tuple[datetime | None, float]] = {}
    fills: list[FillRecord] = []
    n_rejected = 0
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            ts = _parse_ts_prefix(line)
            if _RE_ORDER_REJECTED.search(line):
                n_rejected += 1
                continue
            sig = _RE_SIGNAL.search(line)
            if sig:
                key = (
                    sig.group("symbol"),
                    sig.group("tf"),
                    sig.group("alpha"),
                    sig.group("direction"),
                )
                pending[key] = (ts, float(sig.group("entry")))
                continue
            opened = _RE_TRADE_OPENED.search(line)
            if opened:
                key = (
                    opened.group("symbol"),
                    opened.group("tf"),
                    opened.group("alpha"),
                    opened.group("direction"),
                )
                paired = pending.pop(key, None)
                if paired is None:
                    continue
                signal_ts, intended = paired
                fills.append(FillRecord(
                    symbol=opened.group("symbol"),
                    timeframe=opened.group("tf"),
                    alpha=opened.group("alpha"),
                    direction=opened.group("direction"),
                    intended_price=intended,
                    fill_price=float(opened.group("fill_price")),
                    lots=float(opened.group("lots")),
                    signal_ts=signal_ts,
                    fill_ts=ts,
                ))
    return fills, n_rejected


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------

def _estimate_k_slippage(
    fills: list[FillRecord],
    atr_by_record: dict[int, float] | None = None,
) -> float:
    """OLS estimate of `slip = k * ATR` from paired fills.

    If `atr_by_record` is omitted (the ATR-at-signal column is not
    yet wired in the live logs), returns 0.0 and the caller must
    keep the default `k`. Phi3 wires the ATR column through the
    log emitter or through a re-derived ATR from parquet at the
    signal timestamp.
    """
    if not fills or atr_by_record is None:
        return 0.0
    slips = []
    atrs = []
    for idx, fill in enumerate(fills):
        atr_val = atr_by_record.get(idx)
        if atr_val is None or atr_val <= 0:
            continue
        slips.append(abs(fill.slippage_price))
        atrs.append(float(atr_val))
    if len(atrs) < 5:  # too few to estimate
        return 0.0
    slips_arr = np.asarray(slips, dtype=float)
    atrs_arr = np.asarray(atrs, dtype=float)
    # No-intercept regression: k = sum(slip*atr) / sum(atr^2)
    denom = float((atrs_arr ** 2).sum())
    if denom <= 0:
        return 0.0
    return float((slips_arr * atrs_arr).sum() / denom)


def calibrate_against_fills(
    symbol: str,
    log_root: Path | str | None = None,
    *,
    atr_by_record: dict[int, float] | None = None,
) -> CalibrationResult:
    """Estimate friction parameters from production broker fills.

    Reads:
      * `{log_root}/{symbol}/{symbol}_*.log` — pairs [SIGNAL] with
        the matching [TRADE OPENED]; counts [ORDER REJECTED] lines.
      * `{log_root}/{symbol}/losses/events.jsonl` — partial-fill /
        haircut accounting (when the vault carries `filled_lots`).

    Returns a `CalibrationResult` with `n_orders == 0` when the path
    is empty (e.g. this Mac research host, where logs live on the VM).
    The caller decides whether to write the result to disk or fall
    back to defaults; `to_friction_config()` always returns a usable
    `FrictionConfig`.

    ATR-aware slippage estimation requires `atr_by_record`, a mapping
    {fill_index -> ATR(14) at signal timestamp}. Without it the
    estimator leaves `slippage_atr_mult = 0.0` and the simulator
    keeps its default `k`.
    """
    root = Path(log_root) if log_root is not None else DEFAULT_LIVE_LOG_ROOT
    sym_dir = root / symbol
    notes = ""
    if not sym_dir.exists():
        notes = (
            f"no logs under {sym_dir} — calibration deferred to Phi3 "
            "when the VM data pipe is wired"
        )
        return CalibrationResult(
            symbol=symbol,
            n_orders=0,
            n_rejections=0,
            n_partial_fills=0,
            median_spread=0.0,
            p95_spread=0.0,
            slippage_atr_mult=0.0,
            median_latency_ms=0.0,
            p95_latency_ms=0.0,
            partial_fill_rate=0.0,
            rejection_rate=0.0,
            source_path=str(sym_dir),
            notes=notes,
        )

    fills: list[FillRecord] = []
    n_rejected_text = 0
    log_files = sorted(sym_dir.glob(f"{symbol}_*.log"))
    for lf in log_files:
        sub_fills, sub_rejected = parse_text_log(lf)
        fills.extend(sub_fills)
        n_rejected_text += sub_rejected

    # Partial-fill count: prefer the structured vault. Falls back to 0
    # when the vault is absent.
    n_partial = 0
    losses_jsonl = sym_dir / "losses" / "events.jsonl"
    for ev in iter_vault_jsonl(losses_jsonl):
        if ev.get("partial_close") or ev.get("partial_scaleout"):
            n_partial += 1

    # Empirical distributions. Spread is reconstructed as
    # |fill - intended| over fills where ATR is unavailable — this is
    # a *proxy* for spread until the log emitter writes ask_high /
    # bid_low at signal time. Document the caveat in the result's notes.
    spread_proxy = np.asarray([abs(f.fill_price - f.intended_price) for f in fills])
    latencies = np.asarray(
        [f.latency_ms for f in fills if f.latency_ms is not None], dtype=float
    )

    n_orders = len(fills)
    median_spread = float(np.median(spread_proxy)) if n_orders else 0.0
    p95_spread = float(np.percentile(spread_proxy, 95)) if n_orders else 0.0
    median_latency = float(np.median(latencies)) if latencies.size else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies.size else 0.0
    k = _estimate_k_slippage(fills, atr_by_record=atr_by_record)
    partial_rate = (n_partial / n_orders) if n_orders else 0.0
    total_attempts = n_orders + n_rejected_text
    reject_rate = (n_rejected_text / total_attempts) if total_attempts else 0.0

    if atr_by_record is None and n_orders:
        notes = (
            "slippage_atr_mult left at 0 — ATR-at-signal not yet "
            "available from the text log; pass atr_by_record to "
            "calibrate_against_fills() once Phi3 wires the parquet join"
        )

    win_start = ""
    win_end = ""
    ts_list = [f.signal_ts for f in fills if f.signal_ts is not None]
    if ts_list:
        win_start = min(ts_list).isoformat()
        win_end = max(ts_list).isoformat()

    return CalibrationResult(
        symbol=symbol,
        n_orders=n_orders,
        n_rejections=int(n_rejected_text),
        n_partial_fills=int(n_partial),
        median_spread=median_spread,
        p95_spread=p95_spread,
        slippage_atr_mult=k,
        median_latency_ms=median_latency,
        p95_latency_ms=p95_latency,
        partial_fill_rate=partial_rate,
        rejection_rate=reject_rate,
        window_start=win_start,
        window_end=win_end,
        source_path=str(sym_dir),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Calibration file loader (FrictionConfig from JSON)
# ---------------------------------------------------------------------------

def load_calibration(
    path: Path | str | None = None,
) -> dict[str, FrictionConfig]:
    """Load per-symbol `FrictionConfig` from the calibration JSON.

    File layout (Phi3, see `friction_calibration_2026-06.json`):

        {
          "version": 1,
          "generated_at_utc": "...",
          "calibrations": {
            "EURUSD": {<CalibrationResult.to_jsonable()>},
            "GBPUSD": {...},
            "USDCAD": {...}
          }
        }

    Returns `{}` if the file does not exist (callers fall back to
    `FrictionConfig()` defaults). Returns a flat
    `{symbol: FrictionConfig}` map otherwise. Bad entries
    (e.g. `n_orders == 0` or missing fields) silently fall back to
    defaults for that symbol so a partial calibration never breaks
    a sim run.
    """
    p = Path(path) if path is not None else DEFAULT_CALIBRATION_PATH
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Friction calibration unreadable at %s: %s", p, e)
        return {}
    out: dict[str, FrictionConfig] = {}
    for sym, entry in (payload.get("calibrations") or {}).items():
        try:
            result = CalibrationResult(
                symbol=str(sym),
                n_orders=int(entry.get("n_orders", 0)),
                n_rejections=int(entry.get("n_rejections", 0)),
                n_partial_fills=int(entry.get("n_partial_fills", 0)),
                median_spread=float(entry.get("median_spread", 0.0)),
                p95_spread=float(entry.get("p95_spread", 0.0)),
                slippage_atr_mult=float(entry.get("slippage_atr_mult", 0.0)),
                median_latency_ms=float(entry.get("median_latency_ms", 0.0)),
                p95_latency_ms=float(entry.get("p95_latency_ms", 0.0)),
                partial_fill_rate=float(entry.get("partial_fill_rate", 0.0)),
                rejection_rate=float(entry.get("rejection_rate", 0.0)),
                window_start=str(entry.get("window_start", "")),
                window_end=str(entry.get("window_end", "")),
                source_path=str(entry.get("source_path", "")),
                notes=str(entry.get("notes", "")),
            )
        except (TypeError, ValueError) as e:
            log.warning("Friction calibration entry for %s ignored: %s", sym, e)
            continue
        out[str(sym)] = result.to_friction_config()
    return out


def config_for_symbol(
    symbol: str,
    *,
    calibration_path: Path | str | None = None,
) -> FrictionConfig:
    """Convenience: return the calibrated FrictionConfig for `symbol`.

    Falls back to `FrictionConfig()` defaults when the calibration
    file is absent OR the symbol is missing from it. Engine wires
    this on a per-symbol basis at run start so a single missing
    calibration entry never breaks the run.
    """
    cal = load_calibration(calibration_path)
    return cal.get(symbol, FrictionConfig())


def write_calibration_file(
    results: dict[str, CalibrationResult],
    path: Path | str | None = None,
    *,
    extra_metadata: dict | None = None,
) -> Path:
    """Serialise per-symbol calibrations to the canonical JSON file.

    The file is the single source of truth for friction values on
    every sim run — bump only with a calibration commit per
    `09-experiment-architecture.md` §6 amendment policy. Returns
    the resolved path.
    """
    p = Path(path) if path is not None else DEFAULT_CALIBRATION_PATH
    payload = {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "calibrations": {
            sym: result.to_jsonable() for sym, result in results.items()
        },
    }
    if extra_metadata:
        payload["metadata"] = dict(extra_metadata)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return p
