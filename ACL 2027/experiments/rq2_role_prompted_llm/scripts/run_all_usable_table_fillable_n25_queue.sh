#!/usr/bin/env bash
set -euo pipefail
trap 'echo "$(date "+%Y-%m-%d %H:%M:%S KST") ERROR line=$LINENO status=$?"' ERR

# Queue table-fillable working runs for every currently usable corpus bank.
#
# This runs a small balanced N=25 slice first so the manuscript Table 3-style
# rows can be filled for Generalist, Fixed role, and All roles before spending
# the full-sample budget. Outputs contain no source text in the CSV summaries,
# but the packet banks and model outputs remain local restricted artifacts.

ROOT="/Users/tom/Documents/GitHub/ACL2027/ACL 2027"
RQ2="$ROOT/experiments/rq2_role_prompted_llm"
STORAGE="$ROOT/Storage/draft_review_packets"
PY="${PYTHON:-python3}"
SAMPLE_N="${SAMPLE_N:-25}"
NUM_PREDICT="${NUM_PREDICT:-256}"
TIMEOUT="${TIMEOUT:-240}"
MODELS=(qwen3:8b llama3.1:8b gemma3:4b)
ROLES=(generalist qualitative_methods domain)

log() {
  date "+%Y-%m-%d %H:%M:%S KST $*"
}

wait_for_prior_screens() {
  while screen -ls | grep -E -q '[.](dreaddit_dev580|table3_primary_qwen_queue)'; do
    log "waiting_for_prior_screen dreaddit_dev580_or_table3_primary_qwen_queue"
    sleep 60
  done
}

wait_for_reviewer_slot() {
  while pgrep -f "[r]un_working_generalist_reviews.py" >/dev/null; do
    log "waiting_for_existing_reviewer"
    sleep 60
  done
}

safe_model_dir() {
  printf "%s" "$1" | tr ':.' '__'
}

build_subset() {
  local bank="$1"
  local corpus="$2"
  RUN_ROOT="$bank" CORPUS_ID="$corpus" SAMPLE_N="$SAMPLE_N" "$PY" - <<'PY'
import json
import os
from collections import defaultdict
from pathlib import Path

run_root = Path(os.environ["RUN_ROOT"])
corpus_id = os.environ["CORPUS_ID"]
sample_n = int(os.environ["SAMPLE_N"])
packet_file = run_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"
truth_file = run_root / "private" / "truth_map.private.jsonl"

packets = {}
with packet_file.open("r", encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            packets[str(row["packet_id"])] = row

by_flaw = defaultdict(list)
with truth_file.open("r", encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            by_flaw[str(row["known_intended_flaw_type"])].append(row)

if sample_n % len(by_flaw):
    raise SystemExit(f"sample_n_not_divisible_by_flaw_count:{sample_n}")

per_flaw = sample_n // len(by_flaw)
selected_truth = []
for flaw_type, rows in sorted(by_flaw.items()):
    rows = sorted(rows, key=lambda item: item["packet_id"])
    if len(rows) < per_flaw:
        raise SystemExit(f"not_enough_rows:{flaw_type}:{len(rows)}<{per_flaw}")
    selected_truth.extend(rows[:per_flaw])
selected_truth.sort(key=lambda item: item["packet_id"])

subset_root = run_root / "sample_packets" / f"balanced_n{sample_n}"
subset_packet = subset_root / "by_dataset" / f"{corpus_id}.review_packets.jsonl"
subset_truth = subset_root / "private" / "truth_map.private.jsonl"
subset_packet.parent.mkdir(parents=True, exist_ok=True)
subset_truth.parent.mkdir(parents=True, exist_ok=True)

with subset_packet.open("w", encoding="utf-8") as handle:
    for row in selected_truth:
        handle.write(json.dumps(packets[str(row["packet_id"])], ensure_ascii=False, sort_keys=True) + "\n")
with subset_truth.open("w", encoding="utf-8") as handle:
    for row in selected_truth:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

manifest = {
    "corpus_id": corpus_id,
    "full_run_root": str(run_root),
    "packet_file": str(subset_packet),
    "sample_n": sample_n,
    "sample_type": "nested_balanced",
    "truth_map": str(subset_truth),
}
(subset_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(subset_packet)
PY
}

run_role_model() {
  local bank="$1"
  local corpus="$2"
  local role="$3"
  local model="$4"
  local packet_file="$bank/sample_packets/balanced_n$SAMPLE_N/by_dataset/$corpus.review_packets.jsonl"
  local output_root="$bank/reviewer_outputs/$role"

  wait_for_reviewer_slot
  log "start corpus=$corpus role=$role model=$model sample_n=$SAMPLE_N"
  "$PY" "$RQ2/scripts/run_working_generalist_reviews.py" \
    --packet-file "$packet_file" \
    --output-root "$output_root" \
    --role "$role" \
    --models "$model" \
    --timeout "$TIMEOUT" \
    --num-predict "$NUM_PREDICT"

  "$PY" "$RQ2/scripts/summarize_working_generalist_reviews.py" \
    --input-root "$output_root" \
    --output-root "$output_root/derived"
}

score_bank() {
  local bank="$1"
  local output_dir="$bank/sample_size_efficiency/table_fillable_n$SAMPLE_N"

  "$PY" "$RQ2/scripts/score_working_sample_size_efficiency.py" \
    --run-root "$bank" \
    --roles "${ROLES[@]}" \
    --balanced-sizes "$SAMPLE_N" \
    --random-sizes "$SAMPLE_N" \
    --random-draws 0 \
    --minimum-complete-fraction 1.0 \
    --fixed-role-selection-size "$SAMPLE_N" \
    --table-methods-only \
    --output-dir "$output_dir"
  log "scored $output_dir/efficiency_curve.csv"
}

run_bank() {
  local run_id="$1"
  local corpus="$2"
  local bank="$STORAGE/$run_id"

  log "bank_start run_id=$run_id corpus=$corpus sample_n=$SAMPLE_N"
  build_subset "$bank" "$corpus" >/dev/null
  for model in "${MODELS[@]}"; do
    for role in "${ROLES[@]}"; do
      run_role_model "$bank" "$corpus" "$role" "$model"
    done
    score_bank "$bank"
  done
  log "bank_done run_id=$run_id corpus=$corpus"
}

wait_for_prior_screens
run_bank dreaddit_dev580_working_v1 dreaddit
run_bank goemotions_train_all_working_v1 goemotions
run_bank agyw_focus_groups_eval765_working_v1 agyw_focus_groups
run_bank parlamint_gb_fullsample_eval100_working_v1 parlamint_gb

log "all_usable_table_fillable_n${SAMPLE_N}_queue_complete"
