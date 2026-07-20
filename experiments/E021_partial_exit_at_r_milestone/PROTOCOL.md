# E021 — Partial exit at fixed-R milestone (pre-registered)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-20 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a design document.** No code is built or run under E021 tonight.
> The deliverable is a pre-registration the user can approve. Follow
> [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md); register in
> [`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
> [`../../reviews/refs.bib`](../../reviews/refs.bib). Data-plane consumer of
> the shared harness at
> [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
> (PRE-0) — schema, walk-forward folds, and replay-engine invariants live
> there and are not re-specified here.

---

## §0 Reuse declaration (no production touch)

E021 Phase 1 (this document) writes **no code**. Phase 2 builds a
counterfactual-replay harness under `programs/E021/` that consumes the
shared PRE-0 data plane. Production code is **read-only reference** only.

| Purpose | Module / artefact | Status |
|---|---|---|
| Existence of the config lever | `multi-pair-trading-agent/agent/live/config.py::LiveConfig.partial_exits` (currently `False`) | read-only reference — E021 does not flip it |
| Base ledger (pnl + exit reasons) | `programs/E017/data/trade_ledger_EURUSD_H4.json` (737 EURUSD trades, hit-rate 0.5577, regenerated read-only from the E013 `all_on` production-matching harness) | read-only bootstrap source |
| Intra-trade OHLC + MFE/MAE | PRE-0 output `programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl` | read-only consumer |
| Replay engine + invariants | `programs/_shared/counterfactual_replay/replay.py` (SPEC §4) | read-only consumer |
| BE-move-at-1R (existing prod behaviour) | `multi-pair-trading-agent/agent/live/exit_manager.py` (BE ratchet) | read-only reference for stop-state at partial time |
| E021 replay harness (Phase 2) | `finance-research-experiments/programs/E021/` (new) | to be built |

**Production wiring is a separate, later phase.** Flipping
`LiveConfig.partial_exits` to `True` (with any winning arm's parameters) is
gated on a Phase 2 `alive` verdict, and only after the trading-agent
repo's own validation chain (grid → holdout → walk-forward → cross-pair →
sealed) re-locks the parameters.

---

## §1 Hypothesis (operational)

Let a deployed-cell trade have entry-time stop distance `stop_pips`,
take-profit distance `tp_pips = 1.5 · stop_pips` (locked cell property,
per SPEC §1), and realised full-lot R-multiple `r_baseline`. Under E021
with parameters `(partial_R, partial_fraction)`, the trade produces a
partial fill at favorable-excursion `partial_R` and a residual exit at
`r_residual`, aggregated per §3.3.

- **H0 (null).** Flipping `partial_exits` on with any of the 9 pre-
  registered `(partial_R, partial_fraction)` arms (§4) does **not**
  improve the risk-adjusted per-trade R distribution of the deployed
  cell against the same-cell baseline (`partial_exits = False`) on the
  pre-registered primary metric **Δ Sharpe of per-trade aggregated R**
  (§5.2), pooled across the 5 walk-forward folds and the three deployed
  symbols.

- **H1 (alt).** At least one frozen arm delivers a **statistically
  positive Δ Sharpe** against the same-cell baseline — bootstrap-95 % CI
  lower bound `> 0`, positive-in-≥4/5 folds, and pooled BH-FDR-adjusted
  `p < 0.05` (§5.3) — with no material degradation of the secondary
  guardrails (§5.2).

- **H2 (parsimony / lower-variance-only special case).** If an arm shows
  a **material variance reduction** (Δ variance of R statistically
  negative) without a Sharpe improvement (Δ Sharpe CI includes 0), that
  is recorded as `parked_lower_variance_lower_return` — **not** buried
  as `dead` — because a lower-variance R generator is a legitimate input
  to a future joint risk-budget stack (see §6 and cross-reference E025).
  The parsimony rule is that a variance-only win does not by itself ship
  E021 to production; it earns a slot in the joint-stack candidate set.

---

## §2 Separation

- **Does this touch the trading agent?** **No.** Phase 1 is documents.
  Phase 2 is a counterfactual replay under `programs/E021/` that reads
  the PRE-0 path ledger and writes to `experiments/E021_*/results.json`.
  Phase 3 (flipping `LiveConfig.partial_exits`) is a separate, gated
  deliverable in `multi-pair-trading-agent`.
- **Prior uses of the same data slice.** The EURUSD H4 2015-01 → 2025-12
  cell is a **re-analysis** of already-reported ledger trades (E004 walk-
  forward, E013 safety-layer contribution, E017 bootstrap ledger). GBPUSD
  and USDCAD H4 slices at 2015-01 → 2025-12 are generated fresh by PRE-0
  from the same `all_on` production-matching harness; their trade counts
  and hit-rates will be reported in the PRE-0 file headers. A `planned`
  row is added to `DATA_LEDGER.md` when Phase 2 starts (§9).
- **Anti-double-dipping note.** Because the deployed-cell trade set is
  the same set E013/E017 evaluated, E021 is a **new pre-registered rule
  on already-reported outcomes**, disclosed as such. The rule is a
  post-trade transformation of the intra-trade path — it does not
  re-select trades from a larger candidate universe, so it does not
  re-open a sealed selection family.

---

## §3 Rule specification (formal)

### §3.1 Trigger

For each historical trade `T` in the deployed-cell ledger with entry
`entry`, direction `d ∈ {+1 (long), −1 (short)}`, entry-time
`stop_pips`, TP price at `entry + d · 1.5 · stop_pips`, and intra-trade
path from PRE-0:

Define the **favorable excursion in R-multiples** at bar `i` as

```
fav_R_i = d · (bar_i_extreme − entry) / (stop_pips · pip_size)
```

where `bar_i_extreme = bar_i.high` for a long and `bar_i.low` for a
short (i.e. the wick that most favours the trade). Iterate bars in
chronological order at the M5 resolution declared in SPEC §1 (fall back
to H4 with `path_resolution="H4"` where M5 is unavailable, per SPEC).

The **partial-fire trigger** on bar `i` is:

```
fav_R_i ≥ partial_R   AND   partial has not yet fired on this trade
```

**partial_R is expressed in R-multiples of the entry-time `stop_pips`**
(not as a fraction of TP distance): with `stop_pips` = 1R and TP at
1.5R, the three grid values `{0.7, 1.0, 1.3}` correspond to
`{0.7, 1.0, 1.3}` R of favorable excursion, all strictly before TP.

### §3.2 Fill price and priority

- **Fill price:** the partial fills at the **trigger price**
  `entry + d · partial_R · stop_pips · pip_size`. This is the touch-fill
  convention used by the E017/E013 harness for TP and SL fills — a wick
  that reaches through the trigger executes AT the trigger. No slippage
  model is added at Phase 2 (the baseline harness has none either;
  slippage remains a Phase-3 production concern).
- **Exit-priority ordering (SPEC §4.3).** On a bar where multiple exits
  could fire, priority is (highest → lowest):

  ```
  hard_catastrophic_SL → hard_soft_SL → E024_stall_exit →
  E021_partial_close → broker_TP_hit →
  E020_MFE_ratchet_stop → E023_structure_trail
  ```

  So the partial fires **before** TP on the same bar (guaranteeing the
  partial is realized when a bar wicks both partial and TP), and
  **after** any hard SL / stall exit (so a fast reversal that hits SL
  first pre-empts the partial and the trade behaves as production
  baseline — see §3.4).

### §3.3 Aggregation to a single per-trade R

Both realized events (partial fill + residual exit) are normalized
against the **ORIGINAL entry-time `stop_pips`** (not a re-measured
post-partial stop). The per-trade aggregated R for the counterfactual
ledger is:

```
alt_r  =  partial_fraction · r_at_partial_price
        + (1 − partial_fraction) · r_at_final_exit_price
```

with

```
r_at_partial_price      =  partial_R                                          (by construction of the trigger)
r_at_final_exit_price   =  d · (residual_exit_price − entry) / (stop_pips · pip_size)
```

If **no** partial fires on the trade (path never reaches `partial_R`, or
priority §3.2 pre-empts it), then `alt_r = r_baseline` byte-for-byte
(invariant §5.1). This is the "no-partial ⇒ replay is identity"
contract.

### §3.4 Interaction with existing production layers

- **BE-move-at-1R (existing, deployed):** for `partial_R < 1.0`, the
  partial fires **before** BE has moved (residual keeps original SL).
  For `partial_R ≥ 1.0`, partial and BE both trigger at or after 1R;
  under the SPEC §4.3 ordering `E021_partial_close` fires **before**
  `MFE_ratchet_stop` / `structure_trail`, but is independent of the
  production BE ratchet — the BE move applies to the residual as usual.
  In this study BE and partial are independent; a future joint-stack
  study (E025) applies both.
- **Soft / catastrophic stop:** a hard SL that fires on the same bar as
  a partial trigger pre-empts the partial (SPEC §4.3 priority ordering).
  Additionally, if the M5 path first crosses the SL before ever reaching
  `partial_R`, no partial fires and the trade is a pure baseline exit
  (`alt_r = r_baseline`). This is the "reversal guard" the brief calls
  out: E021 only fires when the trade is genuinely in profit at the
  milestone.
- **Original TP unchanged:** the residual continues to the original TP
  price and original SL (which may already be at BE due to the deployed
  BE-move-at-1R rule). E021 does **not** move the TP.

### §3.5 Determinism and invariants (inherited from SPEC §4)

- **§4.1 Null-rule invariant.** `partial_R = ∞` (never triggers) ⇒
  `alt_r == r_baseline` for every trade. Unit-tested.
- **§4.2 Stop-authority monotonicity.** E021 does not adjust the stop.
- **§4.3 Exit priority.** As enumerated in §3.2 above.
- **§4.4 No look-ahead.** Trigger detection uses only bars ≤ current
  bar; the fill price is the trigger price itself, not a subsequent
  close (mutation-tested).
- **§4.5 Determinism.** For fixed `(trade, partial_R, partial_fraction,
  seed=42)`, `alt_r` is bit-identical across runs.

---

## §4 Locked parameters (9-arm grid, frozen at approval)

| Knob | Value(s) | Rationale |
|---|---|---|
| `partial_R` (R-multiples of entry-time `stop_pips`) | {0.7, 1.0, 1.3} | 0.7 = early bank before BE moves; 1.0 = at BE-move (production landmark); 1.3 = late bank just below TP (1.5R). Three points span the operative pre-TP band; no continuous tuning. |
| `partial_fraction` (fraction of original lots closed at trigger) | {0.25, 0.4, 0.5} | 0.25 = light scale-out; 0.4 = middle (matches the motivating-review illustrations); 0.5 = half-off. Bounded above by 0.5 to guarantee a non-trivial residual runs to TP. |
| Full-arm grid | 3 × 3 = **9 arms** | Locked 2-D grid; no additional arm added post-freeze. |
| Symbols | EURUSD, GBPUSD, USDCAD | Deployed cells. All three feed a single pooled test after per-fold aggregation (§5). |
| Timeframe | H4 | Deployed TF. |
| Window | 2015-01 → 2025-12 | Matches SPEC §2 and E017 §7 A1. |
| Walk-forward folds | 5 (per SPEC §3, mirroring E004) | No new fold structure; consumer studies inherit the deployed cell's fold boundaries. |
| Path resolution | M5 primary; H4 fallback flagged per-trade (`path_resolution` field, SPEC §1) | Deterministic; low-fidelity trades are flagged, not silently dropped. |
| Fill model | Touch-fill at the trigger price | Matches the E013/E017 harness convention (no separate slippage layer at Phase 2). |
| Bootstrap resamples | 5,000 | Convention (E017 §4). |
| Random seed | 42 | Convention (E014, E017 §4). |
| Ruin threshold (equity-level guardrail, if simulated) | 0.50 · E_0 | Carried from E017 §4 for continuity. |
| FDR method | Benjamini–Hochberg at α = 0.10 across the 9-arm family | Family = 9 arms tested vs baseline on one primary metric (§5.3). |

**No parameter above is tuned during Phase 2.** Phase 2 evaluates
exactly this 9-arm grid, once, per walk-forward fold, per symbol.

---

## §5 Validation method (Phase 2 — not run in Phase 1)

### §5.1 Counterfactual-replay harness (PRE-0 consumer)

For each `(symbol, fold)` pair and each of the 9 arms:

1. Load the PRE-0 test-slice path ledger
   `programs/_shared/counterfactual_replay/data/{symbol}_H4_paths.jsonl`.
2. For each trade `T` in the fold's test slice, call
   `replay(T, e021_rule(partial_R, partial_fraction))` from
   `programs/_shared/counterfactual_replay/replay.py`.
3. Aggregate the two realized fills per §3.3 into `alt_r`, log both
   sub-fills (`partial_r`, `residual_r`) plus a boolean `partial_fired`.
4. Write per-arm per-symbol per-fold results to
   `experiments/E021_partial_exit_at_r_milestone/results.json`.

**Two-fill accounting note (inherited from the brief).** Because each
E021 trade produces **two realized P&L events**, the harness must
aggregate them into a **single** per-trade R for the counterfactual
ledger before any statistical test runs. All statistical work in §5.2 /
§5.3 uses the aggregated `alt_r` sequence, not the two-event stream,
and both components are normalized against the ORIGINAL entry-time
`stop_pips` (never a re-measured post-partial stop). Reporting the two
sub-fills (`partial_r`, `residual_r`) is descriptive-only and does not
open a second FDR family.

### §5.2 Metrics (primary + secondaries, pre-registered)

All Δ metrics are computed on **paired** per-trade R sequences (each
arm vs same-cell baseline, identical trade ordering), per fold, then
pooled across folds by inverse-variance-weighted mean.

**Primary metric (single, decision-relevant):**

- **Δ Sharpe of per-trade aggregated R.** Sharpe here is the
  per-trade Sharpe `mean(r) / sd(r)` computed on the per-trade R
  sequence (no annualisation — the deployed cell's ~66 trades/yr
  cadence is stable across arms, so a Sharpe on per-trade R is scale-
  free and comparable). Paired bootstrap, 5,000 resamples, seed 42;
  reported with a 95 % CI per fold and pooled.

**Secondary metrics (guardrails / context, not swappable to primary
post hoc):**

1. **Δ mean R** — the level metric. E021 is *not* expected to raise
   mean R on TP-clean winners (partial locks in less than TP for the
   partial fraction); the study asks whether variance reduction
   compensates.
2. **Δ P(losing trade after partial > 0R aggregate)** — probability that
   a trade whose partial fired ends with `alt_r > 0` overall (i.e. the
   partial rescued a trade whose residual gave back). This is the direct
   "give-back protection" measurement.
3. **Δ tail-mean R (worst 10 %)** — mean R over the worst-decile
   aggregated-R trades. E021 should raise this if give-back protection
   works.
4. **Δ variance of R** — the H2 special-case observable
   (`parked_lower_variance_lower_return`).
5. **Count of trades where the partial fired** — descriptive: the
   fraction of the cell's trades that hit `partial_R` at all.

Each secondary is reported with a 95 % bootstrap CI. Secondaries **may
not** be promoted to primary post hoc (anti-cherry-pick, per E017 §6 and
E019 §7).

### §5.3 Verdict rule (locked, single primary, BH-FDR family = 9)

For each arm `a ∈ {1..9}`, compute the pooled `Δ Sharpe_a` with its
paired bootstrap 95 % CI and a two-sided p-value against `H0: ΔSharpe = 0`.
Apply Benjamini–Hochberg at α = 0.10 across the family of 9 arms
(`benjamini1995controlling`). An arm passes the multiplicity gate iff
its BH-adjusted p-value is < 0.10.

Verdict labels (locked before results, mapped to
`PROTOCOL_DISCIPLINE.md` §4 with E017-style `parked_*` extensions — see
§6 for the full label list):

| Label | Trigger |
|---|---|
| `alive` | At least one arm has Δ Sharpe CI-LB > 0 **AND** positive-in-≥4/5 folds **AND** BH-adjusted p < 0.05 (stricter than the family α, to allow selection width). Secondary guardrails (§5.2 items 1–3) must not materially degrade. |
| `parked_low_yield` | Δ Sharpe point estimate positive but CI includes 0, OR positive-in-only-3-folds. |
| `parked_lower_variance_lower_return` | Δ variance of R statistically negative (CI-UB < 0) AND Δ Sharpe CI includes 0. Special-case retention for the E025 joint-stack candidate set (see §6). |
| `dead` | None of the above; Δ Sharpe CI-UB ≤ 0 or positive-in-≤2/5 folds. |

### §5.4 Ex-post illustration on the motivating trades (n = 2, descriptive)

The 2026-07-20 weekly review flagged three GBPUSD trades whose paths
this study directly addresses. Reported here as a **descriptive
illustration** of the mechanic (n = 2 realized, plus 1 open at protocol-
freeze time) — **not** a statistical claim and **not** an FDR family
member. Numbers below use the user-supplied review figures and the
formal §3.3 aggregation math; where the two disagree, the formal math
governs Phase-2 accounting and the review figures are shown for
audit continuity.

- **GBPUSD ticket 2966547972 (2026-07-15 short, full-lot exit +1.96R,
  +$8.88).** Path hit the eventual TP cleanly. Under arm
  `(partial_R=1.0, partial_fraction=0.4)`:
  - Partial fires at +1.0R: `partial_r = 1.0`, dollar-approximate
    +$3.55 per the user's review (40 % of position).
  - Residual continues to TP: `r_residual = 1.5` (TP is at 1.5R for
    this cell), dollar-approximate +$5.33.
  - Per §3.3: `alt_r = 0.4 · 1.0 + 0.6 · 1.5 = 1.30` — i.e. the E021
    winner realizes **1.30R vs the baseline 1.96R** for this trade
    (because the residual TP is at 1.5R, not at 1.96R; the extra 0.46R
    was slippage-favoured over TP in the actual fill and is lost by the
    partial fraction that already exited at 1.0R).
  - Take-away: on a **TP-clean winner**, E021 costs a modest give-up.
    This is the expected trade-off; the study asks whether the tail-
    protection benefit dominates.
- **GBPUSD ticket 2969136564 (2026-07-16 short, still open at protocol-
  freeze time; MFE 79.1p ≈ 1.49R before retracing).** Under arm
  `(partial_R=1.0, partial_fraction=0.4)`:
  - Partial fires when MFE crossed 1.0R (~2 h into the trade):
    `partial_r = 1.0`, dollar-approximate +$3.55 realized.
  - Residual (60 %) now floats with BE stop already in effect:
    - Worst case (BE stop hits): `r_residual = 0`, `alt_r = 0.4`.
    - Best case (TP fills): `r_residual = 1.5`, `alt_r = 1.3`.
  - Currently unrealized under baseline: ~+$4.26 (per review).
  - Take-away: on a **runner that MFE-then-fades**, E021 in the worst-
    case still delivers +0.4R vs a possible baseline give-back to 0R
    or worse. This is the "give-back protection" mode the study exists
    to measure.
- **USDCAD full-cycle loser at −1.02R (referenced in review).** Path
  never reached +0.7R, so no partial would have fired under any of the
  9 arms; `alt_r = −1.02` = baseline exactly. E021 is silent on losers
  that never trade in the trade's favour (invariant §3.5 §5.1).

These three cases together illustrate the three regimes E021 must be
scored on:
(a) TP-clean winners take a small give-up,
(b) MFE-then-fade runners get give-back protection,
(c) direct-to-SL losers are unchanged.
Whether the *distribution* of R across the cell's ~700–800 trades per
symbol improves in Sharpe terms is what Phase 2 will decide.

### §5.5 Robustness / diagnostics (reported but not decision-gating)

- **Fold sensitivity table.** Per-arm Δ Sharpe per fold, to expose any
  arm that wins on a single fold only.
- **Symbol-stratified Δ Sharpe.** Per arm, split by symbol; a winning
  arm should not be carried by one symbol only.
- **Trigger-rate diagnostic.** Fraction of trades where the partial
  fired, per arm. If ≤ 5 % of trades trigger the partial, the arm's
  effect is mechanically bounded and reported as low-power context.
- **Path-resolution audit.** Fraction of trades with
  `path_resolution="H4"` per fold (SPEC §1). If > 15 % of a fold's
  trades fall back to H4 the fold's result is flagged as low-fidelity.
- **Deflated primary statistic + PBO.** For the winning arm, report
  the deflated Sharpe statistic (`bailey2014deflated`) and Probability
  of Backtest Overfitting across the 9-arm search
  (`bailey2014pseudo`). Reader can gauge selection-width inflation.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Four verdict labels (locked; §5.3 defines the triggers):

| Verdict | Meaning | Ships? |
|---|---|---|
| `alive` | At least one arm passes the §5.3 gate. | Advance to a Phase 3 production-wiring proposal in `multi-pair-trading-agent` (still gated on the agent's own re-validation). |
| `parked_low_yield` | Point estimate positive but CI includes 0, or positive-in-only-3-folds. | Do not ship. Candidate stays in the exit-stack candidate pool for E025 joint evaluation. |
| `parked_lower_variance_lower_return` | Variance drops (CI-UB < 0) without Sharpe improvement. | Do not ship stand-alone. **Special retention:** carried forward as a lower-variance-generator candidate for the E025 joint stack (risk-budget stacks may prefer lower-variance R even without Sharpe improvement). |
| `dead` | Neither Sharpe, positivity-in-folds, nor variance criteria met. | Stop. Write `STOP_NOTICE.md`, keep `LiveConfig.partial_exits = False`. |

**Stop rule (pre-declared).** If **zero** arms are `alive` or
`parked_lower_variance_lower_return` at the end of Phase 2, STOP:
`LiveConfig.partial_exits` stays `False` in production; a
`STOP_NOTICE.md` is written; no grid extension, no continuous tuning,
no post-freeze arm addition (`PROTOCOL_DISCIPLINE.md` §5). A
`parked_low_yield` alone does not extend the grid — it enters E025 as-is.

**Anti-overfit discipline (mirrors E017 §6 / E019 §7).**

1. Single pre-registered primary (Δ Sharpe of aggregated per-trade R).
   Secondaries (§5.2) are guardrails/context and **may not** be promoted
   to primary post hoc.
2. Frozen discrete 9-arm grid (§4). No continuous tuning, no post-freeze
   grid extension, no new arm added after approval.
3. Multiplicity accounting: BH-FDR at α = 0.10 across the 9-arm family;
   deflated Sharpe statistic + PBO for the winner (§5.5).
4. Positive-in-≥4/5 folds requirement guards against single-fold luck.
5. Symbol-stratified diagnostic (§5.5) guards against single-symbol
   luck.
6. Negative and null results are reported honestly (`STOP_NOTICE.md` on
   `dead`; MANIFEST verdict recorded for any `parked_*` label). Pre-
   registration ethos per `nosek2018preregistration`.

---

## §7 Amendments

_(Appended after pre-registration commits only. Empty at freeze.)_

---

## §8 Cross-references

- **PRE-0 shared data plane (required reading, not duplicated here).**
  [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
  — per-trade schema (§1), walk-forward folds (§3), replay engine
  contract (§4), exit-priority ordering (§4.3).
- **E013 safety-layer contribution**
  ([`../E013_safety_layer_contribution/`](../E013_safety_layer_contribution/))
  — source of the `all_on` production-matching harness that generates
  the base ledger E021 replays against.
- **E017 confidence-gated cooldown**
  ([`../E017_confidence_gated_cooldown/`](../E017_confidence_gated_cooldown/))
  — provides the EURUSD H4 ledger export
  (`programs/E017/data/trade_ledger_EURUSD_H4.json`, 737 trades, hit-
  rate 0.5577) that PRE-0 extends with intra-trade paths.
- **E019 risk-adjusted confidence recovery**
  ([`../E019_confidence_recovery_riskadjusted/`](../E019_confidence_recovery_riskadjusted/))
  — methodological precedent for a **risk-adjusted primary metric** on
  a mechanism study; E021 inherits its verdict-registry discipline
  (§6) and its "single primary, no post-hoc swaps" rule (§7).
- **E020 MFE-ratcheted trail, E023 post-BE structure trail, E024 near-
  TP stall exit, E025 joint exit stack** — sibling PRE-0 consumers;
  E021's `parked_lower_variance_lower_return` special case exists to
  feed candidates into E025.
- **Production references (read-only):**
  `multi-pair-trading-agent/agent/live/config.py::LiveConfig.partial_exits`
  (currently `False`); `agent/live/exit_manager.py` (BE-move-at-1R;
  the residual's stop-state at partial time).

**Existing bibliography (already in `reviews/refs.bib`):**
`benjamini1995controlling` (BH-FDR family across the 9 arms);
`bailey2014deflated` and `bailey2014pseudo` (deflated Sharpe + PBO for
the selected arm); `harvey2016cross` (selection-context reporting);
`efron1993bootstrap` (paired bootstrap CIs, 5,000 resamples);
`nosek2018preregistration` (pre-registration ethos);
`chan2009quantitative` (drawdown-throttle / scale-out precedent).

**Bibliography to ADD before the E021 REPORT** (not added here to
avoid a concurrent-write race on the shared bib — flagged for the
coordinator; see return-list at protocol-close):

- `sharpe1966` (or `sharpe1994`) — the primary metric (Sharpe on per-
  trade R) needs its canonical citation, currently absent from
  `refs.bib`. Flagged in E019 §8 as well; land once, cite from both.
- `kaminski2014stop` — Kaminski & Lo, "When Do Stop-Loss Rules Stop
  Losses?" (JFM 2014) — the closest peer-reviewed treatment of
  mechanical partial-exit / stop rules and their effect on the
  distribution of realized R. Justifies the study's framing that a
  variance-reducing exit rule can be legitimate even at flat mean R.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| Base ledger | EURUSD H4 `all_on` 2015-01 → 2025-12 (737 trades) | re-analysis under new pre-registered rule; no fresh sealed slice consumed | E004, E013, E017 |
| Path extension (PRE-0) | EURUSD/GBPUSD/USDCAD H4 intra-trade OHLC + MFE/MAE, 2015-01 → 2025-12 | first consumer of PRE-0 for EURUSD; GBPUSD and USDCAD generated fresh by PRE-0 from the same `all_on` harness | none (new shared data plane) |
| Replay (Phase 2) | per-trade counterfactual R under 9 arms × 5 folds × 3 symbols | new simulation, deterministic under seed 42 | none |

**No sealed `(pair, TF, split)` bar slice is consumed for a
statistical claim on new market bars.** The counterfactual replay is a
post-trade transformation of the intra-trade path recorded from the
already-reported deployed-cell trades — it does not re-open a Stage-1
screen on new bars. A `planned` row is added to `DATA_LEDGER.md` when
Phase 2 starts, marked `re-analysis, no fresh selection`.

The two-fill accounting rule (§3.3) is the only novel data-plane
statement in this experiment; it is defined in this protocol and
implemented in `programs/E021/`, not in the shared PRE-0 replay engine
(which is arm-agnostic).

---

**Pre-registration commit:** _(hash after push)_
