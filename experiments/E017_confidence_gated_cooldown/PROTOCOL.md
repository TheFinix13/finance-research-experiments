# E017 - Confidence-gated cooldown vs. binary kill-switch (pre-registered)

**Status:** PRE-REGISTERED 2026-07-13 · **Date frozen:** 2026-07-13

The deployed agent halts trading on a self-inflicted risk event with a
**binary kill-switch**: a 3.0 % daily-drawdown breach
(`RiskConfig.daily_dd_halt_pct = 0.03`), a 3-consecutive-loss circuit
breaker, or a catastrophic stop-out
(`PostLossGuard`, `catastrophic_loss_frac = 0.10`) writes a per-symbol
`{log_root}/{SYMBOL}/kill.txt` that **blinds the whole loop until a
human deletes it**. On the real 2026-07-08 → 07-12 incident this cost
GBPUSD **50.9 h+ of continuous dead time** (07-10 03:15 → still active
at end of logs), on top of an earlier 92.4 h stale-`kill.txt` episode —
~50 % downtime over the 12-day window, with only 2 real GBPUSD trades
fired all week. The 07-10 halt was triggered largely by a **shared-
account** EURUSD loss that force-closed an open GBPUSD ticket, then left
all symbols dark.

E017 asks: **does a graduated, loss-magnitude-scaled confidence score
(continuous, never a hard drop to 0) that keeps the agent watching and
shadow-trading — with recovery driven by demonstrated hypothetical
success rather than a calendar rollover — preserve capital at least as
well as the binary kill-switch while drastically reducing dead time and
opportunity cost?**

This is a **risk/execution-mechanism study**, not an alpha study. It
changes *when the agent is allowed to place real orders*, never the
entry signal itself. Per the plan, **Phase 3 (implementation in
`multi-pair-trading-agent`) is gated on a positive Phase 2 verdict from
this protocol.** If inconclusive or negative, the current hard
kill-switch stays and a `STOP_NOTICE.md` is written (E012/E015/E016
convention).

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Literature in
[`../../reviews/refs.bib`](../../reviews/refs.bib).

---

## §0 Reuse declaration (no production code touched)

E017 Phase 1 (this document) writes **no code**. Phase 2 builds a
simulation harness **in this repo only**. Production
`monitor.py`, `post_loss_guard.py`, `risk/manager.py`, and
`signal_loop.py` are **read-only references** for parameter values and
the incident replay; nothing here trades, routes orders, or edits live
parameters.

| Purpose | Module / artefact | Status |
|---|---|---|
| Daily-DD halt reference | `multi-pair-trading-agent/agent/risk/manager.py::RiskManager.record_trade_pnl` (`daily_dd_halt_pct=0.03`) | read-only |
| Circuit breaker / stop-out reference | `multi-pair-trading-agent/agent/risk/post_loss_guard.py::PostLossGuard` (`max_consecutive_losses=3`, `loss_risk_multiplier=0.5`, `catastrophic_loss_frac=0.10`) | read-only |
| Shared-account read pattern | `multi-pair-trading-agent/agent/risk/manager.py::RiskManager.portfolio_open_risk_pct` (each process reads the same broker account) | read-only pattern to mirror |
| Incident logs | GBPUSD/EURUSD/USDCAD live logs + vault `events.jsonl`, 2026-07-08 → 07-12 | read-only case-study input |
| MC + replay harness (Phase 2) | `finance-research-experiments/programs/E017/` (new, Phase 2) | to be built |

---

## §1 Hypothesis (operational)

Let a per-symbol **confidence** `c_s ∈ [C_min, 1]` and an account-wide
**gauge** `g ∈ [g_min, 1]` combine into an **effective confidence**
`κ_s = c_s · g`. The agent is in `live` mode when `κ_s ≥ τ_live` and in
`reduced` (shadow-only, still watching) mode otherwise — **never fully
off**. On resume, real risk is tapered by `κ_s` (mirroring
`PostLossGuard.loss_risk_multiplier`) until `κ_s ≥ τ_full`.

**H0 (null).** Graduated confidence + shadow recovery (Arm GC-S) does
**not** Pareto-improve on the binary kill-switch (Arm HK): it fails to
reduce time-to-resume without a capital-preservation cost (no better on
median terminal equity / max-drawdown / risk-of-ruin), across the frozen
parameter grid.

