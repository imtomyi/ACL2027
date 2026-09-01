import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = "/Users/OODI/Downloads/ACL 2027";
const experimentRoot = path.join(projectRoot, "experiments/qualitative_coding_baselines");
const runDir = path.join(projectRoot, "Storage/synthetic-results/model-qualification/20260825_synthetic_qualification");
const outputDir = path.join(
  runDir,
  "outputs/01a03a7b-c05d-7cb1-b9b3-8579059b8966",
);
const previewDir = path.join(runDir, "workbook_previews");
const outputPath = path.join(outputDir, "qualitative_coding_model_comparison.xlsx");

const COLORS = {
  navy: "#183B56",
  teal: "#2A9D8F",
  blue: "#3A6EA5",
  paleBlue: "#EAF2F8",
  paleTeal: "#E8F5F2",
  amber: "#E9C46A",
  paleAmber: "#FFF5D6",
  coral: "#E76F51",
  paleCoral: "#FCE9E4",
  green: "#3A8D5D",
  paleGreen: "#E8F3EC",
  ink: "#24323D",
  muted: "#667784",
  line: "#D7E0E7",
  white: "#FFFFFF",
};

function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function rectangular(values) {
  const width = Math.max(...values.map((row) => row.length));
  return values.map((row) => [...row, ...Array(width - row.length).fill(null)]);
}

async function csvValues(relativePath) {
  const csvText = await fs.readFile(path.join(runDir, relativePath), "utf8");
  const imported = await Workbook.fromCSV(csvText, { sheetName: "Imported" });
  const used = imported.worksheets.getItem("Imported").getUsedRange(true);
  return rectangular(used.values);
}

function addTableSheet(workbook, name, values, tableName) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const rows = values.length;
  const cols = values[0].length;
  sheet.getRangeByIndexes(0, 0, rows, cols).values = values;
  const tableRange = `A1:${columnName(cols - 1)}${rows}`;
  const table = sheet.tables.add(tableRange, true, tableName);
  table.style = "TableStyleMedium2";
  table.showBandedColumns = false;
  table.showFilterButton = true;
  const header = sheet.getRangeByIndexes(0, 0, 1, cols);
  header.format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.navy },
  };
  header.format.rowHeight = 34;
  sheet.freezePanes.freezeRows(1);
  return { sheet, rows, cols };
}

function setColumnWidths(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidth = width;
  });
}

function styleTitle(sheet, range, fill = COLORS.navy) {
  range.format = {
    fill,
    font: { bold: true, color: COLORS.white, size: 16 },
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: fill },
  };
  range.format.rowHeight = 28;
}

