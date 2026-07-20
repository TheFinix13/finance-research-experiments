| Field | Value |
|---|---|
| ID | E022 |
| Short name | Structure-aware TP snap (order-placement) |
| Pre-registration commit | (draft — awaiting user approval, then git log) |
| Status | **Phase 2 complete — verdict `dead` (2026-07-20).** See `REPORT.md` and `STOP_NOTICE.md`. Phase 3 not initiated. |
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
| Reuse | consumer of PRE-0 harness (`programs/_shared/counterfactual_replay/`); read-only reference to production `signal_loop.py` and `target_ladder.py`; new module `programs/E022/level_detector.py` implements the reconstruction (imports `agent.detectors.*` and `agent.rules.engine.precompute` read-only; does NOT import `agent/journal/target_ladder.py::compute_target_ladder`) |
| Key references (existing) | benjamini1995controlling, harvey2016cross, bailey2014deflated, bailey2014pseudo, lopezdeprado2018, lopezdeprado2018tactical, efron1993bootstrap, nosek2018preregistration, chan2009quantitative |
| References to add before REPORT | osler2003currency (FX order clustering — load-bearing), sonnemans2006price (cross-asset price clustering), chengwilym2007round (round-number effect corroboration, exact citation to be confirmed by coordinator) |

## Verdict

**`dead`** — 2026-07-20. Phase 2 executed against the frozen §4.1 grid;
0 arms alive.

**Winning arms:** none.

**Arm-level classification (12 arms):**

- `dead` (11): every arm except `ladder_top_d5`. Pooled ΔSharpe in
  `[−0.028, −0.001]`. Seven of them BH-FDR α = 0.10 survivors in the
  direction of **degradation** (`daily_only_d10/d15`, `ladder_top_d15`,
  `round_number_d10/d15`, `all_d10/d15`).
- `inactive_snap_never_fires` (1): `ladder_top_d5`. Pooled ΔSharpe
  point +0.0006 but `snap_fire_rate = 3.02 %` < 5 % floor → fails
  PROTOCOL §H3 feasibility. Not `alive`; not counted as evidence for
  `parked_snap_never_fires` (family-level H3 requires **every** arm to
  fire < 5 %; only 1 / 12 does).

**Study-level outcome:** `dead`. Not `parked_snap_never_fires`
(only 1/12 arms fires < 5 %), not `parked_daily_only_suffices`
(no `alive` arm exists to compare parsimony), not
`parked_weak_effect` (no arm has positive CI-LB with weak evidence
elsewhere; the one positive point-estimate arm fails the feasibility
floor). Every remaining pooled point estimate is negative.

**Headline mechanism read (largest-firing arm, `all_d15`):**

- fire_rate 52.1 %, ΔP(TP fills) +3.48 pp (mechanism sanity: PASS)
- Δ mean R \| winner = −0.106 R (predicted expected slight negative:
  yes, but larger than expected)
- Δ mean time-in-trade \| winner = −4 h (~−1 H4 bar; predicted
  expected slight negative: yes)
- ΔSharpe = **−0.028** with CI [−0.041, −0.014], p = 0.0000 — the R
  cost per winner dominates the fill-rate gain

**Follow-up posture:** keep the shipped mechanical placement. Do not
extend the grid, do not adjust `snap_offset` post-freeze, do not
re-run Phase 2 with a modified rule spec (that would be a NEW
pre-registration, E022b or fresh ID). Unblocks E024 (near-TP stall
exit, exit-side different mechanism) and E025 (joint stack, minus
E022 as a stack component). See [`STOP_NOTICE.md`](./STOP_NOTICE.md)
for the full stop rationale and family-multiplicity impact on E025.

**Deliverables landed in this Phase-2 tree:**

- [`../../programs/E022/level_detector.py`](../../programs/E022/level_detector.py)
- [`../../programs/E022/rescorer.py`](../../programs/E022/rescorer.py)
- [`../../programs/E022/run_e022_validation.py`](../../programs/E022/run_e022_validation.py)
- [`../../programs/E022/results.json`](../../programs/E022/results.json)
- [`../../programs/E022/tests/test_e022_rule.py`](../../programs/E022/tests/test_e022_rule.py) (7 / 7 pass)
- [`REPORT.md`](./REPORT.md), [`STOP_NOTICE.md`](./STOP_NOTICE.md), this MANIFEST
