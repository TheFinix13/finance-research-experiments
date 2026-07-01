# AI Context — finance research experiments (updated 2026-07-01, post-v1-v2-reframe + Phase-M scaffolding)

Research workshop for the M001 multi-agent ensemble AND for the six single-
alpha studies gating live-agent improvements (E011-E016). Production
execution lives in `multi-pair-trading-agent`; lab experiments never
auto-change live params. Parquet cache:
`PYTHONPATH=../multi-pair-trading-agent:.` (no duplicate data).
Index: `EXPERIMENTS.md` · Rules: `PROTOCOL_DISCIPLINE.md` · M001 program:
`programs/M001_multi_agent_ensemble/` (branch `multi-agent-ensemble`).

## 2026-07-01 v1/v2 reframe — closed same day

User directive during Phase 6 completion: "each agent should operate on
equal versionings. isagi, rin, backira, kunigami should all have complete
version 1s that are all efficient in one way or the other or in their
playstyles before movign to creating a version 2." **v1 = squad-tested
checkpoint** (not initial implementation); **v2 = architectural upgrade
that trumps v1**. This retroactively reclassified 6 prior "v2" labels as
"v1 mechanic iterations" and introduced **G7 v1-checkpoint gate** as a
squad-level pre-condition on ANY v2 authorisation. Session shipped:

- **Doctrine v0.5 + roster v0.8:** preamble + §3.11.5 versioning
  discipline + §4.1a F19/F20/F21 primitives.
- **G7 pre-registered protocol** at
  `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md`.
- **6 evolution-ledger RELABEL-2026-07-01 rows** (Barou / Bachira / Rin /
  Chigiri / Reo / Kunigami).
- **F19 `lot_intent` + F20 `risk_intent` + F21 `read_workspace`** as
  first-class BaseStriker primitives with playstyle dispatch. Fixed-lot
  = 0.1 is now the "unknown-playstyle default", not a global rule.
- **All 8 v1 agents wired** with playstyle + tier (Isagi tier-1
  conservative_metavision, Bachira rebel_tight, Rin analytical_precision,
  Chigiri speed_momentum, Reo copier_hrp, Nagi confluence_only, Barou
  solo_king, Kunigami defensive).
- **Engine threads F21 workspace snapshot** into `intend()` per tick;
  Bachira consumes Isagi peer confluence (+0.05 lift). All other agents
  absorb the kwarg via `**_kwargs` (silent, but participating in
  workspace publish).
- **G7 harness scaffold** at
  `sim/scoring/run_g7_v1_checkpoint_gate.py`: C1/C5/C6 computed live,
  C2/C3/C4 stubbed PENDING full 7-window batch run + workspace-threaded
  driver.
- **Sentinel Phi4.1 physical rerun** (`--sentinel-blocks --tag physical`)
  landed 5,236 trades / 28,830 proposals / 336,707 thoughts (vs audit
  0.2922 TQS locked). Side-by-side report pending full-run completion.
- **Phase M news calendar scaffolding LANDED (2026-07-01 pm):** user
  authorised parallel scaffolding while G7 walk-forward compute job
  runs. Three new modules under `sim/regime/`
  (`news_calendar.py` -- Φ5 schema + adapter,
  `news_calendar_sources.py` -- DK/FF/FRED/TE fallback stubs,
  `news_windowing.py` -- per-agent TF windowing helper).
  `validate_real.load_news_calendar` rewritten as a 5-line proxy to
  the new adapter (spec §5.2). 3 committed parquet fixtures under
  `sim/tests/fixtures/news_calendar/` (dk_2024_sample 20 rows +
  ff_2024_sample 5 rows + dk_2024_USD 32 real events from BLS/Fed
  release schedules). 49 tests green. Live-HTTP fetch scripts
  (backfill/update/audit) deferred to next session -- adapter is
  usable today with any archive that follows the parquet layout.

**Statistical honesty flags:** no verdict retuning; all reclassifications
appended to `evolution_ledger.md` as new rows (never edits); G7 pre-reg
requires §11 amendment before any threshold change; 458 sim tests
passing + 4 slow skips (this session added 62 tests over the earlier
396 baseline: 49 news calendar + windowing + 13 workspace threading).

## 2026-07-01 research-pipeline sweep (E011-E016) — closed

