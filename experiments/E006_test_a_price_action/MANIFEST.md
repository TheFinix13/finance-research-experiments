# E006 manifest — price-action confluence (Test A)

| Field | Value |
|---|---|
| Pre-registered | 2026-06-12 (`PROTOCOL.md` in this folder) |
| Pre-reg commit | confluence-lab history (see git log for `PROTOCOL.md`) |
| Report | `REPORT.md` (canonical; root `REPORT.md` redirects here) |

## Code (lab)

| Component | Path |
|---|---|
| Detectors | `conflab/detectors_*.py`, `conflab/events.py` |
| Stage 1 | `conflab/screening.py`, `scripts/run_stage1.py` |
| Stage 2 | `conflab/stage2.py`, `scripts/run_stage2.py` |

## Evidence

| Artifact | Location |
|---|---|
| Canonical hour-matched registry | `results/stage1_EURUSD_screen_hourmatched_2026-06-12_1340.jsonl` (copy) |
| Full registry set | `../../output/stage1_*.jsonl` |
| Summary figure | `results/stage1_summary.png` (copy) · `../../output/stage1_summary.png` |
| Stage 2 exploratory | `../../output/stage2_EURUSD_2026-06-12_1348.jsonl` |

## Verdict

5/284 alive (hour-matched); effects gate-sized only — see `REPORT.md`.
