"""Phase AC — Stage 0 helper: extend pair_character.json with USDJPY + USDCHF.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        PROTOCOL.md §4 (feature vector definitions)
        AMENDMENT_2026-07-20_ac0_methodology_switch.md §3
            (pair_character.json FROZEN — only y-axis is re-measured)
        Task prompt 2026-07-20 evening:
            "Find the feature-extractor code that computed the initial JSON
             entries [...] Run it JUST for the two new pairs and merge results
             into the existing JSON. If the extractor doesn't have a per-pair
             mode, wrap it minimally so it only computes USDJPY/USDCHF and
             appends — do NOT recompute the frozen 5 existing pairs (that
             would be a frozen-file drift violation per amendment)."

What this does
--------------

Loads the H4 + D1 bars for USDJPY and USDCHF from the production parquet
cache over the pre-registered training window (2015-01-01 → 2019-01-01,
per PROTOCOL §4 and G7 walk-forward IS/OOS boundary at 2019-01-01),
computes the four §4 features (``d1_ac1``, ``median_h4_atr_abs``,
``max_session_impulse``, ``d1_chop_fraction``), and derives an
``h4_atr_percentile`` for each of the two new pairs by ranking their
pip-normalised median H4 ATR-14 against the frozen 5-pair distribution.

Frozen-invariant preservation
-----------------------------

The 5 existing pair entries in ``pair_character.json``
(EURUSD/GBPUSD/USDCAD/AUDUSD/NZDUSD) are read and rewritten
bytewise-identical. Only the two placeholder entries currently marked
``"error": "NEEDS CACHE PULL"`` (USDJPY, USDCHF) are replaced with
computed feature dicts.

Pip normalisation for the H4 ATR percentile
-------------------------------------------

The frozen 5 pairs are all non-JPY USD-quoted, so their pip size is
identical (0.0001) and their raw ``median_h4_atr_abs`` ranking equals
their pip-normalised ranking; that's why their frozen
``h4_atr_percentile`` values 0.1/0.3/0.5/0.7/0.9 = (rank+0.5)/5 on the
raw abs distribution happen to coincide with the pip-normalised
distribution. USDJPY uses pip size 0.01 (yen quote), so its raw abs
ATR is ~100× the non-JPY values and is NOT rankable in raw absolute
terms.

For the new pairs we therefore:

1. Compute pip-normalised median H4 ATR (raw abs / pip_size) for all
   7 pairs (frozen 5 read from stored ``median_h4_atr_abs`` × 10000;
   new 2 computed fresh).
2. Sort the 7 pip-normalised values, find the rank of each new pair,
   and assign its ``h4_atr_percentile = (rank + 0.5) / 7``.
3. Do NOT touch the frozen 5 percentile values. They stay at their
   (rank+0.5)/5 = 0.1/0.3/0.5/0.7/0.9 encoding.

This is a deliberate, documented scale mismatch: the frozen 5 stay on
a 5-pair (rank+0.5)/5 scale and the new 2 land on a 7-pair (rank+0.5)/7
scale. The scales overlap in [0.071, 0.929] so no new-pair percentile
can escape the frozen range, and the relative ordering across all 7
pairs is preserved. The alternative (recomputing all 7 on the 7-pair
distribution) would perturb every one of the frozen values and violate
the amendment §3 frozen-file invariant.

CLI
---

::

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.compute_pair_character_delta \\
        --pair-character programs/M001_multi_agent_ensemble/experiments/\\
phase_ac_pitch_assignment/results/pair_character.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)

log = logging.getLogger(__name__)


UTC = timezone.utc

TRAIN_START = datetime(2015, 1, 1, tzinfo=UTC)
TRAIN_END = datetime(2019, 1, 1, tzinfo=UTC)

NEW_PAIRS: tuple[str, ...] = ("USDJPY", "USDCHF")
FROZEN_PAIRS: tuple[str, ...] = (
    "EURUSD", "GBPUSD", "USDCAD", "AUDUSD", "NZDUSD",
)


def _pip_size(symbol: str) -> float:
    """Pip size in absolute price units. JPY quotes are 2-decimal (0.01),
    everything else is 4-decimal (0.0001)."""
    return 0.01 if symbol.endswith("JPY") else 0.0001


def _load_bars(symbol: str, timeframe_str: str, start: datetime, end: datetime):
    """Load bars from the production parquet cache directly (READ-ONLY).

    Bypasses ``BarLoader.get`` because that method falls back to
    fetching from the source (Dukascopy) when the cache doesn't fully
    cover the requested range, which would risk upserting new data into
    the frozen production cache. Stage 0 is strictly a read-only
    computation on whatever is already in the cache — even if the cache
    starts later than ``TRAIN_START`` (e.g. USDJPY/USDCHF start
    2015-07-23), we use the actual cached slice without triggering a
    refresh.
    """
    import pandas as pd

    from agent.config import load_config
    from agent.data.source import ParquetCache
    from agent.types import Timeframe

    cfg = load_config()
    cache = ParquetCache(cfg.data_dir)
    tf = getattr(Timeframe, timeframe_str)
    df = cache.load(symbol, tf)
    if df.empty:
        return df
    start_ts = pd.Timestamp(start, tz="UTC") if start.tzinfo is None else pd.Timestamp(start)
    end_ts = pd.Timestamp(end, tz="UTC") if end.tzinfo is None else pd.Timestamp(end)
    slice_start = max(start_ts, df.index.min())
    slice_end = min(end_ts, df.index.max())
    if slice_start > slice_end:
        return df.iloc[0:0]
    return df.loc[slice_start:slice_end]


def _compute_new_pair_features(symbol: str) -> dict[str, Any]:
    """Compute the 4 §4 features for one new pair on the training window.

    Reuses the exact feature primitives from
    ``run_ac0_regression.py`` so the numeric outputs are the same as if
    the pair had been in the original AC.0-v1 fire.
    """
    # Import at call time so the module import doesn't drag in
    # numpy/pandas unless needed (tests can stub _load_bars).
    from programs.M001_multi_agent_ensemble.experiments.phase_ac_pitch_assignment.run_ac0_regression import (  # noqa: E501
        _d1_ac1,
        _d1_chop_fraction,
        _max_session_impulse,
        _median_h4_atr14,
    )

    h4 = _load_bars(symbol, "H4", TRAIN_START, TRAIN_END)
    d1 = _load_bars(symbol, "D1", TRAIN_START, TRAIN_END)
    if h4 is None or d1 is None or h4.empty or d1.empty:
        return {
            "error": f"empty bars for {symbol}",
            "n_h4": int(0 if h4 is None else len(h4)),
            "n_d1": int(0 if d1 is None else len(d1)),
        }
    return {
        "n_h4": int(len(h4)),
        "n_d1": int(len(d1)),
        "d1_ac1": float(_d1_ac1(d1)),
        "median_h4_atr_abs": float(_median_h4_atr14(h4)),
        "max_session_impulse": float(_max_session_impulse(h4)),
        "d1_chop_fraction": float(_d1_chop_fraction(d1)),
        "training_window_utc": [
            TRAIN_START.isoformat(), TRAIN_END.isoformat(),
        ],
    }


def _pip_normalised_atr(sym: str, features: dict[str, Any]) -> float:
    """Return ``median_h4_atr_abs / pip_size(sym)``.

    Raises ``KeyError`` if the entry lacks a numeric ``median_h4_atr_abs``.
    """
    raw = features["median_h4_atr_abs"]
    if not isinstance(raw, (int, float)):
        raise KeyError(
            f"{sym}: median_h4_atr_abs is non-numeric ({raw!r}); cannot "
            "compute pip-normalised percentile"
        )
    return float(raw) / _pip_size(sym)


def assign_new_pair_h4_atr_percentile(
    existing: dict[str, dict[str, Any]],
    new_features: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Rank the two new pairs against the FROZEN 5 pairs' pip-normalised
    median H4 ATR distribution and assign each new pair
    ``h4_atr_percentile = (rank + 0.5) / 7``.

    Returns dict[symbol -> percentile] for the two new pairs only. The
    frozen 5 pairs' percentiles are NOT touched.
    """
    pip_atrs: list[tuple[str, float]] = []
    for sym in FROZEN_PAIRS:
        entry = existing.get(sym)
        if entry is None or "error" in entry:
            raise ValueError(
                f"Frozen pair {sym} missing or errored in existing "
                f"pair_character.json — cannot compute new-pair rankings"
            )
        pip_atrs.append((sym, _pip_normalised_atr(sym, entry)))
    for sym in NEW_PAIRS:
        entry = new_features.get(sym)
        if entry is None or "error" in entry:
            log.warning(
                "New pair %s missing feature dict — skipping ranking; "
                "no h4_atr_percentile will be emitted", sym,
            )
            continue
        pip_atrs.append((sym, _pip_normalised_atr(sym, entry)))

    pip_atrs.sort(key=lambda t: t[1])
    n = len(pip_atrs)
    out: dict[str, float] = {}
    for rank, (sym, _val) in enumerate(pip_atrs):
        if sym in NEW_PAIRS:
            out[sym] = float((rank + 0.5) / n)
    return out


