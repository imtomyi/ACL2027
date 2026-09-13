"""Run the authorized full local Formula experiment with durable status."""

import fcntl
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main():
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    with (runs / "qwen_formula.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A supervised Qwen Formula run is already active")
        directory = runs / datetime.now(timezone.utc).strftime("qwen_formula_%Y%m%dT%H%M%SZ")
        directory.mkdir(exist_ok=False)
        command = [
            str(ROOT / ".venv-finance/bin/python"), "-u",
            str(ROOT / "scripts/run_model_specific_ace.py"),
            "--models", "qwen3:8b", "--train-samples", "500",
            "--validation-samples", "300", "--test-samples", "200",
            "--epochs", "5", "--reflection-rounds", "5",
            "--max-tokens", "4096", "--eval-steps", "100",
            "--deduplicate", "--native-nonthinking", "--context-window", "32768",
            "--playbook-token-budget", "12000",
        ]
        state = {
            "status": "starting", "started_at": timestamp(),
            "supervisor_pid": os.getpid(), "command": command,
            "console_log": str(directory / "console.log"),
            "status_file": str(directory / "status.json"),
        }
        save(directory / "status.json", state)
        save(runs / "qwen_formula_retry.json", state)
        try:
            with (directory / "console.log").open("w") as output:
                child = subprocess.Popen(command, cwd=ROOT.parent, stdout=output,
                                         stderr=subprocess.STDOUT)
                state.update(status="running", child_pid=child.pid)
                save(directory / "status.json", state)
                save(runs / "qwen_formula_retry.json", state)
                code = child.wait()
            state.update(status="finished_pending_verification" if code == 0 else "failed",
                         exit_code=code, finished_at=timestamp())
        except Exception as error:
            state.update(status="supervisor_error", error=str(error), finished_at=timestamp())
            raise
        finally:
            save(directory / "status.json", state)
            save(runs / "qwen_formula_retry.json", state)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