function styleSection(sheet, range) {
  range.format = {
    fill: COLORS.paleBlue,
    font: { bold: true, color: COLORS.navy },
    borders: { preset: "outside", style: "thin", color: COLORS.line },
  };
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const selection = JSON.parse(
  await fs.readFile(path.join(runDir, "selection.json"), "utf8"),
);
const validation = JSON.parse(
  await fs.readFile(path.join(runDir, "validation_summary.json"), "utf8"),
);
const judgeValidation = JSON.parse(
  await fs.readFile(path.join(runDir, "judge_validation_summary.json"), "utf8"),
);

const workbook = Workbook.create();

// Create sheets first so all later formulas can safely reference them.
const readMe = workbook.worksheets.add("Read Me");
readMe.showGridLines = false;
const modelSummary = workbook.worksheets.add("Model Summary");
modelSummary.showGridLines = false;

const datasetStatusValues = await csvValues("dataset_status.csv");
const modelDatasetValues = await csvValues("model_dataset_summary.csv");
const objectiveValues = await csvValues("objective_metrics_long.csv");
const issueValues = await csvValues("validation_issues.csv");
const stabilityValues = await csvValues("stability_by_model_packet.csv");
const judgeScoreValues = await csvValues("judge_scores_long.csv");
const judgeSummaryValues = await csvValues("judge_model_summary.csv");
const humanReviewValues = await csvValues("human_pairwise_review_template.csv");
const sourcePacketValues = await csvValues("source_packets_flat.csv");
const blindOutputValues = await csvValues("blind_outputs_flat.csv");
const inventoryValues = await csvValues("run_inventory.csv");

const datasetStatus = addTableSheet(
  workbook,
  "Dataset Status",
  datasetStatusValues,
  "DatasetStatusTable",
);
const modelDataset = addTableSheet(
  workbook,
  "Model Dataset",
  modelDatasetValues,
  "ModelDatasetTable",
);
const objective = addTableSheet(
  workbook,
  "Objective Metrics",
  objectiveValues,
  "ObjectiveMetricsTable",
);
const validationIssues = addTableSheet(
  workbook,
  "Validation Issues",
  issueValues,
  "ValidationIssuesTable",
);
const stability = addTableSheet(
  workbook,
  "Stability",
  stabilityValues,
  "StabilityTable",
);
const judgeScores = addTableSheet(
  workbook,
  "Judge Scores",
  judgeScoreValues,
  "JudgeScoresTable",
);
const judgeSummary = addTableSheet(
  workbook,
  "Judge Summary",
  judgeSummaryValues,
  "JudgeSummaryTable",
);
const humanReview = addTableSheet(
  workbook,
  "Human Review",
  humanReviewValues,
  "HumanReviewTable",
);
const sourcePackets = addTableSheet(
  workbook,
  "Source Packets",
  sourcePacketValues,
  "SourcePacketsTable",
);
const blindOutputs = addTableSheet(
  workbook,
  "Blind Outputs",
  blindOutputValues,
  "BlindOutputsTable",
);
const inventory = addTableSheet(
  workbook,
  "Run Inventory",
  inventoryValues,
  "RunInventoryTable",
);
const protocol = workbook.worksheets.add("Protocol");
protocol.showGridLines = false;

// Read Me
readMe.getRange("A1:H1").merge();
readMe.getRange("A1").values = [["Qualitative-coding model qualification"]];
styleTitle(readMe, readMe.getRange("A1:H1"));
readMe.getRange("A2:H2").merge();
readMe.getRange("A2").values = [[
  "Synthetic engineering evidence only — no real Dreaddit, AGYW, KODIS, or CANDOR text was sent to a model.",
]];
readMe.getRange("A2:H2").format = {
  fill: COLORS.paleAmber,
  font: { bold: true, color: COLORS.ink },
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: COLORS.amber },
};
readMe.getRange("A2:H2").format.rowHeight = 34;
readMe.getRange("A4:B4").values = [["Current recommendation", "Status"]];
styleSection(readMe, readMe.getRange("A4:B4"));
readMe.getRange("A5:B5").values = [[
  selection.provisional_candidate,
  "Remediation candidate; paper model not selected",
]];
readMe.getRange("A5:B5").format = {
  fill: COLORS.paleTeal,
  font: { bold: true, color: COLORS.navy },
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: COLORS.teal },
};
readMe.getRange("A7:B7").values = [["Qualification accounting", "Value"]];
styleSection(readMe, readMe.getRange("A7:B7"));
readMe.getRange("A8:B15").values = [
  ["Recent model variants", 5],
  ["Synthetic corpus proxies", 4],
  ["Independent repetitions per model/packet", 3],
  ["Generation records", validation.run_records],
  ["Schema-valid generation records", validation.run_records],
  ["Strict hard-gate passes", validation.hard_gate_pass_records],
  ["Blinded judge records", judgeValidation.judge_records],
  ["Candidate score rows", judgeValidation.score_rows],
];
readMe.getRange("D4:H4").merge();
readMe.getRange("D4").values = [["How to interpret this workbook"]];
styleSection(readMe, readMe.getRange("D4:H4"));
readMe.getRange("D5:H12").merge();
readMe.getRange("D5").values = [[
  "Use Model Summary for the overall comparison and Model Dataset for corpus-proxy detail. Objective Metrics and Validation Issues preserve run-level audit evidence. Stability is diagnostic, not validity. Judge scores are supplementary because all judges are same-vendor models. Human Review is a blank, blinded pairwise instrument for qualified reviewers. Dataset Status is authoritative about what has and has not been run on real data. No model passed all 12 strict run-level gates; GPT-5.6 Sol is the remediation candidate because it had the highest hard-gate pass rate (10/12), despite GPT-5.4 and GPT-5.5 receiving slightly higher supplementary judge quality scores.",
]];
readMe.getRange("D5:H12").format = {
  fill: COLORS.paleBlue,
  font: { color: COLORS.ink },
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "outside", style: "thin", color: COLORS.line },
};
readMe.getRange("D14:H14").merge();
readMe.getRange("D14").values = [["Required next stage"]];
styleSection(readMe, readMe.getRange("D14:H14"));
readMe.getRange("D15:H19").merge();
readMe.getRange("D15").values = [[selection.next_required_step]];
readMe.getRange("D15:H19").format = {
  fill: COLORS.paleCoral,
  font: { color: COLORS.ink },
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "outside", style: "thin", color: COLORS.coral },
};
setColumnWidths(readMe, [38, 27, 3, 20, 20, 20, 20, 20]);
readMe.freezePanes.freezeRows(2);

