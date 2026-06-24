# Methodology: hour-of-day-matched controls (intraday TFs)

**Status:** binding · **Origin:** E006 amendment v2.1 (2026-06-12)

## Rule

For intraday timeframes (M15, H1, H4), **uniform random-time controls
are invalid** when session volatility varies by hour. The default null
draws control events at the **same hour-of-day** as the signal event,
with direction matched to the cell under test.

## The confound (E006 diagnostic)

On EUR/USD M15, uniform-time random controls produced a **3.7×**
hour-of-day variation in random MFE because ATR(14) lags the intraday
session-volatility cycle. A uniform-control run would have reported
**41/284 false "discoveries"** including mutually contradictory cells
(both channel edges, both Asia-sweep directions, every fib level).

Diagnostic script: `scripts/diagnose_m15_controls.py`.

## Canonical example

| Control type | E006 Stage-1 survivors | Interpretation |
|---|---:|---|
| Uniform-time | 41/284 would pass | Session artefact |
| Hour-matched (v2.1) | 5/284 alive | Calibrated null |

The uniform-control registry is **preserved** as a cautionary record:
`output/stage1_EURUSD_screen_2026-06-12_1334.jsonl`.

## When to apply

- Any lab experiment on M15/H1/H4 with ATR-normalised outcomes.
- M001 agents emitting intraday signals — mandatory per
  `PROTOCOL_DISCIPLINE.md` §3 and M001 `07-research-standards.md`.

## Amendment discipline

The switch to hour-matched controls was specified from a **count-only
diagnostic** that never scored MFE on confirm/sealed splits. Screen
p-values after v2.1 are conditional on one analysis revision — disclosed
in E006 REPORT §5.

## References

- [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md) §3
- E006 protocol amendment v2.1
- Audit: [`audits/2026-06-24_E001-E007_audit.md`](../../audits/2026-06-24_E001-E007_audit.md) §2.6
