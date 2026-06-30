# AI Context — finance research experiments (updated 2026-06-30, post-Φ4.1 + round-2 doctrine resolutions)

Research workshop for the M001 multi-agent ensemble. Production execution lives in
`multi-pair-trading-agent`; lab experiments never auto-change live params.
Parquet cache: `PYTHONPATH=../multi-pair-trading-agent:.` (no duplicate data).
Index: `EXPERIMENTS.md` · Rules: `PROTOCOL_DISCIPLINE.md` · M001 program:
`programs/M001_multi_agent_ensemble/` (branch `multi-agent-ensemble`).

## 1) What is built and working

**Lab Phase 1 (E001–E007) — closed.** Tag `lab-phase-1-closed`. E004 walk-forward
7/7 OOS (median +11.34 pips/trade) deployed. E005 cross-pair (GBPUSD / USDCAD
replicate). E006 5/284 alive. E007 0/12 alive. Audit:
`audits/2026-06-24_E001-E007_audit.md`.

**M001 — Φ3 PASS · Φ4 FAIL · Φ4.1 FAIL · doctrine v0.4 / roster v0.7.**

- **Φ3 v1 — A1 Isagi v1 wrapper PASS:** +11.04 pips/trade vs Sae +11.34
  (Δ −2.7 %, inside ±5 %); 7/7 OOS positive. `reviews/phi3_gate_isagi_v1.md`.
- **Φ4 v1 — 4-agent squad FAIL @ 0.98× Isagi-alone TQS.** Nagi 0 confluence
  thoughts (predicate-starved on MVP). `reviews/phi4_squad_v1.md`.
- **Φ4.1 v1 — 8-agent expanded squad FAIL @ 0.92×** (squad TQS 0.2922,
  Isagi 0.3175). Predicate starvation **confirmed + fixed** (Nagi 0 → 34,302
  confluence-firing thoughts; TQS 0.349 highest in squad). New failure mode:
  **structural crowding-out** — Isagi 0 trades, Barou 0 trades, slot-
  cannibalised by Bachira's `+0.10` rebel-lift. Per-agent: Bachira 2,840
  trades / TQS 0.308; Rin 244 / 0.277; Chigiri 536 / 0.229; Reo 0 by design /
  28,469 mirror Thoughts; Kunigami 0 / 25,877 warning Thoughts (R5 not wired).
  `reviews/phi41_squad_v1{,_addendum,_crossstat_addendum}.md`.
- **Isagi v1→v2 arc FAIL** (2026-06-24). v1 canonical; v2 archived.
  `reviews/isagi_v2_arc.md`.
- **Regime redesign:** `vol_spike` + `news` RETIRED on structural grounds;
  live-classes-only macro F1 = 0.971. `reviews/regime_redesign_2026-06-24.md`.
- **Methodology lock:** `docs/methodology/gate_verdict_registry.md` v0.1 binds
  per-gate locked statistic; `07-research-standards.md` v0.4 §11.
- **v2 backlog round-1 (2026-06-25):** Nagi RETIRED · Barou REDESIGN-hybrid-A+B
  (user decision 2026-06-30: closed-loss replay USDCAD + symbol expansion to
  EURUSD/GBPUSD/USDCAD) · Kunigami DEFERRED pending Sentinel R1–R5.
  `reviews/v2_arc_backlog_resolution_2026-06-25.md`.
- **v2 backlog round-2 (2026-06-30):** Bachira REFINE-to-peer-silence · Rin
  REFINE-regime+peer-disagreement · Chigiri REFINE-multi-TF-ADX+ATR-percentile ·
  Reo ADVANCE-coupled-to-Φ5-multi-position.
  `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md`.

**Architectural insight (Φ4.1 + Isagi v2 converged):** the **single-position-
per-symbol queue with conviction-only ranking** is the binding constraint —
not roster size, not the F11 predicate. Φ5 lever is the aggregator.

