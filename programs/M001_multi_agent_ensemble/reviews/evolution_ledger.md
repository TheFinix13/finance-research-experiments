# Evolution ledger — agent vN → vN+1 audit trail

**Status:** `OPEN` — started 2026-06-24 alongside `06-blue-lock-doctrine.md`
§3.11 (Agent Evolution Arcs).

This file is the binding record of every `vN → vN+1` event in the M001
roster. The per-agent sketches in `06-blue-lock-doctrine.md` §3.11.3
are *priors*, not commitments — this file is where actual evolutions
land once their §3.11.2 contract has been honoured.

## How to add a row

1. The defeat note `reviews/<agent_id>_vN_defeat.md` has been written.
2. The evolution hypothesis is stated in that note **before** vN+1 is
   implemented.
3. `sim/agents/aXX_<name>_v2.py` (or equivalent) exists next to the vN
   module, with regression + forward tests under `sim/tests/`.
4. vN and vN+1 are both registered in `sim/roster/` so the ablation can
   swap them via config.
5. Append a row to the table below with the seven fields. Update the
   *Outcome* field after the co-existence window closes.

Per `07-research-standards.md` §3, nothing is deleted from history; a
retired vN remains in the roster config for at least one full phase
gate, and its module stays on disk indefinitely.

## Tier-1 visibility

The ledger is Tier-1 read-only per `06-blue-lock-doctrine.md` §3.9.
The human dashboard renders it; the post-hoc evaluation harness reads
it; no agent reads it at decision time. Agents do not get to vote on
their own evolution.

## Ledger

| Date | Phase | Agent | vN → vN+1 | Trigger (defeat / phase / inspiration) | Hypothesis | Co-existence window | Outcome |
|---|---|---|---|---|---|---|---|

_(no rows yet — first evolution lands when an A1–A10 agent meets the
§3.11.2 contract on a documented defeat)_

## Standing notes

- **A1 Isagi v1** is the only currently-implemented striker (Φ3 gate
  `PASS` per `reviews/phi3_gate_isagi_v1.md`, commit `12c2bf4`). Its
  expected next evolution (sketch §3.11.3) is the metavision-sharpens
  arc — `zone_d1_against` vocabulary → full liquidity / FVG / OB
  primitives on H1. No defeat note has been written yet; v1 is the
  canonical Isagi until one lands.
- **A6 Nagi, A7 Barou, A10 Kunigami** are the Φ4 MVP parallel-worker
  targets; their v1 implementations are in flight and have not yet
  faced a defeat trigger.
- **A2 Bachira, A3 Rin, A4 Chigiri, A5 Reo, A8 Yukimiya, A9 Aoshi**
  are not yet implemented; their evolution sketches in §3.11.3 are
  *future-state* priors.
