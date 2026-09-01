import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const RESEARCH = path.join(ROOT, "research");
const CUTOFF = "2026-08-24";

const read = (name) => JSON.parse(fs.readFileSync(path.join(RESEARCH, name), "utf8"));
const master = read("master_evidence.json");
const priorResolution = read("screening_2026_resolution.json");
const flow = read("review_flow.json");
const union = read("search_union_deduplicated.json");

const columns = master.metadata.extraction_columns;
const dimensions = master.metadata.quality_dimensions || master.quality_dimensions;
if (!Array.isArray(columns) || columns.length !== 52) throw new Error("Master extraction schema is not 52 fields");
if (!Array.isArray(dimensions) || dimensions.length !== 12) throw new Error("Master quality schema is not 12 dimensions");

const batchFiles = fs.readdirSync(path.join(RESEARCH, "screening_2026_batches"))
  .filter((name) => /^batch_\d+\.json$/.test(name))
  .sort();
const batchRows = batchFiles.flatMap((name) => {
  const parsed = read(path.join("screening_2026_batches", name));
  return parsed.records.map((row) => ({...row, checkpoint_file: `research/screening_2026_batches/${name}`}));
});

const duplicateBatchIds = [...batchRows.reduce((map, row) => map.set(row.screen_id, (map.get(row.screen_id) || 0) + 1), new Map())]
  .filter(([, count]) => count !== 1);
if (duplicateBatchIds.length) throw new Error(`Duplicate checkpoint IDs: ${JSON.stringify(duplicateBatchIds)}`);
const outcomeById = new Map(batchRows.map((row) => [row.screen_id, row]));

const unionByScreenId = new Map(flow.title_abstract_screening.records.map((row, index) => [row.screen_id, union.records[index]]));
const supplementalById = new Map(priorResolution.supplemental_forward_chain_candidates.map((row) => [row.screen_id, row]));

const standaloneHandoffMetadata = {
  "FC-17": {
    title: "LLMs and Coding in Qualitative Research: Advancements and Opportunities for Social Verbatim as an Integral Qualitative Tool",
    authors: ["Juan Miguel Gómez Espino"],
    year: 2026,
    venue: "Revista CENTRA de Ciencias Sociales, 5(1), Debate section",
    doi: "10.54790/rccs.176",
    url: "https://doi.org/10.54790/rccs.176",
  },
};

const supplementalOverrides = {
  "FC-03": {
    authors: ["Runlong Ye", "Oliver Huang", "Patrick Yung Kang Lee", "Michael Liut", "Carolina Nobre", "Ha-Kyung Kong"],
    venue: "Proceedings of the 2026 CHI Conference on Human Factors in Computing Systems (CHI '26)",
  },
  "FC-06": {
    authors: ["Songhee Han", "Jueun Shin", "Jiyoon Han", "Bung-Woo Jun", "Hilal Ayan Karabatman"],
    venue: "arXiv",
  },
  "FC-07": {
    authors: ["Neil A. Ernst", "Christoph Treude"],
    venue: "arXiv; submitted ACM manuscript",
  },
  "FC-11": {
    authors: ["Jesus A. Beltran", "Hanna Mofid", "Harita Parikh", "Jaydeep Gondaliya", "Diego Guzman", "Jenil Shah", "Lizbeth Escobedo", "Franceli Cibrian"],
    venue: "Communications in Computer and Information Science 2725 / SEET proceedings",
  },
  "TA-0351": {
    authors: ["Tim Fischer", "Chris Biemann"],
    venue: "Proceedings of the 6th International Conference on Natural Language Processing for the Digital Humanities (NLP4DH 2026)",
  },
  "TA-0151": {
    venue: "Proceedings of the 16th International Learning Analytics and Knowledge Conference (LAK 2026)",
  },
  "TA-0338": {
    venue: "Proceedings of the 2026 CHI Conference on Human Factors in Computing Systems (CHI '26)",
  },
  "TA-0955": {
    venue: "ACM Transactions on Computer-Human Interaction, 33(1), Article 111",
  },
  "TA-1327": {
    authors: ["Samantha Sudhoff", "Pranav Perumal", "Zhaoqing Wu", "Tunazzina Islam"],
    venue: "arXiv; ACL ARR May 2026 submission",
  },
};

function clean(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function normalizeDoi(value) {
  const normalized = clean(value).toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//, "");
  return /^10\.\d{4,9}\//.test(normalized) ? normalized.replace(/[.\s]+$/, "") : "";
}

function normalizeTitle(value) {
  return clean(value).toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, " ").trim();
}

function unwrapField(field) {
  if (field && typeof field === "object" && !Array.isArray(field)) return clean(field.value);
  return clean(field);
}

function fieldAnchor(field) {
  if (field && typeof field === "object" && !Array.isArray(field)) return clean(field.anchor) || "full text";
  return "full text";
}

