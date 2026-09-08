#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACE_DIR="$(cd "$ROOT_DIR/../upstream" && pwd)"
PYTHON="$ROOT_DIR/.venv-finance/bin/python"

usage() {
  cat <<'EOF'
Usage: run_table2_finance.sh TARGET

TARGET is one of:
  base_finer                 base_formula
  offline_gt_finer           offline_gt_formula
  offline_no_gt_finer        offline_no_gt_formula
  online_gt_finer            online_gt_formula
  online_no_gt_finer         online_no_gt_formula
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

if [[ -z "${SAMBANOVA_API_KEY:-}" ]]; then
  echo "SAMBANOVA_API_KEY is required for the paper's DeepSeek-V3.1 runs." >&2
  exit 2
fi

TARGET="$1"
TASK="${TARGET##*_}"
case "$TASK" in
  finer|formula) ;;
  *) usage; exit 2 ;;
esac

MODE=""
NO_GT=()
case "$TARGET" in
  base_finer|base_formula)
    MODE="eval_only"
    ;;
  offline_gt_finer|offline_gt_formula)
    MODE="offline"
    ;;
  offline_no_gt_finer|offline_no_gt_formula)
    MODE="offline"
    NO_GT=(--no_ground_truth)
    ;;
  online_gt_finer|online_gt_formula)
    MODE="online"
    ;;
  online_no_gt_finer|online_no_gt_formula)
    MODE="online"
    NO_GT=(--no_ground_truth)
    ;;
  *)
    usage
    exit 2
    ;;
esac

SAVE_PATH="$ROOT_DIR/runs/table2/$TARGET"
if [[ -e "$SAVE_PATH" ]]; then
  echo "Refusing to mix runs: $SAVE_PATH already exists." >&2
  exit 2
fi
mkdir -p "$SAVE_PATH"

cd "$ACE_DIR"
export PYTHONPATH="$ACE_DIR${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="$ROOT_DIR/.hf"

"$PYTHON" -m eval.finance.run \
  --task_name "$TASK" \
  --mode "$MODE" \
  --api_provider sambanova \
  --generator_model DeepSeek-V3.1 \
  --reflector_model DeepSeek-V3.1 \
  --curator_model DeepSeek-V3.1 \
  --num_epochs 5 \
  --max_num_rounds 5 \
  --curator_frequency 1 \
  --eval_steps 100 \
  --save_steps 50 \
  --batch_size 1 \
  --max_tokens 4096 \
  --playbook_token_budget 100000 \
  --test_workers 20 \
  --use_bulletpoint_analyzer \
  --bulletpoint_analyzer_threshold 0.90 \
  --save_path "$SAVE_PATH" \
  "${NO_GT[@]}"
