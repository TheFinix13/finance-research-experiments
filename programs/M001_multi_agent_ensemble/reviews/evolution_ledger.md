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
| 2026-06-24 | Φ3.5 (single-agent arc, post-Φ4 diagnosis) | A1 Isagi (`isagi_yoichi`) | v1 → v2 | **Defeat:** Φ4 squad-gate rejection analysis — 1579 / 2994 (52.7 %) of v1's rejections were *same-direction* with peers, i.e. v1's `zone_d1_against` vocabulary leaves dimensional space unused. See `reviews/isagi_yoichi_v1_defeat.md`. | Add a `liquidity_sweep` weapon (production `detect_liquidity_sweeps`) alongside the preserved zone weapon; sweep weapon takes the **D1-agree** side (inverse of zone's D1-against gate) — sweeps are confirmations of macro trend, zones are fades against it. H4 cadence retained; H1 cadence, FVG, OB deferred to a future arc. | Single-agent arc only (no co-existence window — verdict was negative). v1 stays canonical; v2 archived on disk. | **FAIL** — see `reviews/isagi_v2_arc.md`. Median OOS-window mean TQS dropped 0.317 → 0.240 (-0.078). The sweep weapon's standalone mean TQS (0.207) is materially below the zone weapon's (0.314); on this panel sweep proposals *cannibalise* zone slots in the single-position queue (v2 zone trades 311 vs v1 856) and the lower-edge sweep trades dominate the mix. Defeat trigger preserved; future arc may revisit with sweep-as-confluence-filter, tighter sweep HTF gate, or a multi-position simulator. |

## Standing notes

- **A1 Isagi v1** remains the canonical striker (Φ3 gate `PASS` per
  `reviews/phi3_gate_isagi_v1.md`, commit `12c2bf4`). The first arc
  attempt (v1 → v2, 2026-06-24) **FAILED** — see ledger row above and
  `reviews/isagi_v2_arc.md`. The v2 module
  `sim/agents/a01_isagi_v2.py` is retained on disk per the §3.11.2
  step 3 + `07-research-standards.md` §3 retention rule. A future v3
  arc may revisit the metavision-sharpens hypothesis with a different
  evolution structure (sweep-as-confluence-filter, FVG / OB primitives,
  H1 cadence, or multi-position simulator).
- **A6 Nagi, A7 Barou, A10 Kunigami** are the Φ4 MVP parallel-worker
  targets; their v1 implementations are in flight and have not yet
  faced a defeat trigger.
- **A2 Bachira, A3 Rin, A4 Chigiri, A5 Reo, A8 Yukimiya, A9 Aoshi**
  are not yet implemented; their evolution sketches in §3.11.3 are
  *future-state* priors.
