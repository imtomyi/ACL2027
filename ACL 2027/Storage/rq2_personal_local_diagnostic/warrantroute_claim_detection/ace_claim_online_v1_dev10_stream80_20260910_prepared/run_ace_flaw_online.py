"""Sequential predict-lock-judge-update runner. Never imports historical outputs."""

import argparse
import copy
import fcntl
import json
import shutil
import statistics
import time
import urllib.request
from pathlib import Path

import ace_flaw_contract as base
import ace_online_contract as contract
import run_ace_flaw_8h as legacy


read, digest, file_hash, require = legacy.read, legacy.digest, legacy.file_hash, legacy.require
write_json, write_text = legacy.write_json, legacy.write_text
BudgetStop, AmbiguousCall, FrozenError = legacy.BudgetStop, legacy.AmbiguousCall, legacy.FrozenError
DATASETS = list(legacy.DISPLAY)
OPTIONS = {**legacy.OPTIONS, "num_predict": 4096}
CODE = ["run_ace_flaw_online.py", "ace_online_contract.py", "run_ace_flaw_8h.py",
        "ace_flaw_contract.py", "plan_gemma_8h.py"]
PROTOCOL = "Storage/experiment_guidelines/ace_claim_online_v1.md"


def build_request(config, role, data):
    schema = contract.wire_schema(role, data)
    prompt = (contract.PROMPTS[role] + "\nINPUT JSON:\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
              + "\nOUTPUT JSON SCHEMA:\n" + json.dumps(schema, separators=(",", ":")))
    options = config["options"]
    bound = len(prompt.encode()) + len(json.dumps(schema).encode()) + options["num_predict"] + 1024
    require(bound <= options["num_ctx"], "context_admission_failed_no_truncation")
    require(config["base_url"] == legacy.BASE and config["paid_api_allowed"] is False, "local_only")
    return {"model": config["model"], "prompt": prompt, "format": schema, "stream": False,
            "keep_alive": "30m", "options": options}, bound


def immutable(path, value):
    if path.exists():
        if read(path) != value:
            raise FrozenError("immutable_record_changed:" + str(path))
    else:
        write_json(path, value)
    return value


def validate_inputs(data):
    require(list(data) == DATASETS, "four_dataset_order_required")
    sizes = set()
    for ds, phases in data.items():
        require(set(phases) == {"development", "evaluation"}, "input_phase_contract")
        sizes.add(tuple(len(phases[k]) for k in ("development", "evaluation")))
        ids, text_keys, records, groups = {}, {}, {}, {}
        for phase, rows in phases.items():
            ids[phase], text_keys[phase], records[phase], groups[phase] = set(), set(), set(), set()
            require(rows, "empty_panel")
            for packet in rows:
                pid, task = packet["packet_id"], packet["task"]
                require(legacy.re.fullmatch(r"[A-Za-z0-9_-]+", pid) and pid not in ids[phase], "packet_identity")
                ids[phase].add(pid)
                require(task["claim"].strip() and task["evidence"], "empty_task")
                require(digest(task) == packet["task_sha256"], "task_hash_changed")
                exids = [e["excerpt_id"] for e in task["evidence"]]
                require(len(exids) == len(set(exids)) and set(task["cited_excerpt_ids"]) <= set(exids), "excerpt_identity")
                require(all(isinstance(s, str) and s for s in packet["source_ids"]), "source_identity")
                require(set(packet["source_ids"]) == {e["source_id"] for e in task["evidence"]}, "source_inventory")
                for excerpt in task["evidence"]:
                    require(excerpt["text"].strip(), "empty_evidence")
                    text_keys[phase].add(" ".join(excerpt["text"].casefold().split()))
                    if excerpt.get("source_record_id"):
                        records[phase].add((excerpt["source_id"], excerpt["source_record_id"]))
                groups[phase].update(packet["source_ids"])
        require(not ids["development"] & ids["evaluation"], "development_stream_id_overlap")
        require(not text_keys["development"] & text_keys["evaluation"], "development_stream_text_overlap")
        require(not records["development"] & records["evaluation"], "development_stream_record_overlap")
        require(ds == "cache" or not groups["development"] & groups["evaluation"], "unapproved_source_overlap")
    require(len(sizes) == 1, "unbalanced_panels")
    return next(iter(sizes))


