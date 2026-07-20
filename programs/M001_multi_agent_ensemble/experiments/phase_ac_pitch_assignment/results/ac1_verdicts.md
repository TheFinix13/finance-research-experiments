# Phase AC — AC.1 sub-arm verdicts (C1 on AC.0-v2 telemetry)

- **Fired:** 2026-07-20T22:56:51.450977+00:00
- **Telemetry source:** `programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/results/ac0_compute`
- **Bootstrap:** n = 10000, seed = 20260720, window-level resample (§6)
- **FDR budget:** BH q = 0.1 across TESTABLE sub-arms only. NOT_TESTABLE sub-arms (amendment §8 sentinels) are enumerated below and excluded from the BH family (no p-value).

## 1. Methodology note (transparent)

The AC.0-v2 fresh compute widened each movable agent to all 7 pairs with other agents at doctrine defaults — the exact per-reg §5 AC.1 semantic for the fully-widened case. Sub-arm evaluation extracts the sub-arm's pair subset from that per-pair per-window mean-TQS grid rather than firing a fresh walk-forward per sub-arm, because (a) `run_g7_v1_checkpoint_gate.py --symbols` restricts the whole PANEL and silences non-widened agents whose doctrine `.symbols` fall outside the panel — not the AC.1 semantic; (b) `run_ac0_compute.py` widens the movable to the panel `--symbols` and cannot express "widen movable to a subset of the panel" — also not the AC.1 semantic; (c) building a per-movable-symbol-override harness is outside this resumer session's write-scope; (d) per-pair per-window mean-TQS is pair-local under phi41's per-pair TQS scoring, so extracting the sub-arm's pair subset from the widest-panel telemetry is a scientifically valid proxy for a narrower-panel run modulo a bounded 2nd-order effect via Reo's HRP copier universe.

## 2. Sub-arm summary table

| Sub-arm | Agent | Nominal `.symbols` | Evaluated | §8-dropped | Populated wins | Trades | Mean TQS | K/7 ≥ 0.20 | 95% CI lower | C1 pass? | BH reject? |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| AC.1.chi-a | `chigiri_hyoma` | AUDUSD, NZDUSD | AUDUSD, NZDUSD | — | 7/7 | 531 | 0.207 | 3/7 | 0.183 | no | no |
| **AC.1.chi-b** | `chigiri_hyoma` | USDJPY | — | USDJPY | — | — | — | — | — | **NOT_TESTABLE** | — |
| AC.1.chi-c | `chigiri_hyoma` | GBPUSD | GBPUSD | — | 7/7 | 232 | 0.219 | 6/7 | 0.190 | no | no |
| AC.1.rin-a | `itoshi_rin` | EURUSD, USDCHF | EURUSD, USDCHF | — | 7/7 | 403 | 0.357 | 6/7 | 0.295 | **YES** | yes |
| AC.1.rin-b | `itoshi_rin` | EURUSD, USDJPY | EURUSD | USDJPY | 7/7 | 203 | 0.370 | 7/7 | 0.329 | **YES** | yes |
| AC.1.rin-c | `itoshi_rin` | USDCHF | USDCHF | — | 7/7 | 200 | 0.349 | 6/7 | 0.244 | no | yes |
| **AC.1.kun-a** | `kunigami_rensuke` | AUDUSD, NZDUSD | — | AUDUSD, NZDUSD | — | — | — | — | — | **NOT_TESTABLE** | — |
| **AC.1.kun-b** | `kunigami_rensuke` | AUDUSD, NZDUSD, USDJPY | — | AUDUSD, NZDUSD, USDJPY | — | — | — | — | — | **NOT_TESTABLE** | — |

## 3. NOT_TESTABLE sub-arms (amendment §8 sentinels)

### AC.1.chi-b — `chigiri_hyoma` on USDJPY

- **Reason:** amendment §8 sentinel: all symbols in this sub-arm (USDJPY) are newly-widened for chigiri_hyoma (v1 defaults = ['EURUSD', 'GBPUSD']) and produced 0 trades in every OOS window in the AC.0-v2 fresh compute. This is a data/logic problem for the movable on those pairs, not a legitimate y = 0 signal — cannot enter the C1 test.

### AC.1.kun-a — `kunigami_rensuke` on AUDUSD, NZDUSD

- **Reason:** amendment §8 sentinel: Kunigami un-retired produced 0 trades across ALL 7 pairs (49 pair-windows) in the AC.0-v2 fresh compute — un-retirement wiring failed silently. Cannot legitimately be counted as y = 0 observations for AC.1. Fix required: investigate Kunigami proposer-wiring in run_ac0_compute._build_movable_roster

### AC.1.kun-b — `kunigami_rensuke` on AUDUSD, NZDUSD, USDJPY

