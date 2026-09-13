"""Offline, type-and-evidence-grounded detection scoring. Never calls an LLM."""

import argparse
import json
from pathlib import Path

import networkx as nx
from jsonschema import Draft202012Validator

import ace_flaw_contract as contract
import run_ace_flaw_8h as io


VERSION = "claim-flaw-detection-scoring-v2"
# Same taxonomy bridge as score_working_detection_table.py, not newly inferred synonyms.
INTENDED_TO_CATEGORY = {
    "unsupported_evidence": "unsupported_inference",
    "source_concentration": "hidden_source_concentration",
    "counterevidence_loss": "lost_negative_case",
    "contextual_flattening": "contextual_flattening",
    "unsupported_abstraction": "unsupported_abstraction",
}
CRITERIA = ("same_target", "same_mechanism", "evidence_supports_flaw", "material_consequence_correct")
PAIR = contract.obj({"prediction_id": contract.TEXT, "gold_id": contract.TEXT,
    **{key: contract.TRI for key in CRITERIA}, "reason": contract.TEXT,
    "evidence": contract.array(contract.ANCHOR), "whole_packet_reason": contract.TEXT})
GOLD = contract.obj({"packet_id": contract.TEXT, "task_sha256": contract.TEXT,
    "annotation_status": {"enum": ["adjudicated"]}, "inventory_complete": {"const": True},
    "verified_negative": contract.BOOL, "adjudicator": contract.TEXT, "adjudication_record": contract.TEXT,
    "review": contract.REVIEW})
RECEIPT = contract.obj({"task_sha256": contract.TEXT, "prediction_sha256": contract.TEXT,
    "gold_sha256": contract.TEXT, "assessor": contract.TEXT, "assessment_record": contract.TEXT,
    "pairs": contract.array(PAIR, 64)})
JUDGE_PROMPT = contract.COMMON + """Compare the LOCKED flaw inventory to the supplied
adjudicated gold inventory. You cannot edit either inventory or assign official
TP/FP/FN counts. Assess EVERY supplied candidate pair. Equal category is only a
prerequisite, not a successful match: require the same claim target, the same
failed warrant/mechanism, evidence establishing that flaw, and a correct material
consequence. Give each criterion true/false/null with a specific reason and exact
evidence. For a whole-packet absence argument, explain the missing warrant in
whole_packet_reason. Do not infer a reported issue from rationale prose when the
locked issues array is empty. Different types cannot match, and an issue cannot
match multiple gold flaws for credit. The program performs one-to-one matching.
Also assess RAW review credibility (defensible diagnoses and disposition) and
conformability (faithful, traceable evidence and context), with reasons. These
ratings cannot override failed detection. Empty output on a positive gold case
does not pass. Do not guess unknown judgments to make them binary. If the gold
appears materially disputed, use null on affected criteria and explain it.
No method identity, Playbook, previous score, or future item is available.
"""


def judge_schema(data):
    fields = {k: v for k, v in PAIR["properties"].items() if k not in ("prediction_id", "gold_id")}
    return contract.obj({"pairs": contract.obj({p["key"]: contract.obj(fields) for p in data["candidate_pairs"]}),
        "credibility": contract.TRI, "conformability": contract.TRI,
        "credibility_reason": contract.TEXT, "conformability_reason": contract.TEXT})


def decode_judge(value, data):
    Draft202012Validator(judge_schema(data)).validate(value)
    io.require(value["credibility_reason"].strip() and value["conformability_reason"].strip(), "quality_reasons_required")
    return value


def judge_input(packet, review, gold, preliminary):
    return {"task": packet["task"], "review": review, "gold_review": gold["review"],
        "integrity_findings": preliminary.get("integrity_findings", []),
        "candidate_pairs": [{"key": f"pair_{n}", "prediction_id": p, "gold_id": g}
            for n, (p, g) in enumerate(preliminary.get("required_pairs", []), 1)]}


