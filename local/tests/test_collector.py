"""local/collector.py: incremental reads, persisted derivation state, the guards, last refresh, per-record errors,
the catalogue, exclusion and the command line. Everything runs on synthetic transcripts in temporary folders."""
import contextlib, hashlib, io, json, os, re, shutil, sqlite3, subprocess, sys, time, types, unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import collector_support as cs
from collector_support import Env, Spy, append, tes
import collector  # noqa: E402
import db  # noqa: E402
import derive  # noqa: E402
import export_sessions  # noqa: E402
import records  # noqa: E402
import test_conformance as tc  # noqa: E402

SID, SID2 = tes.SID, tes.SID2
SID3 = '33333333-aaaa-bbbb-cccc-000000000003'
SID4 = '44444444-aaaa-bbbb-cccc-000000000004'
DAY = 86400
CLOCK = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
PRIVATE_DIR = 'C:\\work\\private'


def quiet(sid, m=0, cwd=tes.CWD):
    """A session with one answered exchange and no agents."""
    return [tes.user(m, 'hello', cwd), tes.reply(m + 1, 'm-%s-%d' % (sid[:2], m), text='hi')]


class Case(unittest.TestCase):
    def setUp(self):
        self.e = Env(self)
        self.now = time.time()

    def tearDown(self):
        # No scenario ever creates an answers table. No scenario here configures a project with a readable
        # repository either, so none writes a tab record. A pass writes one status record per configured
        # project and no other, and the project records name those same projects, so the stored statuses are
        # exactly their statusDoc paths -- the empty set for the many scenarios that configure no project.
        c = self.e.conn
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertFalse({n for n in names if 'answer' in n.lower()})
        self.assertEqual(c.execute('SELECT COUNT(*) FROM project_tabs').fetchone()[0], 0)
        self.assertEqual(set(db.stored(c, 'status')), self.e.configured)

    def assert_equivalent(self, cfg=None, now=None):
        self.assertEqual(self.e.stored(), self.e.exported(cfg, now if now is not None else self.now))

    def spy(self):
        s = Spy()
        p = mock.patch.object(collector, '_open', side_effect=s)
        p.start()
        self.addCleanup(p.stop)
        return s


# ---------------------------------------------------------------- incremental reads

