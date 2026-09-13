#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/sources/ace-appworld-latest"
APPWORLD="$ROOT_DIR/.venv-appworld/bin/appworld"
PLAYBOOK_DIR="$SOURCE_DIR/experiments/playbooks"

usage() {
  cat <<'EOF'
Usage: run_table1_appworld.sh TARGET

TARGET is one of:
  released_offline_no_gt_eval
  offline_gt_full
  offline_no_gt_full
  online_no_gt_normal
  online_no_gt_challenge
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
case "$TARGET" in
  released_offline_no_gt_eval|offline_gt_full|offline_no_gt_full|online_no_gt_normal|online_no_gt_challenge) ;;
  *) usage; exit 2 ;;
esac

RUN_DIR="$ROOT_DIR/runs/table1/$TARGET"
RUN_ROOT="$RUN_DIR/appworld_root"
if [[ -e "$RUN_DIR" ]]; then
  echo "Refusing to mix runs: $RUN_DIR already exists." >&2
  exit 2
fi
mkdir -p "$RUN_ROOT/experiments/outputs" "$ROOT_DIR/runs/playbooks"
ln -s "$SOURCE_DIR/data" "$RUN_ROOT/data"

export APPWORLD_PROJECT_PATH="$SOURCE_DIR"
cd "$SOURCE_DIR"

run_eval() {
  local config="$1"
  local playbook="$2"
  local split="$3"
  local override
  override="{\"config\":{\"dataset\":\"$split\",\"agent\":{\"trained_playbook_file_path\":\"$playbook\"}}}"
  "$APPWORLD" run "$config" --root "$RUN_ROOT" --override "$override"
  "$APPWORLD" evaluate "$config" "$split" --root "$RUN_ROOT"
}

run_adaptation() {
  local config="$1"
  local playbook="$2"
  local split="$3"
  local epochs="$4"
  local initial_playbook="${5:-}"
  local override
  if [[ -n "$initial_playbook" ]]; then
    override="{\"config\":{\"dataset\":\"$split\",\"num_epochs\":$epochs,\"agent\":{\"initial_playbook_file_path\":\"$initial_playbook\",\"trained_playbook_file_path\":\"$playbook\"}}}"
  else
    override="{\"config\":{\"dataset\":\"$split\",\"num_epochs\":$epochs,\"agent\":{\"trained_playbook_file_path\":\"$playbook\"}}}"
  fi
  "$APPWORLD" run "$config" --root "$RUN_ROOT" --override "$override"
}

case "$TARGET" in
  released_offline_no_gt_eval)
    PLAYBOOK="$PLAYBOOK_DIR/appworld_offline_trained_no_gt_playbook.txt"
    run_eval ACE_offline_no_GT_evaluation "$PLAYBOOK" test_normal
    run_eval ACE_offline_no_GT_evaluation "$PLAYBOOK" test_challenge
    ;;
  offline_gt_full)
    PLAYBOOK="$ROOT_DIR/runs/playbooks/appworld_offline_gt_generated.txt"
    [[ ! -e "$PLAYBOOK" ]] || { echo "$PLAYBOOK already exists" >&2; exit 2; }
    run_adaptation ACE_offline_with_GT_adaptation "$PLAYBOOK" train 5
    run_eval ACE_offline_with_GT_evaluation "$PLAYBOOK" test_normal
    run_eval ACE_offline_with_GT_evaluation "$PLAYBOOK" test_challenge
    ;;
  offline_no_gt_full)
    PLAYBOOK="$ROOT_DIR/runs/playbooks/appworld_offline_no_gt_generated.txt"
    [[ ! -e "$PLAYBOOK" ]] || { echo "$PLAYBOOK already exists" >&2; exit 2; }
    run_adaptation ACE_offline_no_GT_adaptation "$PLAYBOOK" train 5
    run_eval ACE_offline_no_GT_evaluation "$PLAYBOOK" test_normal
    run_eval ACE_offline_no_GT_evaluation "$PLAYBOOK" test_challenge
    ;;
  online_no_gt_normal)
    PLAYBOOK="$ROOT_DIR/runs/playbooks/appworld_online_no_gt_normal_generated.txt"
    [[ ! -e "$PLAYBOOK" ]] || { echo "$PLAYBOOK already exists" >&2; exit 2; }
    run_adaptation ACE_online_no_GT "$PLAYBOOK" test_normal 1 \
      "$PLAYBOOK_DIR/appworld_offline_trained_no_gt_playbook.txt"
    "$APPWORLD" evaluate ACE_online_no_GT test_normal --root "$RUN_ROOT"
    ;;
  online_no_gt_challenge)
    PLAYBOOK="$ROOT_DIR/runs/playbooks/appworld_online_no_gt_challenge_generated.txt"
    [[ ! -e "$PLAYBOOK" ]] || { echo "$PLAYBOOK already exists" >&2; exit 2; }
    run_adaptation ACE_online_no_GT "$PLAYBOOK" test_challenge 1 \
      "$PLAYBOOK_DIR/appworld_offline_trained_no_gt_playbook.txt"
    "$APPWORLD" evaluate ACE_online_no_GT test_challenge --root "$RUN_ROOT"
    ;;
esac
