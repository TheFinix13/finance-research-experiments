| Field | Value |
|---|---|
| ID | E020 |
| Short name | MFE-ratcheted trailing stop |
| Pre-registration commit | _(fill after pre-reg commit lands)_ |
| Status | pre-registered (Phase 1 of 3); Phase 2 validation not yet run |
| Study type | exit-mechanism (not an alpha study) |
| Motivating trade | GBPUSD ticket 2969136564 (entered 2026-07-16 short 1.35060, TP 1.34264, MFE 79.1 p, retraced 36.5 p — see `PROTOCOL.md` motivation + §5.5 illustrative replay) |
| Primary artefacts | `PROTOCOL.md`, `MANIFEST.md`, `results.json` (placeholder until Phase 2), `REPORT.md` (Phase 2), `STOP_NOTICE.md` (if `dead`) |
| Data plane | consumes `programs/_shared/counterfactual_replay/SPEC.md` (PRE-0) — path ledgers for EURUSD, GBPUSD, USDCAD H4 (2015-01 → 2025-12) via `replay()` engine, unmodified |
| Baseline | E013 `all_on` cell — wick-proof SL + BE-at-1 R + PLG, ratchet **off** — same trade population, same paths, ratchet is the single mechanism delta |
| Arms | 12-arm 3-D grid: `activation_R` × `lock_fraction` = {1.0, 1.2, 1.3} × {0.4, 0.5, 0.6, 0.7} (frozen §4.1) |
| Ratchet rule | on any bar with `mfe_R ≥ activation_R`, set effective stop to `entry ± lock_fraction × MFE_current`; monotone tightening only; BE-at-1 R kept as a floor; exits priority per SPEC §4.3 (fires after broker TP on same bar) |
| Validation panel | per-trade counterfactual replay via PRE-0 engine on all three symbols; 5-fold walk-forward mirroring E004 / SPEC §3; paired per-trade ΔR sequence |
| Primary metric | ΔSharpe of per-trade R sequence (paired) — per fold and pooled, bootstrap-95 % CI, seed 42, 5000 resamples |
| Secondary metrics | Δ mean R; Δ P(winner reaches ≥ 1 R); Δ tail-mean R (worst 10 %); Δ max-consecutive-loss streak; `n_fired_no_reach` (ratchet fired without TP reach) |
| Verdict gate (`alive`) | pooled ΔSharpe CI-LB > 0 **AND** positive in ≥ 4 of 5 folds **AND** joint bootstrap p < 0.05 **AND** BH-FDR α = 0.10 survivor **AND** tail-mean/streak guardrails clear |
| FDR | Benjamini–Hochberg at α = 0.10 across the 12-arm family |
| Acceptable outcomes | `alive`, `parked_low_yield` (positive point estimate, CI includes 0 OR positive in 3 folds OR fails BH-FDR), `parked_capital_cost` (wins Sharpe, breaches tail/streak guardrail), `dead` |
| Stop rule | 0 arms `alive` at Phase-2 end → keep the shipped `all_on` cell, write `STOP_NOTICE.md`, no grid extension, no post-hoc primary swap |
| Parsimony tie-break (H2) | inside `alive` set only: tied Sharpe across `lock_fraction` → prefer higher; tied across `activation_R` → prefer higher (fires less, disturbs fewer runners) |
| Phase 3 gate | production wiring (new `Ratchet` stop-move handler in `PositionMonitor` + config flag) proceeds ONLY on an `alive` verdict |
| Anti-overfit | single pre-registered primary; frozen 12-arm discrete grid; BH-FDR + selection-context reporting; no post-freeze retuning; case study is descriptive only (n = 1, not an FDR family member); negatives reported |
| Key references (existing, in `reviews/refs.bib`) | benjamini1995controlling, bailey2014deflated, bailey2014pseudo, harvey2016cross, efron1993bootstrap, chan2009quantitative, nosek2018preregistration, lopezdeprado2018tactical |
| References to add before REPORT (parent to add centrally — **not** edited here) | `kaminski2014trend` (Kaminski & Lo 2014, "When do stop-loss rules stop losses?", *Journal of Financial Markets* 18, 234–254) — MFE-based trailing exit rationale; `shefrin1985disposition` (Shefrin & Statman 1985, "The disposition to sell winners too early and ride losers too long", *Journal of Finance* 40 (3), 777–790) — behavioural motivation for the give-back phenomenon; `odean1998losers` (Odean 1998, "Are investors reluctant to realize their losses?", *Journal of Finance* 53 (5), 1775–1798) — empirical counterpart |
