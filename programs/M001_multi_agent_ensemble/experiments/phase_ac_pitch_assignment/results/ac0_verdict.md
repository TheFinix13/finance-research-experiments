# Phase AC — AC.0 verdict (pair-character regression)

- **Verdict:** **FAIL**
- **Fired:** 2026-07-20T18:20:19.427818+00:00
- **Training window (pair-character features):** 2015-01-01 → 2019-01-01
- **OOS windows (banked telemetry):** 2019-01-01 → 2026-01-01 (K=7)
- **Banked telemetry source:** `reviews/g7_replay_cache_g7retry1-phi41/trades.jsonl`
- **Feature-vector n:** 5 pairs (EURUSD, GBPUSD, USDCAD, AUDUSD, NZDUSD). USDJPY / USDCHF blocked pending cache pull (§4, §10).
- **Features:** d1_ac1, h4_atr_percentile, max_session_impulse, d1_chop_fraction (dxy_beta DROPPED — DXY not in production parquet).

## 1. Pair-character feature vector (frozen)

| Pair | d1_ac1 | h4_atr_pct | max_session_impulse | d1_chop_frac | dxy_beta |
|---|---:|---:|---:|---:|---|
| EURUSD | -0.0216 | 0.50 | 0.489 | 0.320 | dropped |
| GBPUSD | +0.0332 | 0.90 | 0.481 | 0.309 | dropped |
| USDCAD | -0.0041 | 0.70 | 0.483 | 0.310 | dropped |
| AUDUSD | -0.0510 | 0.10 | 0.465 | 0.330 | dropped |
| NZDUSD | -0.0093 | 0.30 | 0.440 | 0.297 | dropped |
| USDJPY | NEEDS CACHE PULL | | | | |
| USDCHF | NEEDS CACHE PULL | | | | |

## 2. Per-agent per-pair coverage in banked telemetry

Coverage tells you whether OLS is even mathematically defined for that agent — need ≥2 observations with ≥2 unique x-values for a non-degenerate β.

| Agent | symbols present | # symbols | # windows |
|---|---|---:|---:|
| **chigiri_hyoma** | EURUSD, GBPUSD | 2 | 7 |
| **itoshi_rin** | EURUSD | 1 | 7 |
| **kunigami_rensuke** | — | 0 | 0 |
| isagi_yoichi (audit) | EURUSD, GBPUSD, USDCAD | 3 | 7 |
| bachira_meguru (audit) | EURUSD, GBPUSD, USDCAD | 3 | 7 |
| nagi_seishiro (audit) | EURUSD, GBPUSD, USDCAD | 3 | 7 |
| barou_shoei (audit) | USDCAD | 1 | 7 |

## 3. Regression outputs — movable agents

### chigiri_hyoma

| Feature | n obs | unique x | β | R² | CI lower | CI upper | |β| CI lower | direction | direction OK? | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `d1_ac1` | 14 | 2 | -1.2613 | 0.1643 | -2.8168 | +0.3144 | 0.0846 | — | n/a |  |
| `h4_atr_percentile` | 14 | 2 | -0.1727 | 0.1643 | -0.3856 | +0.0430 | 0.0116 | — | n/a |  |
| `max_session_impulse` | 14 | 2 | +8.8946 | 0.1643 | -2.2161 | +19.8991 | 0.5963 | + | ✓ |  |
| `d1_chop_fraction` | 14 | 2 | +6.1720 | 0.1643 | -1.5378 | +13.8081 | 0.4138 | - | ✗ |  |

### itoshi_rin

