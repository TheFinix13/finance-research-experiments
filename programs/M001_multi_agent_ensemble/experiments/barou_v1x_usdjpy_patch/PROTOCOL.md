# Barou v1.4 — USDJPY stop/ATR entry gate (pre-registration)

Registered: **2026-08-05, BEFORE any v1.4 replay executed.**
Charter: Phase AN-5 near-miss (isolation median PF 1.138 vs 1.15 floor,
mean R +0.105, 5/5, n≈418) + autopsy Candidate A
(`barou_v1x_usdjpy_autopsy/FINDINGS.md`). Doctrine: change the PLAYER
(one mechanism), never the TEST floors.

## Question

Does adding ONE entry-time gate — reject when structural stop distance
exceeds **2.25 × ATR(14)** — lift Barou's deployed v1.3 weapon on
USDJPY above the AN isolation floors after honest costs?

## Declared mechanism (frozen)

```
if stop_pips / atr_pips > 2.25:  return None   # no proposal
```

- Threshold **2.25** rounded from the in-sample median 2.28; frozen HERE
  before sealed contact. No sweep on sealed data.
- Inputs known at signal time (structural stop + ATR). No peer chemistry.
- Code flag: `A7BarouV1(weapon_v14=True, stop_atr_max=2.25)` on product
  `@ HEAD` (live default remains `weapon_v14=False`).

## Arms

| arm | weapon | roster |
|---|---|---|
| baseline (reference only) | v1.3, no gate | AN-5 design tapes already on disk — DO NOT re-run |
| **treatment** | v1.3 + v1.4 gate | isolation `barou_shoei` only, USDJPY |

## Design (contaminated upper-bound — n/stability check only)

- Window 2015-01-01 → 2022-12-31 (already consumed by AN-5; second look
  declared; KPIs are NOT confirmatory).
- K=5 starts: 2015-01 / 04 / 07 / 10 / 2016-01; 3-month burn-in; median.
- Honest RT cost: **1.0** USDJPY pip (same as AN).
- Equity=500, aggregator phi41, engine post-I030.
- Purpose: confirm median n ≥ 60 after the gate and that PF does not
  collapse. Design PASS is necessary but not sufficient.

## Sealed confirmation (the judgment)

- Opened ONCE if design n-floor holds: **USDJPY H4 2023-01-01 → 2026-05-31**
  (still sealed per DATA_LEDGER — AN never opened it).
- K=5 starts 2023-01 +0/3/6/9/12 months, same burn-in + 1.0 pip cost.
- Floors (identical to AN, do not move), all at 1× cost:
  1. median n ≥ 25
  2. median PF ≥ 1.10
  3. median mean R > 0
  4. PF > 1 in ≥ 4 of 5 starts

## Out of scope this patch

- USDCAD home review, USTEC, devour/H1/H2, rollover filter, breakeven
  exits (Candidate B — separate charter if A fails), conviction gates
  (degenerate), DOW filters, re-judging AN-5 baseline.

## Multiplicity / honesty

Autopsy screened ~26 filters on consumed design data; Candidate A was
pre-selected for its margin + mechanism, not for sealed peeking. Design
PF ~1.5 from the autopsy counterfactual is an **upper bound**. Fail on
sealed is final; the USDJPY 2023+ window stays consumed either way.

## Outputs

`results/{design,sealed}_summary.json`, raw tapes under `results/`,
`REPORT.md`, DATA_LEDGER row on the sealed open.
