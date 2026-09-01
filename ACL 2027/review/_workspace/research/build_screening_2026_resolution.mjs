import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const RESEARCH = path.join(ROOT, "research");
const CUTOFF = "2026-08-24";

const flow = JSON.parse(fs.readFileSync(path.join(RESEARCH, "review_flow.json"), "utf8"));
const union = JSON.parse(fs.readFileSync(path.join(RESEARCH, "search_union_deduplicated.json"), "utf8"));
const chaining = JSON.parse(fs.readFileSync(path.join(RESEARCH, "citation_chaining.json"), "utf8"));

const advanceCore = new Set(`
TA-0004 TA-0016 TA-0025 TA-0027 TA-0029 TA-0038 TA-0040 TA-0054 TA-0064 TA-0077
TA-0090 TA-0117 TA-0120 TA-0140 TA-0144 TA-0151 TA-0153 TA-0228 TA-0231 TA-0246
TA-0251 TA-0264 TA-0276 TA-0308 TA-0314 TA-0318 TA-0330 TA-0334 TA-0336 TA-0345
TA-0346 TA-0351 TA-0370 TA-0385 TA-0386 TA-0389 TA-0424 TA-0429 TA-0441 TA-0445
TA-0450 TA-0453 TA-0460 TA-0461 TA-0477
TA-0065 TA-0089 TA-0133 TA-0175 TA-0221 TA-0294 TA-0338 TA-0382 TA-0388
`.trim().split(/\s+/));

// TA-0145 was removed after the actual abstract was inspected in the
// second pass: it is rubric-based patient-communication assessment, not
// qualitative coding, theme development, or an evaluation of either.
const advanceAdjacent = new Set(`TA-0008 TA-0255 TA-0392 TA-0419 TA-0426 TA-0475`.split(/\s+/));
const advanceContextual = new Set(`TA-0010 TA-0018 TA-0037 TA-0047 TA-0059 TA-0123 TA-0137 TA-0360 TA-0373 TA-0416 TA-0454`.split(/\s+/));
const advance = new Set([...advanceCore, ...advanceAdjacent, ...advanceContextual]);