function getField(row, key) {
  if (row.fields?.[key]) return unwrapField(row.fields[key]);
  if (key === "Fine-tuning or adaptation" && row.fields?.["Fine-tuning or retrieval augmentation"]) {
    return unwrapField(row.fields["Fine-tuning or retrieval augmentation"]);
  }
  return "";
}

function getAnchor(row, key) {
  if (row.fields?.[key]) return fieldAnchor(row.fields[key]);
  if (key === "Fine-tuning or adaptation" && row.fields?.["Fine-tuning or retrieval augmentation"]) {
    return fieldAnchor(row.fields["Fine-tuning or retrieval augmentation"]);
  }
  return "";
}

function statusSaysNotPeerReviewed(status) {
  const text = clean(status).toLowerCase();
  return /\bnot (?:a )?peer[- ]reviewed\b|\bno peer[- ]reviewed\b|\bnot certified by peer review\b|\bpeer review (?:was |is )?not established\b|\bacceptance(?:\/peer review)?[^.;]{0,100}\bnot (?:established|treated as established)\b|\bunder review\b/.test(text);
}

function metadataFor(screenId) {
  const unionRow = unionByScreenId.get(screenId);
  if (unionRow) return {...unionRow, ...(supplementalOverrides[screenId] || {}), year: unionRow.year || 2026};
  const supplemental = supplementalById.get(screenId);
  if (supplemental) return {...supplemental, ...(supplementalOverrides[screenId] || {}), year: supplemental.year || 2026};
  const handoff = standaloneHandoffMetadata[screenId];
  if (handoff) return {...handoff, ...(supplementalOverrides[screenId] || {})};
  throw new Error(`No bibliographic source record for included ${screenId}`);
}

function inferPublicationType(status, decision, fields) {
  const supplied = unwrapField(fields?.["Publication type"]);
  if (supplied) return supplied;
  const text = clean(status).toLowerCase();
  if (/software package|cran software|documentation/.test(text)) return "software/package documentation";
  if (/preprint|arxiv|osf|psyarxiv|medrxiv|research square/.test(text) && statusSaysNotPeerReviewed(text)) return "preprint";
  if (/protocol/.test(text)) return "peer-reviewed research protocol";
  if (/conference|proceedings|chapter|hicss|chi 2026|lak 2026/.test(text)) return "conference/proceedings paper";
  if (/journal|article|scientific reports|plos|jmir|dementia|healthcare|risk analysis/.test(text)) return "journal article";
  if (decision === "include_contextual") return "methodological or contextual contribution";
  return "not reported";
}

function inferPeerReview(status, fields) {
  const supplied = unwrapField(fields?.["Peer-reviewed status"]);
  if (supplied) return supplied;
  const text = clean(status).toLowerCase();
  if (/software package|cran software/.test(text)) return "not peer reviewed as a research study";
  if (statusSaysNotPeerReviewed(text)) return "not peer reviewed or peer review not established as of 2026-08-24";
  if (/accepted\/presented|accepted conference/.test(text)) return "accepted conference paper; inspected author manuscript";
  if (/peer-reviewed/.test(text)) return "peer reviewed";
  return "not reported";
}

function surnameFromAuthors(authors) {
  const first = clean(authors?.[0] || "unknown");
  if (!first) return "unknown";
  if (first.includes(",")) return first.split(",")[0].replace(/[^A-Za-z0-9]+/g, "").toLowerCase() || "unknown";
  const tokens = first.split(/\s+/);
  return (tokens.at(-1) || "unknown").replace(/[^A-Za-z0-9]+/g, "").toLowerCase() || "unknown";
}

function paperId(screenId, authors) {
  return `${screenId.toLowerCase().replace(/-/g, "_")}_2026_${surnameFromAuthors(authors)}`;
}

function classificationFor(decision) {
  return decision.startsWith("include_core") ? "core" : "adjacent";
}

