# E030 MANIFEST

| Item | Path / value |
|---|---|
| Protocol | `experiments/E030_london_continuation/PROTOCOL.md` (frozen 2026-07-28, commit `36328ab`; §5 empty — no amendments) |
| Report | `experiments/E030_london_continuation/REPORT.md` |
| Day logic | `programs/E030/continuation_days.py` (commit `3e90cf4`; delegates classification to `programs/E028/po3_days.py` @ `6722012`) |
| Runner | `programs/E030/run_e030_validation.py` |
| Tests | `programs/E030/tests/test_continuation_days.py` — 4 pass, incl. E028 classifier equivalence |
| Stage-1 results | `output/E030_london_continuation/stage1_EURUSD_lock_2026-07-28_1813.json` |
| Stop files | `output/E030_london_continuation/stage{2,3,4}_E030_stop.json` |
| Seed | 30 (Stages 2–4 never run) |
| Data | EURUSD M15 2015-01-01→2021-12-31 only (Stage-1 lock, taint declared); Stages 2–4 slices untouched; sealed reservation released |
| Verdict | **STOPPED at Stage 1 go/no-go** — SHORT arm mean −1.38 pips at base costs |
