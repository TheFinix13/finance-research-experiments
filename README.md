# confluence-lab

> **Test A is complete — see `REPORT.md`** for the full research report
> (methods, the session-volatility confound and amendment v2.1, results,
> limitations). Headline: 5/284 cells survived the hour-matched screen;
> M15 `trendline_liquidity_sweep_low` confirmed on the frozen 2022-24
> split, M15 `channel_top_touch` replicated on frozen GBPUSD. Protocol:
> `PROTOCOL.md` (v2 + amendment). The v1 pooled band-density experiment
> below is retained as the recorded baseline: H0 not rejected (EURUSD H4,
> p=0.23, no source survived FDR).

A standalone research experiment. **Observation-only by construction**: no
broker code, no order placement, no imports into the live trading agent.
It borrows perception concepts from `eurusd-ai-agent` (optional adapter)
but its results have zero authority over that system until they pass that
system's own validation pipeline.

## Research question (pre-registered)

> Do high-confluence price bands — where two or more independent technical
> levels from one or more timeframes overlap — produce measurably stronger
> price reactions than (a) random price levels and (b) low-confluence
> single-source levels?

**H0:** reaction strength at high-confluence bands is indistinguishable from
matched random levels.
**H1:** reaction strength increases with confluence density.

If H0 survives, confluence is storytelling and we say so. If H1 wins after
multiplicity correction, confluence density graduates to a *candidate*
gate/exit input for the main agent — via that repo's full pipeline only.

## Protocol (fixed before looking at results)

1. **Level extraction** per timeframe (D1/H4/H1), causal (bars up to t only):
   swings, double-top/bottom levels + necklines, S/R polarity flips,
   Bollinger/Donchian/Keltner bands, EMA(50/200), VWAP, plus (via the
   main-repo adapter) supply/demand zone edges, trendline projections,
   fib levels, PDH/PDL/PWH/PWL.
2. **Clustering**: all levels projected onto one price axis, greedy-clustered
   within an ATR-scaled tolerance into bands. Density score counts members,
   distinct sources and distinct timeframes.
3. **Touch + reaction measurement**: a touch is the first bar entering a band
   from outside; reaction is the maximum ATR-normalised excursion *against*
   the approach direction within a fixed horizon (default 12 bars), plus a
   binary "held" flag.
4. **Null model**: at every rebuild step, the same number of uniform-random
   levels is generated inside the recent price range and scored by the
   *identical* touch/reaction code. Bands and controls are never compared
   through different code paths.
5. **Analysis**: Spearman correlation of density vs reaction; permutation
   test (high-density bands vs controls); per-source ablation table.
   Multiple-testing correction (Benjamini-Hochberg) across all source
   combinations examined.
6. **Walk-forward only**: levels are rebuilt every `stride` bars from history
   alone; touches are scored strictly forward. No leakage by design.

## Anti-fooling rules

- Indicator/pattern parameters are defaults fixed in code, not tuned to make
  the answer come out "interesting".
- Every combination tested is counted toward the FDR correction.
- Candle patterns are *event tags* at touches, not levels (they have no
  persistent price, so treating them as levels would inflate density).
- FX tick volume is a weak proxy — volume-based tags are labelled as such.
  This is NOT institutional order flow.

## Layout

| Path | What |
|---|---|
| `conflab/indicators.py` | Classic TA suite (pure pandas, no TA-Lib) |
| `conflab/patterns.py` | Double tops/bottoms, S/R flips, candle events |
| `conflab/levels.py` | Level extraction + optional main-repo adapter |
| `conflab/confluence.py` | Cross-TF clustering into scored bands |
| `conflab/reaction.py` | Touch detection + ATR-normalised reaction metric |
| `conflab/experiment.py` | Walk-forward harness, null model, analysis |
| `conflab/render.py` | Annotated mplfinance charts |
| `scripts/scan.py` | Visual scanner: charts + bands JSONL for a symbol |
| `scripts/run_experiment.py` | Runs the H0/H1 test on historical data |

## Running

Uses the main repo's venv and parquet cache (no separate environment):

```bash
cd /Users/the1finix/Documents/GitHub/confluence-lab
export PYTHONPATH=/Users/the1finix/Documents/GitHub/eurusd-ai-agent:.

# visual scan (today's confluence map)
../eurusd-ai-agent/.venv/bin/python scripts/scan.py --symbol EURUSD

# the experiment
../eurusd-ai-agent/.venv/bin/python scripts/run_experiment.py --symbol EURUSD --tf H4

# tests
../eurusd-ai-agent/.venv/bin/python -m pytest tests/ -q
```
