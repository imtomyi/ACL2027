#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RUN_ROOT="$WORKSPACE/Storage/draft_review_packets/dreaddit_dev580_working_v1"
PACKET_FILE="$RUN_ROOT/by_dataset/dreaddit.review_packets.jsonl"
LOG_DIR="$RUN_ROOT/logs"
NUM_PREDICT="${NUM_PREDICT:-256}"
RUN_QUALITY_JUDGE="${RUN_QUALITY_JUDGE:-1}"

mkdir -p "$LOG_DIR"

echo "run_root=$RUN_ROOT"
echo "packet_file=$PACKET_FILE"
echo "num_predict=$NUM_PREDICT"
echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for role in generalist qualitative_methods domain; do
  for model in 'qwen3:8b' 'llama3.1:8b' 'gemma3:4b'; do
    output_root="$RUN_ROOT/reviewer_outputs/$role"
    echo "job_start role=$role model=$model at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 "$SCRIPT_DIR/run_working_generalist_reviews.py" \
      --packet-file "$PACKET_FILE" \
      --output-root "$output_root" \
      --role "$role" \
      --models "$model" \
      --num-predict "$NUM_PREDICT"
    python3 "$SCRIPT_DIR/summarize_working_generalist_reviews.py" \
      --input-root "$output_root" \
      --output-root "$output_root/derived"
    echo "job_done role=$role model=$model at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  done
done

if [[ "$RUN_QUALITY_JUDGE" == "1" ]]; then
  echo "quality_judge_start at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 "$SCRIPT_DIR/run_working_quality_judge.py" \
    --packet-file "$PACKET_FILE" \
    --output-root "$RUN_ROOT/quality_judge/credibility_conformability" \
    --judge-model 'qwen3:8b'
  echo "quality_judge_done at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi

python3 "$SCRIPT_DIR/score_working_detection_table.py" \
  --run-root "$RUN_ROOT" \
  --output-dir "$RUN_ROOT/table_exports/role_methods"

echo "table_csv=$RUN_ROOT/table_exports/role_methods/table_metrics.csv"
echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
