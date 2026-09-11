"""Tests for exporters/refresh.py's plan and commit steps, run against a synthetic out/ in a temporary
directory. The exporters are never run: main() is given a stub in their place.
"""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exporters'))
import refresh as rf  # noqa: E402


class Out:
    """A throwaway out/ holding project p (status in meta/status, its five tabs) and two sessions: b (linked
    to p) and o (linked to nothing), with two runs each."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.out = os.path.join(self.tmp, 'out')
        self.doc('projects', 'p', {'name': 'p', 'statusDoc': 'meta/status', 'sessions': ['b']})
        for tab in rf.TABS:
            self.doc('projectTabs', 'p.' + tab, {'tab': tab, 'generatedAt': '2026-09-10T00:00:00+00:00'})
        self.doc('sessions', 'b', {'title': 'build', 'project': 'p'})
        self.doc('sessions', 'o', {'title': 'other', 'project': None})
        for rid, sid, pid in (('rb1', 'b', 'p'), ('rb2', 'b', 'p'), ('ro1', 'o', None), ('ro2', 'o', None)):
            self.doc('runs', rid, {'session': sid, 'project': pid, 'kind': 'done'})

    def add_project_q(self):
        """A second project whose status document is status/q, with one session and one run."""
        self.doc('projects', 'q', {'name': 'q', 'statusDoc': 'status/q', 'sessions': ['qs']})
        self.doc('projectTabs', 'q.git', {'tab': 'git'})
        self.doc('sessions', 'qs', {'title': 'q build', 'project': 'q'})
        self.doc('runs', 'rq1', {'session': 'qs', 'project': 'q', 'kind': 'done'})

    def path(self, coll, name):
        return os.path.join(self.out, *([coll] if coll else []), name + '.json')

    def doc(self, coll, name, obj):
        p = self.path(coll, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f)

    def read(self, coll, name):
        with io.open(self.path(coll, name), encoding='utf-8') as f:
            return json.load(f)

    def edit(self, coll, name, **changes):
        obj = self.read(coll, name)
        obj.update(changes)
        self.doc(coll, name, obj)

    def remove(self, coll, name):
        os.remove(self.path(coll, name))

    @property
    def pending(self):
        return os.path.join(self.out, '.pending.json')

    def pushed(self):
        """Plan and commit everything, as after a successful write_db."""
        rf.plan(self.out)
        rf.commit(self.out)

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def writes(plan):
    return plan['writes'] if plan['batches'] == 1 else [w for b in plan['writes'] for w in b]


def keys(plan):
    return {(w['op'], w['collection'] + '/' + w['doc_id']) for w in writes(plan)}


STATUS = ('update', 'meta/status')


class Plan(unittest.TestCase):
    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)

    def test_first_plan_sets_everything_and_the_status(self):
        p = rf.plan(self.o.out)
        k = keys(p)
        self.assertEqual(len(k), 1 + 5 + 2 + 4 + 1)
        self.assertIn(('set', 'projects/p'), k)
        self.assertIn(('set', 'projectTabs/p.spec'), k)
        self.assertIn(('set', 'runs/ro1'), k)
        self.assertIn(STATUS, k)
        self.assertTrue(os.path.exists(self.o.pending))

    def test_dotted_doc_ids_keep_their_file(self):
        w = [x for x in writes(rf.plan(self.o.out)) if x['doc_id'] == 'p.spec'][0]
        self.assertEqual((w['collection'], w['file_path']), ('projectTabs', self.o.path('projectTabs', 'p.spec').replace('\\', '/')))

    def test_commit_then_nothing_to_push(self):
        rf.plan(self.o.out)
        self.assertEqual(rf.commit(self.o.out), 14)  # 12 documents plus p's live flag and document list
        self.assertFalse(os.path.exists(self.o.pending))
        self.assertIsNone(rf.plan(self.o.out))

    def test_nothing_to_push_removes_a_stale_pending_file(self):
        self.o.pushed()
        with io.open(self.o.pending, 'w', encoding='utf-8') as f:
            json.dump({'state': {'runs/zz': 'stale'}}, f)
        self.assertIsNone(rf.plan(self.o.out))
        self.assertFalse(os.path.exists(self.o.pending))

    def test_generated_at_alone_is_not_a_change(self):
        self.o.pushed()
        self.o.edit('projectTabs', 'p.spec', generatedAt='2026-09-11T00:00:00+00:00')
        self.assertIsNone(rf.plan(self.o.out))

    def test_vanished_run_is_deleted(self):
        self.o.pushed()
        self.o.remove('runs', 'ro1')
        self.assertEqual(keys(rf.plan(self.o.out)), {('delete', 'runs/ro1')})

    def test_vanished_project_tab_is_deleted(self):
        self.o.pushed()
        self.o.remove('projectTabs', 'p.git')
        self.assertEqual(keys(rf.plan(self.o.out)), {('delete', 'projectTabs/p.git'), STATUS})

    def test_vanished_project_is_deleted_with_the_flag(self):
        self.o.add_project_q()
        self.o.pushed()
        self.o.remove('projects', 'q')
        self.o.remove('projectTabs', 'q.git')
        self.assertEqual(keys(rf.plan(self.o.out, allow_mass_delete=True)), {('delete', 'projects/q'), ('delete', 'projectTabs/q.git')})

    def test_retired_tabs_are_never_deleted(self):
        self.o.pushed()
        pushed = rf.load(os.path.join(self.o.out, '.pushed.json'), {})
        pushed.update({'tabs/spec': 'x', 'tabs/usage': 'y'})  # recorded by the page's earlier layout
        rf.save(os.path.join(self.o.out, '.pushed.json'), pushed)
        self.assertIsNone(rf.plan(self.o.out))

    def test_unmanaged_collections_are_never_deleted(self):
        self.o.pushed()
        pushed = rf.load(os.path.join(self.o.out, '.pushed.json'), {})
        pushed.update({'answers/1': 'x', 'meta/other': 'y'})
        rf.save(os.path.join(self.o.out, '.pushed.json'), pushed)
        self.assertIsNone(rf.plan(self.o.out))

    def test_batches_past_the_limit(self):
        for i in range(60):
            self.o.doc('runs', 'x%02d' % i, {'session': 'o', 'kind': 'done'})
        p = rf.plan(self.o.out)
        self.assertEqual(p['batches'], 2)
        self.assertEqual(len(p['writes'][0]), rf.BATCH)


class UpdatedAt(unittest.TestCase):
    """A project's status updatedAt moves only when that project's data changed or its live flag flipped."""

    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)
        self.o.pushed()

    def test_unlinked_session_change_does_not_bump(self):
        self.o.edit('sessions', 'o', title='renamed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'sessions/o')})

    def test_unlinked_run_change_does_not_bump(self):
        self.o.edit('runs', 'ro1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/ro1')})

    def test_running_unlinked_run_does_not_bump(self):
        self.o.edit('runs', 'ro1', kind='running')
        p = rf.plan(self.o.out)
        self.assertEqual(keys(p), {('set', 'runs/ro1')})
        self.assertFalse(p['live'])

    def test_linked_session_change_bumps(self):
        self.o.edit('sessions', 'b', title='renamed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'sessions/b'), STATUS})

    def test_linked_run_change_bumps(self):
        self.o.edit('runs', 'rb1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/rb1'), STATUS})

    def test_deleted_linked_run_bumps(self):
        self.o.remove('runs', 'rb1')
        self.assertEqual(keys(rf.plan(self.o.out)), {('delete', 'runs/rb1'), STATUS})

    def test_project_tab_change_bumps(self):
        self.o.edit('projectTabs', 'p.backlog', tab='changed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'projectTabs/p.backlog'), STATUS})

    def test_project_document_change_bumps(self):
        self.o.edit('projects', 'p', runs=3)
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'projects/p'), STATUS})

    def test_live_flip_bumps(self):
        self.o.edit('runs', 'rb1', kind='running')
        p = rf.plan(self.o.out)
        self.assertTrue(p['live'])
        status = self.o.read('meta', 'status')
        self.assertTrue(status['live'])
        self.assertIn('updatedAt', status)


class ProjectStatus(unittest.TestCase):
    """Each project has its own status document; meta/status stays the first project's."""

    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)
        self.o.add_project_q()

    def test_first_write_of_a_new_status_document_is_a_set(self):
        k = keys(rf.plan(self.o.out))
        self.assertIn(('set', 'status/q'), k)
        self.assertIn(STATUS, k)  # meta/status holds hand-written fields, so it is only ever merged into
        self.assertEqual(set(self.o.read('status', 'q')), {'live', 'updatedAt'})

    def test_later_writes_merge(self):
        self.o.pushed()
        self.o.edit('runs', 'rq1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/rq1'), ('update', 'status/q')})

    def test_a_change_bumps_only_its_own_project(self):
        self.o.pushed()
        self.o.edit('runs', 'rb1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/rb1'), STATUS})
        rf.commit(self.o.out)
        self.o.edit('projectTabs', 'q.git', tab='changed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'projectTabs/q.git'), ('update', 'status/q')})

    def test_live_is_per_project(self):
        self.o.pushed()
        self.o.edit('runs', 'rq1', kind='running')
        p = rf.plan(self.o.out)
        self.assertEqual(keys(p), {('set', 'runs/rq1'), ('update', 'status/q')})
        self.assertTrue(p['live'])
        self.assertTrue(self.o.read('status', 'q')['live'])
        self.assertFalse(self.o.read('meta', 'status')['live'])

    def test_project_without_a_status_doc_field_uses_status_collection(self):
        self.o.edit('projects', 'q', statusDoc=None)
        self.assertIn(('set', 'status/q'), keys(rf.plan(self.o.out)))


class Save(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, '.pushed.json')

    def test_replaces_the_file_and_leaves_no_temp_file(self):
        rf.save(self.path, {'a': 1})
        rf.save(self.path, {'a': 2})
        self.assertEqual(rf.load(self.path, None), {'a': 2})
        self.assertEqual(os.listdir(self.tmp), ['.pushed.json'])

    def test_a_failed_write_keeps_the_previous_file(self):
        rf.save(self.path, {'runs/x': 'digest'})
        with self.assertRaises(TypeError):
            rf.save(self.path, {'runs/x': object()})  # not serialisable
        self.assertEqual(rf.load(self.path, None), {'runs/x': 'digest'})
        self.assertEqual(os.listdir(self.tmp), ['.pushed.json'])


class MassDelete(unittest.TestCase):
    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)
        self.o.pushed()

    def test_more_than_half_is_refused(self):
        for rid in ('rb1', 'rb2', 'ro1', 'ro2'):
            self.o.remove('runs', rid)
        with self.assertRaises(rf.MassDelete):
            rf.plan(self.o.out)
        self.assertFalse(os.path.exists(self.o.pending))

    def test_refusal_removes_a_stale_pending_file(self):
        rf.plan(self.o.out)  # leaves nothing pending: no change since the push
        with io.open(self.o.pending, 'w', encoding='utf-8') as f:
            json.dump({'state': {}}, f)
        for rid in ('rb1', 'rb2', 'ro1', 'ro2'):
            self.o.remove('runs', rid)
        with self.assertRaises(rf.MassDelete):
            rf.plan(self.o.out)
        self.assertFalse(os.path.exists(self.o.pending))

    def test_zero_sessions_is_refused(self):
        self.o.remove('sessions', 'o')
        self.o.remove('sessions', 'b')
        with self.assertRaises(rf.MassDelete):
            rf.plan(self.o.out)

    def test_zero_sessions_refused_even_for_a_small_delete(self):
        for i in range(10):
            self.o.doc('runs', 'n%d' % i, {'session': 'b', 'kind': 'done'})
        self.o.pushed()
        self.o.remove('sessions', 'o')
        self.o.remove('sessions', 'b')  # 2 of 16 pushed documents, but the export has no sessions at all
        with self.assertRaises(rf.MassDelete):
            rf.plan(self.o.out)

    def test_losing_every_tab_of_a_project_is_refused(self):
        for tab in rf.TABS:
            self.o.remove('projectTabs', 'p.' + tab)
        with self.assertRaises(rf.MassDelete) as cm:
            rf.plan(self.o.out)
        self.assertIn('every tab of project p', str(cm.exception))
        self.assertFalse(os.path.exists(self.o.pending))
        self.assertIn(('delete', 'projectTabs/p.spec'), keys(rf.plan(self.o.out, allow_mass_delete=True)))

    def test_losing_the_only_tab_of_a_second_project_is_refused(self):
        self.o.add_project_q()
        self.o.pushed()
        self.o.remove('projectTabs', 'q.git')
        with self.assertRaises(rf.MassDelete):
            rf.plan(self.o.out)
        self.assertFalse(os.path.exists(self.o.pending))

    def test_losing_some_tabs_of_a_project_goes_through(self):
        for tab in ('git', 'spec'):
            self.o.remove('projectTabs', 'p.' + tab)
        self.assertIn(('delete', 'projectTabs/p.git'), keys(rf.plan(self.o.out)))

    def test_deleting_a_project_document_is_refused(self):
        self.o.add_project_q()
        self.o.pushed()
        self.o.remove('projects', 'q')
        with self.assertRaises(rf.MassDelete) as cm:
            rf.plan(self.o.out)
        self.assertIn('projects/q', str(cm.exception))
        self.assertFalse(os.path.exists(self.o.pending))

    def test_allowed_with_the_flag(self):
        for rid in ('rb1', 'rb2', 'ro1', 'ro2'):
            self.o.remove('runs', rid)
        k = keys(rf.plan(self.o.out, allow_mass_delete=True))
        self.assertIn(('delete', 'runs/ro2'), k)
        self.assertTrue(os.path.exists(self.o.pending))