**H1 (alt).** Arm GC-S **Pareto-dominates** Arm HK on the pre-registered
Monte-Carlo panel — materially lower dead time / time-to-resume **and**
no-worse capital preservation (median terminal equity, worst-path max
drawdown, empirical risk-of-ruin) — and on the 2026-07-08 incident
replay would have eliminated the multi-day blinding **without** removing
the immediate protective close of real positions.

**H2 (parsimony).** If Arm GC-S is statistically indistinguishable from
Arm GC-T (graduated confidence, time-decay recovery only, no shadow) on
all primary metrics, the shadow-recovery machinery earns no keep:
verdict caps at `parked_shadow_adds_nothing` (prefer the simpler
time-decay variant or stop).

**Primary outcome metrics** (per arm, per MC path, pre-registered):
1. **Capital preservation** — median terminal equity; worst-path
   maximum drawdown; empirical risk-of-ruin `P(equity ≤ ruin_frac ·
   E_0)` with `ruin_frac = 0.50`; account-curve CDaR at β = 0.95
   (Chekhlov–Uryasev–Zabarankin `chekhlov2005drawdown`).
2. **Time-to-resume** — bars (and wall-clock-equivalent hours) from a
   suspension event to the return of full-risk trading, per symbol.
3. **Opportunity cost** — count and net R of trades that *would* have
   fired during suspension (shadow ledger), i.e. the "50 h dead-time"
   loss the incident exposed.

---

## §2 Separation

- **Does this touch the trading agent?** **No.** Phase 1 is documents +
  citations. Phase 2 is a sim harness under `programs/E017/`. Phase 3
  (production wiring) is a **separate, gated** deliverable in
  `multi-pair-trading-agent`, contingent on the Phase 2 verdict.
- **Prior uses of the same data.** No `(pair, TF, split)` research bar
  slice is consumed for a statistical claim. The Monte-Carlo panel is
  synthetic (parameters in §4). The incident replay uses the agent's own
  2026-07-08 → 07-12 live logs (a one-off operational record, n = 1 case
  study, reported descriptively — **not** an FDR family member). No
  `DATA_LEDGER.md` sealed-slice consumption; a `planned` note is added
  when Phase 2 starts.

---

## §3 Candidate confidence-score formulas (frozen)

All candidates are **continuous** and **loss-magnitude-scaled** — a
larger loss lowers confidence more, and confidence floors at `C_min > 0`
(the agent keeps analysing/shadow-trading; it is never killed). "Since
the last high-confidence state" means since the anchor at which `c_s`
was last 1.0 (fresh start, or a post-recovery reset).

Notation (per symbol `s`):
- `L_s` = cumulative **realised** loss in R since the anchor (R =
  realised P&L / initial per-trade risk). Wins net against it,
  `L_s = max(0, Σ −R_loss − Σ R_win)`.
- `S_s` = cumulative **shadow** gain in R banked while `reduced`
  (hypothetical wins from the shadow tracker), `S_s ≥ 0`.
- `E` = current broker **account equity**; `M` = running account
  **equity peak**; both read directly from the shared broker account
  each iteration (§5).

### Per-symbol confidence candidates

| ID | Formula | Grounding |
|---|---|---|
| **P-exp** | `c_s = C_min + (1 − C_min)·exp(−λ · max(0, L_s − S_s))` | Fractional-/risk-constrained-Kelly single risk-aversion parameter that smoothly trades growth for drawdown control; exponential decay never reaches 0. `busseti2016kelly`, `kelly1956` |
| **P-lin** | `c_s = clip(1 − (L_s − S_s)/L_floor, C_min, 1)` | Piecewise-linear drawdown throttle; `L_floor` = R-loss at which confidence bottoms to `C_min`. Simplest loss-magnitude scaling; interpretable kill-equivalent point. `chan2009quantitative` |

Recovery is **symmetric in the same metric**: banking shadow gains `S_s`
(or real wins after resume) raises `c_s` back up. An **optional additive
time-decay** term `+ ρ · Δt` (bounded so it cannot alone restore full
confidence) is included **only** in Arm GC-T to isolate the shadow
contribution (H2).

### Account-wide gauge candidates

| ID | Formula | Grounding |
|---|---|---|
| **G-surplus** | `g = clip( (E − α·M) / ((1 − α)·M), g_min, 1 )` | Grossman–Zhou drawdown-constrained optimal exposure ∝ surplus over a floor that is a fraction `α` of the running max; exposure falls to the floor as equity approaches `α·M` and recovers as equity climbs back to `M`. `grossman1993drawdowns` (discrete-time caveat: `klass2005grossmanzhou`) |
| **G-cdar** | `g = clip(1 − CDaR_β(underwater)/D_tol, g_min, 1)` | Penalises **sustained/deep** account drawdowns (mean of worst `(1−β)` tail of the underwater curve) rather than a single blip — robust to one-tick spikes. `chekhlov2005drawdown` |

