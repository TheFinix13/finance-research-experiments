# Phase AF — causal re-tune of the M001 proposer roster (pre-registration)

Registered: 2026-08-04 (before any sweep cell was executed).
Charter: multi-pair-trading-agent D139 (causality audit verdict) +
user directive 2026-08-04: Isagi/Bachira/Rin/Barou are core players —
the study's goal is to find causal-surviving parameterisations, with
benching only as a last-resort recommendation, never an automatic
outcome.

## Background and honesty note

The 2026-08-04 causality audit (product repo,
`reviews/audits/2026-08-04-prefix-parity/FINDINGS.md`, I027/D138)
found the shared zone detector's replay semantics were lookahead
(centered median voting on impulse validity; zones tradable before
their displacement closed; unconfirmed swings feeding structural TP).
Under corrected CAUSAL semantics, the 2019→2026 full-window replay
(D139) went from +29,207 pips / PF 1.52 to −2,324 pips / PF 0.95;
Rin survived (PF 1.20), Bachira (0.93) and Isagi (0.96) collapsed.

**Known contamination prior:** the D139 full-window per-agent causal
KPIs have been SEEN before this registration. This protocol therefore
(a) tunes only on the 2019–2023 in-sample window, (b) seals 2024-01-01
→ 2026-07-31 for one-shot validation per promoted configuration, and
(c) declares all floors below BEFORE any sweep cell runs. The overlap
between the seen full-window numbers and the sealed validation window
is unavoidable (the audit had to be run on everything); it is
mitigated, not eliminated. Any promotion from this study must carry
this caveat and remain shadow-paper-only until a live measurement week
corroborates it.

## Hypothesis

H-AF1: the old detector's lookahead median admitted low-quality zones
whose profitability was an artifact; under the causal trailing median,
a DIFFERENT impulse-quality threshold (and possibly a higher
reward:risk target) restores positive expectancy for some or all of
the collapsed proposers.

## Fixed infrastructure (not swept)

- Code: `multi-pair-trading-agent-product` worktree at or after commit
  `66c3bb7` (causal D138 semantics; S0 calendar fields).
- Engine: `SquadEngine.run_batch`, `aggregator_arm="phi41"`, live
  default roster shape (`build_roster()`, barou_v13=True, Sae benched).
- Data: H4 parquet cache (EURUSD, GBPUSD, USDCAD), read-only from the
  agent repo's `data/parquet`.
- Splits: IN-SAMPLE 2019-01-01 → 2023-12-31. VALIDATION 2024-01-01 →
  2026-07-31 (sealed; touched once per promoted config).

## Sweep grid (8 in-sample cells, declared exhaustively)

- Axis 1 — `cfg.detectors.zone_min_impulse_pips` ∈ {20, 30*, 40, 50}
  (* = deployed baseline).
- Axis 2 — `rr_delta` ∈ {0.0*, +0.5}: added to each zone-lineage
  agent's own locked `target_rr` (Isagi 1.5, Bachira 1.5, Barou-v13
  1.5, Chigiri 1.5, Rin 2.5). Nagi and Reo carry no `target_rr` knob
  and receive only Axis 1.

One replay per cell over the IS window; per-agent KPIs are read from
the same 8 replays (no per-agent reruns). No grid extension, no new
axes, without a dated amendment section in this file committed BEFORE
the extra cells run.

## Promotion rule (per proposer, declared before execution)

1. Candidate cell = argmax in-sample profit factor across the 8 cells,
   subject to IS `n_trades ≥ 40` for that agent (≥ 20 for Nagi and
   Reo, whose fire rates are structurally lower).
2. Promote to validation only if candidate IS PF ≥ 1.15 AND IS mean
   R ≥ +0.05.
3. Validation: ONE replay of the promoted cell's full config over the
   sealed window. Agent PASSES if validation PF ≥ 1.10 AND mean R ≥
   +0.03 AND n_trades ≥ 15.
4. Rin anchor: Rin's deployed config (30 pips, rr 2.5) is the
   reference. A Rin variant may only displace it if the variant PASSES
   validation and its validation PF exceeds the deployed config's
   validation PF measured in the same run.
5. Agents with no cell clearing rule 2: verdict is
   `no_causal_edge_in_grid` — the REPORT must propose the next weapon
   redesign direction; benching is a recommendation for the user, not
   an automatic action.

## Multiplicity accounting

7 proposers × 8 cells = 56 IS readouts, but selection is per-agent
argmax (7 selections); validation is single-shot per promoted config.
Expected false-promotion rate under the null at these floors is
reported in the REPORT using a per-agent binomial sketch; no p-value
theatre beyond that.

## Outputs

- `results/is_cell_<impulse>_<rrdelta>.json` — per-cell squad +
  per-agent KPIs (IS window).
- `results/validation_<agent>_<impulse>_<rrdelta>.json` — one per
  promoted config.
- `REPORT.md` — verdicts per agent, honesty caveats, recommendation.

## Abort conditions

- Any cell crashes or produces zero trades squad-wide → stop, file a
  STOP_NOTICE, investigate before resuming.
- Evidence of residual lookahead (prefix-parity regression failing on the
  product worktree) → the whole study is void.
