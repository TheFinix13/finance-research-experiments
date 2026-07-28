# E027 — Valid-liquidity sweep reversal (BOS-qualified swing levels)

**Status:** PRE-REGISTERED 2026-07-28 · **Date frozen:** 2026-07-28 ·
**Branch:** `main` (user-declared 2026-07-28 session)

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Relationship to E001 (why this is a new experiment, not a re-look)

E001 tested "liquidity sweep reversal" as one operational definition —
wick-through-and-reject of PDH/PDL/PWH/PWL, fractal swings, and
equal-extreme clusters, with **no qualification of which swept levels
carry meaningful resting liquidity** — and it was eliminated under
BH-FDR at 5 % (even after a relaxed "fair shot" wave). Per E001
REPORT §6: *"A 'dead' verdict closes this definition, not the
underlying folk concept."*

E027 tests a **sharper definition** the E001 detector never
implemented: a swept swing low is only *valid liquidity* if the leg
that came out of it **broke the swing high it came from** (break of
structure). The hypothesis is that E001's sweep universe mixed
BOS-qualified sweeps (informative stop pools) with consolidation noise
(nothing meaningful beneath), diluting any signal to zero. This is a
**conditional split within the sweep universe**, not a re-run of the
E001 marginal test.

Source of the hypothesis: external discretionary-trading material
reviewed 2026-07-28 (user-supplied; "the low has to break the high it
came from"). Treated as folk prior with zero evidential weight.

## §0b Reuse declaration (no re-derived code)

| Purpose | Module | Symbol |
|---|---|---|
| Swing points (confirmed fractals) | `conflab/patterns.py` | `swing_points` (lookback confirmation lag) |
| Directional MFE outcome (ATR units) | `conflab/screening.py` | `directional_outcome` |
| ATR(14) Wilder | `conflab/indicators.py` | `atr` |
| Permutation p-value | `conflab/stats.py` | `_permutation_pvalue` (label-shuffle variant in `programs/E027/`, same +1 smoothing) |
| BH-FDR | `conflab/stats.py` | `benjamini_hochberg` |
| Parquet bar loader | `conflab/data.py` | `load_frames` |

New experiment-scoped code lives in `programs/E027/` (detector +
runner + tests). The sweep/validity detector is new by necessity (no
committed detector implements the validity split) and is frozen at the
pre-registration commit.

---

## §1 Hypothesis (operational)

**Event (sellside sweep, direction +1).** On one TF frame:

1. Confirmed swing low `L` at bar `iL`, price `pL`
   (`swing_points(df, lookback=5)`; usable from `iL+5`).
2. **Originating high** `H_o` = the most recent confirmed swing high
   with index `< iL`. If none exists, no event.
3. Scanning forward from `iL+5` for at most `max_scan=200` bars:
   a bar that **closes below `pL`** ends the level (no event);
   the first bar `t` with `low[t] < pL` **and** `close[t] > pL` is the
   **sweep event** at `t`.
4. **Validity label (known at `t`):** `valid` iff any bar `u`,
   `iL < u ≤ t`, **closed above** `H_o.price` (close-based break,
   matching the house BOS convention in
   `conflab/detectors_structure.py::detect_bos_choch`); else `invalid`.

**Mirror (buyside sweep, direction −1):** swing high `H` at `iH`;
originating low `L_o` = most recent confirmed swing low before `iH`;
level ends on a close above `pH`; sweep = `high[t] > pH` and
`close[t] < pH`; `valid` iff some bar closed below `L_o.price` before
the sweep.

One event per swing level (first sweep only). Events are causal: all
inputs are from bars `≤ t`.

**Outcome metric.** Directional MFE within the TF horizon (H1: 20
bars, H4: 20 bars), ATR(14)-normalised at the event bar —
`conflab/screening.py::directional_outcome`, identical to E006/E010.

**H0.** Within each cell, mean MFE(valid) − mean MFE(invalid) ≤ 0:
the BOS qualification does not separate post-sweep reaction quality.

**H1.** Mean MFE(valid) − mean MFE(invalid) ≥ **+0.10 ATR** with
permutation p below the cell's BH-FDR threshold (α = 0.05 across the
§2 family). The permutation shuffles **validity labels within
hour-of-day strata** (hour-matched by construction; PROTOCOL_DISCIPLINE
§3), `n_perm = 5000`.

