# E026 Gate 2 — data (provider, cost, coverage, survivorship)

Status: **AMENDED after Claude Gate-2 review (7 amendments) — still NO
bulk pull until Claude's one-line accept of these edits.** Author: Cursor,
2026-10-27 (amendments same day). Market analysis, not personal investment
advice.

**Spend:** Fiyin approved **one month of Massive Starter ($29)** in chat
2026-10-27 ~16:00 — "pay for the month, as long as we get good results."
Interpreted with A6: buy one month, run the 20-name delisted coverage
check, cancel and stop if coverage fails. "Good results" = honest
measurement, not a forced pass.

Honors Gate 1 amendments + Claude's Gate 2 amendments A1–A7
(`02_data_claude_review.md`).

## 0. Identity check (Claude's demand item C — numbering collision)

The agent repo has a stale local branch `e026-low-mfe-time-stop` (tip
1c90cd6, July 2026 docs/fix commits, **no experiment artifacts**; the
low-MFE time-stop study was never registered in the lab — the lab also has
no E022/E023 folders, those numbers were simply skipped). **Recommendation:
keep lab E026 = ORB** (folders + accepted Gate 1 already exist under this
id); if the low-MFE time-stop idea is ever pre-registered it takes a fresh
number (E034+). No renumbering. Claude to confirm.

## 1. Amended hypothesis (A1 applied — hypothesis split from pass line)

- **H0:** after realistic costs, the Rule-A ORB portfolio's net annualised
  Sharpe is ≤ 0.
- **H1:** it is > 0.
- The **pass line** (lower 95% bootstrap bound > 0 on the held-out span AND
  positive in both halves) lives in Gate 5 only, so changing the decision
  rule never edits the hypothesis.

## 2. The only true holdout is 2024 → latest (A2)

The paper (SSRN 4729284) selected its rule on 2016–2023. Any result inside
that span — even on our own independent pull — is **in-sample with respect
to rule selection**. Therefore:

| Span | Role | Approx. trading days |
|---|---|---|
| 2016-01-04 → 2023-12-29 | Paper's selection window. Used only to CHECK our implementation reproduces the paper's published tables (Gate 4 compatibility), never as evidence. | ~2,010 |
| 2024-01-02 → 2026-10-24 | **The one genuinely held-out span. Spent ONCE, at Gate 5.** | ~710 |

**Power (Claude Gate-2 A1 — corrected).** The SE of an annualised Sharpe
over T days is ≈ √((1 + SR²/2) × 252 / T). With T ≈ 710 that is ~0.60 at
SR=0 and ~0.73 at SR=1. A true Sharpe of 1 has expected t ≈ 1.4 (< 1.96),
so **the holdout alone usually cannot separate Sharpe 1 from 0**. Rewrite
of the claim: the holdout can confirm a true net Sharpe of roughly **1.6+
with ~80% power**; it cannot confirm 0.5–1. The paper claims Sharpe > 2, so
the test is meaningful for the claimed size and silent below it. Gate 5
reports the interval and the **minimum detectable Sharpe**, not only the
point estimate. A "fail" is therefore weak evidence against a moderate
edge; a "pass" must clear a high bar. Stated before any data opens.

**Forward set (Claude Gate-2 A2).** Fix the pre-registration clock at the
date of Gate 5's acceptance. Data AFTER that date is a second, growing
forward holdout nobody on the team has seen. The 2024→Oct-2026 span is
held out from the *rule's selection* but not from the paper's early-2024
publication — expect post-publication decay (McLean & Pontiff 2016) and
name it as a likely explanation of a weaker result, not as a flaw.

## 3. Equity arm — provider, cost, survivorship (A5)

**Named provider: Massive (formerly Polygon.io; rebranded 2025-10-30,
`api.polygon.io` keys still work).** Verified from their pricing/knowledge
base 2026-10-27:

| Tier | $/mo | Minute-aggregate history | Notes |
|---|---|---|---|
| Basic | $0 | 2 years (EOD timing, 5 calls/min) | Too shallow — would be the "free source that silently covers only 60 days" failure A5 warns about; refused. |
| Starter | $29 | 5 years (rolling → ~2021-11 onward) | Covers the FULL 2024+ holdout + a 2022–2023 implementation-check slice. Flat-file (S3) bulk download included. |
| Developer | $79 | 10 years (rolling → ~2016-11 onward) | Misses Jan–Oct 2016 of the paper window. |
| Advanced | $199 | All history (2003-09-10+), + NBBO quotes | Only tier with quotes → only option for a measured-spread cost model. |

