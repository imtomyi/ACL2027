const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL, fileURLToPath } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const base = __dirname;
  const data = JSON.parse(fs.readFileSync(path.join(base, 'catalog.json'), 'utf8'));
  const checks = [];
  const errors = [];
  const network = [];
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (/^https?:/.test(request.url())) network.push(request.url());
    });
    await page.goto(pathToFileURL(path.join(base, 'index.html')).href);
    await page.waitForFunction(() => document.querySelectorAll('.packet-button').length === 400);
    assert.equal(await page.locator('#view-guide').isVisible(), true);
    assert.equal(await page.locator('#view-packets').isVisible(), false);
    assert.equal(await page.locator('#sample-map span').count(), 100);
    assert.equal(await page.locator('#dataset-table-body tr').count(), 4);
    assert.deepEqual(await page.locator('#flaw-legend b').allTextContents(), ['20 / 100', '20 / 100', '20 / 100', '20 / 100', '20 / 100']);
    for (const corpus of ['dreaddit', 'goemotions', 'agyw_focus_groups', 'parlamint_gb']) {
      await page.selectOption('#guide-dataset', corpus);
      const example = data.packets.find(p => p.main_n100 && p.corpus_id === corpus);
      assert.deepEqual(await page.locator('.snippet p').allTextContents(), example.packet.source_text_context.map(e => e.text));
      assert.equal(await page.locator('.anatomy-claim blockquote').innerText(), example.packet.llm_generated_qualitative_claim.claim);
      await page.click('[data-guide-flaw="source_concentration"]');
      assert.equal(await page.locator('#sample-map span:not(.dimmed)').count(), 20);
      assert.equal(await page.locator('[data-guide-flaw="source_concentration"]').getAttribute('aria-pressed'), 'true');
      const chosen = data.packets.find(p => p.main_n100 && p.corpus_id === corpus && p.packet.known_intended_flaw_type === 'source_concentration');
      await page.click('#open-example');
      assert.equal(await page.locator('#view-packets').isVisible(), true);
      assert.equal(await page.locator('.packet-id').innerText(), chosen.packet_id);
      assert.deepEqual(await page.locator('.source-text').allTextContents(), chosen.packet.source_text_context.map(e => e.text));
      await page.click('#tab-guide');
      await page.click('[data-guide-flaw="source_concentration"]');
      assert.equal(await page.locator('#sample-map span.dimmed').count(), 0);
    }
    await page.click('[data-guide-dataset="dreaddit"]');
    assert.equal(await page.locator('#guide-dataset').inputValue(), 'dreaddit');
    await page.locator('#tab-guide').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#view-packets').isVisible(), true);
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#view-metrics').isVisible(), true);
    assert.equal(await page.locator('.metric-table tbody tr').count(), 4);
    await page.keyboard.press('Home');
    assert.equal(await page.locator('#view-guide').isVisible(), true);
    checks.push('Guide: 100-square sample map, five groups of 20, four source profiles, exact packet previews, example-to-explorer links and keyboard tabs.');
    await page.click('#tab-pipeline');
    assert.equal(await page.locator('#view-pipeline').isVisible(), true);
    assert.equal(await page.locator('#answer-files details').count(), 4);
    const evidence = await page.locator('#pipeline-data').textContent().then(JSON.parse);
    assert.equal(evidence.run_id, 'n100_same_model_table3_20260905_v2');
    assert.equal(evidence.files.filter(f => !f.frozen).length, 4);
    assert.ok(evidence.files.filter(f => f.frozen).length >= 15);
    for (const [i, file] of evidence.files.entries()) {
      const bytes = fs.readFileSync(file.path);
      assert.equal(require('node:crypto').createHash('sha256').update(bytes).digest('hex'), file.sha256);
      assert.equal(bytes.toString('utf8'), file.text);
      await page.selectOption('#pipeline-file', String(i));
      assert.equal(await page.locator('#pipeline-code').textContent(), file.text);
      assert.equal(await page.locator('#code-file-link').getAttribute('href'), file.url);
      assert.match(await page.locator('#code-meta').textContent(), file.frozen ? /Frozen run copy/ : /historical executed version not verified/);
    }
    await page.selectOption('#pipeline-file', '3');
    checks.push('Answer provenance: four selected truth maps; full code and prompts byte-matched to source; frozen versus reference labels verified.');
    await page.click('#tab-packets');
    await page.selectOption('#dataset', 'all');
    await page.locator('.packet-button').first().click();
    assert.equal(await page.locator('.source-text').count(), 4);
    const first = data.packets.find(p => p.main_n100);
    assert.deepEqual(JSON.parse(await page.locator('.answer-record').textContent()), first.truth_record);
    assert.equal(first.truth_record.packet_id, first.packet_id);
    assert.equal(await page.locator('.answer-key-panel').count(), 1);
    assert.match(await page.locator('.answer-key-panel').innerText(), /VISUAL ANSWER KEY/);
    assert.equal(await page.locator('.answer-chip').count(), 4);
    assert.deepEqual(await page.locator('.source-text').allTextContents(), first.packet.source_text_context.map(e => e.text));
    await page.getByText('Reviewer output files (9)', { exact: true }).click();
    assert.equal(await page.locator('#detail table').first().locator('tbody tr').count(), 9);
    checks.push('Default set: 400 packets; four verbatim excerpts; nine current role/model records.');

    for (const corpus of ['dreaddit', 'goemotions', 'agyw_focus_groups', 'parlamint_gb']) {
      await page.selectOption('#dataset', corpus);
      assert.equal(await page.locator('.packet-button').count(), 100);
      await page.selectOption('#flaw', 'source_concentration');
      assert.equal(await page.locator('.packet-button').count(), 20);
      assert.equal(await page.locator('.excerpt .cited').count(), 1);
      await page.selectOption('#flaw', 'all');
    }
    checks.push('All four corpus filters: 100 packets each; source-concentration filter: 20 packets and one actual citation.');

    const parliament = data.packets.find(p => p.main_n100 && p.corpus_id === 'parlamint_gb');
    await page.fill('#search', parliament.packet_id);
    assert.equal(await page.locator('.packet-button').count(), 1);
    assert.deepEqual(await page.locator('.source-text').allTextContents(), parliament.packet.source_text_context.map(e => e.text));
    await page.locator('.source-provenance summary').first().click();
    assert.match(await page.locator('#detail').innerText(), /XML /);
    await page.fill('#search', 'a_query_with_no_results_019292929');
    assert.equal(await page.locator('.packet-button').count(), 0);
    assert.equal(await page.locator('#previous').isDisabled(), true);
    assert.equal(await page.locator('#next').isDisabled(), true);
    await page.fill('#search', '');
    await page.selectOption('#dataset', 'all');
    await page.selectOption('#scope', 'all');
    assert.equal(await page.locator('.packet-button').count(), 1010);
    await page.selectOption('#scope', 'earlier');
    assert.equal(await page.locator('.packet-button').count(), 610);
    await page.fill('#search', 'PKT_c4eae72db76207c1');
    await page.evaluate(() => document.querySelectorAll('.source-provenance').forEach(node => node.open = true));
    assert.match(await page.locator('#detail').innerText(), /whitespace-only difference/);
    checks.push('ID search, full source text, XML trace, empty state, earlier scope (610) and whitespace-only audit warning.');

    await page.fill('#search', '');
    await page.selectOption('#scope', 'main');
    const before = await page.locator('.packet-heading h2').innerText();
    await page.click('#next');
    assert.notEqual(await page.locator('.packet-heading h2').innerText(), before);
    await page.click('#previous');
    assert.equal(await page.locator('.packet-heading h2').innerText(), before);
    await page.getByText('Dataset origin and theoretical context', { exact: true }).click();
    const provenance = await page.getByText('Local provenance record', { exact: true }).getAttribute('href');
    assert.ok(fs.existsSync(fileURLToPath(provenance)));
    checks.push('Previous/next navigation and local provenance links.');

    const shotDir = path.join(base, 'screenshots');
    fs.mkdirSync(shotDir, { recursive: true, mode: 0o700 });
    await page.getByText('Dataset origin and theoretical context', { exact: true }).click();
    for (const view of ['guide', 'packets', 'metrics', 'pipeline']) {
      await page.click('#tab-' + view);
      for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844], ['narrow', 320, 740]]) {
        await page.setViewportSize({ width, height });
        await page.evaluate(() => window.scrollTo(0, 0));
        const sizes = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }));
        assert.ok(sizes.scroll <= sizes.viewport, `${view}/${name}: horizontal overflow ${JSON.stringify(sizes)}`);
        await page.screenshot({ path: path.join(shotDir, `${view}-${name}.png`), fullPage: name === 'mobile' });
        checks.push(`${view}/${name}: ${width}x${height}, no document horizontal overflow.`);
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.click('#tab-guide');
    await page.reload();
    assert.equal(await page.locator('#view-guide').isVisible(), true);
    const linkPaths = await page.locator('a[href]').evaluateAll(nodes => nodes.map(node => node.href).filter(href => href.startsWith('file:')));
    for (const href of linkPaths) assert.ok(fs.existsSync(fileURLToPath(href)), href);
    const mainEntries = data.packets.filter(p => p.main_n100);
    assert.equal(mainEntries.length, 400);
    assert.equal(mainEntries.flatMap(p => p.packet.source_text_context).length, 1600);
    for (const p of data.packets) {
      for (const ref of [p.packet_file, p.snapshot, ...Object.values(p.prompts || {}),
        ...p.source_traces.map(t => t.raw_file), ...p.outputs]) {
        assert.ok(fs.existsSync(ref.path), ref.path);
      }
    }
    for (const file of ['DATASET_BACKGROUND.md', 'README.md', 'VERIFIED_INVENTORY.md']) {
      const markdown = fs.readFileSync(path.join(base, file), 'utf8');
      for (const match of markdown.matchAll(/\]\(([^)]+)\)/g)) {
        if (!/^https?:/.test(match[1])) assert.ok(fs.existsSync(path.resolve(base, match[1])), match[1]);
      }
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(network, []);
    checks.push('All linked local source/output/prompt files and Markdown links exist; no browser errors or network requests.');
    fs.writeFileSync(path.join(base, 'browser_checks.json'), JSON.stringify({ status: 'passed', checked_at_utc: new Date().toISOString(), checks }, null, 2) + '\n', { mode: 0o600 });
    for (const file of fs.readdirSync(shotDir)) fs.chmodSync(path.join(shotDir, file), 0o600);
    console.log(JSON.stringify({ status: 'passed', checks }, null, 2));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
