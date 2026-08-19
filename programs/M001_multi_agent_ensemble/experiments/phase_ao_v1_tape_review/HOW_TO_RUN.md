# Phase AO — how to run a weekly review

Observation only. Needs two directories copied off the VM (Tailscale
or a USB stick). The harness does not talk to either live agent.

## Inputs

1. **v1 journal** — `C:\Users\<you>\Documents\TradingAgentLogs\` day
   files live under the v1 clone's `data\journal\live\` (or the weekly
   report zip's `journal/` folder). Files named `YYYY-MM-DD.jsonl`.
2. **squad tape** — `%USERPROFILE%\Documents\TradingAgentLogs\squad_live\`
   containing `proposals_all.jsonl`, `proposals_rejected.jsonl`,
   `trades.jsonl`.

Copy both to the research Mac, then from repo root on
`multi-agent-ensemble`:

```bash
python3 programs/M001_multi_agent_ensemble/experiments/phase_ao_v1_tape_review/tape_review.py \
  --v1-journal /path/to/journal/live \
  --squad-live /path/to/squad_live \
  --start 2026-08-01 --end 2026-08-10 \
  --out programs/M001_multi_agent_ensemble/experiments/phase_ao_v1_tape_review/results/2026-08-01_to_2026-08-10
```

Gaps (Aug 3 DNS death, weekend) mark affected trades `tape_gap` and
drop them from advice totals — never guessed.

No review has been computed yet: the Aug 1–10 tapes were inspected in
chat but not copied onto this host as a durable input.
