# Multi-Agent Ensemble — Research & Development (M001 program root)

**Status:** `OPEN`, doctrine v0.3, started 2026-06-23, migrated to research repo 2026-06-24.
**Owner:** the1finix (research lead), assistant (R&D + implementation).
**Parent repo:** the production repo at `/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/` — only validated agents from this program graduate back into it.
**Brain-box node:** `life/finance-research/multi-pair-trading-agent.md`.

> The single-strategy, single-gate `zone_d1_against` agent is preserved as
> production. This folder is an isolated research track to design and
> validate a multi-agent ensemble system that runs in parallel. Nothing
> here changes live behaviour until a separate promotion gate is passed.

## Why this exists

Week of 2026-06-15 produced three distinct, valid analyses of the same
market — the live agent's, the assistant's quant read, and the trader's
discretionary multi-timeframe read — that disagreed on direction, timing,
sizing, and exit. Different strategies worked for different reasons. The
single-funnel "find the one true edge" approach kept eliminating those
divergent voices instead of harnessing them.

This R&D track explores the opposite frame: **a roster of specialist
agents, each owning one strategy / mindset / regime, combined at the
decision layer via late fusion.** Soccer / *Blue Lock* metaphor —
formalised in the **doctrine** (`06-blue-lock-doctrine.md`) into typed
objects (Coordinate, AgentProposal), measurable KPIs (Trade Quality
Score, Assertion / Coexistence / Devour-rate), and structural rules
(every proposal carries a hard SL; chemical reactions detected and
size-multiplied; weekly devour reweighting). The *human discretionary
trader* is the named opponent — Kaiser / Loki / Sae — and the squad
must beat them on TQS over a rolling 12-week window before earning
promotion to live capital. Many egos, one scoreboard.

## Doc index

| # | File | What's inside |
|---|---|---|
| 00 | [`00-charter.md`](00-charter.md) | Mandate, scope, success criteria, non-goals, kill conditions |
| 01 | [`01-week-2026-06-15-archive.md`](01-week-2026-06-15-archive.md) | Preserved analyses: chart breakdown, demo +$67.30 trades, live −$144.30 blowup, lessons learned |
| 02 | [`02-literature-survey-plan.md`](02-literature-survey-plan.md) | Papers, books, and topics to study; formulas to extract; what we will *not* re-derive |
| 03 | [`03-architecture-v0-sketch.md`](03-architecture-v0-sketch.md) | First architecture: specialist pool, allocator, aggregator, risk conductor, fusion |
| 04 | [`04-quant-foundations.md`](04-quant-foundations.md) | Math we will rely on: combination weights, risk parity, correlation-adjusted sizing, Kelly fraction, PBO |
| 05 | [`05-agent-roster-v0.md`](05-agent-roster-v0.md) | The 10-striker Blue Lock cast (Isagi / Bachira / Rin / Chigiri / Reo / Nagi / Barou / Yukimiya / Aoshi / Kunigami) + Ego (coach) + Kaiser/Loki/Sae (opponents). Diversity matrix + per-agent specs + build order. |
| 06 | [`06-blue-lock-doctrine.md`](06-blue-lock-doctrine.md) | **The philosophical spine.** Translates ego, weapon, metavision, coordinate, chemical reaction, devour, awakening, TQS, and the human-as-opponent into typed objects, formulas, and measurable KPIs. Read this *before* `05` to understand what the cast is instantiating. |
| 07 | [`07-research-standards.md`](07-research-standards.md) | Φ2.5 standards: nested walk-forward CV, reproducibility manifests, experiment tracking, null-baseline suite, shadow-mode-first policy, locked human-adversary submission protocol. **v0.2 §10** appends post-audit amendments (E010 parallel, agent promotion internal to M001, E008 skipped, hybrid verdict registry, v0.1 tier definitions superseded). |
| 08 | [`08-dashboard-spec.md`](08-dashboard-spec.md) | **v0.2 new.** Streamlit v0 surface: panel inventory (league table, thought feed, chemical-reaction graph, human-vs-squad scoreboard, Sentinel state, per-trade explainability), verdict-vocabulary translation (`alive`/`parked_*`/`dead` → `starter`/`sub`/`benched`/`cut`), tier display, data-plane bindings, auth (local-only), and a ~200-LoC implementation skeleton. |
| 09 | [`09-experiment-architecture.md`](09-experiment-architecture.md) | **v0.3 new.** Binding experiment spec: replay-first kernel, injectable ledger, TQS-only optimisation, numeric phase gates G1–G7, friction-calibrated simulator, falsification dashboard mapping, 4-agent Φ4 MVP roster, modular ablation via config. |
| — | [`sim/`](sim/) | **Φ2.5 scaffold (2026-06-24).** Deterministic replay simulator + Streamlit v0 dashboard + regime classifier. Sub-tree: `sim/core/` (kernel), `sim/regime/` (4-class classifier + G4 gate), `sim/scoring/` (F12 TQS · F17 ΔInfo · F18 regime KPIs · Φ3 gate harness), `sim/roster/` (`mvp_phi4.yaml` + `full_canon.yaml`), `sim/agents/` (A1 Isagi v1 wraps production `zone_d1_against`; A6/A7/A10 stubs + placeholder), `sim/dashboard/` (Streamlit, six panels), `sim/tests/` (≥ 68 tests, all passing). See [`sim/README.md`](sim/README.md). |
| — | [`reviews/`](reviews/) | **Φ3 onwards — lab evidence ledger.** Per-gate markdown reviews + per-trade JSONLs. Current: [`reviews/phi3_gate_isagi_v1.md`](reviews/phi3_gate_isagi_v1.md) (Φ3→Φ4 wrapper validation, **PASS** @ +11.04 median OOS pips/trade vs Sae +11.34, drift −2.7 %, 7/7 OOS windows positive). Every replay run that claims a gate verdict lands here. |

Each doc carries a `Status:` banner at the top: `DRAFT` / `IN REVIEW` /
`STABLE` / `SUPERSEDED-BY: …`.

## How this program relates to the rest of the world

- **The production repo** (`multi-pair-trading-agent`) is untouched by
  anything in this program until an explicit promotion checkpoint. Only
  validated agents land back there under `agent/multi/`.
- **All numerical experiments** live under `sim/`, `notebooks/`, and
  `reviews/` in this M001 folder, with seed control, evidence files,
  and review notes per the standards in
  [`07-research-standards.md`](07-research-standards.md).
- **Quant evidence** is finalised in `reviews/` once experiments are
  sealed; the production repo only receives the graduated-agent code.
- **The Brain Box mirror** (`life/finance-research/multi-pair-trading-agent.md`)
  gets a single one-line session-log entry per material decision here.

## Pivot / kill conditions

This research track is killed (or paused) if any of the following hold:

- A 4-agent ensemble cannot beat the single `zone_d1_against` agent on
  sealed 2026 H1 data on **all three** of: median PnL/trade, hit rate,
  and max drawdown.
- Capital-allocator / aggregator code adds > 200 lines without producing
  a single configuration that materially beats equal-weight voting.
- After a literature pass, no proposed fusion mechanism has been
  empirically validated in FX/futures live trading by an independent
  source (i.e. we are inventing rather than building on prior art).

If killed, we keep the architecture sketch + literature survey in this
folder as a permanent design reference and move on.
