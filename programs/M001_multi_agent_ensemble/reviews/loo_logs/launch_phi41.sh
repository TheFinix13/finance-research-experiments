#!/usr/bin/env bash
# Launch 7 leave-one-out replays in parallel for phi41 aggregator.
# Each writes to programs/.../reviews/g7_leave_one_out_g7retry1-phi41/lo1_<agent>/.
set -u
cd /Users/the1finix/Documents/GitHub/finance-research-experiments
export PYTHONPATH=/Users/the1finix/Documents/GitHub/finance-research-experiments
PY=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python
LOGDIR=programs/M001_multi_agent_ensemble/reviews/loo_logs
mkdir -p "$LOGDIR"
AGENTS=(isagi_yoichi bachira_meguru itoshi_rin chigiri_hyoma reo_mikage nagi_seishiro barou_shoei)
PIDS=()
for a in "${AGENTS[@]}"; do
  logf="$LOGDIR/phi41_${a}.log"
  echo "launch phi41 lo1=$a -> $logf"
  /usr/bin/nohup /bin/bash -c "exec '$PY' -m programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out \
    --tag g7retry1-phi41 \
    --baseline-cache-dir programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-phi41 \
    --exclude '$a' \
    --no-aggregate \
    --aggregator-arm phi41 \
    --retire-kunigami \
    -v" >"$logf" 2>&1 </dev/null &
  disown
  PIDS+=($!)
  sleep 6
done
echo "phi41 PIDS: ${PIDS[*]}"
printf '%s\n' "${PIDS[@]}" > "$LOGDIR/phi41.pids"
