#!/usr/bin/env bash
set -u
set -o pipefail

WORKSPACE="/Users/tom/Documents/GitHub/ACL2027"
STORAGE="$WORKSPACE/ACL 2027/Storage/draft_review_packets"
FINALIZER="$WORKSPACE/ACL 2027/experiments/rq2_role_prompted_llm/scripts/finalize_table3_warrantroute.py"
SOURCE_QUEUE_NAME="${SOURCE_QUEUE_NAME:-table3_resilient_n100_20260902}"
AGENT_NAME="${AGENT_NAME:-table3_warrantroute_n100_postprocess}"
POLL_SECONDS="${POLL_SECONDS:-30}"
RETRY_SECONDS="${RETRY_SECONDS:-60}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-100}"

SOURCE_QUEUE_LOG="$STORAGE/${SOURCE_QUEUE_NAME}.log"
SOURCE_WATCHDOG_LOG="$STORAGE/${SOURCE_QUEUE_NAME}.watchdog.log"
AGENT_LOG="$STORAGE/${AGENT_NAME}.agent.log"
FINALIZER_LOG="$STORAGE/table3_warrantroute_n100_finalize.log"

mkdir -p "$STORAGE"
printf '[%s] postprocess_agent_start source_queue=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SOURCE_QUEUE_NAME" >> "$AGENT_LOG"

while true; do
  queue_complete=0
  queue_gave_up=0
  queue_running=0
  reviewer_running=0

  if [ -f "$SOURCE_QUEUE_LOG" ] && grep -q 'all_usable_table3_queue_complete' "$SOURCE_QUEUE_LOG"; then
    queue_complete=1
  fi
  if [ -f "$SOURCE_WATCHDOG_LOG" ] && grep -q 'resilient_agent_gave_up' "$SOURCE_WATCHDOG_LOG"; then
    queue_gave_up=1
  fi
  if pgrep -f 'run_all_usable_table3_queue.py' >/dev/null 2>&1; then
    queue_running=1
  fi
  if pgrep -f 'run_working_generalist_reviews.py' >/dev/null 2>&1; then
    reviewer_running=1
  fi

  if [ "$queue_running" -eq 0 ] && [ "$reviewer_running" -eq 0 ] && \
     { [ "$queue_complete" -eq 1 ] || [ "$queue_gave_up" -eq 1 ]; }; then
    break
  fi
  printf '[%s] waiting queue_complete=%s queue_gave_up=%s queue_running=%s reviewer_running=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$queue_complete" "$queue_gave_up" \
    "$queue_running" "$reviewer_running" >> "$AGENT_LOG"
  sleep "$POLL_SECONDS"
done

printf '[%s] source_queue_idle starting_finalizer\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$AGENT_LOG"

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  printf '[%s] finalizer_attempt=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$attempt" >> "$AGENT_LOG"
  python3 "$FINALIZER" \
    --sample-n 100 \
    --repair-invalid \
    --max-repair-rounds 5 \
    --timeout 240 \
    --num-predict 256 \
    --log-path "$FINALIZER_LOG" \
    >> "$AGENT_LOG" 2>&1
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then
    printf '[%s] postprocess_agent_complete attempts=%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$attempt" >> "$AGENT_LOG"
    exit 0
  fi
  printf '[%s] finalizer_failed attempt=%s exit_code=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$attempt" "$exit_code" >> "$AGENT_LOG"
  attempt=$((attempt + 1))
  sleep "$RETRY_SECONDS"
done

printf '[%s] postprocess_agent_gave_up max_attempts=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MAX_ATTEMPTS" >> "$AGENT_LOG"
exit 1

