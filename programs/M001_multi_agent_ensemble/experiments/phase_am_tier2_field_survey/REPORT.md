# Phase AM — Tier-2 first-wave survey report (2026-08-04)

Executed same day as pre-registration (`ebb1eec`), engine `48cf140`
(post-I030 + field-card pip values), equity=500, design region
2015-01-01 → 2022-12-31, 2023+ seals untouched. First study EVER on
this data (virgin per DATA_LEDGER). 50,112 bars, 4,246 trades.
Squad-level: PF 0.955, mean R −0.026 — an unfiltered squad on alien
fields, as expected.

NOTE on units: "pips" are per-field units (gold $0.10, silver $0.01,
oil $0.01, USTEC 1 point) — pips are NOT comparable across cells;
judge PF / mean R / win rate.

## Verdict vs the declared floor (n ≥ 60, PF ≥ 1.15, mean R > 0)

**PASS — chartered follow-up candidates:**

| cell | n | win rate | PF | mean R |
|---|---|---|---|---|
| chigiri_hyoma:XAGUSD | 134 | 50.0% | 1.541 | +0.243 |
| barou_shoei:USTEC | 98 | 40.8% | 1.156 | +0.041 |

Chigiri on silver is the strongest single cell either survey (AL or
AM) has produced. Barou:USTEC is a marginal floor pass — real but
thin margin; his rare-fire profile means the multi-start standard is
non-negotiable there.

**Noted, below floor:** chigiri:XAUUSD (141, PF 1.126),
nagi:USOIL (133, PF 1.163 but mean R exactly 0.000 → fails),
bachira:XAUUSD (282, PF 1.063), chigiri:USOIL (156, PF 1.058).

**Reported, closed:** everything else. Isagi is negative on all four
fields (USTEC his worst cell anywhere: n=319, PF 0.762). Rin is
negative on all four (win rate ~27% across the board).

## Patterns worth naming (hypotheses, not findings)

1. **Chigiri travels; his home pitch was the problem.** Net-negative
   on EURUSD/GBPUSD (autopsy: pure win-rate deficit), yet positive on
   AUDUSD (AL: PF 1.376), silver (AM: PF 1.541) and gold-lite. His
   ATR-breakout weapon appears to fit commodity-linked, trend-prone
   tapes and to die in the majors' chop. Three independent surveys
   now point the same way.
2. **Rin is a specialist, confirmed again.** Precision counter-trend
   works on EURUSD (home) and USDJPY (AL A1 headline) — deep-liquidity
   mean-reverting FX — and fails every commodity/index tape surveyed.
   His AJ "does not travel" verdict was field-type, not symbol.
3. **Isagi's zone-confluence weapon does not travel at all** (negative
   on all 8 away fields across AL+AM). Home-only until reworked.
4. **Barou's rare-fire continuation shows up on trending fields**
   (USTEC here, USDJPY in AL A1, USDCAD home) — consistent story,
   always thin-n, always needs the K=5 multi-start guard.

## Carried caveats

Declared distortions (protocol sec "Declared distortions") apply to
every number above: zone-grammar price-scale filters effectively OFF,
FX cost model understates Tier-2 costs, regime_fit tilts high. The
USOIL tape includes the Apr-2020 negative-price episode (survey KPIs
unaffected mechanically — R-multiples are stop-relative). Follow-up
protocols must add per-instrument grammar calibration + honest costs
before believing anything here.
