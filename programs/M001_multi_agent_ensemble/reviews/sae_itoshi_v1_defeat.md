# A9 Sae v1 — defeat note (pre-v2 evolution-arc charter)

**Status:** `REGISTERED` — 2026-08-19. No v2 code exists at registration
time; that is the point of this file.
**Authoritative contract:** `06-blue-lock-doctrine.md` §3.11.2 step 1
("defeat documented") + step 2 ("evolution hypothesis stated
explicitly"); `07-research-standards.md` §10.6 (evolution-arc contract).
**Audit trail:** evolution row appended to `reviews/evolution_ledger.md`
once the v2 arc closes or fails.

This note is the **earned** justification for a Sae v1 → v2 arc. It
quotes the specific failure-mode metrics, states the hypothesis up front
so v2 cannot be retconned, and — unusually for a defeat note — records
an explicit **prior against the arc succeeding**, because three of the
four event-trading lanes in this program are already closed.

Written in response to a direct operator question on 2026-08-19: *"let's
work on fixing him as a player so his v1 is ready like the other
players — what improvements can we perform so his performance in
testing becomes better?"* The honest answer has two halves that must not
be conflated, and §1 separates them: he fails **three G7 bits because
code is missing** (cheap, legitimate to fix now, no alpha claim), and he
fails **the quality bar because the alpha is not there** (expensive,
may be unfixable, and explicitly may not be retuned on the spent panel).

---

## 1. Defeat trigger (the observed metrics)

Phase AE (`experiments/phase_ae_sae_event_specialist/`, verdict
`reviews/phase_ae_verdict.md`) locked its criteria in commit `dfe5ce1`
before either arm ran, then measured:

| Criterion | Locked threshold | Observed | Status |
|---|---|---|---|
| AE1 volume | ≥ 30 OOS trades | 54 | PASS |
| AE2 quality | mean TQS ≥ 0.30 AND boot CI95 lower > 0.20 | mean **0.097**, CI95 **[0.042, 0.162]** | **FAIL** |
| AE3 mechanic split | park any mechanic < 20 % of trades | fade 22.2 %, ride 77.8 % | no park |
| AE4 chemistry | no incumbent regresses > 0.02 mean TQS | max delta −0.000 | PASS |

Verdict verbatim: "**VERDICT: FAIL** … AE2 fails decisively. **Sae v1 is
NOT armed for the Aug 7 NFP.** The lever stops here; no threshold
softening, no rerun."

Trade signature (REPORT §1): "25 TP / 62 SL = **28.7 % win rate at a
fixed 1.5R target (breakeven 40 %)**, mean −4.16 pips/trade over 87
trades."

### 1.1 The number that triggers the arc

Not the headline TQS — the **45× asymmetry between his two mechanics**.

| Mechanic | n (full panel) | Win | Mean TQS | Mean pips | Share of OOS book |
|---|---:|---:|---:|---:|---:|
| `sae_fade` | 26 | 34.6 % | 0.234 | **−0.13** | 22.2 % |
| `sae_ride` | 61 | 26.2 % | 0.148 | **−5.88** | 77.8 % |

AE3's own wording was "Both ≥ 20 %, so no mechanic parked — **both simply
lose**", which is true of the sign and badly misleading about the
magnitude. Fade over 26 trades is **within a fifth of a pip of
breakeven before its own bracket is questioned**. Ride is the entire
loss, and it is 78 % of the book. Cross-tabulated against event type,
the only positive pips cell in the whole panel is `sae_fade` on NFP
(n=16, 31.2 % win, TQS 0.218, **+0.33 pips**); every ride cell is
negative (ride/NFP −8.84, ride/FOMC −7.21, ride/CPI −3.05).

Structurally this is unsurprising: the ride stop is the **event bar's
open**, i.e. the entire impulse plus the retention overshoot, making it
the widest stop in the design and pinning ride's risk to the very
quantity that triggered it. A wider stop at a fixed 1.5R needs a
proportionally larger continuation to pay, on the mechanic whose entry
is already 30 minutes late.

### 1.2 Corroborating decay (why this is not a bad-luck window)

Per-window OOS mean TQS: **0.245, 0.064, 0.096, 0.266, 0.088, 0.000,
0.073** — "uniformly poor, no rescueable regime". By calendar year the
picture is worse than uniform, it is *decaying*: positive in 2015
(+4.08 pips, 53.8 % win), 2016 (+5.51), 2019 (+11.57), 2022 (+15.58);
negative and deepening after — 2020 −9.88, 2021 −14.55, 2023 −4.62,
**2024 −23.92 (0 wins from 9)**, 2025 −9.36. Whatever this
specification once captured is not in the recent tape.

By entry hour UTC his home slot is also his loss centre: 13h n=40
(−4.06), and the FOMC 18–19h slots are his worst (−6.13 / −4.95).

### 1.3 What the defeat is NOT

- **Not a sample-size problem.** AE §4.1: "A denser calendar would
  raise trade count, not TQS — the quality failure is about post-event
  M15 predictability, not sample size (CI upper bound 0.162 is still
  below both floors)."
- **Not a cost-model artefact in his favour.** AE §4.3: "Real NFP
  spreads are catastrophically wider — live results would be WORSE than
  sim, which only strengthens the FAIL."
- **Not an integration problem.** AE4 deltas are exactly 0.000 for five
  incumbents; the M15 side-book displaced 2 Chigiri trades in 11 years.
  "Sae the *mechanism* integrates safely; Sae the *edge* does not exist
  as specified."

### 1.4 Why this is a §3.11.1 defeat, not a hyperparameter knob

AE PROTOCOL §5.1 pre-banned exactly the tempting knobs: "no threshold
softening (min-move 40 → 35, wick 0.5 → 0.4) against the same OOS
windows." The verdict adds: "v1's fade/ride + 1.5R are spent and may not
be retuned against this panel." So the knob route is closed by
pre-registration, not by preference.

The **structural absence** is that the trigger has no volatility
normalisation and no event-magnitude conditioning. `_try_fade` fires on
a flat `move_pips ≥ 40.0` regardless of whether 40 pips is a violent
reaction or a Tuesday. Phase AG
(`experiments/phase_ag_event_first_move/`) measured the shape of exactly
what that misses, on the same 349-event calendar:

- "**All 12 arms have positive net means.** … The market's first move
  after a high-impact USD release points the right way more often than
  not."
- "**The edge concentrates in violent reactions.** The ≥8×ATR arms earn
  **+14 to +19 pips/trade** with BOTH sub-halves positive — the only
  arms with sign consistency — but only ~**25–28 qualifying events exist
  in seven years.**"
- "**Small-impulse arms flip sign in 2018–2021.** … modest first moves
  carry no reliable continuation information. This matches the user's
  read that 'uneventful' events dilute everything (**Phase AE's
  unconditional FAIL is the extreme case of the same effect**)."

That last sentence is AG's, not this note's, and it is the load-bearing
citation: AG identifies Sae v1's failure as the limiting case of a
dilution effect it measured independently. No setting of
`fade_min_move_pips` expresses "impulse magnitude relative to prevailing
volatility" — that requires an ATR term the trigger does not have. New
code surface, not a new constant.

### 1.5 The second, separable defeat: he is not a v1 *player* at all

Independent of alpha, Sae fails the G7 v1 checkpoint
(`experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §3) on bits that are
**missing code**, not measured underperformance:

| G7 bit | Status | Cause |
|---|---|---|
| C1 quality | fail | AE2 (the alpha defeat above) |
| C2 lifts a peer | fail | AE4 deltas exactly 0.000; he publishes to the workspace and reads nothing, so no mechanism exists |
| C3 no peer cannibalisation | **pass** | worst effect in 11 years is Chigiri 503 → 501 |
| C4 workspace read AND publish | fail (read side) | `intend(workspace=…)` is accepted and discarded — "v1 Sae reads no peers" |
| C5 `lot_intent` dispersion ≥ 0.10 CV | fail | no F19 override; `playstyle="event_specialist"` is absent from `sim/core/lot_intent.py`'s dispatch, so it silently takes the fallback the module header labels "v1 checkpoint FALLBACK, not a valid v1 implementation" |
| C6 `risk_intent` dispersion ≥ 0.10 CV | fail | no F20 override; `event_specialist` likewise absent from `sim/core/risk_intent.py` |

He scores **1 of 6**. Three of the five failures (C4-read, C5, C6) are
absent implementations. Compounding it, `_build_proposal` emits a
literal `conviction=0.85` and `regime_fit=0.6` on **every** proposal, so
even a correctly registered playstyle would produce near-zero dispersion
and fail C5/C6 anyway — the same way Nagi scored exactly 0.000 in §11.13.

A third gap, cheap and unambiguous: **there is no time stop.**
`valid_until` is `timestamp + 6 h` per the canon `target_hold_hours=6.0`,
but exits are SL/TP only, and observed holds run to **6,675 minutes ≈
111 hours** (median 15 min). AG's own arms used a 12-hour timeout. This
is the identical design gap found live in Bachira's 5-day GBPUSD short
on 2026-08-13.

### 1.6 Roster bookkeeping problem (fix before any v2 lands)

`05-agent-roster-v0.md` assigns the **A9 slot to "Aoshi Tokimitsu"**
("Macro-event-only vol-breakout (FOMC / NFP / CPI)", status
`not-yet-implemented`), while **"Sae Itoshi (foil)" is listed as an
*opponent*** — the frozen adversarial baseline the squad must beat, also
used as the heritage floor in `07-research-standards.md` §4.2. Neither
the roster nor the doctrine mentions `sae_itoshi`, `a09_sae`, or
`event_release_impulse` anywhere. The Phase AE striker therefore
occupies Aoshi's niche under the adversary's name, has no roster row, no
§1.0 checkpoint row, and no evolution-ledger row.

This must be resolved by a naming decision recorded in the ledger before
a v2 module lands, or "Sae" will be ambiguous between a player and a
benchmark in every future report. Recommended: rename the striker to
`aoshi_tokimitsu` (A9's rightful occupant, whose canon brief is
verbatim what this agent does) and leave "Frozen-Sae" as the opponent.

---

## 2. Evolution hypothesis (stated BEFORE v2 lands)

Per doctrine §3.11.2 step 2 — what v2 adds, what failure it resolves,
what it must NOT regress. Three tiers, deliberately separable so a
failure in one does not contaminate the others.

### Tier 0 — v1-readiness plumbing (no alpha claim, no panel consumed)

Purpose: make him a *measurable* player. None of this asserts an edge,
and none of it may be reported as an improvement in performance.

1. Register `event_specialist` in `sim/core/lot_intent.py` and
   `sim/core/risk_intent.py` dispatch tables so the primitives stop
   silently taking the invalid fallback.
2. Implement F19 `lot_intent(conviction, sl_pips, equity, regime_fit)`
   and F20 `risk_intent(conviction, atr_pips, h1_swing_pips)` with
   event-specialist semantics: size **down** as the pre-release window
   narrows and as the impulse-to-ATR ratio grows (a violent print is a
   wider-stop, smaller-lot trade, not a bigger one).
3. Implement F21 `read_workspace` — at minimum, read peers' directional
   bias on the traded symbol and *abstain* when a Tier-1 incumbent
   already holds the slot in the opposite direction. This is the only
   route to C2 and it is defensive, which suits the role.
4. Replace constant conviction with a function of the observed geometry
   (impulse/ATR ratio, wick fraction, retention) so C5/C6 dispersion can
   exist at all. **A conviction function is not an edge claim** — it
   changes sizing, which is scored, so it must be measured under §4.
5. Add a hard time stop at `target_hold_hours`, closing at bar close
   when the bracket has not resolved. Kills the 111-hour tail and aligns
   with AG's 12 h convention.
6. Resolve the Karasu R7 interlock explicitly (§1.6 of Phase AD): R7
   blocks the exact events this agent exists to trade, and **Phase AD's
   own research harness never ran** (confirmed in AD.2 §1b), so the
   trade-off is undocumented. Either grant an `agent_id` bypass with a
   stated reason, or accept that the agent is unreachable live and say
   so in the ledger.

Expected outcome of Tier 0 alone: G7 bits C3–C6 become **passable**, C1
and C2 remain open. He becomes eligible, not good.

### Tier 1 — trigger redesign (the alpha hypothesis)

**What v2 adds.** A volatility-normalised, magnitude-conditioned
trigger, and the deletion of the ride mechanic.

- **Drop `sae_ride` entirely.** Citation: §1.1 (61 trades, −5.88
  pips/trade, 78 % of the book, every event-type cell negative, widest
  stop in the design). Retaining a mechanic whose only measured property
  is loss requires an argument nobody has.
- **Replace `fade_min_move_pips = 40.0` with `move ≥ m × ATR96`,**
  m pre-declared from AG's monotone shape (AG's sign-consistent band is
  m = 8; the redesign must pre-register its m and may not search it on
  the validation window).
- **Abstain by default.** The redesign's *primary* expected effect is
  that he proposes ~25 times per 7 years instead of 87 per 11. Fewer,
  larger-impulse, fade-only proposals.

**What failure it resolves.** The dilution effect AG named and AE
suffered: firing unconditionally on all 349 high-impact prints buries
whatever signal the violent tail carries.

**The binding constraint, stated honestly.** AG's own hand-off: "the
binding constraint is identifying the ~4 events/year that will move
≥8×ATR. Waiting K bars to observe the impulse costs entry price AND
cannot expand n." A fade mechanic observes the impulse by construction,
so it inherits the entry-price cost but not necessarily the n problem —
because n can be widened along two axes that do **not** weaken the
threshold:

1. **More symbols.** AG's untuned GBPUSD robustness check reproduced the
   same monotone shape (+6 to +24 pips/trade at m=8). Pooling
   EURUSD/GBPUSD/USDCAD turns ~4 qualifying events/year into ~12.
2. **More event types.** The frozen calendar is disclosed as "a
   CONSERVATIVE SUBSET of 'high-impact USD' — ~2.7 events/month vs the
   §2 volume prior's 4–8/month". Extending the fixture (a new
   `DATA_LEDGER.md` row, §5.4) raises n without touching the threshold.

Both are pre-registerable. Neither is a retune.

### Tier 2 — the data unblock (highest expected value, needs the VM)

Phase AI's surprise panel — consensus vs actual — **does not exist**.
`phase_ai_surprise_panel/DATA_PLAN.md` status: "TOOLING READY, DATA
PENDING (needs one run on the trading VM)". The tooling is already
written and committed: copy `ExportCalendarHistory.mq5` into the demo
terminal's `MQL5/Scripts/`, compile in MetaEditor, run once on any
chart, retrieve `MQL5/Files/calendar_history_usd.csv`, then
`normalize_panel.py` + the mandatory coverage audit
(`data/panel_gaps.json`) before a protocol may be registered.

Why this outranks Tier 1: surprise-z identifies the movers **at t0**,
recovering the entry price that a fade or a K-bar wait gives away, and
it expands usable sample by letting lower-m arms condition on surprise
instead of realised impulse. It is the only lane that attacks AG's
binding constraint head-on.

Why it is Tier 2 and not Tier 1: it is blocked on one operator action,
and registering floors before knowing event coverage "would be theatre"
(DATA_PLAN's own words).

### Lanes that are closed — do not reopen

- **FOMC statement tone.** Phase AH is `dead`: sign agreement 38.1 % vs
  a ≥58 % floor, Spearman ρ = **+0.144** (wrong sign, p = 0.36). Reading
  the Fed's prose with a frozen dictionary does not predict direction.
  AH's own hand-off redirects the Sae critical path to S1 (surprise) and
  the AG near-miss — i.e. to Tier 1 and Tier 2 above.
- **Softening the v1 thresholds on the AE panel.** Pre-banned (§1.4).

### What v2 must NOT regress

1. **AE4 chemistry must hold.** No incumbent's mean TQS may regress by
   more than 0.02, the AE threshold. v1's cleanest property was that it
   displaced almost nothing (2 trades in 11 years); a v2 that proposes
   less should displace less, so a regression here means the sizing or
   slot logic broke.
2. **Abstention must not be scored as skill.** If v2's only measured
   effect is "trades less and therefore loses less", the correct verdict
   label is `parked_insufficient_n` or `dead`, **not** `alive`. A
   near-zero mean with a tiny n is not an edge, and this note pre-commits
   to that reading so it cannot be argued later.
3. **Tier 0 must be reported separately from Tier 1.** A joint run whose
   lift cannot be attributed to either the primitives or the trigger is
   uninterpretable and must be re-split.

### Window declaration (§4.1) — read before touching data

The panel is spent asymmetrically and this is the easiest place for the
arc to cheat itself:

- **AE consumed 2015–2025 in full** for the fade/ride/1.5R specification
  across 7 walk-forward windows.
- **AG consumed 2015–2021** tuning 12 impulse arms and left **2022–2025
  sealed** for S1 / AG-2 validation.

A v2 that inherits AG's m×ATR trigger therefore has exactly **one**
honest validation window: **2022–2025, opened once, at promotion.**
Tuning happens on 2015–2021. Note the residual contamination and do not
paper over it: AE has already seen 2022–2025 under a *different*
specification, so a 2022–2025 result on the m×ATR fade is
quasi-out-of-sample, not virgin. That caveat belongs in the report's
limitations section, verbatim.

---

## 3. Architecture sketch (so a v2 module on disk is verifiable)

`sim/agents/a09_sae_v2.py` — NEW file; `a09_sae.py` untouched, per
§10.6 ("vN untouched").

- **Trigger.** `move_pips ≥ m × atr96_pips` on the M15 event bar,
  `m` pre-declared. Wick-fraction filter retained at its v1 value
  (0.5) — unchanged, so it is not a retune.
- **Mechanic.** Fade only. `entry = event_bar.close`,
  `stop = wick extremum ± fade_stop_padding_pips`, and a
  `risk_intent`-derived TP ladder rather than the hard-coded single
  1.5R rung.
- **Conviction.** `f(move/ATR, wick_frac, minutes_since_release)`,
  monotone increasing in the first two, decreasing in the third,
  clipped to [0.5, 0.95]. Dispersion is then a measurable property, not
  a constant.
- **Sizing.** F19 `lot_intent`, event-specialist semantics per §2 Tier 0.
- **Exit.** SL, TP ladder, **or** time stop at `target_hold_hours`.
- **Workspace.** F21 read → abstain on directional conflict with an
  incumbent holding the slot; publish unchanged.
- **Event selection.** Fix the v1 quirk where
  `_nearest_scheduled_event` returns the **earliest** candidate in the
  window, so a 60-minute-stale event can be preferred over one about to
  print. v2 selects the event whose release is nearest to `as_of`.
- **Universe.** EURUSD + GBPUSD + USDCAD (the n-expansion axis of §2
  Tier 1), declared up front rather than discovered.

Tags on every v2 Thought: `["sae_v2", "weapon:event_fade_vol_norm",
"m:<m>", …]` so the behaviour delta is greppable.

---

## 4. Tests v2 must pass (so the arc is closeable, not just claimable)

Per §10.6, missing either of the first two is a code-review failure.

1. **Regression test** — `sim/tests/test_a09_sae_v2_regression.py`. On
   the subset of AE events where v1's trigger fired **and** the v2
   volatility trigger also fires, v2's fade proposal must be
   byte-identical to v1's in direction, entry and stop. (TP and lot
   legitimately differ — those are the declared changes — so the
   assertion is scoped to the geometry v2 claims to preserve, and the
   test docstring must say so.)
2. **Forward test** —
   `sim/tests/test_a09_sae_v2_resolves_ae2_ride_loss.py`. Named defeat:
   AE2 / the §1.1 ride asymmetry. Pre-declared threshold: on the
   2015–2021 tuning window, v2 emits **zero** `sae_ride`-class trades
   and its proposal count is ≤ 40 % of v1's on the same events. This
   tests that the redesign *did the thing it claims*, independent of
   whether the thing pays.
3. **Primitive-dispersion test.** `lot_intent` CV ≥ 0.10 and
   (`sl_pips` CV ≥ 0.10 OR `tp_ladder[0]` CV ≥ 0.10) across the tuning
   window — the C5/C6 bits, measured directly rather than inferred.
4. **Time-stop test.** No trade's hold exceeds `target_hold_hours`,
   with the 111-hour v1 case as the explicit regression fixture.
5. **Chemistry test.** AE4 re-run: no incumbent regresses > 0.02 mean
   TQS.

Harness: `sim/scoring/run_sae_v2_arc.py`. Report:
`reviews/sae_v2_arc.md`. Ledger row: `reviews/evolution_ledger.md`.
Every result file carries a `sim/manifest.py` manifest (§5) or is
excluded from aggregation.

---

## 5. Verdict criteria

The arc **closes successfully** (v2 canonised) only when all of:

1. Tests 1–5 pass.
2. On the 2015–2021 tuning window, v2's mean pips/trade > 0 and its
   fade-only book has ≥ 30 trades (AE1's volume floor, unchanged).
3. On **2022–2025, opened once**, mean TQS ≥ 0.30 with bootstrap CI95
   lower > 0.20 (AE2's floors, unchanged — the arc must clear the bar
   its predecessor failed, not a friendlier one).
4. AE4 chemistry holds.

The arc **fails** (v2 archived, v1 stays canonical, FAIL row in the
ledger) when any of:

- A regression or forward test breaks.
- The volatility trigger leaves n < 30 on the tuning window even after
  the symbol- and event-type expansions of §2 Tier 1 — verdict
  `parked_insufficient_n`. **This is the single most likely outcome**
  (AG failed n ≥ 30 by 2–5 events on EURUSD alone).
- Mean pips/trade ≤ 0 on the tuning window — verdict `dead`; do not
  open 2022–2025.
- The only effect is reduced trade count with a mean indistinguishable
  from zero — verdict per §2 non-regression rule 2.

---

## 6. Honest prior (recorded now so it cannot be revised later)

Of the four lanes this program has opened on event trading, **three are
closed**: AE failed unconditionally, AH is dead with a wrong-signed
point estimate, and AG's only sign-consistent arms are n-starved. The
fourth — surprise data — is blocked on one MQL5 export that has never
been run.

The realistic distribution of outcomes for this arc, stated before it
runs:

- **Most likely (`parked_insufficient_n`):** the volatility trigger is
  correct and there is simply not enough history at m=8 to clear a
  30-trade floor, even pooled across three symbols. Useful negative
  result; leaves Tier 2 as the only live path.
- **Plausible (`dead`):** the fade's near-breakeven −0.13 pips over 26
  trades was noise, and conditioning on impulse magnitude does not
  rescue it.
- **Least likely (`alive`):** a small, well-powered fade book on violent
  prints clears AE2's floors.

Tier 0 is worth doing regardless and independently of all of this: it
costs no panel, makes him measurable against G7, kills the 111-hour hold
tail, and forces the Karasu interlock and the A9 naming collision into
the open. **Tier 0 is not an alpha improvement and must never be
reported as one.**

For the operator's live question — SAE is on the pitch from 2026-08-19
under the **v1 specification**. Nothing in this note changes that, and
the expectation for the next NFP is a losing specialist book, exactly as
Phase AE measured. He is there to be observed, and the observation is
the deliverable.

---

## 7. References

- Defeat data: `experiments/phase_ae_sae_event_specialist/REPORT.md`,
  `reviews/phase_ae_verdict.md`,
  `results/phase_ae_evaluation.json`,
  `results/ae_replay_cache_ae-treatment/sae_trade_meta.json` (the 87
  per-trade records the §1.1 cross-tabs are computed from).
- Locked criteria: `phase_ae_sae_event_specialist/PROTOCOL.md` §2
  (conviction/mechanics spec), §5.1 (the retune ban).
- Impulse-magnitude prior: `experiments/phase_ag_event_first_move/REPORT.md`
  (the ≥8×ATR band, the 2018–2021 sign flip, the AE-dilution sentence).
- Closed tone lane: `experiments/phase_ah_fomc_statement_tone/REPORT.md`.
- Blocked data lane: `experiments/phase_ai_surprise_panel/DATA_PLAN.md`
  + `ExportCalendarHistory.mq5` + `normalize_panel.py`.
- Karasu interlock: `experiments/phase_ad_karasu_news_defender/PROTOCOL.md`,
  `experiments/phase_ad2_karasu_window_semantics/` (Stage 1 null; and
  §1b's confirmation that AD's harness never ran).
- v1-readiness contract: `06-blue-lock-doctrine.md` §3.11.5 (the six
  criteria), §4.1a (F19/F20/F21 signatures);
  `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §3 (C1–C6 thresholds),
  §11.18 (latest FAIL 3/7).
- Method contract: `07-research-standards.md` §4.1 (windows), §4.3
  (regime-conditional KPIs), §5 / §5.4 (manifests, data ledger), §10.4
  (verdict labels), §10.6 (evolution-arc contract), §11 (pre-registration).
- Naming collision: `05-agent-roster-v0.md` (A9 = Aoshi Tokimitsu;
  "Sae Itoshi (foil)" = opponent), `07-research-standards.md` §4.2
  (Frozen-Sae as heritage floor).
- Precedent for this note's format: `reviews/isagi_yoichi_v1_defeat.md`.
- Live parallel to the missing time stop: the 2026-08-13 finding that
  `target_hold_hours` only feeds TQS scoring and enforces no exit
  (Bachira's 5-day GBPUSD short).
