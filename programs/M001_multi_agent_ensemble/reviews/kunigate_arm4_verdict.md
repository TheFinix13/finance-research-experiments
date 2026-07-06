# Phase X-kunigami Wild Card gate verdict (PROTOCOL sec 5)

Generated: 2026-07-06T20:27:20.464443+00:00

Baseline `phi5-arm4-post-kunigami` vs gated `kunigate-arm4`.

| metric | baseline | gated |
|---|---:|---:|
| worst-window max DD | 169.8% | 169.8% |
| median-of-window-mean TQS | 0.3643 | 0.3643 |
| trades | 7273 | 7272 |
| gate vetoes journalled | -- | 9 |

- DD relative reduction: **+0.0%** (LAND needs >= +20%)
- TQS delta: **+0.0000** (LAND tolerance -0.005; REVERT below -0.010)
- Trade retention: **100.0%** (LAND floor 60%; REVERT below 40%)

Checks: gate_ever_tripped=Y, dd_reduced_ge_20pct=n, tqs_within_tolerance=Y, trades_ge_60pct=Y, revert_trades_lt_40pct=n, revert_tqs_drop_gt_0.010=n

## VERDICT: **AMBIGUOUS**

## Per-window drawdown

| OOS window | baseline DD | gated DD | baseline n | gated n |
|---|---:|---:|---:|---:|
| 2019-01-01 | 79.2% | 79.2% | 614 | 614 |
| 2020-01-01 | 169.8% | 169.8% | 529 | 529 |
| 2021-01-01 | 147.4% | 147.4% | 670 | 670 |
| 2022-01-01 | 89.1% | 89.1% | 670 | 670 |
| 2023-01-01 | 35.7% | 35.7% | 608 | 608 |
| 2024-01-01 | 82.6% | 82.6% | 496 | 496 |
| 2025-01-01 | 46.1% | 46.1% | 483 | 483 |
