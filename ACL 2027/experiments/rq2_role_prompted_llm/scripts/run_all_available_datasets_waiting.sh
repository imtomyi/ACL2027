#!/usr/bin/env bash
set -u

ROOT="/Users/tom/Documents/GitHub/ACL2027"
SCRIPT="$ROOT/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py"
STORAGE="$ROOT/ACL 2027/Storage/draft_review_packets"
LOG="$STORAGE/all_available_datasets_waiting.log"

export PATH="/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/bin:/bin:/usr/sbin:/sbin"

log() {
  date "+%Y-%m-%d %H:%M:%S KST $*" >> "$LOG"
}

log "waiting_queue_start"

while true; do
  if screen -ls | grep -q '[.]dreaddit_dev580'; then
    log "waiting_for_dreaddit_dev580_screen"
    sleep 60
    continue
  fi

  if pgrep -f "[r]un_dreaddit_dev580_role_methods.sh|[r]un_working_generalist_reviews.py|[r]un_working_quality_judge.py" >/dev/null; then
    log "waiting_for_existing_model_work"
    sleep 60
    continue
  fi

  break
done

log "starting_all_available_datasets_queue"
python3 "$SCRIPT" >> "$LOG" 2>&1
status=$?
log "all_available_datasets_queue_exit status=$status"
exit "$status"
