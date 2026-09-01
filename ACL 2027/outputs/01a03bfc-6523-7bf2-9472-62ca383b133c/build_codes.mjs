import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "/Users/OODI/Downloads/ACL 2027/outputs/01a03bfc-6523-7bf2-9472-62ca383b133c";
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Access Codes");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(5);

sheet.getRange("A1:G1").merge();
sheet.getRange("A1").values = [["Warrant Study — Access Code Registry"]];
sheet.getRange("A1:G1").format = {
  fill: "#17324D",
  font: { bold: true, color: "#FFFFFF", size: 18 },
  verticalAlignment: "center",
};
sheet.getRange("A1:G1").format.rowHeight = 34;

sheet.getRange("A2:G2").merge();
sheet.getRange("A2").values = [["Living registry for testing and rotating app access codes. Treat this workbook as confidential."]];
sheet.getRange("A2:G2").format = {
  fill: "#EAF1F7",
  font: { color: "#334E68", italic: true },
  verticalAlignment: "center",
};
sheet.getRange("A2:G2").format.rowHeight = 26;

sheet.getRange("A4:B4").values = [["Active codes", null]];
sheet.getRange("B4").formulas = [["=COUNTIF(F6:F100,\"Active\")"]];
sheet.getRange("D4:E4").values = [["Last registry update", new Date("2026-08-25T12:00:00")]];
sheet.getRange("E4").setNumberFormat("yyyy-mm-dd");
sheet.getRange("A4:E4").format = { font: { bold: true, color: "#17324D" } };
sheet.getRange("B4").format = { fill: "#DDF4E4", font: { bold: true, color: "#166534" }, horizontalAlignment: "center" };
sheet.getRange("E4").format = { fill: "#FFF4CC", font: { bold: true, color: "#7A5200" }, horizontalAlignment: "center", numberFormat: "yyyy-mm-dd" };

const headers = [["Code Type", "Access Code", "Purpose", "Environment", "Last Updated", "Status", "Notes"]];
sheet.getRange("A5:G5").values = headers;
sheet.getRange("A5:G5").format = {
  fill: "#2E5D7B",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#17324D" },
};
sheet.getRange("A5:G5").format.rowHeight = 28;

sheet.getRange("A6:G7").values = [
  ["Participant", "DRE-6H9R-W2CM-Q8TX", "Enter the participant review flow", "Local configuration; production secret is configured", new Date("2026-08-25T12:00:00"), "Active", "Use for app testing; rotate if shared beyond approved testers."],
  ["Organizer", "ORG-8V3N-M7KQ-4PZT", "Open the organizer dashboard and exports", "Local configuration; production secret is configured", new Date("2026-08-25T12:00:00"), "Active", "More privileged—share only with study organizers."],
];
sheet.getRange("E6:E7").setNumberFormat("yyyy-mm-dd");
sheet.getRange("A6:G7").format = {
  font: { color: "#243B53", size: 10 },
  verticalAlignment: "center",
  wrapText: true,
  borders: { insideHorizontal: { style: "thin", color: "#D9E2EC" }, bottom: { style: "thin", color: "#BCCCDC" } },
};
sheet.getRange("A6:A7").format.font = { bold: true, color: "#17324D" };
sheet.getRange("B6:B7").format = { fill: "#FFF8E6", font: { bold: true, color: "#7A5200", name: "Aptos Mono" }, horizontalAlignment: "center" };
sheet.getRange("F6:F7").format = { fill: "#DDF4E4", font: { bold: true, color: "#166534" }, horizontalAlignment: "center" };
sheet.getRange("A6:G7").format.rowHeight = 44;

sheet.getRange("A9:G9").merge();
sheet.getRange("A9").values = [["Update guide: add a new row when a code changes, mark the old row Retired, and record the rotation date in Last Updated."]];
sheet.getRange("A9:G9").format = { fill: "#F0F4F8", font: { color: "#486581" }, wrapText: true, verticalAlignment: "center" };
sheet.getRange("A9:G9").format.rowHeight = 30;

sheet.getRange("F6:F100").dataValidation = { rule: { type: "list", values: ["Active", "Retired", "Pending"] } };
sheet.getRange("A5:G7").format.borders = { preset: "outside", style: "thin", color: "#9FB3C8" };

sheet.getRange("A:A").format.columnWidth = 16;
sheet.getRange("B:B").format.columnWidth = 25;
sheet.getRange("C:C").format.columnWidth = 31;
sheet.getRange("D:D").format.columnWidth = 40;
sheet.getRange("E:E").format.columnWidth = 16;
sheet.getRange("F:F").format.columnWidth = 13;
sheet.getRange("G:G").format.columnWidth = 46;

const table = sheet.tables.add("A5:G7", true, "AccessCodeRegistry");
table.style = "TableStyleMedium2";
table.showFilterButton = true;

const check = await workbook.inspect({ kind: "table", range: "Access Codes!A1:G9", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 8 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);

const preview = await workbook.render({ sheetName: "Access Codes", range: "A1:G9", scale: 1.5, format: "png" });
await fs.writeFile(`${outputDir}/access-code-registry-preview.png`, new Uint8Array(await preview.arrayBuffer()));
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/warrant-study-access-code-registry.xlsx`);
