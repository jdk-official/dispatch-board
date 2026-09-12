"""The collector's tab and status pass: local/tabs.py and its hook into local/collector.py.

Every git call goes to an injected fake, so no test needs a repository or reaches a network host, and the
document a project's tabs are built from is a throwaway folder of markdown. The transcripts and database come
from collector_support, as the other collector tests' do.
"""
import contextlib, io, json, os, sqlite3, subprocess, time, unittest

from collector_support import Env, tes
import collector  # noqa: E402
import db  # noqa: E402
import export_board  # noqa: E402
import records  # noqa: E402
import schema  # noqa: E402
import tabs  # noqa: E402
import test_conformance as tc  # noqa: E402

SID = tes.SID
SID2 = tes.SID2
# What the fake git prints for each argv. The origin is on github.com, so the exporter would list pull
# requests here: a pass that ran gh would be caught by the network test rather than passing vacuously.
GIT_OUT = {
    ('branch', '--show-current'): 'work',
    ('rev-parse', '--verify', '--quiet', 'master'): '',
    ('rev-parse', '--verify', '--quiet', 'main'): 'm1m1m1m',
    ('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict'): 'abc1234|2026-09-10T10:00:00+01:00|Add the widget',
    ('ls-files',): 'README.md\ndocs/spec.md',
    ('status', '--short'): ' M docs/spec.md',
    ('remote', '-v'): 'origin\thttps://github.com/owner/repo.git (fetch)\norigin\thttps://github.com/owner/repo.git (push)',
    ('rev-parse', '--short', 'HEAD'): 'abc1234',
    ('rev-list', '--count', 'main..work'): '2',
    ('diff', '--shortstat', 'main', 'work'): ' 1 file changed, 2 insertions(+)',
}
FINDINGS = {'generatedAt': '2026-09-01T00:00:00+00:00', 'source': 'review findings', 'items': {'PBI-001': []}}


class FakeRun:
    """Stands in for subprocess.run: fixed git output per argv, every call recorded, and a per-repository or
    per-command failure on demand. A folder not in repos answers `rev-parse --is-inside-work-tree` as the real
    git does outside a work tree.

    raw holds bytes for a repository or one of its commands, decoded here with the encoding the caller asked
    for, exactly as subprocess.run decodes git's output under text=True. Bytes that are not valid in that
    encoding therefore raise the real UnicodeDecodeError git's own output would raise, rather than a
    hand-made one.
    """

    def __init__(self, repos=(), raises=None, raw=None):
        self.repos, self.raises, self.calls = set(repos), dict(raises or {}), []
        self.raw = dict(raw or {})

    def __call__(self, cmd, cwd=None, **kw):
        args = tuple(cmd[1:])
        self.calls.append({'cmd': list(cmd), 'cwd': cwd, 'timeout': kw.get('timeout')})
        for key in ((cwd, args), cwd):
            if key in self.raises:
                raise self.raises[key]
            if key in self.raw:
                return subprocess.CompletedProcess(cmd, 0, self.raw[key].decode(kw.get('encoding') or 'utf-8'), '')
        if args == ('rev-parse', '--is-inside-work-tree'):
            inside = cwd in self.repos
            return subprocess.CompletedProcess(cmd, 0 if inside else 128, 'true\n' if inside else '', '')
        return subprocess.CompletedProcess(cmd, 0, GIT_OUT.get(args, '') + '\n', '')


def project(pid, root, **over):
    p = {'id': pid, 'name': pid, 'repoPath': root, 'branch': 'main', 'sessions': [], 'docs': dict(tc.DOCS)}
    p.update(over)
    return p


class Watcher:
    """A second connection, opened before the pass being watched. PRAGMA data_version does not move for writes
    made on the connection reading it (local/db.py:175-186), so only another connection can see whether a pass
    committed; the table contents read here are the assertion, and the pragma a cross-check."""

    def __init__(self, case, path):
        self.conn = sqlite3.connect(path)
        case.addCleanup(self.conn.close)
        self.version = self.poll()

    def poll(self):
        return self.conn.execute('PRAGMA data_version').fetchone()[0]

    def rows(self):
        return {table: sorted(self.conn.execute('SELECT id, doc FROM %s' % table))
                for table, _ in records.TABLES.values()}

    def counts(self):
        return {table: len(rows) for table, rows in self.rows().items()}


