# Phase AE — Sae Itoshi event specialist (pre-registration DRAFT)

- **Registered:** 2026-07-20 (DRAFT — untracked working-tree file in
  `finance-research-experiments`; not yet committed). Sibling
  implementation commits live on `next-gen` of the trading-agent
  repo (`multi-pair-trading-agent`) at `a26eba8`
  *"sae: event-specialist agent (disabled by default, EURUSD-only)"*
  and `38a91b4` *"squad: export A9SaeV1 + SaeConfig …"*.
- **Program:** M001 multi-agent ensemble.
- **Branch (target for merge, when ratified):** `multi-agent-ensemble`
  (research repo). Draft on `main` mirrors the standard M001 WIP
  pattern.
- **Authorization:** user 2026-07-20 (this session). Motivated by:
  (a) the same 3-year hour-13 EURUSD bleed that motivates Phase AD
  Karasu — some of those pips come from *tradable* impulses on
  scheduled prints, not just avoidable ones; (b) canon Sae is
  the elite striker who takes over decisive moments — a natural
  fit for "propose only inside event windows".
- **Lever slot:** proposer-roster addition lever. Adds ONE new
  agent to the proposer list (behind a config flag). G7 §11.17
  panel is the evaluation vehicle. Consumes one OOS touch when
  ratified — reserved separately from any Phase AD budget because
  the two studies test different mechanisms (defender vs striker).

---

## 1. Problem (banked evidence)

**Bank 1 — event impulses are a tradable regime, not a monolithic
avoid-zone:** the same audit that motivates Karasu (hour-13
EURUSD -857 pips) also shows plenty of bars in that hour with
one-sided 40-80 pip impulses whose next-M15 bar retains most of
the move. If we frame news as ONLY a risk source we leave those
setups uncontested. Sae is the canon-appropriate agent to contest
them: an event-specialist Tier-1 striker with a bounded fire
window and two mechanic-level triggers.

**Bank 2 — no v1 agent currently trades this regime:** Isagi,
Bachira, Barou, Rin, Chigiri, Reo, Nagi all use zone / breakout /
harmonic / confluence primitives that (by design) do not read the
economic calendar. Their Thoughts don't fire on impulse bars whose
context is "release + retention" or "release + failed impulse".
Adding Sae is therefore adding *coverage*, not competing for the
same signal.

**Bank 3 — geometric mechanics are pure-price, not surprise-z:**
v1 Sae uses M15 bar geometry (move size, wick fraction, next-bar
retention) to decide. He does NOT read the `actual` field from the
calendar — that data isn't cleanly available yet. Phase AE.2 is
reserved for surprise-z integration once a data source is chosen.

## 2. Canon → mechanism mapping (locked BEFORE running arms)

Canon Sae is the elite striker who takes over decisive moments.
Locked v1 mechanics:

- **Universe:** EURUSD only (v1 constraint — the parquet cache
  today has M15 for EURUSD and GBPUSD only; Sae will ship as
  EURUSD-only until Phase AE.2 broadens M15 coverage). Sae's
  constructor accepts a `symbols=` override so the API is
  multi-pair-ready.
