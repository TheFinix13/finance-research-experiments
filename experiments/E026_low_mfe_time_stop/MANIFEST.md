# E026 — Manifest

| Field | Value |
|---|---|
| ID | E026 |
| Short name | Low-MFE time-stop — close trades that never "get going" (age ≥ B bars with MFE < P) |
| Pre-registration commit | (this commit — PROTOCOL.md frozen before Phase-2 execution) |
| Status | (set at verdict) |
| Direct motivator | User directive 2026-07-28 (weekly v1 review): GBPUSD 3000652586 held 4+ days / USDCAD 2987854368 held 7+ days, both range-trapped below 1R MFE; user proposed a per-trade time limit plus a "health points" vitality meter. Stage 1 tests the time limit; the meter is stage 2, gated. |
| Study type | per-trade exit-mechanism study on the deployed `zone_d1_against` H4 all cell (does NOT touch the 1.5R TP) |
| Design shape | two-stage: **stage 1** = 15-arm time-stop grid with `exit_action = close_at_market` fixed; **stage 2** (health-meter controller) gated on ≥ 1 stage-1 alive cell, requires a fresh §7 amendment |
| Stage-1 arms | `P ∈ {0.25, 0.50, 0.75}` × `B ∈ {12, 18, 24, 30, 42}` H4 bars = **15 arms** |
| Firing condition | first bar with `bars_held ≥ B` AND `mfe_r_so_far < P`; permanent exemption once MFE touches P; close at bar close |
| Cohort-separation argument | can only fire while `mfe_r < 0.75` — structurally disjoint from the near-TP zone that killed E020 (runner-choke) and E024 (78 % clean-TP false positives); engine state-order makes a same-bar-TP fire impossible |
| Symbols | EURUSD, GBPUSD, USDCAD |
| Window / folds | 2015-01 → 2025-12, five PRE-0/E004 walk-forward folds |
| Primary metric | paired Δ Sharpe of per-trade R sequence, bootstrap-95 % CI, seed 42, 5000 resamples |
| Secondary guardrails | Δ tail-mean R (worst 10 %); Δ P(fire); Δ P(false positive) (fires on baseline-TP trades, park threshold 0.50); Δ P(rescued) (fires on baseline-SL trades); Δ mean R fired cohort; Δ mean bars-held (descriptive capital-efficiency read, never a verdict criterion) |
| Verdict gate (`alive`) | ΔSharpe CI-LB > 0 AND ≥ 4/5 folds positive AND Stouffer joint p < 0.05 AND BH-FDR α = 0.10 (per-symbol 15-arm family) AND ΔP(FP) ≤ 0.50 |
| Stop rule | 0 alive cells → STOP_NOTICE.md, no stage 2 (health meter not pursued in this form), no grid extension, no post-hoc promotion of Δ bars-held |
| Data plane | PRE-0 ledgers unchanged; H4 path resolution is FULL fidelity for this rule (bar-count clock; ≤ 4 h intra-bar ambiguity ≪ min B = 48 h) |
| Intake provenance | `multi-pair-trading-agent` `company/rd/intake/I021-time-boxed-trades-health-meter.md` |
| Deliverables | `experiments/E026_low_mfe_time_stop/{PROTOCOL,MANIFEST,REPORT or STOP_NOTICE}.md`; `programs/E026/{time_stop_rule.py, run_e026_validation.py, results.json, tests/}` |