**Effective confidence** `κ_s = c_s · g` (multiplicative **dampening**,
floored at `C_min · g_min > 0`): a bad day on one symbol lowers `E`,
which lowers `g`, which dampens *every* symbol's confidence — but never
to zero, and each symbol's own `c_s` (its own signal-quality state)
still drives its own decisions (§4a). This is the risk-budgeting
intuition that account-level risk is shared across correlated
instruments on one account (`maillard2010erc`, `chekhlov2005drawdown`).

**Frozen candidate matrix (Phase 2 evaluates exactly these, no
continuous tuning):** per-symbol ∈ {P-exp, P-lin} × gauge ∈ {G-surplus,
G-cdar} = 4 confidence configurations, each run as Arm GC-S and Arm
GC-T, against the single Arm HK baseline.

---

## §4 Locked parameters

| Knob | Value(s) | Rationale |
|---|---|---|
| `C_min` (per-symbol floor) | 0.15 | Matches `PostLossGuard.loss_risk_multiplier=0.5` philosophy of *reduce, don't zero*; 0.15 keeps a live-but-tiny watcher. Never 0. |
| `g_min` (gauge floor) | 0.25 | Account dampening bottoms at ¼, not 0 — "dampens, not blocks" (plan requirement). |
| `λ` (P-exp decay) | {0.25, 0.5} | Two risk-aversion settings; `exp(−λ·L)` gives c≈0.61/0.37 at L=2R for λ=0.25/0.5 (frozen; no third value added post-hoc). |
| `L_floor` (P-lin) | {4, 8} R | R-loss to reach `C_min`; 4R ≈ current same-day cascade scale, 8R = slower. |
| `α` (G-surplus floor frac) | 0.97 | Mirrors the 3 % daily-DD line (`daily_dd_halt_pct=0.03`): gauge hits floor exactly where the old kill-switch fired. |
| `β` (G-cdar tail) | 0.95 | Convention (aligns with the CVaR-family 95 % tail). |
| `D_tol` (G-cdar tolerance) | 0.03 of `M` | Same 3 % reference as the daily-DD halt. |
| `τ_live` (shadow→live threshold) | 0.30 | Below this, real orders suspended (shadow only). |
| `τ_full` (full-risk threshold) | 0.80 | At/above this, risk multiplier returns to 1.0; between `τ_live` and `τ_full`, real risk = `κ_s` (tapered resume). |
| `ρ` (GC-T time-decay) | 0.01 / bar, capped so time-decay alone tops out at `κ = τ_full − 0.05` | Time can partially heal but **cannot** fully restore confidence without demonstrated (shadow/real) success — isolates the shadow effect for H2. |
| Ruin threshold `ruin_frac` | 0.50 | Risk-of-ruin defined as equity ≤ 50 % of start. |
| MC paths `N` | 10,000 | Powered for stable tail (risk-of-ruin, CDaR) estimates. |
| MC horizon | 2,000 trade-events / symbol | ≈ multi-year at the deployed ~66 trades/yr/symbol cadence. |
| Symbols | 3 (EURUSD, GBPUSD, USDCAD) on ONE shared account | Matches production topology. |
| Per-trade edge / R-distribution | bootstrapped from the deployed cell's own trade R-distribution (E004/E013 trade ledger) **and** a synthetic Bernoulli control (`p_win`, `R_win`, `R_loss` in the frozen grid below) | Two data-generating processes so the verdict is not an artefact of one. |
| Synthetic grid | `p_win ∈ {0.40, 0.55}`, `R_win = +1.5`, `R_loss = −1.0` | Spans a losing-ish and a winning regime; RR matches the alpha's `target_rr=1.5`. |
| Cross-symbol correlation | ρ ∈ {0.0, 0.5} on trade outcomes | Tests the shared-account gauge under independent vs. correlated symbols. |
| Random seed | 42 | Convention (matches E014). |
| Bootstrap resamples (CI on metrics) | 5,000 | Convention. |

### §4a Portfolio-gauge design — three processes, one account, no new IPC

Production runs **three independent OS processes**, one per symbol, with
no shared memory. The account-wide gauge must be computable **per
process from data it already has**, mirroring
`RiskManager.portfolio_open_risk_pct` (each process reads the same
broker account balance/equity directly):