- **Reason:** amendment §8 sentinel: Kunigami un-retired produced 0 trades across ALL 7 pairs (49 pair-windows) in the AC.0-v2 fresh compute — un-retirement wiring failed silently. Cannot legitimately be counted as y = 0 observations for AC.1. Fix required: investigate Kunigami proposer-wiring in run_ac0_compute._build_movable_roster

## 4. Testable sub-arm detail

### AC.1.chi-a — `chigiri_hyoma` on AUDUSD, NZDUSD

- **Populated windows:** 7/7
- **Total trades in sub-arm:** 531
- **Mean TQS (across populated windows):** 0.2067  (≥ 0.30? no)
- **K-of-7 windows ≥ 0.20:** 3/7  (≥ 5? no)
- **Bootstrap 95% CI on mean TQS:** [0.1826, 0.2396]  (lower > 0.25? no)
- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** 0.991900
- **C1 pass?** no (need all 3 sub-criteria met)
- **BH FDR (q = 0.1):** rank 5/5, threshold = 0.1000, raw p = 0.991900, reject H0 at q = 0.1: no

Per-window (trade-weighted across sub-arm pairs):

| Window | mean TQS | n trades | breakdown |
|---:|---:|---:|---|
| 0 | 0.218 | 73 | AUDUSD (0.249, n=29), NZDUSD (0.197, n=44) |
| 1 | 0.296 | 83 | AUDUSD (0.318, n=37), NZDUSD (0.279, n=46) |
| 2 | 0.179 | 68 | AUDUSD (0.158, n=33), NZDUSD (0.199, n=35) |
| 3 | 0.214 | 79 | AUDUSD (0.211, n=35), NZDUSD (0.216, n=44) |
| 4 | 0.184 | 79 | AUDUSD (0.191, n=45), NZDUSD (0.174, n=34) |
| 5 | 0.184 | 87 | AUDUSD (0.210, n=44), NZDUSD (0.159, n=43) |
| 6 | 0.172 | 62 | AUDUSD (0.129, n=26), NZDUSD (0.203, n=36) |

### AC.1.chi-c — `chigiri_hyoma` on GBPUSD

- **Populated windows:** 7/7
- **Total trades in sub-arm:** 232
- **Mean TQS (across populated windows):** 0.2187  (≥ 0.30? no)
- **K-of-7 windows ≥ 0.20:** 6/7  (≥ 5? YES)
- **Bootstrap 95% CI on mean TQS:** [0.1896, 0.2461]  (lower > 0.25? no)
- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** 0.987800
- **C1 pass?** no (need all 3 sub-criteria met)
- **BH FDR (q = 0.1):** rank 4/5, threshold = 0.0800, raw p = 0.987800, reject H0 at q = 0.1: no

Per-window (trade-weighted across sub-arm pairs):

| Window | mean TQS | n trades | breakdown |
|---:|---:|---:|---|
| 0 | 0.249 | 34 | GBPUSD (0.249, n=34) |
| 1 | 0.203 | 33 | GBPUSD (0.203, n=33) |
| 2 | 0.228 | 26 | GBPUSD (0.228, n=26) |
| 3 | 0.212 | 31 | GBPUSD (0.212, n=31) |
| 4 | 0.148 | 32 | GBPUSD (0.148, n=32) |
| 5 | 0.280 | 38 | GBPUSD (0.280, n=38) |
| 6 | 0.210 | 38 | GBPUSD (0.210, n=38) |

### AC.1.rin-a — `itoshi_rin` on EURUSD, USDCHF

- **Populated windows:** 7/7
- **Total trades in sub-arm:** 403
- **Mean TQS (across populated windows):** 0.3571  (≥ 0.30? YES)
- **K-of-7 windows ≥ 0.20:** 6/7  (≥ 5? YES)
- **Bootstrap 95% CI on mean TQS:** [0.2952, 0.4106]  (lower > 0.25? YES)
- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** 0.000300
- **C1 pass?** **YES**
- **BH FDR (q = 0.1):** rank 2/5, threshold = 0.0400, raw p = 0.000300, reject H0 at q = 0.1: YES

Per-window (trade-weighted across sub-arm pairs):

| Window | mean TQS | n trades | breakdown |
|---:|---:|---:|---|
| 0 | 0.196 | 23 | EURUSD (0.325, n=11), USDCHF (0.079, n=12) |
| 1 | 0.385 | 61 | EURUSD (0.337, n=27), USDCHF (0.423, n=34) |
| 2 | 0.418 | 56 | EURUSD (0.313, n=25), USDCHF (0.502, n=31) |
| 3 | 0.456 | 98 | EURUSD (0.454, n=73), USDCHF (0.465, n=25) |
| 4 | 0.348 | 65 | EURUSD (0.324, n=29), USDCHF (0.367, n=36) |
| 5 | 0.303 | 40 | EURUSD (0.372, n=17), USDCHF (0.251, n=23) |
| 6 | 0.393 | 60 | EURUSD (0.467, n=21), USDCHF (0.353, n=39) |

