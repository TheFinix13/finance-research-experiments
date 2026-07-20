| Field | Value |
|---|---|
| ID | E022 |
| Short name | Structure-aware TP snap (order-placement) |
| Pre-registration commit | (draft — awaiting user approval, then git log) |
| Status | pre-registered (Phase 1 of 3); Phase 2 validation not yet run |
| Study type | order-placement rule (single-parameter TP-price adjustment at entry time; no exit-manager change, no entry-signal change, no lifetime replay) |
| Motivating case | GBPUSD live ticket 2969136564 (2026-07-16 short) — MFE 79.1 p vs TP-distance 79.6 p, missed by 0.5 p |
| Rule | at placement, if a "sticky" level from `snap_source` lies between entry and TP within `snap_distance` pips of TP, pull TP inside that level by `snap_offset = min(3, snap_distance/2)` pips (inward-only, direction invariant §3.2) |
| Arms | 12 = `snap_distance ∈ {5,10,15}` × `snap_source ∈ {daily_only, ladder_top, round_number, all}` |
| Level sources | daily_only = PDH/PDL/PDM/PWH/PWL/PWM; ladder_top = nearest-to-entry rung of reconstructed extension ladder (swing/zone_edge/trendline/fib_ext/daily_level detectors from `agent/journal/target_ladder.py`, no beyond-TP filter); round_number = every `.00`/`.50` sub-figure between entry and TP; all = union with 3-pip dedupe |
| Ladder availability gap | **Option (a) reconstruction chosen.** Levels are reconstructed from bar-level OHLC over `[entry_time − 200·H4, entry_time)` using the locked §4 detector parameters (mirrors `compute_target_ladder(lookback=200, trendline_lookahead=20, dedupe_pips=3.0, max_rungs=6)`). Applies uniformly to every trade in the 2015-01 → 2025-12 window. Rationale: option (b) sub-window post-2026-06 has < 2 % of trade count (insufficient for 5-fold walk-forward), and the production ladder returns rungs strictly beyond TP anyway (unusable for E022's between-entry-and-TP filter). |
| Primary metric | **ΔSharpe** of per-trade R sequence (paired, bootstrap-95 % CI, 5,000 resamples, seed 42), pooled across symbols with fixed-effects weight ∝ per-symbol trade count on each fold's test slice |
| Secondary metrics | Δ P(TP fills), Δ mean R \| winner, Δ mean time-in-trade \| winner, snap_fire_rate (feasibility gate for `parked_snap_never_fires`) |
| Baseline | deployed cell's unmodified mechanical TP placement (`entry ± target_rr · stop_pips`, no snap) |
| Validation panel | PRE-0 counterfactual replay ({EURUSD, GBPUSD, USDCAD}_H4_paths.jsonl), 5-fold walk-forward (SPEC §3), 2015-01 → 2025-12 |
| Verdict gate | ΔSharpe pooled CI-LB > 0 AND positive-in-≥ 4/5 folds AND BH-FDR α = 0.10 (12-arm family) AND snap_fire_rate ≥ 5 % AND Δ P(TP fills) > 0 |
| Acceptable outcomes | `alive`, `parked_daily_only_suffices` (H2 parsimony), `parked_snap_never_fires` (H3 first-class negative — cell already places TPs off sticky levels), `parked_weak_effect`, `dead` |
| Stop rule | 0 arms `alive` at Phase-2 end → keep unmodified placement, write `STOP_NOTICE.md`, no grid extension, no post-freeze `snap_offset` tuning |
| Phase 3 gate | production wiring in `agent/live/signal_loop.py::SignalLoop._route_signal` proceeds ONLY on an `alive` verdict, through the agent's full validation chain |
| Direction invariant | snap only fires on levels strictly between entry and TP (§3.2); pulls TP inward only, never outward — unit-tested in Phase 2 |
| Anti-overfit | single pre-registered primary (ΔSharpe); frozen 12-arm discrete grid; `snap_offset` pinned as a function of `snap_distance` (not an arm); no continuous tuning; no post-freeze grid extension; no-look-ahead mutation test; BH-FDR + walk-forward + deflated statistic on the winner; negatives reported |
| Reuse | consumer of PRE-0 harness (`programs/_shared/counterfactual_replay/`); read-only reference to production `signal_loop.py` and `target_ladder.py`; new module `programs/E022/level_detector.py` (or shared `programs/_shared/level_detector.py` if delivered first) — not written in Phase 1 |
| Key references (existing) | benjamini1995controlling, harvey2016cross, bailey2014deflated, bailey2014pseudo, lopezdeprado2018, lopezdeprado2018tactical, efron1993bootstrap, nosek2018preregistration, chan2009quantitative |
| References to add before REPORT | osler2003currency (FX order clustering — load-bearing), sonnemans2006price (cross-asset price clustering), chengwilym2007round (round-number effect corroboration, exact citation to be confirmed by coordinator) |
