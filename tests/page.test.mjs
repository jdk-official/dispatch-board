// Checks the page's project picker and session filter, the project Overview, the Agent catalogue tab and the Backlog's
// Later group: runs the inline script from
// site/index.html against a stub DOM and a fake store, fires store snapshots and picker changes, and asserts on
// what the page renders.
//
//     node tests/page.test.mjs
//
// PAGE_HTML=<path> runs the checks against another copy of the page (for example a deliberately broken one);
// without it they read site/index.html.
//
// Node built-ins only (no npm install). Any failed check throws, so the process exits non-zero.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html = fs.readFileSync(process.env.PAGE_HTML || new URL('../site/index.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tabNames = [...html.matchAll(/role="tab" id="tab-(\w+)"/g)].map(m => m[1]);
assert.ok(tabNames.includes('spec') && tabNames.includes('overview'), 'tab buttons found in site/index.html');

// The page catches a tab renderer that throws, draws that tab's error state and only logs the error with
// console.error, so a crashing tab would otherwise pass every check. Every console.error the page makes is
// recorded, and each check fails if one was logged that the test did not ask for with expectErrors.
let pageErrors = [];
console.error = (...args) => pageErrors.push(args);
const noPageErrors = where => assert.equal(pageErrors.length, 0, `unexpected console.error ${where}:\n` +
  pageErrors.map(a => a.map(x => x instanceof Error ? x.stack : String(x)).join(' ')).join('\n'));
// Runs fn and returns the console.error calls it made, instead of counting them as unexpected.
const expectErrors = fn => { const outer = pageErrors; pageErrors = []; try { fn(); return pageErrors; } finally { pageErrors = outer; } };

