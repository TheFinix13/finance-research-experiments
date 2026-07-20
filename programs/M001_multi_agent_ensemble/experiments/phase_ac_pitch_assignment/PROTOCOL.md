# Phase AC — Pitch assignment for sub-passing v1 agents (pre-registration)

- **Registered:** 2026-07-20 (DRAFT — not yet committed; pending USDJPY/USDCHF cache pull and final ratification).
- **Program:** M001 multi-agent ensemble.
- **Branch:** `multi-agent-ensemble` (research repo). Winning arm ports to
  `next-gen` (trading-agent repo) as a follow-up commit.
- **Authorization:** user 2026-07-20 (this session). Motivated by G7
  Phase-Z / Phase-AA / Phase-AB result: 3/7 v1 checkpoint pass with a
  chemistry-coupled failure (Nagi C1 lost when Bachira's proposal
  volume halved). Two failing agents (Chigiri, Rin) have canon
  playstyles that suggest a different pair-character than their
  current home would be a better fit. Kunigami is currently retired
  as a proposer; user wants to test un-retirement on a candidate pitch.
- **Lever slot:** exploration lever — no G7 re-gate replay budget
  consumed by AC.0 or AC.1 (they use a fresh panel). AC.2 squad arms
  consume ONE OOS touch per arm on the G7 §11.17 walk-forward panel
  once the panel is extended (see §7 harness extension).

---

## 1. Hypothesis

**H1 (character detectability, AC.0):** Pair-character features
(§4.1) explain a non-trivial share of the variance in per-agent
mean-TQS across the current 5-pair panel, at bootstrap 95 % CI
lower bound |β| > 0 for at least 2 movable agents on at least one
feature. **If H1 rejects, AC.1/AC.2 do not fire — the pitch-terrain
concept is unsupported and the study concludes NEGATIVE.**