class Catalogue(unittest.TestCase):
    """catalogue/index, from export_catalogue.py: managed like the other collections, never deleted by accident."""

    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)
        self.o.doc('catalogue', 'index', {'generatedAt': '2026-09-11T00:00:00+00:00', 'entries': [{'id': 'p:a'}], 'plugins': []})

    def test_catalogue_is_a_managed_collection(self):
        self.assertIn('catalogue', rf.MANAGED)
        self.assertIn(('set', 'catalogue/index'), keys(rf.plan(self.o.out)))

    def test_a_catalogue_change_is_one_write_and_moves_no_status(self):
        self.o.pushed()
        self.o.edit('catalogue', 'index', entries=[{'id': 'p:a'}, {'id': 'p:b'}])
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'catalogue/index')})

    def test_a_new_generated_at_alone_is_not_a_change(self):
        self.o.pushed()
        self.o.edit('catalogue', 'index', generatedAt='2026-09-12T00:00:00+00:00')
        self.assertIsNone(rf.plan(self.o.out))

    def test_deleting_the_catalogue_is_refused(self):
        self.o.pushed()
        self.o.remove('catalogue', 'index')
        with self.assertRaises(rf.MassDelete) as cm:
            rf.plan(self.o.out)
        self.assertIn('catalogue/index', str(cm.exception))
        self.assertFalse(os.path.exists(self.o.pending))
        self.assertEqual(keys(rf.plan(self.o.out, allow_mass_delete=True)), {('delete', 'catalogue/index')})


