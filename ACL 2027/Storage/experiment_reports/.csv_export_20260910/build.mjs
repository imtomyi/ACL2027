import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { Workbook } from '@oai/artifact-tool';

const project = '/Users/tom/Documents/GitHub/ACL2027/ACL 2027';
const output = path.join(project, 'Storage/experiment_reports');
const old = path.join(project, 'Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_flaw_gemma_expansion_dev10_eval80_20260910');
const next = path.join(project, 'Storage/rq2_personal_local_diagnostic/warrantroute_claim_detection/ace_claim_online_v1_dev10_stream80_20260910_prepared');
const python = '/Users/tom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';

async function readCSV(file) {
  const wb = await Workbook.fromCSV(await fs.readFile(file, 'utf8'), { sheetName: 'Source' });
  const [headers, ...rows] = wb.worksheets.getItemAt(0).getUsedRange().values;
  return rows.filter(row => row.some(value => value !== null && value !== '')).map(row =>
    Object.fromEntries(headers.map((key, i) => [key, row[i] ?? ''])));
}

const historical = await readCSV(path.join(project, 'Storage/draft_review_packets/table3_warrantroute_n100_final.csv'));
const quality = await readCSV(path.join(old, 'dataset_quality.csv'));
const paired = await readCSV(path.join(old, 'paired_changes.csv'));
const playbook = await readCSV(path.join(old, 'playbook_result.csv'));
const status = JSON.parse(await fs.readFile(path.join(next, 'status.json'), 'utf8'));
const config = JSON.parse(await fs.readFile(path.join(next, 'config.json'), 'utf8'));
assert.equal(historical.length, 48);
assert.equal(quality.length, 8);
assert.equal(paired.length, 8);
assert.equal(playbook.length, 4);
assert.equal(status.status, 'prepared_not_started');

const headers = ['Dataset', 'Method', 'Model', 'TP/N', 'Recall (%)', 'Credibility (%)', 'Conformability (%)',
  'Experiment', 'Checkpoint', 'Status', 'Processed N', 'Planned N', 'Credibility binary N',
  'Credibility unresolved N', 'Credibility technical N', 'Conformability binary N',
  'Conformability unresolved N', 'Conformability technical N', 'Pending N', 'Quality denominator', 'Qualification'];
const qualification = 'Private working diagnostic; not manuscript-qualified; no cross-protocol ranking';
const rows = quality.map(r => [r.Dataset, r.Method, 'Gemma 3 4B', 'N/A', 'N/A',
  Number(r.credibility_resolved_case_pct), Number(r.conformability_resolved_case_pct),
  'ACE flaw expansion 20260910', r.Checkpoint, 'Paused - partial', Number(r.Processed), Number(r.Planned_N),
  Number(r.credibility_binary_n), Number(r.credibility_null), Number(r.credibility_technical),
  Number(r.conformability_binary_n), Number(r.conformability_null), Number(r.conformability_technical),
  Number(r.credibility_unprocessed), 'Resolved binary cases only; excludes unresolved and pending', qualification]);
for (const r of historical) {
  rows.push([r.Dataset, r.Method, r.Model, r['TP/N'], r['Recall (%) \u2191'],
    Number(r['Credibility (%)']), Number(r['Conformability (%)']), 'Historical Table 3 n100', '',
    'Historical recorded result', 100, 100, 100, 0, 0, 100, 0, 0, 0,
    '100 binary judgments per metric, per historical protocol notes', qualification]);
}
for (const ds of ['Dreaddit', 'GoEmotions', 'CaChe', 'ParlaMint-GB']) {
  for (const method of ['Static seed control', 'ACE-inspired online WarrantRoute']) {
    rows.push([ds, method, 'Gemma 3 4B', 'N/A', 'N/A', 'N/A', 'N/A', 'ACE claim online v1', '',
      'Not run', 0, config.stream_n, 0, 0, 0, 0, 0, 0, config.stream_n,
      'Not measured; all cases pending', qualification]);
  }
}
assert.equal(rows.length, 64);
assert(rows.every(row => row.length === headers.length));

const pairHeaders = ['Dataset', 'Dimension', 'Adapted checkpoint', 'Joint binary N', 'Improved', 'Worsened',
  'Unchanged', 'Paired change (pp)', 'Experiment', 'Status'];
const pairRows = paired.map(r => [r.Dataset, r.Dimension, r.Adapted_checkpoint, Number(r.Joint_binary_N),
  Number(r.Improved), Number(r.Worsened), Number(r.Unchanged), Number(r.Paired_change_pp),
  'ACE flaw expansion 20260910', 'Paused - partial']);
const pbHeaders = ['Dataset', 'Development exposures', 'Seed rules', 'Learned rules at E3', 'Proposed edits',
  'Accepted additions', 'Accepted refinements', 'Distinct learned rules retrieved', 'Experiment', 'Status'];
const pbRows = playbook.map(r => [r.Dataset, Number(r.Development_processed), 2, Number(r.Learned_rules_evaluated),
  Number(r.Proposed_edits), Number(r.Accepted_adds), Number(r.Accepted_replacements),
  Number(r.Distinct_learned_rules_retrieved), 'ACE flaw expansion 20260910', 'Seed only']);

const outputs = [
  ['table3_style_results_20260910.csv', headers, rows],
  ['table3_style_paired_changes_20260910.csv', pairHeaders, pairRows],
  ['table3_style_playbook_20260910.csv', pbHeaders, pbRows],
];
for (const [name, columns, records] of outputs) {
  const wb = Workbook.create();
  const sheet = wb.worksheets.add('Results');
  const matrix = [columns, ...records];
  sheet.getRangeByIndexes(0, 0, matrix.length, columns.length).values = matrix;
  wb.recalculate();
  const actual = sheet.getUsedRange().values;
  assert.deepEqual(actual, matrix);
  console.log((await wb.inspect({kind: 'table', range: 'Results!A1:G4', include: 'values', tableMaxRows: 4,
    tableMaxCols: 7, maxChars: 1600})).ndjson);
  // CSV has no styling or native workbook export in the documented API.
  // Serialize the verified Artifact Tool matrix with the standard CSV library.
  execFileSync(python, ['-c', 'import csv,json,sys; rows=json.load(sys.stdin); f=open(sys.argv[1],"x",encoding="utf-8-sig",newline=""); csv.writer(f).writerows(rows); f.close()',
    path.join(output, name)], { input: JSON.stringify(actual), encoding: 'utf8' });
  console.log(JSON.stringify({file: path.join(output, name), rows: records.length, columns: columns.length}));
}
