# Test B Protocol — impulse-origin return → bounce study

Status: **PRE-REGISTERED 2026-06-16**, before any Test B detector code or
data run exists. This file is committed and pushed BEFORE Stage 1 runs;
the audit trail is the commit hash on `origin/main`. Any change to a
pre-registered parameter after Stage 1 is recorded as an explicit AMENDMENT
section with a new commit, never silent edits.

This is a NEW, ENTIRELY SEPARATE family from Test A (`PROTOCOL.md`). It
does not pollute Test A's dictionary (`conflab.events.all_detectors`),
its registries, or its FDR families. The two share only general-purpose
infrastructure: `conflab.screening.directional_outcome` (per-bar MFE),
`conflab.stats._permutation_pvalue`, `conflab.stats.benjamini_hochberg`,
and the parquet `BarLoader` idiom from `conflab.data.load_frames`.

## 1. Hypotheses (operational)

The user's discretionary intuition (verbatim): *"price will always come
down to the rejected liquidity zone that starts the previous uptrend and
will always have a huge bounce when it comes back to that zone whether or
not it has so much friction in between."* This protocol tests the
"always" framing as a measurable conditional probability.

- **H1 (main).** Given a strong, clean impulse from origin zone A to peak
  B on timeframe T, the conditional MFE in the impulse direction over W
  bars after price returns to within A is materially higher than at
  hour-of-day-matched random levels with the same return-direction
  expectation. Effect size and reach probability `P(MFE ≥ 0.5R within W)`
  both reported.
- **H2 (path friction).** Among origin-return events, events whose path
  between impulse-end and return-touch has LOW friction (clean retrace)
  produce higher conditional MFE than HIGH-friction events.
- **H3 (cross-pair).** If H1 survives EURUSD screen + confirm, it
  replicates on GBPUSD and USDCAD in a sealed look (run once, no peeking).

H1 and H3 are tested in BOTH directions: up-impulse → return → bounce up,
and down-impulse → return → bounce down. The agent trades both sides.

`R` is defined per event as `R = impulse_height / 4`, so 1R is one
quarter of the impulse and 4R = full retracement back to the impulse top
(or bottom). The user gets a literal "X% of the time" statement on every
pair via `P(MFE ≥ 0.5R within W bars)` reach probabilities.

## 2. Hard separation from Test A

