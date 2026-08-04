# E031 — Slot-blocking: max_open_positions relaxation / queue-replacement

Status: **PRE-REGISTERED 2026-08-04** (commit hash recorded below once
pushed). No Stage-1 outcome has been computed at registration time.

Follows `PROTOCOL_DISCIPLINE.md` in full.

---

## 0. Motivation (hypothesis-generating evidence, not proof)

Live-week resolver counterfactuals in the production repo
(`multi-pair-trading-agent/docs/reviews/2026-07-28_week_review.md` and
`2026-08-04_week_review.md`): across two consecutive live windows,
**6/6 GBPUSD signals blocked by `risk_manager: max_positions` resolved
as +1.50R winners**, in every case while the single position slot was
held by a losing carried ticket. n=6, one symbol, clustered around one
incident-adopted position — this is an anecdote with a mechanism, not
evidence. The mechanism is structural, though: with
`max_open_positions=1` per symbol, a lingering loser blocks every
re-entry, and the deployed cell's own re-entry behaviour (first fade
stops, re-entry pays — three consecutive weekly reviews) makes those
blocked re-entries systematically interesting.

Same binding constraint was independently diagnosed in M001 (Φ4.1
"structural crowding-out"; Isagi v2 arc FAIL — "the binding constraint
exposed at v1→v2 was the queue itself").

## 1. Hypothesis (operational)

- **H1:** On the deployed cells (EURUSD/GBPUSD/USDCAD H4
  `zone_d1_against`, frozen production parameters), relaxing the
  per-symbol position cap — or replacing a losing incumbent ticket
  with a fresh signal — increases pooled portfolio Sharpe relative to
  the cap=1 baseline, without materially worsening drawdown.
- **H0:** ΔSharpe ≤ 0, or ΔSharpe > 0 only with MaxDD degradation
  beyond the guardrail (§3).

Outcome metric: **ΔSharpe of daily portfolio returns (arm − baseline)**,
pooled across the 3 symbols on one shared account, annualised from
daily P&L. Baseline is the RECONSTRUCTED cap=1 replay, not the
production ledger (E026 Amendment-1 lesson: reconstruction drift
≈ −0.09…−0.15 Sharpe/symbol must cancel by construction).

## 2. Separation

- Touches the trading agent: **no** (lab replay only). Reads the
  agent's frozen detector (`agent/alphas/concepts/zone_alpha.py` +
  `_htf.py`) via `PYTHONPATH`, per the Isagi-Φ3 precedent — imported
  read-only, never modified.
- Any surviving arm is a **candidate** for the agent's own validation
  chain; the live `RiskConfig.max_open_positions` does not change from
  this study.

## 3. Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Signal stream | `zone_d1_against` frozen production params (htf_align=D1, mode=against, lookback=10, min_move=60p), H4 close cadence, conviction fixed 0.65 | Reproduces production, including signals production would drop |
| Symbols | EURUSD, GBPUSD, USDCAD H4 (risk_scale 1.0 / 0.5 / 0.5 as routed) | Deployed book |
| Sizing | Fixed 1.0% equity risk per ticket × risk_scale | Sizing is orthogonal to the slot question; conviction-band excluded to isolate the mechanism |
| Exit geometry | Zone-edge SL, fixed 1.5R TP (PRE-0 reconstruction, as E020–E026) | Matches deployed geometry |
| Portfolio ceiling | 5% aggregate open risk, enforced in ALL arms | Production posture is not on trial |
| Costs | Round-trip spread: 1.0p EURUSD, 1.5p GBPUSD, 2.0p USDCAD | Base-cost convention of E028/E030 line |
| Arm A0 (baseline) | cap=1 per symbol | Production |
| Arm A1 | cap=2 per symbol | Minimal relaxation |
| Arm A2 | cap=3 per symbol | Dose-response check |
| Arm B1 | cap=1 + replace: new signal arrives while slot full AND incumbent unrealised ≤ −0.25R → close incumbent at market, open new ticket | The live pattern: loser blocks winner |
| Arm B2 | As B1 but replacement only when new signal is same-direction as incumbent | Conservative variant (all 6 live blocks were same-direction) |

Family size: **4 arms** (A1, A2, B1, B2), pooled-portfolio primary.
Per-symbol breakdowns reported descriptively, not verdict-bearing.

## 4. Statistical pipeline

| Stage | Data | Period | Family | Test |
|---|---|---|---|---|
| 0 feasibility | slot-conflict event counts per symbol | screen period | — | ≥ 100 blocked-signal events/symbol required, else `parked_insufficient_n` |
| 1 screen | EURUSD+GBPUSD+USDCAD H4 | 2015-01-01 → 2021-12-31 | 4 | ΔSharpe > 0, moving-block bootstrap CI + BH-FDR α=0.05; 5 time-block folds, require ≥ 4/5 folds positive |
| 2 confirm | same pairs | 2022-01-01 → 2024-12-31 | survivors | per-arm α=0.05, no re-tuning |
| 3 sealed | same pairs | 2025-01-01 → 2026-07-25, run ONCE | survivors | report only |

Guardrail (verdict-bearing): an arm with ΔSharpe alive but relative
MaxDD worsening > 20% vs A0, or > 1.5× the baseline count of daily-DD
(−3%) days, lands `parked_risk_degraded`, not `alive`.

Data-ledger note: EURUSD H4 2015–2021 is on its 8th registered use
(overuse acknowledged; hypothesis is orthogonal — portfolio slot
mechanics, not a new entry/exit signal on the same bars). H4 2025+
sealed slices previously touched only by E005 (documented prior use).

## 5. Stop rules

- Stage 0: any symbol with < 100 slot-conflict events in screen →
  that symbol drops to descriptive-only; if ALL symbols fail → STOP
  (`parked_insufficient_n`), because the live anecdote then has no
  base-rate to generalise from.
- Stage 1: 0/4 arms alive → STOP, file STOP_NOTICE, live evidence
  recorded as anecdote-not-confirmed.
- Any alive arm at sealed → hand to agent validation chain as a
  candidate; joint-interaction study with E032 required BEFORE any
  deployment decision if E032 also produces a live cell (two
  strategies sharing slots changes the contention rate).

## 6. Amendments

(none at registration)

---

**Pre-registration commit:** `c838b28` (pushed 2026-08-04, before any
Stage-1 computation)