const includedRows = batchRows.filter((row) => row.full_text_decision.startsWith("include"));
const evidenceLocations = [];
const evidenceRecords = includedRows.map((row) => {
  const meta = metadataFor(row.screen_id);
  const suppliedAuthors = getField(row, "Authors");
  const authorsArray = suppliedAuthors
    ? suppliedAuthors.split(/\s*;\s*/).filter(Boolean)
    : Array.isArray(meta.authors)
      ? meta.authors.map(clean).filter(Boolean)
      : supplementalOverrides[row.screen_id]?.authors || [];
  const authors = suppliedAuthors || (authorsArray.length ? authorsArray.join("; ") : "not reported");
  const title = getField(row, "Title") || clean(meta.title) || "not reported";
  const suppliedUrl = getField(row, "URL") || clean(row.official_full_text_url) || clean(meta.url) || "not reported";
  const doi = normalizeDoi(getField(row, "DOI")) || normalizeDoi(meta.doi) || normalizeDoi(suppliedUrl) || "not reported";
  const officialUrl = /^https?:\/\/(?:www\.)?arxiv\.org\/(?:abs|pdf)\//i.test(suppliedUrl)
    ? suppliedUrl
    : doi !== "not reported"
      ? `https://doi.org/${doi}`
      : suppliedUrl;
  const status = clean(row.publication_status_as_of_cutoff) || "not reported";
  const venue = getField(row, "Venue") || clean(meta.venue) || supplementalOverrides[row.screen_id]?.venue || (
    /arxiv\.org/i.test(officialUrl) ? "arXiv" :
      /research square/i.test(status) ? "Research Square" :
        /osf|psyarxiv/i.test(status) ? "OSF/PsyArXiv" :
          /medrxiv/i.test(status) ? "medRxiv" : "not reported"
  );
  const id = paperId(row.screen_id, authorsArray);
  const classification = classificationFor(row.full_text_decision);
  const year = row.screen_id === "FC-15" ? "2026 conference status; 2027 proceedings citation" : "2026";
  const generatedCitation = `${authors}. (${year}). ${title}. ${venue}. ${officialUrl}`;
  const derived = {
    "Paper ID": id,
    "Full citation": getField(row, "Full citation") || generatedCitation,
    "Title": title,
    "Authors": authors,
    "Year": year,
    "Venue": venue,
    "Publication type": inferPublicationType(status, row.full_text_decision, row.fields),
    "Peer-reviewed status": inferPeerReview(status, row.fields),
    "Publication history notes": getField(row, "Publication history notes") || status,
    "URL": officialUrl,
    "DOI": doi,
    "Citation count, source, and retrieval date": getField(row, "Citation count, source, and retrieval date") || clean(row.bibliographic_identity?.citation_count) || "not reported",
    "Core or adjacent classification": classification,
    "Relationship/dependence family": getField(row, "Relationship/dependence family") || clean(row.relationship_flag) || "not reported",
  };
  const record = {};
  const locations = {};
  for (const column of columns) {
    const fieldValue = getField(row, column);
    record[column] = fieldValue || derived[column] || "not reported";
    locations[column] = getAnchor(row, column) || (
      column === "Paper ID" || column === "Core or adjacent classification"
        ? "reviewer extraction/classification record"
        : column in derived
          ? `official full-text title page/DOI record and ${row.checkpoint_file}`
          : "not reported in inspected full text"
    );
  }
  evidenceLocations.push({
    "Paper ID": id,
    screen_id: row.screen_id,
    retrieval_status: row.retrieval_status,
    inspected_full_text: row.local_text || row.official_full_text_url,
    checkpoint_file: row.checkpoint_file,
    field_locations: locations,
  });
  return record;
});

const evidenceByScreenId = new Map(evidenceRecords.map((record, index) => [includedRows[index].screen_id, record]));

function isMissing(value) {
  const text = clean(value).toLowerCase();
  return !text || text === "none" || text === "not reported" || text === "not applicable" || text === "not applicable/not reported" ||
    /^no (?:new |formal |current |empirical |human |automatic |model |system |direct |independent )?.*(?:reported|evaluation|baseline|metric|analysis|study|data)/.test(text);
}

function excerpt(value, length = 220) {
  const text = clean(value);
  if (!text) return "not reported";
  return text.length <= length ? text : `${text.slice(0, length - 1).trim()}…`;
}

const scoreOverrides = {
  "FC-01": [2, 2, 1, 1, 2, 1, 1, 1, 0, 1, 1, 2],
  "FC-03": [2, 2, 2, 0, 2, 1, 2, 2, 0, 2, 1, 2],
  "FC-05": [2, 2, 1, 1, 2, 1, 0, 1, 0, 2, 1, 2],
  "FC-11": [1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1],
  "FC-15": [1, 2, 1, 2, 1, 2, 0, 1, 1, 1, 1, 2],
};

