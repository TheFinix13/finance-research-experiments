# E022 — STOP NOTICE

**Date:** 2026-07-20 · **Verdict:** `dead` · **Registry status:** LOCKED

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md`, this notice records that
E022 (structure-aware TP snap, order-placement rule) failed its
pre-registered `alive` criteria and is stopped without Phase 3
(production wiring in `SignalLoop._route_signal`).

## What was found

Zero of the twelve pre-registered arms
(`snap_distance ∈ {5, 10, 15} × snap_source ∈ {daily_only, ladder_top,
round_number, all}`) achieved pooled bootstrap 95 % CI lower > 0 on
ΔSharpe of the per-trade R sequence versus the deployed mechanical
placement.

- Nine of the twelve arms produced pooled ΔSharpe with 95 % CI entirely
  below zero (range −0.011 to −0.028); seven of those survived BH-FDR
  at α = 0.10 — significant DEGRADATION, not improvement.
- Two arms (`daily_only_d5`, `all_d5`) produced small negative point
  estimates with CIs that overlap zero — no evidence of improvement.
- One arm (`ladder_top_d5`) produced a marginally positive point
  estimate (ΔSharpe = +0.0006) but fails the PROTOCOL §H3 5 %
  fire-rate floor (its actual fire rate is 3.02 %, ~2 pp below the
  feasibility floor) — registered as `inactive_snap_never_fires` per
  arm-level classification.
- The family-level `parked_snap_never_fires` outcome (PROTOCOL §H3
  first-class negative) does **not** apply, because the other 11 arms
  fire well above the 5 % floor.

Numeric detail: [`../../programs/E022/results.json`](../../programs/E022/results.json).
Narrative + mechanism diagnostics: [`REPORT.md`](./REPORT.md).

## Why

The mechanism worked as PROTOCOL §1 predicted: snap fired on a
substantial fraction of trades (up to 52 % on `all_d15`), lifted the
empirical probability of a TP fill by up to +3.5 pp, and shortened
winners' time-in-trade by ~1 H4 bar (~4 hours). The secondaries move
in the pre-registered expected direction — the rule is not broken.

The primary is unambiguously off-plan. The per-winner R cost (mean R
on winners fell by ~0.11 on the largest-firing arm) more than offsets
the fill-rate gain: aggregate R lift from ~85 extra TP-fills at ~1 R
each (~+85 R) is dominated by the R cost on ~1 400 baseline winners
losing ~0.1 R each (~−140 R). Net pooled ΔR is small in absolute
terms, decisive in Sharpe because per-trade R variance on the deployed
cell is comparatively low.

The finding is monotone in `snap_distance` inside every `snap_source`:
larger fire rates produce larger negative ΔSharpe. That monotonicity
is robust across four independent level constructions (UTC daily/weekly
anchors, reconstructed structural swings/zone-edges/trendlines,
mechanical round-number sub-figures, and the union), which is
diagnostic that the negative effect is a property of the **rule's
interaction with the deployed cell's TP=1.5 R geometry** — not a
property of any particular level source.

## What we DO NOT do

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md`:

1. **NOT** extending the arm grid to search for a positive arm (e.g.
   `snap_distance` < 5 pips, alternative `snap_offset` schedule, a
   fifth `snap_source`).
2. **NOT** promoting ΔP(TP fills) — a real +3.5 pp secondary lift on
   `all_d15` — to primary post hoc.
3. **NOT** shipping any snap variant to the deployed cell's
   `SignalLoop._route_signal`.
4. **NOT** re-running Phase 2 with a modified rule spec — that would
   be a NEW study, requiring fresh pre-registration.
5. **NOT** claiming a partial win from `ladder_top_d5`'s marginally
   positive point estimate; §H3 feasibility floor is exactly there to
   prevent that arm being promoted on a technicality.

## What we DO

1. Keep the shipped mechanical TP placement
   (`entry ± target_rr · stop_pips`, no snap) exactly as it is.
2. Register this study as `stopped_dead` in the campaign registry —
   `EXPERIMENTS.md` row updated by the coordinator in the commit
   that lands this STOP_NOTICE.
3. Preserve the results.json, REPORT.md, and this STOP_NOTICE.md on
   `main` for future meta-analysis.
4. Unblock E024 (near-TP stall exit) and E025 (joint stack) which were
   gated on this verdict per the campaign group note in
   `EXPERIMENTS.md`. Both will be evaluated on their own merits;
   neither inherits E022's failure.

## Family-multiplicity impact on E025

E022's `dead` verdict removes 12 arms from the campaign's joint search
width. E025 (joint exit-stack Pareto) can no longer include E022 as a
stack component (`π1 = A` where A = E022 is now void). E025's
compositions collapse to the remaining `alive` upstream studies (E024
if it lives, plus E021 if it lives). Effective family size for the
deflated-Sharpe argument in E025 drops by 12 arms; if E020 also stays
`dead`, the drop is 24 arms. E025 protocol should be re-visited when
it comes up.

## Harness note

This study bypasses the shared PRE-0 replay engine
(`programs/_shared/counterfactual_replay/replay.py`) for the fill
scan because that engine's `adjust_tp` action applies AFTER bar 0's
exit check (replay.py L560-565: `if i == 0: tp = rule_tp_adjust.price`),
while PROTOCOL §4.2 requires bar 0 to count. The E022 rescorer
(`programs/E022/rescorer.py`) scans `trade.path` directly — cleaner
architecture for an order-placement-only rule anyway. The design note
in the rescorer's module docstring documents the scan-window choice
(iterate the full `trade.path`, matching PROTOCOL §4.2 "inclusive on
M5 path bars") and the reason it differs from the task prompt's
suggested `bar.time < exit_time` form (which would silently drop 33 %
of EURUSD winners' same-bar-TP fills).
