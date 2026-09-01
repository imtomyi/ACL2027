#!/usr/bin/env python3
"""Delegate the v2.1 compatibility freeze to the byte-frozen v2 core."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
RQ2_ROOT = SCRIPT.parents[1]
CORE_RUNNER = SCRIPT.with_name("run_personal_local_main_v2.py")
COMPAT_CONFIG = RQ2_ROOT / "config" / "personal_local_main_v2_compat_freeze.json"
CORE_RUNNER_SHA256 = "7fbbafc74f3ad40b2041b054bb72ae84c66214c84ef882d0f3a08d21c00caa64"


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_frozen_core() -> Any:
    if raw_sha256(CORE_RUNNER) != CORE_RUNNER_SHA256:
        raise SystemExit("v21_core_runner_hash_drift")
    spec = importlib.util.spec_from_file_location(
        "rq2_personal_local_main_v2_frozen_for_v21", CORE_RUNNER
    )
    if spec is None or spec.loader is None:
        raise SystemExit("v21_core_runner_import_spec_invalid")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DEFAULT_CONFIG = COMPAT_CONFIG
    module.SCRIPT = SCRIPT
    return module


core = load_frozen_core()


def main() -> int:
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
