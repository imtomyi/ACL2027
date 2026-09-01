import fs from "node:fs";

const sourceFiles = [
  "research/screening_2025_database_fulltext_batch01.json",
  "research/screening_2025_database_fulltext_batch02.json",
  "research/screening_2025_database_fulltext_batch03.json",
  "research/screening_2025_database_fulltext_batch04.json",
  "research/screening_2025_database_fulltext_batch05.json",
  "research/screening_2025_database_fulltext_batch06.json",
  "research/screening_2025_forward_chain_extractions.json",
];
const outputPath = "research/screening_2025_fulltext_extractions.json";

const sources = sourceFiles.map((path) => ({
  path,
  payload: JSON.parse(fs.readFileSync(path, "utf8")),
}));
const extractionColumns = sources[0].payload.metadata.extraction_columns;
const qualityDimensions = sources[0].payload.metadata.quality_dimensions;
const evidenceRecords = sources.flatMap(({ payload }) => payload.evidence_records ?? []);
const qualityScores = sources.flatMap(({ payload }) => payload.quality_scores ?? []);
const recordSources = Object.fromEntries(
  sources.flatMap(({ path, payload }) =>
    (payload.evidence_records ?? []).map((record) => [record["Paper ID"], path]),
  ),
);

const normalize = (value) =>
  String(value ?? "")
    .toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, "")
    .replace(/[^a-z0-9]+/g, "");
const meaningfulDoi = (value) => value && value !== "not reported";

const fail = (message) => {
  throw new Error(message);
};

for (const record of evidenceRecords) {
  const keys = Object.keys(record);
  if (keys.length !== 52 || extractionColumns.some((column) => !(column in record))) {
    fail(`Evidence schema failure for ${record["Paper ID"]}: ${keys.length} fields`);
  }
}
for (const score of qualityScores) {
  const dimensions = Object.keys(score["Dimension scores"] ?? {});
  if (
    dimensions.length !== 12 ||
    qualityDimensions.some((dimension) => !(dimension in score["Dimension scores"]))
  ) {
    fail(`Quality schema failure for ${score["Paper ID"]}: ${dimensions.length} dimensions`);
  }
}

const evidenceIds = evidenceRecords.map((record) => record["Paper ID"]);
const qualityIds = qualityScores.map((score) => score["Paper ID"]);
if (new Set(evidenceIds).size !== evidenceIds.length) fail("Duplicate candidate Paper ID");
if (new Set(qualityIds).size !== qualityIds.length) fail("Duplicate candidate quality Paper ID");
if (
  evidenceIds.some((id) => !qualityIds.includes(id)) ||
  qualityIds.some((id) => !evidenceIds.includes(id))
) {
  fail("Evidence/quality Paper ID mismatch");
}

const auditAgainst = (path) => {
  const payload = JSON.parse(fs.readFileSync(path, "utf8"));
  const records = payload.evidence_records ?? [];
  const doiMap = new Map(
    records
      .filter((record) => meaningfulDoi(record.DOI))
      .map((record) => [normalize(record.DOI), record["Paper ID"]]),
  );
  const titleMap = new Map(records.map((record) => [normalize(record.Title), record["Paper ID"]]));
  return evidenceRecords.flatMap((record) => {
    const match =
      (meaningfulDoi(record.DOI) && doiMap.get(normalize(record.DOI))) ||
      titleMap.get(normalize(record.Title));
    return match ? [{ candidate_id: record["Paper ID"], existing_id: match }] : [];
  });
};

const masterExactMatches = auditAgainst("research/master_evidence.json");
const earlierCompanionExactMatches = auditAgainst("research/screening_2020_2024_resolution.json");
if (masterExactMatches.length || earlierCompanionExactMatches.length) {
  fail("Exact DOI/title collision with an existing evidence stream");
}

const coreCount = evidenceRecords.filter(
  (record) => record["Core or adjacent classification"] === "core",
).length;
const adjacentCount = evidenceRecords.filter(
  (record) => record["Core or adjacent classification"] === "adjacent",
).length;

