"""E022 level detector — reconstruction of the four snap-source level sets.

PROTOCOL:
  experiments/E022_structure_aware_tp_snap/PROTOCOL.md §3.3, §3.4, §4.2.

This module reconstructs, per trade, the level set ``L(snap_source)`` used
by the E022 TP-snap rule (``rescorer.snap_tp``). It is deterministic and
enforces the no-look-ahead invariant by only ever consuming H4 bars
strictly before the trade's ``entry_time`` (§3.4 mutation-test contract).

Sources (PROTOCOL §3.3):

* ``daily_only`` — six anchor levels: previous-day high (PDH), low (PDL),
  midpoint (PDM = (PDH+PDL)/2), previous-week high (PWH), low (PWL),
  midpoint (PWM). Session boundary is **UTC** (PROTOCOL §3.3, §4.2). D1
  and W1 buckets are aggregated directly from H4 bars ending strictly
  before ``entry_time``.

* ``ladder_top`` — the single nearest-to-entry rung of a reconstructed
  extension ladder over ``[entry_time − 200·H4, entry_time)`` using the
  same detectors that back ``agent/journal/target_ladder.py`` —
  ``swings``, ``zones``, ``trendlines``, ``fib_ext``, ``daily_levels``.
  This module DOES NOT import ``compute_target_ladder`` (the production
  helper filters rungs strictly *beyond* TP, which is the opposite of
  what E022 needs); it mirrors the assembly logic with the E022 filter
  ("levels strictly between entry and TP", PROTOCOL §3.2).

* ``round_number`` — every ``.00`` and ``.50`` sub-figure (4-decimal FX,
  step 0.0050) between ``min(entry, tp)`` and ``max(entry, tp)``.

* ``all`` — union of the three sets, deduped within 3.0 pips
  (nearest-to-entry survives).

The production module ``agent/journal/target_ladder.py`` is treated as a
**READ-ONLY reference**: none of its functions are imported. The individual
detector helpers under ``agent/detectors/*`` and ``agent/rules/engine.py``
are imported as-is and applied to the pre-entry slice.

Locked parameters (PROTOCOL §4.2):

* ``lookback = 200`` H4 bars (window: ``[entry_time − 200·H4, entry_time)``)
* ``trendline_lookahead = 20`` H4 bars
* ``dedupe_pips = 3.0`` (mirrors production ``compute_target_ladder``)
* ``max_rungs = 6`` (mirrors production)
* ``PIP = 0.0001`` (4-decimal FX: EURUSD, GBPUSD, USDCAD)
* ``fib extensions = (1.272, 1.618)`` (mirrors production
  ``target_ladder.FIB_EXTENSIONS``)

Data source (PROTOCOL §5.1, MANIFEST). H4 bars come from the trading-agent
parquet cache
(``multi-pair-trading-agent/data/parquet/{SYMBOL}_H4.parquet``) via
``agent.data.loader.BarLoader``. This is the same source ``E013`` /
``PRE-0`` use, so bar timestamps align with the PRE-0 ledger's
``entry_time`` field to the H4 grid.
"""
from __future__ import annotations

import logging
import math
from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

# ---------------------------------------------------------------------------
# Imports from the trading-agent perception stack (read-only use).
#
# We treat ``agent/journal/target_ladder.py`` as READ-ONLY: none of its
# functions are imported. We DO import individual detector helpers and the
# ``precompute`` orchestrator so the level reconstruction shares the
# production semantics exactly on swings / zones / trendlines / daily levels.
# ---------------------------------------------------------------------------

from agent.config import Config, load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.detectors.fib import auto_fib  # noqa: E402
from agent.rules.engine import PrecomputedContext, precompute  # noqa: E402
from agent.types import Bar, Direction, Timeframe  # noqa: E402

log = logging.getLogger("E022.level_detector")


# ---------------------------------------------------------------------------
# Constants — LOCKED per PROTOCOL §4.2.
# ---------------------------------------------------------------------------

PIP: float = 0.0001

