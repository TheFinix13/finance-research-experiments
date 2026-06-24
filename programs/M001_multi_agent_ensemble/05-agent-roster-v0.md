# 05 — Agent Roster v0 (Blue Lock cast)

**Status:** `DRAFT v0.3` — 2026-06-24. v0.3 adds per-agent home /
supporting timeframes, the Φ3 MVP scope flag (yes for A1, A4, A10
only), and the principled-form note on the ego column (numeric egos
are placeholders until F-information-ratio derivation in Φ4+).
Supersedes v0.1 (2026-06-23, deleted before pivot to the doctrine in
`06-blue-lock-doctrine.md`).

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
| A1 | **Yoichi Isagi** | Field general / striker | Metavision (sees the board's future state) | Liquidity + market-structure (IRL / ERL / FVG / OB) | `isagi_yoichi` | H1 | M15 entry, H4+D1 context | 0.60 | yes | seeded — wraps existing `zone_d1_against` as Isagi v1 |
| A2 | **Meguru Bachira** | Wild striker | Monstrous dribble / non-linear creativity | Pattern geometry (H&S, double tops/bottoms, harmonics) | `bachira_meguru` | H1 | M15 entry, H4 pattern scale | 0.85 | Φ4+ | to-build |
| A3 | **Itoshi Rin** | Cold technician | Technical perfection | Fibonacci / harmonic / Elliott ratio mathematics | `itoshi_rin` | H4 | D1 source-swing, H1 entry | 0.40 | Φ4+ | to-build |
| A4 | **Hyoma Chigiri** | Speedster | Pure breakaway speed | Range-break + ATR vol-expansion momentum | `chigiri_hyoma` | M15 | H1 confirmation, H4 trend bias | 0.80 | yes | to-build |
| A5 | **Reo Mikage** | Chameleon | Adaptive copying | Regime-conditional dynamic copier (mimics best trailing-TQS agent) | `reo_mikage` | inherits | inherits | 0.30 | Φ4+ | to-build |
| A6 | **Seishiro Nagi** | Lazy genius | Perfect trap (ball stops dead) | Confluence-only multi-signal AND gate; lowest frequency | `nagi_seishiro` | multi-TF native | M15/H1/H4/D1 simultaneously | 0.45 | Φ4+ | to-build |
| A7 | **Shoei Barou** | King / lone wolf | Dominant solo finishing | Single-pair specialist; locks one symbol end-to-end | `barou_shoei` | H4 (locked pair) | pair-specific D1+H1 | 1.00 | Φ4+ | to-build |
| A8 | **Kenyu Yukimiya** | Smooth dribbler | Clean execution | Sub-bar entry-timing refiner (improves *other* agents' fills) | `yukimiya_kenyu` | M1–M5 sub-bar | inherits parent | 0.35 | Φ4+ | to-build (depends on A1+) |
| A9 | **Aoshi Tokimitsu** | Berserker | Overwhelming physicality (event mode) | Macro-event-only vol-breakout (FOMC / NFP / CPI) | `aoshi_tokimitsu` | M5 event-window | M15 follow-through, H1 fade-protection | 0.75 | Φ4+ | to-build |
| A10 | **Rensuke Kunigami** | Reformed power-shooter | Recovery / discipline | Anti-tilt risk auxiliary (post-loss recalibration) | `kunigami_rensuke` | daily state, not market state | n/a | 0.00 | yes | to-build |
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
| **Status** | **seeded** — wraps existing `agent/alphas/concepts/zone_alpha.py` as Isagi v1 (zone-only sub-detector on the legacy H4 cadence); v2 adds full IRL/ERL/FVG/OB on the H1 home TF once Φ3 stabilises |
| **MVP Φ3?** | yes |

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
| **Status** | to-build |
| **MVP Φ3?** | Φ4+ |

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
| **Status** | to-build |
| **MVP Φ3?** | Φ4+ |

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
| **Status** | to-build |
| **MVP Φ3?** | yes |

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
| **Status** | to-build (depends on at least 4 weeks of A1+A4 KPIs) |
| **MVP Φ3?** | Φ4+ |

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
| **Status** | to-build (depends on chemical-reaction detector being live) |
| **MVP Φ3?** | Φ4+ |

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
| **Status** | to-build (Φ4+; the architectural control agent) |
| **MVP Φ3?** | Φ4+ |

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
| **Status** | to-build (mandatory before live promotion; this is the agent that would have prevented the 2026-06-19 blow-up) |
| **MVP Φ3?** | yes |

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