def judge_receipt(packet, review, gold, data, value, assessor, record):
    decode_judge(value, data)
    return {"task_sha256": io.digest(packet["task"]), "prediction_sha256": io.digest(review),
        "gold_sha256": io.digest(gold), "assessor": assessor, "assessment_record": record,
        "pairs": [{"prediction_id": pair["prediction_id"], "gold_id": pair["gold_id"],
                   **value["pairs"][pair["key"]]} for pair in data["candidate_pairs"]]}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def validate_gold(packet, gold):
    Draft202012Validator(GOLD).validate(gold)
    io.require(gold["packet_id"] == packet["packet_id"] and gold["task_sha256"] == io.digest(packet["task"]),
               "gold_task_binding")
    io.require(gold["adjudicator"].strip() and gold["adjudication_record"].strip(), "gold_provenance_required")
    io.require(not contract.check_review(gold["review"], packet["task"])["integrity_findings"], "gold_integrity_failure")
    issues = gold["review"]["issues"]
    io.require((bool(issues) and gold["review"]["decision"] == "established_flaw" and not gold["verified_negative"])
               or (not issues and gold["review"]["decision"] == "no_flaw_established" and gold["verified_negative"]),
               "positive_or_verified_negative_gold_required")
    io.require(not gold["review"]["unresolved"], "gold_inventory_not_resolved")


