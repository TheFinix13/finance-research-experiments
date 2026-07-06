# Phase X-kunigami Wild Card gate — POSTMORTEM (AMBIGUOUS)

**Date:** 2026-07-06 night.
**Verdict:** **AMBIGUOUS** per PROTOCOL.md sec 5 (locked rules), from
`../../reviews/kunigate_arm4_verdict.{json,md}`. Per the locked rules
this triggers a postmortem and forbids retuning the trip/release
levels. No constants were changed at any point.

## 1. What was run

- Gated walk-forward, tag `kunigate-arm4`, vs canonical baseline
  `phi5-arm4-post-kunigami` (identical env: Arm 4, 7-agent roster,
  2015–2025 panel, 53,164 bars). Implementation committed before
  compute (`5769f9f`); analyzer committed while the run was in flight,
  before results were known (`c55575a`). Heartbeat monitor attached
  for the full ~23 min run (healthy: 94–99% CPU throughout).

## 2. Numbers

| metric | baseline | gated |
|---|---:|---:|
| worst-window max DD | 169.8% | 169.8% |
| median-of-window-mean TQS | 0.3643 | 0.3643 |
| trades | 7,273 | 7,272 |
| gate trips | — | 2 |
| gate vetoes journalled | — | 9 |

All 9 vetoes fall on 2015-02-17/18 — inside the panel's first weeks,
four YEARS before the first OOS window (2019). Zero OOS-window trades
were affected; every per-window DD figure is byte-identical to
baseline. LAND fails only on the DD-reduction check; neither REVERT
condition fires; the gate DID trip, so the sec 5 stop rule
(NOT-MEASURABLE) does not apply. Hence AMBIGUOUS.

## 3. Root cause — additive pips vs multiplicative drawdown

The mechanic (locked, sec 2) tracks the **full-panel running** equity
curve: $100 start, +$1 per pip, never reset. Fixed-lot pnl is
**additive**, but the trip condition — DD >= 25% **of running peak** —
is **multiplicative**. Early on, when peak is near $100, a ~25-pip
losing cluster trips the gate (observed: trips at 45.4% and 40.9% DD
in Feb 2015). But the squad nets ~55,000 pips over the panel, so by
2019 (first OOS window) the peak is in the thousands of dollars and a
25% relative DD requires **thousands of pips** of drawdown — orders of
magnitude beyond any losing streak the squad produces. The gate is
therefore structurally inert over the entire OOS evaluation region.

The Φ5 §11.5 finding that motivated this phase — every window breaches
25% DD — was measured on **per-window curves reset to $100** (the
analyzer's convention, inherited by this phase's verdict statistic).
The pre-registered mechanic and the pre-registered statistic silently
used two different equity-curve conventions. That mismatch is the
experiment's real finding.

## 4. What this does and does not say

- It does NOT say drawdown gating is useless — the gate demonstrably
  fires and vetoes correctly when equity is near its base (Feb 2015),
  and the implementation is verified by 12 unit tests.
- It DOES say: on a fixed-lot additive-pnl curve, a peak-relative DD
  trigger only has teeth near the curve's origin. A faithful defender
  for this sandbox needs a **windowed base** (e.g. DD measured against
  a rolling N-week peak) or a **dollar-denominated** trip (e.g. -$25
  from rolling peak), either of which is a NEW mechanic requiring a
  fresh pre-registration — explicitly not tuned or tried here.
- Production relevance is limited anyway: the live agent sizes risk
  as a percentage of equity (adaptive lots), where relative DD and
  pnl move on the same scale and a peak-relative gate stays sensitive
  for the account's life. The sandbox's fixed-lot convention is the
  distorting factor.

## 5. Disposition

- Gate code stays in the driver behind `--kunigami-gate` (default
  OFF; all sealed caches byte-identical — verified by the identical
  baseline numbers above).
- Kunigami's roster status is unchanged: retired proposer/publisher,
  Sentinel R5 side channel retained. The `wildcard_defender` role
  label is NOT granted (sec 6 required a LAND).
- Any Phase X v2 (rolling-base or dollar-trip variant) requires a new
  pre-registered protocol. Parked — not started without discussion.
