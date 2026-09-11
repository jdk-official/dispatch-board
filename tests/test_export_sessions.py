"""Tests for exporters/export_sessions.py, run against synthetic transcripts in a temporary directory.

Every test passes its own config, projects root and out dir, so nothing here reads board.config.json,
the real ~/.claude/projects or the repo's out/.
"""
import contextlib, io, json, os, shutil, sys, tempfile, time, unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exporters'))
import export_sessions as es  # noqa: E402

BASE = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=3)
SID = '11111111-aaaa-bbbb-cccc-000000000001'
SID2 = '22222222-aaaa-bbbb-cccc-000000000002'
CWD = 'C:\\work\\app'
FOLDER = 'C--work-app'
CW_META = {'agentType': 'engineering-agents:code-writer', 'description': 'PBI-001 widget', 'toolUseId': 'toolu_cw'}


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


def launch(m, tool_id):
    return reply(m, 'msg-launch-' + tool_id, tools=[(tool_id, 'Agent', {'description': 'task'})])


def stop(m, aid):
    return reply(m, 'msg-stop-%s-%d' % (aid, m), tools=[('toolu_stop_%s_%d' % (aid, m), 'TaskStop', {'task_id': aid})])


def notify(m, aid, status='completed', result='', tokens='', ms=''):
    body = ('<task-notification><task-id>%s</task-id><status>%s</status><result>%s</result>'
            '<subagent_tokens>%s</subagent_tokens><duration_ms>%s</duration_ms></task-notification>') % (aid, status, result, tokens, ms)
    return {'type': 'user', 'timestamp': ts(m), 'message': {'role': 'user', 'content': body}}


