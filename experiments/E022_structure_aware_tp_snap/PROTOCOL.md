# E022 — Structure-aware TP snap (order-placement)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-20 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a design document.** No code is built or run under E022 tonight.
> The deliverable is a pre-registration the user can approve before Phase 2
> begins. Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md);
> register in [`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
> [`../../reviews/refs.bib`](../../reviews/refs.bib).

---

## Why E022 exists — the 0.5-pip problem in one paragraph

GBPUSD live ticket **2969136564** (2026-07-16 short, entry 1.35060, TP
1.34264, 79.6-pip target) reached an intra-trade MFE of **79.1 pips** and
never printed the TP. It exited on the reverse — an actual profit-of-run
inside the stop, converted into a scratch/loss by literally **0.5 pips**
of missed fill. The trade's paths-ledger record shows the price stalled at
consolidation and never traded through a nearby sticky level between entry
and the TP. This is a *fill-probability* problem: order books cluster
depth around round numbers and prior-session extremes, and price often
retraces from the near side of a level rather than punching through
[@osler2003currency; @sonnemans2006price]. If the trade's TP is priced
*just past* such a level, the trade is asking the tape to consume that
resting depth for a single pip of extra reward.

E022 pre-registers an **order-placement modification only**: at entry
time, if the mechanically-computed TP sits within `snap_distance` pips of
a "sticky" price level that lies **between entry and TP** (i.e. a level
the price must break through to hit TP), pull TP **inside** that level by
`snap_offset` pips. The trade closes on the near side of the resting
depth, not past it.

**No lifetime replay, no exit-manager change, no entry-signal change.**
E022 changes exactly one number in the live path — the TP price at
placement — and rescores the historical ledger under the new price.

**This is a Reuse consumer of PRE-0** — the shared counterfactual-replay
harness ([`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md)).
Phase 2 (if approved) uses the intra-trade path solely to decide whether
the *new* TP would have filled before the historical exit; the ledger
itself is not regenerated.

---

## §0 Reuse declaration (no production code touched)

E022 Phase 1 (this document) writes **no code**. Phase 2 will build a
level-detector and a per-trade rescorer **under `programs/E022/` in this
repo only**. Production `agent/live/signal_loop.py::SignalLoop._route_signal`
(the placement path where the mechanical TP is set) and
`agent/journal/target_ladder.py` (the observation-only extension-ladder
module) are **read-only references** for level definitions and placement
timing. Nothing here trades, routes orders, or edits live parameters.

| Purpose | Module / artefact | Status |
|---|---|---|
| Placement path (where TP is set at entry) | `multi-pair-trading-agent/agent/live/signal_loop.py::SignalLoop._route_signal` | read-only reference |
| Level definitions (swing / daily / zone_edge / trendline / fib_ext) | `multi-pair-trading-agent/agent/journal/target_ladder.py` (`compute_target_ladder`, `TargetRung`) | read-only reference for detectors |
| Historical ledger + intra-trade path | `programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl` (PRE-0 output) | read-only consumer |
| Rescorer + level reconstruction (Phase 2) | `programs/E022/` (new; not written in Phase 1) | to be built |

The production ladder in `target_ladder.py` is used *only* as the source
of truth for **which detectors** are legitimate (`swing`, `daily_level`,
etc.) and for the reference implementation of each. It is **not** invoked
directly — production returns rungs strictly *beyond* TP (see docstring),
which is the opposite of what E022 needs (see §3.3 below).

---

## §1 Hypothesis (operational)

Let `T` be the historical trade ledger for one (symbol, TF) cell. Let
`ρ(T, arm)` denote the per-trade R sequence obtained by rescoring every
trade in `T` under the E022 snap rule with arm-specific
`(snap_distance, snap_source)` at order placement. Let `Sharpe(·)` be the
annualised Sharpe of a per-trade R sequence (return per unit
cross-trade R-volatility, standard convention for backtest R-series).

