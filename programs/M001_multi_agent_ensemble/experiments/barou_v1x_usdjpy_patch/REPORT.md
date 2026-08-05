# Barou v1.4 — USDJPY stop/ATR entry gate: REPORT

Executed 2026-08-05 exactly per `PROTOCOL.md` (registered before any
v1.4 replay). One mechanism: reject if structural stop > 2.25 × ATR(14).
Live default stays `weapon_v14=False`.

## Verdict: **sealed FAIL** (final on this window)

| phase | n median | PF | mean R | PF>1 starts | verdict |
|---|---|---|---|---|---|
| Design 2015–2022 (contaminated) | 534 | **1.163** | **+0.066** | 5/5 | PASS (n/stability ok; not confirmatory) |
| **Sealed 2023–2026 (judgment)** | 200 [159–243] | **1.005** [0.946–1.076] | **−0.035** | **3/5** | **FAIL** (PF, meanR, stability) |

Sealed floors were n≥25 / PF≥1.10 / meanR>0 / ≥4/5 — all at 1× honest
cost (1.0 JPY pip). Fail is final; USDJPY 2023+ seal is now CONSUMED.

## What the design said (upper bound)

The gate fires: vs AN-5 baseline on the same fill model, ~980
high-stop/ATR proposals are suppressed per full start. Design median
PF 1.163 clears the 1.15 floor with thin margin (autopsy counterfactual
~1.50 was an optimistic in-sample filter on a fixed tape, not a
replay). Path dependence raised trade count vs AN-5 (n≈534 post
burn-in vs ~418) because removing early rejects changes later
admission — another reason design KPIs are not forecasts.

## Sealed per-start (1× cost)

| start | n | PF | mean R |
|---|---|---|---|
| 2023-01 | 243 | 1.054 | +0.007 |
| 2023-04 | 223 | 1.005 | −0.035 |
| 2023-07 | 200 | 0.946 | −0.058 |
| 2023-10 | 177 | 0.965 | −0.042 |
| 2024-01 | 159 | 1.076 | +0.037 |

Flat-to-negative after costs. The mechanism that looked load-bearing on
the design split does not survive the sealed open.

## Process notes

1. A void first design attempt used JPY field-pip fill costs (`* 0.01`),
   which reshaped the path and made the gate a no-op. Discarded; not
   reported as a floor read. Fill policy restored: FX keeps legacy
   `* 1e-4`; Tier-2 non-FX uses field pip (product `84564de`).
2. Autopsy Candidate A remains a legitimate *hypothesis generator*; it
   is not evidence. This sealed open is the evidence.

## Recommendations

1. **Do not enable `weapon_v14` on live.** Flag stays False.
2. **Candidate B (breakeven at +1R MFE)** may be chartered separately
   with a fresh pre-reg — it needs a replay (path timing), not a
   filter on this consumed sealed window. New design window or live
   weeks only.
3. Barou:USDJPY weapon claim stays at the AN-5 near-miss state
   (isolation PF 1.138). No promotion.

## Artifacts

`results/design_summary.json`, `results/sealed_summary.json`, raw
tapes under `results/{design,sealed}/start_*/` (local).
