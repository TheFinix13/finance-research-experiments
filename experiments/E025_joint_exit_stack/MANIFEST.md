| Field | Value |
|---|---|
| ID | E025 |
| Short name | Joint exit-stack Pareto validation |
| Pre-registration commit | (see git log) |
| Status | pre-registered (Phase 1 of 3); Phase 2 gated on ALL of E020/E021/E022/E024 verdicts landing first |
| Study type | composability / safety-net (not a new mechanism) |
| Primary artefacts | `PROTOCOL.md`, `results.json` (placeholder until Phase 2), `STOP_NOTICE.md` (if `dead`/`cancelled_dependency_failed`) |
| Compositions | π0 (baseline) · π1 = A (E022) · π2 = A+B (+E021) · π3 = A+B+C (+E020) · π4 = A+B+C+D (+E024) |
| Upstream arm hyperparameters | TBD — filled from E020/E021/E022/E024 verdicts before Phase 2 |
| Primary metric | Δ Sharpe of per-trade R sequence (paired bootstrap-95 % CI, seed 42, resamples 5000, per-fold + pooled) |
| Secondary guardrails | tail-mean R (worst 10 %), mean R, max consec-loss streak, P(R < −1.0R) — see §4 for caps |
| Selection-inflation control | Deflated Sharpe against family size 57 (12+9+12+24 upstream arms) |
| Verdict gate | Pareto dominance on Δ Sharpe + all secondaries + OOS-only sensitivity + bar-granularity sensitivity |
| Phase 3 gate | production `ExitManager` module wiring proceeds ONLY on `alive` verdict here, plus ≥2 weeks paper-mode observation |
| Dependencies | E020, E021, E022, E024 verdicts must all be registered before Phase 2 kickoff |
| Key references | bailey2016pbo, chekhlov2005drawdown, stouffer1949american, sharpe1994, kaminski2014stop; also E017, E019, E013 (in-repo) |
