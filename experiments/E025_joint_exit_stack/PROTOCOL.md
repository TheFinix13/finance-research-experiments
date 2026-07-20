# E025 — Joint exit-stack Pareto validation (pre-registered)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-20 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a composability safety net, not a new mechanism.** E025 exists
> because E020, E021, E022, and E024 each pre-register an independent
> question against the same baseline (deployed `zone_d1_against` cell). If
> each individually validates and we simply turn them ALL on in production,
> the composition may not Pareto-improve on the last-passing subset. E025
> is the study that closes that gap: it explicitly tests the actual stack
> we would deploy against the deployed baseline, using the surviving arms
> from each upstream study.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md); register in
[`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
[`../../reviews/refs.bib`](../../reviews/refs.bib). Consumer of the shared
counterfactual-replay harness at
[`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md).

---

## §0 Reuse declaration (no production code touched)

E025 phase 1 (this document) writes no code and touches no production
module. Phase 2 builds an integration harness under `programs/E025/` that
imports each upstream study's arm implementation from `programs/E020/`,
`programs/E021/`, `programs/E022/`, `programs/E024/`. Production
`agent/live/monitor.py::PositionMonitor`, `agent/live/signal_loop.py`,
`agent/config.py::LiveConfig`, and `agent/journal/target_ladder.py` are
**read-only references** for the levels/mechanisms each individual study
mirrors; nothing here trades, routes orders, or edits live parameters.

Phase 3 (production wiring of the composite `ExitManager` — see §3.5)
proceeds ONLY on an `alive` verdict here, regardless of whether the
individual upstream studies were `alive` on their own. **This is the
gate that decides what actually ships.**

| Purpose | Module / artefact | Status |
|---|---|---|
| Upstream arm A (order placement) | `programs/E022/` (structure TP snap winner) | read-only import |
| Upstream arm B (partial exit) | `programs/E021/` (partial-at-R milestone winner) | read-only import |
| Upstream arm C (MFE ratchet) | `programs/E020/` (MFE-ratcheted trail winner) | read-only import |
| Upstream arm D (near-TP stall) | `programs/E024/` (near-TP stall exit winner) | read-only import |
| Shared replay engine | `programs/_shared/counterfactual_replay/replay.py` | read-only import |
| Baseline cell | `zone_d1_against` `all_on` (wick_proof + be_migration + plg) | read-only reference (via E017/E013 ledger export) |
| Exit-priority ordering | `programs/_shared/counterfactual_replay/SPEC.md` §4.3 | read-only reference |
| Live `ExitManager` (Phase 3 only) | new `agent/live/exit_manager.py` in `multi-pair-trading-agent` | to be built, PHASE 3 ONLY |

---

## §1 Hypothesis (operational)

Let `π0` be the deployed baseline (`all_on` cell, current live behaviour:
BE-move-at-1R, no partial, no ratchet, no snap, no stall exit). Let
`{A, B, C, D}` be the winning arms of E022, E021, E020, E024 respectively
(with hyperparameters fixed to their per-study verdicts). Define four
forward-only compositions:

| Composition | Contents | Description |
|---|---|---|
| `π0` | (none) | Deployed baseline |
| `π1` | A | `π0` + E022 TP-snap only (order-placement change) |
| `π2` | A + B | `π1` + E021 partial exit |
| `π3` | A + B + C | `π2` + E020 MFE ratchet |
| `π4` | A + B + C + D | `π3` + E024 stall exit — full stack |

Compositions apply the SPEC §4.3 exit-priority ordering and stop-authority
monotonicity invariants. Each composition is a *superset* of the prior;
`πi+1` may only add rules to `πi`, never remove or weaken.

**H0 (null).** `π4` does not Pareto-dominate `π0` on the pre-registered
primary metric AND at least one secondary guardrail (§4). The joint
stack, as designed, offers no material improvement over baseline.

