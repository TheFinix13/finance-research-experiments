# E026 — Opening-range breakout baseline

Status: **pre-registration in progress** — Gate 1 literature drafted; **no Stage-1 data run authorised**.  
Follow `PROTOCOL_DISCIPLINE.md`. Source brief: reel-intel `analysis/research-briefs/orb-baseline-brief.md`.

Gates (stop for Claude review after each):

| Gate | File | Status |
|---|---|---|
| 1 literature | [gates/01_literature.md](gates/01_literature.md) | **ACCEPTED with 5 amendments** ([Claude review](gates/01_literature_claude_review.md), 2026-10-27) |
| 2 data | [gates/02_data.md](gates/02_data.md) | DRAFT — awaiting Claude (2026-10-27) |
| 3 implementation | gates/03_implementation.md | not started |
| 4 compatibility | gates/04_compatibility.md | not started |
| 5 experiment | gates/05_experiment.md | not started |

## 1. Hypothesis (operational)

See Gate 1. Locked only after Gates 1–4 are accepted.

## 2. Separation

- Does not touch the trading agent execution path.
- Equity ORB uses a new data slice (Gate 2). Forex session-open arm must ledger-cite existing bar coverage.

## 3. Locked parameters

Deferred to Gate 3–4 (paper defaults: 5-minute range, top-20 relative volume, 14-day RVOL window).

## 4. Statistical pipeline

Deferred to Gate 5 (primary metric: net annualised Sharpe with block-bootstrap interval; pass line written in the brief).

## 5. Stop rules

- Any gate rejected by Claude → amend gate doc, do not peek at outcomes.
- If Gate 5 fail → report honestly; do not tune ORB into production.

## 6. Amendments

- **2026-10-27 (Gate 1 review, Claude — all five accepted):**
  1. H0/H1 split from the Gate 5 pass line (H0: net Sharpe ≤ 0).
  2. Only 2024→latest is genuinely held out (paper selected on 2016–2023);
     spent once, wide interval acknowledged in advance.
  3. Added citations: Bailey & López de Prado 2014 (deflated Sharpe),
     Harvey/Liu/Zhu 2016 (multiple-testing hurdles), Barber/Lee/Liu/Odean
     (Taiwan counter-prior); precursor QQQ paper confirmed as SSRN 4416622.
  4. Two controls pre-registered: shuffled-direction and random-time arms.
  5. Data provider, cost, coverage, delistings named before Gate 2 closes
     (Gate 2 §3: Massive/Polygon, Starter $29/mo recommended, Fiyin pays).

**Pre-registration commit:** _(none — no git commit by Cursor without Fiyin ask)_
