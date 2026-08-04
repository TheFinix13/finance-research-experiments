# E032 MANIFEST

| Item | Path / value |
|---|---|
| Protocol | `experiments/E032_with_trend_breakout_cell/PROTOCOL.md` (frozen 2026-08-04, commit `c838b28`; §6 empty — no amendments) |
| Stop notice | `experiments/E032_with_trend_breakout_cell/STOP_NOTICE.md` |
| Runner | `programs/E032/run_e032.py` |
| Tests | `programs/E032/tests/test_breakout_cell.py` (4 invariants: breakout fires + 1.5R geometry, impulse filter blocks, D1-bias gate blocks counter-trend, 10p stop floor) — all pass |
| Reused frozen code | Production D1-trend rule read-only via PYTHONPATH: `agent/alphas/concepts/_htf.py::htf_bias_at` (lookback 10, min-move 60p — deployed parameters); `agent/data/loader.BarLoader` |
| Results | `programs/E032/results_screen.json` (12 cells, full stats incl. 2× spread stress column) |
| Seeds | bootstrap 32 (10,000 reps) |
| Data | EURUSD/GBPUSD/USDCAD H4 2015-01-01 → 2021-12-31 (+90 d warmup), read-only parquet, refresh=False |
| ATR | SMA of true range, period 14 (granularity left open by protocol; declared here) |
| Verdict | **DEAD — stopped at Stage-1 go/no-go, 0/12 cells.** Confirm + sealed reservations released un-consumed |
| Claim grade | Entry-class screen. Closes the "missing the big moves" thesis under this operationalisation; motivating live week remains BURNT |
