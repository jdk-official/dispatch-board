// Checks the page's project picker and session filter, the project Overview, the Agent catalogue tab, the Backlog's
// Later group and the pull requests (the GitHub tab's panel, the Overview's awaiting-merge items): runs the inline script from
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

// The path the page was loaded from, as the failure messages and stack traces name it.
const PAGE_PATH = process.env.PAGE_HTML || 'site/index.html';
const html = fs.readFileSync(process.env.PAGE_HTML || new URL('../site/index.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tabNames = [...html.matchAll(/role="tab" id="tab-(\w+)"/g)].map(m => m[1]);
assert.ok(tabNames.includes('spec') && tabNames.includes('overview'), 'tab buttons found in ' + PAGE_PATH);

// The page catches a tab renderer that throws, draws that tab's error state and only logs the error with
// console.error, so a crashing tab would otherwise pass every check. Every console.error the page makes is
// recorded, and each check fails if one was logged that the test did not ask for with expectErrors.
let pageErrors = [];
console.error = (...args) => pageErrors.push(args);
const formatErrors = list => list.map(a => a.map(x => x instanceof Error ? x.stack : String(x)).join(' ')).join('\n');
const noPageErrors = where => assert.equal(pageErrors.length, 0, `unexpected console.error ${where}:\n` + formatErrors(pageErrors));
// A check that fails on its own assertion never reaches noPageErrors, so the error the page logged (often the
// reason) would go unseen. console.error is taken over above, hence the direct write to stderr.
process.on('exit', code => {
  if (code !== 0 && pageErrors.length) process.stderr.write(`console.error calls the page made that no check expected:\n${formatErrors(pageErrors)}\n`);
});
// Runs fn and returns the console.error calls it made, instead of counting them as unexpected.
const expectErrors = fn => { const outer = pageErrors; pageErrors = []; try { fn(); return pageErrors; } finally { pageErrors = outer; } };

// Every store path any page subscribed to, across every env(): the page must never go back to a retired tabs/* document.
const everySub = new Set();
// A fresh page: each call re-runs the script against new stubs, with localStorage preset to `storage`.
// With offline, the page gets no store, as when the artifact runs without its db capability. claude, when given,
// builds the page's window.claude from the fake store, for a store that is absent, refuses to open or opens late.
function env(storage = {}, { offline = false, claude } = {}) {
  const els = {}, doc = { activeElement: null, appended: [] };
  const el = id => els[id] || (els[id] = {
    id, innerHTML: '', textContent: '', className: '', hidden: false, disabled: false, value: '', tabIndex: 0, dataset: {}, attrs: {}, listeners: {},
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
    addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
    focus() { doc.activeElement = this; }, querySelectorAll() { return []; }, querySelector() { return null; },
  });
  const tabs = tabNames.map(n => { const t = el('tab-' + n); t.dataset.tab = n; return t; });
  const subs = {};
  const db = {
    collection: name => ({ orderBy() { return this; }, onSnapshot(cb) { subs['c:' + name] = cb; everySub.add('c:' + name); } }),
    doc: path => ({ onSnapshot(cb) { subs['d:' + path] = cb; everySub.add('d:' + path); } }),
  };
  const store = new Map(Object.entries(storage));
  Object.assign(doc, {
    getElementById: el, querySelectorAll: () => tabs, addEventListener() {},
    createElement: tag => ({ tagName: tag.toUpperCase() }), head: { appendChild: n => { doc.appended.push(n); return n; } },
  });
  globalThis.document = doc;
  globalThis.window = globalThis;
  globalThis.localStorage = { getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)) };
  globalThis.claude = claude ? claude(db) : { use: async () => offline ? null : db };
  globalThis.scrollTo = () => {};
  // The page's timers are recorded rather than started; a check runs them with timers.forEach(f => f()).
  const timers = [];
  globalThis.setInterval = f => { timers.push(f); return 0; };
  vm.runInThisContext(script, { filename: PAGE_PATH + ' <script>' });
  const fire = (key, docs) => subs[key](key.startsWith('d:') ? { exists: !!docs, data: () => docs } :
    { docs: docs.map(d => ({ id: d.id, exists: true, data: () => { const { id, ...rest } = d; return rest; } })) });
  const change = (id, value) => { const e = el(id); e.value = value; e.listeners.change.forEach(f => f({ target: e })); };
  const selected = () => tabs.find(t => t.attrs['aria-selected'] === 'true').dataset.tab;
  return { el, subs, fire, change, selected, store, doc, timers };
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
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  noPageErrors('drawing every tab before the unreadable catalogue arrives');
  // Only the catalogue snapshot may log, and only the catalogue's own error: a second tab failing on the same data must fail here.
  const logged = expectErrors(() => e.fire('d:catalogue/index', { generatedAt: now, plugins: [], entries: [null] }));  // an entry the tab cannot read
  assert.deepEqual(logged.map(a => a[0]), ['Board: the catalogue could not be drawn'], 'exactly one error, the catalogue\'s');
  assert.ok(logged[0][1] instanceof Error, 'the error is logged with console.error');
  assert.match(e.el('panel-catalogue').innerHTML, /^<div class="empty">This tab could not be shown from the current data\.<\/div>$/);
  assert.doesNotMatch(e.el('panel-overview').innerHTML, /could not be shown/, 'the Overview shows no error state');
  assert.match(e.el('panel-overview').innerHTML, /<div class="tiles">/);
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
  assert.deepEqual(tileOf(H, 'Agent runs'), ['2', '1 review verdicts · 0.00M reported tokens']);
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

// ---- 10. pull requests: the GitHub tab's panel and the Overview's awaiting-merge items
{
  const PT = '2026-09-10T09:30:00Z';
  const HOSTILE_PR = 'Evil <img src=x onerror=alert(1)> **bold** `code`';
  const GH = 'https://github.com/o/dispatch-board/pull/';
  const LINK = u => `href="${u}" target="_blank" rel="noopener noreferrer"`;
  const PULLS = [
    { number: 12, title: 'Show PR links', state: 'OPEN', url: GH + '12', branch: 'pbi/pr-links', updatedAt: PT },
    { number: 11, title: HOSTILE_PR, state: 'OPEN', url: 'javascript:alert(1)', branch: 'evil<b>x', updatedAt: PT },
    { number: 10, title: 'Merged one', state: 'MERGED', url: GH + '10', branch: 'pbi/merged', updatedAt: old },
    { number: 9, title: 'Closed one', state: 'CLOSED', url: GH + '9', branch: 'pbi/closed', updatedAt: old },
    { number: 8, title: 'Quoted url', state: 'OPEN', url: GH + '8" onmouseover="alert(1)', branch: 'pbi/q', updatedAt: PT },
  ];
  const withGit = git => TABS.map(t => t.id === 'dispatch-board.git' ? { ...t, ...git } : t);
  const load = async git => {
    const e = env({ 'board-view': 'p:dispatch-board' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', withGit(git));
    return e;
  };
  const prPanel = G => { const m = G.match(/<div class="panel" data-pulls[\s\S]*$/); assert.ok(m, 'the Pull requests panel is drawn'); return m[0]; };
  const prRow = (P, n) => { const m = P.match(new RegExp(`<tr data-pr="${n}">([\\s\\S]*?)</tr>`)); assert.ok(m, 'row #' + n); return m[1]; };
  const attItems = O => ((O.match(/<ul class="att">([\s\S]*?)<\/ul>/) || [])[1] || '').split('<li').slice(1);

  const e = await load({ pulls: PULLS });
  const G = e.el('panel-git').innerHTML, P = prPanel(G);
  assert.match(P, /<h3>Pull requests<\/h3>/);
  assert.equal((P.match(/<tr data-pr=/g) || []).length, 5);
  const r12 = prRow(P, 12);
  assert.ok(r12.includes(`<a class="id" ${LINK(GH + '12')}>#12</a>`), 'the number links to the PR, in the mono id style');
  assert.ok(r12.includes(`<a ${LINK(GH + '12')}>Show PR links</a>`), 'the title links to the PR');
  assert.ok(r12.includes('<span class="tag open">Open</span>'));
  assert.ok(r12.includes('<td>pbi/pr-links</td>'), 'the branch in the sans face, not the mono id style');
  assert.ok(text(r12).includes(whenStr(PT)), 'the updated time');
  assert.ok(prRow(P, 10).includes('<span class="tag merged">Merged</span>'));
  assert.ok(prRow(P, 9).includes('<span class="tag closed">Closed</span>'));
  assert.ok(!/--human|tag human/.test(P), 'the panel never uses the human colour');
  ok('pulls: the GitHub tab lists each PR with a linked number and title, a state tag, the branch and the updated time');

  assert.ok(P.includes('Evil &lt;img src=x onerror=alert(1)&gt; **bold** `code`'));
  assert.ok(P.includes('evil&lt;b&gt;x'));
  assert.ok(!P.includes('<img') && !P.includes('<b>bold</b>') && !P.includes('<code>code</code>') && !P.includes('<b>x'));
  ok('pulls: titles and branches are escaped and never rendered as markdown');

  const r11 = prRow(P, 11);
  assert.ok(!r11.includes('<a') && !r11.includes('href'), 'a javascript: URL is not a link');
  assert.ok(r11.includes('javascript:alert(1)') && r11.includes('<span class="id">#11</span>'), 'it is shown as text');
  const r8 = prRow(P, 8);
  assert.ok(r8.includes(`href="${GH}8&quot; onmouseover=&quot;alert(1)"`) && !G.includes('" onmouseover'), 'a quote in a URL cannot leave the attribute');
  assert.ok(!/href="(?!https:\/\/github\.com\/)/.test(G), 'every link on the GitHub tab goes to github.com');
  ok('pulls: only https://github.com/ URLs are links; anything else is escaped text');

  const O = e.el('panel-overview').innerHTML, items = attItems(O), pr = items.filter(li => li.includes('awaiting your merge'));
  assert.deepEqual(pr.map(li => text('<li' + li).match(/PR #\d+ awaiting your merge/)[0]),
    ['PR #12 awaiting your merge', 'PR #11 awaiting your merge', 'PR #8 awaiting your merge']);
  assert.ok(!/PR #(10|9)\b/.test(O), 'merged and closed PRs are not in Needs attention');
  const a12 = pr[0];
  assert.ok(a12.includes('style="--t:var(--human)"'), 'the awaiting-merge item uses the human tone');
  assert.ok(a12.includes(`<a class="linkbtn" ${LINK(GH + '12')}>`), 'it links to the PR');
  assert.ok(a12.includes('Show PR links'));
  assert.ok(!pr[1].includes('<a') && !pr[1].includes('href'), 'a javascript: URL gets no link in Needs attention either');
  assert.ok(pr[1].includes('Evil &lt;img src=x onerror=alert(1)&gt; **bold** `code`') && !O.includes('<img') && !O.includes('<b>bold</b>'));
  assert.ok(!/href="(?!https:\/\/github\.com\/)/.test(O) && !O.includes('" onmouseover'));
  assert.match(O, new RegExp(`<h3>Needs attention</h3><span class="count">${items.length}</span>`));
  ok('pulls: each open PR is "PR #n awaiting your merge" in Needs attention, in the human tone, linked and escaped');

  for (const [git, why] of [[{}, 'no pulls field'], [{ pulls: null }, 'pulls null']]) {
    const q = await load(git), GP = prPanel(q.el('panel-git').innerHTML);
    assert.match(GP, /Pull requests are not available/, why);
    assert.ok(!GP.includes('<table'), why + ': no empty table');
    assert.doesNotMatch(q.el('panel-overview').innerHTML, /awaiting your merge/, why);
  }
  ok('pulls: without pulls, the panel says pull requests are not available and Needs attention has no PR items');

  const none = await load({ pulls: PULLS.filter(x => x.state !== 'OPEN') });
  assert.doesNotMatch(none.el('panel-overview').innerHTML, /awaiting your merge/);
  const empty = prPanel((await load({ pulls: [] })).el('panel-git').innerHTML);
  assert.match(empty, /No pull requests yet/);
  assert.ok(!empty.includes('<table'));
  ok('pulls: no open PR means no awaiting-merge item; an empty list says there are none yet');

  // Each of these only looks like GitHub: a host that merely begins with github.com, plain http, and
  // userinfo that puts github.com before an @ so the real host is evil.example.
  const LOOKALIKE = [
    { number: 21, title: 'Lookalike host', state: 'OPEN', url: 'https://github.com.evil.example/o/r/pull/1', branch: 'pbi/a', updatedAt: PT },
    { number: 22, title: 'Plain http', state: 'OPEN', url: 'http://github.com/o/r/pull/2', branch: 'pbi/b', updatedAt: PT },
    { number: 23, title: 'Userinfo', state: 'OPEN', url: 'https://github.com@evil.example/x', branch: 'pbi/c', updatedAt: PT },
  ];
  const look = await load({ pulls: LOOKALIKE });
  const LP = prPanel(look.el('panel-git').innerHTML);
  const lookAtt = attItems(look.el('panel-overview').innerHTML).filter(li => li.includes('awaiting your merge'));
  for (const x of LOOKALIKE) {
    const row = prRow(LP, x.number);
    assert.ok(!row.includes('<a') && !row.includes('href'), `${x.url} is not a link in the Pull requests panel`);
    assert.ok(row.includes(`<span class="id">#${x.number}</span>`) && row.includes(`<div class="sub">${x.url}</div>`),
      `${x.url} is shown as text in the Pull requests panel`);
    const li = lookAtt.find(l => text('<li' + l).includes(`PR #${x.number} awaiting your merge`));
    assert.ok(li, `PR #${x.number} is in Needs attention`);
    assert.ok(!li.includes('<a') && !li.includes('href'), `${x.url} is not a link in Needs attention`);
    assert.ok(li.includes('<button class="linkbtn" data-go="git">View</button>'), `PR #${x.number} points at the GitHub tab instead`);
  }
  assert.ok(!LP.includes('href'), 'no lookalike URL becomes a link anywhere in the panel');
  ok('pulls: lookalike hosts, plain http and userinfo tricks are text, not links, in the panel and in Needs attention');

  // State names that are members every object inherits must not be taken for a known state.
  const INHERITED = ['constructor', '__proto__', 'toString', 'hasOwnProperty', '<b>DRAFT'];
  const inh = await load({ pulls: INHERITED.map((state, i) =>
    ({ number: 30 + i, title: 'State ' + i, state, url: GH + (30 + i), branch: 'pbi/s', updatedAt: PT })) });
  noPageErrors('rendering pull requests whose state is an inherited object member');
  const IP = prPanel(inh.el('panel-git').innerHTML);
  assert.equal((IP.match(/<tr data-pr=/g) || []).length, INHERITED.length, 'every row is drawn');
  INHERITED.forEach((state, i) => assert.ok(prRow(IP, 30 + i).includes(`<span class="tag muted">${state.replace('<', '&lt;').replace('>', '&gt;')}</span>`),
    `state ${state} is the muted tag with the raw state, escaped`));
  assert.doesNotMatch(inh.el('panel-overview').innerHTML, /awaiting your merge/, 'none of them is an open PR');
  ok('pulls: an unknown state, even one named like an inherited object member, is a muted tag with the escaped raw state');
}

// ---- 11. the usage limit forecast: an estimate from the recorded limit hits, never a meter
{
  const NO_HIT = 'no forecast: no limit hit recorded', UNTIMED = 'no forecast: too little timing data to estimate';
  const PASSED = ' · passed with no hit since';
  // Hourly usage (UTC) from `first` for n hours: one unit in every hour except the hours of the day listed in idle.
  const series = (first, n, idle = []) => Array.from({ length: n }, (_, i) => {
    const hour = new Date(Date.parse(first + ':00:00Z') + i * 3600e3).toISOString().slice(0, 13);
    return { hour, main: idle.includes(Number(hour.slice(11))) ? 0 : 1, sub: 0 };
  });
  const withLimits = (u, limits, hourly) => ({ ...u, limits, hourly });

  // Gaps of 1 h, 1 h and 7 h, so the mean (3 h) differs from the median (1 h). Stored out of time order, so the
  // estimate cannot depend on the order the store returns. Every hour from 00:00 to 13:00 has usage.
  const SEVERAL = [
    { firstAt: '2099-01-01T12:00:00Z', refused: 2, type: 'five_hour', resetsAt: '2099-01-01T13:00:00Z' },
    { firstAt: '2099-01-01T01:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-01T02:00:00Z' },
    { firstAt: '2099-01-01T03:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-01T05:00:00Z' },
  ];
  const SEVERAL_H = series('2099-01-01T00', 14);
  // By hand: the 01:00 hit has no reset before it, so it is timed from the first hour with usage, 00:00: 1 h.
  // The 03:00 hit follows the 02:00 reset, and the 02:00 hour has usage: 1 h. The 12:00 hit follows the 05:00
  // reset, and the 05:00 hour has usage: 7 h. The mean, (1 + 1 + 7) / 3 = 3 h, added to the latest reset (13:00,
  // the latest hit's own) gives 16:00. The median, 1 h, would give 14:00.
  const SEVERAL_AT = '2099-01-01T16:00:00Z';

  const ONE = [{ firstAt: '2026-09-10T11:30:00Z', refused: 1, type: 'five_hour', resetsAt: '2026-09-10T13:00:00Z' }];
  const ONE_H = series('2026-09-10T08', 2);
  // By hand: no reset before the hit and the first hour with usage is 08:00, so the hit came 3 h 30 min after
  // work resumed; added to its 13:00 reset, 16:30. That time is in the past, so the tile says it passed with no hit since.
  const ONE_AT = '2026-09-10T16:30:00Z';

  // Idle hours after a reset do not count. Usage only in the hours 00, 01, 09, 10, 12 and 13; the 09:00 hour's
  // usage is all by agents, which counts as usage too.
  const IDLE = [
    { firstAt: '2099-01-02T10:30:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-02T12:20:00Z' },
    { firstAt: '2099-01-02T01:30:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-02T03:20:00Z' },
    { firstAt: '2099-01-02T13:50:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-02T15:00:00Z' },
  ];
  const IDLE_H = series('2099-01-02T00', 16, [2, 3, 4, 5, 6, 7, 8, 11, 14, 15]).map(h => h.hour.endsWith('T09') ? { ...h, main: 0, sub: 1 } : h);
  // By hand: the 01:30 hit has no reset before it; the first hour with usage is 00:00: 1 h 30 min. The 10:30 hit's
  // latest reset before it is 03:20; the hours 03 to 08 are idle and work resumed at 09:00: 1 h 30 min. The 13:50
  // hit's latest reset before it is 12:20; the 12:00 hour has usage but starts before the reset, so the later of
  // the two, 12:20: 1 h 30 min. The mean, 1 h 30 min, added to the latest reset, 15:00, gives 16:30.
  // Timed from the resets instead, the gaps would be 1 h 30 min, 7 h 10 min and 1 h 30 min: a mean of 3 h 23 min
  // 20 s, giving 18:23:20. Timing the last hit from the 12:00 hour start rather than the 12:20 reset would make its
  // gap 1 h 50 min and the answer 16:36:40.
  const IDLE_AT = '2099-01-02T16:30:00Z', IDLE_FROM_RESETS = '2099-01-02T18:23:20Z', IDLE_FROM_HOUR = '2099-01-02T16:36:40Z';

  // One hit has nothing before it: the 03:00 hit has no reset before it and the recorded usage starts at 05:00.
  // Usage only in the hours 05 to 08.
  const MIXED = [
    { firstAt: '2099-01-03T03:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-03T04:00:00Z' },
    { firstAt: '2099-01-03T08:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-03T09:00:00Z' },
    { firstAt: '2099-01-03T10:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-03T11:00:00Z' },
  ];
  const MIXED_H = series('2099-01-03T05', 4);
  // By hand: the 03:00 hit gives no gap. The 08:00 hit's latest reset before it is 04:00, and the first hour with
  // usage after that is 05:00: 3 h. The 10:00 hit's latest reset before it is 09:00, and the recorded usage ends
  // with the 08:00 hour, so it is timed from the reset: 1 h. The mean of the 2 gaps, 2 h, added to the latest
  // reset, 11:00, gives 13:00, from 2 of the 3 recorded hits.
  const MIXED_AT = '2099-01-03T13:00:00Z';

  // The latest hit has no reset time. Usage in every hour from 00:00 to 06:00.
  const NORESET = [
    { firstAt: '2099-01-04T06:00:00Z', refused: 1, type: 'five_hour', resetsAt: null },
    { firstAt: '2099-01-04T02:00:00Z', refused: 1, type: 'five_hour', resetsAt: '2099-01-04T03:00:00Z' },
  ];
  const NORESET_H = series('2099-01-04T00', 7);
  // By hand: the 02:00 hit has no reset before it; the first hour with usage is 00:00: 2 h. The 06:00 hit's latest
  // reset before it is 03:00, whose hour has usage: 3 h. The mean is 2 h 30 min, but the latest hit's reset is not
  // recorded, so there is nothing to add it to: "2 h 30 min after reset", not a time. Added to the 06:00 hit
  // itself, it would give 08:30, before that limit could have reset.

  const FP = [
    { ...PROJECTS[0], usage: withLimits(PROJECTS[0].usage, SEVERAL, SEVERAL_H) },
    { ...PROJECTS[1] },
  ];
  const FS = SESSIONS.map(s => s.id === 's1' ? { ...s, usage: withLimits(s.usage, ONE, ONE_H) }
    : s.id === 's4' ? { ...s, usage: withLimits(s.usage, SEVERAL, SEVERAL_H) } : s);
  const tileHtml = (H, label) => { const m = H.match(new RegExp(`<div class="tile[^"]*" style="--tone:([^"]*)"><div class="tl">${reEsc(label)}</div>`)); assert.ok(m, 'tile ' + label); return m[1]; };
  const forecast = e => [tileOf(e.el('panel-usage').innerHTML, 'Next limit hit'), tileOf(e.el('panel-overview').innerHTML, 'Next limit hit')];
  const noteOf = e => { const m = e.el('panel-usage').innerHTML.match(/<div class="pb faint" data-forecast[^>]*>([\s\S]*?)<\/div>/); assert.ok(m, 'the usage tab explains the forecast'); return text(m[1]); };

  const e = env({ 'board-view': 'p:platform-catalogue' });
  await tick();
  e.fire('c:projects', FP); e.fire('c:sessions', FS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  const [u, o] = forecast(e);
  assert.deepEqual(u, [whenStr(SEVERAL_AT), 'estimate from 3 limit hits']);
  assert.deepEqual(o, u, 'the Overview tile matches the usage tab');
  assert.equal(tileOf(e.el('panel-usage').innerHTML, 'Limit hits')[0], '3');
  ok('forecast, project view: skewed gaps give the mean, added to the latest reset, labelled an estimate, on the usage tab and the Overview');

  const note = noteOf(e);
  assert.match(note, /^Next limit hit is an estimate from 3 limit hits: /);
  assert.match(note, /from when work resumed after a reset/);
  assert.match(note, /added to the latest reset/);
  assert.match(note, /not a plan meter/);
  for (const H of [e.el('panel-usage').innerHTML, e.el('panel-overview').innerHTML]) {
    const tone = tileHtml(H, 'Next limit hit');
    assert.ok(tone.startsWith('var(--') && tone !== 'var(--human)', 'the forecast tile uses a token other than --human: ' + tone);
  }
  ok('forecast: the usage tab says how the estimate is derived and that it is not a meter; the tile never uses --human');

  e.change('session', 's1');
  const [su, so] = forecast(e);
  assert.deepEqual(su, [whenStr(ONE_AT), 'estimate from 1 limit hit' + PASSED]);
  assert.deepEqual(so, su);
  ok('forecast, session filter: one hit gives the hand-computed time from that session\'s own usage, marked as passed');

  e.change('project', 'p:dispatch-board');
  assert.deepEqual(forecast(e), [['—', NO_HIT], ['—', NO_HIT]]);
  assert.match(noteOf(e), /^No forecast until a limit hit is recorded\. The estimate is /);
  ok('forecast, project view with no limit hit: "no forecast: no limit hit recorded" on the usage tab and the Overview');

  e.change('project', 'other');
  e.change('session', 's3');
  assert.deepEqual(forecast(e), [['—', NO_HIT], ['—', NO_HIT]]);
  e.change('session', 's4');
  assert.deepEqual(forecast(e)[0], [whenStr(SEVERAL_AT), 'estimate from 3 limit hits']);
  assert.deepEqual(forecast(e)[1], forecast(e)[0]);
  ok('forecast, Other sessions: each session\'s own limit hits, or none');

  const load = async usage => {
    const q = env({ 'board-view': 'p:platform-catalogue' });
    await tick();
    q.fire('c:projects', [{ ...PROJECTS[0], usage }, PROJECTS[1]]); q.fire('c:sessions', SESSIONS); q.fire('c:runs', RUNS); q.fire('c:projectTabs', TABS);
    return q;
  };

  const qi = await load(withLimits(PROJECTS[0].usage, IDLE, IDLE_H));
  assert.deepEqual(forecast(qi), [[whenStr(IDLE_AT), 'estimate from 3 limit hits'], [whenStr(IDLE_AT), 'estimate from 3 limit hits']]);
  for (const other of [IDLE_FROM_RESETS, IDLE_FROM_HOUR]) assert.notEqual(whenStr(other), whenStr(IDLE_AT), 'the fixture tells the methods apart');
  ok('forecast: idle hours after a reset do not count; each hit is timed from the later of its reset and the first hour with usage');

  const qm = await load(withLimits(PROJECTS[0].usage, MIXED, MIXED_H));
  const MIXED_FROM = 'estimate from 2 of the 3 recorded limit hits';
  assert.deepEqual(forecast(qm), [[whenStr(MIXED_AT), MIXED_FROM], [whenStr(MIXED_AT), MIXED_FROM]]);
  assert.equal(tileOf(qm.el('panel-usage').innerHTML, 'Limit hits')[0], '3');
  assert.match(noteOf(qm), /^Next limit hit is an estimate from 2 of the 3 recorded limit hits: /);
  ok('forecast: a hit with nothing before it adds no gap, and the tile and note say "from 2 of the 3 recorded limit hits"');

  const qn = await load(withLimits(PROJECTS[0].usage, NORESET, NORESET_H));
  const NORESET_TILE = ['2 h 30 min after reset', 'estimate from 2 limit hits · reset time of the latest hit not recorded'];
  assert.deepEqual(forecast(qn), [NORESET_TILE, NORESET_TILE]);
  assert.match(noteOf(qn), /^Next limit hit is an estimate from 2 limit hits\. The reset time of the latest hit is not recorded/);
  ok('forecast: when the latest hit has no reset time, the estimate is a time after that reset, never the mean added to the hit');

  const qa = await load(undefined);
  assert.deepEqual(tileOf(qa.el('panel-overview').innerHTML, 'Claude usage'), ['—', 'not exported yet']);
  assert.deepEqual(tileOf(qa.el('panel-overview').innerHTML, 'Next limit hit'), ['—', 'no forecast: usage not exported yet']);
  ok('forecast: with no usage exported, the Overview says "no forecast: usage not exported yet", not that no hit was recorded');

  // The store may not change for hours while the board sits idle, so the minute timer has to add the passed marker.
  const qt = await load(withLimits(PROJECTS[0].usage, IDLE, IDLE_H));
  const realNow = Date.now;
  try {
    assert.equal(forecast(qt)[0][1], 'estimate from 3 limit hits');
    qt.el('panel-usage').innerHTML = 'untouched';
    qt.timers.forEach(f => f());
    assert.equal(qt.el('panel-usage').innerHTML, 'untouched', 'no redraw while the forecast is still ahead');
    Date.now = () => Date.parse('2099-01-02T17:00:00Z');
    qt.timers.forEach(f => f());
    assert.deepEqual(forecast(qt), [[whenStr(IDLE_AT), 'estimate from 3 limit hits' + PASSED], [whenStr(IDLE_AT), 'estimate from 3 limit hits' + PASSED]]);
    qt.el('panel-usage').innerHTML = 'untouched';
    qt.timers.forEach(f => f());
    assert.equal(qt.el('panel-usage').innerHTML, 'untouched', 'redrawn once when the forecast passes, not every minute');
  } finally { Date.now = realNow; }
  noPageErrors('running the minute timer');
  ok('forecast: on an idle board the minute timer marks the forecast as passed once its time has gone by');

  for (const bad of ['x', 7, {}, null, { firstAt: SEVERAL_AT }, [null, 3, 'x', [], [SEVERAL[0]]]]) {
    const q = await load({ ...PROJECTS[0].usage, limits: bad });
    noPageErrors('rendering usage.limits = ' + JSON.stringify(bad));
    assert.deepEqual(forecast(q), [['—', NO_HIT], ['—', NO_HIT]], JSON.stringify(bad));
    assert.equal(tileOf(q.el('panel-usage').innerHTML, 'Limit hits')[0], '0', JSON.stringify(bad));
    assert.doesNotMatch(q.el('panel-usage').innerHTML, /could not be shown/, JSON.stringify(bad));
    q.timers.forEach(f => f());
    noPageErrors('the minute timer with usage.limits = ' + JSON.stringify(bad));
  }
  for (const [usage, why] of [
    [{ ...PROJECTS[0].usage, limits: [{ firstAt: 'not a date', resetsAt: 'nope', refused: '<b>x' }, { firstAt: 12345 }] }, 'hits without a readable time'],
    [{ ...PROJECTS[0].usage, limits: ONE, hourly: [] }, 'a hit with no recorded usage or reset before it'],
  ]) {
    const q = await load(usage);
    noPageErrors('rendering ' + why);
    assert.deepEqual(forecast(q), [['—', UNTIMED], ['—', UNTIMED]], why);
    assert.match(noteOf(q), /^No forecast: no limit hit has both a readable time and a reset or recorded usage before it\. /, why);
    assert.doesNotMatch(q.el('panel-usage').innerHTML, /could not be shown|<b>x/, why);
    q.timers.forEach(f => f());
    noPageErrors('the minute timer with ' + why);
  }
  ok('forecast: malformed usage.limits shows no forecast with the right reason, draws every tab and logs no console.error');

  // A render reads the clock once. Here the first reading is a minute before the forecast time and every later one
  // a minute after it, so a tile that read the clock again would already say the forecast had passed.
  const qc = await load(withLimits(PROJECTS[0].usage, IDLE, IDLE_H));
  const AHEAD = [whenStr(IDLE_AT), 'estimate from 3 limit hits'], BEHIND = [whenStr(IDLE_AT), 'estimate from 3 limit hits' + PASSED];
  try {
    let first = true;
    Date.now = () => { const t = Date.parse(IDLE_AT) + (first ? -60e3 : 60e3); first = false; return t; };
    qc.fire('c:projectTabs', TABS);
    assert.deepEqual(forecast(qc), [AHEAD, AHEAD], 'every forecast tile uses the render\'s one clock reading');
    Date.now = () => Date.parse(IDLE_AT) + 60e3;
    qc.timers.forEach(f => f());
    assert.deepEqual(forecast(qc), [BEHIND, BEHIND], 'the minute timer then finds the drawn tiles out of date and redraws them');
  } finally { Date.now = realNow; }
  noPageErrors('a render whose clock readings straddle the forecast time');
  ok('forecast: a render reads the clock once, for the tiles and for the passed check the minute timer compares against');

  // Store data cannot hold a getter; one stands in for any input that makes the forecast throw.
  const qx = env({ 'board-view': 'p:platform-catalogue' });
  await tick();
  const boom = { ...PROJECTS[0].usage, limits: [{ get firstAt() { throw new Error('an unreadable limit'); } }] };
  const thrown = expectErrors(() => {
    qx.fire('c:projects', [{ ...PROJECTS[0], usage: boom }, PROJECTS[1]]); qx.fire('c:sessions', SESSIONS); qx.fire('c:runs', RUNS); qx.fire('c:projectTabs', TABS);
    qx.timers.forEach(f => f());
  });
  assert.deepEqual([...new Set(thrown.map(a => a[0]))].sort(), ['Board: the overview could not be drawn', 'Board: the usage could not be drawn']);
  assert.match(qx.el('panel-dispatch').innerHTML, /PC write/);
  assert.match(qx.el('panel-spec').innerHTML, /PCSPEC/);
  ok('forecast: a forecast that throws costs only the tabs that draw it; renderAll and the minute timer carry on');

  for (const bad of ['x', 7, {}, null, [null, 3, 'x', []], [null, { hour: '2026-09-10T10', main: 1, sub: 1 }]]) {
    const q = await load({ ...PROJECTS[0].usage, hourly: bad });
    noPageErrors('rendering usage.hourly = ' + JSON.stringify(bad));
    for (const tab of ['overview', 'usage']) {
      assert.doesNotMatch(q.el('panel-' + tab).innerHTML, /could not be shown/, tab + ': ' + JSON.stringify(bad));
      assert.doesNotMatch(q.el('panel-' + tab).innerHTML, /NaN/, tab + ': ' + JSON.stringify(bad));
    }
    if (Array.isArray(bad) && bad.some(h => h && h.hour)) assert.match(q.el('panel-usage').innerHTML, /agents 1<\/title>/, 'the readable hour is still drawn');
    else assert.match(q.el('panel-usage').innerHTML, /No hourly data\./, JSON.stringify(bad));
  }
  ok('usage chart: a non-list usage.hourly, or entries that are not hours, draw no error and log nothing');

  // An hour whose main or sub is missing or not a number is drawn as no usage in that hour, never as NaN coordinates.
  for (const [hourly, why] of [
    [[{ hour: '2026-09-10T10' }, { hour: '2026-09-10T11', main: 'x', sub: null }], 'no hour with a number'],
    [[{ hour: '2026-09-10T10', main: 1, sub: 1 }, { hour: '2026-09-10T11', main: 'x', sub: null }, { hour: '2026-09-10T12', main: {} }], 'one readable hour among them'],
  ]) {
    const q = await load({ ...PROJECTS[0].usage, hourly });
    noPageErrors('rendering usage.hourly with ' + why);
    for (const tab of ['overview', 'usage']) {
      const H = q.el('panel-' + tab).innerHTML;
      assert.doesNotMatch(H, /could not be shown/, tab + ': ' + why);
      assert.match(H, /<svg viewBox="[^"]*" role="img" aria-label="Effective Claude usage per hour/, tab + ': the chart is drawn: ' + why);
      assert.doesNotMatch(H, /NaN/, tab + ': no NaN in the chart markup: ' + why);
    }
  }
  const qh = await load({ ...PROJECTS[0].usage, hourly: [{ hour: '2026-09-10T10', main: 1, sub: 1 }, { hour: '2026-09-10T11', main: 'x', sub: null }] });
  assert.match(qh.el('panel-usage').innerHTML, /agents 1<\/title>/, 'the readable hour keeps its bars');
  ok('usage chart: hours whose main or sub is missing or not a number count as no usage, with no NaN in the chart');
}

// ---- 12. the "Running now" tile follows the header when a session's running window elapses unseen by the store
{
  const T = Date.parse('2026-09-11T09:00:00Z'), realNow = Date.now;
  const QUIET = [{ id: 'w1', title: 'Quiet session', project: null, last: new Date(T).toISOString(), start: new Date(T).toISOString(), running: 0, windowMinutes: 10, usage: usage('W1', 1) }];
  try {
    Date.now = () => T + 5 * 60e3;
    const e = env({ 'board-view': 'other' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', QUIET); e.fire('c:runs', []);
    const running = () => tileOf(e.el('panel-overview').innerHTML, 'Running now');
    assert.equal(e.el('statusText').textContent, 'Active');
    assert.deepEqual(running(), ['0', 'session active']);
    Date.now = () => T + 9 * 60e3;
    e.timers.forEach(f => f());
    assert.equal(e.el('statusText').textContent, 'Active');
    assert.deepEqual(running(), ['0', 'session active']);
    Date.now = () => T + 11 * 60e3;  // the 10-minute window has elapsed, and the store has not changed
    e.timers.forEach(f => f());
    assert.equal(e.el('statusText').textContent, 'Idle');
    assert.deepEqual(running(), ['0', 'session idle'], 'the tile says idle on the same minute tick the header does');
    e.el('panel-overview').innerHTML = 'untouched';
    e.timers.forEach(f => f());
    assert.equal(e.el('panel-overview').innerHTML, 'untouched', 'redrawn once when the state changes, not every minute');
  } finally { Date.now = realNow; }
  ok('running window: when a session\'s running window elapses with no store change, "Running now" says "session idle" on the tick the header says Idle');

  // The running window ends while a render is under way: every clock reading before the given panel is drawn is 1 ms
  // before the end, and every one after it 1 ms past. A render that read the clock again after drawing the tile would
  // record the idle state as drawn while the tile shows active, and the minute timer would then never redraw it.
  const endsWhileDrawn = (e, panel, end) => {
    const P = e.el(panel);
    let markup = P.innerHTML, drawn = false;
    Object.defineProperty(P, 'innerHTML', { get: () => markup, set: v => { markup = v; drawn = true; }, configurable: true });
    Date.now = () => drawn ? end + 1 : end - 1;
  };
  const END = T + 10 * 60e3;
  try {
    Date.now = () => T + 5 * 60e3;
    const e = env({ 'board-view': 'other' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', QUIET); e.fire('c:runs', []);
    const running = () => tileOf(e.el('panel-overview').innerHTML, 'Running now');
    endsWhileDrawn(e, 'panel-overview', END);
    e.fire('c:sessions', QUIET);  // the same snapshot again: a render with the store unchanged
    assert.equal(e.el('statusText').textContent, 'Active', 'the header uses the render\'s one reading');
    assert.deepEqual(running(), ['0', 'session active'], 'the tile uses the render\'s one reading');
    Date.now = () => T + 11 * 60e3;
    e.timers.forEach(f => f());
    assert.equal(e.el('statusText').textContent, 'Idle');
    assert.deepEqual(running(), ['0', 'session idle'], 'the next minute tick finds the drawn tile out of date and redraws it');
  } finally { Date.now = realNow; }
  noPageErrors('a render whose clock readings straddle the end of the running window');
  ok('running window: a render that straddles the end of the window reads the clock once, so the next tick turns the header Idle and "Running now" to "session idle"');

  // The Dispatch tile's live or paused follows the session a project's filter shows.
  try {
    Date.now = () => T + 5 * 60e3;
    const FILTERED = [{ ...QUIET[0], id: 'w2', title: 'Filtered session', project: 'dispatch-board' }];
    const FRUNS = [{ id: 'f1', session: 'w2', project: 'dispatch-board', seq: 1, lane: 'cw', kind: 'done', label: 'Filtered run' }];
    const e = env({ 'board-view': 'p:dispatch-board', 'board-filter': 'w2' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', FILTERED); e.fire('c:runs', FRUNS);
    assert.match(e.el('session').innerHTML, /value="w2" selected/);
    const running = () => tileOf(e.el('panel-dispatch').innerHTML, 'Running now');
    assert.deepEqual(running(), ['0', 'live']);
    Date.now = () => T + 9 * 60e3;
    e.timers.forEach(f => f());
    assert.deepEqual(running(), ['0', 'live']);
    endsWhileDrawn(e, 'panel-dispatch', END);
    e.fire('c:runs', FRUNS);
    assert.deepEqual(running(), ['0', 'live'], 'the tile uses the render\'s one reading');
    Date.now = () => T + 11 * 60e3;
    e.timers.forEach(f => f());
    assert.deepEqual(running(), ['0', 'paused'], 'the next minute tick finds the drawn tile out of date and redraws it');
    e.el('panel-dispatch').innerHTML = 'untouched';
    e.timers.forEach(f => f());
    assert.equal(e.el('panel-dispatch').innerHTML, 'untouched', 'redrawn once when the state changes, not every minute');
  } finally { Date.now = realNow; }
  noPageErrors('the Dispatch tile across the end of the filtered session\'s running window');
  ok('running window, project with a session filter: Dispatch\'s "Running now" turns from live to paused on the tick after the window ends, even when a render straddles it');
}

// ---- 13. a project tab kept from an earlier export (carriedSince) warns, stating since when
{
  const C = '2026-09-10T08:15:00Z';
  const CARRIED = [
    { id: 'dispatch-board.spec', generatedAt: now, source: 'SPEC', revision: '5', prd: { frs: 1 }, rounds: [], goals: [], scopeIn: [], scopeOut: [], logicCore: [], approval: '—', approvedBy: '—', carriedSince: C },
    { id: 'dispatch-board.assumptions', generatedAt: now, source: 'A', rows: [], humanList: [], carriedSince: C },
    { id: 'dispatch-board.decisions', generatedAt: now, source: 'D', notWorkedOut: [], adrs: [], decisions: [], carriedSince: C },
    { id: 'dispatch-board.backlog', generatedAt: now, source: 'B', board: '', pbis: [{ id: 'PBI-001', title: 't', dependsOn: '—', state: 'done', group: 'g', risk: 'Low' }], carriedSince: C },
    { ...TABS.find(t => t.id === 'dispatch-board.git'), carriedSince: 'soon <img src=x>' },
  ];
  const e = env({ 'board-view': 'p:dispatch-board' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS);
  e.fire('c:projectTabs', [...TABS.filter(t => !t.id.startsWith('dispatch-board.')), ...CARRIED]);
  const warning = tab => (e.el('panel-' + tab).innerHTML.match(/<div class="callout warn" data-carried>[\s\S]*?<\/div>/) || [])[0];
  for (const tab of ['spec', 'assumptions', 'decisions', 'backlog']) {
    const w = warning(tab);
    assert.ok(w, tab + ' shows the carried warning');
    assert.ok(text(w).includes(whenStr(C)), tab + ' states the time: ' + text(w));
    assert.ok(w.includes('var(--changes)') && !w.includes('--human'), tab + ': the semantic warning colour, never --human');
  }
  assert.ok(warning('git').includes('soon &lt;img src=x&gt;') && !warning('git').includes('<img'), 'an unreadable time is shown as escaped text');
  assert.doesNotMatch(e.el('panel-overview').innerHTML, /data-carried/);
  ok('carried tab: each shown project tab carrying carriedSince warns in the warning callout, stating the time, escaped');

  e.change('project', 'p:platform-catalogue');
  for (const tab of ['spec', 'backlog', 'git']) assert.equal(warning(tab), undefined, tab + ' without carriedSince has no warning');
  ok('carried tab: a tab without carriedSince shows no carried warning');
}

// ---- 14. design rules: the brand dot, the header dot's pulse, and the sans face for paths and branch names
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1];
{
  const brand = html.match(/<div class="brand">[\s\S]*?<\/svg>/)[0];
  assert.match(brand, /<circle /);
  assert.ok(!brand.includes('--human'), 'the brand dot awaits no one, so it does not use --human');
  ok('design: the brand dot does not use --human');
}
{
  const pulsing = css.match(/([^{}]*)\{\s*animation: ping/);
  assert.ok(pulsing && /\.status\.run i/.test(pulsing[1]) && !/\.status\.on i/.test(pulsing[1]), 'the pulse is keyed to .run, not .on: ' + pulsing?.[1]);
  const e = env({ 'board-view': 'p:dispatch-board' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  assert.equal(e.el('status').className, 'status on run', 'an agent is running');
  const DONE = RUNS.map(r => ({ ...r, kind: r.kind === 'running' ? 'done' : r.kind }));
  e.fire('c:runs', DONE); e.fire('d:status/dispatch-board', { live: true, updatedAt: now });
  assert.equal(e.el('statusText').textContent, 'Building');
  assert.equal(e.el('status').className, 'status on', 'live by its status document, but no agent runs: no pulse');
  e.change('project', 'other');
  assert.equal(e.el('statusText').textContent, 'Active');
  assert.equal(e.el('status').className, 'status on', 'an active session with no running agent: no pulse');
  e.fire('c:runs', DONE.map(r => r.id === 'r4' ? { ...r, kind: 'running' } : r));
  assert.equal(e.el('status').className, 'status on run');
  ok('design: the header status dot pulses only while an agent runs, not merely while the view is live');
}
{
  const e = env({ 'board-view': 'p:dispatch-board' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  const flows = () => (e.el('panel-overview').innerHTML.match(/class="flow"/g) || []).length;
  assert.ok(flows() > 0, 'the pipeline arrows move while an agent runs');
  e.fire('c:runs', RUNS.map(r => ({ ...r, kind: r.kind === 'running' ? 'done' : r.kind }))); e.fire('d:status/dispatch-board', { live: true, updatedAt: now });
  assert.equal(e.el('statusText').textContent, 'Building', 'the view is live by its status document');
  assert.equal(flows(), 0, 'live, but no agent runs: the arrows stay still');
  ok('design: the pipeline arrows move only while an agent runs, not merely while the view is live');
}
{
  assert.doesNotMatch(css.match(/\.crumb \{([^}]*)\}/)[1], /Mono|monospace/, 'the branch crumb is in the sans face');
  // A value is in the mono face when it sits straight inside <code> or an element of class id.
  const mono = (h, v) => new RegExp(`(<code>|class="(?:sub )?id"[^>]*>)${reEsc(v)}<`).test(h);
  const GIT = { id: 'dispatch-board.git', generatedAt: now, source: 'git', repoPath: 'C:/Repos/sans-path', branch: 'feature/sans-branch', defaultBranch: 'trunk-default',
    head: 'deadbee', remotes: ['origin https://github.com/o/sans.git (fetch)'], dirty: ['site/dirty-file.html'], byDir: { 'site/folder-x': 3 },
    commits: [{ sha: 'cafe123', subject: 's', date: now }], pulls: [{ number: 5, title: 't', state: 'OPEN', url: 'https://github.com/o/r/pull/5', branch: 'pbi/pr-branch', updatedAt: now }] };
  const DEC = { id: 'dispatch-board.decisions', generatedAt: now, source: 'D', notWorkedOut: [], decisions: [],
    adrs: [{ id: 'ADR-0007', resolves: 'row 1', title: 'T', status: 'Proposed', path: 'docs/adr/0007-sans.md' }] };
  for (const [git, shown] of [
    [GIT, ['C:/Repos/sans-path', 'feature/sans-branch', 'trunk-default', 'origin https://github.com/o/sans.git (fetch)', 'site/dirty-file.html', 'site/folder-x', 'pbi/pr-branch']],
    [{ ...GIT, remotes: [] }, ['C:/Repos/sans-path', 'feature/sans-branch', 'trunk-default', 'site/dirty-file.html', 'site/folder-x', '/platform-catalogue/']],
  ]) {
    const e = env({ 'board-view': 'p:dispatch-board' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS);
    e.fire('c:projectTabs', [...TABS.filter(t => t.id !== 'dispatch-board.git'), git, DEC]);
    const G = e.el('panel-git').innerHTML;
    for (const v of shown) {  // none of these values holds a character esc() changes
      assert.ok(G.includes(v), v + ' is shown');
      assert.ok(!mono(G, v), v + ' is not in the mono face');
    }
    assert.ok(mono(G, 'deadbee') && mono(G, 'cafe123'), 'commit hashes stay in the mono face');
    const D = e.el('panel-decisions').innerHTML;
    assert.ok(D.includes('docs/adr/0007-sans.md') && !mono(D, 'docs/adr/0007-sans.md'), 'an ADR path is in the sans face');
    assert.ok(mono(D, 'ADR-0007'), 'an ADR id stays in the mono face');
  }
  const e = env({ 'board-view': 'other' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS.map(s => s.id === 's3' ? { ...s, cwd: 'C:/work/loose-folder' } : s));
  const O = e.el('panel-overview').innerHTML;
  assert.ok(O.includes('C:/work/loose-folder') && !mono(O, 'C:/work/loose-folder'), 'the session folder is in the sans face');
  ok('design: paths and branch names are in the sans face; ids and commit hashes stay in IBM Plex Mono');
}

// ---- 15. Dispatch's figure is the agents' self-reported subagent_tokens, and says so wherever it is shown
{
  const e = env({ 'board-view': 'p:dispatch-board' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS.map(r => r.id === 'r3' ? { ...r, tok: 123456 } : r)); e.fire('c:projectTabs', TABS);
  const O = e.el('panel-overview').innerHTML, D = e.el('panel-dispatch').innerHTML;
  assert.equal(tileOf(O, 'Agent runs')[1], '0 review verdicts · 0.12M reported tokens');
  assert.match(O, /<th class="num">Reported tokens<\/th>/);
  assert.deepEqual(tileOf(D, 'Reported tokens'), ['0.12 M', 'across all runs']);
  assert.match(D, /<th style="min-width:120px">Reported tokens<\/th>/);
  assert.match(D, /Box width is proportional to reported tokens\./);
  const said = text(O + D).match(/\S+ tokens/gi) || [];
  assert.ok(said.length >= 5 && said.every(m => /^reported tokens$/i.test(m)), 'every token figure is labelled reported: ' + said.join(' | '));
  ok('reported tokens: the Overview tile, both run tables, the Dispatch tile and the swimlane caption say "reported tokens"');
}

// ---- 16. label lookups read only their own keys, never an inherited Object.prototype member
{
  const PROTO_RUNS = [...RUNS,
    { id: 'r9', session: 's2', project: 'dispatch-board', seq: 2, lane: 'toString', kind: 'constructor', label: 'PROTO RUN', feeds: 'r3', from: 'toString' },
    { id: 'r8', session: 's2', project: 'dispatch-board', seq: 3, lane: 'cw', kind: '__proto__', label: 'PROTO KIND', feeds: 'r9' }];
  const PROTO_BACKLOG = { id: 'dispatch-board.backlog', generatedAt: now, source: 'B', board: '', pbis: [
    { id: 'PBI-101', title: 'a', dependsOn: '—', state: 'constructor', group: 'g', risk: 'Low' },
    { id: 'PBI-102', title: 'b', dependsOn: 'PBI-101', state: '__proto__', group: 'g', risk: 'Low' }] };
  const e = env({ 'board-view': 'p:dispatch-board' });
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', PROTO_RUNS); e.fire('c:projectTabs', [...TABS, PROTO_BACKLOG]);
  noPageErrors('rendering states, kinds and lanes named after Object.prototype members');
  for (const tab of ['overview', 'dispatch', 'backlog']) {
    const H = e.el('panel-' + tab).innerHTML;
    assert.doesNotMatch(H, /native code|\[object Object\]|could not be shown/, tab);
  }
  assert.ok(e.el('panel-dispatch').innerHTML.includes('<span class="tag constructor">constructor</span>'), 'the raw kind is shown');
  assert.ok(text(e.el('panel-dispatch').innerHTML).includes('toString PROTO RUN'), 'the raw lane is the agent name');
  assert.ok(e.el('panel-backlog').innerHTML.includes('<span class="tag __proto__">__proto__</span>'), 'the raw state is shown');
  ok('labels: a state, kind or lane named like an inherited member shows its raw text, never the member');
}

// ---- 17. the Agent catalogue's usage figures wait for both sessions and runs
{
  const CAT = { generatedAt: now, source: {}, plugins: [{ plugin: 'engineering-agents', purpose: 'E.', purposeFull: 'E.', installed: true, agents: 1, skills: 0 }],
    entries: [{ id: 'engineering-agents:code-writer', kind: 'agent', plugin: 'engineering-agents', name: 'code-writer', description: 'W.', installed: true }] };
  const RUN = [{ id: 'p1', session: 's2', project: 'dispatch-board', seq: 1, lane: 'cw', kind: 'done', label: 'x', agentType: 'engineering-agents:code-writer', start: old }];
  for (const [first, last] of [[['c:sessions', SESSIONS], ['c:runs', RUN]], [['c:runs', RUN], ['c:sessions', SESSIONS]]]) {
    const e = env({ 'board-view': 'p:dispatch-board', 'board-tab': 'catalogue' });
    await tick();
    e.fire('c:projects', PROJECTS); e.fire('d:catalogue/index', CAT); e.fire(...first);
    let H = e.el('panel-catalogue').innerHTML;
    assert.deepEqual(cells(rowOf(H, 'agent:engineering-agents:code-writer')).slice(2), ['pending', 'pending', 'pending', 'pending'], 'without ' + last[0]);
    assert.ok(!H.includes('never used'), 'nothing reads "never used" yet');
    assert.equal(tileOf(H, 'Agents used')[0], '—');
    assert.equal(tileOf(H, 'Outside the catalogue')[0], '—');
    e.fire(...last);
    H = e.el('panel-catalogue').innerHTML;
    assert.deepEqual(cells(rowOf(H, 'agent:engineering-agents:code-writer')).slice(2), ['1', whenStr(old), 'dispatch-board', '1']);
    assert.equal(tileOf(H, 'Agents used')[0], '1 of 1 · 1 in all sessions');
  }
  ok('catalogue: usage reads pending, not 0 or "never used", until both sessions and runs have loaded');
}

// ---- 18. the app bar and the Overview render on the first load whatever the store and the fonts do
{
  assert.doesNotMatch(html.replace(/<script>[\s\S]*?<\/script>/, ''), /<link[^>]*rel="stylesheet"/, 'no stylesheet link in the markup');
  const e = env();
  await tick();
  const f = e.doc.appended.find(n => n.tagName === 'LINK');
  assert.ok(f && f.rel === 'stylesheet' && /^https:\/\/fonts\.googleapis\.com\/css2\?family=Schibsted\+Grotesk/.test(f.href), 'the script adds the font stylesheet');
  ok('load: the font stylesheet is added by the script, so a stalled font request cannot hold back the first render');
}
const drawnOffline = (e, why) => {
  assert.equal(e.el('statusText').textContent, 'Offline', why);
  assert.equal(e.selected(), 'overview', why);
  assert.match(e.el('panel-overview').innerHTML, /^<div class="empty">This view cannot reach the live store\.<\/div>$/, why);
  assert.equal(e.el('foot').textContent, 'This view cannot reach the live store, so it shows no data.', why);
};
{
  for (const [claude, why] of [[() => undefined, 'no window.claude'], [() => ({}), 'no claude.use'], [() => ({ use: async () => null }), 'no db capability']]) {
    const e = env({}, { claude });
    await tick();
    drawnOffline(e, why);
  }
  ok('load, store absent: the app bar says Offline and the Overview says the store is out of reach');
}
{
  const warned = [], realWarn = console.warn;
  console.warn = (...a) => warned.push(a);
  try {
    for (const [claude, why] of [[() => ({ use: () => Promise.reject(new Error('refused')) }), 'use() rejects'], [() => ({ use() { throw new Error('thrown'); } }), 'use() throws']]) {
      const e = env({}, { claude });
      await tick();
      drawnOffline(e, why);
    }
  } finally { console.warn = realWarn; }
  assert.equal(warned.length, 2);
  assert.ok(warned.every(a => a[0] === 'Board: the live store could not be opened' && a[1] instanceof Error), 'each failure is logged with its error');
  ok('load, store refuses to open: no unhandled rejection; the app bar says Offline and the Overview says the store is out of reach');
}
{
  let release;
  const e = env({ 'board-view': 'p:platform-catalogue' }, { claude: db => ({ use: () => new Promise(r => { release = () => r(db); }) }) });
  await tick();
  const waiting = () => {
    assert.equal(e.el('statusText').textContent, 'Connecting');
    assert.equal(e.selected(), 'overview');
    assert.match(e.el('panel-overview').innerHTML, /^<div class="empty">Connecting to the live store…<\/div>$/);
  };
  waiting();
  e.timers.forEach(f => f());
  waiting();
  release();
  await tick();
  e.fire('c:projects', PROJECTS); e.fire('c:sessions', SESSIONS); e.fire('c:runs', RUNS); e.fire('c:projectTabs', TABS);
  assert.deepEqual(tileOf(e.el('panel-overview').innerHTML, 'Work items built'), ['1 / 1', '0 with open conditions · 0 partly built']);
  ok('load, late store: the app bar and Overview draw a Connecting state at once, then the data when the store arrives');
}

assert.deepEqual([...everySub].filter(k => k === 'c:tabs' || k.startsWith('d:tabs/')), [], 'a retired tabs/* subscription');
assert.ok(everySub.has('c:projectTabs'), 'the guard saw the page\'s real subscriptions');
ok('the page never subscribes to the retired tabs collection or a tabs/* document');
noPageErrors('after the last check');
console.log(`all ${passed} page checks passed`);
