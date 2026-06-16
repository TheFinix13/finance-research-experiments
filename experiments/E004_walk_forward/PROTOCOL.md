# E004 — Walk-forward validation (retrospective protocol)

Status: **executed-then-registered 2026-06-16**.

## Design

- **Windows:** 7 rolling 4-year IS / 1-year OOS
- **Script:** `multi-pair-trading-agent/scripts/run_walk_forward.py`
- **Analysis:** `scripts/analyze_walk_forward.py`

## Claim tested

Robust cells show positive OOS expectancy in most windows, not just one
holdout slice.

## Primary deployed outcome

`zone_d1_against / H4 / all`: **7/7 positive OOS windows**, median
**+11.34 pips/trade**, ~66 trades/year.

## Agent reference

`docs/reviews/2026-06-09_walk_forward.md` · `docs/reviews/walk_forward_raw.json`
