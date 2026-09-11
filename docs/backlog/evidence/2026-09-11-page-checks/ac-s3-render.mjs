// AC-S3 check for PBI-021: runs the PUBLISHED page's script (as read back from the artifact) against the live
// store's documents as read after the tabs/* delete, and renders every project's tabs. Stub DOM copied from
// tests/page.test.mjs env(). Fails on any console.error the page logs (a tab renderer that threw).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const [pagePath, dumpDir] = process.argv.slice(2);
const html = fs.readFileSync(pagePath, 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tabNames = [...html.matchAll(/role="tab" id="tab-(\w+)"/g)].map(m => m[1]);

const errors = [];
console.error = (...a) => errors.push(a.map(x => x instanceof Error ? x.stack : String(x)).join(' '));

const els = {}, doc = { activeElement: null };
const el = id => els[id] || (els[id] = {
  id, innerHTML: '', textContent: '', className: '', hidden: false, disabled: false, value: '', tabIndex: 0, dataset: {}, attrs: {}, listeners: {},
  setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
  focus() { doc.activeElement = this; }, querySelectorAll() { return []; }, querySelector() { return null; },
});
const tabs = tabNames.map(n => { const t = el('tab-' + n); t.dataset.tab = n; return t; });
const subs = {};
const db = {
  collection: name => ({ orderBy() { return this; }, onSnapshot(cb) { subs['c:' + name] = cb; } }),
  doc: p => ({ onSnapshot(cb) { subs['d:' + p] = cb; } }),
};
Object.assign(doc, { getElementById: el, querySelectorAll: () => tabs, addEventListener() {} });
globalThis.document = doc; globalThis.window = globalThis;
const ls = new Map();
globalThis.localStorage = { getItem: k => ls.has(k) ? ls.get(k) : null, setItem: (k, v) => ls.set(k, String(v)) };
globalThis.claude = { use: async () => db };
globalThis.scrollTo = () => {}; globalThis.setInterval = () => 0;
vm.runInThisContext(script, { filename: 'published page <script>' });
await new Promise(r => setTimeout(r, 0));

const load = coll => {
  const dir = path.join(dumpDir, coll);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.endsWith('.json'))
    .map(f => ({ id: f.slice(0, -5), ...JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) }));
};
const fire = (key, docs) => subs[key](key.startsWith('d:') ? { exists: !!docs, data: () => docs } :
  { docs: docs.map(d => ({ id: d.id, exists: true, data: () => { const { id, ...rest } = d; return rest; } })) });
const byOrder = (a, b) => String(a.last ?? '').localeCompare(String(b.last ?? ''));

const projects = load('projects').sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
fire('c:projects', projects);
fire('c:sessions', load('sessions').sort(byOrder));
fire('c:runs', load('runs').sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0)));
fire('c:projectTabs', load('projectTabs'));
if (subs['d:catalogue/index']) fire('d:catalogue/index', load('catalogue').find(d => d.id === 'index') || null);
for (const k of Object.keys(subs).filter(k => k.startsWith('d:') && k !== 'd:catalogue/index')) {
  const [coll, id] = k.slice(2).split('/');
  fire(k, load(coll).find(d => d.id === id) || null);
}
await new Promise(r => setTimeout(r, 0));

const bad = /has not been exported|not exported yet|could not be drawn|failed to render|Something went wrong/i;
let failures = 0;
for (const p of projects) {
  const e = el('project'); e.value = 'p:' + p.id; (e.listeners.change || []).forEach(f => f({ target: e }));
  const rows = tabNames.map(n => {
    const h = el('panel-' + n).innerHTML, hidden = el('tab-' + n).hidden;
    const issue = hidden ? 'tab hidden' : !h.trim() ? 'empty panel' : bad.test(h) ? 'shows: ' + h.match(bad)[0] : '';
    if (issue) failures++;
    return `${n}=${issue || 'ok (' + h.length + ' chars)'}`;
  });
  console.log(`${p.id}: ${rows.join(', ')}`);
}
console.log(`console.error calls: ${errors.length}`);
errors.forEach(x => console.log('  ' + x.split('\n')[0]));
console.log(failures || errors.length ? 'AC-S3 render check: FAIL' : 'AC-S3 render check: PASS');
process.exit(failures || errors.length ? 1 : 0);