1. Every iteration, each process reads broker **balance** and **equity**
   (already available; `portfolio_open_risk_pct` proves the pattern).
2. Each process persists **its own** running equity peak `M` in its own
   `state.json` (not day-scoped), updated `M ← max(M, E)` each iteration.
3. The gauge `g = f(E, M, α)` (or the CDaR variant over a rolling equity
   buffer) is a **pure deterministic function** of those reads — so all
   three processes compute the **same** `g` up to at most one
   iteration's read-lag on the shared equity.
4. Symbols still **decide trades independently** (`c_s` is private per
   symbol); the account gauge only **dampens** the shared risk budget.

**Pre-registered convergence check (must pass or the design is
rejected):** in Phase 2, run the three-process gauge computation on a
shared simulated equity feed and verify the pairwise gauge disagreement
stays `≤ ε_gauge = 0.02` for ≥ 99 % of iterations (bounded read-lag).
If processes cannot agree on `g` within tolerance without IPC, the
no-IPC design **fails** and E017 stops.

---

## §5 Validation method (Phase 2 — not run in Phase 1)

### (i) Synthetic Monte-Carlo equity-curve simulation

Three arms on the identical simulated trade streams (same seed / paths):

| Arm | Behaviour |
|---|---|
| **HK** (baseline) | Current production: on a 3 % daily-DD breach OR 3 consecutive losses OR catastrophic stop-out → **close real positions and halt (blind) until a day rollover / manual reset**. Models `kill.txt` persistence. |
| **GC-S** | Graduated confidence (§3 candidate) + **shadow recovery**: on the same trigger, close real positions immediately (safety preserved) but keep evaluating; suspend real orders while `κ_s < τ_live`; bank shadow gains `S_s`; taper real risk by `κ_s` on resume. |
| **GC-T** | Same as GC-S but recovery is **time-decay only** (`ρ`), shadow ledger disabled — the H2 control. |

Scored on the §1 primary metrics with bootstrap-95 % CIs (5,000
resamples, seed 42) across the frozen §4 grid.

### (ii) Historical replay — the 2026-07-08 → 07-12 incident (case study, n = 1)

Reconstruct the real GBPUSD/EURUSD/USDCAD cascade from the agent's own
logs and replay each arm over the same bar/event stream:
- **Ground truth (HK):** GBPUSD blinded 07-10 03:15 → 50.9 h+; 2 real
  trades all week; a shared-account EURUSD loss force-closed GBPUSD then
  left every symbol dark.
- **Replay GC-S / GC-T:** would the agent have (a) still executed the
  immediate protective close on the DD breach (**required** — safety
  invariant), and (b) kept evaluating + shadow-trading through the
  50.9 h window, resuming on demonstrated recovery instead of a manual
  `kill.txt` delete? Report dead-time hours removed and the shadow P&L
  of trades that would have fired.
- Reported **descriptively**; a single incident is illustrative, not a
  statistical claim.

**Safety invariant (non-negotiable, pre-registered).** In every arm the
immediate close of real open positions on a genuine DD/stop-out event is
**retained**. E017 only replaces the *persistent blinding* of the loop,
never the protective close.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4:

- **`alive` → advance to Phase 3 implementation** iff, for at least one
  frozen §3 configuration:
  1. **MC:** GC-S **Pareto-dominates** HK — time-to-resume materially
     lower (median dead-time reduction ≥ 50 %) **AND** capital
     preservation no worse on all three sub-metrics (median terminal
     equity CI lower-bound ≥ HK median; worst-path max-drawdown not
     larger beyond noise; risk-of-ruin ≤ HK), robust across both
     data-generating processes and both correlation settings; **AND**
  2. **Gauge convergence check** (§4a) passes (≤ ε_gauge); **AND**
  3. **Replay:** GC-S removes the multi-day blind window while
     preserving the protective close.
- **`parked_capital_cost`** — GC-S cuts dead time but fails Pareto
  (worse on a capital metric). Do not ship; redesign required.
- **`parked_shadow_adds_nothing`** (H2) — GC-S ≈ GC-T on all primary
  metrics: shadow machinery unjustified; prefer time-decay or stop.
- **`dead` / STOP (keep hard kill-switch, write `STOP_NOTICE.md`)** iff
  GC-S does **not** beat HK on time-to-resume, **or** it degrades any
  capital-preservation metric / raises risk-of-ruin, **or** the gauge
  convergence check fails. Phase 3 does **not** proceed.

