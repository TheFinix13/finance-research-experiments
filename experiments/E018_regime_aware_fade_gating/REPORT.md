# E018 — Regime-aware fade gating: REPORT

**Verdict: `dead` (STOP).** The pre-registered Stage-1 gate is **not met**.
The R2 (trend-extension/breakout) subset of the `zone_d1_against` fade is **not**
a negative-expectancy regime out-of-sample — it is roughly break-even to
mildly positive across all three deployed pairs. Gating it out is therefore
**not justified**, and **no live code is changed** (`STOP_NOTICE.md`).

- Study registered in [`PROTOCOL.md`](PROTOCOL.md) (frozen 2026-07-14, before any labelling/backtest).
- Raw numbers: [`results.json`](results.json); per-trade labelled ledger: [`../../programs/E018/data/labelled_ledger.json`](../../programs/E018/data/labelled_ledger.json).
- Harness: [`../../programs/E018/`](../../programs/E018/). Unit tests: 10/10 pass.

---

## Abstract

The deployed `zone_d1_against` alpha fades the D1 bias at fresh supply/demand
zone touches. A single live incident (2026-07-08 → 07-12) suggested the fade
loses when the D1-biased move is a **breakout/extension** and wins on a
**pullback**. E018 pre-registered a **causal, past-bars-only** regime labeller
whose thresholds are **frozen from documented priors** (Chigiri Φ4.1 breakout
constants; the deployed D1-bias parameters; the F18 ADX>25 trend convention) and
asked whether standing aside on the extension regime (R2) improves out-of-sample
risk-adjusted performance. Over 2015–2025 walk-forward OOS (2019–2025 pooled)
across EURUSD/GBPUSD/USDCAD H4, R2-labelled fades show OOS expectancy of
**+0.19 / +16.20 / +2.53 pips** (EURUSD/GBPUSD/USDCAD) — **none significantly
negative** (BH-FDR q = 0.70 / 0.98 / 0.70; one-sided "less"). The pre-registered
requirement that R2 be a **significantly negative** regime fails on 0 of 3
pairs. The 2026-07 incident is a small-sample streak that does not generalise
under a frozen definition. **The fade is left unchanged.**

## 1 Introduction

`zone_d1_against` (SupplyDemandAlpha, `htf_align="D1", htf_align_mode="against",
htf_lookback=10, htf_min_move_pips=60`) is deployed on EURUSD (risk 1.0),
GBPUSD/USDCAD (risk 0.5), H4 (`agent/alphas/zone_routing.py`). It only trades
when the D1 bias **opposes** the zone direction (a counter-trend fade), and
never trades on NEUTRAL D1 (it already stands aside on no-bias/range = R3).

The 2026-07 incident logs show the fade losing on EURUSD/GBPUSD (D1 up, price
extending up — e.g. EURUSD 2026-07-09 01:00 SHORT @1.14212 `htf_bias=up`; GBPUSD
2026-07-08 13:00 SHORT @1.33361 `htf_bias=up`) and winning on USDCAD (D1 down,
pullback into demand — 2026-07-08 09:00 LONG @1.41641 `htf_bias=down`). The
hypothesised discriminator is **pullback (R1) vs extension/breakout (R2)**, not
D1 direction. E018 tests whether that hypothesis survives a frozen,
pre-registered, out-of-sample test.

## 2 Related work / priors reused (frozen, not tuned)

- **Breakout/extension definition** — Φ4.1-locked `CHIGIRI_V1_*`
  (`programs/M001_multi_agent_ensemble/sim/agents/a04_chigiri.py`): 20-bar range,
  Wilder ATR-14, 80-bar vol-median window, breakout magnitude ≥ 0.50·ATR.
- **D1 bias** — the deployed `htf_bias_at(htf="D1", lookback=10, min_move=60p)`,
  reused verbatim (`agent/alphas/concepts/_htf.py`).