function evidenceVector(record) {
  const claimed = record["Claimed qualitative methodology"];
  const actual = record["Actual operationalized methodology"];
  const dataset = `${record["Dataset name"]} ${record["Number of documents"]} ${record["Number of participants"]} ${record["Approximate corpus size"]}`;
  const workflowParts = [record["Exact model/version"], record["Prompting strategy"], record["Unit of analysis"], record["Generated outputs"]];
  const baseline = record.Baselines;
  const human = `${record["Human-evaluation design"]} ${record["Number and expertise of evaluators"]}`;
  const metrics = record["Automatic metrics"];
  const pluralityText = `${claimed} ${actual} ${record["Human role"]} ${record["Principal results"]} ${record["Additional validity concerns"]}`.toLowerCase();
  const provenance = record["Evidence/provenance mechanism"];
  const runs = record["Number of runs or seeds"];
  const ethics = record["Ethics and privacy treatment"];
  const resources = `${record["Reproducibility resources"]} ${record["Exact model/version"]}`;
  const limits = `${record["Author-reported limitations"]} ${record["Additional validity concerns"]}`;

  const clarity = !isMissing(claimed) && !isMissing(actual) && clean(actual).length >= 90 ? 2 : (!isMissing(claimed) || !isMissing(actual) ? 1 : 0);
  const datasetScore = /\b\d[\d,]*(?:\s|$)|interview|document|transcript|message|comment|article|participant/i.test(dataset) && !/no (?:fixed|substantive|evaluation) dataset/i.test(dataset)
    ? 2
    : (!isMissing(record["Dataset name"]) ? 1 : 0);
  const transparentCount = workflowParts.filter((value) => !isMissing(value)).length;
  const workflow = transparentCount === 4 && !/not reported|unspecified|incompletely reported|incomplete/i.test(workflowParts.join(" ")) ? 2 : transparentCount >= 2 ? 1 : 0;
  const baselineEvidence = `${baseline} ${limits}`.toLowerCase();
  const weakBaseline = /no (?:formal )?(?:independent |human(?:-only)? |task-matched )?(?:analysis |thematic-analysis )?baseline|no independent|same[- ](?:coders?|researchers?)|not task-matched|(?:one|single) (?:human|expert|coder|analyst|rater)\b|(?:experienced )?human coder as the primary|ai involvement[^.;]{0,90}(?:reference|theme|codebook)|one run per model/.test(baselineEvidence);
  const baselines = isMissing(baseline) || /^(none|not applicable)/i.test(clean(baseline))
    ? 0
    : /independent|held-out|human|manual|expert|randomized|counterbalanced|gold|reference labels/i.test(baseline) && !weakBaseline
      ? 2
      : 1;
  const humanEvidence = `${human} ${limits}`.toLowerCase();
  const weakHumanEvaluation = /unspecified (?:subset|sample)|not fully (?:enumerated|characterized|reported)|not enumerated|single[- ]rater|single expert|one expert|one human|one evaluator|one rater|same[- ]coders?|unblinded|no independent|not independent|appears to rely|evaluator (?:count|expertise)[^.;]{0,60}not/.test(humanEvidence);
  const humanEval = isMissing(record["Human-evaluation design"]) || /^(none|not applicable)/i.test(clean(record["Human-evaluation design"]))
    ? 0
    : !isMissing(record["Number and expertise of evaluators"]) && !/not reported/i.test(record["Number and expertise of evaluators"]) && /independent|blind|expert|trained|participant|pair|multiple|two |three |\bn\s*=|\b\d+\b/i.test(human) && !weakHumanEvaluation
      ? 2
      : 1;
  const metricScore = isMissing(metrics) || /^(none|not applicable)/i.test(clean(metrics))
    ? 0
    : /confidence interval|bootstrap|icc|correlation|recall|coverage|precision|sensitivity|specificity|auc|kappa|alpha|f1/i.test(metrics) && !/agreement.*not quality|proxy|not.*valid|embedding similarity.*not|llm.*judge/i.test(limits)
      ? 2
      : 1;
  const pluralityHits = (pluralityText.match(/reflexiv|plural|alternative|disagreement|positional|participant validation|member check|negative case|minority|divergen|co-research|lived experience/g) || []).length;
  const plurality = pluralityHits >= 2 ? 2 : pluralityHits === 1 || /consensus|multiple coder|two coder|human review/.test(pluralityText) ? 1 : 0;
  const grounding = isMissing(provenance) || /no (?:systematic )?(?:source|provenance|trace)|not reported/i.test(provenance)
    ? 0
    : /source|quote|excerpt|identifier|\bid\b|link|trace|raw text|transcript context|document-level/i.test(provenance) && !/incomplete|selected|partial|but no|does not provide|can lose|no model|not reported/i.test(provenance)
      ? 2
      : 1;
  const runEvidence = clean(runs).toLowerCase();
  const countedRepetition = /(?:\b[2-9]|\b\d{2,}|\b(?:two|three|four|five|six|seven|eight|nine|ten))\s+(?:complete |independent |random )?(?:runs|seeds|repetitions|repeats)|repeated \d+ times|run \b(?:two|three|four|five|six|seven|eight|nine|ten)\b times|across \d+ runs/.test(runEvidence);
  const genericRepetition = /stochastic repetitions used|multiple (?:runs|seeds)|run-to-run (?:comparison|analysis)/.test(runEvidence) && !/not reported|not tested|no [^.;]{0,80}(?:run-to-run|stochastic repetitions|multiple runs|multiple seeds)/.test(runEvidence);
  const actualPerturbation = /context[- ]window pilot|threshold sweep|\bablation\b|bootstrap resamples|prompt (?:iterations?|conditions?|development)|robustness (?:check|analysis|comparison)|sensitivity (?:check|analysis)|held-out|train(?:ing)?\/?test split|anchor(?:ing)?|activation steer|optuna trials|\b\d+ iterations?\b/.test(runEvidence) && !/not model stability/.test(runEvidence);
  const missingRepeatDetails = /seeds? (?:not reported|unreported)|no seed value|exact run count (?:is )?not/.test(runEvidence);
  const stability = isMissing(runs) || /^not reported\b/.test(runEvidence)
    ? 0
    : countedRepetition
      ? (missingRepeatDetails ? 1 : 2)
      : genericRepetition || actualPerturbation ? 1 : 0;
  const ethicsScore = isMissing(ethics) || /no (?:irb|ethics|privacy|governance)|not reported/i.test(ethics)
    ? 0
    : /irb|ethics (?:board|committee)|consent/.test(ethics.toLowerCase()) && /privacy|de-?ident|anonym|secure|local|restricted|governance/.test(ethics.toLowerCase()) && !/not reported|no .*reported/i.test(ethics)
      ? 2
      : 1;
  const resourceEvidence = clean(resources).toLowerCase();
  const resourceTypes = [
    /github|repository|\bcode\b/.test(resourceEvidence),
    /\bdata(?:set)?\b/.test(resourceEvidence),
    /\bprompts?\b/.test(resourceEvidence),
    /appendix|supplement|protocol|container|package/.test(resourceEvidence),
  ].filter(Boolean).length;
  const resourceWeakness = /incomplete|no (?:code|data|prompt|repository|resources|materials)|not (?:fully )?reported|unavailable|request-only|not released|restricted|requires? repository audit|repository audit required|proprietary[^.;]{0,60}opaque/.test(resourceEvidence);
  const exactVersionAvailable = !isMissing(record["Exact model/version"]) && !/unspecified|not reported|exact [^.;]{0,40}not/.test(record["Exact model/version"].toLowerCase());
  const availability = isMissing(record["Reproducibility resources"]) || /^(?:not reported|none|no (?:code|data|repository|resources|materials)(?: (?:are|were))? (?:available|reported|released))\b/i.test(clean(record["Reproducibility resources"]))
    ? 0
    : resourceTypes >= 2 && exactVersionAvailable && !resourceWeakness
      ? 2
      : 1;
  const proportionate = isMissing(record["Author-reported limitations"])
    ? 1
    : /severe|fabricat|fundamental invalid|unsupported headline/i.test(limits)
      ? 0
      : /overclaim|over-claim|contradict|inconsisten|not establish|confound|not task-matched|not reported|no .*reported/i.test(limits)
        ? 1
        : 2;
  return [clarity, datasetScore, workflow, baselines, humanEval, metricScore, plurality, grounding, stability, ethicsScore, availability, proportionate];
}