LOOKBACK: int = 200
TRENDLINE_LOOKAHEAD: int = 20
DEDUPE_PIPS: float = 3.0
MAX_RUNGS: int = 6
FIB_EXTENSIONS: tuple[float, ...] = (1.272, 1.618)

ROUND_STEP: float = 0.0050  # every ``.00`` and ``.50`` sub-figure

SUPPORTED_SNAP_SOURCES: tuple[str, ...] = (
    "daily_only",
    "ladder_top",
    "round_number",
    "all",
)


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LevelCandidate:
    """One reconstructed level with provenance (for diagnostics / logs)."""

    price: float
    source: str  # "PDH" / "PDL" / ... / "swing" / "zone_edge" / "trendline" / "fib_ext" / "daily_level" / "round_number"
    detail: str = ""


@dataclass
class SymbolCache:
    """Full-history H4 bar series + a ``bar.time → index`` lookup."""

    symbol: str
    bars: list[Bar]
    times: list[datetime]  # cached bar times for bisect
    tf: str = "H4"

    def index_before(self, ts: datetime) -> int:
        """Return the largest bar index i with ``bars[i].time < ts``. Returns
        -1 if no such bar exists."""
        i = bisect_left(self.times, ts) - 1
        return i


# Module-level cache: symbol → SymbolCache. Populated lazily by callers.
_SYMBOL_CACHES: dict[str, SymbolCache] = {}


def load_symbol_cache(
    symbol: str,
    tf: str = "H4",
    start: datetime = datetime(2014, 1, 1, tzinfo=timezone.utc),
    end: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
    cfg: Optional[Config] = None,
) -> SymbolCache:
    """Load and cache the full ``symbol`` H4 series from the trading-agent
    parquet cache. Idempotent (per-process)."""
    key = f"{symbol}_{tf}"
    if key in _SYMBOL_CACHES:
        return _SYMBOL_CACHES[key]

    if cfg is None:
        cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    df = loader.get(symbol, Timeframe(tf), start, end, refresh=False)
    bars = df_to_bars(df, Timeframe(tf))
    times = [b.time for b in bars]
    cache = SymbolCache(symbol=symbol, bars=bars, times=times, tf=tf)
    _SYMBOL_CACHES[key] = cache
    log.info(
        "load_symbol_cache: %s %s → %d bars %s..%s",
        symbol, tf, len(bars),
        times[0].date().isoformat() if times else "?",
        times[-1].date().isoformat() if times else "?",
    )
    return cache


# ---------------------------------------------------------------------------
# UTC-bucketed previous-day / previous-week aggregation.
#
# PROTOCOL §3.3, §4.2: "Session boundary: UTC" — this deliberately
# overrides the NY-date bucketing used by
# ``agent.detectors.daily_levels.compute_daily_levels`` (which the E022
# pre-registration flags as a deliberate simplification, not a bug — the
# production module is a read-only reference for the D1 SOURCE, not for
# the boundary choice).
# ---------------------------------------------------------------------------

def _utc_date(ts: datetime) -> date:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).date()


