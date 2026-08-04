# Phase AJ report — cross-symbol weapon transfer

Executed: 2026-08-04, same day as registration (protocol committed at
`bbb3f01` BEFORE the replay ran). One in-sample replay 2019-01-01 →
2023-12-31, causal D138 semantics, deployed configs, Rin/Barou/Chigiri
expanded to all three pairs. Sealed 2024–2026 validation window:
**NEVER OPENED** (no cell cleared rule 1) — it remains pristine for
follow-ups.

## Verdicts per away cell (pre-registered floors: PF ≥ 1.15, mean R ≥ +0.05, n ≥ 40)

| Cell | n | PF | mean R | Verdict |
|---|---|---|---|---|
| Barou : EURUSD | 25 | **2.032** | **+0.450** | **registered_near_miss** (rule 2: n < 40, PF ≥ 1.15) |
| Barou : GBPUSD | 32 | 1.027 | +0.008 | fail (PF floor) |
| Rin : GBPUSD | 224 | 1.037 | +0.016 | fail (PF floor) |
| Rin : USDCAD | 163 | 0.778 | −0.155 | fail |
| Chigiri : USDCAD | 103 | 1.078 | −0.029 | fail (PF and meanR floors) |

**Promotions to validation: 0 of 5.** No validation replay was run.

## Home-cell interaction check (PASS — study not confounded)

| Home cell | AF baseline (is_cell_30_0.0) | AJ expanded | shift |
|---|---|---|---|
| Rin : EURUSD | PF 1.132, n=173 | PF 1.204, n=167 | +0.072 |
| Barou : USDCAD | PF 1.345, n=29 | PF 1.327, n=23 | −0.018 |
| Chigiri : EUR+GBP | PF 0.680, n=190 | PF 0.725 / 0.599, n=189 | within band |

All shifts < 0.15 — expanding the roster did not distort anyone's
home game. The transfer readouts are trustworthy.

## Interpretation

1. **The headline is Barou.** The USDCAD lone-wolf's weapon posts its
   strongest cell in ANY study on a pair he has never traded: EURUSD
   PF 2.03, mean R +0.45, 56% wins. Combined with Phase AF (positive
   in all 8 USDCAD IS cells, always n-starved), the picture is
   consistent: a genuinely selective weapon whose only documented
   weakness is sample size. Phase AJ-2 (pre-registered separately,
   `PROTOCOL_AJ2.md`) extends the in-sample window to 2015–2023 to
   give the n-floor an honest chance before any validation spend.
2. **Rin does not travel (yet).** His EURUSD-only restriction looks
   load-bearing: GBPUSD is flat (PF 1.037 on a healthy n=224) and
   USDCAD is outright negative. The cold-geometry weapon reads
   EURUSD's structure specifically; symbol-specific re-parameterisation
   (not plain transfer) would be the next question, and it is NOT
   chartered yet.
3. **Chigiri's problem is the weapon, not the field.** Negative at
   home and abroad; his AF redesign direction stands unchanged.

## Multiplicity honesty

5 cells at the joint floor, 0 promotions claimed — no selection event
occurred, so no false-promotion budget was spent. The Barou:EURUSD
near-miss is a REGISTERED observation (this file) and may only be
acted on through AJ-2's pre-registered floors.
