#!/usr/bin/env bash
set -euo pipefail

# Pending queue for table-fillable working runs across all usable datasets.
#
# This does not start model calls by itself. It records the queue and waits until
# the release file exists. After release, it still waits for any active reviewer
# before running the table-fillable primary queue.

ROOT="/Users/tom/Documents/GitHub/ACL2027/ACL 2027"
RUNNER="$ROOT/experiments/rq2_role_prompted_llm/scripts/run_table_fillable_primary_queue.sh"
STORAGE="$ROOT/Storage/draft_review_packets"
LOG="$STORAGE/all_available_table3_pending_queue.log"
RELEASE_FILE="$STORAGE/all_available_table3_pending_queue.release"

log() {
  date "+%Y-%m-%d %H:%M:%S KST $*" >> "$LOG"
}

log "pending_queue_registered datasets=dreaddit_dev100_working_v1,goemotions_dev100_working_v1,agyw_focus_groups_eval100_working_v1,parlamint_gb_fullsample_eval100_working_v1 methods=Generalist,Fixed_role,All_roles model=qwen3:8b"
log "waiting_for_release_file $RELEASE_FILE"

while [[ ! -f "$RELEASE_FILE" ]]; do
  sleep 60
  log "still_pending_release"
done

log "release_seen waiting_for_active_reviewer_to_finish"
while pgrep -f "[r]un_working_generalist_reviews.py" >/dev/null; do
  sleep 60
  log "waiting_for_existing_reviewer"
done

log "starting_table_fillable_primary_queue"
exec "$RUNNER" >> "$LOG" 2>&1
