# E028 evidence manifest

| Artefact | Path / commit |
|---|---|
| Pre-registration | `experiments/E028_power_of_three_sessions/PROTOCOL.md` @ `cdb7a01` |
| Amendment §7 A1 (loader) | @ `6722012`, before any statistic |
| Day classifier (frozen) | `programs/E028/po3_days.py` @ `6722012` |
| Runner | `programs/E028/run_e028_validation.py` @ `6722012` |
| Unit tests (6, passing) | `programs/E028/tests/test_po3_days.py` |
| Stage-1 results (D1–D6 + 2 cells) | `output/E028_power_of_three_sessions/stage1_EURUSD_screen_2026-07-28_1716.json` |
| Stop files | `output/E028_power_of_three_sessions/stage{2,3}_E028_stop.json` |
| Data | `multi-pair-trading-agent/data/parquet/EURUSD_M15.parquet`, read-only, sliced 2015-01-01 → 2021-12-31 |
| Seeds | Stage 1: 28 (as pre-registered); bootstrap B = 10,000 |
| Report | `experiments/E028_power_of_three_sessions/REPORT.md` |
