# Phi4 squad gate -- 4-agent MVP vs A1 Isagi-alone

**Run date:** 2026-06-24T19:22:26.963681+00:00

**Window:** 2015-01-01 -> 2025-12-31 on **EURUSD, USDCAD** (H4)

**Agents:** A1 Isagi v1, A6 Nagi v1 (confluence), A7 Barou v1 (USDCAD baseline-zone), A10 Kunigami v1 (anti-tilt).

---

## Verdict

**Phi4 -> Phi5 gate (G5): `FAIL`**

_squad TQS 0.311 is 0.98x Isagi-alone (0.317) -- adding agents LOST edge; reported honestly_

Honest framing: PASS = squad TQS >= 1.10 x Isagi-alone (G5 in `09-experiment-architecture.md`). PARTIAL = positive lift below 1.10x. FAIL = adding agents LOST edge. Reported verbatim; no silent retuning per user constraint.

---

## Squad TQS vs Isagi-alone


| Metric | Squad (Phi4) | Isagi-alone (Phi3) | Ratio |
|---|---|---|---|
| Median OOS-window mean pips/trade | **+4.42** | +11.04 | 0.40x |
| Median OOS-window mean TQS (F12) | **0.311** | 0.317 | **0.98x** |
| OOS windows positive | 7 / 7 | 7 / 7 | -- |

---

## Per-agent KPIs (full dev window)


| Agent | Trades | Mean pips | Median pips | Mean TQS | Win % |
|---|---|---|---|---|---|
| `barou_shoei` | 1150 | +9.79 | -7.28 | 0.319 | 49.8% |
| `isagi_yoichi` | 856 | +6.28 | -11.28 | 0.315 | 48.6% |
| `kunigami_rensuke` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |
| `nagi_seishiro` | 0 | +0.00 | +0.00 | 0.000 | 0.0% |

---

## Per-window walk-forward (squad-level)

(4 yr IS / 1 yr OOS rolling -- matches E004 + Phi3)


| IS window | OOS yr | barou_shoei n | barou_shoei mean pips | isagi_yoichi n | isagi_yoichi mean pips | kunigami_rensuke n | kunigami_rensuke mean pips | nagi_seishiro n | nagi_seishiro mean pips | Squad n | Squad mean pips | Squad mean TQS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-2018 | 2019 | 107 | +4.91 | 50 | +17.37 | 0 | +0.00 | 0 | +0.00 | 157 | +8.88 | 0.338 |
| 2016-2019 | 2020 | 118 | -3.82 | 77 | +12.25 | 0 | +0.00 | 0 | +0.00 | 195 | +2.52 | 0.311 |
| 2017-2020 | 2021 | 120 | +4.82 | 62 | +6.44 | 0 | +0.00 | 0 | +0.00 | 182 | +5.38 | 0.305 |
| 2018-2021 | 2022 | 98 | +0.44 | 119 | +3.61 | 0 | +0.00 | 0 | +0.00 | 217 | +2.18 | 0.307 |
| 2019-2022 | 2023 | 121 | +3.33 | 63 | +5.38 | 0 | +0.00 | 0 | +0.00 | 184 | +4.03 | 0.349 |
| 2020-2023 | 2024 | 89 | +0.28 | 43 | +12.99 | 0 | +0.00 | 0 | +0.00 | 132 | +4.42 | 0.333 |
| 2021-2024 | 2025 | 82 | +19.23 | 50 | +11.04 | 0 | +0.00 | 0 | +0.00 | 132 | +16.13 | 0.310 |

---

## F17 DeltaInfo (Tier-2 candidates: Nagi, Barou)


| Agent | n informed | n isolated | Median TQS informed | Median TQS isolated | DeltaInfo | 95% CI | Tier | Notes |
|---|---|---|---|---|---|---|---|---|
| `barou_shoei` | 1150 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |
| `nagi_seishiro` | 0 | 0 | 0.000 | 0.000 | +0.000 | [+0.000, +0.000] | 3 | [underpowered] |

