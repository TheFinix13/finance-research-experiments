| Field | Value |
|---|---|
| ID | E018 |
| Short name | Regime-aware fade gating (R2 stand-aside) |
| Pre-registration commit | (see git log) |
| Status | pre-registered 2026-07-14; Phase 2 harness + backtest |
| Study type | alpha-layer (fade gating by causal regime label) |
| Primary artefacts | `PROTOCOL.md`, `REPORT.md`, `results.json` |
| Fade under test | `zone_d1_against` (SupplyDemandAlpha, htf_against, D1, lookback=10, min_move=60p) |
| Regime taxonomy | R1 trend-pullback (keep fade) · R2 trend-extension/breakout (stand aside) · R3 no-bias/range (already stands aside on NEUTRAL D1) |
| Labeller | causal, frozen: Chigiri Φ4.1 breakout priors (lookback=20, ATR=14, vol_lookback=80, mult=0.50) + deployed D1-bias; ADX>25 reported only |
| Arms | baseline (all fades) · R2-filtered (drop R2, keep R1) |
| Pairs / TF | EURUSD, GBPUSD, USDCAD / H4 / all sessions |
| FDR family | 6 cells = {EURUSD,GBPUSD,USDCAD} × {R1,R2}; BH-FDR α=0.05 |
| Validation | 7× 4yr-IS / 1yr-OOS walk-forward (2015–2025); pooled OOS 2019–2025; 2025 sealed final read |
| Verdict gate | R2 significantly negative OOS (q≤0.05, n≥30, robust) AND R2-filter improves R1 survivors' OOS risk-adjusted perf (§5) |
| Phase 3 gate | live alpha-layer wiring proceeds ONLY on an `alive` verdict |
| Harness | `programs/E018/regime_labeller.py`, `programs/E018/run_e018_validation.py`, `programs/E018/tests/` |
| Key references | Chigiri Φ4.1 (a04_chigiri.py), F18 ADX convention (classifier.py), bailey2016pbo, bailey2014deflated |
