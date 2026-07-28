# E010 — Stage-2b: H1 `equal_highs_pool` × M15 setups (pre-registered)

**Status:** PRE-REGISTERED 2026-06-24 · **Date frozen:** 2026-06-24 ·
**Parallel with:** M001 program (`programs/M001_multi_agent_ensemble/`)

This file is the pre-registration of E010. No Stage-1 statistic has been
scored on the EURUSD screen window for the H1×M15 family declared in §2
under the parameters frozen in §3 — the only prior numbers on this
slice/family are the **exploratory** Stage-2 run in E006
(`output/stage2_EURUSD_2026-06-12_1348.jsonl`, 65 H1-context × M15-setup
rows), which produced the hypothesis we now test under pre-registered
parameters.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration (no re-derived code)

E010 reuses the following `conflab/` primitives **exactly as committed at
the pre-registration commit**. No detector parameter, statistical
routine, or null specification is re-derived for this experiment.

| Purpose | Module | Symbol (file:line) |
|---|---|---|
| H1 context detector | `conflab/detectors_liquidity.py` | `detect_liquidity_events` (lines 13–68) emits `equal_highs_pool` at line 45 |
| M15 setup — bullish FVG touch | `conflab/detectors_zones.py` | `detect_fvg_events` emits `bullish_fvg_touch` at line 128 |
| M15 setup — channel bottom touch | `conflab/detectors_trendlines.py` | `detect_trendline_events` emits `channel_bottom_touch` at line 150 |
| M15 setup — fib retracement tags | `conflab/detectors_fib.py` | `detect_fib_events` emits `fib_382_tag` / `fib_50_tag` / `fib_618_tag` (line 19–20) |
| M15 setup — fib extension tag | `conflab/detectors_fib.py` | `detect_fib_events` emits `fib_ext_1272_tag` (line 21) |
| M15 setup — OTE tag | `conflab/detectors_fib.py` | `detect_fib_events` emits `ote_tag` at line 83 |
| M15 setup — trendline support touch | `conflab/detectors_trendlines.py` | `detect_trendline_events` emits `trendline_support_touch` at line 132 |
| M15 setup — trendline break + retest (bullish) | `conflab/detectors_trendlines.py` | `detect_trendline_events` emits `trendline_break_retest_bullish` at line 119 |
| M15 setup — trendline liquidity sweep low | `conflab/detectors_trendlines.py` | `detect_trendline_events` emits `trendline_liquidity_sweep_low` at line 126 |
| Pair screening with displacement null | `conflab/stage2.py` | `screen_pair`, `run_stage2`, `Stage2Config` |
| One-bar directional MFE (ATR units) | `conflab/screening.py` | `directional_outcome` (line 44) |
| Permutation p-value | `conflab/stats.py` | `_permutation_pvalue` (line 7) |
| BH-FDR | `conflab/stats.py` | `benjamini_hochberg` (line 21) |
| ATR(14) (Wilder) | `conflab/indicators.py` | `atr` (line 38) |
| Parquet bar loader | `conflab/data.py` | identical to E006/E007 use |

**Stage-0 prerequisites (must be confirmed before Stage 1 runs):**

1. **Detector inventory complete** — every event type in §2 is emitted by
   the registry returned by `conflab.events.all_detectors()`. No new
   detector is required.
2. **Cache coverage check** — GBPUSD H1 and GBPUSD M15 cached windows
   must be inspected non-destructively (file metadata only, no MFE
   scoring) before Stage 3 runs; E007 §3.8 audit (2026-06-16) recorded
   GBPUSD H1 ending at 2021. Stage 3 inherits that constraint; see §4.
3. **USDCAD H1/M15 absent** — per E007 §3.8 audit, USDCAD H1/M15 are
   not in the parquet cache and therefore cannot serve as the Stage-3
   cross-pair. Re-caching USDCAD intraday slices is **out of scope** for
   E010; if completed later, a separate pre-registration must justify a
   second cross-pair arm.

---

## §1 Hypothesis (operational)

