# E034 — Scheduled-news price-process characterisation (EURUSD M5)

Status: **DRAFT, not yet pre-registered.** Awaiting user sign-off; the
pre-registration commit locks §3–§6 and must land before any number in
§4 is computed.

Follows `PROTOCOL_DISCIPLINE.md` in full. Register a `planned` row in
`EXPERIMENTS.md` at the pre-registration commit; add the
`DATA_LEDGER.md` row when Stage 1 starts.

---

## 0. Why this study exists (and why it is not E033 reopened)

E033 asked whether suppressing trades near scheduled news improves the
deployed H4 fade cell, and stopped dead: 0/30 cells alive, with touched
fills coming back net winners. That question is closed and this study
does not reopen it. **E033 is STOPPED-DEAD and no arm, window or cell
of it may be rescored here** — doing so would be exactly the post-freeze
refitting `PROTOCOL_DISCIPLINE.md` §5 forbids.

What E033 could not answer is a different question, and the reason is
arithmetic rather than evidence. Measured on EURUSD M5 against the same
frozen 349-event calendar, the share of tradable time each window
occupies is:

| Window | Share of tradable clock | Expected touches @ 573 trades | E033 observed |
|---|---|---|---|
| ±30 min | 0.55% | 3.2 | 7 |
| ±60 min | 1.06% | 6.1 | 8 |
| ±120 min | 2.08% | 11.9 | 15 |
| ±240 min | 4.09% | 23.4 | 21 |
| ±12 h | 11.27% | 64.6 | 81 |

Engagement is explained almost entirely by how much of the calendar each
window covers, running 1.1–2.2× above random arrival because zone
touches do cluster mildly toward volatility. A book taking roughly one
trade a week cannot place many entries inside a window that is half a
percent of the clock. **The thinness is structural, not a data defect,
and no amount of extra history fixes it.**

The two available levers are widening the window and raising the trade
arrival rate. Widening is already spent: `event_day` reached n=81 and
died on all three symbols with tight intervals, and it contains every
tighter window. So the strategy-conditional question is answered at the
only resolution where it can be asked.

This study therefore changes the estimand rather than the window. "Does
news move price?" is a property of the **price process**, needs no
strategy and no trades, and is measurable on all 349 events at n=349.
It has no power problem at all.

**Stated up front so it cannot be claimed as a discovery later:** the
expected result is that news moves price hard. That is fully compatible
with E033. Violence is not damage — a fade entering at a zone edge with
a structure-sized stop can have a violent move resolve for it as easily
as against it, which is what the 7/7 at +1.50R already hints. This study
is run to *size* through events and to gate E035, **not** to relitigate
the blackout.

## 1. Hypothesis (operational)

H1 (dispersion). Realised volatility in [t₀, t₀+30 min] around a
scheduled USD NFP / CPI / FOMC release exceeds the matched-control
baseline by a ratio whose 95% CI lower bound is > 1.0.

H2 (excursion). The probability that an open position experiences an
adverse excursion exceeding a stop of width S within [t₀, t₀+30 min] is
higher on event windows than on matched controls, for every S in the
locked grid.

H3 (persistence, directional). The sign of the first 5-minute return
after t₀ carries information about the cumulative return over the
following 30 and 60 minutes.

H1 and H2 are about violence. **H3 is the only one about
tradability**, and it is the gate to E035.

## 2. Separation

Descriptive characterisation of the price process. It computes **no
strategy outcomes, no R sequences and no Sharpe**, proposes no rule,
and produces no promotable claim. Nothing here may be wired to v1 or
v2 on its own; its only downstream uses are (a) supplying the
excursion number to a future size-down design and (b) opening or
closing the E035 gate.

## 3. Locked parameters

**Instrument.** EURUSD M5, `data/parquet/EURUSD_M5.parquet` from the v1
agent cache (read-only). 852,437 bars, 2015-01-01 → 2026-05-26; the
study window is clipped to 2015-01-01 → 2025-12-31 to match the frozen
calendar exactly (822,437 bars).

**Events.** The Phase AE frozen fixture already vendored at
`programs/E033/data/news_calendar_frozen_2026-07-24.json`, sha256
`cfd186021ea87a5a…`, 349 USD events of types Employment Situation
(NFP), Consumer Price Index, FOMC Statement (scheduled). Re-vendored
read-only; **the calendar is not extended, re-scraped or re-typed** —
using the identical fixture is what keeps E034 commensurable with E033.

**Matched controls — the design's load-bearing element.** NFP and CPI
release at 13:30 UTC, which is already the most volatile hour of the FX
day because of the London/New York overlap; FOMC at 19:00 UTC sits in
a different regime again. Comparing an event window to an all-hours
average would attribute the session effect to news and manufacture a
large fake result. Each event therefore pairs with controls drawn from
**the same weekday and the same clock minute** on non-event weeks
within ±26 weeks, excluding any date within ±1 trading day of any
calendar event, and excluding the 2015-01-15 CHF de-peg week. Target
20 controls per event; an event with < 8 usable controls is dropped and
the count reported.

