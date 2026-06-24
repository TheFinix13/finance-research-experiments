# AI Context — finance research experiments (updated 2026-06-24, post-Φ4 squad gate)

Read this first in a fresh chat. This repo is the **central research workshop**.
Production execution lives in `multi-pair-trading-agent`; lab experiments never
auto-change live params.

**Index:** `EXPERIMENTS.md` · **Rules:** `PROTOCOL_DISCIPLINE.md` ·
**M001 program:** `programs/M001_multi_agent_ensemble/` (branch `multi-agent-ensemble`)

Parquet cache: `PYTHONPATH=../multi-pair-trading-agent:.` (no duplicate data).

## 1) What is built and working

### Lab Phase 1 (E001–E007) — closed

- Tag **`lab-phase-1-closed`** marks pre-M001 lab state (do not recreate).
- **E004** walk-forward: 7/7 OOS, median +11.34 pips/trade → deployed cell.
  Promoted: `docs/findings/2026-06-09_walk_forward_validation.md`.
- **E005** cross-pair: GBPUSD/USDCAD replicate; AUD/NZD excluded.
  Promoted: `docs/findings/2026-06-10_cross_pair_replication.md`.
- **E006** price-action: 5/284 alive; hour-matched controls (v2.1).
  Exploratory `equal_highs_pool` → `docs/findings/2026-06-12_equal_highs_pool_context.md`.
- **E007** impulse bounce: 0/12 alive; clean negative at Stage 1.
- Methodology promoted: `docs/methodology/` (hour_matched_controls,
  verdict_registry, exploratory_stage2, amendments).
- Audit: `audits/2026-06-24_E001-E007_audit.md`.

### M001 multi-agent ensemble (Φ3 wrapper PASS, Φ4 squad gate FAIL)

- **Doctrine v0.3 + Φ2.5 scaffold landed** (pre-Φ3 commits): deterministic
  kernel, four-impl ledger (Full/Redacted/Frozen/Synthetic), regime
  classifier (synthetic F1≈0.999; real-data macro F1=0.496 vs heuristic
  weak labels, 30 disagreements pending hand-label), TQS+ΔInfo+regime-KPI
  scoring, 4-agent MVP roster YAML + 10-agent canon YAML, Streamlit v0
  dashboard (six panels). Friction calibration machinery wired; defaults
  conservative (VM run pending). Details in
  `programs/M001_multi_agent_ensemble/sim/README.md`.
- **Φ3 v1 (2026-06-24) — A1 Isagi v1 wrapper PASS:** wraps production
  `SupplyDemandAlpha` at locked E004 params via cross-repo import
  (`sim/_cross_repo.py`). EURUSD H4 2015-2025: **verdict `PASS`** —
  median OOS-window mean **+11.04 pips/trade** vs Sae +11.34 (drift
  −2.7%); **7/7 OOS windows positive**; mean TQS 0.317. Report:
  `reviews/phi3_gate_isagi_v1.md`.
- **Φ4 v1 (2026-06-24) — 4-agent squad gate FAIL @ 0.98x Isagi-alone TQS.**
  Three new strikers shipped: A6 Nagi v1 (confluence-only, F11
  independent-OR lift), A7 Barou v1 (USDCAD baseline-zone + devour
  mechanic +0.10 lift), A10 Kunigami v1 (anti-tilt observer). Engine
  refactored to explicit two-phase tick order (observe-all then
  intend-all) with deterministic lexicographic agent ordering. Harness
  `sim/scoring/run_phi4_squad_gate.py` ran 2015–2025 EURUSD + USDCAD H4
  (124 045 thoughts, 8 421 proposals, 2 006 trades). **Verdict `FAIL`**:
  squad median OOS TQS **0.311** vs Isagi-alone **0.317** = **0.98x**.
  Per-agent: Isagi 856 trades / +6.28 mean pips; Barou 1150 trades /
  +9.79 mean / −7.28 median; Nagi 0 trades / 0 confluence thoughts
  (predicate-starved, NOT one-bar-lag); Kunigami 0 trades / 0 warnings.
  Reports: `reviews/phi4_squad_v1.md` (verdict + Diagnosis +
  honest caveats) + `reviews/phi4_isagi_rejection_analysis.md`
  (2994 Isagi rejections bucketed: same=1579, opposite=351, silent=1064,
  elsewhere=0). **195 tests passing + 3 skipped** (70 lab + 125 sim;
  +41 new Phi4 tests).
- Branch: **`multi-agent-ensemble`** only for M001.

### Planned

- **E010** Stage-2b `equal_highs_pool` — skeleton pre-reg at
  `experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md`; parallel with M001.
