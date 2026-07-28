# E010 — Report: Stage-2b H1 `equal_highs_pool` × M15 setups

**Verdict: STOPPED at Stage 2 (2026-07-28).** Stage 1 (screen) put 7 of
10 cells alive; Stage 2 (confirm, EURUSD 2022–2024) confirmed **0 of
7** — every Stage-1 survivor's selection term collapsed. Per §6, the
Stage-1 survivors are tagged `parked_weak_effect` at the experiment
level; Stages 3–4 did not run; the Stage-4 sealed reservation (EURUSD
H1+M15 2025-01-01 → 2026-06-09) is **released** in `DATA_LEDGER.md`.

- Pre-registration commit: `fd8eb3d` (2026-06-24)
- §7 amendments A1/A2 + runner commit: `a159ec1` (2026-07-28, before
  any statistic)
- Stage-0 counts: `output/E010_equal_highs_pool_stage2b/stage0_counts_2026-07-28_1723.json`
- Stage-1 registry: `output/E010_equal_highs_pool_stage2b/stage1_EURUSD_screen_2026-07-28_1724.jsonl`
- Stage-2 registry: `output/E010_equal_highs_pool_stage2b/stage2_EURUSD_confirm_2026-07-28_1730.jsonl`
- Stop files: `output/E010_equal_highs_pool_stage2b/stage{3,4}_E010_stop.json`

---

## 1. Stage 0 — integrity check passed exactly

The count-only diagnostic reproduced the E006 exploratory joint counts
**to the event** on all 10 cells (1319, 2416, 317, 305, 274, 179, 274,
394, 153, 1327): the frozen detector pipeline regenerates the
exploratory event universe identically. All cells crossed the
n_joint ≥ 100 gate; no §7 relaxation was needed.

## 2. Stage 1 — screen (EURUSD 2015–2021, seed 42): 7/10 alive

| Cell | n_joint | joint MFE | marginal | **selection** | **lift** | p | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| bullish_fvg_touch | 1,319 | 2.621 | 2.423 | +0.198 | +0.131 | 0.0002 | alive |
| channel_bottom_touch | 2,416 | 2.584 | 2.485 | +0.099 | +0.123 | 0.0002 | parked_weak_effect |
| fib_382_tag | 317 | 2.739 | 2.549 | +0.190 | +0.163 | 0.0004 | alive |
| fib_50_tag | 305 | 2.883 | 2.605 | +0.278 | +0.245 | 0.0002 | alive |
| fib_618_tag | 274 | 2.723 | 2.605 | +0.118 | +0.275 | 0.0002 | alive |
| fib_ext_1272_tag | 179 | 3.221 | 2.756 | +0.465 | +0.325 | 0.0002 | alive |
| ote_tag | 274 | 2.723 | 2.605 | +0.118 | +0.275 | 0.0002 | alive |
| trendline_break_retest_bullish | 394 | 2.711 | 2.589 | +0.122 | +0.021 | 0.308 | dead |
| trendline_liquidity_sweep_low | 153 | 3.006 | 2.821 | +0.184 | +0.090 | 0.081 | dead |
| trendline_support_touch | 1,327 | 2.664 | 2.452 | +0.212 | +0.149 | 0.0002 | alive |

Lifts match the E006 exploratory values to ~0.001 ATR (e.g. fvg
+0.131 vs +0.132); `channel_bottom_touch` missed the +0.10 selection
floor by 0.0014 ATR; the two exploratory-dead cells stayed dead. Note
Stage 1 shares its window with the exploratory run — passing it was
necessary, not evidential; the test was Stage 2.

## 3. Stage 2 — confirm (EURUSD 2022–2024, seed 142): 0/7, STOP

| Cell | n_joint | joint MFE | marginal | **selection** | **lift** | p | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| bullish_fvg_touch | 680 | 2.437 | 2.424 | **+0.013** | +0.112 | 0.0002 | parked_weak_effect |
| fib_382_tag | 156 | 2.341 | 2.392 | **−0.050** | +0.183 | 0.0002 | dead |
| fib_50_tag | 141 | 2.194 | 2.547 | **−0.353** | +0.139 | 0.0036 | dead |
| fib_618_tag | 121 | 2.308 | 2.611 | **−0.303** | +0.279 | 0.0002 | dead |
| fib_ext_1272_tag | 92 | 2.167 | 2.830 | **−0.664** | +0.256 | 0.0016 | parked_insufficient_n |
| ote_tag | 121 | 2.308 | 2.611 | **−0.303** | +0.279 | 0.0002 | dead |
| trendline_support_touch | 712 | 2.369 | 2.535 | **−0.166** | +0.134 | 0.0002 | dead |

## 4. The interesting decomposition

The two halves of the pre-registered claim split cleanly out of
sample:

- **The displacement-null lift survives.** Inside an active
  `equal_highs_pool` window, real setup timing beats hour-matched
  displaced timing by +0.11 to +0.28 ATR with p ≤ 0.0036 — in the
  *confirm* window, on frozen parameters. The within-window timing
  component of the exploratory finding is genuine and stable.
- **The selection term flips sign everywhere.** In 2015–2021 the
  windows caught above-average setups (+0.12 to +0.47 ATR); in
  2022–2024 they caught *below*-average ones (−0.05 to −0.66; the fib
  family worst). H1 equal-highs context stopped being a useful setup
  *selector* even though in-window timing still matters.

Since the §3 alive criterion demanded **both** floors, the composite
claim fails; per §6 the honest label for the seven Stage-1 survivors is
`parked_weak_effect` with the confirm-window stats above.

## 5. Consequences

- **A6 Nagi's confluence-only deployment grade stays blocked** — the
  doctrine was explicitly waiting on an E010 `alive` at Stage 4; it
  never got past Stage 2.
- The E006 §4.4 exploratory prior is now bounded: it was real, but
  regime-local to the screen years in its selection component.
- A future hypothesis targeting the **lift** component alone (does the
  pool window improve *timing* rather than *selection*?) is a
  legitimately different claim and requires a new ID; this registry's
  numbers (Stage-2 lifts, all positive and significant) are its
  motivating exploratory prior.
- Sealed slice EURUSD H1+M15 2025-01-01 → 2026-06-09 released to
  pristine; GBPUSD Stage-3 reservation released.

## 6. Discipline notes

- Amendments A1 (network-free loader) and A2 (marginal via shared MFE
  table, no marginal p) landed in `a159ec1` before any statistic.
- Stage-2 registry rows carry the mechanical §3 labels
  (`dead`/`parked_*`); the §6 stop clause governs the experiment-level
  tags reported here.
- `fib_ext_1272_tag` fell to n_joint = 92 (< 100) on the confirm
  window; stats computed and recorded per compute-vs-claim, no
  parameter relaxed (§7 planned-diagnostic rule).
