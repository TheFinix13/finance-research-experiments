# Phase AD — Karasu Tabito news-defender (pre-registration DRAFT)

- **Registered:** 2026-07-20 (DRAFT — untracked working-tree file in
  `finance-research-experiments`; not yet committed). Sibling
  implementation commit lives on `next-gen` of the trading-agent
  repo (`multi-pair-trading-agent`) at `2df58ae`
  *"karasu: news defender agent + Sentinel R7 (advisory-only)"*.
- **Program:** M001 multi-agent ensemble.
- **Branch (target for merge, when ratified):** `multi-agent-ensemble`
  (research repo). This draft on `main` is the standard M001 WIP
  pattern; it moves to `multi-agent-ensemble` only after user
  ratification and once Phase AC exits the shared working tree.
- **Authorization:** user 2026-07-20 (this session). Motivated by the
  3-year detector audit (`data/agent_3yr_v5_M15H1.db`, 2023-05 to
  2026-05) finding that NY-time hour 13 bleeds -857 pips on EURUSD
  and a non-trivial chunk of that came from scheduled high-impact
  USD prints. The trading-agent repo already has the primitive
  (`agent.news.calendar` + `agent.news.blackout`); Karasu wraps it
  into a Blue Lock squad side-channel + Sentinel R7 rule and asks
  the walk-forward panel whether that changes drawdown / TQS.
- **Lever slot:** side-channel gate lever. This does NOT touch the
  proposer roster or aggregator; it modifies only the
  Sentinel-admission path. G7 §11.17 walk-forward panel is the
  evaluation vehicle, sharing OOS budget with any concurrent Phase
  AC arm evaluation (see §5 stop rules).

---

## 1. Problem (banked evidence)

**Bank 1 — hour-13 EURUSD bleed:** the 3-year audit shows an EURUSD
NY-time-hour-13 pnl of **-857 pips** across the 3-year window.
That's the empirical prior. The prior is agnostic on cause; several
of the largest daily bars in that hour coincide with scheduled
high-impact USD prints (FOMC, CPI, NFP). Blocking hour 13 entirely
kills profitable London-close setups too. `agent.news.blackout`
was the existing partial answer: a ±15-min window around each
scheduled high-impact USD/EUR release, deployed pre-Karasu at the
rule-engine layer.

**Bank 2 — R7 is a squad-layer distinction:** Kunigami's R5
dampener (§3.11.12) demonstrated the pattern: an auxiliary Tier-2
agent + a Sentinel rule that consumes his signal on admission.
Karasu ports the same shape to news data: he observes on every
tick, publishes advisory Thoughts to the F21 workspace, and
exposes `warning_active_at(as_of, symbol) -> KarasuWarning` for
R7. The two-agent-plus-two-rules pattern is already a doctrinally
supported architecture — this phase measures whether the news
side-channel version of it actually reduces drawdown without
costing material alpha.

**Bank 3 — three-tier response makes drawdown reduction plausible
without a full block:** the two-knob ladder (BLOCK on high impact,
SCALE 0.5 on medium impact, pass-through on none) preserves
Medium-impact edge (which the ±15-min hard block would kill) while
still removing High-impact tail risk. The 0.5 scale factor is the
same magnitude as R5's dampener, chosen for consistency, not
empirically tuned.

## 2. Canon → mechanism mapping (locked BEFORE running arms)

Canon Karasu is the cerebral defender who reads the field and
communicates positioning to the team. In the trading agent:

- "reads the field" = pulls the ForexFactory weekly calendar (via
  the already-implemented `agent.news.calendar` module) and computes
  `warning_active_at(as_of, symbol)` per (symbol, timestamp).
- "communicates positioning" = publishes an advisory Thought to the
  F21 workspace with `expected_action="advisory_blackout"` and
  `conviction=0.0`. NEVER proposes. `intend()` always returns None.
- "defensive read" = Sentinel R7 consumes the warning on admission;
  the striker never has to know news exists.

**Single-variable change from the pre-Karasu baseline:**
Sentinel R7 (news-impact ladder) is enabled. All other roster /
aggregator / R1-R6 wiring is byte-identical to the G7 §11.17 gate
baseline. Karasu himself has ZERO effect on trades when R7 is
disabled (his `intend()` returns None, so he never enters the
proposal stream). The measurement is therefore isolated to the R7
Sentinel layer.