**Prior (exploratory only — does not count as a claim).** E006 Stage-2
exploratory ran 65 H1-context × M15-setup pairs on EURUSD 2015–2021 with
hour-matched displacement nulls. Of those, **10 pairs** used H1
`equal_highs_pool` as the context (rows 11–20 of
`output/stage2_EURUSD_2026-06-12_1348.jsonl`). Every one of those 10 had a
**positive selection term** (joint MFE − setup-marginal MFE) in the
+0.10 to +0.46 ATR range — the finding documented at
[`docs/findings/2026-06-12_equal_highs_pool_context.md`](../../docs/findings/2026-06-12_equal_highs_pool_context.md).

**H0.** Conditional on a +1-direction M15 setup event from the
pre-declared family (§2) firing inside an active H1 `equal_highs_pool`
window, the joint directional MFE is **not** materially higher than the
setup-marginal MFE outside that window (selection term ≤ 0) and not
materially higher than a within-window displaced-setup baseline
(displacement-null lift ≤ 0).

**H1.** Both the **selection term** (`joint_mfe − setup_marginal_mfe`)
and the **displacement-null lift** (`joint_mfe − displaced_mfe`,
computed by `conflab/stage2.py:screen_pair`) are **≥ +0.10 ATR**, with
permutation p < BH-FDR threshold at α = 0.05 across the §3 family.

**Outcome metric.** Mean MFE in event direction within the cell's setup
horizon (M15: 16 bars), divided by ATR(14) at the event bar — the same
metric used in E006 Stage 1 and Stage 2.

**Effect-size floor (+0.10 ATR) is pre-registered and locked.** It is
the lower bound of the exploratory selection-term range (+0.10 ATR), not
a post-hoc choice; cited from
[`docs/findings/2026-06-12_equal_highs_pool_context.md`](../../docs/findings/2026-06-12_equal_highs_pool_context.md)
"selection +0.10 to +0.46 ATR".

---

## §2 Setup family LOCKED (10 cells)

The family is the **complete** set of +1-direction M15 setups that were
paired with H1 `equal_highs_pool` in E006 Stage-2 **exploratory** (rows
11–20 of `output/stage2_EURUSD_2026-06-12_1348.jsonl`) — including the
two that failed the exploratory displacement null. Locking the full
candidate set, not the exploratory survivors, prevents selection bias
from carrying forward into E010 (per
[`docs/methodology/exploratory_stage2.md`](../../docs/methodology/exploratory_stage2.md)).

| # | M15 event type | Detector module | Direction | E006 expl. n_joint | E006 expl. lift (ATR) | E006 expl. verdict |
|---:|---|---|---:|---:|---:|---|
| 1 | `bullish_fvg_touch` | `detectors_zones.py` | +1 | 1,319 | +0.1318 | alive |
| 2 | `channel_bottom_touch` | `detectors_trendlines.py` | +1 | 2,416 | +0.1238 | alive |
| 3 | `fib_382_tag` | `detectors_fib.py` | +1 | 317 | +0.1632 | alive |
| 4 | `fib_50_tag` | `detectors_fib.py` | +1 | 305 | +0.2432 | alive |
| 5 | `fib_618_tag` | `detectors_fib.py` | +1 | 274 | +0.2757 | alive |
| 6 | `fib_ext_1272_tag` | `detectors_fib.py` | +1 | 179 | +0.3237 | alive |
| 7 | `ote_tag` | `detectors_fib.py` | +1 | 274 | +0.2748 | alive |
| 8 | `trendline_break_retest_bullish` | `detectors_trendlines.py` | +1 | 394 | +0.0170 | dead |
| 9 | `trendline_liquidity_sweep_low` | `detectors_trendlines.py` | +1 | 153 | +0.0901 | dead |
| 10 | `trendline_support_touch` | `detectors_trendlines.py` | +1 | 1,327 | +0.1484 | alive |

**Family size:** 10 cells (1 H1 context × 10 M15 setups).

**Directional convention.** `equal_highs_pool` carries `direction=+1`
(buy-side liquidity above the level acts as an upward magnet); only
+1-direction M15 setups count as joint by `conflab/stage2.py`'s
direction-agreement rule (line 113). Mirror tests on `equal_lows_pool`
× −1 M15 setups are out of scope and would require a separate
pre-registration.

---

## §3 Locked parameters

All knobs below are **frozen at this pre-registration commit**. The only
permitted post-registration change is via a §7 amendment that satisfies
the [`docs/methodology/amendments.md`](../../docs/methodology/amendments.md)
recipe.