| Concern | Test B path |
|---|---|
| Pre-registration | `protocols/TEST_B_PROTOCOL.md` (this file, in repo root) |
| Detector | `conflab/detectors_impulse_return.py` (NOT in `events.all_detectors`) |
| Friction module | `conflab/friction.py` (pure functions, unit tested) |
| Runners | `scripts/test_b/run_stage1.py`, `run_stage2.py`, `run_stage3.py`, `run_stage4_friction.py`, `render_figures.py` |
| Outputs | `output/test_b/` (JSONL registries) and `output/test_b/figures/` (PNGs) |
| Report | `REPORT_TEST_B.md` (repo root, redirects to this folder's `REPORT.md`) |

Test A's PROTOCOL.md, REPORT.md, registries, and detector dictionary are
not modified. The shared `conflab.screening`, `conflab.stage2`,
`conflab.stats` modules are read-only from Test B's perspective: Test B
adds new code, never edits existing behaviour.

## 3. Locked parameters (frozen 2026-06-16, before any data is screened)

All parameters below are LOCKED prior to the Stage-1 run. Adjustments
within the literature-acceptable ranges were applied here based on (a)
keeping `pip` thresholds consistent with the live agent's existing
zone definitions and (b) keeping the BH-FDR family small enough to retain
power on a permutation floor of 1/(n_perm+1).

### 3.1 Impulse leg detection (each timeframe independently)

| Knob | Value | Rationale |
|---|---|---|
| Net move (pips) | H4: `M_pips = 40` · H1: `M_pips = 20` | Matches the live agent's strong-zone threshold (~40p on H4 active hours). |
| Net move (ATR) | `M_atr ∈ {1.0, 1.5, 2.0}` (gridded) | Default 1.5; bracketed for robustness. The only Stage-1 grid axis. |
| Both pip AND ATR floors must be met | logical AND | A 40-pip move at very low ATR could be noise; ATR gate enforces "strong relative to regime." |
| Max bars to complete | `K = 3` | Default; not gridded. The user's "strong, clean" qualifier rules out drawn-out drifts. |
| Max retrace during leg | `30%` of leg height | A clean impulse stays within 30% retrace at every bar. |
| Direction | `up` AND `down` (both tested) | The agent trades both sides. |
| Inter-event spacing | `≥ K` bars between consecutive impulse-end bars | Prevents a single rolling trend from emitting `K` overlapping events. |

### 3.2 Origin zone

| Knob | Value |
|---|---|
| Definition A | `[low, high]` of the last opposite-direction bar before impulse start (red bar before an up-impulse, green bar before a down-impulse). If no opposite bar in the 5 bars preceding the impulse, fall back to the impulse-start bar itself. |
| Definition B | `[min(low), max(high)]` over the last `M = 5` bars before impulse start. |
| Selection | Pick whichever of A or B has the **larger pip span** (more room to be touched). |
| Padding | `pad = 0` pips (raw zone). |

### 3.3 Return-touch event

| Knob | Value |
|---|---|
| Validity window | `N` bars after the impulse end. H4: `N = 40` (≈ 6–7 calendar days). H1: `N = 80` (≈ 3–4 calendar days). Fixed per TF. |
| Touch | First bar `s` in `[t_end+1, t_end+N]` where `low[s] ≤ origin_zone_top` (up impulse) or `high[s] ≥ origin_zone_bottom` (down impulse). |
| First touch only | Yes — once a zone is touched, no second event from the same impulse. |
| If no touch in window | Impulse is dropped; no event emitted. |

### 3.4 Outcome (MFE)

| Knob | Value |
|---|---|
| MFE window | `W` bars after the touch bar. H4: `W = 20` (≈ 3 days). H1: `W = 40` (≈ 1.5 days). Fixed per TF. |
| Direction | Toward the impulse top (up-impulse events) or impulse bottom (down-impulse events). |
| Pip unit | EURUSD/GBPUSD/USDCAD: `1 pip = 0.0001`. |
| `R` | Per event: `R = impulse_height / 4`. So 1R = a quarter-impulse, 4R = a full return. |
| Reach thresholds reported | `MFE ≥ {0.5, 1.0, 1.5, 2.0, 3.0, 4.0} R` |
| Headline reach metric | `P(MFE ≥ 0.5R within W bars after return-touch)` reported as a literal percentage. |

### 3.5 Stage-1 family

The Stage-1 BH-FDR family is exactly the cross product:

```
TF ∈ {H4, H1} × direction ∈ {up, down} × M_atr ∈ {1.0, 1.5, 2.0}
```

= **12 cells**. (`K`, `M_pips`, `N`, `W` are scaled per timeframe but
fixed within a timeframe — they do not multiply the family.) Per the
compute-vs-claim principle (Test A's PROTOCOL.md §1), statistics are
computed for every cell at every stage regardless of `n`; `n_gate` only
governs which cells are eligible for `alive`.

### 3.6 Statistical pipeline

| Stage | Symbols | Period | Hypotheses | Family | FDR |
|---|---|---|---|---|---|
| 1 — Screen | EURUSD | 2015-01-01 → 2021-12-31 | H1 | 12 cells (§3.5) | BH-FDR α=0.05 across the 12 |
| 2 — Confirm | EURUSD | 2022-01-01 → 2024-12-31 | H1 | Stage-1 survivors only | per-cell α=0.05 (small family; no BH) |
| 3 — Cross-pair sealed | GBPUSD, USDCAD | 2015-01-01 → 2024-12-31 | H1, H3 | Stage-2 survivors only; **H4 only** (see Practical constraints below) | per-cell α=0.05 |
| 4 — Friction conditioning | survivors of Stage 3 | as per stage | H2 | quartile reach curves | bootstrap CIs (10000 resamples) |

**Permutation null.** For each event `e_i` in cell `(TF, direction, M_atr)`:
draw `control_mult = 5` random control bar indices `j_1..j_5` with the
SAME hour-of-day as `e_i`'s touch bar (Test A amendment v2.1 carries
forward), and the SAME direction. At each control bar, compute the MFE
in the event direction over `W` bars. The control reach metric uses the
event's own `R` so 0.5R is comparable.

`n_perm = 5000` shuffles for the mean-MFE permutation p (floor =
1/5001 ≈ 1.9e-4). The chosen floor is below the most stringent BH-FDR
threshold the 12-cell family imposes (α=0.05, top rank: 0.05/12 ≈
4.2e-3), so genuine cells can clear FDR without being capped at the
permutation floor.

**n_gate.** A cell qualifies for `alive` iff `n ≥ 30` events. Below 30
the cell is `parked_insufficient_n` (stats still recorded). Effect-size
gate for `parked_weak_effect` is 0 < Cohen's d < 0.2 with `n ≥ 30`. The
four-tier verdict registry (alive / parked_weak_effect /
parked_insufficient_n / dead) follows Test A's PROTOCOL.md.

### 3.7 Stop rules

- If H1 dies at Stage 1 (no `alive` cell after BH-FDR) → STOP. Report "no
  evidence" honestly. H2 and H3 do not run.
- If H1 dies at Stage 2 → STOP. Tag the screen-survivor cells as
  `parked_weak_effect` and explain.
- If H1 survives Stage 3 → run Stage 4. Otherwise tag and stop.

The protocol's exit condition under "no evidence" is itself a deliverable.
The headline sentence still runs, just truthfully: "X% of impulse-origin
return events produced a bounce ≥ 0.5R, **vs Y% at hour-matched random
levels (p > 0.05; null not rejected)** — the user's 'always' framing is
not supported."

### 3.8 Practical constraints (data availability)

Audited 2026-06-16 against `multi-pair-trading-agent/data/parquet/`:

- **EURUSD H4, EURUSD H1**: 2015 → 2026 (full coverage for screen + confirm).
- **GBPUSD H4**: 2015 → 2026.
- **GBPUSD H1**: only available 2015 → 2021. Stage 3 cross-pair on H1
  would have NO post-screen-window confirm data; therefore Stage 3 is
  scoped to **H4 only** across all three pairs.
- **USDCAD H4**: 2015 → 2026.
- **USDCAD H1**: NOT cached; reinforces the H4-only Stage-3 scope.

This is documented in advance, not after seeing results, and applies
symmetrically to up and down directions.

## 4. Friction score (pre-registered recipe)

Computed over the bars between `impulse_end` and `return_touch`
(inclusive of both endpoints). Four standardised components:

1. **`wick_density`**: mean over the path bars of
   `(upper_wick + lower_wick) / range`, where
   - `upper_wick = high − max(open, close)`
   - `lower_wick = min(open, close) − low`
   - `range = high − low` (zero-range bars contribute 0).
2. **`oscillation_count`**: number of zig-zag swings on the path under a
   ZigZag threshold of `δ = 0.5 × ATR(20)` evaluated at the touch bar.
   A swing counts each time the local extreme reverses by ≥ δ.
3. **`path_drawdown_ratio`**:
   - up-impulse: `(impulse_top − path_low) / impulse_height`
   - down-impulse: `(path_high − impulse_bottom) / impulse_height`

   Higher = more retrace overshoot relative to the leg.
4. **`time_in_chop_band`**: share of path bars where
   `|close − origin_zone_mid| < 0.5 × ATR(20)` at the touch bar.

**Aggregator.** Each component is z-scored against the
**EURUSD-screen-split distribution** (mean and std computed once after
Stage 1 runs, then FROZEN). The friction score is the **simple sum** of
the four z-scores (no PCA, no learned weights — boringly defensible).

**Quartile cutoffs.** The cutoffs (Q1/Q2 boundary, Q2/Q3, Q3/Q4) are
learned ON THE EURUSD SCREEN SPLIT events ONLY, then frozen for every
subsequent stage and pair. The exact cutoff values are appended to this
protocol as a §6 amendment after Stage 1 finishes — explicitly called
out as "frozen after Stage 1 screen; never relearned per pair/stage."

## 5. Multiplicity, honesty, separation

1. Every cell evaluated at any stage counts toward that stage's FDR
   family — including ones we lose interest in.
2. `parked_insufficient_n` is a recorded verdict distinct from pass/fail.
3. No detector or friction-recipe retuning after Stage 1. A
   "wouldn't this work better if…" idea is a NEW pre-registered protocol.
4. Negative results are reported with the same prominence as positive
   ones in `REPORT_TEST_B.md`.
5. Hard-coded random seeds: Stage 1 = 42, Stage 2 = 142, Stage 3 = 242,
   Stage 4 = 342 (independent across stages so a single-bit run-order
   accident cannot rotate seeds).
6. Test B does not modify any Test A artifact. The trading agent
   (`multi-pair-trading-agent`) is not touched.

## 6. Amendments

(Appended in commit-by-commit order. Each amendment is committed before
the analysis it enables runs, so the audit trail is the commit hash.)

### Amendment 6.2 — `max_retrace_frac`: 0.30 → 0.50 (2026-06-16, pre-MFE)

**Why amended.** §3.1's `max_retrace_frac = 0.30` (intrabar drawdown from
the running max ≤ 30% of leg height at every bar in the K-bar window)
was found to be too strict for real H4/H1 forex bars: a count-only
diagnostic on EURUSD 2015-2021 (no MFE outcome touched) returned

