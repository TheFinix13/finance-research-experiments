# E033 — Scheduled-news blackout window for the deployed fade cell

Status: **PRE-REGISTERED (DRAFT for approval) 2026-08-13** · commit
hash recorded below once approved and pushed. No Stage-1 outcome has
been computed at registration time.

Follows `PROTOCOL_DISCIPLINE.md` in full. Register a `planned` row in
`EXPERIMENTS.md` at the pre-registration commit; add the
`DATA_LEDGER.md` row when Stage 1 starts.

---

## 0. Motivation (hypothesis-generating evidence, not proof)

The deployed cell (`zone_d1_against` / H4 / all, EURUSD + GBPUSD +
USDCAD) is blind to the economic calendar. In the 2026-08-01 → 08-10
live week, the Aug 7 NFP release ran directly over both open positions
(EURUSD short −1.53R, USDCAD long −2.40R) and triggered the daily-DD
halt; on 2026-08-11, CPI reversed the open GBPUSD trade from profit to
a breakeven exit. The user's read: "the only reason some trades won on
news days is that the news happened to go their way" — i.e. the cell
is not trading news, it is coin-flipping through it.

**Priors AGAINST a blackout, stated for the record:**

- **Phase AD.2 (M001, 2026-07-28).** The C-style holding-window
  variant of the Karasu news gate engaged 166 squad trades over 11
  years — and the gated trades were **net winners** (+3.18 pips
  mean). Banked explicitly as "the prior AGAINST a future C lever".
  Population caveat: squad proposals, not the deployed fade cell —
  but it is the closest measured cousin and it points the other way.
- Symmetry: a blackout removes both tails. Wins that ride favourable
  releases are deleted along with the losses the user remembers.

**Priors FOR a blackout:**

- **Phase AE (M001, 2026-07-24, FAIL).** The Sae event specialist
  could not TRADE scheduled events (OOS mean TQS 0.097, 28.7% wins),
  and the verdict's reading of the hour-13 bleed was "**avoidable,
  not tradable**" — precisely the blackout hypothesis: the edge is in
  not being there, not in being there smarter.
- The 2026-08-07 live tape (descriptive, n = 2 trades, quarantined as
  motivation).

E033 settles which prior applies to the deployed cell's own ledger.
If the family dies — the AD.2 prior generalises and blackout windows
delete as much win as loss — that is a valid, useful outcome: it
closes the "we must hook up news" thread with evidence instead of
recency bias.

## 1. Hypothesis (operational)

Two treatment families, tested as separate FDR families on the same
calendar (user directive 2026-08-13: "test both"):

**Family A — entry suppression (Stage 1a).** An arm is a blackout
window `[T − pre, T + post]` around each scheduled high-impact
release time `T`. Under an arm, every ledger trade whose **entry fill
timestamp** falls inside any window is suppressed (removed from the R
sequence); all other trades are untouched. Exits unmodified.

**Family B — open-position de-risking (Stage 1b).** An arm acts on
trades whose position is still OPEN when a window opens (entered
before `T − pre`, original exit after `T − pre`) — the 2026-08-07
NFP shape, where both live losses were carried INTO the release, not
opened during it. Two actions, repriced deterministically on the H4
bar record:

- `flatten_pre_event` — close at the open of the first H4 bar at or
  after `T − pre`.
- `tighten_to_be_pre_event` — at that same bar open, if the trade is
  in profit, move the stop to entry (breakeven); replay the remaining
  H4 path: first bar whose range touches entry exits at entry,
  otherwise the original exit stands. Trades not yet in profit are
  left untouched (mirrors the live GBPUSD CPI case, which only
  survived because BE had already migrated — this arm asks whether
  forcing that migration before every red release generalises).

- **H1:** at least one arm (either family) improves the per-trade R
  sequence — Δ Sharpe bootstrap-95% CI lower bound > 0 on at least
  one symbol, fold-stable, surviving BH-FDR within its family.
- **H0:** neither entering less around news nor de-risking into news
  measurably beats the cell trading straight through it.

Outcome metric (primary, both families): **Δ Sharpe of the per-trade
R sequence** (counterfactual minus baseline, unannualised, per
symbol).

## 2. Separation

- Touches the trading agent: **no.** Stage 1–2 are pure ledger
  arithmetic in `programs/E033/` (lab-side). Phase 3 — an entry-time
  blackout check in the v1 signal path (and, separately, the v2
  Karasu R7 evidence base) — is a **gated** deliverable in
  `multi-pair-trading-agent`, authorised only by an `alive` verdict
  here, and goes through its own review.
- **Grid-inertness distinction from AD.2.** AD.2 found point windows
  structurally inert on the H4 bar-OPEN grid (13:30/18:00/19:00 UTC
  releases never fall within ±15 min of a 00/04/…/20 anchor). The v1
  deployed cell does NOT share that geometry: entries are intra-bar
  zone-touch limit fills, so entry timestamps are continuous on the
  clock and windows of ±30 min or more can genuinely engage. Stage 0
  measures the engagement rate before anything is scored (§5 stop
  rule), so inertness is detected, not assumed away.