| Knob | Value | Rationale / source |
|---|---|---|
| Context TF | H1 | Matches E006 exploratory finding (E006 §4.4) |
| Setup TF | M15 | All E006 Stage-1 alive cells are M15; matches finding |
| Context detector | `equal_highs_pool` | Frozen as defined in `detectors_liquidity.py` |
| `equal_highs_pool` lookback | 5 bars (detector default) | Frozen E006 value (`detect_liquidity_events` default) |
| `equal_highs_pool` tol_atr | 0.25 (detector default) | Frozen E006 value |
| `equal_highs_pool` max_scan | 200 bars (detector default) | Frozen E006 value (governs sweep emission only) |
| Setup family | 10 M15 event types in §2 | Locked exploratory candidate set |
| Context window length | 20 H1 bars from context event | `Stage2Config.context_horizons['H1'] = 20`; E006 default |
| Setup MFE horizon | 16 M15 bars | `Stage2Config.setup_horizons['M15'] = 16`; E006 default |
| Permutation null | Within-window displacement (`screen_pair`) | Hour-restricted re-draws per E006 v2.1 (`stage2.py` line 131) |
| Control multiplier (setup-marginal pass) | 5× draws | E006 v2.1 hour-matched recipe |
| `n_perm` (displacement draws) | **5,000** | Floor = 1 / 5,001 ≈ 1.999 × 10⁻⁴ ; below BH-FDR top-rank threshold of 0.005 |
| `n_gate` (alive eligibility) | **100** events per cell | E006 Stage-1 gate; exploratory n_joint was ≥ 153 across all 10 cells |
| Effect-size floor (selection term) | **+0.10 ATR** | Lower bound of E006 exploratory range +0.10 → +0.46 ATR |
| Effect-size floor (displacement-null lift) | **+0.10 ATR** | Same floor applied to the displacement null for consistency |
| FDR | BH α = 0.05 across §2 family (10 cells) | Standard |
| Random seed | 42 (Stage 1) · 142 (Stage 2) · 242 (Stage 3) · 342 (Stage 4) | E007 seed-discipline pattern |
| Warmup | 60 bars per TF | Indicator stabilisation; `Stage2Config.warmup = 60` |
| ATR window | 14 (Wilder) | `conflab/indicators.py:atr` default |

**Cell-level alive verdict (locked).** A cell is `alive` iff **all** of:

1. `n_joint ≥ 100` (n_gate);
2. `selection_term ≥ +0.10 ATR` AND `displacement_lift ≥ +0.10 ATR`;
3. permutation `p` survives BH-FDR α = 0.05 across the 10-cell family.

A cell is `parked_weak_effect` iff it has `n_joint ≥ 100` and either
effect floor missed (positive but <+0.10 ATR on at least one of the two
metrics) OR FDR failed at raw `p < 0.05`. A cell is
`parked_insufficient_n` iff `n_joint < 100` (stats still computed and
recorded per the compute-vs-claim principle). All other cells are
`dead`.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR / α |
|---|---|---|---|---|---|
| 1 — Screen | EURUSD | 2015-01-01 → 2021-12-31 | 10 cells (§2) | displacement-null permutation p; selection-term & lift effect floors | BH α = 0.05 across 10 |
| 2 — Confirm | EURUSD | 2022-01-01 → 2024-12-31 | Stage-1 survivors only | same test, frozen parameters | per-cell α = 0.05 (small family; no BH) |
| 3 — Cross-pair | GBPUSD | 2015-01-01 → 2021-12-31 (see below) | Stage-2 survivors only | same test, frozen parameters | per-cell α = 0.05 |
| 4 — Sealed | EURUSD | 2025-01-01 → 2026-06-09 (H1+M15) | Stage-3 survivors only | same test, frozen parameters | per-cell α = 0.05 |

**Cross-pair scope (Stage 3).** The task's two candidates were GBPUSD
2015–2024 and USDCAD 2015–2024. Per E007 §3.8 audit (2026-06-16):

- USDCAD H1 and USDCAD M15 are **not cached** in
  `multi-pair-trading-agent/data/parquet/` (verified again at this
  pre-reg commit: only `USDCAD_D1.parquet` and `USDCAD_H4.parquet`
  exist). USDCAD is therefore **infeasible** without re-caching, which
  is out of scope.