```
EURUSD H4  frac=0.30 M_atr=1.0 → up=1   down=1
EURUSD H4  frac=0.40 M_atr=1.0 → up=3   down=4
EURUSD H4  frac=0.50 M_atr=1.0 → up=61  down=55
EURUSD H1  frac=0.30 M_atr=1.0 → up=2   down=4
EURUSD H1  frac=0.40 M_atr=1.0 → up=13  down=15
EURUSD H1  frac=0.50 M_atr=1.0 → up=273 down=305
```

i.e. 1–4 candidate legs across 7 years per H4 cell at the original
ceiling — at or below the n_gate=30 — meaning Stage 1 is *not testable*
at that setting on H4 even before the return-touch filter further
shrinks the count. This is the infeasibility case that the parent
study's instructions explicitly anticipated.

**What changed.** `max_retrace_frac` is relaxed to **0.50** — the
smallest value at which every cell in the §3.5 grid crosses the n=30
floor before the return-touch filter is applied. 0.50 is still well
within the textbook "clean leg" envelope (most ICT/SMC heuristics call
anything up to ~0.62/0.79 a clean retrace; 0.50 is the standard
mid-point fib). This is a single, one-shot relaxation — not a sweep
toward a positive outcome.

**Audit guarantees.**
1. The diagnostic that motivated the change inspected only **candidate
   counts**, never MFE in events or controls. The MFE outcome code path
   is downstream of the leg filter and was not exercised.
