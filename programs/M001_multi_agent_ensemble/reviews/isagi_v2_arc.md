# Isagi v1 vs v2 evolution-arc head-to-head

**Run date:** 2026-06-24T19:57:22.088672+00:00

**Symbol:** EURUSD -- **Window:** 2015-01-01 -> 2025-12-31 (17723 H4 bars)

**v1:** `sim/agents/a01_isagi.py` -- wraps `SupplyDemandAlpha` at locked E004 params (`htf_align=D1`, `htf_align_mode=against`, `htf_lookback=10`, `htf_min_move_pips=60`, `target_rr=1.5`).

**v2:** `sim/agents/a01_isagi_v2.py` -- v1 zone weapon byte-preserved + new `liquidity_sweep` weapon (sweep_max_age_bars=6, stop_atr_mult=0.5, target_rr=1.5, sweep_conviction=0.55; HTF gate: D1 bias must AGREE with sweep reaction).

**Defeat trigger (the §3.11.2 step 1 evidence):** Φ4 squad-gate rejection analysis -- **1579 of 2994 (52.7 %) of v1's rejections were SAME-DIRECTION** with the rest of the squad. v1's `zone_d1_against` vocabulary leaves the rest of the dimensional space unused. v2 adds the liquidity-sweep vocabulary to claim ticks v1 cannot read at all. Full defeat note: `reviews/isagi_yoichi_v1_defeat.md`.

---

## Verdict

**Arc: `FAIL`**

_v2 median OOS TQS 0.240 < v1 0.317 -- vocabulary expansion has net-negative TQS effect._

Honest framing: **CLOSE** means v2 dominates v1 by the §3.11.2 step 6 contract -- v2 takes all v1 trades, ≥4-of-7 OOS windows carry sweep trades, median OOS TQS not below v1, no single window worse by > 5%. **FAIL** means v2 should be archived; v1 stays canonical (the module on disk is preserved for the audit trail per §3.11.2 step 3).

---

## Top-line comparison

Comparator -- **median across OOS windows of each window's mean TQS (F12)**. This is the same statistic the Phi3 gate locked.


| Metric | v1 | v2 | Delta |
|---|---|---|---|
| **Median OOS-window mean TQS** | **0.317** | **0.240** | **-0.078** |
| Median OOS-window mean pips/trade | +11.04 | +2.90 | -8.14 |
| OOS windows positive (pips) | 7 / 7 | 4 / 7 | -- |
| Total trades | 856 | 1089 | +233 |
| v2 zone-branch trades | -- | 311 | -- |
| v2 sweep-branch trades (NEW vocab) | -- | 778 | -- |
| Sweep-trade window coverage | -- | 7 / 7 | -- |

_v1 reference (Phi3 gate): **0.317** median OOS-window mean TQS; this run reproduces it for the arc comparator._

---

## Per-window walk-forward (v1 vs v2 OOS)

(4 yr IS / 1 yr OOS rolling -- matches `reviews/phi3_gate_isagi_v1.md`)


| IS window | OOS yr | v1 n | v1 mean pips | v1 mean TQS | v2 n | v2 mean pips | v2 mean TQS | v2 zone | v2 sweep | ΔPips | ΔTQS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2015-2018 | 2019 | 50 | +17.37 | 0.369 | 113 | -12.30 | 0.190 | 27 | 86 | -29.67 | -0.179 |
| 2016-2019 | 2020 | 77 | +12.25 | 0.317 | 117 | +5.07 | 0.265 | 34 | 83 | -7.17 | -0.052 |
| 2017-2020 | 2021 | 62 | +6.44 | 0.317 | 98 | -3.14 | 0.234 | 25 | 73 | -9.58 | -0.083 |
| 2018-2021 | 2022 | 119 | +3.61 | 0.294 | 101 | +9.39 | 0.286 | 45 | 56 | +5.78 | -0.007 |
| 2019-2022 | 2023 | 63 | +5.38 | 0.327 | 90 | +2.90 | 0.245 | 11 | 79 | -2.48 | -0.082 |
| 2020-2023 | 2024 | 43 | +12.99 | 0.392 | 114 | +6.70 | 0.240 | 20 | 94 | -6.28 | -0.152 |
| 2021-2024 | 2025 | 50 | +11.04 | 0.308 | 133 | -1.79 | 0.214 | 24 | 109 | -12.83 | -0.093 |

---

## Per-weapon breakdown (v2 zone vs sweep, standalone quality)

Isolating each weapon's per-trade quality answers the diagnostic question 'is the FAIL driven by negative sweep-weapon edge, or by queue collision stealing slots from zone trades?'


| Weapon (v2) | Trades | Mean pips | Median pips | Mean TQS | Win % |
|---|---|---|---|---|---|
| zone | 311 | +3.44 | -12.62 | 0.314 | 46.9% |
| sweep | 778 | -2.91 | -23.59 | 0.207 | 36.1% |
| _v1 zone (reference)_ | 856 | +6.28 | -11.28 | 0.315 | 48.6% |

