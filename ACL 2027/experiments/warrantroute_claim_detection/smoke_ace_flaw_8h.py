"""Local live preflight on development-only packets. Never export as results."""

import argparse
import copy
import fcntl
from pathlib import Path
import time

import ace_flaw_contract as c
import run_ace_flaw_8h as run


def smoke(output, source):
    run.require(output.is_relative_to((run.PROJECT / "Storage").resolve()), "private_storage_only")
    data = run.read(source / "inputs.private.json")
    schedule = run.read(source / "development_schedule.json")
    run.require(all(p.with_name("response.json").exists() for p in (source / "calls").glob("**/request.json")),
                "prior_call_unresolved")
    identity = run.model_identity()
    output.mkdir(parents=True, exist_ok=False)
    report = {"started_at": run.now(), "source_run": str(source), "status": "running",
              "model_digest": identity, "options": run.OPTIONS,
              "code_sha256": {name: run.file_hash(Path(__file__).with_name(name)) for name in run.CODE},
              "inputs_sha256": run.digest(data), "evaluation_packets_used": 0,
              "datasets_tested": [], "checks": [], "quality_values_are_not_gate_thresholds": True,
              "preflight_only_not_experiment_evidence": True}
    run.write_json(output / "preflight.json", report)
    client = run.Client(output, time.time() + 1800)
    memories = {ds: copy.deepcopy(c.SEED) for ds in run.DISPLAY}
    selected = [j for j in schedule if j["epoch"] == 1 and j["position"] <= 2]
    for job in selected:
        ds = job["dataset"]
        packet = next(p for p in data[ds]["development"] if p["packet_id"] == job["packet_id"])
        result = run.execute_job(client, job, packet, memories[ds])
        run.write_json(output / "results" / job["id"] / "result.json", result)
        record = {"dataset": ds, "packet_id": packet["packet_id"], "diagnosis_status": result["status"],
                  "technical_trajectory": result["technical_trajectory"], "error": result.get("error"),
                  "learning_status": result.get("learning_status"), "reference_status": result.get("reference_status")}
        if result["status"] == "valid":
            reference = run.read(output / "references" / ds / (packet["packet_id"] + ".json"))
            # Use development-only diagnoses to exercise the judge, never held-out outcomes.
            quality = client.call(job["id"] + "/quality_smoke", "quality", {
                "task": packet["task"], "review": result["review"],
                "integrity_findings": result["checks"]["integrity_findings"], "provisional_reference": reference["review"]})
            quality = c.check_quality(quality, result["review"], reference["review"])
            run.write_json(output / "results" / job["id"] / "quality_smoke.json", quality)
            record["quality_schema_valid"] = True
            if result.get("learning", {}).get("patches") and "patch_audit" not in result:
                audit = client.call(job["id"] + "/audit_smoke", "patch_audit", {
                    "task": packet["task"], "locked_prediction": result["review"],
                    "provisional_reference": reference["review"], "current_playbook": c.visible_memory(memories[ds]),
                    "learning": result["learning"]})
                # A rejection is a valid audit result, not a reason to retry.
                record["audit_smoke_approved"] = c.audit_approved(audit, result["learning"], packet["task"])
        memories[ds] = result["memory_after"]
        report["checks"].append(record)
        run.write_json(output / "progress.json", report, replace=True)
        print(record, flush=True)
    report["datasets_tested"] = list(run.DISPLAY)
    report["status"] = "passed" if all(r["diagnosis_status"] == "valid" and not r["technical_trajectory"]
                                      and r.get("quality_schema_valid") for r in report["checks"]) else "failed"
    report["completed_at"] = run.now()
    report["timing"] = run.timing(output)
    report["accepted_rule_counts"] = {ds: len(m)-len(c.SEED) for ds, m in memories.items()}
    report["artifact_sha256"] = {str(p.relative_to(output)): run.file_hash(p) for p in output.rglob("*.json")}
    run.write_json(output / "smoke_report.json", report)
    run.require(report["status"] == "passed", "live_preflight_failed_do_not_launch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    args = parser.parse_args()
    global_lock = run.PROJECT / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    with global_lock.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        output = args.output.resolve()
        try:
            smoke(output, args.source_run.resolve())
        except Exception as exc:
            if output.exists() and not (output / "smoke_report.json").exists():
                run.write_json(output / "smoke_report.json", {"status": "failed", "at": run.now(),
                    "error": str(exc), "type": type(exc).__name__, "preflight_only_not_experiment_evidence": True})
            raise


if __name__ == "__main__":
    main()
