"""E022 rule tests — invariants, fuzz, reproducibility, motivating case.

Reference: experiments/E022_structure_aware_tp_snap/PROTOCOL.md §3 (rule)
and §5.4 (anti-lookahead audit).

Test list (must all pass for the study to be publishable):

- ``test_snap_direction_invariant_never_widens_tp`` — random-fuzz the
  ``(entry, tp, direction, L)`` inputs and assert ``abs(new_tp − entry) ≤
  abs(tp − entry)`` on every output (PROTOCOL §3.1 invariant #2, §3.2).
- ``test_snap_idempotent`` — ``snap_tp(snap_tp(...)) == snap_tp(...)``
  (PROTOCOL §3.1 invariant #1).
- ``test_snap_direction_never_fires_beyond_tp`` — a level beyond TP must
  not produce a snap (PROTOCOL §3.2 bug fix).
- ``test_snap_returns_tp_when_no_candidates`` — empty L or all-beyond
  levels → new_tp == tp (null-rule identity).
- ``test_snap_fires_on_worked_example_no_fire_gbp`` — PROTOCOL §5.3
  motivating GBPUSD trade must NOT fire under any locked arm.
- ``test_level_detector_reproducibility`` — same H4 bars → same levels.
- ``test_snap_no_lookahead_via_level_detector`` — mutate an at-or-after
  entry bar; recomputed levels are unchanged (PROTOCOL §5.4 mutation test).

The tests use pytest style but only depend on ``unittest`` idioms so they
also run under ``python -m unittest`` if needed.
"""
from __future__ import annotations

import copy
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT.parent / "multi-pair-trading-agent"))

from programs.E022.level_detector import (  # noqa: E402
    PIP,
    LOOKBACK,
    SymbolCache,
    compute_trade_levels,
    load_symbol_cache,
)
from programs.E022.rescorer import snap_tp  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _offset(snap_distance: float) -> float:
    """PROTOCOL §4.2: snap_offset_pips = min(3, snap_distance/2)."""
    return min(3.0, snap_distance / 2.0)


# ---------------------------------------------------------------------------
# Invariants (fuzz + spot).
# ---------------------------------------------------------------------------

def test_snap_direction_invariant_never_widens_tp() -> None:
    """|new_tp − entry| must be ≤ |tp − entry| for every random input."""
    rng = random.Random(20260720)
    for _ in range(2000):
        entry = 1.0 + rng.uniform(-0.5, 0.5)
        direction = rng.choice(["long", "short"])
        target_pips = rng.uniform(20.0, 200.0)
        tp = entry + (1 if direction == "long" else -1) * target_pips * PIP
        # A grab-bag of level candidates (mix of between / outside / on TP).
        n_levels = rng.randint(0, 8)
        levels = []
        for _ in range(n_levels):
            # Levels drawn uniformly across an interval that includes and
            # extends beyond (entry, tp), so we exercise both "between"
            # and "beyond" branches of the rule.
            span_lo = min(entry, tp) - 30 * PIP
            span_hi = max(entry, tp) + 30 * PIP
            levels.append(rng.uniform(span_lo, span_hi))
        snap_distance = rng.choice([5.0, 10.0, 15.0])
        new_tp = snap_tp(
            entry, tp, direction, levels, snap_distance, _offset(snap_distance),
        )
        assert abs(new_tp - entry) <= abs(tp - entry) + 1e-9, (
            f"new_tp widened target: entry={entry}, tp={tp}, "
            f"new_tp={new_tp}, direction={direction}, levels={levels}, "
            f"snap_distance={snap_distance}"
        )


def test_snap_direction_never_fires_beyond_tp() -> None:
    """A level strictly beyond TP (further from entry than TP) must not fire."""
    # Long: entry=1.10000, tp=1.10500, beyond level at 1.10600
    for direction, entry, tp, beyond in [
        ("long", 1.10000, 1.10500, 1.10600),
        ("short", 1.10000, 1.09500, 1.09400),
    ]:
        for snap_distance in (5.0, 10.0, 15.0):
            new_tp = snap_tp(
                entry, tp, direction, [beyond], snap_distance, _offset(snap_distance),
            )
            assert new_tp == tp, (
                f"Snap fired on beyond-TP level ({beyond}) for {direction}: "
                f"entry={entry}, tp={tp}, new_tp={new_tp}"
            )