**Secondary (reported, NOT gating, no verdict):**

- each validity class vs 5× hour-matched direction-matched
  random-time controls (E006 Stage-1 recipe) — locates the classes
  against baseline;
- valid share of all sweeps per cell (descriptive; answers "how much
  of the E001 sweep universe was noise under this rule").

---

## §2 Cell family LOCKED (Stage 1: 4 cells)

| # | Pair | TF | Side | Direction |
|---:|---|---|---|---:|
| 1 | EURUSD | H1 | sellside sweep (swing lows) | +1 |
| 2 | EURUSD | H1 | buyside sweep (swing highs) | −1 |
| 3 | EURUSD | H4 | sellside sweep | +1 |
| 4 | EURUSD | H4 | buyside sweep | −1 |

**Family size 4.** M15 is excluded (E010 holds the M15 reservation
lane and intraday cost realism is E028's problem); D1 is excluded
(too few events for the n-gate on 7 years).

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Swing lookback | 5 bars | House default (`swing_points`, `detect_swings`) |
| Break convention | close beyond origin level | House BOS convention (`detect_bos_choch`) |
| Sweep convention | wick through + close back inside | House convention (`detectors_liquidity.py`) |
| Level expiry | close through level, or `max_scan=200` bars | House pool-ending rule |
| MFE horizon | 20 bars (H1 and H4) | `Stage1Config.horizons` house values |
| ATR window | 14 (Wilder) | House default |
| Warmup | 60 bars | House default |
| `n_perm` | 5,000 | Floor 1/5001 ≈ 2.0×10⁻⁴ < BH top-rank 0.0125 (m=4) |
| n-gate | ≥100 events **per validity class** per cell | E006/E010 gate, applied to both classes so the difference is powered |
| Effect floor | +0.10 ATR on the valid−invalid difference | House floor (E010 convention) |
| FDR | BH α = 0.05 across 4 cells | Standard |
| Controls (secondary) | 5× draws, hour+direction matched | E006 v2.1 recipe |
| Seeds | 27 (Stage 1) · 127 (Stage 2) · 227 (Stage 3) | Distinct from E010's 42/142/242 |

**Cell verdict (locked).** `alive` iff n_valid ≥ 100 AND
n_invalid ≥ 100 AND difference ≥ +0.10 ATR AND p survives BH α=0.05
across the family. `parked_weak_effect` iff both n ≥ 100 and either
the floor is missed (positive but < +0.10) or FDR failed at raw
p < 0.05. `parked_insufficient_n` iff either class < 100 (stats still
computed — compute-vs-claim). Otherwise `dead`.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | α |
|---|---|---|---|---|---|
| 1 — Screen | EURUSD | 2015-01-01 → 2021-12-31 | 4 cells (§2) | label-shuffle permutation (hour-stratified) | BH α=0.05 across 4 |
| 2 — Confirm | EURUSD | 2022-01-01 → 2024-12-31 | Stage-1 survivors | same, frozen params | per-cell α=0.05 |
| 3 — Cross-pair | GBPUSD H1+H4, USDCAD H4 | 2015-01-01 → 2021-12-31 | Stage-2 survivors (same TF/side) | same, frozen params | per-cell α=0.05 |

**No sealed stage in this pre-registration.** EURUSD H1/M15
2025→2026-06-09 is reserved by E010; EURUSD H4 2025→2026-06-09 was
consumed sealed by E005. There is no pristine sealed slice at these
TFs today. A sealed pass (e.g. 2026-06-10 → 2026-12-31, once enough
bars accrue) requires its own pre-registered amendment; the maximum
claim E027 can produce is **cross-pair replicated**, and any
production candidacy still goes through the agent's own validation
pipeline (grid → holdout → walk-forward → cross-pair → sealed).

**Cross-pair note (Stage 3).** USDCAD H1/M15 are not cached (E007
§3.8; E010 §0); USDCAD participates at H4 only. GBPUSD H1 cache ends
2021-12-31 — inside the Stage-3 window by construction.

---

## §5 Controls and confounds

- The **primary test is a within-sweep-universe label shuffle**, so
  hour-of-day and session-volatility confounds are handled by
  stratifying shuffles within hour-of-day (each permutation reassigns
  validity labels only among events sharing the event bar's
  hour-of-day; strata with a single event keep their label).
- A validity-vs-hour composition check is reported: the distribution
  of event hours per class (valid sweeps could cluster in high-vol
  sessions; the stratified shuffle makes this non-fatal, the table
  makes it visible).
- Secondary baseline uses the binding hour-matched random-time control
  recipe unchanged (E006 v2.1).

---

## §6 Stop rules (pre-declared)

Stops emit `stage{N}_E027_stop.json` under `output/E027_valid_liquidity_sweep/`.

- **Stage 1.** If **0 of 4** cells are `alive` → **STOP.** The
  validity refinement does not separate reaction quality on EURUSD;
  the folk rule is dead in this operationalisation. No Stage 2/3. Any
  M001 striker or v1 candidate premised on "valid liquidity" is
  blocked by this registry entry until a new pre-registration.
- **Stage 2.** If 0 survivors confirm → **STOP**; tag survivors
  `parked_weak_effect` with confirm-window stats.
- **Stage 3.** If 0 replicate on any cross-pair cell → finding is
  **EURUSD-local**; do not promote.

Stopping is a valid outcome and is reported with the same prominence
as a survivor.

---

## §7 Amendments

_(Append-only; each amendment lands as its own commit before the
analysis it enables runs.)_

**A1 — 2026-07-28 (infrastructure, pre-Stage-1, non-claiming).** Bars
are loaded by direct read-only `pd.read_parquet` of the canonical
cache instead of `conflab.data.load_frames`: `BarLoader`'s head-gap
backfill hits the Dukascopy network path (Phase AE incident
2026-07-24, reproduced 2026-07-28 during the Stage-0 coverage check
and killed before any cache write; mtimes verified untouched). No
statistic was scored before this amendment. Window slicing and column
schema are identical.

Pre-declared non-amendment: the tighter "immediate-leg" validity
variant (break must occur before the next confirmed same-side swing
forms) is **out of scope**; testing it later requires a new ID, not an
amendment to E027.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses (documented per overuse rule) |
|---|---|---|---|---|---|
| 1 | EURUSD | H1 + H4 | 2015-01-01 → 2021-12-31 | screen | H1: E001, E006, E007, E010(reserved) — E027 is the 5th; H4: E001, E002, E003, E004, E006, E007 — **overuse warning acknowledged**; the hypothesis is a conditional split within a new event universe (orthogonal outcome definition), and H1 carries the primary power |
| 2 | EURUSD | H1 + H4 | 2022-01-01 → 2024-12-31 | confirm | H1: E006, E007, E010(reserved); H4: E003, E004, E006, E007 |
| 3 | GBPUSD | H1 + H4 | 2015-01-01 → 2021-12-31 | cross-pair | H1: E001, E006, E010(reserved); H4: E001, E004, E005 (frozen-parameter replication only; no selection on this slice) |
| 3 | USDCAD | H4 | 2015-01-01 → 2021-12-31 | cross-pair | E001, E004, E005 (frozen-parameter replication only) |

E010's sealed reservation (EURUSD H1+M15 2025-01-01 → 2026-06-09) is
**untouched** by E027.

---

## §9 Output artefacts (locked naming)

| Artefact | Path |
|---|---|
| Stage-1 registry | `output/E027_valid_liquidity_sweep/stage1_EURUSD_screen_<stamp>.jsonl` |
| Stage-2 registry | `output/E027_valid_liquidity_sweep/stage2_EURUSD_confirm_<stamp>.jsonl` |
| Stage-3 registry | `output/E027_valid_liquidity_sweep/stage3_crosspair_<stamp>.jsonl` |
| Stop files | `output/E027_valid_liquidity_sweep/stage{N}_E027_stop.json` |
| Report | `experiments/E027_valid_liquidity_sweep/REPORT.md` |
| Manifest | `experiments/E027_valid_liquidity_sweep/MANIFEST.md` |

Runner: `programs/E027/run_e027_validation.py` · Detector:
`programs/E027/sweep_validity.py` · Tests: `programs/E027/tests/`.

---

**Pre-registration commit:** _(this file's commit hash on `main`;
recorded in `EXPERIMENTS.md` E027 row and in `REPORT.md` when results
land)_
