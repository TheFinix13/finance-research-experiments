# Φ4.1 expanded-squad gate -- 8-agent vs A1 Isagi-alone

**Run date:** 2026-06-24T23:06:14.353616+00:00

**Window:** 2015-01-01 -> 2025-12-31 on **EURUSD, GBPUSD, USDCAD** (H4)

**Agents:** A1 Isagi v1, A2 Bachira v1 (rebel baseline-zone), A3 Rin v1 (precision zone_d1_against), A4 Chigiri v1 (ATR breakout), A5 Reo v1 (chameleon mirror, no-trade), A6 Nagi v1 (confluence), A7 Barou v1 (USDCAD baseline-zone), A10 Kunigami v1 (anti-tilt).

---

## Verdict

**Φ4.1 gate (G5 statistic): `FAIL`**

_squad TQS 0.292 is 0.92x Isagi-alone (0.317) -- expanding the roster did not close the gap; reported honestly_

Honest framing: PASS = squad TQS >= 1.10x Isagi-alone. PARTIAL = positive lift below 1.10x. FAIL = adding agents did NOT close the gap. Reported verbatim; no silent retuning per user constraint.

---

## Predicate-starvation falsifier headline


| Metric | Φ4 | Φ4.1 | Delta |
|---|---|---|---|
| **Nagi confluence-firing thoughts** | 0 | **34302** | +34302 |
| Reo mirror Thoughts emitted | n/a (Reo new in Φ4.1) | 28469 | -- |
| Rin precision-lift Thoughts | n/a (Rin new in Φ4.1) | 3094 | -- |
| Bachira rebel-lift Thoughts | n/a (Bachira new in Φ4.1) | 46584 | -- |
| Chigiri breakout-firing Thoughts | n/a (Chigiri new in Φ4.1) | 3615 | -- |
| Barou devour-lift Thoughts | 0 | 0 | -- |

**Interpretation:** The Φ4.1 hypothesis is that the Φ4 FAIL was driven by predicate starvation. If Nagi's confluence count moves from 0 to ANY positive number, the hypothesis is confirmed -- the predicate works, it just needed more peer fuel. If it stays at 0 with Reo specifically designed to deterministically lift any qualifying peer above Nagi's floor, the diagnosis was wrong and the problem is elsewhere (see the detailed diagnosis section at the bottom).

---

## Squad TQS vs Isagi-alone


| Metric | Squad (Φ4.1) | Isagi-alone (Φ3) | Ratio |
|---|---|---|---|
| Median OOS-window mean pips/trade | **+8.41** | +11.04 | 0.76x |
| Median OOS-window mean TQS (F12) | **0.292** | 0.317 | **0.92x** |
| OOS windows positive | 7 / 7 | 7 / 7 | -- |

---

## Per-agent KPIs (full dev window)


| Agent | Trades | Mean pips | Median pips | Mean TQS | Win % |
|---|---|---|---|---|---|
| `isagi_yoichi` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `bachira_meguru` | 2840 | +9.97 | +14.21 | 0.308 | 50.9% |
| `itoshi_rin` | 244 | +9.95 | -28.26 | 0.277 | 35.7% |
| `chigiri_hyoma` | 536 | +6.62 | -26.67 | 0.229 | 39.9% |
| `reo_mikage` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `nagi_seishiro` | 94 | +10.28 | -20.04 | 0.349 | 42.6% |
| `barou_shoei` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `kunigami_rensuke` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |

_Note: Reo and Kunigami emit no Proposals (Reo by design, Kunigami is a risk auxiliary). Their rows show no trades._

---

## Per-window walk-forward (squad-level)

(4 yr IS / 1 yr OOS rolling -- matches E004 + Φ3)