def score_packet(packet, review, gold, adjudication=None, quality=None, execution_status="completed"):
    """Score locked predictions only. Unknown gold/adjudication never becomes a pass."""
    io.require(execution_status in ("completed", "technical_failure", "pending"), "invalid_execution_status")
    result = {"protocol": VERSION, "packet_id": packet["packet_id"], "task_sha256": io.digest(packet["task"]),
              "execution_status": execution_status, "status": "gold_unavailable", "tp": None, "fp": None,
              "fn": None, "exact_packet_correct": None, "detection_gated_credibility": None,
              "detection_gated_conformability": None, "manuscript_eligible": False}
    if gold is None or gold.get("annotation_status") != "adjudicated" or gold.get("inventory_complete") is not True:
        return result
    validate_gold(packet, gold)
    expected = gold["review"]["issues"]
    result.update(gold_sha256=io.digest(gold), gold_issue_n=len(expected), verified_negative=gold["verified_negative"])
    if execution_status == "pending":
        result["status"] = "pending"
        return result
    if execution_status == "completed":
        io.require(review is not None, "completed_review_required")
        checked = contract.check_review(review, packet["task"])
        predicted = review["issues"]
        contradiction = any(f["kind"] == "decision_issue_mismatch" for f in checked["integrity_findings"])
        invalid_ids = {f["issue_id"] for f in checked["integrity_findings"] if f.get("issue_id")}
        if contradiction:
            invalid_ids.update(p["id"] for p in predicted)
        eligible = [p for p in predicted if p["id"] not in invalid_ids]
        result.update(prediction_sha256=io.digest(review), integrity_findings=checked["integrity_findings"],
                      abstained=review["decision"] == "cannot_judge")
    else:
        io.require(review is None, "technical_failure_must_not_discard_an_existing_review")
        predicted, eligible, contradiction = [], [], False
        result.update(prediction_sha256=None, integrity_findings=[], abstained=False)
    needed = {(p["id"], g["id"]) for p in eligible for g in expected if p["category"] == g["category"]}
    edges = []
    if needed:
        if adjudication is None:
            result.update(status="pair_adjudication_pending", required_pairs=[list(pair) for pair in sorted(needed)])
            return result
        Draft202012Validator(RECEIPT).validate(adjudication)
        io.require(adjudication["task_sha256"] == result["task_sha256"]
                   and adjudication["prediction_sha256"] == io.digest(review)
                   and adjudication["gold_sha256"] == io.digest(gold), "adjudication_binding")
        io.require(adjudication["assessor"].strip() and adjudication["assessment_record"].strip(), "assessor_provenance_required")
        pairs = [(p["prediction_id"], p["gold_id"]) for p in adjudication["pairs"]]
        io.require(len(pairs) == len(set(pairs)) and set(pairs) == needed, "adjudication_pair_coverage")
        uncertain = []
        for pair in adjudication["pairs"]:
            io.require(pair["reason"].strip(), "empty_pair_reason")
            _, errors = contract.anchors_checked(pair["evidence"], packet["task"])
            grounded = not errors and (bool(pair["evidence"]) or bool(pair["whole_packet_reason"].strip()))
            identity = (pair["prediction_id"], pair["gold_id"])
            if not grounded:
                uncertain.append(identity)
            elif any(pair[k] is False for k in CRITERIA):
                continue
            elif any(pair[k] is None for k in CRITERIA):
                uncertain.append(identity)
            else:
                edges.append(identity)
        if uncertain:
            result.update(status="pair_adjudication_pending", unresolved_pairs=[list(pair) for pair in sorted(uncertain)])
            return result
    graph = nx.Graph()
    left = [("prediction", p["id"]) for p in predicted]
    right = [("gold", g["id"]) for g in expected]
    graph.add_nodes_from(left, bipartite=0)
    graph.add_nodes_from(right, bipartite=1)
    graph.add_edges_from((("prediction", p), ("gold", g)) for p, g in sorted(edges))
    matching = nx.algorithms.bipartite.maximum_matching(graph, top_nodes=left)
    matches = sorted((p[1], matching[p][1]) for p in left if p in matching)
    tp, fp, fn = len(matches), len(predicted) - len(matches), len(expected) - len(matches)
    exact = (execution_status == "completed" and not result["abstained"] and not contradiction
             and tp == len(expected) and fp == 0 and not review["unresolved"])
    by_type = []
    matched_p, matched_g = {p for p, _ in matches}, {g for _, g in matches}
    for category in contract.CATEGORIES:
        ps, gs = [p for p in predicted if p["category"] == category], [g for g in expected if g["category"] == category]
        by_type.append({"category": category, "tp": sum(p["id"] in matched_p for p in ps),
                        "fp": sum(p["id"] not in matched_p for p in ps), "fn": sum(g["id"] not in matched_g for g in gs),
                        "gold_n": len(gs), "predicted_n": len(ps)})
    result.update(status="scored", tp=tp, fp=fp, fn=fn, predicted_issue_n=len(predicted), matches=matches,
                  exact_packet_correct=exact, true_negative=bool(gold["verified_negative"] and exact),
                  by_type=by_type, precision=ratio(tp, tp + fp), recall=ratio(tp, tp + fn),
                  f1=ratio(2 * tp, 2 * tp + fp + fn))
    for metric in ("credibility", "conformability"):
        value = (quality or {}).get(metric)
        io.require(value is None or type(value) is bool, "invalid_quality_value")
        # These are newly named composite endpoints, never replacements for old raw judge scores.
        result["detection_gated_" + metric] = value if exact else False
    return result


