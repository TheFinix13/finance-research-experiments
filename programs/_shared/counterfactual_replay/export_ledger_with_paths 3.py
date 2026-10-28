"""PRE-0 exporter — trade ledger with intra-trade OHLC paths + MFE/MAE.

Consumes the deployed cell (``zone_d1_against`` / H4 / ``all_on``) via the
E013 walk-forward A/B harness and, for each closed trade, augments the
record with:

- intra-trade OHLC path at the finest resolution available in the agent's
  parquet cache (M5 preferred → M15 → H4 fallback, with a
  ``path_resolution`` flag on every record);
- MFE/MAE pips + timestamps (deterministic; earliest bar wins on ties);
- target ladder if the production journal has one for the trade
  (typically absent for historical 2015-2025 trades; present for
  2026-onwards).

Emits one JSONL file per symbol under
``programs/_shared/counterfactual_replay/data/{symbol}_H4_paths.jsonl``.
First line is a ``# meta: ...`` header carrying symbol, TF, count, window
bounds, hit-rate, mean R, and the path-resolution used.

Consumer studies (E020, E021, E022, E024, E025) import
``programs/_shared/counterfactual_replay/replay.py`` (built separately)
which loads these JSONL files via ``load_paths_ledger`` and feeds trades
into the deterministic replay engine per
``programs/_shared/counterfactual_replay/SPEC.md`` §4.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/_shared/counterfactual_replay/export_ledger_with_paths.py \\
        --symbol EURUSD
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import subprocess
import sys
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT))

from run_walk_forward_ab import (  # noqa: E402
    FULL_END,
    FULL_START,
    ArmToggles,
    PlgConfig,
    _make_alpha,
    _run_alpha_ab,
)

from agent.config import load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.rules.engine import precompute  # noqa: E402
from agent.types import Bar, Direction, Timeframe  # noqa: E402
from agent.utils import to_pips  # noqa: E402

log = logging.getLogger("pre0_export")


# ---------------------------------------------------------------------------
# Per-symbol intra-trade timeframe choice.
#
# EURUSD has full M5 fidelity. GBPUSD's parquet cache stops at M15.
# USDCAD only has H4/D1. We degrade gracefully and flag the resolution
# per SPEC §1 so downstream studies can weight or filter appropriately.
# ---------------------------------------------------------------------------

PATH_TF_PREFERENCE: dict[str, list[Timeframe]] = {
    "EURUSD": [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4],
    "GBPUSD": [Timeframe.M15, Timeframe.H1, Timeframe.H4],
    "USDCAD": [Timeframe.H4],
    # Fallback for any future pair.
    "*": [Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4],
}

# Trade-TF bar durations. The intra-trade path must cover the ENTIRE H4
# bar containing exit_time — otherwise same-bar-open-close trades (e.g. a
# trade that opens at 08:00 and hits TP intra-bar the same 08:00 H4 bar)
# would only include the 08:00 M5 bar, missing the movement that actually
# hit TP. We include all M5 bars strictly before the NEXT H4 bar boundary.
TRADE_TF_DURATION: dict[str, timedelta] = {
    "H4": timedelta(hours=4),
    "H1": timedelta(hours=1),
    "M15": timedelta(minutes=15),
    "M5": timedelta(minutes=5),
}


@dataclass(frozen=True)
class IntradayCache:
    """One intraday timeframe's bars + its bar-time index."""

    tf: Timeframe
    bars: list[Bar]
    times: list[datetime]  # cached bar times (for bisect)

    def covers(self, lo: datetime, hi: datetime) -> bool:
        """True if this cache has bars covering the closed interval [lo, hi]."""
        if not self.times:
            return False
        return self.times[0] <= lo and self.times[-1] >= hi


# ---------------------------------------------------------------------------
# Path extraction (deterministic MFE/MAE recovery per SPEC §1).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PathExtract:
    """Deterministic MFE/MAE + serialised OHLC path for one trade."""

    mfe_pips: float
    mae_pips: float
    mfe_ts: str  # ISO-8601 UTC
    mae_ts: str
    path: list[dict]  # each {ts, o, h, l, c}
    path_resolution: str  # "M5" | "M15" | "H1" | "H4"