def schedule(data, epochs):
    jobs = []
    for epoch in range(1, epochs + 1):
        orders = {ds: sorted(data[ds]["development"], key=lambda p: digest([
            contract.VERSION, 20260910, ds, epoch, p["packet_id"]])) for ds in DATASETS}
        for position in range(len(data[DATASETS[0]]["development"])):
            for ds in DATASETS:
                packet = orders[ds][position]
                jobs.append({"id": f"development/{ds}/E{epoch}/{packet['packet_id']}", "phase": "development",
                             "dataset": ds, "epoch": epoch, "position": position + 1, "packet_id": packet["packet_id"]})
    orders = {ds: sorted(data[ds]["evaluation"], key=lambda p: digest([
        contract.VERSION, 20260910, ds, p["packet_id"]])) for ds in DATASETS}
    for position in range(len(data[DATASETS[0]]["evaluation"])):
        for ds in DATASETS:
            packet = orders[ds][position]
            jobs.append({"id": f"online/{ds}/{position+1:04d}-{packet['packet_id']}", "phase": "online",
                         "dataset": ds, "epoch": 0, "position": position + 1, "packet_id": packet["packet_id"]})
    return jobs


def prepare(run, source, epochs=3):
    require(run.is_relative_to((legacy.PROJECT / "Storage").resolve()), "private_storage_only")
    require(source.is_relative_to((legacy.PROJECT / "Storage").resolve()), "private_source_only")
    require(epochs in (0, 1, 3), "prespecified_epochs_only")
    prior = read(source / "manifest.json")
    for name, expected in prior["files"].items():
        require(file_hash(source / name) == expected, "source_contract_changed:" + name)
    data = read(source / "inputs.private.json")
    dev_n, stream_n = validate_inputs(data)
    jobs = schedule(data, epochs)
    config = {"protocol": contract.VERSION, "model": legacy.MODEL, "model_digest": prior["model_digest"],
              "options": OPTIONS, "base_url": legacy.BASE, "budget_seconds": 28800,
              "reserve_seconds": 900, "epochs": epochs, "development_n": dev_n, "stream_n": stream_n,
              "call_ceiling": 4 * dev_n * epochs * 3 + 4 * stream_n * 7,
              "paid_api_allowed": False, "manuscript_eligible": False,
              "prior_exposure": "Reused diagnostic panel, not untouched test data.",
              "source_run": str(source), "source_manifest_sha256": file_hash(source / "manifest.json"),
              "source_inputs_sha256": file_hash(source / "inputs.private.json"),
              "imported_predictions_scores_references_playbooks": 0,
              "cache_scope": "User-authorized within-source diagnostic; no repeated dev/stream text or records."}
    bounds = []
    for ds, phases in data.items():
        for phase, packets in phases.items():
            for packet in packets:
                _, bound = build_request(config, "online_detector", {
                    "task": packet["task"], "playbook": contract.retrieve(contract.seed_state(), packet["task"])})
                bounds.append({"dataset": ds, "phase": phase, "packet_id": packet["packet_id"], "initial_detector_bound": bound})
    run.mkdir(parents=True, exist_ok=False)
    write_json(run / "config.json", config)
    write_json(run / "input_admission.json", {"items": bounds,
               "scope": "Initial seed detector only; dynamic downstream requests are checked at dispatch, without truncation."})
    write_json(run / "inputs.private.json", data)
    write_json(run / "schedule.json", jobs)
    write_json(run / "prompts.json", contract.PROMPTS)
    shutil.copyfile(legacy.PROJECT / PROTOCOL, run / "protocol.md")
    for name in CODE:
        shutil.copyfile(Path(__file__).with_name(name), run / name)
    write_json(run / "manifest.json", {"protocol": contract.VERSION, "created_at": legacy.now(),
        "project_root": str(legacy.PROJECT), "manuscript_eligible": False,
        "files": {p.name: file_hash(p) for p in sorted(run.iterdir()) if p.is_file()}})
    return export(run, "prepared_not_started")


