# Phase AJ — cross-symbol weapon transfer (pre-registration)

Registered: 2026-08-04, BEFORE any replay executed. Charter:
multi-pair-trading-agent D145 (Neo Egoist League, Tier B step 1) +
user directive 2026-08-04: "of what point is the multi ensemble if
it's not working for multiple instruments/pairs" — the cheapest new
field is the pairs we already bank data for.

## Hypothesis

H-AJ1: weapons parameterised on their home symbol carry positive
causal expectancy to away symbols they have never traded. The pitch
is currently uneven BY DESIGN (Rin EURUSD-only, Barou USDCAD-only,
Chigiri EURUSD+GBPUSD); nothing has ever tested whether that
restriction is load-bearing or historical accident.

Secondary motivation: Barou was direction-positive in ALL 8 Phase AF
in-sample cells but n-starved (14–38 trades). Two more fields at his
deployed config could triple his sample without touching his weapon.

## Cells (declared exhaustively — 5 away cells)

| Agent | Home field(s) | Away cells tested |
|---|---|---|
| Rin (itoshi_rin) | EURUSD | GBPUSD, USDCAD |
| Barou (barou_shoei, v1.3) | USDCAD | EURUSD, GBPUSD |
| Chigiri (chigiri_hyoma) | EURUSD, GBPUSD | USDCAD |

Isagi, Bachira, Nagi, Reo already play all three symbols — no new
cells for them. Sae stays benched. No configuration knobs are swept:
every agent runs its DEPLOYED parameterisation (impulse 30, own
target_rr). This is a transfer test, not a re-tune.

## Method

ONE in-sample replay (2019-01-01 → 2023-12-31, H4 parquet, causal
D138 semantics, `aggregator_arm="phi41"`, live roster shape) with the
three symbol-restricted agents' symbol lists EXPANDED to all three
pairs (module-constant patch before `build_roster()`, own process).
Per-agent×symbol KPIs are read from the single replay's trades.

**Interaction caveat (declared up front):** expanding three agents
simultaneously changes aggregator/risk-cap interactions relative to
both deployment and Phase AF. The home cells (Rin/EURUSD,
Barou/USDCAD, Chigiri/EURUSD+GBPUSD) from this replay are therefore
reported against their Phase AF is_cell_30_0.0 references as an
interaction-shift check; a home-cell PF shift > 0.15 in either
direction flags the whole study `interaction_confounded` and the
REPORT must say so.

## Promotion rule (per away cell, declared before execution)

1. IS floors: PF ≥ 1.15 AND mean R ≥ +0.05 AND n ≥ 40.
2. 20 ≤ n < 40 with PF ≥ 1.15: `registered_near_miss` (Phase AF
   convention) — reported, not promoted, no validation spend.
3. Validation: ONE sealed replay 2024-01-01 → 2026-07-31 with the
   same expanded roster, run ONLY if at least one cell passes rule 1.
   Away cell PASSES if validation PF ≥ 1.10 AND mean R ≥ +0.03 AND
   n ≥ 15.
4. A PASS means: eligible for shadow-paper pitch time on the away
   symbol (a product-repo roster change, user-approved), still
   shadow-only. It does NOT mean live-order power — F018 stays
   default-off.

## Multiplicity accounting

5 away cells, single-shot validation only for rule-1 survivors. Under
a null of PF~1.0 noise, the joint floor (PF ≥ 1.15 AND meanR ≥ +0.05
AND n ≥ 40, then revalidated out-of-sample) has per-cell false-pass
probability well under 5%; with 5 cells the family-wise false-promotion
expectation stays < 0.25 promotions. Reported per-cell in the REPORT
with a binomial sketch, same as Phase AF; no p-value theatre.

## Contamination note

The sealed 2024–2026 window overlaps windows already seen in D139/AF
aggregate and home-symbol form. The 5 AWAY cells have never been
computed anywhere (Rin has never traded GBPUSD/USDCAD in any replay,
etc.), so their validation readouts are first-look; the overlap
caveat still rides along in any promotion, and any promoted cell
remains shadow-paper-only until a live measurement week corroborates.

## Outputs

- `results/is_expanded.json` — per agent×symbol KPIs, IS window.
- `results/val_expanded.json` — same, sealed window (only if rule 1
  fires).
- `REPORT.md` — per-cell verdicts, home-cell interaction check,
  honesty caveats.

## Abort conditions

- Replay crash or squad-wide zero trades → STOP_NOTICE, investigate.
- Home-cell interaction shift > 0.15 PF → `interaction_confounded`
  flag on all promotions (study still reported).