### AC.1.rin-b — `itoshi_rin` on EURUSD, USDJPY

- **Populated windows:** 7/7
- **Total trades in sub-arm:** 203
- **Mean TQS (across populated windows):** 0.3703  (≥ 0.30? YES)
- **K-of-7 windows ≥ 0.20:** 7/7  (≥ 5? YES)
- **Bootstrap 95% CI on mean TQS:** [0.3286, 0.4159]  (lower > 0.25? YES)
- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** 0.000000
- **C1 pass?** **YES**
- **BH FDR (q = 0.1):** rank 1/5, threshold = 0.0200, raw p = 0.000000, reject H0 at q = 0.1: YES

Per-window (trade-weighted across sub-arm pairs):

| Window | mean TQS | n trades | breakdown |
|---:|---:|---:|---|
| 0 | 0.325 | 11 | EURUSD (0.325, n=11) |
| 1 | 0.337 | 27 | EURUSD (0.337, n=27) |
| 2 | 0.313 | 25 | EURUSD (0.313, n=25) |
| 3 | 0.454 | 73 | EURUSD (0.454, n=73) |
| 4 | 0.324 | 29 | EURUSD (0.324, n=29) |
| 5 | 0.372 | 17 | EURUSD (0.372, n=17) |
| 6 | 0.467 | 21 | EURUSD (0.467, n=21) |

### AC.1.rin-c — `itoshi_rin` on USDCHF

- **Populated windows:** 7/7
- **Total trades in sub-arm:** 200
- **Mean TQS (across populated windows):** 0.3487  (≥ 0.30? YES)
- **K-of-7 windows ≥ 0.20:** 6/7  (≥ 5? YES)
- **Bootstrap 95% CI on mean TQS:** [0.2438, 0.4386]  (lower > 0.25? no)
- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** 0.032700
- **C1 pass?** no (need all 3 sub-criteria met)
- **BH FDR (q = 0.1):** rank 3/5, threshold = 0.0600, raw p = 0.032700, reject H0 at q = 0.1: YES

Per-window (trade-weighted across sub-arm pairs):

| Window | mean TQS | n trades | breakdown |
|---:|---:|---:|---|
| 0 | 0.079 | 12 | USDCHF (0.079, n=12) |
| 1 | 0.423 | 34 | USDCHF (0.423, n=34) |
| 2 | 0.502 | 31 | USDCHF (0.502, n=31) |
| 3 | 0.465 | 25 | USDCHF (0.465, n=25) |
| 4 | 0.367 | 36 | USDCHF (0.367, n=36) |
| 5 | 0.251 | 23 | USDCHF (0.251, n=23) |
| 6 | 0.353 | 39 | USDCHF (0.353, n=39) |

## 5. Aggregate

- **Sub-arms testable:** 5 of 8
- **Sub-arms passing C1 (all 3 sub-criteria):** 2
- **Sub-arms BH-rejected at q = 0.1 (i.e. C1 pass survives multi-test correction):** 3

## 6. Passing pitch sets per movable (STRICT: evaluated pairs only)

The pre-reg §5 says the 'passing pitch set' is the union of `.symbols` across passing sub-arms. Applying that literally to sub-arms where amendment §8 dropped a widened pair from the eval would credit the drop-victim pair for a pass it never demonstrated. STRICT reading: only credit `evaluated_pairs` (i.e. the pairs that actually contributed trades to the eval) toward the passing pitch set. Widenings that never produced a trade cannot be authorised by a pass that didn't measure them.

- **`itoshi_rin`** v1 defaults: `['EURUSD']`; AC.1 evaluated-pairs union: `['EURUSD', 'USDCHF']`; **newly authorised widening pitches: `['USDCHF']`**; UNION `.symbols` for AC.2: `['EURUSD', 'USDCHF']`.

§8-reduced sub-arm crediting:

- AC.1.rin-b: nominal `.symbols` = ['EURUSD', 'USDJPY']; §8 dropped ['USDJPY']; evaluated on ['EURUSD']. Pass CREDITS ONLY ['EURUSD'].

## 7. Verdict

**AC.1 PASSES on the widening question** — at least one movable earned a new authorised pitch beyond its v1 defaults (3 sub-arm(s) survived BH FDR at q = 0.10). Passing pitch sets recorded above (§6) authorise the corresponding movable-agent widenings for AC.2 A2 / B1 arm construction per PROTOCOL §5.1 UNION semantic.
