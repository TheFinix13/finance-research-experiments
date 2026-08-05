# Barou v1.x USDJPY loss autopsy — FINDINGS

**Date:** 2026-08-05
**Source data:** AN-5 single-agent isolation tapes, `barou_shoei` on USDJPY H4,
`phase_an_field_followups/results/AN-5/USDJPY/design/start_0..4/trades.jsonl`
(start dates 2015-01-01 / 04-01 / 07-01 / 10-01 / 2016-01-01, burn-in 92 days,
1.0 pip honest cost subtracted per trade, r recomputed as
`(pnl_pips − 1.0) / source_sl_pips`).
**Script:** `autopsy_barou_usdjpy.py` → `results.json` (full numbers), `run_log.txt`.

> **HONESTY BANNER — EVERY NUMBER BELOW IS IN-SAMPLE.** This is the DESIGN
> split, already consumed by AN-5. It is legitimate for *designing* the v1.x
> patch and for nothing else. No claim here survives until replayed on sealed
> data. Additionally the five staggered starts share most of their 2015–2022
> trade population (n=379–441 each, heavily overlapping windows of one price
> path), so "stable in 5/5 starts" is much weaker evidence than five
> independent confirmations — treat it as one path, five reads.

## Baseline reproduction (1× cost, post burn-in)

| start | n | PF | mean R | win rate |
|---|---|---|---|---|
| start_0 | 441 | 1.113 | +0.095 | 43.3% |
| start_1 | 426 | 1.138 | +0.105 | 43.7% |
| start_2 | 418 | 1.115 | +0.098 | 43.5% |
| start_3 | 399 | 1.138 | +0.120 | 44.4% |
| start_4 | 379 | 1.161 | +0.123 | 44.3% |

Median PF **1.138** — matches the AN-5 near-miss verdict exactly.

## 1. Loss anatomy (start_0 primary; other starts agree)

- The r distribution is **strictly bimodal**: p25 = −1.015, p50 = −1.007,
  p75 = +1.483. Every trade either rides to the full stop (−1R) or to the
  fixed 1.5R take-profit. **99.6% of losers are full-stop exits**; exit
  reasons are `sl` (249), `tp` (191), `end_of_data` (1). Barou has **zero
  trade management** — no breakeven, no trail, no time stop.
- **Losers show substantial favourable excursion first**: mean loser MFE =
  0.52× stop distance; **44% of losers reached ≥0.5R in profit** and
  **15.6% reached ≥1.0R** before reversing to the full stop. Stable in 5/5
  starts (0.5R share 44–46%, 1.0R share 15.6–17.1%).
- Data notes: `bars_held` is 0 on every trade (unpopulated in these tapes —
  the bars-held slice is uninformative); `source_conviction` is degenerate
  (0.75 on all trades — no slice possible); `source_regime_fit` is a
  near-perfect monotone transform of `source_atr_pips` (Spearman **0.993**
  on start_0), so the regime-fit and ATR quartile slices are the *same*
  slice and must not be counted as independent evidence.

## 2. Slice screen

26 single-value drop-filters screened across 8 slice families (session,
day-of-week, regime-fit/ATR quartile, conviction quartile, stop/ATR quartile,
direction, bars-held bucket). 9 passed the charter gate (pooled PF > 1.15,
median n ≥ 60/start, mean R ≥ +0.05) — full table in `results.json
→ candidate_filters`. With 26 screens on overlapping starts, several passes
are expected by pure chance; only candidates with a monotone dose-response
or a real market mechanism were promoted below. Notable rejects:

- **drop Tuesday / drop Thursday** — pass numerically (pooled PF 1.206 /
  1.192, 5/5) but day-of-week has no mechanism for an H4 swing weapon;
  classic multiple-comparisons bait. Rejected.
- **drop shorts** — pooled PF 1.176, 5/5, but USDJPY 2015–2022 is one long
  carry/uptrend regime; this is a regime bet, not a weapon fix. Rejected.
- **regime-fit quartile drops** — duplicates of the ATR slice (ρ=0.993),
  non-monotone across quartiles. Rejected.

## 3. Top 3 candidate mechanisms

### Candidate A — stop-distance/ATR entry gate (skip if stop > ~2.3× ATR)

Barou's stop is structural (H1 swing), so stop/ATR measures how far entry is
from the protective structure. Bottom-half (tight-relative-stop) trades are
strongly profitable, top-half are dead money: start_0 quartile PFs are
q1 = 1.31, q2 = 1.57, **q3 = 0.81, q4 = 1.05**. Mechanism: a stop several
ATR away means a late/chasing entry far from structure — and with the fixed
1.5R target, the TP is then 4+ ATR away, rarely reached before mean
reversion. Counterfactual, keep only stop ≤ 2.28×ATR (start_0 median):