function normalizeSpace(value) {
  return String(value ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function normalizeDoi(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//, "")
    .replace(/[\s.]+$/, "")
    .trim();
}

function normalizeTitle(value) {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function clip(value, length = 260) {
  const text = normalizeSpace(value);
  return text.length <= length ? text : `${text.slice(0, length - 1).trim()}…`;
}

function positiveEvidence(title, abstract) {
  if (!abstract) {
    return `The title directly identifies a computational qualitative-analysis contribution (${title}); no abstract was available in the union, so full text is required.`;
  }
  const sentences = normalizeSpace(abstract).split(/(?<=[.!?])\s+/);
  const scored = sentences.map((sentence, index) => {
    const lower = sentence.toLowerCase();
    let score = 0;
    if (/large language model|\bllm\b|chatgpt|generative ai|artificial intelligence|natural language processing/.test(lower)) score += 2;
    if (/qualitative|thematic|coding|codebook|theme|interpret|annotation|concept|taxonomy|cluster/.test(lower)) score += 2;
    if (/we (?:present|propose|develop|evaluate|apply|analy[sz]e)|pipeline|workflow|framework|compared|validated/.test(lower)) score += 2;
    if (/performed by|human-coded|expert|human validation|source text|inter-rater/.test(lower)) score += 1;
    return {sentence, score, index};
  }).sort((a, b) => b.score - a.score || a.index - b.index);
  return `The abstract explicitly advances a computational qualitative-analysis or directly relevant evaluation contribution: ${clip(scored[0]?.sentence || abstract)}`;
}

function exclusion(screen, abstract) {
  const title = normalizeSpace(screen.title);
  const titleLower = title.toLowerCase();
  const text = `${title} ${normalizeSpace(abstract)}`.toLowerCase();
  const topic = clip(title, 170);

  if (/scoping review|systematic review|narrative review|rapid review|review protocol|study protocol|protocol for|protocol\.$|living scoping review|meta-research study/.test(text)) {
    return {
      reason_code: "EXCLUDE_REVIEW_OR_PROTOCOL_WITHOUT_TARGET_CONTRIBUTION",
      reason: `This is a review or protocol about ${topic}; the title/abstract do not report a completed computational qualitative-analysis system or a directly applicable code/theme evaluation method.`,
    };
  }
  if (/speech|audio|voice|speaker|codec|phonolog|prosod|text-to-cad|diffusion|vision-language|multimodal emotion|talking head|gesture generation|robot control|voiceprint|facial privacy|object placement|medical diagnosis through cross-modality|compression|clip on the pretrained/.test(titleLower)) {
    return {
      reason_code: "EXCLUDE_NON_TEXT_OR_UNRELATED_COMPUTATIONAL_TASK",
      reason: `The title identifies ${topic} as a speech/audio/vision/robotics or other non-target computational task; the abstract does not present qualitative coding or thematic interpretation support.`,
    };
  }
  if (/conducting inclusive qualitative content analysis|deductive qualitative content analysis|introduction to inductive qualitative content analysis|qualitative content analysis: foundations|qualitative data analysis and reporting|the qualitative content analysis: combing/.test(text)) {
    return {
      reason_code: "EXCLUDE_NONCOMPUTATIONAL_QUALITATIVE_METHOD",
      reason: `The record is a general qualitative-method chapter (${topic}) with no LLM or computational-analysis contribution in the title/available abstract.`,
    };
  }
  if (/sentiment analysis|topic model|stance detection|classification|trial matching|demographic extraction|text simplification|summari[sz]ation|readability|report generation|question-answer|clinical scenario generation|patient education material|guideline adherence|checklist|discharge summar|communication quality/.test(text)) {
    return {
      reason_code: "EXCLUDE_NON_TARGET_MODEL_TASK",
      reason: `The model contribution in ${topic} is classification, sentiment/topic modeling, extraction, summarization, generation, or response assessment rather than qualitative coding/theme development or its evaluation.`,
    };
  }
  if (/perceptions? of|perspectives? on|experiences? (?:of|with|using)|acceptance of|adoption of|attitudes? toward|use of (?:ai|chatgpt|generative|large language)|using (?:ai|chatgpt|generative ai) (?:for|in)|ai integration|ai-mediated|ai-assisted learning|human-ai interaction|chatbot use|views? of/.test(text) && /qualitative|thematic|mixed.methods|interview|focus group|survey/.test(text)) {
    return {
      reason_code: "EXCLUDE_AI_IS_TOPIC_NOT_QUALITATIVE_ANALYST",
      reason: `The study uses interviews, surveys, focus groups, or researcher-led thematic analysis to examine experiences or perceptions of AI in ${topic}; the model is the phenomenon studied, not the qualitative analyst.`,
    };
  }
  if (/thematic analysis (?:was|is) performed|we (?:performed|conducted) (?:a )?(?:reflexive )?thematic analysis|responses were evaluated.*thematic analysis|qualitative thematic analysis of (?:chatbot|conversation|response)/.test(text)) {
    return {
      reason_code: "EXCLUDE_MANUAL_QUALITATIVE_METHOD_ONLY",
      reason: `For ${topic}, qualitative/thematic analysis is the researchers' method for studying another system or its outputs; the abstract does not make the model an analyst or evaluate computational coding.`,
    };
  }
  if (/mixed.methods|qualitative study|thematic study|qualitative perspective|qualitative case study|qualitative research/.test(text) && /chatgpt|large language model|generative ai|artificial intelligence|chatbot/.test(text)) {
    return {
      reason_code: "EXCLUDE_AI_IS_TOPIC_NOT_QUALITATIVE_ANALYST",
      reason: `The title/abstract of ${topic} describe a qualitative or mixed-methods study about an AI tool, its users, or its effects; they do not report the AI performing or evaluating qualitative analysis.`,
    };
  }
  return {
    reason_code: "EXCLUDE_NO_TARGET_COMPUTATIONAL_QUALITATIVE_CONTRIBUTION",
    reason: `The title and abstract for ${topic} do not report a computational system performing, supporting, or directly evaluating qualitative coding, codebook development, or thematic interpretation.`,
  };
}

const assignments = [];
for (let index = 0; index < flow.title_abstract_screening.records.length; index += 1) {
  const screen = flow.title_abstract_screening.records[index];
  const source = union.records[index];
  const inScope = String(screen.year) === "2026" &&
    (screen.decision === "uncertain" || (screen.decision === "included" && !screen.full_text_report_key));
  if (!inScope) continue;
  const abstract = normalizeSpace(source.abstract || "");
  let decision;
  let reason_code;
  let reason;
  let anticipated_classification = "not applicable — excluded at title/abstract";
  if (advance.has(screen.screen_id)) {
    decision = "advance_to_full_text";
    anticipated_classification = advanceCore.has(screen.screen_id)
      ? "core candidate"
      : advanceAdjacent.has(screen.screen_id)
        ? "adjacent candidate"
        : "contextual/methodological candidate";
    reason_code = advanceCore.has(screen.screen_id)
      ? "POTENTIAL_CORE_COMPUTATIONAL_QUALITATIVE_ANALYSIS"
      : advanceAdjacent.has(screen.screen_id)
        ? "POTENTIAL_ADJACENT_VALIDITY_OR_STANDARD"
        : "POTENTIAL_CONTEXTUAL_METHOD_OR_SYSTEM";
    reason = positiveEvidence(screen.title, abstract);
  } else {
    decision = "exclude_title_abstract";
    ({reason_code, reason} = exclusion(screen, abstract));
  }
  assignments.push({
    screen_id: screen.screen_id,
    source: screen.source,
    sources: screen.sources,
    source_id: screen.source_id,
    title: screen.title,
    year: screen.year,
    doi: screen.doi,
    url: screen.url,
    original_triage_decision: screen.decision,
    original_reason_code: screen.reason_code,
    abstract_available: Boolean(abstract),
    abstract: abstract || "not available in search_union_deduplicated.json",
    title_abstract_decision: decision,
    anticipated_classification,
    reason_code,
    reason,
    reviewer_basis: "single-reviewer/Codex-assisted title/abstract assessment",
  });
}

const outcomesPath = path.join(RESEARCH, "screening_2026_fulltext_outcomes.json");
const outcomeFile = fs.existsSync(outcomesPath)
  ? JSON.parse(fs.readFileSync(outcomesPath, "utf8"))
  : {outcomes: []};
const outcomes = new Map((outcomeFile.outcomes || []).map(row => [row.screen_id, row]));
const fullTextCandidates = assignments
  .filter(row => row.title_abstract_decision === "advance_to_full_text")
  .map(row => ({
    screen_id: row.screen_id,
    title: row.title,
    doi: row.doi,
    url: row.url,
    anticipated_classification: row.anticipated_classification,
    ...(outcomes.get(row.screen_id) || {
      retrieval_status: "pending",
      full_text_decision: "pending",
      retrieval_notes: "Full-text retrieval not yet attempted in this generated snapshot.",
    }),
  }));

// This is a supplemental citation-chain stratum, not part of the 271-record
// database-screen denominator.  Exact DOI and normalized-title checks make the
// derivation reproducible and prevent the forward-chain side list from being
// silently mixed into the search-union count.
const unionDois = new Set(union.records.map(row => normalizeDoi(row.doi)).filter(Boolean));
const unionTitles = new Set(union.records.map(row => normalizeTitle(row.title)).filter(Boolean));
const supplementalForward = chaining.forward_result_screening.new_focused_scope_title_candidates
  .filter(row => String(row.year) === "2026")
  .filter(row => !unionDois.has(normalizeDoi(row.doi)) && !unionTitles.has(normalizeTitle(row.title)))
  .map((row, index) => {
    const screenId = `FC-${String(index + 1).padStart(2, "0")}`;
    return {
      screen_id: screenId,
      stratum: "supplemental forward citation chain outside the deduplicated search union",
      direction: "forward",
      title: row.title,
      year: row.year,
      doi: row.doi || "not reported",
      arxiv: row.arxiv || "not reported",
      url: row.url,
      deduplication_key: row.deduplication_key,
      parent_seed_ids: row.parent_seed_ids,
      sources: row.sources,
      title_screening_basis: "Focused-scope title candidate identified by citation chaining; deduplicated against the database union by exact normalized DOI and title.",
      ...(outcomes.get(screenId) || {
        retrieval_status: "pending",
        full_text_decision: "pending",
        retrieval_notes: "Full-text retrieval not yet attempted in this generated snapshot.",
      }),
    };
  });

const countBy = (rows, key) => Object.fromEntries(
  [...rows.reduce((map, row) => map.set(row[key], (map.get(row[key]) || 0) + 1), new Map())]
    .sort(([a], [b]) => String(a).localeCompare(String(b))),
);

const output = {
  metadata: {
    title: "Complete second-pass title/abstract resolution for unresolved 2026 records",
    review_cutoff: CUTOFF,
    generated_on: CUTOFF,
    source_flow: "research/review_flow.json",
    source_records: "research/search_union_deduplicated.json",
    scope: "Every 2026-dated record labeled uncertain, plus every 2026 included/high-priority record not linked to an assessed full text, in the source flow used for this pass.",
    reviewer_model: "Single-reviewer/Codex-assisted; no independent duplicate screening or adjudication.",
    decision_rule: "Advance when the title/abstract reports or plausibly reports computational support for qualitative coding/thematic interpretation, a directly applicable code/theme evaluation or validity contribution, or a directly relevant methodological/system contribution. Exclude only when title/abstract evidence identifies an out-of-scope task or makes qualitative analysis solely the researchers' method for studying AI.",
    no_abstract_rule: "A missing abstract was not silently treated as exclusion. Directly relevant titles advanced to retrieval; clearly unrelated or noncomputational titles were excluded with the title-only basis stated.",
    methodological_claim_rule: "No methodological or numerical claim is extracted from an abstract; master-ready evidence is permitted only after full-text inspection.",
    master_merge_status: "No candidate from this second pass has been merged into master_evidence.json by this workflow.",
    assigned_record_count: assignments.length,
    counts_by_title_abstract_decision: countBy(assignments, "title_abstract_decision"),
    counts_by_original_triage_decision: countBy(assignments, "original_triage_decision"),
    counts_by_reason_code: countBy(assignments, "reason_code"),
    advance_count: fullTextCandidates.length,
    database_full_text_candidate_count: fullTextCandidates.length,
    supplemental_forward_chain_candidate_count: supplementalForward.length,
    combined_full_text_candidate_count: fullTextCandidates.length + supplementalForward.length,
    abstract_available_count: assignments.filter(row => row.abstract_available).length,
    abstract_unavailable_count: assignments.filter(row => !row.abstract_available).length,
  },
  assignments,
  full_text_candidates: fullTextCandidates,
  supplemental_forward_chain_candidates: supplementalForward,
  combined_full_text_candidates: [...fullTextCandidates, ...supplementalForward],
  nonretrieval_log: [...fullTextCandidates, ...supplementalForward]
    .filter(row => row.retrieval_status === "not_retrieved"),
  master_ready_extractions: [...fullTextCandidates, ...supplementalForward]
    .filter(row => row.retrieval_status === "retrieved_and_inspected" && row.master_ready_extraction)
    .map(row => row.master_ready_extraction),
};

if (assignments.length !== 271) throw new Error(`Expected 271 scoped records, found ${assignments.length}`);
if (supplementalForward.length !== 16) throw new Error(`Expected 16 supplemental 2026 forward-chain candidates, found ${supplementalForward.length}`);
if (new Set(assignments.map(row => row.screen_id)).size !== assignments.length) throw new Error("Duplicate screen IDs in 2026 resolution");
if (assignments.some(row => !row.reason || !row.reason_code || !row.title_abstract_decision)) throw new Error("Incomplete decision record");

fs.writeFileSync(path.join(RESEARCH, "screening_2026_resolution.json"), `${JSON.stringify(output, null, 2)}\n`);
console.log(JSON.stringify(output.metadata, null, 2));
