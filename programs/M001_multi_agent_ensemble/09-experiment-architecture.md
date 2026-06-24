# 09 — Experiment Architecture (Brilliant Architecture operational spec)

**Status:** `DRAFT v0.1` — 2026-06-24. v0.3 doctrine. Binding design
spec for how M001 runs experiments: replay kernel, injectable ledger,
TQS-only optimisation, numeric phase gates, simulator friction, and
modular roster ablation. Supersedes informal architecture notes scattered
across `03-architecture-v0-sketch.md` for *experiment execution* only;
the v0 sketch remains authoritative for component wiring.

**Audience:** implementers of `sim/`, reviewers in `reviews/`, and anyone
grading a phase gate. This doc is not blog prose — deviations require an
amendment commit before the affected run starts.

Reading order: `00-charter.md` (mandate) → this doc (how we run) →
`07-research-standards.md` (statistical hygiene) → `08-dashboard-spec.md`
(how we falsify via UI).

---

## §1. Design principles (ten pillars)

### §1.1 Replay-first, live-second

The **simulator is the experiment**. Every hypothesis, roster change,
allocator sweep, and ΔInfo measurement runs in `sim/` against historical
bars with a reproducible manifest before any capital is risked.

The **live $100 / 1:1000 demo account** (charter §7) is **out-of-sample
validation only**:

| Layer | Role | Pass/fail authority |
|---|---|---|
| `sim/` replay | Primary evidence; sealed panels; PBO; adversarial cohort | Phase gates Φ2→Φ6 |
| Live demo | Confirms simulator ↔ broker parity; monitors drift | Φ6→live gate only |
| Production router | Unchanged until explicit promotion from M001 | Separate promotion pass |

**Binding rules.**

1. No phase gate may be cleared on live PnL alone.
2. Live trades append to the evidence ledger but **never retroactively
   upgrade** a failed replay gate.
3. Simulator calibration (§1.9) must be re-verified against June 2026
   VM broker fills before Φ5 shadow live begins.

### §1.2 Deterministic kernel

Given identical inputs `(market_state_t, ledger_snapshot_t, seed)` every
agent emits an identical `Thought` on tick `t`. Given identical
`(proposals[], allocator_state, seed)` the Aggregator emits identical
fused output.

**Deterministic path (must be pure):**

```
market_state → feature_fanout → agent.observe() → Thought
ledger_snapshot → agent.intend() → Proposal (optional)
proposals[] → allocator → aggregator → sentinel → OrderIntent
```

**Firewall — these MUST NOT sit in the decision path without an
explicit, tested adapter that preserves determinism under replay:**

| Component | Allowed role | Default |
|---|---|---|
| Broker API | Fill simulation output only | Out of kernel |
| Async I/O / websockets | Dashboard sidecar | Out of kernel |
| LLM / NLP narrative | Post-hoc Thought.text enrichment *after* structured fields are fixed | **Forbidden** in Φ4 |
| Wall-clock time | `sim/` uses bar timestamps only | No `now()` in kernel |

**Replay contract.** A run directory must contain enough state to reproduce
every Thought and Proposal:

- `manifest.json` — seed, roster hash, ledger mode, data slices
- `thought_ledger/` — append-only JSONL per agent per UTC day
- `proposal_bus/` — one JSONL per run
- `market_snapshots/` — parquet of bar features at decision horizons

If replay diverges on a second pass with the same manifest, the run is
**invalid** and cannot gate a phase.

### §1.3 Injectable Ledger (ΔInfo = config flip)

Information isolation is not a code fork — it is a **ledger adapter**
injected at runtime. ΔInfo (F17) is measured by running the same agent
twice with different adapters on the same sealed panel:

| Adapter | Read scope | Write scope | Use |
|---|---|---|---|
| `FullLedger` | All agents' Thoughts + fused journal | Own Thoughts | Tier-2 deployment candidate |
| `RedactedLedger` | Subset per agent policy (peers only) | Own Thoughts | Ablation: partial observability |
| `FrozenLedger` | Snapshot as-of `t−1` only | Own Thoughts | Look-ahead regression tests |
| `SyntheticLedger` | Injected counterfactual Thoughts | Own Thoughts | Stress tests; chemical-reaction what-ifs |

