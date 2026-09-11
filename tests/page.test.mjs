// Checks the page's project picker and session filter: runs the inline script from site/index.html against a
// stub DOM and a fake store, fires store snapshots and picker changes, and asserts on what the page renders.
//
//     node tests/page.test.mjs
//
// Node built-ins only (no npm install). Any failed check throws, so the process exits non-zero.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html = fs.readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tabNames = [...html.matchAll(/role="tab" id="tab-(\w+)"/g)].map(m => m[1]);
assert.ok(tabNames.includes('spec') && tabNames.includes('overview'), 'tab buttons found in site/index.html');

// A fresh page: each call re-runs the script against new stubs, with localStorage preset to `storage`.
function env(storage = {}) {
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
    doc: path => ({ onSnapshot(cb) { subs['d:' + path] = cb; } }),
  };
  const store = new Map(Object.entries(storage));
  Object.assign(doc, {
    getElementById: el, querySelectorAll: () => tabs, addEventListener() {},
  });
  globalThis.document = doc;
  globalThis.window = globalThis;
  globalThis.localStorage = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)) };
  globalThis.claude = { use: async () => db };
  globalThis.scrollTo = () => {};
  globalThis.setInterval = () => 0;
  vm.runInThisContext(script, { filename: 'site/index.html <script>' });
  const fire = (key, docs) => subs[key](key.startsWith('d:') ? { exists: !!docs, data: () => docs } :
    { docs: docs.map(d => ({ id: d.id, exists: true, data: () => { const { id, ...rest } = d; return rest; } })) });
  const change = (id, value) => { const e = el(id); e.value = value; e.listeners.change.forEach(f => f({ target: e })); };
  const selected = () => tabs.find(t => t.attrs['aria-selected'] === 'true').dataset.tab;
  return { el, subs, fire, change, selected, store, doc };
}
const tick = () => new Promise(r => setTimeout(r, 0));

const now = new Date().toISOString(), old = '2026-09-01T10:00:00Z';
const usage = (src, eff) => ({ source: src, totals: { effective: eff, requests: 3, output: 1, cacheRead: 1 }, byModel: [], groups: [], subagents: [], hourly: [{ hour: '2026-09-10T10', main: 1, sub: 1 }], limits: [], span: { first: old, last: old } });
const PROJECTS = [
  { id: 'platform-catalogue', name: 'platform-catalogue', order: 0, statusDoc: 'meta/status', branch: 'build/logic-core', running: 0, sessions: ['s1'], usage: usage('PC-ALL', 1000) },
  { id: 'dispatch-board', name: 'dispatch-board', order: 1, statusDoc: 'status/dispatch-board', branch: 'main', running: 1, sessions: ['s2'], usage: usage('DB-ALL', 2000) },
];
const SESSIONS = [  // newest last: the page reverses the orderBy('last') snapshot
  { id: 's1', title: 'PC build', project: 'platform-catalogue', last: old, start: old, running: 0, usage: usage('S1-ONLY', 10) },
  { id: 's4', title: 'Legacy <img src=x>', project: 'jdk', last: old, start: old, running: 0, usage: usage('S4', 1) },
  { id: 's3', title: 'Loose session', project: null, last: now, start: now, running: 0, usage: usage('S3', 2) },
  { id: 's2', title: 'DB build', project: 'dispatch-board', last: now, start: now, running: 1, usage: usage('S2', 20) },
];
const RUNS = [
  { id: 'r1', session: 's1', project: 'platform-catalogue', seq: 1, lane: 'cw', kind: 'done', label: 'PC write' },
  { id: 'r2', session: 's1', project: 'platform-catalogue', seq: 2, lane: 'cr', kind: 'go', label: 'PC review' },
  { id: 'r3', session: 's2', project: 'dispatch-board', seq: 1, lane: 'cw', kind: 'running', label: 'DB write' },
  { id: 'r4', session: 's3', project: null, seq: 1, lane: 'other', kind: 'done', label: 'Loose run' },
];
const TABS = [
  { id: 'platform-catalogue.spec', generatedAt: now, source: 'PCSPEC', revision: '9', prd: { frs: 1 }, rounds: [], goals: [], scopeIn: [], scopeOut: [], logicCore: [], approval: '—', approvedBy: '—' },
  { id: 'platform-catalogue.backlog', generatedAt: now, source: 'x', board: '', pbis: [{ id: 'PBI-001', title: 't', dependsOn: '—', state: 'done', group: 'g', risk: 'Low' }] },
  { id: 'platform-catalogue.git', generatedAt: now, source: 'git', branch: 'build/logic-core', commits: [], remotes: [] },
  { id: 'dispatch-board.git', generatedAt: now, source: 'git', branch: 'main', commits: [{ sha: 'abc', subject: 'x', date: now }], remotes: ['origin x'], repoPath: 'C:/Users/jdk/dispatch-board' },
];
let passed = 0;
const ok = m => { passed++; console.log('ok  ' + m); };

