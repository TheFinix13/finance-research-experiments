# Phase Z — Bachira v1.4 weave-weapon differentiation (pre-registration)

- **Registered:** 2026-07-14 (committed BEFORE any result is computed).
- **Program:** M001 multi-agent ensemble.
- **Authorization:** user authorized a four-lever third-attempt campaign
  2026-07-14 with explicit canon guidance: *"Bachira is based off pure
  dribbling — figure out how to canonically apply this"*; make his
  setups structurally disjoint from Barou's decisive strikes.
- **Lever slot:** Lever A of the G7 §11.17 third-attempt campaign.
  Target blocker: **Bachira C3 = 0/7 clean windows (phi41), worst peer
  = Barou in every window** (§11.16).
- **Evaluation vehicle:** the G7 re-gate replays pre-registered in G7
  PROTOCOL §11.17 (tag `g7retry2`) — the OOS windows are touched
  exactly once, jointly for all four campaign levers.

---

## 1. Problem (banked evidence)

§11.16 falsified the duplication story: Phase Y v1.3 pushed the
Bachira→Barou worst-peer duplicate share from 89 % to **0.0 %** under
phi41, yet Bachira still fails C3 v1 AND C3 v2 (0/7 clean windows;
worst-window reductions 0.65–0.91, worst peer `barou_shoei` in all 7).
Bachira genuinely suppresses Barou's *distinct* trades. Mechanism (from
the banked caches, no new compute): Bachira fires on EVERY baseline
zone touch on all three pairs (no HTF gate) at conviction 0.65–0.80
(rebel lift + Isagi peer-confluence lift), so on USDCAD ticks where
Barou's D1 with-trend weapon fires at base 0.65 (+ situational lifts),
Bachira usually wins the single-position slot. The slot mutex, not
geometry duplication, is the residual suppression channel — the exact
failure family §11.9/§11.11 established cannot be fixed by conviction
mechanics on the *loser's* side. Phase Z fixes it on the *winner's*
side: shrink Bachira's fire set to the subset that is structurally
disjoint from Barou's.

## 2. Canon → mechanism mapping (doctrine + banked evidence ONLY)

Canon (user directive + doctrine §3.1 "monstrous dribble"): Bachira's
weapon is **pure dribbling** — he thrives when the pitch is CROWDED,
weaving through defenders where there is no open lane. Barou (roster
§3.7) is the king striking down the open lane; Isagi (roster §3.1)
exploits the defence's overcommitment against the lane.

Operational translation: the "open lane" is a directional D1 trend
(the same `htf_bias_at` read Isagi's and Barou's locked cells already
use). The squad's three zone-family strikers partition the D1-bias
space:

| Agent | D1 gate | Canon read |
|---|---|---|
| Isagi v1 | `against` — D1 bias OPPOSES the zone direction | exploit the overcommitted defence |
| Barou v1.3 | `with` — D1 bias MATCHES the zone direction | strike down the open lane |
| **Bachira v1.4** | **`neutral` — NO D1 bias (no lane at all)** | **weave through congestion** |

**Bachira v1.4 weave gate:** Bachira fires a baseline-zone touch iff
`htf_bias_at(bars, i, htf="D1", htf_lookback=10, min_move_pips=60.0)`
returns **NEUTRAL** — i.e. the last 10 D1 bars show no ≥ 60-pip net
move. No lane, defenders packed in the box: dribble time. On any tick
where the D1 bias is UP or DOWN, Bachira abstains (observation-only
Thought, `bachira_weave_abstain` reason).

Locked parameters (`BACHIRA_V14_WEAVE_PARAMS`):

| Param | Value | Source (no new tuning) |
|---|---|---|
| `htf` | `"D1"` | Same HTF the two sibling gates read |
| `htf_lookback` | `10` | Copied verbatim from `ISAGI_V1_PARAMS` (E001-derived, locked 2026-06-24) |
| `htf_min_move_pips` | `60.0` | Same — copied verbatim, zero re-tuning |
| gate predicate | `bias is NEUTRAL` | The set-complement of the two locked sibling gates — not a searched value |

Everything else in Bachira v1 is UNCHANGED: inner
`SupplyDemandAlpha(htf_align=None, target_rr=1.5)`, symbols
(EURUSD/GBPUSD/USDCAD), rebel lift (+0.10, 3-bar opposite-swing
predicate), Isagi peer-confluence lift (+0.05), playstyle
`rebel_tight`, tier 2, F19/F20 dispersion-r2 primitives.

**Structural disjointness guarantee:** `htf_bias_at` returns exactly
one of {UP, DOWN, NEUTRAL} per bar. Barou v1.3 requires
`bias.matches(direction)` (UP∧long or DOWN∧short); Bachira v1.4
requires NEUTRAL. Therefore Bachira and Barou can never propose from
the same signal tick on any shared symbol — the slot contention that
produced 7/7 dirty C3 windows is removed mechanically, not
probabilistically. (Residual suppression via open-position occupancy
across ticks remains possible and is what the C3 statistic will
measure.) The same argument makes Bachira disjoint from Isagi's
against-gated fire set on the SIGNAL tick.