| Feature | n obs | unique x | β | R² | CI lower | CI upper | |β| CI lower | direction | direction OK? | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `d1_ac1` | 7 | 1 | — | — | — | — | — | — | n/a | n=7, unique_x=1 — need n>=2 with >1 unique x-value for OLS β. |
| `h4_atr_percentile` | 7 | 1 | — | — | — | — | — | - | ✗ | n=7, unique_x=1 — need n>=2 with >1 unique x-value for OLS β. |
| `max_session_impulse` | 7 | 1 | — | — | — | — | — | — | n/a | n=7, unique_x=1 — need n>=2 with >1 unique x-value for OLS β. |
| `d1_chop_fraction` | 7 | 1 | — | — | — | — | — | — | n/a | n=7, unique_x=1 — need n>=2 with >1 unique x-value for OLS β. |

### kunigami_rensuke

**No banked trades for kunigami_rensuke in the g7retry1-phi41 cache.**

Reason: Kunigami is retired as a proposer (G7 §11.12). AC.1 tests un-retirement, but AC.0 uses banked (retired-Kunigami) telemetry — he cannot contribute a regression row.

## 4. Pass criterion (§5)

- **Condition 1** — ≥2 of {Chigiri, Rin, Kunigami} with a feature whose bootstrap 95 % CI lower on |β| > 0: **NOT MET** (1/3 movables passing).
  * chigiri_hyoma: ['d1_ac1', 'h4_atr_percentile', 'max_session_impulse', 'd1_chop_fraction']
  * itoshi_rin: no feature passing
  * kunigami_rensuke: no feature passing
- **Condition 2** — ≥1 passing (agent, feature) pair with pre-locked direction respected: **MET** (1 pair(s)).

## 5. Verdict narrative

**AC.0 FAILS per §5. Pitch-character-predicts-agent-success unsupported at the banked-panel scale; pitch-assignment concept unsupported without a larger panel; further arms not authorised per PROTOCOL §5 fail-branch language and §10 kill condition.**

### 5a. Why the pre-registered test cannot fire cleanly

The pre-reg §5 pass criterion requires ≥2 of {Chigiri, Rin, Kunigami} to produce a non-degenerate regression with |β| CI lower > 0. Two structural constraints of the banked telemetry make this mathematically inaccessible:

1. **Kunigami has 0 banked trades** — he is retired as a proposer (G7 §11.12). The g7retry1-phi41 replay was run with the retired-Kunigami roster, so his per-symbol mean-TQS row is empty. Un-retirement is what AC.1.kun-a *tests*, so AC.0 cannot use un-retired-Kunigami data.
2. **Rin has only 1 unique x-value.** His default `.symbols = ('EURUSD',)` means every banked window×symbol row for Rin sits at the same EURUSD feature value; OLS β requires ≥2 unique x-values, so no feature can produce a well-defined β for Rin — CI is undefined.
3. **Chigiri has 2 unique x-values** (EURUSD, GBPUSD). Chigiri is the ONLY movable that produces a defined β. Even a passing Chigiri result cannot meet the ≥2-agent threshold on its own.

The pre-reg §9 pre-mortem anticipated 'AC.0 low power at n=5 pairs'. The realised banked panel is n=3 pairs, and the agents' `.symbols` restrictions collapse per-agent coverage further to n=2/1/0 unique x-values. The pre-reg's own §5 fail-branch language is the correct verdict text: "pitch-character-predicts-agent-success unsupported at n=5 pairs; pitch-assignment concept unsupported without a larger panel; further arms not authorised."

### 5b. What this means for the campaign

- Per PROTOCOL §5 AC.0 fail-branch and §10 kill conditions: **AC.1 and AC.2 arms DO NOT fire.**
- The harness extension (commit 3e0f611f) is a valid methodology deliverable and stays in the codebase — no strategy was changed.
- Any future Phase-AC-style pitch-assignment work will need either (a) a much larger banked panel (≥ 7 pairs, with movable agents' `.symbols` deliberately widened before the g7 walk-forward so the banked telemetry covers all pairs), or (b) a materially different statistic that does not require per-agent per-pair OLS — an amendment file (`AMENDMENT_YYYY-MM-DD_<slug>.md`) per PROTOCOL §13.