**Diagnostic:** the sweep weapon's standalone mean TQS (0.207) is **below** v2's preserved zone weapon (0.314). The FAIL is dominated by **sweep-weapon edge being weaker than zone-weapon edge** on this panel -- adding sweep proposals to the single-position queue *cannibalises* the high-TQS zone slots with low-TQS sweep slots. A future v2 attempt should either (a) use the sweep weapon as a *zone confluence filter* rather than an independent entry, (b) tighten the sweep HTF gate (more conservative min_move_pips or longer lookback) so it fires only on highest-conviction sweeps, or (c) move v2 to a multi-position simulator so the queue collision is removed.

---

## Behaviour delta (v2's NEW vocabulary in plain English)

v2 fired **778 liquidity-sweep trades** across the eleven-year dev window that v1 cannot emit at all (v1's `zone_d1_against` codepath has no sweep branch). Of those, 7 of the seven OOS windows carry at least one sweep trade -- PASSES the 4-of-7 coverage floor.

What v2 catches that v1 misses, concretely: when price wicks above a tagged equal-highs / swing-high / PDH cluster and closes back below (a buyside sweep) -- AND the D1 trend is ALREADY pointing down -- v2 takes a SHORT at the H4 close. Mirror geometry for sellside sweeps and LONG entries. v1 ignores these setups entirely.

v2's zone-branch trade count is **311**, vs v1's **856** total trades. If the zone branch is preserved byte-equivalently the two numbers should match; any positive gap on v2's side is the harness opening a trade on a sweep that pre-empts a zone touch in the same per-symbol single-position queue.

---

## Rejection-rate proxy

Single-agent runs do not have a squad to be rejected by, so the directly-comparable Phi4 rejection bucket count (2994 / 1579 same-direction) is **not** the right comparator here. The closest single-agent proxy is the count of proposals the production fill model produced but the per-symbol single-position rule blocked.


| Agent | Proposals | Trades | Blocked-by-concurrency | Same-direction-as-open-trade % |
|---|---|---|---|---|
| v1 | 1920 | 856 | 1064 | 95.6 % |
| v2 | 7142 | 1089 | 6053 | 68.9 % |

**Did the rejection rate drop?** v1 blocked-by-concurrency: 1064. v2 blocked-by-concurrency: 6053. v2 has MORE rejections (expected -- the sweep weapon adds proposals on bars where a zone trade is already open, which then get rejected). The Phi4 squad-gate's **same-direction redundancy** number cannot be recomputed here because there is no squad; the closest single-agent proxy is the same-direction-as-open-trade column above, which only describes self-self interaction.

---

## Recommendation

**Keep v1 as the canonical Isagi.** v2 is archived in `sim/agents/a01_isagi_v2.py` for the audit trail; the module is NOT deleted (§3.11.2 step 3 + `07-research-standards.md` §3 retention rule). Append a FAIL row to `reviews/evolution_ledger.md` quoting the verdict reason above. The defeat trigger (1579 / 52.7 % same-direction rejections) is preserved; a future arc may revisit with a different evolution hypothesis (e.g. FVG primitive, OB primitive, H1 cadence move alone).

---

## Honest caveats

1. **Single-agent evaluation only.** This is NOT a squad gate. The Phi4 squad-gate same-direction rejection count cannot be directly reproduced here; the §3.11.2 contract is about *agent* evolution, not roster fusion.
2. **Same panel as Phi3.** EURUSD H4 2015-2025, 4 yr IS / 1 yr OOS rolling. v2's gate is evaluated on the exact same data v1's Phi3 PASS verdict used.
3. **HTF gate inversion is intentional.** v1's zone weapon wants D1 to OPPOSE the trade (fade); v2's sweep weapon wants D1 to AGREE with the trade (ride the reaction). This is the canon 'metavision evolved' framing -- sweeps are confirmations of the macro trend, not fades against it. Documented in the v2 module docstring.
4. **No look-ahead in the sweep detector.** The production `detect_liquidity_sweeps` runs in its default `require_reversal_confirmation=False` mode, which is fully causal per the module's docstring.
5. **The Phi3 gate baseline TQS (0.317) is the comparator** -- this run reproduces it for v1 on the same panel; any drift is noise from the harness, not a re-evaluation of E004.

---

## References

- Defeat note: `reviews/isagi_yoichi_v1_defeat.md`
- v1 Phi3 PASS: `reviews/phi3_gate_isagi_v1.md`
- Squad-gate evidence chain: `reviews/phi4_squad_v1.md`, `reviews/phi4_isagi_rejection_analysis.md`
- Doctrine contract: `06-blue-lock-doctrine.md` §3.11.2
- Roster row: `05-agent-roster-v0.md` §3.1
- v2 module: `sim/agents/a01_isagi_v2.py`
- v2 tests: `sim/tests/test_a01_isagi_v2.py`
- Production primitives: `agent.detectors.liquidity_sweep.detect_liquidity_sweeps`, `agent.alphas.concepts._htf.htf_bias_at`