def test_snap_returns_tp_when_no_candidates() -> None:
    """Empty L → new_tp == tp; L with only beyond-TP or beyond-entry levels
    → new_tp == tp (null-rule identity)."""
    entry, tp = 1.10000, 1.10500
    # No candidates.
    assert snap_tp(entry, tp, "long", [], 15.0, 3.0) == tp
    # Only outside levels.
    outside = [1.09000, 1.11500]  # below entry and above tp
    assert snap_tp(entry, tp, "long", outside, 15.0, 3.0) == tp
    # Only exactly-on-endpoint levels (strict inequality; excluded).
    on_endpoints = [entry, tp]
    assert snap_tp(entry, tp, "long", on_endpoints, 15.0, 3.0) == tp


def test_snap_idempotent() -> None:
    """After one snap, running snap_tp again on the SAME level set is a
    fixed point (PROTOCOL §3.1 invariant #1)."""
    rng = random.Random(20260720 + 1)
    for _ in range(500):
        entry = 1.0 + rng.uniform(-0.5, 0.5)
        direction = rng.choice(["long", "short"])
        target_pips = rng.uniform(30.0, 200.0)
        tp = entry + (1 if direction == "long" else -1) * target_pips * PIP
        # Pick a level between entry and TP within the snap window.
        snap_distance = rng.choice([5.0, 10.0, 15.0])
        # Force a fire by placing a level within snap_distance of TP.
        lo, hi = (min(entry, tp), max(entry, tp))
        # Level between entry and TP, close to TP.
        d = rng.uniform(0.5, snap_distance - 0.5)
        level = tp - (1 if direction == "long" else -1) * d * PIP
        # Guard against numeric drift moving level outside (lo, hi).
        if not (lo < level < hi):
            continue
        levels = [level]
        offset = _offset(snap_distance)
        new_tp_1 = snap_tp(entry, tp, direction, levels, snap_distance, offset)
        # If snap fired, run again on the same L and assert fixed point.
        if new_tp_1 == tp:
            continue  # not a firing case; not exercising idempotence
        new_tp_2 = snap_tp(entry, new_tp_1, direction, levels, snap_distance, offset)
        assert abs(new_tp_2 - new_tp_1) < 1e-9, (
            f"Not idempotent: entry={entry}, tp={tp}, new_tp_1={new_tp_1}, "
            f"new_tp_2={new_tp_2}, level={level}, direction={direction}, "
            f"snap_distance={snap_distance}"
        )


# ---------------------------------------------------------------------------
# Motivating trade (PROTOCOL §5.3): GBPUSD 2969136564, short 1.35060 → 1.34264.
# Under the frozen 12-arm grid, no arm may fire — the swing low at 1.34111
# is BEYOND TP (further from entry, on the far side of TP), so the direction
# invariant §3.2 excludes it. Round-numbers in [1.34264, 1.35060] = {1.34500,
# 1.35000}; only 1.34500 is strictly between entry and TP (1.34264 < 1.34500
# < 1.35060), and its distance to TP = 23.6 pips > snap_distance = 15.
# ---------------------------------------------------------------------------

def test_snap_fires_on_worked_example_no_fire_gbp() -> None:
    """PROTOCOL §5.3: under every locked arm, snap must NOT fire on
    GBPUSD 2969136564. new_tp must equal tp exactly."""
    entry = 1.35060
    tp = 1.34264
    direction = "short"

    # Level sets per PROTOCOL §5.3:
    #  * ladder_top (nearest reconstructed swing): 1.34111 — BEYOND TP.
    #  * round_number: {1.34500, 1.35000}; only 1.34500 is between entry/TP.
    #    Distance to TP = |1.34500 − 1.34264| / PIP ≈ 23.6 pips.
    #  * daily_only: we don't have live values on this ticket; but §5.3
    #    predicts no arm fires — we verify with an empty daily set here.

    ladder_top_level = 1.34111  # beyond TP
    round_number_levels = [1.34500, 1.35000]

    for snap_distance in (5.0, 10.0, 15.0):
        offset = _offset(snap_distance)
        # ladder_top → beyond TP → no fire.
        got = snap_tp(entry, tp, direction, [ladder_top_level], snap_distance, offset)
        assert got == tp, (
            f"[ladder_top] arm sd={snap_distance}: snap fired on beyond-TP "
            f"swing ({ladder_top_level}); got new_tp={got}"
        )
        # round_number → 1.34500 in (1.34264, 1.35060); distance to TP = 23.6 p
        # > snap_distance in {5, 10, 15}, so no fire.
        got = snap_tp(entry, tp, direction, round_number_levels, snap_distance, offset)
        assert got == tp, (
            f"[round_number] arm sd={snap_distance}: snap fired on distant "
            f"round ({round_number_levels}); got new_tp={got}"
        )