- Prior uses of the same data slice: the deployed-cell ledgers
  (E013 `all_on` harness; EURUSD 737-trade ledger locked at E017 §A1)
  are the shared substrate of E013/E017/E019/E020/E021/E024/E025/E026.
  E033 opens a **new family** (calendar-conditioned exclusion) for
  FDR purposes; no intra-trade paths are consumed.

## 3. Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Event calendar | Phase AE frozen fixture `programs/M001_multi_agent_ensemble/experiments/phase_ae_sae_event_specialist/data/news_calendar_frozen_2026-07-24.json` (NFP / CPI / FOMC, USD, 349 events, sha256 `cfd18602…`), read-only | Already frozen and hash-pinned; no fresh acquisition dependency; the three event types that motivated the study |
| Currency-matched extension (EUR/GBP/CAD events) | **OUT of Stage 1** | Needs a new frozen fixture; adding it post hoc would be a family extension. Stage-2 candidate only, own amendment |
| Family A arms `(pre, post)` minutes | {(30, 30), (60, 60), (120, 60), (120, 120), (240, 120)} + `event_day` (entire UTC calendar day of the release) | 5 point windows spanning "release minute only" to "half a session", plus the user's actual heuristic ("NFP week killed us") as the 6th arm. Six settings; no post-hoc widening |
| Family A size | 6 arms × 3 symbols, decisions per symbol | E005 posture: per-symbol survival, not pooled averaging |
| Family A suppression rule | entry fill timestamp ∈ any window ⇒ trade removed; ties/overlaps resolved by union of windows | Deterministic; no exit modification in Family A |
| Family B arms | {`flatten_pre_event`, `tighten_to_be_pre_event`} × `pre` ∈ {4h, 8h} | Two actions × two lead times = 4 arms per symbol. H4 bars bound the repricing resolution, so sub-4h lead times are not honestly computable from this data plane — declared, not fudged |
| Family B size | 4 arms × 3 symbols, decisions per symbol; **separate BH family from A** | Different mechanism (exit-side vs entry-side); pooling them would let one family's power mask the other's |
| Family B repricing | exit at first H4 bar OPEN at or after `T − pre`; BE-touch replay on subsequent bar ranges; a trade caught by multiple windows uses the earliest | Deterministic from the bar record; no look-ahead (the bar open is the first price known after the decision time) |
| Ledger / window | deployed-cell ledgers, 2015-01-01 → 2025-12-01 | Same substrate and window as E017/E020–E026 |
| Walk-forward folds | 5 (E004 folds) | House convention; no test-slice leakage |
| Bootstrap | 5,000 resamples, seed 42, per-trade resampling with window classification held fixed | Convention |
| Stage-1 FDR | BH α = 0.10 over the 6-arm family per symbol (joint fold p via Stouffer, weights √n_fold) | E024 §5.4 convention |

## 4. Statistical pipeline

| Stage | Pairs | Period | Family size | FDR |
|---|---|---|---|---|
| 0 engagement count | EURUSD, GBPUSD, USDCAD | 2015-01 → 2025-12 | — (no outcomes computed) | — |
| 1a screen (entry suppression) | EURUSD, GBPUSD, USDCAD | 2015-01 → 2025-12, 5 folds | 6 per symbol | BH α = 0.10 |
| 1b screen (position de-risking) | EURUSD, GBPUSD, USDCAD | same | 4 per symbol | BH α = 0.10 (own family) |
| 2 confirm (gated) | surviving arm(s) only | same | ≤ 3 | per-cell α = 0.05 |

**Stage 0 (engagement, outcome-blind).** For each arm and symbol,
count touched trades per fold (Family A: suppressed entries;
Family B: positions open into a window) — nothing else. Computed and
reported BEFORE any R sequence is touched.

**Stage 1 (screen).** For each engaged arm: counterfactual R sequence
per (symbol, fold); Δ Sharpe point estimate + bootstrap CI; fold
positivity; joint fold p; BH within the arm's own per-symbol family
(6 for A, 4 for B).

**Secondaries** (guardrails, never promotable to primary):

1. Touched-cohort mean R with 95% CI — is the cohort actually bad?
2. **Winners eaten** — Family A: count and total R of suppressed
   trades that finished positive; Family B: count and total R given
   back on trades whose ORIGINAL path went on to hit TP after the
   flatten/tighten point (the AD.2 check, reported per arm, always).
3. Δ mean R and Δ tail-mean R (worst 10%).
4. Touched-trade count per fold (power/context).
5. Family B only: Δ R on the touched cohort split by "in profit at
   window open" vs "underwater at window open" — the user's
   observation is that BE-migrated trades already survive news (CPI
   GBPUSD) while trades still underwater get blown out (NFP EURUSD /
   USDCAD); this split tests that reading directly.

**Stage 2 (gated on ≥ 1 alive arm, run per family).** The winning
arm is re-scored against a placebo: the same windows (Family A) or
the same de-risking actions (Family B) applied around an equal number
of randomly-placed non-event weekday timestamps (seed 42, 200
placements) — the arm's Δ Sharpe must exceed the placebo 95th
percentile, killing "any exclusion/de-risking of random hours helps"
as an alternative explanation. Family A's winner is additionally
compared against the `event_day` control arm.