- **H0 (null).** For every locked arm in §4, `Sharpe(ρ(T, arm)) ≤
  Sharpe(ρ(T, baseline))`, where `baseline` is the deployed cell's
  unmodified TP placement. The rule adds no risk-adjusted value.

- **H1 (alt).** There exists at least one locked arm for which
  `ΔSharpe = Sharpe(ρ(T, arm)) − Sharpe(ρ(T, baseline))` has a
  bootstrap-95 % CI lower bound `> 0`, is positive in ≥ 4 of the 5
  walk-forward folds (§5), and passes BH-FDR at α = 0.10 across the
  12-arm family. The snap earns keep.

- **H2 (parsimony, level source).** If the winning arm on `snap_source
  = daily_only` is statistically indistinguishable from the winning arm
  on `snap_source = all` (paired ΔSharpe CI overlaps 0), prefer
  `daily_only`: the extra ladder/round-number machinery earns no keep.
  Verdict caps at `parked_daily_only_suffices`.

- **H3 (fill-rate feasibility, negative-outcome first-class).** If, over
  the walk-forward test slices, **< 5 %** of trades have any candidate
  level within `snap_distance` of the mechanical TP for a given
  `snap_source`, that arm is *uninformative* — the deployed cell already
  places TPs away from sticky levels for that source, and no rescoring
  can move the population. Verdict for the family caps at
  `parked_snap_never_fires`; this is a **legitimate acceptable outcome**
  (§6).

**Primary outcome metric (single, pre-registered):** `ΔSharpe` of the
per-trade R sequence, paired across trades, bootstrap-95 % CI, seed 42,
5,000 resamples. Aggregated across symbols with a fixed-effects pooling
weight (per-symbol trade count).

**Secondary / corroborating metrics** (reported with bootstrap CIs but
**not** used as the primary decision variable — anti-cherry-pick, §7):

1. `Δ P(TP fills)` — change in the empirical probability that TP fills
   before any other exit condition (stop, timeout, reverse).
2. `Δ mean R conditional on winner` — winners lose a small amount of R
   (they take profit earlier), so this is expected slightly negative;
   the primary must overcome this via the fill-rate gain.
3. `Δ mean time-in-trade for winners` (bars, and hours via §4 bar↔hour
   map) — expected slightly negative (fills come earlier).
4. `snap_fire_rate` — fraction of trades on which the snap actually
   moved the TP; feeds the §6 `parked_snap_never_fires` gate.

---

## §2 Separation

- **Does this touch the trading agent?** **No.** Phase 1 is documents.
  Phase 2 is a rescorer under `programs/E022/`. Phase 3 (production
  wiring: adding a snap step inside `SignalLoop._route_signal` after
  TP is set and before the broker order goes out) is a **separate,
  gated** deliverable in `multi-pair-trading-agent`, contingent on an
  `alive` verdict from this study through the agent's full validation
  pipeline (grid → holdout → walk-forward → cross-pair → sealed).
- **Prior uses of the same data slice.** The `(EURUSD, H4, 2015-01 →
  2025-12)` trade ledger has been used by **E013** (safety-layer
  contribution, `all_on` cell) and **E017** (bootstrap ledger for MC).
  Both prior uses were summary/bootstrap consumers of the R-distribution,
  not per-trade counterfactual rescorings. `(GBPUSD, H4)` and
  `(USDCAD, H4)` at this window are **fresh** — first per-trade use is
  PRE-0 generation. E022 opens **one new FDR family** on the joint
  (EURUSD, GBPUSD, USDCAD) × H4 slice (12 arms, one primary, §5).
  A `planned` row is added to `DATA_LEDGER.md` when Phase 2 starts.
- **Sibling exit-side studies.** E020 (MFE ratchet), E021 (partial
  exit), E023 (post-BE trail), E024 (near-TP stall exit), E025 (joint
  stack) all consume PRE-0 and manipulate the *exit* side. E022 is the
  only sibling that manipulates the *entry-placement* side (TP price)
  and does **not** need per-bar replay of the trade lifetime. The
  primary-metric families are disjoint (different arms, different
  rules); joint FDR across all six studies is a coordinator concern
  (see [`EXPERIMENTS.md`](../../EXPERIMENTS.md)), not scoped here.

