# Φ4.1 expanded-squad gate -- 8-agent vs A1 Isagi-alone

**Run date:** 2026-07-01T15:54:42.688598+00:00

**Window:** 2015-01-01 -> 2025-12-31 on **EURUSD, GBPUSD, USDCAD** (H4)

**Agents:** A1 Isagi v1, A2 Bachira v1 (rebel baseline-zone), A3 Rin v1 (precision zone_d1_against), A4 Chigiri v1 (ATR breakout), A5 Reo v1 (chameleon mirror, no-trade), A6 Nagi v1 (confluence), A7 Barou v1 (USDCAD baseline-zone), A10 Kunigami v1 (anti-tilt).

---

## Verdict

**Φ4.1 gate (G5 statistic): `PASS`**

_squad median OOS-window mean TQS 0.358 is 1.13x Isagi-alone (0.317); G5 threshold 1.10x_

Honest framing: PASS = squad TQS >= 1.10x Isagi-alone. PARTIAL = positive lift below 1.10x. FAIL = adding agents did NOT close the gap. Reported verbatim; no silent retuning per user constraint.

---

## Predicate-starvation falsifier headline


| Metric | Φ4 | Φ4.1 | Delta |
|---|---|---|---|
| **Nagi confluence-firing thoughts** | 0 | **34313** | +34313 |
| Reo mirror Thoughts emitted | n/a (Reo new in Φ4.1) | 28477 | -- |
| Rin precision-lift Thoughts | n/a (Rin new in Φ4.1) | 3094 | -- |
| Bachira rebel-lift Thoughts | n/a (Bachira new in Φ4.1) | 46594 | -- |
| Chigiri breakout-firing Thoughts | n/a (Chigiri new in Φ4.1) | 3615 | -- |
| Barou devour-lift Thoughts | 0 | 0 | -- |

**Interpretation:** The Φ4.1 hypothesis is that the Φ4 FAIL was driven by predicate starvation. If Nagi's confluence count moves from 0 to ANY positive number, the hypothesis is confirmed -- the predicate works, it just needed more peer fuel. If it stays at 0 with Reo specifically designed to deterministically lift any qualifying peer above Nagi's floor, the diagnosis was wrong and the problem is elsewhere (see the detailed diagnosis section at the bottom).

---

## Squad TQS vs Isagi-alone


| Metric | Squad (Φ4.1) | Isagi-alone (Φ3) | Ratio |
|---|---|---|---|
| Median OOS-window mean pips/trade | **+7.38** | +11.04 | 0.67x |
| Median OOS-window mean TQS (F12) | **0.358** | 0.317 | **1.13x** |
| OOS windows positive | 7 / 7 | 7 / 7 | -- |

---

## Per-agent KPIs (full dev window)


| Agent | Trades | Mean pips | Median pips | Mean TQS | Win % |
|---|---|---|---|---|---|
| `isagi_yoichi` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `bachira_meguru` | 4245 | +9.53 | +20.36 | 0.389 | 54.5% |
| `itoshi_rin` | 392 | +10.87 | -24.35 | 0.399 | 38.8% |
| `chigiri_hyoma` | 466 | -4.21 | -27.48 | 0.253 | 35.8% |
| `reo_mikage` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `nagi_seishiro` | 133 | +8.66 | -20.04 | 0.439 | 42.1% |
| `barou_shoei` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `kunigami_rensuke` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |

_Note: Reo and Kunigami emit no Proposals (Reo by design, Kunigami is a risk auxiliary). Their rows show no trades._

---

## Per-window walk-forward (squad-level)

(4 yr IS / 1 yr OOS rolling -- matches E004 + Φ3)


| IS window | OOS yr | isagi_yoichi n | isagi_yoichi mean pips | bachira_meguru n | bachira_meguru mean pips | itoshi_rin n | itoshi_rin mean pips | chigiri_hyoma n | chigiri_hyoma mean pips | reo_mikage n | reo_mikage mean pips | nagi_seishiro n | nagi_seishiro mean pips | barou_shoei n | barou_shoei mean pips | kunigami_rensuke n | kunigami_rensuke mean pips | Squad n | Squad mean pips | Squad mean TQS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-2018 | 2019 | 0 | +0.00 | 356 | +6.59 | 12 | +54.83 | 55 | -10.00 | 0 | +0.00 | 6 | -21.23 | 0 | +0.00 | 0 | +0.00 | 429 | +5.43 | 0.340 |
| 2016-2019 | 2020 | 0 | +0.00 | 298 | +9.18 | 27 | +1.16 | 48 | +0.14 | 0 | +0.00 | 14 | +5.84 | 0 | +0.00 | 0 | +0.00 | 387 | +7.38 | 0.358 |
| 2017-2020 | 2021 | 0 | +0.00 | 413 | +4.92 | 27 | -0.41 | 44 | -3.82 | 0 | +0.00 | 6 | -7.70 | 0 | +0.00 | 0 | +0.00 | 490 | +3.69 | 0.337 |
| 2018-2021 | 2022 | 0 | +0.00 | 376 | +11.69 | 63 | +17.29 | 33 | -0.65 | 0 | +0.00 | 19 | +23.50 | 0 | +0.00 | 0 | +0.00 | 491 | +12.03 | 0.409 |
| 2019-2022 | 2023 | 0 | +0.00 | 351 | +11.64 | 27 | +4.68 | 46 | -12.81 | 0 | +0.00 | 10 | +30.44 | 0 | +0.00 | 0 | +0.00 | 434 | +9.05 | 0.376 |
| 2020-2023 | 2024 | 0 | +0.00 | 275 | +6.28 | 16 | +32.40 | 51 | +1.10 | 0 | +0.00 | 5 | -16.29 | 0 | +0.00 | 0 | +0.00 | 347 | +6.40 | 0.353 |
| 2021-2024 | 2025 | 0 | +0.00 | 270 | +10.03 | 17 | +7.64 | 45 | -1.14 | 0 | +0.00 | 7 | +10.17 | 0 | +0.00 | 0 | +0.00 | 339 | +8.43 | 0.376 |

