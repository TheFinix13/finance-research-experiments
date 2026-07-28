# E010 evidence manifest

| Artefact | Path / commit |
|---|---|
| Pre-registration | `experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md` @ `fd8eb3d` (2026-06-24) |
| Amendments §7 A1/A2 + runner | @ `a159ec1` (2026-07-28, before any statistic) |
| Stage-0 count diagnostic | `scripts/E010/diagnose_counts.py`; output `output/E010_equal_highs_pool_stage2b/stage0_counts_2026-07-28_1723.json` |
| Stage runner | `scripts/E010/run_e010.py` |
| Stage-1 registry | `output/E010_equal_highs_pool_stage2b/stage1_EURUSD_screen_2026-07-28_1724.jsonl` |
| Stage-2 registry | `output/E010_equal_highs_pool_stage2b/stage2_EURUSD_confirm_2026-07-28_1730.jsonl` |
| Run logs | `output/E010_equal_highs_pool_stage2b/stage{0,1,2}_run.log` |
| Stop files | `output/E010_equal_highs_pool_stage2b/stage{3,4}_E010_stop.json` |
| Reused primitives | `conflab/` per PROTOCOL §0 (detectors, `screen_pair`, `_mfe_table`, BH-FDR) |
| Data | `multi-pair-trading-agent/data/parquet/EURUSD_{H1,M15}.parquet`, read-only; screen 2015–2021, confirm 2022–2024; Stage-3/4 slices not consumed |
| Seeds | Stage 1: 42 · Stage 2: 142 (as pre-registered); n_perm 5,000 |
| Report | `experiments/E010_equal_highs_pool_stage2b/REPORT.md` |
