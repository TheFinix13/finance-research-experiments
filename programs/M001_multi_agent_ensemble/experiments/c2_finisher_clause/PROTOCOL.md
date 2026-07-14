# C2 finisher clause — receiver-role C2 amendment (pre-registration, ADVISORY)

- **Registered:** 2026-07-14 (committed BEFORE any C2-finisher number
  is computed on fresh replays).
- **Program:** M001 multi-agent ensemble.
- **Parent gate:** `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §3
  Criterion 2; formal amendment logged as G7 §11.17 (campaign Lever D).
- **Status of verdicts under this clause:** **ADVISORY ONLY** until the
  user ratifies the amendment. C2 as written (outgoing lift) remains
  the verdict-bearing definition for any G7 gate attempt until
  ratification — the same pattern as C3 v2 (§11.14). This clause is a
  GATE-DEFINITION change, not a code-behaviour change: no trade stream
  moves.

---

## 1. Motivation (banked evidence + canon)

C2 as written asks: *does removing agent `a` hurt some peer?* — it
measures **outgoing** lift. Nagi is canonically the FINISHER (user
directive 2026-07-14: *"players complement him, he doesn't complement
them — Nagi is a control genius no one can predict"*; doctrine §3.11.3
A6: v1 confluence floor "correct as-shipped"). A confluence-only agent
*structurally cannot* generate outgoing lift at his volume: he fires
only where ≥ 2 peers already fired (his thoughts are echoes of theirs,
adding no new coordinates for peers to read), and his n = 67 OOS
trades (§11.16 phi41) sit far below what the bootstrap-CI gate can
resolve. The structure of the failure is role-shaped, exactly like
Reo's C1/C5/C6 waivers (§11.1): the criterion measures a thing the
role is designed not to do.

Banked evidence that the *incoming* direction is where Nagi's
chemistry lives:

- Φ5 §11.7 chemistry re-baseline (arm4, 2026-07-06): Nagi has THREE
  lifting peers — Bachira +0.1806, Rin +0.0624, Reo +0.0504 TQS —
  the strongest incoming-chemistry profile on the roster; C7 pass;
  role labels `finisher, workspace_catalyst` (Role Registry v1,
  RETAINED).
- §11.16 `g7retry1` phi41 final verdict: in the C2 evaluations of
  **bachira_meguru** and **itoshi_rin**, the qualifying peer is
  `nagi_seishiro` in both cases (dTrades +51, CI [4.86, 10.0];
  dTrades +42, CI [2.86, 9.71]) — two independent
  statistically-qualified INCOMING lifts, under the evaluator's own
  bootstrap-CI letter.

## 2. Definition (locked BEFORE evaluation on fresh replays)

**Finisher clause.** In a G7 final-verdict evaluation, agent `a`
satisfies Criterion 2 via the finisher clause iff BOTH:

1. **Role eligibility:** `a`'s playstyle is confluence-gated — the
   agent cannot propose without prior same-tick-window peer thoughts.
   Locked eligibility set: `{"confluence_only"}` (currently only
   `nagi_seishiro`). Extending the set requires a new amendment.
2. **≥ 2 statistically-qualified incoming lifts:** there exist at
   least 2 distinct peers `p ≠ a` such that in the C2 evaluation of
   `p` (excluded = `p`, same replays, same bootstrap spec), `a` is a
   qualifying peer — i.e. removing `p` significantly hurts `a` under
   the evaluator's existing CI-gated letter (TQS route or trade-count
   route). No new statistic is invented; the clause REUSES the locked
   C2 qualification test, pointed the other way.

Reported statistic: the number of qualified incoming lifts and the
lifting peers. Thresholds (bootstrap n = 10,000, seed 42, percentile,
α = 0.05) are the evaluator's existing constants — nothing is retuned.

**Waiver semantics:** a finisher-clause pass is reported as `W`
(waiver-style) in the advisory bit vector, distinguishable from a
plain `1`, mirroring how Reo's §11.1 waivers render.

## 3. Implementation + evaluation plan

- `sim/scoring/run_g7_final_verdict.py`: new pure function
  `evaluate_c2_finisher_clause(...)` + CLI flag
  `--c2-finisher-clause`. When the flag is ON the report gains, per
  eligible agent, an `advisory_c2_finisher` block (clause outcome,
  lifting peers, evidence) and an `advisory_squad_verdict_with_clause`
  field. The **verdict-bearing bit vectors and squad verdict are
  byte-identical with the flag on or off** — enforced by unit test.
- Unit tests BEFORE results: (a) clause requires ≥ 2 qualified
  incoming lifts (1 is not enough); (b) non-eligible playstyles never
  get the clause; (c) verdict-bearing outputs unchanged by the flag;
  (d) advisory squad count uses the clause pass for eligible agents
  only.
- Evaluated on the `g7retry2` replays (§11.17) alongside the
  verdict-bearing run, both arms.

## 4. Multiplicity / honesty note

This clause is designed KNOWING it would pass on the banked `g7retry1`
caches (§1 evidence — 2 qualified incoming lifts already exist under
phi41). That is deliberate and disclosed: like Reo's structural
waivers, the clause is derived from the agent's designed role, and the
banked numbers demonstrate the role is real rather than calibrate a
threshold. The clause still faces fresh data at `g7retry2` (Phase Z
cuts Bachira's volume — his incoming lift to Nagi is NOT guaranteed to
survive), so the advisory evaluation is falsifiable, not a rubber
stamp. Ratification (promote to verdict-bearing, keep advisory, or
reject) is the USER's decision; this protocol changes no verdict on
its own.

## 5. Artifacts

- Advisory blocks inside
  `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`.
- Ratification record: G7 PROTOCOL §11.17/§11.18 amendment text.
