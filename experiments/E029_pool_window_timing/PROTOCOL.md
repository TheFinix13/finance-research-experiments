# E029 — Pool-window timing (lift-only successor to E010)

**Status:** PRE-REGISTERED 2026-07-28 · **Date frozen:** 2026-07-28 ·
**Branch:** `main` (user-declared 2026-07-28 session)

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Provenance and taint declaration (read this first)

E010 (stopped at Stage 2, 2026-07-28) decomposed its claim into a
**selection term** (do pool windows catch above-average setups?) and a
**displacement-null lift** (inside a window, does real setup timing
beat displaced timing?). The selection term died out-of-sample; the
**lift survived everywhere it was measured**:

| Window (EURUSD) | Lift range (7 Stage-1-alive cells) | p |
|---|---|---|
| 2015–2021 screen | +0.12 … +0.33 ATR | ≤ 0.0004 |
| 2022–2024 confirm | +0.11 … +0.28 ATR | ≤ 0.0036 |

E029 pre-registers the lift as a **standalone claim**. Because both
EURUSD windows above were *observed* under E010, they carry **zero
confirmation power** here — they are motivating priors, cited, never
re-scored, never claimed. E029's evidence comes exclusively from data
the lift statistic has never been computed on:

1. **GBPUSD 2015–2021** (E010's Stage 3 that never ran), and
2. **EURUSD 2025-01-01 → 2026-05-27 sealed** (released to pristine by
   E010's stop; re-reserved here — see §8 shared-reservation note).

## §0b Reuse declaration

Identical machinery to E010 at commit `a159ec1` — detectors
(`conflab/detectors_liquidity.py` `equal_highs_pool`; M15 setup
detectors per E010 §0), `conflab/stage2.py::screen_pair` (displacement
null, hour-restricted re-draws), `_mfe_table`, BH-FDR, direct
read-only parquet loads (E010 §7 A1). Runner:
`programs/E029/run_e029_validation.py` (thin stage wrapper importing
the E010 runner's frozen helpers; **no selection-term / marginal pass
— the marginal is not part of this claim**).

---

## §1 Hypothesis (operational)

**H0.** Conditional on a +1-direction M15 setup event (§2 family)
firing inside an active H1 `equal_highs_pool` window, the joint
directional MFE does not exceed the within-window hour-matched
displaced-setup baseline (lift ≤ 0).

**H1.** Lift = `joint_mfe − displaced_mfe` (computed by `screen_pair`,
`n_perm = 5000`) is **≥ +0.10 ATR** with permutation p below the
stage's FDR/α threshold.

Outcome metric, window definitions, horizons, warmup, ATR: identical
to E010 §1/§3 (frozen).

**What this claim is and is not.** It is a *timing-primitive*
validation at screen grade (MFE-based, no cost model): pool windows
as a **when-filter**, not a **which-filter** (E010 killed the
which-claim). It is NOT a tradable-expectancy claim; any production
use (e.g. gating an existing entry by pool-window activity) requires
its own study plus the agent validation chain.

---

## §2 Cell family LOCKED (10 cells)

The **complete** E010 §2 family — all 10 M15 setup types — not the 7
Stage-1 survivors and not the cells with the best observed lifts.
Locking the full set prevents selection on observed EURUSD results
from leaking into the GBPUSD test: `bullish_fvg_touch`,
`channel_bottom_touch`, `fib_382_tag`, `fib_50_tag`, `fib_618_tag`,
`fib_ext_1272_tag`, `ote_tag`, `trendline_break_retest_bullish`,
`trendline_liquidity_sweep_low`, `trendline_support_touch`.

---

## §3 Locked parameters

All E010 §3 values carry over frozen (context H1 `equal_highs_pool`
detector defaults; context window 20 H1 bars; setup horizon 16 M15
bars; warmup 60; ATR 14 Wilder; `n_perm` 5,000; `n_gate` 100 joint
events; hour-restricted displacement re-draws), except:

| Knob | Value | Rationale |
|---|---|---|
| Verdict metric | **lift only** ≥ +0.10 ATR | The E010 decomposition finding; floor below the weakest observed OOS lift (+0.11) |
| Selection term / marginal | **not computed** | Not part of the claim; computing it invites peeking |
| Seeds | 29 (Stage 1) · 129 (Stage 2) | Fresh; E010 used 42/142/242/342 |

**Cell verdict (locked).** `alive` iff `n_joint ≥ 100` AND
`lift ≥ +0.10 ATR` AND p survives the stage threshold.
`parked_weak_effect` iff `n_joint ≥ 100` and lift positive but floor
or FDR missed (raw p < 0.05). `parked_insufficient_n` iff
`n_joint < 100` (stats still recorded). Otherwise `dead`.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | α |
|---|---|---|---|---|
| 1 — Cross-pair screen | GBPUSD | 2015-01-01 → 2021-12-31 (H1+M15 cache-constrained) | 10 cells (§2) | BH α = 0.05 across 10 |
| 2 — Sealed | EURUSD | 2025-01-01 → 2026-05-27 (H1+M15; M15 cache ends 2026-05-27) | Stage-1 survivors only | per-cell α = 0.05, run once |

Two stages only: the EURUSD screen/confirm windows are burnt for this
statistic (§0). A GBPUSD-first design is deliberately conservative —
the pattern must replicate on a pair it has never been measured on
before it may touch the sealed slice.

---

## §5 Controls

The displacement null IS the control (hour-restricted in-window
re-draws, E006 v2.1 recipe wired into `screen_pair`); no additional
random-time control is required for a lift-only claim.

---

## §6 Stop rules (pre-declared)

Stops emit `stage{N}_E029_stop.json` under `output/E029_pool_window_timing/`.

- **Stage 1.** If **0 of 10** cells `alive` on GBPUSD → **STOP.** The
  timing edge is declared EURUSD-local; the E010 lift observations are
  downgraded to a parked curiosity; the sealed reservation is
  **released**. No Stage 2.
- **Stage 2.** Any Stage-1 survivor failing sealed → `dead` at the
  sealed level, published as such; no re-look under this ID.

---

## §7 Amendments

_(Append-only; committed before the analysis they enable.)_

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status | Prior uses |
|---|---|---|---|---|---|
| 1 | GBPUSD | H1 + M15 | 2015-01-01 → 2021-12-31 | screen (this statistic: first computation) | H1: E001, E006; M15: E006 — marginal screens, orthogonal statistic; E010/E027/E028 Stage-3 reservations were released un-consumed |
| 2 | EURUSD | H1 + M15 | 2025-01-01 → 2026-05-27 | **sealed (re-reserved)** | Pristine (E010's reservation released un-consumed 2026-07-28) |

**Shared-reservation note.** E030 (pre-registered in the same commit)
reserves the same EURUSD **M15** 2025-01-01 → 2026-05-27 slice for its
own sealed stage. Both reservations are declared simultaneously,
before either experiment has looked at the slice, for **different
event families and different outcome statistics** (conditional MFE
lift vs session-drift net pips). Each experiment runs its sealed stage
once, on frozen parameters; neither may amend based on the other's
sealed result.

---

## §9 Output artefacts (locked naming)

| Artefact | Path |
|---|---|
| Stage-1 registry | `output/E029_pool_window_timing/stage1_GBPUSD_screen_<stamp>.jsonl` |
| Stage-2 registry | `output/E029_pool_window_timing/stage2_EURUSD_sealed_<stamp>.jsonl` |
| Stop files | `output/E029_pool_window_timing/stage{N}_E029_stop.json` |
| Report / Manifest | `experiments/E029_pool_window_timing/{REPORT,MANIFEST}.md` |

---

**Pre-registration commit:** _(hash recorded in `EXPERIMENTS.md` E029
row and `REPORT.md`)_
