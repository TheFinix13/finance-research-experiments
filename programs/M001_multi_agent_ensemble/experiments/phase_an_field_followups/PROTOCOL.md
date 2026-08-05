# Phase AN — chartered field follow-ups, multi-start family (pre-registration)

Registered 2026-08-05, BEFORE any replay in this family executed.
Charter: Phase AL A1 + Phase AM survey nominations (user go 2026-08-05:
"work on this ... we can start working on all of these ... proceed
carefully"). This ONE protocol covers the whole family so multiplicity
is accounted in one place.

## The five studies

| study | agent | field(s) | nominating survey (squad-context) |
|---|---|---|---|
| AN-1 | itoshi_rin | USDJPY | AL A1: n=336, PF 1.212, meanR +0.125 |
| AN-2 | chigiri_hyoma | AUDUSD | AL: n=183, PF 1.376, meanR +0.175 |
| AN-3 | chigiri_hyoma | XAGUSD | AM: n=134, PF 1.541, meanR +0.243 |
| AN-4 | bachira_meguru | NZDUSD | AL: n=332, PF 1.269, meanR +0.092 |
| AN-5 | barou_shoei | USDCAD + USDJPY + USTEC | home + AL A1 (78/1.364) + AM (98/1.156); folds his open n-growth question into one study |

## Question (per study)

Does the agent's DEPLOYED weapon (unchanged code, deployed config)
have positive after-cost expectancy on the nominated field, measured
in single-agent ISOLATION? Isolation is the mechanism claim (the
weapon itself); the surveys already measured squad context. AJ-2's
registered note requires isolation replays for thin-n follow-ups.

## Design (identical machinery for all five)

- Engine: product `product` @ `d98fbf3` (post-I030, field-card pip
  values). `build_roster()` defaults (barou_v12=False, barou_v13=True),
  then `roster.proposers` filtered to the study agent ONLY.
  Declared consequence: peer-chemistry lifts, Karasu advisories and
  Kunigami streak warnings are absent — this tests the solo weapon.
- Aggregator arm phi41, **equity=500** (the real v2 demo account).
- Data: Tier-1 pairs from the agent-repo cache; XAGUSD/USTEC from the
  research `data/parquet_tier2/` bank.
- **Multi-start K=5 per methodology standard** (applied to ALL studies,
  including n>100 cells, for family uniformity):
  design starts 2015-01-01 / 2015-04-01 / 2015-07-01 / 2015-10-01 /
  2016-01-01, common end **2022-12-31**; 3-month burn-in per start
  (trades entered before start+3mo are discarded from KPIs); judge
  the MEDIAN across starts; report median [min–max].
- AN-5 runs each of its three fields as separate isolation replays on
  the same start set (15 replays); per-field verdicts.

## Cost honesty (declared BEFORE execution)

Engine fill costs are FX-calibrated and understate JPY/metals/index
costs. Post-hoc, every trade's pnl_pips is reduced by a declared
honest round-trip spread (deducted ON TOP of engine costs —
conservative by construction; r_multiple recomputed per trade as
(pnl−c)/source_sl_pips):

| field | honest RT spread (field-pips) |
|---|---|
| AUDUSD 1.2 | NZDUSD 1.6 | USDJPY 1.0 | USDCAD 1.4 | XAGUSD 2.5 | USTEC 2.0 |

Sensitivity grid reported at 0 / 0.5× / 1× / 2×; **all floors are
judged at the 1× deduction**.

## Floors (declared BEFORE execution)

Design pass (per study; per field for AN-5), all four required at 1×
cost:

1. median n ≥ 60 (post burn-in)
2. median PF ≥ 1.15
3. median mean R ≥ +0.05
4. PF > 1 in ≥ 4 of 5 starts (else `path_unstable`, reported not passed)

**Sealed confirmation** — opened ONCE per passing study; for AN-5 at
most ONE field (highest passing median PF). Window **2023-01-01 →
2026-05-31** (uniform; inside every field's banked coverage), K=5
starts 2023-01-01 +0/3/6/9/12 months, same 3-month burn-in — one open
EVENT with five state-paths over the same sealed tape. Pass, all at
1× cost:

1. median n ≥ 25
2. median PF ≥ 1.10
3. median mean R > 0
4. PF > 1 in ≥ 4 of 5 starts

## Multiplicity, stated

Up to 5 sealed opens. If each passing design cell had NO real edge,
the sealed floors would still pass by luck an estimated 10–20% of the
time each — so with 5 opens, ~1 false pass is EXPECTED in the
no-edge world. Therefore: all five outcomes are reported together;
a single isolated pass is "validated-with-1-of-5-caveat"; 2+ passes
materially strengthen the family. No retuning after sealed results;
failures are final and the windows stay consumed.

## Declared distortions carried from the surveys

- Zone-grammar price-scale filters effectively OFF on USDJPY / XAGUSD /
  USTEC (major-calibrated constants). The artifact under test is the
  weapon AS IMPLEMENTED — the same code that would deploy. A
  recalibrated grammar would be a different weapon (v1.1 territory).
- Design regions were already consumed by AL/AM (second look,
  declared); freshness lives entirely in the sealed windows, which
  have NEVER been opened for these fields.

## Outputs

`results/<study>/design/start_<k>/` raw tapes; `results/<study>/design_summary.json`;
sealed equivalents for passers; REPORT.md with the family table
(median [min–max] per methodology rule 4); DATA_LEDGER rows on
execution.