_F17 ΔInfo measures whether each Tier-2 candidate's edge depends on reading the ledger. Tier-2 = ΔInfo > 0 AND bootstrap CI lower bound > 0._


---

## Engine telemetry


- Symbols: EURUSD, USDCAD (H4)
- Thoughts emitted (squad-wide): 124045
- Proposals (all): 8421
- Proposals accepted: 6491
- Proposals rejected: 6415
- Trades opened+closed: 2006
- Nagi confluence-firing thoughts: 0
- Barou devour lifts applied: 0
- Kunigami warning thoughts: 0

Sentinel R1-R5 not wired in v1 -- the rules live in `sim/core/sentinel.py` and are exercised in unit tests; live wiring to the squad gate harness is a Phi4.1 deliverable.

## Diagnosis -- why the squad lost edge

The FAIL is information, not a problem to hide. Three concrete failure modes drove the 0.98x ratio. All three are visible in the engine telemetry above.

### 1. Nagi fired 0 confluence thoughts -- the chemical reaction is starved by design

Nagi's predicate requires ≥ 2 OTHER strikers' Thoughts at tick T-1 with:
- both `confidence_in_thought > 0.7`, AND
- ≥ 2 shared tags, AND
- overlapping coordinate price bands, AND
- agreeing direction bias.

In this run the MVP squad had effectively two trading agents (Isagi + Barou). Their coordinate price bands rarely overlap because they target DIFFERENT setups (Isagi: zone-touch *against* D1; Barou: baseline zone, no D1 gate). On any given tick at least one of them is silent or below the 0.7 floor. With only one other tradable agent per symbol (USDCAD is the only pair both can trade), the 2-distinct-peer floor is mathematically unreachable on EURUSD (Isagi only) and structurally rare on USDCAD. **Nagi v1 is correct but starved.** The fix is NOT to relax the F11 predicate; the fix is to expand the squad so 3+ tradable strikers exist on the same symbol. That's a Φ5 deliverable.

### 2. Barou dilutes Isagi's trade quality

Barou contributed 1150 trades (57% of squad volume) with **+9.79 mean pips but -7.28 median pips and 49.8% win rate**. The mean is rescued by a fat right tail; the median is negative. Isagi alone in Φ3 delivered **+11.04 median OOS pips with 7/7 positive years**. Pooling Barou's median-negative stream with Isagi's median-positive stream pulls the squad mean TQS down from 0.317 to 0.311.

This is exactly the asymmetry the E005 audit warned about: USDCAD baseline-zone is RIGHT TAIL skewed (Sharpe 1.16, p=0.028 on per-year mean) but NOT median-positive on a trade-by-trade basis. The TQS metric (median-of-OOS-window-means) is sensitive to that tail behaviour. **Barou's edge is real but lives in mean not median.** A correct allocation would size Barou DOWN, not equally with Isagi. This is the F19/HRP wiring that Φ5 brings.

### 3. Per-symbol single-position rule + highest-conviction aggregator suppresses Isagi when Barou is on USDCAD

