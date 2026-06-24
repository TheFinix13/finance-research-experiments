# A1 Isagi v1 — defeat note (pre-v2 evolution-arc charter)

**Status:** `LANDED` — 2026-06-24.
**Authoritative contract:** `06-blue-lock-doctrine.md` §3.11.2 step 1
("defeat documented") + step 2 ("evolution hypothesis stated explicitly").
**Audit trail:** evolution row appended to `reviews/evolution_ledger.md`
once the v2 arc closes/fails.

This note is the **earned** justification for an Isagi v1 → v2 evolution
arc. It quotes the specific failure-mode metric (not "v1 underperformed"),
states the hypothesis up front (so v2 cannot be post-hoc retconned), and
names the regression / forward tests v2 must clear.

---

## 1. Defeat trigger (the observed metric)

From `reviews/phi4_isagi_rejection_analysis.md` (companion to the Φ4
squad-gate report):

| Bucket | n | % of Isagi rejections |
|---|---|---|
| Squad would have traded SAME direction | **1579** | **52.7%** |
| Squad would have traded OPPOSITE direction | 351 | 11.7% |
| Squad stayed silent (Isagi was alone) | 1064 | 35.5% |
| Squad had own setup elsewhere | 0 | 0.0% |
| **Total Isagi rejections in Φ4 squad run** | **2994** | 100% |

**The number that triggers the arc: 1579 / 52.7 % same-direction
rejections.** Read literally: more than half of the squad-gate ticks
where Isagi v1 was rejected, the squad would have gone the same way
anyway — Isagi's signal was *redundant* with the rest of the roster, not
*missed*. The other strikers (Barou v1 on USDCAD; nothing else on
EURUSD beyond Isagi himself) already covered the directional read on
those 1579 ticks. Isagi v1 was fighting for shelf space the squad
already owned.

The 35.5 % "squad silent" bucket (1064 trades) is what Isagi v1
**uniquely** brought to the table. The 52.7 % redundancy bucket is the
**dimensional space he leaves unused** — every tick where his
`zone_d1_against` vocabulary produced an already-covered signal is a
tick where a *different* primitive could have produced a setup the
squad does not yet see.

