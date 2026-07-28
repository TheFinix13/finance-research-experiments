# E028 — "Power of Three" session sequence: descriptive base rates + one mechanical rule

**Status:** PRE-REGISTERED 2026-07-28 · **Date frozen:** 2026-07-28 ·
**Branch:** `main` (user-declared 2026-07-28 session)

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 What is being tested and why it must be reduced first

The folk narrative (external discretionary material reviewed
2026-07-28, user-supplied): *Asia accumulates and builds the range;
London manipulates by taking exactly one side of it; New York fakes a
continuation of London's move, then reverses to the untapped Asia
liquidity on the other side.*

As stated this is unfalsifiable (three-act narrative with no
frequencies). E028 reduces it to (a) **pre-declared descriptive base
rates** — how often does the full sequence actually complete, versus
how often price reaches the same levels unconditionally — and (b)
**one mechanical entry rule** tested for after-cost expectancy. No
component of this narrative has been tested in this lab before: E001's
sweep concept was level-based, not session-sequence-based;
`conflab/detectors_sessions.py` (Asia-range sweeps) was part of E006's
Test-A registry, a different (marginal, MFE-screen) question.

Folk prior carries zero evidential weight. Expected outcome under the
lab's priors: completion rates far below what the material implies.

## §0b Reuse declaration

| Purpose | Module | Symbol |
|---|---|---|
| Session window convention | `conflab/detectors_sessions.py` | Asia 00:00–06:59 UTC, London 07:00–12:59 UTC (house convention, kept) |
| Parquet bar loader | `conflab/data.py` | `load_frames` |
| BH-FDR | `conflab/stats.py` | `benjamini_hochberg` |

New experiment-scoped code lives in `programs/E028/` (day classifier +
runner + tests), frozen at the pre-registration commit.

**Session-window caveat (pre-declared).** Windows are **fixed UTC**,
matching the committed house detector, not DST-aware exchange-local
time. The NY equity open (09:30 ET) is 13:30 UTC in summer and 14:30
UTC in winter; the entry rule (§2) anchors at **13:30 UTC year-round**
for mechanical simplicity. This is a deliberate, frozen simplification;
a DST-aware variant is a new ID, not an amendment.

---

## §1 Day construction and descriptive metrics (no verdicts, CIs only)

On M15 bars, per UTC calendar day `D`:

- **Asia range:** `asia_high` / `asia_low` = max high / min low over
  bars with hour in [0, 7). Require ≥ 16 Asia bars, else skip the day
  (holiday/gap guard; expected ~28).
- **London take:** during hours [7, 13): `took_high` iff any
  `high > asia_high`; `took_low` iff any `low < asia_low`. Day class:
  `HIGH_ONLY`, `LOW_ONLY`, `BOTH`, `NEITHER`.
- **NY window:** hours [13, 21). "NY touches level X" iff any NY bar's
  high ≥ X (upper level) / low ≤ X (lower level).

Descriptive metrics, each with a Wilson 95 % CI, reported per pair per
split window and per year:

