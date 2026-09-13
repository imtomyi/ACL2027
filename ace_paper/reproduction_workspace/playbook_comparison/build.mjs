import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../original_sources/ace-appworld/experiments/playbooks');
function read(name) {
  const raw = fs.readFileSync(path.join(root, name), 'utf8');
  const sections = []; const items = []; let section = ''; let item;
  for (const line of raw.split(/\r?\n/)) {
    if (/^##\s/.test(line)) { section = line.replace(/^##\s+/, '').trim(); sections.push(section); item = undefined; }
    else {
      const match = line.match(/^\[([a-z]+-\d+)\]\s*(.*)$/);
      if (match) { item = {id: match[1], text: match[2], section}; items.push(item); }
      else if (item) item.text += '\n' + line;
    }
  }
  items.forEach(x => x.text = x.text.trimEnd());
  if (new Set(items.map(x => x.id)).size !== items.length) throw new Error('Duplicate IDs: ' + name);
  return {name, raw, items, sections, sha256: crypto.createHash('sha256').update(raw).digest('hex')};
}
const initial = read('appworld_initial_playbook.txt');
const offline = read('appworld_offline_trained_no_gt_playbook.txt');
const data = JSON.stringify({initial, offline}).replace(/</g, '\\u003c');
const template = fs.readFileSync(path.join(here, 'template.html.in'), 'utf8');
fs.writeFileSync(path.join(here, 'index.html'), template.replace('/*__DATA__*/', data));
console.log(JSON.stringify({initial: initial.items.length, offline: offline.items.length, output: path.join(here, 'index.html')}, null, 2));
