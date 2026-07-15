# Phase AB verdict — Barou v1.3 multi-pair scope reversal (Lever B, §11.17 campaign)

- **Protocol:** `experiments/phase_ab_barou_multipair/PROTOCOL.md`
  (registered 2026-07-14, committed before implementation results).
- **Evaluated:** 2026-07-15 on the §11.17 `g7retry2` replays (single
  pre-registered OOS touch). Baselines are the §11.16 `g7retry1` numbers.
- **Evidence:** `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`,
  `reviews/g7retry2_lever_audits.json`.

## Verdict: **PASS** (AB1–AB5 all hold)

| Criterion | Locked threshold | Result | Pass |
|---|---|---|---|
| AB1 — volume floor | ≥ 100 OOS trades phi41 (was 43) | **n = 444** | ✅ |
| AB2 — C1 pass (primary) | mean ≥ 0.30, ≥ 5/7 windows ≥ 0.20, CI low > 0.25 | mean **0.4056**, 7/7 windows, CI [0.3647, 0.4466] | ✅ |
| AB3 — no self-regression | keeps C3 ≥ 4/7, C5, C6 | C3 **7/7** clean, C5 0.2847, C6 0.1659 | ✅ |
| AB4 — no peer C3 poisoning | no peer C3 pass→fail with Barou as worst-peer cause | no C3 pass→fail flips in either arm (all seven agents' C3 pass at g7retry2) | ✅ |
| AB5 — no squad regression | within −0.02 of §11.16 per arm | phi41 Δ −0.0112; arm4 Δ −0.0141 | ✅ |

Barou C1 under phi41: 0.283 (n=43) → **0.4056 (n=444)**. Under arm4 he
re-confirms at 0.402 (was 0.380). The Phase Y weapon's per-trade
quality generalised across all three pairs instead of diluting.

## Pre-registered audit (non-decisive): per-symbol split vs the E001 prior

| Symbol | n | mean TQS |
|---|---|---|
| USDCAD (home) | 166 | 0.3872 |
| GBPUSD | 158 | 0.4573 |
| EURUSD | 120 | 0.3631 |

(arm4 split is materially identical; see `g7retry2_lever_audits.json`.)

The EURUSD slice — the one the E001 negative prior warned about —
comes in at 0.3631 mean TQS over 120 trades, above the 0.30 bar. Note
the honest framing: E001's negative verdict was about a *standalone*
EURUSD deployment of the baseline-zone cell; here the D1 with-gate +
structural-TP weapon (Phase Y) plus squad aggregation is a different
object, and this audit does not overturn E001 — it shows the weapon
form travels. GBPUSD is, unexpectedly, his best pair (0.4573); the
home-ground devour/lone-conviction lifts stayed USDCAD-only per the
protocol and doctrine §3.11.3 A7 mechanic B.

## Remaining gap (out of this lever's scope, disclosed in §3)

Barou still fails C2 (no qualifying outgoing lift; bit vector
`101111`), so this lever alone does not flip his v1 pass. C2 was
explicitly out of scope for Phase AB.

## Status of the code

The expanded whitelist (`BAROU_V1_SYMBOLS = USDCAD/EURUSD/GBPUSD`,
home-ground privileges pinned to USDCAD) is validated and recommended
for **adoption as Barou's standing v1.3 configuration** at the §11.18
review. The canon "steal" mechanic (F21 read of Isagi/Rin thoughts)
remains designed-but-untested per protocol §3 — it ships nothing.