def verify(run):
    manifest = read(run / "manifest.json")
    require(manifest["protocol"] == contract.VERSION, "wrong_protocol")
    for name, expected in manifest["files"].items():
        if file_hash(run / name) != expected:
            raise FrozenError("frozen_file_changed:" + name)
    for name in CODE:
        if file_hash(Path(__file__).with_name(name)) != manifest["files"][name]:
            raise FrozenError("execute_frozen_code_only:" + name)
    return manifest


class Client:
    def __init__(self, run, deadline):
        self.run, self.deadline = run, deadline
        self.config = read(run / "config.json")

    def call(self, key, role, data):
        request, bound = build_request(self.config, role, data)
        folder = self.run / "calls" / key
        sent, received = folder / "request.json", folder / "response.json"
        if sent.exists():
            if read(sent)["request_sha256"] != digest(request):
                raise FrozenError("call_identity_changed")
            if not received.exists():
                raise AmbiguousCall(str(folder))
            response = read(received)
        else:
            if self.deadline - time.time() < 181:
                raise BudgetStop("inference_admission_closed")
            if len(list((self.run / "calls").glob("**/request.json"))) >= self.config["call_ceiling"]:
                raise BudgetStop("call_ceiling")
            write_json(sent, {"role": role, "started_at": legacy.now(), "request": request,
                              "request_sha256": digest(request), "conservative_context_bound": bound})
            write_json(self.run / "active_call.json", {"key": key, "role": role, "started_at": legacy.now()}, replace=True)
            started = time.monotonic()
            try:
                req = urllib.request.Request(legacy.BASE + "/api/generate", json.dumps(request).encode(),
                                             {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as handle:
                    body = json.load(handle)
            except Exception as exc:
                write_json(folder / "transport_error.json", {"at": legacy.now(), "error": str(exc)})
                raise AmbiguousCall(str(folder)) from exc
            response = {"body": body, "body_sha256": digest(body), "request_sha256": digest(request),
                        "role": role, "wall_seconds": time.monotonic() - started, "completed_at": legacy.now()}
            write_json(received, response)
            write_json(self.run / "active_call.json", {"status": "idle", "at": legacy.now()}, replace=True)
        if response["request_sha256"] != digest(request) or response["body_sha256"] != digest(response["body"]):
            raise FrozenError("response_identity_changed")
        body = response["body"]
        require(body.get("done") is True and body.get("done_reason") != "length", "incomplete_generation")
        return contract.decode_wire(role, json.loads(body["response"]), data)


def step(run, path, action):
    if path.exists():
        envelope = read(path)
        if envelope["sha256"] != digest(envelope["value"]):
            raise FrozenError("step_record_changed:" + str(path))
        return envelope["value"]
    try:
        value = {"status": "valid", "value": action()}
    except (BudgetStop, AmbiguousCall, FrozenError):
        raise
    except Exception as exc:
        value = {"status": "technical_failure", "error": str(exc)}
    write_json(path, {"value": value, "sha256": digest(value)})
    return value


def prediction(client, job, packet, state, arm):
    retrieved = contract.retrieve(state, packet["task"])
    ranked_n = len(retrieved)
    config = read(client.run / "config.json") if (client.run / "config.json").exists() else {
        "options": OPTIONS, "model": legacy.MODEL, "base_url": legacy.BASE, "paid_api_allowed": False}
    while True:
        try:
            build_request(config, "online_detector", {"task": packet["task"], "playbook": retrieved})
            break
        except ValueError as exc:
            if str(exc) != "context_admission_failed_no_truncation" or len(retrieved) <= len(base.SEED):
                raise
            retrieved.pop()
    def generate():
        value = client.call(job["id"] + "/" + arm + "/detector", "online_detector",
                            {"task": packet["task"], "playbook": retrieved})
        checks = contract.check_detection(value, packet["task"], retrieved)
        return {**value, "checks": checks, "retrieved_rules": retrieved,
                "retrieval_budget_omitted": ranked_n - len(retrieved),
                "memory_sha256": digest(state), "content_sha256": contract.content_hash(state),
                "task_sha256": packet["task_sha256"]}
    result = step(client.run, client.run / "predictions" / job["id"] / (arm + ".locked.json"), generate)
    if result["status"] == "valid":
        value = result["value"]
        if value["memory_sha256"] != digest(state) or value["task_sha256"] != packet["task_sha256"]:
            raise FrozenError("prediction_chain_changed")
    return result


def learn(client, job, packet, state, locked):
    key = job["id"]
    raw = client.call(key + "/learning", "online_learning", contract.learning_input(packet, locked, state))
    eligible, receipts = contract.eligible_patches(raw, packet, state)
    after = copy.deepcopy(state)
    audit = None
    if eligible["patches"]:
        audit = client.call(key + "/audit", "online_audit", {
            **contract.learning_input(packet, locked, state), "learning": eligible})
        after, decisions = contract.apply_audited(state, eligible, audit, packet)
        receipts.extend(decisions)
    return {"proposal": raw, "audit": audit, "receipts": receipts, "state_after": after,
            "status": "updated" if after != state else "no_change"}


def execute_job(client, job, packet, state, parent):
    root = client.run
    before, original = copy.deepcopy(state), state
    result = {**job, "task_sha256": packet["task_sha256"], "parent_record_sha256": parent,
              "state_before_sha256": digest(state), "content_before_sha256": contract.content_hash(state),
              "predictions": {}, "quality": {}}
    arms = ["online"] if job["phase"] == "development" else (["static", "online"] if job["position"] % 2 else ["online", "static"])
    for arm in arms:
        result["predictions"][arm] = prediction(client, job, packet, state if arm == "online" else contract.seed_state(), arm)
    # Both predictions are durable before a reference or quality judgment is generated.
    if job["phase"] == "online":
        def reference():
            value = client.call(job["id"] + "/reference", "reference", {"task": packet["task"]})
            require(not base.check_review(value, packet["task"])["integrity_findings"], "reference_integrity_failure")
            return value
        ref = step(root, root / "judgments" / job["id"] / "reference.json", reference)
        result["reference"] = ref
        ref_value = ref.get("value")
        for arm in arms:
            pred = result["predictions"][arm]
            if pred["status"] != "valid":
                result["quality"][arm] = {"status": "not_reached_prediction_failure"}
                continue
            locked = pred["value"]
            def judge(locked=locked, arm=arm):
                value = client.call(job["id"] + "/" + arm + "/quality", "quality", {
                    "task": packet["task"], "review": locked["review"],
                    "integrity_findings": locked["checks"]["integrity_findings"], "provisional_reference": ref_value})
                return base.check_quality(value, locked["review"], ref_value)
            result["quality"][arm] = step(root, root / "judgments" / job["id"] / (arm + ".locked.json"), judge)
    pred = result["predictions"]["online"]
    # No reference, judgment, score, later sample or other corpus state is an updater argument.
    if pred["status"] == "valid":
        result["learning"] = step(root, root / "deltas" / job["id"] / "decision.json",
                                  lambda: learn(client, job, packet, state, pred["value"]))
        if result["learning"]["status"] == "valid":
            state = result["learning"]["value"]["state_after"]
    else:
        result["learning"] = {"status": "not_reached_prediction_failure"}
    require(before == original, "unexpected_input_mutation")
    result.update(state_after=state, state_after_sha256=digest(state), content_after_sha256=contract.content_hash(state))
    artifacts = [* (root / "predictions" / job["id"]).glob("*.json"),
                 * (root / "judgments" / job["id"]).glob("*.json"),
                 * (root / "deltas" / job["id"]).glob("*.json")]
    result["artifacts"] = {str(p.relative_to(root)): file_hash(p) for p in artifacts}
    return result


def load_record(path):
    record = read(path)
    if record["sha256"] != digest(record["value"]):
        raise FrozenError("result_record_changed:" + str(path))
    return record


def process_job(client, job, packet, state, parent):
    path = client.run / "results" / job["id"] / "result.json"
    if not path.exists():
        value = execute_job(client, job, packet, state, parent)
        immutable(path, {"value": value, "sha256": digest(value)})
    record = load_record(path)
    value = record["value"]
    if (value["id"] != job["id"] or value["parent_record_sha256"] != parent
            or value["state_before_sha256"] != digest(state) or value["task_sha256"] != packet["task_sha256"]
            or value["state_after_sha256"] != digest(value["state_after"])):
        raise FrozenError("result_memory_chain_changed")
    for name, expected in value["artifacts"].items():
        if file_hash(client.run / name) != expected:
            raise FrozenError("locked_artifact_changed:" + name)
    return value["state_after"], record["sha256"]


def worker(run, client):
    data, jobs = read(run / "inputs.private.json"), read(run / "schedule.json")
    packets = {(ds, p["packet_id"]): p for ds, phases in data.items() for rows in phases.values() for p in rows}
    states = {ds: contract.seed_state() for ds in DATASETS}
    parents = {ds: None for ds in DATASETS}
    for job in jobs:
        complete = (run / "results" / job["id"] / "result.json").exists()
        if not complete and (run / "PAUSE.request.json").exists():
            return export(run, "paused_at_item_boundary")
        ds = job["dataset"]
        if not complete:
            write_json(run / "phase.json", job, replace=True)
        states[ds], parents[ds] = process_job(client, job, packets[(ds, job["packet_id"])], states[ds], parents[ds])
        if not complete:
            export(run, "running")
    return export(run, "completed")


def quality_stats(rows, arm, metric, expected):
    values = [r["quality"].get(arm, {}) for r in rows]
    valid = [v["value"][metric] for v in values if v.get("status") == "valid"]
    true, false = sum(v is True for v in valid), sum(v is False for v in valid)
    binary = true + false
    return {"true": true, "false": false, "null": sum(v is None for v in valid),
            "technical_or_not_reached": len(values) - len(valid), "pending": expected - len(values),
            "binary_n": binary, "success_pct_binary": 100 * true / binary if binary else None,
            "binary_coverage_pct_planned": 100 * binary / expected,
            "true_pct_planned": 100 * true / expected}


def paired_stats(rows, metric):
    pairs = [(r["quality"].get("static", {}).get("value", {}).get(metric),
              r["quality"].get("online", {}).get("value", {}).get(metric)) for r in rows]
    resolved = [(a, b) for a, b in pairs if type(a) is bool and type(b) is bool]
    return {"paired_binary_n": len(resolved),
            "paired_delta_pp": 100 * sum(int(b) - int(a) for a, b in resolved) / len(resolved) if resolved else None,
            "unresolved_or_failed_pairs": len(rows) - len(resolved)}


def export(run, status=None):
    config, jobs = read(run / "config.json"), read(run / "schedule.json")
    completed = [load_record(run / "results" / j["id"] / "result.json")["value"] for j in jobs
                 if (run / "results" / j["id"] / "result.json").exists()]
    stream = [r for r in completed if r["phase"] == "online"]
    table, paired, playbooks, curve = [], [], [], []
    for ds in DATASETS:
        rows = [r for r in stream if r["dataset"] == ds]
        history = [r for r in completed if r["dataset"] == ds]
        state = history[-1]["state_after"] if history else contract.seed_state()
        root = run / "playbooks" / ds
        write_json(root / "current.json", state, replace=True)
        write_text(root / "current.md", legacy.memory_markdown(ds, "Online v1", state["rules"]), replace=True)
        receipts = [p for r in history for p in r.get("learning", {}).get("value", {}).get("receipts", [])]
        retrieved = [rule for r in history for rule in r["predictions"]["online"].get("value", {}).get("retrieved_rules", []) if not rule["seed"]]
        checks = [c for r in history for key, c in r["predictions"]["online"].get("value", {}).get("rule_checks", {}).items() if key.startswith("learned-")]
        playbooks.append({"Dataset": legacy.DISPLAY[ds], "learned_rules": len(state["rules"]) - len(base.SEED),
            "revision": state["revision"], "content_sha256": contract.content_hash(state),
            "added": sum(p["outcome"] == "added" for p in receipts),
            "refined": sum(p["outcome"] == "refined" for p in receipts),
            "reinforced": sum(p["outcome"] == "reinforced" for p in receipts),
            "noops": sum(p["outcome"] in ("duplicate_noop", "repeated_support_noop") for p in receipts),
            "withheld": sum(p["outcome"].startswith("withheld") for p in receipts),
            "learned_rule_prompt_inclusions": len(retrieved),
            "learned_rule_reported_applicable": sum(c["applicable"] is True for c in checks),
            "rule_trace_integrity_findings": sum(len(r["predictions"]["online"].get("value", {}).get("checks", {}).get("rule_integrity_findings", [])) for r in history),
            "retrieval_budget_omissions": sum(r["predictions"]["online"].get("value", {}).get("retrieval_budget_omitted", 0) for r in history)})
        for arm in ("static", "online"):
            row = {"Dataset": legacy.DISPLAY[ds], "Method": "Static seed" if arm == "static" else "ACE-inspired online",
                   "Model": "Gemma 3 4B", "planned": config["stream_n"], "completed_items": len(rows)}
            for metric in ("credibility", "conformability"):
                row.update({metric + "_" + k: v for k, v in quality_stats(rows, arm, metric, config["stream_n"]).items()})
            table.append(row)
        for metric in ("credibility", "conformability"):
            paired.append({"Dataset": legacy.DISPLAY[ds], "metric": metric, **paired_stats(rows, metric),
                           "pending": config["stream_n"] - len(rows)})
        for start in range(0, config["stream_n"], 20):
            end = min(start + 20, config["stream_n"])
            for scope, begin in (("block", start), ("cumulative", 0)):
                subset = [r for r in rows if begin < r["position"] <= end]
                for metric in ("credibility", "conformability"):
                    point = {"Dataset": legacy.DISPLAY[ds], "scope": scope, "start_position": begin + 1,
                             "end_position": end, "metric": metric, "completed": len(subset), "planned": end - begin,
                             **paired_stats(subset, metric)}
                    for arm in ("static", "online"):
                        point.update({arm + "_" + k: v for k, v in quality_stats(subset, arm, metric, end - begin).items()})
                    curve.append(point)
    legacy.table_csv(run / "results_table_online.csv", table)
    legacy.table_csv(run / "paired_comparison.csv", paired)
    legacy.table_csv(run / "playbook_result.csv", playbooks)
    legacy.table_csv(run / "learning_curve.csv", curve)
    lines = ["# Online Claim-Flaw Diagnostic", "", "Private working diagnostics, not manuscript-qualified results.", "",
             "| Dataset | Method | Items | Credibility T/binary N | Conformability T/binary N |",
             "| --- | --- | ---: | ---: | ---: |"]
    for row in table:
        lines.append(f"| {row['Dataset']} | {row['Method']} | {row['completed_items']}/{row['planned']} | "
                     f"{row['credibility_true']}/{row['credibility_binary_n']} | {row['conformability_true']}/{row['conformability_binary_n']} |")
    lines.extend(["", "Zero binary N means unresolved or pending, not zero percent. Full coverage and failure counts are in CSV.",
                  "Playbook inclusion/application traces are diagnostic self-reports, not proof of causal benefit.", ""])
    write_text(run / "results_table_online.md", "\n".join(lines), replace=True)
    old = read(run / "status.json") if (run / "status.json").exists() else {}
    quality_pairs = sum(q.get("status") == "valid" and all(type(q["value"][m]) is bool for m in ("credibility", "conformability"))
                        for r in stream for q in r["quality"].values())
    timings = {}
    for path in sorted((run / "calls").glob("**/response.json"), key=lambda p: p.stat().st_mtime):
        response = read(path)
        timings.setdefault(response["role"], []).append(response["wall_seconds"])
    medians = {role: statistics.median(values[-50:]) for role, values in timings.items()}
    dev_left = sum(j["phase"] == "development" for j in jobs) - sum(r["phase"] == "development" for r in completed)
    stream_left = 4 * config["stream_n"] - len(stream)
    needed = {"online_detector": dev_left + 2 * stream_left, "online_learning": dev_left + stream_left,
              "online_audit": dev_left + stream_left, "reference": stream_left, "quality": 2 * stream_left}
    eta = sum(medians[k] * n for k, n in needed.items() if n) if all(k in medians for k, n in needed.items() if n) else None
    failures = {stage: sum(s.get("status") == "technical_failure" for r in completed for s in
                (list(r["predictions"].values()) if stage == "prediction" else
                 list(r["quality"].values()) if stage == "quality" else [r.get(stage, {})]))
                for stage in ("prediction", "quality", "reference", "learning")}
    report = {"at": legacy.now(), "status": status or old.get("status", "prepared_not_started"),
              "development_completed": sum(r["phase"] == "development" for r in completed),
              "development_expected": config["development_n"] * config["epochs"] * 4,
              "stream_completed": len(stream), "stream_expected": 4 * config["stream_n"],
              "binary_quality_pairs": quality_pairs, "quality_pairs_expected": 8 * config["stream_n"],
              "current": read(run / "phase.json") if (run / "phase.json").exists() else None,
              "remaining_work_seconds_provisional": eta, "role_median_seconds": medians,
              "technical_failures_by_stage": failures,
              "eta_assumption": "Maximum one audit per remaining item; partial in-flight item not subtracted.",
              "playbooks": playbooks, "manuscript_eligible": False}
    write_json(run / "status.json", report, replace=True)
    if stream and len(stream) % 50 == 0:
        checkpoint = run / "checkpoints" / f"items-{len(stream):04d}.json"
        if not checkpoint.exists():
            write_json(checkpoint, {"stream_items": len(stream), "rows": table, "paired": paired,
                                   "playbooks": playbooks, "result_ids": [r["id"] for r in stream]})
    if status == "completed":
        unresolved = quality_pairs < 8 * config["stream_n"]
        immutable(run / "final_manifest.json", {"status": "completed_with_unresolved_quality" if unresolved else "completed_binary_quality",
            "completed_items": len(stream), "binary_quality_pairs": quality_pairs, "table_rows": len(table),
            "manuscript_eligible": False, "files": {name: file_hash(run / name) for name in
                ("results_table_online.csv", "results_table_online.md", "paired_comparison.csv", "playbook_result.csv", "learning_curve.csv")}})
    return report


def run_local(run, resume=False):
    manifest = verify(run)
    require(not (run / "final_manifest.json").exists(), "terminal_run_not_resumable")
    project = Path(manifest["project_root"])
    # Use the legacy project-wide lock as well: suspended old workers still own it.
    global_path = project / "Storage/rq2_personal_local_diagnostic/ace_flaw_8h.lock"
    with global_path.open("a") as global_lock, (run / "worker.lock").open("a") as local_lock:
        fcntl.flock(global_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(local_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = read(run / "config.json")
        require(legacy.model_identity() == config["model_digest"], "installed_model_digest_changed")
        if resume and (run / "PAUSE.request.json").exists():
            history = run / "pause_history"
            history.mkdir(exist_ok=True)
            (run / "PAUSE.request.json").rename(history / f"resumed-{time.time_ns()}.json")
        require(not (run / "PAUSE.request.json").exists(), "pause_request_still_present")
        clock_path = run / "clock.json"
        if not clock_path.exists():
            started = time.time()
            write_json(clock_path, {"started_unix": started, "deadline_unix": started + config["budget_seconds"]})
        deadline = read(clock_path)["deadline_unix"] - config["reserve_seconds"]
        try:
            return worker(run, Client(run, deadline))
        except BudgetStop:
            return export(run, "stopped_budget_incomplete")
        except Exception as exc:
            write_json(run / "supervisor_error.json", {"at": legacy.now(), "type": type(exc).__name__, "error": str(exc)}, replace=True)
            export(run, "needs_attention_no_automatic_retry")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "status", "run", "resume", "pause"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--epochs", type=int, default=3, choices=[0, 1, 3])
    parser.add_argument("--authorize-local-inference", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.command == "prepare":
        require(args.source_run is not None, "source_run_required")
        result = prepare(run, args.source_run.resolve(), args.epochs)
    elif args.command == "status":
        verify(run)
        result = read(run / "status.json")
    elif args.command == "pause":
        verify(run)
        require(not (run / "final_manifest.json").exists(), "already_terminal")
        if not (run / "PAUSE.request.json").exists():
            write_json(run / "PAUSE.request.json", {"at": legacy.now(), "action": "finish_current_item_then_pause"})
        result = {"status": "pause_requested", "meaning": "Not paused until status confirms an item boundary."}
    else:
        require(args.authorize_local_inference, "explicit_local_inference_authorization_required")
        result = run_local(run, resume=args.command == "resume")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