@contextlib.contextmanager
def counting():
    """Counts every db.upsert and db.delete the pass makes, by kind and id."""
    calls = {'upsert': [], 'delete': []}
    real_upsert, real_delete = db.upsert, db.delete

    def upsert(conn, kind, row):
        calls['upsert'].append((kind, row['id']))
        return real_upsert(conn, kind, row)

    def delete(conn, kind, record_id):
        calls['delete'].append((kind, record_id))
        return real_delete(conn, kind, record_id)

    db.upsert, db.delete = upsert, delete
    try:
        yield calls
    finally:
        db.upsert, db.delete = real_upsert, real_delete


@contextlib.contextmanager
def swapped(obj, name, value):
    before = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, before)


class Local:
    """A collector environment with project repositories: collector_support's transcripts and database, plus
    throwaway repositories, a data folder and a fake git."""

    def __init__(self, case):
        self.case = case
        self.e = Env(case)
        self.tmp = self.e.tmp
        self.data_dir = os.path.join(self.tmp, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.e.t.basic(sid=SID)
        self.run = FakeRun()
        self.now = time.time()

    def repo(self, pid, files=tc.FILES, is_git=True):
        root = os.path.join(self.tmp, pid)
        for rel, text in (files or {}).items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
        os.makedirs(root, exist_ok=True)
        if is_git:
            self.run.repos.add(root)
        return root

    def data(self, pid, obj):
        with io.open(os.path.join(self.data_dir, pid + '.json'), 'w', encoding='utf-8') as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))

    def cfg(self, projects):
        c = self.e.cfg()
        c['projects'] = list(projects)
        return c

    def run_pass(self, cfg, **kw):
        kw.setdefault('now', self.now)
        kw.setdefault('data_dir', self.data_dir)
        kw.setdefault('run', self.run)
        return self.e.run(cfg, **kw)

    @contextlib.contextmanager
    def cli(self):
        """The command line's own pass, with its git and its data folder pointed at this fixture."""
        with swapped(subprocess, 'run', self.run), swapped(tabs, 'DATA_DIR', self.data_dir):
            yield

    def stored(self, kind, conn=None):
        return db.stored(conn or self.e.conn, kind)

    def doc_text(self, table, record_id):
        row = self.e.conn.execute('SELECT doc FROM %s WHERE id = ?' % table, (record_id,)).fetchone()
        return row and row[0]


class TabsCase(unittest.TestCase):
    def setUp(self):
        self.l = Local(self)
        self.conn = self.l.e.conn


# ---------------------------------------------------------------- which tabs are built

class Building(TabsCase):
    def test_a_project_with_a_spec_and_a_repository_gets_all_five_tabs(self):
        root = self.l.repo('alpha')
        self.l.data('alpha', tc.DATA)
        report = self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        stored = self.l.stored('tab')
        self.assertEqual(set(stored), {'alpha.%s' % t for t in tabs.OWNED})
        self.assertEqual(report['tabs'], 5)
        self.assertEqual(stored['alpha.git']['branch'], 'work')
        self.assertEqual(stored['alpha.git']['defaultBranch'], 'main')
        self.assertEqual(stored['alpha.git']['ahead'], '2')
        self.assertEqual(stored['alpha.backlog']['pbis'][0]['state'], 'done')
        self.assertEqual(stored['alpha.spec']['generatedAt'], stored['alpha.git']['generatedAt'])

    def test_a_project_without_a_spec_gets_only_the_git_tab(self):
        root = self.l.repo('alpha', files={})
        self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        self.assertEqual(set(self.l.stored('tab')), {'alpha.git'})

    def test_a_folder_that_is_not_a_repository_gets_no_git_tab(self):
        root = self.l.repo('alpha', is_git=False)
        self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        self.assertEqual(set(self.l.stored('tab')), {'alpha.%s' % t for t in ('spec', 'assumptions', 'decisions', 'backlog')})

    def test_a_missing_repository_produces_no_tabs_and_a_warning(self):
        report = self.l.run_pass(self.l.cfg([project('alpha', os.path.join(self.l.tmp, 'nowhere'), sessions=[SID])]))
        self.assertEqual(self.l.stored('tab'), {})
        self.assertEqual((report['tabs'], report['deleted']), (0, 0))
        self.assertIn('project alpha: repository', self.l.e.err)
        self.assertIn('does not exist', self.l.e.err)

    def test_a_tab_that_never_existed_is_neither_written_nor_deleted(self):
        root = self.l.repo('alpha', files={})
        report = self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        self.assertNotIn('alpha.spec', self.l.stored('tab'))
        self.assertEqual(report['deleted'], 0)

    def test_every_git_call_carries_the_timeout(self):
        root = self.l.repo('alpha')
        self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        made = [c for c in self.l.run.calls if c['cwd'] == root]
        self.assertTrue(made)
        self.assertEqual({c['timeout'] for c in made}, {tabs.TIMEOUT})


