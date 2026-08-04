# Phase AL report — Tier-1 field survey (exploratory; no promotions by design)

Executed 2026-08-04, protocol committed (`28f8e82`) before execution.
ONE replay, AUDUSD/NZDUSD/USDJPY/USDCHF, 2015-01-01 → 2022-12-31
(design region; 2023+ stays sealed), causal semantics, deployed
configs, all agents expanded to the survey pairs. 51,556 bars,
2,437 trades, squad PF 0.985 (≈ breakeven wholesale — the value is
in specific cells, not the pitch as a whole).

## USDJPY: INVALID CELL — `invalid_pip_semantics` (I030, P1)

Zero trades from every agent. NOT a market result: proposals flowed
(24k+), conviction contests resolved, and sentinel R1 blocked 100%
of 14,621 winners because `PIP_SIZE = 0.0001` is hardcoded — a
0.50-yen stop reads as 5,000 pips and fails the risk cap. Filed as
product intake I030 (blocks all JPY pairs + gold/indices/oil until
fixed). The protocol's abort clause (investigate before reading
KPIs) worked as designed.

## Valid cells (AUDUSD / NZDUSD / USDCHF) — survey KPIs

| Cell | n | PF | mean R | total pips |
|---|---|---|---|---|
| **chigiri:AUDUSD** | **183** | **1.376** | **+0.175** | **+1117** |
| **bachira:NZDUSD** | **332** | **1.269** | **+0.092** | **+1592** |
| nagi:USDCHF | 31 | 1.568 | +0.242 | +302 |
| barou:AUDUSD | 30 | 1.301 | +0.165 | +191 |
| nagi:AUDUSD | 23 | 1.611 | +0.196 | +221 |
| rin:NZDUSD | 197 | 1.176 | +0.102 | +826 |
| isagi:USDCHF | 44 | 1.163 | +0.023 | +63 |
| bachira:AUDUSD | 336 | 0.937 | −0.063 | −421 |
| chigiri:NZDUSD | 204 | 0.929 | −0.032 | −267 |
| rin:AUDUSD | 201 | 0.928 | −0.060 | −368 |
| isagi:AUDUSD / isagi:NZDUSD | 52 / 60 | 0.603 / 0.469 | −0.279 / −0.417 | −222 / −378 |
| rin:USDCHF | 171 | 0.724 | −0.202 | −1252 |
| bachira:USDCHF | 317 | 0.774 | −0.172 | −1562 |
| chigiri:USDCHF | 197 | 0.988 | +0.003 | −45 |
| barou:NZDUSD / barou:USDCHF | 22 / 17 | 0.418 / 0.692 | — | −397 / −135 |

## Chartered follow-ups (declared criteria: n ≥ 30 AND PF ≥ 1.2; cap TWO)

Four cells qualified: chigiri:AUDUSD, bachira:NZDUSD, nagi:USDCHF,
barou:AUDUSD. Under the declared cap the two with the largest
evidence base advance:

1. **Chigiri:AUDUSD (n=183, PF 1.376).** Converges with the
   INDEPENDENT Phase AK-2 finding (his high-conviction subset is
   positive: mirror n=307, PF 1.26). Two separate lenses now say
   Chigiri's core weapon is sound in the right conditions — feeds
   the v1.1 rework study directly.
2. **Bachira:NZDUSD (n=332, PF 1.269).** His largest positive cell
   anywhere under honest semantics; a live candidate for his
   re-gating charter (AF-2 family).

Qualifying-but-capped (recorded so the cap can't be silently
lifted): nagi:USDCHF, barou:AUDUSD. Barou's cell rides into his
already-chartered multi-start n-growth study rather than a new one.

## Caveats (binding)

- Exploratory: NOTHING here is promoted; each follow-up needs its
  own pre-registration, the K=5 multi-start standard (all these n's
  are path-noise-exposed; Barou/Nagi cells especially), and a sealed
  2023+ or live confirmation.
- Squad-state interactions differ from home deployment (away-only
  pitch); numbers are not comparable to AF/AJ tables.
- DATA_LEDGER updated: 2015–2022 × {AUDUSD, NZDUSD, USDCHF} now
  consumed as design data (USDJPY consumed-but-invalid).

---

## Amendment A1 results — post-I030-fix re-survey (2026-08-04)

Engine fix `2650524` (product repo) re-run of the identical survey.
`results/survey_postfix.json` supersedes the original readout.

**USDJPY is unblocked**: 1,025 trades flowed (0 before). Squad-level:
3,462 trades, PF 1.015, mean R −0.007 (exploratory noise, as expected
for an unfiltered squad on unfamiliar fields).

Cells worth a chartered follow-up (all exploratory, no promotions):

| cell | n | win rate | PF | mean R | pips |
|---|---|---|---|---|---|
| itoshi_rin:USDJPY | 336 | 32.1% | 1.212 | +0.125 | +1,875.4 |
| chigiri_hyoma:AUDUSD | 183 | 47.0% | 1.376 | +0.175 | +1,117.1 |
| bachira_meguru:NZDUSD | 332 | 43.7% | 1.269 | +0.092 | +1,591.7 |
| barou_shoei:USDJPY | 78 | 43.6% | 1.364 | +0.182 | +749.0 |

Reading:

- **Rin:USDJPY is the headline.** His largest-n positive cell on ANY
  field (his home EURUSD baseline is thinner and weaker). A precision
  fibre-zone counter-trend weapon appears to fit the yen tape. This
  becomes the third chartered follow-up alongside Chigiri:AUDUSD and
  Bachira:NZDUSD — same standard: multi-start K=5 on the design
  region, sealed 2023+ single-open confirmation.
- Chigiri:AUDUSD and Bachira:NZDUSD survived the re-run essentially
  unchanged (183/1.376 and 332/1.269) — cross-symbol squad-state
  coupling from USDJPY joining the contest was minimal.
- Barou:USDJPY (n=78, PF 1.364) is noted but NOT chartered yet — thin
  n and Barou already has an open n-growth question (AJ-2); folding a
  new field into that charter is a user decision.
- Isagi/Bachira on USDJPY are flat-to-negative; USDCHF remains the
  weakest field surveyed (only Nagi positive, n=31).

FDR discipline: three chartered follow-ups from ~24 surveyed cells is
the selection event this survey exists to fund; the follow-up protocols
carry the multiplicity accounting, not this report.
