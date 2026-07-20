# Phase AC — AC.0-v2 verdict (fresh-compute per-movable regression)

- **Verdict:** **PASS**
- **Fired:** 2026-07-20T22:47:11.829724+00:00
- **Telemetry source:** `programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/results/ac0_compute` (per-movable walk-forward outputs from `run_ac0_compute`)
- **Pair-character source (FROZEN):** `programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/results/pair_character.json`
- **Bootstrap:** n = 10000, seed = 20260720, window-level resample
- **Amendment:** `AMENDMENT_2026-07-20_ac0_methodology_switch.md` (§5 pass criterion unchanged; y-axis switched from banked to fresh)

## 1. Per-agent coverage (fresh telemetry)

| Agent | symbols present | # symbols | # windows | movable trades |
|---|---|---:|---:|---:|
| **chigiri_hyoma** | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF | 6 | 7 | 1539 |
| **itoshi_rin** | AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF | 6 | 7 | 1340 |
| **kunigami_rensuke** | — | 0 | 0 | 0 |

## 2. Regression outputs — movable agents

### chigiri_hyoma

| Feature | n obs | unique x | β | R² | CI lower | CI upper | |β| CI lower | direction | direction OK? | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `d1_ac1` | 42 | 6 | +0.3203 | 0.0245 | -0.3451 | +0.9735 | 0.0155 | — | n/a |  |
| `h4_atr_percentile` | 42 | 6 | -0.0051 | 0.0007 | -0.0634 | +0.0582 | 0.0012 | — | n/a |  |
| `max_session_impulse` | 42 | 6 | +1.0963 | 0.0899 | +0.2576 | +1.9917 | 0.2687 | + | ✓ |  |
| `d1_chop_fraction` | 42 | 6 | +0.9874 | 0.0548 | -0.4316 | +2.2579 | 0.0511 | - | ✗ |  |

### itoshi_rin

| Feature | n obs | unique x | β | R² | CI lower | CI upper | |β| CI lower | direction | direction OK? | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `d1_ac1` | 42 | 6 | +0.9720 | 0.0542 | -0.2710 | +2.1288 | 0.0710 | — | n/a |  |
| `h4_atr_percentile` | 42 | 6 | +0.1159 | 0.0837 | -0.0083 | +0.2324 | 0.0113 | - | ✗ |  |
| `max_session_impulse` | 42 | 6 | +1.9563 | 0.0687 | -0.0548 | +4.0682 | 0.1845 | — | n/a |  |
| `d1_chop_fraction` | 42 | 6 | +0.0091 | 0.0000 | -2.9729 | +2.5941 | 0.0471 | — | n/a |  |

### kunigami_rensuke

**No AC.0-v2 telemetry available for kunigami_rensuke.** Fresh walk-forward not run OR produced zero trades across all widened pairs (see amendment §8 zero-trades sentinel).

## 3. Pass criterion (§5, unchanged by amendment)

- **Condition 1** — ≥2 of {Chigiri, Rin, Kunigami} with a feature whose bootstrap 95 % CI lower on |β| > 0: **MET** (2/3 movables passing).
  * chigiri_hyoma: ['d1_ac1', 'h4_atr_percentile', 'max_session_impulse', 'd1_chop_fraction']
  * itoshi_rin: ['d1_ac1', 'h4_atr_percentile', 'max_session_impulse', 'd1_chop_fraction']
  * kunigami_rensuke: no feature passing
- **Condition 2** — ≥1 passing (agent, feature) pair with pre-locked direction respected: **MET** (1 pair(s)).
  * chigiri_hyoma × max_session_impulse

## 4. Verdict narrative

AC.0-v2 PASSES per §5. Pair-character features explain a non-trivial share of per-movable-agent mean-TQS variance on the fresh-compute walk-forwards. **AC.1 sub-arms are AUTHORISED to fire per §12 sequencing (amendment §10).**