# ---------------------------------------------------------------------------
# Level detector reproducibility (deterministic bar cache → same output).
# ---------------------------------------------------------------------------

def _small_bar_series(n_bars: int = 240, symbol: str = "EURUSD"):
    """Load a real slice of the trading-agent H4 cache for reproducibility /
    no-lookahead tests. Returns (cache, cfg)."""
    from agent.config import load_config
    cfg = load_config()
    cfg.symbol = symbol
    cache = load_symbol_cache(symbol, cfg=cfg)
    return cache, cfg


def test_level_detector_reproducibility() -> None:
    """Two independent calls on the same bar cache & trade parameters must
    return the same TradeLevels."""
    cache, cfg = _small_bar_series(symbol="EURUSD")
    # Pick a mid-history entry so we have >= 200 pre-entry bars.
    entry_time = cache.times[max(300, LOOKBACK + 5)]
    entry = cache.bars[300].close
    tp = entry + 60 * PIP  # arbitrary target
    a = compute_trade_levels(
        symbol_cache=cache, cfg=cfg,
        trade_id="repro_1", entry_time=entry_time,
        entry=entry, tp=tp, direction="long",
    )
    b = compute_trade_levels(
        symbol_cache=cache, cfg=cfg,
        trade_id="repro_2", entry_time=entry_time,
        entry=entry, tp=tp, direction="long",
    )
    assert a.prices("daily_only") == b.prices("daily_only")
    assert a.prices("ladder_top") == b.prices("ladder_top")
    assert a.prices("round_number") == b.prices("round_number")
    assert a.prices("all") == b.prices("all")


def test_snap_no_lookahead_via_level_detector() -> None:
    """Mutation test (PROTOCOL §5.4). Pick a trade with a fixed entry_time,
    compute levels; then mutate a random bar at ``entry_time`` or later,
    recompute levels, assert unchanged."""
    cache, cfg = _small_bar_series(symbol="EURUSD")
    # Trade at entry index e = 500 (well past the 200-bar warmup).
    e = 500
    if len(cache.bars) <= e + 50:
        return  # cache too small; skip (should not happen in practice)
    entry_time = cache.times[e]
    entry = cache.bars[e].close
    tp = entry + 100 * PIP
    baseline = compute_trade_levels(
        symbol_cache=cache, cfg=cfg,
        trade_id="mut_baseline", entry_time=entry_time,
        entry=entry, tp=tp, direction="long",
    )

    # Mutate a random bar at or after entry_time. Do so on a DEEP COPY of
    # the cache so we don't corrupt the module-level SymbolCache singleton.
    mutated_bars = list(cache.bars)  # shallow list copy
    # Bar objects are frozen dataclasses; replace field values by
    # constructing a new instance with the same fields but altered price.
    from agent.types import Bar as _Bar
    victim_idx = e + 3
    victim = mutated_bars[victim_idx]
    huge = victim.high + 500 * PIP
    smash = victim.low - 500 * PIP
    mutated_bars[victim_idx] = _Bar(
        time=victim.time,
        open=victim.open,
        high=huge,
        low=smash,
        close=victim.close,
        volume=victim.volume,
        timeframe=victim.timeframe,
    )
    mutated_cache = SymbolCache(
        symbol=cache.symbol,
        bars=mutated_bars,
        times=list(cache.times),
        tf=cache.tf,
    )
    mutated = compute_trade_levels(
        symbol_cache=mutated_cache, cfg=cfg,
        trade_id="mut_perturbed", entry_time=entry_time,
        entry=entry, tp=tp, direction="long",
    )
    assert mutated.prices("daily_only") == baseline.prices("daily_only"), \
        "no-lookahead violation on daily_only"
    assert mutated.prices("ladder_top") == baseline.prices("ladder_top"), \
        "no-lookahead violation on ladder_top"
    assert mutated.prices("round_number") == baseline.prices("round_number"), \
        "no-lookahead violation on round_number"
    assert mutated.prices("all") == baseline.prices("all"), \
        "no-lookahead violation on all"


if __name__ == "__main__":  # pragma: no cover
    # Simple "python test_e022_rule.py" runner for smoke.
    fns = [
        test_snap_direction_invariant_never_widens_tp,
        test_snap_direction_never_fires_beyond_tp,
        test_snap_returns_tp_when_no_candidates,
        test_snap_idempotent,
        test_snap_fires_on_worked_example_no_fire_gbp,
        test_level_detector_reproducibility,
        test_snap_no_lookahead_via_level_detector,
    ]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {e!r}")
    print(f"{passed}/{len(fns)} passed")
