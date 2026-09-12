"""Conformance with v1: every document the exporters and refresh.plan() write validates against its record
kind, and each one's store_path is the path it was written to.

The three exporters run in-process with their real signatures on synthetic input built here, in a temporary
folder: a projects root of transcripts, two small repositories, a data folder, an agent-catalog marketplace and
an installed-plugins file. Then refresh.plan() adds the status documents. Nothing is read from the real out/,
~/.claude or the store.
"""
import contextlib, io, json, os, shutil, stat, subprocess, sys, tempfile, time, unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
sys.path.insert(0, os.path.join(HERE, 'local'))
import records  # noqa: E402
import export_board  # noqa: E402
import export_catalogue  # noqa: E402
import export_sessions  # noqa: E402
import refresh  # noqa: E402

HAS_GIT = shutil.which('git') is not None
NOW = '2026-09-11T12:00:00+00:00'
# Transcript times sit a few hours back, inside the sessions window, so the exporter keeps every session.
BASE = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=3)

SID_A = 'aaaaaaaa-0000-4000-8000-00000000000a'  # linked to alpha, whose statusDoc is meta/status
SID_B = 'bbbbbbbb-0000-4000-8000-00000000000b'  # linked to beta, with no readable timestamps
SID_C = 'cccccccc-0000-4000-8000-00000000000c'  # linked to no project
CWD = 'C:\\work\\app'
FOLDER = 'C--work-app'
MANUAL = {'id': 'orch-inline', 'after': 'acw', 'lane': 'orch', 'label': 'In-line work', 'verdict': 'wired'}

SPEC = """---
revision: 2
---
# App: solution spec

**Rows the human must confirm or correct at the plan gate:** 2.

- **G-1** Ship the widget.

### In scope
- Widgets

### Out of scope
- Gadgets

## Assumptions & open questions

| # | Question | Resolution | Status | Source | Impact |
|---|---|---|---|---|---|
| 1 | Where does the data live? | JSON | RESOLVED | PRD | Low - one file |
| 2 | Who owns an entry? | The team | ASSUMED | brief | Medium - rework |

## Key decisions

| Decision | Rationale | Made by | Date |
|---|---|---|---|
| Use JSON | simple | owner | 2026-09-01 |

## Backlog

### PBI list (proposed)

| ID | Title | Depends on | Group | Risk | Requires spec | Notes |
|---|---|---|---|---|---|---|
| PBI-001 | Widget | — | core | Low | no | x |

### Future iterations (not planned)

- **Phone notifications**: later.
"""
FILES = {'docs/spec.md': SPEC, 'docs/prd.md': '- **FR-1** a\n', 'docs/brief.md': '# Brief\n',
         'docs/adr/0001-data.md': '---\nid: ADR-0001\ntitle: Data\nstatus: proposed\nresolves: row 1\n---\n',
         'docs/reviews/plan-gate-review-r1.md': '**Verdict:** **GO**\n'}
DOCS = {'spec': 'docs/spec.md', 'prd': 'docs/prd.md', 'brief': 'docs/brief.md', 'adrDir': 'docs/adr',
        'reviews': [{'gate': 'Plan gate', 'path': 'docs/reviews/plan-gate-review-r{round}.md'}]}
DATA = {'buildState': {'PBI-001': {'state': 'done', 'review': 'GO', 'open': '', 'commit': 'abc1234'}},
        'notWorkedOut': [{'item': 'Where the data lives', 'row': 1, 'adr': 'ADR-0001'}], 'boardNote': 'Nothing yet.'}

# The folders of out/ and the record kind of each document in them; status documents are matched by path.
FOLDERS = {'sessions': 'session', 'runs': 'run', 'projects': 'project', 'projectTabs': 'tab', 'status': 'status'}
SKIPPED = ('.pending.json', '.pushed.json')


