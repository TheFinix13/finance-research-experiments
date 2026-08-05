# AN-3 recency-fade diagnostic — the fade is mostly capital censoring

Executed 2026-08-05, read-only re-read of the consumed AN-3 tapes
(mechanism question, no selection, no retuning; declared per
DATA_LEDGER rule 2d). Script: `diagnose_an3_recency.py`; raw output
`results/an3_recency_diagnostic.json`.

## Question

The sealed pass was front-loaded (2024-01 start path PF 0.941). Is
that thin-sample noise or genuine edge decay on recent silver?

## Answer: mostly NEITHER — it is sentinel R1 capital censoring

Per-calendar-year view on the continuous 2023-01 path (1x cost):

| year | n | PF | win% | median ATR (pips) | proposals rejected |
|---|---|---|---|---|---|
| 2023 | 26 | 1.659 | 57.7 | 22.9 | 10/39 (26%) |
| 2024 | 28 | 1.498 | 57.1 | 30.6 | 18/46 (39%) |
| 2025 | 18 | 0.732 | 33.3 | 33.9 | 33/51 (65%) |
| 2026 (Jan–May) | **0** | — | — | — | **15/15 (100%)** |

All five sealed paths converge to identical 2024/2025 KPIs (burn-in
works; this is a calendar effect, not path noise). Design single-year
PF range 2015–2022: 0.806–1.835, 2 of 8 years below 1.0 — so 2025's
0.732 on n=18 is only slightly below the historical worst year and
within thin-n variation on its own.

The load-bearing fact is the rejection column. Nearly every rejection
is `sentinel_R1_block: min-lot risk $X > cap $25.00 (=5.0% of
equity)`. Silver's dollar volatility roughly doubled 2023→2026;
min-lot risks on his 2026 proposals run $68–$568. **At equity=$500
and min lot 0.01 ($0.50/pip), the account is structurally priced out
of silver in the current regime — Chigiri never stopped proposing.**

Second-order effect, and the likely cause of the 2025 win-rate
collapse: R1 censoring is not random. It deletes the WIDE-stop
proposals first, so the filled subset is squeezed toward tight
stops relative to volatility — filled-trade max stop/ATR fell from
2.20 (2023) to 1.42 (2025) with the wide tail gone entirely. Tight
stops in the highest-vol regime mechanically stop out more often.
So the 2025 PF 0.732 measures a censored, adversely-selected slice
of the weapon, not the weapon.

## What this means

1. **The sealed verdict stands as stated** — it honestly measured
   "the weapon as deployable on the $500 account, blocks included."
   But the correct reading of the fade is "the account outgrew by
   shrinking relative to silver," not "the edge decayed."
2. **A naive shadow deployment at $500 would measure nothing** — at
   2026 silver vol, R1 blocks ~100% of his proposals, so the fresh
   tape would stay empty. Shadow measurement must therefore run in a
   MEASUREMENT configuration (see paper-loop charter): signals and
   R1 verdicts both recorded, KPIs computed on the uncensored signal
   stream, deployability tracked separately as the fraction R1 would
   admit at real equity.
3. **The open risk question for real capital** is not edge decay but
   sizing: silver at 2026 vol needs either more equity, a smaller
   min lot, or a per-field risk-cap decision (user's call — that is
   a risk-rule change and stays out of scope for the shadow).
4. The uncensored-signal expectancy in 2025–2026 is UNKNOWN (that
   slice was never executed). The paper loop is the only clean way
   to learn it — one more reason to ship it as measurement-first.