- GBPUSD H1 cache ends 2021-12-31 (E007 §3.8). GBPUSD M15 cache exists
  but the upper bound is not separately audited; Stage 0 verifies and
  the Stage-3 window is the **intersection** of the GBPUSD H1 and
  GBPUSD M15 cached ranges, defaulting to 2015-01-01 → 2021-12-31.

**Choice:** GBPUSD 2015–2021 (frozen parameters). Re-caching GBPUSD
H1 to 2024 or USDCAD H1/M15 enables a wider Stage-3 in a future
amendment; E010 does not depend on that.

**Sealed slice (Stage 4).** EURUSD H1 + M15 over 2025-01-01 → 2026-06-09.
Pristine for these timeframes: per `DATA_LEDGER.md`, EURUSD H4
2025-2026 is the only EURUSD sealed slice consumed (by E005); H1 and
M15 in that window are unused.

**Displacement null and hour-restricted re-draws.** Per
`conflab/stage2.py` lines 125–137: setup-event timings are re-drawn from
the same context window restricted to bars sharing the event's
hour-of-day (fallback: any in-window bar) — this is the binding
hour-matched-controls recipe (§5).

**Compute-vs-claim.** Every cell in the §2 family is scored and recorded
at every stage regardless of `n_joint`. The n_gate governs eligibility
to be called `alive`, not whether statistics are computed.

---

## §5 Hour-matched controls (mandatory)

Binding per
[`docs/methodology/hour_matched_controls.md`](../../docs/methodology/hour_matched_controls.md)
and `PROTOCOL_DISCIPLINE.md` §3. M15 outcomes are
ATR(14)-normalised and the EUR/USD M15 hour-of-day cycle produces a
**3.7×** random-MFE variation (E006 diagnostic). Uniform-time controls
would impose a false null. Two consequences for E010:

1. The setup-marginal MFE used in the selection-term decomposition is
   computed from **hour-matched** random-time draws on the M15 frame
   (`conflab/screening.py:screen_cell` with `hour_matched=True`), 5×
   draws per event, direction-matched.
2. The displacement-null draws inside `screen_pair` are restricted to
   in-window bars sharing the event's hour-of-day (the v2.1 carry-forward
   already wired into `conflab/stage2.py` lines 125–137).

No new control specification is introduced. Any change to either
control draw is a §7 amendment.

---

## §6 Stop rules (pre-declared)

Each stop emits a `stage{N}_..._stop.json` artefact under
`output/E010_equal_highs_pool_stage2b/` documenting the trigger, the
family snapshot at that stage, and which downstream stages did not run
(E007 stop-file template).

- **Stage 1.** If **0 of 10** cells in §2 finish with verdict `alive`
  on EURUSD 2015–2021 → **STOP at Stage 1.** Emit
  `stage{2,3,4}_E010_stop.json` referencing the Stage-1 registry.
  Final verdict: the exploratory finding does not survive
  pre-registered confirmation; report the negative honestly. M001 A6
  Nagi treats `equal_highs_pool` as a parked primitive, not a
  deployment input.
- **Stage 2.** If **0 of Stage-1 survivors** confirm on EURUSD
  2022–2024 → **STOP at Stage 2.** Emit `stage{3,4}_E010_stop.json`.
  Tag each Stage-1 survivor as `parked_weak_effect` in the registry
  with the confirm-window p and effect.
- **Stage 3.** If **0 of Stage-2 survivors** replicate on GBPUSD
  2015–2021 → finding is declared **local to EURUSD**, do **not**
  promote. Emit `stage4_E010_stop.json`. Stage 4 sealed slice is
  **released** back to pristine status in `DATA_LEDGER.md`.
- **Stage 4.** If the sealed slice fails on any Stage-3 survivor →
  **publish as null** and tag the cell `dead` at the sealed level. No
  further re-look is permitted under this pre-registration; a new
  hypothesis requires a new ID.

**Stopping at any stage is a valid outcome and is reported with the
same prominence as a survivor.**

---

## §7 Amendments

(Append-only; each amendment is its own commit landing **before** the
analysis it enables runs, per
[`docs/methodology/amendments.md`](../../docs/methodology/amendments.md).)