// A fresh page: each call re-runs the script against new stubs, with localStorage preset to `storage`.
// With offline, the page gets no store, as when the artifact runs without its db capability.
function env(storage = {}, { offline = false } = {}) {
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
  globalThis.claude = { use: async () => offline ? null : db };
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
const ok = m => { noPageErrors(`before "${m}"`); passed++; console.log('ok  ' + m); };

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
// ---- 4. the Agent catalogue tab
const whenStr = iso => new Date(iso).toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' });
const text = h => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const rowOf = (html, key) => { const m = html.match(new RegExp(`<tr data-entry="${reEsc(key)}">([\\s\\S]*?)</tr>`)); assert.ok(m, 'row ' + key); return m[1]; };
// cells: entry, description, uses in the view, last use in the view, projects, all-sessions uses
const cells = row => row.split('<td').slice(1).map(c => text(c.replace(/^[^>]*>/, '')));
const tileOf = (html, label) => { const m = html.match(new RegExp(`<div class="tl">${reEsc(label)}</div><div class="tv">([\\s\\S]*?)</div><div class="ts">([\\s\\S]*?)</div>`)); assert.ok(m, 'tile ' + label); return [text(m[1]), text(m[2])]; };
const groupOf = (html, plugin) => { const m = html.match(new RegExp(`data-plugin="${reEsc(plugin)}"([\\s\\S]*?)</table>`)); assert.ok(m, 'group ' + plugin); return m[1]; };
{
  const T0 = '2026-09-05T08:00:00Z', T1 = '2026-09-06T09:00:00Z', T2 = '2026-09-07T10:00:00Z', T3 = '2026-09-08T11:00:00Z';
  const HOSTILE = 'Hostile <img src=x onerror=alert(1)> **bold** `code`';
  const CATALOGUE = {
    generatedAt: now, source: { marketplacePath: 'M', installedPath: 'I' },
    plugins: [
      { plugin: 'engineering-agents', purpose: 'Engineering doers.', purposeFull: 'Engineering doers. ENG-FULL-TEXT', installed: true, agents: 2, skills: 0 },
      { plugin: 'backlog-delivery', purpose: 'Delivery skills.', purposeFull: 'Delivery skills.', installed: true, agents: 0, skills: 3 },
      { plugin: 'workflow-agents', purpose: 'workflow-agents', purposeFull: '', installed: false, agents: 1, skills: 1 },
    ],
    entries: [
      { id: 'engineering-agents:code-writer', kind: 'agent', plugin: 'engineering-agents', name: 'code-writer', description: 'Writes the smallest change. CW-DESC', installed: true },
      { id: 'engineering-agents:test-writer', kind: 'agent', plugin: 'engineering-agents', name: 'test-writer', description: HOSTILE, installed: true },
      { id: 'backlog-delivery:dup', kind: 'skill', plugin: 'backlog-delivery', name: 'dup', description: 'One of two skills named dup.', installed: true },
      { id: 'backlog-delivery:pbi-plan', kind: 'skill', plugin: 'backlog-delivery', name: 'pbi-plan', description: 'Plans.', installed: true },
      { id: 'backlog-delivery:pbi-review', kind: 'skill', plugin: 'backlog-delivery', name: 'pbi-review', description: 'Reviews.', installed: true },
      { id: 'workflow-agents:orchestrator', kind: 'agent', plugin: 'workflow-agents', name: 'orchestrator', description: 'Coordinates.', installed: false },
      { id: 'workflow-agents:dup', kind: 'skill', plugin: 'workflow-agents', name: 'dup', description: 'The other dup.', installed: false },
    ],
  };
  const CS = [  // newest last, as the store's orderBy('last') returns them
    { id: 'c1', title: 'PC one', project: 'platform-catalogue', last: old, start: old, running: 0, skillUses: { 'backlog-delivery:pbi-plan': { count: 2, last: T1 } } },
    { id: 'c4', title: 'Old parser', project: null, last: old, start: old, running: 0 },  // cached before skillUses existed
    { id: 'c3', title: 'Loose', project: null, last: old, start: old, running: 0, skillUses: { 'backlog-delivery:pbi-review': { count: 1, last: T1 } } },
    { id: 'c2b', title: 'DB two', project: 'dispatch-board', last: old, start: old, running: 0, skillUses: { 'backlog-delivery:pbi-plan': { count: 1, last: T2 } } },
    { id: 'c2', title: 'DB one', project: 'dispatch-board', last: now, start: now, running: 0, skillUses: { 'pbi-review': { count: 1, last: T3 }, dup: { count: 1, last: T3 }, 'artifact-design': { count: 1 } } },
  ];
  const CR = [
    { id: 'k1', session: 'c1', project: 'platform-catalogue', seq: 1, lane: 'cw', kind: 'done', label: 'x', agentType: 'engineering-agents:code-writer', start: T1 },
    { id: 'k0', session: 'c1', project: 'platform-catalogue', seq: 2, lane: 'orch', kind: 'done', label: 'in-line work' },
    { id: 'k2', session: 'c2', project: 'dispatch-board', seq: 1, lane: 'cw', kind: 'done', label: 'x', agentType: 'engineering-agents:code-writer', start: T3 },
    { id: 'k3', session: 'c2b', project: 'dispatch-board', seq: 1, lane: 'cw', kind: 'done', label: 'x', agentType: 'engineering-agents:code-writer', start: T2 },
    { id: 'k4', session: 'c3', project: null, seq: 1, lane: 'plan', kind: 'go', label: 'x', agentType: 'Plan', start: T1 },
    { id: 'k5', session: 'c3', project: null, seq: 2, lane: 'tw', kind: 'done', label: 'x', agentType: 'engineering-agents:test-writer', start: T0 },
  ];

  const i = tabNames.indexOf('catalogue');
  assert.ok(i > 0 && tabNames[i - 1] === 'dispatch' && tabNames[i + 1] === 'usage');
  assert.match(html, /<button role="tab" id="tab-catalogue" aria-controls="panel-catalogue" data-tab="catalogue">Agent catalogue<\/button>/);
  ok('catalogue: the Agent catalogue tab sits straight after Dispatch, before Claude usage');

  const e = env({ 'board-view': 'p:dispatch-board', 'board-tab': 'catalogue' });
  await tick();
  assert.ok(e.subs['d:catalogue/index'], 'catalogue/index is watched');
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', CS); e.fire('c:runs', CR);
  assert.equal(e.selected(), 'catalogue');
  assert.equal(e.el('tab-catalogue').hidden, false);
  assert.match(e.el('panel-catalogue').innerHTML, /<div class="empty">Connecting to the live store…<\/div>/);
  ok('catalogue: until catalogue/index has answered, the tab says it is connecting, not that nothing was exported');
  e.fire('d:catalogue/index', null);
  assert.match(e.el('panel-catalogue').innerHTML, /<div class="empty">The agent catalogue has not been exported yet\.<\/div>/);
  ok('catalogue: before catalogue/index exists, the tab shows the empty state');

  e.fire('d:catalogue/index', CATALOGUE);
  let H = e.el('panel-catalogue').innerHTML;
  assert.deepEqual(tileOf(H, 'Agents used'), ['1 of 3 · 2 in all sessions', '2 installed']);
  assert.deepEqual(tileOf(H, 'Skills used'), ['2 of 4 · 2 in all sessions', '3 installed']);
  assert.equal(tileOf(H, 'Outside the catalogue')[0], '2 · 3 in all sessions');
  ok('catalogue, project view: tiles give the view figure, the all-sessions figure beside it, and K installed');
  assert.ok(H.includes('Usage covers the sessions the board exports: the last 7 days plus every linked session.'));
  ok('catalogue: the coverage caption is shown');

  const order = ['engineering-agents', 'backlog-delivery', 'workflow-agents'].map(p => H.indexOf(`data-plugin="${p}"`));
  assert.ok(order.every(x => x >= 0) && order[0] < order[1] && order[1] < order[2], 'groups in plugins order');
  const eng = groupOf(H, 'engineering-agents'), wf = groupOf(H, 'workflow-agents');
  assert.ok(eng.includes('Engineering doers.') && /<details[^>]*>[\s\S]*ENG-FULL-TEXT[\s\S]*<\/details>/.test(eng));
  assert.ok(wf.includes('not installed') && !eng.includes('not installed'));
  const cw = rowOf(H, 'agent:engineering-agents:code-writer');
  assert.ok(/<details[^>]*>[\s\S]*CW-DESC[\s\S]*<\/details>/.test(cw), 'description expandable');
  assert.ok(cw.includes('<span class="id') && cw.includes('engineering-agents:code-writer'), 'id in the mono face');
  ok('catalogue: one group per plugin in order, purpose with purposeFull expandable, not-installed tag, descriptions expandable');

  assert.deepEqual(cells(cw).slice(2), ['2', whenStr(T3), 'platform-catalogue, dispatch-board', '3']);
  ok('catalogue: uses and last use (latest run start) in the view; projects and uses over all sessions');
  const tw = cells(rowOf(H, 'agent:engineering-agents:test-writer'));
  assert.deepEqual(tw.slice(2), ['never used', '—', 'Other sessions', '1']);
  assert.deepEqual(cells(rowOf(H, 'agent:workflow-agents:orchestrator')).slice(2), ['never used', '—', '—', '0']);
  ok('catalogue: never used in the view; projects include Other sessions for unlinked sessions');

  assert.deepEqual(cells(rowOf(H, 'skill:backlog-delivery:pbi-plan')).slice(2), ['1', whenStr(T2), 'platform-catalogue, dispatch-board', '3']);
  assert.deepEqual(cells(rowOf(H, 'skill:backlog-delivery:pbi-review')).slice(2), ['1', whenStr(T3), 'dispatch-board, Other sessions', '2']);
  assert.equal(cells(rowOf(H, 'skill:backlog-delivery:dup'))[2], 'never used');
  assert.equal(cells(rowOf(H, 'skill:workflow-agents:dup'))[2], 'never used');
  ok('catalogue: a bare Skill id counts toward the one skill of that name, and an ambiguous one toward neither');
  const bd = groupOf(H, 'backlog-delivery');
  assert.ok(bd.indexOf('backlog-delivery:pbi-plan') < bd.indexOf('backlog-delivery:pbi-review') && bd.indexOf('backlog-delivery:pbi-review') < bd.indexOf('backlog-delivery:dup'));
  ok('catalogue: rows sort by uses in the view, then name');

  assert.deepEqual(cells(rowOf(H, 'skill:dup')).slice(2), ['1', whenStr(T3), 'dispatch-board', '1']);
  assert.deepEqual(cells(rowOf(H, 'skill:artifact-design')).slice(2), ['1', '—', 'dispatch-board', '1']);
  assert.deepEqual(cells(rowOf(H, 'agent:Plan')).slice(2), ['never used', '—', 'Other sessions', '1']);
  assert.ok(H.indexOf('data-entry="skill:dup"') > H.indexOf('data-plugin="workflow-agents"'), 'outside panel comes last');
  ok('catalogue: ids outside the catalogue get their own final panel with the same columns');

  assert.ok(H.includes('Hostile &lt;img src=x onerror=alert(1)&gt; **bold** `code`'));
  assert.ok(!H.includes('<img') && !H.includes('<b>bold</b>') && !H.includes('<code>code</code>'));
  ok('catalogue: descriptions are escaped and never rendered as markdown');

  e.change('session', 'c2b');
  H = e.el('panel-catalogue').innerHTML;
  assert.deepEqual(cells(rowOf(H, 'agent:engineering-agents:code-writer')).slice(2), ['1', whenStr(T2), 'platform-catalogue, dispatch-board', '3']);
  assert.equal(cells(rowOf(H, 'skill:backlog-delivery:pbi-review'))[2], 'never used');
  assert.deepEqual(tileOf(H, 'Agents used'), ['1 of 3 · 2 in all sessions', '2 installed']);
  assert.deepEqual(tileOf(H, 'Skills used'), ['1 of 4 · 2 in all sessions', '3 installed']);
  assert.equal(tileOf(H, 'Outside the catalogue')[0], '0 · 3 in all sessions');
  ok('catalogue: the session filter narrows both runs and sessions');

  e.change('project', 'other');
  e.change('session', 'c3');
  assert.equal(e.el('tab-catalogue').hidden, false);
  assert.equal(e.selected(), 'catalogue');
  H = e.el('panel-catalogue').innerHTML;
  assert.deepEqual(cells(rowOf(H, 'agent:engineering-agents:test-writer')).slice(2), ['1', whenStr(T0), 'Other sessions', '1']);
  assert.deepEqual(cells(rowOf(H, 'skill:backlog-delivery:pbi-review')).slice(2), ['1', whenStr(T1), 'dispatch-board, Other sessions', '2']);
  assert.equal(cells(rowOf(H, 'agent:engineering-agents:code-writer'))[2], 'never used');
  assert.deepEqual(tileOf(H, 'Agents used'), ['1 of 3 · 2 in all sessions', '2 installed']);
  assert.deepEqual(tileOf(H, 'Skills used'), ['1 of 4 · 2 in all sessions', '3 installed']);
  assert.deepEqual(cells(rowOf(H, 'agent:Plan')).slice(2), ['1', whenStr(T1), 'Other sessions', '1']);
  ok('catalogue, Other sessions: the tab stays, and follows the chosen session');

  e.change('session', 'c4');
  H = e.el('panel-catalogue').innerHTML;
  assert.equal(tileOf(H, 'Agents used')[0], '0 of 3 · 2 in all sessions');
  assert.equal(tileOf(H, 'Skills used')[0], '0 of 4 · 2 in all sessions');
  assert.equal(tileOf(H, 'Outside the catalogue')[0], '0 · 3 in all sessions');
  CATALOGUE.entries.forEach(x => assert.equal(cells(rowOf(H, x.kind + ':' + x.id))[2], 'never used', x.id));
  ok('catalogue: a session with no uses (and no skillUses field) reads 0, and every entry never used');

  e.fire('d:catalogue/index', null);
  assert.match(e.el('panel-catalogue').innerHTML, /The agent catalogue has not been exported yet\./);
  ok('catalogue: a deleted catalogue/index returns to the empty state');
}

// ---- 5. the catalogue tab while the store is connecting or out of reach
{
  const e = env({ 'board-tab': 'catalogue' });
  await tick();
  const P = () => e.el('panel-catalogue').innerHTML;
  assert.match(P(), /<div class="empty">Connecting to the live store…<\/div>/);
  e.fire('d:catalogue/index', null);
  assert.match(P(), /<div class="empty">Connecting to the live store…<\/div>/);
  ok('catalogue: an absent catalogue/index still reads Connecting while sessions and projects load');
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS);
  assert.match(P(), /<div class="empty">The agent catalogue has not been exported yet\.<\/div>/);
  ok('catalogue: "not exported yet" only once the store has loaded without catalogue/index');
}
{
  const e = env({ 'board-tab': 'catalogue' }, { offline: true });
  await tick();
  assert.match(e.el('panel-catalogue').innerHTML, /<div class="empty">This view cannot reach the live store\.<\/div>/);
  assert.doesNotMatch(e.el('panel-catalogue').innerHTML, /not been exported/);
  ok('catalogue, offline: the tab says the store is out of reach');
}