---

## §3 Rule specification (frozen)

### §3.1 Formal snap logic

At order placement, given the historical trade's `direction`, `entry`,
mechanical `take_profit` (= `entry ± target_rr · stop_pips`), and a
level set `L(snap_source)` (see §3.3):

```python
def snap_tp(entry, tp, direction, L, snap_distance_pips, snap_offset_pips):
    # sign = +1 for long, -1 for short (pips point toward TP)
    sign = 1 if direction == "long" else -1
    pip = pip_size(symbol)  # 1e-4 for EURUSD/GBPUSD/USDCAD

    # Candidates: sticky levels the price must break THROUGH to hit TP.
    # i.e. levels strictly between entry and tp on the trade's directed axis.
    candidates = [
        level for level in L
        if is_between(entry, level, tp)   # see §3.2 direction invariant
    ]
    if not candidates:
        return tp                          # no snap

    # Nearest candidate to TP (i.e. the last hurdle before target).
    nearest = min(candidates, key=lambda L_: abs(L_ - tp))

    # Distance from TP to nearest candidate, in pips.
    d_pips = abs(nearest - tp) / pip
    if d_pips > snap_distance_pips:
        return tp                          # too far, no snap

    # Pull TP inside the level by snap_offset pips (never outward).
    new_tp = nearest - sign * snap_offset_pips * pip
    return new_tp
```

**Key properties (invariants, tested):**

- **Idempotence.** `snap_tp(entry, snap_tp(...), ...) == snap_tp(...)`
  for the same level set: after one snap, the new TP is `snap_offset`
  inside the sticky level, so on a second pass the level is no longer
  strictly between entry and new_tp (it is now *beyond* new_tp) and no
  further snap fires.
- **Inward-only monotonicity.** `|new_tp − entry| ≤ |tp − entry|` for
  all inputs. The snap can only *shorten* the target distance; it can
  never lengthen it. This is the direction fix — see §3.2.
- **No level in the set below entry (long) / above entry (short) can
  ever produce a snap.** `is_between` filters those out. This prevents
  the pathological "pull TP past entry" case.
- **`snap_offset < snap_distance`** for every arm in §4 by
  construction (`snap_offset = min(3, snap_distance/2)`), so after a
  snap the new_tp remains strictly between entry and the sticky level.

### §3.2 Direction invariant (the bug fix, called out explicitly)

An earlier scoping formulation of the rule allowed the snap to fire on
levels beyond TP (further from entry than TP). That would have **pulled
TP outward** — increasing target distance and *reducing* fill
probability — the exact opposite of the intended effect. The pre-
registered rule (§3.1) **only fires on levels strictly between entry and
TP**:

```python
def is_between(entry, level, tp):
    # Level is on the trade's directed axis between entry and tp
    # (exclusive of both endpoints; strict inequality on both sides).
    lo, hi = (entry, tp) if entry < tp else (tp, entry)
    return lo < level < hi
```

This is a **hard invariant** (unit-tested in Phase 2, §5). Any rule
implementation that fires on a level beyond TP is a bug and must fail
the invariant test before the arm is scored.

Equivalent statement in words: *E022 only pulls TP inward, never
outward. If the nearest sticky level is on the far side of TP, the
trade keeps its mechanical TP unchanged.*

### §3.3 Level sources `L(snap_source)`

Four values of `snap_source`, deterministic at entry time using data
available at or before `entry_time`:

- **`daily_only`.** Six levels: previous-day high (**PDH**), previous-day
  low (**PDL**), previous-day mid (**PDM = (PDH+PDL)/2**), previous-week
  high (**PWH**), previous-week low (**PWL**), previous-week mid
  (**PWM = (PWH+PWL)/2**). "Previous day" = the D1 bar ending strictly
  before `entry_time`; "previous week" = the W1 bar ending strictly
  before `entry_time`. Both use the same D1/W1 bar source as
  `agent/journal/target_ladder.py::_daily_levels`. Session boundary: UTC.

