# Phi3 gate -- A1 Isagi v1 vs Sae frozen baseline

**Run date:** 2026-06-24T18:11:11.646912+00:00

**Symbol:** EURUSD -- **Window:** 2015-01-01 -> 2025-12-31 (17723 H4 bars)

**Wrapped cell:** `agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` (`htf_align=D1`, `htf_align_mode=against`, `htf_lookback=10`, `htf_min_move_pips=60`, `target_rr=1.5`)

**Sae baseline:** `zone_d1_against / H4 / all (E004)` -- median **+11.34 pips/trade**, **7/7 OOS** (E004 walk-forward).

---

## Verdict

**Phi3 -> Phi4 gate: `PASS`**

_median OOS-window mean pips/trade +11.04 within +/- 5 % of Sae (+11.34); 7/7 OOS windows positive._

Honest framing: this is the **wrapper validation**, not a new edge. PASS means no degradation from production behaviour. PARTIAL means pip behaviour drifted outside +/- 5 % of the Sae baseline. FAIL means we lost the edge in the wrap.

---

## Apples-to-apples vs Sae (E004)

Comparator: **median across 7 OOS windows of each window's mean per-trade pip expectancy**. This is the same statistic E004's headline reports.


| Metric | A1 Isagi v1 | Sae (E004) | Delta |
|---|---|---|---|
| **Median OOS-window mean pips/trade** | **+11.04** | **+11.34** | **-2.7 %** |
| Mean OOS-window mean pips/trade | +9.87 | -- | -- |
| Median OOS-window mean TQS (F12) | 0.317 | (same trade stream by construction) | 0.000 |
| OOS windows positive | **7 / 7** | 7 / 7 | -- |

## Per-trade distribution (full dev window)

Reported for transparency; **not** the gate statistic. At target_rr=1.5 with ~ 49 % win rate, the per-trade median is structurally negative (most trades hit SL by R:R design).


| Metric | A1 Isagi v1 |
|---|---|
| Mean pips/trade | +6.28 |
| Median pips/trade | -11.28 |
| Mean TQS (F12) | 0.315 |
| Win rate | 48.6% |
| Trades | 856 |

---

## Per-window walk-forward

(4 yr IS / 1 yr OOS rolling -- matches `multi-pair-trading-agent/scripts/run_walk_forward.py`)


| IS window | OOS yr | IS n | IS mean pips | IS med pips | IS mean TQS | IS win % | OOS n | OOS mean pips | OOS med pips | OOS mean TQS | OOS win % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-2018 | 2019 | 392 | +3.29 | -14.09 | 0.304 | 47% | 50 | +17.37 | +16.81 | 0.369 | 64% |
| 2016-2019 | 2020 | 322 | +4.91 | -9.56 | 0.314 | 49% | 77 | +12.25 | -12.57 | 0.317 | 44% |
| 2017-2020 | 2021 | 314 | +9.02 | +1.69 | 0.325 | 50% | 62 | +6.44 | -10.89 | 0.317 | 48% |
| 2018-2021 | 2022 | 286 | +9.43 | -8.34 | 0.323 | 50% | 119 | +3.61 | -18.18 | 0.294 | 45% |
| 2019-2022 | 2023 | 308 | +8.58 | -9.56 | 0.317 | 48% | 63 | +5.38 | +14.69 | 0.327 | 51% |
| 2020-2023 | 2024 | 321 | +6.58 | -12.42 | 0.310 | 46% | 43 | +12.99 | +14.09 | 0.392 | 60% |
| 2021-2024 | 2025 | 287 | +6.02 | -11.50 | 0.321 | 49% | 50 | +11.04 | +1.74 | 0.308 | 50% |

---

## Engine telemetry


- Bars processed: 17723
- Thoughts emitted: 17723
- Proposals emitted: 1920
- Trades opened+closed: 856 (rejected post-open: 1064 due to open-position concurrency limit, matches E004 single-position rule)

## Honest baseline caveats

1. **No chemical-reaction beauty bonus** -- entry_inside_chemical_reaction=False for every trade. Phi3 has no F11 layer wired.
2. **Tier-3 RedactedLedger acts identically to FullLedger** for Isagi v1 because the wrapper does not read peer thoughts (production cell has no peer-reading branch).
3. **`regime_fit = 0.5` placeholder** -- the four-class classifier (09 section 1.5 G4 row) is not wired into the proposal stream yet.
4. **`cleanliness = 1.0`** -- no panic-exits / no adds / broker-stop never threatened (single-position simulator, hard SL).


## What this proves (and what it does not)

**Proves:** the BlueLockStriker `observe` / `intend` protocol can carry the E004-deployed production cell without losing its trade signature. The wrapper preserves direction, entry, stop, take-profit, and conviction byte-identically. The Phi2.5 aggregator stub accepts the AgentProposal stream without modification. The Thought Ledger journals every H4 close.
**Does not prove:** that Isagi v1 wins on TQS alone vs the squad. The G5 gate (Phi4 -> Phi5) requires the squad-ensemble TQS to beat Sae's TQS by ~ 1.10 x. This is a *necessary precondition* (wrapper fidelity) for that downstream measurement.


## References

- E004 walk-forward: `docs/findings/2026-06-09_walk_forward_validation.md`
- Doctrine: `06-blue-lock-doctrine.md` section 4.1, 3.8, 3.9
- Experiment architecture: `09-experiment-architecture.md` section 1.5 (G4)
- Production cell: `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py`
- Wrapper: `sim/agents/a01_isagi.py`

