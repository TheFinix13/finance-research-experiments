# E026 — Low-MFE time-stop, "get going or get out" (pre-registered)

**Pre-registered:** 2026-07-28 (before any Phase-2 execution) ·
**Owner:** research lead · **Motivator:** user directive, 2026-07-28
weekly v1 review session.

## §0 Reuse declaration (no production code touched)

Phase 2 is a pure consumer of the PRE-0 data plane
(`programs/_shared/counterfactual_replay/SPEC.md`) and the shared
replay engine (`replay.py`), both reused UNMODIFIED. The rule emits
`close_at` actions tagged `e026_time_stop`; the engine maps unknown
reason tags to the `PRIORITY_E024_STALL` slot (above broker TP, below
hard SL). That slot's above-TP position is **moot for this rule by
construction**: the engine updates MFE state from the current bar's
extremes BEFORE calling the rule, so any bar that touches TP raises
`mfe_r_so_far ≥ tp_r (≥ 1.4) > P_max (0.75)` and the firing condition
(`mfe_r_so_far < P`) is false on that bar. Hard SL still wins any
same-bar tie (priority slot 0). No live-agent code is touched in
Phase 1–2.

## §1 Hypotheses (operational)

Direct motivator: 2026-07-28 weekly review — GBPUSD 3000652586 held
4+ days and USDCAD 2987854368 held 7+ days, both range-trapped with
MFE that never approached 1R ("at this point we become swing traders
with very little profit" — user). Both tickets post-date the PRE-0
window and are narrated ex-post in the REPORT as illustrative n=2
only, never as statistical evidence (E024 §5.5 posture).

- **H1 (primary).** Closing a trade at market once it has been held
  ≥ `B` H4 bars without EVER reaching `mfe_r ≥ P` improves the Sharpe
  of the per-trade R sequence versus the deployed baseline
  (`all_on` cell), because the low-MFE-at-age cohort is
  disproportionately populated by eventual losers and scratch-outs.
- **H2 (cohort-separation rationale, tested via guardrail not
  primary).** Unlike E020/E024 — which armed on WINNING trades near
  TP and died on clean-TP cannibalization — a detector that can only
  fire while `mfe_r < P ≤ 0.75` is structurally disjoint from the
  near-TP zone, so its Δ P(false positive) (fires on baseline-TP
  trades) should be far below E024's 0.63–0.91 range. If Δ P(false
  positive) still exceeds 0.50, the `parked_false_positive_heavy`
  label applies exactly as in E024 §6 (H3).
- **H3 (capital-efficiency secondary, descriptive only).** The rule
  reduces mean bars-held materially on the fired cohort. This is
  reported, never promoted to a verdict criterion.

Stage 2 (the user's "health points" meter — a continuous vitality
score drained by losses and holding time, restored by timely wins,
throttling size/entries) is a SEPARATE mechanism gated on stage 1: if
zero stage-1 arms are `alive`, the time signal has no per-trade value
on this cell and the meter is not pursued in this form. Stage-2
parameters are deliberately NOT drafted here (a fresh pre-registration
amendment would follow a stage-1 alive verdict; drafting them now
against unknown stage-1 results would be theatre).

## §2 Separation

Same repo separation as E020/E024: research lane only; the deployed
cell's config (fixed 1.5R TP, wick-proof soft SL, BE-at-1R, PLG) is
the untouched baseline. Phase 3 (live wiring) requires an `alive`
verdict plus user sign-off, and would be a `multi-pair-trading-agent`
deliverable (a bars-held counter beside `_track_excursion`'s MFE
bookkeeping — noted for feasibility, not built).

## §3 Rule specification (frozen)

At each completed path bar `i` (state as-of end of bar `i`, no
look-ahead — SPEC §4 invariant 4):

```
bars_held = i + 1                      # completed H4 path bars since entry
fire  ⇔  (bars_held ≥ B)  AND  (mfe_r_so_far < P)
action = close_at(price = bar.close, reason = "e026_time_stop")
```

