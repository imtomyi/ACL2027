import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const targetPath = path.join(ROOT, "latest_additions.json");
const masterPath = path.join(ROOT, "master_evidence.json");
const source = JSON.parse(fs.readFileSync(targetPath, "utf8"));
const master = JSON.parse(fs.readFileSync(masterPath, "utf8"));
const columns = master.metadata.extraction_columns;
const dimensions = master.metadata.quality_dimensions || master.quality_dimensions;

if (!Array.isArray(columns) || columns.length !== 52) throw new Error("Master schema must contain exactly 52 extraction columns");
if (!Array.isArray(dimensions) || dimensions.length !== 12) throw new Error("Master schema must contain exactly 12 quality dimensions");

const priorLocations = new Map((source.evidence_locations || []).map((row) => [row["Paper ID"], row.locations]));
const priorClaims = new Map((source.author_reported_claims || []).map((row) => [row["Paper ID"], row.claims]));
const priorReviewerNotes = new Map((source.reviewer_validity_notes || []).map((row) => [row["Paper ID"], row.concerns]));

const evidenceLocations = [];
const authorReportedClaims = [];
const reviewerValidityNotes = [];
const evidenceRecords = source.evidence_records.map((record) => {
  const paperId = record["Paper ID"];
  evidenceLocations.push({
    "Paper ID": paperId,
    locations: record["Evidence locations"] || priorLocations.get(paperId) || ["not reported"],
  });
  authorReportedClaims.push({
    "Paper ID": paperId,
    claims: record["Author-reported claims"] || priorClaims.get(paperId) || ["not reported"],
  });
  reviewerValidityNotes.push({
    "Paper ID": paperId,
    concerns: record["Reviewer-identified validity concerns"] || priorReviewerNotes.get(paperId) || [record["Additional validity concerns"] || "not reported"],
  });
  return Object.fromEntries(columns.map((column) => [column, record[column] ?? "not reported"]));
});

const qualityAliases = new Map([
  ["Clarity of its qualitative methodology", "Clarity of qualitative methodology"],
  ["Appropriateness of its dataset", "Appropriateness of dataset"],
  ["Transparency of its computational workflow", "Transparency of computational workflow"],
  ["Strength and independence of its baselines", "Strength and independence of baselines"],
  ["Adequacy of its human evaluation", "Adequacy of human evaluation"],
  ["Validity of its automatic metrics", "Validity of automatic metrics"],
  ["Whether conclusions are proportionate to the evidence", "Conclusions proportionate to evidence"],
]);
if (!Array.isArray(source.quality_scores)) throw new Error("Missing quality_scores array");
const qualityScores = source.quality_scores.map((row) => {
  const normalizedDimensions = Object.fromEntries(dimensions.map((dimension) => {
    const sourceKey = qualityAliases.get(dimension) || dimension;
    const item = row["Dimension scores"]?.[dimension] || row["Dimension scores"]?.[sourceKey];
    if (!item) throw new Error(`Missing quality dimension ${sourceKey} for ${row["Paper ID"]}`);
    return [dimension, item];
  }));
  return {...row, "Dimension scores": normalizedDimensions};
});
if (evidenceRecords.some((record) => Object.keys(record).length !== 52 || columns.some((column) => !(column in record)))) {
  throw new Error("52-field evidence invariant failed");
}
if (qualityScores.some((row) => Object.keys(row["Dimension scores"] || {}).length !== 12 || dimensions.some((dimension) => !(dimension in row["Dimension scores"])))) {
  throw new Error("12-dimension quality invariant failed");
}
const evidenceIds = new Set(evidenceRecords.map((record) => record["Paper ID"]));
const qualityIds = new Set(qualityScores.map((row) => row["Paper ID"]));
if (evidenceIds.size !== evidenceRecords.length || qualityIds.size !== qualityScores.length || [...evidenceIds].some((id) => !qualityIds.has(id))) {
  throw new Error("Evidence/quality identity invariant failed");
}

const normalized = {
  metadata: {
    ...source.metadata,
    extraction_columns: columns,
    extraction_column_count: columns.length,
    quality_dimensions: dimensions,
    quality_dimension_count: dimensions.length,
    quality_scoring: source.quality_dimensions?.scale || "0 = absent/inadequate, 1 = partial, 2 = adequate for the paper's stated claim",
    schema_note: "Evidence records contain exactly the master's 52 fields. Extended author-claim, evidence-location, and reviewer-validity audit notes are preserved in separate top-level arrays.",
  },
  source_verification: source.source_verification,
  evidence_records: evidenceRecords,
  evidence_locations: evidenceLocations,
  author_reported_claims: authorReportedClaims,
  reviewer_validity_notes: reviewerValidityNotes,
  quality_dimensions: dimensions,
  quality_scores: qualityScores,
};

fs.writeFileSync(targetPath, `${JSON.stringify(normalized, null, 2)}\n`);
console.log(JSON.stringify({evidence_records: evidenceRecords.length, quality_scores: qualityScores.length}, null, 2));
