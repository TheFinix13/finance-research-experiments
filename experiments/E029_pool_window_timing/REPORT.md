# E029 — Pool-window timing (lift-only): REPORT

**Verdict: ALIVE at sealed (2026-07-28) — 2 cells.**
First surviving claim of the liquidity-structure line (E010 / E027 /
E028 / E030 all stopped). Pre-registration commit `36328ab`; harness
commit `3e90cf4`; protocol frozen 2026-07-28; both stages run
2026-07-28, sealed stage run once.

---

## 1. Claim tested

Inside active H1 `equal_highs_pool` windows, real M15 setup timing
beats hour-matched displaced timing by ≥ +0.10 ATR of directional MFE
(16-bar horizon). Lift-only successor to E010, whose selection term
died OOS but whose lift survived everywhere it was measured. EURUSD
2015–2021 and 2022–2024 were declared burnt for this statistic
(observed under E010, priors only) — all evidence below is from data
the statistic had never touched.

## 2. Stage 1 — GBPUSD 2015–2021, full 10-cell family, BH α = 0.05

First computation of the lift on a second pair. 319 H1 pool events;
seed 29; `n_perm` 5,000.

| Cell | n_joint | Lift (ATR) | p | Verdict |
|---|---|---|---|---|
| bullish_fvg_touch | 1,378 | +0.111 | 0.0002 | alive |
| channel_bottom_touch | 2,851 | +0.141 | 0.0002 | alive |
| fib_382_tag | 319 | +0.122 | 0.0014 | alive |
| fib_50_tag | 321 | +0.177 | 0.0002 | alive |
| fib_618_tag | 315 | +0.203 | 0.0002 | alive |
| fib_ext_1272_tag | 200 | +0.378 | 0.0002 | alive |
| ote_tag | 315 | +0.204 | 0.0002 | alive |
| trendline_break_retest_bullish | 422 | +0.049 | 0.110 | dead |
| trendline_liquidity_sweep_low | 142 | −0.026 | 0.652 | dead |
| trendline_support_touch | 1,559 | +0.159 | 0.0002 | alive |

**8/10 alive.** The two dead cells are the same trendline-event
families that were weakest on EURUSD under E010. Cross-pair
replication of the timing effect is unambiguous.

## 3. Stage 2 — EURUSD 2025-01-01 → 2026-05-27 sealed, run once

8 Stage-1 survivors; per-cell α = 0.05; seed 129; 83 H1 pool events
in the 17-month window (n-gate = 100 joint events bound five cells).

| Cell | n_joint | Lift (ATR) | p | Verdict |
|---|---|---|---|---|
| bullish_fvg_touch | 381 | **+0.101** | 0.0002 | **alive** |
| trendline_support_touch | 422 | **+0.102** | 0.0014 | **alive** |
| channel_bottom_touch | 741 | +0.091 | 0.0004 | parked_weak_effect (floor missed) |
| fib_382_tag | 81 | +0.096 | 0.047 | parked_insufficient_n |
| fib_50_tag | 86 | +0.050 | 0.226 | parked_insufficient_n |
| fib_618_tag | 82 | +0.198 | 0.0044 | parked_insufficient_n |
| fib_ext_1272_tag | 48 | +0.385 | 0.0004 | parked_insufficient_n |
| ote_tag | 82 | +0.199 | 0.0034 | parked_insufficient_n |

## 4. Interpretation

- **The claim stands, narrowly and exactly as registered:** pool
  windows are a valid **when-filter**. Real setups inside an active
  equal-highs-pool window resolve ~0.10–0.38 ATR more favourably than
  the same-hour displaced baseline, on every pair and window measured
  (EURUSD 2015–21 / 2022–24 as E010 priors; GBPUSD 2015–21 and sealed
  EURUSD 2025–26 as fresh evidence).
- **All 8 sealed point estimates are positive.** The five
  insufficient-n cells parked on the gate, not on sign — the short
  sealed window (83 pool events) simply cannot power ~80-event cells.
  Per protocol there is no re-look under this ID; a longer sealed
  window would need a new pre-registration.
- **What this is NOT:** a tradable edge. The statistic is MFE-based,
  cost-free, screen-grade. E010's which-claim (selection) remains
  dead: the windows don't pick better setups, they mark better
  *moments*. Production use = a timing gate on an already-validated
  entry, and that requires its own study plus the agent validation
  chain (per house rules, nothing lands in `multi-pair-trading-agent`
  from this).

## 5. Discipline notes

- Family locked at the full 10 cells (not E010's 7 survivors) before
  any GBPUSD computation — Stage 1 could have embarrassed the
  hypothesis and nearly did for the trendline cells.
- Sealed slice consumed by this run once; shared reservation with
  E030 documented in both protocols pre-look (E030 stopped at its
  Stage 1 and never touched it).
- No selection term / marginal computed anywhere, as registered.
- Seeds 29/129; direct read-only parquet loads; no amendments needed
  (§7 empty).

## 6. Artefacts

- Stage 1: `output/E029_pool_window_timing/stage1_GBPUSD_screen_2026-07-28_1818.jsonl`
- Stage 2: `output/E029_pool_window_timing/stage2_EURUSD_sealed_2026-07-28_1818.jsonl`
