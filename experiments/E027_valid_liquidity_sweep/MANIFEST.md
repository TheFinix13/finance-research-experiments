# E027 evidence manifest

| Artefact | Path / commit |
|---|---|
| Pre-registration | `experiments/E027_valid_liquidity_sweep/PROTOCOL.md` @ `cdb7a01` |
| Amendment §7 A1 (loader) | @ `6722012`, before any statistic |
| Detector (frozen) | `programs/E027/sweep_validity.py` @ `6722012` |
| Runner | `programs/E027/run_e027_validation.py` @ `6722012` |
| Unit tests (5, passing) | `programs/E027/tests/test_sweep_validity.py` |
| Stage-1 registry | `output/E027_valid_liquidity_sweep/stage1_EURUSD_screen_2026-07-28_1716.jsonl` |
| Stage-1 run log | `output/E027_valid_liquidity_sweep/stage1_run.log` |
| Stop files | `output/E027_valid_liquidity_sweep/stage{2,3}_E027_stop.json` |
| Data | `multi-pair-trading-agent/data/parquet/EURUSD_{H1,H4}.parquet`, read-only, sliced 2015-01-01 → 2021-12-31 |
| Seeds | Stage 1: 27 (as pre-registered) |
| Report | `experiments/E027_valid_liquidity_sweep/REPORT.md` |