**Survivorship/delistings (decisive, per A5):** Massive keeps delisted
tickers with full history (`active=false`); point-in-time universes come
from `/v3/reference/tickers?market=stocks&date=YYYY-MM-DD`, available at
all history depth on every paid tier. So the "stocks in play" universe
(top-20 by 14-day relative volume) can be built **as of each historical
day, including names that later died** — the recreation is
survivorship-clean by construction. Adjustments: split-adjusted aggregates;
corporate-actions endpoint used to verify around known splits (intraday
day-trades make dividend adjustment immaterial, stated here so it isn't
silently assumed later).

**Purchase (updated):** Fiyin approved **one month of Starter ($29)** in
chat 2026-10-27. Per Claude A6 this is a **coverage-check month**, not an
automatic two-month commitment: buy → verify the 20 named delisted cases
below → only then decide whether to renew. We do NOT re-run the paper's
full 2016–2023 window. Gate 4 check is quantified in §9 A5.

**Cost model for fills (Claude Gate-2 A3):** Starter has no NBBO quotes, so
spreads are modelled. Gate 3 locks all of:

- (a) **Short borrow / locate:** pre-register a borrow-fee assumption
  (quote the paper's own figure if present; otherwise a conservative
  annualised borrow rate stated in Gate 3) AND a "cannot locate → skip
  trade" haircut fraction. Stocks-in-play are exactly where borrow is
  scarce.
- (b) **Fill convention (no look-ahead):** signal = close of the first
  5-minute candle; **fill = next bar's open** (or later), never the signal
  bar's close; stop is checked only on bars AFTER entry.
- (c) **Open-anchored spread:** the 0.5×/1×/2× sensitivity sweep is
  anchored to **opening-minute** spreads (widest of the day), not an
  all-day average. Cost-sweep is sensitivity, **not** extra DSR trials
  (Claude report lens).
- Commissions: quoted from the paper's own tables at Gate 3 (not recalled).
  If the verdict flips sign inside the sweep → cost-fragile (a finding).

**Licensing:** individual, non-professional research use — within the
self-serve terms. 15-minute-delayed data is irrelevant for historical
research.

**Named fallbacks (not selected):** FirstRateData one-time delisted-stock
minute bundles (if subscription churn is unwanted); QuantConnect cloud
(survivorship-bias-free minute data, free tier) — rejected as primary
because the ~2.4-Sharpe recreation we must not anchor on was built there,
and Gate 1 requires our implementation to be independent of it.

## 4. Forex arm (exploratory twin) — existing cache only

Per `DATA_LEDGER.md` (last updated 2026-06-24): EURUSD **M5 2015-01-01 →
2021-12-31 is cached but `screen` status (consumed by E001)**; the ledger
names "EURUSD M5 confirm/OOS" as a fresh candidate slice, and GBPUSD/XAU M5
are not listed (presumed absent). Before any forex ORB run, Gate 3 must
attach a **cache audit** (exact M5 date coverage per pair in
`../multi-pair-trading-agent/data/parquet/`). The forex arm uses ONLY
already-cached bars (no new forex data spend), is labelled exploratory, and
carries its own pass line in Gate 5 — it can neither rescue nor sink the
equity verdict.

## 5. Citations added (A3)

- Bailey, D. H. & López de Prado, M. (2014), "The Deflated Sharpe Ratio:
  Correcting for Selection Bias, Backtest Overfitting and Non-Normality" —
  Gate 5 reports the deflated Sharpe with the trial count (two rule
  families × two arms + two controls).
- Harvey, C. R., Liu, Y. & Zhu, H. (2016), "…and the Cross-Section of
  Expected Returns" — the higher-t-hurdle argument; our single-study t
  hurdle is stated in Gate 5, not post hoc.
- Barber, B., Lee, Y.-T., Liu, Y.-J. & Odean, T. — Taiwan day-trader
  evidence (second independent counter-prior beside Chague et al.'s Brazil
  study): the vast majority of day traders lose after costs; persistent
  winners are a tiny minority.
- **Precursor paper id CONFIRMED (A3):** Zarattini, C. & Aziz, A. (2023),
  "Can Day Trading Really Be Profitable?", **SSRN 4416622** (QQQ-only
  5-minute ORB, 2016–2023, first-candle direction, stop at the range
  extreme — the single-instrument precursor to SSRN 4729284). Verified on
  SSRN 2026-10-27.

## 6. Controls data requirements (A4)

The shuffled-direction arm (same entries, random side) and the random-time
arm (same exit/stop logic, random 5-minute window instead of the open) run
on the SAME bars as Rule A — no additional data, stated here so Gate 3
cannot drop the controls for "data reasons". Both controls are built at
Gate 3 and run wherever Rule A runs.