- E008 skipped per M001 standards §10.3; E009 cross-family parked.

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Findings | `docs/findings/2026-06-09_*.md`, `2026-06-10_*.md`, `2026-06-12_*.md` |
| Methodology | `docs/methodology/*.md` |
| Audits | `audits/README.md`, `audits/2026-06-24_E001-E007_audit.md` |
| M001 doctrine | `programs/M001_multi_agent_ensemble/00`–`09` + `README.md` |
| M001 Φ2.5 sim | `programs/M001_multi_agent_ensemble/sim/{core,regime,scoring,roster,agents,dashboard,tests}/` + `sim/README.md` + `sim/regime/README.md` (Φ3-prep) |
| M001 Φ3-prep artefacts | `sim/regime/validate_real.py`, `sim/regime/validation_2024_eurusd_h4.json`, `sim/regime/disagreements_for_review.csv`, `sim/tests/test_friction_calibration.py` |
| M001 Φ3 v1 artefacts | `sim/_cross_repo.py`, `sim/agents/a01_isagi.py` (A1IsagiV1 wrapper), `sim/scoring/run_isagi_phi3_gate.py`, `sim/tests/test_a01_isagi_wrap.py`, `sim/tests/test_phi3_gate.py`, `programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1.md` (+ `*_trades.jsonl`) |
| M001 Φ4 v1 artefacts | `sim/agents/a06_nagi.py` (A6NagiV1 confluence), `sim/agents/a07_barou.py` (A7BarouV1 USDCAD baseline-zone + devour), `sim/agents/a10_kunigami.py` (A10KunigamiV1 anti-tilt), `sim/scoring/run_phi4_squad_gate.py` (squad gate + F17 isolated arms + rejection analysis), `sim/tests/test_a06_nagi_wrap.py`, `sim/tests/test_a07_barou_wrap.py`, `sim/tests/test_a10_kunigami_wrap.py`, `sim/tests/test_phi4_engine.py`, `sim/tests/test_phi4_gate.py`, `programs/M001_multi_agent_ensemble/reviews/phi4_squad_v1.md` (+ `*_trades.jsonl`, `*_proposals_all.jsonl`, `*_rejected_proposals.jsonl`), `reviews/phi4_isagi_rejection_analysis.md` |
| E006/E007 code | `conflab/`, `scripts/run_stage1.py`, `scripts/test_b/` |
| Outputs | `output/` (legacy paths; reorganise deferred — needs git mv + MANIFEST sync) |

Tests: **195** passing + **3 skipped** (70 pre-existing lab + 125 sim).
`PYTHONPATH=../multi-pair-trading-agent:. M001_PRODUCTION_REPO=../multi-pair-trading-agent ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**M001 Φ4 v1 SHIPPED with `FAIL` verdict (0.98x Isagi-alone TQS) —
reported honestly per user constraint, no silent retuning.**

The FAIL is information, not a problem to hide. Three concrete failure
modes are documented in `reviews/phi4_squad_v1.md` Diagnosis section:
(1) **Nagi predicate-starved** — 2-distinct-peer floor unreachable on
EURUSD (Isagi-only) and structurally rare on USDCAD (Isagi + Barou
rarely overlap on coordinate price bands because they target different
setups). The fix is NOT to relax F11; it's to expand the squad. (2)
**Barou median-dilutes** — mean +9.79 pips but median −7.28 pips on
1150 USDCAD trades; pooling that median-negative stream with Isagi's
median-positive stream drags the squad TQS down. HRP allocation is the
empirical remedy (Φ5 deliverable). (3) **Concurrency + highest-
conviction-wins rule triple Isagi's rejection count** (2994 vs Phi3's
1064); 52.7% of those rejections had the squad going same-direction
anyway, so they were redundant not missed.

**Next steps (in priority order):**
1. **Φ4.1: Expand the squad** so Nagi's predicate is reachable. Add at
   least one more H4-trading agent (A4 Chigiri H4-adapted, or A3 Rin)
   so EURUSD has ≥ 2 high-conviction tradable strikers per tick.
2. **Φ4.1: Wire Sentinel R5 dampener** to read Kunigami's warning
   Thoughts (currently emitted but unconsumed by the harness).
3. **Φ5 prep:** stop equal-weight risk budgeting; wire HRP allocator
   so right-tail-skewed agents (Barou) get sized DOWN automatically.
4. **Φ3 carryovers:** replace synthetic regime bars with real parquet,
   hand-label 30 disagreement bars in
   `sim/regime/disagreements_for_review.csv` and extend to ≥ 200 for
   the G4 F1 ≥ 0.75 gate. On the VM, run
   `calibrate_against_fills(symbol, ...)` for EURUSD/GBPUSD/USDCAD.
5. **E010:** finalise locked params in PROTOCOL before Stage 1.

Parked (do NOT start without discussion): Isagi v2 expansion (separate
phase per user direction); chemical-reaction beauty bonus in F12
(deferred to Φ4.1 once Nagi actually fires); `output/` reorganisation;
E009 cross-family.

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5.