- **Trend convention** — F18 ADX>25 = trending
  (`.../sim/regime/classifier.py::label_rule_based`), reported only.
- **Statistics** — bootstrap p-values + BH-FDR α=0.05
  (`agent/backtest/metrics.py`); walk-forward windows from
  `scripts/run_walk_forward.py`; replay via `scripts/run_walk_forward_ab.py`
  (E013 `all_on` production-matching toggles). Overfitting hygiene per
  `bailey2016pbo` / `bailey2014deflated`.

## 3 Methodology

**Labeller (frozen, causal, §2 of PROTOCOL).** At each fade signal bar `i`
(reading only `bars[:i+1]`): if D1 bias is NEUTRAL → R3; else if a vol-expansion
20-bar breakout (magnitude ≥ 0.50·ATR14, ATR14 > 80-bar median) fires **in the
D1-bias direction** → R2 (extension); else → R1 (pullback).

**Replay.** For each pair, the deployed fade is run over 2015–2025 H4
(`_run_alpha_ab`, `all_on`, `start_index=200`). Each closed trade is labelled at
its decision bar (entry-bar-index − 1). Trades are split into 7 walk-forward
windows (4yr-IS / 1yr-OOS); the gate is judged on **pooled OOS 2019–2025**, with
the 2025 window held as a sealed final read and 2015–2018 reported descriptively.

**Arms & cells.** baseline (all fades) vs R2-filtered (drop R2). FDR family =
6 cells {pair}×{R1,R2}; R2 tested one-sided "less" (negative), R1 "greater". ≥30
OOS trades/cell floor. n_resamples=2000, seed=42.

**Gate (pre-registered §5).** `alive` requires **all** of: (1) R2 significantly
**negative** OOS (q≤0.05, n≥30); (2) robust across ≥2 pairs with no contradicting
significant-positive R2; (3) R2-filter improves R1 survivors' OOS risk-adjusted
performance without destroying sample. Otherwise `dead`/STOP.

## 4 Results

### 4.1 Regime counts (full 2015–2025)

| Pair | Total | R1 (pullback) | R2 (extension) | R3 (neutral) |
|---|---|---|---|---|
| EURUSD | 737 | 679 | 58 | 0 |
| GBPUSD | 944 | 871 | 73 | 0 |
| USDCAD | 707 | 661 | 46 | 0 |

R2 is a sparse regime (~6–8% of fades). R3 = 0 by construction (the fade never
fires on NEUTRAL D1 — the agent already stands aside there).

### 4.2 Regime-conditional OOS expectancy (pooled 2019–2025) — the gate

| Cell | n | exp (pips) | median | hit | p (1-sided) | q (BH) | reject? |
|---|---|---|---|---|---|---|---|
| EURUSD/R1 | 375 | **+17.13** | +20.29 | 60.0% | 0.0005 (greater) | 0.001 | ✅ edge |
| EURUSD/R2 | 35 | **+0.19** | −11.98 | 45.7% | 0.47 (less) | 0.70 | ❌ |
| GBPUSD/R1 | 480 | **+19.56** | +24.99 | 56.7% | 0.0005 (greater) | 0.001 | ✅ edge |
| GBPUSD/R2 | 37 | **+16.20** | +34.53 | 62.2% | 0.98 (less) | 0.98 | ❌ |
| USDCAD/R1 | 361 | **+18.18** | +20.03 | 56.8% | 0.0005 (greater) | 0.001 | ✅ edge |
| USDCAD/R2 | 28† | **+2.53** | −11.96 | 42.9% | 0.58 (less) | 0.70 | ❌ |

† USDCAD/R2 is **underpowered** (n=28 < 30 floor).

**R2 is not significantly negative on any pair** (0/3). GBPUSD/R2 is clearly
*positive*. EURUSD/R2 and USDCAD/R2 have negative medians and sub-50% hit rates
but their **means are not significantly negative** — a handful of large winners
offset the frequent small losers, so on an expectancy (P&L) basis R2 is not a
losing bucket. **Gate condition 1 fails → `dead`.**