**H2 (per-agent multi-pitch fit, AC.1):** Each movable agent (Chigiri,
Rin, Kunigami) passes G7 §3.11.5 criterion C1 on **at least one**
candidate pitch under the standard walk-forward panel. Multiple wins
per agent are permitted and expected (per user 2026-07-20: "players
can succeed in multiple fields").

**H3 (squad-composition benefit, AC.2):** At least one of the squad
arms (A2 single-squad multi-pitch, B1-hard multi-squad isolated,
B1-soft multi-squad shared-workspace) improves overall squad
mean-of-window-mean TQS by ≥ +0.02 over the A1 baseline, WITHOUT
anchor regression (Isagi, Bachira, Barou C1 status unchanged).

**Rejection:** each hypothesis is evaluated independently with its own
locked criterion (§5). AC.0 rejects → study STOPS with NEGATIVE
verdict. AC.1 passes only for agents/pitches that clear C1. AC.2
passes only for arms that clear H3 without violating anchor lock.

## 2. Empirical motivation (numbers locked from prior G7 rounds)

| Observation | Source | Motivates |
|---|---|---|
| E005 §2.5 excluded AUDUSD (p=0.032, +3.45 pips) and NZDUSD (p=0.096, +2.47) from the deployed router for `zone_d1_against` (Isagi's playstyle) | E005 REPORT §2.5 | AC.1 Chigiri arm on AUDUSD+NZDUSD — pairs where Isagi cannot fire have less crowding for a momentum-family agent |
| Φ4.1 Chigiri: 3,615 breakout Thoughts → 536 trades, mean TQS 0.229, win 39.9 % (lowest among trading agents), refined v1-iter-1 with M15×H1×H4 ADX + top-decile σ pending | evolution ledger 2026-06-30 | AC.1 Chigiri sub-arms — his refined guards target impulse subsets present in JPY/GBP that may be under-represented in EUR/CAD |
| Φ4.1 Rin: 3,094 precision-lift fires → 244 trades at +9.95 mean / −28.26 median (right-tail concentrated), regime-gate to `trending` + peer-disagreement pending | evolution ledger 2026-06-30 | AC.1 Rin sub-arms — precision playstyle may fit USDCHF (inverse-EUR safe-haven, similar structure) and USDJPY (structured trending pair) |
| Φ4.1 Kunigami: 25,877 warning Thoughts, 0 R5 consumers (pre-Φ4.2 wiring); currently retired as a proposer per §11.12 | evolution ledger 2026-07-01 | AC.1 Kunigami un-retirement sub-arms — defensive playstyle may fit rangy pairs (AUD/NZD) where dampening bites hardest |
| G7 Phase-Z (Bachira weave): Bachira C1 passed but Nagi C1 dropped (chemistry cost of halving proposal volume) | user brain dump 2026-07-20 | AC.2 chemistry constraint — Nagi ≥ 50 OOS trades floor in every arm |
| G7 Phase-AB (Barou multi-pair): PASS on `("USDCAD","EURUSD","GBPUSD")` with home-symbol privileges (devour lift) USDCAD-only | evolution ledger 2026-07-14 | Anchor lock for Barou — his passed config is inviolate |

## 3. Canon → mechanism mapping (locked BEFORE running arms)

The 8-agent squad has three positional archetypes (per doctrine §3.1):

- **Anchors** (locked to canon home): Isagi (`conservative_metavision`
  on EURUSD/GBPUSD/USDCAD), Bachira (`rebel_tight` — Phase Z v1-iter-1,
  same home), Barou (`solo_king` — Phase AB v1-iter-1, USDCAD+EURUSD+GBPUSD
  with USDCAD-only home privileges).
- **Peer-consumers** (derived pitch, not manually assigned): Nagi
  (`confluence_only`), Reo (`copier_hrp`). Their `.symbols` = union of
  anchor `.symbols` — they follow the peers they consume.
- **Movable pieces** (subject to this pre-reg): Chigiri
  (`speed_momentum`), Rin (`analytical_precision`), Kunigami
  (`defensive`, currently retired to R5 side channel).

Playstyle → pair-character prior (pre-locked mapping, evaluated
in AC.0 for detectability before AC.1 fires):

| Playstyle | Expected favouring character feature | Direction |
|---|---|---|
| `speed_momentum` (Chigiri) | high session-open impulse ratio | positive β |
| `speed_momentum` (Chigiri) | D1 chop fraction | negative β |
| `analytical_precision` (Rin) | tight H4 ATR percentile (structure) | negative β on ATR pct |
| `analytical_precision` (Rin) | moderate DXY-beta (not too USD-driven) | negative β on \|DXY-beta\| |
| `defensive` (Kunigami) | D1 chop fraction | positive β |
| `rebel_tight` (Bachira, anchor audit) | neutral D1 AC1 (no dominant HTF push) | negative β on \|D1 AC1\| |

## 4. Pair-character feature vector (locked)

Computed per pair over the panel training window
(2015-01-01 → OOS-start), never on OOS data:

- **`d1_ac1`** — first-order autocorrelation of daily log-returns.
- **`h4_atr_percentile`** — median H4 ATR-14 relative to the panel-wide
  distribution (0 = tightest, 1 = widest).
- **`session_impulse_ratio`** — average \|open-to-3rd-H4-close\| pip
  move / average H4 range, computed per major session (Sydney, Tokyo,
  London, NY). Stored as 4-vector; primary feature is `max(sessions)`.
- **`d1_chop_fraction`** — fraction of D1 bars where
  \|close − open\| < 0.3 × (high − low).
- **`dxy_beta`** — β of pair weekly returns regressed on DXY weekly
  returns (using dukascopy DXY proxy already in cache; if missing,
  drop feature and note in results).

### 4.1 Pair-character reference table (to be populated in AC.0 output)

| Pair | d1_ac1 | h4_atr_pct | max_session_impulse | d1_chop_frac | dxy_beta |
|---|---|---|---|---|---|
| EURUSD | *tbd* | *tbd* | *tbd* | *tbd* | *tbd* |
| GBPUSD | *tbd* | *tbd* | *tbd* | *tbd* | *tbd* |
| USDCAD | *tbd* | *tbd* | *tbd* | *tbd* | *tbd* |
| AUDUSD | *tbd* | *tbd* | *tbd* | *tbd* | *tbd* |
| NZDUSD | *tbd* | *tbd* | *tbd* | *tbd* | *tbd* |
| USDJPY | *tbd (needs cache pull)* | | | | |
| USDCHF | *tbd (needs cache pull)* | | | | |

Values ARE computed and committed to `results/pair_character.json` on
first AC.0 fire. Values are then FROZEN — no recomputation after
seeing agent results.

## 5. Arms and locked success criteria

### AC.0 — Meta-control: does pair character predict agent success?

**Panel:** current g7retry1-phi41 per-agent per-pair mean TQS
(banked telemetry from `reviews/g7_leave_one_out_verdict_phi5-arm4.md`
+ per-agent trade files). No new run; regress banked outputs against
the feature vector from §4.

**Statistic:** OLS with bootstrap 95 % CI. Per movable agent, per
character feature, report β and CI. Also report R² of the full
per-agent model.

**Pass threshold:** AC.0 PASSES if:
- For at least **2 of {Chigiri, Rin, Kunigami}**, at least ONE
  feature has bootstrap 95 % CI lower bound on \|β\| > 0.
- AND the pre-locked direction (§3) is respected for at least one
  passing agent-feature pair (i.e. we predicted the sign a priori).

**Pass threshold if AC.0 FAILS:** study STOPS. Written verdict:
"pitch-character-predicts-agent-success unsupported at n=5 pairs;
pitch-assignment concept unsupported without a larger panel; further
arms not authorised." Result committed as-is; no further arms fire.

### AC.1 — Per-agent multi-pitch fit (movable agents only)

Runs only if AC.0 PASSES. Each movable agent runs solo (rest of squad
still present as peer readers, but only the movable agent's
`.symbols` is changed) on a candidate pitch, evaluated via the G7
walk-forward panel extended per §7 to include the candidate's pairs.

**Sub-arms (locked, exhaustive per user 2026-07-20):**

| Sub-arm | Agent | `.symbols` | Prereq |
|---|---|---|---|
| AC.1.chi-a | Chigiri | AUDUSD, NZDUSD | none |
| AC.1.chi-b | Chigiri | USDJPY | cache pull |
| AC.1.chi-c | Chigiri | GBPUSD | none |
| AC.1.rin-a | Rin | EURUSD, USDCHF | cache pull |
| AC.1.rin-b | Rin | EURUSD, USDJPY | cache pull |
| AC.1.rin-c | Rin | USDCHF | cache pull |
| AC.1.kun-a | Kunigami (un-retire) | AUDUSD, NZDUSD | none |
| AC.1.kun-b | Kunigami (un-retire) | AUDUSD, NZDUSD, USDJPY | cache pull |

**Pass threshold (per sub-arm):** the movable agent passes G7 §3.11.5
C1 on the sub-arm's `.symbols`:
- mean TQS ≥ 0.30 AND per-window mean TQS ≥ 0.20 in ≥ 5/7 rolling
  OOS windows AND bootstrap 95 % CI lower bound on mean TQS > 0.25.
- Multiple sub-arms may pass per agent; the agent's "passing pitch
  set" is the union of `.symbols` from all passing sub-arms.

### AC.2 — Squad composition arms

Runs only if AC.1 produces ≥ 1 passing sub-arm per agent (else that
agent stays at canon home). Consumes ONE OOS touch per arm on the
extended G7 walk-forward panel.

**Arms (locked):**

| Arm | Shape | Definition |
|---|---|---|
| **A1** | baseline (control) | current wiring: anchors at canon home, movables at doctrine defaults (Rin EURUSD only, Chigiri EURUSD+GBPUSD, Kunigami retired). Reproduces the current 3/7 verdict on the extended panel for shared reference. |
| **A2** | single-squad, per-player home-pitch widened | anchors unchanged; movable agents' `.symbols` = passing-pitch-set from AC.1 (union with current home if user pre-declares "additive only"; see §5.1 flag). One `SquadRoster`, one workspace, one thought stream. |
| **B1-hard** | multi-squad, HARD isolation | three independent `run_squad_live.py` processes (or equivalent scoring harness invocations), each with its own workspace/thought stream/paper broker. Pitches: **Bastard Munich** (Isagi + Rin, EURUSD + Rin's AC.1-passing pitches); **Manshine City** (Bachira + Chigiri + Nagi + Reo, GBPUSD + Chigiri's AC.1-passing pitches + AUD/NZD); **Barou solo** (Barou, USDCAD + EURUSD + GBPUSD per Phase AB). |
| **B1-soft** | multi-squad, SOFT isolation | same rosters and pitches as B1-hard, but ALL squads share one workspace/thought stream (one process, N sub-rosters iterated per tick). Measures the pure "cost of process isolation" vs "cost of pitch specialisation". |

### 5.1 §5 §5 Additivity flag (locked BEFORE any arm fires)

For A2 and B1-*: does each movable agent's `.symbols` UNION with
their current canon home, or REPLACE it?

- **UNION (additive):** e.g. Rin `.symbols = ("EURUSD","USDCHF")` if
  AC.1.rin-a passes. Preserves current wins; adds new terrain.
- **REPLACE (substitutive):** e.g. Rin `.symbols = ("USDCHF",)` if
  ONLY AC.1.rin-c passes. Cleaner test of "did we find a better
  home"; risks losing legit EURUSD trades.

**Locked choice (pending user ratification):** **UNION** — additive
matches the user's "players can succeed in multiple fields"
constraint. Any REPLACE-mode variants would need a Phase AC.2
amendment.

### 5.2 Success criteria for AC.2 (all locked)

- **AC2.1 — anchor lock:** Isagi, Bachira, Barou per-agent C1 pass
  status is IDENTICAL to their arm-A1 baseline in every AC.2 arm.
  Any regression kills that arm.
- **AC2.2 — squad lift (primary):** arm's squad mean-of-window-mean
  TQS ≥ A1 baseline + 0.02, bootstrap 95 % CI lower on the delta > 0.
- **AC2.3 — Nagi volume floor:** Nagi ≥ 50 OOS trades in every arm.
  Below-floor arms fail on chemistry regardless of TQS.
- **AC2.4 — no C3 poisoning:** no agent's C3 (same-tick collision
  clean-window count) drops by ≥ 2 windows in any arm vs A1.
- **AC2.5 — isolation-cost audit (non-decisive):** report
  `mean_tqs(B1-soft) − mean_tqs(B1-hard)`. Expected positive
  (soft > hard). A NEGATIVE delta would be a surprising finding
  worth noting but does not fail any arm.

## 6. Statistic (locked)

- Per-agent C1: mean TQS, per-window mean, bootstrap 95 % percentile
  CI (n=10,000 resamples). Same as G7 §5.
- Squad TQS: mean-of-window-mean across all trading agents in the
  arm's roster (Kunigami excluded if retired in that arm).
- Bootstrap unit: OOS window (K=7 rolling), not individual trades —
  matches G7's window-level bootstrap.
- FDR budget: BH q=0.10 across the 8 AC.1 sub-arms + 4 AC.2 arms ×
  5 AC.2 criteria = **28 tests total**. Family-wise q-adjusted.

## 7. Harness extension required (methodology, not strategy)

`run_g7_v1_checkpoint_gate.py` today hardcodes
`SYMBOLS_G7 = ("EURUSD","GBPUSD","USDCAD")` at module level (line 86).
This pre-reg requires:

1. Promote `SYMBOLS_G7` to a CLI/config parameter with default
   preserved for backwards-compat.
2. Extend the panel loader to handle the new symbols (USDJPY/USDCHF)
   once cached.
3. Add unit tests that a per-agent `.symbols` restriction is honoured
   by the harness (agent skips ticks outside its `.symbols`).

Landing: separate infrastructure commit BEFORE AC.0 fires, tagged
`phase-ac-harness-extension`.

## 8. Panel

- Symbols: EURUSD, GBPUSD, USDCAD, AUDUSD, NZDUSD, **USDJPY** (needs
  cache pull), **USDCHF** (needs cache pull).
- Training window: 2015-01-01 → OOS-start (per G7 §4).
- OOS windows: 7 rolling, same schedule as G7 (post-W walk-forward).
- Feature vector (§4): computed on training window only per pair.

## 9. Pre-mortems

- **AC.0 low power at n=5 pairs.** With only 5 banked-panel pairs and
  5 features, β estimates are noisy. Mitigation: pre-locked directions
  (§3) are used as a directional-only test even if magnitude is
  underpowered. If AC.0 fails, the honest verdict is "unsupported at
  n=5", not "hypothesis rejected".
- **USDJPY/USDCHF character may not match priors.** JPY has been
  atypically trend-heavy 2022–2024 (BoJ policy shift); USDCHF has
  had SNB regime discontinuities. Feature values are computed on
  full training window, but the OOS windows may not reflect those
  regimes. Mitigation: pre-declare that AC.1 pass on USDJPY/USDCHF
  requires ≥ 4/7 (not 5/7) window pass for those pairs — one-window
  relaxation for regime-shifted pairs. Written into the C1 threshold
  in the sub-arm rows in §5.
- **A2 vs B1 may not be separable at panel size.** With 7 OOS windows,
  the squad-TQS delta between A2 and B1-* may be within noise.
  Mitigation: AC2.5 (isolation-cost audit) is non-decisive; the
  primary is AC2.2 (any arm ≥ +0.02 over A1).
- **Peer-confluence lift audit.** B1-hard breaks the
  `BACHIRA_PEER_CONFLUENCE_LIFT` (+0.05 when Isagi's Thought carries
  a fired zone signal, `a02_bachira.py:96`). Measured directly by
  the B1-soft vs B1-hard delta.

## 10. Kill conditions (PROTOCOL_DISCIPLINE §5, §7)

- No post-hoc statistic swaps.
- No retuning of playstyle × character mapping (§3) after seeing AC.0
  output.
- No widening of AC.1 candidate pitch list after seeing AC.0.
- No shifting anchor `.symbols` in any arm.
- If USDJPY/USDCHF cache pull incomplete when AC.0 fires, sub-arms
  chi-b, rin-a, rin-b, rin-c, kun-b DROP from the batch; the study
  ships as a partial with a NEEDS-CACHE-PULL amendment slot for
  those sub-arms.

## 11. File footprint plan

| File | Content |
|---|---|
| `results/pair_character.json` | §4 feature vector per pair, computed once, frozen. |
| `results/ac0_regression.json` | AC.0 β/CI table per agent × feature. |
| `results/ac0_verdict.md` | AC.0 pass/fail written verdict. |
| `results/ac1_<agent>_<pitch>.json` | AC.1 sub-arm C1 output per sub-arm. |
| `results/ac1_summary.md` | AC.1 passing-pitch-set per movable agent. |
| `results/ac2_<arm>.json` | AC.2 arm output (per-agent C1, squad TQS, chemistry deltas). |
| `results/ac2_verdict.md` | AC.2 arm-by-arm verdict and portability note for `next-gen`. |
| `POSTMORTEM.md` | Written after study completes; standard evolution-ledger row per arm. |

## 12. Sequencing

1. **Cache pull** — USDJPY + USDCHF H4 + D1, 11 years, via
   `scripts/refresh_cache.py` on the VM (draft ready).
2. **Harness extension** — §7 changes committed to
   `multi-agent-ensemble` as `phase-ac-harness-extension`.
3. **AC.0 fire** — regression on banked panel + feature vector.
   PASS gates AC.1; FAIL stops the study.
4. **AC.1 fire** — all 8 sub-arms (or 3 if cache pull incomplete).
   PASS produces per-agent passing-pitch-set.
5. **AC.2 fire** — 4 arms (A1, A2, B1-hard, B1-soft) on the extended
   G7 panel.
6. **Verdict** — POSTMORTEM.md, evolution-ledger row per movable
   agent, port-plan for `next-gen` if any arm PASSES.

## 13. Amendment procedure

Per doctrine §11 and PROTOCOL_DISCIPLINE §5: this pre-reg is BINDING
once committed to `multi-agent-ensemble`. Any change requires an
amendment file
(`AMENDMENT_YYYY-MM-DD_<slug>.md`) referencing the changed §; no
in-place edits after commit. Values in §4 and §5 are frozen at
first-AC.0-fire time.

---

**Status:** DRAFT (2026-07-20). Not yet committed. Pending:
- USDJPY / USDCHF cache pull authorised (§12.1).
- Additivity flag ratification (§5.1 — currently UNION).
- Harness extension implemented (§7).
- User final green-light for `git add` on `multi-agent-ensemble`.