| IS window | OOS yr | isagi_yoichi n | isagi_yoichi mean pips | bachira_meguru n | bachira_meguru mean pips | itoshi_rin n | itoshi_rin mean pips | chigiri_hyoma n | chigiri_hyoma mean pips | reo_mikage n | reo_mikage mean pips | nagi_seishiro n | nagi_seishiro mean pips | barou_shoei n | barou_shoei mean pips | kunigami_rensuke n | kunigami_rensuke mean pips | Squad n | Squad mean pips | Squad mean TQS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-2018 | 2019 | 0 | +0.00 | 278 | +8.97 | 12 | +50.70 | 64 | -2.20 | 0 | +0.00 | 4 | +12.49 | 0 | +0.00 | 0 | +0.00 | 358 | +8.41 | 0.318 |
| 2016-2019 | 2020 | 0 | +0.00 | 260 | -0.94 | 21 | +21.60 | 64 | +3.65 | 0 | +0.00 | 10 | -10.70 | 0 | +0.00 | 0 | +0.00 | 355 | +0.95 | 0.292 |
| 2017-2020 | 2021 | 0 | +0.00 | 287 | +10.40 | 19 | +13.05 | 43 | +8.24 | 0 | +0.00 | 5 | -18.37 | 0 | +0.00 | 0 | +0.00 | 354 | +9.88 | 0.300 |
| 2018-2021 | 2022 | 0 | +0.00 | 270 | +5.28 | 32 | -16.30 | 52 | +8.28 | 0 | +0.00 | 13 | +55.86 | 0 | +0.00 | 0 | +0.00 | 367 | +5.62 | 0.273 |
| 2019-2022 | 2023 | 0 | +0.00 | 283 | +11.67 | 23 | -1.43 | 48 | -2.91 | 0 | +0.00 | 10 | +26.36 | 0 | +0.00 | 0 | +0.00 | 364 | +9.32 | 0.317 |
| 2020-2023 | 2024 | 0 | +0.00 | 210 | +5.58 | 11 | +13.56 | 44 | +16.45 | 0 | +0.00 | 5 | -16.29 | 0 | +0.00 | 0 | +0.00 | 270 | +7.27 | 0.287 |
| 2021-2024 | 2025 | 0 | +0.00 | 196 | +18.00 | 14 | +87.20 | 45 | +4.67 | 0 | +0.00 | 6 | -18.40 | 0 | +0.00 | 0 | +0.00 | 261 | +18.57 | 0.283 |

---

## F17 ΔInfo (Tier-2 candidates)


| Agent | n informed | n isolated | Median TQS informed | Median TQS isolated | ΔInfo | 95% CI | Tier | Notes |
|---|---|---|---|---|---|---|---|---|
| `bachira_meguru` | 2840 | 282 | 0.000 | 0.000 | +0.000 | [-0.000, +0.000] | 3 |  |
| `itoshi_rin` | 244 | 34 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |
| `chigiri_hyoma` | 536 | 48 | 0.000 | 0.000 | +0.000 | [-0.233, +0.000] | 3 | [underpowered] |
| `reo_mikage` | 0 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] [structural Tier-2: isolated arm always trivial] |
| `nagi_seishiro` | 94 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |
| `barou_shoei` | 0 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |

_ΔInfo measures whether each Tier-2 candidate's edge depends on reading the ledger. Tier-2 = ΔInfo > 0 AND bootstrap CI lower bound > 0. The `[underpowered]` flag fires when informed or isolated trade count < 100, per the user spec._

---

## Engine telemetry


- Symbols: EURUSD, GBPUSD, USDCAD (H4)
- Thoughts emitted (squad-wide): 336683
- Proposals (all): 28819
- Proposals accepted: 15345
- Proposals rejected: 25105
- Trades opened+closed: 3714
- Nagi confluence-firing thoughts: 34302
- Barou devour lifts applied: 0
- Bachira rebel lifts applied: 46584
- Rin precision lifts applied: 3094
- Chigiri breakout-firing thoughts: 3615
- Reo mirror Thoughts emitted: 28469
- Kunigami warning thoughts: 25877

---

## Diagnosis -- did predicate starvation get fixed?

**YES.** Nagi's confluence count moved from 0 (Φ4) to **34302** (Φ4.1). The Φ4 predicate-starvation hypothesis is confirmed -- the F11/F13 predicate works, it just needed more peer fuel. The expanded roster (Bachira, Rin, Chigiri, Reo) delivered enough overlapping coordinate × tag × direction combinations to clear the 2-distinct-peer floor.

- **Reo mirror Thoughts:** 28469. Reo's mirror count is the lower bound on Nagi-qualifying peer lifts. If this is large but Nagi fires 0, the predicate is blocked by coordinate / tag / direction (not by conviction).

- **Bachira rebel lifts:** 46584. These are the bars where Bachira jumped from 0.65 (base) to 0.75 (rebel) -- a Nagi-qualifying conviction with shared zone tags. A low count here means the recent-opposite-swing trigger fires rarely; a high count means Nagi had plenty of Bachira peer fuel on EURUSD + GBPUSD + USDCAD.

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