// Formula-driven model summary.
modelSummary.getRange("A1:O1").merge();
modelSummary.getRange("A1").values = [["Model comparison — synthetic qualification"]];
styleTitle(modelSummary, modelSummary.getRange("A1:O1"));
modelSummary.getRange("A2:O2").merge();
modelSummary.getRange("A2").values = [[
  "Gate metrics are calculated from 12 generation records per model; judge metrics use 36 blinded ratings per model. No score here selects the paper model.",
]];
modelSummary.getRange("A2:O2").format = {
  fill: COLORS.paleAmber,
  font: { color: COLORS.ink },
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: COLORS.amber },
};
const modelHeaders = [
  "Model",
  "Hard-gate pass rate",
  "Exact quote rate",
  "Attribution rate",
  "Multi-source theme rate",
  "Cited source coverage",
  "Judge overall (1–5)",
  "Judge support (1–5)",
  "Voice/context (1–5)",
  "Negative case (1–5)",
  "Judge accept rate",
  "Judge serious-error rate",
  "Pairwise preference rate",
  "Cited-evidence stability",
  "Strict status",
];
modelSummary.getRange("A4:O4").values = [modelHeaders];
modelSummary.getRange("A4:O4").format = {
  fill: COLORS.navy,
  font: { bold: true, color: COLORS.white },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: COLORS.navy },
};
modelSummary.getRange("A5:A9").values = [
  ["gpt-5.6-sol"],
  ["gpt-5.4"],
  ["gpt-5.5"],
  ["gpt-5.6-luna"],
  ["gpt-5.6-terra"],
];
for (let row = 5; row <= 9; row += 1) {
  modelSummary.getRange(`B${row}`).formulas = [[
    `=AVERAGEIF('Objective Metrics'!$C$2:$C$61,$A${row},'Objective Metrics'!$I$2:$I$61)`,
  ]];
  modelSummary.getRange(`C${row}`).formulas = [[
    `=AVERAGEIF('Objective Metrics'!$C$2:$C$61,$A${row},'Objective Metrics'!$P$2:$P$61)`,
  ]];
  modelSummary.getRange(`D${row}`).formulas = [[
    `=AVERAGEIF('Objective Metrics'!$C$2:$C$61,$A${row},'Objective Metrics'!$R$2:$R$61)`,
  ]];
  modelSummary.getRange(`E${row}`).formulas = [[
    `=AVERAGEIF('Objective Metrics'!$C$2:$C$61,$A${row},'Objective Metrics'!$U$2:$U$61)`,
  ]];
  modelSummary.getRange(`F${row}`).formulas = [[
    `=AVERAGEIF('Objective Metrics'!$C$2:$C$61,$A${row},'Objective Metrics'!$T$2:$T$61)`,
  ]];
  modelSummary.getRange(`G${row}`).formulas = [[
    `=AVERAGEIF('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$N$2:$N$181)`,
  ]];
  modelSummary.getRange(`H${row}`).formulas = [[
    `=AVERAGEIF('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$F$2:$F$181)`,
  ]];
  modelSummary.getRange(`I${row}`).formulas = [[
    `=AVERAGEIF('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$H$2:$H$181)`,
  ]];
  modelSummary.getRange(`J${row}`).formulas = [[
    `=AVERAGEIF('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$I$2:$I$181)`,
  ]];
  modelSummary.getRange(`K${row}`).formulas = [[
    `=COUNTIFS('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$Q$2:$Q$181,"accept")/COUNTIF('Judge Scores'!$E$2:$E$181,$A${row})`,
  ]];
  modelSummary.getRange(`L${row}`).formulas = [[
    `=COUNTIFS('Judge Scores'!$E$2:$E$181,$A${row},'Judge Scores'!$O$2:$O$181,">0")/COUNTIF('Judge Scores'!$E$2:$E$181,$A${row})`,
  ]];
  modelSummary.getRange(`M${row}`).formulas = [[
    `=INDEX('Judge Summary'!$R$2:$R$6,MATCH($A${row},'Judge Summary'!$A$2:$A$6,0))`,
  ]];
  modelSummary.getRange(`N${row}`).formulas = [[
    `=AVERAGEIF('Stability'!$A$2:$A$21,$A${row},'Stability'!$G$2:$G$21)`,
  ]];
  modelSummary.getRange(`O${row}`).formulas = [[`=IF(B${row}=1,"PASS","REMEDIATE")`]];
}
modelSummary.getRange("A5:O9").format.borders = {
  insideHorizontal: { style: "thin", color: COLORS.line },
  bottom: { style: "thin", color: COLORS.line },
};
modelSummary.getRange("B5:F9").format.numberFormat = "0.0%";
modelSummary.getRange("G5:J9").format.numberFormat = "0.00";
modelSummary.getRange("K5:N9").format.numberFormat = "0.0%";
modelSummary.getRange("B5:B9").conditionalFormats.add("colorScale", {
  colors: [COLORS.paleCoral, COLORS.paleAmber, COLORS.paleGreen],
  thresholds: ["min", "50%", "max"],
});
modelSummary.getRange("G5:G9").conditionalFormats.add("colorScale", {
  colors: [COLORS.paleCoral, COLORS.paleAmber, COLORS.paleGreen],
  thresholds: ["min", "50%", "max"],
});
modelSummary.getRange("O5:O9").conditionalFormats.add("containsText", {
  text: "REMEDIATE",
  format: { fill: COLORS.paleAmber, font: { bold: true, color: COLORS.ink } },
});
modelSummary.getRange("A12:O12").merge();
modelSummary.getRange("A12").values = [[
  "Decision: GPT-5.6 Sol is the remediation candidate because it leads the strict gate portfolio (10/12). GPT-5.4 and GPT-5.5 lead the same-vendor judge scores, so qualified human review remains decisive.",
]];
modelSummary.getRange("A12:O12").format = {
  fill: COLORS.paleTeal,
  font: { bold: true, color: COLORS.navy },
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: COLORS.teal },
};
modelSummary.getRange("A12:O12").format.rowHeight = 42;
setColumnWidths(modelSummary, [18, 14, 13, 13, 15, 15, 15, 15, 15, 15, 14, 16, 16, 16, 14]);
modelSummary.freezePanes.freezeRows(4);
const qualityChart = modelSummary.charts.add("bar", {
  chartType: "bar",
  title: "Supplementary judge overall quality (1–5)",
  hasLegend: false,
});
const qualitySeries = qualityChart.series.add("Overall quality");
qualitySeries.categoryFormula = "'Model Summary'!$A$5:$A$9";
qualitySeries.formula = "'Model Summary'!$G$5:$G$9";
qualitySeries.fill = COLORS.blue;
qualityChart.title = "Supplementary judge overall quality (1–5)";
qualityChart.hasLegend = false;
qualityChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
qualityChart.yAxis = { numberFormatCode: "0.0", min: 0, max: 5 };
qualityChart.setPosition("Q2", "Y17");