- **`ladder_top`.** The single **nearest-to-entry rung** of a
  reconstructed extension ladder computed with the same detectors as
  production `target_ladder.py` (`swing`, `zone_edge`, `trendline`,
  `fib_ext`, `daily_level`) but **without** the production module's
  "strictly beyond TP" filter. The ladder is computed over a
  `lookback = 200` H4 bars ending at `entry_time − 1` (no look-ahead),
  `trendline_lookahead = 20`, `dedupe_pips = 3.0`, `max_rungs = 6` —
  parameters mirrored from `compute_target_ladder`. Of the rungs that
  fall *between entry and TP* (per §3.2), the one nearest to entry is
  `ladder_top`. If there are no such rungs, `L(ladder_top) = ∅`.

- **`round_number`.** Levels at every `.00` and `.50` sub-figure within
  `[min(entry,tp), max(entry,tp)]`. Formally, for a 4-decimal FX pair:
  every price `p` such that `p = k · 0.0050` for integer `k` and
  `min(entry,tp) ≤ p ≤ max(entry,tp)`. Concretely for GBPUSD in the
  1.34xxx range: `1.34000`, `1.34500`, `1.35000`, `1.35500`, ... Same
  for EURUSD and USDCAD.

- **`all`.** Union of the three sets above. Duplicates within
  `dedupe_pips = 3.0` are collapsed (nearest-to-entry survives, mirror
  of the production ladder's dedupe rule).

### §3.4 Level-detector availability gap — the reconstruction choice

**Problem.** Historical trades before ~2026-06 do not have the
`target_ladder` field populated in the PRE-0 paths ledger (see SPEC §1
last note: "Historical trades from 2015-2025 will have this field
mostly absent"). Two ways to handle the gap:

- **(a) Reconstruct the ladder from bar-level OHLC** using the same
  detectors as production, applied read-only over `[entry_time −
  200·H4, entry_time)`. Applies to every trade in the full window.
- **(b) Sub-window only.** Evaluate `ladder_top` and `all` arms only on
  the sub-slice where the field is present (post-2026-06). ~6 months
  of forward trades → far below the n-power floor for a 5-fold walk-
  forward.

**Locked choice: (a) reconstruction.** Rationale:

1. **Power.** (b) leaves ~1–2 % of the trade count for `ladder_top` /
   `all` — well below any reasonable per-fold n and worthless for the
   pooled BH-FDR.
2. **Consistency of the level set.** Even for post-2026-06 trades, the
   production `target_ladder.py` returns rungs strictly *beyond* TP
   (module docstring, verified 2026-07-20). E022's rule needs rungs
   *between* entry and TP, so the production output is not directly
   consumable regardless of vintage. A reconstruction is required
   for **all** trades, not just historical ones.
3. **Determinism.** The detectors in `target_ladder.py` are pure
   functions of prior bars and named parameters (`lookback`,
   `trendline_lookahead`, `dedupe_pips`, `max_rungs`). Locking those
   in §4 makes the reconstruction fully reproducible.

The reconstruction lives in a new module `programs/E022/level_detector.py`
(Phase 2 deliverable) — **or**, if PRE-0's promised
`programs/_shared/level_detector.py` (SPEC §7) is delivered first, E022
consumes that instead. Either way the parameters are locked in §4 and
the module is read-only from E022's perspective (no per-trade tuning).

**No look-ahead audit.** All levels are computed from bars strictly
before `entry_time` (§4 parameters). A mutation test in the Phase 2
harness (mirroring SPEC §5 `test_no_lookahead.py`) fails the run if
any level depends on a bar at or after `entry_time`.

---

## §4 Locked parameters (frozen at approval)

### §4.1 The 12-arm grid (2-D, no continuous tuning)

| snap_distance ↓ / snap_source → | daily_only | ladder_top | round_number | all |
|---|---|---|---|---|
| **5 pips** | A1 | A2 | A3 | A4 |
| **10 pips** | A5 | A6 | A7 | A8 |
| **15 pips** | A9 | A10 | A11 | A12 |

Twelve arms total. Each arm is a single `(snap_distance, snap_source)`
pair. **No continuous tuning of `snap_distance` or `snap_offset`;
no other arm is added post-freeze** (PROTOCOL_DISCIPLINE §5).

### §4.2 Pinned constants (all knobs)

| Knob | Value | Rationale |
|---|---|---|
| `snap_offset_pips` | `min(3, snap_distance/2)` — i.e. 2.5 / 3 / 3 pips for `snap_distance ∈ {5,10,15}` | Pinned function of `snap_distance`, not an arm. Half-distance is the symmetric "middle of the buffer" heuristic; the `min(3, …)` cap prevents snap_offset from growing without bound. Never larger than 3 pips so the pull never overshoots typical spread. |
| Pip factor | `1e-4` for EURUSD, GBPUSD, USDCAD | Standard 4-decimal FX convention (matches `target_ladder.PIP = 0.0001`). |
| `lookback` (level reconstruction) | 200 H4 bars | Mirrors `compute_target_ladder(..., lookback=200)`. |
| `trendline_lookahead` | 20 H4 bars | Mirrors `compute_target_ladder(..., trendline_lookahead=20)`. |
| `max_rungs` | 6 | Mirrors production. |
| `dedupe_pips` | 3.0 pips | Mirrors production. |
| Round-number step | 50 pips (`.00` and `.50` sub-figures) | Standard FX depth clustering [@osler2003currency; @sonnemans2006price]. |
| PDH/PDL/PDM window | preceding UTC D1 bar strictly before `entry_time` | Same D1 source as production `_daily_levels`. |
| PWH/PWL/PWM window | preceding UTC W1 bar strictly before `entry_time` | Same W1 source. |
| `is_between` (direction invariant) | strict inequality on both endpoints | Prevents zero-distance snap (see §3.2). |
| Symbols | EURUSD, GBPUSD, USDCAD | Three deployed cells. |
| Timeframe | H4 | Deployed cell. |
| Window | 2015-01-01 → 2025-12-01 | Matches PRE-0 SPEC §2. |
| Walk-forward folds | 5 (SPEC §3 table) | Inherited from PRE-0. |
| Fill decision on new TP | `new_tp` fills iff, on any bar between `entry_time` and the original `exit_time` (inclusive), `bar.high ≥ new_tp` (long) or `bar.low ≤ new_tp` (short), evaluated on M5 path bars if available else H4 (SPEC §1 `path_resolution`). The fill timestamp is the first such bar. | Deterministic single-authority fill rule; no re-simulation of stop/trail dynamics — the trade continues on its original path until the new TP is hit or the original exit fires, whichever comes first. |
| Bar ↔ hour | 1 H4 bar = 4 h; 6 bars/day | Consistent with E017 §7 A1. |
| Random seed | 42 | Repo convention. |
| Bootstrap resamples | 5,000 | Convention. |
| Pooling across symbols | fixed-effects, weight ∝ per-symbol trade count on the test slice of each fold | Standard weighted pooling; declared so a reader can reproduce. |

**No parameter above is tuned during Phase 2.** Phase 2 selects only
among the 12 discrete frozen arms.

---

## §5 Validation method (Phase 2 — not run in Phase 1)

### §5.1 Pipeline overview

For each of the three symbols and each of the 12 arms:

1. **Load** the PRE-0 paths ledger (`{symbol}_H4_paths.jsonl`).
2. **Reconstruct** `L(snap_source)` for every trade using bars
   `[entry_time − 200·H4, entry_time)` and the locked §4 detector
   parameters. Cache per-symbol.
3. **Compute** `new_tp = snap_tp(entry, tp, direction, L, snap_distance,
   snap_offset_pips)` per §3.1. Log `snap_fired ∈ {True, False}` per
   trade.
4. **Rescore** each trade under `new_tp` using the §4 fill decision
   rule. Emit `alt_r`, `alt_exit_time`, `alt_exit_reason`.
5. **Aggregate** per (fold, symbol, arm): `Sharpe(alt_r)`,
   `Sharpe(baseline_r)`, `ΔSharpe`, `Δ P(TP fills)`, `Δ mean R | win`,
   `Δ mean time-in-trade | win`, `snap_fire_rate`.
6. **Bootstrap** the paired ΔSharpe distribution (5,000 resamples of the
   per-trade Δ R sequence, seed 42) → 95 % CI.
7. **Pool** across the 3 symbols on each fold's test slice using the
   §4 fixed-effects weights → per-fold `ΔSharpe_pooled` per arm.
8. **Per-arm p-value.** Bootstrap p-value on the pooled per-fold
   `ΔSharpe` (Stouffer-combined across folds, or the equivalent single
   paired-bootstrap on the concatenated test-slice per-trade Δ R —
   both pre-declared; Phase 2 picks one and lists the other as
   sensitivity).
9. **BH-FDR at α = 0.10** across the 12-arm family of p-values
   [@benjamini1995controlling; @harvey2016cross].

### §5.2 Walk-forward discipline

Folds are the SPEC §3 5-fold split. **No arm hyperparameters are fit on
train slices** — the 12-arm grid is completely locked in §4 and no
knob varies within an arm. Train slices are therefore used only for
descriptive checks (`snap_fire_rate` on train ≈ `snap_fire_rate` on
test, sanity check). Scoring is on **test slices only**.

### §5.3 Ex-post case walkthrough (illustrative, non-inferential)

To make the direction invariant (§3.2) concrete and honest about the
scope of E022, Phase 2's REPORT will include the following worked
example on the motivating trade. **This is descriptive; n = 1; it does
not enter any FDR family.**

**Trade.** GBPUSD ticket **2969136564** (2026-07-16 short):
- `entry = 1.35060`, `tp = 1.34264`, `stop_pips = 53.1`, target 79.6 p.
- Historical MFE 79.1 p at the intra-trade peak; missed TP by 0.5 p.
- Nearest reconstructed **swing low** on the H4 lookback: `1.34111`
  (bar 111, ~15.3 p **below** TP).

**Arm walk-through: `snap_source = ladder_top, snap_distance = 15,
snap_offset = 3` (arm A10).**

- Swing low 1.34111 vs TP 1.34264: swing is at 1.34111, TP at 1.34264;
  short direction so `is_between(1.35060, 1.34111, 1.34264)`? Ordering:
  `1.34111 < 1.34264 < 1.35060`. The swing at 1.34111 is **below** TP,
  i.e. **beyond** TP on the short's directed axis — NOT between entry
  and TP. `is_between` returns `False`. **Snap does not fire.**
- Extension: with `snap_source = round_number`, the round-number set on
  the trade's price band is `{1.34500, 1.35000}`. Of these, only
  `1.34500` is between entry 1.35060 and TP 1.34264 (short axis:
  `1.34264 < 1.34500 < 1.35060` — yes). Distance to TP:
  `1.34500 − 1.34264 = 23.6 p > snap_distance = 15`. **Snap does not
  fire.**
- The consolidation shelf near 1.34300 that human eyes would draw is
  **not** in any locked `L(snap_source)` — the E022 level set is
  deliberately limited to the four sources in §3.3 to keep the study
  parsimonious.

**Result.** For this specific trade under every arm in the §4 grid,
`new_tp = tp` and the trade's rescored R is identical to its
historical R (still a scratch/loss). **E022 does not solve every
"close but no cigar" case** — only the ones where a sticky level from
the locked source set falls between entry and TP within
`snap_distance`. The E024 near-TP stall exit is a separate,
non-overlapping mechanism aimed at the same class of failures from the
*exit* side; joint stacking is E025's scope, not E022's.

This walkthrough is included so a reader can see, on the motivating
trade, that the rule's direction invariant behaves as pre-registered
and does not silently rescue this ticket by pulling TP outward.

### §5.4 Anti-lookahead audit (unit test, must pass)

The Phase 2 harness includes a mutation test: for every trade, mutate a
random bar at `entry_time` or later, recompute `L(snap_source)`, and
assert `L` is unchanged. If any level depends on a post-entry bar, the
run fails and E022 stops. Mirrors SPEC §5 `test_no_lookahead.py`.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4 (with
study-specific `parked_*` reasons per E017/E019 precedent):

- **`alive` → advance to Phase 3 (production wiring, separately gated)**
  iff, for **at least one** locked arm in §4, **all** hold:
  1. **Primary.** `ΔSharpe` pooled-across-symbols bootstrap-95 % CI
     lower bound **> 0**; **AND**
  2. **Cross-fold robustness.** `ΔSharpe` is positive on **≥ 4 of 5**
     walk-forward folds (pointwise, not just on pooling); **AND**
  3. **Family-wise correction.** The arm's per-arm p-value survives
     **BH-FDR at α = 0.10** across the 12-arm family; **AND**
  4. **Feasibility.** `snap_fire_rate` on the test slices is **≥ 5 %**
     for that arm (i.e. the rule actually moves TP on a non-trivial
     fraction of trades — see H3 below); **AND**
  5. **Sanity.** `Δ P(TP fills) > 0` for that arm (the mechanism works
     as designed: pulling TP inward raises fill probability).

- **`parked_daily_only_suffices` (H2)** — the winning arm on
  `snap_source = daily_only` is statistically indistinguishable from
  the winning arm on `snap_source = all` (paired ΔSharpe CI overlaps
  0). Prefer the simpler `daily_only`; do not ship `ladder_top` /
  `round_number` / `all` machinery.

- **`parked_snap_never_fires` (H3, SPECIAL — first-class outcome).**
  For every arm, `snap_fire_rate < 5 %` on the walk-forward test
  slices. The study is *uninformative* — the deployed cell already
  places TPs away from sticky levels for the four locked sources. This
  is a **legitimate acceptable outcome**; the shipped placement is
  vindicated and no snap machinery is added.

- **`parked_weak_effect`.** Point estimate positive but CI includes 0,
  or positive on only 3 folds, or fails BH-FDR. Do not ship; may
  motivate a redesigned family (new pre-registration required, not an
  amendment).

- **`dead` / STOP (keep unmodified placement, write `STOP_NOTICE.md`).**
  0 arms `alive` and the outcome is neither `parked_daily_only_suffices`
  nor `parked_snap_never_fires`. Phase 3 does **not** proceed.

**Stop rule (pre-declared).** If 0 arms are `alive` at the end of
Phase 2, STOP: keep the shipped mechanical TP placement and write
`STOP_NOTICE.md` under this directory. **Do not open a Phase 2b, do not
extend the grid, do not add a new `snap_source`, do not adjust
`snap_offset`.** Any future E022-family work requires a **new
pre-registration** (E022b or a fresh ID).

---

## §7 Amendments

_(Empty at pre-registration. Any change requires a dated subsection
here per `PROTOCOL_DISCIPLINE.md` §5 before the amended analysis runs.)_

---

## §8 Cross-references

- **Predecessor / baseline for the (EURUSD, H4) ledger:**
  [`../E013_safety_layer_contribution/`](../E013_safety_layer_contribution/)
  (`all_on` production-matching harness; the source of the R
  distribution the E017 ledger export mirrors).
- **Shared harness (PRE-0):**
  [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md).
  E022 is the only PRE-0 consumer that uses `target_ladder` reconstruction
  and does not require intra-trade lifetime replay (SPEC §7 table).
- **Sibling exit-side studies (disjoint arms, coordinated FDR upstream):**
  E020 (MFE ratchet), E021 (partial exit at 1R), E023 (post-BE structure
  trail), E024 (near-TP stall exit), E025 (joint stack).
- **Production references (read-only):**
  `multi-pair-trading-agent/agent/live/signal_loop.py`
  (`SignalLoop._route_signal` — placement site),
  `multi-pair-trading-agent/agent/journal/target_ladder.py`
  (`compute_target_ladder`, `TargetRung`, and the individual detector
  helpers `_daily_levels`, `_swing_rungs`, `_zone_edges`,
  `_trendline_rung`, `_fib_extensions`).
- **Motivating live ticket:** GBPUSD 2969136564, 2026-07-16 short
  (multi-pair-trading-agent live logs; descriptive only, n = 1).

**Existing bibliography (in `../../reviews/refs.bib`):**
`benjamini1995controlling` (BH-FDR), `harvey2016cross` (multiplicity),
`bailey2014deflated` + `bailey2014pseudo` (deflated statistics /
overfitting hygiene), `lopezdeprado2018` + `lopezdeprado2018tactical`
(financial ML pitfalls), `efron1993bootstrap` (paired bootstrap CIs),
`nosek2018preregistration` (pre-registration ethos), `chan2009quantitative`
(execution-side interventions).

**References to ADD to `reviews/refs.bib` before the E022 REPORT** (not
added in this pre-registration to avoid a concurrent-write race on the
shared bib — flagged for the coordinator):

- `osler2003currency` — Carol Osler, "Currency Orders and Exchange Rate
  Dynamics: An Explanation for the Predictive Success of Technical
  Analysis," *Journal of Finance* 58 (5), 2003. The canonical
  reference for FX order-book clustering at round numbers and
  support/resistance levels — direct grounding for `round_number` and
  `daily_only` as level sources.
- `sonnemans2006price` — Joep Sonnemans, "Price Clustering and
  Natural Resistance Points in the Dutch Stock Market," *European
  Economic Review* 50 (8), 2006. Cross-asset evidence for price
  clustering at round numbers as a fill-probability effect.
- `chengwilym2007round` — Fang Chen & Owain ap Gwilym, "The Impact of
  Fair Value Accounting on the Round-Number Effect in FX Markets,"
  *(replace with the specific 2007 paper the coordinator prefers)* —
  additional round-number-effect corroboration for the mixed-symbol
  panel. **Coordinator should verify the exact citation before adding.**

If the coordinator prefers to ship only one microstructure citation,
`osler2003currency` is the load-bearing one; the other two are
corroborating.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| §5 rescore | `programs/_shared/counterfactual_replay/data/EURUSD_H4_paths.jsonl` (PRE-0 output; regenerated read-only from E013 `all_on` harness, 737 trades, hit-rate 0.5577) | new per-trade counterfactual rescoring | E013 (summary), E017 (bootstrap R-distribution). Neither prior use was per-trade counterfactual rescoring; no double-dipping of a sealed slice. |
| §5 rescore | `programs/_shared/counterfactual_replay/data/GBPUSD_H4_paths.jsonl` (PRE-0 output; generated fresh) | new per-trade counterfactual rescoring | none |
| §5 rescore | `programs/_shared/counterfactual_replay/data/USDCAD_H4_paths.jsonl` (PRE-0 output; generated fresh) | new per-trade counterfactual rescoring | none |
| §5.3 case walkthrough | GBPUSD live ticket 2969136564 (2026-07-16 short) | one-off descriptive case, n = 1 | none (operational record) |

**FDR family opened:** one, 12 arms, one primary metric (`ΔSharpe`),
BH at α = 0.10, pooled across (EURUSD, GBPUSD, USDCAD) on H4.
Walk-forward folds inherited from SPEC §3 (mirrors E004).

No sealed `(pair, TF, split)` bar slice is consumed for a statistical
claim — E022 consumes the PRE-0 paths ledger (which is itself a
regeneration of the deployed cell's own trades, not a new bar-slice
family). A `planned` row is added to `DATA_LEDGER.md` when Phase 2
starts, updated to `screen` when scoring completes.

---

**Pre-registration commit:** _(hash after push)_