# ---------------------------------------------------------------- keep-last and carriedSince

class Carry(TabsCase):
    def setUp(self):
        super().setUp()
        self.root = self.l.repo('alpha')
        self.cfg = self.l.cfg([project('alpha', self.root, sessions=[SID])])
        self.spec = os.path.join(self.root, tc.DOCS['spec'])

    def since(self, offset):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(self.l.now + offset)))

    def test_the_full_carry_cycle(self):
        self.l.run_pass(self.cfg)
        first = self.l.stored('tab')
        self.assertNotIn('carriedSince', first['alpha.spec'])

        os.remove(self.spec)  # the source goes missing
        self.l.run_pass(self.cfg, now=self.l.now + 60)
        carried = self.l.stored('tab')
        for tab in ('spec', 'assumptions', 'decisions', 'backlog'):
            self.assertEqual(carried['alpha.%s' % tab], dict(first['alpha.%s' % tab], carriedSince=self.since(60)))
        self.assertIn('project alpha: cannot rebuild spec, assumptions, decisions, backlog; keeping the last export',
                      self.l.e.err)

        with counting() as calls:  # still missing: the record is left exactly as it is
            self.l.run_pass(self.cfg, now=self.l.now + 120)
        self.assertEqual([i for k, i in calls['upsert'] if k == 'tab'], [])
        self.assertEqual(self.l.stored('tab'), carried)

        with io.open(self.spec, 'w', encoding='utf-8', newline='\n') as f:
            f.write(tc.SPEC)
        self.l.run_pass(self.cfg, now=self.l.now + 180)
        back = self.l.stored('tab')
        self.assertNotIn('carriedSince', back['alpha.spec'])
        stamp = collector.datetime.fromtimestamp(self.l.now + 180, collector.timezone.utc).isoformat(timespec='seconds')
        self.assertEqual(back['alpha.spec']['generatedAt'], stamp)

    def test_the_local_carried_since_equals_the_exporters(self):
        out = os.path.join(self.l.tmp, 'out')
        exporter_cfg = {'projects': [project('alpha', self.root, sessions=[SID])]}

        def export(offset):
            stamp = collector.datetime.fromtimestamp(self.l.now + offset, collector.timezone.utc).isoformat(timespec='seconds')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                export_board.main(exporter_cfg, out, self.l.data_dir, stamp)

        self.l.run_pass(self.cfg)  # both sides export the tab once, then both lose its source
        export(0)
        os.remove(self.spec)
        self.l.run_pass(self.cfg, now=self.l.now + 60)
        export(60)
        with io.open(os.path.join(out, 'projectTabs', 'alpha.spec.json'), encoding='utf-8') as f:
            exported = json.load(f)
        self.assertIn('carriedSince', exported)
        self.assertEqual(self.l.stored('tab')['alpha.spec']['carriedSince'], exported['carriedSince'])

    def test_a_git_call_that_times_out_carries_the_stored_git_tab(self):
        self.l.run_pass(self.cfg)
        first = self.l.stored('tab')['alpha.git']
        self.l.run.raises[(self.root, ('ls-files',))] = subprocess.TimeoutExpired(['git', 'ls-files'], tabs.TIMEOUT)
        self.l.run_pass(self.cfg, now=self.l.now + 60)
        self.assertEqual(self.l.stored('tab')['alpha.git'], dict(first, carriedSince=self.since(60)))
        self.assertIn('project alpha: cannot read its git repository (TimeoutExpired', self.l.e.err)


# ---------------------------------------------------------------- the network boundary

