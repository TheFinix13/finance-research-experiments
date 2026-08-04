# AI Context — finance research experiments (updated 2026-08-04)

Read this first in a fresh chat. This repo is the **central research workshop**
for all hypothesis tests. The trading agent (`multi-pair-trading-agent`)
executes only what survived the agent validation chain (E001–E005); lab
experiments never auto-change live params.

**Index:** `EXPERIMENTS.md` · **Rules:** `PROTOCOL_DISCIPLINE.md` ·
**Data accounting:** `DATA_LEDGER.md`

Parquet cache: borrow via `PYTHONPATH=../multi-pair-trading-agent:.` (no
duplicate data). Two-branch discipline: `main` = v1 six-study E0xx research
registry (this file). `multi-agent-ensemble` = v2 M001 Blue-Lock squad
program (separate lane; do not commit v1 work there — see
`.cursor/rules/branch-targeting-discipline.mdc`).

## 1) What is built and working

**Agent validation chain (documented retrospectively as E001–E005):**
E001 concept ablation; E002 zone grid; E003 holdout; E004 walk-forward
(`zone_d1_against`/H4/all, `target_rr=1.5`, 7/7 OOS windows +11.34 p/trade);
E005 cross-pair sealed (GBPUSD +10.24 p=0.001, USDCAD +4.63 p=0.028).

**Lab experiments E006–E019 (all pre-registered, all landed):**
- E006 price-action confluence (5/284 alive gate-sized on EURUSD).
- E007 impulse-origin bounce dead.
- E010–E016 various zone-context / gate / re-entry / conviction studies
  (mostly parked or dead — see `EXPERIMENTS.md`).
- E017 confidence-gated cooldown → `parked`.
- E018 regime-aware fade gating → `dead`.
- E019 risk-adjusted confidence recovery → `dead` (GR-S safer but
  10× lower AnnRet → `RaC_β` collapses).

**Exit-management campaign (E020–E025, 2026-07-20):**
Shared PRE-0 counterfactual-replay harness (`faf186f`) + all five studies
on `main` at HEAD `929a585`. Full campaign result: all four upstream
mechanisms `dead` on the deployed cell; E025 joint-stack cancelled per
PROTOCOL §4a. 98/105 pre-registered arms rejected in the DEGRADATION
direction (0/105 in favour). The deployed 1.5R fixed TP + BE-at-1R +
wick_proof + PLG stack is close to optimal given the entry model:

| Study | Verdict | Mechanism | Commit |
|---|---|---|---|
| E020 MFE ratchet | dead (12/12) | Runner-choke — P(reach 1R) drops 22 pp | `7e1a3e7` |
| E021 partial at R | dead (9/9) | Give-up on 47–63 % of trades dominates tail cap | `343b512` |
| E022 structure TP snap | dead (11/12) | ΔP(TP) +3.48 pp real, per-winner-R give-up 5× larger | `dbe398c` |
| E024 near-TP stall exit | dead (72/72 cells) | Δ P(false positive) 0.63–0.91 across every arm | `93f4887` |
| E025 joint stack | cancelled_dependency_failed | 0 alive upstream | `929a585` |

**E026 low-MFE time-stop (2026-07-28, I021 stage 1):** `parked_low_yield`,
0/45 cells alive (best EURUSD P0.75_B12 ΔSharpe +0.0150 CI-LB>0 but 3/5
folds). Aged-and-still-flat cohort is a tail event (0–49 fires/symbol in
11 y; 2–5 at the user-anchor P0.50/B30). Stage 2 (I021 health meter)
cancelled per §6. **CAVEAT now on record (E026 REPORT §5): the E020–E025
deltas above used a ledger-r baseline and are confounded with path-
reconstruction drift (−0.090/−0.089/−0.145 Sharpe per symbol — same
magnitude as the reported "degradation"). "No improvement" stands;
"actively harmful" effect sizes are unsafe. E026 (and any future replay
study) uses a replayed null-arm baseline (E026 PROTOCOL §7 Amendment 1).**

**Liquidity-structure line + E010 execution (2026-07-28):** three
studies run to verdict in one session (pre-reg `cdb7a01`, harnesses
`6722012`, E010 amendments `a159ec1`):

| Study | Verdict | Headline |
|---|---|---|
| E027 valid-liquidity sweep (BOS-qualified) | STOPPED-DEAD Stage 1 (0/4) | "Valid" class reacts WORSE than invalid on every cell (diff −0.29…−0.57 ATR); the folk rule selects the weaker half |
| E028 Power-of-Three sessions | STOPPED-DEAD Stage 1 (full stop) | Narrative inverted: NY completes to untapped Asia extreme 26.2 % vs 61.2 % baseline; both mechanical arms negative at base costs; stable 7/7 years |
| E010 equal_highs_pool × M15 (executed per `fd8eb3d` pre-reg) | STOPPED Stage 2; survivors parked_weak_effect | Stage 1 7/10 alive; confirm 2022–24: selection term flips negative everywhere (−0.05…−0.66) while displacement lift stays +0.11…+0.28 (p ≤ 0.0036). Timing edge real OOS; selection edge regime-local. A6 Nagi confluence stays blocked. E010 sealed + Stage-3 reservations RELEASED (EURUSD H1/M15 2025→2026-06-09 pristine again) |

