# 05 — Agent Roster v0 (Blue Lock cast)

**Status:** `DRAFT v0.6` — 2026-06-24. v0.6 marks the **Φ4 v1 squad
gate landing**: A6 Nagi v1, A7 Barou v1, and A10 Kunigami v1 are now
**implemented**, tested, and have run end-to-end against the 2015–2025
EURUSD + USDCAD H4 squad gate. The gate FAILed at 0.98× Isagi-alone
TQS — reported honestly per user constraint, with a Diagnosis section
in `reviews/phi4_squad_v1.md` explaining each agent's contribution
(Nagi predicate-starved, Barou median-dilutes, Kunigami silent in the
regime). The per-agent rows below carry the **v1 implemented** status
plus the empirical telemetry from the squad gate run. v0.5 introduced
the §3.11 evolution-arc fields (**Current version**, **Evolution arc**,
**Defeat trigger**); v0.6 fills in the post-Φ4-v1 empirical state for
A1/A6/A7/A10. The version field points at the audit trail in
`reviews/evolution_ledger.md` (evolution ledger remains empty — no
vN+1 has been claimed yet). v0.4
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
| A1 | **Yoichi Isagi** | Field general / striker | Metavision (sees the board's future state) | Liquidity + market-structure (IRL / ERL / FVG / OB) | `isagi_yoichi` | H1 | M15 entry, H4+D1 context | 0.60 | yes | seeded — wraps existing `zone_d1_against` as Isagi v1 |
| A2 | **Meguru Bachira** | Wild striker | Monstrous dribble / non-linear creativity | Pattern geometry (H&S, double tops/bottoms, harmonics) | `bachira_meguru` | H1 | M15 entry, H4 pattern scale | 0.85 | Φ4+ | to-build |
| A3 | **Itoshi Rin** | Cold technician | Technical perfection | Fibonacci / harmonic / Elliott ratio mathematics | `itoshi_rin` | H4 | D1 source-swing, H1 entry | 0.40 | Φ4+ | to-build |
| A4 | **Hyoma Chigiri** | Speedster | Pure breakaway speed | Range-break + ATR vol-expansion momentum | `chigiri_hyoma` | M15 | H1 confirmation, H4 trend bias | 0.80 | yes | to-build |
| A5 | **Reo Mikage** | Chameleon | Adaptive copying | Regime-conditional dynamic copier (mimics best trailing-TQS agent) | `reo_mikage` | inherits | inherits | 0.30 | Φ4+ | to-build |
| A6 | **Seishiro Nagi** | Lazy genius | Perfect trap (ball stops dead) | Confluence-only multi-signal AND gate; lowest frequency | `nagi_seishiro` | H4 (Φ4 v1) | M15/H1/H4/D1 (canon) | 0.45 | Φ4 v1 | **v1 implemented (Φ4 squad gate)** — fired 0 confluence thoughts (predicate-starved; see `reviews/phi4_squad_v1.md` Diagnosis) |
| A7 | **Shoei Barou** | King / lone wolf | Dominant solo finishing | Single-pair specialist; locks one symbol end-to-end | `barou_shoei` | H4 (locked pair) | pair-specific D1+H1 | 1.00 | Φ4 v1 | **v1 implemented (Φ4 squad gate)** — 1150 trades, +9.79 mean / −7.28 median pips, devour mechanic shipped (0 lifts in 11-yr run) |
| A8 | **Kenyu Yukimiya** | Smooth dribbler | Clean execution | Sub-bar entry-timing refiner (improves *other* agents' fills) | `yukimiya_kenyu` | M1–M5 sub-bar | inherits parent | 0.35 | Φ4+ | to-build (depends on A1+) |
| A9 | **Aoshi Tokimitsu** | Berserker | Overwhelming physicality (event mode) | Macro-event-only vol-breakout (FOMC / NFP / CPI) | `aoshi_tokimitsu` | M5 event-window | M15 follow-through, H1 fade-protection | 0.75 | Φ4+ | to-build |
| A10 | **Rensuke Kunigami** | Reformed power-shooter | Recovery / discipline | Anti-tilt risk auxiliary (post-loss recalibration) | `kunigami_rensuke` | H4 (Φ4 v1) | daily state (canon) | 0.00 | Φ4 v1 | **v1 implemented (Φ4 squad gate)** — 0 warnings emitted; 3-of-5 high-conf-loss predicate never tripped in 2006-trade run |
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
| **Status** | **seeded** — wraps existing `agent/alphas/concepts/zone_alpha.py` as Isagi v1 (zone-only sub-detector on the legacy H4 cadence); v2 adds full IRL/ERL/FVG/OB on the H1 home TF once Φ3 stabilises |
| **MVP Φ3?** | yes |
| **Canon role (fixed)** | Field-general striker reading the field's future state via metavision |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement (F17 in `04-quant-foundations.md`) |
| **Current version** | **v1** — landed at commit `12c2bf4` (Φ3 wrapper of production `zone_d1_against`); Φ3 gate `PASS` per `reviews/phi3_gate_isagi_v1.md` |
| **Evolution arc** | v1 → v2 metavision sharpens (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* setups outside the `zone_d1_against` vocabulary missed at material frequency. *v2 hypothesis:* expand primitives via `conflab/detectors_liquidity.py` (`equal_highs_pool`, `equal_lows_pool`, `liquidity_sweep_high/low`) + FVG/OB detectors; coordinate cadence H4 → H1 |
| **Defeat trigger** | Expected: TQS regression in vol-expansion regime bucket OR an audit pass showing IRL/ERL sweeps Isagi v1 cannot read; cite trade-ID range in `reviews/isagi_yoichi_v1_defeat.md` when it lands |
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
| **Status** | to-build |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Wild striker; monstrous-dribble creativity; pattern geometry as non-linear improvisation |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 — not yet implemented** (benched per `09-experiment-architecture.md` §2; not in Φ4 v1 MVP roster) |
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
| **Status** | to-build |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Cold technician; technical perfection via mathematical ratios |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 — not yet implemented** (benched per `09-experiment-architecture.md` §2; Φ4 v2 sweep target) |
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
| **Status** | to-build |
| **MVP Φ3?** | yes |
| **Canon role (fixed)** | Speedster; pure breakaway speed; commit-and-run once the range resolves |
| **Information tier status** | TBD — pending Φ3 ΔInfo measurement |
| **Current version** | **v1 — not yet implemented** (Φ3 MVP scope target but currently deferred to Φ4 v2 sweep; see `05-agent-roster-v0.md` §1.1) |
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
| **Status** | to-build (depends on at least 4 weeks of A1+A4 KPIs) |
| **MVP Φ3?** | Φ4+ |
| **Canon role (fixed)** | Chameleon; adaptive copying; ego defers to whoever is winning this week |
| **Information tier status** | **Structural Tier 2 (by design).** Reo's weapon *is* reading the leader's thoughts; he cannot exist as Tier-3. ΔInfo (F17) is still measured to verify the design — if informed Reo does not beat isolated Reo on F17, Reo is cut from the roster (not relegated). |
| **Current version** | **v1 — not yet implemented** (depends on ≥ 4 weeks of A1+A4 KPIs; Φ4 v2 sweep target) |
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
| **Status** | **v1 implemented (Φ4 squad gate)** — Φ4 squad ran 2015–2025 EURUSD + USDCAD H4, Nagi fired **0 confluence-firing thoughts** (the 2-distinct-peer floor was never met because MVP squad has only 2 tradable strikers; predicate-starved by design, not by the one-bar lag). See `reviews/phi4_squad_v1.md` Diagnosis #1. |
| **MVP Φ3?** | Φ4 v1 (shipped) |
| **Canon role (fixed)** | Lazy genius; perfect trap; lowest-frequency, highest-RR; fires only on multi-signal confluence |
| **Information tier status** | **Structural Tier 2 (by design).** Nagi is the canonical chemical-reaction agent — his trigger is overlap of other agents' coordinates and resonance of their Thoughts. Cannot operate as Tier-3. F17 still measured to verify the design. v1 F17 ΔInfo = +0.000 [underpowered] — uninformative until enough Tier-2 source signal exists for Nagi to fire on. |
| **Current version** | **v1 implemented** — code: `sim/agents/a06_nagi.py`; tests: `sim/tests/test_a06_nagi_wrap.py` (8 tests, all passing). Predicate: ≥ 2 OTHER strikers' Thoughts at tick T-1 with conviction > 0.7, ≥ 2 shared tags, overlapping coordinate price bands, matching direction. F11 lift via 1 − ∏(1 − cᵢ). Home TF H4 (Φ4 v1) per `09-experiment-architecture.md` §2; the multi-TF canon home is a Φ5+ wiring. Live-capital allocation still blocked until E010 confirms the H1 `equal_highs_pool` × M15 setup exploratory finding. |
| **Evolution arc** | v1 → v2 boredom into mastery (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* confluence-only firing rate too low — sample size never clears C1 under the v1 ≥ 3-striker overlap rule. *v2 hypothesis:* tolerate 2-striker overlaps with lower aggregate conviction floor when regime is favourable per F18 |
| **Defeat trigger** | Expected: v1 trade count too low for statistical power on the rolling 12-week window (< 5 trades per pair); insufficient-n verdict on the C1 gate |
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
| **Status** | **v1 implemented (Φ4 squad gate)** — 1150 trades on USDCAD H4 2015–2025, **+9.79 mean pips** but **−7.28 median pips**, 49.8 % win rate. Mean-positive but median-negative (E005's fat-right-tail asymmetry confirmed); dilutes the squad's median-of-means TQS. **0 devour lifts** in 11-year run — Isagi was either silent or directionally aligned on every USDCAD signal tick. See `reviews/phi4_squad_v1.md` Diagnosis #2. |
| **MVP Φ3?** | Φ4 v1 (shipped) |
| **Canon role (fixed)** | King / lone wolf; dominant solo finishing; refuses to participate in chemical reactions |
| **Information tier status** | **Structural Tier 2 by canon revision (devour mechanic).** Barou's devour lift reads Isagi's prior-tick high-conviction thoughts to detect directional disagreement; the original v0.1 "Tier-3 by design" framing referenced the *default* state when Isagi is silent. With devour wired, Barou is Tier-2 with isolation as the experimental control. v1 F17 ΔInfo measured: +0.000 [underpowered] — devour fired 0 times so isolation made no measurable difference. |
| **Current version** | **v1 implemented** — code: `sim/agents/a07_barou.py`; tests: `sim/tests/test_a07_barou_wrap.py` (6 tests, all passing). Wraps production `agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` with `htf_align=None` and `target_rr=1.5` (baseline zone, no D1 gate). USDCAD-only; abstains on EURUSD/GBPUSD via observation-only Thoughts. Devour mechanic: +0.10 conviction lift (cap 1.0) when Isagi has prior-tick thought on USDCAD at conviction ≥ 0.7 with opposite direction. |
| **Evolution arc** | v1 → v2 devour mechanic awakens (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* USDCAD baseline `zone` alone is a small edge (audit §2.5, +4.63 pips/trade vs EURUSD's +11.34); the King is not yet eating. *v2 hypothesis:* when Isagi shows high conviction on USDCAD that Barou disagrees with, Barou takes the opposite side at scaled size; devour bonus δ becomes measurable per F15 |
| **Defeat trigger** | Expected: v1 TQS on USDCAD does not clear C1 vs Sae despite the baseline-zone asymmetry; "lone wolf" PnL underperforms even simple equal-weight fusion |
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
| **Status** | **v1 implemented (Φ4 squad gate)** — **0 trades, 0 warnings emitted** in 2006-trade squad run (loss-streak 3-of-5 high-conviction predicate never tripped; overconfidence ≥ 10-sample 0.85-mean predicate never tripped). The conservative predicates are tight enough to never produce a false positive; possibly TOO tight for the 2015–2025 EURUSD+USDCAD volatility regime. See `reviews/phi4_squad_v1.md` Diagnosis. Sentinel R5 wiring lives in `sim/core/sentinel.py` and is exercised by `sim/tests/test_a10_kunigami_wrap.py::test_warning_active_at_24h_window`. |
| **MVP Φ3?** | Φ4 v1 (shipped); mandatory before live promotion |
| **Canon role (fixed)** | Reformed power-shooter; recovery / discipline; anti-tilt risk auxiliary |
| **Information tier status** | **Structural Tier 1 (by design).** Kunigami reads the ledger AGGREGATE (squad-wide confidence + per-striker closed-trade outcomes), not individual peer Thoughts during decision. The v0.1 "Tier 2" framing is superseded — aggregate reads are Tier-1 by definition (doctrine §3.9). F17 still measured in squad gate for the audit trail. |
| **Current version** | **v1 implemented** — code: `sim/agents/a10_kunigami.py`; tests: `sim/tests/test_a10_kunigami_wrap.py` (9 tests, all passing). `intend()` always returns None — Kunigami never trades. External harness pushes closed-trade outcomes via `record_closed_trade(rec)`. Two predicates: (1) **loss-streak warning** if ≥ 3 of last 5 closed trades were losses AND from high-conviction (≥ 0.7) proposals; (2) **overconfidence warning** if mean confidence-in-thought across non-Kunigami peer Thoughts in the last 50 ticks exceeds 0.85 (with n ≥ 10 floor). `warning_active_at(ts)` exposes a 24-h `kunigami_loss_streak_warning` window for the Sentinel R5 dampener. |
| **Evolution arc** | v1 → v2 gentle giant (`06-blue-lock-doctrine.md` §3.11.3). *Trigger:* loss-streak dampener fires *after* damage is done — three losses before the half-size kicks in. *v2 hypothesis:* read forward-looking ledger confidence aggregates (low aggregate conviction × high pairwise correlation) and dampen **pre-emptively**, before the third loss lands; anti-tilt becomes anticipatory |
| **Defeat trigger** | Expected: v1 activates only after the loss has accumulated (post-hoc); on the 2026-06-19 replay window, v1 would have halved size after −$48 of damage rather than before. The defeat is the lateness, not the direction |
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