**Binding rule.** Tier assignment (doctrine §3.9) is decided by F17
using `FullLedger` vs `FrozenLedger(self)` arms — not by character feel.
Switching adapters is a **config flip** (`ledger.mode` in manifest), not
a redeploy.

Implementation target: `sim/ledger/` with a shared `LedgerReader`
protocol; agents depend on the protocol, not on filesystem layout.

### §1.4 TQS-only optimisation

**Trade Quality Score (F12)** is the sole objective for roster selection,
allocator sweeps, Population-Based Training (Φ5+), and adversarial gates
(C6).

| Metric | Reported | Scored |
|---|---|---|
| TQS (F12) | yes | **yes** — primary |
| Regime-conditional TQS (F18) | yes | **yes** — allocation |
| ΔInfo (F17) | yes | **yes** — tier assignment |
| PnL / pips / Sharpe | yes | **no** — sanity check only |
| Hit rate | yes | guardrail only (C1: ≥ baseline − 2 pp) |
| Max drawdown | yes | guardrail only (C1: ≤ baseline + 25 %) |

**Binding rule.** No configuration may be promoted because it "made more
money" on a sealed panel if TQS did not improve. PnL is logged in the
trade journal for human sanity and for broker-parity checks, never as the
optimisation target in `sim/sweeps/`.

### §1.5 Phase gates with numeric exit criteria

Phase progression is **fail-closed**. All thresholds below are evaluated
on the **sealed 2026 H1 panel** unless a row specifies otherwise.

| Gate | From → To | Numeric exit criteria (all must pass) |
|---|---|---|
| **G1** | Φ1 → Φ2 | Foundations doc reviewed; ≥ 10 papers consumed with formulas extracted (`04-quant-foundations.md` checklist) |
| **G2** | Φ2 → Φ2.5 | Architecture + roster v0 reviewed; fusion API typed objects frozen in `03-architecture-v0-sketch.md` §3 |
| **G3** | Φ2.5 → Φ3 | Data manifest verifiable for M1/M5/M15/H1/H4/D1 on EUR/GBP/USDCAD; MLflow tracker live; null-baseline suite scaffolded; standards doc reviewed |
| **G4** | Φ3 → Φ4 | **Replay fidelity:** simulator median pips/trade per rolling OOS window reproduces E004 `zone_d1_against / H4 / all` baseline **±5 %** per window (reference +11.34 pips/trade). **Regime classifier:** macro-regime labels achieve **F1 ≥ 0.75** vs hand-labelled validation set (≥ 200 bars). **Dashboard:** Streamlit v0 renders all **six panels** in `08-dashboard-spec.md` §2 against synthetic + one real replay run without exception |
| **G5** | Φ4 → Φ5 | **A1 Isagi v1 alone** clears **C1 vs Sae** (+11.34 pips/trade E004 baseline; TQS ≥ baseline × 1.10 on sealed 2026 H1). **Roster:** **10 agents implemented** in `sim/agents/` (infrastructure complete). **ΔInfo measured** for all 10. **≥ 6 agents** with **TQS > 0** in **≥ 1 regime bucket** (F18). **Information tiers frozen** per F17 (no further tier churn without new sealed run) |
| **G6** | Φ5 → Φ6 | **Squad TQS ≥ 1.1 × Sae** TQS on sealed 2026 H1 (ensemble, not single agent). **Zero Sentinel violations** (R1–R5) on replay post-Sentinel wiring |
| **G7** | Φ6 → live demo | **Rolling 12-week squad TQS ≥ Kaiser** (moving user baseline, F14). **Coverage ≥ 0.6** (≥ 60 % human coordinates overlap an agent coordinate per F13). Live demo confirms simulator fill parity within calibrated tolerance (§1.9) |

**MVP note (Φ4 v1).** The first Φ4 fusion sweep may run the **4-agent
MVP roster** (§1.10) while the 10-agent infrastructure is completed.
G5's "10 agents implemented" is an infrastructure gate; the MVP ensemble
is the first fusion experiment shipped.

**Failure handling.** Missing any criterion holds the program at the
current Φ. Partial credit is recorded in `reviews/` but does not advance
the charter phase table (`00-charter.md`).

### §1.6 Reflexive coupling budget

