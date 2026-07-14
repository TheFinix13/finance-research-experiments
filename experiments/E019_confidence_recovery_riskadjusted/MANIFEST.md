| Field | Value |
|---|---|
| ID | E019 |
| Short name | Risk-adjusted confidence recovery (redesign of parked E017) |
| Pre-registration commit | (draft — awaiting user approval, then git log) |
| Status | **Phase 2 COMPLETE 2026-07-14 → verdict `dead` / STOP** (Phase 3 blocked; keep shipped AK) |
| Verdict | `dead` — no frozen config beats AK on `RaC_β` in any of 6 DGP×ρ cells (best GR-S `RaC_β` ≈ 0.03–0.10 vs AK ≈ 11.6–15.5); GR-S is safer (lower DD/CDaR/ruin) but its AnnRet collapses to ≈0.2%/yr so return-per-drawdown is ≈0. See `REPORT.md` / `STOP_NOTICE.md`. |
| Study type | risk/execution-mechanism (not an alpha study) |
| Predecessor | E017 (`parked_capital_cost` — scored on raw terminal equity) |
| Core fix | replace terminal-equity gate with a **risk-adjusted** primary metric |
| Primary metric | **CDaR-adjusted return** `RaC_β = AnnRet / CDaR_β`, β = 0.95 |
| Secondary metrics | Calmar, Sharpe, worst-path max DD, risk-of-ruin, time-to-resume, opportunity cost |
| Baseline | **AK** = shipped 2026-07-14 daily-DD auto-clear (re-arm at UTC rollover; sticky-escalate after 3 days) — NOT E017's 48 h-blind HK |
| Arms | AK (baseline) · GR-S (graduated + risk-adjusted shadow recovery) · GR-T (time-decay control) |
| Recovery laws (frozen) | {R-riskadj, R-kelly} × gauge {G-surplus, G-cdar} = 4 configs × {GR-S, GR-T} |
| Validation panel | synthetic MC (N=10,000, 11k-day horizon) + 2026-07-08 incident replay (n=1, descriptive) |
| Verdict gate | GR-S beats AK on `RaC_β` (CI-LB > AK point) with DD/ruin/time-to-resume guardrails, both DGPs, both ρ |
| Acceptable outcomes | `alive`, `parked_baseline_sufficient` (H3), `parked_shadow_adds_nothing` (H2), `parked_capital_cost`, `dead` |
| Stop rule | 0 configs `alive` at Phase-2 end → keep AK, write `STOP_NOTICE.md`, no grid extension |
| Phase 3 gate | production wiring proceeds ONLY on an `alive` verdict |
| Anti-overfit | single pre-registered primary; frozen discrete grid; BH-FDR + PBO + deflated stat; two DGPs must agree; negatives reported |
| Key references (existing) | chekhlov2005drawdown, busseti2016kelly, kelly1956, grossman1993drawdowns, klass2005grossmanzhou, maillard2010erc, chen2024darkside, subrahmanyam1994circuit, bailey2016pbo, bailey2014deflated, benjamini1995controlling, harvey2016cross, nosek2018preregistration, chan2009quantitative |
| References to add before REPORT | sharpe1966/sharpe1994 (Sharpe), young1991 / magdon2004maximumdrawdown (Calmar/drawdown ratio) |