### 4.3 R2 per-window robustness (sign of OOS expectancy)

R2 expectancy sign flips window-to-window with no consistent negativity:
GBPUSD/R2 is positive in **6/7** OOS years; USDCAD/R2 in 4/7; EURUSD/R2 in 4/7.
Per-window n is tiny (1–10), consistent with noise, not a stable regime effect.

### 4.4 Baseline vs R2-filtered (pooled OOS)

| Pair | arm | n | exp (pips) | exp CI | PF | Sharpe |
|---|---|---|---|---|---|---|
| ALL | baseline | 1316 | +17.52 | [13.2, 20.5] | 1.96 | 4.67 |
| ALL | R2-filtered | 1216 | +18.40 | [14.0, 21.6] | 1.99 | 4.78 |

Dropping R2 nudges pooled expectancy +0.88 pips and Sharpe +0.11 — but the
CIs **overlap heavily** and the improvement is a trivial arithmetic consequence
of removing ~break-even trades from a higher-mean pool, **not** evidence that R2
is a losing regime. The pre-registered gate deliberately requires R2 to be
*significantly negative* (4.2) precisely so this kind of noise-level "improvement"
cannot justify a live change. It does not.

### 4.5 Descriptive bands

- **IS 2015–2018 R2 expectancy:** EURUSD +10.88 (n=23), GBPUSD +7.13 (n=36),
  USDCAD −8.12 (n=18). Mixed, not systematically negative.
- **Sealed 2025 OOS R2:** n = 2/2/3 (EURUSD −31.3, GBPUSD +43.1, USDCAD +11.8) —
  far too few to conclude anything; consistent with noise.

## 5 Discussion

The frozen, prior-derived "fade into an aligned vol-expansion breakout" label
(R2) does **not** isolate a negative-expectancy subset of the fade out-of-sample.
The fade's edge lives overwhelmingly in R1 (all three R1 cells are BH-significant
at q=0.001, +17 to +20 pips), but R2 is not its mirror-image loser — it is
break-even to positive. The 2026-07 incident (a handful of extension-short
losses) is therefore best read as a **small-sample streak**, not a generalisable
regime signature detectable by this frozen definition.

There is a *nuance worth flagging for a future, separately pre-registered study*
(NOT a reason to ship now): EURUSD/R2 and USDCAD/R2 have **negative medians and
sub-50% hit rates** despite non-negative means. A hit-rate- or median-based
filter, or a different (stricter/looser) breakout definition, might behave
differently — but choosing any such variant *now*, having seen these results,
would be exactly the post-hoc, incident-driven tuning the protocol forbids.
Anyone pursuing it must pre-register the new definition and open a fresh FDR
family. The strict-specialist ratios (1.5/1.5) are recorded per-trade in the
ledger for that future work.

**Limitations.** Costs are TF/pair-invariant in the config (the R1-vs-R2
contrast is within-pair, so this does not bias the comparison, but absolute
expectancies are not the deployed cross-pair-scaled numbers). R2 is sparse
(~6–8%), so per-window and sealed-window cells are underpowered by design; the
pooled OOS is the powered read and it is unambiguous.

## 6 Conclusion

Stage-1 verdict: **`dead`**. R2 is not a fade-hostile negative-expectancy regime
out-of-sample; the go/no-go gate is not met. **Live code is unchanged.** A clean
negative that leaves the validated fade intact is the correct outcome. See
[`STOP_NOTICE.md`](STOP_NOTICE.md).

## References

Chigiri Φ4.1 breakout constants (`a04_chigiri.py`); F18 ADX convention
(`sim/regime/classifier.py`); `bailey2016pbo`, `bailey2014deflated` (overfitting
hygiene); walk-forward + BH-FDR machinery (`agent/backtest/metrics.py`,
`scripts/run_walk_forward.py`, `scripts/run_walk_forward_ab.py`).
