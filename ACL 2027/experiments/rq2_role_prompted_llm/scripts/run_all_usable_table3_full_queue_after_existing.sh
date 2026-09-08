#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/tom/Documents/GitHub/ACL2027"
SCRIPT="$ROOT/ACL 2027/experiments/rq2_role_prompted_llm/scripts/run_all_usable_table3_queue.py"
STORAGE="$ROOT/ACL 2027/Storage/draft_review_packets"
LOG="$STORAGE/all_usable_table3_full_queue.log"

export PATH="/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/bin:/bin:/usr/sbin:/sbin"

log() {
  date "+%Y-%m-%d %H:%M:%S KST $*" >> "$LOG"
}

log "full_queue_wrapper_start"
while screen -ls | grep -E -q '[.](dreaddit_dev580|all_usable_table_n25_waiting|all_usable_table_n25_queue|table3_primary_qwen_queue)'; do
  log "waiting_for_prior_screen"
  sleep 60
done

while pgrep -f "[a]ll_usable_table_n25_waiting|[r]un_all_usable_table_fillable_n25_queue.sh|[r]un_dreaddit_dev580_role_methods.sh|[r]un_table_fillable_primary_queue.sh" >/dev/null; do
  log "waiting_for_prior_table_queue"
  sleep 60
done

while pgrep -f "[r]un_working_generalist_reviews.py" >/dev/null; do
  log "waiting_for_existing_reviewer"
  sleep 60
done

log "starting_all_usable_table3_queue"
python3 "$SCRIPT" >> "$LOG" 2>&1
log "full_queue_wrapper_complete"