def _iso_week(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return (iso[0], iso[1])


@dataclass
class _DailyAnchors:
    pdh: Optional[float] = None
    pdl: Optional[float] = None
    pdm: Optional[float] = None
    pwh: Optional[float] = None
    pwl: Optional[float] = None
    pwm: Optional[float] = None

    def to_candidates(self) -> list[LevelCandidate]:
        pairs = [
            ("PDH", self.pdh),
            ("PDL", self.pdl),
            ("PDM", self.pdm),
            ("PWH", self.pwh),
            ("PWL", self.pwl),
            ("PWM", self.pwm),
        ]
        return [
            LevelCandidate(price=float(p), source="daily_level", detail=name)
            for name, p in pairs
            if p is not None
        ]


def _compute_utc_daily_anchors(pre_bars: Sequence[Bar]) -> _DailyAnchors:
    """Aggregate PDH / PDL / PDM / PWH / PWL / PWM from bars *strictly before*
    the trade's ``entry_time``.

    ``pre_bars`` MUST be the slice ``[entry_time − 200·H4, entry_time)``
    (or any subset up to but not including the entry bar). Bucketing is by
    UTC calendar date / ISO week (PROTOCOL §3.3). Returns ``None`` for
    fields that have no prior data.
    """
    if not pre_bars:
        return _DailyAnchors()

    entry_ts = pre_bars[-1].time + timedelta(hours=4)  # first H4 bar at/after entry
    entry_day = _utc_date(entry_ts)
    entry_week = _iso_week(entry_day)

    daily_hi: dict[date, float] = {}
    daily_lo: dict[date, float] = {}
    weekly_hi: dict[tuple[int, int], float] = {}
    weekly_lo: dict[tuple[int, int], float] = {}

    for b in pre_bars:
        d = _utc_date(b.time)
        w = _iso_week(d)
        if b.high > daily_hi.get(d, float("-inf")):
            daily_hi[d] = b.high
        if b.low < daily_lo.get(d, float("+inf")):
            daily_lo[d] = b.low
        if b.high > weekly_hi.get(w, float("-inf")):
            weekly_hi[w] = b.high
        if b.low < weekly_lo.get(w, float("+inf")):
            weekly_lo[w] = b.low

    prior_days = sorted(d for d in daily_hi.keys() if d < entry_day)
    prior_weeks = sorted(w for w in weekly_hi.keys() if w < entry_week)

    anchors = _DailyAnchors()
    if prior_days:
        pd_ = prior_days[-1]
        anchors.pdh = daily_hi.get(pd_)
        anchors.pdl = daily_lo.get(pd_)
        if anchors.pdh is not None and anchors.pdl is not None:
            anchors.pdm = (anchors.pdh + anchors.pdl) / 2.0
    if prior_weeks:
        pw = prior_weeks[-1]
        anchors.pwh = weekly_hi.get(pw)
        anchors.pwl = weekly_lo.get(pw)
        if anchors.pwh is not None and anchors.pwl is not None:
            anchors.pwm = (anchors.pwh + anchors.pwl) / 2.0
    return anchors


# ---------------------------------------------------------------------------
# Round-number set — trivial closed-form on the price band.
# ---------------------------------------------------------------------------

def _round_number_candidates(entry: float, tp: float) -> list[LevelCandidate]:
    lo = min(entry, tp)
    hi = max(entry, tp)
    lo_k = math.ceil(lo / ROUND_STEP - 1e-9)
    hi_k = math.floor(hi / ROUND_STEP + 1e-9)
    out: list[LevelCandidate] = []
    for k in range(lo_k, hi_k + 1):
        p = round(k * ROUND_STEP, 5)
        out.append(LevelCandidate(price=p, source="round_number", detail=f"k={k}"))
    return out


# ---------------------------------------------------------------------------
# Extension-ladder reconstruction.
#
# Mirrors ``agent/journal/target_ladder.py::compute_target_ladder`` in
# structure, but with two deliberate changes per PROTOCOL §3.3:
#
#   1. The ``beyond_tp`` filter (rung price beyond TP on the trade's
#      directed axis) is REPLACED with an ``is_between`` filter (strictly
#      between entry and TP, PROTOCOL §3.2).
#   2. The ``ctx`` is computed per-trade on the pre-entry slice, not on
#      the full series. This guarantees the no-look-ahead invariant by
#      construction (mutation test §5.4).
#
# The dedupe / max_rungs / trendline_lookahead / fib_extensions parameters
# are read from the module-level constants (PROTOCOL §4.2 locked values).
# ---------------------------------------------------------------------------

def _ladder_candidates_from_ctx(
    ctx: PrecomputedContext,
    at_index: int,
    *,
    direction: Direction,
    entry: float,
    tp: float,
    trendline_lookahead: int = TRENDLINE_LOOKAHEAD,
    lookback: int = LOOKBACK,
) -> list[LevelCandidate]:
    """Assemble level candidates from a precomputed context, filtered to
    prices strictly between ``entry`` and ``tp`` (PROTOCOL §3.2).

    ``at_index`` is the index of the last bar in the pre-entry slice
    (i.e. the H4 bar ending at ``entry_time − 1``). The function only
    considers detector output whose ``bar_index < at_index + 1`` — same
    causality constraint as ``compute_target_ladder``.
    """
    is_long = direction == Direction.LONG
    lo, hi = (min(entry, tp), max(entry, tp))

    def between(price: float) -> bool:
        return lo < price < hi

    candidates: list[LevelCandidate] = []

    # -- swings: opposite-side highs / lows (resting liquidity) ----------
    for s in getattr(ctx, "swings", None) or []:
        try:
            if s.bar_index >= at_index or s.bar_index < at_index - lookback:
                continue
            # For a LONG trade, an "opposite-side swing" providing resistance
            # is a swing HIGH. For a SHORT trade, a swing LOW providing
            # support. Mirrors production compute_target_ladder.
            if is_long != bool(s.is_high):
                continue
            if between(float(s.price)):
                kind = "high" if s.is_high else "low"
                candidates.append(LevelCandidate(
                    price=float(s.price),
                    source="swing",
                    detail=f"{kind} @ bar {s.bar_index}",
                ))
        except (AttributeError, TypeError):
            continue

    # -- zone edges: near edge of the opposite-side zone -----------------
    for z in getattr(ctx, "zones", None) or []:
        try:
            if z.created_bar_index >= at_index or getattr(z, "mitigated", False):
                continue
            if is_long and z.direction == Direction.SHORT:
                edge = float(z.bottom)
            elif (not is_long) and z.direction == Direction.LONG:
                edge = float(z.top)
            else:
                continue
            if between(edge):
                candidates.append(LevelCandidate(
                    price=edge,
                    source="zone_edge",
                    detail=(
                        f"{'supply' if is_long else 'demand'} zone edge "
                        f"@ bar {z.created_bar_index}"
                    ),
                ))
        except (AttributeError, TypeError):
            continue

    # -- trendlines: projected N bars ahead -----------------------------
    for t in getattr(ctx, "trendlines", None) or []:
        try:
            if not getattr(t, "valid", True):
                continue
            proj = float(t.price_at(at_index + trendline_lookahead))
            if between(proj):
                candidates.append(LevelCandidate(
                    price=proj,
                    source="trendline",
                    detail=(
                        f"trendline proj +{trendline_lookahead} bars "
                        f"(slope {t.slope:+.7f})"
                    ),
                ))
        except (AttributeError, TypeError, ValueError):
            continue

    # -- fib extensions of the most recent impulse leg -------------------
    # PROTOCOL §4.2: mirror production FIB_EXTENSIONS = (1.272, 1.618).
    # Production ``compute_target_ladder`` consults ``ctx.fib_by_index``,
    # which the current ``precompute`` populates lazily (comment in
    # ``agent/rules/engine.py::precompute``). We call ``auto_fib`` here
    # explicitly with the same lookback bars so the fib_ext contribution
    # is not silently dropped.
    fib = None
    try:
        # ``auto_fib`` scans swings on the passed bars and returns the last
        # impulse leg (or None). We only pass the pre-entry slice, so its
        # output is causal by construction.
        pre_bars = ctx.bars
        fib = auto_fib(pre_bars)
    except Exception:
        fib = None
    if fib is not None:
        try:
            leg_start = float(fib.impulse_start)
            leg_end = float(fib.impulse_end)
            for ext in FIB_EXTENSIONS:
                price = leg_start + (leg_end - leg_start) * ext
                if between(price):
                    candidates.append(LevelCandidate(
                        price=price,
                        source="fib_ext",
                        detail=f"{ext}× extension of last impulse leg",
                    ))
        except (AttributeError, TypeError, ValueError):
            pass

    # -- daily / weekly anchor levels ------------------------------------
    # Production reads ``ctx.daily_levels[at_index]`` (NY-bucketed). E022
    # PROTOCOL §3.3 pins the boundary to UTC. Rather than dual-source, we
    # inject the E022 UTC anchors here so the ladder's daily_level
    # component matches the ``daily_only`` snap_source exactly (this is
    # what ``all`` needs to dedupe correctly).
    anchors = _compute_utc_daily_anchors(ctx.bars)
    for lc in anchors.to_candidates():
        if between(lc.price):
            candidates.append(lc)

    return candidates


def _sort_dedupe_cap(
    candidates: list[LevelCandidate],
    entry: float,
    *,
    dedupe_pips: float = DEDUPE_PIPS,
    max_rungs: int = MAX_RUNGS,
) -> list[LevelCandidate]:
    """Sort nearest-to-entry, dedupe within ``dedupe_pips``, cap at
    ``max_rungs`` — mirrors production ``compute_target_ladder`` §-166."""
    candidates.sort(key=lambda c: abs(c.price - entry))
    keep: list[LevelCandidate] = []
    tol = dedupe_pips * PIP
    for c in candidates:
        if any(abs(c.price - k.price) < tol for k in keep):
            continue
        keep.append(c)
        if len(keep) >= max_rungs:
            break
    return keep


# ---------------------------------------------------------------------------
# Per-trade compute API.
# ---------------------------------------------------------------------------

@dataclass
class TradeLevels:
    """Reconstructed level set for one trade — one entry per snap_source.

    All prices in the four lists are already filtered to lie strictly
    between entry and TP (PROTOCOL §3.2 direction invariant), so the
    ``snap_tp`` rescorer can iterate them without re-filtering.
    """

    trade_id: str
    entry_time: datetime
    entry: float
    tp: float
    direction: str
    daily_only: list[LevelCandidate] = field(default_factory=list)
    ladder_top: list[LevelCandidate] = field(default_factory=list)
    round_number: list[LevelCandidate] = field(default_factory=list)
    all: list[LevelCandidate] = field(default_factory=list)

    def prices(self, snap_source: str) -> list[float]:
        if snap_source == "daily_only":
            return [c.price for c in self.daily_only]
        if snap_source == "ladder_top":
            return [c.price for c in self.ladder_top]
        if snap_source == "round_number":
            return [c.price for c in self.round_number]
        if snap_source == "all":
            return [c.price for c in self.all]
        raise ValueError(f"Unknown snap_source: {snap_source!r}")


def compute_trade_levels(
    *,
    symbol_cache: SymbolCache,
    cfg: Config,
    trade_id: str,
    entry_time: datetime,
    entry: float,
    tp: float,
    direction: str,
    lookback: int = LOOKBACK,
    dedupe_pips: float = DEDUPE_PIPS,
    max_rungs: int = MAX_RUNGS,
    trendline_lookahead: int = TRENDLINE_LOOKAHEAD,
) -> TradeLevels:
    """Reconstruct the four level sets for one trade.

    The pre-entry slice is ``symbol_cache.bars[max(0, i - lookback + 1) : i + 1]``
    where ``i = symbol_cache.index_before(entry_time)``. If ``i < 0`` (no
    H4 bar strictly before ``entry_time`` exists in the cache), every set
    is returned empty — the trade is un-snappable.
    """
    dir_enum = Direction.LONG if direction == "long" else Direction.SHORT

    i = symbol_cache.index_before(entry_time)
    if i < 0:
        return TradeLevels(
            trade_id=trade_id, entry_time=entry_time,
            entry=entry, tp=tp, direction=direction,
        )
    lo = max(0, i - lookback + 1)
    pre_bars = symbol_cache.bars[lo : i + 1]

    # --- daily_only -----------------------------------------------------
    anchors = _compute_utc_daily_anchors(pre_bars)
    daily_only_candidates = anchors.to_candidates()
    daily_only_filtered = _filter_between(daily_only_candidates, entry, tp)

    # --- round_number ---------------------------------------------------
    rn_candidates = _round_number_candidates(entry, tp)
    # round_number entries are already inside [min, max]; the direction
    # invariant is strict inequality, so we still filter to be safe (the
    # exact endpoints entry / tp are excluded per PROTOCOL §3.2).
    rn_filtered = _filter_between(rn_candidates, entry, tp)

    # --- ladder_top -----------------------------------------------------
    # precompute() is comparatively cheap on 200 bars; we call per-trade
    # so the resulting ctx cannot see any bar >= entry_time (no-lookahead).
    if len(pre_bars) < 2 * cfg.detectors.swing_lookback + 1:
        # Too few bars to detect swings; ladder is empty.
        ladder_filtered: list[LevelCandidate] = []
    else:
        ctx = precompute(pre_bars, cfg)
        # ``at_index`` here is the index of the last bar in ``pre_bars``,
        # which is ``len(pre_bars) - 1`` in the LOCAL frame of the slice.
        at_index_local = len(pre_bars) - 1
        ladder_all = _ladder_candidates_from_ctx(
            ctx,
            at_index_local,
            direction=dir_enum,
            entry=entry,
            tp=tp,
            trendline_lookahead=trendline_lookahead,
            lookback=lookback,
        )
        ladder_all = _sort_dedupe_cap(
            ladder_all, entry, dedupe_pips=dedupe_pips, max_rungs=max_rungs,
        )
        # PROTOCOL §3.3: ``ladder_top`` is ONE level — the extension-ladder
        # rung nearest to *entry* that lies between entry and TP. After
        # the sort_dedupe_cap by nearest-to-entry, that is candidate[0]
        # if any; else empty.
        ladder_filtered = [ladder_all[0]] if ladder_all else []

    # --- all: union of the three, deduped within dedupe_pips ------------
    union = list(daily_only_filtered) + list(ladder_filtered) + list(rn_filtered)
    union_dedup = _sort_dedupe_cap(
        union, entry, dedupe_pips=dedupe_pips, max_rungs=len(union),
    )

    return TradeLevels(
        trade_id=trade_id,
        entry_time=entry_time,
        entry=entry,
        tp=tp,
        direction=direction,
        daily_only=daily_only_filtered,
        ladder_top=ladder_filtered,
        round_number=rn_filtered,
        all=union_dedup,
    )


def _filter_between(
    candidates: Iterable[LevelCandidate], entry: float, tp: float,
) -> list[LevelCandidate]:
    """PROTOCOL §3.2 direction invariant: strictly between entry and tp."""
    lo = min(entry, tp)
    hi = max(entry, tp)
    return [c for c in candidates if lo < c.price < hi]


# ---------------------------------------------------------------------------
# Batch pre-compute (one call per (symbol, trade_id)).
# ---------------------------------------------------------------------------

def compute_all_trade_levels(
    trades: Sequence[dict],
    *,
    cfg: Optional[Config] = None,
    lookback: int = LOOKBACK,
    dedupe_pips: float = DEDUPE_PIPS,
    max_rungs: int = MAX_RUNGS,
    trendline_lookahead: int = TRENDLINE_LOOKAHEAD,
) -> dict[str, TradeLevels]:
    """Reconstruct levels for a batch of trades. ``trades`` is a list of
    dicts (subset of PRE-0 fields) with keys:

        - ``trade_id`` (str)
        - ``symbol`` (str)
        - ``entry_time`` (``datetime`` UTC)
        - ``entry`` (float)
        - ``take_profit`` (float)
        - ``direction`` (``"long"`` | ``"short"``)

    Symbol caches are memoised inside this call.
    """
    if cfg is None:
        cfg = load_config()

    out: dict[str, TradeLevels] = {}
    for t in trades:
        symbol = t["symbol"]
        cache = load_symbol_cache(symbol, cfg=cfg)
        out[t["trade_id"]] = compute_trade_levels(
            symbol_cache=cache,
            cfg=cfg,
            trade_id=t["trade_id"],
            entry_time=t["entry_time"],
            entry=t["entry"],
            tp=t["take_profit"],
            direction=t["direction"],
            lookback=lookback,
            dedupe_pips=dedupe_pips,
            max_rungs=max_rungs,
            trendline_lookahead=trendline_lookahead,
        )
    return out


__all__ = [
    "PIP",
    "LOOKBACK",
    "TRENDLINE_LOOKAHEAD",
    "DEDUPE_PIPS",
    "MAX_RUNGS",
    "FIB_EXTENSIONS",
    "ROUND_STEP",
    "SUPPORTED_SNAP_SOURCES",
    "LevelCandidate",
    "SymbolCache",
    "TradeLevels",
    "load_symbol_cache",
    "compute_trade_levels",
    "compute_all_trade_levels",
]