| ID | Metric |
|---|---|
| D1 | Day-class distribution (4 classes) |
| D2 | **Completion rate:** P(NY touches the *opposite* Asia extreme \| class ∈ {HIGH_ONLY, LOW_ONLY}) — the headline Po3 claim |
| D3 | Baselines: P(NY touches asia_high), P(NY touches asia_low) unconditionally; and completion-equivalents on BOTH and NEITHER days |
| D4 | **Fake rate:** P(NY first extends beyond London's own extreme in the taken direction before touching the opposite Asia extreme \| one-side day) |
| D5 | Completion timing: median NY bar index at first opposite-extreme touch (completed days) |
| D6 | Per-year D2 vs D3 table (stability read) |

**Pre-declared separation margin (feeds the stop rule, not a
verdict):** the narrative is *descriptively supported* only if
D2 exceeds the matched unconditional baseline (D3 for the same target
level) by ≥ **+5 percentage points** on the screen window.

---

## §2 Mechanical rule (the only inferential test)

On one-side days only; entry decision uses information available at
entry time only.

| Component | Rule |
|---|---|
| Arm LONG (cell 1) | Day class `LOW_ONLY` (London took Asia lows) → long toward `asia_high` |
| Arm SHORT (cell 2) | Day class `HIGH_ONLY` → short toward `asia_low` |
| Entry | Close of the first M15 bar with open time ≥ 13:30 UTC |
| Skip rules | Skip if the opposite extreme (TP) was already touched before entry; skip degenerate geometry (entry beyond TP, or SL side inverted); skipped-day counts reported |
| Stop loss | The day's manipulation extreme so far: for LONG, min low over hours [7, entry); for SHORT, max high over [7, entry) |
| Take profit | The untapped Asia extreme |
| Time exit | Close of the last M15 bar before 21:00 UTC if neither SL nor TP hit |
| Intrabar both-hit | Adverse-first (house conservative rule, `directional_outcome` convention) |
| Costs — base | 0.3 pip per side (house E001 convention) |
| Costs — stress | 1.0 pip per side (intraday realism arm; both reported) |

**Outcome:** net pips per trade. **Statistic per cell:** mean net
pips at base costs; one-sided bootstrap p = (1 + #{resample mean ≤ 0})
/ (1 + B), B = 10,000, seed 28. BH α = 0.05 across the 2-cell family.

**Cell verdict (locked).** `alive` iff n ≥ 100 trades AND bootstrap
95 % CI lower bound > 0 at base costs AND mean > 0 at stress costs AND
BH-significant. `parked_weak_effect` iff n ≥ 100 and mean > 0 at base
costs but any other condition fails. `parked_insufficient_n` iff
n < 100. Otherwise `dead`.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| TF | M15 | Finest cached TF with full-window coverage |
| Asia window | 00:00–06:59 UTC | House convention (`detectors_sessions.py`) |
| London window | 07:00–12:59 UTC | House convention |
| NY window | 13:00–20:59 UTC | Completes the 24 h partition to rollover |
| Entry anchor | 13:30 UTC fixed | §0b caveat, frozen |
| Min Asia bars | 16 | Holiday/gap guard |
| n-gate (mechanical) | 100 trades per cell | House gate |
| Bootstrap B | 10,000 | CI stability |
| Seeds | 28 (Stage 1) · 128 (Stage 2) · 228 (Stage 3) | Distinct from E010/E027 |
| Costs | 0.3 pip/side base; 1.0 pip/side stress | E001 convention + intraday stress |
| FDR | BH α = 0.05 across 2 cells | Standard |
| Descriptive margin | +5 pp over matched baseline | Pre-declared, feeds stop rule |

---

## §4 Statistical pipeline

| Stage | Pair | Period | Content | α |
|---|---|---|---|---|
| 1 — Screen | EURUSD | 2015-01-01 → 2021-12-31 | D1–D6 descriptive + 2 mechanical cells | BH α=0.05 across 2 |
| 2 — Confirm | EURUSD | 2022-01-01 → 2024-12-31 | D1–D6 re-report + surviving mechanical cells | per-cell α=0.05 |
| 3 — Cross-pair | GBPUSD | 2015-01-01 → 2021-12-31 (M15 cache-constrained) | same, frozen params | per-cell α=0.05 |

**No sealed stage:** EURUSD M15 2025-01-01 → 2026-06-09 is **reserved
by E010** and is not touched. USDCAD M15 is not cached — no USDCAD
arm. A sealed pass requires a future pre-registered amendment once a
pristine M15 slice exists.

---

## §5 Controls and confounds

- D2 vs D3 is a **conditional-vs-marginal comparison on identical
  target levels within identical NY windows** — the session-volatility
  confound cancels by construction (same clock window, same day
  universe).
- The BOTH/NEITHER conditional completions (D3) act as the placebo
  arms: if "London took one side" adds no information, D2 ≈ the
  BOTH-day equivalent.
- Mechanical-rule expectancy is reported at both cost levels; the
  stress arm exists because M15 fills near session opens are where the
  0.3-pip house convention is least realistic.
- No hour-matched random-time control is needed: the day structure IS
  the clock control.

---

## §6 Stop rules (pre-declared)

Stops emit `stage{N}_E028_stop.json` under `output/E028_power_of_three_sessions/`.

- **Stage 1 (full stop).** If D2 fails the +5 pp margin over the
  matched baseline **AND** both mechanical cells are non-positive at
  base costs → **STOP.** The narrative is not descriptively supported
  and carries no tradable expectancy on the screen window. Any M001
  Po3 striker is blocked by this registry entry until a new
  pre-registration.
- **Stage 1 (partial).** If D2 passes the margin but both mechanical
  cells fail → publish the descriptive finding, tag mechanical cells
  per §2, **no Stage 2/3 for the mechanical rule**; a redesigned entry
  is a new ID.
- **Stage 2.** If 0 surviving cells confirm → STOP; survivors tagged
  `parked_weak_effect`.
- **Stage 3.** If 0 replicate on GBPUSD → **EURUSD-local**; do not
  promote.

Stopping is a valid outcome and is reported with the same prominence
as a survivor.

---

## §7 Amendments

_(Append-only; each amendment lands as its own commit before the
analysis it enables runs.)_

**A1 — 2026-07-28 (infrastructure, pre-Stage-1, non-claiming).** Bars
are loaded by direct read-only `pd.read_parquet` of the canonical
cache instead of `conflab.data.load_frames` — same rationale and same
incident record as E027 §7 A1 (BarLoader head-gap backfill hits the
Dukascopy network path). No statistic was scored before this
amendment.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | M15 | 2015-01-01 → 2021-12-31 | screen | E001, E006, E010(reserved, different event family) — documented per overuse rule; E028's outcome (day-level sequence completion + session trade expectancy) is orthogonal to prior marginal MFE screens |
| 2 | EURUSD | M15 | 2022-01-01 → 2024-12-31 | confirm | E006, E010(reserved) |
| 3 | GBPUSD | M15 | 2015-01-01 → 2021-12-31 | cross-pair | E006 (screen-style replication), E010(reserved) — frozen-parameter replication only |

E010's sealed reservation (EURUSD H1+M15 2025-01-01 → 2026-06-09) is
**untouched** by E028.

---

## §9 Output artefacts (locked naming)

| Artefact | Path |
|---|---|
| Stage-1 descriptive + registry | `output/E028_power_of_three_sessions/stage1_EURUSD_screen_<stamp>.json` |
| Stage-2 | `output/E028_power_of_three_sessions/stage2_EURUSD_confirm_<stamp>.json` |
| Stage-3 | `output/E028_power_of_three_sessions/stage3_GBPUSD_<stamp>.json` |
| Stop files | `output/E028_power_of_three_sessions/stage{N}_E028_stop.json` |
| Report | `experiments/E028_power_of_three_sessions/REPORT.md` |
| Manifest | `experiments/E028_power_of_three_sessions/MANIFEST.md` |

Runner: `programs/E028/run_e028_validation.py` · Day classifier:
`programs/E028/po3_days.py` · Tests: `programs/E028/tests/`.

---

**Pre-registration commit:** _(this file's commit hash on `main`;
recorded in `EXPERIMENTS.md` E028 row and in `REPORT.md` when results
land)_
