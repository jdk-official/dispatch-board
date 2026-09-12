"""The collector's tab and status records equal the board's documents for the same repositories, config, data
files and now: the tabs export_board.py writes (apart from generatedAt and pulls), the carriedSince it marks a
kept tab with, the tab suffixes it leaves to the other writer, and the status rule refresh.py applies.

Built on test_conformance.Fixture, which is imported and consumed exactly as it is: it is the one file
local/tests holds that another work item also touches, so nothing here edits it.
"""
import contextlib, io, json, os, subprocess, unittest
from datetime import datetime, timezone

from collector_support import Env
import collector  # noqa: E402
import db  # noqa: E402
import export_board  # noqa: E402
import export_catalogue  # noqa: E402
import export_sessions as es  # noqa: E402
import records  # noqa: E402
import refresh  # noqa: E402
import test_conformance as tc  # noqa: E402

HAS_GIT = tc.HAS_GIT
NOW = tc.NOW
T0 = datetime.fromisoformat(NOW).timestamp()  # the same instant as NOW, for the exporters that take an epoch
PRS = [{'number': 7, 'title': 'Add the widget', 'state': 'OPEN', 'url': 'https://github.com/owner/repo/pull/7',
        'headRefName': 'work', 'updatedAt': '2026-09-10T10:00:00Z'}]
IGNORED = ('generatedAt', 'pulls')  # generatedAt is stamped per run; pulls is a network call the collector never makes


def fake_gh(cmd, **kw):
    """Stands in for subprocess.run when export_board lists pull requests, so no test reaches the real gh."""
    return subprocess.CompletedProcess(cmd, 0, json.dumps(PRS), '')


def compare(doc):
    return {k: v for k, v in doc.items() if k not in IGNORED}