Agents whose proposals are **ledger-coupled** (Tier 2, or any agent whose
`intend()` reads `FullLedger`) can herd. The Allocator applies a
**correlation penalty** on fused weights:

```
w_i' = w_i × (1 − ρ_thought_resonance_i)
```

Where `ρ_thought_resonance_i` is the trailing-30-day Pearson correlation
between agent *i*'s proposal conviction series and the squad median
conviction series **conditional on both having proposed** (exclude
observation-only ticks).

| Parameter | Value | Rationale |
|---|---|---|
| Correlation window | 30 calendar days | Matches basket-risk rolling window (charter C4) |
| Floor on multiplier | 0.50 | Never zero-out a specialist entirely from one spike |
| Application point | Pre-HRP, post-chemical-reaction boost | Prevents double-counting confluence |

**Binding rule.** The reflexive budget is **always on** in Φ4+ sweeps;
turning it off is an ablation variant, not the default deployment.

### §1.7 Personalised baselines

The adversarial cohort (F14 / F16) mixes **universal gates** and
**personalised moving baselines**:

| Opponent | Type | Baseline construction |
|---|---|---|
| **Random** | Universal gate | Hour-matched random entry controls (E006 v2.1 recipe) |
| **Sae (frozen)** | Universal gate | E004 deployed cell `zone_d1_against / H4 / all`; TQS computed on identical panel |
| **Kaiser** | Personalised | Human high-conviction trades; **rolling 12-week** median TQS |
| **Loki** | Personalised | Human adaptive mid-week revisions; **rolling 12-week** median TQS |
| **Median human** | Personalised | Pooled human cohort median over same window |

**Binding rules.**

1. Φ6→live gate (G7) compares squad TQS to **Kaiser's moving 12-week
   baseline**, not a one-shot historical average.
2. Random and Sae are **universal** — every agent and ensemble must beat
   them on sealed data before Φ5 shadow live.
3. Human proposals graded under C7 (no retro-fit); proposals after H4
   close of the entry bar are discarded before any baseline update.

### §1.8 Friction-calibrated simulator

The simulator must be pessimistic enough that replay success survives
live demo. Calibration target: **June 2026 VM broker fills** on Exness
demo (1:1000, $100 equity profile).

| Friction component | Model | Default parameter |
|---|---|---|
| Spread | `ask_high − bid_low` on entry bar | From parquet bid/ask columns |
| Slippage | `k × ATR(14)` adverse | k = 0.05 (calibrate to VM fills) |
| Latency | Fixed delay before fill | **250 ms** → next tick or bar open rule per TF |
| Partial fills | Probabilistic size haircut | 20 % of orders filled at 50 % size |
| Reject rate | Independent Bernoulli | **1 %** reject (retry once, then skip) |

**Calibration protocol (Φ2.5 deliverable).**

1. Run 20+ live demo orders across EUR/GBP/USDCAD H4; log intended vs
   filled price, size, latency.
2. Adjust `k` and reject rate until sim PnL distribution is within the
   95 % band of live PnL on the same signals.
3. Freeze friction params in `sim/friction.yaml`; bump only with a new
   calibration commit.

Wide-stop agents (Isagi v1) must survive this friction model on replay
before Φ4 claims C1 clearance.

### §1.9 Dashboard as falsification interface

Each Streamlit panel exists to **falsify a specific claim**. If the
panel cannot disconfirm the claim, the claim is not admissible in
`reviews/`.

| Panel (`08-dashboard-spec.md`) | Falsification question | Disconfirming observation |
|---|---|---|
| §2.1 League table | "Does agent *i* earn its weight on TQS?" | TQS median ≤ 0 with CI excluding positive ΔInfo |
| §2.2 Thought feed | "Is the ledger free of look-ahead?" | Thought references bar index > current `decision_horizon` |
| §2.3 Chemical-reaction graph | "Do confluence boosts predict TQS uplift?" | Reacted trades ≤ non-reacted TQS with overlapping CI |
| §2.4 Scoreboard | "Does the squad beat the human + Sae cohort?" | 12-week rolling TQS below Kaiser **and** Sae |
| §2.5 Sentinel state | "Are hard rules enforced?" | Any R1–R5 violation logged without block |
| §2.6 Per-trade explainability | "Can we replay this trade from artefacts?" | Missing Thought, Proposal, or manifest join on `trade_id` |