class Incremental(Case):
    def test_an_appended_line_is_the_only_thing_read(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        path = self.e.main_path(SID)
        size = os.path.getsize(path)
        raw = append(path, [tes.skill_call(40, 'toolu_sk', 'eng:tdd')])
        spy = self.spy()
        self.e.run(now=self.now)
        opens = spy.of(path)
        self.assertEqual(len(opens), 1)
        self.assertEqual(opens[0]['seeks'], [size])
        self.assertEqual(opens[0]['data'], raw)
        self.assertEqual(spy.of(self.e.agent_path(SID, 'acw11')), [])
        self.assert_equivalent()

    def test_an_unchanged_file_is_not_opened(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual(spy.calls, [])

    def test_a_partial_line_waits_for_its_newline_and_is_counted_once(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        path = self.e.main_path(SID)
        offset = self.e.session_state(SID)['main']['offset']
        append(path, [tes.skill_call(40, 'toolu_sk', 'eng:tdd')], newline=False)
        self.e.run(now=self.now)
        self.assertEqual(self.e.session_state(SID)['main']['offset'], offset)
        self.assertEqual(self.e.stored()['session'][SID]['skillUses'], {})
        with open(path, 'ab') as f:
            f.write(b'\n')
        self.e.run(now=self.now)
        self.e.run(now=self.now)
        self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:tdd']['count'], 1)
        self.assert_equivalent()

    def test_a_truncated_file_is_read_again_from_the_start(self):
        self.e.t.basic()
        append(self.e.main_path(SID), [tes.skill_call(40, 'toolu_sk', 'eng:tdd')])
        self.e.run(now=self.now)
        self.e.t.session(SID, [tes.user(0, 'short again'), tes.reply(1, 'm-short', text='ok')])
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
        self.assertEqual(self.e.stored()['session'][SID]['skillUses'], {})
        self.assert_equivalent()

    def test_a_replaced_file_is_read_again_from_the_start(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        path = self.e.main_path(SID)
        spare = os.path.join(self.e.tmp, 'spare.jsonl')
        with open(path, 'rb') as f:
            body = f.read()
        with open(spare, 'wb') as f:  # the same lines and more, so only the file id shows the swap
            f.write(body.replace(b'Please build the widget', b'Please build the gadget') + cs.line(
                tes.skill_call(41, 'toolu_sk2', 'eng:review')).encode())
        os.replace(spare, path)
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual(spy.of(path)[0]['seeks'], [0])
        self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:review']['count'], 1)
        self.assert_equivalent()

    def test_new_and_deleted_files(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        self.e.t.session(SID3, quiet(SID3))
        self.e.run(now=self.now)
        self.e.t.agent(SID, 'anew', [tes.user(3, 'task'), tes.reply(4, 'm-new', text='Looking')], {'agentType': 'Plan'})
        self.e.run(now=self.now)
        self.assertIn('anew', self.e.stored()['run'])
        self.assert_equivalent()
        os.remove(self.e.agent_path(SID, 'anew'))
        self.e.run(now=self.now)
        self.assertNotIn('anew', self.e.stored()['run'])
        self.assertNotIn((SID, 'anew'), self.e.state()[1])
        self.assert_equivalent()
        shutil.rmtree(os.path.join(self.e.root, tes.FOLDER, SID2))
        os.remove(self.e.main_path(SID2))
        self.e.run(now=self.now)
        self.assertNotIn(SID2, self.e.stored()['session'])
        self.assertNotIn(SID2, self.e.state()[0])
        self.assertFalse([k for k in self.e.state()[1] if k[0] == SID2])
        self.assert_equivalent()

    def test_a_restart_continues_from_the_stored_cursors(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        path = self.e.main_path(SID)
        size = os.path.getsize(path)
        raw = append(path, [tes.skill_call(40, 'toolu_sk', 'eng:tdd')])
        self.e.reconnect()
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual([(c['seeks'], c['data']) for c in spy.calls], [([size], raw)])
        self.assert_equivalent()

    def test_a_running_row_is_re_derived_and_killed_once_the_window_passes(self):
        self.e.t.session(SID, [tes.user(0, 'go'), tes.launch(1, 'toolu_r')])
        self.e.t.agent(SID, 'arun', [tes.user(1, 'task'), tes.reply(2, 'm-r', text='Reading')],
                       {'agentType': 'review-agents:code-reviewer', 'toolUseId': 'toolu_r'})
        self.e.run(now=self.now)
        self.assertEqual(self.e.stored()['run']['arun']['kind'], 'running')
        later = self.now + 11 * 60
        spy = self.spy()
        self.e.run(now=later)
        self.assertEqual(spy.calls, [])
        self.assertEqual((self.e.stored()['run']['arun']['kind'], self.e.stored()['run']['arun']['verdict']),
                         ('killed', 'no result'))
        self.assert_equivalent(now=later)

    def test_a_touched_file_re_derives_without_being_opened(self):
        self.e.t.session(SID, [tes.user(0, 'go'), tes.launch(1, 'toolu_r')])
        apath = self.e.t.agent(SID, 'aq', [tes.user(1, 'task'), tes.reply(2, 'm-q', text='Reading')],
                               {'agentType': 'review-agents:code-reviewer', 'toolUseId': 'toolu_r'})
        later = self.now + 3600
        self.e.run(now=later)
        self.assertEqual(self.e.stored()['run']['aq']['kind'], 'killed')
        os.utime(apath, (later, later))
        spy = self.spy()
        self.e.run(now=later)
        self.assertEqual(spy.calls, [])
        self.assertEqual(self.e.stored()['run']['aq']['kind'], 'running')
        self.assert_equivalent(now=later)


# ---------------------------------------------------------------- persisted state

class Codec(unittest.TestCase):
    def same(self, a, b):
        """Equal, with the same container types and dict key order at every depth."""
        self.assertIs(type(a), type(b))
        if isinstance(a, dict):
            self.assertEqual(list(a), list(b))
            for k in a:
                self.same(a[k], b[k])
        elif isinstance(a, (list, tuple)):
            self.assertEqual(len(a), len(b))
            for x, y in zip(a, b):
                self.same(x, y)
        else:
            self.assertEqual(a, b)

    def test_session_state_round_trips(self):
        s = derive.new_session(SID)
        s['by'] = {'m2': {'model': 'x', 'ts': None, 'tools': ['Agent'], 'usage': {'input_tokens': 1}}, None: {'model': None}}
        s['launched'] = {None: 't', 'toolu_a': '2026'}
        s['stopped'] = {None: None, 'a': 't'}
        s['sync'] = {None: {'at': None}}
        s['skillCalls'] = {None, 'toolu_1'}
        s['title'] = 'lone \ud800 surrogate'
        text = collector.encode(s)
        text.encode('ascii')
        self.same(collector.decode(text), s)
        self.assertEqual(list(collector.decode(text)['by']), ['m2', None])

    def test_generic_values_round_trip(self):
        v = {'b': [{1, 2}, frozenset({'x'}), (1, [2, (3,)])], 'a': {1: 'one', True: 'yes', None: 0, 'z': {('t', 1): 2}},
             '$': {'$': 'map', 'v': []}, 'n': [float('nan')][0:0], 'f': 1.5, 's': [set()]}
        self.same(collector.decode(collector.encode(v)), v)
        nested = {'k': [{'deep': ({'set': {3}},)}]}
        self.same(collector.decode(collector.encode(nested)), nested)

    def test_an_unknown_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            collector.encode({'x': object()})
        with self.assertRaises(TypeError):
            collector.encode([b'bytes'])


class State(Case):
    def rewrite(self, sql_select, sql_update, change):
        for key, text in self.e.conn.execute(sql_select).fetchall():
            v = collector.decode(text)
            change(v)
            self.e.conn.execute(sql_update, (collector.encode(v), key))

    def reset_case(self, change_session=None, change_agent=None):
        self.e.t.basic()
        self.e.run(now=self.now)
        if change_session:
            self.rewrite('SELECT id, data FROM collector_sessions', 'UPDATE collector_sessions SET data = ? WHERE id = ?',
                         lambda v: change_session(v['state']))
        if change_agent:
            self.rewrite('SELECT agent, data FROM collector_agents', 'UPDATE collector_agents SET data = ? WHERE agent = ?',
                         lambda v: change_agent(v['state']))
        self.e.reconnect()
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertNotIn('KeyError', self.e.err)
        return spy

    def test_a_session_state_with_a_missing_key_is_read_again(self):
        spy = self.reset_case(change_session=lambda s: s.pop('notes'))
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
        self.assert_equivalent()

    def test_a_session_state_with_an_extra_key_is_read_again(self):
        spy = self.reset_case(change_session=lambda s: s.update(extra=1))
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
        self.assert_equivalent()

    def test_an_agent_state_with_another_key_set_is_read_again(self):
        spy = self.reset_case(change_agent=lambda s: s.pop('text'))
        self.assertEqual(spy.of(self.e.agent_path(SID, 'acw11'))[0]['seeks'], [0])
        self.assert_equivalent()

    def test_a_state_that_cannot_be_decoded_is_read_again(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        self.e.conn.execute("UPDATE collector_sessions SET data = '{not json'")
        self.e.reconnect()
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
        self.assert_equivalent()

    def test_a_parser_version_change_reads_again(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        with mock.patch.object(export_sessions, 'PARSER_VERSION', export_sessions.PARSER_VERSION + 1):
            spy = self.spy()
            self.e.run(now=self.now)
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
        self.assert_equivalent()

    def malformed_entry_resets(self, table, change):
        """A stored row that decodes but whose layout is wrong resets its session alone: that session's files are
        read again from 0, the other session is not opened, and the pass commits."""
        spy = self.spy()
        cfg = self.e.cfg(exclude=['C:\\nothing\\*'])  # so exclusion is decided from the stored cursor and cwd
        sql = {'sessions': ('SELECT id, data FROM collector_sessions WHERE id = ?',
                            'UPDATE collector_sessions SET data = ? WHERE id = ?'),
               'agents': ('SELECT agent, data FROM collector_agents WHERE session = ?',
                          'UPDATE collector_agents SET data = ? WHERE agent = ?')}[table]
        for name, fn in change.items():
            with self.subTest(name):
                self.e = Env(self)
                self.e.t.basic()
                self.e.t.basic(sid=SID2)
                self.e.run(cfg, now=self.now)
                for key, text in self.e.conn.execute(sql[0], (SID,)).fetchall():
                    v = collector.decode(text)
                    fn(v)
                    self.e.conn.execute(sql[1], (collector.encode(v), key))
                self.e.reconnect()
                del spy.calls[:]
                self.e.run(cfg, now=self.now, clock=lambda: CLOCK)
                self.assertIn('2026-09-11T12:00:00', self.e.last_refresh())
                self.assertEqual(spy.of(self.e.agent_path(SID, 'acw11'))[0]['seeks'], [0])
                if table == 'sessions':
                    self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [0])
                self.assertEqual((spy.of(self.e.main_path(SID2)), spy.of(self.e.agent_path(SID2, 'acw22'))), ([], []))
                self.assertNotIn('could not be read', self.e.err)
                self.assert_equivalent(cfg)
                del spy.calls[:]
                self.e.run(cfg, now=self.now)  # reset once: the rewritten row is read incrementally again
                self.assertEqual(spy.calls, [])

    def test_a_session_row_with_a_wrong_layout_resets_that_session_only(self):
        self.malformed_entry_resets('sessions', {
            'no result': lambda v: v.pop('result'),
            'no main cursor': lambda v: v.pop('main'),
            'no window': lambda v: v.pop('window'),
            'an extra key': lambda v: v.update(extra=1),
            'a result that is not an object': lambda v: v.update(result=['rows']),
            'a result without rows': lambda v: v['result'].pop('rows'),
            'a cursor offset that is text': lambda v: v['main'].update(offset=str(v['main']['offset'])),
            'a cursor without its file id': lambda v: v['main'].pop('ino'),
        })

    def test_an_agent_row_with_a_wrong_layout_resets_that_agent(self):
        self.malformed_entry_resets('agents', {
            'no cursor': lambda v: v.pop('cursor'),
            'an extra key': lambda v: v.update(extra=1),
            'a cursor offset that is null': lambda v: v['cursor'].update(offset=None),
        })


class FailedFeed(Case):
    """A raise part-way through new lines leaves no partly fed state, so every record is counted once."""

    def appended(self):
        return [tes.skill_call(40, 'toolu_s1', 'eng:tdd'), {'type': 'assistant', 'timestamp': tes.ts(41), 'apiErrorStatus': 429},
                tes.skill_call(42, 'toolu_s2', 'eng:tdd'), tes.typed(43, '/eng:plan')]

    def raising_on(self, target, k):
        real, calls = getattr(derive, target), []

        def wrapper(*a, **kw):
            calls.append(1)
            if len(calls) == k:
                raise RuntimeError('boom on record %d' % k)
            return real(*a, **kw)
        return mock.patch.object(derive, target, side_effect=wrapper)

    def test_a_main_transcript_raise_keeps_the_stored_state_and_counts_once(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        before = self.e.state()
        docs = self.e.stored()
        append(self.e.main_path(SID), self.appended())
        with self.raising_on('add_record', 3):
            self.e.run(now=self.now)
        self.assertIn('session %s could not be read' % SID, self.e.err)
        self.assertEqual(self.e.state(), before)
        self.assertEqual(self.e.stored(), docs)
        self.e.run(now=self.now)
        s = self.e.stored()['session'][SID]
        self.assertEqual((s['skillUses']['eng:tdd']['count'], s['skillUses']['eng:plan']['count']), (2, 1))
        self.assertEqual(len(s['usage']['limits']), 1)
        self.assert_equivalent()

    def test_an_agent_file_raise_keeps_that_agent_and_counts_once(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        apath = self.e.agent_path(SID, 'acw11')
        before = self.e.state()[1][(SID, 'acw11')]
        append(apath, [tes.reply(5, 'm-a2', text='more'), {'type': 'user', 'timestamp': tes.ts(6), 'apiErrorStatus': 429},
                       tes.reply(7, 'm-a3', text='All green. DONE')])
        with self.raising_on('add_agent', 2):
            self.e.run(now=self.now)
        self.assertIn('agent acw11 skipped', self.e.err)
        self.assertEqual(self.e.state()[1][(SID, 'acw11')], before)
        self.assertIn('acw11', self.e.stored()['run'])
        self.e.run(now=self.now)
        sub = self.e.stored()['session'][SID]['usage']['subagents'][0]
        self.assertEqual(sub['requests'], 3)
        self.assert_equivalent()


class FailureAfterFeed(Case):
    """A raise after the main feed, up to encoding, discards every working copy and cursor of the session."""

    def check(self, target, attr):
        self.e.t.basic()
        self.e.run(now=self.now)
        before, docs = self.e.state(), self.e.stored()
        main_size = os.path.getsize(self.e.main_path(SID))
        agent_size = os.path.getsize(self.e.agent_path(SID, 'acw11'))
        append(self.e.main_path(SID), [tes.skill_call(40, 'toolu_s1', 'eng:tdd')])
        append(self.e.agent_path(SID, 'acw11'), [tes.reply(5, 'm-a2', text='more')])
        real, calls = getattr(target, attr), []

        def once(*a, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('boom')
            return real(*a, **kw)
        with mock.patch.object(target, attr, side_effect=once):
            self.e.run(now=self.now)
        self.assertTrue(calls)
        self.assertIn('session %s could not be read' % SID, self.e.err)
        self.assertEqual(self.e.state(), before)
        self.assertEqual(self.e.stored(), docs)
        spy = self.spy()
        self.e.run(now=self.now)
        self.assertEqual(spy.of(self.e.main_path(SID))[0]['seeks'], [main_size])
        self.assertEqual(spy.of(self.e.agent_path(SID, 'acw11'))[0]['seeks'], [agent_size])
        s = self.e.stored()['session'][SID]
        self.assertEqual(s['skillUses']['eng:tdd']['count'], 1)
        self.assertEqual(s['usage']['subagents'][0]['requests'], 2)
        self.assert_equivalent()

    def test_session_result(self):
        self.check(derive, 'session_result')

    def test_the_post_feed_exclusion_check(self):
        self.check(collector, 'post_feed_excluded')

    def test_encode(self):
        self.check(collector, 'encode')


# ---------------------------------------------------------------- guards and pruning

class Guard(Case):
    def three(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        self.e.t.session(SID3, quiet(SID3))
        self.e.run(now=self.now)

    def snapshot(self):
        return self.e.stored(), self.e.state(), self.e.last_refresh(), db.stored(self.e.conn, 'catalogue')

    def test_more_than_half_deleted_other_than_by_age_is_refused_writing_nothing(self):
        self.three()
        before = self.snapshot()
        watcher_conn = self.e.connect()
        watch = db.Changes(watcher_conn)
        watch.poll()
        for sid in (SID, SID2):
            os.remove(self.e.main_path(sid))
        append(self.e.main_path(SID3), [tes.reply(5, 'm-more', text='more')])  # an upsert the guard must hold back
        counted = mock.patch.object(db, 'upsert', side_effect=db.upsert)
        with counted as upsert, self.assertRaises(collector.Refusal) as cm:
            self.e.run(now=self.now)
        self.assertEqual(upsert.call_count, 0)
        self.assertIn('--allow-mass-delete', str(cm.exception))
        self.assertIn(SID, str(cm.exception))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(watch.poll())
        # The same pass, allowed once, applies the deletions and commits.
        self.assertEqual(self.e.main(['--once', '--allow-mass-delete'], now=self.now), 0, self.e.err)
        self.assertEqual(set(self.e.stored()['session']), {SID3})
        self.assertTrue(watch.poll())

    def test_refused_through_main_exits_2(self):
        self.three()
        for sid in (SID, SID2):
            os.remove(self.e.main_path(sid))
        self.assertEqual(self.e.main(['--once'], now=self.now), 2)
        self.assertIn('refusing to delete', self.e.err)
        self.assertIn('--allow-mass-delete', self.e.err)

    def test_no_sessions_and_a_deletion_other_than_by_age_is_refused(self):
        # Stored: SID (its file will leave the window, an age deletion) and SID2 (its transcript vanishes while its
        # last activity is recent: other). One of two held is not more than half, so only "no sessions" refuses.
        days6 = 6 * 24 * 60
        self.e.t.session(SID, quiet(SID))
        self.e.t.session(SID2, quiet(SID2, m=days6))
        first = self.now + 6.5 * DAY
        for sid in (SID, SID2):
            os.utime(self.e.main_path(sid), (first, first))
        self.e.run(now=first)
        self.assertEqual(set(self.e.stored()['session']), {SID, SID2})
        os.utime(self.e.main_path(SID), (self.now, self.now))
        os.remove(self.e.main_path(SID2))
        with self.assertRaises(collector.Refusal) as cm:
            self.e.run(now=first + 1.6 * DAY)
        self.assertIn('no sessions', str(cm.exception))

    def test_no_sessions_and_only_age_deletions_commits(self):
        self.e.t.session(SID, quiet(SID))
        self.e.run(now=self.now)
        self.e.run(now=self.now + 8 * DAY, clock=lambda: CLOCK)
        self.assertEqual(self.e.stored()['session'], {})
        self.assertIn('2026-09-11T12:00:00+00:00', self.e.last_refresh())

    def test_deleting_a_project_record_is_refused(self):
        self.e.t.basic()
        cfg = self.e.cfg()
        cfg['projects'] = [{'id': 'alpha', 'sessions': [SID]}, {'id': 'beta', 'sessions': []}]
        self.e.run(cfg, now=self.now)
        self.assertEqual(set(self.e.stored()['project']), {'alpha', 'beta'})
        cfg['projects'] = cfg['projects'][:1]
        with self.assertRaises(collector.Refusal) as cm:
            self.e.run(cfg, now=self.now)
        self.assertIn('beta', str(cm.exception))
        self.assertEqual(set(self.e.stored()['project']), {'alpha', 'beta'})
        self.assertEqual(self.e.main(['--once', '--allow-mass-delete'], cfg=cfg, now=self.now), 0, self.e.err)
        self.assertEqual(set(self.e.stored()['project']), {'alpha'})

    def test_a_quiet_week_prunes_more_than_half_by_age_and_commits(self):
        for sid in (SID, SID2, SID3):
            self.e.t.basic(sid=sid)
        self.e.t.basic(sid=SID4)
        cfg = self.e.cfg(build=[SID4])
        self.e.run(cfg, now=self.now)
        self.assertEqual(len(self.e.stored()['session']), 4)
        report = self.e.run(cfg, now=self.now + 8 * DAY)
        self.assertEqual(set(self.e.stored()['session']), {SID4})
        self.assertEqual(report['aged'], 6)
        self.assert_equivalent(cfg, now=self.now + 8 * DAY)


class Pruning(Case):
    def test_an_unlinked_session_8_days_quiet_loses_its_records(self):
        self.e.t.basic()
        self.e.run(now=self.now)
        self.e.run(now=self.now + 8 * DAY)
        self.assertEqual(self.e.stored(), {'session': {}, 'run': {}, 'project': {}})

    def test_a_linked_session_30_days_quiet_keeps_its_records(self):
        self.e.t.basic()
        cfg = self.e.cfg(build=[SID])
        self.e.run(cfg, now=self.now)
        self.e.run(cfg, now=self.now + 30 * DAY)
        self.assertIn(SID, self.e.stored()['session'])
        self.assertIn('acw11', self.e.stored()['run'])
        self.assert_equivalent(cfg, now=self.now + 30 * DAY)

    def pruned_on_activity(self, recs):
        """A session whose file time stays inside the window while its records are 8 days old."""
        cfg = self.e.cfg(exclude=['C:\\nothing\\*'])
        later = self.now + 8 * DAY
        self.e.t.session(SID, recs)
        self.e.t.session(SID2, quiet(SID2))
        self.e.run(cfg, now=self.now)
        for p in (self.e.main_path(SID), self.e.main_path(SID2)):
            os.utime(p, (later, later))
        return cfg, later

    def test_pruned_on_last_activity_keeps_its_state_and_is_not_opened_again(self):
        cfg, later = self.pruned_on_activity([tes.user(0, 'go'), tes.launch(1, 'toolu_cw'),
                                              tes.notify(30, 'acw11', result='DONE', tokens='5', ms='60000')])
        self.e.t.agent(SID, 'acw11', [tes.user(1, 'task'), tes.reply(2, 'm-a', text='DONE')], tes.CW_META)
        os.utime(self.e.agent_path(SID, 'acw11'), (later, later))
        self.e.run(cfg, now=self.now)
        self.assertIn(SID, self.e.stored()['session'])
        self.e.run(cfg, now=later)
        self.assertNotIn(SID, self.e.stored()['session'])
        self.assertNotIn('acw11', self.e.stored()['run'])
        self.assertIn(SID, self.e.state()[0])
        self.assertIn((SID, 'acw11'), self.e.state()[1])
        spy = self.spy()
        with mock.patch.object(export_sessions, 'cwd_of', side_effect=export_sessions.cwd_of) as cwd_of:
            self.e.run(cfg, now=later)
        self.assertEqual((spy.calls, cwd_of.call_count), ([], 0))
        self.assertNotIn(SID, self.e.stored()['session'])
        self.assert_equivalent(cfg, now=later)

    def test_a_session_with_no_answer_keeps_its_state_and_is_not_opened_again(self):
        self.e.t.session(SID, [tes.user(0, 'anyone there?')])
        self.e.t.session(SID2, quiet(SID2))
        cfg = self.e.cfg(exclude=['C:\\nothing\\*'])
        self.e.run(cfg, now=self.now)
        self.assertNotIn(SID, self.e.stored()['session'])
        self.assertIsNone(self.e.session_state(SID)['result'])
        spy = self.spy()
        with mock.patch.object(export_sessions, 'cwd_of', side_effect=export_sessions.cwd_of) as cwd_of:
            self.e.run(cfg, now=self.now)
        self.assertEqual((spy.calls, cwd_of.call_count), ([], 0))
        self.assert_equivalent(cfg)

    def test_leaving_the_window_by_file_time_drops_the_state(self):
        self.e.t.basic()
        self.e.t.session(SID2, quiet(SID2))
        self.e.run(now=self.now)
        old = self.now - 8 * DAY
        os.utime(self.e.main_path(SID), (old, old))
        self.e.run(now=self.now)
        self.assertNotIn(SID, self.e.state()[0])
        self.assertFalse([k for k in self.e.state()[1] if k[0] == SID])
        self.assertNotIn(SID, self.e.stored()['session'])

    def test_vanished_transcripts_with_old_activity_are_age_deletions(self):
        for sid in (SID, SID2, SID3):
            self.e.t.basic(sid=sid)
        self.e.run(now=self.now)
        for sid in (SID, SID2):
            os.remove(self.e.main_path(sid))
        report = self.e.run(now=self.now + 8 * DAY)
        self.assertEqual(report['aged'], 6)
        self.assertEqual(self.e.stored()['session'], {})

    def test_vanished_transcripts_with_recent_activity_are_not(self):
        for sid in (SID, SID2, SID3):
            self.e.t.basic(sid=sid)
        self.e.run(now=self.now)
        for sid in (SID, SID2):
            os.remove(self.e.main_path(sid))
        with self.assertRaises(collector.Refusal):
            self.e.run(now=self.now)

    def test_auto_linked_sessions_are_pruned_by_age_past_the_guard_and_a_listed_one_is_kept(self):
        for sid in (SID, SID2, SID3):
            tes.edit_session(self.e.t, sid, tes.REPO + '/%s.py' % sid[:2])
        self.e.t.basic(sid=SID4)
        cfg = self.e.cfg()
        cfg['projects'] = [tes.proj('p', SID4, repoPath=tes.REPO)]
        self.e.run(cfg, now=self.now)
        self.assertEqual(self.e.stored()['project']['p']['sessions'], [SID4, SID, SID2, SID3])
        report = self.e.run(cfg, now=self.now + 8 * DAY)
        self.assertEqual(set(self.e.stored()['session']), {SID4})
        self.assertEqual((report['aged'], self.e.stored()['project']['p']['sessions']), (3, [SID4]))
        self.assert_equivalent(cfg, now=self.now + 8 * DAY)


class AutoLink(Case):
    """The collector links the sessions no project lists exactly as the session exporter does."""

    def cfg(self, *projects):
        cfg = self.e.cfg()
        cfg['projects'] = list(projects) or [tes.proj('p', repoPath=tes.REPO)]
        return cfg

    def link(self, sid):
        doc = self.e.stored()['session'][sid]
        return doc['project'], doc.get('linkedBy')

    def test_a_listed_session_keeps_its_project_whatever_it_edited(self):
        tes.edit_session(self.e.t, SID, 'C:/b/1.py', 'C:/b/2.py')
        cfg = self.cfg(tes.proj('a', SID, repoPath='C:/a'), tes.proj('b', repoPath='C:/b'))
        self.e.run(cfg, now=self.now)
        self.assertEqual(self.link(SID), ('a', 'config'))
        self.assertEqual((self.e.stored()['project']['a']['sessions'], self.e.stored()['project']['b']['sessions']),
                         ([SID], []))
        self.assert_equivalent(cfg)

    def test_an_auto_linked_session_whose_transcript_has_gone_is_deleted_not_refused(self):
        tes.edit_session(self.e.t, SID, tes.REPO + '/a.py')
        for sid in (SID2, SID3):
            self.e.t.basic(sid=sid)
        cfg = self.cfg()
        self.e.run(cfg, now=self.now)
        self.assertEqual(self.link(SID), ('p', 'edits'))
        os.remove(self.e.main_path(SID))
        self.e.run(cfg, now=self.now)
        self.assertNotIn(SID, self.e.stored()['session'])
        self.assertEqual(self.e.stored()['project']['p']['sessions'], [])
        self.assert_equivalent(cfg)

    def test_with_nothing_else_stored_only_the_mass_delete_guard_can_refuse(self):
        tes.edit_session(self.e.t, SID, tes.REPO + '/a.py')
        cfg = self.cfg()
        self.e.run(cfg, now=self.now)
        os.remove(self.e.main_path(SID))
        with self.assertRaises(collector.Refusal) as cm:
            self.e.run(cfg, now=self.now)
        self.assertIn('refusing to delete', str(cm.exception))
        self.assertNotIn('no transcript', str(cm.exception))

    def test_one_appended_edit_links_the_session_reading_only_the_appended_bytes(self):
        self.e.t.session(SID, quiet(SID))
        cfg = self.cfg()
        self.e.run(cfg, now=self.now)
        self.assertEqual(self.link(SID), (None, None))
        raw = append(self.e.main_path(SID), [tes.edit_call(5, 'te', tes.REPO + '/a.py'), tes.tool_result(5, 'te')])
        report = self.e.run(cfg, now=self.now)
        self.assertEqual((self.link(SID), report['bytes']), (('p', 'edits'), len(raw)))
        self.assert_equivalent(cfg)

    def test_a_link_config_change_re_derives_no_session(self):
        tes.edit_session(self.e.t, SID, tes.REPO + '/a.py')
        self.e.run(self.cfg(), now=self.now)
        for cfg, want in ((self.cfg(tes.proj('p', repoPath='C:/moved')), (None, None)),
                          (self.cfg(tes.proj('p', repoPath='C:/moved', worktreeRoots=['C:/work'])), ('p', 'edits')),
                          (self.cfg(tes.proj('a', SID), tes.proj('p', repoPath=tes.REPO)), ('a', 'config'))):
            with self.subTest(cfg=cfg['projects']):
                report = self.e.run(cfg, now=self.now)
                self.assertEqual((report['rederived'], self.link(SID)), (0, want))

    def test_state_stored_by_the_previous_parser_is_read_again_from_the_start_once(self):
        tes.edit_session(self.e.t, SID, tes.REPO + '/a.py')
        cfg = self.cfg()
        self.e.run(cfg, now=self.now)

        def as_base(v):  # parser 10 stored no failed set and no main-transcript edits
            v['parser'] = 10
            v['state'].pop('failed')
            v['result']['doc'].pop('edits')
        for key, text in self.e.conn.execute('SELECT id, data FROM collector_sessions').fetchall():
            v = collector.decode(text)
            as_base(v)
            self.e.conn.execute('UPDATE collector_sessions SET data = ? WHERE id = ?', (collector.encode(v), key))
        self.e.reconnect()
        spy = self.spy()
        self.e.run(cfg, now=self.now)
        self.assertEqual([c['seeks'] for c in spy.of(self.e.main_path(SID))], [[0]])
        self.assertEqual(self.link(SID), ('p', 'edits'))
        self.e.run(cfg, now=self.now)
        self.assertEqual(len(spy.of(self.e.main_path(SID))), 1)

    def test_an_unusable_worktree_roots_or_repo_path_refuses_the_pass(self):
        self.e.t.basic()
        for over in ({'worktreeRoots': 'x'}, {'worktreeRoots': ['C:/']}, {'worktreeRoots': ['~/x']}, {'repoPath': 5}):
            with self.subTest(over=over):
                with self.assertRaises(collector.Refusal) as cm:
                    self.e.run(self.cfg(tes.proj('p', **over)), now=self.now)
                self.assertIn('project p', str(cm.exception))


# ---------------------------------------------------------------- exclusion

class Exclusion(Case):
    def cfg(self, exclude=(PRIVATE_DIR + '*',)):
        return self.e.cfg(exclude=list(exclude))

    def setup(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        self.e.t.session(SID3, quiet(SID3, cwd=PRIVATE_DIR))
        self.path = self.e.main_path(SID3)

    def rule(self, exclude=(PRIVATE_DIR + '*',)):
        return hashlib.sha256(json.dumps(list(exclude)).encode('utf-8')).hexdigest()

    def counted(self):
        spy = self.spy()
        cwd_of = mock.patch.object(export_sessions, 'cwd_of', side_effect=export_sessions.cwd_of)
        return spy, cwd_of

    def test_an_excluded_session_leaves_only_a_content_free_marker(self):
        self.setup()
        self.e.run(self.cfg(), now=self.now)
        self.assertNotIn(SID3, self.e.stored()['session'])
        self.assertNotIn(SID3, self.e.state()[0])
        st = os.stat(self.path)
        self.assertEqual(self.e.state()[2], [(str(st.st_dev), str(st.st_ino), st.st_size, self.rule())])
        cols = [r[1] for r in self.e.conn.execute('PRAGMA table_info(collector_excluded)')]
        self.assertEqual(cols, ['dev', 'ino', 'size', 'rule'])
        self.assert_equivalent(self.cfg())

    def test_with_a_marker_the_file_is_not_opened(self):
        self.setup()
        self.e.run(self.cfg(), now=self.now)
        append(self.path, [tes.reply(5, 'm-x', text='more')])
        spy, cwd_of = self.counted()
        with cwd_of as c:
            self.e.run(self.cfg(), now=self.now)
        self.assertEqual((spy.of(self.path), c.call_count), ([], 0))
        self.assertEqual(self.e.state()[2][0][2], os.path.getsize(self.path))

    def decides_again(self, change, cfg=None):
        self.setup()
        self.e.run(self.cfg(), now=self.now)
        change()
        _, cwd_of = self.counted()
        with cwd_of as c:
            self.e.run(cfg or self.cfg(), now=self.now)
        self.assertEqual(c.call_count, 1)
        self.assertNotIn(SID3, self.e.stored()['session'])

    def test_a_changed_exclude_list_decides_again(self):
        other = [PRIVATE_DIR + '*', 'C:\\elsewhere*']
        self.decides_again(lambda: None, self.cfg(other))
        self.assertEqual([m[3] for m in self.e.state()[2]], [self.rule(other)])

    def test_a_replaced_file_decides_again(self):
        def replace():
            spare = os.path.join(self.e.tmp, 'spare.jsonl')
            shutil.copyfile(self.path, spare)
            os.replace(spare, self.path)
        self.decides_again(replace)

    def test_a_truncated_file_decides_again(self):
        self.decides_again(lambda: self.e.t.session(SID3, [tes.user(0, 'x', PRIVATE_DIR)]))

    def test_a_file_with_no_cwd_gets_no_marker(self):
        self.e.t.session(SID3, [{'type': 'user', 'timestamp': tes.ts(0), 'message': {'role': 'user', 'content': 'hi'}},
                                tes.reply(1, 'm-nc', text='hi')])
        self.e.run(self.cfg(), now=self.now)
        self.assertEqual(self.e.state()[2], [])
        self.assertIn(SID3, self.e.stored()['session'])

    def test_a_session_that_becomes_excluded_is_purged(self):
        self.setup()
        self.e.run(now=self.now)
        self.assertIn(SID3, self.e.stored()['session'])
        self.e.run(self.cfg(), now=self.now)
        self.assertNotIn(SID3, self.e.stored()['session'])
        self.assertNotIn(SID3, self.e.state()[0])
        self.assert_equivalent(self.cfg())

    def test_a_first_cwd_in_appended_lines_excludes_the_session(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        nocwd = {'type': 'user', 'timestamp': tes.ts(0), 'message': {'role': 'user', 'content': 'hi'}}
        self.e.t.session(SID3, [nocwd, tes.reply(1, 'm-nc', text='hi')])
        self.e.run(self.cfg(), now=self.now)
        self.assertIn(SID3, self.e.stored()['session'])
        append(self.e.main_path(SID3), [tes.user(2, 'now with a folder', PRIVATE_DIR)])
        self.e.run(self.cfg(), now=self.now)
        self.assertNotIn(SID3, self.e.stored()['session'])
        self.assertNotIn(SID3, self.e.state()[0])
        self.assert_equivalent(self.cfg())

    def test_a_stale_marker_is_deleted_and_the_rewritten_file_stays_included(self):
        self.setup()
        self.e.run(self.cfg(), now=self.now)
        st = os.stat(self.path)
        with open(self.path, 'wb') as f:  # truncated and rewritten in place: the same file id
            f.write(cs.line(tes.user(0, 'hi', tes.CWD)).encode())
        self.assertEqual(os.stat(self.path).st_ino, st.st_ino)
        self.e.run(self.cfg(), now=self.now)
        self.assertEqual(self.e.state()[2], [])
        while os.path.getsize(self.path) <= st.st_size:
            append(self.path, [tes.reply(3, 'm-grow-%d' % os.path.getsize(self.path), text='x' * 40)])
        self.e.run(self.cfg(), now=self.now)
        self.assertIn(SID3, self.e.stored()['session'])
        self.assertFalse([m for m in self.e.state()[2] if m[:2] == (str(st.st_dev), str(st.st_ino))])
        self.assert_equivalent(self.cfg())

    def test_a_file_id_above_the_signed_64_bit_range_is_stored_and_matches(self):
        self.setup()
        real, target = os.stat, os.path.normcase(os.path.abspath(self.path))

        def fake(path, *a, **kw):
            st = real(path, *a, **kw)
            if isinstance(path, (str, bytes, os.PathLike)) and os.path.normcase(os.path.abspath(os.fsdecode(path))) == target:
                return types.SimpleNamespace(st_dev=st.st_dev, st_ino=2 ** 64 - 1, st_size=st.st_size,
                                             st_mtime=st.st_mtime, st_mode=st.st_mode)
            return st
        with mock.patch('os.stat', side_effect=fake):
            self.e.run(self.cfg(), now=self.now)
            self.assertEqual([m[1] for m in self.e.state()[2]], [str(2 ** 64 - 1)])
            spy, cwd_of = self.counted()
            with cwd_of as c:
                self.e.run(self.cfg(), now=self.now)
        self.assertEqual((spy.of(self.path), c.call_count), ([], 0))
        self.assertNotIn(SID3, self.e.stored()['session'])


# ---------------------------------------------------------------- records, catalogue, last refresh

class Records(Case):
    def test_a_record_that_cannot_be_stored_is_skipped_and_its_stored_version_kept(self):
        for error in (ValueError('bad'), UnicodeEncodeError('utf-8', '\ud800', 0, 1, 'surrogates'),
                      RecursionError('deep'), TypeError('odd')):
            with self.subTest(error=type(error).__name__):
                e = self.e = Env(self)
                e.t.basic()
                e.t.basic(sid=SID2)
                e.run(now=self.now)
                old = e.stored()['run']['acw11']
                append(e.main_path(SID), [tes.notify(50, 'acw11', result='Changed. NOT-DONE', tokens='9', ms='120000')])
                append(e.main_path(SID2), [tes.skill_call(51, 'toolu_z', 'eng:tdd')])
                real = records.to_row

                def to_row(kind, rid, doc):
                    if (kind, rid) == ('run', 'acw11'):
                        raise error
                    return real(kind, rid, doc)
                with mock.patch.object(records, 'to_row', side_effect=to_row):
                    e.run(now=self.now)
                self.assertIn('run acw11 not stored (%s' % type(error).__name__, e.err)
                self.assertEqual(e.stored()['run']['acw11'], old)
                self.assertIn('eng:tdd', e.stored()['session'][SID2]['skillUses'])
                self.assertEqual(e.stored()['session'][SID]['runs'], 1)

    def test_a_lone_surrogate_title_is_skipped_end_to_end(self):
        self.e.t.basic()
        self.e.t.session(SID2, [{'type': 'custom-title', 'customTitle': '\ud800', 'sessionId': SID2}] + quiet(SID2))
        self.e.run(now=self.now)
        self.assertIn('session %s not stored (UnicodeEncodeError' % SID2, self.e.err)
        self.assertNotIn(SID2, self.e.stored()['session'])
        self.assertIn(SID, self.e.stored()['session'])

    def test_last_refresh_is_written_by_a_committed_pass_only(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        self.e.run(now=self.now, clock=lambda: CLOCK)
        doc = json.loads(self.e.last_refresh())
        self.assertEqual(doc, {'at': '2026-09-11T12:00:00+00:00', 'writer': 'collector'})
        self.assertEqual(records.validate('lastRefresh', doc), [])
        self.e.run(now=self.now, clock=lambda: CLOCK + timedelta(minutes=1))  # a quiet pass still writes it
        self.assertIn('12:01:00', self.e.last_refresh())
        before = self.e.last_refresh()
        for sid in (SID, SID2):
            os.remove(self.e.main_path(sid))
        with self.assertRaises(collector.Refusal):
            self.e.run(now=self.now, clock=lambda: CLOCK + timedelta(hours=1))
        self.assertEqual(self.e.last_refresh(), before)
        with self.assertRaises(collector.Refusal):
            collector.run_pass(self.e.conn, self.e.cfg(), projects_root=os.path.join(self.e.tmp, 'missing'),
                               now=self.now, clock=lambda: CLOCK + timedelta(hours=2))
        self.assertEqual(self.e.last_refresh(), before)

    def test_only_the_kinds_the_collector_writes_are_written(self):
        f = tc.Fixture()
        self.addCleanup(f.cleanup)
        f.transcripts()
        f.marketplace()
        cfg = self.e.seen(f.config())  # this pass is driven directly, so the config is declared to the guard
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            collector.run_pass(self.e.conn, cfg, projects_root=f.root, now=self.now)
        counts = {t: self.e.conn.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0] for t, _ in records.TABLES.values()}
        # No project of this fixture has its repository on disk (repos() is not called), so the tab pass builds
        # no tab record; it still writes every configured project's status.
        self.assertEqual({t for t, n in counts.items() if n},
                         {'sessions', 'runs', 'projects', 'statuses', 'catalogue', 'last_refresh'})


class Catalogue(Case):
    def setUp(self):
        super().setUp()
        self.f = tc.Fixture()
        self.addCleanup(self.f.cleanup)
        self.f.marketplace()
        self.e.t.basic()
        self.cfg = self.e.cfg()
        self.cfg['catalogue'] = {'marketplacePath': self.f.market, 'installedPath': self.f.installed}

    def exported(self):
        out = os.path.join(self.e.tmp, 'cat-out')
        with contextlib.redirect_stdout(io.StringIO()):
            import export_catalogue
            self.assertEqual(export_catalogue.main(self.cfg, out, tc.NOW), 0)
        with io.open(os.path.join(out, 'catalogue', 'index.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def test_it_equals_the_exporter_ignoring_generated_at(self):
        self.e.run(self.cfg, now=self.now)
        got = db.stored(self.e.conn, 'catalogue')['index']
        want = self.exported()
        self.assertEqual({k: v for k, v in got.items() if k != 'generatedAt'}, {k: v for k, v in want.items() if k != 'generatedAt'})

    def test_a_missing_marketplace_keeps_the_stored_record(self):
        self.e.run(self.cfg, now=self.now)
        before = db.stored(self.e.conn, 'catalogue')
        self.cfg['catalogue']['marketplacePath'] = os.path.join(self.e.tmp, 'moved')
        self.e.run(self.cfg, now=self.now + 60)
        self.assertEqual(db.stored(self.e.conn, 'catalogue'), before)

    def test_only_a_new_generated_at_does_not_rewrite_it(self):
        self.e.run(self.cfg, now=self.now)
        before = db.stored(self.e.conn, 'catalogue')
        with mock.patch.object(db, 'upsert', side_effect=db.upsert) as upsert:
            self.e.run(self.cfg, now=self.now + 3600)
        self.assertNotIn('catalogue', [c.args[1] for c in upsert.call_args_list])
        self.assertEqual(db.stored(self.e.conn, 'catalogue'), before)

    def test_a_catalogue_value_of_the_wrong_type_refuses_the_pass(self):
        self.cfg['catalogue'] = {'marketplacePath': 3}
        with self.assertRaises(collector.Refusal):
            self.e.run(self.cfg, now=self.now)


# ---------------------------------------------------------------- command line

class CommandLine(Case):
    def test_once_exits_0_after_a_committed_pass(self):
        self.e.t.basic()
        self.assertEqual(self.e.main(['--once'], now=self.now), 0, self.e.err)
        self.assertRegex(self.e.out, r'collector: 1 sessions \(1 re-derived, \d+ bytes read\), 1 runs, 0 projects, '
                                     r'0 tabs; 2 written, 0 deleted \(0 by age\) \| [\d.]+s')

    def test_once_exits_2_for_a_config_error_and_a_missing_root(self):
        cfg = self.e.cfg()
        cfg['sessions']['days'] = 'seven'
        self.assertEqual(self.e.main(['--once'], cfg=cfg), 2)
        self.assertIn('sessions.days', self.e.err)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = collector.main(['--once'], config=self.e.cfg(), db_path=self.e.db_path,
                                  projects_root=os.path.join(self.e.tmp, 'missing'))
        self.assertEqual(code, 2)
        self.assertIn('does not exist', err.getvalue())

    def test_once_exits_2_for_a_bad_local_key(self):
        cfg = self.e.cfg()
        cfg['local'] = {'databasePath': ''}
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(collector.main(['--once'], config=cfg, projects_root=self.e.root), 2)
        self.assertIn('local.databasePath', err.getvalue())

    def test_once_exits_1_after_any_other_failure(self):
        with mock.patch.object(collector, 'run_pass', side_effect=RuntimeError('broken')):
            self.assertEqual(self.e.main(['--once']), 1)
        self.assertIn('RuntimeError: broken', self.e.err)

    def test_allow_mass_delete_needs_once(self):
        self.assertEqual(self.e.main(['--allow-mass-delete']), 2)
        self.assertIn('--allow-mass-delete', self.e.err)

    def test_the_loop_carries_on_after_a_failed_pass(self):
        self.e.t.basic()
        real, calls = collector.run_pass, []

        def flaky(*a, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('first pass fails')
            return real(*a, **kw)
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            if len(sleeps) == 2:
                raise KeyboardInterrupt
        with mock.patch.object(collector, 'run_pass', side_effect=flaky), mock.patch('time.sleep', side_effect=sleep):
            code = self.e.main(['--interval', '5'], now=self.now)
        self.assertEqual(code, 0)
        self.assertEqual((len(calls), sleeps), (2, [5.0, 5.0]))
        self.assertIn('first pass fails', self.e.err)
        self.assertIn(SID, self.e.stored()['session'])

    def test_a_unc_database_path_refuses_to_start(self):
        for argv_path, via in (('\\\\nas\\share\\board.db', 'db_path'), ('\\\\nas\\share\\board.db', 'config')):
            with self.subTest(via=via):
                cfg = self.e.cfg()
                out, err = io.StringIO(), io.StringIO()
                with mock.patch('os.makedirs') as mk, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    if via == 'db_path':
                        code = collector.main(['--once'], config=cfg, db_path=argv_path, projects_root=self.e.root)
                    else:
                        cfg['local'] = {'databasePath': argv_path}
                        code = collector.main(['--once'], config=cfg, projects_root=self.e.root)
                self.assertEqual(code, 2)
                self.assertIn('refusing to start: the database path \\\\nas\\share\\board.db is a network path', err.getvalue())
                mk.assert_not_called()

    def test_a_file_that_is_not_a_database_exits_2_unchanged(self):
        path = os.path.join(self.e.tmp, 'notes.db')
        with open(path, 'wb') as f:
            f.write(b'my notes\n' * 20)
        self.assertEqual(self.e.main(['--once'], db_path=path), 2)
        self.assertIn('cannot be used as the database', self.e.err)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'my notes\n' * 20)
        self.assertFalse(os.path.exists(path + '-wal') or os.path.exists(path + '-shm'))

    def test_another_collector_holding_the_lock_exits_1(self):
        self.e.t.basic()
        other = sqlite3.connect(self.e.db_path, isolation_level=None)
        self.addCleanup(other.close)
        other.execute('BEGIN IMMEDIATE')
        try:
            with mock.patch.object(db, 'TIMEOUT', 0.05):
                self.assertEqual(self.e.main(['--once'], now=self.now), 1)
        finally:
            other.execute('ROLLBACK')
        self.assertIn('another collector holds the database lock', self.e.err)

    def test_a_lock_on_the_pass_itself_raises_the_lock_error(self):
        self.e.t.basic()
        conn = self.e.conn
        other = sqlite3.connect(self.e.db_path, isolation_level=None, timeout=0.05)
        self.addCleanup(other.close)
        conn.execute('PRAGMA busy_timeout = 50')
        other.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(sqlite3.OperationalError) as cm:
                self.e.run(now=self.now)
        finally:
            other.execute('ROLLBACK')
        self.assertIn('locked', str(cm.exception))

    def test_a_path_sqlite_cannot_open_exits_2(self):
        folder = os.path.join(self.e.tmp, 'a-folder.db')
        os.makedirs(folder)
        self.assertEqual(self.e.main(['--once'], db_path=folder), 2)
        self.assertIn('refusing to start: %s cannot be used as the database' % folder, self.e.err)
        self.assertTrue(os.path.isdir(folder))


STAMP = r'collector: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d '


class ConfigFile(Case):
    """The config as the owner saves it by hand: one that parses but is not an object is a refusal, never a crash."""

    def write(self, value):
        path = os.path.join(self.e.tmp, 'board.config.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(value if isinstance(value, str) else json.dumps(value))
        return path

    def main(self, argv, **kw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = collector.main(argv, projects_root=self.e.root, now=self.now, **kw)
        self.e.out, self.e.err = out.getvalue(), err.getvalue()
        return code

    def test_a_config_that_is_not_an_object_refuses_to_start(self):
        deep = '[' * 100000 + ']' * 100000
        for text, says in (('null', 'null'), ('[]', 'an array'), ('"board"', 'a string'), ('3', 'a number'),
                           ('true', 'true or false'), (deep, 'nests too deeply')):
            for argv in (['--once'], []):
                with self.subTest(text=text[:8], argv=argv):
                    path = self.write(text)
                    with mock.patch('time.sleep', side_effect=AssertionError('the loop must not start')):
                        code = self.main(argv + ['--config', path])
                    self.assertEqual(code, 2, self.e.err)
                    self.assertIn(path, self.e.err)
                    self.assertIn(says, self.e.err)
                    self.assertIn('not started', self.e.err)
        self.assertEqual(self.main(['--once'], config=[]), 2)
        self.assertIn('the config must be a JSON object, not an array; not started', self.e.err)
        self.assertEqual(self.e.stored(), {'session': {}, 'run': {}, 'project': {}})

    def test_a_bad_save_mid_loop_refuses_that_pass_and_the_loop_goes_on(self):
        self.e.t.basic()
        cfg = self.e.cfg()
        cfg['local'] = {'databasePath': self.e.db_path}
        path = self.write(cfg)
        steps = [lambda: self.write([]), lambda: self.write('null'),
                 lambda: (self.write(cfg), append(self.e.main_path(SID), [tes.skill_call(40, 'toolu_sk', 'eng:tdd')]))]
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            if len(sleeps) > len(steps):
                raise KeyboardInterrupt
            steps[len(sleeps) - 1]()
        with mock.patch.object(collector, 'run_pass', side_effect=collector.run_pass) as passes, \
                mock.patch('time.sleep', side_effect=sleep):
            code = self.main(['--interval', '5', '--config', path])
        self.assertEqual(code, 0, self.e.err)
        self.assertEqual((passes.call_count, len(sleeps)), (2, 4))  # no pass ran on either bad save
        refused = re.findall(STAMP + r'the config could not be re-read \((.*)\); this pass did not run', self.e.err)
        self.assertEqual(len(refused), 2, self.e.err)
        self.assertIn('must hold a JSON object, not an array', refused[0])
        self.assertIn('must hold a JSON object, not null', refused[1])
        self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:tdd']['count'], 1)
        self.assert_equivalent()


class TakingTurns(Case):
    """Two collectors on one database: this process, which keeps its cache between passes as the scheduled collector
    does, and a manual --once run in a separate process beside it."""

    def config_file(self):
        cfg = self.e.cfg(projectsRoot=self.e.root)
        cfg['local'] = {'databasePath': self.e.db_path}
        path = os.path.join(self.e.tmp, 'board.config.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        return cfg, path

    def other(self, path):
        r = subprocess.run([sys.executable, '-B', os.path.join(cs.HERE, 'local', 'collector.py'), '--once', '--config', path],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_passes_taken_in_turns_count_every_line_once(self):
        self.e.t.basic()
        self.e.t.basic(sid=SID2)
        cfg, path = self.config_file()
        self.e.run(cfg, now=self.now)
        main, agent = self.e.main_path(SID), self.e.agent_path(SID2, 'acw22')
        spy = self.spy()
        for turn in range(1, 6):  # the other process on odd turns, this one on even turns
            size = os.path.getsize(main)
            raw = append(main, [tes.skill_call(40 + turn, 'toolu_t%d' % turn, 'eng:tdd')])
            append(agent, [tes.reply(10 + turn, 'm-t%d' % turn, text='more')])
            if turn % 2:
                self.other(path)
            else:
                del spy.calls[:]
                self.e.run(cfg, now=self.now)
                # The other process committed since this one's last pass, so it reads from the other's cursor.
                self.assertEqual([(c['seeks'], c['data']) for c in spy.of(main)], [([size], raw)])
            self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:tdd']['count'], turn)
        del spy.calls[:]
        self.e.run(cfg, now=self.now)  # after the other's last pass, nothing is left for this one to read
        self.assertEqual(spy.calls, [])
        self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:tdd']['count'], 5)
        self.assertEqual(self.e.stored()['session'][SID2]['usage']['subagents'][0]['requests'], 6)
        self.assert_equivalent(cfg)

    def test_a_pass_that_meets_the_other_collectors_lock_says_so_and_loses_nothing(self):
        self.e.t.basic()
        other = sqlite3.connect(self.e.db_path, isolation_level=None)
        self.addCleanup(other.close)

        def hold():
            append(self.e.main_path(SID), [tes.skill_call(40, 'toolu_sk', 'eng:tdd')])
            other.execute('BEGIN IMMEDIATE')  # the other collector part-way through its pass
        steps = [hold, lambda: other.execute('ROLLBACK')]
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            if len(sleeps) > len(steps):
                raise KeyboardInterrupt
            steps[len(sleeps) - 1]()
        with mock.patch.object(db, 'TIMEOUT', 0.05), mock.patch('time.sleep', side_effect=sleep):
            code = self.e.main(['--interval', '5'], now=self.now)
        self.assertEqual(code, 0, self.e.err)
        self.assertEqual(len(re.findall(STAMP + re.escape(
            'another collector holds the database lock on %s; this pass did not run' % self.e.db_path), self.e.err)), 1)
        self.assertEqual(len(re.findall(r'^collector: \d+ sessions', self.e.out, re.M)), 2)  # the passes either side
        self.assertEqual(self.e.stored()['session'][SID]['skillUses']['eng:tdd']['count'], 1)
        self.assert_equivalent()


if __name__ == '__main__':
    unittest.main()
