# 01 — Archive: Week of 2026-06-15 (the trigger for this R&D)

**Status:** `STABLE` (historical record) — 2026-06-23.

This doc preserves the analyses, trades, and lessons from the week
that motivated the multi-agent ensemble pivot. It is the **shared
ground truth** for every subsequent design choice in this folder.

Everything in this file is descriptive — no claims, no
recommendations. Recommendations live in `00-charter.md` and beyond.

---

## 1. The three independent reads of the same week

The same five sessions (Jun 15 – Jun 19, 2026) produced three valid
directional reads from three different "voices."

### 1a. The live `zone_d1_against` agent

- **Setup logic.** H4 supply / demand zone touch, faded *against* the
  D1 trend. Mean reversion.
- **Behaviour this week.** Generated repeated short signals on USDCAD
  (D1 trend up → fade with shorts at H4 supply touches). USDCAD #1
  (June 11 → 15) closed soft-SL for −$5.66 (pre-vault). USDCAD #2
  (June 16 → 17) closed soft-SL for **−$3.48**, vaulted. Multiple
  EUR / GBP H4 closes produced no signal or rejected at gate (broker
  reject `retcode=10027`, HTF gate, vol gate).
- **Final result this week.** Net **−$9.14** on demo across the three
  symbols.
- **Why it failed.** The "fade D1 trend" thesis is structurally
  short-gamma into a vol-expansion week (FOMC June 17). It was
  positioned for mean reversion in a market that did the opposite.

### 1b. The assistant's quant read (institutional / vol-breakout frame)

- **Setup logic.** Pre-FOMC vol compression → known structural lid →
  asymmetric vol-breakout. Mon ranges ≈ 0.5× 20-D ATR. Tue Mon lower-high
  print. Wed FOMC → expect one-sided expansion.
- **Trades proposed.** Three:
  1. USDCAD long Mon/Tue on H4 demand fade with D1 trend (would have
     paid).
  2. EUR / GBP shorts at Wed H4 close after the FOMC reaction was
     directionally confirmed.
  3. Continuation USD-strength holds into Thu close.
- **Estimated PnL.** +4–5 % on a $1000 account.
- **Limitations identified afterwards.** Entry timing was 1h45m later
  than the trader's actual entry, because it used H4-close confirmation
  rather than 1h pattern-break trigger. Lost ~85 pips of combined edge
  versus the trader's intra-bar entry.

### 1c. The trader's discretionary multi-timeframe read

- **Setup logic.** Top-down: Monthly → Weekly → Daily → 4h → 1h.
  Liquidity zones (D1: 1.14660 from 2026-03-30; 1.14152) + 4h
  pullback zones (1.15885 / 1.15749 / 1.15649 / 1.15033 / 1.14447) +
  1h head-and-shoulders pattern trigger on GBP.
- **Demo trades taken (Jun 17, Exness $1000 demo).**
  - EUR/USD SELL 0.1 @ 1.15923 → close 1.15611 → **+$31.20**
  - GBP/USD SELL 0.1 @ 1.34018 → close 1.33657 → **+$36.10**
  - Total day: **+$67.30 = +6.73 % in 3h47m**
- **Live trades taken (Jun 18 – 19, Exness real $72.41).**
  - GBP SELL 0.1 @ 1.32055 (Jun 18 18:54 UTC) → margin-closed 1.32215 → −$16.00
  - EUR SELL 0.1 @ 1.14600 (Jun 18 18:55 UTC) → margin-closed 1.14605 → −$0.50
  - **EUR add SELL 0.2 @ 1.14423** (Jun 19 04:00 UTC) → margin-closed 1.14605 → −$36.40
  - **GBP add SELL 0.2 @ 1.31758** (Jun 19 04:42 UTC) → margin-closed 1.32215 → −$91.40
  - All four positions liquidated simultaneously at 2026-06-19 08:25:44 UTC.
  - **Net: −$144.30 → account zeroed (−199 % of deposit).**
