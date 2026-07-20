| Field | Value |
|---|---|
| ID | E021 |
| Short name | Partial exit at fixed-R milestone |
| Pre-registration commit | (draft — awaiting user approval, then git log) |
| Status | **Phase 2 COMPLETE 2026-07-20** — verdict `dead`; `LiveConfig.partial_exits` stays `False` |
| Verdict | **`dead`** — 0/9 arms alive, 0/9 parked, 9/9 dead (see `REPORT.md` §1 and Verdict block below) |
| Study type | exit-mechanism / risk-shape study (not an alpha study) |
| Motivation | 2026-07-20 weekly review: GBPUSD 2966547972 (+1.96R TP winner), GBPUSD 2969136564 (open, MFE 1.49R then fading), USDCAD −1.02R loser — all closed / are closing with no intermediate partial-take; `LiveConfig.partial_exits = False` in production |
| Config lever under test | `multi-pair-trading-agent/agent/live/config.py::LiveConfig.partial_exits` (currently `False`) — READ-ONLY reference; E021 does not flip it |
| Primary metric | **Δ Sharpe of per-trade aggregated R** (paired bootstrap 95 % CI, seed 42, 5,000 resamples), per fold and pooled |
| Aggregation rule | `alt_r = partial_fraction · r_at_partial_price + (1 − partial_fraction) · r_at_final_exit_price`, both normalized against ORIGINAL entry-time `stop_pips` (PROTOCOL §3.3) |
| Secondary metrics | Δ mean R · Δ P(losing-trade-after-partial > 0R aggregate) · Δ tail-mean R (worst 10 %) · Δ variance of R · count of trades where partial fired |
| Baseline | same-cell `partial_exits = False` (paired per trade) |
| Arms (frozen 9-arm 2-D grid) | `partial_R ∈ {0.7, 1.0, 1.3}` × `partial_fraction ∈ {0.25, 0.4, 0.5}` |
| Data plane | PRE-0 shared harness: `programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl` (schema per SPEC §1) |
| Symbols | EURUSD, GBPUSD, USDCAD on H4 |
| Window | 2015-01 → 2025-12 |
| Walk-forward folds | 5 (inherited from PRE-0 SPEC §3, mirroring E004) |
| Fill model | Touch-fill at trigger price `entry ± partial_R · stop_pips · pip_size` (E013/E017 convention; no slippage layer at Phase 2) |
| Exit priority (SPEC §4.3) | `hard_catastrophic_SL → hard_soft_SL → E024_stall_exit → E021_partial_close → broker_TP_hit → E020_MFE_ratchet_stop → E023_structure_trail` |
| Interaction with production BE-move-at-1R | Independent in E021; residual keeps original TP and inherits current stop-state (BE if `partial_R ≥ 1.0` and BE ratchet has fired, else original SL). Joint stack handled in E025. |
| Reversal guard | Hard SL / stall exit hits before partial trigger ⇒ no partial fires; `alt_r = r_baseline` (invariant §3.5) |
| FDR method | Benjamini–Hochberg at α = 0.10 across the 9-arm family; single primary; deflated Sharpe + PBO for the selected arm |
| Verdict gate | `alive` iff at least one arm: Δ Sharpe CI-LB > 0 AND positive-in-≥4/5 folds AND BH-adjusted p < 0.05, with §5.2 guardrails not materially degraded |
| Acceptable outcomes | `alive`, `parked_low_yield`, `parked_lower_variance_lower_return` (special — feeds E025 candidate set), `dead` |
| Stop rule | 0 arms `alive` or `parked_lower_variance_lower_return` at Phase-2 end → keep `LiveConfig.partial_exits = False`, write `STOP_NOTICE.md`, no grid extension |
| Phase 3 gate | flipping `LiveConfig.partial_exits` to `True` proceeds ONLY on an `alive` verdict AND after the trading-agent repo's own validation chain re-locks the parameters |
| Anti-overfit | single pre-registered primary; frozen discrete 9-arm grid; BH-FDR + deflated Sharpe + PBO; positive-in-folds guard against single-fold luck; symbol-stratified diagnostic; negatives reported |
| Key references (existing in `refs.bib`) | benjamini1995controlling, bailey2014deflated, bailey2014pseudo, harvey2016cross, efron1993bootstrap, nosek2018preregistration, chan2009quantitative |
| References to add before REPORT | sharpe1966 / sharpe1994 (canonical Sharpe citation for the primary metric — also flagged by E019 §8); kaminski2014stop (Kaminski & Lo, "When Do Stop-Loss Rules Stop Losses?", JFM 2014 — closest peer-reviewed treatment of mechanical partial-exit / stop rules and their effect on the R distribution) |
| Sibling PRE-0 consumers | E020 (MFE ratchet), E023 (post-BE structure trail), E024 (near-TP stall exit), E025 (joint stack — consumes E021's `parked_lower_variance_lower_return` candidates — n.b. E021 landed `dead`, no candidates promoted) |
| Predecessor experiments | E004 (walk-forward), E013 (`all_on` production-matching harness), E017 (base ledger export) |
| Methodological precedent | E019 §7 (single-primary, no post-hoc metric swaps); E017 §6 (frozen discrete grid, `parked_*` labels, honest-negatives ethos) |
| Phase 2 artefacts | [`REPORT.md`](./REPORT.md) · [`STOP_NOTICE.md`](./STOP_NOTICE.md) · [`../../programs/E021/results.json`](../../programs/E021/results.json) · [`../../programs/E021/run_e021_validation.py`](../../programs/E021/run_e021_validation.py) · [`../../programs/E021/tests/test_e021_rule.py`](../../programs/E021/tests/test_e021_rule.py) |

## Verdict

**Study verdict: `dead`** (2026-07-20, generator commit `7e1a3e7`).

Zero of 9 arms alive, zero parked (including the H2
`parked_lower_variance_lower_return` special case), 9/9 dead. Pooled
ΔSharpe range across arms: **[−0.1314, −0.1076]**; least-bad arm
`pR1.3_pf0.25` gives ΔSharpe = **−0.1076** with 95 % CI **[−0.1385,
−0.0790]**, BH-adjusted p = 0.0000, 0/5 folds positive. Every arm's
ΔSharpe CI lies **entirely below 0** — the study is significantly
worse-than-baseline, not just noisy-around-zero.

**One-line finding:** the partial-exit mechanic realises the promised
tail cap (+1.0R on the worst decile), variance reduction
(ΔVar ∈ [−0.90, −0.49] R², CI-UB < 0 on all arms), and give-back rescue
(+7 to +18 pp of fired trades convert to net-positive) — but the
mean-R give-up on the 47–63 % of trades whose paths cross the trigger
(fired-cohort Δmean R ∈ [−0.17, −0.03] R; whole-population Δmean R ∈
[−0.23, −0.18] R) dominates the Sharpe.

**H2 special case status:** did not fire. All 9 arms show
statistically-negative Δ variance of R (CI-UB in [−0.85, −0.43]),
which is the H2 variance criterion. However H2 also requires the
ΔSharpe CI to *include* 0; every arm's ΔSharpe CI is entirely below
0, so H2 is not authorised. E021 is NOT promoted to the E025
joint-stack candidate set as a variance generator via H2.

**Production action:** none. `LiveConfig.partial_exits` stays `False`.
See [`STOP_NOTICE.md`](./STOP_NOTICE.md) for the non-actions log and
[`REPORT.md`](./REPORT.md) for the full mechanism narrative + per-arm
table + per-symbol stratification.

Numeric artefact:
[`../../programs/E021/results.json`](../../programs/E021/results.json).