// Dataset-status formatting.
setColumnWidths(datasetStatus.sheet, [18, 16, 18, 28, 22, 18, 28, 48, 48]);
datasetStatus.sheet.getRange("A2:I5").format.wrapText = true;
datasetStatus.sheet.getRange("A2:I5").format.verticalAlignment = "top";
datasetStatus.sheet.getRange("E2:E5").conditionalFormats.add("containsText", {
  text: "NOT_RUN",
  format: { fill: COLORS.paleCoral, font: { bold: true, color: COLORS.coral } },
});
datasetStatus.sheet.getRange("E2:E5").conditionalFormats.add("containsText", {
  text: "ABSENT",
  format: { fill: COLORS.paleAmber, font: { bold: true, color: COLORS.ink } },
});

// Model-by-dataset table.
setColumnWidths(modelDataset.sheet, [16, 18, 18, 30, 12, 13, 12, 12, 12, 14, 14, 14, 14, 14, 12, 14, 14, 14, 14, 14, 14, 14, 14, 14]);
modelDataset.sheet.getRange("F2:N21").format.numberFormat = "0.0%";
modelDataset.sheet.getRange("P2:T21").format.numberFormat = "0.00";
modelDataset.sheet.getRange("U2:X21").format.numberFormat = "0.0%";
modelDataset.sheet.getRange("D2:D21").format.wrapText = true;
modelDataset.sheet.getRange("F2:F21").conditionalFormats.add("colorScale", {
  colors: [COLORS.paleCoral, COLORS.paleAmber, COLORS.paleGreen],
  thresholds: ["min", "50%", "max"],
});
modelDataset.sheet.getRange("T2:T21").conditionalFormats.add("colorScale", {
  colors: [COLORS.paleCoral, COLORS.paleAmber, COLORS.paleGreen],
  thresholds: ["min", "50%", "max"],
});

