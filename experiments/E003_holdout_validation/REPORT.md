# E003 — Report: holdout validation

## Headline

> **Single holdout split validated only H4/asia — later shown to be selection
> bias from one OOS window (E004).**

## Numbers

| Metric | Value |
|---|---|
| IS survivors tested | 8 |
| OOS validated | 1 (`zone_d1_against / H4 / asia`) |
| D1 collapse example | +25 IS → +1 OOS expectancy |

## Lesson

Picking best cells on a window and testing one OOS slice **is** selection
bias. Motivated walk-forward (E004).

## Verdict

**Complete.** Historical; deployment cell updated by E004.
