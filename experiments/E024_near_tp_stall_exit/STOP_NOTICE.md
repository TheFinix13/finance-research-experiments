# E024 — STOP NOTICE

**Date:** 2026-07-20 · **Verdict:** `dead` · **Registry status:** LOCKED

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5, this notice records
that E024 (near-TP stall exit) failed its pre-registered `alive`
criteria at stage 1 and is stopped without stage 2 (exit-action sweep)
and without Phase 3 (production wiring).

## What was found

Zero of the pre-registered **24 stage-1 arms × 3 symbols = 72
(arm, symbol) cells** produced a pooled bootstrap 95 % CI lower > 0
on ΔSharpe of the per-trade R sequence versus the deployed `all_on`
cell. All 72 cells produced negative pooled ΔSharpe:

- **EURUSD** range −0.0852 to −0.0936
- **GBPUSD** range −0.0839 to −0.0948
- **USDCAD** range −0.1327 to −0.1448

BH-FDR at α = 0.10 (applied per-symbol across the 24-arm family per
PROTOCOL §5.4) rejected H0 in the direction of **degradation** for
22/24 EURUSD arms, 24/24 GBPUSD arms, and 24/24 USDCAD arms. Not a
single arm produced even 3/5 fold-positive point estimates; the
maximum observed was 1/5 folds positive on a handful of EURUSD arms.
Under PROTOCOL §6 the `parked_low_yield` label requires either a
positive pooled point estimate with a CI including 0, or
positive-in-3-folds — neither obtains, so the residual label is
`dead` for all 72 cells.

Numeric detail:
[`../../programs/E024/results.json`](../../programs/E024/results.json).
Narrative + mechanism diagnostics + fire-rate + FP-rate + path
fidelity audit: [`REPORT.md`](./REPORT.md).

## Why

**Two mechanisms combine to produce the population-level negative:**

1. **Tail cap ≠ new edge.** The stall detector does cap the worst-decile
   tail — the tail-mean R (worst 10 %) moves from −2.00 to −1.00 on
   every arm (positive R at close-at-market when activated ≥ 1.30R).
   That gain aggregates to ≈ 15–30 R across the 20–160 trades any
   given arm rescues.
2. **Near-miss cohort is 44:1 clean-TP over give-back.** In PRE-0's
   in-window GBPUSD trades, the strict `mfe_r ∈ [1.45, 1.50]` bucket
   contains 12 near-miss give-backs versus 525 clean TPs (mfe_r ≥ 1.45
   with exit_reason == "tp"). Any detector armed in the near-miss zone
   fires overwhelmingly on trades that would have reached TP. The
   anchor arm `a=1.45, S1, s=3600` on GBPUSD has n_fires = 28 of which
   **22 (78.6 %) landed on baseline-TP trades** — the pre-registered
   H3 "false-positive-heavy" pathology.

Every single arm exceeds 60 % Δ P(false positive) on every symbol —
most exceed 75 %. If any arm had otherwise satisfied the `alive` gate
on ΔSharpe (none did), PROTOCOL §6 (H3) would have downgraded it to
`parked_false_positive_heavy`. As it stands, all 72 cells resolve to
`dead` under the pre-registered label rules.

The Δ Sharpe cost is remarkably uniform: every arm on every symbol
lands in a ~0.01-wide band below zero within-symbol. This
uniformity — as with E020 — is diagnostic: the mechanism's fundamental
interaction with the deployed cell's TP=1.5R geometry is the issue,
not the specific `activation_R`, `stall_secs`, or signal family.
Grid-tuning will not rescue it.

## What we DO NOT do

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5:

1. **NOT** running stage 2 (the exit-action sweep of `move_stop_to_current`
   and `move_stop_to_mfe_minus_2p` on a winning stage-1 detector).
   Zero stage-1 arms are `alive`; stage 2 is deterministically
   cancelled per PROTOCOL §5.4 last paragraph.
2. **NOT** extending the 24-arm stage-1 grid to search for a positive
   arm.
3. **NOT** promoting Δ tail-mean R (a large positive secondary
   guardrail: +1.00R across all arms) to primary post hoc.
4. **NOT** promoting Δ P(worse-than-stall-trigger) to primary despite
   its ~30 % rate on the fired-trade subset.
5. **NOT** shipping any stall variant to the deployed cell. Phase 3
   (live-agent wiring: `mfe_ts` capture in `PositionMonitor._track_excursion`
   + exit-priority hook) is gated on an `alive` verdict per PROTOCOL
   §2 and MANIFEST — that gate does not open.
6. **NOT** re-running Phase 2 with a modified rule spec (that would
   be a NEW study, requiring fresh pre-registration).
7. **NOT** claiming a partial win from any single arm or any single
   symbol — no arm has a positive point estimate on any symbol, let
   alone a subset of symbols surviving the four-leg gate.

## What we DO

1. Keep the shipped `all_on` cell (EURUSD/GBPUSD/USDCAD, H4,
   `zone_d1_against`, wick-proof SL + BE-at-1R + PLG) with fixed 1.5R
   TP — the exact posture E004/E005 sealed.
2. Register this study as `stopped_dead` in the campaign registry
   (EXPERIMENTS.md row updated in the coordinator's commit).
3. Preserve `results.json`, `REPORT.md`, and this `STOP_NOTICE.md` on
   `main` for future meta-analysis.
4. Note the descriptive-only status of PROTOCOL §5.5 (Case A GBPUSD
   2969136564, Case B GBPUSD 2966547972): both live-agent 2026-07
   tickets are outside PRE-0's window (2015-01 → 2025-12) and cannot
   be literally replayed. The population-level analogue of "branch B2"
   (78.6 % of GBPUSD anchor-arm fires land on clean-TP trades) is the
   representative reading.

## Family-multiplicity impact on E025

E024's dead verdict removes 24 arms from the campaign's search-width
argument. E025 (joint exit-stack Pareto) cannot include an E024 stall
component. If E020's earlier note applied (E025 family size adjusted
by −12 arms after E020), the additional −24 from E024 further trims
the E025 effective family size. E025's protocol should re-check its
deflated-Sharpe argument when its pre-registration is drawn up.

## What this triangulates against E020

E020 (MFE ratchet trailing stop, `dead`) and E024 (near-TP stall
exit, `dead`) attack the same "give-back after MFE" pathology via
different mechanisms:

- E020: continuous MFE-tightening → **runner-choke** pathology (chops
  legitimate late-extension runners into 0.4–0.9 R exits).
- E024: near-TP failure-to-extend detector → **false-positive**
  pathology (chops clean TPs at ~78 % rate on the fired cohort).

Both fail because the deployed cell's fixed 1.5R TP is close enough
to the natural near-miss zone that any "clip early" intervention
cannibalises more clean TPs than it saves give-backs. Any future
proposal in this campaign group (E023 post-BE structure trail; a
future E026 anchored on a non-MFE signal) must confront this joint
constraint or provide a mechanism-level argument for why it escapes.