**Discipline guards.** All §3/§4 formulas and constants are **frozen at
this pre-registration**. Phase 2 selects among the discrete candidate
set only — **no continuous parameter tuning, no post-freeze grid
extension** (`PROTOCOL_DISCIPLINE.md` §5). A negative or inconclusive
result **is reported** (`STOP_NOTICE.md`), never buried. Backtest-
overfitting hygiene applies to the candidate selection: with 4
configurations × 2 arms, the winning configuration's edge is reported
with its selection context so a reader can gauge search-width inflation
(`bailey2016pbo`, `bailey2014deflated`).

---

## §7 Amendments

**A1 (2026-07-13, Phase 2 start — operationalization constants, no formula
or grid changes).** The §3/§4 formulas and grid are untouched. The Phase 2
harness requires five operationalization constants the pre-registration
left unpinned; they are fixed here **before any simulation is run**:

1. **Trade-event cadence / bars↔hours mapping.** The MC is day-driven:
   each symbol fires a trade event with per-day intensity
   `λ_trade = 66/365 ≈ 0.18` (matches the deployed ~66 trades/yr/symbol),
   capped at 2 events/symbol/day. Horizon = **11,000 days/path**
   (expected ≈ 2,000 trade-events/symbol, per §4). Dead time converts at
   **24 h/day** (1 H4 bar = 4 h, 6 bars/day).
2. **HK manual-reset delay.** Production `kill.txt` requires a human
   delete; observed episodes ran 50.9 h and 92.4 h. The HK baseline
   models kill-file persistence as a **fixed 48 h** blind window
   (conservative: *shorter* than both observed episodes, which favours
   HK), with pre-registered sensitivity runs at **24 h and 72 h**.
   Day-scoped halts (`PostLossGuard` circuit breaker) reset at UTC
   rollover as in production.
3. **Per-symbol risk fractions** mirror production routing:
   EURUSD 1.475 % (route_scale 1.0), GBPUSD/USDCAD 0.7375 %
   (route_scale 0.5), conviction fixed 0.65.
4. **Consecutive-loss circuit breaker is retained but near-inert** at
   this cadence (≥3 same-day losses on one symbol is rare with ≤2
   events/day); the operative trigger — as in the real 07-10 incident —
   is the 3 % account daily-DD. Reported as-is.
5. **GC-T time-decay** is implemented as `+0.06/day` on `c_s`
   (= 6 H4 bars × ρ 0.01/bar), with the decayed `c_s` capped at 0.75 so
   decay alone cannot exceed `κ = τ_full − 0.05` (§4). **G-cdar** uses a
   rolling 250-day underwater window, tail mean of the worst 5 %,
   refreshed every 5 days (drawdown moves slowly at day resolution).

The bootstrap ledger declared in §4/§9 is pinned to
`programs/E017/data/trade_ledger_EURUSD_H4.json` (737 trades, regenerated
read-only from the E013 `all_on` production-matching harness; hit-rate
0.5577 identical to E013 `results.json`).

---

## §8 Cross-references

- **Plan.** `~/.cursor/plans/confidence-gated_cooldown_*.plan.md` (3-phase,
  Phase 3 gated on this study).
- **E013 safety-layer contribution**
  ([`../E013_safety_layer_contribution/REPORT.md`](../E013_safety_layer_contribution/REPORT.md))
  — the `plg_earns_keep` finding (PostLossGuard blocks winners more
  often than it averts losses) is the sibling evidence that the current
  blunt halting layer is *expensive*; E017 tests a graduated replacement.
- **Kunigami Wild-Card DD gate (M001)** — the M001 finding that
  peak-relative DD gating is inert on the additive fixed-lot sandbox but
  stays sensitive on the production %-of-equity curve directly motivates
  the equity-based G-surplus / G-cdar gauges here.
- **Production references (read-only):** `agent/risk/manager.py`,
  `agent/risk/post_loss_guard.py`, `agent/live/monitor.py`,
  `agent/live/signal_loop.py`.

---

## §9 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| MC (i) | synthetic + bootstrap of deployed-cell R-distribution | new simulation | trade ledger from E004/E013 (summary reuse) |
| Replay (ii) | agent live logs 2026-07-08 → 07-12 (GBPUSD/EURUSD/USDCAD) | one-off case study, descriptive | none (operational record) |

No sealed `(pair, TF, split)` bar slice is consumed for a statistical
claim; no FDR family is opened on market bars. A `planned` row is added
to `DATA_LEDGER.md` if Phase 2 later bootstraps from a specific trade
ledger export.

---

**Pre-registration commit:** _(hash after push)_
