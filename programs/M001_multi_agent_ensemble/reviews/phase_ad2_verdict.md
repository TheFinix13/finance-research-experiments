# Phase AD.2 verdict — NULL (Stage 2 gate CLOSED), evaluated once 2026-07-28

Pre-registration: `experiments/phase_ad2_karasu_window_semantics/PROTOCOL.md`
(incl. §1b pre-run amendment). Program: M001. Trading-agent linkage:
intake I020 (resolved), decisions D130/D131 on `product`.

## 1. Result

Stage 1 disagreement audit per PROTOCOL §2, run once
(`stage1_audit.py` → `results_stage1.json`):

| Metric | Value | Gate |
|---|---|---|
| Evaluation points (H4 open labels × 3 symbols, 2015-02..2025-12, weekends excluded) | 51,042 | — |
| Ladder fires under **A** (current: bar-open anchor) | **0** | — |
| Ladder fires under **B** (entry-moment anchor) | **0** | — |
| **S1** disagreement A vs B | **0 (0.0000 %)** | < 1 % ✓ |
| **S2** flipped admissions among 5,236 admitted trades | **0** | = 0 ✓ |
| Audit column: fires under **C** (holding-window) | 1,035 points; 166 admitted trades intersected | non-decisive |

**Gate CLOSED → NULL verdict.** No Stage 2 counterfactual replay. Per
the locked rule: the A-vs-B anchor question is moot at panel scale —
trading-agent intake I020 closed as "no material divergence"; the
live path keeps semantics A unchanged.

## 2. The actual finding (stronger than the question)

The ±15-minute point-anchored window is **structurally inert on the
H4 grid for this event population, under EITHER anchor**. NFP/CPI
land at 13:30 UTC and FOMC at 18:00/19:00 UTC; on the
midnight-anchored H4 grid every anchor sits at 00/04/08/12/16/20:00,
so no event ever comes within 15 minutes of any evaluation moment —
in 11 years, across 349 events, the window never fired once. Anchor
choice cannot matter for a window that never opens.

Non-decisive audit color on C (protect the holding bar): it is the
only semantics that engages at all (1,035 points; 166 of 5,236
admitted trades ≈ 3.2 %). Honest caution before anyone proposes C as
a lever: the C-gated trades were **net winners** in the sampled flips
(first 50: +158.8 pips, mean +3.18/trade) — on this fixture a
holding-window blackout looks more likely to cost alpha than save
drawdown, consistent with Phase AE's "avoidable, not tradable" read
being about entry QUALITY rather than calendar proximity. Promoting C
would need its own pre-registration (PROTOCOL §3) and this number is
its prior AGAINST.

## 3. Scope limits (banked in §1b before the run)

- Fixture = high-impact **USD NFP/CPI/FOMC only** (349 events,
  `data/news_calendar_frozen_2026-07-24.json`). A full FF calendar
  (4–8 High/month + Medium, at more varied minute marks) could
  produce nonzero A/B fire rates — S1 here is a lower bound. The
  live tape's 03/07/…/23 grid also differs (the 2026-07-24 "PMI in
  +15 min" advisory proves A fires in live operation on the full
  calendar).
- Verdict is therefore: **the anchor question is moot for the panel
  evidence we have**; it is NOT a claim that R7 is globally inert in
  live operation.

## 4. Provenance notes

- Stage 1 executed 2026-07-28 ~17:05 UTC against the
  `multi-agent-ensemble` working tree (fixture + phi41 physical
  ledger). Minutes after the run a concurrent session checked the
  shared working tree out to `main`; the experiment's files were
  untracked and survived; no re-run occurred and none is permitted
  against the same gate (PROTOCOL §4 stop rules).
- Branch declared by the user 2026-07-28 evening; committed to
  `multi-agent-ensemble` via a dedicated worktree (shared checkout
  left untouched on `main`).
- Parent Phase AD pre-registration remains an untracked DRAFT owned
  by the 2026-07-20 session (`experiments/phase_ad_karasu_news_defender/PROTOCOL.md`)
  — deliberately not committed here (not this session's work).
