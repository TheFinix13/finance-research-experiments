# Phase AA — Chigiri v1.4 panther-ignition weapon (pre-registration)

- **Registered:** 2026-07-14 (committed BEFORE any result is computed).
- **Program:** M001 multi-agent ensemble.
- **Authorization:** user authorized a four-lever third-attempt campaign
  2026-07-14 with explicit canon guidance: *"speed and his '44 panther'
  snipe, outrunning every other agent in acceleration"* — earliest-entry
  on fresh momentum ignition; be FIRST to a new move before slower
  confirmation-based peers arrive. Upgrade the `speed_momentum` weapon,
  do not replace the identity.
- **Lever slot:** Lever C of the G7 §11.17 third-attempt campaign.
  Target blockers: **Chigiri C1 0.267 < 0.30 (n = 296)** and **C2 no
  qualifying peer** (§11.16 — unchanged since §11.13; no prior lever
  ever pointed at Chigiri).
- **Evaluation vehicle:** the G7 re-gate replays pre-registered in G7
  PROTOCOL §11.17 (tag `g7retry2`) — OOS touched exactly once, jointly
  for all four campaign levers.

---

## 1. Problem (banked evidence)

Chigiri v1 fires on a 20-bar range break only after price has already
travelled ≥ 0.5 × ATR *beyond* the broken level (predicate 5 of the
locked detector). That magnitude hurdle is a **confirmation tax**: by
the time it clears, the H4 close used as entry is deep into the move.
The banked evidence says this is exactly where his TQS bleeds:

- TQS is entry-efficiency-weighted (doctrine §3.5; Kaufman–Sweeney
  entry_efficiency is a TQS component). Late entries mechanically
  score lower efficiency. Chigiri's §11.16 phi41 mean TQS is 0.267
  with per-window means as low as 0.187.
- Phase U (2026-07-01, banked): Chigiri was the ONE agent whose
  REJECTED proposals out-scored his accepted ones (Δ +0.065) — his
  fire set contains better trades than the slice that survives; his
  weakest fires are what the squad executes.
- Φ4.1 telemetry (doctrine §3.11.3 A4): median-negative profile from
  whipsaw on "early-stage σ expansions" — the v1 answer (magnitude
  hurdle) waits the move out instead of qualifying the *bar* that
  starts it.

The canon diagnosis: v1 makes Chigiri a confirmation trader — the
opposite of the character. Speed is acceleration at the START of the
move, not distance covered after it.

## 2. Canon → mechanism mapping (doctrine + banked evidence ONLY)

**Weapon: '44 panther' ignition snipe.** Chigiri fires on the FIRST H4
close beyond the 20-bar range — no distance-travelled hurdle — but
ONLY when the breakout bar itself is an **ignition bar**: its true
range shows acceleration relative to the immediately preceding bars.
He outruns the field by qualifying the bar's *energy*, not by waiting
for the move to prove itself.

Locked detector change (v1 predicates 1–4 retained verbatim):

| Predicate | v1 (locked Φ4.1) | v1.4 panther-ignition |
|---|---|---|
| 1. warmup | unchanged | unchanged |
| 2. ATR valid | unchanged | unchanged |
| 3. vol-expansion regime (ATR > 80-bar median) | unchanged | unchanged (identity retained) |
| 4. close beyond 20-bar high/low | unchanged | unchanged |
| 5. magnitude ≥ 0.5 × ATR beyond level | **REMOVED** (the confirmation tax) | **REPLACED by ignition thrust:** `TR[i] ≥ 1.5 × mean(TR[i-5..i-1])` |

Locked parameters (`CHIGIRI_V14_IGNITION_PARAMS`):

| Param | Value | Source (no new tuning) |
|---|---|---|
| `thrust_ratio` | `1.5` | The 1.5× family already locked in Chigiri's own cell (`CHIGIRI_V1_REGIME_MIN_MAG_ATR = 1.5`, `CHIGIRI_V1_REGIME_ATR_MULT = 1.5`, Phase V-a, and `target_rr = 1.5`) — a qualitative "half-again" acceleration, not a searched value |
| `thrust_window` | `5` | The freshest handful of bars; matches the existing `+5` warmup pad in `CHIGIRI_V1_WARMUP_BARS` — declared as a frozen design constant |

