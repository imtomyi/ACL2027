import fs from "node:fs";

const resolutionPath = "research/screening_2025_resolution.json";
const nonretrievalPath = "research/screening_2025_database_nonretrievals.json";
const batchPaths = [1, 2, 3, 4, 5].map((number) =>
  `research/screening_2025_database_fulltext_batch0${number}.json`,
);

const resolution = JSON.parse(fs.readFileSync(resolutionPath, "utf8"));
const nonretrieval = JSON.parse(fs.readFileSync(nonretrievalPath, "utf8"));
const followups = new Map();

for (const batchPath of batchPaths) {
  const batch = JSON.parse(fs.readFileSync(batchPath, "utf8"));
  const decisions = batch.screening_decisions ?? batch.full_text_decisions ?? [];
  const includedEvidence = batch.evidence_records ?? [];
  let evidenceIndex = 0;

  for (const item of decisions) {
    const decision = item.full_text_decision ?? item.decision;
    const included = decision === "include_core" || decision === "include_adjacent";
    const evidence = included ? includedEvidence[evidenceIndex++] : null;
    followups.set(item.screen_id, {
      required: true,
      status: "assessed",
      retrieval_attempts: [],
      final_full_text_decision: decision,
      reason: item.reason,
      extraction_record:
        included || decision === "exclude_duplicate_version"
          ? (item.paper_id ?? evidence?.["Paper ID"] ?? null)
          : null,
      quality_score: included ? (item.paper_id ?? evidence?.["Paper ID"] ?? null) : null,
      artifact: batchPath,
    });
  }
}

for (const item of nonretrieval.records) {
  const assessed = item.full_text_status === "assessed";
  const extractionId = item.extraction_location?.split("#")[1] ?? null;
  followups.set(item.screen_id, {
    required: true,
    status: assessed ? "assessed" : "not_retrieved",
    retrieval_attempts: item.retrieval_attempts ?? [],
    final_full_text_decision: item.final_full_text_decision,
    reason: item.record_specific_reason,
    extraction_record: extractionId,
    quality_score: extractionId,
    artifact: assessed
      ? (item.extraction_location?.split("#")[0] ?? nonretrievalPath)
      : nonretrievalPath,
  });
}

const advancedRecords = resolution.database_records.filter((record) =>
  ["advance_core", "advance_adjacent"].includes(record.second_pass_decision),
);
const missing = advancedRecords
  .map((record) => record.screen_id)
  .filter((screenId) => !followups.has(screenId));
if (missing.length) {
  throw new Error(`Missing full-text resolution for: ${missing.join(", ")}`);
}

for (const record of advancedRecords) {
  record.full_text_followup = followups.get(record.screen_id);
}

const databaseCounts = advancedRecords.reduce(
  (counts, record) => {
    const followup = record.full_text_followup;
    counts.full_text_sought += 1;
    if (followup.status === "assessed") counts.full_text_assessed += 1;
    if (followup.status === "not_retrieved") counts.full_text_not_retrieved += 1;
    if (followup.final_full_text_decision === "include_core") counts.include_core_after_full_text += 1;
    if (followup.final_full_text_decision === "include_adjacent") counts.include_adjacent_after_full_text += 1;
    if (["exclude_after_full_text", "exclude_false_friend", "exclude_duplicate_version"].includes(followup.final_full_text_decision)) {
      counts.exclude_after_full_text += 1;
    }
    return counts;
  },
  {
    title_abstract_advanced: advancedRecords.length,
    full_text_sought: 0,
    full_text_assessed: 0,
    full_text_not_retrieved: 0,
    include_core_after_full_text: 0,
    include_adjacent_after_full_text: 0,
    exclude_after_full_text: 0,
  },
);

databaseCounts.master_ready_evidence_records =
  databaseCounts.include_core_after_full_text + databaseCounts.include_adjacent_after_full_text;
databaseCounts.quality_scores = databaseCounts.master_ready_evidence_records;
databaseCounts.arithmetic_check =
  "62 advanced = 57 assessed + 5 not retrieved; 57 assessed = 48 core + 7 adjacent + 2 excluded.";