- **Event filter:** high-impact USD only (canon: "takes over
  decisive moments"). Medium-impact / non-USD events are not Sae's
  regime.
- **Fire window:** [T − 30 min, T + 60 min] around the event time
  T. Sae does not propose pre-release in v1
  (`fire_window_before_min=30` is symmetric-API only; the mechanics
  themselves fire at T+15 or T+30, so the effective pre-release
  fire probability is 0).
- **Mechanic 1 — fade** (fires at as_of ≥ T + 15 min):
  - Locate the M15 bar covering [T, T+15 min] = "event bar".
  - Require `|move_pips| = |close − open| / pip ≥ 40`.
  - Require wick opposite the move ≥ 50 % of bar range
    (`(high−close)/range` for bullish, `(open−low)/range` for
    bearish).
  - Propose in the OPPOSITE direction; stop at wick extremum ±5
    pip padding; `target_rr = 1.5`. Tag `sae_fade`.
- **Mechanic 2 — ride** (fires at as_of ≥ T + 30 min, only if
  fade did NOT fire for the same event):
  - Take impulse direction from the event bar.
  - Require next M15 bar (T+15 → T+30) close same-direction AND
    `|next_close − event_open| / |event_move| ≥ 0.7`.
  - Propose in impulse direction; stop at event_bar.open;
    `target_rr = 1.5`. Tag `sae_ride`.
- **One proposal per event:** once fade or ride fires, Sae does
  NOT fire again for the same event.
- **Conviction:** fixed 0.85 on any Sae proposal (Tier-1, deliberate
  spike above Isagi/Bachira base 0.65-0.70 so the aggregator lets
  Sae through on the event tick). No metavision / peer lift
  wiring in v1.

**Empirical priors, banked honestly:**
- **Prior FOR fade:** rejection wicks on release bars are a
  well-documented mean-reversion setup (E006 rejection-wick prior
  on non-news bars was +0.11 mean-TQS — not a like-for-like
  benchmark, but same geometric shape).
- **Prior AGAINST fade:** M15 wick fractions on 40+-pip release
  bars are noisy; a 50 % wick floor might yield too few trades for
  a stable CI.
- **Prior FOR ride:** 70 %+ retention on the second M15 is a
  strong impulse-continuation signature. Chigiri's breakout family
  has a similar structural predicate, though Chigiri does not gate
  on the event calendar.
- **Prior AGAINST ride:** on many high-impact prints the M15+15
  bar is a chop / mean-reversion bar even when the trend eventually
  resumes — retention-based gating may miss the setup and re-enter
  wrong.
- **Volume prior:** high-impact USD events are ~4-8/month; even at
  100 % fire rate Sae would see ~200-400 trades over the multi-year
  panel. Realistic fire rate (fade ~30 %, ride ~30 %, cross-mechanic
  overlap ~10 %) puts him nearer 100-200 OOS trades. The AE1 floor
  is therefore weaker than the standard AB1 100-trade floor.

## 3. Implementation plan

**Trading-agent repo (already landed on `next-gen`):**
- `agent/squad/agents/a09_sae.py` — Sae class, fade / ride
  mechanics, `bars_provider` DI, `load_calendar` sharing with
  Karasu.
- `agent/squad/sae_config.py` — locked knobs + `sae_enabled=False`
  master flag.
- `agent/squad/roster.py` — Sae instantiated regardless;
  `sae_enabled=True` puts him in `proposers`. Log line at build:
  "Sae ENABLED (event_specialist)" or "Sae DISABLED (awaiting
  Phase AE pre-reg)".
- `tests/test_squad_sae.py` — 17 tests, all pass.

**Research-repo harness plan (to land on `multi-agent-ensemble`
when ratified):**
- New harness flag `--sae-enabled` on the G7 walk-forward driver;
  when set, builds the roster with `SaeConfig(sae_enabled=True)`
  and wires an M15 bars_provider closure onto Sae at prepare-time.
- Baseline arm: `--sae-enabled` off (7-proposer roster + Karasu R7
  if AD is passing).
- Treatment arm: `--sae-enabled` on (8-proposer roster).
- Both arms use the same frozen news calendar (§Phase AD §7).
- **AE + AD interaction:** if Phase AD is deployed, R7 will
  BLOCK every Sae proposal on high-impact USD events because
  those are the exact events Sae fires on. This is the
  Karasu-Sae design tension (see §8). The base evaluation
  therefore runs with **R7 DISABLED** in both arms so Sae's
  effect is measured cleanly; a joint AE+AD arm is a follow-up
  Phase AE.3.

## 4. Success criteria (locked; evaluated ONCE)