## 5. Stop rules

- **Stage-0 floor:** if an arm touches < 30 trades pooled across
  folds on a symbol, that (arm, symbol) is `underpowered` — excluded
  from its family (family size shrinks accordingly, recorded in the
  report) and cannot produce a claim. If ALL arms of a family are
  underpowered on all symbols → that family STOPS after Stage 0;
  report the engagement table (the AD.2-style inertness outcome for
  limit fills, worth knowing on its own). Families stop
  independently — A dying does not kill B or vice versa.
- If 0 arms are `alive` after Stage 1 in BOTH families → STOP; no
  grid extension, no new actions, no new event types. Write
  `STOP_NOTICE.md`.
- If the winning arm fails the Stage-2 placebo → verdict downgrades
  to `parked_placebo_equivalent`; not deployable.

## 6. Verdict labels (locked)

- **`alive`** — CI-LB > 0, fold-positive ≥ 4/5, joint p < 0.05,
  survives BH (all per symbol), and survives the Stage-2 placebo.
  Authorises Phase 3 design work (v1 wiring proposal), which still
  needs its own review before any live change.
- **`parked_low_yield`** — directionally positive, CI includes 0.
- **`parked_winner_heavy`** — Δ Sharpe clears the bar but the
  suppressed cohort's winners-eaten share exceeds 50% of suppressed
  trades: the gate mostly deletes wins and profits only via the tail.
  Requires explicit user trade-off review; does not auto-advance
  (mirrors E024's `parked_false_positive_heavy` and the AD.2 prior).
- **`dead`** — nothing clears. The deployed cell keeps trading
  through news; the "hook up fundamentals" thread closes with
  evidence.

## 7. Amendments

(Empty at pre-registration. Any change follows `PROTOCOL_DISCIPLINE.md`
§5 — dated subsection, rationale, committed before the amended
analysis runs. No silent edits.)

---

## Cross-references

- **Live motivators (descriptive, quarantined):** 2026-08-07 NFP —
  EURUSD short −1.53R + USDCAD long −2.40R carried INTO the release
  (Family B's exact shape), daily-DD halt (weekly report
  2026-08-01→10); 2026-08-11 CPI — GBPUSD survived on an
  already-migrated breakeven stop (Family B's `tighten_to_be` arm
  asks whether forcing that migration generalises).
- **Successor study (E034 candidate, own pre-registration, NOT
  authorised here):** event-distance as a continuous REGIME FEATURE —
  time-to-nearest-red-event modulating conviction/size/stop-width
  instead of a binary gate. Gated on E033's evidence either way: an
  `alive` E033 says the naive binary version already pays (E034 asks
  if graded beats binary); a `dead` E033 with a fat touched-cohort
  variance says the cohort is high-variance-zero-mean (E034 asks if
  sizing down, not skipping, captures that). Stage-3 directional
  interpretation (surprise vs consensus) stays in the v2/SAE lane —
  it is alpha, not a filter, and competes with the squad's
  event-specialist design brief.
- **Prior AGAINST:** Phase AD.2 verdict
  (`programs/M001_multi_agent_ensemble/experiments/phase_ad2_karasu_window_semantics/`)
  — C-variant gated squad trades net winners (+3.18p mean).
- **Prior FOR:** Phase AE REPORT — event trades "avoidable, not
  tradable" (OOS TQS 0.097, 28.7% wins at 1.5R).
- **Calendar fixture:** Phase AE frozen calendar (sha256-pinned,
  read-only consumption; E033 never regenerates it).
- **Baseline cell:** E004 walk-forward + E005 cross-pair sealed
  (`zone_d1_against` H4 all, 1.5R TP — untouched here).
- **Substrate ledgers:** E013 `all_on` harness; E017 §A1 locked
  EURUSD ledger.
- **v2 sibling:** Karasu R7 news defender (live in the squad
  Sentinel) — an `alive` E033 verdict is also the first quantitative
  evidence base for Karasu's window widths; a `dead` verdict bounds
  what R7 should be expected to add.

## Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| 0–1a | Deployed-cell trade ledgers (EURUSD/GBPUSD/USDCAD H4, 2015-01→2025-12) × Phase AE frozen calendar | new calendar-conditioned exclusion family; `planned` row added to `DATA_LEDGER.md` at Stage-1 start | ledgers: E013/E017/E019/E020/E021/E024/E025/E026; calendar: Phase AD.2 / AE (M001 lane) |
| 1b | same ledgers + H4 parquet bars (same slices, read-only) for flatten/BE repricing | new exit-repricing family on already-consumed bar slices — no fresh seal consumed, no OOS window opened | H4 bars: E004/E005 and every replay since |
| 2 (gated) | same + 200 seeded placebo window placements | conditional on Stage-1 alive | none |

---

**Pre-registration commit:** `b62eae1` (2026-08-13, pushed to
`origin/main`; user approved the two-family scope in the 2026-08-13
session before registration).