**Planned diagnostic that may trigger an amendment.** Before Stage 1 is
scored, a **count-only** diagnostic verifies that every cell in §2
crosses `n_joint ≥ 100` on the EURUSD 2015–2021 screen window
(`scripts/E010/diagnose_counts.py`, MFE outcome path not invoked). If
**any** cell falls below n=100 because of frozen detector parameters
interacting with the screen window:

- The cell is reported `parked_insufficient_n` with statistics still
  computed (compute-vs-claim).
- **No parameter is relaxed** to recover the count. E010 inherits
  E007's amendment 6.2 rule: one-shot relaxation is permitted only when
  it is the *smallest* change crossing the gate, and only with a
  cautionary file preserving the original strict registry. This is not
  expected here because the exploratory data showed every cell at
  n_joint ≥ 153 on the same window.

**A1 — 2026-07-28 (infrastructure, pre-Stage-0, non-claiming).** Bars
are loaded by direct read-only `pd.read_parquet` of the canonical
cache (`multi-pair-trading-agent/data/parquet/`) instead of
`conflab.data.load_frames`: `BarLoader`'s head-gap backfill hits the
Dukascopy network path (Phase AE incident 2026-07-24; reproduced
2026-07-28 during E027/E028 Stage-0 coverage checks and killed before
any cache write). Window slicing and column schema are identical; no
detector parameter, statistical routine, or null specification
changes; no E010 statistic had been scored at the time of this
amendment. Runner code: `scripts/E010/` (`diagnose_counts.py`
count-only diagnostic per §7; `run_e010.py` stage runner).

**A2 — 2026-07-28 (clarification, pre-Stage-0, non-claiming).** The
setup-marginal MFE in the §1 selection-term decomposition is computed
with the identical event/outcome code path as `screen_cell`
(`directional_outcome` over all usable setup events of the cell's
type, warmup-filtered) accompanied by 5× hour-matched
direction-matched random-time control draws, but WITHOUT
`screen_cell`'s marginal permutation p-value — no test is
pre-registered on the marginal itself and computing that p on
10⁴–10⁵-event M15 marginals would burn hours for a number the §3
verdict never consults. The verdict-bearing p remains `screen_pair`'s
displacement null with `n_perm = 5000`, unchanged.

---

## §8 Cross-references

- **E006 — exploratory source.**
  [`experiments/E006_test_a_price_action/REPORT.md`](../../experiments/E006_test_a_price_action/REPORT.md)
  §4.4 (the 65-pair exploratory Stage-2 run); registry at
  `output/stage2_EURUSD_2026-06-12_1348.jsonl` rows 11–20.
- **Finding doc.**
  [`docs/findings/2026-06-12_equal_highs_pool_context.md`](../../docs/findings/2026-06-12_equal_highs_pool_context.md)
  — the +0.10 to +0.46 ATR selection-term range cited as the effect-floor
  source.
- **M001 doctrine.**
  [`programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md`](../../programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md)
  §3.3 (Chemical reaction / confluence) cites E006 Stage-2 exploratory
  as the empirical prior for the late-fusion frame. E010 is the
  pre-registered validation that prior is waiting on.
- **M001 A6 Nagi (confluence-only thesis).**
  [`programs/M001_multi_agent_ensemble/05-agent-roster-v0.md`](../../programs/M001_multi_agent_ensemble/05-agent-roster-v0.md)
  — A6 Nagi's deployment-grade confluence layer does not graduate until
  E010 produces an `alive` verdict at Stage 4. The doctrine treats this
  as a directional prior, not deployment authority.
- **M001 A1 Isagi v2.** Same roster — `equal_highs_pool` is the
  vocabulary primitive Isagi v2 imports from
  `conflab/detectors_liquidity.py`.
- **Audit.**
  [`audits/2026-06-24_E001-E007_audit.md`](../../audits/2026-06-24_E001-E007_audit.md)
  §2.6 (E006 exploratory Stage-2 disclosure; the source of the E010
  registration).

---