class NoNetwork(TabsCase):
    def test_a_full_pass_runs_git_and_nothing_else(self):
        root = self.l.repo('alpha')
        calls = []

        def recorder(cmd, **kw):
            calls.append(list(cmd))
            return self.l.run(cmd, **kw)

        with swapped(subprocess, 'run', recorder):
            self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]), run=None)
        self.assertTrue(calls)
        self.assertEqual({c[0] for c in calls}, {'git'})
        git_tab = self.l.stored('tab')['alpha.git']
        # Non-vacuous: the exporter would list this project's pull requests, because its origin is on github.com.
        self.assertTrue(export_board.github_origin(git_tab['remotes']))
        self.assertNotIn('pulls', git_tab)


# ---------------------------------------------------------------- the shapes

class Shapes(TabsCase):
    def test_every_record_written_validates_and_round_trips(self):
        root = self.l.repo('alpha')
        self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID], statusDoc='meta/status'),
                                    project('beta', self.l.repo('beta'), sessions=[])]))
        paths = []
        for kind in ('tab', 'status'):
            written = self.l.stored(kind)
            self.assertTrue(written)
            for record_id, doc in written.items():
                with self.subTest(kind=kind, id=record_id):
                    self.assertEqual(records.validate(kind, doc), [])
                    self.assertEqual(records.from_row(kind, records.to_row(kind, record_id, doc)), doc)
                    paths.append(records.store_path(kind, record_id))
        self.assertIn('projectTabs/alpha.spec', paths)
        self.assertIn('meta/status', paths)
        self.assertIn('status/beta', paths)

    def test_the_shapes_the_pass_relies_on_are_unchanged(self):
        # Containment, not equality: TAB_NAMES also holds the suffixes of the other writer of projectTabs.
        self.assertGreaterEqual(set(records.TAB_NAMES), set(tabs.OWNED))
        self.assertEqual(records.SHAPES['tab'], {'required': {'generatedAt': 'str'}, 'optional': {'source': 'str'}})
        self.assertEqual(records.SHAPES['status'], {'required': {}, 'optional': {
            'title': 'str', 'message': 'str', 'live': 'bool', 'updatedAt': 'str', 'metrics': 'object'}})
        self.assertEqual(records.TABLES['tab'], ('project_tabs', ('id', 'project', 'tab', 'doc')))
        self.assertEqual(records.TABLES['status'], ('statuses', ('id', 'doc')))
        self.assertEqual(schema.SCHEMA_VERSION, 1)


# ---------------------------------------------------------------- the other writer's tab suffix

class ForeignSuffixes(TabsCase):
    def test_owned_is_exactly_the_exporters_tabs(self):
        self.assertEqual(tabs.OWNED, export_board.TABS)

    def test_a_findings_record_is_left_exactly_as_it_is(self):
        root = self.l.repo('alpha')
        db.upsert(self.conn, 'tab', records.to_row('tab', 'alpha.findings', FINDINGS))
        before = self.l.doc_text('project_tabs', 'alpha.findings')
        with counting() as calls:
            self.l.run_pass(self.l.cfg([project('alpha', root, sessions=[SID])]))
        self.assertEqual(self.l.doc_text('project_tabs', 'alpha.findings'), before)
        self.assertEqual([i for k, i in calls['delete'] if i == 'alpha.findings'], [])
        self.assertEqual([i for k, i in calls['upsert'] if i == 'alpha.findings'], [])
        self.assertEqual(set(self.l.stored('tab')), {'alpha.%s' % t for t in tabs.OWNED} | {'alpha.findings'})

    def test_a_project_whose_only_stored_tab_is_findings_does_not_trip_the_guard(self):
        db.upsert(self.conn, 'tab', records.to_row('tab', 'gamma.findings', FINDINGS))
        cfg = self.l.cfg([project('alpha', self.l.repo('alpha'), sessions=[SID]),
                          project('gamma', '', sessions=[])])
        report = self.l.run_pass(cfg)  # no --allow-mass-delete: an empty owned group must not refuse the pass
        self.assertEqual(report['tabs'], 5)
        self.assertEqual(self.l.doc_text('project_tabs', 'gamma.findings') is not None, True)


# ---------------------------------------------------------------- status records