function rationaleFor(index, score, record) {
  const prefix = score === 2 ? "Adequate" : score === 1 ? "Partial" : "Absent/inadequate";
  const omitMissingClauses = (value) => clean(value).split(/(?<=[.;])\s+|\s*;\s*/).filter((part) => !/not reported|not applicable|no .*reported/i.test(part)).join("; ") || "available full-text evidence is limited";
  const templates = [
    () => score === 2
      ? `${prefix}: the full-text extraction distinguishes the claimed method (${excerpt(record["Claimed qualitative methodology"], 120)}) from the operational procedure (${excerpt(record["Actual operationalized methodology"], 180)}).`
      : `${prefix}: qualitative-method reporting is incomplete or methodologically incongruent; claimed=${excerpt(record["Claimed qualitative methodology"], 110)}; operationalized=${excerpt(record["Actual operationalized methodology"], 160)}.`,
    () => `${prefix}: dataset support for the stated claim comprises ${excerpt(omitMissingClauses(`${record["Dataset name"]}; ${record["Number of documents"]}; ${record["Number of participants"]}`), 230)}.`,
    () => `${prefix}: workflow reporting covers model=${excerpt(record["Exact model/version"], 100)}; prompting=${excerpt(record["Prompting strategy"], 115)}; unit=${excerpt(record["Unit of analysis"], 90)}.`,
    () => `${prefix}: the extracted comparator design is ${excerpt(record.Baselines, 230)}.`,
    () => score === 2
      ? `${prefix}: human evaluation is ${excerpt(omitMissingClauses(record["Human-evaluation design"]), 170)} Evaluators: ${excerpt(omitMissingClauses(record["Number and expertise of evaluators"]), 120)}.`
      : `${prefix}: human evaluation is ${excerpt(record["Human-evaluation design"], 175)} Evaluators: ${excerpt(record["Number and expertise of evaluators"], 115)}.`,
    () => `${prefix}: reported automatic evidence is ${excerpt(record["Automatic metrics"], 190)}; this score reflects whether those measures support the paper's qualitative-quality claim, not merely whether metrics are present.`,
    () => score === 2
      ? `${prefix}: the full-text method/human-role evidence explicitly preserves reflexivity, disagreement, positionality, alternative interpretations, or participant/domain-expert perspectives (${excerpt(omitMissingClauses(record["Human role"]), 210)}).`
      : `${prefix}: plurality/reflexivity was assessed from the human-role evidence (${excerpt(record["Human role"], 145)}) and explicit validity concerns (${excerpt(record["Additional validity concerns"], 145)}).`,
    () => `${prefix}: source grounding/provenance is ${excerpt(record["Evidence/provenance mechanism"], 235)}.`,
    () => `${prefix}: stability evidence is ${excerpt(record["Number of runs or seeds"], 235)}.`,
    () => `${prefix}: responsible-research reporting is ${excerpt(record["Ethics and privacy treatment"], 235)}.`,
    () => `${prefix}: reproducibility assets/version reporting are ${excerpt(record["Reproducibility resources"], 235)}.`,
    () => score === 2
      ? `${prefix}: conclusions are bounded by the authors' substantive limitations (${excerpt(omitMissingClauses(record["Author-reported limitations"]), 225)}).`
      : `${prefix}: conclusion proportionality was judged against author limitations (${excerpt(record["Author-reported limitations"], 140)}) and reviewer validity concerns (${excerpt(record["Additional validity concerns"], 140)}).`,
  ];
  return templates[index]();
}