**Ladder knobs (locked; no post-freeze retuning):**
- `news_impact_block_min = {"High"}`
- `news_impact_scale_medium = {"Medium"}`
- `news_impact_scale_factor = 0.5`
- Window: ±15 min around each event.
- Watched currencies: {USD, EUR, GBP, CAD, AUD, NZD, JPY, CHF}
  (Karasu's full 7-pair-derived scope).

**Empirical priors, banked honestly:**
- **Prior FOR:** the 3-year hour-13 bleed is real and part of that
  bleed is high-impact-USD prints. Blocking those windows should
  measurably reduce worst-window drawdown.
- **Prior AGAINST:** blackout windows kill both winning and losing
  trades inside them; if the -857 hour-13 pips are dominated by
  UNSCHEDULED news / regime-shift bars rather than scheduled
  prints, R7 will reduce trade count without reducing drawdown
  proportionally.
- **Prior on rare-event volume:** high-impact USD prints are ~4-8
  per month; even the panel's widest windows only see 20-40 R7
  interactions per arm. Criterion AD3 sets a sanity floor of ≥10
  advisories per month to catch a broken cache path early.

## 3. Implementation plan

**Trading-agent repo (already landed on `next-gen`, commit `2df58ae`):**
- `agent/squad/agents/a08_karasu.py` — Karasu class, KarasuWarning
  dataclass, load_calendar, warning_active_at.
- `agent/squad/sentinel.py` — added `check_r7_news_impact()`; four
  new fields on `SentinelContext` for the ladder input; three new
  fields for ladder knobs (defaults locked here).
- `agent/squad/roster.py` — Karasu instantiated, `roster.karasu`
  attribute; not in `proposers`.
- `agent/squad/engine.py` — Karasu observes each tick (workspace
  publish); admission gate resolves warning per proposal
  `(timestamp, symbol)` and feeds it into SentinelContext.
- `agent/squad/news_config.py` — shared `NewsDefenderConfig`.
- `agent/squad/news_refresher.py` — background daemon thread.
- `scripts/run_squad_live.py` — non-blocking refresh hook.
- `tests/test_squad_karasu.py` — 16 tests, all pass.

**Research-repo harness plan (to land on `multi-agent-ensemble`
when ratified):**
- New harness flag `--sentinel-r7-enabled` on the G7 walk-forward
  driver; when set, hydrates the Karasu calendar from a frozen
  snapshot fixture (see §7 artifacts) and feeds R7 into admission.
- Baseline arm: R7 disabled (`karasu_impact` forced to "none"
  regardless of calendar).
- Treatment arm: R7 enabled, ladder knobs at their §2 locked
  defaults.
- Both arms use identical proposer roster + aggregator (phi41),
  identical bars, identical seeds. Ledger diff is the R7 effect.

## 4. Success criteria (locked; evaluated ONCE on the §11.17 replays)

Baselines referenced are the §11.16 `g7retry1` numbers plus the
Phase AB / AC panel extensions that land before AD.

- **AD1 — drawdown reduction (primary):** panel-wide worst-window
  drawdown (in pips) drops by **≥ 15 %** in the R7-enabled arm vs
  the R7-disabled arm.
- **AD2 — no C1 regression:** every anchor's (Isagi, Bachira,
  Barou) mean TQS delta is **≥ −0.02** vs the R7-disabled arm.
  Karasu shouldn't cost material alpha to the confirmed strikers.
- **AD3 — advisory publish rate:** Karasu publishes **≥ 10
  advisories/month** on the panel window (sanity floor — catches
  a stale-cache or broken currency-scope path).
- **AD4 — false-blackout audit (non-decisive):** ≤ 5 % of Karasu
  blackouts should coincide with an event whose actual value was
  within ±0.5σ of consensus (proxy for "the event was a non-event
  and R7 needlessly gated a trade"). NON-DECISIVE in v1 because
  the fixture does not include `actual` values yet; deferred to
  Phase AD.2 as a follow-up gate.

**Phase verdict:** PASS iff AD1 AND AD2 AND AD3. AD4 is an audit
row only in v1. Anything else is FAIL or PARTIAL with the failing
criteria named.

## 5. Stop rules / anti-leakage

1. One evaluation. Failure STOPS the lever — no ladder retuning
   (block/scale/factor stay at §2 values) against the same OOS
   windows.
2. R7 is enabled OR disabled at the harness level for the entire
   panel; no per-window / per-symbol on/off flipping.
3. If AD1 passes but AD2 fails, DO NOT attempt "R7 with
   ScaleFactor=0.8" as a retry — that's a fresh pre-reg (Phase
   AD.2) with its own OOS discipline.
4. Infra reruns (identical seed, identical fixture, identical
   code) are not analysis iterations.

## 6. Multiplicity note

Karasu is the first news-side-channel lever in M001. R7 is a new
Sentinel rule (not a Kunigami-R5 retune). No G7 threshold is
touched. See G7 §11.17 for the walk-forward multiplicity budget;
this lever consumes one OOS touch shared with any concurrent Phase
AC squad-composition arm.

## 7. Artifacts

- **Calendar fixture:** `programs/M001_multi_agent_ensemble/data/
  news_calendar_frozen_YYYY-MM-DD.json` — a snapshot of the FF
  weekly XML covering the entire G7 walk-forward panel, taken
  once at pre-reg registration time. Never refetched during a
  study run.
- **Verdict:** `reviews/phase_ad_verdict.md` + numbers appended to
  the §11.17 gate report table. EXPERIMENTS.md + ai_context.md
  rows updated on completion.
- **Trading-agent implementation:** `next-gen` @ `2df58ae`. Any
  Phase AD.2 amendment (e.g. surprise-z gating) MUST be a new
  trading-agent commit with a new pre-reg here.

## 8. Known limitations (documented up front)

- Sae (A9) is disabled by default in the trading-agent roster.
  This phase evaluates Karasu WITHOUT Sae; Sae's Phase AE pre-reg
  is a separate lever. If Sae is later enabled AND Karasu is
  active, R7 would BLOCK Sae's proposals on the exact events Sae
  wants to trade. Documented as an operational tension for the
  Phase AE research (see Phase AE §8).
- Karasu depends on the ForexFactory weekly XML feed. Cache-only
  mode works but stale after 6 h (the cache TTL). The live
  runtime's background refresher (`NewsFeedRefresher`) mitigates
  this in operation; the research harness uses a frozen fixture
  (§7) so the study result is reproducible.
- Karasu's currency → symbols map (`news_config.py`) covers the
  8 majors we expect the future panel to include. If the panel
  ever adds a cross (EURJPY, GBPAUD, etc.), the map needs an
  amendment BEFORE R7 can meaningfully gate those symbols.