class Status(TabsCase):
    def setUp(self):
        super().setUp()
        self.root = self.l.repo('alpha')
        self.other = self.l.repo('beta')
        self.clock = ['2026-09-12T09:00:00+00:00']

    def tick(self):
        return collector.datetime.fromisoformat(self.clock[0])

    def cfg(self, *projects):
        return self.l.cfg(projects or (project('alpha', self.root, sessions=[SID], statusDoc='meta/status'),
                                       project('beta', self.other, sessions=[])))

    def go(self, cfg=None, **kw):
        return self.l.run_pass(cfg or self.cfg(), clock=self.tick, **kw)

    def running_session(self):
        self.l.e.t.session(SID2, [tes.user(0, 'review it'), tes.launch(1, 'toolu_run')])
        self.l.e.t.agent(SID2, 'arun', [tes.user(1, 'task'), tes.reply(2, 'm-run', text='Reading the diff')],
                         {'agentType': 'review-agents:code-reviewer', 'description': 'Review', 'toolUseId': 'toolu_run'})

    def test_both_status_forms_are_written_with_live_and_updated_at(self):
        report = self.go()
        stored = self.l.stored('status')
        self.assertEqual(set(stored), {'meta/status', 'status/beta'})
        self.assertEqual(stored['meta/status'], {'live': False, 'updatedAt': self.clock[0]})
        self.assertEqual(report['statuses'], 2)

    def test_live_follows_a_running_run_of_that_project(self):
        self.running_session()
        self.go(self.cfg(project('alpha', self.root, sessions=[SID2], statusDoc='meta/status'),
                         project('beta', self.other, sessions=[SID])))
        stored = self.l.stored('status')
        self.assertTrue(stored['meta/status']['live'])
        self.assertFalse(stored['status/beta']['live'])

    def test_a_stored_title_message_and_metrics_survive_a_rewrite(self):
        hand = {'title': 'Local tabs', 'message': 'Building', 'metrics': {'tests': 265}}
        db.upsert(self.conn, 'status', records.to_row('status', 'meta/status', hand))
        self.go()
        self.assertEqual(self.l.stored('status')['meta/status'], dict(hand, live=False, updatedAt=self.clock[0]))

    def test_updated_at_does_not_move_on_a_pass_whose_only_difference_is_generated_at(self):
        self.go()
        first = self.l.stored('status')
        self.clock[0] = '2026-09-12T10:00:00+00:00'
        report = self.go(now=self.l.now + 60)
        self.assertEqual(self.l.stored('status'), first)
        self.assertEqual(report['statuses'], 0)

    def test_updated_at_moves_for_the_project_that_changed_and_no_other(self):
        self.go()
        first = self.l.stored('status')
        with io.open(os.path.join(self.root, tc.DOCS['spec']), 'a', encoding='utf-8', newline='\n') as f:
            f.write('\n- **G-2** Ship it twice.\n')
        self.clock[0] = '2026-09-12T10:00:00+00:00'
        self.go(now=self.l.now + 60)
        stored = self.l.stored('status')
        self.assertEqual(stored['meta/status']['updatedAt'], self.clock[0])
        self.assertEqual(stored['status/beta'], first['status/beta'])

    def test_updated_at_moves_when_live_flips(self):
        self.running_session()
        cfg = self.cfg(project('alpha', self.root, sessions=[SID2], statusDoc='meta/status'),
                       project('beta', self.other, sessions=[SID]))
        self.go(cfg)
        self.assertTrue(self.l.stored('status')['meta/status']['live'])
        self.clock[0] = '2026-09-12T10:00:00+00:00'
        # Far enough past the running window that the run is judged killed, so live flips with nothing else new.
        self.go(cfg, now=self.l.now + 4000)
        stored = self.l.stored('status')
        self.assertFalse(stored['meta/status']['live'])
        self.assertEqual(stored['meta/status']['updatedAt'], self.clock[0])

    def test_no_pass_deletes_a_status_record_even_for_a_project_removed_from_the_config(self):
        gone = project('gamma', self.l.repo('gamma'), sessions=[])
        self.go(self.cfg(project('alpha', self.root, sessions=[SID], statusDoc='meta/status'), gone))
        self.assertIn('status/gamma', self.l.stored('status'))
        before = self.l.doc_text('statuses', 'status/gamma')
        self.assertIsNotNone(before)
        with counting() as calls:
            self.go(allow_mass_delete=True)
        self.assertEqual([i for k, i in calls['delete'] if k == 'status'], [])
        self.assertEqual(self.l.doc_text('statuses', 'status/gamma'), before)
        self.assertEqual(records.validate('status', self.l.stored('status')['status/gamma']), [])


# ---------------------------------------------------------------- deletion, the guard and errors

