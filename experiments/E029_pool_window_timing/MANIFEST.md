# E029 MANIFEST

| Item | Path / value |
|---|---|
| Protocol | `experiments/E029_pool_window_timing/PROTOCOL.md` (frozen 2026-07-28, commit `36328ab`; §7 empty — no amendments) |
| Report | `experiments/E029_pool_window_timing/REPORT.md` |
| Runner | `programs/E029/run_e029_validation.py` (commit `3e90cf4`) |
| Reused frozen code | `scripts/E010/run_e010.py` helpers @ `a159ec1`; `conflab/stage2.py::screen_pair`, `_mfe_table`; `conflab/stats.py::benjamini_hochberg` |
| Stage-1 registry | `output/E029_pool_window_timing/stage1_GBPUSD_screen_2026-07-28_1818.jsonl` (10 rows) |
| Stage-2 registry | `output/E029_pool_window_timing/stage2_EURUSD_sealed_2026-07-28_1818.jsonl` (8 rows) |
| Seeds | Stage 1: 29 · Stage 2: 129 |
| Data | GBPUSD H1+M15 2015-01-01→2021-12-31 (screen); EURUSD H1+M15 2025-01-01→2026-05-27 (sealed, consumed once) — direct read-only parquet |
| Verdict | **ALIVE at sealed** — `bullish_fvg_touch`, `trendline_support_touch`; 1 parked_weak_effect; 5 parked_insufficient_n; 2 dead at Stage 1 |
| Claim grade | Timing primitive, screen-grade (MFE, cost-free). NOT tradable expectancy. |