**Horizons (locked).** [−60, −5], [0, +5], [0, +30], [0, +60],
[0, +240] minutes relative to t₀. No other horizon may be reported.

**Stop grid for H2 (locked).** S ∈ {10, 15, 20, 30, 45, 60} pips,
spanning the deployed fade cell's observed SL distribution. Frozen
before any excursion is computed.

## 4. Metrics (locked; no substitution, no addition)

Primary, each reported as an event-vs-control ratio with a
bootstrap 95% CI over events (5,000 resamples, seed 42):

1. **RV ratio** — sum of squared 5-min log returns in the window,
   divided by the median of the event's own matched controls. Primary
   horizon [0, +30]; other horizons secondary.
2. **Range ratio** — (high − low) over the window, same normalisation.
3. **Excursion probability** — for each S in the grid, the fraction of
   events whose adverse excursion from the t₀ price exceeds S, against
   the same fraction over controls. Reported for both directions
   separately, since a long and a short do not face the same tail.
4. **Jump count** — 5-min bars with |log return| > 4× the trailing
   20-bar σ measured on the pre-window [−60, −5].
5. **Persistence (H3)** — Spearman correlation between the [0, +5]
   return and the [+5, +30] and [+5, +60] returns, with CI. Reported
   separately per event type.

Secondaries (context, never promotable): per-event-type breakdown
(NFP / CPI / FOMC), per-year stability of the RV ratio, control-count
distribution, and the pre-window [−60, −5] ratio as a placebo — a
large pre-window effect would indicate leakage or contaminated
controls rather than a news reaction.

**FDR.** Five primaries, BH at α = 0.10 across the family. The stop
grid within metric 3 is one family of six at BH α = 0.10, reported
separately.

## 5. What this study cannot measure

The cached parquet is **OHLCV only — there is no spread or tick data**.
So E034 can establish how far and how fast price moves, and cannot
establish what it costs to trade through. Retail FX spreads routinely
widen several-fold around NFP, and that cost is usually what kills news
strategies.

Every violence result here is therefore an **upper bound on
tradability**, and must be reported as one. Any statement of the form
"this is exploitable" is out of scope for E034 by construction, and
E035 inherits a mandatory cost-stress because of it (§6).

## 6. Stop rules and the E035 gate

- If H1's RV-ratio CI lower bound ≤ 1.0 at [0, +30], the premise fails
  and the study reports that null. E035 does not open.
- If < 200 of the 349 events survive the control-matching requirement,
  the study is `underpowered`; report the matching diagnostics and
  stop rather than loosening the matching rule to recover events.
  **Loosening the control definition after seeing the matching yield
  is the specific failure this clause exists to prevent.**
- **E035 opens only if BOTH:** H1 survives (violence is real) AND H3
  shows a persistence correlation whose CI excludes zero on at least
  one event type after BH. Violence alone does not authorise a
  tradability study — "large and unpredictable" is the most common
  finding in this literature and is a reason to size down, not to
  trade.

## 7. Verdict labels (locked)

- **`characterised`** — H1 and H2 survive BH; effect sizes and the
  excursion table are banked as inputs to a future size-down design
  (which needs its own pre-registration).
- **`characterised_tradable_candidate`** — as above, and H3 also
  survives. Opens E035, nothing more.
- **`null`** — H1's CI includes 1.0. News does not measurably move
  this instrument at this resolution; the news thread closes for good.
- **`underpowered`** — control matching failed per §6.

## 8. Amendments

(Empty at draft. Any change follows `PROTOCOL_DISCIPLINE.md` §5 —
dated subsection, rationale, committed before the amended analysis
runs. No silent edits.)

---

## Data-ledger declaration

EURUSD **M5 2015-01-01 → 2025-12-31**, descriptive pass.

This overlaps the `M5 2015-01-01 → 2021-12-31 screen` slice already
consumed by E001, and extends into the currently-fresh 2022+ region
that `DATA_LEDGER.md` flags as a good candidate for new hypotheses.

Declared honestly: E034 computes no strategy outcome, so it does not
consume a screen or confirm slice in the usual sense. **It is still a
look.** A descriptive pass that later informs a strategy design is a
form of look-ahead, and pretending otherwise is how a lab quietly
burns its own out-of-sample. The consequence is recorded here and
binds E035: **E035 may not use EURUSD M5 as its confirm population.**

## Cross-references

- `experiments/E033_scheduled_news_blackout/` — the closed
  strategy-conditional study. STOPPED-DEAD; not to be rescored.
- Phase AD.2 (M001) — squad news-gate prior, gated trades net winners.
- Phase AE (M001) — Sae event-specialist FAIL; "avoidable, not
  tradable" reading of the hour-13 bleed.
