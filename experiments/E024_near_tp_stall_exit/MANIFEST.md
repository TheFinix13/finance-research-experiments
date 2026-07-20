| Field | Value |
|---|---|
| ID | E024 |
| Short name | Near-TP stall exit (arm the detector once MFE enters the near-TP zone) |
| Pre-registration commit | (draft — awaiting user approval, then git log) |
| Status | **Phase 2 stage-1 complete · `dead`** (2026-07-20). Stage 2 cancelled per PROTOCOL §6 stop rule; Phase 3 live-agent wiring not authorised. See [`REPORT.md`](./REPORT.md) and [`STOP_NOTICE.md`](./STOP_NOTICE.md). |
| Direct motivator | User observation 2026-07-20 on GBPUSD short ticket **2969136564**: MFE 79.1p vs TP distance 79.6p (0.5p shy of take-profit), consolidated for hours, then reversed 36.5p off MFE. User-proposed study. |
| Study type | per-trade exit-mechanism study on the deployed `zone_d1_against` H4 all cell (does NOT touch the 1.5R TP itself) |
| Design shape | two-stage: **stage 1** sweeps the stall detector (24 arms) with `exit_action = close_at_market` fixed; **stage 2** sweeps `exit_action` (3 arms) with the winning stage-1 detector fixed |
| Stage-1 arms | `activation_R ∈ {1.30, 1.40, 1.45}` × { S1_wallclock × `stall_secs ∈ {900, 1800, 3600, 14400}` s ⇒ 4; S2_h1_range ⇒ 1; S3_h1_reversal ⇒ 1; S4_bar_stall_h1 ⇒ 1; S5_any_of_1-4 (S1 sub-timer locked at 3600 s) ⇒ 1 } = 3 × 14 = **24 arms** |
| Stage-2 arms | winning stage-1 `(activation_R, stall_signal[, stall_secs])` × `exit_action ∈ {close_at_market, move_stop_to_current, move_stop_to_mfe_minus_2p}` = **3 arms** |
| Stall signals (locked) | S1_wallclock (`now − mfe_ts ≥ stall_secs`); S2_h1_range (last 4 H1 closes inside ≤10-pip band); S3_h1_reversal (latest H1 close crosses back past prior 3-bar favourable extremum by ≥3 pips); S4_bar_stall_h1 (3 consecutive completed H1 bars without a new MFE extension); S5_any_of_1-4 (OR of the above with S1 sub-timer = 3600 s) |
| Symbols | EURUSD, GBPUSD, USDCAD |
| Timeframe / cell | H4 / `zone_d1_against` / all-session |
| Window | 2015-01-01 → 2025-12-01 (matches PRE-0 §2 and E017 §A1) |
| Walk-forward folds | 5 (PRE-0 §3, inherited from E004; no test-slice leakage) |
| Primary metric | **Δ Sharpe of per-trade R sequence** (arm − baseline), paired, bootstrap-95 % CI, seed 42, resamples 5000 |
| Secondary metrics | Δ mean R; Δ P(worse-than-stall-trigger) on the near-miss cohort; Δ mean R of the near-miss cohort; Δ tail-mean R (worst 10 %); Δ P(stall trigger fires); Δ P(false positive) (rule fires and observed path would have hit TP anyway); trades-touched-per-fold, TP-hits-eaten (operational context) |
| Data plane | Consumer of PRE-0 (`programs/_shared/counterfactual_replay/SPEC.md`) — requires `mfe_pips`, `mfe_ts`, `path_m5` (S1), `path_h1` (S2/S3/S4) |
| Verdict gate (`alive`) | Δ Sharpe CI-LB > 0 **AND** point > 0 on ≥ 4/5 folds **AND** Stouffer joint p < 0.05 **AND** BH-FDR α = 0.10 across 24-arm stage-1 family |
| Stage-2 authorisation | Runs **only if** ≥ 1 stage-1 arm is `alive`; otherwise study stops, keep deployed 1.5R TP, write `STOP_NOTICE.md` |
| Verdict labels (locked) | `alive`, `parked_low_yield`, `parked_false_positive_heavy` (special — winning arm's Δ P(false positive) > 50 %, requires user review before Phase 3), `dead` |
| Stop rule | 0 stage-1 arms `alive` at BH-FDR α = 0.10 → keep 1.5R TP, write `STOP_NOTICE.md`, no stage 1b, no grid extension |
| Phase 3 gate | production wiring proceeds **only** on an `alive` verdict (and, if applicable, explicit user sign-off on any `parked_false_positive_heavy` trade-off) |
| Live-implementability posture (H2 parsimony) | S1_wallclock ties any bar-based signal → prefer S1 (drop-in feasible on the current 5 s poll: capture `mfe_ts` at the update site in `PositionMonitor._track_excursion`, then check `now − mfe_ts` per poll). S2/S3/S4 require new intraday-polling infrastructure in the live agent — a follow-up dev task, not blocking this study. |
| Anti-overfit | single pre-registered primary; frozen discrete 24-arm grid at stage 1 + 3-arm grid at stage 2; BH-FDR + PBO + deflated statistic on the selected arm; per-symbol survival (E005 posture, not pooled-across-symbols averaging); negatives reported |
| Separation | no live-path touch in Phase 1–2; Phase 3 (if `alive`) adds one `mfe_ts` capture line in `_track_excursion` and one exit-priority hook (per SPEC §4.3, above broker TP hit and below hard SLs); Phase 3 is a separate, gated `multi-pair-trading-agent` deliverable |
| Key references (existing in `reviews/refs.bib`) | benjamini1995controlling, bailey2014deflated, bailey2014pseudo, harvey2016cross, nosek2018preregistration, efron1993bootstrap, lopezdeprado2018 |
| References to add before REPORT | bailey2016pbo (PBO across 24-arm family); stouffer1949american (Stouffer's Z fold-p combiner, or a methods-textbook substitute if preferred) |
| Ex-post narrative (illustrative, n=1 each; NOT statistical claims) | Case A — GBPUSD 2969136564 (motivating "good miss"); Case B — GBPUSD 2966547972 (clean-TP false-positive check under the same arm; branch B1/B2 resolved by PRE-0 path in the REPORT) |

## Verdict

**Verdict:** `dead` (2026-07-20) · **Stage 2:** cancelled per PROTOCOL §6 stop rule · **Phase 3:** not authorised.

| Metric | Value |
|---|---|
| Study verdict | `dead` |
| (arm, symbol) cells at `alive` | 0 / 72 |
| (arm, symbol) cells at `parked_low_yield` | 0 / 72 |
| (arm, symbol) cells at `parked_false_positive_heavy` | 0 / 72 |
| (arm, symbol) cells at `dead` | 72 / 72 |
| EURUSD ΔSharpe range (24 arms) | [−0.0852, −0.0936] |
| GBPUSD ΔSharpe range (24 arms) | [−0.0839, −0.0948] |
| USDCAD ΔSharpe range (24 arms) | [−0.1327, −0.1448] |
| BH-FDR rejected (in direction of DEGRADATION) | EURUSD 22/24; GBPUSD 24/24; USDCAD 24/24 |
| Δ P(false positive) — range across all 72 cells | [0.630, 0.909] |
| Δ P(false positive) on anchor arm (a=1.45, S1, s=3600) per symbol | EURUSD 0.810; GBPUSD 0.786; USDCAD 0.714 |
| Δ tail-mean R (worst 10 %) — near-uniform across arms | ≈ +1.00 R (real, but dominated by runner-choke cost) |
| Δ mean R on near-miss cohort (anchor arm) per symbol | EURUSD −0.479; GBPUSD −0.508; USDCAD −0.553 |
| Runtime (bootstrap seed 42, 5000 resamples, 24 × 3 arms) | ≈ 39 s |
| Deliverables on branch `main` | `programs/E024/{stall_signals.py, run_e024_validation.py, results.json, tests/test_e024_signals.py}`; `experiments/E024_near_tp_stall_exit/{REPORT.md, STOP_NOTICE.md}` |

Mechanism (from `REPORT.md` §5): the stall detector caps the worst-decile
tail at −1.00 R (real +1 R gain on the ≈ 20–160 rescued trades) but
eats **60–91 % of clean-TP wins** on the near-miss cohort. In the
strict `mfe_r ∈ [1.45, 1.50]` band on PRE-0 GBPUSD, clean TPs outnumber
near-miss give-backs by ~44:1 — any detector armed in that zone is
almost guaranteed to fire on a majority of eventual TPs. This is the
E020 pathology's mirror image (E020's runner-choke; E024's
false-positive-heavy); both die on the deployed cell's 1.5R TP
geometry.

Study stopped per PROTOCOL §6. Keep the deployed 1.5R TP unchanged; no
stage 2, no grid extension, no post-hoc primary swap.