// ---- 6. store text that names an Object.prototype member
{
  const T = '2026-09-09T12:00:00Z';
  const CAT = {
    generatedAt: now, source: { marketplacePath: 'M', installedPath: 'I' },
    plugins: [{ plugin: 'proto', purpose: 'Proto.', purposeFull: 'Proto.', installed: true, agents: 0, skills: 2 }],
    entries: [
      { id: 'proto:constructor', kind: 'skill', plugin: 'proto', name: 'constructor', description: 'A skill named constructor.', installed: true },
      { id: 'proto:plain', kind: 'skill', plugin: 'proto', name: 'plain', description: 'Plain.', installed: true },
    ],
  };
  // JSON.parse makes "__proto__" an own key, as a store snapshot would; an object literal would set the prototype.
  const uses = JSON.parse(`{"constructor":{"count":2,"last":"${T}"},"hasOwnProperty":{"count":1,"last":"${T}"},"isPrototypeOf":{"count":1},"__proto__":{"count":3}}`);
  const PS = [{ id: 'q1', title: 'Proto', project: 'dispatch-board', last: now, start: now, running: 0, skillUses: uses }];
  const PR = [{ id: 'q9', session: 'q1', project: 'dispatch-board', seq: 1, lane: 'other', kind: 'done', label: 'PROTO RUN', agentType: 'constructor', start: T }];
  const e = env({ 'board-view': 'p:dispatch-board', 'board-tab': 'catalogue' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', PS); e.fire('c:runs', PR); e.fire('c:projectTabs', TABS);
  e.fire('d:catalogue/index', CAT);
  const H = e.el('panel-catalogue').innerHTML;
  assert.deepEqual(cells(rowOf(H, 'skill:proto:constructor')).slice(2), ['2', whenStr(T), 'dispatch-board', '2']);
  assert.equal(cells(rowOf(H, 'skill:proto:plain'))[2], 'never used');
  ok('catalogue: a catalogue skill named "constructor" takes the bare "constructor" uses');
  const outAt = H.indexOf('data-outside');
  for (const [k, n] of [['skill:hasOwnProperty', '1'], ['skill:isPrototypeOf', '1'], ['skill:__proto__', '3'], ['agent:constructor', '1']]) {
    assert.ok(outAt > 0 && H.indexOf(`data-entry="${k}"`) > outAt, k + ' is under Outside the catalogue');
    assert.equal(cells(rowOf(H, k))[2], n, k);
  }
  assert.equal(tileOf(H, 'Outside the catalogue')[0], '4 · 4 in all sessions');
  ok('catalogue: uses named after Object.prototype members with no matching entry go under Outside the catalogue');
  assert.match(e.el('panel-dispatch').innerHTML, /PROTO RUN/);
  assert.match(e.el('panel-spec').innerHTML, /has not been exported/);
  assert.match(e.el('panel-git').innerHTML, /dispatch-board/);
  assert.match(e.el('panel-usage').innerHTML, /DB-ALL/);
  ok('catalogue: the tabs drawn after it still render');
}

// ---- 7. one tab failing leaves the others drawn
{
  const e = env({ 'board-view': 'p:dispatch-board', 'board-tab': 'catalogue' });
  await tick();
  const logged = expectErrors(() => {
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
    e.fire('d:catalogue/index', { generatedAt: now, plugins: [], entries: [null] });  // an entry the tab cannot read
  });
  assert.match(e.el('panel-catalogue').innerHTML, /^<div class="empty">This tab could not be shown from the current data\.<\/div>$/);
  assert.ok(logged.some(a => a.some(x => x instanceof Error)), 'the error is logged with console.error');
  assert.match(e.el('panel-dispatch').innerHTML, /DB write/);
  assert.match(e.el('panel-spec').innerHTML, /has not been exported/);
  assert.match(e.el('panel-git').innerHTML, /dispatch-board/);
  assert.match(e.el('panel-usage').innerHTML, /DB-ALL/);
  ok('a tab that throws shows its own empty state and is logged; the other tabs still render');
}

// ---- 8. the project Overview
{
  const e = env({ 'board-view': 'p:platform-catalogue' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  const H = e.el('panel-overview').innerHTML;
  assert.deepEqual(tileOf(H, 'Work items built'), ['1 / 1', '0 with open conditions · 0 partly built']);
  assert.deepEqual(tileOf(H, 'Agent runs'), ['2', '1 review verdicts · 0.00M tokens']);
  assert.match(H, /<span class="id">PBI-001<\/span>/);
  ok('project Overview: the summary tiles and backlog cells come from the project\'s backlog and runs');
}

// ---- 9. the Backlog's Later group: future-iteration ideas from the spec, never counted as work items
{
  const HOSTILE_TITLE = 'Evil <img src=x onerror=alert(1)> title';
  const LATER = [
    { title: 'Phone notifications', description: 'a review returns **NO-GO** or `run` is cut off' },
    { title: HOSTILE_TITLE, description: '<script>alert(2)</script> "quoted"' },
    { title: 'A plain idea with no bold span', description: '' },
  ];
  const PBIS = [
    { id: 'PBI-001', title: 't', dependsOn: '—', state: 'done', group: 'g', risk: 'Low' },
    { id: 'PBI-002', title: 'u', dependsOn: 'PBI-001', state: 'conditions', group: 'g', risk: 'Low', open: 'fix it' },
  ];
  const withBacklog = backlog => TABS.map(t => t.id === 'platform-catalogue.backlog' ? { ...t, pbis: PBIS, ...backlog } : t);
  const load = async backlog => {
    const e = env({ 'board-view': 'p:platform-catalogue' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', withBacklog(backlog));
    return e;
  };
  const e = await load({ later: LATER }), B = e.el('panel-backlog').innerHTML;
  const later = (B.match(/<div class="panel" data-later[\s\S]*$/) || [''])[0];
  assert.ok(later, 'the Later panel is drawn');
  assert.ok(B.indexOf('data-later') > B.indexOf('<h3>Work items</h3>'), 'Later sits below the work items');
  assert.equal((later.match(/<div class="tile idea">/g) || []).length, 3);
  assert.match(later, /<h3>Later<\/h3>/);
  assert.ok(text(later).includes('Phone notifications a review returns NO-GO or run is cut off'));
  assert.ok(later.includes('<b>NO-GO</b>') && later.includes('<code>run</code>'), 'repo text keeps bold and code spans');
  ok('backlog: later items render as a separate Later group of idea cards below the work items');

  assert.ok(later.includes('Evil &lt;img src=x onerror=alert(1)&gt; title'));
  assert.ok(later.includes('&lt;script&gt;alert(2)&lt;/script&gt; &quot;quoted&quot;'));
  assert.ok(!later.includes('<img') && !later.includes('<script'));
  ok('backlog: Later titles and descriptions are escaped');

  assert.ok(!/--tone|--human|--go|--changes|--nogo|--live|class="tag/.test(later), 'idea cards carry no state or human colour');
  ok('backlog: idea cards are neutral');

  const plain = await load({}), P = plain.el('panel-backlog').innerHTML;
  assert.deepEqual(tileOf(B, 'Built and reviewed'), tileOf(P, 'Built and reviewed'));
  assert.deepEqual(tileOf(B, 'Built and reviewed'), ['1', 'of 2 work items']);
  assert.deepEqual(tileOf(B, 'Not started'), tileOf(P, 'Not started'));
  assert.match(B, /<h3>Work items<\/h3><span class="faint">2<\/span>/);
  assert.match(B, /Dependency graph of 2 work items/);
  assert.equal(e.el('c-backlog').textContent, plain.el('c-backlog').textContent);
  const O = e.el('panel-overview').innerHTML;
  assert.equal(O, plain.el('panel-overview').innerHTML, 'the Overview is unchanged by later items');
  assert.deepEqual(tileOf(O, 'Work items built'), ['2 / 2', '1 with open conditions · 0 partly built']);
  assert.equal((O.match(/<div class="cell /g) || []).length, 2);
  assert.ok(!O.includes('Phone notifications') && !O.includes('Evil'), 'no later item in the cells or Needs attention');
  ok('backlog: later items are left out of the PBI totals, the Overview tile, the backlog cells and Needs attention');

  assert.doesNotMatch(P, /data-later|<h3>Later<\/h3>/);
  for (const bad of [{ later: [] }, { later: null }, { later: 'x' }, { later: [null, 3] }]) {
    const H = (await load(bad)).el('panel-backlog').innerHTML;
    assert.doesNotMatch(H, /data-later/, JSON.stringify(bad));
    assert.match(H, /<h3>Work items<\/h3>/, JSON.stringify(bad));
  }
  ok('backlog: no Later group without later items (a spec without the heading, or an older export)');
}
noPageErrors('after the last check');
console.log(`all ${passed} page checks passed`);
