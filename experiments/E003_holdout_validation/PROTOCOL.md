# E003 — Holdout validation (retrospective protocol)

Status: **executed-then-registered 2026-06-16**.

## Design

- **IS:** 2015-01-01 → 2022-12-31
- **OOS:** 2023-01-01 → 2025-12-31
- **Script:** `eurusd-ai-agent/scripts/run_holdout_validation.py`
- **Input:** IS-survivors from E002-style grid (8 cells)

## Claim tested

IS-significant cells repeat positive expectancy OOS.

## Result (as executed)

**1 of 8** IS-survivors validated OOS: `zone_d1_against / H4 / asia`.
Large D1 cells collapsed (+25 IS expectancy → +1 OOS) — selection bias lesson.

## Agent reference

`docs/00-journey.md` §6.2
