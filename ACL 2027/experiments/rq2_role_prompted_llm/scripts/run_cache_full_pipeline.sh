#!/usr/bin/env zsh
set -euo pipefail
export PATH="/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/bin:/bin:/usr/sbin:/sbin"

RUN_ROOT="/Users/tom/Documents/GitHub/ACL2027/ACL 2027/Storage/draft_review_packets/agyw_focus_groups_eval765_working_v1"
SCRIPT_ROOT="/Users/tom/Documents/GitHub/ACL2027/ACL 2027/experiments/rq2_role_prompted_llm/scripts"
PACKET_FILE="$RUN_ROOT/by_dataset/agyw_focus_groups.review_packets.jsonl"
DREADDIT_PID="${DREADDIT_PID:-4220}"

if [[ -z "${CACHE_PIPELINE_LOG:-}" ]]; then
  CACHE_PIPELINE_LOG="$RUN_ROOT/cache_full_pipeline_default.log"
fi
exec >> "$CACHE_PIPELINE_LOG" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiting_for_existing_dreaddit_role_run pid=$DREADDIT_PID"
while true; do
  if ! ps -p "$DREADDIT_PID" >/dev/null 2>&1; then
    break
  fi
  sleep 60
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiting_for_other_review_runners"
while true; do
  other_runner_pids="$(pgrep -f 'run_working_generalist_reviews.py' || true)"
  if [[ -z "$other_runner_pids" ]]; then
    other_runner_count="0"
  else
    other_runner_count="$(printf "%s\n" "$other_runner_pids" | wc -l | tr -d ' ')"
  fi
  if [[ "$other_runner_count" == "0" ]]; then
    break
  fi
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] still_waiting other_review_runners=$other_runner_count"
  sleep 60
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] starting_cache_full_roles"
for role in generalist qualitative_methods domain; do
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] start_role $role"
  python3 "$SCRIPT_ROOT/run_working_generalist_reviews.py" \
    --packet-file "$PACKET_FILE" \
    --output-root "$RUN_ROOT/reviewer_outputs/$role" \
    --role "$role" \
    --models qwen3:8b llama3.1:8b gemma3:4b
  python3 "$SCRIPT_ROOT/summarize_working_generalist_reviews.py" \
    --input-root "$RUN_ROOT/reviewer_outputs/$role" \
    --output-root "$RUN_ROOT/reviewer_outputs/$role/derived"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] summarized_role $role"

  if [[ "$role" == "generalist" ]]; then
    completed_roles=(generalist)
    efficiency_dir="$RUN_ROOT/sample_size_efficiency/interim_generalist"
  elif [[ "$role" == "qualitative_methods" ]]; then
    completed_roles=(generalist qualitative_methods)
    efficiency_dir="$RUN_ROOT/sample_size_efficiency/interim_generalist_methods"
  else
    completed_roles=(generalist qualitative_methods domain)
    efficiency_dir="$RUN_ROOT/sample_size_efficiency/full_roles"
  fi
  python3 "$SCRIPT_ROOT/score_working_sample_size_efficiency.py" \
    --run-root "$RUN_ROOT" \
    --roles "${completed_roles[@]}" \
    --balanced-sizes 25 50 75 100 150 250 500 765 \
    --random-sizes 25 50 100 250 500 \
    --random-draws 30 \
    --fixed-role-selection-size 100 \
    --table-methods-only \
    --output-dir "$efficiency_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] scored_efficiency $efficiency_dir"
done

python3 "$SCRIPT_ROOT/score_working_detection_table.py" \
  --run-root "$RUN_ROOT" \
  --roles generalist qualitative_methods domain \
  --output-dir "$RUN_ROOT/table_exports/role_methods"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cache_full_pipeline_complete"