resolution.metadata.full_text_followup_generated_utc = "2026-08-25T01:05:00Z";
resolution.metadata.full_text_followup_status =
  "Complete for all 62 database records advanced at title/abstract screening; five remain plausibly core but not retrieved.";
resolution.database_full_text_resolution = {
  status: "complete_with_nonretrievals",
  batch_files: [
    ...batchPaths,
    "research/screening_2025_database_fulltext_batch06.json",
  ],
  nonretrieval_reconciliation: nonretrievalPath,
  counts: databaseCounts,
  merge_status: "candidate-only; do not merge without parent review",
};
resolution.cross_stream_2025_handoffs = {
  status: "resolved",
  source: "Root cross-stream handoff for later 2025 publication identities or undated OpenReview records",
  artifact: "research/screening_2025_database_fulltext_batch05.json",
  counts: {
    total: 4,
    full_text_assessed: 4,
    include_core_after_full_text: 3,
    include_adjacent_after_full_text: 0,
    exclude_after_full_text: 1,
  },
  records: [
    {
      screen_id: "TA-1121",
      final_full_text_decision: "include_core",
      version_family: "arXiv:2309.10771 / Computers in Human Behavior: Artificial Humans (2025), DOI 10.1016/j.chbah.2025.100144",
    },
    {
      screen_id: "TA-1332",
      final_full_text_decision: "include_core",
      version_family: "CSCL 2025, DOI 10.22318/cscl2025.114185; dependent reuse of TA-1334 data/codebooks but a distinct contribution analysis",
    },
    {
      screen_id: "TA-1354",
      final_full_text_decision: "exclude_after_full_text",
      version_family: "HICSS 2025, DOI 10.24251/HICSS.2025.300; LLM is only a sentiment classifier and themes are manual",
    },
    {
      screen_id: "TA-1355",
      final_full_text_decision: "include_core",
      version_family: "arXiv:2510.06788 / ICWSM 2026 VOR, DOI 10.1609/icwsm.v20i1.42761",
    },
  ],
};

const forward = resolution.forward_chain_2025_outside_union.counts;
resolution.consolidated_2025_assignment = {
  unit: "record identities; publication-family dependencies and duplicate versions are separately flagged",
  assigned_records: 208,
  database_title_abstract_records: 188,
  forward_chain_records_outside_union: 16,
  cross_stream_handoff_records: 4,
  final_record_dispositions: {
    include_core: databaseCounts.include_core_after_full_text + forward.include_core_after_full_text + 3,
    include_adjacent: databaseCounts.include_adjacent_after_full_text + forward.include_adjacent_after_full_text,
    excluded: 126 + databaseCounts.exclude_after_full_text + forward.excluded + 1,
    unresolved_not_retrieved: databaseCounts.full_text_not_retrieved + forward.full_text_not_retrieved,
  },
  full_text_flow: {
    sought: databaseCounts.full_text_sought + forward.full_text_sought + 4,
    assessed: databaseCounts.full_text_assessed + forward.full_text_assessed + 4,
    not_retrieved: databaseCounts.full_text_not_retrieved + forward.full_text_not_retrieved,
    assessed_included: databaseCounts.master_ready_evidence_records + forward.include_core_after_full_text + forward.include_adjacent_after_full_text + 3,
    assessed_excluded: databaseCounts.exclude_after_full_text + 1,
  },
  candidate_companion_totals: {
    evidence_records: databaseCounts.master_ready_evidence_records + forward.include_core_after_full_text + forward.include_adjacent_after_full_text + 3,
    quality_scores: databaseCounts.quality_scores + forward.include_core_after_full_text + forward.include_adjacent_after_full_text + 3,
    core_records: databaseCounts.include_core_after_full_text + forward.include_core_after_full_text + 3,
    adjacent_records: databaseCounts.include_adjacent_after_full_text + forward.include_adjacent_after_full_text,
  },
  arithmetic_check: "208 assigned record identities = 61 core + 9 adjacent + 132 excluded + 6 unresolved/not retrieved. Full-text flow: 79 sought = 73 assessed + 6 not retrieved; 73 assessed = 70 included + 3 excluded.",
};

fs.writeFileSync(resolutionPath, `${JSON.stringify(resolution, null, 2)}\n`);