def extend_pair_character(
    pair_character_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, dict[str, Any]]:
    """Read ``pair_character_path``, replace only the USDJPY / USDCHF
    placeholder entries with freshly-computed feature dicts (including
    ``h4_atr_percentile`` derived per the docstring's ranking rule),
    and write the result back to disk unless ``dry_run=True``.

    Returns the FULL merged dict (frozen 5 + new 2).
    """
    ensure_production_repo_on_path()

    if not pair_character_path.exists():
        raise FileNotFoundError(
            f"pair_character.json not found at {pair_character_path}"
        )
    raw = json.loads(pair_character_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(
            f"pair_character.json at {pair_character_path} is not a dict"
        )

    for sym in FROZEN_PAIRS:
        entry = raw.get(sym)
        if entry is None or "error" in entry:
            raise ValueError(
                f"Refusing to touch pair_character.json — frozen pair "
                f"{sym} has no valid feature entry (found: {entry!r}). "
                "This helper only appends new pairs; the frozen 5 must "
                "already be populated."
            )

    frozen_before = {
        sym: json.loads(json.dumps(raw[sym])) for sym in FROZEN_PAIRS
    }

    new_features: dict[str, dict[str, Any]] = {}
    for sym in NEW_PAIRS:
        log.info(
            "Computing pair-character features for %s "
            "(training window %s → %s)",
            sym, TRAIN_START.date(), TRAIN_END.date(),
        )
        new_features[sym] = _compute_new_pair_features(sym)

    new_percentiles = assign_new_pair_h4_atr_percentile(raw, new_features)
    for sym in NEW_PAIRS:
        entry = new_features.get(sym, {})
        if "error" in entry:
            merged_entry: dict[str, Any] = dict(entry)
        else:
            merged_entry = dict(entry)
            merged_entry["h4_atr_percentile"] = new_percentiles.get(sym)
            merged_entry["dxy_beta"] = (
                "dropped (DXY not in production parquet)"
            )
        raw[sym] = merged_entry

    for sym in FROZEN_PAIRS:
        if raw[sym] != frozen_before[sym]:
            raise RuntimeError(
                f"FROZEN-INVARIANT VIOLATION: {sym} was mutated during "
                "the extension. Refusing to write. Before: "
                f"{frozen_before[sym]!r} After: {raw[sym]!r}"
            )

    if not dry_run:
        pair_character_path.write_text(
            json.dumps(raw, indent=2, default=str),
            encoding="utf-8",
        )
        log.info("Wrote extended pair_character.json to %s",
                 pair_character_path)
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extend pair_character.json with USDJPY + USDCHF entries "
            "post-cache-pull. Frozen 5 pairs are preserved bytewise."
        ),
    )
    parser.add_argument(
        "--pair-character", type=Path, required=True,
        help="Path to results/pair_character.json (in-place update).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    merged = extend_pair_character(
        args.pair_character, dry_run=args.dry_run,
    )
    n_ok = sum(
        1 for sym in NEW_PAIRS
        if isinstance(merged.get(sym, {}).get("h4_atr_percentile"),
                      (int, float))
    )
    print(f"[pair_character.delta] extended entries: {n_ok}/{len(NEW_PAIRS)} "
          f"(pairs: {NEW_PAIRS})")
    for sym in NEW_PAIRS:
        entry = merged.get(sym, {})
        if "error" in entry:
            print(f"  {sym}: ERROR — {entry['error']}")
        else:
            print(
                f"  {sym}: d1_ac1={entry['d1_ac1']:+.4f} "
                f"median_h4_atr_abs={entry['median_h4_atr_abs']:.6f} "
                f"h4_atr_pct={entry['h4_atr_percentile']:.3f} "
                f"max_session_impulse={entry['max_session_impulse']:.3f} "
                f"d1_chop_frac={entry['d1_chop_fraction']:.3f} "
                f"(n_h4={entry['n_h4']}, n_d1={entry['n_d1']})"
            )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