**H1 (alt, strong).** `π4` Pareto-dominates `π0`: Δ Sharpe(π4, π0) CI
lower-bound > 0 AND no worse on any secondary guardrail (§4). Full stack
ships.

**H2 (Pareto-monotone alt).** Each successive composition Pareto-improves
on the prior: `Sharpe(πi+1) > Sharpe(πi) − δ_regress` for all `i`, with
`δ_regress = 0.10` (small tolerance for noise). If H2 holds, the ordering
A → B → C → D is empirically justified and each layer earns its keep. If
H2 fails at layer `k`, the layer at position `k+1` degrades the stack:
strip it and ship `πk` instead.

**H3 (parsimony, first-class outcome).** If `π1` (A alone) achieves
Sharpe within `δ_parsimony = 0.15` of `π4`, the simpler order-placement-
only stack ships. Complex lifetime rules add code paths, tests, and
failure modes — parsimony wins ties.

**Primary outcome metric** (pre-registered, mirrors the upstream studies):
- Δ Sharpe(πi, π0) of per-trade R sequence, paired bootstrap-95 % CI,
  seed 42, 5000 resamples, per-fold + pooled.

**Secondary guardrails** (must all clear for `alive`):
- Δ tail-mean R (worst 10 %) — cannot be worse than −0.10R vs baseline
- Δ mean R — cannot be worse than −0.20R vs baseline (level regression cap)
- Δ max consecutive-loss streak — cannot exceed baseline + 2
- Δ P(losing trade < −1.0R) — cannot exceed baseline + 5 %

---

## §2 Separation

- **Does this touch the trading agent?** **No** in Phase 1 (this
  document) and Phase 2 (the composite replay). Phase 3 wires a new
  `ExitManager` module in `agent/live/`, **only** on `alive` verdict here.
- **Prior uses of the same data.** E025 reuses the same trade ledger
  (2015-01 → 2025-12, EURUSD/GBPUSD/USDCAD H4 all-session,
  `zone_d1_against` `all_on`) as E020/E021/E022/E024. **Because each
  upstream study fits arms on the SAME walk-forward split**, using their
  fitted winners on the SAME test slices in E025 creates a subtle
  selection-inflation risk (Bailey et al. `bailey2016pbo`, PBO). We
  mitigate this by (a) reporting the deflated Sharpe ratio (deflated
  against the aggregated arm-family size 12 + 9 + 12 + 24 = 57), (b)
  requiring `positive-in-≥4/5 folds` on Δ Sharpe (a robustness gate
  independent of nominal p-values), (c) reporting a purely OOS
  re-check on the FINAL walk-forward test slice (2024-07 → 2025-12) as a
  sensitivity — if the composition fails there, do not ship regardless
  of pooled p.
- No sealed `(pair, TF, split)` bar slice is consumed for a new
  statistical claim; the walk-forward split is the same as E004's.

---

## §3 Composition mechanics

### §3.1 Rule ordering (locked, mirrors SPEC §4.3)

On any bar during trade lifetime, if multiple rules fire, exit-priority
is applied top-down; the highest-priority firing rule wins:

1. `hard_catastrophic_SL` — broker-side catastrophic stop (existing)
2. `hard_soft_SL` — panic-overshoot stop (existing)
3. **`D` — E024 near-TP stall exit** (market close if stall)
4. **`B` — E021 partial-close event** (level touch on partial_R milestone)
5. `broker_TP_hit` — TP fills at target price (existing)
6. **`C` — E020 MFE-ratcheted stop-move** (adjust stop, does not close)
7. `existing_BE_move_at_1R` — moves stop to entry once MFE ≥ 1R (existing)

**Rule A (E022 TP snap)** does not appear in the lifetime ordering — it
runs ONCE at order placement, before any bar exists.

Rules 6 and 7 both write the stop. The stop-authority monotonicity
invariant (SPEC §4.2, restated here): `current_stop = max(all writing
rules' proposals)` for a long (`min` for a short). A rule may propose a
looser stop; the invariant filters it out.

