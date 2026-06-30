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
| 2026-06-25 | Φ4.1 post-mortem (no co-existence; sketch-level update) | A6 Nagi (`nagi_seishiro`) | v1 → v2 sketch retired | **Empirical (no defeat):** Φ4.1 telemetry shows v1 confluence floor is correct. With peer fuel Nagi fired 34,302 confluence-firing Thoughts → 94 trades at mean **TQS 0.349** (HIGHEST per-agent TQS in 8-agent squad). Relaxing floor would make Nagi less canonical, not more. | v2 sketch retired; new defeat trigger forward-looking (TQS regression across regime buckets, see `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1.3). | n/a (no v2 module ever shipped) | **DROP** — v1 canonical, v2 sketch retired. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1. |
| 2026-06-25 (Barou row amended 2026-06-30) | Φ4.1 post-mortem (no co-existence; redesign-level update) | A7 Barou (`barou_shoei`) | v1 → v2 sketch redesigned (hybrid A + B) | **Defeat:** live-ledger devour fired 0 times in 11 yrs × 2 runs (Φ4 + Φ4.1). Root cause #1: live disagreement between Isagi (USDCAD zone × D1-against) and Barou (USDCAD baseline zone, no D1 gate) is architecturally rare — they target different setups on the only shared symbol. Root cause #2 (Φ4.1): Barou opened 0 trades on the expanded roster — slot-cannibalised by Bachira's `+0.10` rebel-lift. | **Stacked mechanic A + B (user decision C-Q1 = both, 2026-06-30):** **(A)** devour reads Isagi's **closed losing trades** from the public ledger (Tier-1 post-fact); when an Isagi loss lands in Barou's coordinate space (USDCAD, last 24 H4 bars, within 1 ATR of a baseline-zone touch Barou would have proposed), Barou's NEXT-bar proposal conviction gets `+0.10` (cap 1.0). **(B)** Symbol whitelist `("USDCAD",)` → `("USDCAD", "EURUSD", "GBPUSD")` running baseline-zone (no D1 gate); USDCAD remains canonical specialty per E005 §2.5; devour lift remains USDCAD-only. **Honest-disagreement note:** prep worker recommended A alone in §2.4; user overrode to A + B. The forward-test conjunction (≥ 100 USDCAD devour-fire events AND ≥ 50 EURUSD/GBPUSD trades) is the falsifier — either half failing retires that half while the surviving half continues. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2 + 2026-06-30 amendment. | Pending v2 implementation (Φ5 or later sprint). Co-existence window declared at implementation time. | **REDESIGN (hybrid A+B)** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2 + 2026-06-30 amendment. |
| 2026-06-25 | Φ4.1 post-mortem (no co-existence; deferral) | A10 Kunigami (`kunigami_rensuke`) | v1 → v2 deferred | **Pre-condition not met:** Sentinel R1–R5 not yet wired into squad-gate harness. Φ4.1 emitted 25,877 Kunigami warning Thoughts but R5 dampener never consumed them. "Pre-emptive dampening" undefined against a Sentinel that does not consume warnings. | Retain v2 hypothesis (forward-looking ledger confidence aggregates). Un-deferring requires (1) R1–R5 wired (Φ4.2), (2) ≥ 100 OOS-window Sentinel-fire observations across `{trend, range, vol-expansion event}` regime buckets, (3) v1 baseline frequency-of-fire established in `reviews/kunigami_v1_sentinel_baseline.md`. | n/a until pre-conditions land. | **DEFER** — v2 deferred-pending-Sentinel-Φ4.2. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §3. |

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
- **A6 Nagi** v1 is **canonical (Φ4.1-validated)**. The v1 confluence
  floor produced 34,302 confluence-firing Thoughts → 94 trades at
  mean **TQS 0.349** (highest per-agent TQS in the 8-agent squad).
  v2 sketch **retired** (ledger row 2026-06-25). Future v2 reserved
  for a forward-looking regression-class defeat across regime buckets;
  no v2 module exists or is in flight.
- **A7 Barou** v1 is implemented but the live-ledger devour mechanic
  fired 0 times in 11 yrs × 2 runs (Φ4 + Φ4.1). v2 **REDESIGNED**
  (hybrid A + B per user decision 2026-06-30, ledger row 2026-06-25
  amended 2026-06-30). Implementation pending. The hybrid stacks
  closed-loss replay (mechanic A) and symbol-whitelist expansion to
  EURUSD/GBPUSD/USDCAD baseline-zone (mechanic B).
- **A10 Kunigami** v1 is implemented; **25,877 warning Thoughts**
  emitted at Φ4.1 but **0 consumed** by Sentinel R5 (R1–R5 not yet
  wired into the squad-gate harness). v2 **DEFERRED** pending Φ4.2
  Sentinel wiring + ≥ 100 OOS-window Sentinel-fire observations
  + v1 baseline frequency-of-fire established (ledger row 2026-06-25).
- **A2 Bachira, A3 Rin, A4 Chigiri, A5 Reo** are now **v1 implemented
  (Φ4.1 squad gate)** — Bachira 2840 trades (TQS 0.308, dominates
  slot allocation via `+0.10` rebel-lift), Rin 244 trades (TQS 0.277,
  precision-lift), Chigiri 536 trades (TQS 0.229, breakout primitive),
  Reo 0 trades by design (28,469 mirror Thoughts emitted). Their
  Φ4.1-telemetry-informed v2 sketch revisions are pending a round-2
  resolution doc per `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §6 Q5 (user decision 2026-06-30: revise all four).
- **A8 Yukimiya, A9 Aoshi** remain **not yet implemented**; their
  evolution sketches in `06-blue-lock-doctrine.md` §3.11.3 are
  *future-state* priors with no Φ4.1 empirical revision required
  (no telemetry yet).