def aggregate(records, expected_n):
    io.require(expected_n > 0 and len(records) <= expected_n, "invalid_planned_count")
    ids = [r["packet_id"] for r in records]
    io.require(len(ids) == len(set(ids)), "duplicate_packet_within_arm")
    ready = [r for r in records if r["status"] == "scored"]
    attempted = [r for r in records if r["execution_status"] != "pending"]
    full = len(ready) == expected_n
    tp, fp, fn = (sum(r[k] for r in ready) for k in ("tp", "fp", "fn"))
    result = {"planned_packets": expected_n, "attempted_packets": len(attempted), "scored_packets": len(ready),
              "unresolved_or_pending_packets": expected_n - len(ready), "confirmed_tp": tp,
              "fp_in_scored_packets": fp, "fn_in_scored_packets": fn,
              "status": "complete" if full else "incomplete_no_headline_rate", "precision": None,
              "recall": None, "f1": None, "exact_packet_accuracy": None, "specificity": None,
              "confirmed_exact_correct_fraction_of_plan": sum(r["exact_packet_correct"] for r in ready) / expected_n,
              "technical_failures": sum(r["execution_status"] == "technical_failure" for r in attempted),
              "abstentions": sum(bool(r.get("abstained")) for r in attempted)}
    result["by_type"] = []
    for category in contract.CATEGORIES:
        counts = [c for r in ready for c in r["by_type"] if c["category"] == category]
        a, b, c = (sum(r[k] for r in counts) for k in ("tp", "fp", "fn"))
        result["by_type"].append({"category": category, "confirmed_tp": a, "fp_in_scored_packets": b,
            "fn_in_scored_packets": c, "gold_n_in_scored_packets": a + c,
            "precision": ratio(a, a + b) if full else None, "recall": ratio(a, a + c) if full else None,
            "f1": ratio(2 * a, 2 * a + b + c) if full else None})
    result["macro_f1_over_gold_supported_types"] = None
    for metric in ("credibility", "conformability"):
        key = "detection_gated_" + metric
        true = sum(r[key] is True for r in ready)
        false = sum(r[key] is False for r in ready)
        result[key] = {"true": true, "false": false, "unresolved_or_pending": expected_n - true - false,
                       "success_rate": true / expected_n if true + false == expected_n else None}
    if full:
        negatives = [r for r in ready if r["verified_negative"]]
        result.update(precision=ratio(tp, tp + fp), recall=ratio(tp, tp + fn), f1=ratio(2 * tp, 2 * tp + fp + fn),
                      exact_packet_accuracy=sum(r["exact_packet_correct"] for r in ready) / expected_n,
                      specificity=ratio(sum(r["true_negative"] for r in negatives), len(negatives)))
        supported = [r["f1"] for r in result["by_type"] if r["gold_n_in_scored_packets"] > 0]
        result["macro_f1_over_gold_supported_types"] = ratio(sum(supported), len(supported))
    return result


def validate_bank(bank, inputs):
    io.require(bank.get("protocol") == VERSION, "wrong_gold_bank_protocol")
    expected = {(ds, p["packet_id"]): p for ds, phases in inputs.items() for p in phases["evaluation"]}
    index = {}
    for row in bank["items"]:
        identity = (row["dataset"], row["packet_id"])
        io.require(identity in expected and identity not in index, "gold_bank_identity_or_duplicates")
        value = {key: field for key, field in row.items() if key != "dataset"}
        validate_gold(expected[identity], value)
        index[identity] = value
    io.require(set(index) == set(expected), "gold_bank_incomplete")
    return index