### §3.2 Rule interactions (three flavours, each analysed)

**Type 1 — Race conditions.** Multiple rules can fire on the same bar
(especially E024 stall + E021 partial + rule 5 broker TP). The ordering
in §3.1 resolves races deterministically. Under the joint stack:
- If E024 and E021 both fire on the same bar (rare — partial fires when
  MFE crosses partial_R; stall fires when MFE ≥ activation_R AND stall
  signal): E024 wins (higher priority) and closes the entire remaining
  position at market. E021 never executes for that trade.
- If E024 and TP both fire on the same bar (bar high touches TP for a
  short as bar closes stall): E024 wins on the FIRST bar (stall detects
  before TP triggers within-bar), preventing TP fill. This is a MODELLING
  choice — the live agent's TP is a broker-side limit order and would
  fill at the tick that touches; the counterfactual replay uses bar
  granularity and cannot distinguish. §5.2 will conduct a sensitivity
  test at M5 resolution to bound this uncertainty.
- If E021 and TP both fire on the same bar (partial + TP): TP wins (rule
  5 above rule 4). Partial does not execute; trade closes fully at TP.

**Type 2 — TP-distance dependencies (via E022).** E022 modifies TP at
order placement. E020, E021, E024 measure activation thresholds as
R-multiples of `stop_pips` (not `tp_pips`), so their parameter grids are
INVARIANT to E022's TP change. Confirmed in §3.3.

**Type 3 — Population selection (via E021).** E021 partial reduces
position size after `partial_R`. The remainder trades onwards with half
(or less) of the original lot. This affects the R-multiple accounting
of subsequent rules only if they use dollar-P&L, not R. Since all rules
use R-multiples, the population-selection effect is captured through the
aggregated R (see §3.4).

### §3.3 R-multiple invariance under composition

For each trade, define:
- `stop_pips` = entry-time |entry − soft_stop|. **Locked at entry.**
- `tp_pips` = entry-time |entry − take_profit`. May be modified by E022 at
  order placement, before any lifetime replay begins.
- `mfe_pips`, `mae_pips` = bar-by-bar excursions from entry.

All lifetime rules (E020, E021, E024) reference `stop_pips` (not
`tp_pips`) in their activation formulas. Therefore their arm parameters
composability-compatible with E022's TP modification: `activation_R` in
E020, `partial_R` in E021, `activation_R` in E024 all mean "R-multiples
of the entry-time stop distance" and do not change semantics when TP
moves.

### §3.4 Multi-fill P&L aggregation

Under `π2/π3/π4` (any composition with E021), a single trade produces
two realized P&L events: the partial fill and the residual exit. The
per-trade aggregated R for the counterfactual ledger is:

```
alt_r = partial_fraction × R_at_partial_fill
      + (1 − partial_fraction) × R_at_residual_exit
