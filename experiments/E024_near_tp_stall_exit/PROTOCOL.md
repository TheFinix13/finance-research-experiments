# E024 — Near-TP stall exit (pre-registered)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-20 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a design document.** No code is built or run under E024 tonight.
> The deliverable is a pre-registration the user can approve. Follow
> [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md); register in
> [`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
> [`../../reviews/refs.bib`](../../reviews/refs.bib). Consumes the shared
> counterfactual-replay data plane
> [`programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
> (PRE-0).

The deployed `zone_d1_against` / H4 / all cell fires a fixed 1.5R take-profit
and, once the trade is in favour beyond breakeven, relies on the BE
migration + wick-proof stack to protect open risk. On 2026-07-20 the user
flagged a specific pathology on **GBPUSD short 2969136564**: the trade
reached MFE **79.1 pips** against a TP distance of **79.6 pips** — half a
pip shy of the take-profit — then consolidated for hours, failed to
extend, and eventually reversed **36.5 pips away** from the MFE. The
1.5R TP itself is the wrong knob to touch (it survived E004 walk-forward
and E005 cross-pair sealed); the missing behaviour is **detecting
failure-to-extend near the take-profit** and exiting at market before the
reversal completes.

E024 asks: **once MFE has entered a near-TP zone (candidate 1.30R–1.45R),
does a deterministic stall detector — wall-clock, H1-range, H1-reversal, or
bar-stall — improve the per-trade R distribution of the deployed cell
without eating so many clean take-profits that the aggregate is a
wash?** The stall is a *deterministic failure-to-extend* signal, not a
reversal prediction — we are not asking the harness to forecast direction,
only to observe that the favourable move has stopped extending.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Literature in
[`../../reviews/refs.bib`](../../reviews/refs.bib).

---

## §0 Reuse declaration (no production code touched)

E024 Phase 1 (this document) writes **no code**. Phase 2 builds an
evaluation harness under `programs/E024/` that consumes the shared
counterfactual-replay data plane (PRE-0 —
[`programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)).
The deployed 1.5R TP, wick-proof, BE migration, and PLG layers are
**unchanged**. Production references are **read-only**.

| Purpose | Module / artefact | Status |
|---|---|---|
| Live MFE tracking (pips) | `multi-pair-trading-agent/agent/live/monitor.py::PositionMonitor._track_excursion` (writes `mfe_pips` per ticket into `self._excursion`) | read-only |
| Persisted excursion snapshot | `state.json::excursion` (contains `mfe_pips`, `mae_pips`, `last_price`, `last_profit`, broker stop/TP) | read-only |
| Deployed cell / TP anchor | `zone_d1_against` H4 all with `target_rr = 1.5` (E004/E005 locked) | read-only |
| Counterfactual replay data | `programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl` (PRE-0) | read-only consumer |
| Replay engine | `programs/_shared/counterfactual_replay/replay.py` (PRE-0) | read-only consumer |
| E024 harness (Phase 2) | `finance-research-experiments/programs/E024/` (new) | to be built |

**Live-implementation note (recorded here, not built in Phase 2).** The
current `PositionMonitor._track_excursion` updates `mfe_pips` every ~5 s
poll but does **not** currently persist an `mfe_ts` timestamp alongside
it. Under Phase 3, capturing `mfe_ts = now()` whenever `mfe_pips` is
raised is a one-line addition inside `_track_excursion`; the S1 wall-clock
detector then reads `now() - mfe_ts` on every poll. This is factually a
tiny live-code delta, but it **is** a live-code delta — this pre-reg
declares it, so the "read-only production references" claim above stays
honest. The M5/M15/H1 candle-boundary polling required for the S2/S3/S4
bar-based arms is **not** in the current architecture (the loop is
H4-clock-driven), so those arms need new intraday-polling infrastructure
in the live agent — a follow-up Phase-3 dev task that does not block this
study.

---

## §1 Hypotheses (operational)

Let the deployed cell's per-trade R-distribution over its historical
window be the baseline. An E024 arm is a triple
`(activation_R, stall_signal, exit_action)`; on every trade whose MFE
reaches at least `activation_R`, the stall detector arms and — if it
fires before the actual TP is hit — the trade closes per `exit_action`,
producing an alternative realised R for that trade.

- **H0 (null).** No stall-exit arm improves the per-trade R distribution
  over the deployed cell's baseline on the pre-registered **primary**
  metric (§4), across walk-forward folds and all three symbols
  (EURUSD, GBPUSD, USDCAD) — i.e. the near-TP zone is not exploitable
  by any deterministic stall signal at any activation threshold.

- **H1 (alt).** At least one stage-1 arm delivers **Δ Sharpe (paired,
  bootstrap-95 % CI lower bound > 0) AND positive point estimate on
  ≥ 4/5 walk-forward folds AND joint fold p < 0.05**, and survives
  BH-FDR at α = 0.10 across the 24-arm stage-1 family.

- **H2 (parsimony / live-implementability).** If **S1_wallclock** ties any
  bar-based signal (S2/S3/S4) on the primary metric within a small
  practical margin (Δ Sharpe overlap of CIs), prefer **S1** for Phase 3
  live deployment: it is drop-in feasible on the current 5 s poll loop,
  while S2/S3/S4 require new intraday-polling infrastructure in the live
  agent. The stage-2 sweep advances the S1 arm in the tie-break case.

- **H3 (false-positive honesty).** A stage-1 arm can post a positive
  Δ Sharpe by clipping the left tail of the near-miss cohort while
  simultaneously destroying a large fraction of clean take-profits. If
  the winning arm's **Δ P(false positive) > 50 %** (rule fires and the
  observed path would have hit TP anyway — §4 secondary), the arm is
  labelled **`parked_false_positive_heavy`** and does not auto-advance
  to Phase 3 — it requires explicit user review of the good-trades-lost
  vs bad-trades-saved trade-off before deployment.

---

## §2 Separation

- **Does this touch the trading agent?** **No in Phase 1–2.** Phase 3
  (production wiring, gated on an `alive` verdict from this study) will
  add (a) an `mfe_ts` capture line in `PositionMonitor._track_excursion`
  and (b) a stall-exit hook in the exit-priority chain (per SPEC §4.3
  ordering: below hard SLs, above broker-TP). Phase 3 is a separate,
  gated deliverable in `multi-pair-trading-agent`.
- **Prior uses of the same data slice.** The deployed-cell historical
  ledger (`zone_d1_against` H4 all, EURUSD 737 trades locked from
  E017 §A1; GBPUSD/USDCAD to be regenerated by PRE-0 from the same
  E013 `all_on` harness) has been consumed by E013 (safety-layer
  contribution), E017 (parked), E019 (dead), and is the shared substrate
  for E020/E021/E023/E025. E024 opens a **new statistical family** on
  intra-trade paths that PRE-0 emits for the first time (`mfe_pips`,
  `mfe_ts`, `path_m5`, `path_h1` — not previously exposed at the
  summary-ledger level); as such it is a new family for FDR purposes,
  documented as a `planned` row in `DATA_LEDGER.md` when Phase 2 starts.
- **No live-path coupling.** All exits in this study are simulated on
  historical bars via the PRE-0 replay engine. The 2026-07-20 GBPUSD
  observation is descriptive motivation, not a statistical claim.

---

## §3 Rule specification (frozen)

### §3.1 Activation

Let a trade have entry price `P0`, direction `d ∈ {long, short}`, stop
distance `stop_pips`, and take-profit at `P0 ± 1.5 · stop_pips` (deployed
cell property, locked from E004). Let `mfe_pips(t)` be the running MFE
at intra-trade time `t` (from PRE-0's `path_m5` reconstruction).

The stall detector **arms** the first time
`mfe_pips(t) / stop_pips ≥ activation_R`. Before that moment, no stall
signal can fire. Once armed, the detector stays armed until (a) the
broker TP is reached (rule irrelevant), (b) a hard SL is reached (rule
irrelevant, hard SL has higher exit priority — SPEC §4.3), or (c) a
stall signal fires and `exit_action` executes.

`mfe_ts` = timestamp of the M5 bar whose high (long) or low (short)
produced the current `mfe_pips`; on ties, the earliest bar wins (SPEC
§1 derivation rule, deterministic).

### §3.2 Stall-signal definitions (locked)

- **S1_wallclock.** Fires at any bar `t` (M5 resolution) where
  `t - mfe_ts ≥ stall_secs`. Interpretation: MFE has not extended for
  `stall_secs` seconds. **Wall-clock, timeframe-independent.** This is
  the live-implementable MVP — one addition to `_track_excursion`
  (capture `mfe_ts`) plus one check per 5 s poll.

- **S2_h1_range.** On each completed H1 bar after activation, let
  `W = {c_{n-3}, c_{n-2}, c_{n-1}, c_n}` be the last 4 consecutive H1
  closes. Fires iff `max(W) − min(W) ≤ 10 pips`. Interpretation: tight
  consolidation inside the near-TP zone.

- **S3_h1_reversal.** On each completed H1 bar after activation, let
  `c_n` be the most recent H1 close and let the prior 3 H1 closes be
  `{c_{n-3}, c_{n-2}, c_{n-1}}`. For a long, let
  `E = max(c_{n-3}, c_{n-2}, c_{n-1})`; fires iff `c_n ≤ E − 3 pips`.
  For a short, let `E = min(c_{n-3}, c_{n-2}, c_{n-1})`; fires iff
  `c_n ≥ E + 3 pips`. Interpretation: a completed H1 close has crossed
  back past the prior 3-bar favourable extremum by ≥ 3 pips.

- **S4_bar_stall_h1.** On the completion of each H1 bar after
  activation, check whether `mfe_pips` has made a new high (long) or
  new low (short) during that H1 bar. Fires on the completion of the
  **3rd consecutive** post-activation H1 bar without a new MFE
  extension. Interpretation: three H1 bars of no progress.

- **S5_any_of_1-4.** Fires iff **any** of S1_wallclock, S2_h1_range,
  S3_h1_reversal, or S4_bar_stall_h1 fires on the same bar. To be
  well-defined, S5 must fix an S1 `stall_secs`; **locked at 3600 s**
  for the S5 arms (matches the motivating trade's timing scale and
  keeps the family size at 24 as scoped). No sweep of `stall_secs`
  inside S5 (that would inflate the family to 33 arms and steal power
  from the stage-1 screen).

Formal union rule for S5 on a given bar `t`: `fire_S5(t) := fire_S1(t;
stall_secs = 3600) ∨ fire_S2(t) ∨ fire_S3(t) ∨ fire_S4(t)`. Exit-priority
inside E024 is irrelevant (whichever sub-signal fires first triggers the
same `exit_action`); the SPEC §4.3 cross-rule priority (E024 stall exit
sits between hard SLs and broker TP hit) applies unchanged.

### §3.3 Exit actions (stage 2 only; stage 1 fixes `close_at_market`)

- **`close_at_market`** — close the full position at the current bid/ask
  on the firing bar. `exit_reason = "e024_stall_close"`.
- **`move_stop_to_current`** — invoke `adjust_stop(price = current bid
  for long / ask for short)` under SPEC §4.2 monotonicity (only tightens
  never loosens). Position stays open; may still hit either the moved
  stop or the broker TP. `exit_reason` becomes `"e024_stall_trail"`
  if the moved stop later fills.
- **`move_stop_to_mfe_minus_2p`** — tighten stop to `entry + (mfe_pips −
  2) · pip / stop_dir` (i.e. lock in almost all of MFE minus a 2-pip
  cushion). Same monotonicity guard. `exit_reason` = `"e024_stall_lockmfe"`.

Stage 2's `move_stop_*` arms preserve the option value of a late-extension
push through TP, at the cost of giving back the 2-pip cushion if price
reverses cleanly to the new stop.

---

## §4 Locked parameters (frozen at approval)

### §4.1 Stage-1 grid (24 arms, family size 24)

| Knob | Value(s) | Rationale |
|---|---|---|
| `activation_R` | {1.30, 1.40, 1.45} | 1.30R = generous zone (0.20R below TP), 1.40R = balanced, 1.45R = strict near-miss (matches motivating trade at 1.49R MFE / 1.5R TP). Three settings; no post-hoc addition. |
| `stall_signal` | {S1_wallclock, S2_h1_range, S3_h1_reversal, S4_bar_stall_h1, S5_any_of_1-4} | §3.2 locked definitions. |
| `stall_secs` (S1 only) | {900, 1800, 3600, 14400} s (= 15 min, 30 min, 1 h, 4 h) | Spans intra-H4-bar (900 s) to a full H4 bar (14400 s). Four settings; no fifth added post-hoc. |
| `stall_secs` (S5 only) | 3600 s (locked, not swept) | See §3.2 union-rule justification; keeps family size at 24. |
| `exit_action` | `close_at_market` (stage 1 only) | Simplest exit; isolates the detection question from the exit-mechanics question. Stage 2 sweeps the exit action. |
| Symbols | EURUSD, GBPUSD, USDCAD | Deployed cells (E004/E005). |
| Timeframe / cell | H4 / `zone_d1_against` / all-sessions | Deployed cell (E004 locked). |
| Window | 2015-01-01 → 2025-12-01 | Matches PRE-0 §2 and E017 §A1. |
| Walk-forward folds | 5 (PRE-0 §3 folds 1–5) | Inherited from E004; no test-slice leakage. |
| Trade universe | near-miss cohort = trades whose `mfe_r ≥ min(activation_R)` = 1.30 | Rule cannot fire on trades that never reach 1.30R MFE; those trades are unchanged by every stage-1 arm and are still counted in the aggregate R-distribution (as baseline R). |
| Random seed | 42 | Convention. |
| Bootstrap resamples (CI on Δ Sharpe) | 5,000 | Convention. |
| Path resolution | M5 (SPEC §1); H4 fallback flagged, not silently dropped | For S1 the 5 s live poll degrades to M5-bar granularity in the replay — declared explicitly so replay ≠ live in that one dimension. |

Stage-1 arm-count derivation: `3 (activation_R) × 4 (S1 stall_secs) +
3 × 1 (S2) + 3 × 1 (S3) + 3 × 1 (S4) + 3 × 1 (S5) = 12 + 3 + 3 + 3 + 3 =
24`. Every one of these 24 arms is scored on the primary metric and
counted in the BH-FDR family (`PROTOCOL_DISCIPLINE.md` §4:
compute-vs-claim).

### §4.2 Stage-2 grid (3 arms, gated on stage-1 alive verdict)

If — and only if — at least one stage-1 arm receives an `alive` verdict
under §6, its `(activation_R, stall_signal[, stall_secs])` triple is
carried into stage 2 and combined with:

| Knob | Value(s) | Rationale |
|---|---|---|
| `exit_action` | {`close_at_market`, `move_stop_to_current`, `move_stop_to_mfe_minus_2p`} | Three exit mechanics on the fixed winning detector. |

Stage-2 family size = 3, evaluated with per-cell α = 0.05 (`PROTOCOL_DISCIPLINE.md`
§2 confirm-stage convention). **Stage 2 is authorised only if stage 1
produces at least one `alive` verdict at BH-FDR α = 0.10; otherwise the
study stops per the §6 stop rule and Stage 2 does not run.**

**No parameter above is tuned during Phase 2.** Phase 2 selects only
among the discrete frozen grids.

---

## §5 Validation method (Phase 2 — not run in Phase 1)

### §5.1 Data plane

Consumer of PRE-0
([`programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)).
E024 imports `programs/_shared/counterfactual_replay/replay.py` and
registers a `RuleFn` per arm. Required fields per trade record: `mfe_pips`,
`mfe_ts`, `stop_pips`, `direction`, `entry`, `take_profit`, `path_m5`,
`path_h1`, `exit_time`, `exit_price`, `exit_reason`, `r`, `pnl_pips` —
all schema §1 of the SPEC.

### §5.2 Per-arm counterfactual

For each of the 3 symbols × 5 folds × 24 stage-1 arms:

1. Read the test-slice trades for that fold from PRE-0.
2. For each trade, run `replay(trade, arm_rule)` under the SPEC §4
   invariants (no look-ahead; stop monotonicity; exit-priority ordering).
3. Assemble the alternative per-trade R sequence for the arm on that
   (symbol, fold).
4. Compute the paired Δ statistic vs the baseline R sequence for the
   same (symbol, fold) — pairing is exact (same trade IDs).

### §5.3 Metrics (frozen)

**Primary.** Δ **Sharpe of per-trade R sequence** — arm minus baseline —
paired, bootstrap-95 % CI (seed 42, resamples 5000, per-trade
pair-resampling). Reported per (symbol, fold) and pooled across
folds within symbol; the pooled per-symbol Δ Sharpe is the arm's
per-symbol point estimate. Sharpe is computed on the per-trade R
sequence (mean R / std R, unannualised — this is a per-trade edge study,
not a horizon-return study; annualisation would introduce a bar-count
denominator that E024 does not touch).

**Secondaries** (reported with 95 % bootstrap CIs, guardrails and
context, **not** promotable to primary post hoc):

1. **Δ mean R** — location of the R distribution.
2. **Δ P(worse-than-stall-trigger)** — for the near-miss cohort
   (trades that reached `activation_R`), the probability that the
   trade's final outcome R is worse than R at the moment the stall
   trigger fires (`R_at_stall = mfe_r_at_fire − round-trip cost`).
   Captures the "how often does the trade actually give back the near-
   miss gain" magnitude the motivating GBPUSD case exemplifies.
3. **Δ mean R of the near-miss cohort** (trades that reached
   `activation_R`). Isolates the arm's effect on the population it
   actually touches.
4. **Δ tail-mean R** — mean of the worst 10 % of R outcomes. A
   left-tail cross-check on the primary.
5. **Δ P(stall trigger fires)** — activation rate; how often the rule
   even engages. An arm with 0 % fire rate cannot help or hurt.
6. **Δ P(false positive)** — the arm's fire rate on trades whose
   **actual observed path** subsequently reached TP anyway (i.e. the
   rule closed a winner early). Deterministic from the historical
   path: fire time `t_fire < actual exit_time` AND actual `exit_reason
   == "tp"` ⇒ this trade is a false positive under the arm.
7. **Operational:** count of trades touched per fold (for power),
   count of TP-hits eaten (for user readability).

### §5.4 Statistical pipeline

- **Fold-level positivity.** An arm is "fold-positive" iff its per-fold
  Δ Sharpe point estimate is > 0. Fold-positive-in-≥ 4/5 is one of the
  three legs of the `alive` verdict (§6).
- **Joint fold p-value.** Combine the 5 per-fold p-values into a joint
  arm-level p via Stouffer's Z (fold weights = √n_fold). Report both
  Fisher and Stouffer for robustness; the pre-registered decision uses
  Stouffer.
- **BH-FDR (stage 1).** Pool the 24 arm-level joint p-values across
  the family. Apply Benjamini–Hochberg at **α = 0.10**
  (`benjamini1995controlling`). An arm's rejection at BH is a
  necessary condition for `alive`.
- **Multiplicity honesty.** Report the selected arm's selection width
  (24) and a deflated statistic for the selected arm
  (`bailey2016pbo`, `bailey2014deflated`), plus the PBO across the
  24-arm family, so a reader can gauge inflation.
- **Cross-symbol aggregation.** The primary decision is per-symbol
  (each of EURUSD, GBPUSD, USDCAD scored independently); an arm can
  be `alive` on a subset of symbols. A cross-symbol per-arm summary
  is reported for context but is not the decision variable — this
  matches the E005 cross-pair posture (per-symbol survival, not
  pooled-across-symbols averaging).
- **Stage-2 gating (deterministic).** If stage-1 BH-FDR produces
  **≥ 1** rejection whose per-arm CI-LB > 0 AND fold-positive-in-≥ 4/5
  (i.e. an `alive` arm — §6), stage 2 runs with the winning arm's
  detector fixed. If stage 1 produces **0** such arms, stage 2 is
  cancelled and the study stops.

### §5.5 Ex-post narrative on the motivating trade (illustrative, n = 1)

The motivating case is descriptive, not a statistical claim
(analogous to E017's 2026-07-08 replay). Reported for reader
grounding only.

**Case A — the "good miss" (GBPUSD short 2969136564).**
- Entry 1.35060 short; TP 1.34264 (79.6 pips = 1.5R ⇒ `stop_pips ≈
  53.07` and stop ≈ 1.35591); MFE 79.1 pips on Friday 2026-07-17
  (≈ 1.49R). Under arm `activation_R = 1.45, stall_signal =
  S1_wallclock, stall_secs = 3600, exit_action = close_at_market`:
  1. MFE crosses 1.45R (≈ 77.4 pips) around Friday morning UTC → detector
     arms.
  2. MFE peaks at 79.1 pips (≈ 1.49R); `mfe_ts` recorded.
  3. Price stalls; wall-clock elapsed since `mfe_ts` grows past 3600 s.
  4. Rule fires: close at market at ≈ 1.34300 → +76 pips realised
     (≈ +1.43R = +$7.60 for a 0.01-lot GBPUSD ticket at `$0.10/pip`;
     corrected from the initial $4.32 estimate in the review brief,
     which used the wrong pip value).
  5. Compare vs the actual open-position unrealised ≈ +$4.26 four days
     later (state.json `last_profit`, at price 1.34634 = 42.6 pips
     favor × $0.10/pip) after price reversed 36.5 pips off MFE.

**Case B — the "clean TP" false-positive check (GBPUSD short 2966547972,
07-15).** This trade hit TP cleanly under the deployed rules. Under
the same arm, whether the detector fires depends on the intra-trade path
that PRE-0 has not yet emitted at pre-registration time. Two branches
are declared here so the report can honestly present either outcome:
- **Branch B1 (rule does NOT fire).** MFE marches monotonically toward
  TP inside `stall_secs = 3600` — the wall-clock timer resets whenever
  `mfe_pips` extends. Detector arms at 1.45R, TP hits at 1.50R within
  3600 s of the last MFE update → S1 never fires, actual TP preserved,
  **not** a false positive.
- **Branch B2 (rule DOES fire).** MFE reaches 1.45R, plateaus briefly
  past 3600 s (a benign consolidation, not a stall), S1 fires, position
  closes at ≈ 1.47R; PRE-0's path shows TP is reached shortly after
  → this **is** a false positive. Counted in Δ P(false positive) for
  this arm.

The report resolves branch B1 vs B2 from PRE-0 data. The point of
including both here is that the answer is **deterministic given the
path** — E024 does not ask the reader to trust a model, only to trust the
bar record.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4,
extended with study-specific `parked_*` reasons (E017/E019 precedent).

**Verdict labels (locked, per-arm at stage 1):**

- **`alive` → carry the arm into stage 2** iff **all** hold:
  1. Δ Sharpe **bootstrap-95 % CI lower bound > 0** on the pooled
     per-symbol R sequence for at least one symbol; AND
  2. Δ Sharpe point estimate > 0 on **≥ 4 of 5** walk-forward folds
     for that symbol; AND
  3. Joint fold p (Stouffer) **< 0.05** for that symbol; AND
  4. Arm survives **BH-FDR at α = 0.10** across the 24-arm stage-1
     family on that symbol's per-arm joint p.
- **`parked_low_yield`** — point estimate positive but CI includes 0
  **OR** fold-positive-in-exactly-3 folds. Signal is directionally
  right but too weak / unstable to earn stage-2 real estate; do not
  ship.
- **`parked_false_positive_heavy`** — the winning stage-1 arm satisfies
  the `alive` conditions on Δ Sharpe **but** its Δ P(false positive)
  **> 50 %** on the near-miss cohort. Not a fail per se — the arm
  makes money on average by clipping the left tail — but it does so
  by eating over half of the clean-TP wins in the near-miss cohort,
  which the user has flagged as needing an explicit human trade-off
  decision before deployment. Requires user review before Phase 3.
- **`dead`** — no arm meets the `alive` criteria. Study stops; keep
  the current 1.5R fixed TP without a stall overlay; write
  `STOP_NOTICE.md`.

**Stop rule (pre-declared).** If **0** arms are `alive` at the end of
stage 1, STOP: keep the deployed 1.5R TP as-is, write `STOP_NOTICE.md`,
and do **not** open a stage 1b or extend the grid. If ≥ 1 arm is
`parked_false_positive_heavy` and 0 arms are `alive`, still STOP under
the same rule — `parked_false_positive_heavy` is a Phase-3 gate, not a
substitute for `alive`.

**Discipline guards** (`PROTOCOL_DISCIPLINE.md` §5). All §3/§4 formulas
and constants are **frozen at approval**. Phase 2 selects only among
the discrete stage-1 candidate set — **no continuous parameter tuning,
no post-freeze grid extension, no new stall signal added after
approval**. A negative or inconclusive result **is reported**
(`STOP_NOTICE.md`, E012/E015/E016/E017 convention;
`nosek2018preregistration`).

**Anti-cherry-pick.** The primary metric is Δ Sharpe. Secondary
metrics (§5.3) are guardrails and cannot be promoted post hoc to
manufacture a win. The winning arm's edge is reported with its full
95 % CI, its Δ P(false positive), and the family-size-24 selection
context (deflated statistic + PBO), never a point estimate alone.

---

## §7 Amendments

(Empty at pre-registration. Any change to a locked parameter after
pre-registration follows `PROTOCOL_DISCIPLINE.md` §5: a new subsection
here with date, rationale, and guarantee that outcomes were not yet
scored, in a dedicated commit **before** the amended analysis runs. No
silent edits.)

---

## §8 Cross-references

- **Direct motivator (user observation, 2026-07-20).** GBPUSD short
  ticket **2969136564** in the deployed live agent reached MFE 79.1
  pips vs a TP distance of 79.6 pips (0.5 pips shy of the take-profit),
  then consolidated for hours and reversed 36.5 pips off MFE. This is
  a **user-proposed study** — credit the observation to the user
  session review on 2026-07-20; the report will cite the specific
  ticket ID and log timestamp in its introduction.
- **Baseline cell.** [`../E004_walk_forward/`](../E004_walk_forward/)
  and [`../E005_cross_pair_sealed/`](../E005_cross_pair_sealed/) —
  deployed `zone_d1_against` H4 all, `target_rr = 1.5`, locked TP that
  E024 explicitly does not touch.
- **Safety-layer sibling.** [`../E013_safety_layer_contribution/REPORT.md`](../E013_safety_layer_contribution/REPORT.md)
  — `plg_earns_keep` shows the current post-loss / exit layer has real
  costs; E024 tests a targeted addition (stall-only, near-TP-only) in
  the same vein.
- **Metric methodology.** [`../E019_confidence_recovery_riskadjusted/PROTOCOL.md`](../E019_confidence_recovery_riskadjusted/PROTOCOL.md)
  §3/§7 — pre-registered primary/single-primary discipline, deflated
  statistic + PBO, negatives-reported ethos. E024 inherits the
  discipline; it does **not** inherit `RaC_β` — this is a per-trade
  edge study, not a risk-overlay study, so Sharpe on the per-trade R
  sequence is the correct yardstick.
- **Data plane.** [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
  (PRE-0) — path schema §1, walk-forward folds §3, replay engine
  invariants §4, exit-priority ordering §4.3 (E024 stall exit sits
  above broker TP hit and below hard SLs).
- **Sibling consumer studies (same data plane, disjoint arms):**
  [`../E020_mfe_ratcheted_trail/`](../E020_mfe_ratcheted_trail/),
  [`../E021_partial_exit_at_r_milestone/`](../E021_partial_exit_at_r_milestone/),
  [`../E025_joint_exit_stack/`](../E025_joint_exit_stack/) —
  E024 exits **before** TP is hit and only in a narrow near-TP zone;
  E020 trails **after** MFE with a ratchet; E021 partial-closes at
  a lower R; E025 stacks all three under SPEC §4.3 priority.
- **Production references (read-only).** `multi-pair-trading-agent/agent/live/monitor.py::PositionMonitor._track_excursion`;
  `state.json::excursion`; deployed cell config `target_rr = 1.5`.

**Existing bibliography** (in `reviews/refs.bib`):
`benjamini1995controlling`, `bailey2014deflated`, `bailey2014pseudo`,
`harvey2016cross`, `nosek2018preregistration`, `efron1993bootstrap`,
`lopezdeprado2018`.

**References to ADD to `reviews/refs.bib` before the E024 REPORT** (not
added here to avoid a concurrent-write race on the shared bib — flagged
for the coordinator):
- **`bailey2016pbo`** — Bailey, Borwein, López de Prado & Zhu, *The
  Probability of Backtest Overfitting* (JCF 2016) — PBO across the
  24-arm stage-1 family (§5.4).
- **`stouffer1949american`** — Stouffer et al., *The American Soldier:
  Adjustment During Army Life* (1949) — Stouffer's Z fold-p combiner
  (§5.4). A methods-textbook citation (e.g. `whitlock2005combining`,
  *Journal of Evolutionary Biology*) is an acceptable substitute if
  the coordinator prefers a peer-reviewed methods paper over the
  original.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| Stage 1 counterfactual replay | PRE-0 `{EURUSD, GBPUSD, USDCAD}_H4_paths.jsonl` (deployed `zone_d1_against` H4 all, 2015-01 → 2025-12, `all_on` toggles) | new counterfactual replay on newly-exposed intra-trade paths (`mfe_pips`, `mfe_ts`, `path_m5`, `path_h1`); a `planned` row is added to `DATA_LEDGER.md` when Phase 2 starts | E017 (EURUSD summary ledger only, no paths); E019 (bootstrap of E017 R-distribution, no paths); E013 (safety-layer, summary only) |
| Stage 2 counterfactual replay (gated) | Same PRE-0 paths, same window | conditional on stage-1 `alive` verdict; separate ledger row on activation | as above |
| Descriptive replay | GBPUSD live-agent ticket 2969136564 (2026-07-17 → 07-20), auxiliary ticket 2966547972 (07-15) — operational records | one-off case studies (n = 1 each), reported descriptively — **not** FDR family members | none (operational records new to this study) |

No sealed `(pair, TF, split)` bar slice is consumed for a statistical
claim beyond what PRE-0 already schedules — E024 opens a **new** family
on intra-trade paths that were not previously exposed at the ledger
level. The 5-fold walk-forward split (PRE-0 §3, inherited from E004) is
the only test-vs-train separation; no test-slice leakage; no re-tuning
of stage-1 grid points on the test slice.

---

**Pre-registration commit:** _(hash after push)_