| ID | Verdict | Registry |
|---|---|---|
| E011 small-stop subset expectancy | `stopped_at_stage_1` | Kills E012 |
| E012 pending-limit entry | `cancelled_dep_failed` | -- |
| E013 safety-layer contribution | `combined_alive` Δ+0.80 Sharpe; `wick_alive` Δ+0.75; BE `not_alive`; PLG `plg_earns_keep` (protocol's own label for "PLG is expensive") | `experiments/E013_.../REPORT.md` |
| E014 quality-score entry gate | `parked_low_yield` (12 % vol) | Kills E015 + E016 |
| E015 / E016 | `cancelled_dep_failed` | -- |

**Follow-up backlog:** PLG cooldown / streak-halt tuning (E017 pre-reg
required). Do NOT tweak `PostLossGuard` constants without a fresh
protocol.

## 1) What is built and working

**Lab Phase 1 (E001–E007) — closed.** Tag `lab-phase-1-closed`. E004
walk-forward 7/7 OOS (median +11.34 pips/trade) deployed. Audit:
`audits/2026-06-24_E001-E007_audit.md`.

**M001 — Φ3 PASS · Φ4 FAIL · Φ4.1 FAIL · doctrine v0.5 / roster v0.8.**

- **Φ3 v1 — A1 Isagi v1 wrapper PASS:** +11.04 pips/trade vs Sae +11.34
  (Δ −2.7 %, ±5 % band); 7/7 OOS positive.
- **Φ4 v1 — 4-agent squad FAIL @ 0.98× Isagi-alone TQS.**
- **Φ4.1 v1 — 8-agent squad FAIL @ 0.92×** (squad TQS 0.2922, Isagi 0.3175).
  Predicate starvation CONFIRMED + FIXED (Nagi 0 → 34,302 confluence-
  firing thoughts). Structural crowding-out uncovered — Isagi 0 trades,
  Barou 0 trades. `reviews/phi41_squad_v1{,_addendum,_crossstat_addendum}.md`.
- **Isagi v1→v2 arc FAIL** (2026-06-24). v1 canonical; v2 archived.
- **Regime redesign:** `vol_spike` + `news` RETIRED; live-classes-only
  macro F1 = 0.971.
- **Methodology lock:** `docs/methodology/gate_verdict_registry.md` v0.1;
  `07-research-standards.md` v0.4 §11.
- **Φ4.2 Sentinel R1–R6 wired** (audit-only in Φ4.1 replay; physical in
  Φ5 harness). Un-blocks Kunigami v2-mechanic + Φ5 Arm 4.
- **Φ5 aggregator PARTIAL VERDICT (2026-07-01):**
  - Arm 0 control 0.2922 (matches Φ4.1 exactly).
  - Arm 1 HRP 0.2941 (Δ+0.0019) — null post-hoc; needs variable lot sizes.
  - Arm 2 TQS floor 0.3109 (Δ+0.0187) — meaningful lift, misses
    Δ ≥ 0.020 by 0.0013.
  - Arms 3/4/5 REQUIRES_RESIM.
- **v1/v2 reframe (2026-07-01):** doctrine v0.5, roster v0.8, G7 gate
  pre-registered. F19/F20/F21 primitives on BaseStriker + all 8 agents.
  Engine threads workspace. Bachira consumes Isagi peer confluence.

**Architectural insight (Φ4.1 + Isagi v2 + Φ5 Arm 2 + v1/v2 reframe
converged):** the single-position-per-symbol queue with conviction-only
ranking is one lever; agent-side chemistry (F19/F20/F21) is the other.
The v1/v2 reframe formalises the mandate: prove squad chemistry via G7
before authorising any single-agent v2 arc.

Tests: **458 sim passing** + 4 slow skips (this session added 21 F21 +
48 F19/F20 + 34 wiring + 10 Bachira chemistry + 21 G7 criteria + 13
workspace threading + 49 news calendar / windowing = 196 new tests).

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Methodology | `docs/methodology/*.md` |
| M001 doctrine | `programs/M001_multi_agent_ensemble/00`–`09` (v0.5) + `README.md` |
| M001 roster | `05-agent-roster-v0.md` (v0.8, includes §1.0 v1 checkpoint status) |
| M001 sim | `programs/M001_multi_agent_ensemble/sim/{core,regime,scoring,roster,agents,dashboard,tests}/` |
| M001 core primitives | `sim/core/{lot_intent,risk_intent,reasoning_workspace}.py` (F19/F20/F21) |
| M001 news calendar | `sim/regime/{news_calendar,news_calendar_sources,news_windowing}.py` + `sim/tests/fixtures/news_calendar/*.parquet` (Phase M scaffolding) |
| M001 agents | `sim/agents/a0{1..7,10}_*.py` (playstyle + tier wired) |
| M001 harnesses | `sim/scoring/run_isagi_phi3_gate.py` · `run_phi{4,41}_squad_gate.py` · `run_phi5_aggregator_gate.py` · `run_g7_v1_checkpoint_gate.py` (new) |
| M001 aggregator arms | `sim/core/aggregator_arms/*.py` |
| M001 Sentinel | `sim/core/sentinel.py` (R1-R6) + `sim/tests/test_sentinel_wired.py` |
| M001 reviews | `reviews/phi{3,4,41,5}_*.md` + `isagi_v2_arc.md` + `evolution_ledger.md` |
| M001 G7 pre-reg | `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` |
| M001 v2 backlog | `reviews/v2_arc_backlog_resolution_{2026-06-25,round2_2026-06-30}.md` (both now "v1 mechanic iterations pending G7" per §3.11.5) |
| News calendar (DEFERRED beyond G7) | `data/news_calendar/README.md` + `specs/news_calendar_wiring{,_DECISION_TREE}.md` |
| E011-E016 protocols + reports | `experiments/E01[1-6]_.../PROTOCOL.md` + `E01{1,3,4}_.../REPORT.md` |

`PYTHONPATH=../multi-pair-trading-agent:. M001_PRODUCTION_REPO=../multi-pair-trading-agent ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**Phase 6 v1/v2 reframe — DELIVERED this session.** All 8 phases (A–H)
of the 2026-07-01 plan shipped. Squad now has F19/F20/F21 primitives
wired end-to-end; G7 harness scaffolded with C1/C5/C6 live + C2/C3/C4
stubbed. Bachira-Isagi flagship chemistry landed with 10 contract tests.
Doctrine v0.5, roster v0.8, evolution ledger updated with 6 RELABEL rows.

**Next immediate goal — G7 full-panel batch run (opex, deferred to a
dedicated compute session):**

1. **G7 batch run (highest priority for next session).** Run
   `run_g7_v1_checkpoint_gate.py` on the full 7-window Φ4.1 panel plus
   8 leave-one-out squads for criterion 2. PROTOCOL §8 stop rule #2
   allows up to 32 hours wall-clock; ship partial verdict on timeout
   per §11.2. Requires wiring the F21 workspace into
   `_drive_squad_replay` (currently only `run_replay` in
   `sim/core/engine.py` threads workspace) OR swapping G7 harness to
   use `run_replay` on the interleaved bar stream.
2. **Phi4.1 physical rerun completion + side-by-side report** (in
   flight at 15:17 -- squad run done 5,236 trades; F17 isolated arms
   in progress). When it completes, emit
   `reviews/phi41_squad_v1_physical_vs_audit.md` with the ratio and
   diagnostic.
3. **Phase 6e Φ5 re-sim path** (Arms 3/4/5 full re-sim). Plumb the 5
   arm aggregators into `_drive_squad_replay`. Runs after G7 batch.

**Backlog (needs pre-reg before touching any parameter):**

1. **PLG cooldown / streak-halt tuning** (E017 pre-reg required).
2. **E014 wider-grid amendment** (θ ∈ {20, 30, 40, 50}). Blocked by
   §Amendments discipline in `E014_.../PROTOCOL.md`.

**Deferred beyond G7 (was WIP but reprioritised 2026-07-01):**

1. **News calendar wiring.** Multi-source fallback + 2007-2026 backfill.
   README at `data/news_calendar/README.md` marked
   `DEFERRED-BEYOND-G7`.
2. **v2 agent implementations** (Barou hybrid, Bachira/Rin/Chigiri/Reo
   refinements). Reclassified as v1 mechanic iterations per §3.11.5;
   no v2 arc authorised until G7 PASS.

**Pending user-only ops (not delegatable):** hand-label ~30 regime
disagreements via `sim/regime/label_disagreements.py`; VM-side friction
calibration via `scripts/vm_calibrate_friction.py`.

**Parked (do NOT start without discussion):** A8 Yukimiya / A9 Aoshi
v1 builds (no telemetry; round-3 after G7); E009 cross-family;
`output/` reorganisation.

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5. Verdict-
comparator discipline: `07-research-standards.md` §11. v1/v2 discipline:
`06-blue-lock-doctrine.md` §3.11.5.
