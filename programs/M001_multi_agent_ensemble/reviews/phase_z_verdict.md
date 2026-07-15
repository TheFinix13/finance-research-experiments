# Phase Z verdict — Bachira v1.4 weave weapon (Lever A, §11.17 campaign)

- **Protocol:** `experiments/phase_z_bachira_weave/PROTOCOL.md` (registered
  2026-07-14, committed before implementation results).
- **Evaluated:** 2026-07-15 on the §11.17 `g7retry2` replays (single
  pre-registered OOS touch). Baselines are the §11.16 `g7retry1` numbers.
- **Evidence:** `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`,
  `reviews/g7retry2_lever_audits.json`.

## Verdict: **FAIL (Z5)** — C3 flipped exactly as designed, but the
pre-registered Nagi-fuel interaction risk fired

Per the locked letter (§4): PASS iff Z1 AND Z3 AND Z4 AND Z5. Z1, Z2,
Z3, Z4 all pass; Z5 fails. The protocol names this outcome explicitly:
*"A Nagi C1 break attributable to Bachira volume loss is a Phase Z
failure even if Z1–Z4 hold."*

| Criterion | Locked threshold | Result | Pass |
|---|---|---|---|
| Z1 — C3 flip (primary) | Bachira C3 clean windows ≥ 4/7 phi41 (was 0/7) | **7/7 clean** phi41 (worst per-window reduction 0.09); arm4 7/7 (was 3/7) | ✅ |
| Z2 — signal-tick disjointness | Bachira×Barou same-tick same-symbol fired proposals = 0 | **0** in both arms (audit over `proposals_all.jsonl`) | ✅ |
| Z3 — Bachira retention | C1 pass + ≥ 150 OOS trades + C2/C4/C5/C6 kept | C1 0.3878 (7/7 windows, CI low 0.359 > 0.25), **n = 733** (≥ 150), C2 pass (nagi qualifies), C4 3620, C5 0.4728, C6 0.1523 — all pass | ✅ |
| Z4 — squad TQS tolerance | within −0.02 of §11.16 per arm | phi41 Δ −0.0112; arm4 Δ −0.0141 | ✅ |
| Z5 — Nagi fuel guardrail | Nagi C1 stays a pass | **Nagi C1 0.1966 FAIL** (was 0.436 pass); n 67 → **21**, 2/7 windows ≥ 0.20, CI [0.035, 0.407] | ❌ |

## Attribution (why this is a Z5 hit and not incidental)

- Bachira OOS volume halved by the weave gate: 1468 → 733 (phi41),
  2035 → 764 (arm4) — the D1-neutral fire set is roughly half of his
  v1 fire set, as the gate predicts.
- Nagi is confluence-gated and Bachira is his primary fuel (Φ5 §11.7:
  +0.18, his strongest lifter). Nagi's OOS volume collapsed with it:
  67 → 21 (phi41), 79 → 25 (arm4). At n = 21 his window means zero out
  in 4/7 windows.
- No other agent lost a criterion in a way attributable to Bachira
  (Isagi/Rin/Reo passes unchanged).

## Consequences per stop rules

- Phase Z **STOPS** (protocol §5 rule 1): no re-tuning of the weave
  gate against the same OOS windows. A successor (e.g. a weave gate
  that keeps Bachira's thought/publish stream at v1 volume while
  gating only his own proposals — Nagi feeds on thoughts, not trades)
  requires a fresh protocol flagged attempt #2.
- The mechanism itself is validated: Z1 + Z2 confirm the D1-bias-space
  partition eliminated the Barou cannibalisation exactly as the canon
  design intended, with zero same-tick overlap. What failed is the
  side-effect budget, on the axis the protocol itself flagged.
- Bachira's own 6-bit vector is a full pass (`111111` phi41) for the
  first time in G7 history.

## Status of the code

`weapon_weave=True` remains the committed default pending the user's
adoption call at the §11.18 review (keep weave + fix Nagi fuel in a
follow-up lever, or revert the default to v1). Reverting is a
one-parameter change; both behaviours are pinned by unit tests.