def _extract_path_and_excursions(
    entry_time: datetime,
    exit_time: datetime,
    entry_price: float,
    direction: Direction,
    cache: IntradayCache,
    trade_tf: str,
) -> PathExtract:
    """Slice ``cache`` to cover [entry_time, end-of-exit-H4-bar] and
    compute MFE/MAE per SPEC §1 field-derivation rules.

    The upper bound is exit_time + trade_tf_duration (exclusive) so that
    the intraday path includes ALL fine-grained bars within the exit H4
    bar. This is a slight superset of the true trade window: for a TP-hit
    trade, some intra-H4 bars AFTER the actual TP moment are included
    (we don't know precisely which intraday bar caused the exit). The
    MFE/MAE fields are therefore "trade-bar-conservative": MFE cannot be
    smaller than the true trade's MFE, MAE cannot be smaller than the
    true MAE within the exit trade-bar. Consumer studies that need
    tighter bounds can re-derive using replay.py.

    Determinism: on ties, the earliest bar wins (per SPEC §1). We iterate
    forward and only replace mfe/mae when strictly larger.
    """
    trade_tf_dur = TRADE_TF_DURATION.get(trade_tf, timedelta(hours=4))
    lo_i = bisect_left(cache.times, entry_time)
    # Include bars strictly before the NEXT trade-TF bar boundary after exit_time.
    hi_i = bisect_left(cache.times, exit_time + trade_tf_dur)
    span = cache.bars[lo_i:hi_i]

    mfe_pips = 0.0
    mae_pips = 0.0
    mfe_ts: Optional[datetime] = None
    mae_ts: Optional[datetime] = None

    path_rows: list[dict] = []

    long = direction == Direction.LONG
    for bar in span:
        # Favorable = distance in the direction of the trade.
        if long:
            fav = to_pips(bar.high - entry_price)
            adv = to_pips(entry_price - bar.low)
        else:
            fav = to_pips(entry_price - bar.low)
            adv = to_pips(bar.high - entry_price)

        # Strict inequality preserves earliest-bar-wins determinism.
        if fav > mfe_pips:
            mfe_pips = fav
            mfe_ts = bar.time
        if adv > mae_pips:
            mae_pips = adv
            mae_ts = bar.time

        path_rows.append({
            "ts": bar.time.isoformat(),
            "o": round(bar.open, 5),
            "h": round(bar.high, 5),
            "l": round(bar.low, 5),
            "c": round(bar.close, 5),
        })

    # If MFE never crossed 0 (rare — trade only had adverse excursion),
    # the field is 0.0 with the entry-bar timestamp; same for MAE.
    if mfe_ts is None:
        mfe_ts = entry_time
    if mae_ts is None:
        mae_ts = entry_time

    return PathExtract(
        mfe_pips=round(mfe_pips, 2),
        mae_pips=round(mae_pips, 2),
        mfe_ts=mfe_ts.isoformat(),
        mae_ts=mae_ts.isoformat(),
        path=path_rows,
        path_resolution=cache.tf.value,
    )


def _select_cache_for_trade(
    caches: list[IntradayCache],
    entry_time: datetime,
    exit_time_plus_trade_tf: datetime,
) -> IntradayCache:
    """Pick the finest cache whose bars cover the trade window. ``caches``
    must be sorted finest → coarsest. Falls back to the last (coarsest)
    entry unconditionally, which is guaranteed to cover any valid trade
    since the trade-TF cache is always included."""
    for cache in caches:
        if cache.covers(entry_time, exit_time_plus_trade_tf):
            return cache
    return caches[-1]


# ---------------------------------------------------------------------------
# Bar loading with graceful degradation across timeframes.
# ---------------------------------------------------------------------------

def _try_load_bars(
    loader: BarLoader,
    symbol: str,
    tf: Timeframe,
    start: datetime,
    end: datetime,
) -> Optional[list[Bar]]:
    """Load bars for ``tf`` if the parquet cache has it. Returns ``None``
    if the cache file is missing rather than raising."""
    parquet = _REPO_ROOT.parent / "multi-pair-trading-agent" / "data" / "parquet" / f"{symbol}_{tf.value}.parquet"
    if not parquet.exists():
        return None
    df = loader.get(symbol, tf, start, end, refresh=False)
    return df_to_bars(df, tf)