- `mfe_r_so_far` is the engine's monotone running MFE in R (includes
  the current bar's favourable extreme). Once a trade touches `P` it
  is **permanently exempt** — this is a "get going or get out" gate,
  not a trail; there is no re-arming.
- Fire happens on the FIRST bar satisfying the condition (for a trade
  that never reaches `P`, that is exactly bar index `B − 1`).
- Clock choice (locked): **market bars, not wall-clock**. H4 path
  bars only exist while the market trades, so weekends do not age a
  position. 6 H4 bars ≈ 1 trading day. Wall-clock ambiguity inside
  one H4 bar (≤ 4 h) is ≤ 2 % of the smallest `B` (48 h), so H4 path
  resolution (USDCAD) is FULL fidelity for this rule — no low-fidelity
  flag needed (contrast E024's H1-bucket signals).
- Exit price `bar.close` is the causal decision price at the bar
  close the condition is first observed. Same-bar hard SL beats the
  rule (priority); same-bar TP cannot coincide with a fire (§0).

## §4 Locked parameters (frozen at approval)

### §4.1 Stage-1 grid (15 arms, family size 15 per symbol)

| Parameter | Grid |
|---|---|
| `P` (progress threshold, R of MFE) | {0.25, 0.50, 0.75} |
| `B` (age threshold, completed H4 bars) | {12, 18, 24, 30, 42} ≈ {2, 3, 4, 5, 7} trading days |

3 × 5 = **15 arms**, `exit_action = close_at_market` fixed (stage 1).
No other free parameters. No grid extension under any result.

### §4.2 Stage 2 (gated)

Runs ONLY if ≥ 1 stage-1 (arm, symbol) cell is `alive`. Mechanism:
health-meter controller (see §1). Requires a fresh §7 amendment with
its own frozen grid before any stage-2 compute.

## §5 Validation method (identical to E024 §5 unless stated)

- **Data plane:** PRE-0 ledgers
  `programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl`,
  symbols EURUSD / GBPUSD / USDCAD, window 2015-01 → 2025-12.
- **Per-arm counterfactual:** shared `replay()`; baseline R is the
  ledger's `trade.r` (null-rule identity, SPEC §4.1).
- **Folds:** the five PRE-0/E004 walk-forward folds (2017–19, 2019–21,
  2021–23, 2023–24H1, 2024H2–26).
- **Primary metric:** paired Δ Sharpe of the per-trade R sequence
  (arm − baseline), bootstrap 95 % CI, seed 42, 5000 resamples,
  pooled per symbol + per fold.
- **Fold combination:** signed Stouffer's Z (weights √n_fold_trades),
  Fisher's combined p as sensitivity.
- **Multiplicity:** BH-FDR α = 0.10 applied per symbol across the
  15-arm family (NOT pooled across symbols — E005 posture).
- **Secondary guardrails (reported, never promoted):** Δ tail-mean R
  (worst 10 %); fire rate Δ P(fire); **Δ P(false positive)** = fraction
  of fires landing on trades whose baseline `exit_reason == "tp"`;
  Δ P(rescued) = fraction of fires landing on baseline-SL trades;
  Δ mean R on the fired cohort; **Δ mean bars-held** (all trades and
  fired cohort — the H3 capital-efficiency read).

## §6 Success criteria and stop/kill conditions (locked before results)

Per (arm, symbol) cell — identical to E024 §6:

- **`alive`** ⇔ pooled ΔSharpe CI-LB > 0 AND point > 0 on ≥ 4/5 folds
  AND Stouffer joint p < 0.05 AND BH-FDR rejected — AND
  Δ P(false positive) ≤ 0.50 (else `parked_false_positive_heavy`,
  user review required before any Phase 3).
- **`parked_low_yield`** ⇔ pooled point > 0 with CI including 0, or
  exactly 3/5 folds positive.
- **`dead`** otherwise.

Study verdict: `alive` if any cell is alive; stop rules on a 0-alive
outcome: write STOP_NOTICE.md, no stage 2, no grid extension, no
post-hoc metric promotion (Δ bars-held stays descriptive however good
it looks), keep the deployed cell unchanged, and the health-meter idea
(I021 stage 2) is not pursued in this form.

## §7 Amendments

Any change after the pre-registration commit is a numbered amendment
with rationale, never a silent edit.

### Amendment 1 — replayed null-arm baseline (2026-07-28, same day)

**Trigger:** the first sweep failed a hard sanity invariant — USDCAD
arm `P0.25_B42` fired on **0 of 707 trades** yet showed pooled
ΔSharpe = −0.1453. An arm that never fires must have Δ ≡ 0. Cause:
the §5 baseline was the ledger's `trade.r`, but a replayed arm's
non-fired trades take the engine's fall-through, which *reconstructs*
the exit from the path (BE-migration timing, intra-bar ordering) — on
coarse paths (USDCAD is H4-resolution) the reconstruction disagrees
with the original backtest's exits. The pre-amendment primary metric
therefore confounded rule effect with reconstruction error. This is
the known PRE-0 "null-rule identity is fast-path-only" caveat the
E020–E025 campaign logged as a deferred amendment.

**Change:** the baseline R sequence is now the **replayed inert-rule
arm** (the same rule class with `age_bars = 10^9`, which provably
never fires) instead of the raw ledger `trade.r`. Arm and baseline
then share identical reconstruction semantics and the paired delta
isolates the rule effect. A `reconstruction_audit` block (per-symbol
null-vs-ledger mismatch count and ΔSharpe) is added to results.json
to quantify the drift that motivated this amendment. Grid, metrics,
folds, bootstrap, FDR, and §6 verdict gates are unchanged. The
amendment was made after seeing confounded results but corrects a
validity bug in a direction-neutral way (it can flip verdicts either
way); the pre-amendment numbers are preserved in the REPORT/STOP
notice for the record.

### Amendment 2 — age clock in H4-equivalents (2026-07-28, same day)

**Trigger:** the Amendment-1 run's bars-held audit showed EURUSD
baseline mean holding of 362 "bars" — impossible for H4. Cause: §3
implemented `bars_held = bar_index + 1` over PATH bars, but PRE-0
path resolution is per-symbol (EURUSD M5, GBPUSD M15, USDCAD H4), so
`B = 12` meant 1 wall-hour on EURUSD and 3 hours on GBPUSD instead of
the pre-registered 2 trading days. The sweep was testing a different
rule on each symbol — implementation error against the §3 intent
("completed H4 bars"), not a design change.

**Change:** `bars_held_h4 = (bar_index + 1) × f(path_resolution)`,
with `f = {M5: 1/48, M15: 1/16, H1: 1/4, H4: 1}`; fire when
`bars_held_h4 ≥ B`. This is exactly the §3 market-bar clock, now
resolution-independent (finer paths simply fire at the first sub-bar
close past the threshold — higher fidelity, same semantics). Grid and
§6 gates unchanged. The invalid-clock run is preserved as
`results_amendment1_wrong_clock.json` for the record.

## §8 Cross-references

- E020 STOP_NOTICE (runner-choke) and E024 STOP_NOTICE
  (false-positive-heavy; the "joint constraint" both died on). E026's
  §1-H2 is the explicit escape argument this study must survive.
- E025 family-multiplicity ledger: E025 was cancelled
  (zero-alive-upstream); this study adds a NEW 15-arm family (45
  (arm, symbol) cells). Campaign meta-accounting to date:
  105 exit-campaign arms rejected 98-in-degradation / 0-in-favor;
  E026 is a new mechanism class (age-gated low-MFE), not an amendment
  to any of them.
- Intake provenance: `multi-pair-trading-agent`
  `company/rd/intake/I021-time-boxed-trades-health-meter.md`.

## §9 Data-ledger declaration

Consumes existing PRE-0 JSONL ledgers unchanged (DATA_LEDGER rows for
Dukascopy H4/M15/M5 paths already registered by the E020–E025
campaign). No new data acquisition.