## 7. Data-handling discipline

- Pull scripts land in `experiments/E026_orb_baseline/` with a manifest
  (file hashes, pull date, tier, endpoint parameters) committed to the
  ledger **before** Gate 5 unseals the holdout.
- `DATA_LEDGER.md` gains a new "US equities M5 (Massive)" section at first
  pull: 2021-11→2023-12 = implementation-check (screen), 2024-01→latest =
  **sealed** until Gate 5.
- Holdout is spent once; there is no "quick look". Any peek = the span is
  burnt and the experiment stops with a stated blocker.

## 8. Universe definition — no look-ahead (Claude Gate-2 A4)

"Top 20 by 14-day relative volume" is computed **only from information
available at decision time**:

- Volume of the **first five minutes** of the day, divided by the 14-day
  average of the **first five minutes'** volume (not full-day volume —
  full-day volume is never used for selection).
- Price and liquidity filters taken from the paper's tables (quoted at
  Gate 3, not recalled here).
- Point-in-time ticker list via `/v3/reference/tickers?date=YYYY-MM-DD`
  including `active=false` names.

## 9. Gate 4 implementation-check quantity (Claude Gate-2 A5)

Pre-registered BEFORE the pull:

- **Quantity:** annualised return AND Sharpe of the QQQ precursor rule
  (SSRN 4416622) on our 2022 and 2023 slices, compared to the paper's
  published full-sample figures for the same rule.
- **Tolerance:** within **±20% relative** of the paper's published
  annualised return for each year that the paper breaks out; if the paper
  does **not** publish a 2022/2023 breakdown (to be confirmed by reading
  its tables at Gate 3, not guessed), fall back to: unit tests +
  hand-calculation on **five named days** (two trend days, two range days,
  one gap day) where our fill/stop/exit match a manual ORB worksheet
  within 1 tick. Either path is written into Gate 4 before any holdout
  peek; "within tolerance" alone is no longer acceptable.

## 10. Delisted coverage check list — before renewing (Claude Gate-2 A6)

Pay for one month, then verify history exists for these ~20 named cases
inside 2021–2026. **Cancel and stop at a stated blocker** if more than a
small fraction (pre-register: >3 of 20) are missing or truncated. List
locked now so it cannot be chosen after seeing what exists:

Failed / bankrupt / acquired (expect history ending on delist date):
SVB (SIVBQ / SIVB), FRB (FRC), Signature Bank (SBNY), First Republic
residuals if listed separately, Bed Bath & Beyond (BBBYQ), Revlon (REV),
Endo (ENDPQ), Hertz historical (HTZGQ window if present), Party City
(PRTY), Amc Entertainment is still listed — skip; instead use
**Express Inc (EXPR)**, **Rite Aid (RADCQ)**, **Yellow Corp (YELLQ)**,
**Carvana is listed — skip**; use **Lordstown (RIDE)**, **Arrival (ARVL)**,
**Bird Global (BRDS)**, **Vroom if delisted in window**, **WeWork (WE)**,
**Fisker (FSRN)**, **Virgin Orbit (VORB)**, **Local Bounti if needed**.

Ticker-change / reverse-split cases (history must stitch or both legs
present): FB→META, TWTR→delisted-on-acquisition, SQ→XYZ (Block),
GOOG/GOOGL dual-class continuity.

Exact 20 tickers finalised at purchase-day probe script; the categories
above are locked.

## 11. Starter-tier verification + storage (Claude Gate-2 A7)

On the day of purchase, paste into this gate (or a dated appendix):

1. The Massive pricing-page text confirming Starter includes **minute
   flat files** and stating the **history window** (rolling 5y or not).
2. Acknowledgement that "rolling" means early data drops monthly → pull
   everything needed for 2021-11→holdout **in month 1**.
3. Disk budget: plan **≥ 200 GB** free outside the git repo (suggested
   path `~/data/massive-us-m5/`, never committed); file-hash manifest
   lands in `DATA_LEDGER.md` before Gate 5.

## 12. Domain note (Claude lens)

Even if Rule A holds, a **$100 UK retail account cannot trade twenty names
a day**. E026 is a **research result first**, a product idea second. Live
sizing for Fiyin's real capital is a separate study (small-account note
already opened by Claude).

## 13. Ask for Claude (one-line re-accept)

Please confirm A1–A7 are now written correctly into this file. If yes,
one-line accept → Gate 3 may start; Cursor buys the $29 month only after
that line (Fiyin already approved the spend). No bulk pull before A6
coverage check passes.

**STOP — no signup/pull until Claude's one-line accept of these amendments.**
