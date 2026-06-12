"""Stage-2 conditional-pair harness contracts."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import synthetic_frame
from conflab.events import Event
from conflab.stage2 import Stage2Config, run_stage2, screen_pair


def _events_from_frame(df, every: int, direction: int, etype: str):
    return [Event(i, str(df.index[i]), etype, direction,
                  float(df["close"].iloc[i]))
            for i in range(70, len(df) - 30, every)]


def test_screen_pair_well_formed():
    ctx_df = synthetic_frame(400, seed=11, tf_hours=24)
    setup_df = synthetic_frame(2400, seed=12, tf_hours=4)
    ctx_events = _events_from_frame(ctx_df, 25, +1, "ctx_evt")
    setup_events = _events_from_frame(setup_df, 15, +1, "setup_evt")
    cfg = Stage2Config(n_draws=200, seed=5)
    rng = np.random.default_rng(cfg.seed)
    row = screen_pair(ctx_events, ctx_df, "D1", setup_events, setup_df,
                      "H4", cfg, rng)
    assert row is not None
    assert row["n_joint"] > 0
    assert 0.0 < row["p_value"] <= 1.0
    assert row["joint_mfe_atr"] >= 0.0


def test_run_stage2_orders_pairs_high_to_low_tf_only():
    frames = {"D1": synthetic_frame(400, seed=11, tf_hours=24),
              "H4": synthetic_frame(2400, seed=12, tf_hours=4)}
    events_by_cell = {
        ("D1", "ctx_evt"): _events_from_frame(frames["D1"], 25, +1,
                                              "ctx_evt"),
        ("H4", "setup_evt"): _events_from_frame(frames["H4"], 15, +1,
                                                "setup_evt"),
    }
    survivors = [
        {"tf": "D1", "event_type": "ctx_evt"},
        {"tf": "H4", "event_type": "setup_evt"},
    ]
    rows = run_stage2(survivors, frames, events_by_cell,
                      Stage2Config(n_draws=150, seed=5, min_joint=5))
    # Only D1-context × H4-setup is a legal ordered pair.
    assert len(rows) == 1
    assert rows[0]["context"] == "D1:ctx_evt"
    assert rows[0]["setup"] == "H4:setup_evt"
    assert rows[0]["verdict"] in {"alive", "parked_weak_effect",
                                  "parked_insufficient_n", "dead"}