The dashboard is **read-only** (Φ2.5–Φ5). A panel that renders green
without answering its falsification question is a **spec bug**, not a
passing grade.

### §1.10 Modularity by agent

The roster is a **config list**, not a compile-time constant.

```yaml
# sim/config/roster.yaml (illustrative)
agents:
  - isagi_yoichi
  - nagi_seishiro
  - barou_shoei
  - kunigami_rensuke
ledger:
  mode: full   # full | redacted | frozen | synthetic
allocator: tqs_hrp_v1
seed: 42
```

**Ablation = config change.**

| Experiment | Config change | Expected artefact |
|---|---|---|
| Drop agent | Remove from `agents:` list | Δ squad TQS, Δ coverage |
| Swap specialist | Replace `barou_shoei` → `chigiri_hyoma` | Pairwise ΔInfo vs Sae |
| Tier isolation | `ledger.mode: frozen` for one agent | F17 arm B |
| Allocator ablation | `allocator: equal_weight` | Sweep row in MLflow |

No ablation requires editing fusion code — only manifest + roster config.
The 10-agent canon in `05-agent-roster-v0.md` is the **maximum roster**;
subsets are first-class experiments.

---

## §2. MVP Φ4 v1 roster (four agents)

Infrastructure supports 10 agents; the **first fusion experiment**
ships four specialists chosen for diversity and Φ3 readiness:

| Agent | Role in MVP | Why in v1 |
|---|---|---|
| **A1 Isagi** | Zone / structure baseline | Wraps E004 cell; must clear C1 alone before squad fusion |
| **A6 Nagi** | Confluence-only (low frequency) | Tests chemical-reaction layer; E010 parallel validates context primitive |
| **A7 Barou** | Single-pair control (no fusion) | Apples-to-apples "lone wolf vs squad" per doctrine |
| **A10 Kunigami** | Anti-tilt / risk auxiliary | Post-loss dampening; required in Φ3 MVP scope |

Chigiri, Bachira, Rin, Reo, Yukimiya, Aoshi remain **implemented but
benched** until Φ4 v2 sweeps. See `05-agent-roster-v0.md` §1.1.

---

## §3. Experiment lifecycle (one replay run)

```
1. Pre-register manifest     reviews/<run_id>/manifest.json
2. Pin data slices           DATA_LEDGER.md cross-check
3. Inject ledger adapter     sim/ledger/*.py
4. Replay kernel             sim/run_replay.py --manifest ...
5. Score TQS + ΔInfo         sim/eval/ (F12, F17, F18)
6. Append review note        reviews/<run_id>/REVIEW.md
7. Update dashboard inputs   output/<run_id>/...
8. Gate check                compare to §1.5 table
```

**MLflow:** every run logs manifest hash, roster hash, primary TQS,
per-agent TQS vector, and gate pass/fail bitmap.

---

## §4. Live demo as OOS (Φ5+)

After G6 (Φ5→Φ6) clears on replay:

1. Shadow runner emits **simultaneous** sim + live intents.
2. Divergence log compares fill price, size, latency, reject events.
3. Weekly review: live TQS tracked but **not scored** until G7 window
   completes (12 weeks).
4. Promotion to production router requires a separate charter amendment —
   not automatic on G7 pass.

---

## §5. Cross-reference

| Topic | Authoritative doc |
|---|---|
| Mandate + C1–C7 success criteria | `00-charter.md` |
| Component wiring + Thought schema | `06-blue-lock-doctrine.md`, `03-architecture-v0-sketch.md` |
| F12 / F17 / F18 definitions | `04-quant-foundations.md` |
| Statistical hygiene | `07-research-standards.md` |
| Panel layout + verdict translation | `08-dashboard-spec.md` |
| Agent specs + 10-agent canon | `05-agent-roster-v0.md` |
| E004 baseline numbers | `docs/findings/2026-06-09_walk_forward_validation.md` |
| Pre-M001 lab close | git tag `lab-phase-1-closed` |

---

## §6. Amendment policy

Changes to numeric gates (§1.5) or friction defaults (§1.8) require:

1. Subsection appended here under **Amendments** with date + rationale.
2. Commit before any run that claims the new threshold.
3. Prior thresholds preserved in git history; no silent edits.

**Amendments:** _(none yet)_