def _load_intraday_caches(
    loader: BarLoader,
    symbol: str,
    start: datetime,
    end: datetime,
) -> list[IntradayCache]:
    """Load every intraday cache that exists for ``symbol`` at TFs in the
    preference list. Returns them sorted finest → coarsest.

    Some symbols have gaps (e.g. GBPUSD M15/H1 end at 2021-12; trades
    2022+ must fall back to a coarser TF that covers the trade window).
    Downstream ``_select_cache_for_trade`` handles per-trade fallback."""
    prefs = PATH_TF_PREFERENCE.get(symbol, PATH_TF_PREFERENCE["*"])
    caches: list[IntradayCache] = []
    for tf in prefs:
        bars = _try_load_bars(loader, symbol, tf, start, end)
        if not bars:
            log.info("  cache absent: %s %s", symbol, tf.value)
            continue
        cache = IntradayCache(tf=tf, bars=bars, times=[b.time for b in bars])
        caches.append(cache)
        log.info(
            "  loaded cache: %s %s (%d bars, %s → %s)",
            symbol, tf.value, len(bars),
            cache.times[0].date().isoformat() if cache.times else "?",
            cache.times[-1].date().isoformat() if cache.times else "?",
        )
    if not caches:
        raise RuntimeError(f"No intraday bars available for {symbol}")
    return caches


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def _fmt_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _hit_rate(rs: list[float]) -> Optional[float]:
    if not rs:
        return None
    return round(sum(1 for r in rs if r > 0) / len(rs), 4)


def _mean_r(rs: list[float]) -> Optional[float]:
    if not rs:
        return None
    return round(statistics.fmean(rs), 4)


