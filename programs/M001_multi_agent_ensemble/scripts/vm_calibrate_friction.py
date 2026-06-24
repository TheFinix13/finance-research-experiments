"""VM-side friction-calibration script — broker fills → calibration JSON.

This is a standalone CLI the user runs **on the deployment VM** (Windows)
to convert the live broker-fill text logs + JSONL vaults into the
canonical `sim/core/friction_calibration_2026-06.json` artefact the
simulator reads at startup.

It is intentionally importable on a Mac host (where the broker logs
don't exist) so the test suite can exercise the structural plumbing
end-to-end. On a host with no logs the script reports `n_orders=0`
per symbol and exits 0 — the "deferred data" path documented in
`sim/core/friction.py` and `sim/README.md`.

Usage (on the Windows VM)::

    python programs/M001_multi_agent_ensemble/scripts/vm_calibrate_friction.py
    python programs/M001_multi_agent_ensemble/scripts/vm_calibrate_friction.py --dry-run
    python programs/M001_multi_agent_ensemble/scripts/vm_calibrate_friction.py "C:\\Users\\Fiyin\\Documents\\TradingAgentLogs"

Path discovery order:

1. Explicit positional argv (first non-flag) — the user can paste a
   path verbatim.
2. `C:\\Users\\Fiyin\\Documents\\TradingAgentLogs\\` — current VM
   home per the production `ai_context.md`.
3. `~\\Documents\\TradingAgentLogs\\` — cross-platform fallback via
   `Path.home()`; resolves to the right place on Windows AND on this
   Mac research host (where the dir exists but is largely empty).
4. `D:\\TradingAgentLogs\\` — legacy VM path retained for archive
   compatibility.

The script never writes anything when `--dry-run` is set. The
"commit these and push" instructions are printed last so the user
can copy the exact git invocations without re-typing.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

# Resolve the repo root from `__file__` so the script works whether
# invoked from the repo root, the program folder, or via Makefile.
THIS_FILE = Path(__file__).resolve()
PROGRAM_ROOT = THIS_FILE.parents[1]
REPO_ROOT = THIS_FILE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.core.friction import (  # noqa: E402
    CalibrationResult,
    calibrate_against_fills,
    write_calibration_file,
)

# ---------------------------------------------------------------------------
# Path discovery + constants
# ---------------------------------------------------------------------------

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")

# pathlib normalises forward-slash strings on Windows, so the
# C: + D: candidates below are safe on both platforms; on Mac they
# are simply relative paths that won't `exists()`.
CANDIDATE_LOG_ROOTS: tuple[Path, ...] = (
    Path("C:/Users/Fiyin/Documents/TradingAgentLogs"),
    Path.home() / "Documents" / "TradingAgentLogs",
    Path("D:/TradingAgentLogs"),
)

DEFAULT_CALIBRATION_OUT = (
    PROGRAM_ROOT / "sim" / "core" / "friction_calibration_2026-06.json"
)

# Production parquet cache — used to derive ATR(14) at signal time
# so the slippage coefficient `k` regression has real data. Look in
# the env var first (matches the cross-repo contract in
# `sim/_cross_repo.py`), then the dev default.
_PRODUCTION_REPO_DEFAULT = (
    Path.home() / "Documents" / "GitHub" / "multi-pair-trading-agent"
)

# Minimum sample size before we warn the user the calibration is thin.
MIN_ORDERS_FOR_RELIABLE = 30

# Constant ATR placeholder used only when neither parquet nor
# log-derived bars are available. The value is the EURUSD H4 long-run
# average; chosen to keep the calibration k *roughly* sane while
# making it obvious in the notes that the number is a placeholder.
ATR_PLACEHOLDER_BY_SYMBOL: dict[str, float] = {
    "EURUSD": 0.0011,
    "GBPUSD": 0.0014,
    "USDCAD": 0.0012,
}


# ---------------------------------------------------------------------------
# Path discovery
# ---------------------------------------------------------------------------

def discover_log_root(
    explicit: str | None = None,
    *,
    candidates: Iterable[Path] = CANDIDATE_LOG_ROOTS,
) -> tuple[Path, str]:
    """Pick the first existing log root in priority order.

    Returns (path, source_note). When nothing exists, returns the
    `Path.home()` fallback and a note explaining the deferred-data path
    so the caller can still run the calibration loop (which will
    cleanly report `n_orders=0` per symbol).
    """
    if explicit:
        p = Path(explicit).expanduser()
        return p, f"explicit argv ({p})"

    candidate_list = list(candidates)
    for candidate in candidate_list:
        try:
            if candidate.exists():
                return candidate, f"auto-detected ({candidate})"
        except OSError:
            continue

    # Nothing exists — fall back to ~/Documents/TradingAgentLogs even
    # if it doesn't exist, so the calibrator can report "directory
    # absent → n_orders=0 per symbol" via its deferred-data branch.
    fallback = candidate_list[1] if len(candidate_list) > 1 else Path.home()
    return fallback, (
        f"no candidate exists; falling back to {fallback} "
        "(deferred-data path — calibration will report n_orders=0)"
    )


# ---------------------------------------------------------------------------
# ATR-at-signal lookup (production parquet preferred; constant fallback)
# ---------------------------------------------------------------------------

def _resolve_production_repo() -> Path:
    """Return the production-repo root, env-var preferred."""
    import os
    env = os.environ.get("M001_PRODUCTION_REPO")
    if env:
        return Path(env).expanduser().resolve()
    return _PRODUCTION_REPO_DEFAULT


def _load_parquet_for_symbol(symbol: str, timeframe: str) -> "object | None":
    """Try to load OHLC bars for (symbol, timeframe) from prod parquet cache.

    Returns the pandas DataFrame on success, None when the parquet is
    absent. Indexed by UTC timestamp.
    """
    repo = _resolve_production_repo()
    cache_path = repo / "data" / "parquet" / f"{symbol}_{timeframe}.parquet"
    if not cache_path.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_parquet(cache_path)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df
    except Exception:  # noqa: BLE001 — best-effort lookup
        return None


def build_atr_map_from_parquet(
    fills: list,
    symbol: str,
    *,
    fallback_atr: float | None = None,
) -> tuple[dict[int, float], str]:
    """Map fill index → ATR(14) at signal timestamp.

    Looks up each `FillRecord.signal_ts` in the production parquet
    cache and computes ATR(14) ending at-or-before that timestamp.
    When the cache is absent, every record falls back to
    `fallback_atr` and a warning note is returned so the caller can
    surface it in the JSON `notes` field.
    """
    if not fills:
        return {}, ""

    # Group fills by timeframe; production logs typically write H4
    # only, but we tolerate mixed timeframes per safety.
    by_tf: dict[str, list[tuple[int, object]]] = {}
    for idx, fill in enumerate(fills):
        if fill.signal_ts is None:
            continue
        by_tf.setdefault(fill.timeframe, []).append((idx, fill.signal_ts))

    if not by_tf:
        note = "no signal_ts on any fill; ATR map empty"
        if fallback_atr is not None and fills:
            return {i: float(fallback_atr) for i in range(len(fills))}, (
                f"{note}; falling back to constant ATR={fallback_atr}"
            )
        return {}, note

    atr_by_record: dict[int, float] = {}
    notes: list[str] = []
    used_parquet = False
    for timeframe, idx_ts_list in by_tf.items():
        df = _load_parquet_for_symbol(symbol, timeframe)
        if df is None:
            notes.append(
                f"no {symbol}_{timeframe}.parquet in production cache; "
                "ATR derived from constant placeholder"
            )
            continue
        used_parquet = True
        try:
            from conflab.indicators import atr as atr_indicator
            atr_series = atr_indicator(df, period=14)
        except Exception as e:  # noqa: BLE001 — best-effort
            notes.append(
                f"ATR computation on {symbol}_{timeframe}.parquet failed: "
                f"{type(e).__name__}: {e}"
            )
            continue
        for idx, ts in idx_ts_list:
            # `asof` semantics: largest index ≤ ts.
            try:
                pos = atr_series.index.asof(ts)
                if pos is None or (
                    isinstance(pos, float) and math.isnan(pos)
                ):
                    continue
                val = float(atr_series.loc[pos])
            except (KeyError, ValueError, TypeError):
                continue
            if math.isfinite(val) and val > 0:
                atr_by_record[idx] = val

    # Fill gaps with the constant placeholder so `_estimate_k_slippage`
    # still has data to regress on (the OLS will weight the
    # placeholder rows toward whatever the placeholder implies; the
    # `notes` line flags the dilution).
    if fallback_atr is not None:
        filled = 0
        for i in range(len(fills)):
            if i not in atr_by_record:
                atr_by_record[i] = float(fallback_atr)
                filled += 1
        if filled:
            notes.append(
                f"{filled}/{len(fills)} fills had no parquet-derived ATR; "
                f"filled with constant ATR={fallback_atr}"
            )

    if not used_parquet and fallback_atr is None:
        notes.append("no parquet cache and no fallback_atr; ATR map left empty")

    return atr_by_record, "; ".join(notes)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_per_symbol_block(result: CalibrationResult) -> str:
    """Build the paste-friendly per-symbol summary block."""
    lines: list[str] = []
    lines.append(f"  {result.symbol}:")
    lines.append(f"    n_orders          : {result.n_orders}")
    lines.append(f"    n_rejections      : {result.n_rejections}")
    lines.append(f"    n_partial_fills   : {result.n_partial_fills}")
    lines.append(f"    median_spread     : {result.median_spread:.6f}")
    lines.append(f"    p95_spread        : {result.p95_spread:.6f}")
    lines.append(
        f"    median_latency_ms : {result.median_latency_ms:.1f}"
    )
    lines.append(f"    p95_latency_ms    : {result.p95_latency_ms:.1f}")
    lines.append(f"    partial_fill_rate : {result.partial_fill_rate:.4f}")
    lines.append(f"    rejection_rate    : {result.rejection_rate:.4f}")
    lines.append(
        f"    slippage_atr_mult : {result.slippage_atr_mult:.4f} (k)"
    )
    if result.window_start:
        lines.append(
            f"    window            : {result.window_start} → "
            f"{result.window_end}"
        )
    lines.append(f"    source_path       : {result.source_path}")
    if result.notes:
        lines.append(f"    notes             : {result.notes}")
    return "\n".join(lines)


def format_aggregate_summary(
    results: dict[str, CalibrationResult],
    *,
    log_root: Path,
    log_root_note: str,
    dry_run: bool,
    out_path: Path,
) -> str:
    """Top-level summary block — what the user pastes into chat."""
    lines = []
    lines.append("=" * 72)
    lines.append("M001 friction calibration — VM broker fills")
    lines.append("=" * 72)
    lines.append(f"log root          : {log_root}")
    lines.append(f"source            : {log_root_note}")
    lines.append(f"target output     : {out_path}")
    lines.append(f"dry run           : {dry_run}")
    lines.append("")
    lines.append("Per-symbol calibration:")
    lines.append("")
    for sym in SYMBOLS:
        result = results.get(sym)
        if result is None:
            lines.append(f"  {sym}: (no result emitted)")
            continue
        lines.append(format_per_symbol_block(result))
        lines.append("")

    lines.append("Fit quality:")
    any_warn = False
    any_nonfinite = False
    for sym, result in results.items():
        if result.n_orders < MIN_ORDERS_FOR_RELIABLE:
            lines.append(
                f"  ⚠️  {sym}: n_orders={result.n_orders} < "
                f"{MIN_ORDERS_FOR_RELIABLE} → calibration is thin; "
                "re-run after more demo fills accumulate"
            )
            any_warn = True
        for field, value in (
            ("median_spread", result.median_spread),
            ("median_latency_ms", result.median_latency_ms),
            ("slippage_atr_mult", result.slippage_atr_mult),
            ("partial_fill_rate", result.partial_fill_rate),
            ("rejection_rate", result.rejection_rate),
        ):
            if not math.isfinite(value):
                lines.append(
                    f"  ⚠️  {sym}: {field}={value} is non-finite — "
                    "calibration ignored this field, defaults will apply"
                )
                any_warn = True
                any_nonfinite = True
    if not any_warn:
        lines.append("  ✅  all per-symbol fields finite; all symbols "
                     f"≥ {MIN_ORDERS_FOR_RELIABLE} orders")
    elif not any_nonfinite:
        lines.append(
            "  (warnings above are sample-size only; the JSON is still "
            "safe to load — the simulator falls back to conservative "
            "defaults for thin symbols)"
        )
    lines.append("")
    return "\n".join(lines)


def format_next_steps(
    out_path: Path,
    *,
    written: bool,
    dry_run: bool,
    any_data: bool,
) -> str:
    """The user-facing 'what to do next' block.

    Three branches:
      - `written`: print git add / commit / push hints.
      - `dry_run`: explain how to re-run without the flag.
      - otherwise (no fills on disk): explain the deferred-data path
        so the user doesn't think the script silently failed.
    """
    rel = out_path
    try:
        rel = out_path.relative_to(REPO_ROOT)
    except ValueError:
        pass

    if written:
        return (
            "To commit the calibration:\n"
            f"    git add {rel}\n"
            "    git commit -m \"M001 Φ3-prep: friction calibration "
            "from June 2026 VM broker fills\"\n"
            "    git push origin multi-agent-ensemble   "
            "# only if you want it on remote\n"
        )

    if dry_run:
        return (
            "(dry run — no file written; re-run without --dry-run to "
            "persist)\n"
        )

    if not any_data:
        return (
            "(no broker fills found under the discovered log root — "
            "n_orders=0 across every symbol. This is the deferred-data "
            "path: the simulator will keep its conservative friction "
            "defaults until live demo trades populate the logs. "
            "Re-run this script after some live trades have landed.)\n"
        )

    return ""


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    *,
    explicit_log_root: str | None = None,
    out_path: Path = DEFAULT_CALIBRATION_OUT,
    symbols: Iterable[str] = SYMBOLS,
    dry_run: bool = False,
    use_atr_parquet: bool = True,
) -> tuple[dict[str, CalibrationResult], str, str]:
    """Calibrate every symbol against the broker fills under `log_root`.

    Returns (results_by_symbol, summary_text, next_steps_text). The
    JSON file is written iff `dry_run` is False AND at least one
    symbol reports `n_orders > 0` (writing an all-zero calibration
    would silently mask the deferred-data path on the next sim run).
    """
    log_root, source_note = discover_log_root(explicit_log_root)
    results: dict[str, CalibrationResult] = {}
    for sym in symbols:
        # Pass 1: parse fills (no ATR yet) so we know how many we have.
        partial = calibrate_against_fills(sym, log_root=log_root)
        # Pass 2: build the ATR map using the production parquet cache
        # if available, then re-calibrate so the k regression has data.
        if partial.n_orders > 0 and use_atr_parquet:
            # We need the fill records (not the empirical summary) to
            # join ATR — re-parse the text logs directly.
            from programs.M001_multi_agent_ensemble.sim.core.friction import (
                parse_text_log,
            )
            sym_dir = log_root / sym
            fills: list = []
            for lf in sorted(sym_dir.glob(f"{sym}_*.log")):
                sub_fills, _ = parse_text_log(lf)
                fills.extend(sub_fills)
            atr_map, atr_note = build_atr_map_from_parquet(
                fills, sym,
                fallback_atr=ATR_PLACEHOLDER_BY_SYMBOL.get(sym),
            )
            result = calibrate_against_fills(
                sym, log_root=log_root, atr_by_record=atr_map,
            )
            if atr_note and not result.notes:
                result.notes = atr_note
            elif atr_note:
                result.notes = f"{result.notes}; {atr_note}"
        else:
            result = partial
        results[sym] = result

    any_written = any(r.n_orders > 0 for r in results.values())
    summary = format_aggregate_summary(
        results,
        log_root=log_root,
        log_root_note=source_note,
        dry_run=dry_run,
        out_path=out_path,
    )

    written = False
    if not dry_run and any_written:
        write_calibration_file(
            results,
            path=out_path,
            extra_metadata={
                "tool": "scripts/vm_calibrate_friction.py",
                "log_root": str(log_root),
                "log_root_source": source_note,
            },
        )
        written = True
    next_steps = format_next_steps(
        out_path,
        written=written,
        dry_run=dry_run,
        any_data=any_written,
    )
    return results, summary, next_steps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate the M001 friction model against the live "
            "broker-fills tree on the deployment VM. Writes "
            "sim/core/friction_calibration_2026-06.json by default."
        ),
    )
    parser.add_argument(
        "log_root",
        nargs="?",
        default=None,
        help=(
            "Optional path to the TradingAgentLogs root. If omitted, "
            "the script auto-detects from a list of well-known paths."
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_CALIBRATION_OUT,
        help=(
            "Path to write the calibration JSON. Defaults to "
            "sim/core/friction_calibration_2026-06.json."
        ),
    )
    parser.add_argument(
        "--symbol", action="append", default=None,
        help=(
            "Restrict calibration to a single symbol (repeat to pass "
            "multiple). Defaults to EURUSD/GBPUSD/USDCAD."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the summary; do not write the JSON file.",
    )
    parser.add_argument(
        "--no-atr-parquet", action="store_true",
        help=(
            "Skip the ATR-from-parquet pass; useful on hosts where "
            "the production cache isn't reachable."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = tuple(args.symbol) if args.symbol else SYMBOLS
    _, summary, next_steps = run(
        explicit_log_root=args.log_root,
        out_path=args.out,
        symbols=symbols,
        dry_run=args.dry_run,
        use_atr_parquet=not args.no_atr_parquet,
    )
    print(summary)
    print(next_steps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