| start | base PF | cf PF | cf n | cf mean R |
|---|---|---|---|---|
| start_0 | 1.113 | **1.459** | 221 | +0.209 |
| start_1 | 1.138 | **1.477** | 213 | +0.220 |
| start_2 | 1.115 | **1.476** | 210 | +0.216 |
| start_3 | 1.138 | **1.586** | 199 | +0.259 |
| start_4 | 1.161 | **1.507** | 188 | +0.244 |

Pooled PF 1.499, mean R +0.229. Improves 5/5 starts. **Threshold
sensitivity** (results.json → `stop_atr_threshold_sweep`): PF stays ≥ ~1.15
in essentially all starts for every cap from 1.75× to 3.0× ATR (best at
≤2.25: PF 1.60–1.73), so it is not a knife-edge artifact — but the exact
2.28 value is the in-sample median and must be rounded/pre-registered
(e.g. 2.25) before validation. Cost: halves trade count (n≈190–220/start,
still ≫ 60).

### Candidate B — breakeven stop after +1R MFE (exit management)

Every loss currently rides to −1R, yet ~16% of losers were +1R in profit
first (stable 15.6–17.1% across all 5 starts). Converting only those losers
to breakeven exits (winners untouched) gives:

| start | base PF | cf PF | losers converted | cf mean R |
|---|---|---|---|---|
| start_0 | 1.113 | 1.303 | 39 | +0.184 |
| start_1 | 1.138 | 1.325 | 38 | +0.194 |
| start_2 | 1.115 | 1.293 | 37 | +0.186 |
| start_3 | 1.138 | 1.325 | 36 | +0.211 |
| start_4 | 1.161 | 1.369 | 36 | +0.218 |

**This is an OPTIMISTIC UPPER BOUND**, not a true counterfactual: a real BE
stop would also clip some eventual TP winners that touched +1R and then
retraced to entry before running to target. The tapes carry only MAE/MFE,
not path timing, so the winner-side cost is *not computable here* — this
candidate requires a replay to price. Its virtue is mechanistic: it attacks
the single most striking anatomical fact (100% full-stop losses, high loser
MFE) and keeps all 418+ trades/start.

### Candidate C — rollover-session entry block (no entries 19–23 UTC)

Rollover-hour entries lose outright (start_0: PF 0.911, mean R −0.069,
n=59). Mechanism is real: 19–23 UTC is the thinnest liquidity window, spread
widening around the 21–22 UTC rollover, and the honest-cost assumption of
1.0 pip is most likely *understated* exactly there. Counterfactual (drop
rollover entries):

| start | base PF | cf PF | cf n | cf mean R |
|---|---|---|---|---|
| start_0 | 1.113 | 1.149 | 382 | +0.120 |
| start_1 | 1.138 | 1.177 | 368 | +0.130 |
| start_2 | 1.115 | 1.150 | 360 | +0.122 |
| start_3 | 1.138 | 1.180 | 343 | +0.150 |
| start_4 | 1.161 | 1.190 | 326 | +0.144 |

Pooled PF 1.168. Improves 5/5, cheap (removes only ~13% of trades), but the
margin over the 1.15 floor is thin (two starts land at 1.149/1.150) — on
sealed data this could easily land below the floor.

## 4. Ranking and recommendation

| rank | mechanism | stability | plausibility | margin over 1.15 |
|---|---|---|---|---|
| 1 | A: stop/ATR ≤ 2.25 entry gate | 5/5, monotone dose-response, robust 1.75–3.0× | good (entry-from-structure distance) | large (+0.31–0.44 PF) |
| 2 | B: breakeven at +1R MFE | 5/5 on loss side | strongest (fixes literal absence of management) | unknown (upper bound +0.15–0.19; true value needs replay) |
| 3 | C: block rollover entries (19–23 UTC) | 5/5 | good (liquidity/spread) | thin (~0.00–0.03) |

**Recommended single mechanism for the v1.x patch: Candidate A — reject
entries whose structural stop exceeds 2.25× current ATR.** It is an
entry-time-computable rule (all inputs known at signal time), has the only
large margin over the floor, shows a monotone dose-response across the
stop/ATR range rather than a lone lucky bucket, and survives a threshold
sweep. Pre-register the rounded 2.25 threshold before touching sealed data.
Candidate B is the best fallback if halving trade count is unacceptable to
the charter, but it cannot be priced from these tapes and needs a replay.

## Multiple-comparisons caveat (read before chartering)

We screened ~26 filters plus 2 engineered follow-ups on a design split that
AN-5 has already consumed, and the 5 "independent" starts are overlapping
windows of one 2015–2022 USDJPY path. Under this regime, a candidate that
*barely* clears 1.15 (Candidate C, and the Tuesday/Thursday rejects) is more
likely noise than signal. Candidate A's margin (+0.31 PF pooled) is large
enough to be interesting *if* the mechanism is real, but the honest prior is
that its effect will shrink materially out-of-sample — the design-split PF of
~1.5 should be treated as an upper bound, not a forecast. The patch verdict
belongs to the sealed-data replay, not to this autopsy.