## §9 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H1 + M15 | 2015-01-01 → 2021-12-31 | screen | EURUSD H1 screen: E001, E006, E007 (E010 → 4th); EURUSD M15 screen: E001, E006 (E010 → 3rd). The hypothesis under test is *conditional* (context × setup), orthogonal to the marginal screen those experiments ran on the same slice. The "overuse warning" on EURUSD H4 (6 uses) does not apply at H1/M15 but is acknowledged. |
| 2 | EURUSD | H1 + M15 | 2022-01-01 → 2024-12-31 | confirm | EURUSD H1 confirm: E006, E007; EURUSD M15 confirm: E006. Independent of Stage 1; survivors enter with frozen parameters. |
| 3 | GBPUSD | H1 + M15 | 2015-01-01 → 2021-12-31 (cache-constrained) | cross-pair / sealed | GBPUSD H1 screen: E001, E006; GBPUSD M15: E006 screen-style replication. E010 cross-pair is run **with frozen parameters** — no selection on this slice — so the prior uses do not contaminate the test. |
| 4 | EURUSD | H1 + M15 | 2025-01-01 → 2026-06-09 | **sealed (reserved, not yet consumed)** | None for H1/M15 in this window (E005 only used H4). |

**Sealed reservation:** the Stage-4 slice (EURUSD H1+M15
2025-01-01 → 2026-06-09) is **declared reserved** for E010 at this
pre-registration commit. No other experiment may consume it without an
amendment to this protocol releasing it. If Stages 1–3 stop early, the
reservation is released and `DATA_LEDGER.md` is updated to remove the
hold.

---

## §10 Statistical floor (shown working)

- **Permutation floor.** With `n_perm = 5000` displacement draws, the
  lowest achievable two-step lower bound on `p` is `1 / (n_perm + 1)`
  = **1 / 5001 ≈ 1.999 × 10⁻⁴**.
- **BH-FDR threshold across the §2 family (m = 10 cells, α = 0.05).**
  Top-rank threshold = `α × 1 / m` = `0.05 / 10` = **5.0 × 10⁻³**.
  Bottom-rank threshold = `α` = 5.0 × 10⁻². The permutation floor sits
  comfortably below the most stringent BH threshold, so a genuine cell
  can clear FDR without being capped at the floor (E007 §3.6 pattern).
- **Sign-test sanity check (reported, not gating).** Under H0, the
  probability that all 10 cells (or all Stage-1 survivors) show
  positive sign on the displacement-null lift in *one* OOS test is
  `0.5^k` (k = survivor count). For k = 10 that is `9.8 × 10⁻⁴`; for
  k = 5 it is `3.1 × 10⁻²`; for k = 3 it is `0.125`. This is reported
  alongside the cell-level test as a family-level coherence diagnostic,
  not as a substitute for per-cell BH-FDR.
- **Effect-size floor logic.** The +0.10 ATR floor on **both** the
  selection term and the displacement-null lift is below the
  exploratory minimum (+0.10 ATR was the lower bound observed across
  all 10 cells) and well below the median (+0.20 ATR), so winner's
  curse-style attenuation on confirm (the E006 fib pattern) would be
  visible without being immediately fatal.

---

## §11 Output artefacts (locked naming)

| Artefact | Path |
|---|---|
| Stage-1 registry | `output/E010_equal_highs_pool_stage2b/stage1_EURUSD_screen_<stamp>.jsonl` |
| Stage-2 registry | `output/E010_equal_highs_pool_stage2b/stage2_EURUSD_confirm_<stamp>.jsonl` |
| Stage-3 registry | `output/E010_equal_highs_pool_stage2b/stage3_GBPUSD_<stamp>.jsonl` |
| Stage-4 registry | `output/E010_equal_highs_pool_stage2b/stage4_EURUSD_sealed_<stamp>.jsonl` |
| Stop files | `output/E010_equal_highs_pool_stage2b/stage{N}_E010_stop.json` |
| Diagnostic (count-only, pre-MFE) | `output/E010_equal_highs_pool_stage2b/stage0_counts_<stamp>.json` |
| Figures | `output/E010_equal_highs_pool_stage2b/figures/` |
| Manifest | `experiments/E010_equal_highs_pool_stage2b/MANIFEST.md` (after Stage 1 lands) |
| Report | `experiments/E010_equal_highs_pool_stage2b/REPORT.md` (after stop or Stage 4) |

---

**Pre-registration commit:** _(this file's commit hash on
`multi-agent-ensemble`; recorded in `EXPERIMENTS.md` E010 row and in
`REPORT.md` when results land)_