**Pre-registered, awaiting implementation:** Φ5 aggregator selection
(`experiments/phi5_aggregator/PROTOCOL.md` + `HRP_NOTES.md`); news calendar
wiring (`specs/news_calendar_wiring{,_DECISION_TREE}.md`); Sentinel R1–R5
(Φ4.2 mini-sprint, un-blocks Kunigami v2 + Φ5 Arm 4); E010 Stage-2b
`equal_highs_pool` (`experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md`).

Tests: **358 sim passing** + 3 slow skips.

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Methodology | `docs/methodology/*.md` (incl. `gate_verdict_registry.md` v0.1) |
| Audits | `audits/2026-06-24_E001-E007_audit.md` |
| M001 doctrine | `programs/M001_multi_agent_ensemble/00`–`09` + `README.md` (v0.4 / v0.7) |
| M001 sim | `programs/M001_multi_agent_ensemble/sim/{core,regime,scoring,roster,agents,dashboard,tests}/` |
| M001 agents | `sim/agents/a0{1..7,10}_*.py` (Isagi v1 + v2 archived; Bachira/Rin/Chigiri/Reo/Nagi/Barou/Kunigami v1) |
| M001 harnesses | `sim/scoring/run_isagi_phi3_gate.py` + `run_phi{4,41}_squad_gate.py` |
| M001 reviews | `reviews/phi{3,4,41}_*.md` + `isagi_v2_arc.md` + `evolution_ledger.md` |
| M001 v2 backlog | `reviews/v2_arc_backlog_resolution_2026-06-25.md` (round-1) + `_round2_2026-06-30.md` (round-2) |
| M001 pre-registered | `experiments/phi5_aggregator/{PROTOCOL,HRP_NOTES}.md` + `specs/news_calendar_wiring{,_DECISION_TREE}.md` |
| E006 / E007 code | `conflab/`, `scripts/run_stage1.py`, `scripts/test_b/` |

`PYTHONPATH=../multi-pair-trading-agent:. M001_PRODUCTION_REPO=../multi-pair-trading-agent ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

Multi-phase 2026-06-30 implementation sprint (kickoff doc + four prep docs are
canonical state).

1. **Φ4.2 — Sentinel R1–R5 wiring.** Module `sim/core/sentinel/` (R1 min-lot,
   R2 discrete sizing, R3 pass bias, R4 concentration cap, R5 loss-streak
   50 %-risk-scale dampener). Wired into Φ4.1 harness + Φ5 successor harness.
   Φ5 PROTOCOL §6 stop rule #3 retired via §11 amendment (Arm 4 ungated).
   Un-blocks Kunigami v2 pre-condition #1.
2. **News calendar wiring (D).** Dukascopy primary + multi-source fallback
   (FF + DailyFX + MyFXBook + FRED). 2007-2026 backfill. Parametrised per-
   agent pre/post windows. Script + manifest committed; data commit deferred
   to milestone. 8 unit tests + 1 integration test per spec §7.
3. **Φ5 aggregator selection (B).** Arms 1–5 (HRP / TQS-floor / same-direction
   merge / multi-position / combined). Arm 1 first; 2/3/4 parallel; 5 last.
   Run all via `run_phi5_aggregator_gate.py`. Verdict report + cross-stat
   robustness table.
4. **v2 agent implementations** — Barou hybrid A+B; Bachira / Rin / Chigiri
   refines; Reo HRP + second-position (mechanic 2 Φ5-gated). Sequenced AFTER
   Φ5 verdict; some may be obviated by aggregator-side fixes.

**Pending user-only ops (not delegatable):** hand-label ~30 regime
disagreements via `sim/regime/label_disagreements.py` Streamlit; VM-side
friction calibration via `scripts/vm_calibrate_friction.py`.

**Parked (do NOT start without discussion):** A8 Yukimiya / A9 Aoshi v1 builds
(no Φ4.1 telemetry; round-3 after build); E009 cross-family; `output/`
reorganisation.

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5. Verdict-
comparator discipline: `07-research-standards.md` §11.
