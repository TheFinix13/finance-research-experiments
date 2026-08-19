# E033 Stage 0 + Stage 1 report

Status: **STOPPED-DEAD at Stage 1** (2026-08-19). Stage 2 (placebo) was
not authorised. The deployed cell keeps trading through scheduled news
under this operationalisation.

Generated: 2026-08-19T11:13:54Z · calendar 349 USD NFP/CPI/FOMC events
(sha256 `cfd186021ea87a5a…`, Phase AE frozen fixture, vendored
read-only at `programs/E033/data/news_calendar_frozen_2026-07-24.json`).
Harness: `programs/E033/run_e033_validation.py` (5,000-resample paired
bootstrap, seed 42, BH α=0.10 within each (family, symbol), Stouffer
joint p). Family A primary is **zero-fill** (suppressed trade contributes
0R — the live-agent meaning of "don't take it"); window classification
held fixed under resample per PROTOCOL §3.

## Verdict in one paragraph

Tight entry-blackout windows barely fire (AD.2-style inertness on
limit-fill timestamps: 6–25 trades / 11y on the ±30–240 min arms, below
the n=30 floor). The one Family A arm that engages everywhere —
`event_day` — is **dead** on all three symbols (ΔSharpe −0.027 / −0.006
/ −0.023). Family B (the NFP shape: flatten or BE-tighten 4h/8h before
the release) engages cleanly (69–88 trades/symbol) and is **dead** on
EURUSD and GBPUSD; USDCAD flatten/BE is `parked_low_yield` (point
positive, CI includes 0, joint p 0.17–0.61). 0/30 (arm, symbol) cells
`stage1_alive`. Both families stop independently under PROTOCOL §5.

The mechanism is the AD.2 prior, now measured on the deployed fade
cell: the trades that sit on news are **net winners**, not net losers.
EURUSD fills inside ±30 min of NFP/CPI/FOMC are 7/7 at +1.50R; the
event-day cohort is +0.45R mean vs a +0.43R book. Flattening them
gives back ~0.27R per touched EURUSD trade. The Aug 7 live NFP wipe
is real and in the motivating tape; it does not generalise to 2015–2025.

## Stage 0 — engagement (outcome-blind; printed before any R was scored)

| Symbol | Arm | Family | Touched | Underpowered |
|---|---|---|---|---|
| EURUSD | A_30_30 | A | 7 | yes |
| EURUSD | A_60_60 | A | 8 | yes |
| EURUSD | A_120_60 | A | 15 | yes |
| EURUSD | A_120_120 | A | 19 | yes |
| EURUSD | A_240_120 | A | 21 | yes |
| EURUSD | A_event_day | A | 81 | no |
| EURUSD | B_flatten_4h | B | 69 | no |
| EURUSD | B_flatten_8h | B | 73 | no |
| EURUSD | B_be_4h | B | 69 | no |
| EURUSD | B_be_8h | B | 73 | no |
| GBPUSD | A_30_30 | A | 10 | yes |
| GBPUSD | A_60_60 | A | 13 | yes |
| GBPUSD | A_120_60 | A | 23 | yes |
| GBPUSD | A_120_120 | A | 30 | no |
| GBPUSD | A_240_120 | A | 30 | no |
| GBPUSD | A_event_day | A | 79 | no |
| GBPUSD | B_flatten_4h | B | 78 | no |
| GBPUSD | B_flatten_8h | B | 88 | no |
| GBPUSD | B_be_4h | B | 78 | no |
| GBPUSD | B_be_8h | B | 88 | no |
| USDCAD | A_30_30 | A | 6 | yes |
| USDCAD | A_60_60 | A | 10 | yes |
| USDCAD | A_120_60 | A | 17 | yes |
| USDCAD | A_120_120 | A | 23 | yes |
| USDCAD | A_240_120 | A | 25 | yes |
| USDCAD | A_event_day | A | 72 | no |
| USDCAD | B_flatten_4h | B | 76 | no |
| USDCAD | B_flatten_8h | B | 73 | no |
| USDCAD | B_be_4h | B | 76 | no |
| USDCAD | B_be_8h | B | 73 | no |

## Stage 1 — screen

