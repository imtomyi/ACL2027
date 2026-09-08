#!/usr/bin/env python3
"""Validate the static WarrantRoute Playbook configuration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import warrantroute_loop_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/warrantroute_loop_n100_same_model_playbook_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        bundle = runtime.load_playbook_bundle(config)
        assert bundle is not None
        summary = runtime.playbook_summary(bundle)
        adapters = sorted(bundle.get("adapters", {}))
        report = {
            "status": "validated",
            "config": str(args.config),
            "playbook": summary,
            "adapter_count": len(adapters),
            "adapters": adapters,
            "updates_enabled": bool(bundle.get("updates_enabled")),
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "blocked",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