Conviction boost re-driver: v1's `boost = min(0.25, 0.10 ×
magnitude/ATR)` becomes `boost = min(0.25, 0.10 × thrust_ratio_observed)`
— same coefficient (0.10), same cap (0.25), the driver changes from
distance to acceleration to match the weapon. Trade plan geometry
unchanged in form: entry = ignition close, stop = broken level ∓ 0.25
ATR, TP = 1.5R. Because entry sits closer to the broken level, risk is
smaller and resolution faster — the speedster's tight, fast trade.

**C2 mechanism (why earliest-entry buys chemistry):** Chigiri's fired
Thought (coordinate, conviction ≥ 0.70 = Nagi's floor, ttl 6 ticks)
lands on the workspace at the ignition tick — BEFORE the zone-family
peers react to the same move on later bars. Nagi's confluence
predicate reads prior-bar peer pairs; Isagi's metavision lift counts
peer alignment. An earlier, larger Chigiri fire set means his Thought
is on the board when slower peers arrive, seeding pairs he currently
misses (§11.16: his best peer delta was Nagi at +1 trade —
directionally right, hopelessly under-powered). Prediction: a
qualifying C2 peer emerges via the trade-count route (most likely
`nagi_seishiro` or `isagi_yoichi`).

Honest uncertainties: (a) removing the magnitude hurdle admits
lower-energy pokes past the level that the thrust gate must filter —
if the thrust gate is a weaker whipsaw filter than the magnitude gate,
C1 worsens instead of improving; (b) there is no banked per-subset
expectancy for "first close + thrust" vs "confirmed magnitude" —
the mechanism argument runs through the TQS efficiency component,
which IS banked (Phase U per-trade metrics), not through a backtest
of this exact cell. The manipulation check AA-M below tests the
mechanism directly.

## 3. Implementation plan

- `sim/agents/a04_chigiri.py`: constructor flag `weapon_ignition:
  bool = True` (legacy v1 weapon behind `weapon_ignition=False` for
  cache-reproduction tests). `_detect_breakout` branches on the flag;
  predicates 1–4 shared. Rationale stamps `weapon:
  chigiri_v14_ignition` + observed thrust ratio. Tags gain
  `chigiri_ignition_bar` on fire.
- Harness: unchanged (default flag active).
- Unit tests BEFORE results: (a) ignition params reach the detector;
  (b) `weapon_ignition=False` reproduces the v1 fire set on a fixture;
  (c) on a synthetic accelerating breakout the v1.4 weapon fires on
  the FIRST breakout close where v1's magnitude hurdle would still be
  waiting; (d) a low-thrust poke past the level does NOT fire v1.4;
  (e) boost formula uses the thrust ratio (dispersion regression
  guard).

## 4. Success criteria (locked; evaluated ONCE on the §11.17 re-gate replays)

Baselines referenced below are the §11.16 `g7retry1` numbers.

- **AA1 — C1 pass (primary):** Chigiri C1 passes under phi41: panel
  mean TQS ≥ 0.30 AND ≥ 5/7 windows ≥ 0.20 AND CI lower > 0.25, at
  n ≥ 200 OOS trades (was 296 — the ignition set must not collapse
  volume).
- **AA2 — C2 pass (primary):** at least one qualifying C2 peer exists
  for Chigiri under phi41 (bootstrap-CI-gated, evaluator letter
  unchanged).
- **AA-M — mechanism manipulation check:** Chigiri's mean
  entry-efficiency TQS component (from the baseline cache
  `tqs_components.efficiency`) strictly exceeds the §11.16 value.
  If AA1 passes while AA-M fails, the improvement did not come
  through the pre-registered mechanism — reported as such.
- **AA3 — no self-regression:** Chigiri keeps C3/C4/C5/C6 passes
  under phi41.
- **AA4 — no squad regression:** squad mean-of-window-mean TQS within
  −0.02 of §11.16 in each arm (shared campaign tolerance).

**Phase verdict:** PASS iff AA1 AND AA2 AND AA3 AND AA4. AA-M failing
downgrades a PASS to PASS-WITH-CAVEAT (mechanism unproven). Anything
else is FAIL or PARTIAL with the failing criteria named.

## 5. Stop rules / anti-leakage

1. One evaluation. Failure STOPS the lever — no thrust-ratio /
   window iteration against the same OOS windows.
2. No post-freeze retuning of `CHIGIRI_V14_IGNITION_PARAMS`.
3. Infra reruns are not analysis iterations.

## 6. Multiplicity note

First Chigiri-directed lever ever (no prior attempt consumed
Chigiri-directed OOS looks; V-a was a routing mechanic, NULL, and its
diagnostic ratios are reused here only as already-banked telemetry),
inside the THIRD G7 gate attempt. Constants are drawn from the 1.5×
family already frozen in his own cell; no G7 threshold is touched.
The doctrine §3.11.3 A4 sketch (stricter three-guard filter) is a
PRIOR, not a commitment (§3.11.3 preamble); this design supersedes it
on canon grounds — the sketch made Chigiri slower, the canon says
faster — and the sketch's defeat trigger stays live. See G7 §11.17.

## 7. Artifacts

- Verdict: `reviews/phase_aa_verdict.md` (+ numbers in the §11.17 gate
  report). EXPERIMENTS.md + ai_context.md rows on completion.
