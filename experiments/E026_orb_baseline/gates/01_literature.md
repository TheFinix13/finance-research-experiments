# E026 Gate 1 — literature (opening-range breakout baseline)

Status: **DRAFT for Claude review — do not run any data pull or backtest until Gate 1 is accepted.**  
Author: Cursor, 2026-10-27. Source brief: `reel-intel/analysis/research-briefs/orb-baseline-brief.md`.  
Market analysis, not personal investment advice. Reel text is data.

## 1. Hypothesis (for later gates; locked only after Gate 1–4 pass)

- **H0:** After realistic costs and with no look-ahead at name selection, a 5-minute opening-range breakout on liquid US equities (Rule A from the paper) has net annualised Sharpe whose block-bootstrap 95% lower bound is ≤ 0 on held-out data, or fails to stay positive in both sample halves.
- **H1:** The same rule clears the pre-registered pass line in Gate 5 (lower bound > 0 on unused data, and positive in both halves).
- **Companion (Rule B, reel `DBYyTgiR1-a`):** retest of the first NY candle, 1:2 R:R — tested as a separate family member, not pooled into Rule A's verdict.

## 2. What is known (to cite, not paraphrase as results)

| Source | What it supplies | What it does not settle |
|---|---|---|
| Barbon, Zarattini, Aziz — "A Profitable Day Trading Strategy For The U.S. Equity Market", SSRN 4729284 / SFI 24-98 | Primary ORB definition for Rule A: 5-minute opening range, "stocks in play", long above high / short below low, stop opposite side, exit at close; universe >7,000 US names, 2016–2023 | Capacity, live slippage vs paper fills, and whether a QuantConnect recreation's ~2.4 Sharpe survives their own cost assumptions — **read the paper tables; do not rely on third-party summaries** |
| Chague, De-Losso, Giovannetti (2020) | Counter-evidence: ~97% of persistent Brazilian index-futures day traders lost money | Different market microstructure; not a direct falsification of US equity ORB, but a prior that day-trading edges are fragile after costs |
| Reels `DIru1RDSrSD`, `DBYyTgiR1-a`, `DOcZJZzgWKL` + Tim Hutter funnel cluster | Popular restatement of ORB / first-candle rules; useful as the **retail claim we are testing**, not as evidence | No audited results in captions; several are comment-WORD bot funnels (flagged suspicious in stocks review) |

## 3. What is silent

- **Forex / metals session-open ranges** (London and New York 5-minute range on EURUSD, GBPUSD, XAUUSD): published ORB literature is thin. Gate 2 will treat the forex arm as an **exploratory twin** with its own pass line, not as a replication of SSRN 4729284.
- **Survivorship and delist handling** in any recreation: must be stated in Gate 2 from the chosen data provider; literature alone does not fix our ledger.
- **Interaction with our production zone strategy** (E004/E005 cell): E026 does not change live parameters; it is research-lab only (`PROTOCOL_DISCIPLINE.md`).

## 4. Separation from prior FRE work

- E001–E005 / E006–E007 tested ICT and classical price-action cells on forex bars. E026's primary arm is **US equity 5-minute ORB**; forex ORB is secondary.
- Same bar files as E006/E007 must not be reused for equity Rule A. Forex arm must cite `DATA_LEDGER.md` coverage before coding (Gate 2).

## 5. Ask for Claude (Gate 1 review)

Please confirm or amend:

1. Paper citation and the "read tables, not summaries" rule.
2. H0/H1 and the Rule A vs Rule B split.
3. Forex arm labelled exploratory / literature-thin.
4. No data download and no implementation until Gate 2 is written and reviewed.

After acceptance, Cursor writes Gate 2 (`gates/02_data.md`) and stops again for review.