const coreRows = includedRows.filter((row) => classificationFor(row.full_text_decision) === "core");
const qualityScores = coreRows.map((row) => {
  const record = evidenceByScreenId.get(row.screen_id);
  const vector = scoreOverrides[row.screen_id] || evidenceVector(record);
  if (vector.length !== 12 || vector.some((score) => ![0, 1, 2].includes(score))) throw new Error(`Invalid score vector for ${row.screen_id}`);
  const dimensionScores = Object.fromEntries(dimensions.map((dimension, index) => [dimension, {
    score: vector[index],
    rationale: rationaleFor(index, vector[index], record),
  }]));
  return {
    "Paper ID": record["Paper ID"],
    Title: record.Title,
    "Core or adjacent classification": "core",
    "Dimension scores": dimensionScores,
    Total: vector.reduce((sum, value) => sum + value, 0),
    "Interpretation caution": "The total is a compact audit aid, not a ranking of study quality; interpret every dimension against the paper's stated claim and the full-text extraction.",
  };
});

function terminalDecision(raw) {
  if (!raw) return "pending";
  if (raw.startsWith("include_core")) return "include_core_after_full_text";
  if (raw === "include_adjacent" || raw === "include_contextual") return "include_adjacent_after_full_text";
  if (raw === "duplicate_already_assessed") return "existing_master_or_assessed_version_family";
  if (raw === "duplicate_family" || raw.startsWith("duplicate_version_family")) return "duplicate_version_family";
  if (raw.startsWith("exclude")) return "exclude_after_full_text";
  if (raw.includes("unresolved") || raw.includes("retrieval_constraint")) return "not_retrieved_after_attempts";
  return raw;
}

function compactOutcome(row) {
  if (!row) return null;
  return {
    retrieval_status: row.retrieval_status,
    official_full_text_url: row.official_full_text_url,
    local_full_text_path: row.local_text || "not reported",
    publication_status_as_of_cutoff: row.publication_status_as_of_cutoff,
    full_text_decision: row.full_text_decision,
    terminal_decision: terminalDecision(row.full_text_decision),
    decision_reason: row.decision_reason,
    retrieval_attempts: row.retrieval_attempts || [],
    checkpoint_file: row.checkpoint_file,
  };
}

const qualityByPaperId = new Map(qualityScores.map((row) => [row["Paper ID"], row]));
const databaseResolution = priorResolution.assignments.map((assignment) => {
  const outcome = assignment.title_abstract_decision === "advance_to_full_text" ? outcomeById.get(assignment.screen_id) : null;
  if (assignment.title_abstract_decision === "advance_to_full_text" && !outcome) throw new Error(`Missing full-text outcome for ${assignment.screen_id}`);
  const evidence = evidenceByScreenId.get(assignment.screen_id) || null;
  return {
    ...assignment,
    second_pass_decision: assignment.title_abstract_decision === "exclude_title_abstract"
      ? "exclude_title_abstract"
      : terminalDecision(outcome.full_text_decision),
    evidence_basis: assignment.title_abstract_decision === "exclude_title_abstract"
      ? "actual title and union abstract (or explicit title-only basis where abstract unavailable)"
      : "inspected full text or documented nonretrieval; no methodological extraction from abstracts",
    full_text_outcome: compactOutcome(outcome),
    master_inclusion_status: evidence ? "master-ready companion record; not merged into master" : "not added to master",
    master_ready_record: evidence,
    quality_score: evidence?.["Core or adjacent classification"] === "core" ? qualityByPaperId.get(evidence["Paper ID"]) : null,
  };
});