class Answers(unittest.TestCase):
    """Answers are recorded only by a human, so an export that holds one is refused whatever the flags."""

    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)

    def test_an_answers_document_refuses_the_plan_and_leaves_nothing_pending(self):
        self.o.pushed()
        self.o.edit('runs', 'ro1', kind='go')  # a real change, so there would otherwise be a plan
        with io.open(self.o.pending, 'w', encoding='utf-8') as f:
            json.dump({'state': {'runs/zz': 'stale'}}, f)
        self.o.doc('answers', 'row-5', {'answer': 'yes'})
        for flag in (False, True):
            with self.subTest(allow_mass_delete=flag):
                with self.assertRaises(rf.AnswersRefused) as cm:
                    rf.plan(self.o.out, allow_mass_delete=flag)
                self.assertIn('answers', str(cm.exception))
                self.assertFalse(os.path.exists(self.o.pending))

    def test_an_answers_document_in_a_sub_folder_counts(self):
        self.o.doc(os.path.join('answers', 'p'), 'row-5', {'answer': 'yes'})
        with self.assertRaises(rf.AnswersRefused):
            rf.plan(self.o.out)


class Export(unittest.TestCase):
    """export() runs each exporter as a subprocess; the real exporters are never run here."""

    def calls(self, results):
        seen = []

        def run(cmd, **kw):
            seen.append(cmd)
            code = results.get(os.path.basename(cmd[1]), 0)
            return subprocess.CompletedProcess(cmd, code, stdout='', stderr='boom' if code else '')
        with mock.patch.object(rf.subprocess, 'run', run), contextlib.redirect_stderr(io.StringIO()):
            err = rf.export('OUTDIR')
        return err, seen

    def test_the_three_exporters_run_in_order(self):
        self.assertEqual(rf.EXPORTERS, ('export_board.py', 'export_sessions.py', 'export_catalogue.py'))
        err, seen = self.calls({})
        self.assertIsNone(err)
        self.assertEqual([os.path.basename(c[1]) for c in seen], list(rf.EXPORTERS))
        self.assertTrue(all(c[0] == sys.executable and c[2] == 'OUTDIR' for c in seen))

    def test_a_failing_exporter_stops_the_rest(self):
        err, seen = self.calls({'export_sessions.py': 2})
        self.assertIn('export_sessions.py failed', err)
        self.assertEqual([os.path.basename(c[1]) for c in seen], ['export_board.py', 'export_sessions.py'])


