# E031 MANIFEST

| Item | Path / value |
|---|---|
| Protocol | `experiments/E031_slot_blocking_position_cap/PROTOCOL.md` (frozen 2026-08-04, commit `c838b28`; §6 empty — no amendments) |
| Stop notice | `experiments/E031_slot_blocking_position_cap/STOP_NOTICE.md` |
| Runner | `programs/E031/run_e031.py` |
| Tests | `programs/E031/tests/test_slot_sim.py` (6 invariants: cap enforcement, conflict counting, B1 replace-losing fires, B2 same-direction gate, winning incumbent kept, SL-first tie-break + cost arithmetic) — all pass |
| Reused frozen code | Production detector read-only via PYTHONPATH: `agent/alphas/concepts/zone_alpha.py` (`SupplyDemandAlpha`, htf_align=D1/against/10/60p), `agent/rules/engine.precompute`, `agent/data/loader.BarLoader` |
| Results | `programs/E031/results_screen.json` (baseline + 4 arms, full stats) |
| Seeds | bootstrap 31 (block 20 d, 5,000 reps) |
| Data | EURUSD/GBPUSD/USDCAD H4 2015-01-01 → 2021-12-31 (+365 d warmup prefix for zone/HTF state), read-only parquet, refresh=False |
| Signal stream | 1,341 / 2,061 / 1,423 signals (EURUSD/GBPUSD/USDCAD), detector driven at every bar close |
| Verdict | **DEAD — stopped at Stage-1 go/no-go, 0/4 arms.** Confirm + sealed reservations released un-consumed |
| Claim grade | Portfolio-mechanics, screen-grade reconstruction. Production `max_open_positions` unchanged |