const forwardResolution = priorResolution.supplemental_forward_chain_candidates.map((candidate) => {
  const outcome = outcomeById.get(candidate.screen_id);
  if (!outcome) throw new Error(`Missing forward-chain outcome for ${candidate.screen_id}`);
  const evidence = evidenceByScreenId.get(candidate.screen_id) || null;
  return {
    ...candidate,
    second_pass_decision: terminalDecision(outcome.full_text_decision),
    full_text_outcome: compactOutcome(outcome),
    retrieval_provenance: {
      direction: candidate.direction,
      parent_seed_ids: candidate.parent_seed_ids,
      sources: candidate.sources,
    },
    master_inclusion_status: evidence ? "master-ready companion record; not merged into master" : "not added to master",
    master_ready_record: evidence,
    quality_score: evidence?.["Core or adjacent classification"] === "core" ? qualityByPaperId.get(evidence["Paper ID"]) : null,
  };
});

const crossStreamIds = ["TA-0955", "TA-1299", "TA-1307", "TA-1327", "TA-1285", "FC-17"];
const crossStreamResolution = crossStreamIds.map((screenId) => {
  const outcome = outcomeById.get(screenId);
  if (!outcome) throw new Error(`Missing cross-stream handoff outcome for ${screenId}`);
  const source = metadataFor(screenId);
  const evidence = evidenceByScreenId.get(screenId) || null;
  return {
    screen_id: screenId,
    title: source?.title || "not reported",
    doi: source?.doi || "not reported",
    source_handoff: "2020-2024/undated screening stream; publication/version or forward-only identity resolved in this 2026 full-text pass",
    second_pass_decision: terminalDecision(outcome.full_text_decision),
    full_text_outcome: compactOutcome(outcome),
    master_inclusion_status: evidence ? "master-ready companion record; not merged into master" : "not added to master",
    master_ready_record: evidence,
    quality_score: evidence?.["Core or adjacent classification"] === "core" ? qualityByPaperId.get(evidence["Paper ID"]) : null,
  };
});

const countBy = (rows, fn) => Object.fromEntries([...rows.reduce((map, row) => {
  const key = fn(row);
  map.set(key, (map.get(key) || 0) + 1);
  return map;
}, new Map())].sort(([a], [b]) => String(a).localeCompare(String(b))));

const allRetrievalRows = [
  ...databaseResolution.filter((row) => row.full_text_outcome).map((row) => ({screen_id: row.screen_id, stratum: "database union", ...row.full_text_outcome})),
  ...forwardResolution.map((row) => ({screen_id: row.screen_id, stratum: "supplemental forward chain", parent_seed_ids: row.parent_seed_ids, direction: row.direction, sources: row.sources, ...row.full_text_outcome})),
  ...crossStreamResolution.map((row) => ({screen_id: row.screen_id, stratum: "cross-stream handoff", ...row.full_text_outcome})),
];
const nonretrievalLog = allRetrievalRows.filter((row) => row.terminal_decision === "not_retrieved_after_attempts");

const counts = {
  assigned_database_records: databaseResolution.length,
  database_title_abstract_decisions: countBy(databaseResolution, (row) => row.title_abstract_decision),
  database_second_pass_decisions: countBy(databaseResolution, (row) => row.second_pass_decision),
  database_full_text_candidates: databaseResolution.filter((row) => row.full_text_outcome).length,
  database_full_text_terminalized: databaseResolution.filter((row) => row.full_text_outcome && row.second_pass_decision !== "pending").length,
  supplemental_forward_records: forwardResolution.length,
  supplemental_forward_decisions: countBy(forwardResolution, (row) => row.second_pass_decision),
  cross_stream_handoffs: crossStreamResolution.length,
  cross_stream_decisions: countBy(crossStreamResolution, (row) => row.second_pass_decision),
  master_ready_evidence_records: evidenceRecords.length,
  master_ready_core_records: evidenceRecords.filter((row) => row["Core or adjacent classification"] === "core").length,
  master_ready_adjacent_records: evidenceRecords.filter((row) => row["Core or adjacent classification"] === "adjacent").length,
  quality_scores: qualityScores.length,
  nonretrievals: nonretrievalLog.length,
};