**Quote from the Φ4 squad-gate diagnosis** (`reviews/phi4_squad_v1.md`
Diagnosis #3): "Of those, **52.7 % (1579) had the squad going the same
direction anyway** — so they were not 'missed trades', they were
redundant." Same number, different framing — that doc emphasises the
*aggregator's* fairness; this doc emphasises *Isagi's vocabulary*
limitation.

### Why this is a §3.11.1 defeat, not a hyperparameter knob

The fix is **not** "lower v1's conviction floor so it fires more often"
(produces *more* redundant signals) or "raise the floor so it fires
less" (loses the 1064 unique trades). The structural absence is that
v1's primitive vocabulary is a single concept — supply/demand zone
touch counter-trend — and that concept is **co-extensive** with the
zone-touch read every other zone-aware striker (Barou v1, Nagi v1 when
he fires) would produce at the same moment. v1 cannot express
liquidity-sweep entries, IRL/ERL fills, FVG fills, or order-block
invalidations from inside the `zone_d1_against` codepath — those are
**different setups in different parts of the field**, the metaphor
§3.11.1 makes load-bearing. A hyperparameter tweak cannot bridge that
absence. A *new code surface* with new primitives can.

### Roster cross-reference

`05-agent-roster-v0.md` §3.1 already names this defeat as the
**expected** v1 → v2 trigger ("setups outside the `zone_d1_against`
vocabulary missed at material frequency"). The Φ4 squad-gate run is
where the expected trigger crystallised into a measured one — a
specific count (1579) on a specific panel (EURUSD + USDCAD H4
2015–2025) with a specific bucketing scheme
(`reviews/phi4_isagi_rejection_analysis.md`).

The Φ3 gate's `PASS` verdict (`reviews/phi3_gate_isagi_v1.md`) is
**preserved unchanged** by this defeat note. v1's wrapper fidelity is
unchallenged — the wrap reproduces E004 to ±2.7 % drift, 7/7 OOS
windows positive. The arc is about **vocabulary**, not wrapper
quality.

---

## 2. Evolution hypothesis (stated BEFORE v2 lands)

Per `06-blue-lock-doctrine.md` §3.11.2 step 2 — "what new capability
v2 adds, what failure it should resolve, what it must NOT regress".

**What v2 adds.** A second primitive vocabulary: **liquidity-sweep
entries** read directly from the production `agent.detectors.
liquidity_sweep.detect_liquidity_sweeps` causal detector. When price
wicks above a tagged equal-highs / swing-high / PDH cluster and closes
back below (a buyside sweep), v2 emits a SHORT proposal at the sweep
close with a stop above the sweep wick and a 1.5R take-profit. Mirror
for sellside sweeps below equal-lows / PDL / swing-low. The legacy
`SupplyDemandAlpha` zone-touch core is **preserved verbatim** — when
both vocabularies fire, the zone-touch wins (legacy-first ordering
keeps v1 trades in v2's output).

**What failure it resolves.** The 1579 redundant-Isagi rejections in
the Φ4 squad-gate were ticks where the zone-touch read was already
covered. The liquidity-sweep weapon emits proposals on a different
set of ticks (sweep events do not correlate 1:1 with zone touches —
sweeps cluster around session opens / news / equal-highs formations,
whereas zone touches cluster around impulse departures from
unmitigated zones). v2's expected behavioural delta is **net-new
trades** the squad cannot already see, addressing the "vocabulary
incomplete" failure rather than the "same vocabulary, finer knob"
failure.

**What v2 must NOT regress.**

1. v2 must take **at least every v1 trade** on the same EURUSD H4
   2015–2025 panel. The zone-touch core is byte-preserved; if v2 ever
   skips a zone-touch trade that v1 took (other than a per-bar
   "sweep-and-zone collision" case where v2's deterministic
   tiebreaker prefers the zone) that is a regression. The contract
   test enforces this via byte-for-byte zone-proposal equivalence
   (see §4 below).
2. v2's median OOS-window mean TQS must not be **below v1's by more
   than −5 %** in *any single* OOS window, and must not be below v1's
   median across all seven OOS windows. The 5 % per-window floor is
   the same tolerance E004's walk-forward used and that Φ3 v1
   inherited (`reviews/phi3_gate_isagi_v1.md` verdict logic).
3. The per-trade rejection-rate analysis (35.5 % squad-silent bucket)
   must **not shrink**: the unique-Isagi trades v1 brought to the
   squad are part of v1's earned edge and v2 must keep them. If the
   sweep weapon cannibalises Isagi's silent-bucket trades v2 has
   added noise, not signal.

---

## 3. v2 architecture sketch (so the v2 module on disk is verifiable)

`sim/agents/a01_isagi_v2.py` (NEW file; v1 module untouched, parallel
worker contract).

Two-weapon stack:

* **Weapon A — `zone_d1_against` (v1 baseline preserved).** Same
  `SupplyDemandAlpha` instance constructed with `ISAGI_V1_PARAMS`
  (cross-repo import). Same `prepare()` precompute path. Same
  `observe` / `intend` codepath for the zone branch. When the
  production cell fires, v2's proposal is byte-identical to v1's.
* **Weapon B — `liquidity_sweep` (new).** At each H4 bar's
  `intend()` call, look up `ctx.liquidity_sweeps` (already computed
  by the v1 `prepare()` call — sweeps are an existing field of
  `PrecomputedContext`, populated by `precompute` on H1 and lower
  TFs; v2 calls `detect_liquidity_sweeps` directly on the H4 bar
  series during its own `prepare()` to ensure the H4 sweep list
  exists regardless of v1's TF gate). Find sweeps whose
  `sweep_bar_index ∈ (i − sweep_max_age_bars, i]` (default 6 H4
  bars ≈ one trading day). For each such sweep:
  * Direction: from `sweep.direction` (LONG for sellside, SHORT for
    buyside).
  * HTF gate (matches v1's philosophy): require
    `htf_bias_at(bars, i, htf="D1", htf_lookback=10,
    min_move_pips=60)` to **oppose** the swept extreme — i.e. for a
    buyside sweep (we're going SHORT after the sweep), the D1 bias
    must be DOWN (the sweep is a fade *into* the prevailing
    multi-day trend). For a sellside sweep (LONG), bias must be UP.
    NEUTRAL bias blocks the sweep entry (same rule v1 uses for zone
    touches).
  * Entry: at the H4 close of bar `i` (the bar driving `intend`).
    No look-ahead; the proposal `entry` is `bars[i].close`.
  * Stop: `entry + stop_atr_mult × ATR` above the sweep wick for
    SHORT, mirror for LONG. `stop_atr_mult = 0.5` matches v1's
    default.
  * Take-profit: `entry + target_rr × (entry − stop)` for LONG,
    mirror for SHORT. `target_rr = 1.5` matches v1.
  * Conviction: 0.55 (lower than v1's 0.65 zone-touch conviction so
    that in any cross-weapon aggregator the v1-style zone-touch
    proposal wins; this preserves §3 binding rule #1).
* **Cross-weapon tiebreaker.** If both weapons fire on the same H4
  bar, the zone-touch proposal is returned (legacy-first). The sweep
  proposal is journalled in the Thought's narrative + tags as
  observation-only so the behaviour-delta test can still see it.

Coordinate emission stays on H4 in v2 (the canonical "metavision
sharpens" sketch in §3.11.3 of the doctrine declares H1 as the v2
home — but the lab's existing v1 wrapper is H4 and the Φ3 evidence is
all H4; moving the cadence to H1 simultaneously with adding a new
vocabulary would conflate two changes and break the §3.11.2 step 4
regression contract. The H1 cadence move is **deferred to a v3 arc**
once the v2 vocabulary is validated. This note records that decision
explicitly so future-you knows v2 ≠ the full §3.11.3 sketch.)

Tagging on every v2 Thought: `["zone_d1_against", "isagi_v2",
"weapon:<zone|sweep|none>", ...]`. The new tag `weapon:sweep`
identifies trades only v2 can take; `weapon:zone` identifies trades
v2 inherits from v1.

---

## 4. Tests v2 must pass (so the arc is closeable, not just claimable)

Per `06-blue-lock-doctrine.md` §3.11.2 steps 3–6:

1. **BlueLockStriker contract test.** v2 satisfies the same protocol
   surface as v1 — `observe(market, ledger) → Thought` on every tick,
   `intend(market, thought) → AgentProposal | None` only at H4 close,
   `prepare(symbol, bars)` for harness use. Type signatures and
   docstrings carry the v2 marker so static analysis can distinguish.
2. **Regression test (the *byte-equivalent zone branch* invariant).**
   For every bar index where v1's `intend()` returns a Proposal, v2's
   `intend()` must return a Proposal with the *same* direction,
   entry, stop, take-profit, and conviction. Failure means v2's
   vocabulary expansion has corrupted the zone codepath — that's a
   ship-blocker.
3. **Behaviour-delta test (the *new-trades exist* invariant).** On a
   synthetic series engineered to produce a clean liquidity sweep
   without a co-located zone touch, v2's `intend()` must return a
   `weapon:sweep`-tagged Proposal that v1 does not return. If the
   delta is empty on a series that *should* trigger it, the
   evolution arc is empty — abort and keep v1 as canonical.
4. **Per-window non-regression.** On the same EURUSD H4 2015–2025
   panel as Φ3, v2's mean TQS in each of the seven OOS windows must
   not drop below v1's by more than 5 % (the §2 binding rule #2
   tolerance).
5. **Squad-rejection drop.** A v1-vs-v2 head-to-head run on EURUSD
   alone (no squad — this is a single-agent arc test, not Φ4
   re-evaluation) reports v2's *internal* trade count, weapon-split,
   and net pips. The interpretation of "did the rejection rate
   drop?" lives in the report — the test only emits the numbers.

The regression suite lives at `sim/tests/test_a01_isagi_v2.py`. The
head-to-head harness lives at `sim/scoring/run_isagi_v2_arc.py`. The
report lives at `reviews/isagi_v2_arc.md` and the audit trail row
lives at `reviews/evolution_ledger.md`.

---

## 5. What success looks like (the verdict criteria)

The §3.11.2 contract is **closed** (arc succeeds → v2 canonised) when
**all** of:

1. v2 takes ≥ all v1 trades on the EURUSD H4 2015–2025 panel
   (regression test passes byte-for-byte on zone branch).
2. v2 introduces ≥ 1 trade per OOS window from `weapon:sweep` on
   average across the seven OOS windows (behaviour delta is
   non-empty in production data, not just synthetic).
3. v2's median OOS-window mean TQS ≥ v1's median OOS-window mean
   TQS (head-to-head non-regression).
4. v2's median OOS-window mean TQS ≥ v1's by **at least + 5 %** on
   at least 4 of 7 OOS windows (positive lift on a majority of the
   windows, mirroring the Φ3 gate's 5/7 floor).

The arc **fails** (v2 archived; v1 stays canonical) when **any** of:

* The regression test breaks (v2 missed a v1 trade) — ship-blocker.
* v2's median OOS-window mean TQS drops below v1's (net regression).
* The behaviour delta is empty on real data (the sweep weapon does
  not produce trades on the real panel; "evolution arc is empty"
  per §3.11.3).
* The squad-silent unique-Isagi bucket shrinks (cannibalisation).

Honest reporting: a FAIL verdict is reported verbatim in
`reviews/isagi_v2_arc.md` and v1 remains the canonical Isagi.
`reviews/evolution_ledger.md` records the FAIL row so future-you can
see *why* v2 was rejected — the §3.11 contract is about preserving
the audit trail of attempted evolutions, not only the successful
ones.

---

## 6. References

- Defeat data: `reviews/phi4_isagi_rejection_analysis.md` (the 2994 /
  1579 / 351 / 1064 buckets).
- Squad-gate verdict + Diagnosis: `reviews/phi4_squad_v1.md`.
- v1 Φ3 PASS baseline (the regression target): `reviews/phi3_gate_isagi_v1.md`.
- Doctrine contract: `06-blue-lock-doctrine.md` §3.11.1 (principle),
  §3.11.2 (contract), §3.11.3 (Isagi sketch).
- Roster row: `05-agent-roster-v0.md` §3.1 (canonical "Defeat trigger"
  text quoted at the top of this note).
- Production primitives: `agent.detectors.liquidity_sweep.
  detect_liquidity_sweeps`, `agent.alphas.concepts._htf.htf_bias_at`
  — both consumed via `sim/_cross_repo.ensure_production_repo_on_path()`.
- Empirical prior for the new vocabulary: E006 Stage-2 exploratory
  finding (`audits/2026-06-24_E001-E007_audit.md` §2.6, §4.3) —
  H1 `equal_highs_pool` lifts every M15 setup by +0.10..+0.46 ATR.
  Acted on here at H4 cadence as a directional prior; not a
  validation claim (E010 pre-registered Stage-2b owns the validation).