Empirical priors (banked, honestly stated):

- E001 (audit §2.1): on EURUSD, `zone_d1_against` beats baseline
  `zone` — the against-subset carries the edge there. E005 (audit
  §4.3): on USDCAD the baseline beats the against-gate. Neither study
  split out the NEUTRAL subset; there is **no banked per-subset
  expectancy for D1-neutral zone touches**. This is a genuine
  uncertainty of this design, accepted because the lever's target is
  C3 (squad chemistry), with C1 retention as a guardrail criterion,
  not the payoff.
- §11.16: Bachira C1 = 0.386 at n = 1,468 (phi41 OOS). The weave gate
  strictly shrinks his fire set, so n will drop materially. The C1
  guardrail below carries an explicit activity floor.

## 3. Implementation plan

- `sim/agents/a02_bachira.py`: add `BACHIRA_V14_WEAVE_PARAMS`;
  constructor flag `weapon_weave: bool = True` (legacy v1 weapon
  retained behind `weapon_weave=False` for cache-reproduction tests).
  Weave gate applied in `observe()` (before the inner-alpha signal is
  turned into a Thought) so abstention is visible in the thought
  stream; `intend()` re-checks it (same double-check pattern the
  inner alpha already provides for the signal itself). Rationale
  stamps `weapon: bachira_v14_weave` + the gate params + the bias
  value at fire time.
- Harness: `run_g7_v1_checkpoint_gate.py` + `run_g7_leave_one_out.py`
  instantiate Bachira with the v1.4 default. Sealed pre-Z caches are
  on disk and are never regenerated.
- Unit tests BEFORE results: (a) gate params reach `htf_bias_at`
  verbatim; (b) `weapon_weave=False` reproduces the v1 fire set on a
  fixture; (c) weave-gate/with-gate disjointness on a synthetic
  series: for every (tick, direction) where a v1.3-parametrised
  with-gate fires, Bachira v1.4 abstains; (d) NEUTRAL tick fires with
  unchanged geometry (entry/stop/TP identical to v1 on that tick).

## 4. Success criteria (locked; evaluated ONCE on the §11.17 re-gate replays)

Baselines referenced below are the §11.16 `g7retry1` numbers.

- **Z1 — C3 flip (primary):** Bachira C3 v1 clean windows ≥ 4/7 under
  phi41 (was 0/7). Report arm4 alongside (was 3/7).
- **Z2 — signal-tick disjointness (manipulation check):** in the
  `g7retry2` baseline replay, the number of ticks where Bachira and
  Barou both emit a fired Thought on the same symbol at the same tick
  = **0** (from the thought/proposal streams; audit).
- **Z3 — Bachira retention guardrail:** Bachira keeps C1 pass (mean
  ≥ 0.30, ≥ 5/7 windows ≥ 0.20, CI low > 0.25) AND ≥ 150 OOS trades
  (phi41) AND keeps C2/C4/C5/C6 passes. Below 150 trades is reported
  as a capacity failure of the weave weapon.
- **Z4 — no squad regression:** squad mean-of-window-mean TQS within
  **−0.02** of the §11.16 baseline in each arm (shared tolerance with
  the other campaign levers; the joint movement is assessed once).
- **Z5 — Nagi fuel guardrail (named interaction risk):** Nagi C1
  stays a pass (his confluence volume is majority-fueled by Bachira
  thoughts — Φ5 §11.7: Bachira is Nagi's primary lifter +0.18).
  A Nagi C1 break attributable to Bachira volume loss is a Phase Z
  failure even if Z1–Z4 hold.

**Phase verdict:** PASS iff Z1 AND Z3 AND Z4 AND Z5 (Z2 is a
manipulation check — its failure invalidates the causal story and
forces a postmortem regardless of the other criteria). Anything else
is FAIL or PARTIAL with the failing criteria named.

## 5. Stop rules / anti-leakage

1. One evaluation. If the pre-registered criteria fail, the lever
   STOPS — no parameter iteration against the same OOS windows. A
   further attempt requires a fresh protocol flagged as attempt #2
   with multiplicity noted.
2. No post-freeze retuning of `BACHIRA_V14_WEAVE_PARAMS` after this
   commit. The gate predicate (NEUTRAL) is part of the freeze.
3. Infra reruns (heartbeat stall / crash) are not analysis iterations.

## 6. Multiplicity note

This is the second Bachira-C3-directed lever (after C3 v2, §11.14,
which retired its own upside by falsifying the duplication story) and
part of the THIRD G7 gate attempt. The mechanism is doctrine-derived
(canon weapon → D1-bias-space partition) with zero free numeric
parameters (both gate constants are verbatim copies of a cell locked
before G7 existed); no G7 threshold is touched. See G7 §11.17 for the
campaign-level multiplicity accounting.

## 7. Artifacts

- Verdict: `reviews/phase_z_verdict.md` (+ numbers in the §11.17 gate
  report). EXPERIMENTS.md + ai_context.md rows on completion.