class Board:
    """A conformance Fixture with the exporters and the collector driven over it side by side."""

    def __init__(self, case, fixture=None):
        self.f = fixture or tc.Fixture()
        case.addCleanup(self.f.cleanup)
        self.f.transcripts()
        self.f.repos()
        self.f.marketplace()
        if HAS_GIT:  # an origin on github.com, so the exporter really does list pull requests for alpha
            tc.git(self.f.alpha, 'remote', 'add', 'origin', 'https://github.com/owner/repo.git')
        self.e = Env(case)
        self.cfg = self.f.config()
        self.err = ''

    def export_board(self, now=NOW):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = export_board.main(self.cfg, self.f.out, self.f.data_dir, now, run=fake_gh)
        self.err = err.getvalue()
        assert code == 0, self.err
        return self.tabs()

    def export_all(self, now=NOW, t0=T0):
        self.export_board(now)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert es.main(self.cfg, self.f.out, self.f.root, t0) == 0
            assert export_catalogue.main(self.cfg, self.f.out, now) == 0

    def plan(self):
        """refresh.plan's writes, keyed by store path, with the plan committed as a push."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            planned = refresh.plan(self.f.out)
        writes = planned['writes']
        writes = [w for batch in writes for w in batch] if writes and isinstance(writes[0], list) else writes
        refresh.commit(self.f.out)
        return {'%s/%s' % (w['collection'], w['doc_id']): w for w in writes}

    def tabs(self):
        """{tab id: document} from out/projectTabs."""
        folder, found = os.path.join(self.f.out, 'projectTabs'), {}
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            with io.open(os.path.join(folder, name), encoding='utf-8') as fh:
                found[name[:-len('.json')]] = json.load(fh)
        return found

    def collect(self, t0=T0, **kw):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            report = collector.run_pass(self.e.conn, self.cfg, projects_root=self.f.root, now=t0,
                                        data_dir=self.f.data_dir, **kw)
        self.err = err.getvalue()
        return report

    def stored(self, kind):
        return db.stored(self.e.conn, kind)


class TabEquivalence(unittest.TestCase):
    def setUp(self):
        self.b = Board(self)

    def test_one_pass_holds_the_documents_the_exporter_wrote(self):
        exported = self.b.export_board()
        self.b.collect()
        stored = self.b.stored('tab')
        self.assertEqual(set(stored), set(exported))
        # Non-vacuous on all three counts: alpha has a spec and a git repository, beta a spec and none, and
        # gamma neither, so a project with no tabs at all is covered too.
        self.assertIn('alpha.spec', stored)
        self.assertEqual(HAS_GIT, 'alpha.git' in stored)
        self.assertNotIn('beta.git', stored)
        self.assertFalse([i for i in stored if i.startswith('gamma.')])
        for record_id, doc in sorted(exported.items()):
            with self.subTest(record_id):
                self.assertEqual(compare(stored[record_id]), compare(doc))

    @unittest.skipUnless(HAS_GIT, 'git is not installed')
    def test_the_exporter_listed_pull_requests_and_the_collector_did_not(self):
        exported = self.b.export_board()
        self.b.collect()
        self.assertEqual(exported['alpha.git']['pulls'][0]['number'], 7)
        self.assertNotIn('pulls', self.b.stored('tab')['alpha.git'])

    def test_both_sides_carry_a_tab_whose_source_went_missing_and_agree_on_carried_since(self):
        self.b.export_board()
        self.b.collect()
        os.rename(self.b.f.alpha, self.b.f.alpha + '-moved')
        later = '2026-09-11T13:00:00+00:00'
        exported = self.b.export_board(later)
        self.b.collect(t0=datetime.fromisoformat(later).timestamp())
        stored = self.b.stored('tab')
        carried = [i for i in exported if i.startswith('alpha.')]
        self.assertTrue(carried)
        for record_id in carried:
            with self.subTest(record_id):
                self.assertEqual(stored[record_id]['carriedSince'], exported[record_id]['carriedSince'])
                self.assertEqual(compare(stored[record_id]), compare(exported[record_id]))


class OwnershipEquivalence(unittest.TestCase):
    """The two writers of projectTabs agree on which suffixes each owns: export_board leaves the findings
    document alone on disk, and a collector pass leaves the equivalent record alone in the database."""

    def setUp(self):
        self.b = Board(self, tc.FindingsFixture())

    def test_neither_side_touches_the_findings_tab(self):
        self.b.export_all()
        path = os.path.join(self.b.f.out, 'projectTabs', 'alpha.findings.json')
        self.assertTrue(os.path.isfile(path))
        with io.open(path, 'rb') as f:
            before = f.read()
        db.upsert(self.b.e.conn, 'tab', records.to_row('tab', 'alpha.findings', json.loads(before.decode('utf-8'))))
        stored_before = self.b.e.conn.execute("SELECT doc FROM project_tabs WHERE id = 'alpha.findings'").fetchone()[0]

        self.b.export_board()
        self.b.collect()

        with io.open(path, 'rb') as f:
            self.assertEqual(f.read(), before)
        after = self.b.e.conn.execute("SELECT doc FROM project_tabs WHERE id = 'alpha.findings'").fetchone()[0]
        self.assertEqual(after, stored_before)
        self.assertIn('alpha.spec', self.b.stored('tab'))


class StatusEquivalence(unittest.TestCase):
    """refresh.plan's status documents and the collector's status records agree on live, and on whether a
    pass moved updatedAt."""

    def setUp(self):
        self.b = Board(self)
        self.hour = [0]

    def board_pass(self, t0=T0):
        self.b.export_all(t0=t0)
        planned = self.b.plan()
        live = {}
        for key, write in planned.items():
            if key == refresh.META_STATUS or key.startswith('status/'):
                with io.open(write['file_path'], encoding='utf-8') as f:
                    live[key] = json.load(f)['live']
        return set(live), live

    def local_pass(self, t0=T0):
        # A clock an hour further on for every pass, so a status the pass rewrites always gets a new updatedAt
        # and "moved" cannot be read as "not written".
        self.hour[0] += 1
        before = self.b.stored('status')
        self.b.collect(t0=t0, clock=lambda: datetime(2026, 9, 11, 12 + self.hour[0], tzinfo=timezone.utc))
        after = self.b.stored('status')
        moved = {k for k, doc in after.items() if before.get(k, {}).get('updatedAt') != doc['updatedAt']}
        return moved, {k: after[k]['live'] for k in moved}

    def check(self, label, t0=T0):
        board_moved, board_live = self.board_pass(t0)
        local_moved, local_live = self.local_pass(t0)
        self.assertEqual(local_moved, board_moved, label)
        self.assertEqual(local_live, board_live, label)
        return board_moved

    def test_the_first_pass_writes_every_project_and_a_quiet_pass_writes_none(self):
        first = self.check('first pass')
        self.assertEqual(first, {'meta/status', 'status/beta', 'status/gamma'})
        self.assertEqual(self.check('quiet pass'), set())

    def test_a_run_of_one_project_changing_moves_only_that_projects_status(self):
        self.check('first pass')
        self.b.f.agent(tc.SID_A, 'anew', [tc.user(6, 'task'), tc.reply(7, 'm-new', text='All green. DONE')],
                       {'agentType': 'engineering-agents:code-writer', 'description': 'A new run', 'toolUseId': 'toolu_new'})
        self.assertEqual(self.check('one project changed'), {'meta/status'})

    def test_deleting_a_linked_run_moves_that_projects_status(self):
        self.check('first pass')
        os.remove(os.path.join(self.b.f.root, tc.FOLDER, tc.SID_A, 'subagents', 'agent-agp.jsonl'))
        self.assertEqual(self.check('a linked run deleted'), {'meta/status'})


if __name__ == '__main__':
    unittest.main()