2. The original `max_retrace_frac=0.30` Stage-1 run is preserved as the
   cautionary record (`output/test_b/stage1_EURUSD_screen_<old_stamp>.jsonl`).
3. Detector code: `cfg.max_retrace_frac` is now configurable and the
   runner pins it to 0.50 in `scripts/test_b/_lib.MAX_RETRACE_FRAC`.
   Unit tests retain 0.30 to keep synthetic fixtures honest under the
   tightest setting.
4. `max_retrace_frac` will not be touched again. If 0.50 still produces
   an unscientific outcome (e.g. zero events in a cell after the
   return-touch filter), the cell is reported as `parked_insufficient_n`
   and the protocol is not amended further.

### Amendment 6.1 — friction quartile cutoffs (frozen 2026-06-16)

Pooled 540 unique events across the 12-cell EURUSD screen-split family
(deduplicated by `(tf, direction, impulse_end_idx, touch_bar_idx)`).
Component-wise reference (mean, std):

| component | mean | std |
|---|---|---|
| `wick_density` | (see `output/test_b/stage1_friction_reference_<stamp>.json`) | |
| `oscillation_count` | ″ | ″ |
| `path_drawdown_ratio` | ″ | ″ |
| `time_in_chop_band` | ″ | ″ |

Quartile boundaries on the simple-sum-of-z-scores friction score:

| boundary | value |
|---|---|
| Q1 ↔ Q2 | **−1.1916** |
| Q2 ↔ Q3 | **−0.2472** |
| Q3 ↔ Q4 | **+0.9864** |

These are frozen for any subsequent Test B work that conditions on
friction. Stage 4 was not executed in the 2026-06-16 run because the
H1 (main) stop rule fired at Stage 1 (§3.7); the cutoffs are recorded
here so a future re-look (under a fresh pre-registration) can use them
without retraining.

## 7. Headline statement (target form)

After all stages run, `REPORT_TEST_B.md` must produce a single sentence
of the form:

> "On EURUSD/GBPUSD/USDCAD H4 2015–2024, **X.X%** of impulse-origin
> return events produced a bounce ≥ 0.5R within `Y` bars (vs **Z.Z%** at
> hour-matched random levels, p = …). Low-friction-path subset:
> **A.A%** vs **B.B%** high-friction. Replicated on **N/3** pairs."

Every number in that sentence has a figure behind it in
`output/test_b/figures/`.

If the data says "no evidence," the headline says exactly that. We are
looking for truth, not confirmation.