```

Both components normalized against the ORIGINAL entry-time `stop_pips`.
This matches E021 §3's own aggregation formula; E025 does not redefine
it.

Under `π4`, if E024 stall exit closes the residual (rather than a TP
fill or a stop hit), the residual R is the exit-price R at the stall
close.

### §3.5 Production `ExitManager` design (Phase 3 preview, NOT built in Phase 2)

If `π4` (or the winning `πi`) validates, the corresponding production
change is a new `agent/live/exit_manager.py` that owns:
- The stop-authority hierarchy (SPEC §4.2, §3.1 above)
- The exit-priority ordering (SPEC §4.3, §3.1 above)
- Each rule registered via a callback: `register(name, priority, fn)`
- A single arbitrator: `def arbitrate(state, bar) → ExitAction | None`
- Comprehensive logging: every rule's proposal on every bar, whether
  it fired, whether it was superseded

This module is behind a config flag (`LiveConfig.exit_manager_enabled =
False` by default). Turning it on in production requires:
1. `alive` verdict on E025 (this study)
2. At least 2 weeks paper-mode observation under Phase 3 config with
   the flag on
3. User sign-off after reviewing paper-mode logs

**This protocol does NOT authorize the production wiring — it authorizes
the study whose verdict determines whether that wiring is proposed.**

---

## §4 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Baseline `π0` | `zone_d1_against` `all_on` (wick_proof + be_migration + plg) | Matches E017/E013 harness; identical to production live |
| Compositions | `π0, π1=A, π2=A+B, π3=A+B+C, π4=A+B+C+D` | Forward-only per-layer additions |
| Upstream arm hyperparameters | **TBD** — filled from E020/E021/E022/E024 verdicts before Phase 2 kickoff | E025 pre-reg is COMPLETE without these values, per PROTOCOL_DISCIPLINE §5 (the family and ordering are locked; the individual arm choices come from each upstream `alive` verdict) |
| Primary metric | Δ Sharpe of per-trade R sequence (paired, bootstrap-95 % CI, seed 42, resamples 5000) | Same as upstream studies; enables direct comparison |
| Secondary guardrails | tail-mean R (worst 10 %), mean R, max consec-loss streak, P(R < −1.0) | See §1 for cap values |
| `δ_regress` (H2 tolerance) | 0.10 Sharpe units | Small noise tolerance; below this the layer is neither adding nor subtracting materially |
| `δ_parsimony` (H3 tolerance) | 0.15 Sharpe units | Slightly larger than δ_regress — parsimony favours the simpler stack unless the complex one is clearly better |
| Walk-forward folds | 5 (per SPEC §3, mirrors E004) | Identical to upstream studies for direct composition |
| Deflated-Sharpe control | Family size = 12 (E020) + 9 (E021) + 12 (E022) + 24 (E024) = **57** | Bailey et al. `bailey2016pbo` deflation across the joint arm search |
| Symbols | EURUSD, GBPUSD, USDCAD H4 all-session | Full three-pair panel |
| Window | 2015-01 → 2025-12 | Full walk-forward window; also do 2024-07 → 2025-12 OOS-only sensitivity |
| Random seed | 42 | Convention |

### §4a Handling of upstream verdicts

E025 Phase 2 does not launch until ALL of E020/E021/E022/E024 have
verdicts registered in EXPERIMENTS.md. Cases:

- **All four `alive`**: Full grid `π0…π4` runs as specified.
- **Three `alive`, one `dead`**: Drop the dead layer from the ordering.
  If E021 is dead, compositions become `π0, π1=A, π3=A+C, π4=A+C+D`
  (renumbered). If E022 is dead, `π0, π2=B, π3=B+C, π4=B+C+D`. Etc.
- **Only two or fewer `alive`**: E025 runs a reduced grid; H3 (parsimony)
  becomes the primary hypothesis — if a single-layer stack ships,
  E025's job is confirming that single-layer works on a fresh test.
- **Zero `alive`**: E025 is `cancelled_dependency_failed`. No stack ships.
- **Any `parked_*`**: Layer is included in an EXPLORATORY (non-verdict-
  bearing) arm; ships gate remains H1 on `alive`-only stack.

**No arm hyperparameter is retuned in E025**. Each upstream verdict pins
its arm's parameters; E025 tests the COMPOSITION at those pinned values.
Any retuning would violate PROTOCOL_DISCIPLINE §5 (no post-freeze
parameter changes).

---

## §5 Validation method (Phase 2 — after all upstream verdicts land)

### §5.1 Replay pipeline

For each fold and each composition:

1. Load per-symbol paths ledger from
   `programs/_shared/counterfactual_replay/data/{symbol}_H4_paths.jsonl`.
2. For each trade in the test slice:
   a. Apply arm A (E022 TP snap) at entry to set `tp_pips_snapped`.
   b. Simulate bar-by-bar (M5 primary, H1 sensitivity, H4 fallback per
      SPEC §1) with the composition's active rules registered in the
      replay engine per SPEC §4.
   c. Extract `alt_r`, `alt_exit_time`, `alt_exit_reason`,
      `partial_fill_r` (if present), `stop_move_events` (if any).
3. Compute per-fold Δ Sharpe(composition, π0), Δ secondaries.
4. Pool across folds; report per-fold and pooled with bootstrap CIs.
5. Deflate the winning composition's Sharpe against family size 57
   (`bailey2016pbo`).

### §5.2 Bar-granularity sensitivity

Because M5 is the finest resolution the paths ledger provides, we cannot
distinguish within-bar orderings of TP-hit vs stall-fire vs partial-fire
on a single M5 bar. Sensitivity: rerun the winning composition with a
uniformly-random ordering when multiple rules fire on the same M5 bar,
compare the Sharpe distribution over 100 random-order draws. If the
Sharpe standard deviation across random orderings exceeds 0.05, the
result is unstable and we must re-run with M1 data (a follow-up data
task, not blocking).

### §5.3 OOS-only sensitivity (2024-07 → 2025-12)

Even if the pooled Sharpe passes, we require the FINAL walk-forward
test slice alone (2024-07 → 2025-12) to also show Δ Sharpe > 0 with CI
lower-bound touching 0 or better. This is the most recent 18-month
period; if the composition fails here, do not ship regardless of
pooled p-value.

### §5.4 The 2026-07-16 GBPUSD live trade case-study (illustrative, n=1)

Not a statistical claim. Replay the actual open GBPUSD trade 2969136564
(entry 1.35060 short, MFE 79.1p at MFE_ts, current price 1.34634)
through each composition using its state.json trajectory. Report the
alternate exit for each composition side-by-side. This is descriptive,
audit-friendly evidence that the composition would have handled a real
case as expected — not a p-value contributor.

Expected on `π4` (with winning arms plugged in):
- E022 snap: no snap fires (nearest sticky level not between entry and
  TP for this trade, per E022 §5 case-study)
- E021 partial: fires when price first crosses 1R (~1.34527) → banks
  ~40 % of position at +1.0R
- E020 MFE ratchet: fires when MFE crosses activation_R × stop_pips
  (~63.7p for activation_R=1.2), sets stop to entry − lock_fraction ×
  MFE; monotonically tightens as MFE grows to 79.1p
- E024 stall exit: MFE reaches 1.49R, S1_wallclock stall_secs=3600 fires
  when price sits at MFE for >1h; residual position closes at ~+1.35R

Aggregate `alt_r` for the composition on this trade should be ~+1.2R
(40 % @ 1.0R + 60 % @ 1.35R) vs current baseline result (still open,
0.80R floating).

### §5.5 Metric computation details

- Sharpe on the per-trade R sequence: `mean(R) / std(R)`,
  UNANNUALIZED (matches E024's choice — the trade-cadence denominator
  should not enter this study's ratio because none of these rules
  changes trade count).
- Bootstrap: pair per-trade indices under the null (differences),
  resample 5000 times, seed 42.
- Per-fold p-value: Stouffer's Z combining 5 fold-level p-values
  (`stouffer1949american`), reported alongside the pooled paired
  bootstrap for cross-check.
- BH-FDR: N/A at this level — E025 tests a fixed ordering of at most
  4 compositions, not a grid family. Deflated Sharpe (`bailey2016pbo`)
  is applied instead for the selection-across-upstream-arms concern.

---

## §6 Success criteria and stop/kill conditions (locked before results)

- **`alive` → advance to Phase 3 (production `ExitManager`)** iff:
  1. Δ Sharpe(π_win, π0) CI lower-bound > 0 AND positive-in-≥4/5 folds
     AND joint bootstrap p < 0.05
  2. All secondary guardrails cleared (§4)
  3. OOS-only sensitivity (§5.3) also positive
  4. Bar-granularity sensitivity (§5.2) SD ≤ 0.05
  5. Deflated Sharpe (family size 57) > 0
  where `π_win` is the highest-index composition that clears H2 (i.e.
  the first `πi+1` that regresses on `πi` by more than `δ_regress` gets
  stripped; ship `πi`).
- **`parked_parsimony_wins`** — H3 fires: `π1` (A alone) is within
  `δ_parsimony` of `π4`. Ship the simpler stack.
- **`parked_composition_regression`** — some layer added negative net;
  ship the largest composition that Pareto-dominates π0.
- **`dead` / STOP** iff no composition dominates π0 on §6.1 + §6.2.
  Write `STOP_NOTICE.md`; keep production `all_on` cell as-is.
  Individual upstream `alive` verdicts do NOT ship without E025 clearance
  — this is the safety net.
- **`cancelled_dependency_failed`** — zero upstream `alive` verdicts.

**Discipline guards.** No post-freeze parameter changes. No post-hoc
composition additions (E023 post-BE trail is a SEPARATE study; if it
lands, E025 does not automatically absorb it — a new E025-successor
study registers). A negative or inconclusive result is reported
(`STOP_NOTICE.md`), never buried.

---

## §7 Amendments

_(Appended after pre-registration commit only. E017/E019 convention:
amendments are dated, described, and never rewrite frozen §3/§4/§6.)_

---

## §8 Cross-references

- **Upstream studies**:
  [`../E020_mfe_ratcheted_trail/`](../E020_mfe_ratcheted_trail/),
  [`../E021_partial_exit_at_r_milestone/`](../E021_partial_exit_at_r_milestone/),
  [`../E022_structure_aware_tp_snap/`](../E022_structure_aware_tp_snap/),
  [`../E024_near_tp_stall_exit/`](../E024_near_tp_stall_exit/).
- **Shared harness**: [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md).
- **Baseline cell + trade ledger source**:
  [`../E013_safety_layer_contribution/`](../E013_safety_layer_contribution/)
  and [`../E017_confidence_gated_cooldown/`](../E017_confidence_gated_cooldown/)
  (E017 pinned the EURUSD 737-trade `all_on` ledger; E025 uses the
  paths-extended version emitted by PRE-0).
- **Methodology**: E019's risk-adjusted-metric framework
  ([`../E019_confidence_recovery_riskadjusted/PROTOCOL.md`](../E019_confidence_recovery_riskadjusted/PROTOCOL.md))
  informs the "level metrics are the wrong yardstick for risk overlays"
  lesson; E025 uses Sharpe (a risk-adjusted metric) as primary,
  consistent with that lesson.
- **Live motivator**: 2026-07-20 weekly review of the deployed VM agent
  (this session's chat, GBPUSD ticket 2969136564 near-miss). Live case
  study appears in §5.4 as descriptive evidence, not a p-value contributor.
- **Production references (read-only)**: `agent/live/monitor.py`,
  `agent/live/signal_loop.py`, `agent/config.py::LiveConfig`,
  `agent/journal/target_ladder.py`.
- **Selection-inflation reference**: `bailey2016pbo` (deflated Sharpe
  across 57-arm upstream family). Add to `reviews/refs.bib` if not
  already present.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| §5.1 replay | EURUSD/GBPUSD/USDCAD H4 all-session `all_on` ledger + paths (PRE-0 output) | new counterfactual composition | E020, E021, E022, E024 each fit arms on same ledger; E025 uses their fitted winners composed |
| §5.3 OOS sensitivity | 2024-07 → 2025-12 test slice only | same ledger, sub-window | fold 5 of the walk-forward is shared with upstream studies; E025 checks composition holds on this sub-window specifically |
| §5.4 live case study | GBPUSD ticket 2969136564 state.json trajectory | descriptive case study, n=1 | one-off live-operational record, not a statistical claim |

No sealed `(pair, TF, split)` bar slice is consumed for a new statistical
claim; the walk-forward split is the same as E004's. A `planned` row is
added to `DATA_LEDGER.md` when Phase 2 begins.

---

**Pre-registration commit:** _(hash after push)_
