# E028 — Report: "Power of Three" session sequence

**Verdict: STOPPED-DEAD at Stage 1 (2026-07-28), full stop.** The
descriptive margin failed *and* both mechanical cells were negative at
base costs — the §6 full-stop condition. Stages 2–3 did not run.

- Pre-registration commit: `cdb7a01` (2026-07-28, `main`)
- Harness + §7 A1 amendment commit: `6722012`
- Stage-1 results: `output/E028_power_of_three_sessions/stage1_EURUSD_screen_2026-07-28_1716.json`
- Stop files: `output/E028_power_of_three_sessions/stage{2,3}_E028_stop.json`

---

## 1. Headline: the narrative is empirically inverted

EURUSD M15, 2015-01-01 → 2021-12-31, 1,816 qualifying days, fixed UTC
windows (Asia 00–07, London 07–13, NY 13–21), seed 28.

**D1 — the setup is common.** London takes exactly one side of the
Asia range on 65 % of days (HIGH_ONLY 580, LOW_ONLY 600), takes both
on 595 (32.8 %), and stays inside on only 41 (2.3 %).

**D2 vs D3 — the completion almost never happens, and conditioning
makes it *worse*.** Given a one-side London take, NY touches the
untapped opposite Asia extreme on **26.2 %** of days
(CI95 [23.8, 28.8]) — versus a **61.2 %** matched unconditional
baseline. The pre-registered support margin was +5 pp *above*
baseline; the observed gap is **−35 pp**. Once London has taken one
side, price is far *more* likely to keep going than to reverse to the
other side.

**D4 — the "NY fake" is just continuation.** On 60.2 % of one-side
days (CI95 [57.4, 62.9]) NY extends beyond London's own extreme before
any completion. The reels present this as a trap that precedes
reversal; in the data it is simply the dominant direction continuing.

**D6 — stable across all seven years.** Yearly completion rates run
20–32 %, never approaching their yearly baselines (60–65 %). This is
not a regime artifact.

## 2. Mechanical rule (2 cells, the only inferential test)

Entry at the first M15 close ≥ 13:30 UTC toward the untapped extreme,
SL at the manipulation extreme, TP at the opposite Asia extreme, time
exit 21:00 UTC; costs 0.3 pip/side base, 1.0 stress.

| Arm | n | mean net pips (base) | boot CI95 | p(≤0) | TP rate | SL rate | verdict |
|---|---:|---:|---|---:|---:|---:|---|
| long (LOW_ONLY) | 511 | **−0.74** | [−2.66, +1.20] | 0.770 | 21.7 % | 53.6 % | dead |
| short (HIGH_ONLY) | 507 | **−0.66** | [−2.43, +1.07] | 0.769 | 19.1 % | 49.7 % | dead |

Both arms lose before the stress arm is even consulted; the SL (the
"manipulation" extreme the narrative says should hold) is hit two and
a half times as often as the TP.

## 3. Interpretation

1. **As a reversal story, Po3 is not just unsupported — the
   conditional evidence points the other way.** The tradeable
   regularity in this data, if any, is *London-direction continuation*,
   not NY reversal to untapped liquidity. Testing that mirror-image
   hypothesis would be a new pre-registration (new ID), and it would
   still have to beat intraday costs from a standing start.
2. The reels' examples are consistent with selecting the ~26 % of days
   on which the sequence completes — base-rate neglect, exactly the
   failure mode the lab's priors predicted.
3. **Production consequences: none to change; standing block.** Any
   M001 "Po3 striker" (session-sequence reversal playstyle) is blocked
   by this registry entry. A continuation-flavoured session agent
   would be a different hypothesis requiring its own protocol.

## 4. Discipline notes

- Full-stop rule fired exactly as pre-declared; both stop files
  emitted.
- Data use: EURUSD M15 2015–2021 screen consumed (documented reuse);
  confirm and GBPUSD cross-pair slices **not consumed**. E010's M15
  sealed reservation untouched.
- Skip accounting: 162 of 1,180 one-side days produced no trade
  (`degenerate_geometry` 119, `tp_touched_pre_entry` 43); counts in
  the results JSON.
- One amendment (§7 A1, network-free loader), committed before any
  statistic was scored.