class Deletion(TabsCase):
    def setUp(self):
        super().setUp()
        self.root = self.l.repo('alpha')
        self.other = self.l.repo('beta')
        self.both = self.l.cfg([project('alpha', self.root, sessions=[SID]), project('beta', self.other, sessions=[])])
        self.one = self.l.cfg([project('beta', self.other, sessions=[SID])])

    def test_tabs_go_only_when_their_project_leaves_the_config_and_every_reason_is_other(self):
        first = self.l.run_pass(self.both)
        self.assertEqual(first['aged'], 0)
        with counting() as calls:
            report = self.l.run_pass(self.one, now=self.l.now + 60, allow_mass_delete=True)
        deleted = {i for k, i in calls['delete'] if k == 'tab'}
        self.assertTrue(deleted >= {'alpha.%s' % t for t in tabs.OWNED})
        self.assertEqual(report['aged'], 0)  # a tab is never age-pruned
        self.assertEqual(report['deleted'], len(calls['delete']))
        self.assertEqual(set(self.l.stored('tab')), {'beta.%s' % t for t in tabs.OWNED})

    def test_deleting_every_tab_of_a_project_is_refused_and_writes_nothing(self):
        self.l.run_pass(self.both)
        watcher = Watcher(self, self.l.e.db_path)
        before, counts = watcher.rows(), watcher.counts()
        with counting() as calls:
            with self.assertRaises(collector.Refusal) as cm:
                self.l.run_pass(self.one, now=self.l.now + 60)
        self.assertIn('every tab of project alpha (check its repoPath and docs in board.config.json)', str(cm.exception))
        self.assertIn('project alpha', str(cm.exception))
        self.assertEqual((calls['upsert'], calls['delete']), ([], []))
        self.assertEqual(watcher.counts(), counts)
        self.assertEqual(watcher.rows(), before)
        self.assertEqual(watcher.poll(), watcher.version)  # a cross-check: no other connection committed either

    def test_allow_mass_delete_applies_the_deletions_from_the_command_line(self):
        self.l.run_pass(self.both)
        with self.l.cli():
            code = self.l.e.main(['--once', '--allow-mass-delete'], cfg=self.one, now=self.l.now + 60)
        self.assertEqual(code, 0, self.l.e.err)
        self.l.e.reconnect()
        self.assertEqual(set(self.l.stored('tab')), {'beta.%s' % t for t in tabs.OWNED})

    def test_deleting_some_of_a_projects_tabs_is_not_refused(self):
        report = self.l.run_pass(self.both)
        self.assertTrue(report['tabs'])
        stored = {'tab': self.l.stored('tab'), 'session': {}, 'run': {}, 'project': {}}
        p = collector._Pass(self.conn, {'days': 7, 'exclude': [], 'projects': []}, self.l.now, {'markers': {}})
        p.results = {SID: True}
        some = [('tab', 'alpha.spec', 'other'), ('tab', 'alpha.git', 'other')]
        p.guard(stored, some)  # no raise
        with self.assertRaises(collector.Refusal):
            p.guard(stored, [('tab', 'alpha.%s' % t, 'other') for t in tabs.OWNED])


