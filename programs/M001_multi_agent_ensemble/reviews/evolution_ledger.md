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
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A2 Bachira (`bachira_meguru`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 rebel-lift fired 46,584 times unconditionally; slot-cannibalised Isagi + Barou (0 trades each); produced 76 % of squad's 3,714 trades. v0.3 sketch's peer-silence spirit was correct; v1 inverts to peer-saturation. | Narrow rebel-lift to peer-silence OR peer-disagreement gated trigger; base conviction 0.65 elsewhere. | Pending v2 implementation (Φ5 aggregator work may obviate via HRP downweighting; revisit ordering after Φ5 verdict). | **REFINE-to-peer-silence** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §1. |
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A3 Rin (`itoshi_rin`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 precision-lift fired 3,094 times; 244 trades at +9.95 mean / −28.26 median (right-tail-concentrated). v0.3 regime-gate targeted retired classes (vol_spike, news). | Regime-gate to live-classes `trending` only; retain v1 R:R + stop-distance filter; add peer-disagreement requirement (Chigiri/Bachira opposite-direction prior-tick Thought at conviction ≥ 0.65). | Pending v2 implementation. | **REFINE-regime+peer-disagreement** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2. |
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A4 Chigiri (`chigiri_hyoma`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 breakout-firing produced 3,615 Thoughts → 536 trades at +6.62 mean / −26.67 median, TQS 0.229, win 39.9 % (lowest among trading agents). v0.3 sketch already in v1; active defeat is whipsaw losses on early-stage σ expansions. | Multi-TF ADX alignment (M15 × H1 × H4 all rising) + top-decile σ floor (replaces v1's top-quartile). Three conjunctive guards. | Pending v2 implementation. | **REFINE-multi-TF-ADX+ATR-percentile** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §3. |
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; advancement-level update) | A5 Reo (`reo_mikage`) | v1 → v2 sketch advanced (HRP + Φ5-second-position) | **Empirical (no defeat):** v1 ships structural Tier-2 falsifier; 28,469 mirror Thoughts emitted, 0 trades. Falsifier worked. Φ4.1 FAIL diagnosis pinned the binding constraint at the single-position queue — Reo is the natural occupant of the second slot under Φ5 multi-position policy. | Stacked mechanic 1 (HRP-weighted mixture of top-K ≥ 2 trailing-TQS agents, from v0.3) + mechanic 2 (second-position proposer when first leader's slot is contested under Φ5 Arm 4 / K = 2). Mechanic 2 gated on Φ5 Arm 4 landing. | Pending v2 implementation; mechanic 2 deferred until Φ5 Arm 4 ships. | **ADVANCE-coupled-to-Φ5-multi-position** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4. |
| 2026-06-30 | Φ4.2 mini-sprint (infrastructure, no agent version change) | Sentinel (`sim/core/sentinel.py`) | R1–R5 + new R6 wired into harness | **Pre-condition unblocker:** Sentinel R1–R5 unit-tested but not wired into `run_phi4_squad_gate.py::_drive_squad_replay`; Kunigami's 25,877 Φ4.1 warning Thoughts had 0 R5 consumers. User decision Q-AGG-1 (2026-06-30) — no deferrals: wire the harness now. | Extend `SentinelContext` with `kunigami_loss_streak_active`, `consecutive_losses`, `open_symbol_risk_dollars`, `additional_risk_dollars`. Add R6 (per-symbol total-risk cap, 1 % equity default) for Φ5 Arm 4 multi-position. Add `evaluate_proposal(proposal, context)` helper so callers don't need to synthesize an `OrderIntent`. Wire into `_drive_squad_replay(..., sentinel_blocks=False)` — audit-only for Φ4 / Φ4.1 replay fidelity; physically blocking in Φ5 via `sentinel_blocks=True`. New tests `sim/tests/test_sentinel_wired.py` (11 tests, all passing). PROTOCOL §11.1 amendment retires §6 stop rule #3. | n/a (infrastructure change; no vN roster row). | **WIRED** — 291 sim tests passing (was 280 pre-Phase-4, +11 Sentinel wiring tests). See `experiments/phi5_aggregator/PROTOCOL.md` §11.1 amendment. |
| 2026-06-30 | Φ4.2 mini-sprint (v2 status transition, no new agent code) | A10 Kunigami (`kunigami_rensuke`) | v2 DEFERRED → WIRED | **Pre-condition met:** Sentinel R1–R6 wired 2026-06-30 (ledger row above). Kunigami's `warning_active_at(as_of)` accessor is now polled by `SentinelContext.kunigami_loss_streak_active` in `_drive_squad_replay`. | v2 mechanic = Sentinel consumer wiring (not new agent code). Kunigami v1's two predicates (loss-streak, overconfidence) unchanged; the un-blocked path is R5's 50 %-risk-scale dampener consuming Kunigami's 24-h warning window. Audit-only in Φ4 / Φ4.1 (preserves sealed verdicts), physically blocking in Φ5. | v2 is the consumer wiring, not a new module — no separate co-existence window. v3 revisit gated on ≥ 100 R5 activations across `{trending, chop}` regimes in Φ5 aggregator gate. | **WIRED** — Sentinel R5 consumer online. See doctrine §3.11.3 A10 + roster §3.10. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A2 Bachira (`bachira_meguru`) | **RELABEL:** v1 → v2 (2026-06-30) reclassified as v1 mechanic-iteration-1 | **Doctrinal reframe (not a defeat):** user 2026-07-01 decision on Phase 6 completion redefined v1 as "checkpoint state where the agent demonstrates undeniable positive results AND functions as a positive-sum cog in the squad." Bachira has neither yet (§3.11.5 criterion #3 fails — 46,584 rebel-lift fires in Φ4.1 slot-cannibalised Isagi and Barou to 0 trades). The peer-silence-gate mechanic ships as v1 mechanic-iteration-1, not as v2. | Same mechanic content as the 2026-06-30 row (peer-silence OR peer-disagreement gate on rebel-lift). Under §3.11.5 this is a v1 tuning, not a v2 evolution — v2 label reserved for post-G7 architectural additions that trump a proven v1. | n/a (labelling amendment; original row above retained per `07-research-standards.md` §3). | **RELABEL** — v1 mechanic-iteration-1 pending G7. Amends the 2026-06-30 row above. See doctrine §3.11.5 + `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §1. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A3 Rin (`itoshi_rin`) | **RELABEL:** v1 → v2 (2026-06-30) reclassified as v1 mechanic-iteration-1 | **Doctrinal reframe:** same as Bachira row above — user 2026-07-01 v1/v2 reframe applied. Rin's regime-gate + peer-disagreement mechanic ships as v1 mechanic-iteration-1, not as v2. | Same mechanic content as the 2026-06-30 row (regime-gate to `trending` + peer-disagreement requirement). | n/a (labelling amendment). | **RELABEL** — v1 mechanic-iteration-1 pending G7. Amends the 2026-06-30 row above. See doctrine §3.11.5 + `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A4 Chigiri (`chigiri_hyoma`) | **RELABEL:** v1 → v2 (2026-06-30) reclassified as v1 mechanic-iteration-1 | **Doctrinal reframe:** same as Bachira row above. Chigiri's three conjunctive guards (M15×H1×H4 ADX + top-decile σ + 20-bar high/low) ship as v1 mechanic-iteration-1. | Same mechanic content as the 2026-06-30 row. | n/a (labelling amendment). | **RELABEL** — v1 mechanic-iteration-1 pending G7. Amends the 2026-06-30 row above. See doctrine §3.11.5 + `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §3. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A5 Reo (`reo_mikage`) | **RELABEL:** v1 → v2 (2026-06-30) reclassified as v1 mechanic-iteration-1 (mechanic 1 only) + post-G7 v2 candidate (mechanic 2) | **Doctrinal reframe:** the HRP-mixture mechanic ships as v1 mechanic-iteration-1 (it makes Reo a functional structural falsifier participant, not a new capability). The Φ5-second-position mechanic remains a genuine v2 candidate (adds a capability Reo v1 cannot express) but defers to post-G7 per §3.11.5 squad-chemistry mandate. | Split: mechanic 1 (HRP mixture) → v1 iter-1; mechanic 2 (second-position) → post-G7 v2 candidate. | n/a (labelling amendment for mechanic 1; mechanic 2 co-existence window declared at implementation). | **RELABEL + SPLIT** — mechanic 1 = v1 iter-1 pending G7; mechanic 2 = v2 candidate deferred to post-G7. Amends the 2026-06-30 row above. See doctrine §3.11.5 + `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A7 Barou (`barou_shoei`) | **RELABEL:** v1 → v2 (2026-06-25 + 2026-06-30 amendment) reclassified as v1 mechanic-iteration-1 | **Doctrinal reframe:** the hybrid A + B mechanic ships as v1 mechanic-iteration-1. Barou's v1 has never had a passing test (0 trades in Φ4.1 + 0 devour fires in 11 yrs × 2 runs); the hybrid mechanic is the *first* attempt at a working v1, not an evolution beyond one. | Same mechanic content as the 2026-06-25 (amended 2026-06-30) row: **(A)** closed-loss replay from Isagi's public ledger, USDCAD-only, 24 H4-bar lookback; **(B)** symbol whitelist expansion to `("USDCAD", "EURUSD", "GBPUSD")` running baseline-zone. | n/a (labelling amendment). | **RELABEL** — v1 mechanic-iteration-1 (hybrid A+B) pending G7. Amends the 2026-06-25 + 2026-06-30 rows above. See doctrine §3.11.5 + `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2. |
| 2026-07-01 | Reframe (doctrine v0.5 §3.11.5 landing) | A10 Kunigami (`kunigami_rensuke`) | **RELABEL:** v2 WIRED (2026-06-30) reclassified as v1 primitive (Sentinel plumbing, not agent evolution) | **Doctrinal reframe:** `warning_active_at(as_of)` is a v1 feature of Kunigami (the loss-streak reflection primitive); Sentinel R5's consumption of it is Sentinel-side plumbing, not a Kunigami evolution. Under §3.11.5 this is Kunigami's canonical v1 mechanic, and the "v2 WIRED" label was over-scoped. | No mechanic change. Kunigami v1 = warning_active_at + Sentinel R5 consumer (both v1); v2 candidacy reserved for a forward-looking pre-emptive-dampening capability that trumps v1's post-loss warning. | n/a (labelling amendment). | **RELABEL** — v1 primitive (not v2). Amends the 2026-06-30 row above. See doctrine §3.11.5 + doctrine §3.11.3 A10. |

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
- **A10 Kunigami** v1 code + v2 **WIRED 2026-06-30** (Φ4.2 mini-sprint
  ledger row). Sentinel R5 now polls `warning_active_at(as_of)` on every
  accepted proposal via `SentinelContext.kunigami_loss_streak_active`;
  audit-only in Φ4 / Φ4.1 replay (sealed verdicts preserved), physically
  blocking in Φ5 via `sentinel_blocks=True`. Kunigami's 25,877 Φ4.1
  warning Thoughts are now the R5 audit stream on any re-run.
  v3 revisit gated on ≥ 100 R5 activations observed in Φ5 aggregator
  gate across `{trending, chop}` regimes.
- **A2 Bachira, A3 Rin, A4 Chigiri, A5 Reo** are now **v1 implemented
  (Φ4.1 squad gate)** and have round-2 v2 sketch resolutions
  (ledger rows 2026-06-30) per `reviews/v2_arc_backlog_resolution_
  round2_2026-06-30.md`:
  - **A2 Bachira REFINE-to-peer-silence** — narrow rebel-lift
    trigger from unconditional to peer-silence OR peer-disagreement.
  - **A3 Rin REFINE-regime+peer-disagreement** — regime-gate to
    `trending` (live-classes-only); add peer-disagreement
    requirement.
  - **A4 Chigiri REFINE-multi-TF-ADX+ATR-percentile** — three
    conjunctive guards (M15×H1×H4 ADX rising, top-decile σ,
    20-bar high/low).
  - **A5 Reo ADVANCE-coupled-to-Φ5-multi-position** — HRP mixture
    (mechanic 1) + second-position proposer under Φ5 Arm 4
    (mechanic 2, Φ5-gated).
  Implementation pending; Bachira v2 may be obviated by Φ5 HRP
  downweighting; Reo v2 mechanic 2 depends on Φ5 Arm 4 shipping.
- **A8 Yukimiya, A9 Aoshi** remain **not yet implemented**; their
  evolution sketches in `06-blue-lock-doctrine.md` §3.11.3 are
  *future-state* priors with no Φ4.1 empirical revision required
  (no telemetry yet).
- **Sentinel R1–R6 infrastructure** wired into `_drive_squad_replay`
  on 2026-06-30 (Φ4.2 mini-sprint). Unit tests: `sim/tests/test_sentinel.py`
  (16, unchanged); integration tests: `sim/tests/test_sentinel_wired.py`
  (11 new). New R6 = per-symbol total-risk cap (1 % equity default),
  built specifically for Φ5 Arm 4 multi-position. Sentinel is audit-only
  in the Φ4 / Φ4.1 harnesses (preserves sealed verdicts) and physically
  blocking in the Φ5 harness via `sentinel_blocks=True`. See
  `experiments/phi5_aggregator/PROTOCOL.md` §11.1 amendment retiring
  the previous §6 stop rule #3 (Sentinel-blocker deferral of Arm 4).
- **2026-07-01 v1/v2 reframe (doctrine v0.5 §3.11.5).** The user's
  Phase 6 completion decision redefined v1 as "checkpoint where the
  agent demonstrates undeniable positive results AND functions as a
  positive-sum cog in the squad" (not "the code the agent was born
  with"). Under this reframe, the six previously-labeled "v1 → v2"
  resolutions from 2026-06-25 / 2026-06-30 are reclassified as **v1
  mechanic iterations pending G7** (the v1-checkpoint gate). The
  original v2-labelled rows above are retained per `07-research-
  standards.md` §3 with companion **RELABEL-2026-07-01** rows citing
  doctrine §3.11.5 as the authoritative source. Reo's mechanic 2
  (Φ5-second-position proposer) is split off as a genuine post-G7 v2
  candidate. **Only A1 Isagi is at v1** (Φ3 PASS analog); the
  Isagi v1→v2 arc that FAILED 2026-06-24 is the sole true v2
  attempt to date. Three new v1 primitives are pre-registered — F19
  `lot_intent`, F20 `risk_intent`, F21 `read_workspace` — per doctrine
  §4.1a; every implemented agent must ship these before G7 fires.
  See `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` for the formal
  pre-registration.