// Raw/diagnostic sheets.
setColumnWidths(objective.sheet, [24, 9, 16, 9, 18, 10, 11, 10, 11, 9, 9, 10, 13, 13, 10, 12, 12, 12, 12, 12, 12, 13, 14, 14, 13, 12, 11]);
objective.sheet.getRange("M2:N61").format.numberFormat = "0.0%";
objective.sheet.getRange("P2:X61").format.numberFormat = "0.0%";
objective.sheet.getRange("I2:I61").conditionalFormats.add("cellIs", {
  operator: "equal",
  formula: 0,
  format: { fill: COLORS.paleCoral, font: { bold: true, color: COLORS.coral } },
});
setColumnWidths(validationIssues.sheet, [24, 9, 16, 9, 18, 10, 26, 80]);
validationIssues.sheet.getRange("H2:H100").format.wrapText = true;
validationIssues.sheet.getRange("F2:F100").conditionalFormats.add("containsText", {
  text: "error",
  format: { fill: COLORS.paleCoral, font: { bold: true, color: COLORS.coral } },
});
setColumnWidths(stability.sheet, [16, 18, 10, 10, 18, 18, 18, 18, 12, 12]);
stability.sheet.getRange("E2:H21").format.numberFormat = "0.0%";
setColumnWidths(judgeScores.sheet, [16, 18, 9, 9, 16, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 32, 12, 10, 80]);
judgeScores.sheet.getRange("S2:S181").format.wrapText = true;
judgeScores.sheet.getRange("O2:O181").conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: 0,
  format: { fill: COLORS.paleCoral, font: { bold: true, color: COLORS.coral } },
});
setColumnWidths(judgeSummary.sheet, [16, 12, 13, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 12, 12, 12, 12, 15, 15]);
judgeSummary.sheet.getRange("C2:S6").format.numberFormat = "0.00";
setColumnWidths(inventory.sheet, [28, 12, 68, 14, 12]);

