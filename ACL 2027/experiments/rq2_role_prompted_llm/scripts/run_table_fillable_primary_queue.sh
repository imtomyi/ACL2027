#!/usr/bin/env bash
set -euo pipefail
trap 'echo "$(date "+%Y-%m-%d %H:%M:%S KST") ERROR line=$LINENO status=$?"' ERR

# Queue the table-fillable primary-model working runs.
#
# This waits for any already-running reviewer process to finish before sending
# more requests to Ollama. Each corpus needs all three role outputs; Generalist,
# Fixed role, and All roles are derived table methods from those outputs.

ROOT="/Users/tom/Documents/GitHub/ACL2027/ACL 2027"
RQ2="$ROOT/experiments/rq2_role_prompted_llm"
STORAGE="$ROOT/Storage/draft_review_packets"
PY="${PYTHON:-python3}"
MODEL="qwen3:8b"
NUM_PREDICT="${NUM_PREDICT:-256}"
TIMEOUT="${TIMEOUT:-240}"

wait_for_reviewer_slot() {
  local current_pid="${1:-}"
  if [[ -n "$current_pid" ]]; then
    while kill -0 "$current_pid" 2>/dev/null; do
      date "+%Y-%m-%d %H:%M:%S KST waiting_for_existing_reviewer_pid_${current_pid}"
      sleep 60
    done
    return 0
  fi

  while pgrep -f "[r]un_working_generalist_reviews.py" >/dev/null; do
    date "+%Y-%m-%d %H:%M:%S KST waiting_for_existing_reviewer"
    sleep 60
  done
  return 0
}

run_role() {
  local bank="$1"
  local corpus="$2"
  local role="$3"
  local packet_file="$bank/by_dataset/$corpus.review_packets.jsonl"
  local output_root="$bank/reviewer_outputs/$role"

  wait_for_reviewer_slot "${WAIT_FOR_REVIEWER_PID:-}"
  date "+%Y-%m-%d %H:%M:%S KST start $corpus $role $MODEL"
  "$PY" "$RQ2/scripts/run_working_generalist_reviews.py" \
    --packet-file "$packet_file" \
    --output-root "$output_root" \
    --role "$role" \
    --models "$MODEL" \
    --timeout "$TIMEOUT" \
    --num-predict "$NUM_PREDICT"

  "$PY" "$RQ2/scripts/summarize_working_generalist_reviews.py" \
    --input-root "$output_root" \
    --output-root "$output_root/derived"
}

score_bank() {
  local bank="$1"
  "$PY" "$RQ2/scripts/score_working_detection_table.py" \
    --run-root "$bank" \
    --roles generalist qualitative_methods domain \
    --output-dir "$bank/table_exports/table3_primary_qwen_methods"

  "$PY" "$RQ2/scripts/score_working_sample_size_efficiency.py" \
    --run-root "$bank" \
    --roles generalist qualitative_methods domain \
    --balanced-sizes 25 50 75 100 \
    --random-sizes 25 \
    --random-draws 0 \
    --minimum-complete-fraction 0.9 \
    --fixed-role-selection-size 25 \
    --table-methods-only \
    --output-dir "$bank/sample_size_efficiency/table3_primary_qwen_methods"
}

run_bank() {
  local run_id="$1"
  local corpus="$2"
  local bank="$STORAGE/$run_id"

  date "+%Y-%m-%d %H:%M:%S KST bank $run_id"
  run_role "$bank" "$corpus" generalist
  run_role "$bank" "$corpus" qualitative_methods
  run_role "$bank" "$corpus" domain
  score_bank "$bank"
  date "+%Y-%m-%d %H:%M:%S KST done $run_id"
}

run_bank dreaddit_dev100_working_v1 dreaddit
run_bank goemotions_dev100_working_v1 goemotions
run_bank agyw_focus_groups_eval100_working_v1 agyw_focus_groups
run_bank parlamint_gb_fullsample_eval100_working_v1 parlamint_gb

date "+%Y-%m-%d %H:%M:%S KST table_fillable_primary_queue_complete"