// ---- 1. a fresh load: guards, default choice, pickers, scoping
{
  const e = env({ 'board-tab': 'spec' });
  await tick();
  assert.equal(e.el('statusText').textContent, 'Connecting');
  assert.equal(e.el('tab-spec').hidden, true);
  assert.equal(e.selected(), 'spec');
  ok('before load: Connecting, project tabs hidden, saved tab kept');

  e.fire('c:projects', PROJECTS);
  assert.equal(e.el('project').innerHTML, '');
  assert.equal(e.el('statusText').textContent, 'Connecting');
  assert.equal(e.selected(), 'spec');
  ok('projects alone do not count as loaded; nothing chosen, saved tab untouched');
  assert.ok(e.subs['d:meta/status'] && e.subs['d:status/dispatch-board']);
  ok('each project status document is watched once');

  e.fire('c:sessions', SESSIONS);
  const P = e.el('project').innerHTML, S = e.el('session').innerHTML;
  assert.match(P, /value="p:platform-catalogue">platform-catalogue<\/option><option value="p:dispatch-board" selected>dispatch-board · live<\/option><option value="other">Other sessions · last 7 days<\/option>$/);
  ok('picker lists projects in order, then Other sessions; default is the project with a live session');
  assert.match(S, /^<option value="" selected>All sessions · 1<\/option><option value="s2">DB build · live<\/option>$/);
  ok('session filter: All sessions (default) plus the project\'s sessions');
  assert.equal(e.el('tab-spec').hidden, false);
  assert.equal(e.selected(), 'spec');
  ok('project view shows every project tab; the saved Spec tab survives the load');
  assert.match(e.el('panel-spec').innerHTML, /has not been exported/);
  assert.match(e.el('panel-assumptions').innerHTML, /has not been exported/);
  assert.match(e.el('panel-backlog').innerHTML, /has not been exported/);
  ok('dispatch-board without spec/backlog shows the existing empty states');

  e.fire('c:runs', RUNS);
  e.fire('c:projectTabs', TABS);
  e.fire('d:status/dispatch-board', { live: true, updatedAt: now });
  e.fire('d:meta/status', { live: false, title: 'Paused', updatedAt: old });
  assert.match(e.el('panel-dispatch').innerHTML, /DB write/);
  assert.doesNotMatch(e.el('panel-dispatch').innerHTML, /PC write|Loose run/);
  assert.equal(e.el('statusText').textContent, 'Building');
  assert.equal(e.el('crumb').textContent, 'main');
  assert.match(e.el('panel-git').innerHTML, /dispatch-board/);
  assert.match(e.el('panel-usage').innerHTML, /DB-ALL/);
  ok('dispatch-board: only its runs, Building while its run runs, branch crumb, git tab, project-wide usage');

  e.change('project', 'p:platform-catalogue');
  assert.equal(e.store.get('board-view'), 'p:platform-catalogue');
  assert.match(e.el('session').innerHTML, /All sessions · 1<\/option><option value="s1">PC build<\/option>$/);
  const D = e.el('panel-dispatch').innerHTML;
  assert.ok(D.includes('PC write') && D.includes('PC review') && !D.includes('DB write'));
  assert.equal(e.el('statusText').textContent, 'Paused');
  assert.match(e.el('panel-spec').innerHTML, /PCSPEC/);
  assert.doesNotMatch(e.el('panel-backlog').innerHTML, /callout warn/);
  assert.match(e.el('panel-usage').innerHTML, /PC-ALL/);
  assert.match(e.el('panel-dispatch').innerHTML, /dispatched in this project&#39;s sessions|dispatched in this project's sessions/);
  ok('switch project: filter rebuilt, runs/status/tabs/usage follow; empty board note shows no callout');

  e.change('session', 's1');
  assert.equal(e.store.get('board-filter'), 's1');
  assert.match(e.el('panel-usage').innerHTML, /S1-ONLY/);
  assert.match(e.el('panel-dispatch').innerHTML, /dispatched in this session/);
  assert.equal(e.el('tab-spec').hidden, false);
  ok('session filter narrows Dispatch and usage to one session; project tabs stay');

  e.change('project', 'other');
  assert.equal(e.el('tab-spec').hidden, true);
  assert.equal(e.selected(), 'overview');
  const S2 = e.el('session').innerHTML;
  assert.ok(!S2.includes('All sessions') && S2.includes('value="s3" selected') && S2.includes('value="s4"'));
  assert.ok(S2.includes('Legacy &lt;img src=x&gt;') && !S2.includes('<img'));
  assert.match(e.el('panel-dispatch').innerHTML, /Loose run/);
  assert.equal(e.el('statusText').textContent, 'Active');
  assert.match(e.el('panel-overview').innerHTML, /Not linked to a project/);
  ok('Other sessions: project tabs hidden, Spec falls back to Overview, unlinked (and unknown-project) sessions listed, titles escaped, session-scoped view');

  // focus guard: an open picker is not rebuilt; its blur catches it up
  const P0 = e.el('project'); P0.innerHTML = 'SENTINEL'; e.doc.activeElement = P0;
  e.fire('c:sessions', SESSIONS);
  assert.equal(P0.innerHTML, 'SENTINEL');
  assert.notEqual(e.el('session').innerHTML, 'SENTINEL');
  e.doc.activeElement = null; P0.listeners.blur.forEach(f => f());
  assert.match(P0.innerHTML, /value="other" selected/);
  ok('focused picker is not rebuilt by a snapshot; blur rebuilds it');

  // the selected session disappears from the store
  e.fire('c:sessions', SESSIONS.filter(s => s.id !== 's3'));
  assert.match(e.el('session').innerHTML, /value="s4" selected/);
  ok('a vanished session is replaced by the next unlinked one');
  e.fire('c:sessions', SESSIONS.filter(s => s.id !== 's3' && s.id !== 's4'));
  assert.doesNotMatch(e.el('project').innerHTML, /Other sessions/);
  assert.match(e.el('project').innerHTML, /value="p:dispatch-board" selected/);
  ok('with no unlinked sessions left, Other sessions disappears and the view falls back to a project');
}

// ---- 2. a saved view wins; a stale one falls back
{
  const e = env({ 'board-view': 'p:platform-catalogue', 'board-filter': 's1' });
  await tick();
  e.fire('c:sessions', SESSIONS); e.fire('c:projects', PROJECTS);
  assert.match(e.el('project').innerHTML, /value="p:platform-catalogue" selected/);
  assert.match(e.el('session').innerHTML, /value="s1" selected/);
  ok('saved project and saved session filter are restored (sessions snapshot first)');
}
{
  const e = env({ 'board-view': 'p:gone' });
  await tick();
  e.fire('c:projects', PROJECTS.map(p => ({ ...p, running: 0 }))); e.fire('c:sessions', SESSIONS.map(s => ({ ...s, running: 0, last: old })));
  assert.match(e.el('project').innerHTML, /value="p:platform-catalogue" selected/);
  ok('no saved view and no live project: the first project');
}
{
  const e = env();
  await tick();
  e.fire('c:projects', []); e.fire('c:sessions', SESSIONS);
  assert.equal(e.el('project').innerHTML.trim(), '<option value="other" selected>Other sessions · last 7 days</option>');
  assert.equal(e.el('tab-spec').hidden, true);
  ok('store without projects yet (before the first push): every session under Other sessions');
}

// ---- 3. the first project push reaches a page that was opened before it
{
  const e = env();
  await tick();
  e.fire('c:projects', []); e.fire('c:sessions', SESSIONS);
  assert.match(e.el('project').innerHTML, /value="other" selected/);
  e.fire('c:projects', PROJECTS);
  assert.match(e.el('project').innerHTML, /value="p:dispatch-board" selected/);
  assert.match(e.el('session').innerHTML, /^<option value="" selected>All sessions · 1<\/option>/);
  assert.equal(e.el('tab-spec').hidden, false);
  ok('first project push: an Other sessions view the page chose by itself moves to the default project');
}
{
  const e = env({ 'board-view': 'other' });
  await tick();
  e.fire('c:projects', []); e.fire('c:sessions', SESSIONS);
  e.fire('c:projects', PROJECTS);
  assert.match(e.el('project').innerHTML, /value="other" selected/);
  ok('first project push: a saved Other sessions view is kept');
}
{
  const e = env();
  await tick();
  e.fire('c:projects', []); e.fire('c:sessions', SESSIONS);
  e.change('project', 'other');
  e.fire('c:projects', PROJECTS);
  assert.match(e.el('project').innerHTML, /value="other" selected/);
  ok('first project push: Other sessions picked in the picker is kept');
}
console.log(`all ${passed} page checks passed`);