const output = {
  metadata: {
    title: "Consolidated master-ready candidate extractions from the complete 2025 second pass",
    generated_utc: "2026-08-25T01:35:00Z",
    review_cutoff: "2026-08-24",
    source_resolution: "research/screening_2025_resolution.json",
    source_files: sourceFiles,
    merge_status: "candidate-only; parent review and cross-year publication-family deduplication required before master merge",
    recommended_merge_scope: "For the pending master merge, retain only the 61 core records. The 9 clearly labeled adjacent records and scores remain in this companion for synthesis and should not be merged unless the parent explicitly reopens adjacent scope.",
    evidence_record_count: evidenceRecords.length,
    quality_score_count: qualityScores.length,
    core_record_count: coreCount,
    adjacent_record_count: adjacentCount,
    extraction_columns: extractionColumns,
    extraction_column_count: extractionColumns.length,
    quality_dimensions: qualityDimensions,
    quality_dimension_count: qualityDimensions.length,
    quality_scoring: "0 absent/inadequate; 1 partial/unclear; 2 adequate for the study's stated claim. Totals are audit aids, not rankings.",
    validation: {
      every_evidence_record_has_exactly_52_fields: true,
      every_evidence_record_has_one_12_dimension_quality_score: true,
      candidate_paper_ids_unique: true,
      candidate_quality_ids_unique: true,
      exact_doi_or_normalized_title_matches_in_current_master: masterExactMatches,
      exact_doi_or_normalized_title_matches_in_2020_2024_companion: earlierCompanionExactMatches,
    },
    cross_year_collision: {
      candidate_id: "nguyen_trung_nguyen_2026_nita",
      other_stream_id: "TA-0336",
      other_stream: "research/screening_2026_resolution.json",
      instruction: "One 2025 SSRN/2026 journal VOR family. Keep this fully inspected extraction once and suppress any duplicate 2026 extraction/merge.",
    },
    publication_family_flags: [
      "ahtisham_2026_annotation_orchestration: 2025 arXiv / 2026 LAK VOR, count once.",
      "moskalewicz_et_al_2026_computational_phenomenology_bpd: 2025 arXiv database identity / current 2026 ETHICAIA manuscript, count once and retain workshop-status caveat.",
      "jain_et_al_2026_multi_llm_dual_reliability: 2025 arXiv identifier / current 2026 v2, count once.",
      "borchers_et_al_2026_temperature_persona_consensus: 2025 arXiv / 2026 EDM VOR, count once.",
      "rodriguez_et_al_2026_text_chunking_urban: 2025 arXiv / 2026 IET Smart Cities VOR, count once.",
      "nguyen_trung_nguyen_2026_nita: 2025 SSRN / 2026 journal VOR and TA-0336 collision, count once.",
      "wei_et_al_2026_childbirth_parenthood_discourse: 2025 arXiv / 2026 ICWSM VOR, count once.",
      "zhang_et_al_2025_harnessing_ai_qualitative_research: arXiv:2309.10771 / renamed 2025 journal VOR, count once.",
      "chen_et_al_2025_processes_matter_open_coding: reuses TA-1334 corpus/codebooks but is a distinct contribution-analysis paper.",
      "than_et_al_2025_future_of_coding_llms: reuses McCall 2013 / Nelson 2018 corpus and labels.",
      "gustavsen_et_al_2025_generative_ai_qualitative_coding: reuses the Surbaugh et al. 2024 corpus and human analysis.",
      "hairston_et_al_2025_xylazine_thematic: expert themes originate in Spadaro et al. 2025; dependent computational validation.",
      "simon_et_al_2025_human_mas_consistency and sankaranarayanan_et_al_2025_ta_mas share the Simon/CSCL survey and human-analysis family.",
      "de_paoli_mathis_2025_codebook_reduction_saturation extends the De Paoli–Mathis thematic-saturation series.",
      "zhao_liu_2025_complex_confidence_diversity is a methodological companion to zhao_liu_2025_confidence_diversity, not an independent replication.",
      "zhou_et_al_2025_llm_qualitative_nursing_scoping_review is a secondary review; do not double-count its 11 constituent studies.",
    ],
  },
  record_sources: recordSources,
  evidence_records: evidenceRecords,
  quality_scores: qualityScores,
};

fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