const shared = {
  metadata: {
    title: "Complete 2026 second-pass title/abstract and full-text resolution",
    review_cutoff: CUTOFF,
    generated_on: CUTOFF,
    reviewer_model: "Single-reviewer/Codex-assisted; no independent duplicate screening or adjudication.",
    scope: "Every 2026-dated uncertain record plus every included/high-priority 2026 record not previously linked to an assessed full text; all 16 deduplicated forward-chain-only 2026 candidates; and six explicit cross-stream 2026 publication/version or forward-only handoffs.",
    methodological_claim_rule: "Methodological, numerical, and quality claims in evidence records derive only from inspected full text. Abstracts were used only for title/abstract screening and retrieval prioritization.",
    full_text_rule: "Unretrieved records remain explicit nonretrievals and do not receive evidence or quality rows.",
    master_merge_status: "No evidence record in this companion was merged into master_evidence.json by this builder.",
    extraction_columns: columns,
    quality_dimensions: dimensions,
    quality_scoring: "0 = absent/inadequate, 1 = partial, 2 = adequate for the study's stated claim. Scores are evidence-gated reviewer judgments; totals are not study rankings.",
    checkpoint_files: batchFiles.map((name) => `research/screening_2026_batches/${name}`),
  },
  counts,
  assignments: databaseResolution,
  database_union_resolution: databaseResolution,
  full_text_candidates: databaseResolution.filter((row) => row.full_text_outcome),
  supplemental_forward_chain_candidates: forwardResolution,
  forward_chain_outside_union_resolution: forwardResolution,
  combined_full_text_candidates: [...databaseResolution.filter((row) => row.full_text_outcome), ...forwardResolution],
  cross_stream_handoffs: crossStreamResolution,
  nonretrieval_log: nonretrievalLog,
  evidence_records: evidenceRecords,
  evidence_locations: evidenceLocations,
  quality_scores: qualityScores,
  limitations: [
    "Single-reviewer/Codex-assisted screening and extraction were not independently duplicated.",
    "Publisher access restrictions produced explicit nonretrievals; no methodological claims were inferred from their abstracts.",
    "Some 2026 conference records have 2027 formal proceedings citation years; their electronic/conference status and formal citation year are kept distinct.",
    "Adjacent records include contextual/methodological items that directly inform validity, provenance, or governance but do not themselves constitute primary LLM-QDA evaluations.",
    "Quality scores are claim-relative diagnostics, not a ranking of papers or a substitute for reading the field-level rationales.",
  ],
};

// Invariants
if (databaseResolution.length !== 271) throw new Error(`Expected 271 database assignments, found ${databaseResolution.length}`);
if (databaseResolution.filter((row) => row.full_text_outcome).length !== 71) throw new Error("Expected 71 database full-text candidates");
if (forwardResolution.length !== 16) throw new Error("Expected 16 supplemental forward-chain candidates");
if (crossStreamResolution.length !== 6) throw new Error("Expected six cross-stream handoffs");
if (evidenceRecords.length !== 70) throw new Error(`Expected 70 evidence records after NITA family deduplication and Social Verbatim resolution, found ${evidenceRecords.length}`);
if (qualityScores.length !== 52) throw new Error(`Expected 52 core quality records after NITA family deduplication, found ${qualityScores.length}`);
if (evidenceRecords.some((record) => Object.keys(record).length !== 52 || columns.some((column) => !(column in record)))) throw new Error("52-field invariant failed");
if (evidenceLocations.length !== evidenceRecords.length || evidenceLocations.some((row) => Object.keys(row.field_locations).length !== 52)) throw new Error("Evidence-location invariant failed");
if (qualityScores.some((row) => Object.keys(row["Dimension scores"]).length !== 12 || dimensions.some((dimension) => !(dimension in row["Dimension scores"])))) throw new Error("12-dimension invariant failed");
if (qualityScores.some((row) => row.Total !== Object.values(row["Dimension scores"]).reduce((sum, item) => sum + item.score, 0))) throw new Error("Quality-total invariant failed");
if (new Set(evidenceRecords.map((row) => row["Paper ID"])).size !== evidenceRecords.length) throw new Error("Duplicate Paper ID");
const dois = evidenceRecords.map((row) => normalizeDoi(row.DOI)).filter(Boolean);
if (new Set(dois).size !== dois.length) throw new Error("Duplicate DOI among evidence records");
const titles = evidenceRecords.map((row) => normalizeTitle(row.Title)).filter(Boolean);
if (new Set(titles).size !== titles.length) throw new Error("Duplicate normalized title among evidence records");
const qualityIds = new Set(qualityScores.map((row) => row["Paper ID"]));
const coreIds = new Set(evidenceRecords.filter((row) => row["Core or adjacent classification"] === "core").map((row) => row["Paper ID"]));
if (qualityIds.size !== coreIds.size || [...coreIds].some((id) => !qualityIds.has(id))) throw new Error("Core-to-quality one-to-one invariant failed");
if (databaseResolution.some((row) => row.title_abstract_decision === "advance_to_full_text" && row.second_pass_decision === "pending")) throw new Error("Unterminalized database full text");
if (forwardResolution.some((row) => row.second_pass_decision === "pending")) throw new Error("Unterminalized forward candidate");

fs.writeFileSync(path.join(RESEARCH, "screening_2026_fulltext_outcomes.json"), `${JSON.stringify(shared, null, 2)}\n`);
fs.writeFileSync(path.join(RESEARCH, "screening_2026_resolution.json"), `${JSON.stringify(shared, null, 2)}\n`);
console.log(JSON.stringify(counts, null, 2));
