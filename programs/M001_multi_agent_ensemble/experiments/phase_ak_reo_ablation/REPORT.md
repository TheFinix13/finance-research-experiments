# Phase AK report — Reo ablation

Executed 2026-08-04, protocol committed at `9a58e22` BEFORE the
replay. One ablation replay (2019–2023, deployed configs, Reo removed
from `roster.proposers`) against the Phase AF `is_cell_30_0.0`
baseline (engine code verified unchanged between the runs).

## Verdict (pre-registered band, judged on Nagi's n_trades)

| Metric | WITH Reo (baseline) | WITHOUT Reo (ablation) |
|---|---|---|
| Nagi n_trades | 27 | **69** (+156%) |
| Nagi win rate | 37.0% | 33.3% |
| Nagi PF | 1.267 | 1.094 |
| Nagi mean R | **+0.222** | +0.094 |
| Nagi total R | +6.0 | +6.5 |
| Squad n / PF | 1796 / 0.944 | 1805 / 0.948 |

n = 69 lands in the ≥33 band ⇒ **`reo_obstructive`** under the
pre-registered rule: Reo does not feed Nagi's confluence — he
suppresses it.

## The honest nuance (context metrics, reported as declared)

The suppression is SELECTIVE. With Reo present, Nagi fires 2.5× less
often but at 2.4× better per-trade quality (mean R +0.222 vs +0.094),
ending at essentially the same total R (+6.0 vs +6.5). Squad-level
KPIs are indistinguishable (PF 0.944 vs 0.948). So Reo's actual,
measured role is a **quality throttle on Nagi** — the exact opposite
of his design premise (Φ4.1 predicate-starvation falsifier says the
mirror should CREATE fires, not filter them).

Mechanism candidates (not adjudicated here): Nagi anchoring on Reo's
conviction-lifted mirror whose humility-shortened time window (−25%)
expires confluence earlier; and leader-selection crowding when the
mirror duplicates the leader's coordinate. Either way the design
premise is FALSIFIED — I029's "assist king" description of Reo does
not survive measurement.

## Recommendation (user decides — NEL due process)

- **Option A (recommended): keep Reo, reclassify honestly.** As a
  throttle he buys the same total R in 27 trades instead of 69 —
  fewer positions, less overtime exposure, better per-trade quality;
  in NEL HP terms roughly equal, in capital-efficiency terms better.
  Rename his function on the dashboard from "assist king" to what he
  measurably is (Nagi's selectivity filter).
- **Option B: cut him** — frees a roster slot and simplifies the
  pitch; costs nothing in total R on this evidence, but doubles
  Nagi's trade count at materially lower quality.
- **Option C: Reo v2 redesign** (trailing-K-week TQS leader tracker
  per canon) — new pre-registration; nothing in this study argues
  urgency.

Single-replay path-dependence caveat (AJ-2 discovery) rides along;
the +156% n-shift is far outside that noise band, the KPI-level
nuances are not.
