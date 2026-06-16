# E002 — Zone definitive grid (retrospective protocol)

Status: **executed-then-registered 2026-06-16**.

## Hypothesis

Among zone-only configurations (`zone` and `zone_d1_against`), which
(TF, session) cells survive BH-FDR 5% on the full 2015–2025 window?

## Method

- **Script:** `multi-pair-trading-agent/scripts/run_zone_all_tfs.py`
- **Window:** 2015 → 2025 (in-sample to later holdout/walk-forward)
- **Output:** 13 BH-significant cells (candidate list, not deployment list)

## Note

This step was necessary to enumerate candidates but **cannot** stand alone
as deployment evidence — see E003 (holdout) and E004 (walk-forward).

## Agent reference

`docs/00-journey.md` §6.1