| Symbol | Arm | ΔSharpe | CI 95% | joint p | folds+ | BH | label |
|---|---|---|---|---|---|---|---|
| EURUSD | A_event_day | −0.0270 | [−0.0636, +0.0090] | 0.115 | 1/5 | fail | **dead** |
| EURUSD | B_flatten_4h | −0.0140 | [−0.0419, +0.0136] | 0.317 | 2/5 | fail | **dead** |
| EURUSD | B_flatten_8h | −0.0111 | [−0.0378, +0.0164] | 0.292 | 2/5 | fail | **dead** |
| EURUSD | B_be_4h | −0.0018 | [−0.0185, +0.0155] | 0.806 | 1/5 | fail | **dead** |
| EURUSD | B_be_8h | −0.0155 | [−0.0295, −0.0021] | 0.048 | 0/5 | fail | **dead** |
| GBPUSD | A_120_120 | −0.0036 | [−0.0189, +0.0122] | 0.504 | 2/5 | fail | **dead** |
| GBPUSD | A_240_120 | −0.0036 | [−0.0189, +0.0122] | 0.504 | 2/5 | fail | **dead** |
| GBPUSD | A_event_day | −0.0064 | [−0.0328, +0.0198] | 0.387 | 1/5 | fail | **dead** |
| GBPUSD | B_flatten_4h | −0.0120 | [−0.0333, +0.0089] | 0.460 | 3/5 | fail | **dead** |
| GBPUSD | B_flatten_8h | −0.0079 | [−0.0289, +0.0137] | 0.713 | 3/5 | fail | **dead** |
| GBPUSD | B_be_4h | −0.0031 | [−0.0137, +0.0075] | 0.618 | 2/5 | fail | **dead** |
| GBPUSD | B_be_8h | −0.0002 | [−0.0098, +0.0095] | 0.865 | 1/5 | fail | **dead** |
| USDCAD | A_event_day | −0.0230 | [−0.0583, +0.0107] | 0.117 | 2/5 | fail | **dead** |
| USDCAD | B_flatten_4h | +0.0213 | [−0.0106, +0.0561] | 0.172 | 5/5 | fail | **parked_low_yield** |
| USDCAD | B_flatten_8h | +0.0200 | [−0.0112, +0.0516] | 0.196 | 4/5 | fail | **parked_low_yield** |
| USDCAD | B_be_4h | +0.0072 | [−0.0140, +0.0300] | 0.540 | 3/5 | fail | **parked_low_yield** |
| USDCAD | B_be_8h | +0.0079 | [−0.0112, +0.0286] | 0.611 | 4/5 | fail | **parked_low_yield** |

(Underpowered Family A cells omitted from the score table; they are in
Stage 0.)

## Secondary: touched-cohort mean R (PROTOCOL §4)

Family A suppressed fills are **better than the book**, not worse:

| Symbol | Book mean R | A_30_30 | A_event_day |
|---|---|---|---|
| EURUSD | +0.433 | **+1.500 (7/7 wins)** | +0.451 (49/81) |
| GBPUSD | +0.375 | +0.400 (6/10) | +0.253 (40/79) |
| USDCAD | +0.378 | **+1.500 (6/6 wins)** | +0.382 (39/72) |

Family B flatten ΔR on the touched cohort: EURUSD −0.29R, GBPUSD −0.25R,
USDCAD **+0.02R**. The USDCAD parked sign is real (news-held USDCAD
trades were the weakest cohort, orig mean +0.105R) but it does not
clear the CI-LB>0 bar.

## What this does and does not close

- **Closes** Stage-1 binary blackout and Stage-1 pre-event flatten/BE
  as deployable v1 filters. No Phase-3 wiring. No live-agent calendar
  gate from this ID.
- **Does not close** "news can hurt a live trade" — Aug 7 happened.
  It closes "therefore a calendar blackout is +EV on this cell."
- **Does not authorise E034** (event-distance as a continuous regime
  feature). PROTOCOL gated E034 on E033 either way; a `dead` E033 with
  a fat touched-cohort *and* a winner-heavy Family A is the case the
  protocol described as "high-variance-zero-mean, maybe size down
  rather than skip." That is a **new** pre-reg, not an amendment.
- Stage-3 directional interpretation (surprise vs consensus) stays in
  the v2/SAE lane. SAE-as-trader already failed Phase AE; this result
  is consistent with "avoidable, not tradable" being about SAE's
  *event trades*, not about wiping the fade cell's own book.

See `STOP_NOTICE.md`. Raw cells: `programs/E033/results.json`.
