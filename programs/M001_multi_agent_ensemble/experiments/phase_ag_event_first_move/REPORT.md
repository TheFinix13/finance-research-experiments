# Phase AG report — S2 follow-the-first-move (2026-08-04)

Protocol: `PROTOCOL.md` (registered 2026-08-04 before execution).
Verdict: **no arm promoted** under the pre-registered floors — but the
failure mode is the informative one (n-starvation at high impulse
thresholds, not randomness), and the study hands a sharpened
hypothesis to S1.

## What ran

12 pre-registered arms (K ∈ {1,2} bars × m ∈ {3,5,8}×ATR96 × TP ∈
{1.5, 2.5}R) on EURUSD M15 over the 2015–2021 in-sample half of the
frozen 349-event USD panel (sha
`cfd186021ea87a5acba4f672250519d89fb8657c11473a73621bcc78c0ee3134`),
1.2 pips costs, SL-first tie-break, 12h timeout. The sealed 2022–2025
validation window was NOT opened (no arm qualified). GBPUSD ran as a
no-tuning robustness readout.

## Results (EURUSD in-sample)

| Arm | n | net mean pips | 2015–17 | 2018–21 | alive? |
|---|---|---|---|---|---|
| K1_m3_tp1.5 | 101 | +4.4 | +512 | −66 | no (half flip) |
| K1_m3_tp2.5 | 101 | +6.9 | +706 | −13 | no (half flip) |
| K1_m5_tp1.5 | 54 | +6.5 | +383 | −32 | no (half flip) |
| K1_m5_tp2.5 | 54 | +9.4 | +539 | −29 | no (half flip) |
| K1_m8_tp1.5 | 25 | **+14.1** | +189 | +163 | no (n < 30) |
| K1_m8_tp2.5 | 25 | **+18.8** | +306 | +163 | no (n < 30) |
| K2_m3_tp1.5 | 99 | +4.9 | +718 | −232 | no (half flip) |
| K2_m3_tp2.5 | 99 | +3.4 | +521 | −189 | no (half flip) |
| K2_m5_tp1.5 | 60 | +7.2 | +512 | −78 | no (half flip) |
| K2_m5_tp2.5 | 60 | +4.7 | +347 | −67 | no (half flip) |
| K2_m8_tp1.5 | 28 | **+15.4** | +237 | +193 | no (n < 30) |
| K2_m8_tp2.5 | 28 | +8.6 | +58 | +182 | no (n < 30) |

Three observations, in decreasing order of strength:

1. **All 12 arms have positive net means.** Under a null of
   direction-symmetric post-event noise this has probability ~2^-12
   ≈ 0.0002 if arms were independent (they are not — K variants and
   TP variants share events — so treat as suggestive, not
   conclusive). The market's first move after a high-impact USD
   release points the right way more often than not.
2. **The edge concentrates in violent reactions.** The ≥8×ATR arms
   earn +14 to +19 pips/trade with BOTH sub-halves positive — the
   only arms with sign consistency — but only ~25–28 qualifying
   events exist in seven years. They fail the pre-registered n ≥ 30
   floor by 2–5 events. The floors stand; no promotion.
3. **Small-impulse arms flip sign in 2018–2021.** m=3/m=5 arms lose
   money in the later half: modest first moves carry no reliable
   continuation information. This matches the user's read that
   "uneventful" events dilute everything (Phase AE's unconditional
   FAIL is the extreme case of the same effect).

GBPUSD (robustness, no tuning): the same monotone pattern — all arms
positive, K2 arms positive in both halves, m=8 means +6 to +24
pips/trade at tiny n. Independent confirmation of the shape.

## Verdict and hand-off

- Formal verdict: `no_arm_promoted` (floors pre-registered; the m=8
  family is a REGISTERED NEAR-MISS, not an unlucky discovery).
- Classification per protocol §"If zero arms are IS-alive":
  **n-starvation at high thresholds**, present-but-random at low
  thresholds. NOT `dead_unconditional`.
- Hand-off to S1: the binding constraint is identifying the ~4
  events/year that will move ≥8×ATR. Waiting K bars to observe the
  impulse costs entry price AND cannot expand n. A SURPRISE gate
  (|actual − consensus| z-score, S1) attacks exactly this: if big
  surprises predict big impulses, the surprise is knowable at t0
  (not t0+K), improving both entry and sample identification.
- Recommended follow-up (needs fresh pre-reg, "Phase AG-2"): expand
  the event panel (FOMC minutes, PPI, retail sales, ECB for EURUSD)
  to raise n at high thresholds, and/or add the S1 surprise axis
  once the panel data exists. The sealed 2022–2025 window remains
  sealed for that study's validation.

## Multiplicity note

12 arms, per-arm selection was not exercised (nothing promoted), so
no selection bias enters the record. The all-positive-means
observation is reported as a family-level pattern with the
dependence caveat above.