def ts(minutes):
    return (BASE + timedelta(minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%S.000Z')


def user(m, text, cwd=CWD):
    return {'type': 'user', 'timestamp': ts(m), 'cwd': cwd, 'message': {'role': 'user', 'content': text}}


def reply(m, mid, text='', tools=()):
    content = ([{'type': 'text', 'text': text}] if text else []) + [
        {'type': 'tool_use', 'id': tid, 'name': name, 'input': inp} for tid, name, inp in tools]
    return {'type': 'assistant', 'timestamp': ts(m), 'message': {
        'id': mid, 'model': 'claude-opus-5', 'content': content,
        'usage': {'input_tokens': 100, 'output_tokens': 10, 'cache_read_input_tokens': 1000, 'cache_creation_input_tokens': 50}}}


def untimed(rec, stamp=None):
    """The record with no readable time: its timestamp removed, or replaced by one that does not parse."""
    rec = dict(rec)
    rec.pop('timestamp')
    if stamp is not None:
        rec['timestamp'] = stamp
    return rec


def launch(m, tool_id):
    return reply(m, 'msg-launch-' + tool_id, tools=[(tool_id, 'Agent', {'description': 'task'})])


def stop(m, aid):
    return reply(m, 'msg-stop-' + aid, tools=[('toolu_stop_' + aid, 'TaskStop', {'task_id': aid})])


def notify(m, aid, result, tokens, ms):
    body = ('<task-notification><task-id>%s</task-id><status>completed</status><result>%s</result>'
            '<subagent_tokens>%s</subagent_tokens><duration_ms>%s</duration_ms></task-notification>') % (aid, result, tokens, ms)
    return {'type': 'user', 'timestamp': ts(m), 'message': {'role': 'user', 'content': body}}


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.invalid',
               GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.invalid')
    subprocess.run(['git', '-c', 'init.defaultBranch=main', '-c', 'commit.gpgsign=false', *args],
                   cwd=cwd, env=env, check=True, capture_output=True)


def _make_writable_and_retry(func, path, _exc):
    # Git writes its object files read-only, and on Windows a read-only file cannot be deleted until it is made
    # writable again.
    os.chmod(path, stat.S_IWRITE)
    func(path)


class Fixture:
    """Everything the exporters read, in one temporary folder, and the out/ they write."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='conformance-test-')
        self.root = os.path.join(self.tmp, 'projects')
        self.out = os.path.join(self.tmp, 'out')
        self.data_dir = os.path.join(self.tmp, 'data')
        self.market = os.path.join(self.tmp, 'agent-catalog')
        self.installed = os.path.join(self.tmp, 'installed_plugins.json')
        self.alpha = os.path.join(self.tmp, 'alpha')
        self.beta = os.path.join(self.tmp, 'beta')

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def jsonl(self, path, recs):
        self.write(path, ''.join(json.dumps(r) + '\n' for r in recs))

    def agent(self, sid, aid, recs, meta):
        path = os.path.join(self.root, FOLDER, sid, 'subagents', 'agent-%s.jsonl' % aid)
        self.jsonl(path, recs)
        self.write(path[:-len('.jsonl')] + '.meta.json', json.dumps(meta))

    def transcripts(self):
        # Session A: a finished code-writer (followed by the runs.manual row), a running reviewer, a stopped
        # test-writer and a general-purpose agent (lane "other"); one skill use with a time, one without.
        self.jsonl(os.path.join(self.root, FOLDER, SID_A + '.jsonl'), [
            user(0, 'Please build the widget'),
            launch(1, 'toolu_cw'), launch(2, 'toolu_run'), launch(3, 'toolu_kill'), launch(4, 'toolu_gp'),
            reply(5, 'm-skill-timed', tools=[('toolu_sk1', 'Skill', {'skill': 'eng:tdd'})]),
            untimed(reply(6, 'm-skill-untimed', tools=[('toolu_sk2', 'Skill', {'skill': 'eng:untimed'})])),
            stop(7, 'akill'),
            notify(30, 'acw', 'All green. DONE', '5000', '1740000'),
            notify(31, 'agp', 'Looked around.', '800', '60000'),
        ])
        self.agent(SID_A, 'acw', [user(1, 'task'), reply(2, 'm-cw', text='All green. DONE')],
                   {'agentType': 'engineering-agents:code-writer', 'description': 'PBI-001 widget', 'toolUseId': 'toolu_cw'})
        self.agent(SID_A, 'arun', [user(2, 'task'), reply(3, 'm-run', text='Reading the diff')],
                   {'agentType': 'review-agents:code-reviewer', 'description': 'Review PBI-001', 'toolUseId': 'toolu_run'})
        self.agent(SID_A, 'akill', [user(3, 'task'), reply(4, 'm-kill', text='Writing tests')],
                   {'agentType': 'engineering-agents:test-writer', 'description': 'PBI-001 tests', 'toolUseId': 'toolu_kill'})
        self.agent(SID_A, 'agp', [user(4, 'task'), reply(5, 'm-gp', text='Looked around.')],
                   {'agentType': 'general-purpose', 'description': 'Explore the repo', 'toolUseId': 'toolu_gp'})
        # Session B: linked, answered, but no record carries a readable time.
        self.jsonl(os.path.join(self.root, FOLDER, SID_B + '.jsonl'), [
            untimed(user(0, 'Hello beta')), untimed(reply(1, 'm-b'), stamp='yesterday-ish')])
        # Session C: linked to no project.
        self.jsonl(os.path.join(self.root, FOLDER, SID_C + '.jsonl'), [
            {'type': 'custom-title', 'customTitle': 'Side quest', 'sessionId': SID_C},
            user(10, 'Something else'), reply(11, 'm-c', text='Done.')])

    def repos(self):
        for root in (self.alpha, self.beta):
            for rel, text in FILES.items():
                self.write(os.path.join(root, rel), text)
        if HAS_GIT:  # beta stays a plain folder, so it gets no git tab
            git(self.alpha, 'init')
            git(self.alpha, 'add', '-A')
            git(self.alpha, 'commit', '-m', 'first')
        self.write(os.path.join(self.data_dir, 'alpha.json'), json.dumps(DATA))

    def marketplace(self):
        plugins = os.path.join(self.market, 'plugins')
        self.write(os.path.join(plugins, 'eng', 'agents', 'code-writer.md'),
                   '---\nname: code-writer\ndescription: "Writes code under TDD"\n---\n\nBody.\n')
        self.write(os.path.join(plugins, 'eng', 'skills', 'tdd', 'SKILL.md'),
                   '---\nname: tdd\ndescription: Red, green, refactor\n---\n\nBody.\n')
        self.write(os.path.join(plugins, 'eng', '.claude-plugin', 'plugin.json'),
                   json.dumps({'name': 'eng', 'description': 'Engineering agents. They build things.'}))
        self.write(os.path.join(plugins, 'ops', 'agents', 'runner.md'), '---\ndescription: Runs things\n---\n')
        self.write(self.installed, json.dumps({'version': 2, 'plugins': {'eng@agent-catalog': [{'scope': 'user'}]}}))

    def config(self):
        return {
            'projects': [
                {'id': 'alpha', 'name': 'Alpha', 'repoPath': self.alpha, 'branch': 'main', 'sessions': [SID_A],
                 'statusDoc': 'meta/status', 'docs': DOCS},
                {'id': 'beta', 'name': 'Beta', 'repoPath': self.beta, 'branch': 'main', 'sessions': [SID_B], 'docs': DOCS},
                {'id': 'gamma', 'name': 'Gamma', 'repoPath': '', 'branch': '', 'sessions': []},
            ],
            'catalogue': {'marketplacePath': self.market, 'installedPath': self.installed},
            'sessions': {'days': 7, 'showFirstPrompt': True},
            'runs': {'runningWindowMinutes': 10, 'manual': [MANUAL]},
        }

    def export(self):
        """Run the exporters as refresh.py does (board, sessions, catalogue), then plan. export_board runs twice,
        with alpha's repository moved away before the second run, so alpha's tabs are ones it kept."""
        cfg, err = self.config(), io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            codes = [export_board.main(cfg, self.out, self.data_dir, NOW)]
            self.first_tabs = self.tab_bytes('alpha')
            os.rename(self.alpha, self.alpha + '-moved')
            codes.append(export_board.main(cfg, self.out, self.data_dir, NOW))
            codes.append(export_sessions.main(cfg, self.out, self.root, time.time()))
            codes.append(export_catalogue.main(cfg, self.out, NOW))
            self.plan = refresh.plan(self.out)
        self.codes, self.err = codes, err.getvalue()

    def tab_bytes(self, pid):
        folder, found = os.path.join(self.out, 'projectTabs'), {}
        for name in sorted(os.listdir(folder)):
            if name.startswith(pid + '.'):
                with io.open(os.path.join(folder, name), 'rb') as f:
                    found[name] = f.read()
        return found

    def documents(self):
        """Every document written under out/, as {relative path without .json: (kind, id, doc)}. Raises
        AssertionError for a file no kind maps to, so a new kind of document cannot go unchecked."""
        found = {}
        for dirpath, dirnames, filenames in os.walk(self.out):
            rel_dir = os.path.relpath(dirpath, self.out).replace('\\', '/')
            if rel_dir == '.':
                dirnames[:] = [d for d in dirnames if d != '.cache']
            for name in filenames:
                rel = name if rel_dir == '.' else rel_dir + '/' + name
                if rel in SKIPPED:
                    continue
                if not rel.endswith('.json'):
                    raise AssertionError('unexpected file in out/: %s' % rel)
                path = rel[:-len('.json')]
                folder, _, doc_id = path.rpartition('/')
                if path == 'catalogue/index':
                    kind, doc_id = 'catalogue', 'index'
                elif path == 'meta/lastRefresh':
                    kind, doc_id = 'lastRefresh', 'lastRefresh'
                elif path == 'meta/status' or folder == 'status':
                    kind, doc_id = 'status', path
                elif folder in FOLDERS:
                    kind = FOLDERS[folder]
                else:
                    raise AssertionError('no record kind for out/%s' % rel)
                with io.open(os.path.join(dirpath, name), encoding='utf-8') as f:
                    found[path] = (kind, doc_id, json.load(f))
        return found

    def cleanup(self):
        # Errors are not ignored: a folder that fails to go would silently leak into the temp folder on every run.
        if sys.version_info >= (3, 12):
            shutil.rmtree(self.tmp, onexc=_make_writable_and_retry)
        else:
            shutil.rmtree(self.tmp, onerror=_make_writable_and_retry)


class FindingsFixture(Fixture):
    """A Fixture whose session A also carries a completed PBI-001 code-review round, so export_sessions.py
    writes projectTabs/alpha.findings (PBI-011) among the documents this test checks for conformance."""

    FINDINGS_RESULT = (
        '**Verdict:** **GO**\n\n'
        '```json\n'
        '{"findings": [{"id": "F1", "severity": "LOW", "title": "Tidy naming", '
        '"subject": {"id": "widget.py:12"}, "remediation": "Rename the helper"}]}\n'
        '```'
    )

    def transcripts(self):
        self.jsonl(os.path.join(self.root, FOLDER, SID_A + '.jsonl'), [
            user(0, 'Please build the widget'),
            launch(1, 'toolu_cw'), launch(2, 'toolu_run'), launch(3, 'toolu_kill'), launch(4, 'toolu_gp'),
            launch(5, 'toolu_rev'),
            reply(6, 'm-skill-timed', tools=[('toolu_sk1', 'Skill', {'skill': 'eng:tdd'})]),
            untimed(reply(7, 'm-skill-untimed', tools=[('toolu_sk2', 'Skill', {'skill': 'eng:untimed'})])),
            stop(8, 'akill'),
            notify(30, 'acw', 'All green. DONE', '5000', '1740000'),
            notify(31, 'agp', 'Looked around.', '800', '60000'),
            notify(32, 'arev', self.FINDINGS_RESULT, '3000', '900000'),
        ])
        self.agent(SID_A, 'acw', [user(1, 'task'), reply(2, 'm-cw', text='All green. DONE')],
                   {'agentType': 'engineering-agents:code-writer', 'description': 'PBI-001 widget', 'toolUseId': 'toolu_cw'})
        self.agent(SID_A, 'arun', [user(2, 'task'), reply(3, 'm-run', text='Reading the diff')],
                   {'agentType': 'review-agents:code-reviewer', 'description': 'Review PBI-001', 'toolUseId': 'toolu_run'})
        self.agent(SID_A, 'akill', [user(3, 'task'), reply(4, 'm-kill', text='Writing tests')],
                   {'agentType': 'engineering-agents:test-writer', 'description': 'PBI-001 tests', 'toolUseId': 'toolu_kill'})
        self.agent(SID_A, 'agp', [user(4, 'task'), reply(5, 'm-gp', text='Looked around.')],
                   {'agentType': 'general-purpose', 'description': 'Explore the repo', 'toolUseId': 'toolu_gp'})
        self.agent(SID_A, 'arev', [user(5, 'task'), reply(6, 'm-rev', text='GO')],
                   {'agentType': 'review-agents:code-reviewer', 'description': 'Review PBI-001 round 2', 'toolUseId': 'toolu_rev'})
        self.jsonl(os.path.join(self.root, FOLDER, SID_B + '.jsonl'), [
            untimed(user(0, 'Hello beta')), untimed(reply(1, 'm-b'), stamp='yesterday-ish')])
        self.jsonl(os.path.join(self.root, FOLDER, SID_C + '.jsonl'), [
            {'type': 'custom-title', 'customTitle': 'Side quest', 'sessionId': SID_C},
            user(10, 'Something else'), reply(11, 'm-c', text='Done.')])


class ConformanceFindings(unittest.TestCase):
    """PBI-026: projectTabs/<projectId>.findings (PBI-011's review findings ledger) must validate as a "tab"
    record and round-trip through to_row/from_row with its store path preserved, like the five original tabs.
    """

    @classmethod
    def setUpClass(cls):
        cls.f = FindingsFixture()
        try:
            cls.f.transcripts()
            cls.f.repos()
            cls.f.marketplace()
            cls.f.export()
            cls.docs = cls.f.documents()
        except BaseException:
            cls.f.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.f.cleanup()

    def test_a_findings_tab_was_written_and_conforms(self):
        self.assertIn('projectTabs/alpha.findings', self.docs)
        kind, doc_id, d = self.docs['projectTabs/alpha.findings']
        self.assertEqual((kind, doc_id), ('tab', 'alpha.findings'))
        self.assertIn('PBI-001', d.get('items', {}))
        self.assertEqual(records.validate(kind, d), [])
        self.assertEqual(records.store_path(kind, doc_id), 'projectTabs/alpha.findings')
        self.assertEqual(records.from_row(kind, records.to_row(kind, doc_id, d)), d)


class Cleanup(unittest.TestCase):
    def test_cleanup_removes_a_folder_holding_read_only_files(self):
        f = Fixture()
        path = os.path.join(f.tmp, 'repo', '.git', 'objects', 'ab', 'cdef0123')
        f.write(path, 'object')
        os.chmod(path, stat.S_IREAD)
        f.cleanup()
        self.assertFalse(os.path.exists(f.tmp))


class ConformanceV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        try:
            cls.f.transcripts()
            cls.f.repos()
            cls.f.marketplace()
            cls.f.export()
            cls.docs = cls.f.documents()
        except BaseException:
            cls.f.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.f.cleanup()

    def of(self, kind):
        return {doc_id: d for k, doc_id, d in self.docs.values() if k == kind}

    # -------- every document conforms

    def test_the_exporters_and_plan_succeeded(self):
        self.assertEqual(self.f.codes, [0, 0, 0, 0], self.f.err)
        self.assertIsNotNone(self.f.plan)

    def test_every_document_validates_against_its_kind(self):
        self.assertTrue(self.docs)
        for path, (kind, doc_id, d) in sorted(self.docs.items()):
            with self.subTest(path=path, kind=kind):
                self.assertEqual(records.validate(kind, d), [])

    def test_every_store_path_equals_the_path_it_was_written_to(self):
        for path, (kind, doc_id, d) in sorted(self.docs.items()):
            with self.subTest(path=path):
                self.assertEqual(records.store_path(kind, doc_id), path)

    def test_every_document_round_trips_through_its_row(self):
        for path, (kind, doc_id, d) in sorted(self.docs.items()):
            with self.subTest(path=path):
                self.assertEqual(records.from_row(kind, records.to_row(kind, doc_id, d)), d)

    def test_every_kind_the_v1_exporters_write_was_seen(self):
        self.assertEqual({k for k, _, _ in self.docs.values()},
                          {'session', 'run', 'project', 'tab', 'status', 'catalogue', 'lastRefresh'})

    def test_both_status_forms_were_written(self):
        self.assertIn('meta/status', self.docs)
        self.assertIn('status/beta', self.docs)
        self.assertIn('status/gamma', self.docs)

    def test_the_bookkeeping_files_are_not_documents(self):
        self.assertTrue(os.path.isfile(os.path.join(self.f.out, '.pending.json')))
        self.assertTrue(os.path.isdir(os.path.join(self.f.out, '.cache')))
        self.assertFalse([p for p in self.docs if p.startswith('.')])

    def test_catalogue_ids_are_plugin_colon_name(self):
        cat = self.docs['catalogue/index'][2]
        self.assertEqual({e['kind'] for e in cat['entries']}, {'agent', 'skill'})
        for e in cat['entries']:
            self.assertEqual(e['id'], '%s:%s' % (e['plugin'], e['name']))

    # -------- the fixture produced every required case

    def test_a_running_run_and_a_killed_run(self):
        runs = self.of('run')
        self.assertEqual(runs['arun']['kind'], 'running')
        self.assertEqual(runs['akill']['kind'], 'killed')
        self.assertEqual(runs['acw']['kind'], 'done')

    def test_a_lane_other_run_carries_agent(self):
        run = self.of('run')['agp']
        self.assertEqual((run['lane'], run['agent'], run['agentType']), ('other', 'general-purpose', 'general-purpose'))

    def test_a_manual_row_has_no_agent_type_or_start(self):
        run = self.of('run')['orch-inline']
        self.assertEqual((run['lane'], run['session'], run['project']), ('orch', SID_A, 'alpha'))
        self.assertNotIn('agentType', run)
        self.assertNotIn('start', run)
        self.assertIn('start', self.of('run')['acw'])

    def test_a_skill_use_without_a_readable_time(self):
        uses = self.of('session')[SID_A]['skillUses']
        self.assertEqual(uses['eng:untimed'], {'count': 1})
        self.assertIn('last', uses['eng:tdd'])

    def test_show_first_prompt_is_on(self):
        self.assertEqual(self.of('session')[SID_A]['firstPrompt'], 'Please build the widget')

    def test_a_project_with_no_sessions_has_null_usage_and_last(self):
        gamma = self.of('project')['gamma']
        self.assertEqual((gamma['sessions'], gamma['usage'], gamma['last']), ([], None, None))

    def test_a_linked_session_with_no_readable_timestamps(self):
        b = self.of('session')[SID_B]
        self.assertEqual((b['project'], b['start'], b['last']), ('beta', None, None))

    def test_a_linked_session_and_an_unlinked_one(self):
        sessions = self.of('session')
        self.assertEqual(sessions[SID_A]['project'], 'alpha')
        self.assertIsNone(sessions[SID_C]['project'])
        self.assertEqual(self.of('project')['alpha']['sessions'], [SID_A])

    def test_alpha_tabs_are_the_ones_export_board_kept(self):
        self.assertIn('project alpha: cannot rebuild', self.f.err)
        expected = {'alpha.%s.json' % t for t in ('spec', 'assumptions', 'decisions', 'backlog')} | (
            {'alpha.git.json'} if HAS_GIT else set())
        self.assertEqual(set(self.f.first_tabs), expected)
        # The first carry adds carriedSince, the carrying run's time in UTC with a Z, and changes nothing else.
        carried = self.f.tab_bytes('alpha')
        self.assertEqual(set(carried), expected)
        for name, raw in self.f.first_tabs.items():
            first = json.loads(raw.decode('utf-8'))
            self.assertNotIn('carriedSince', first, name)
            self.assertEqual(json.loads(carried[name].decode('utf-8')), dict(first, carriedSince='2026-09-11T12:00:00Z'), name)
        self.assertEqual(set(self.f.tab_bytes('beta')), {'beta.%s.json' % t for t in ('spec', 'assumptions', 'decisions', 'backlog')})
        self.assertEqual(self.f.tab_bytes('gamma'), {})
        # A later run while alpha is still missing leaves the kept bytes as they were, first carriedSince included,
        # so refresh.py plans no write for them. It runs on a copy of projectTabs, the only part of out/ that
        # export_board reads, so the out/ the other tests share is left as it is.
        again = os.path.join(self.f.tmp, 'out-again')
        shutil.copytree(os.path.join(self.f.out, 'projectTabs'), os.path.join(again, 'projectTabs'))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = export_board.main(self.f.config(), again, self.f.data_dir, '2026-09-12T09:00:00+00:00')
        self.assertEqual(code, 0)
        folder, kept = os.path.join(again, 'projectTabs'), {}
        for name in carried:
            with io.open(os.path.join(folder, name), 'rb') as f:
                kept[name] = f.read()
        self.assertEqual(kept, carried)

    def test_the_catalogue_was_exported(self):
        cat = self.docs['catalogue/index'][2]
        self.assertEqual([e['id'] for e in cat['entries']], ['eng:code-writer', 'eng:tdd', 'ops:runner'])
        self.assertEqual([p['installed'] for p in cat['plugins']], [True, False])


if __name__ == '__main__':
    unittest.main()