def inline(m, tool_id, text, tokens=None, ms=None):
    return {'type': 'user', 'timestamp': ts(m), 'toolUseResult': {'status': 'completed', 'totalTokens': tokens, 'totalDurationMs': ms},
            'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'content': [{'type': 'text', 'text': text}]}]}}


def config(build=(), window=10, **sessions):
    s = {'days': 7}
    s.update(sessions)
    return {'build': {'sessions': list(build)}, 'sessions': s, 'runs': {'runningWindowMinutes': window, 'manual': []}}


class Tree:
    """A throwaway projects root and out dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.root = os.path.join(self.tmp, 'projects')
        self.out = os.path.join(self.tmp, 'out')
        os.makedirs(self.root)
        self.err = ''

    def write(self, path, recs):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write((r if isinstance(r, str) else json.dumps(r)) + '\n')
        return path

    def session(self, sid, recs, folder=FOLDER):
        return self.write(os.path.join(self.root, folder, sid + '.jsonl'), recs)

    def agent(self, sid, aid, recs, meta=None, folder=FOLDER):
        path = self.write(os.path.join(self.root, folder, sid, 'subagents', 'agent-%s.jsonl' % aid), recs)
        if meta is not None:
            with io.open(path[:-len('.jsonl')] + '.meta.json', 'w', encoding='utf-8') as f:
                f.write(meta if isinstance(meta, str) else json.dumps(meta))
        return path

    def basic(self, sid=SID, prompt='Please build the widget', folder=FOLDER, cwd=CWD, result='All green. DONE'):
        """One session that launched one code-writer, which finished by notification."""
        self.session(sid, [user(0, prompt, cwd), launch(1, 'toolu_cw'),
                           notify(30, 'acw' + sid[:2], result=result, tokens='5000', ms='1740000')], folder)
        self.agent(sid, 'acw' + sid[:2], [user(1, 'task', cwd), reply(2, 'm-a1', text=result)], CW_META, folder)

    def run(self, cfg=None, projects_root=None):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = es.main(config=cfg or config(), out_dir=self.out, projects_root=projects_root or self.root)
        self.err = err.getvalue()
        return code

    def docs(self, coll):
        d = os.path.join(self.out, coll)
        found = {}
        for f in (os.listdir(d) if os.path.isdir(d) else []):
            with io.open(os.path.join(d, f), encoding='utf-8') as fh:
                found[f[:-5]] = json.load(fh)
        return found

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TreeCase(unittest.TestCase):
    def setUp(self):
        self.t = Tree()
        self.addCleanup(self.t.cleanup)


# ---------------------------------------------------------------- verdicts and kinds

class VerdictOf(unittest.TestCase):
    def test_labelled(self):
        self.assertEqual(es.verdict_of('Summary...\nVerdict: GO-WITH-CONDITIONS', 'cr'), 'GO-WITH-CONDITIONS')
        self.assertEqual(es.verdict_of('**Verdict:** **NO-GO**', 'plan'), 'NO-GO')

    def test_bold_and_backticked(self):
        self.assertEqual(es.verdict_of('Outcome is **CHANGES-REQUIRED** for now', 'ver'), 'CHANGES-REQUIRED')
        self.assertEqual(es.verdict_of('Result: `APPROVED`', 'plan'), 'APPROVED')
        self.assertEqual(es.verdict_of('`DONE-WITH-CONDITIONS` two notes', 'cw'), 'DONE-WITH-CONDITIONS')

    def test_bare(self):
        self.assertEqual(es.verdict_of('Overall GO from me', 'cr'), 'GO')
        self.assertEqual(es.verdict_of('NOT-DONE: two tests still fail', 'cw'), 'NOT-DONE')

    def test_lane_decides_the_vocabulary(self):
        self.assertIsNone(es.verdict_of('Verdict: GO', 'cw'))
        self.assertIsNone(es.verdict_of('Verdict: DONE', 'cr'))
        self.assertIsNone(es.verdict_of('nothing to report', 'cr'))

    def test_rereview_quoting_an_earlier_verdict_takes_the_last_label(self):
        text = 'Round 1 Verdict: NO-GO. All four findings were fixed.\n\nVerdict: GO-WITH-NOTES'
        self.assertEqual(es.verdict_of(text, 'cr'), 'GO-WITH-NOTES')
        self.assertEqual(es.verdict_of('Last round was **NO-GO**; this round is **GO**', 'plan'), 'GO')

    def test_builders_keep_the_leading_token(self):
        self.assertEqual(es.verdict_of('Verdict: NOT-DONE\n... once fixed it will be Verdict: DONE', 'cw'), 'NOT-DONE')
        self.assertEqual(es.verdict_of('DONE. Earlier attempt was NOT-DONE', 'tw'), 'DONE')


class KindOf(unittest.TestCase):
    def test_review_lanes(self):
        self.assertEqual(es.kind_of('NO-GO', 'cr'), 'nogo')
        self.assertEqual(es.kind_of('REJECTED', 'plan'), 'nogo')
        self.assertEqual(es.kind_of('CHANGES-REQUIRED', 'ver'), 'changes')
        self.assertEqual(es.kind_of('GO-WITH-CONDITIONS', 'cr'), 'go')
        self.assertEqual(es.kind_of(None, 'cr'), 'done')

    def test_build_lanes(self):
        self.assertEqual(es.kind_of('DONE', 'cw'), 'done')
        self.assertEqual(es.kind_of('DONE-WITH-CONDITIONS', 'tw'), 'done')
        self.assertEqual(es.kind_of(None, 'cw'), 'done')

    def test_not_done_is_changes_on_build_lanes(self):
        for lane in ('req', 'cw', 'tw'):
            self.assertEqual(es.kind_of('NOT-DONE', lane), 'changes', lane)


# ---------------------------------------------------------------- classification precedence

def fin(m, status='completed', result='', ms=''):
    return {'at': ts(m), 'status': status, 'result': result, 'tokens': '', 'ms': ms}


class Classify(unittest.TestCase):
    def c(self, lane='cr', fin=None, stop_at=None, text='', begin=ts(0), end=ts(30), age=3600, window=600):
        return es.classify(lane, fin, stop_at, text, begin, end, age, window)

    def test_stopped(self):
        self.assertEqual(self.c(stop_at=ts(10))[:2], ('killed', 'stopped'))

    def test_stop_echo_notification_keeps_stopped(self):
        # TaskStop is followed by the platform's own "killed" notification for that task.
        self.assertEqual(self.c(fin=fin(11, 'killed'), stop_at=ts(10))[:2], ('killed', 'stopped'))

    def test_stopped_then_resumed_and_completed(self):
        self.assertEqual(self.c(fin=fin(30, result='Verdict: GO'), stop_at=ts(10))[:2], ('go', 'GO'))

    def test_completion_before_an_ineffective_stop_keeps_its_verdict(self):
        # A stop that kills something is echoed by a later "killed" notification; a completion that is
        # still the latest notification means the stop came too late to matter.
        self.assertEqual(self.c(fin=fin(5, result='Verdict: GO'), stop_at=ts(10))[:2], ('go', 'GO'))

    def test_rate_limit(self):
        self.assertEqual(self.c(text="You've hit your session limit · resets 4pm")[:2], ('killed', 'killed · rate limit'))
        self.assertEqual(self.c(fin=fin(30, result="You've hit your session limit"))[:2], ('killed', 'killed · rate limit'))

    def test_completed(self):
        self.assertEqual(self.c(fin=fin(30, result='Verdict: NO-GO'))[:2], ('nogo', 'NO-GO'))
        self.assertEqual(self.c(fin=fin(30, result='no token here'), text='**GO**')[:2], ('go', 'GO'))
        self.assertEqual(self.c(fin=fin(30, result='nothing'))[:2], ('done', 'finished'))
        self.assertEqual(self.c(lane='cw', fin=fin(30, result='NOT-DONE: 2 failing'))[:2], ('changes', 'NOT-DONE'))

    def test_failed_finish(self):
        self.assertEqual(self.c(fin=fin(30, 'failed'))[:2], ('killed', 'failed'))
        self.assertEqual(self.c(fin=fin(30, ''))[:2], ('killed', 'failed'))

    def test_running_window(self):
        self.assertEqual(self.c(age=60)[:2], ('running', 'running'))
        self.assertEqual(self.c(age=900)[:2], ('killed', 'no result'))

    def test_minutes(self):
        self.assertEqual(self.c(fin=fin(30, ms='120000'))[2], 2)
        self.assertEqual(self.c(fin=fin(30, ms=''))[2], 30)

    def test_minutes_survive_malformed_numbers_and_timestamps(self):
        self.assertEqual(self.c(fin=fin(30, ms='soon'))[2], 30)
        self.assertEqual(self.c(fin=fin(30, ms='1e400'))[2], 30)
        self.assertEqual(self.c(begin='not a date')[2], 0)


# ---------------------------------------------------------------- link()

def row(rid, lane, kind, start, end, pbis=(), fix=False):
    return {'id': rid, 'lane': lane, 'kind': kind, 'start': ts(start), 'end': ts(end), 'pbis': list(pbis), 'fix': fix}


class Link(unittest.TestCase):
    def test_builder_comes_from_the_plan_gate(self):
        rows = [row('p1', 'plan', 'go', 0, 5, ['001']), row('c1', 'cw', 'done', 6, 20, ['001'])]
        es.link(rows)
        self.assertEqual(rows[1].get('from'), 'p1')

    def test_review_comes_from_the_last_finished_build(self):
        rows = [row('c1', 'cw', 'done', 0, 10, ['001']), row('c2', 'cw', 'changes', 11, 20, ['001']),
                row('r1', 'cr', 'go', 21, 30, ['001'])]
        es.link(rows)
        self.assertEqual(rows[2].get('from'), 'c1')  # the NOT-DONE build is not a hand-off

    def test_fix_is_fed_by_the_review(self):
        rows = [row('r1', 'cr', 'changes', 0, 10, ['001']), row('c1', 'cw', 'done', 11, 20, ['001'], fix=True)]
        es.link(rows)
        self.assertEqual(rows[1].get('feeds'), 'r1')

    def test_parallel_group(self):
        rows = [row('a', 'cw', 'done', 0, 10), row('b', 'cw', 'done', 1, 10), row('d', 'cw', 'done', 10, 20)]
        es.link(rows)
        self.assertEqual([r.get('group') for r in rows], ['A', 'A', None])


# ---------------------------------------------------------------- pipeline

class WriteJson(TreeCase):
    def test_a_failed_write_keeps_the_previous_file(self):
        path = os.path.join(self.t.tmp, 'sessions.json')
        es.write_json(path, {'a': 1})
        with self.assertRaises(TypeError):
            es.write_json(path, {'a': object()})  # not serialisable
        with io.open(path, encoding='utf-8') as f:
            self.assertEqual(json.load(f), {'a': 1})
        self.assertEqual(sorted(os.listdir(self.t.tmp)), ['projects', 'sessions.json'])  # no temp file left behind


class Records(TreeCase):
    def test_only_dict_records(self):
        p = self.t.write(os.path.join(self.t.tmp, 'x.jsonl'), ['1', '[]', 'null', '"s"', '{"a": 1}', '{broken'])
        self.assertEqual([o for _, o in es.records(p)], [{'a': 1}])


class Pipeline(TreeCase):
    def test_basic_export(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        runs, sessions = self.t.docs('runs'), self.t.docs('sessions')
        self.assertEqual(list(sessions), [SID])
        self.assertEqual(runs['acw11']['kind'], 'done')
        self.assertEqual(runs['acw11']['tok'], 5000)
        self.assertEqual(runs['acw11']['min'], 29)

    def test_not_done_builder_is_changes_and_does_not_hand_off(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), notify(10, 'acw', result='NOT-DONE: 2 failing'),
                             launch(11, 'toolu_cr'), notify(20, 'acr', result='Verdict: NO-GO')])
        self.t.agent(SID, 'acw', [reply(2, 'a', text='NOT-DONE')], CW_META)
        self.t.agent(SID, 'acr', [reply(12, 'b', text='NO-GO')],
                     {'agentType': 'review-agents:code-reviewer', 'description': 'PBI-001 review', 'toolUseId': 'toolu_cr'})
        self.assertEqual(self.t.run(), 0)
        runs = self.t.docs('runs')
        self.assertEqual(runs['acw']['kind'], 'changes')
        self.assertNotIn('from', runs['acr'])

    def test_inline_result(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), inline(5, 'toolu_cw', 'DONE', tokens=77, ms=240000)])
        self.t.agent(SID, 'acw', [reply(2, 'a', text='DONE')], CW_META)
        self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw']
        self.assertEqual((run['kind'], run['verdict'], run['tok'], run['min']), ('done', 'DONE', 77, 4))

    def test_window_days_on_the_session_doc(self):
        self.t.basic()
        self.t.run(config(days=3))
        self.assertEqual(self.t.docs('sessions')[SID]['windowDays'], 3)

    def test_window_minutes_on_the_session_doc(self):
        self.t.basic()
        self.t.run(config(window=25))
        self.assertEqual(self.t.docs('sessions')[SID]['windowMinutes'], 25)


class Malformed(TreeCase):
    def test_truncated_meta_falls_back_to_empty(self):
        self.t.basic()
        self.t.agent(SID, 'abad', [reply(3, 'x', text='hi')], '{"agentType": "engin')
        self.assertEqual(self.t.run(), 0)
        runs = self.t.docs('runs')
        self.assertEqual(runs['abad']['lane'], 'other')
        self.assertEqual(runs['acw11']['lane'], 'cw')

    def test_meta_that_is_not_an_object(self):
        self.t.basic()
        self.t.agent(SID, 'alist', [reply(3, 'x', text='hi')], '[1, 2]')
        self.assertEqual(self.t.run(), 0)
        self.assertIn('alist', self.t.docs('runs'))

    def test_non_object_lines_are_skipped(self):
        self.t.session(SID, ['42', '[1]', 'null', user(0, 'go'), '"text"', launch(1, 'toolu_cw'), notify(5, 'acw', result='DONE')])
        self.t.agent(SID, 'acw', ['7', reply(2, 'a', text='DONE'), '[]'], CW_META)
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'done')

    def test_unreadable_subagent_is_skipped_with_a_warning(self):
        self.t.basic()
        os.makedirs(os.path.join(self.t.root, FOLDER, SID, 'subagents', 'agent-broken.jsonl'))
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['acw11'])
        self.assertIn('broken', self.t.err)

    def flaky_read(self, aid):
        """read_subagent that fails, as a locked file would, for one agent."""
        real = es.read_subagent

        def read(path):
            if os.path.basename(path) == 'agent-%s.jsonl' % aid:
                raise PermissionError(13, 'Permission denied', path)
            return real(path)
        return mock.patch.object(es, 'read_subagent', read)

    def test_transient_agent_read_error_does_not_drop_the_run_for_good(self):
        # Both agents have finished, so nothing about the session forces a re-read.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), notify(20, 'acw11', result='DONE', tokens='5000'),
                             notify(21, 'aother', result='found it')])
        self.t.agent(SID, 'acw11', [reply(2, 'a', text='DONE')], CW_META)
        self.t.agent(SID, 'aother', [reply(3, 'x', text='hi')], {'agentType': 'Explore', 'description': 'look around'})
        with self.flaky_read('acw11'):
            self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['aother'])
        self.assertIn('acw11', self.t.err)
        # Nothing on disk changed, but the next run must re-read the session rather than reuse the partial result.
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['acw11', 'aother'])
        self.assertEqual(self.t.docs('sessions')[SID]['runs'], 2)

    def test_agent_that_cannot_be_reread_keeps_its_last_row(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        with io.open(os.path.join(self.t.root, FOLDER, SID + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(user(40, 'more')) + '\n')
        with self.flaky_read('acw11'):
            self.assertEqual(self.t.run(), 0)
        runs = self.t.docs('runs')
        self.assertEqual(sorted(runs), ['acw11'])  # carried over, so refresh.py does not delete it
        self.assertEqual((runs['acw11']['kind'], runs['acw11']['tok']), ('done', 5000))
        self.assertEqual(self.t.docs('sessions')[SID]['last'], ts(40))
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['acw11'])

    def test_malformed_numeric_tags(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), notify(20, 'acw', result='DONE', tokens='12k', ms='soon')])
        self.t.agent(SID, 'acw', [reply(2, 'a', text='DONE')], CW_META)
        self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw']
        self.assertEqual(run['tok'], 1160)  # falls back to the agent's last context size
        self.assertEqual(run['min'], 19)

    def test_subagent_file_that_vanishes_is_skipped(self):
        self.t.basic()
        self.t.agent(SID, 'agone', [reply(3, 'x', text='hi')], {'agentType': 'x'})
        real = os.path.getmtime

        def getmtime(p):
            if 'agent-agone' in str(p):
                raise FileNotFoundError(p)
            return real(p)
        with mock.patch.object(es.os.path, 'getmtime', getmtime):
            self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['acw11'])

    def test_main_transcript_that_vanishes_is_skipped(self):
        self.t.basic()
        self.t.basic(SID2)
        real = os.path.getsize

        def getsize(p):
            if str(p).endswith(SID2 + '.jsonl'):
                raise FileNotFoundError(p)
            return real(p)
        with mock.patch.object(es.os.path, 'getsize', getsize):
            self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('sessions')), [SID])

    def test_failed_parse_keeps_the_previous_result(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        with io.open(os.path.join(self.t.root, FOLDER, SID + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(user(40, 'more')) + '\n')
        with mock.patch.object(es, 'parse_session', side_effect=RuntimeError('boom')):
            self.assertEqual(self.t.run(), 0)
        self.assertIn(SID, self.t.docs('sessions'))
        self.assertIn('acw11', self.t.docs('runs'))
        self.assertIn('boom', self.t.err)
        # The session is retried on the next run rather than frozen on the old result.
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['last'], ts(40))

    def test_failed_parse_without_a_cached_result_omits_the_session(self):
        self.t.basic()
        self.t.basic(SID2)
        real = es.parse_session

        def flaky(base, sid, *a, **kw):
            if sid == SID2:
                raise ValueError('bad transcript')
            return real(base, sid, *a, **kw)
        with mock.patch.object(es, 'parse_session', flaky):
            self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('sessions')), [SID])


class Discovery(TreeCase):
    def test_missing_projects_root_fails_and_keeps_the_last_export(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        code = self.t.run(projects_root=os.path.join(self.t.tmp, 'nowhere'))
        self.assertNotEqual(code, 0)
        self.assertIn(SID, self.t.docs('sessions'))

    def test_missing_build_transcript_fails(self):
        self.t.basic()
        self.assertNotEqual(self.t.run(config(build=['99999999-0000-0000-0000-000000000000'])), 0)
        self.assertIn('99999999', self.t.err)


class Cache(TreeCase):
    def count_parses(self, cfg=None):
        real, calls = es.parse_session, []

        def spy(*a, **kw):
            calls.append(a[1])
            return real(*a, **kw)
        with mock.patch.object(es, 'parse_session', spy):
            self.assertEqual(self.t.run(cfg), 0)
        return len(calls)

    def test_reused_when_nothing_changed(self):
        self.t.basic()
        self.assertEqual(self.count_parses(), 1)
        self.assertEqual(self.count_parses(), 0)

    def test_invalidated_by_a_transcript_change(self):
        self.t.basic()
        self.count_parses()
        with io.open(os.path.join(self.t.root, FOLDER, SID + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(user(40, 'more')) + '\n')
        self.assertEqual(self.count_parses(), 1)

    def test_build_sessions_change_applies_without_a_transcript_change(self):
        self.t.basic()
        self.t.run(config())
        self.assertFalse(self.t.docs('sessions')[SID]['build'])
        self.t.run(config(build=[SID]))
        self.assertTrue(self.t.docs('sessions')[SID]['build'])
        self.t.run(config())
        self.assertFalse(self.t.docs('sessions')[SID]['build'])

    def test_running_window_change_applies_without_a_transcript_change(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw')])
        path = self.t.agent(SID, 'acw', [reply(2, 'a', text='working')], CW_META)
        old = time.time() - 30 * 60
        os.utime(path, (old, old))
        self.t.run(config(window=10))
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'killed')
        self.t.run(config(window=60))
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'running')


class Privacy(TreeCase):
    def test_exclude_by_cwd(self):
        self.t.basic()
        self.t.basic(SID2, folder='C--work-secret-app', cwd='C:\\work\\secret-app')
        self.assertEqual(self.t.run(config(exclude=['C:/work/secret*'])), 0)
        self.assertEqual(sorted(self.t.docs('sessions')), [SID])
        self.assertEqual(sorted(self.t.docs('runs')), ['acw11'])

    def test_exclude_by_project_folder(self):
        self.t.basic()
        self.t.basic(SID2, folder='C--work-private', cwd='D:\\elsewhere')
        self.assertEqual(self.t.run(config(exclude=['*-private'])), 0)
        self.assertEqual(sorted(self.t.docs('sessions')), [SID])

    def test_excluded_sessions_are_not_cached(self):
        self.t.basic(SID2, folder='C--work-private')
        self.t.run(config(exclude=['*-private']))
        with io.open(os.path.join(self.t.out, '.cache', 'sessions.json'), encoding='utf-8') as f:
            cache = f.read()
        self.assertNotIn(SID2, cache)

    def test_first_prompt_is_off_by_default(self):
        self.t.basic(prompt='Please build the widget')
        self.t.run()
        doc = self.t.docs('sessions')[SID]
        self.assertNotIn('firstPrompt', doc)
        self.assertNotIn('widget', doc['title'])

    def test_first_prompt_when_on_is_redacted(self):
        secrets = ['sk-ant-api03-abcdefghijklmnop', 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', 'AKIAIOSFODNN7EXAMPLE',
                   '0123456789abcdef0123456789abcdef01', 'QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo0MjQyMg==', 'hunter2', 'tok3n-value']
        prompt = ('Deploy with %s and %s, key %s, hash %s, blob %s, password=%s token=%s please' % tuple(secrets))
        self.t.basic(prompt=prompt)
        self.t.run(config(showFirstPrompt=True))
        doc = self.t.docs('sessions')[SID]
        self.assertTrue(doc['firstPrompt'].startswith('Deploy with'))
        for s in secrets:
            self.assertNotIn(s, doc['firstPrompt'])
            self.assertNotIn(s, doc['title'])

    def test_toggling_first_prompt_applies_without_a_transcript_change(self):
        self.t.basic()
        self.t.run(config(showFirstPrompt=True))
        self.assertIn('firstPrompt', self.t.docs('sessions')[SID])
        self.t.run(config())
        self.assertNotIn('firstPrompt', self.t.docs('sessions')[SID])


class Redact(unittest.TestCase):
    def test_patterns(self):
        for secret in ('sk-proj-AbCdEfGhIjKlMnOpQrSt', 'gho_abcdefghijklmnopqrstuvwxyz0123', 'ghs_abcdefghijklmnopqrstuvwxyz0123',
                       'AKIAABCDEFGHIJKLMNOP', 'deadbeefdeadbeefdeadbeefdeadbeef', 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo0'):
            self.assertNotIn(secret, es.redact('use ' + secret + ' now'), secret)
        self.assertEqual(es.redact('password=hunter2 and TOKEN: abc'), 'password=[redacted] and TOKEN: [redacted]')

    def test_ordinary_text_is_untouched(self):
        text = 'Refactor the session picker so the 7-day window is configurable; see PBI-010 and commit 2a8ce40.'
        self.assertEqual(es.redact(text), text)


if __name__ == '__main__':
    unittest.main()
