# E035 — Is the news reaction itself tradable? (M5/M15)

Status: **DRAFT, not yet pre-registered, and GATED.** This study does
not open unless E034 returns `characterised_tradable_candidate`. It is
drafted now only so the gate criteria are fixed *before* E034's numbers
are seen — writing E035 after reading E034 would let the result choose
the test.

Follows `PROTOCOL_DISCIPLINE.md` in full.

---

## 0. What makes this a different study, not an E033 window change

E033 asked whether the deployed H4 fade cell should stand aside for
news. E035 asks whether a **different strategy, on a different
timeframe, with a different holding period** can trade the reaction.
The only thing the two share is the calendar.

This distinction is not bookkeeping. The fade cell enters at zone edges
and holds for many hours; a news-reaction strategy enters within
minutes of a release and holds for tens of minutes. They have different
entry logic, different stop geometry, different cost sensitivity and
different capacity. **Nothing E033 learned transfers, in either
direction**, and no E033 arm may be reused, rescored or cited as
support here.

## 1. Why not H1 — the resolution question, answered with arithmetic

The obvious move from H4 is H1, and it is the wrong one. H1 is the
worst of both worlds.

**Too coarse to measure.** A one-hour bar swallows the entire ±30-minute
reaction into a single candle. The net move survives; the spike, the
excursion and the path — the parts that decide whether a stop is hit —
do not. E034 uses M5 for exactly this reason.

**Too slow to generate sample.** Bar counts on the cached EURUSD
history are H4 20,488 / H1 71,484 / M15 284,277 / M5 822,437. Even
granting the generous assumption that trade arrival scales linearly
with bars — it does not, because zones are structural objects whose
count grows sublinearly with resolution, and an open position blocks
new entries — H1's 3.5× lifts a 573-trade book to roughly 2,000 trades
and about 22 touches at ±30 min. That is still under the n=30 floor,
and it is a ceiling rather than an estimate.

M15 (13.9×) and M5 (40×) are the resolutions that clear the floor with
room to spare. **This study therefore uses M5 for entry timing and M15
for context, and does not use H1 at all.**

## 2. Hypothesis (operational)

A rule that enters in the minutes after a scheduled release, in the
direction indicated by the initial reaction, with a volatility-scaled
stop and a fixed time exit, produces positive expectancy net of a
stressed cost assumption.

## 3. Locked design

**Population.** EURUSD M5 2015-01-01 → 2025-12-31, the same frozen
349-event calendar as E033/E034.

**Entry.** At t₀ + k minutes for k ∈ {5, 10, 15}, in the direction of
the [0, +k] return, if |[0, +k] return| exceeds the pre-window ATR by
a factor f ∈ {1.0, 1.5, 2.0}. Nine (k, f) cells, locked.

**Stop.** ATR-normalised, measured on the [−60, −5] pre-window, at
multiples {1.0, 1.5} — pooled into the cell grid, not tuned per cell.

**Exit.** Time exit at t₀ + 60 min. **No trailing, no partials, no
discretionary management** — every one of those is a knob, and a
nine-cell grid with knobs is a fishing expedition.

**Costs — mandatory, and the reason this study can fail on its own
terms.** E034 cannot measure spread (OHLCV only), so E035 must not
assume it away. Every cell is scored at three cost levels: base spread,
5× base, and 10× base through the window, with the multiplier applied
for [0, +30] and base thereafter. **A cell is only alive if it clears
at 5×.** A strategy that needs a tight spread through NFP is not a
strategy, it is a data artefact.

## 4. Data-ledger constraint inherited from E034

E034's descriptive pass looks at EURUSD M5 across the full span. That
is recorded in `DATA_LEDGER.md` as a look, and it binds here:
**EURUSD M5 may not serve as E035's confirm population.**

EURUSD M15 cannot substitute. Its screen slice is consumed by five
registered experiments, its confirm slice by three, and its sealed
slice is marked **CONSUMED** by E029 — there is no pristine EURUSD M15
real estate left, and the `DATA_LEDGER.md` overuse warning already
flags this pair as the most heavily mined in the lab.

So confirmation requires a **different pair**, and the cache does not
currently hold one at this resolution: GBPUSD M15/H1 stop at
2021-12-31, and there is no GBPUSD or USDCAD M5 cached at all.

**Therefore caching GBPUSD M5 (or USDCAD M5) 2015 → 2025 is a hard
prerequisite of E035, not an optimisation.** If that data cannot be
obtained, E035 runs as screen-only on EURUSD M5 and **cannot produce a
promotable verdict** — its best possible outcome becomes
`screen_only_unconfirmable`. That limit is stated here, at draft time,
so it cannot be discovered late and negotiated away.

## 5. Stop rules

- Does not open at all unless E034 returns
  `characterised_tradable_candidate` (§6 of E034).
- Stage 0 engagement floor: a cell touching < 30 events is
  `underpowered` and excluded from its family.
- If 0/9 cells clear at the 5× cost level after BH (α = 0.10),
  **STOP**. No grid extension, no new k or f values, no new event
  types, no relaxing the cost stress.
- If the confirm population is unavailable per §4, the verdict caps at
  `screen_only_unconfirmable` regardless of screen strength.

## 6. Verdict labels (locked)

- **`alive`** — clears BH at the 5× cost level on screen AND replicates
  on the confirm pair. Authorises design work only; any live wiring is
  a separate review.
- **`parked_cost_fragile`** — clears at base cost, fails at 5×.
  Explicitly not deployable; recorded so the idea is not retried.
- **`screen_only_unconfirmable`** — clears on screen but §4's confirm
  population does not exist. Not promotable.
- **`dead`** — nothing clears. The "news is tradable" thread closes
  with evidence, at the resolution where it actually could have been
  true.

## 7. Amendments

(Empty at draft.)

---

## Cross-references

- `experiments/E034_news_price_process/PROTOCOL.md` — the gate.
- `experiments/E033_scheduled_news_blackout/` — STOPPED-DEAD; separate
  estimand, not to be reused here.
- `DATA_LEDGER.md` — EURUSD overuse warning and the M15 exhaustion
  that forces §4.