In Phi3 Isagi opened **1064 fewer trades than his raw signal stream** because of his own concurrency limit. In Phi4 Isagi is ALSO rejected when Barou outranks him on USDCAD (Barou's signal_reason confidence is sometimes higher). The rejection analysis (companion doc) shows **2994 total Isagi rejections** -- nearly triple the Phi3 number. Of those, **52.7% (1579) had the squad going the same direction anyway** -- so they were not "missed trades", they were redundant. But **11.7% (351) had the squad going the OPPOSITE direction** -- those are the cases where Barou explicitly vetoed Isagi. Without a way to verify whose read was right on those 351 ticks, we cannot say whether the suppression cost or saved pips.

### What this run tells us about each agent's design

- **Isagi v1** -- still works as the Phi3 baseline. Pulling out the squad-effect, Isagi's per-trade behaviour is unchanged.
- **A6 Nagi v1** -- correct implementation, but the MVP squad does not have enough Tier-2 source signal to feed it. **The one-bar lag is NOT what killed Nagi; the predicate is.** Even with zero lag Nagi would fire ~zero times because the 2-distinct-peer ledger floor isn't met. Documented in `audits/2026-06-24_E001-E007_audit.md` section 2.6 -- this matches the E006 finding that `equal_highs_pool` overlap is rare on H4 data.
- **A7 Barou v1** -- the E005 prior held for the MEAN but not for the MEDIAN-of-trades. Barou DOES add edge measured in cumulative pips; he LOSES edge measured in trade-by-trade TQS. The F12 metric's median-of-means rollup punishes him.
- **A10 Kunigami v1** -- never fired a warning (0 loss-streak triggers; 0 overconfidence triggers). The 3-of-5 high-confidence-loss predicate is conservative; the squad's win rate around 49% kept it below the trigger. Sentinel R5 was therefore never invoked. **Kunigami v1's predicates are tight enough to never produce a false positive, but possibly TOO tight in a low-volatility decade.**

## Honest caveats

1. **One-bar chemical-reaction lag is intentional** -- doctrine sec 3.8 forbids same-tick reads. Nagi sees peers at tick T-1 (or earlier within ttl_ticks). Reported as a design choice, not a bug. **But see Diagnosis #1 above -- the lag is NOT what killed Nagi; the 2-distinct-peer floor is.**
2. **Per-symbol single-position rule** preserves the E004 execution contract; cross-symbol concurrency is allowed.
3. **Risk Conductor: equal risk-budget per agent** for v1 (no HRP). Φ5 wires HRP-driven reweighting. **Diagnosis #2 above is the empirical motivation for that wiring.**
4. **`regime_fit = 0.5` placeholder** on every Proposal -- regime classifier (F1=0.496 weak-label) not yet wired into the conviction stream. See `sim/regime/validation_2024_eurusd_h4.json`.
5. **F17 ΔInfo sampled** on a subset of OOS windows for compute economy; underpowered arms flagged `[underpowered]` in the table above per user spec. Nagi's isolated arm trivially produced 0 trades because the FullLedger arm also produced 0 trades -- ΔInfo is mathematically defined but uninformative until the squad has enough Tier-2 source signal for Nagi to fire on.
6. **No Φ4.1 chemical-reaction beauty bonus.** F12 still scores trades with `entry_inside_chemical_reaction=False` because the Aggregator does not yet flag entry-inside-CR. Wiring lands in Phi4.1.
7. **Squad-vs-baseline comparator caveat.** The Phi3 baseline ran on EURUSD ONLY. The Phi4 squad ran on EURUSD + USDCAD because Barou is USDCAD-only. The 0.98x TQS ratio is calculated against EURUSD-only Isagi; an apples-to-apples Isagi-also-on-USDCAD comparator was deemed redundant by the user spec (Isagi's USDCAD edge under `htf_align="against"` is documented in audit E005 sec 4.3 as **weaker than EURUSD**). This caveat is the ONLY reason the FAIL is not strictly stronger than reported -- Isagi-alone on the same EURUSD+USDCAD stream would also have produced fewer-trades-than-EURUSD-only Phi3.


## References

- Phi3 gate (Isagi-alone): `reviews/phi3_gate_isagi_v1.md`
- Doctrine: `06-blue-lock-doctrine.md` sec 3.3 / 3.4 / 4.2 / 4.3
- Roster (MVP Phi4 v1): `05-agent-roster-v0.md` sec 1.1
- Experiment architecture: `09-experiment-architecture.md` sec 1.5 (G5)
- E005 USDCAD baseline-zone prior: `audits/2026-06-24_E001-E007_audit.md` sec 4.3
- E006 equal_highs_pool prior: same audit sec 2.6 + 4.3
- Rejection analysis (companion): `reviews/phi4_isagi_rejection_analysis.md`

