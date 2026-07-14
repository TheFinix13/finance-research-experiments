#!/usr/bin/env bash
# Launch 7 leave-one-out replays in parallel for arm4 aggregator.
set -u
cd /Users/the1finix/Documents/GitHub/finance-research-experiments
export PYTHONPATH=/Users/the1finix/Documents/GitHub/finance-research-experiments
PY=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python
LOGDIR=programs/M001_multi_agent_ensemble/reviews/loo_logs
mkdir -p "$LOGDIR"
AGENTS=(isagi_yoichi bachira_meguru itoshi_rin chigiri_hyoma reo_mikage nagi_seishiro barou_shoei)
PIDS=()
for a in "${AGENTS[@]}"; do
  logf="$LOGDIR/arm4_${a}.log"
  echo "launch arm4 lo1=$a -> $logf"
  /usr/bin/nohup /bin/bash -c "exec '$PY' -m programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out \
    --tag g7retry1-arm4 \
    --baseline-cache-dir programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-arm4 \
    --exclude '$a' \
    --no-aggregate \
    --aggregator-arm arm4 \
    --retire-kunigami \
    -v" >"$logf" 2>&1 </dev/null &
  disown
  PIDS+=($!)
  sleep 6
done
echo "arm4 PIDS: ${PIDS[*]}"
printf '%s\n' "${PIDS[@]}" > "$LOGDIR/arm4.pids"
