#!/usr/bin/env bash
# Launch 14 leave-one-out replays (7 per aggregator arm) for the G7
# third gate attempt (tag g7retry2, PROTOCOL §11.17).
set -u
cd /Users/the1finix/Documents/GitHub/finance-research-experiments
export PYTHONPATH=/Users/the1finix/Documents/GitHub/finance-research-experiments
PY=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python
LOGDIR=programs/M001_multi_agent_ensemble/reviews/loo_logs
mkdir -p "$LOGDIR"
AGENTS=(isagi_yoichi bachira_meguru itoshi_rin chigiri_hyoma reo_mikage nagi_seishiro barou_shoei)
PIDS=()
for arm in phi41 arm4; do
  for a in "${AGENTS[@]}"; do
    logf="$LOGDIR/g7retry2_${arm}_${a}.log"
    echo "launch $arm lo1=$a -> $logf"
    /usr/bin/nohup /bin/bash -c "exec '$PY' -m programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out \
      --tag g7retry2-${arm} \
      --baseline-cache-dir programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry2-${arm} \
      --exclude '$a' \
      --no-aggregate \
      --aggregator-arm ${arm} \
      --retire-kunigami \
      -v" >"$logf" 2>&1 </dev/null &
    disown
    PIDS+=($!)
    sleep 4
  done
done
echo "g7retry2 LOO PIDS: ${PIDS[*]}"
printf '%s\n' "${PIDS[@]}" > "$LOGDIR/g7retry2_loo.pids"

# Heartbeat monitor (brain-box canonical protocol) over all 14 jobs.
MARGS=()
i=0
for arm in phi41 arm4; do
  for a in "${AGENTS[@]}"; do
    pid="${PIDS[$i]}"
    MARGS+=(--pid "$pid:g7retry2_${arm}_${a}")
    MARGS+=(--output-artefact "$pid:programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry2-${arm}/lo1_${a}/trades.jsonl")
    MARGS+=(--tail-on-exit "$pid:$LOGDIR/g7retry2_${arm}_${a}.log:200")
    i=$((i+1))
  done
done
/usr/bin/nohup python3 /Users/the1finix/Documents/GitHub/brain-box/meta/tools/monitor_compute_jobs.py \
  "${MARGS[@]}" \
  --notify --interval 30 --cpu-floor 20 --stall-samples 4 \
  --jsonl programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.jsonl \
  --log programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.log \
  >"$LOGDIR/g7retry2_loo_monitor.log" 2>&1 </dev/null &
disown
echo "monitor pid: $!"
