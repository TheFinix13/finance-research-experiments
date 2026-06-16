# E005 — Frozen cross-pair + sealed 2026 look (retrospective protocol)

Status: **executed-then-registered 2026-06-16**.

## Part A — Frozen cross-pair

- **Script:** `multi-pair-trading-agent/scripts/run_cross_pair_frozen.py`
- **Config:** byte-for-byte `zone_d1_against` H4 — zero re-tuning
- **Pairs:** GBPUSD, USDCAD (primary); AUDUSD, NZDUSD (expansion test)
- **Costs:** scaled UP vs EURUSD (conservative)
- **Window:** full history per pair (entire history OOS for params)

## Part B — Sealed 2026 first look (EURUSD)

- **Window:** Jan–Jun 2026 (per `EvalConfig` sealed split)
- **Purpose:** live-adjacent monitor, not parameter fit

## Agent references

`docs/reviews/2026-06-10_cross_pair_frozen.md`
`docs/reviews/2026-06-10_similar_pairs_frozen.md`