// Editable human-review sheet.
setColumnWidths(humanReview.sheet, [16, 18, 9, 28, 11, 11, 16, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 13, 13, 32, 11, 20, 60, 14]);
humanReview.sheet.getRange("W2:W121").format.wrapText = true;
humanReview.sheet.getRange("A2:A121").format.fill = COLORS.paleAmber;
humanReview.sheet.getRange("G2:G121").dataValidation = {
  rule: { type: "list", values: ["A preferred", "B preferred", "both adequate", "neither adequate", "cannot judge"] },
};
for (const column of ["H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "U"]) {
  humanReview.sheet.getRange(`${column}2:${column}121`).dataValidation = {
    rule: { type: "list", values: [1, 2, 3, 4, 5] },
  };
}
for (const column of ["R", "S"]) {
  humanReview.sheet.getRange(`${column}2:${column}121`).dataValidation = {
    rule: { type: "list", values: ["accept", "revise", "reject", "escalate"] },
  };
}
humanReview.sheet.getRange("X2:X121").dataValidation = {
  rule: { type: "list", values: ["not_started", "in_progress", "complete", "adjudication_needed"] },
};
humanReview.sheet.getRange("X2:X121").conditionalFormats.add("containsText", {
  text: "complete",
  format: { fill: COLORS.paleGreen, font: { bold: true, color: COLORS.green } },
});

// Source and blind-output review aids.
setColumnWidths(sourcePackets.sheet, [18, 18, 55, 12, 18, 18, 30, 80]);
sourcePackets.sheet.getRange("C2:C49").format.wrapText = true;
sourcePackets.sheet.getRange("G2:H49").format.wrapText = true;
sourcePackets.sheet.getRange("A2:H49").format.verticalAlignment = "top";
setColumnWidths(blindOutputs.sheet, [18, 9, 9, 55, 80, 80, 60, 55, 55, 55, 32]);
blindOutputs.sheet.getRange("D2:J61").format.wrapText = true;
blindOutputs.sheet.getRange("A2:K61").format.verticalAlignment = "top";

// Protocol and source record.
protocol.getRange("A1:F1").merge();
protocol.getRange("A1").values = [["Protocol and audit sources"]];
styleTitle(protocol, protocol.getRange("A1:F1"));
protocol.getRange("A3:B3").values = [["Item", "Value"]];
styleSection(protocol, protocol.getRange("A3:B3"));
protocol.getRange("A4:B12").values = [
  ["Analytic contract", "Bounded codebook-oriented thematic coding; not reflexive thematic analysis"],
  ["Prompt version", "qc-direct-v1"],
  ["Output schema", "qualitative-output-v1"],
  ["Benchmark", "qc-synthetic-v1; 48 entirely fictional excerpts"],
  ["Model repetitions", "3 independent contexts per model and packet; no best-run selection"],
  ["Selection rule", "Governance/evidence gates → qualified human noninferiority → total cost → stability tie-break"],
  ["Current limitation", "No model passed all strict gates; no human ratings; no real-data inference"],
  ["Real selection split", "Approved eligible Dreaddit train only"],
  ["Held-out protection", "Dreaddit test and all AGYW outputs cannot influence selection"],
];
protocol.getRange("A14:B14").values = [["Source", "URL"]];
styleSection(protocol, protocol.getRange("A14:B14"));
protocol.getRange("A15:B23").values = [
  ["OpenAI current model guidance", "https://developers.openai.com/api/docs/guides/latest-model"],
  ["Braun & Clarke method congruence", "https://doi.org/10.1080/14780887.2020.1769238"],
  ["Jacobs & Wallach measurement", "https://doi.org/10.1145/3442188.3445901"],
  ["Chen et al. plurality metrics", "https://aclanthology.org/2026.findings-acl.2073/"],
  ["HICode many-to-many evaluation", "https://aclanthology.org/2025.emnlp-main.1580/"],
  ["CentaurTA evaluation rubric", "https://aclanthology.org/2026.findings-acl.778/"],
  ["Quote fidelity audit", "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0330217"],
  ["Stability vs alignment", "https://doi.org/10.3390/educsci16081314"],
  ["Blinded source-symmetric comparison (preprint)", "https://arxiv.org/abs/2607.28890"],
];
setColumnWidths(protocol, [42, 100, 12, 12, 12, 12]);
protocol.getRange("A4:B23").format.wrapText = true;
protocol.freezePanes.freezeRows(3);

// Compact verification before export.
const modelCheck = await workbook.inspect({
  kind: "table",
  range: "'Model Summary'!A1:O12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 15,
});
console.log(modelCheck.ndjson);
const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);

const previewSpecs = [
  ["Read Me", "A1:H19"],
  ["Model Summary", "A1:Y17"],
  ["Dataset Status", "A1:I5"],
  ["Model Dataset", "A1:X12"],
  ["Objective Metrics", "A1:Q12"],
  ["Validation Issues", "A1:H18"],
  ["Stability", "A1:J15"],
  ["Judge Scores", "A1:S12"],
  ["Judge Summary", "A1:S6"],
  ["Human Review", "A1:X12"],
  ["Source Packets", "A1:H12"],
  ["Blind Outputs", "A1:K8"],
  ["Run Inventory", "A1:E16"],
  ["Protocol", "A1:B23"],
];
for (const [sheetName, range] of previewSpecs) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  const safeName = sheetName.toLowerCase().replaceAll(" ", "_");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);
console.log(JSON.stringify({ outputPath, previewDir, sheets: previewSpecs.length }));
