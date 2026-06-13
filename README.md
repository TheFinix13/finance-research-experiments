# Trading AI Confluence Experiment

A small research project I built alongside my main trading agent to answer
one question honestly.

## The question

> Traders constantly talk about "confluence" — the idea that price reacts
> more strongly where several different signals line up at the same level.
> Is that actually true on EUR/USD and GBP/USD, or is it just a story
> told after the fact?

## How I tried to answer it

I picked a long list of patterns and levels that traders care about —
support and demand zones, trendlines, channels, double tops/bottoms,
head & shoulders, fibonacci levels, fair-value gaps, liquidity sweeps,
candlestick patterns and a few others — and turned each into a rule that
a computer can spot on a chart.

Then, on seven years of historical price data, I asked: when one of these
events happens, does the next few hours move more in the expected
direction than at a random moment in time? I split the data into a
**screen** half (used to look for promising signals) and a **confirm**
half (kept hidden until the screen was finished, used to test whether the
signals still worked on fresh data). I also re-ran the whole thing on
GBP/USD as an independent check.

Statistical multiplicity, time-of-day biases, and the temptation to
re-tune things after seeing results are all genuine traps, so the rules
of the experiment were written down **before** I looked at any results.

## What I found

A short version (the full write-up with charts and numbers is in
[`REPORT.md`](REPORT.md)):

- Out of the patterns I tested, **a handful look genuinely informative**,
  but the effects are modest — useful as one input among many, not as a
  standalone strategy.
- The most interesting two: **a wick below a rising trendline that closes
  back above** (a swept support trendline) and **the first touch of the
  upper edge of a parallel channel** — both held up in out-of-sample
  tests.
- Everything else either failed to beat random timing, or didn't appear
  often enough in seven years to be sure either way.

Nothing here trades real money. The lab is observation-only by design,
and any finding can only influence my main trading agent after going
through that agent's separate, stricter validation pipeline.

## Repo guide

- [`REPORT.md`](REPORT.md) — the research report (methods, results,
  limitations, what I'd do next).
- [`PROTOCOL.md`](PROTOCOL.md) — the rules of the experiment, written
  before any results existed.
- [`conflab/`](conflab/) — the code.
- [`output/`](output/) — the actual data the report is based on
  (registries, logs, the summary figure).