class Cli(unittest.TestCase):
    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)

    def main(self, *argv, run_export=lambda out: None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rf.main(list(argv), out=self.o.out, run_export=run_export)
        return code, out.getvalue(), err.getvalue()

    def test_plan_prints_the_writes(self):
        code, out, _ = self.main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['batches'], 1)

    def test_nothing_to_push(self):
        self.o.pushed()
        self.assertEqual(self.main()[:2], (0, 'nothing to push\n'))

    def test_commit_without_pending(self):
        code, _, err = self.main('--commit')
        self.assertEqual(code, 1)
        self.assertIn('nothing pending', err)

    def test_commit(self):
        self.main()
        code, out, _ = self.main('--commit')
        self.assertEqual(code, 0)
        self.assertIn('recorded', out)

    def test_mass_delete_exits_non_zero_without_the_flag(self):
        self.o.pushed()
        for rid in ('rb1', 'rb2', 'ro1', 'ro2'):
            self.o.remove('runs', rid)
        code, out, err = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn('--allow-mass-delete', err)
        self.assertEqual(out, '')
        self.assertFalse(os.path.exists(self.o.pending))
        self.assertEqual(self.main('--allow-mass-delete')[0], 0)

    def test_project_delete_exits_non_zero_without_the_flag(self):
        self.o.pushed()
        self.o.remove('projects', 'p')
        code, out, err = self.main()
        self.assertNotEqual(code, 0)
        self.assertIn('--allow-mass-delete', err)
        self.assertEqual(out, '')
        self.assertFalse(os.path.exists(self.o.pending))
        self.assertEqual(self.main('--allow-mass-delete')[0], 0)
        self.assertTrue(os.path.exists(self.o.pending))

    def test_an_answers_document_exits_non_zero_naming_the_collection(self):
        self.o.doc('answers', 'row-5', {'answer': 'yes'})
        for argv in ((), ('--allow-mass-delete',)):
            with self.subTest(argv=argv):
                code, out, err = self.main(*argv)
                self.assertNotEqual(code, 0)
                self.assertIn('answers', err)
                self.assertEqual(out, '')
                self.assertFalse(os.path.exists(self.o.pending))

    def test_export_failure_stops_before_planning(self):
        code, _, err = self.main(run_export=lambda out: 'export_sessions.py failed:\nboom')
        self.assertEqual(code, 1)
        self.assertIn('boom', err)
        self.assertFalse(os.path.exists(self.o.pending))


if __name__ == '__main__':
    unittest.main()