def _generator_commit() -> str:
    """Short SHA of the generator commit (for reproducibility). Falls back
    to 'uncommitted' if the repo is dirty on this file."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return sha
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, choices=["EURUSD", "GBPUSD", "USDCAD"])
    parser.add_argument("--timeframe", default="H4", help="Trade-level TF (deployed cell = H4)")
    parser.add_argument("--alpha", default="zone_d1_against")
    parser.add_argument(
        "--output-dir",
        default="programs/_shared/counterfactual_replay/data",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    cfg = load_config()
    cfg.symbol = args.symbol
    trade_tf = Timeframe(args.timeframe)

    loader = BarLoader(cache_root=cfg.data_dir)

    log.info(
        "Loading %s %s bars %s → %s ...",
        args.symbol, trade_tf.value,
        FULL_START.date().isoformat(), FULL_END.date().isoformat(),
    )
    trade_bars = _try_load_bars(loader, args.symbol, trade_tf, FULL_START, FULL_END)
    if trade_bars is None:
        raise SystemExit(f"No {args.symbol}_{trade_tf.value}.parquet in cache; aborting.")
    log.info("  %d %s bars loaded", len(trade_bars), trade_tf.value)

    log.info("Loading all intraday caches (finest → coarsest) ...")
    caches = _load_intraday_caches(loader, args.symbol, FULL_START, FULL_END)

    log.info("Precomputing detector context ...")
    ctx = precompute(trade_bars, cfg)

    toggles = ArmToggles(
        wick_proof_enabled=True,
        be_migration_enabled=True,
        plg_enabled=True,
        plg_cfg=PlgConfig(),
        record_plg_blocks=False,
    )
    alpha = _make_alpha(cfg, args.alpha)
    log.info("Running all_on backtest to generate base trade ledger ...")
    run = _run_alpha_ab(alpha, trade_bars, cfg, ctx=ctx, start_index=200, toggles=toggles)
    log.info("  %d trades", len(run.trades))

    # Augment each trade with the intra-trade path + MFE/MAE.
    trade_tf_dur = TRADE_TF_DURATION.get(trade_tf.value, timedelta(hours=4))
    ledger: list[dict] = []
    resolution_histogram: dict[str, int] = {}
    skipped_no_exit = 0
    for idx, t in enumerate(run.trades):
        stop_pips = to_pips(abs(t.setup.entry - t.setup.stop))
        if stop_pips <= 0:
            continue
        if t.exit_time is None:
            skipped_no_exit += 1
            continue

        pnl_pips = float(t.pnl_pips or 0.0)
        r = round(pnl_pips / stop_pips, 4)
        tp_pips = to_pips(abs(t.tp_price - t.entry_price))

        # Per-trade cache selection: prefer finest that covers the trade
        # window (some symbols have finer TFs that don't cover late years).
        cache = _select_cache_for_trade(
            caches, t.entry_time, t.exit_time + trade_tf_dur,
        )
        path_extract = _extract_path_and_excursions(
            entry_time=t.entry_time,
            exit_time=t.exit_time,
            entry_price=t.entry_price,
            direction=t.direction,
            cache=cache,
            trade_tf=trade_tf.value,
        )
        resolution_histogram[path_extract.path_resolution] = (
            resolution_histogram.get(path_extract.path_resolution, 0) + 1
        )

        row: dict = {
            "trade_id": f"{args.symbol}_{trade_tf.value}_{idx:05d}",
            "symbol": args.symbol,
            "tf": trade_tf.value,
            "direction": t.direction.value,
            "entry_time": _fmt_iso(t.entry_time),
            "entry": round(t.entry_price, 5),
            "stop": round(t.stop_price, 5),
            # soft_stop = original entry-time stop; production BE migration mutates t.stop_price
            # so we back it out from stop_pips at the entry price direction:
            "soft_stop": round(t.setup.stop, 5),
            "take_profit": round(t.tp_price, 5),
            "stop_pips": round(stop_pips, 2),
            "tp_pips": round(tp_pips, 2),
            "r": r,
            "pnl_pips": round(pnl_pips, 2),
            "exit_time": _fmt_iso(t.exit_time),
            "exit_price": round(t.exit_price, 5) if t.exit_price is not None else None,
            "exit_reason": t.exit_reason,

            # PRE-0 additions
            "mfe_pips": path_extract.mfe_pips,
            "mae_pips": path_extract.mae_pips,
            "mfe_ts": path_extract.mfe_ts,
            "mae_ts": path_extract.mae_ts,
            "mfe_r": round(path_extract.mfe_pips / stop_pips, 4),
            "mae_r": round(path_extract.mae_pips / stop_pips, 4),
            "path": path_extract.path,
            "path_resolution": path_extract.path_resolution,
        }

        # target_ladder omitted per SPEC §1: mostly absent for 2015-2025,
        # consumer studies must not require it.
        ledger.append(row)

    if skipped_no_exit:
        log.warning("Skipped %d trade(s) with no exit_time (open at series end?)", skipped_no_exit)
    log.info("Resolution histogram: %s", resolution_histogram)

    rs = [row["r"] for row in ledger]
    meta = {
        "symbol": args.symbol,
        "timeframe": trade_tf.value,
        "alpha": args.alpha,
        "toggles": "all_on (wick_proof + be_migration + plg) — production-matching",
        "harness": "scripts/run_walk_forward_ab.py::_run_alpha_ab (E013)",
        "path_resolution_histogram": resolution_histogram,
        "full_start": FULL_START.isoformat(),
        "full_end": FULL_END.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "n_trades": len(ledger),
        "hit_rate": _hit_rate(rs),
        "mean_r": _mean_r(rs),
        "median_r": round(statistics.median(rs), 4) if rs else None,
        "min_r": round(min(rs), 4) if rs else None,
        "max_r": round(max(rs), 4) if rs else None,
        "schema_version": "pre0.v1",
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.symbol}_{trade_tf.value}_paths.jsonl"

    with out_path.open("w") as fh:
        fh.write("# meta: " + json.dumps(meta) + "\n")
        for row in ledger:
            fh.write(json.dumps(row) + "\n")

    log.info("Wrote %s (%d trades, resolutions=%s)", out_path, len(ledger), resolution_histogram)
    log.info("Meta: %s", json.dumps(meta, indent=None))


if __name__ == "__main__":
    main()
