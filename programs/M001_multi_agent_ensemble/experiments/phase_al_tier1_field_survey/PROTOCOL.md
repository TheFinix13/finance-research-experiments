# Phase AL — Tier-1 field survey: the squad on four never-played pairs (pre-registration)

Registered: 2026-08-04, BEFORE execution. Charter: D148 Tier 1 —
AUDUSD, NZDUSD, USDJPY, USDCHF are banked, lightly fingerprinted only
by Phase AC (whose results are void: pre-D138 lookahead semantics),
and never replayed by the causal squad.

## Question class: EXPLORATORY FIELD SURVEY — declared up front

This stage produces NO promotions and NO verdicts on agents. It maps
the terrain: which agents produce trades on which new field, at what
rough quality, so that specific promotion studies (with the
multi-start standard and sealed confirmation) can be chartered
narrowly instead of sweeping blind. Survey KPIs are hypothesis
GENERATORS. Anything interesting here must earn promotion in its own
later pre-registered study; those verdict stages will comply with
METHODOLOGY_thin_sample_replays.md (K=5 staggered starts, median,
4/5 sign stability).

## Data discipline

- Window: **2015-01-01 → 2022-12-31** (design region ONLY — the
  2023→present slice of every Tier-1 field is SEALED per DATA_LEDGER
  rule 4 and is not loaded by the runner at all).
- JPY-pair pip semantics (0.01) verified in the KPI layer before any
  numbers are read.

## Method

ONE replay, four symbols (AUDUSD, NZDUSD, USDJPY, USDCHF), H4,
causal D138 semantics, deployed parameterisations, live roster shape
with every symbol-restricted agent's symbol list EXPANDED to the four
survey pairs (module-constant patch as in Phase AJ, own process).
The three home pairs are NOT included: this is an away-field survey;
squad-state interactions with home fields are out of scope and the
absence of home pairs is a declared limitation (KPIs here are not
comparable to AF/AJ numbers — different pitch mix).

## Readouts (all descriptive)

Per agent × symbol: n trades, win rate, PF, mean R, total pips; plus
proposal/rejection funnel per symbol; plus per-symbol zone/swing
counts from prepare() (does the zones grammar even find structure on
these fields?). DATA_LEDGER gets a row: 2015–2022 × 4 pairs opened
by AL (design region).

## Outputs

`results/survey.json`, `REPORT.md` with a "chartered follow-ups"
section naming at most TWO agent×field cells that justify their own
promotion study (chosen on declared criteria: n ≥ 30 AND PF ≥ 1.2 in
the survey — the SELECTION is declared here so the follow-up study's
multiplicity accounting can cite it).

## Abort

Replay crash or all-agents-zero-trades on a symbol → investigate
data/pip semantics before reading any KPI (I024/I029-class checks
first).
