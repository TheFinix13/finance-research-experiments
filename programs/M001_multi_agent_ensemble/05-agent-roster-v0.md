# 05 — Agent Roster v0 (Blue Lock cast)

**Status:** `DRAFT v0.8` — 2026-07-01 (v1/v2 versioning discipline
clarification landed per `06-blue-lock-doctrine.md` v0.5 §3.11.5;
new **Version status** column added to §1 table replacing the
inconsistent inline v1/v2 markers; per §3.11.5 only A1 Isagi has
reached the v1 checkpoint (Φ3 PASS analog) — all seven other
implemented agents are `pre-v1 (mechanic in flight)` pending the G7
v1-checkpoint gate; three new v1 primitives — F19 `lot_intent`, F20
`risk_intent`, F21 `read_workspace` — are v1 requirements per
doctrine §4.1a and must be implemented on every agent before G7 fires;
per-agent playstyle mapping table in doctrine §4.1a is the canonical
source for each agent's F19/F20 defaults). v0.7.1 stands below.

**Status:** `DRAFT v0.7.1` — 2026-06-25 (Barou row amended 2026-06-30;
A10 Kunigami row un-deferred 2026-06-30 post Sentinel R1–R6 wiring).
v0.7 marks the **Φ4.1 expanded-squad gate landing + first three
§3.11 sketch resolutions**. The Φ4.1 squad ran 8 agents (A1 Isagi v1,
A2 Bachira v1, A3 Rin v1, A4 Chigiri v1, A5 Reo v1, A6 Nagi v1, A7
Barou v1, A10 Kunigami v1) on EURUSD + GBPUSD + USDCAD H4 2015–2025.
**Verdict:** FAIL at **0.92× Isagi-alone TQS** (squad TQS 0.2922,
Isagi-alone 0.3175). The Φ4 predicate-starvation diagnosis was
**confirmed and fixed** — Nagi's confluence-firing thought count
moved 0 → 34,302 — but a new failure mode surfaced: **structural
crowding-out**. Isagi made 0 trades and Barou made 0 trades, fully
cannibalised by Bachira's `+0.10` rebel-lift on the same baseline-
zone primitive. Per-agent rows below carry the **v1 implemented**
status plus the empirical Φ4.1 telemetry. **Three §3.11 sketch
resolutions applied** (per `reviews/v2_arc_backlog_resolution_2026-06-25.md`):
A6 Nagi v2 DROPPED (v1 floor empirically correct, mean TQS 0.349
highest in squad); A7 Barou v2 REDESIGNED to hybrid mechanic A
(closed-loss replay) + mechanic B (symbol-whitelist expansion to
EURUSD/GBPUSD/USDCAD), per user decision 2026-06-30; A10 Kunigami
v2 WIRED 2026-06-30 (Φ4.2 Sentinel R1–R6 mini-sprint — Kunigami's
25,877 Φ4.1 warning Thoughts are now consumed by R5 via
`SentinelContext.kunigami_loss_streak_active`, audit-only in
Φ4/Φ4.1 replays and physically blocking in Φ5+).
**Version flips:** A2 Bachira / A3 Rin / A4 Chigiri / A5 Reo move
from "to-build" to `v1 implemented`. Evolution-ledger now has four
rows (the 2026-06-24 Isagi v1→v2 FAIL + three 2026-06-25 sketch
resolutions). v0.6 stands below.

v0.6 (2026-06-24) marked the **Φ4 v1 squad gate landing**: A6 Nagi
v1, A7 Barou v1, and A10 Kunigami v1 are now **implemented**, tested,
and have run end-to-end against the 2015–2025 EURUSD + USDCAD H4
squad gate. The gate FAILed at 0.98× Isagi-alone TQS — reported
honestly per user constraint, with a Diagnosis section in
`reviews/phi4_squad_v1.md` explaining each agent's contribution
(Nagi predicate-starved, Barou median-dilutes, Kunigami silent in the
regime). v0.5 introduced the §3.11 evolution-arc fields
(**Current version**, **Evolution arc**, **Defeat trigger**); v0.6
filled in the post-Φ4-v1 empirical state for A1/A6/A7/A10. v0.4
added per-agent **canon_role** (fixed identity), **info_tier_status**
(TBD pending Φ3 ΔInfo, F17 in `04-quant-foundations.md`),
**conflab/ inheritance** (specific lab-side primitives the agent
reuses), and **empirical prior** (one-line E0XX citation per agent,
from `audits/2026-06-24_E001-E007_audit.md` §4.2). The character-feel
ego column is unchanged. The two-method protocol from
`06-blue-lock-doctrine.md` §4.1 (`observe` / `intend`) applies to
every agent below; the per-agent specs continue to describe `intend`
triggers, with `observe` being the every-tick Thought emitter using
each agent's tag set. v0.3 added per-agent home / supporting
timeframes, the Φ3 MVP scope flag (yes for A1, A4, A10 only), and
the principled-form note on the ego column (numeric egos are
placeholders until F-information-ratio derivation in Φ4+).
Supersedes v0.1 (2026-06-23, deleted before pivot to the doctrine
in `06-blue-lock-doctrine.md`).

> "I am the protagonist of this story." — Yoichi Isagi

This doc instantiates the doctrine from `06-blue-lock-doctrine.md`
into a concrete cast of 10 specialist striker agents, one coach, one
validation harness, and three named opponents (the human discretionary
trader). Every striker maps to a Blue Lock character chosen for the
fit between the character's canonical weapon and the strategy
primitive we want isolated.

Reading order: `00-charter.md` → `06-blue-lock-doctrine.md` (most
critical) → this doc → `04-quant-foundations.md` for the math.

---

## 1. The squad — at a glance

Ten strikers, one coach, one club official, three named opponents.

| # | Player | Role | Weapon (canonical) | Strategy primitive | `agent_id` | Home TF | Supporting TFs | Ego | MVP Φ3? | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | **Yoichi Isagi** | Field general / striker | Metavision (sees the board's future state) | Liquidity + market-structure (IRL / ERL / FVG / OB) | `isagi_yoichi` | H1 | M15 entry, H4+D1 context | 0.60 | yes | **v1 canonical (Φ3 PASS).** Φ4: 856 trades. **Φ4.1: 0 trades** — slot-cannibalised by Bachira rebel-lift. v1→v2 arc attempted 2026-06-24, FAIL (TQS 0.317 → 0.240); v2 archived at `sim/agents/a01_isagi_v2.py`. See `reviews/isagi_v2_arc.md`. |
| A2 | **Meguru Bachira** | Wild striker | Monstrous dribble / non-linear creativity | Pattern geometry + baseline-zone rebel-lift (Φ4.1 v1 primitive) | `bachira_meguru` | H1 | M15 entry, H4 pattern scale | 0.85 | Φ4.1 v1 | **v1 implemented (Φ4.1 squad gate)** — **2840 trades** (76 % of squad trade count), +9.97 mean / **+14.21 median pips**, TQS 0.308, win 50.9 %; rebel-lift mechanic fired 46,584 times — Φ4.1 slot-allocation dominator |
| A3 | **Itoshi Rin** | Cold technician | Technical perfection | Fibonacci / harmonic + zone_d1_against precision-lift + Phase T-evolve **peer-yield-and-lift** (Rin v1.1 primitive, 2026-07-01) | `itoshi_rin` | H4 | D1 source-swing, H1 entry | 0.40 | Φ4.1 v1 | **v1.1 confirmed (Phase T-evolve, 2026-07-01 walk-forward-post-TU).** Post-Phase-S v1.0 regressed to 0 trades / 7 windows (crowded out by Isagi metavision). v1.1: yields to Isagi when peers align (`peer_agree>=1, peer_disagree==0`), lone-read-lifts +0.10 conviction otherwise. **Empirical result: 966 accepted trades, TQS 0.337, delta (rej-acc) = −0.146** (passes doctrine §4.1c acceptance test ≤ −0.05). Rin now higher accepted-TQS than Isagi (0.337 > 0.300). Canon: scores goals Isagi *can't*. |
| A4 | **Hyoma Chigiri** | Speedster | Pure breakaway speed | Range-break + ATR vol-expansion momentum | `chigiri_hyoma` | M15 | H1 confirmation, H4 trend bias | 0.80 | Φ4.1 v1 | **v1 implemented (Φ4.1 squad gate)** — 536 trades, +6.62 mean / −26.67 median pips, TQS 0.229, win 39.9 %; breakout-firing thoughts 3,615 — the only non-zone-family primitive in the squad |
| A5 | **Reo Mikage** | Chameleon | Adaptive copying | Regime-conditional dynamic copier (mimics best trailing-TQS agent) | `reo_mikage` | inherits | inherits | 0.30 | Φ4.1 v1 | **v1 implemented (Φ4.1 squad gate, structural Tier-2 falsifier)** — 0 trades by design; **28,469 mirror Thoughts emitted** — falsifier worked, confirming Reo as fuel for Nagi's confluence floor without claiming Tier-3 |
| A6 | **Seishiro Nagi** | Lazy genius | Perfect trap (ball stops dead) | Confluence-only multi-signal AND gate; lowest frequency | `nagi_seishiro` | H4 (Φ4 v1) | M15/H1/H4/D1 (canon) | 0.45 | Φ4.1 v1 | **v1 canonical (Φ4.1-validated).** Φ4: 0 trades / 0 confluence thoughts (predicate-starved). **Φ4.1: 94 trades** at mean **TQS 0.349 (HIGHEST per-agent TQS in 8-agent squad)**; 34,302 confluence-firing Thoughts → 645 proposals. v2 sketch RETIRED per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1. |
| A7 | **Shoei Barou** | King / lone wolf | Dominant solo finishing | Single-pair specialist; locks one symbol end-to-end | `barou_shoei` | H4 (locked pair) | pair-specific D1+H1 | 1.00 | Φ4 v1 | **v1 implemented (Φ4 squad gate)** — 1150 trades, +9.79 mean / −7.28 median pips, devour mechanic shipped (**0 lifts** in 11-yr run × 2 runs). **Φ4.1: 0 trades** — slot-cannibalised by Bachira rebel-lift; second kill-path for v1 confirmed. v2 REDESIGN-hybrid-A+B per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2 + 2026-06-30 amendment. |
| A8 | **Kenyu Yukimiya** | Smooth dribbler | Clean execution | Sub-bar entry-timing refiner (improves *other* agents' fills) | `yukimiya_kenyu` | M1–M5 sub-bar | inherits parent | 0.35 | Φ4+ | to-build (depends on A1+) |
| A9 | **Aoshi Tokimitsu** | Berserker | Overwhelming physicality (event mode) | Macro-event-only vol-breakout (FOMC / NFP / CPI) | `aoshi_tokimitsu` | M5 event-window | M15 follow-through, H1 fade-protection | 0.75 | Φ4+ | to-build |
| A10 | **Rensuke Kunigami** | Reformed power-shooter | Recovery / discipline | Anti-tilt risk auxiliary (post-loss recalibration) | `kunigami_rensuke` | H4 (Φ4 v1) | daily state (canon) | 0.00 | Φ4.2 v1 (v2-wired) | **v1 implemented + v2 wired 2026-06-30 (Φ4.2 Sentinel mini-sprint).** Φ4.1: **25,877 warning Thoughts emitted, 0 consumed** (R5 unwired). Φ4.2 wiring: `SentinelContext.kunigami_loss_streak_active` now polls `A10KunigamiV1.warning_active_at(as_of)` in `_drive_squad_replay`; audit-only in Φ4/Φ4.1 replays (sealed verdicts preserved), physically blocking in Φ5 harness via `sentinel_blocks=True`. Formal v3 revisit gated on ≥ 100 R5 activations across `{trending, chop}` regimes in Φ5 aggregator gate. |
| — | **Jinpachi Ego** | Coach (non-player) | Egoist doctrine | Allocator + Risk Conductor | `coach_ego` | n/a | n/a | n/a | n/a | architectural — see `03-architecture` |
| — | **Anri Teieri** | Club executive | Process / records | Validation harness + evidence ledger | `harness_anri` | n/a | n/a | n/a | n/a | architectural — see `reviews/` |
| — | **Michael Kaiser** | Opponent | Engineered single decisive shot | Human's high-conviction discretionary trades | `opponent_kaiser` | n/a | n/a | n/a | n/a | adversarial benchmark |
| — | **Yuya Loki** | Opponent | Observation + counter | Human's adaptive mid-week revisions | `opponent_loki` | n/a | n/a | n/a | n/a | adversarial benchmark |
| — | **Sae Itoshi (foil)** | Opponent | Cold pragmatic excellence | Synthetic baseline (buy-and-hold + zone_d1_against frozen) | `opponent_sae` | n/a | n/a | n/a | n/a | adversarial benchmark |

**Ego is now principled (Q3 resolution).** The numeric ego values in
the table are *placeholders* set by character feel for v0; under Φ4+
they will be re-derived as the information ratio of the agent's edge
versus its peers — if an agent's weapon is one no other agent shares,
it carries high ego; if its weapon is shared, ego is dampened. The
character ego values stay as priors; the data updates them. See
`06-blue-lock-doctrine.md` §3.1.b for the formal definition.

Two notes on the cast.

First, the **ego column**. Each ego value is justified two-line:
- A1 Isagi `0.60` — protagonist, hungry but team-aware; refuses to defer only when his metavision sees the goal.
- A2 Bachira `0.85` — monster mode; "I'll dribble through anyone." Will fire often, sometimes wrongly.
- A3 Rin `0.40` — cold; refuses to take a shot unless the geometry is perfect. Low-ego in *frequency*, lethal in *precision*.
- A4 Chigiri `0.80` — the speed-merchant once he commits; almost never loses a foot-race when he's already moving.
- A5 Reo `0.30` — by design copies others; ego defers to whoever is winning this week.
- A6 Nagi `0.45` — lazy; hates moving unless the ball is already on his foot. Highest conviction floor of the squad.
- A7 Barou `1.00` — the King. Refuses to participate in chemical reactions. Maximum ego by canon definition.
- A8 Yukimiya `0.35` — support / micro-edge. Doesn't *take* shots; refines them.
- A9 Aoshi `0.75` — explodes only inside a 6-hour event window; insanely committed within it.
- A10 Kunigami `0.00` — a control agent, not a forecaster. No shooting drive at all; pure dampening role.

Second, **A7 Barou is intentionally outside the fusion layer.** He is the experimental control agent that tests "what if we just let one specialised striker run end-to-end without participating in confluence?" His PnL is the apples-to-apples baseline that any fusion mechanism must beat.

### §1.0 v1 checkpoint status (per doctrine §3.11.5, added 2026-07-01)

The doctrine's operational v1 definition (§3.11.5) requires: (1)
per-agent positive results, (2) positive-sum chemistry contribution,
(3) non-cannibalising slot behaviour, (4) F21 workspace participation,
(5) F19 owned lot cognition, (6) F20 owned risk cognition. This
table replaces the ambiguous v1/v2 markers scattered in the §1 cast
table's `Status` column with a single per-agent checkpoint state.

| Agent | Version status (§3.11.5) | Playstyle (§4.1a) | Blockers before G7 |
|---|---|---|---|
| **A1 Isagi** | `v1-checkpoint (Φ3 PASS)` — the only agent past the v1 gate to date. v1→v2 arc FAILED 2026-06-24; v2 archived. | Conservative-metavision | F19/F20/F21 defaults still need agent-side implementation (currently harness-default fixed-lot) |
| **A2 Bachira** | `pre-v1 (mechanic-iter-1 in flight)` — v1 mechanic pending peer-silence gate on rebel-lift; §3.11.5 criterion #3 (non-cannibalising slot behaviour) currently FAILS (46,584 rebel-lift fires in Φ4.1 forced Isagi + Barou to 0 trades) | Rebel-tight | Peer-silence gate + F19/F20/F21 |
| **A3 Rin** | `pre-v1 (mechanic-iter-1 in flight)` — v1 mechanic pending regime-gate to `trending` + peer-disagreement requirement | Analytical-precision | Regime + peer-disagreement gate + F19/F20/F21 |
| **A4 Chigiri** | `pre-v1 (mechanic-iter-1 in flight)` — v1 mechanic pending three conjunctive guards (M15×H1×H4 ADX rising, top-decile σ, 20-bar high/low) | Speed-momentum | Three conjunctive guards + F19/F20/F21 |
| **A5 Reo** | `pre-v1 (mechanic-iter-1 in flight)` — v1 mechanic 1 (HRP mixture) pending; mechanic 2 (Φ5-second-position) deferred to post-G7 | Copier-HRP | HRP mixture + F19/F20/F21 |
| **A6 Nagi** | `pre-v1 (canonical-mechanic-validated)` — highest per-agent TQS in Φ4.1 (0.349), but §3.11.5 criterion #4 (workspace participation) requires F21 read implementation before G7 | Confluence-only | F19/F20/F21 (mechanic itself validated) |
| **A7 Barou** | `pre-v1 (mechanic-iter-1 in flight)` — v1 mechanic pending hybrid A + B (closed-loss replay + symbol whitelist expansion) | Solo-king | Hybrid A+B + F19/F20/F21 |
| **A8 Yukimiya** | `not-yet-implemented` | (canon: friction-quartile-filtered execution refinement) | full v1 build + F19/F20/F21 |
| **A9 Aoshi** | `not-yet-implemented` | (canon: calendar-aware vol events) | full v1 build + F19/F20/F21 |
| **A10 Kunigami** | `pre-v1 (canonical-mechanic-validated)` — Sentinel R5-wiring via `warning_active_at` is a v1 primitive (not v2 per §3.11.5 reclassification); mechanic itself validated | Defensive | F19/F20/F21 |

**Squad-level v1-checkpoint gate (G7).** All eight implemented agents
must clear §3.11.5 as a squad, not individually — no agent moves to
v2 candidacy while the squad's chemistry is broken. The formal G7
pre-registration lives at `experiments/G7_v1_checkpoint_gate/PROTOCOL.md`.

**Rows in the §1 table above marked with "v1 implemented"** refer to
the *pre-2026-07-01 labelling convention* and should be read as
`pre-v1 (mechanic-iter-N in flight)` under §3.11.5. The §1 table is
retained un-edited for historical continuity; §1.0 is the authoritative
version-status source going forward.

### §1.1 MVP Φ4 roster (four agents — v1 fusion experiment)

The **10-agent canon** in §1 above is unchanged — infrastructure
implements all ten strikers. The **first Φ4 fusion sweep** (v1) ships a
deliberately small roster to limit degrees of freedom while the replay
kernel and ΔInfo harness mature (`09-experiment-architecture.md` §2).

| Agent | `agent_id` | MVP role |
|---|---|---|
| **A1 Isagi** | `isagi_yoichi` | E004 baseline wrapper; must clear C1 alone before squad fusion counts |
| **A6 Nagi** | `nagi_seishiro` | Confluence-only chemical-reaction layer; lowest frequency, highest conviction floor |
| **A7 Barou** | `barou_shoei` | End-to-end lone-wolf control (USDCAD-locked in spec §3.7); does not participate in fusion |
| **A10 Kunigami** | `kunigami_rensuke` | Anti-tilt risk auxiliary; post-loss dampening across the squad |

**Not in Φ4 v1 (benched, not cut):** A2 Bachira, A3 Rin, A4 Chigiri,
A5 Reo, A8 Yukimiya, A9 Aoshi. These agents are built and measured under
G5 (10 implemented, ≥ 6 with TQS > 0 in ≥ 1 regime) but excluded from
the first fusion config until Φ4 v2 ablation sweeps.

Ablation is config-only: drop or swap agents via `sim/config/roster.yaml`
without code changes (`09-experiment-architecture.md` §1.10).

---

## 2. Diversity matrix

The matrix that justifies the cast. Each cell answers: *under this regime, does the agent agree with the baseline directional read?* `++` strong agree, `+` weak agree, `o` neutral / abstains, `−` weak disagree, `−−` strong disagree.

| Agent | Trend (D1 ADX > 25) | Range (ADX < 20, low σ) | Vol-expansion event (post-FOMC) | Mean-revert range (zone touch) |
|---|---|---|---|---|
| A1 Isagi (zone v1) | `−` (with-trend kills it) | `+` | `−−` | `++` |
| A2 Bachira (pattern) | `+` (continuation patterns) | `+` (range patterns) | `++` (breakouts confirm) | `o` |
| A3 Rin (Fib/harmonic) | `++` (structural retracements pay) | `+` (precise S/R) | `o` | `+` |
| A4 Chigiri (breakout) | `++` | `−−` (whipsaws) | `++` | `−` |
| A5 Reo (adapter) | follows leader | follows leader | follows leader | follows leader |
| A6 Nagi (confluence) | conditional on confluence | conditional | `++` (post-event confluence is strongest) | conditional |
| A7 Barou (single-pair) | depends on his symbol's regime | same | same | same |
| A8 Yukimiya (timing) | meta — refines whoever | meta | meta | meta |
| A9 Aoshi (event) | `o` | `o` | `++` | `o` |
| A10 Kunigami (anti-tilt) | regime-neutral (drawdown-state-driven) | regime-neutral | regime-neutral | regime-neutral |

**Sanity check.** Under "vol-expansion event" (FOMC / NFP), A1 says `−−`, A4 says `++`, A2 says `++`, A6 says `++`, A9 says `++`. The roster *disagrees with itself* in a regime where the live agent failed last week. That is the point. The week of 2026-06-15 would have had A4 + A2 + A6 + A9 each emitting bullish-USD-shorts coordinates around the FOMC H4 close, and A1 ignored or overruled.

Under "mean-revert range" (USDCAD pre-Jun-15), A1 says `++`, A4 says `−`, A6 conditional, A2 `o`. The roster *agrees with itself* on a true mean-revert regime — the regime A1 was designed for. A1 dominates the allocator weight there.

Diversity is real, not cosmetic.

---

## 3. Per-agent specifications

Eight fields per agent, same template throughout. The fields define what the code in `agent/multi/strikers/<agent_id>.py` will need.

### 3.1 A1 — Yoichi Isagi (`isagi_yoichi`)

| Field | Value |
|---|---|
| **Thesis** | Liquidity targets price; price moves to where institutional orders need filling. The agent reads the field's future state — IRL pools, ERL sweeps, FVGs, OBs — and predicts where price *must* travel for the chart to make sense |
| **Weapon (canonical)** | Metavision |
| **Home TF / Supporting TFs** | H1 home; M15 entry, H4+D1 context |
| **Regime fit** | Mean-revert range and ranging (high); trend (mixed — depends on whether HTF supports the structural read); vol-expansion event (low until post-event re-pricing) |
| **Signal trigger** | H1 close inside an unmitigated zone or just past a swept liquidity pool, with HTF (H4/D1) bias supportive of return-to-mean; Isagi v1 keeps the legacy H4-close `zone_d1_against` detector as its primitive seed |
| **Coordinate** | `price_band` = zone or 50%-equilibrium of the swept range; `time_window` = next 6–12 H1 bars; `vol_band` = (0.5×, 2.0×) of 80-bar median σ; `regime_predicate` = D1 trend AGAINST the trade direction OR ranging |
| **Sizing rule** | Conviction × 0.5–2 % equity (sandbox 5 %), capped at ⅓-Kelly of trailing 90-trade realised distribution |
| **Exit rule** | SL at zone-edge ± 0.25× ATR; ladder = 0.5R partial / 1.0R BE / 1.5R structural |
| **Anti-thesis** | A4 Chigiri — same H1 close interpreted as breakout-momentum continuation, not reversion |
| **Status** | **v1 canonical (Φ3 PASS).** Wraps existing `agent/alphas/concepts/zone_alpha.py` as Isagi v1 (zone-only sub-detector on the legacy H4 cadence). Φ3 gate `PASS` (median OOS-window mean pips/trade = +11.04 vs Sae +11.34, Δ −2.7 %, inside ±5 % band). **Φ4:** 856 trades, +6.28 mean pips. **Φ4.1:** **0 trades** — slot-cannibalised by Bachira's `+0.10` rebel-lift on the same baseline-zone primitive (see `reviews/phi41_squad_v1.md` engine telemetry + addendum §1). **v1→v2 arc attempted 2026-06-24:** FAIL — v2 added a liquidity-sweep weapon; sweep proposals cannibalised zone slots in the single-position queue (v2 zone trades 311 vs v1 856; median OOS TQS 0.317 → 0.240); v2 archived at `sim/agents/a01_isagi_v2.py` per §3.11.2 step 3, see `reviews/isagi_v2_arc.md`. v3 may revisit metavision via sweep-as-confluence-filter, multi-position simulator, FVG/OB primitives, or H1 cadence — deferred. |
| **MVP Φ3?** | yes |
| **Canon role (fixed)** | Field-general striker reading the field's future state via metavision |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement (F17 in `04-quant-foundations.md`) |
| **Current version** | **v1** — landed at commit `12c2bf4` (Φ3 wrapper of production `zone_d1_against`); Φ3 gate `PASS` per `reviews/phi3_gate_isagi_v1.md`. v2 attempted 2026-06-24 and archived (FAIL); v1 remains canonical. |
| **Evolution arc** | v1 → v2 attempted 2026-06-24 (FAIL — see `reviews/isagi_v2_arc.md`); **v1 remains canonical, v2 archived on disk per §3.11.2 step 3**. Future v3 reserved for a different evolution structure (sweep-as-confluence-filter, multi-position simulator, FVG/OB primitives, or H1 cadence). The original v2 metavision-sharpens hypothesis (`06-blue-lock-doctrine.md` §3.11.3) is retired in its single-position-queue form; the binding constraint exposed at v1→v2 was the queue itself, not the primitive vocabulary. |
| **Defeat trigger** | Original (queue-collision class): a vN+1 reintroducing the sweep / FVG / OB weapon must do so without cannibalising v1 zone slots. Active forward-looking trigger: TQS regression in a specific regime bucket (vol-expansion or trending) on the locked walk-forward panel; cite trade-ID range in `reviews/isagi_yoichi_v1_defeat.md` when it lands. |
| **Home TF (fixed)** | H1 |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance (v1)** | `agent/alphas/concepts/zone_alpha.py` (production, untouched). Empirical prior: **E004** walk-forward 7/7 OOS, median +11.34 pips/trade (audit §2.4). Baseline for the C1 promotion gate. |
| **conflab/ inheritance (v2)** | `conflab/detectors_liquidity.py` (`equal_highs_pool`, `equal_lows_pool`, `liquidity_sweep_high`, `liquidity_sweep_low`), `conflab/detectors_zones.py` (lab-native zone re-impl as cross-check). Empirical prior: **E006** exploratory — H1 `equal_highs_pool` is the strongest context amplifier (+0.10 to +0.46 ATR lift across 65 M15 setups; audit §2.6, §4.3). |

### 3.2 A2 — Meguru Bachira (`bachira_meguru`)

| Field | Value |
|---|---|
| **Thesis** | Classical chart-pattern geometry encodes failed re-tests; the neckline / pattern-failure level is high-probability when nested inside a higher-TF structural lid or floor |
| **Weapon (canonical)** | Monstrous dribble — non-linear creativity |
| **Home TF / Supporting TFs** | H1 home; M15 entry, H4 pattern scale |
| **Regime fit** | Vol-expansion (high — patterns confirm under volatility); range (moderate — patterns also form in compression); trend (low — patterns get steamrolled) |
| **Signal trigger** | H1 pattern detector fires (H&S, double top/bottom, flag) AND price closes through neckline AND HTF lid/floor within 2× ATR_H4 |
| **Coordinate** | `price_band` = neckline ± 0.5× ATR_H1; `time_window` = next 4–8 H1 bars; `vol_band` = (0.8×, 3.0×) median σ; `regime_predicate` = HTF lid/floor proximity |
| **Sizing rule** | Conviction = pattern-strength × HTF-alignment; size = conviction × 1 % equity |
| **Exit rule** | SL = pattern invalidation (right shoulder / opposite peak); ladder = T1 measured-move 50 % / T2 100 % / T3 next D1 liquidity zone |
| **Anti-thesis** | A1 Isagi — Isagi often sees the H&S right shoulder as a fade-able zone touch; Bachira sees it as the pattern's confirmation |
| **Status** | **v1 implemented (Φ4.1 squad gate)** — **2,840 trades** (76 % of squad trade count, the Φ4.1 slot-allocation dominator), +9.97 mean / **+14.21 median pips**, TQS 0.308, win 50.9 %. v1 primitive: baseline-zone (no D1 gate) on EURUSD + GBPUSD + USDCAD H4 with a `+0.10` rebel-lift to 0.75 conviction when the recent-opposite-swing trigger fires (lift fired 46,584 times in 11 yrs). Crowded out Isagi v1 + Barou v1 on every signal-tick where Bachira proposed, producing the Φ4.1 FAIL diagnosis "structural crowding-out" (`reviews/phi41_squad_v1_addendum.md` §1). v2 sketch **REFINE-to-peer-silence** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §1. |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Wild striker; monstrous-dribble creativity; pattern geometry as non-linear improvisation |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 implemented** — Φ4.1 v1 wraps a baseline-zone primitive with a recent-opposite-swing rebel-lift (`sim/agents/a02_bachira.py`); benchmark of Φ4.1 squad-gate FAIL. v2 sketch **REFINE-to-peer-silence** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §1 (narrow rebel-lift to peer-silence OR peer-disagreement gated trigger; ordering depends on Φ5 HRP verdict). |
| **Evolution arc** | v1 → v2 releasing the monster (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* standalone pattern detectors do not fire (E001/E006 prior). *v2 hypothesis:* patterns trigger only when **no other striker has a clean read** on the same symbol; ledger read for *peer silence* becomes part of the trigger |
| **Defeat trigger** | Expected: v1's pattern-only firing rate produces TQS ≤ 0 in ≥ 2 regime buckets (matching the E001/E006 standalone-vocabulary kill prior, audit §2.1, §2.6) |
| **Home TF (fixed)** | H1 |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance** | `conflab/detectors_chartpatterns.py` (H&S, double tops/bottoms, triples, triangles, wedges, flags, rectangles). Empirical prior: **E001** killed 6/7 ICT standalone concepts and **E006** killed candlestick families everywhere they were powered (audit §2.1, §2.6). Bachira's edge cannot come from a standalone pattern; it must come from pattern × HTF-lid/floor combination — i.e. confluence is mandatory, not optional. |

### 3.3 A3 — Itoshi Rin (`itoshi_rin`)

| Field | Value |
|---|---|
| **Thesis** | Markets respect mathematical ratios — Fibonacci retracements (38.2 / 50 / 61.8 / 78.6 %) and harmonic patterns (Gartley, Bat, Butterfly) — at multi-timeframe alignment points |
| **Weapon (canonical)** | Technical perfection |
| **Home TF / Supporting TFs** | H4 home; D1 source-swing, H1 entry |
| **Regime fit** | Trend (high — retracements pay); range (moderate — Fib levels act as S/R); vol-expansion (neutral); mean-revert (moderate) |
| **Signal trigger** | H4 close at a multi-TF Fib confluence (e.g., D1 50 % retrace + H4 61.8 % retrace within 5 pips) AND the swing it retraces is structurally clean (single thrust, no overlapping pivots) |
| **Coordinate** | `price_band` = Fib zone ± 5 pips; `time_window` = next 4–10 H4 bars; `vol_band` = (0.6×, 1.8×) median σ; `regime_predicate` = clean swing structure (no whipsaw in source thrust) |
| **Sizing rule** | Conviction = Fib-confluence count × structural cleanliness; size = conviction × 1 % equity |
| **Exit rule** | SL at next Fib level past entry + 0.25× ATR; ladder = 1R / 1.618R extension / 2.618R extension |
| **Anti-thesis** | A6 Nagi — Rin shoots when geometry is clean even without confluence; Nagi waits for confluence even when geometry is clean |
| **Status** | **v1 implemented (Φ4.1 squad gate)** — 244 trades, +9.95 mean / **−28.26 median pips**, TQS 0.277, win 35.7 %. Mean-positive / median-negative — fat-right-tail with concentrated losses. v1 primitive: zone_d1_against on EURUSD with a `+0.15` precision-lift to 0.80 conviction when R:R ≥ 2.5 AND stop-distance ≥ 20 pips (lift fired 3,094 times in 11 yrs). Shares all `zone_d1_against` tags with Isagi by construction — peer fuel for Nagi's confluence floor on EURUSD (3,094 precision lifts contributed to the 34,302 Nagi confluence-firing thoughts). v2 sketch **REFINE-regime+peer-disagreement** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2. |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Cold technician; technical perfection via mathematical ratios |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 implemented** — Φ4.1 v1 wraps zone_d1_against with R:R + stop-distance precision filter (`sim/agents/a03_rin.py`). v2 sketch **REFINE-regime+peer-disagreement** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2 (regime-gate to `trending` live-class; retain v1 R:R + stop filter; add peer-disagreement requirement). |
| **Evolution arc** | v1 → v2 cold clinical reset (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* Fib / harmonic tags fire too often in chop (E006 fib cells were exploratory-only, not confirmed on 2022–2024 split or GBPUSD; audit §2.6). *v2 hypothesis:* gate firing on the F18 regime classifier — emit only when regime ∈ {trending, vol_spike}, never in chop |
| **Defeat trigger** | Expected: v1 TQS regression in `range` / chop regime bucket; single-Fib tag false-positive rate ≥ 60 % during chop windows |
| **Home TF (fixed)** | H4 |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance** | `conflab/detectors_fib.py` (retracement, OTE, extensions), `conflab/detectors_trendlines.py` (trendline + channel touch, break+retest, parallel-channel boundary). Empirical prior: **E006** Stage-1 found `fib_50_tag` and `fib_618_tag` alive on the EURUSD screen (effect +0.12 to +0.15 ATR) but **not confirmed** on the 2022–2024 confirm split and **not replicated** on GBPUSD (audit §2.6). Rin's edge is conditional on multi-TF Fib confluence, not standalone — the data says single-Fib tags do not survive OOS. |

### 3.4 A4 — Hyoma Chigiri (`chigiri_hyoma`)

| Field | Value |
|---|---|
| **Thesis** | Range compressions resolve with momentum; first M15 close beyond an N-bar high/low with rising realised vol leaks predictable directional PnL for the next 4–12 M15 bars |
| **Weapon (canonical)** | Speed |
| **Home TF / Supporting TFs** | M15 home; H1 confirmation, H4 trend bias |
| **Regime fit** | Trend and vol-expansion (very high); range (very low — gets whipsawed); mean-revert (very low) |
| **Signal trigger** | M15 close beyond 20-bar high/low AND realised σ over trailing 10 M15 bars > 1.2× the 80-bar median, with H1 ADX rising |
| **Coordinate** | `price_band` = (broken_level, broken_level ± 1× ATR_M15); `time_window` = next 6–12 M15 bars; `vol_band` = (1.2× median, ∞); `regime_predicate` = ADX_H1 rising |
| **Sizing rule** | Vol-targeted (lot ∝ 1/σ_M15); conviction = z-score of breakout magnitude vs prior range |
| **Exit rule** | SL at broken level − 0.25× ATR_M15; ladder = 1R partial, then trail at most-recent swing |
| **Anti-thesis** | A1 Isagi — same close interpreted as zone touch to fade |
| **Status** | **v1 implemented (Φ4.1 squad gate)** — 536 trades, +6.62 mean / **−26.67 median pips**, TQS 0.229, win 39.9 %. Mean-positive / median-negative; the only non-zone-family primitive in the squad (range-break + ATR vol-expansion). Breakout-firing thoughts: 3,615. Chigiri's tags do **not** inherit `zone_d1_against` from Isagi/Rin — he reaches Nagi's confluence floor only via Reo's mirror mediation (cleanest test of the tag-overlap pathway). v2 sketch **REFINE-multi-TF-ADX+ATR-percentile** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §3. |
| **MVP Φ3?** | yes |
| **Canon role (fixed)** | Speedster; pure breakaway speed; commit-and-run once the range resolves |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 implemented** — Φ4.1 v1 wraps `conflab/detectors_impulse_return.py` for the breakout-on-continuation primitive (`sim/agents/a04_chigiri.py`). v2 sketch **REFINE-multi-TF-ADX+ATR-percentile** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §3 (three conjunctive guards: M15×H1×H4 ADX rising, top-decile σ_M15, 20-bar high/low). |
| **Evolution arc** | v1 → v2 learning to run again (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* breakouts on impulse-origin retest are dead (E007 0/12 cells alive, audit §2.7). *v2 hypothesis:* take only the **continuation** of confirmed breakouts, never the retest; speed deployed forward on confirmation, never backward on a retrace |
| **Defeat trigger** | Expected: v1 retest-layer firing produces TQS ≤ 0 (already predicted by E007 negative prior); first false-start loss in the live ledger triggers v2 reframing |
| **Home TF (fixed)** | M15 |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance** | `conflab/detectors_impulse_return.py` (impulse-leg detector with K-bar net-move + ATR floor + intra-leg retrace ceiling) — the primitive that recognises a "strong leg" Chigiri rides. Empirical prior: **E007** is a *negative* prior at the retest layer — 0/12 cells alive on impulse-origin retest at Stage 1, BH-FDR α=0.05 (audit §2.7). **Chigiri's edge must therefore live in the *continuation* of the impulse, not in the retest of the origin zone.** Up-impulse cells were +4 to +14 pips on EURUSD 2015–2021 vs negative H4 down-impulse cells — a symmetric-long-short warning that Chigiri must respect at the spec level. |

### 3.5 A5 — Reo Mikage (`reo_mikage`)

| Field | Value |
|---|---|
| **Thesis** | The ensemble's best-performing agent of the last K weeks contains transferable bias; explicitly mirroring it lifts the floor of overall ensemble performance during stable regimes |
| **Weapon (canonical)** | Chameleon adaptation |
| **Home TF / Supporting TFs** | inherits — Reo runs on whichever TF the current leader runs on |
| **Regime fit** | All — Reo doesn't have a regime; he has a leader |
| **Signal trigger** | Identifies the trailing-K-week TQS leader; emits a coordinate co-located with the leader's most recent coordinate, with reduced expected_strength |
| **Coordinate** | Inherits from the leader minus a "humility margin" (price band ±20 % wider, time window 25 % shorter, expected_strength × 0.7) |
| **Sizing rule** | 0.7 × leader's size (always smaller; this is a follower) |
| **Exit rule** | Inherits leader's ladder; SL = leader's SL ± 0.25× ATR (slightly tighter to fail first) |
| **Anti-thesis** | A7 Barou — Reo defines himself by deference to peers; Barou refuses to defer to anyone |
| **Status** | **v1 implemented (Φ4.1 squad gate, structural Tier-2 falsifier)** — **0 trades by design**; **28,469 mirror Thoughts emitted** in the Φ4.1 run. v1 falsifier worked: Reo's mirror count is the lower bound on Nagi-qualifying peer lifts; Nagi's 34,302 confluence-firing thoughts confirms the mirror mediation pathway. By design Reo emits Thoughts but never `intend()` returns — the no-trade contract is the test. v2 sketch **ADVANCE-coupled-to-Φ5-multi-position** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4. |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Chameleon; adaptive copying; ego defers to whoever is winning this week |
| **Information tier status** | **Structural Tier 2 (by design).** Reo's weapon *is* reading the leader's thoughts; he cannot exist as Tier-3. ΔInfo (F17) is still measured to verify the design — if informed Reo does not beat isolated Reo on F17, Reo is cut from the roster (not relegated). |
| **Current version** | **v1 implemented** — Φ4.1 v1 ships the mirror-Thought emitter without `intend()` (`sim/agents/a05_reo.py`); structural Tier-2 falsifier validated by the 28,469 mirror-Thought count. v2 sketch **ADVANCE-coupled-to-Φ5-multi-position** per `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4 — stacked mechanic 1 (HRP-weighted mixture of top-K ≥ 2 trailing-TQS agents) + mechanic 2 (second-position proposer under Φ5 Arm 4 / K = 2; mechanic 2 gated on Arm 4 landing). |
| **Evolution arc** | v1 → v2 chemistry not mimicry (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* mimicking a single trailing leader (Isagi) reproduces Isagi's edge with extra cost — Reo adds friction without marginal ΔInfo. *v2 hypothesis:* copy a weighted HRP mixture of the top-K trailing-TQS agents with K ≥ 2 enforced architecturally |
| **Defeat trigger** | Expected: v1 F17 ΔInfo ≤ 0 (he reproduces the leader rather than adding signal); Reo is cut from the roster (per the structural Tier-2 design) unless v2 lands and clears the threshold |
| **Home TF (fixed)** | inherits (whichever TF the current trailing-K-week TQS leader runs on) |
| **Symbols (fixed)** | inherits |
| **conflab/ inheritance** | No direct conflab primitive — Reo's weapon is the Thought Ledger itself (he reads other agents' Thoughts and emits a coordinate co-located with the leader's). No empirical prior from E001–E007 applies. |

### 3.6 A6 — Seishiro Nagi (`nagi_seishiro`)

| Field | Value |
|---|---|
| **Thesis** | The vast majority of "setups" are noise; only multi-signal confluence is worth firing on. Frequency × accuracy curve is concave — fewer, higher-quality shots dominate |
| **Weapon (canonical)** | Perfect trap (ball stops dead) |
| **Home TF / Supporting TFs** | multi-TF native — operates across M15/H1/H4/D1 simultaneously, fires only when confluence spans them all |
| **Regime fit** | Vol-expansion post-event (very high — confluence usually peaks here); all others (low — Nagi simply abstains) |
| **Signal trigger** | ≥ 3 other strikers' coordinates overlap on the same symbol (chemical reaction event) AND aggregate independent-OR conviction (F11) ≥ 0.85 |
| **Coordinate** | Lazy — emits no proactive coordinates; only responds to others'. Fires once inside the chemical-reaction box |
| **Sizing rule** | Highest conviction floor → largest single-trade size in the squad; capped at 1.5 % equity |
| **Exit rule** | SL at chemical-reaction's tightest agent SL; ladder = 1.5R / 2.5R / 4R (asymmetric — Nagi only takes high-RR shots) |
| **Anti-thesis** | A2 Bachira — Bachira shoots from anywhere, Nagi shoots only from the perfect spot |
| **Status** | **v1 canonical (Φ4.1-validated).** Φ4 (4-agent MVP, EURUSD + USDCAD): 0 confluence-firing thoughts, 0 trades (the 2-distinct-peer floor was never met because MVP had only 2 tradable strikers — predicate-starved, not predicate-broken). **Φ4.1 (8-agent expanded, EURUSD + GBPUSD + USDCAD): 34,302 confluence-firing thoughts → 645 proposals → 94 trades** at mean +10.28 pips / −20.04 median pips, **mean TQS 0.349 (HIGHEST per-agent TQS in the 8-agent squad)**, win 42.6 %. Predicate-starvation diagnosis confirmed and fixed. See `reviews/phi4_squad_v1.md` Diagnosis #1 + `reviews/phi41_squad_v1.md`. |
| **MVP Φ3?** | Φ4 v1 (shipped) |
| **Canon role (fixed)** | Lazy genius; perfect trap; lowest-frequency, highest-RR; fires only on multi-signal confluence |
| **Information tier status** | **Structural Tier 2 (by design).** Nagi is the canonical chemical-reaction agent — his trigger is overlap of other agents' coordinates and resonance of their Thoughts. Cannot operate as Tier-3. F17 still measured to verify the design. v1 F17 ΔInfo = +0.000 [underpowered] — uninformative until enough Tier-2 source signal exists for Nagi to fire on. |
| **Current version** | **v1 implemented** — code: `sim/agents/a06_nagi.py`; tests: `sim/tests/test_a06_nagi_wrap.py` (8 tests, all passing). Predicate: ≥ 2 OTHER strikers' Thoughts at tick T-1 with conviction > 0.7, ≥ 2 shared tags, overlapping coordinate price bands, matching direction. F11 lift via 1 − ∏(1 − cᵢ). Home TF H4 (Φ4 v1) per `09-experiment-architecture.md` §2; the multi-TF canon home is a Φ5+ wiring. Live-capital allocation still blocked until E010 confirms the H1 `equal_highs_pool` × M15 setup exploratory finding. |
| **Evolution arc** | **v1 canonical (Φ4.1-validated); v2 sketch retired** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1. Φ4.1 telemetry showed v1's 2-distinct-peer floor is correct as-shipped: with peer fuel Nagi fired 34,302 confluence-firing Thoughts at mean TQS 0.349 (highest per-agent TQS in the 8-agent squad). Relaxing the floor would make Nagi less canonical, not more. Future v2 reserved for a regression-class defeat (see Defeat trigger). |
| **Defeat trigger** | Nagi's per-OOS-window mean TQS regresses below the median of all other proposing strikers in ≥ 2 of 3 regime buckets (trend / range / vol-expansion event) across ≥ 4 of 7 rolling OOS windows on the locked walk-forward panel. The trigger is forward-looking; not currently active (Nagi v1 leads the squad on TQS at Φ4.1). When tripped, cite trade-ID range in `reviews/nagi_seishiro_v1_defeat.md`. |
| **Home TF (fixed)** | multi-TF native (M15 / H1 / H4 / D1 simultaneously) |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance** | `conflab/stage2.py` (context × setup pair-screening with displacement null and hour-restricted re-draws — the methodological template for Nagi's confluence layer). Empirical prior: **E006 exploratory** Stage-2 (audit §2.6, §4.3) found H1 `equal_highs_pool` × M15 setups lift +0.10 to +0.46 ATR (selection term). **This is the canonical chemical-reaction event.** Nagi's deployment-grade confluence layer waits for **E010** (pre-registered Stage-2b) to confirm the exploratory finding before live capital is allocated. |

### 3.7 A7 — Shoei Barou (`barou_shoei`)

| Field | Value |
|---|---|
| **Thesis** | A specialist focused on a single instrument develops deeper symbol-specific edge than a generalist trading 5+ pairs. End-to-end ownership beats fusion when the agent's thesis is regime-stable |
| **Weapon (canonical)** | Lone-wolf King |
| **Home TF / Supporting TFs** | H4 home on the locked pair; pair-specific D1+H1 context |
| **Regime fit** | Whatever regime suits Barou's chosen symbol; he doesn't switch to other symbols |
| **Signal trigger** | Symbol-specific. Default: USDCAD-locked H4 trend continuation (the regime where Isagi's `zone_d1_against` historically struggled — Barou is the specialist who would have made USDCAD work) |
| **Coordinate** | Emits coordinates only on the locked symbol; ignores all other instruments |
| **Sizing rule** | Independent of the rest of the ensemble — operates outside the fusion layer |
| **Exit rule** | Symbol-specific; for USDCAD: SL beyond the H4 swing structure; ladder = 1R / 1.5R / 2.5R |
| **Anti-thesis** | The entire ensemble — Barou's existence asks the question "did fusion add value over a single specialist?" |
| **Status** | **v1 implemented (Φ4 + Φ4.1 squad gates).** **Φ4** (4-agent MVP, EURUSD + USDCAD): 1,150 trades on USDCAD H4 2015–2025, +9.79 mean / −7.28 median pips, 49.8 % win, **0 devour lifts** — Isagi silent or directionally aligned on every USDCAD signal tick (E005 inverse-asymmetry confirmed; structural rarity of disagreement is mechanic-A's kill-path). **Φ4.1** (8-agent expanded): **0 trades, 0 devour lifts** — slot-cannibalised by Bachira's `+0.10` rebel-lift on every USDCAD signal tick (second independent kill-path: mechanic-A's pre-condition of Barou actually proposing is missing on the expanded roster). See `reviews/phi4_squad_v1.md` Diagnosis #2 + `reviews/phi41_squad_v1.md` engine telemetry. v2 REDESIGN-hybrid-A+B per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2 + 2026-06-30 amendment. |
| **MVP Φ3?** | Φ4 v1 (shipped) |
| **Canon role (fixed)** | King / lone wolf; dominant solo finishing; refuses to participate in chemical reactions |
| **Information tier status** | **Structural Tier 2 by canon revision (devour mechanic).** Barou's devour lift reads Isagi's prior-tick high-conviction thoughts to detect directional disagreement; the original v0.1 "Tier-3 by design" framing referenced the *default* state when Isagi is silent. With devour wired, Barou is Tier-2 with isolation as the experimental control. v1 F17 ΔInfo measured: +0.000 [underpowered] — devour fired 0 times so isolation made no measurable difference. |
| **Current version** | **v1 implemented** — code: `sim/agents/a07_barou.py`; tests: `sim/tests/test_a07_barou_wrap.py` (6 tests, all passing). Wraps production `agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` with `htf_align=None` and `target_rr=1.5` (baseline zone, no D1 gate). USDCAD-only; abstains on EURUSD/GBPUSD via observation-only Thoughts. Devour mechanic: +0.10 conviction lift (cap 1.0) when Isagi has prior-tick thought on USDCAD at conviction ≥ 0.7 with opposite direction. |
| **Evolution arc** | **v1 → v2 devour replays Isagi's losses (Tier-1 asynchronous, mechanic A) + symbol-whitelist expansion to EURUSD/GBPUSD/USDCAD (mechanic B). HYBRID A+B** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2 + 2026-06-30 amendment. *Defeat (Φ4 + Φ4.1):* live-ledger devour fired 0 times in 11 yrs × 2 runs (mechanic dead); Φ4.1 Barou opened 0 trades (slot-cannibalised by Bachira rebel-lift). *v2 hypothesis:* **(A)** devour reads Isagi's **closed losing trades** from the public ledger (Tier-1 post-fact); when an Isagi loss lands in Barou's coordinate space (USDCAD, last 24 H4 bars, within 1 ATR of a baseline-zone touch), Barou's NEXT-bar proposal conviction gets `+0.10` (cap 1.0). **(B)** Symbol whitelist `("USDCAD",)` → `("USDCAD", "EURUSD", "GBPUSD")` running baseline-zone (no D1 gate); USDCAD remains canonical specialty per E005 §2.5; devour lift remains USDCAD-only. Locked lookback 24 H4 bars (Φ5-tunable). |
| **Defeat trigger** | **v2 conjunction (hybrid):** Barou v2 produces (i) ≥ 100 devour-fire events on the 11-yr USDCAD H4 panel AND (ii) ≥ 50 trades opened on EURUSD or GBPUSD combined. Either half failing retires that half (mechanic A or mechanic B) while the surviving half continues as a narrower v2. The Φ5-aggregator-with-multi-position-policy work removes one Φ4.1 confound — if v2 still produces 0 trades on USDCAD with multi-position enabled, the mechanic is dead independent of slot-cannibalisation. |
| **Home TF (fixed)** | H4 (locked pair) |
| **Symbols (fixed)** | USDCAD (locked; ignores all other instruments) |
| **conflab/ inheritance** | `conflab/detectors_zones.py` (lab-native zone re-impl). Empirical prior: **E005 cross-pair side-note** (audit §2.5, §4.3) — the *baseline* `zone` (WITHOUT the D1-trend gate) is **stronger** than `zone_d1_against` on USDCAD, AUDUSD, NZDUSD — the **inverse** of the EURUSD pattern. **This asymmetry is Barou's entire thesis.** USDCAD-locked zone-without-D1-gate is the configuration that would have made USDCAD work where A1 Isagi v1 (zone × D1-against) only managed +4.63 pips/trade vs EURUSD's +11.34. Acting on this in production requires its own pre-registered walk-forward (a new E0XX experiment), per audit §4.3. |

### 3.8 A8 — Kenyu Yukimiya (`yukimiya_kenyu`)

| Field | Value |
|---|---|
| **Thesis** | Most agents pick a price; few pick a *fill*. Yukimiya doesn't generate signals; he refines other agents' entry timing using sub-bar mechanics — spread compression, micro-pullback to limit price, session liquidity transitions |
| **Weapon (canonical)** | Smooth dribble |
| **Home TF / Supporting TFs** | M1–M5 sub-bar; inherits parent agent's home TF for context |
| **Regime fit** | Meta — he refines whoever is firing |
| **Signal trigger** | Receives an OrderIntent from the Aggregator; converts it from "market" to "limit at calculated micro-level" with a defined max-wait window |
| **Coordinate** | Doesn't emit; subscribes to others' |
| **Sizing rule** | Inherits from the parent OrderIntent |
| **Exit rule** | Inherits |
| **Anti-thesis** | None directly — Yukimiya is positive-sum for the squad |
| **Status** | to-build (Φ4+; depends on stable A1+A4) |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Smooth dribbler; clean execution; sub-bar entry-timing refiner; doesn't take shots, refines them |
| **Information tier status** | **Structural Tier 2 (by design).** Yukimiya's weapon is reading parent agents' OrderIntents — he cannot exist as Tier-3. F17 still measured to verify the design. |
| **Current version** | **v1 — not yet implemented** (depends on stable A1+A4; Φ4 v2 sweep target) |
| **Evolution arc** | v1 → v2 sharper hands (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* execution-timing improvements are small without friction context — v1 gains do not survive the calibrated simulator friction. *v2 hypothesis:* use E007 friction-quartile cutoffs (`conflab/friction.py`, Q1/Q2 = −1.1916, Q3/Q4 = +0.9864 per audit §4.1) to filter low-quality entries **before commit**, refusing fills below the bottom-friction-quartile threshold |
| **Defeat trigger** | Expected: v1 ΔTQS on refined OrderIntents is within noise band of unrefined v1 baseline; F17 ΔInfo not significant at α = 0.05 |
| **Home TF (fixed)** | M1–M5 sub-bar (inherits parent agent's home TF for context) |
| **Symbols (fixed)** | inherits from parent OrderIntent |
| **conflab/ inheritance** | `conflab/friction.py` (`wick_density`, `oscillation_count`, `path_drawdown_ratio`, `time_in_chop_band`) — the path-quality measurement primitives. Empirical prior: **E007** friction-quartile cutoffs (audit §4.1) — frozen reference distribution `Q1/Q2 = −1.1916`, `Q2/Q3 = −0.2472`, `Q3/Q4 = +0.9864` on the simple-sum-of-z-scores friction score, with per-component (mean, std) in `output/test_b/stage1_friction_reference_2026-06-16_1656.json`. **Re-usable calibration for the F12 TQS efficiency/cleanliness components without re-training.** |

### 3.9 A9 — Aoshi Tokimitsu (`aoshi_tokimitsu`)

| Field | Value |
|---|---|
| **Thesis** | Around macro events (FOMC / NFP / CPI / ECB), implied vol > realised vol; the first M5 bar with a 2×-ATR range *after* the event is a directional bet that price extends in the bar's direction for the next 4–6 M15 bars |
| **Weapon (canonical)** | Berserker (overwhelming physicality only when triggered) |
| **Home TF / Supporting TFs** | M5 event-window; M15 follow-through, H1 fade-protection |
| **Regime fit** | Vol-expansion event (very high); all others (zero — abstains entirely) |
| **Signal trigger** | Calendar tag = high-impact + event time within last 30 min + first post-event M5 close has range > 2× ATR_M5 |
| **Coordinate** | `price_band` = (event_close, event_close ± 1× ATR_M5); `time_window` = next 4–6 M15 bars; `vol_band` = (1.5×, ∞); `regime_predicate` = post-event window |
| **Sizing rule** | Higher cap (1.5 % equity) for lower frequency; conviction = range_z × event_severity |
| **Exit rule** | SL at event_close − 1× ATR_M5; ladder = 1R / 2R / 3R |
| **Anti-thesis** | A1 Isagi — Isagi fades the post-event move; Aoshi rides it |
| **Status** | to-build |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Berserker; overwhelming physicality only in event mode (FOMC / NFP / CPI / ECB) |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 — not yet implemented** (Φ4 v2 sweep target; novel weapon — no direct E001–E007 prior) |
| **Evolution arc** | v1 → v2 calendar-aware vol (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* vol-event detection without news context produces false positives at non-news vol spikes (random liquidity holes mis-classified as FOMC-style events). *v2 hypothesis:* read the production forex calendar (`agent/news/calendar.py` in `multi-pair-trading-agent`, PYTHONPATH consumption per `sim/README.md`); vol-events without news context become observation-only thoughts, never proposals |
| **Defeat trigger** | Expected: v1 false-positive rate ≥ 40 % during sealed-panel evaluation — vol spikes flagged as "events" that have no calendar tag and produce TQS ≤ 0 |
| **Home TF (fixed)** | M5 event-window |
| **Symbols (fixed)** | EURUSD, GBPUSD, USDCAD |
| **conflab/ inheritance** | `conflab/indicators.py:atr` for the post-event range-z computation; vol-regime detection (to be written as part of the F18 regime classifier in `04-quant-foundations.md`). **No direct empirical prior from E001–E007** — Aoshi is a novel weapon; the program will produce its own empirical prior at first Φ3 sealed run. |

### 3.10 A10 — Rensuke Kunigami (`kunigami_rensuke`)

| Field | Value |
|---|---|
| **Thesis** | After a loss streak, residual conviction drift biases sizing upward (in humans and in over-fit allocators). An explicit "no" voice is needed at the conductor layer |
| **Weapon (canonical)** | Reformed power-shooter (came back from injury stronger, knows when not to fire) |
| **Home TF / Supporting TFs** | daily state, not market state — fires off internal equity/streak triggers, not bar closes |
| **Regime fit** | Activated by drawdown state, not market state |
| **Signal trigger** | Daily DD > 2 % equity OR last 3 trades all losses OR PostLossGuard active for ≥ 2 consecutive sessions |
| **Coordinate** | Doesn't emit positive coordinates; emits *negative coordinates* — bands where the squad is forbidden to enter for 24 h |
| **Sizing rule** | Halves the next aggregator output for 24 h; cannot be overridden |
| **Exit rule** | n/a |
| **Anti-thesis** | Every shooting agent — Kunigami dampens them all without taking direction sides |
| **Status** | **v1 implemented + v2 wired 2026-06-30 (Φ4.2 Sentinel R1–R6 mini-sprint).** **Φ4** (4-agent MVP, EURUSD + USDCAD): 0 trades, **0 warnings emitted** in 2,006-trade squad run (predicates never tripped on the narrow MVP roster). **Φ4.1** (8-agent expanded, EURUSD + GBPUSD + USDCAD): 0 trades, **25,877 warning Thoughts emitted** — loss-streak + overconfidence predicates fired repeatedly across 11 years; Bachira's rebel-lift and Rin's precision-lift pushed peer-mean confidence above 0.85 for extended stretches. **Φ4.2 wiring (2026-06-30):** Sentinel R5 now polls `warning_active_at(as_of)` on every accepted proposal via `SentinelContext.kunigami_loss_streak_active` in `_drive_squad_replay`; a new `SentinelContext.consecutive_losses` field also fires R5 directly on any agent with ≥ 3 consecutive losses. Audit-only in the Φ4 / Φ4.1 replay paths (sealed verdicts preserved — `sentinel_blocks=False`), physically blocking in the Φ5 harness (`sentinel_blocks=True`). Wiring surface: `sim/core/sentinel.py` (R6 + `evaluate_proposal` + extended context), `sim/scoring/run_phi4_squad_gate.py`, `sim/tests/test_sentinel_wired.py` (11 new tests). |
| **MVP Φ3?** | Φ4 v1 (shipped); mandatory before live promotion |
| **Canon role (fixed)** | Reformed power-shooter; recovery / discipline; anti-tilt risk auxiliary |
| **Information tier status** | **Structural Tier 1 (by design).** Kunigami reads the ledger AGGREGATE (squad-wide confidence + per-striker closed-trade outcomes), not individual peer Thoughts during decision. The v0.1 "Tier 2" framing is superseded — aggregate reads are Tier-1 by definition (doctrine §3.9). F17 still measured in squad gate for the audit trail. |
| **Current version** | **v1 code + v2-wired 2026-06-30** — code: `sim/agents/a10_kunigami.py` (unchanged); tests: `sim/tests/test_a10_kunigami_wrap.py` (9) + `sim/tests/test_sentinel_wired.py` (11 new). `intend()` still returns None. Sentinel wiring at `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay` — every accepted proposal is evaluated with `SentinelContext.kunigami_loss_streak_active = kunigami.warning_active_at(bar.time)` and journalled to `out.sentinel_log`. The two predicates (loss-streak, overconfidence) and `warning_active_at(ts)` 24-h window are unchanged from v1 — v2 is the consumer wiring, not new agent code. |
| **Evolution arc** | **v1 → v2 wired 2026-06-30** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §3 + `experiments/phi5_aggregator/PROTOCOL.md` §11.1 amendment. Sentinel R1–R6 are now integrated into the squad-gate harness (audit-only for Φ4/Φ4.1 replay fidelity, physically blocking for Φ5). Kunigami's 25,877 Φ4.1 warning Thoughts are now feeding R5's audit stream on any re-run and will physically dampen risk in the Φ5 harness. **v2 → v3 revisit gated on:** (1) ≥ 100 R5 activations observed in Φ5 aggregator gate across `{trending, chop}` regimes (post-vol_spike+news retirement 2026-06-24); (2) v2-wired baseline frequency-of-fire published in the Φ5 verdict report. |
| **Defeat trigger** | Expected (retained for v3 revisit): v2 still activates AFTER the loss-streak has accumulated (post-hoc — 3+ losses out of 5); a v3 arc would move to **pre-emptive** dampening via forward-looking ledger confidence aggregates (low mean conviction × high pairwise correlation). Currently measurable in the Φ5 aggregator gate output — R5 activation events + their forward P&L will define the v3 defeat trigger empirically. |
| **Home TF (fixed)** | daily state (fires off internal equity/streak triggers, not bar closes) |
| **Symbols (fixed)** | all squad symbols (his negative coordinates apply globally) |
| **conflab/ inheritance** | No direct conflab primitive — Kunigami reads ledger aggregate sentiment and equity-state triggers; the implementation lives at `sim/kunigami.py` (Φ3 MVP). No empirical prior from E001–E007 applies; the prior is the 2026-06-19 live blow-up itself (per `01-week-2026-06-15-archive.md`). |

---

## 4. The coach — Jinpachi Ego

Ego is not a striker. He is the **Allocator + Risk Conductor**. His job is to enforce the doctrine without ever taking a shot.

| Responsibility | Architectural element |
|---|---|
| Set the egoist tone | The doctrine itself — `06-blue-lock-doctrine.md` is Ego's manifesto |
| Cull weak strikers | Weekly TQS-driven HRP reweighting; sub-2 % floor agents stay benched but in training |
| Prevent over-leverage | Hard SL invariant + 200 %-margin-floor + per-basket cap |
| Engineer chemical reactions | The confluence detector + size multiplier in the aggregator |
| Adversarial design | Schedules opponents (Kaiser/Loki/Sae) and ranks the squad against them |

Ego does not negotiate with strikers. The conductor's vetoes are absolute.

## 5. The opponents — Kaiser / Loki / Sae

The squad must beat the league exploiters. Three named opponents, each capturing a distinct side of the human's discretionary trading.

### 5.1 Michael Kaiser (`opponent_kaiser`)

The user's **high-conviction discretionary trades**. Engineered, calculated, single-decisive-shot. Logged to `opponents/kaiser_proposals.jsonl` whenever the user submits a trade plan with explicit entries and target ladder. Reverse-engineered into Coordinate format for apples-to-apples comparison with agent coordinates.

Test the squad answers: *can any agent's coordinate cover Kaiser's coordinate?* If yes, the squad has the read. If no, that's a coverage gap to study.

### 5.2 Yuya Loki (`opponent_loki`)

The user's **adaptive mid-week revisions** — the trades that emerge as new information arrives. Logged with timestamp + which prior signal was abandoned. Tests the squad's ability to update beliefs in real time, not just to fire on initial reads.

### 5.3 Sae Itoshi (foil) (`opponent_sae`)

A **synthetic baseline** that the squad must beat — buy-and-hold of the major basket + the frozen `zone_d1_against` strategy run with no improvements. Cold, mature, indifferent. If the squad cannot beat Sae, the entire architecture has not earned its complexity.

Sae's role in the canon — "the elder Itoshi who set the standard of cold excellence" — maps perfectly to "the baseline the project replaced."

---

## 6. Build order

Aligned with the phases in `00-charter.md`.

| Phase | Build | Why |
|---|---|---|
| **Φ2** | Spec out A1 (re-wrap), A2, A4, A6 in `sim/strikers/<id>.py` skeleton | Four-agent matrix covering trend / range / event / mean-revert |
| **Φ3** | A1 Isagi (re-wrap with home TF = H1, retaining `zone_d1_against` as Isagi v1's primitive H4 detector) + A4 Chigiri (M15 home) + A10 Kunigami + Sentinel + Sae composite. End-to-end through aggregator + equal-weight allocator + risk conductor + Sentinel. | The MVP. Minimum honest live-shape system with an external-shock auxiliary and a competitive baseline |
| **Φ3.5** | Add A2 + A6; chemical-reaction detector live; first TQS reports | The four-corner squad |
| **Φ4** | Add A3 Rin + A9 Aoshi; HRP allocator + Sharpe-weighted (F10) + TQS-weighted comparison; ego re-derived as information ratio per `06-blue-lock-doctrine.md` §3.1.b | Fusion sweep |
| **Φ4.5** | Add A5 Reo + A7 Barou + A8 Yukimiya; full 10-agent roster | Architectural maturity |
| **Φ5** | Population-Based Training over hyperparameters (Awakening); Sae baseline run continuously | Agent evolution |
| **Φ5.5** | Live shadow vs Kaiser + Loki adversarial benchmark begins | The 12-week season |
| **Φ6** | Capital promotion if charter gates C1–C6 hold | Real money |

A1 + A4 + A10 + Sentinel + Sae ship first because together they are the smallest set that exercises every architectural surface: a fade specialist (A1), a momentum specialist with a different home TF (A4), a discipline auxiliary (A10), an external-shock circuit breaker (Sentinel, see `06-blue-lock-doctrine.md` §4.2), and a competitive synthetic adversary (Sae composite, F16 in `04-quant-foundations.md`). A1 alone would have repeated the 2026-06-19 blow-up; the MVP is the smallest configuration that wouldn't.

Everyone else earns their kit as the squad proves it can play.