class PerProjectFailures(TabsCase):
    """A failure reading one project's sources costs that project's tabs for the pass and nothing else."""

    def setUp(self):
        super().setUp()
        self.alpha = self.l.repo('alpha')
        self.beta = self.l.repo('beta')
        self.cfg = self.l.cfg([project('alpha', self.alpha, sessions=[SID]), project('beta', self.beta, sessions=[])])
        self.first = self.l.run_pass(self.cfg)

    def failing_read(self, error, part):
        real = export_board.read

        def read(root, rel):
            if os.path.normcase(root) == os.path.normcase(self.alpha) and part in rel.replace('\\', '/'):
                raise error
            return real(root, rel)
        return swapped(export_board, 'read', read)

    def check_confined(self, warning):
        stored = self.l.stored('tab')
        self.assertEqual(set(stored), {'%s.%s' % (pid, t) for pid in ('alpha', 'beta') for t in tabs.OWNED})
        for tab in ('spec', 'assumptions', 'decisions', 'backlog'):
            self.assertIn('carriedSince', stored['alpha.%s' % tab])
            self.assertNotIn('carriedSince', stored['beta.%s' % tab])
        self.assertIsNotNone(self.l.e.last_refresh())
        self.assertTrue(self.l.stored('session') and self.l.stored('run') and self.l.stored('project'))
        self.assertIn(warning, self.l.e.err)

    def test_a_permission_error_on_the_adr_folder_is_confined(self):
        with self.failing_read(PermissionError(13, 'denied'), 'docs/adr'):
            with self.l.cli():
                code = self.l.e.main(['--once'], cfg=self.cfg, now=self.l.now + 60)
        self.assertEqual(code, 0, self.l.e.err)
        self.l.e.reconnect()
        self.check_confined('project alpha: cannot read its documents (PermissionError')

    def test_a_non_utf8_spec_file_is_confined(self):
        bad = UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid start byte')
        with self.failing_read(bad, 'docs/spec.md'):
            self.l.run_pass(self.cfg, now=self.l.now + 60)
        self.check_confined('project alpha: cannot read its documents (UnicodeDecodeError')

    def test_a_git_timeout_is_confined(self):
        self.l.run.raises[self.alpha] = subprocess.TimeoutExpired(['git', 'status'], tabs.TIMEOUT)
        self.l.run_pass(self.cfg, now=self.l.now + 60)
        stored = self.l.stored('tab')
        self.assertIn('carriedSince', stored['alpha.git'])
        self.assertNotIn('carriedSince', stored['alpha.spec'])
        self.assertNotIn('carriedSince', stored['beta.git'])
        self.assertIn('project alpha: cannot read its git repository (TimeoutExpired', self.l.e.err)

    def test_non_utf8_git_output_is_confined(self):
        # A commit subject written under a non-UTF-8 i18n.commitEncoding: git prints bytes the strict utf-8
        # decode of the log call cannot read. The whole pass, not one project, is what this used to cost.
        self.l.run.raw[(self.alpha, ('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict'))] = \
            b'abc1234|2026-09-10T10:00:00+01:00|Caf\xe9 fix\n'
        watcher = Watcher(self, self.l.e.db_path)
        with self.l.cli():
            code = self.l.e.main(['--once'], cfg=self.cfg, now=self.l.now + 60)
        self.assertEqual(code, 0, self.l.e.err)
        self.assertGreater(watcher.poll(), watcher.version)  # the pass committed rather than writing nothing
        self.l.e.reconnect()
        stored = self.l.stored('tab')
        self.assertIn('carriedSince', stored['alpha.git'])
        self.assertNotIn('carriedSince', stored['alpha.spec'])
        self.assertNotIn('carriedSince', stored['beta.git'])
        self.assertEqual(stored['beta.git']['branch'], 'work')  # the healthy project was built, not carried
        self.assertIsNotNone(self.l.e.last_refresh())
        self.assertIn('project alpha: cannot read its git repository (UnicodeDecodeError', self.l.e.err)

    def test_a_malformed_project_data_file_fails_the_whole_pass_and_writes_nothing(self):
        self.l.data('alpha', '{"buildState": {')
        watcher = Watcher(self, self.l.e.db_path)
        before, counts = watcher.rows(), watcher.counts()
        with counting() as calls:
            with self.assertRaises(ValueError):
                self.l.run_pass(self.cfg, now=self.l.now + 60)
        self.assertEqual((calls['upsert'], calls['delete']), ([], []))
        self.assertEqual(watcher.counts(), counts)
        self.assertEqual(watcher.rows(), before)


class PerRecordFailure(TabsCase):
    def test_a_tab_that_cannot_be_stored_is_skipped_and_its_stored_version_kept(self):
        root = self.l.repo('alpha')
        cfg = self.l.cfg([project('alpha', root, sessions=[SID])])
        self.l.run_pass(cfg)
        first = self.l.stored('tab')['alpha.spec']
        with io.open(os.path.join(root, tc.DOCS['spec']), 'a', encoding='utf-8', newline='\n') as f:
            f.write('\n- **G-9** A goal that changes the document.\n')
        real = records.to_row

        def to_row(kind, record_id, doc):
            if (kind, record_id) == ('tab', 'alpha.spec'):
                raise ValueError('refused for the test')
            return real(kind, record_id, doc)

        with swapped(records, 'to_row', to_row):
            self.l.run_pass(cfg, now=self.l.now + 60)
        self.assertIn('tab alpha.spec not stored (ValueError', self.l.e.err)
        self.assertEqual(self.l.stored('tab')['alpha.spec'], first)
        self.assertEqual(len(self.l.stored('tab')), 5)
        self.assertTrue(self.l.stored('session'))


if __name__ == '__main__':
    unittest.main()
