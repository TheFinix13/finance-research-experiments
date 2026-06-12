"""Level extraction, clustering and scoring contracts."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.confluence import cluster_levels, top_bands
from conflab.data import synthetic_frame
from conflab.levels import Level, extract_levels


def _lv(price: float, source: str = "swing_high", tf: str = "H4",
        weight: float = 1.0) -> Level:
    return Level(price=price, source=source, timeframe=tf, weight=weight)


def test_extract_levels_returns_finite_prices():
    df = synthetic_frame(400, seed=3)
    levels = extract_levels(df, "H4")
    assert levels, "no levels extracted from synthetic data"
    assert all(np.isfinite(lv.price) for lv in levels)
    sources = {lv.source for lv in levels}
    assert {"bb_upper", "bb_lower", "ema50"} <= sources
    assert any(s.startswith("swing") for s in sources)


def test_clustering_merges_within_tolerance_only():
    levels = [_lv(1.1000), _lv(1.1003), _lv(1.1050)]
    bands = cluster_levels(levels, tolerance=0.0010)
    assert len(bands) == 2
    assert bands[0].n_members == 2
    assert bands[1].n_members == 1


def test_score_rewards_multi_source_and_multi_tf():
    same_source = cluster_levels(
        [_lv(1.1000), _lv(1.1001)], tolerance=0.001)[0]
    multi_source = cluster_levels(
        [_lv(1.1000), _lv(1.1001, source="zone_edge")], tolerance=0.001)[0]
    multi_tf = cluster_levels(
        [_lv(1.1000), _lv(1.1001, source="zone_edge", tf="D1")],
        tolerance=0.001)[0]
    assert multi_source.score > same_source.score
    assert multi_tf.score > multi_source.score


def test_top_bands_filters_singletons_and_ranks():
    levels = [_lv(1.1000), _lv(1.1001, source="zone_edge", tf="D1"),
              _lv(1.2000)]
    ranked = top_bands(cluster_levels(levels, tolerance=0.001))
    assert len(ranked) == 1
    assert ranked[0].n_members == 2


def test_empty_and_zero_tolerance():
    assert cluster_levels([], tolerance=0.001) == []
    assert cluster_levels([_lv(1.1)], tolerance=0.0) == []
