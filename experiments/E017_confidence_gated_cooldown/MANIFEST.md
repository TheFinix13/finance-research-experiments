| Field | Value |
|---|---|
| ID | E017 |
| Short name | Confidence-gated cooldown vs. binary kill-switch |
| Pre-registration commit | (see git log) |
| Status | pre-registered (Phase 1 of 3); Phase 2 validation not yet run |
| Study type | risk/execution-mechanism (not an alpha study) |
| Primary artefacts | `PROTOCOL.md`, `results.json` (placeholder until Phase 2) |
| Validation panel | synthetic Monte-Carlo (N=10,000) + 2026-07-08→07-12 incident replay |
| Arms | HK (binary kill-switch baseline) · GC-S (graduated + shadow) · GC-T (graduated + time-decay) |
| Candidate configs | {P-exp, P-lin} × {G-surplus, G-cdar} (frozen §3) |
| Verdict gate | Pareto dominance on capital preservation + time-to-resume (§6) |
| Phase 3 gate | production wiring proceeds ONLY on an `alive` verdict |
| Key references | grossman1993drawdowns, busseti2016kelly, chekhlov2005drawdown, chen2024darkside, subrahmanyam1994circuit, maillard2010erc, bailey2016pbo, klass2005grossmanzhou |