**Follow-ups E029/E030 (2026-07-28, pre-reg `36328ab`, harnesses `3e90cf4`):**

| Study | Verdict | Headline |
|---|---|---|
| E029 pool-window timing (lift-only) | **ALIVE at sealed — first alive of the line** | GBPUSD 2015–21: 8/10 cells alive (lift +0.11…+0.38 ATR, p=0.0002). Sealed EURUSD 2025→2026-05-27 (run once, now CONSUMED): `bullish_fvg_touch` +0.101 (p=0.0002, n=381) and `trendline_support_touch` +0.102 (p=0.0014, n=422) alive; `channel_bottom_touch` +0.091 under floor; 5 fib/OTE cells parked_insufficient_n (83 pool events). Claim = when-filter timing primitive, screen-grade MFE, NOT tradable expectancy |
| E030 London-continuation drift | STOPPED Stage 1 go/no-go (zero OOS cost) | WITH-London 13:30→21:00 time-exit trade: SHORT −1.38 p/trade (n=600), LONG +0.34 = noise (p=0.41, stress-negative). E028's 60 % extension is touch/path, not holdable drift. Both Po3 readings now dead |

Standing blocks: no valid-liquidity striker, no Po3 striker (either
direction). EURUSD 2025→2026-05-27 sealed slice is CONSUMED (E029) —
no longer pristine. E029's production use (timing gate on a validated
entry) needs its own study + agent validation chain.

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| PRE-0 shared harness | `programs/_shared/counterfactual_replay/{SPEC.md, replay.py, export_ledger_with_paths.py, tests/, data/*_H4_paths.jsonl}` |
| E020–E026 experiment dirs | `experiments/E02{0..6}_*/{PROTOCOL,MANIFEST,REPORT,STOP_NOTICE}.md` |
| E020–E026 program dirs | `programs/E02{0,1,2,4,6}/{run_e0xx_validation.py, results.json, tests/}` (E025 is docs-only) |
| E017 lineage | `programs/E017/{confidence_sim.py, export_trade_ledger.py, run_e017_validation.py, data/trade_ledger_EURUSD_H4.json}` |
| E018/E019 lineage | `programs/E018/`, `programs/E019/` |
| v1 harness | `scripts/{run_walk_forward_ab.py, run_e011.py, run_e014.py, analyze_e013.py}` (ported from multi-agent-ensemble in `bb00c9e`) |

Tests: E020–E024 unit tests + PRE-0 invariants all pass under
`PYTHONPATH=../multi-pair-trading-agent:.:scripts ../multi-pair-trading-agent/.venv/bin/python -m pytest programs/`.

## 3) Next immediate goal

**E031 + E032 registered 2026-08-04, awaiting pre-reg commit + push
before ANY Stage-1 run** (user must declare the target branch; recent
E-sessions were user-declared `main`). Raised by the 2026-08-04 weekly
v1 review: E031 slot-blocking (cap=2/3 + queue-replacement arms vs
reconstructed cap=1 baseline; live evidence 6/6 blocked winners across
two weeks is motivation only; MaxDD guardrail tier
`parked_risk_degraded`; Stage-0 floor ≥ 100 slot-conflict
events/symbol). E032 with-trend H4 breakout-continuation cell (12
cells, D1-aligned range-break, structure SL / 1.5R TP; priors AGAINST
on record — E004 with-mode, E030 dead, Chigiri v1 TQS 0.229; the
motivating 2026-07-28→08-03 live week is BURNT). Interaction clause:
both alive → joint slot sim required before any deployment talk.
Harnesses to build in `programs/E031/`, `programs/E032/` after the
pre-reg push. Null-arm baseline convention (E026 Amendment 1) binds
E031.

**Exit-side campaign is closed on the current cell** (E026 included).
Open user decision: whether to re-run E020–E025 effect sizes against the
null-arm baseline (E026 Amendment-1 finding) — verdict directions are
not expected to flip to alive, but the "actively harmful" claims need
re-basing before anyone cites them. Other options unchanged: (a) run
E023 (pre-registered, Phase-2 unstarted); (b) redesign the cell (fresh
`target_rr` walk-forward, new pre-registration); (c) leave deployed
mechanics alone.

**Parked (do not start without discussion):** E008 indicators; E009
cross-family; E023 post-BE structure trail (pre-registered on main but
not run — decide before touching); an E029 production-use study
(pool-window timing gate on the deployed entry — needs new ID, cost
model, agent validation chain); any new exit-side mechanism that has
not been pre-registered. E026–E030 are consumed IDs (E026 landed
2026-07-28, verdict parked_low_yield).

**Do not:** flip `LiveConfig.partial_exits`, wire `agent/live/exit_manager.py`,
or narrow the 1.5R TP without a fresh pre-registration and full agent
validation chain re-run. Honesty rules binding per `PROTOCOL_DISCIPLINE.md`.
