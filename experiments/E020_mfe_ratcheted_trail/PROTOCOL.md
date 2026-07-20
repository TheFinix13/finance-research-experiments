# E020 — MFE-ratcheted trailing stop (pre-registered)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-20 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a design document.** Phase 1 writes no production or research
> code. The deliverable is a pre-registration the user can approve.
> Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md); register
> in [`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
> [`../../reviews/refs.bib`](../../reviews/refs.bib). Data-plane spec is
> [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
> (PRE-0) — cited, not duplicated.

---

## Motivation — the 2026-07-20 GBPUSD give-back

On 2026-07-20 the weekly review flagged GBPUSD ticket **2969136564** as
the archetypal give-back trade the deployed cell has no mechanism for:

- opened short at **1.35060** on 2026-07-16, TP **1.34264** (TP distance
  **79.6 pips = 1.5 R**, so 1 R = 53.1 pips);
- price reached MFE **79.1 pips** (0.5 pips shy of TP);
- retraced to **1.34634** and is still open, unrealised **+42.6 pips**;
- **36.5 pips** of paper profit evaporated with **no mechanism** between
  the break-even stop (which triggers at 1 R) and the take-profit (at
  1.5 R).

The existing safety stack — wick-proof SL, BE-migration at 1 R, and the
post-loss guard (E013's `all_on` cell) — closes losses well and locks in
the first 1 R of profit, but from 1 R to TP the trade is either fully
open (all upside available, all upside also refundable) or dead at the
BE stop. No graduated give-back defence exists in that band.

**E020 asks:** does an MFE-ratcheted trailing stop — one that on any bar
where MFE ≥ `activation_R` sets the effective stop to
`entry ± lock_fraction × MFE_current`, monotonic (tightening only), with
BE-at-1 R kept as a floor — catch this class of give-back **without**
degrading the deployed cell's positive Sharpe on the trades it already
wins?

This is an **exit-mechanism** study (mirrors E017/E019 posture, opposite
side of the trade). It changes only *when a live trade is closed*, never
the entry signal, and Phase 3 (production wiring in
`multi-pair-trading-agent`) is gated on an `alive` Phase 2 verdict here.

---

## §0 Reuse declaration (no production code touched)

E020 Phase 1 (this document) writes **no code**. Phase 2 builds a replay
harness under `programs/E020/` that consumes the shared PRE-0 ledger
(`programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl`)
via the shared loader (`programs/_shared/counterfactual_replay/replay.py`).
Production `agent/live/monitor.py::PositionMonitor._check_exit` and
`agent/live/soft_stop.py` are **read-only references** for the BE-migration
and hard-stop semantics that the E020 ratchet must interoperate with;
nothing here trades, routes orders, or edits live parameters.

| Purpose | Module / artefact | Status |
|---|---|---|
| Exit-check reference | `multi-pair-trading-agent/agent/live/monitor.py::PositionMonitor._check_exit` | read-only |
| BE-migration reference | `multi-pair-trading-agent/agent/live/soft_stop.py` (BE at 1 R) | read-only |
| Shared counterfactual-replay data plane | `programs/_shared/counterfactual_replay/SPEC.md` (PRE-0) | consumed |
| Deployed cell R-distribution / hit-rate | `programs/E017/data/trade_ledger_EURUSD_H4.json` (E013 `all_on`, 737 trades, HR 0.5577) | read-only anchor |
| E020 replay harness (Phase 2) | `programs/E020/` (new, Phase 2) | to be built |

Phase 3 (production wiring — a new stop-move handler in
`PositionMonitor` and a config flag) is a **separate, gated** deliverable
in `multi-pair-trading-agent`, contingent on an `alive` verdict here.

---

## §1 Hypothesis (operational)

Let a trade be characterised at bar `i` by `mfe_i` (max favorable
excursion in pips since entry, computed per SPEC §1) and `stop_pips`
(the entry-time R-distance from `entry` to the catastrophic SL,
locked from the base ledger). Define `mfe_R_i = mfe_i / stop_pips` and
`current_stop_i` = the effective stop after applying, in order,
(a) the entry-time catastrophic SL, (b) the BE-at-1 R migration (if
`mfe_R_i ≥ 1.0`, floor at `entry`), and (c) the E020 ratchet (§3).

**H0 (null).** The MFE-ratcheted trailing stop (any arm on the frozen
§4 grid) does **not** improve the deployed `all_on` cell's per-trade
R-sequence Sharpe: the paired ΔSharpe (arm − baseline), computed per
walk-forward fold and pooled per SPEC §3, has a bootstrap-95 % CI that
includes 0 across all 12 arms after BH-FDR correction at α = 0.10.

**H1 (alt).** At least one arm on the frozen §4 grid delivers
**statistically superior risk-adjusted return** on the same trade
population: the paired ΔSharpe CI lower bound exceeds 0, the arm is
positive in **≥ 4 of 5** walk-forward folds, and the pooled joint
bootstrap **p < 0.05** — all robust to the BH-FDR correction across the
12-arm family (§5). The secondary metrics (Δ mean R, Δ P(winner
reaches ≥ 1 R), Δ tail-mean R (worst 10 %), Δ max-consecutive-loss
streak) are reported as guardrails but are **not** primary decision
variables (§5).

**H2 (parsimony).** If the best-Sharpe arm at `lock_fraction = 0.4`
is statistically indistinguishable from the best-Sharpe arm at
`lock_fraction = 0.7` (paired ΔSharpe CI includes 0 in every fold and
pooled), **prefer the higher `lock_fraction`**: the tighter lock banks
more of the observed MFE per firing, giving up less expectancy in the
long tail of runners that would have reached TP anyway. Symmetrically,
if activation_R ties across `{1.0, 1.2, 1.3}` in the winner-neighbourhood,
prefer the **higher** activation_R (fires less often, disturbs fewer
runners). This is a parsimony tie-break, not a primary hypothesis, and
applies only inside the "alive" set.

---

## §2 Separation

- **Does this touch the trading agent?** **No.** Phase 1 is documents.
  Phase 2 is a replay harness under `programs/E020/` that reads the
  shared PRE-0 path ledger read-only. Phase 3 (production wiring — a
  new `Ratchet` stop-move handler + config flag in
  `multi-pair-trading-agent`) is a **separate, gated** deliverable,
  contingent on the Phase 2 verdict here.
- **Prior uses of the same data.** The trade population and R-distribution
  are inherited from the deployed E013 `all_on` cell (EURUSD 737 trades
  reconciled to hit-rate 0.5577; GBPUSD and USDCAD counts to be published
  in the PRE-0 header line). E020 is a **counterfactual replay** of that
  population under an alternative exit rule — no new `(pair, TF, split)`
  sealed slice is consumed for a statistical claim; the walk-forward
  fold boundaries (§5) mirror E004 exactly. A `planned` row is added to
  `DATA_LEDGER.md` when Phase 2 starts.

---

## §3 Rule specification (formal, frozen at approval)

### §3.1 Definitions

Let a trade `T` have entry price `p_0`, direction `d ∈ {+1, −1}`
(`+1` = long, `−1` = short), stop distance `S = stop_pips` (locked at
entry), TP distance `1.5·S` (deployed cell property, locked). Let bar
`i ∈ {1, 2, …}` walk the M5 path (`path_m5`, per SPEC §1) from
`entry_time` to `exit_time`. Denote by

- `favorable_i` = `d · (high_i − p_0)` for a long, `d · (p_0 − low_i)`
  for a short (in pips) — the bar-`i` favorable excursion;
- `mfe_i` = `max_{j ≤ i} favorable_j` — MFE up to and including bar `i`
  (monotone non-decreasing in `i`);
- `mfe_R_i` = `mfe_i / S`;
- `S_BE_i` = the BE-migrated stop: for a long, `S_BE_i = p_0` once
  `mfe_R_i ≥ 1.0`, else the entry-time catastrophic SL; mirrored for a
  short (BE floors the stop at `p_0` from below on a short by treating
  a short's stop as a ceiling — see production `soft_stop.py`);
- `S_ratchet_i` = the E020 ratchet stop candidate (§3.2 below);
- `S_effective_i` = the exit-effective stop at bar `i` (§3.3 below).

### §3.2 The ratchet rule (frozen)

For arm `(a, ℓ)` with `activation_R = a` and `lock_fraction = ℓ`:

```
S_ratchet_i =
    if mfe_R_i >= a:
        p_0 + d · ℓ · mfe_i         # long: entry + ℓ·MFE (positive-pip lock)
                                    # short: entry - ℓ·MFE (mirror)
    else:
        None                        # ratchet inactive
```

Equivalently in prose: **on any bar where MFE has reached `a` R-multiples
of the entry-time stop distance, place the ratchet stop `ℓ` of the
current MFE inside the entry price** (banking at least `ℓ · MFE_current`
pips of profit if price retraces through the ratchet).

### §3.3 Effective-stop composition (BE floor + monotonicity invariant)

The exit engine composes the entry-time SL, the BE-at-1 R floor, and
the E020 ratchet, and enforces a **monotone tightening** invariant on
the effective stop across bars (SPEC §4.2). For a long:

```
S_candidate_i = max(S_entry, S_BE_i, S_ratchet_i)     # ratchet None => omit
S_effective_i = max(S_effective_{i-1}, S_candidate_i) # never loosen
```

Mirrored for a short (`max` → `min`, signs flipped). This is exactly
SPEC §4.2 "stop authority monotonicity" — the ratchet may only tighten;
if `S_ratchet_i` is looser than an already-established `S_effective_{i-1}`
(from a prior ratchet fire on a larger MFE, or from BE), it is **dropped**
without warning (it is the normal case, not an error). Trades exit at
`S_effective_i` the first bar the bar's adverse extreme crosses it, per
the SPEC §4 replay engine; exit priority is fixed by SPEC §4.3:

```
hard_catastrophic_SL → hard_soft_SL → E024_stall_exit →
E021_partial_close → broker_TP_hit → E020_MFE_ratchet_stop →
E023_structure_trail
```

E020 fires **after** the broker TP check on the same bar — so a bar
that both hits TP and would have triggered the ratchet exits at TP, not
at the ratchet (consistent with production TP semantics).

### §3.4 Pseudocode (single-trade replay, deterministic)

```
def e020_ratchet_rule(state: TradeState, bar: Bar, a: float, l: float) -> ExitAction | None:
    # state carries: entry p0, direction d, stop_pips S, mfe_pips_so_far,
    # current_effective_stop, entry_sl, be_migrated.
    mfe_i = update_mfe(state, bar)                    # monotone, deterministic
    mfe_R = mfe_i / state.stop_pips
    if mfe_R < a:
        return None                                   # ratchet inactive
    ratchet_stop = state.p0 + state.d * l * mfe_i     # candidate
    # BE floor (already present in state.current_effective_stop if mfe_R crossed 1.0)
    be_floor = state.p0 if mfe_R >= 1.0 else state.entry_sl
    # Compose: pick the tightest of {BE floor, ratchet, previous effective}
    if state.d == +1:   # long
        proposed = max(state.current_effective_stop, be_floor, ratchet_stop)
    else:               # short
        proposed = min(state.current_effective_stop, be_floor, ratchet_stop)
    if proposed == state.current_effective_stop:
        return None                                   # no tightening this bar
    return ExitAction(kind="adjust_stop", price=proposed, reason=f"E020_ratchet_a{a}_l{l}")
```

The engine walks `path_m5` per SPEC and closes the trade when the bar's
adverse extreme first touches `S_effective_i`.

### §3.5 Interaction with BE-at-1 R (explicit)

BE-at-1 R remains **exactly as in production** — a hard stop-move to
`entry` the first bar `mfe_R ≥ 1.0`. E020 **supersedes** BE once the
ratchet stop is tighter than BE (i.e. once `ℓ · mfe_i` exceeds the BE
gap of zero, which for any `ℓ > 0` happens on the same bar the ratchet
first fires above 1 R). Below `activation_R`, BE is untouched and behaves
as today. There is **no double-count**: the composition (§3.3) picks the
tightest of the three candidates, and both are stops moving in the same
direction, so the composition is well-defined for every `(a, ℓ)` on the
grid.

**Non-negotiable safety invariant (mirrors SPEC §4.2).** The E020
ratchet is **only** allowed to move the stop **inside** the current
position (tighten). Any attempt to loosen is dropped by the replay
engine and, in Phase 3, by the production `PositionMonitor` handler
(pre-registered guardrail).

---

## §4 Locked parameters (frozen at approval)

### §4.1 The 3-D arm grid (12 arms)

| Knob | Values | Rationale |
|---|---|---|
| `activation_R` | {1.0, 1.2, 1.3} | 1.0 = fire the moment BE migrates (maximum coverage); 1.3 = wait until well past BE and closer to TP (minimum runner disturbance). 1.5 not tested because it coincides with TP. |
| `lock_fraction` | {0.4, 0.5, 0.6, 0.7} | Four settings spanning conservative (lock little, give runners room) to aggressive (lock most of MFE, catch give-backs). 0.5 anchors the design (motivating example). |

12 arms total = 3 × 4 (all combinations frozen; no continuous tuning).

### §4.2 Implementation constants (frozen)

| Knob | Value | Rationale |
|---|---|---|
| Symbols | EURUSD, GBPUSD, USDCAD | Three deployed cells (SPEC §2). |
| Timeframe | H4 (deployed cell) | Matches E013 `all_on`. |
| Window | 2015-01-01 → 2025-12-01 | SPEC §2. |
| Path resolution | M5 (`path_m5`), degrades to H4 with `path_resolution` flag if M5 unavailable | SPEC §1. |
| Walk-forward folds | 5 folds per SPEC §3 (mirrors E004) | No leakage: hyperparameter (arm) chosen on train, scored on test. |
| Baseline | E013 `all_on` cell — wick-proof SL + BE-at-1 R + PLG, ratchet **off** | The deployed configuration; the pair (arm, baseline) is scored per-trade paired. |
| BE-at-1 R | production semantics: stop → entry on first bar `mfe_R ≥ 1.0`; **not** an E020 knob | Kept as a floor per §3.5. |
| Exit priority | SPEC §4.3 | E020 fires after broker TP on the same bar. |
| Primary metric | ΔSharpe of per-trade R sequence (§5) | Paired, bootstrap-95 % CI, seed 42, 5000 resamples. |
| Bootstrap seed | 42 | Convention (matches E017/E019). |
| Bootstrap resamples | 5000 | Convention. |
| FDR | Benjamini–Hochberg at α = 0.10 across the 12-arm family | `benjamini1995controlling`. |
| Ties | Bar-index earliest wins (SPEC §1 determinism) | Fully deterministic replay. |

**No parameter above is tuned during Phase 2.** Phase 2 selects only
among the 12 discrete frozen arms.

---

## §5 Validation method (Phase 2 — not run in Phase 1)

### §5.1 Data plane (defer to PRE-0)

E020 consumes the shared path ledger produced by PRE-0
(`programs/_shared/counterfactual_replay/SPEC.md`) and the shared
`replay(trade, rule, tf_grid="M5", interaction_hierarchy=...)` engine.
The engine's invariants (SPEC §4) — null-rule fidelity, stop-authority
monotonicity, exit-priority ordering, no-look-ahead, determinism — are
**pre-registered guardrails** for E020. If any invariant test fails,
E020 stops and this protocol is amended (per §7 / PROTOCOL_DISCIPLINE §5)
before further analysis.

### §5.2 Per-trade replay (single-arm scoring)

For each arm `(a, ℓ) ∈ §4.1` grid:

1. For each `symbol ∈ {EURUSD, GBPUSD, USDCAD}` and each of the 5
   walk-forward folds (SPEC §3):
   1. Load the test-slice trades from the PRE-0 path ledger.
   2. Replay every trade under the E020 rule (§3.4) via
      `replay(trade, e020_rule)`, obtaining an `AltTradeRecord` per
      trade with modified `exit_time / exit_price / pnl_pips / r /
      exit_reason` and the original `mfe_pips / mae_pips` intact.
   3. Score per-trade paired R-deltas: `Δr_i = r_arm_i − r_baseline_i`
      on the *same trade* (same entry, same path, different exit).
2. Compute per-fold ΔSharpe = `Sharpe(r_arm) − Sharpe(r_baseline)` on
   the paired R-sequence, with a 5000-resample paired bootstrap 95 %
   CI (seed 42).
3. Pool across folds by concatenating per-fold Δr sequences and
   computing a pooled ΔSharpe with the same bootstrap protocol; report
   the pooled joint bootstrap p-value against ΔSharpe = 0.

### §5.3 Primary and secondary metrics

**Primary (single, pre-registered).** ΔSharpe of the per-trade R
sequence, per fold and pooled, with bootstrap-95 % CI. Decision uses
the pooled statistic; the per-fold sign pattern is a robustness
guardrail (§6).

**Secondary (guardrails, reported with CIs; not primary).**

1. **Δ mean R** — the pure expectancy delta (level metric; smaller than
   Sharpe cares about, but decision-relevant if the arm makes trades
   more equal in R rather than a mean shift).
2. **Δ P(winner reaches ≥ 1 R)** — fraction of trades that closed at
   ≥ +1 R under the arm minus the baseline; catches the "banked at least
   1 R" property the motivating GBPUSD case cares about.
3. **Δ tail-mean R (worst 10 %)** — mean R of the worst-decile paired
   trades; guards against the arm hiding worse tails behind an improved
   mean.
4. **Δ max-consecutive-loss streak** — the arm must not create a longer
   loss streak than the baseline (PLG re-arm concern).
5. **`n_fired_no_reach`** — count (and R impact) of trades where the
   ratchet **fired** (MFE ≥ activation_R at least once) but the
   subsequent path never reached TP — i.e. trades where the ratchet
   materially changed the exit. This is the study's mechanism-check
   diagnostic: a large `n_fired_no_reach` with large negative Δr means
   the ratchet is choking runners; a small `n_fired_no_reach` with
   near-zero Δr means the arm is effectively inert.

### §5.4 FDR and multiplicity

Twelve arms are tested against the same baseline on one primary
metric. Apply **Benjamini–Hochberg** at α = 0.10 to the 12 pooled
per-arm p-values (`benjamini1995controlling`; `harvey2016cross` for
selection-context reporting). Report the raw p-values, BH-adjusted
p-values, and the arm-selection context (search width = 12) alongside
the winner's CI so a reader can gauge inflation
(`bailey2014deflated`; `bailey2014pseudo`).

### §5.5 Ex-post replay of the motivating trade (illustrative, n = 1)

GBPUSD ticket **2969136564** is replayed under the anchor arm
`(activation_R = 1.2, lock_fraction = 0.6)` as a **descriptive** case
study. Under the frozen rule:

- entry `p_0 = 1.35060` (short, `d = −1`), TP `1.34264`, `S = 53.07`
  pips (1 R), TP distance `1.5 · S = 79.6` pips;
- BE-at-1 R migrates the stop to `1.35060` on the first bar
  `mfe_R ≥ 1.0`;
- the ratchet activates on the first bar `mfe_R ≥ 1.2` — MFE = `1.2 · 53.07`
  = **63.7 pips**, price = `1.35060 − 0.00637` = **1.34423**;
- at that MFE, `S_ratchet` = `1.35060 − 0.6 · 0.00637` = `1.35060 − 0.003822`
  = **1.34678** (locks `+38.2` pips = `+0.72 R`);
- MFE then extends to **79.1 pips** (price ≈ **1.34269**, 0.5 pips shy of
  TP); by the monotonicity invariant, the ratchet tightens with MFE, and
  `S_ratchet` at MFE = 79.1p = `1.35060 − 0.6 · 0.00791` = **1.34585**
  (locks `+47.5` pips = `+0.90 R`);
- price retraces from 1.34269 back up; on the first bar whose high
  crosses `S_effective` (≈ **1.34585** by monotonicity), the trade exits
  short at that ratcheted stop for `+47.5` pips ≈ `+0.90 R` (`$4.75`
  for a 0.01-lot GBPUSD ticket at `$0.10/pip`); under the illustrative
  snapshot frozen at the fire-point (`S = 1.34678`), the exit is at
  `+38.2` pips = `+0.72 R` = `$3.82`.
- **Contrast with the actual live outcome:** the ticket is still open
  with unrealised `+42.6` pips and no ratchet in the code path, having
  given back **36.5 pips** from the MFE peak.

This is a **case study (n = 1), reported descriptively**. It illustrates
the mechanism; it is **not** a statistical claim, is **not** an FDR
family member, and does **not** substitute for the walk-forward evidence
of §5.2–§5.4. It cannot rescue a losing verdict (§6). The exact fire
point (63.7 p vs 47.5 p depending on which snapshot of the ratchet is
reported) is illustrative only — the tightening pathway between them
is what the replay engine computes bar-by-bar.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4
(labels extended with study-specific `parked_*` reasons per
E017/E019 precedent):

- **`alive` → advance to Phase 3 (production wiring, separately gated)**
  iff, for **at least one** arm on the frozen §4.1 grid, **all** hold:
  1. **Primary:** pooled ΔSharpe bootstrap-95 % CI **lower bound > 0**
     on the paired per-trade R sequence; **AND**
  2. **Robustness:** the arm is **positive in ≥ 4 of the 5** walk-forward
     folds (per-fold ΔSharpe point estimate > 0); **AND**
  3. **Joint significance:** pooled joint bootstrap **p < 0.05** and
     the arm **survives BH-FDR** at α = 0.10 across the 12-arm family;
     **AND**
  4. **Tail guardrail:** Δ tail-mean R (worst 10 %) **≥ 0 within
     bootstrap noise** — the arm may not manufacture a Sharpe gain by
     hiding a fatter tail; **AND**
  5. **Streak guardrail:** Δ max-consecutive-loss streak ≤ 0 within
     noise — the arm may not extend consecutive-loss episodes beyond
     baseline.

- **`parked_low_yield`** — a point-estimate positive arm whose CI
  includes 0 **OR** which is positive in only 3 of 5 folds **OR** which
  fails BH-FDR. The mechanism is directionally right but the evidence
  is thin: do not ship, do not open a Phase 2b, and do not extend the
  grid to fish for significance (`PROTOCOL_DISCIPLINE.md` §5;
  `bailey2014pseudo`).

- **`parked_capital_cost`** — an arm wins on ΔSharpe but breaches a
  guardrail (tail-mean or streak); the ratchet's Sharpe gain is coming
  from making worst trades worse or from clustering losses. Redesign
  required; not shipped.

- **`dead` / STOP (keep the shipped `all_on` cell, write `STOP_NOTICE.md`)**
  — no arm meets the `alive` criteria and no arm qualifies as
  `parked_low_yield`. The ratchet is null on this deployed cell at the
  current sample size and the shipped exit stack stays as-is. Phase 3
  does **not** proceed.

**Stop rule (pre-declared).** If 0 arms are `alive` at the end of
Phase 2, STOP: keep the shipped `all_on` cell and write
`STOP_NOTICE.md`. Do **not** open a Phase 2b, do **not** extend the
grid, and do **not** promote a secondary metric to primary post hoc
(`PROTOCOL_DISCIPLINE.md` §5).

**Parsimony tie-break (H2).** Inside the `alive` set only: if the
best-Sharpe arm at one `lock_fraction` is statistically
indistinguishable from another (paired ΔSharpe CI includes 0), prefer
the **higher `lock_fraction`**; if two `activation_R` values tie,
prefer the **higher** (fires less, disturbs fewer runners). See §1 H2.

---

## §7 Amendments

_None at pre-registration._ Amendments follow
`PROTOCOL_DISCIPLINE.md` §5: dedicated commit before the amended
analysis runs, pre-amendment registry preserved, rationale + guarantee
that outcomes were not yet scored included.

---

## §8 Cross-references

- **Deployed baseline `all_on` cell:** E013 —
  [`../E013_safety_layer_contribution/PROTOCOL.md`](../E013_safety_layer_contribution/PROTOCOL.md),
  [`REPORT.md`](../E013_safety_layer_contribution/REPORT.md). Wick-proof
  SL + BE-at-1 R + PLG stack; +0.796 combined Sharpe [+0.382, +1.224]
  BH-reject over raw alpha; per-trade R distribution anchored to
  hit-rate 0.5577.
- **Risk-mechanism methodology (parked predecessors):** E017
  [`../E017_confidence_gated_cooldown/PROTOCOL.md`](../E017_confidence_gated_cooldown/PROTOCOL.md)
  and E019
  [`../E019_confidence_recovery_riskadjusted/PROTOCOL.md`](../E019_confidence_recovery_riskadjusted/PROTOCOL.md).
  Same pre-registration discipline (single frozen primary, frozen
  discrete grid, no post-freeze retuning, negatives reported); different
  side of the trade (entry-suspension / re-arm vs exit-tightening);
  E020 inherits their FDR + selection-context reporting posture.
- **Walk-forward folds:** E004
  [`../E004_walk_forward/`](../E004_walk_forward/) — 5-fold structure
  mirrored in SPEC §3 and used verbatim here.
- **Shared harness contract:**
  [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)
  (PRE-0) — data schema, replay engine contract, invariants, exit
  priority. E020 uses `replay()` unmodified.
- **Sibling exit-mechanism studies:** E021 (partial exit at 1 R), E023
  (post-BE structure trail), E024 (near-TP stall exit), E025 (joint
  stack). E020 is a standalone arm-set inside SPEC §7's shared plan and
  is composable with the others via the exit-priority ordering
  (SPEC §4.3) in E025.
- **Production references (read-only):**
  `multi-pair-trading-agent/agent/live/monitor.py::PositionMonitor._check_exit`,
  `multi-pair-trading-agent/agent/live/soft_stop.py`.

### Existing bibliography (in `reviews/refs.bib`) cited here

`benjamini1995controlling` (BH-FDR, §5.4),
`bailey2014deflated` (deflated Sharpe / selection context, §5.4),
`bailey2014pseudo` (backtest-overfitting hygiene, §6),
`harvey2016cross` (search-width reporting, §5.4),
`efron1993bootstrap` (paired-bootstrap CI, §5.2),
`chan2009quantitative` (drawdown-throttle / trailing-stop practice,
§3.2 rationale),
`nosek2018preregistration` (pre-registration ethos, whole document),
`lopezdeprado2018tactical` (risk-overlay cost measurement, §5.3 secondary).

### References suggested for `reviews/refs.bib` (for parent to add centrally — **not edited here**)

E020 would benefit from three additions the parent agent should add
centrally (do **not** touch `refs.bib` from this session):

- `kaminski2014trend` — Kaminski, K. M., and Lo, A. W. (2014), "When do
  stop-loss rules stop losses?", *Journal of Financial Markets* 18,
  234–254. Backs §3.2's rationale for MFE-based trailing exits and
  §5.3's "tail-mean guardrail" logic.
- `shefrin1985disposition` — Shefrin, H., and Statman, M. (1985), "The
  disposition to sell winners too early and ride losers too long",
  *Journal of Finance* 40 (3), 777–790. Behavioural motivation for the
  give-back phenomenon E020 targets.
- `odean1998losers` — Odean, T. (1998), "Are investors reluctant to
  realize their losses?", *Journal of Finance* 53 (5), 1775–1798. Same
  behavioural strand, empirical counterpart.

Cite as `[@kaminski2014trend]` etc. once added; do **not** add inline
citations in this protocol until the entries land in `refs.bib`.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| Replay (per-trade counterfactual) | PRE-0 path ledger `programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl` — H4 all-session, 2015-01 → 2025-12, regenerated read-only from the E013 `all_on` production-matching harness | planned (Phase 2) | E013 (summary reuse); E017 pinned the EURUSD ledger `trade_ledger_EURUSD_H4.json` (737 trades, HR 0.5577) as its bootstrap source, read-only |
| Case study (n = 1) | GBPUSD live journal ticket 2969136564, 2026-07-16 → open | descriptive only | none (operational record) |

No **sealed** `(pair, TF, split)` bar slice is consumed for a
statistical claim. The 5-fold walk-forward split (SPEC §3) mirrors E004
and does **not** touch a sealed 2026+ slice; test-slice endpoints stop
at 2025-12. A `planned` row is added to `DATA_LEDGER.md` when Phase 2
starts; a `used` row is added when the replay runs and consumes the
PRE-0 ledger.

---

**Pre-registration commit:** _(hash after push)_