def audit_existing(run):
    """Recover intended labels through hash-bound source packets, not model references."""
    manifest, plan, inputs = (io.read(run / name) for name in ("manifest.json", "plan.json", "inputs.private.json"))
    for name, expected in manifest["files"].items():
        io.require(io.file_hash(run / name) == expected, "frozen_source_changed:" + name)
    source = io.PROJECT / plan["candidate_run"]
    upstream = io.read(source / "manifest.json")
    selected, provenance = {}, {}
    for ds in plan["datasets"]:
        rows = {p["packet_id"]: p for p in inputs[ds]["evaluation"]}
        split = upstream["splits"][ds]
        path = Path(split["evaluation_file"])
        io.require(io.file_hash(path) == split["evaluation_file_sha256"], "source_split_changed")
        found = set()
        with path.open() as handle:
            for line in handle:
                original = json.loads(line)
                pid = original["packet_id"]
                if pid not in rows:
                    continue
                io.require(pid not in found and io.digest(original) == rows[pid]["original_packet_sha256"], "original_packet_identity")
                intended = original["known_intended_flaw_type"]
                io.require(intended in INTENDED_TO_CATEGORY, "unmapped_intended_type")
                selected[(ds, pid)] = {"packet": rows[pid], "intended_type": intended,
                                      "category": INTENDED_TO_CATEGORY[intended]}
                found.add(pid)
        io.require(found == set(rows), "incomplete_label_coverage")
        provenance[ds] = {"source_file": str(path), "sha256": io.file_hash(path), "selected_packets": len(found)}
    raw_rows = [r for r in io.records(run) if r["phase"] == "evaluation"]
    raw = {r["id"]: r for r in raw_rows}
    io.require(len(raw) == len(raw_rows), "duplicate_result_identity")
    details, table = [], []
    for ds in plan["datasets"]:
        for checkpoint in plan["core_checkpoints"]:
            group = []
            for packet in inputs[ds]["evaluation"]:
                pid, label = packet["packet_id"], selected[(ds, packet["packet_id"])]
                result = raw.get(f"core/{ds}/{checkpoint}/{pid}")
                if result is not None:
                    io.require(result["task_sha256"] == packet["task_sha256"], "result_task_mismatch")
                    if result.get("review") is not None:
                        locked = io.read(run / "predictions" / result["id"] / "locked.json")
                        io.require(io.digest(locked) == result["prediction_sha256"] and locked["review"] == result["review"],
                                   "locked_review_changed")
                review = result.get("review") if result else None
                categories = [i["category"] for i in review["issues"]] if review else []
                hit = bool(review and review["decision"] == "established_flaw" and label["category"] in categories)
                row = {"dataset": ds, "checkpoint": checkpoint, "packet_id": pid, "intended_type": label["intended_type"],
                       "canonical_category": label["category"], "processed": result is not None,
                       "decision": review["decision"] if review else None, "predicted_categories": categories,
                       "intended_type_present": hit if result else None,
                       "strict_detection_score": None, "gold_status": "intended_only_not_adjudicated"}
                group.append(row)
                details.append(row)
            for category in ["ALL", *INTENDED_TO_CATEGORY.values()]:
                subset = [r for r in group if category == "ALL" or r["canonical_category"] == category]
                processed = [r for r in subset if r["processed"]]
                hits = sum(r["intended_type_present"] is True for r in processed)
                table.append({"dataset": ds, "checkpoint": checkpoint, "category": category, "planned": len(subset),
                              "processed": len(processed), "pending": len(subset) - len(processed),
                              "intended_type_hits": hits, "intended_type_misses": len(processed) - hits,
                              "intended_type_presence_rate": ratio(hits, len(processed)),
                              "strict_precision": None, "strict_recall": None, "strict_f1": None})
    return {"protocol": VERSION, "analysis": "posthoc_intended_type_inventory_only", "source_run": str(run),
            "source_manifest_sha256": io.file_hash(run / "manifest.json"), "source_files": provenance,
            "manuscript_eligible": False, "new_model_calls": 0,
            "limitation": "Intended labels are not complete adjudicated flaw inventories. Type presence is not strict detection correctness.",
            "table": table, "items": details}


def audit_markdown(report):
    rows = report["table"]
    lines = ["# Flaw-Type Detection Audit", "", "Post-hoc private diagnostic. No new model calls or rewritten outputs.", "",
             "Type presence means the locked final issue list names the intended category and its decision establishes a flaw.",
             "These are generator-intended labels, not independently adjudicated truth. Strict P/R/F1 remain unavailable.", "",
             "| Dataset | Checkpoint | Intended category | Hits / processed | Pending |",
             "| --- | --- | --- | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {io.DISPLAY[row['dataset']]} | {row['checkpoint']} | {row['category']} | "
                     f"{row['intended_type_hits']}/{row['processed']} | {row['pending']} |")
    lines.extend(["", "A no_flaw_established decision with an empty issue list cannot be rescued by a positive review-quality judgment.",
                  "Unknown/pending gold is not a negative label and does not qualify a headline detection rate.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit-existing"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    io.require(out.is_relative_to((io.PROJECT / "Storage").resolve()), "private_storage_only")
    report = audit_existing(args.run_dir.resolve())
    out.mkdir(parents=True, exist_ok=False)
    io.write_json(out / "intended_type_audit.private.json", report)
    io.write_text(out / "flaw_type_detection_audit.md", audit_markdown(report))
    print(json.dumps({"output_dir": str(out), "new_model_calls": 0,
                      "all_category_rows": [r for r in report["table"] if r["category"] == "ALL"]}, indent=2))


if __name__ == "__main__":
    main()