Baselines are the §11.17 walk-forward panel with R7 disabled
(so the comparison isolates Sae's proposer contribution).

- **AE1 — C1 volume floor:** Sae **≥ 30 OOS trades** on the panel
  window. Weaker than the standard 50-trade floor because event
  days are naturally rare.
- **AE2 — C1 mean-TQS threshold:** Sae panel mean TQS **≥ 0.30
  AND bootstrap 95 % CI lower bound > 0.20**. Looser than the
  standard 0.25 floor because event-driven variance is inherently
  high.
- **AE3 — mechanic split audit:** report fade vs ride trade counts
  and mean TQS separately. If either mechanic contributes < 20 %
  of Sae's total trades, that mechanic is **parked** for a Phase
  AE.2 refinement (its own pre-reg, its own OOS budget).
- **AE4 — no chemistry damage:** no other agent's C1 regresses by
  more than −0.02 mean-TQS in the Sae-enabled arm.

**Phase verdict:** PASS iff AE1 AND AE2 AND AE4. AE3 is a
mechanic-audit gate that can PARK either mechanic without failing
the phase overall.

## 5. Stop rules / anti-leakage

1. One evaluation. Failure STOPS the lever — no threshold
   softening (min-move 40 → 35, wick 0.5 → 0.4) against the same
   OOS windows.
2. If AE1 fails on volume, DO NOT drop AE2's mean-TQS floor to
   "salvage" the phase — that's the failure mode Phase Y demonstrated
   at n=43.
3. If AE2 passes overall but AE3 shows one mechanic dominant
   (e.g. all fade, no ride), the dominant mechanic is retained
   and the sub-20 % mechanic is PARKED. Retention is data-driven,
   not tuning.
4. Infra reruns (identical seed, identical fixture, identical
   code) are not analysis iterations.

## 6. Multiplicity note

Sae is the first new proposer added since Phase AA. The addition
sits inside the third G7 gate attempt (§11.17). It does not touch
existing proposer parameters, does not touch the aggregator, does
not touch R1-R6 sizes. Only R7 (Karasu) interacts with Sae, and
that interaction is deferred to Phase AE.3.

## 7. Artifacts

- **Calendar fixture:** shared with Phase AD (§Phase AD §7). Frozen
  once; never refetched.
- **M15 bar fixture:** the walk-forward driver already replays
  M15 EURUSD bars via the parquet cache (`data/parquet/
  EURUSD_M15.parquet`). Bars_provider closure reads directly from
  that cache, filtered to the study window.
- **Verdict:** `reviews/phase_ae_verdict.md` + numbers in the
  §11.17 gate report. EXPERIMENTS.md + ai_context.md rows updated
  on completion.

## 8. Known limitations (documented up front)

- **EURUSD-only in v1.** The M15 cache today covers EURUSD (and
  GBPUSD). USDCAD / AUDUSD / NZDUSD / USDJPY / USDCHF M15 caches
  do NOT exist yet. Sae's constructor exposes `symbols=` for the
  future broadening, but the AE1/AE2 gates only evaluate EURUSD
  in v1. **Phase AE.2 amendment slot** is reserved for
  multi-symbol expansion when the cache lands.
- **No `actual`-value gating.** Sae v1 is pure-price. The Phase
  AE.2 amendment slot is also reserved for surprise-z integration
  when a data source (Bloomberg / Refinitiv / ForexFactory
  "actual" scraper) is chosen. Doing this now would be invention
  under time pressure, not derivation.
- **Karasu-Sae interlock.** Karasu R7 (if deployed via Phase AD)
  blocks proposals on high-impact USD events — the exact events
  Sae wants to trade. Phase AE deliberately runs with R7 DISABLED
  to measure Sae cleanly. A joint AE+AD evaluation is Phase AE.3
  (would need R7 to be Sae-aware — e.g. bypass R7 for
  `proposal.agent_id == "sae_itoshi"`, or a new R7-Sae pass-through
  flag). No design decision is committed here; that's the
  next-phase discussion.
- **Fixed conviction 0.85.** No metavision / peer lift in v1. Sae
  is the "closes it out" archetype — an evolution that gives him
  peer-read variance would be Phase AE.2 territory, not v1.
- **One-proposal-per-event lock.** Deliberate. Prevents a fade
  loss then re-entering ride on the same event. If an event
  produces two distinct valid setups (fade fails → ride works),
  Sae leaves the second on the table in v1. Documented so the
  audit can spot missed opportunities.
