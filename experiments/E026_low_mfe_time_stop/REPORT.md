# E026 — Low-MFE time-stop: stage-1 report

**Date:** 2026-07-28 · **Verdict:** `parked_low_yield` (0/45 cells
alive) · **Stage 2 (health meter): NOT authorised** ·
**Results:** `programs/E026/results.json`

## 1. What was tested

Pre-registered 15-arm grid (PROTOCOL §4.1): close at market the first
bar a trade has been held ≥ `B` H4-equivalent bars while its running
MFE has never reached `P` R. `P ∈ {0.25, 0.50, 0.75}`,
`B ∈ {12, 18, 24, 30, 42}` (≈ 2–7 trading days). Paired ΔSharpe vs a
replayed null-arm baseline (Amendment 1), 5 walk-forward folds,
bootstrap seed 42 × 5000, Stouffer fold combination, BH-FDR α = 0.10
per symbol.

## 2. Headline result

| Symbol | alive | parked_low_yield | dead | max ΔSharpe (arm) |
|---|---|---|---|---|
| EURUSD | 0 | 11 | 4 | +0.0150 (P0.75_B12) |
| GBPUSD | 0 | 1 | 14 | +0.0003 (P0.25_B12) |
| USDCAD | 0 | 6 | 9 | +0.0061 (P0.50_B24) |

Study verdict `parked_low_yield`; §6 stop rule engaged — no stage 2,
no grid extension, no live wiring.

The signal is real but tiny and statistically unconfirmable at this
event rate. Seven cells have the entire 95 % CI above zero (e.g.
EURUSD P0.75_B12 +0.0150 CI [+0.0007, +0.0292], BH-rejected, joint
p ≈ 0 — but only 3/5 folds positive; EURUSD P0.75_B18 is positive in
5/5 folds but Stouffer p = 0.22). No cell clears all four alive legs
simultaneously, and the binding constraint is always the same: **the
firing cohort is minuscule** (0–49 fires per symbol out of 707–944
trades over 11 years), so fold-level significance is unreachable.

## 3. Why the cohort is so small (the finding that matters)

Once the age clock was corrected to H4-equivalents (Amendment 2), a
trade that is BOTH ≥ 2 trading days old AND still below 0.75R MFE
turns out to be rare on this cell: the deployed entry model's trades
either reach ~1R quickly or hit the stop — they do not typically
lounge below 0.5R for days. At the anchor of the user's complaint
(P0.50, B30 ≈ 5 trading days): EURUSD 2 fires, GBPUSD 5, USDCAD 5 in
eleven years. The two July-2026 stuck tickets (GBPUSD 3000652586,
USDCAD 2987854368 — illustrative n = 2, outside the ledger window)
are genuine members of this cohort, but the cohort is a tail event,
not a systematic drag: a rule policing it cannot move portfolio
Sharpe by more than ~+0.015 even when every fire is a rescue.

Guardrails behaved as H2 predicted: fires land overwhelmingly on
eventual losers (rescued fraction 0.5–1.0; FP fraction 0–0.50, mostly
0–0.33 — far below E024's 0.63–0.91), and same-bar-TP fires are
structurally impossible. The cohort-separation argument survived; the
mechanism just has almost nothing to police.

## 4. Amendments (both same-day, pre-verdict; full text in PROTOCOL §7)

1. **Null-arm baseline.** First sweep failed the zero-fire identity
   (USDCAD arm with 0 fires showed ΔSharpe −0.145). Ledger-`r`
   baseline vs path-reconstructed arm confounds rule effect with
   reconstruction drift; baseline switched to a replayed inert rule.
   Pre-amendment numbers preserved in
   `results_pre_amendment1_confounded.json`.
2. **H4-equivalent age clock.** PRE-0 paths are per-symbol resolution
   (EURUSD M5, GBPUSD M15, USDCAD H4); counting raw path bars made
   B=12 mean one hour on EURUSD. Clock converted via resolution
   factor. Invalid-clock run preserved in
   `results_amendment1_wrong_clock.json`.

## 5. Collateral finding — E020–E025 campaign deltas are contaminated

Amendment 1's reconstruction audit measured the pure null-arm vs
ledger drift (no rule firing at all):

| Symbol | drift ΔSharpe (null vs ledger) | E024's reported "dead" ΔSharpe range |
|---|---|---|
| EURUSD | −0.0904 | [−0.0852, −0.0936] |
| GBPUSD | −0.0895 | [−0.0839, −0.0948] |
| USDCAD | −0.1453 | [−0.1327, −0.1448] |

E020/E021/E022/E024 all used the ledger-`r` baseline against replayed
arms, so their reported degradation is **indistinguishable in
magnitude from pure reconstruction drift** (BE-migration timing and
intra-bar ordering on coarse paths; ~86 % of trades' reconstructed R
differs from ledger R). Implications, stated carefully:

- The campaign's *"no evidence of improvement"* conclusion stands —
  drift is direction-uniform and would not mask a genuinely positive
  arm's paired CI.
- The campaign's *"actively harmful, 98/105 rejected in degradation
  direction"* claims are **unsafe** — much or all of that measured
  degradation is likely harness artifact, not rule effect.
- No deployment decision changes (nothing shipped either way), but
  any future citation of E020–E025 effect SIZES should re-run against
  a null-arm baseline first. Re-opening those verdicts is a user
  decision, not taken here.

## 6. Verdict and posture

- Stage 1 `parked_low_yield`; stage 2 (health-meter generalisation of
  PostLossGuard) **not pursued in this form** per §6 — the per-trade
  time signal is too rare on this cell to feed a meter.
- Deployed cell unchanged: TP 1.5R / soft-SL / BE-at-1R / PLG.
- The honest answer to the motivating complaint: multi-day sub-1R
  holds are real but rare (≈ 0.5–2 % of trades), and killing them
  earlier is at best a ~+0.01 Sharpe rounding improvement — not the
  drag it feels like when watching one live.
- STOP_NOTICE.md filed alongside this report.
