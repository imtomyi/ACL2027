"""Read historical result metadata without emitting source text or making model calls."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    groups = {}
    bindings = []
    for path in sorted(args.run_dir.glob("results/**/result.json")):
        raw = path.read_bytes()
        row = json.loads(raw)
        content = {key: value for key, value in row.items() if key != "result_sha256"}
        digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        if row.get("result_sha256") != digest:
            raise ValueError(f"Result integrity failure: {path}")
        bindings.append([str(path.relative_to(args.run_dir)), hashlib.sha256(raw).hexdigest()])
        group = groups.setdefault(row["configuration"], {
            "n": 0, "statuses": collections.Counter(), "routes": collections.Counter(),
            "rounds": collections.Counter(), "errors": collections.Counter(),
            "open_issues": 0, "resolved_issues": 0,
            "repeated_owner_category_evidence_keys": 0,
        })
        group["n"] += 1
        for field, key in [("statuses", "status"), ("routes", "route"), ("rounds", "revision_rounds")]:
            group[field][row[key]] += 1
        group["errors"][row["error"] or "none"] += 1
        for issue in row["issues"]:
            group["resolved_issues" if issue["status"] == "resolved" else "open_issues"] += 1
        keys = [(issue["owner_role"], issue["category"], tuple(sorted(issue["evidence_ids"]))) for issue in row["issues"]]
        group["repeated_owner_category_evidence_keys"] += len(keys) - len(set(keys))
    print(json.dumps({
        "scope": "historical_controlled_packet_diagnostic_not_manuscript_evidence",
        "run_dir": str(args.run_dir.resolve()), "result_integrity_checks": len(bindings),
        "result_inventory_sha256": hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest(),
        "note": "Repeated keys are only a coarse recurrence signal, not proof of semantically identical issues. No live runtime compatibility check was performed.",
        "configurations": groups,
    }, indent=2))


if __name__ == "__main__":
    main()