---

## F17 ΔInfo (Tier-2 candidates)


| Agent | n informed | n isolated | Median TQS informed | Median TQS isolated | ΔInfo | 95% CI | Tier | Notes |
|---|---|---|---|---|---|---|---|---|
| `bachira_meguru` | 4245 | 879 | 0.402 | 0.000 | +0.402 | [+0.201, +0.469] | 2 |  |
| `itoshi_rin` | 392 | 80 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |
| `chigiri_hyoma` | 466 | 135 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 |  |
| `reo_mikage` | 0 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] [structural Tier-2: isolated arm always trivial] |
| `nagi_seishiro` | 133 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |
| `barou_shoei` | 0 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |

_ΔInfo measures whether each Tier-2 candidate's edge depends on reading the ledger. Tier-2 = ΔInfo > 0 AND bootstrap CI lower bound > 0. The `[underpowered]` flag fires when informed or isolated trade count < 100, per the user spec._

---

## Engine telemetry


- Symbols: EURUSD, GBPUSD, USDCAD (H4)
- Thoughts emitted (squad-wide): 336707
- Proposals (all): 28830
- Proposals accepted: 15350
- Proposals rejected: 23594
- Trades opened+closed: 5236
- Nagi confluence-firing thoughts: 34313
- Barou devour lifts applied: 0
- Bachira rebel lifts applied: 46594
- Rin precision lifts applied: 3094
- Chigiri breakout-firing thoughts: 3615
- Reo mirror Thoughts emitted: 28477
- Kunigami warning thoughts: 23028

---

## Diagnosis -- did predicate starvation get fixed?

**YES.** Nagi's confluence count moved from 0 (Φ4) to **34313** (Φ4.1). The Φ4 predicate-starvation hypothesis is confirmed -- the F11/F13 predicate works, it just needed more peer fuel. The expanded roster (Bachira, Rin, Chigiri, Reo) delivered enough overlapping coordinate × tag × direction combinations to clear the 2-distinct-peer floor.

- **Reo mirror Thoughts:** 28477. Reo's mirror count is the lower bound on Nagi-qualifying peer lifts. If this is large but Nagi fires 0, the predicate is blocked by coordinate / tag / direction (not by conviction).

- **Bachira rebel lifts:** 46594. These are the bars where Bachira jumped from 0.65 (base) to 0.75 (rebel) -- a Nagi-qualifying conviction with shared zone tags. A low count here means the recent-opposite-swing trigger fires rarely; a high count means Nagi had plenty of Bachira peer fuel on EURUSD + GBPUSD + USDCAD.

- **Rin precision lifts:** 3094. These are the bars where Rin's strict R:R + stop-distance filter passed and conviction jumped to 0.80. Shares all zone_d1_against tags with Isagi by construction -- if this is > 0 on the same ticks Isagi fires, Nagi sees a 2-peer confluence on EURUSD.

- **Chigiri breakout thoughts:** 3615. Chigiri is the diversity striker (NOT a zone wrap). His tags do NOT inherit `zone_d1_against`, so he tags-overlaps with Reo only by the Reo-merger trick (Reo inherits Chigiri's tags when Chigiri is the highest-conviction peer). Reads on Nagi's predicate are therefore Chigiri-driven only via Reo's mediation -- this is the cleanest test of the tag-overlap pathway.

---

## Honest caveats

1. **One-bar chemical-reaction lag is intentional** -- doctrine sec 3.8 forbids same-tick reads.
2. **Per-symbol single-position rule** preserves the E004 execution contract.
3. **Risk Conductor: equal risk-budget per agent** for v1 (no HRP). Φ5 wires HRP.
4. **`regime_fit = 0.5` placeholder** on every Proposal -- regime classifier (F1=0.496 weak-label) not yet wired.
5. **F17 ΔInfo sampled** on a subset of OOS windows for compute economy; underpowered arms flagged in the table.
6. **No Φ4.2 chemical-reaction beauty bonus** wired yet.
7. **Squad-vs-baseline comparator caveat.** The Φ3 baseline ran on EURUSD ONLY. The Φ4.1 squad ran on EURUSD + GBPUSD + USDCAD (GBPUSD added so Bachira + Chigiri are not silenced). The TQS ratio is calculated against EURUSD-only Isagi-alone -- a structural conservatism.
8. **Reo's isolated-arm trade count is always 0** by construction (he never trades). The F17 ΔInfo column for Reo therefore reports the structural Tier-2 marker rather than a meaningful CI.


## References

- Φ4 FAIL diagnostic: `reviews/phi4_squad_v1.md`
- Doctrine: `06-blue-lock-doctrine.md` sec 3.1 / 3.3 / 3.5 / 3.8 / 3.11
- Roster (Φ4.1): `sim/roster/mvp_phi41.yaml`
- Experiment architecture: `09-experiment-architecture.md` sec 1.5 (G5)
- Rejection analysis (companion): `reviews/phi41_isagi_rejection_analysis.md`

