# Phase AF report — causal re-tune of the M001 proposers (2026-08-04)

Protocol: `PROTOCOL.md` (registered before any cell ran). 8 in-sample
cells (impulse {20,30,40,50} × rr_delta {0,+0.5}, 2019–2023) + 3
validation replays (2024-01 → 2026-07), causal D138 semantics
throughout, live roster shape, phi41 aggregator.

## Verdicts per player

| Player | IS best cell | IS PF | Validation | Verdict |
|---|---|---|---|---|
| **Rin** | imp20/rr+0 | 1.228 (n=167) | variant 1.132 vs **deployed 1.136** (n=72, meanR +0.033) | **Deployed config VALIDATED causal — keep exactly as is.** Variant passed floors but did not beat the deployed config (rule 4), so no change. |
| **Nagi** | imp50/rr+0 | 2.652 (n=21) | n=10 < 15 → FAIL | No change. Real-looking but under-powered; every IS cell positive (PF 1.27–2.65). Watch in shadow. |
| **Barou** | imp50/rr+0 | 1.393 (n=26) | — (never promoted: n<40 floor) | Registered near-miss: positive in ALL 8 IS cells (PF 1.14–1.39) at n=23–30. Validation slice negative at tiny n (≤16). Inconclusive — needs more history or wider symbols, not a bench. |
| **Bachira** | best 0.975 | <1.0 in ALL 8 cells | not opened | `no_causal_edge_in_grid`. The rebellion (no D1 gate) does not survive causal zones at any impulse/RR in this grid. |
| **Isagi** | best 0.917 | <1.0 in ALL 8 cells | (see note) | `no_causal_edge_in_grid` for 2019–2023. |
| **Chigiri** | best 0.80 | <1.0 in ALL 8 cells | not opened | `no_causal_edge_in_grid`, worst of the roster (PF 0.68–0.80 IS). |
| **Reo** | — | **zero trades in every cell** | — | Not a research verdict — a plumbing question. A proposer that never proposes in 5 years of batch replay needs an intake (I-number) in the product repo. |

## The rule-4 anchor result (the headline)

Rin's DEPLOYED parameterisation — untouched — passes the sealed
2024–2026 window under causal semantics: PF 1.136, mean R +0.033,
n=72, +244 pips. Combined with D139's full-window causal readout
(PF 1.20, 2019–2026), Rin is the one player with a confirmed,
twice-measured causal edge. The squad's honest core is currently
Rin + (thin-sample) Nagi/Barou.

## Observational note (NOT a promotion — Phase AF-2 material)

Isagi at impulse 50 in the VALIDATION window: PF 1.331, +1,082 pips,
n=210 — while the same cell was his WORST in-sample (PF 0.853).
Promoting on this would be selecting on validation data (the exact
failure mode this program exists to prevent). But as a HYPOTHESIS it
is coherent: 2024–2026 is a different volatility regime, and strict
impulse thresholds may fit it better. A Phase AF-2 could pre-register
regime-conditioned thresholds (e.g. ATR-scaled impulse floors instead
of fixed pips — note `precompute` already scales by symbol, not by
regime) and test on data neither window has consumed (2016–2018
backfill, wider symbol set, or forward shadow weeks).

## Redesign directions per the user's no-benching directive

- **Bachira:** the no-gate rebellion was profitable only with the
  lookahead detector. Candidate redesigns: re-instate a gate (D1 or
  H4 structure) while keeping the rebel conviction mechanics; or move
  the rebellion to entry TIMING (limit at zone edge) rather than gate
  removal. Needs AF-2 pre-reg.
- **Isagi:** regime/ATR-conditioned impulse floor (observation above).
- **Chigiri:** his mechanics lose under causal zones everywhere —
  redesign should start from what his weapon is FOR (speed/late
  entries) rather than parameter nudges.
- **Barou/Nagi:** not broken — starved. Widening symbols or adding
  2016–2018 history are sample-size plays, not redesigns.

## Multiplicity

7 proposers × 8 cells read out; 2 promotions attempted; 1 passed
floors but lost to the deployed anchor; 1 failed n. No validation
readout influenced any promotion decision (Isagi observation
explicitly quarantined above).
