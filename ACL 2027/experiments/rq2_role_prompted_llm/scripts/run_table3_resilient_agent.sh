#!/usr/bin/env bash
set -u

WORKSPACE="/Users/tom/Documents/GitHub/ACL2027"
QUEUE_SCRIPT="ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py"
STORAGE="ACL 2027/Storage/draft_review_packets"
QUEUE_NAME="${QUEUE_NAME:-table3_resilient_n100_20260902}"
MAX_RESTARTS="${MAX_RESTARTS:-30}"
SLEEP_SECONDS="${SLEEP_SECONDS:-20}"

cd "$WORKSPACE" || exit 1

WATCHDOG_LOG="$STORAGE/${QUEUE_NAME}.watchdog.log"
QUEUE_LOG="$STORAGE/${QUEUE_NAME}.log"
NOHUP_LOG="$STORAGE/${QUEUE_NAME}.nohup.log"

mkdir -p "$STORAGE"
printf '[%s] resilient_agent_start queue=%s max_restarts=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$MAX_RESTARTS" >> "$WATCHDOG_LOG"

restart_count=0
while [ "$restart_count" -lt "$MAX_RESTARTS" ]; do
  if [ -f "$QUEUE_LOG" ] && tail -n 20 "$QUEUE_LOG" | grep -q 'all_usable_table3_queue_complete'; then
    printf '[%s] resilient_agent_complete queue=%s restarts=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$restart_count" >> "$WATCHDOG_LOG"
    exit 0
  fi

  printf '[%s] queue_run_start queue=%s attempt=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$((restart_count + 1))" >> "$WATCHDOG_LOG"
  python3 "$QUEUE_SCRIPT" \
    --max-stage 100 \
    --queue-name "$QUEUE_NAME" \
    --skip-quality-judge \
    --timeout 240 \
    --num-predict 256 \
    >> "$NOHUP_LOG" 2>&1
  exit_code=$?
  printf '[%s] queue_run_exit queue=%s attempt=%s exit_code=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$((restart_count + 1))" "$exit_code" >> "$WATCHDOG_LOG"

  if [ -f "$QUEUE_LOG" ] && tail -n 20 "$QUEUE_LOG" | grep -q 'all_usable_table3_queue_complete'; then
    printf '[%s] resilient_agent_complete queue=%s restarts=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$restart_count" >> "$WATCHDOG_LOG"
    exit 0
  fi

  restart_count=$((restart_count + 1))
  sleep "$SLEEP_SECONDS"
done

printf '[%s] resilient_agent_gave_up queue=%s max_restarts=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$QUEUE_NAME" "$MAX_RESTARTS" >> "$WATCHDOG_LOG"
exit 1
