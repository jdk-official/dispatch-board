"""Tests for exporters/refresh.py's plan and commit steps, run against a synthetic out/ in a temporary
directory. The exporters are never run: main() is given a stub in their place.
"""
import contextlib, io, json, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exporters'))
import refresh as rf  # noqa: E402


class Out:
    """A throwaway out/ holding two sessions: b (a build) and o (not), with two runs each."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.out = os.path.join(self.tmp, 'out')
        for tab in rf.TABS:
            self.doc(None, tab, {'tab': tab, 'generatedAt': '2026-09-10T00:00:00+00:00'})
        self.doc('sessions', 'b', {'title': 'build', 'build': True})
        self.doc('sessions', 'o', {'title': 'other', 'build': False})
        for rid, sid in (('rb1', 'b'), ('rb2', 'b'), ('ro1', 'o'), ('ro2', 'o')):
            self.doc('runs', rid, {'session': sid, 'kind': 'done'})

    def path(self, coll, name):
        return os.path.join(self.out, *([coll] if coll else []), name + '.json')

    def doc(self, coll, name, obj):
        p = self.path(coll, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f)

    def edit(self, coll, name, **changes):
        p = self.path(coll, name)
        with io.open(p, encoding='utf-8') as f:
            obj = json.load(f)
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


def keys(plan):
    writes = plan['writes'] if plan['batches'] == 1 else [w for b in plan['writes'] for w in b]
    return {(w['op'], w['collection'] + '/' + w['doc_id']) for w in writes}


STATUS = ('update', 'meta/status')


class Plan(unittest.TestCase):
    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)

    def test_first_plan_sets_everything_and_the_status(self):
        p = rf.plan(self.o.out)
        k = keys(p)
        self.assertEqual(len(k), 5 + 2 + 4 + 1)
        self.assertIn(('set', 'tabs/spec'), k)
        self.assertIn(('set', 'runs/ro1'), k)
        self.assertIn(STATUS, k)
        self.assertTrue(os.path.exists(self.o.pending))

    def test_commit_then_nothing_to_push(self):
        rf.plan(self.o.out)
        self.assertEqual(rf.commit(self.o.out), 13)  # 11 documents plus the live flag and the build list
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
        self.o.edit(None, 'spec', generatedAt='2026-09-11T00:00:00+00:00')
        self.assertIsNone(rf.plan(self.o.out))

    def test_vanished_run_is_deleted(self):
        self.o.pushed()
        self.o.remove('runs', 'ro1')
        self.assertEqual(keys(rf.plan(self.o.out)), {('delete', 'runs/ro1')})

    def test_batches_past_the_limit(self):
        for i in range(60):
            self.o.doc('runs', 'x%02d' % i, {'session': 'o', 'kind': 'done'})
        p = rf.plan(self.o.out)
        self.assertEqual(p['batches'], 2)
        self.assertEqual(len(p['writes'][0]), rf.BATCH)


class UpdatedAt(unittest.TestCase):
    """meta/status.updatedAt moves only for build-relevant changes or a live flip."""

    def setUp(self):
        self.o = Out()
        self.addCleanup(self.o.cleanup)
        self.o.pushed()

    def test_non_build_session_change_does_not_bump(self):
        self.o.edit('sessions', 'o', title='renamed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'sessions/o')})

    def test_non_build_run_change_does_not_bump(self):
        self.o.edit('runs', 'ro1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/ro1')})

    def test_running_non_build_run_does_not_bump(self):
        self.o.edit('runs', 'ro1', kind='running')
        p = rf.plan(self.o.out)
        self.assertEqual(keys(p), {('set', 'runs/ro1')})
        self.assertFalse(p['live'])

    def test_build_session_change_bumps(self):
        self.o.edit('sessions', 'b', title='renamed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'sessions/b'), STATUS})

    def test_build_run_change_bumps(self):
        self.o.edit('runs', 'rb1', kind='go')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'runs/rb1'), STATUS})

    def test_deleted_build_run_bumps(self):
        self.o.remove('runs', 'rb1')
        self.assertEqual(keys(rf.plan(self.o.out)), {('delete', 'runs/rb1'), STATUS})

    def test_tab_change_bumps(self):
        self.o.edit(None, 'backlog', tab='changed')
        self.assertEqual(keys(rf.plan(self.o.out)), {('set', 'tabs/backlog'), STATUS})

    def test_live_flip_bumps(self):
        self.o.edit('runs', 'rb1', kind='running')
        p = rf.plan(self.o.out)
        self.assertTrue(p['live'])
        with io.open(os.path.join(self.o.out, 'meta', 'status.json'), encoding='utf-8') as f:
            status = json.load(f)
        self.assertTrue(status['live'])
        self.assertIn('updatedAt', status)


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

    def test_allowed_with_the_flag(self):
        for rid in ('rb1', 'rb2', 'ro1', 'ro2'):
            self.o.remove('runs', rid)
        k = keys(rf.plan(self.o.out, allow_mass_delete=True))
        self.assertIn(('delete', 'runs/ro2'), k)
        self.assertTrue(os.path.exists(self.o.pending))


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

    def test_export_failure_stops_before_planning(self):
        code, _, err = self.main(run_export=lambda out: 'export_sessions.py failed:\nboom')
        self.assertEqual(code, 1)
        self.assertIn('boom', err)
        self.assertFalse(os.path.exists(self.o.pending))


if __name__ == '__main__':
    unittest.main()
