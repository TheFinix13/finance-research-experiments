# E032 — STOP NOTICE

**Stopped 2026-08-04 at the Stage-1 go/no-go: 0/12 cells alive → DEAD.**
Stop rule §5 ("Stage 1: 0/12 cells alive → STOP") fired. Confirm and
sealed reservations RELEASED un-consumed — zero OOS cost.

Pre-registration commit `c838b28` (protocol frozen before any
computation, priors AGAINST on record); harness + this notice
committed together 2026-08-04.

---

## 1. What was tested

Whether a D1-aligned H4 breakout-continuation entry (close above the
prior-N-bar high, in the production D1-trend direction, bar range
≥ k × ATR14; structure SL floored at 10p; fixed 1.5R TP) has positive
per-trade expectancy at base costs. 12 cells: N ∈ {10, 20} ×
k ∈ {1.0, 1.5} × {EURUSD, GBPUSD, USDCAD}, screen 2015-01-01 →
2021-12-31, BH-FDR α = 0.05 across the family.

## 2. Stage 1 — screen: 0/12 cells alive

All cells clear the n ≥ 100 gate. One-sided bootstrap p for
mean pips/trade > 0 (10,000 reps, seed 32):

| Cell | n | Mean pips | p | Folds + | Verdict |
|---|---|---|---|---|---|
| EURUSD N10 k1.0 | 374 | +0.4 | 0.479 | 3/5 | dead |
| EURUSD N10 k1.5 | 261 | +1.3 | 0.416 | 4/5 | dead |
| EURUSD N20 k1.0 | 313 | +1.7 | 0.363 | 3/5 | dead |
| EURUSD N20 k1.5 | 221 | +3.0 | 0.325 | 3/5 | dead |
| GBPUSD N10 k1.0 | 230 | +9.9 | 0.161 | 2/5 | dead |
| GBPUSD N10 k1.5 | 167 | +17.6 | 0.088 | 3/5 | dead |
| GBPUSD N20 k1.0 | 183 | +11.9 | 0.166 | 2/5 | dead |
| GBPUSD N20 k1.5 | 131 | +20.4 | 0.104 | 4/5 | dead |
| USDCAD N10 k1.0 | 402 | +4.5 | 0.149 | 2/5 | dead |
| USDCAD N10 k1.5 | 266 | +7.9 | 0.107 | 3/5 | dead |
| USDCAD N20 k1.0 | 329 | +6.1 | 0.113 | 3/5 | dead |
| USDCAD N20 k1.5 | 222 | +13.3 | 0.034 | 3/5 | dead |

Best single cell (USDCAD N20 k1.5, raw p = 0.034) is nowhere near its
BH threshold (0.0042 for rank 1 of 12). No cell reaches 4/5 folds AND
a BH pass.

## 3. Interpretation

- **Descriptive pattern, stated for honesty and NOT verdict-bearing:**
  every mean is positive, and means rise monotonically with both N and
  k on all three symbols (stricter breakout + bigger impulse → better
  trades). The direction of the folk intuition is right; the
  magnitude, at 1.5R fixed-target geometry and base costs, is
  indistinguishable from noise over 7 years.
- This is consistent with all three recorded priors AGAINST (E004
  with-mode, E030 session drift dead, Chigiri v1 TQS 0.229). The
  motivating 2026-07-28 → 08-03 live week (three hand-picked +1.5R
  counterfactuals) was a tail sample from the best trending week of
  the run, and stays BURNT.

## 4. Consequences

- **No `htf_with_breakout` cell candidate. v1 stays fade-only** — the
  "we're missing the big moves" complaint is now closed with evidence
  under this operationalisation (folk-concept clause: this
  definition, not every conceivable with-trend entry).
- Any future re-open needs a materially different mechanism — e.g.
  Chigiri's full conjunctive-guard refinement (multi-TF ADX rising +
  top-decile σ + 20-bar extreme) or trailing exits instead of fixed
  1.5R, and preferably fresh data real estate (the screen slice is
  now on its 9th registered EURUSD use).
- The E031/E032 joint-interaction clause is moot (E031 also stopped).

## 5. Deviations from protocol

None. Grid, filters, geometry, costs and stop rules ran exactly as
pre-registered. (ATR14 operationalised as SMA of true range —
granularity the protocol left open; recorded in MANIFEST.)