- **Thesis outcome.** The directional view paid. EUR closed Friday at
  1.13805 (below the trader's "last line" target). GBP closed at 1.31881
  (inside the trader's final demand-zone target 1.32140). **The forecast
  was correct; the path-survival was not.**

---

## 2. The opportunity table (what was on offer)

Pip math: 0.1 lot EUR / GBP majors ⇒ $1/pip. 0.2 lot ⇒ $2/pip. 0.3 lot ⇒ $3/pip.

| Scenario | Size | Method | Pips captured (EUR + GBP) | $ on lot size | Return on $72 | Return on $1000 |
|---|---|---|---|---|---|---|
| A — plan, all-or-nothing | 0.1 each | hold to last reached target | 156 + 170 = 326 | $326 | **+453 %** | +32.6 % |
| A′ — plan, 25 %-rung ladder | 0.1 each | scale out at each TP | n/a | $230.50 | +320 % | +23.1 % |
| B — plan @ live size | 0.3 each | hold to last reached target | as above × 3 | $978 | +1,359 % | +97.8 % |
| C — live trades, perfect exit | 0.3 each, deep entries | exit at Fri low | 30.9 + 14.4 = 45.3 | $13.59 | +19 % | +1.4 % |
| **D — actual realized** | 0.3 each | broker margin call | — | **−$144.30** | **−199 % (blown)** | n/a |

Spread A → D is **the same correct directional view priced under
different execution disciplines**. Every multi-agent design choice that
follows is judged against its ability to compress this spread.

---

## 3. Why the live account blew

Drivers, in order of magnitude of contribution:

1. **Account size × leverage × correlation mismatch.** $72 with 0.6
   lots total (after adds) on two ρ ≈ 0.85 USD pairs = $6 / pip basket
   exposure. 1 adverse pip ≈ 11 % of equity. The system could not survive
   a 5-pip retrace, let alone the 18p / 46p actually delivered. Margin-call
   threshold at 50 % was hit at the London-open pop.
2. **No hard stop on broker.** All trades opened without S/L. Broker
   stop-out engine became the de-facto SL — exit price set by margin
   math, not thesis.
3. **Scaling deeper into a winning trade with no thesis refresh.** The
   0.2-lot adds were placed within 25 pips of the eventual low (EUR) and
   within 4.5 pips (GBP) — discretionary precision. But they tripled
   exposure at the point in the move where remaining edge was smallest
   and pullback probability was highest.
4. **Correlation hidden behind "two trades."** Two correlated USD-pair
   shorts is one risk position. Sizing them independently double-counts
   diversification that doesn't exist.
5. **Demo → live transfer of size, not of process.** 0.1 lot on a
   $1000 demo (= 0.01 % per pip-unit per dollar of equity) translated
   to 0.1 lot on $72 live (= 0.14 % per pip-unit per dollar of equity).
   Same nominal lot, 14× the relative risk. The process didn't scale
   with the account.

---

## 4. What the live `zone_d1_against` agent's risk envelope would have prevented

Strictly relevant to the multi-agent design (the production agent
already enforces this; the trader didn't because the manual order
ticket has no such guards):

- **Hard SL at order placement.** Always set.
- **Conviction-scaled risk 0.5 – 2 % × `risk_scale`.** Lot computed
  from `target_$_risk / (stop_pips × pip_value)`. Cannot exceed margin
  caps.
- **PostLossGuard after a loss.** Halves size next trade.
- **No-add to winners.** Each new signal sizes from scratch.
- **Per-symbol independence (current gap).** Does not net basket
  exposure across correlated pairs. ← **This is the gap C4 in the
  charter exists to close.**

---

## 5. Lessons distilled into design constraints

The following are the constraints that any multi-agent ensemble must
satisfy. They are inputs to the architecture sketch.

| L# | Lesson | Becomes design constraint |
|---|---|---|
| L1 | Same view → spread of outcomes from $-144 to +$978 driven entirely by sizing / additions / stops / fusion | Capital allocation and order aggregation must be deterministic functions of agent state, account state, and basket state |
| L2 | Single-strategy agent silently mis-positions for the wrong regime | Roster must contain agents whose theses *disagree* in opposite regimes |
| L3 | "Two trades" can be one bet | Risk conductor sizes baskets (USD long, USD short, JPY long, …), not single tickets |
| L4 | Discretionary intra-bar entry beat mechanical H4-close entry by ≈ 85 pips | At least one agent runs on intrabar / 1h trigger logic, not only H4-close logic |
| L5 | Pattern triggers (H&S) carry real predictive content when nested in higher-TF structure | A pattern-detector agent belongs in the roster |
| L6 | Account size dictates whether a strategy is *feasible*, not whether it has edge | Position sizer must hard-refuse trades whose minimum survivable stop > account-permitted risk |
| L7 | "Last reached target" depends on the ladder, which the existing system journals but does not execute | Per-agent exit ladders, with per-rung partial-exit execution, become a roster requirement |
| L8 | Three different valid analyses of the same chart produced different actions | Fusion mechanism must combine, not eliminate, disagreeing voices |

These eight constraints will be revisited at each phase gate.

---

## 6. Verbatim source material (for traceability)

- Trader's analysis (EUR + GBP, by timeframe, with target ladders) —
  recorded in chat transcript at
  `~/.cursor/projects/Users-the1finix-Documents-GitHub-multi-pair-trading-agent/agent-transcripts/5e662e2d-da95-4d51-b80d-746dcacdb878/5e662e2d-da95-4d51-b80d-746dcacdb878.jsonl`.
- Demo statement (Jun 17 trades) — pasted in same transcript.
- Live statement (Jun 18 – 19 blowup) —
  `~/Downloads/daily_statement_10000189685_20260618.pdf`. Summary: net
  deposit $72.41, closed P/L −$144.30, null compensation $0.46, end
  balance $0.
- Live agent logs — VM `C:\Users\Fiyin\Documents\TradingAgentLogs\`.
- USDCAD loss vault — `~/Documents/TradingAgentLogs/USDCAD/losses/events.jsonl`
  (file came online 2026-06-10 — see commit `f49e469`).
