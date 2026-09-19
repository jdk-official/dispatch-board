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
        self.assertIsNone(es.verdict_of('Verdict: exercised', 'cr'))
        self.assertIsNone(es.verdict_of('Verdict: fallback-declared', 'cw'))

    def test_rereview_quoting_an_earlier_verdict_takes_the_last_label(self):
        text = 'Round 1 Verdict: NO-GO. All four findings were fixed.\n\nVerdict: GO-WITH-NOTES'
        self.assertEqual(es.verdict_of(text, 'cr'), 'GO-WITH-NOTES')
        self.assertEqual(es.verdict_of('Last round was **NO-GO**; this round is **GO**', 'plan'), 'GO')

    def test_builders_keep_the_leading_token(self):
        self.assertEqual(es.verdict_of('Verdict: NOT-DONE\n... once fixed it will be Verdict: DONE', 'cw'), 'NOT-DONE')
        self.assertEqual(es.verdict_of('DONE. Earlier attempt was NOT-DONE', 'tw'), 'DONE')

    # A verifier leads with its outcome, then says what it observed or why it could not run the flow.
    def test_a_fallback_headline_that_goes_on_to_say_not_exercised_stays_fallback_declared(self):
        text = 'fallback-declared - no headless entrypoint; the live path was not exercised.'
        self.assertEqual(es.verdict_of(text, 'ver'), 'fallback-declared')

    def test_a_json_outcome_is_read_before_the_prose(self):
        block = ('```json\n{"schema_version": "1", "report": {"agent": "verifier", "outcome": "%s", '
                 '"summary": "..."}, "fallback_reason": "no headless entrypoint"}\n```\n')
        self.assertEqual(es.verdict_of(block % 'fallback-declared' + 'The flow was not exercised.', 'ver'), 'fallback-declared')
        self.assertEqual(es.verdict_of(block % 'exercised' + 'The error path was not exercised.', 'ver'), 'exercised')

    def test_the_verifier_words_are_read_in_any_case(self):
        self.assertEqual(es.verdict_of('Outcome: Exercised', 'ver'), 'exercised')
        self.assertEqual(es.verdict_of('**Outcome:** `FALLBACK-DECLARED`', 'ver'), 'fallback-declared')
        self.assertEqual(es.verdict_of('Exercised - ran the /greet flow.', 'ver'), 'exercised')

    def test_a_negated_verifier_word_is_never_the_outcome(self):
        for negated in ('not exercised', 'could not be exercised', "wasn't exercised", 'was never exercised',
                        "hasn't been exercised", 'cannot be exercised', 'not **exercised**', 'not fallback-declared'):
            with self.subTest(negated=negated):
                self.assertIsNone(es.verdict_of('The live path was %s: no headless entrypoint.' % negated, 'ver'))

    def test_the_first_bare_verifier_word_leads_but_a_bare_fallback_is_preferred(self):
        self.assertEqual(es.verdict_of('exercised - ran /greet; the error path was not exercised', 'ver'), 'exercised')
        self.assertEqual(es.verdict_of('Unit checks exercised, but the live flow is fallback-declared.', 'ver'), 'fallback-declared')

    # Without an outcome label, a bold, code-quoted or Verdict-labelled exercised must not outrank a bare
    # fallback-declared: claiming a run that never happened is the one-sided risk.
    def test_without_an_outcome_label_any_fallback_wins_whatever_form_each_word_takes(self):
        for text in ('fallback-declared (headless run infeasible; `exercised` needs a browser)',
                     'fallback-declared: the flow could only be `exercised` in a browser',
                     'fallback-declared. **Exercised** requires Playwright, which I lack.',
                     'fallback-declared, as the Verdict: exercised run needs a browser'):
            with self.subTest(text=text):
                self.assertEqual(es.verdict_of(text, 'ver'), 'fallback-declared')

    def test_an_outcome_label_still_decides_over_any_other_mention(self):
        self.assertEqual(es.verdict_of('Outcome: exercised. Last round was **fallback-declared**.', 'ver'), 'exercised')
        self.assertEqual(es.verdict_of('{"outcome": "exercised"} `fallback-declared` was round 1', 'ver'), 'exercised')

    def test_unable_to_rather_than_and_instead_of_negate_the_word_after_them(self):
        for negated in ('unable to be exercised', 'unable to exercise it, so not exercised', 'skipped rather than exercised',
                        'read instead of being exercised'):
            with self.subTest(negated=negated):
                self.assertIsNone(es.verdict_of('The live path was %s: no headless entrypoint.' % negated, 'ver'))
        self.assertEqual(es.verdict_of('exercised rather than fallback-declared: Playwright ran the flow.', 'ver'), 'exercised')


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

    def test_verifier_result_words_are_the_verdict_and_the_kind_stays_done(self):
        for word in ('exercised', 'fallback-declared'):
            self.assertEqual(self.c(lane='ver', fin=fin(30, result='Verdict: %s' % word))[:2], ('done', word))
        # A labelled or bold word wins over one mentioned in passing.
        self.assertEqual(self.c(lane='ver', fin=fin(30, result='**fallback-declared**: the live path was not exercised'))[:2],
                         ('done', 'fallback-declared'))
        self.assertEqual(self.c(lane='cr', fin=fin(30, result='Verdict: exercised'))[:2], ('done', 'finished'))
        self.assertEqual(self.c(lane='ver', fin=fin(30, result='fallback-declared - no headless entrypoint; the live path was not exercised'))[:2],
                         ('done', 'fallback-declared'))

    def test_minutes(self):
        self.assertEqual(self.c(fin=fin(30, ms='120000'))[2], 2)
        self.assertEqual(self.c(fin=fin(30, ms=''))[2], 30)

    def test_minutes_survive_malformed_numbers_and_timestamps(self):
        self.assertEqual(self.c(fin=fin(30, ms='soon'))[2], 30)
        self.assertEqual(self.c(fin=fin(30, ms='1e400'))[2], 30)
        self.assertEqual(self.c(begin='not a date')[2], 0)


class Carried(unittest.TestCase):
    ROW = {'id': 'a', 'kind': 'running', 'verdict': 'running', 'end': ts(0)}

    def test_only_a_running_row_past_the_window_changes(self):
        at = es.epoch(ts(0))
        self.assertEqual(es.carried(self.ROW, 600, at + 599), self.ROW)
        self.assertEqual(es.carried(self.ROW, 600, at + 600), dict(self.ROW, kind='killed', verdict='no result'))
        done = dict(self.ROW, kind='done', verdict='DONE')
        self.assertEqual(es.carried(done, 600, at + 9999), done)
        self.assertEqual(self.ROW['kind'], 'running')  # the cached row itself is not changed

    def test_a_running_row_without_a_readable_end_is_killed(self):
        for end in (None, 'soon', 5):
            self.assertEqual(es.carried(dict(self.ROW, end=end), 600, time.time())['kind'], 'killed', end)


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

    def test_a_deeply_nested_line_is_skipped(self):
        p = self.t.write(os.path.join(self.t.tmp, 'x.jsonl'), ['[' * 100000 + ']' * 100000, '{"a": 1}'])
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

    def test_verifier_that_exercised_its_checks(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_ver'),
                             notify(10, 'aver', result='Verdict: exercised. The happy path and both failure paths ran.')])
        self.t.agent(SID, 'aver', [reply(2, 'a', text='exercised')],
                     {'agentType': 'review-agents:verifier', 'description': 'Verify PBI-001', 'toolUseId': 'toolu_ver'})
        self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['aver']
        self.assertEqual((run['lane'], run['kind'], run['verdict']), ('ver', 'done', 'exercised'))

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

    def test_a_running_agent_that_cannot_be_reread_is_killed_once_the_window_has_passed(self):
        # The agent's last record is three hours old but its file was just written, so the first run sees it running.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw')])
        self.t.agent(SID, 'acw', [reply(2, 'a', text='working')], CW_META)
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'running')
        with self.flaky_read('acw'):
            self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw']
        self.assertEqual((run['kind'], run['verdict']), ('killed', 'no result'))
        self.assertEqual(self.t.docs('sessions')[SID]['running'], 0)

    def test_a_running_agent_that_cannot_be_reread_stays_running_within_the_window(self):
        # BASE is three hours ago, so minute 178 is two minutes ago: well inside the 10-minute window.
        self.t.session(SID, [user(176, 'go'), launch(177, 'toolu_cw')])
        self.t.agent(SID, 'acw', [reply(178, 'a', text='working')], CW_META)
        self.assertEqual(self.t.run(), 0)
        with self.flaky_read('acw'):
            self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw']
        self.assertEqual((run['kind'], run['verdict']), ('running', 'running'))

    def test_a_string_token_count_skips_only_that_response(self):
        def bad(m, mid, value):
            r = reply(m, mid, text='x')
            r['message']['usage']['output_tokens'] = value
            return r
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), bad(2, 'm-bad-main', float('nan')),
                             notify(20, 'acw', result='DONE', tokens='5000'), notify(21, 'aother', result='found it')])
        self.t.agent(SID, 'acw', [reply(3, 'a', text='DONE'), bad(4, 'm-bad-agent', '10')], CW_META)
        self.t.agent(SID, 'aother', [reply(5, 'x', text='hi')], {'agentType': 'Explore', 'description': 'look around'})
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(sorted(self.t.docs('runs')), ['acw', 'aother'])
        session = self.t.docs('sessions')[SID]
        self.assertEqual(session['runs'], 2)
        self.assertEqual(session['usage']['totals']['requests'], 3)  # the launch reply and one reply per agent

    def test_a_deeply_nested_line_costs_only_that_line(self):
        # An exclude list makes the exporter read each transcript's working folder before anything else.
        deep = '[' * 100000 + ']' * 100000
        self.t.session(SID, [deep, user(0, 'go'), launch(1, 'toolu_cw'), notify(5, 'acw', result='DONE')])
        self.t.agent(SID, 'acw', [deep, reply(2, 'a', text='DONE')], CW_META)
        self.assertEqual(self.t.run(config(exclude=['*-private'])), 0)
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'done')
        self.assertEqual(self.t.docs('sessions')[SID]['cwd'], CWD)

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

    def test_a_running_row_in_a_session_that_cannot_be_parsed_is_killed_once_the_window_has_passed(self):
        # The agent's last record is three hours old but its file was just written, so the first run sees it running.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw')])
        self.t.agent(SID, 'acw', [reply(2, 'a', text='working')], CW_META)
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('runs')['acw']['kind'], 'running')
        with mock.patch.object(es, 'parse_session', side_effect=RuntimeError('boom')):
            self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw']
        self.assertEqual((run['kind'], run['verdict']), ('killed', 'no result'))
        self.assertEqual(self.t.docs('sessions')[SID]['running'], 0)
        # Only the export changes: the cache keeps the row as it was read, so the session is re-read next run.
        with io.open(os.path.join(self.t.out, '.cache', 'sessions.json'), encoding='utf-8') as f:
            self.assertEqual([r['kind'] for r in json.load(f)[SID]['result']['rows']], ['running'])

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


class ConfigTypes(TreeCase):
    def assert_refused(self, cfg, key):
        self.assertEqual(self.t.run(cfg), 2)
        self.assertIn(key, self.t.err)
        self.assertEqual(self.t.docs('sessions'), {})

    def test_show_first_prompt_as_a_string_is_refused(self):
        self.t.basic()
        self.assert_refused(config(showFirstPrompt='false'), 'sessions.showFirstPrompt')

    def test_exclude_as_a_string_is_refused(self):
        self.t.basic()
        self.assert_refused(config(exclude='*-private'), 'sessions.exclude')

    def test_each_documented_type_is_checked(self):
        self.t.basic()
        for block, key, value in (('sessions', 'days', '7'), ('sessions', 'days', True), ('sessions', 'projectsRoot', 5),
                                  ('sessions', 'exclude', ['*-private', 3]), ('sessions', 'showFirstPrompt', 0),
                                  ('runs', 'runningWindowMinutes', '10'), ('runs', 'manual', {'id': 'x'})):
            with self.subTest(key=key, value=value):
                cfg = config()
                cfg[block][key] = value
                self.assert_refused(cfg, '%s.%s' % (block, key))

    def test_a_block_that_is_not_an_object_is_refused(self):
        self.t.basic()
        for block in ('sessions', 'runs'):
            with self.subTest(block=block):
                cfg = config()
                cfg[block] = ['x']
                self.assert_refused(cfg, '"%s"' % block)

    def test_documented_types_are_accepted(self):
        self.t.basic()
        cfg = config(days=2, exclude=['*-private'], showFirstPrompt=False, projectsRoot=self.t.root)
        cfg['runs']['runningWindowMinutes'] = 15
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(self.t.err, '')

    def test_a_bad_manual_row_is_refused_by_name(self):
        self.t.basic()
        cfg = config()
        cfg['runs']['manual'] = [{'id': 'orch-typo', 'after': 'acw11', 'label': 'x', 'lane': 'orhc'}]
        self.assert_refused(cfg, 'orch-typo')
        self.assertIn('lane', self.t.err)

    def test_an_unusable_worktree_roots_value_is_refused_naming_the_project(self):
        self.t.basic()
        for value in ('x', None, [1], [''], ['/'], ['\\'], ['C:/'], ['C:\\'], ['C:'], ['relative/x'], ['.'], [' '],
                      ['~/x'], ['\\\\server\\share'], ['//server'], ['//server/share'], ['C:/x ']):
            with self.subTest(value=value):
                self.assert_refused(pconfig(proj('app', SID, repoPath=REPO, worktreeRoots=value)), 'worktreeRoots')
                self.assertIn('project app', self.t.err)

    def test_a_repo_path_that_is_not_a_string_or_null_is_refused(self):
        self.t.basic()
        for value in (5, False, ['C:/x']):
            with self.subTest(value=value):
                self.assert_refused(pconfig(proj('app', SID, repoPath=value)), 'repoPath')
                self.assertIn('project app', self.t.err)

    def test_a_null_or_root_repo_path_is_accepted_and_links_nothing(self):
        edit_session(self.t, SID, 'C:/a.py', '//server/share/b.py', 'C:/x/c.py')
        for value in (None, 'C:/', '\\\\server\\share'):
            with self.subTest(value=value):
                self.assertEqual(self.t.run(pconfig(proj('app', repoPath=value))), 0)
                self.assertEqual(self.t.docs('projects')['app']['repoPath'], value or '')
                self.assertEqual(linked(self.t, SID), (None, None))


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

    def test_a_link_config_change_applies_without_a_transcript_change(self):
        # FR-40: the link is decided from the cached evidence each run, so none of these re-reads a transcript.
        edit_session(self.t, SID, REPO + '/a.py')
        self.assertEqual(self.count_parses(pconfig(proj('a'), proj('p', repoPath=REPO))), 1)
        self.assertEqual(linked(self.t, SID), ('p', 'edits'))
        for cfg, want in ((pconfig(proj('a'), proj('p', repoPath='C:/moved')), (None, None)),
                          (pconfig(proj('a'), proj('p', repoPath='C:/moved', worktreeRoots=['C:/work'])), ('p', 'edits')),
                          (pconfig(proj('a', SID), proj('p', repoPath=REPO)), ('a', 'config'))):
            with self.subTest(cfg=cfg['projects']):
                self.assertEqual(self.count_parses(cfg), 0)
                self.assertEqual(linked(self.t, SID), want)

    def test_a_cache_from_before_main_edits_were_parsed_is_read_again(self):
        # PARSER_VERSION 10 cached no main-transcript edits, so such an entry must not be replayed as a session
        # that edited nothing.
        self.assertGreater(es.PARSER_VERSION, 10)
        edit_session(self.t, SID, REPO + '/a.py')
        cfg = pconfig(proj('p', repoPath=REPO))
        self.assertEqual(self.t.run(cfg), 0)
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        cache[SID]['sig'][0] = 10
        del cache[SID]['result']['doc']['edits']
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        self.assertEqual(self.count_parses(cfg), 1)
        self.assertEqual(linked(self.t, SID), ('p', 'edits'))

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


def skill_call(m, tool_id, skill, args=None):
    inp = {'skill': skill} if args is None else {'skill': skill, 'args': args}
    return reply(m, 'msg-skill-' + tool_id, tools=[(tool_id, 'Skill', inp)])


def typed(m, name, meta=None, order='message-first'):
    """A slash command the owner typed, recorded as Claude Code writes it."""
    msg, nm = '<command-message>%s</command-message>' % name.lstrip('/'), '<command-name>%s</command-name>' % name
    rec = user(m, msg + '\n' + nm if order == 'message-first' else nm + '\n' + msg + '\n<command-args></command-args>')
    if meta is not None:
        rec['isMeta'] = meta
    return rec


class CatalogueUsage(TreeCase):
    """What the agent catalogue tab counts: agentType and start on runs, skillUses on sessions."""

    def test_subagent_runs_carry_agent_type_and_start(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['acw11']
        self.assertEqual((run['agentType'], run['start']), ('engineering-agents:code-writer', ts(1)))

    def test_no_agent_type_when_the_meta_is_missing_or_empty(self):
        self.t.basic()
        self.t.agent(SID, 'anometa', [reply(3, 'x', text='hi')])
        self.t.agent(SID, 'aempty', [reply(4, 'y', text='hi')], {'agentType': '', 'description': 'blank'})
        self.assertEqual(self.t.run(), 0)
        runs = self.t.docs('runs')
        self.assertNotIn('agentType', runs['anometa'])
        self.assertNotIn('agentType', runs['aempty'])
        self.assertEqual(runs['anometa']['start'], ts(3))  # falls back to the agent's first timestamp

    def test_no_start_when_the_launch_time_is_unknown(self):
        self.t.basic()
        undated = reply(3, 'z', text='hi')
        del undated['timestamp']
        self.t.agent(SID, 'aundated', [undated], {'agentType': 'Plan', 'description': 'gate'})
        self.assertEqual(self.t.run(), 0)
        run = self.t.docs('runs')['aundated']
        self.assertNotIn('start', run)
        self.assertEqual(run['agentType'], 'Plan')

    def test_manual_rows_carry_neither(self):
        self.t.basic()
        cfg = config()
        cfg['runs']['manual'] = [{'id': 'orch-x', 'after': 'acw11', 'label': 'in-line work'}]
        self.assertEqual(self.t.run(cfg), 0)
        run = self.t.docs('runs')['orch-x']
        self.assertNotIn('agentType', run)
        self.assertNotIn('start', run)

    def test_sessions_without_skill_use_carry_an_empty_map(self):
        self.t.basic()
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses'], {})

    def test_skill_calls_and_typed_plugin_commands_are_counted(self):
        undated = skill_call(0, 'toolu_sk_undated', 'backlog-delivery:pbi-review')
        del undated['timestamp']
        self.t.session(SID, [
            user(0, 'go'),
            skill_call(1, 'toolu_sk1', 'backlog-delivery:pbi-plan', args='SECRET-ARGUMENT docs/prd.md'),
            skill_call(5, 'toolu_sk2', 'backlog-delivery:pbi-plan'),
            skill_call(3, 'toolu_sk3', 'loop'),  # a bare Skill id is still a use; the page decides what it matches
            typed(4, '/anthropic-skills:i-have-adhd'),
            typed(6, '/review-agents:triage', order='name-first'),
            undated,
        ])
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses'], {
            'backlog-delivery:pbi-plan': {'count': 2, 'last': ts(5)},
            'loop': {'count': 1, 'last': ts(3)},
            'anthropic-skills:i-have-adhd': {'count': 1, 'last': ts(4)},
            'review-agents:triage': {'count': 1, 'last': ts(6)},
            'backlog-delivery:pbi-review': {'count': 1},
        })
        for coll in ('sessions', 'runs'):
            for d in self.t.docs(coll).values():
                self.assertNotIn('SECRET-ARGUMENT', json.dumps(d))
        with io.open(os.path.join(self.t.out, '.cache', 'sessions.json'), encoding='utf-8') as f:
            self.assertNotIn('SECRET-ARGUMENT', f.read())

    def test_a_use_without_a_timestamp_leaves_last_unchanged(self):
        undated = skill_call(0, 'toolu_u', 'backlog-delivery:pbi-plan')
        del undated['timestamp']
        self.t.session(SID, [user(0, 'go'), skill_call(2, 'toolu_a', 'backlog-delivery:pbi-plan'), undated])
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses'], {'backlog-delivery:pbi-plan': {'count': 2, 'last': ts(2)}})

    def test_a_streamed_skill_call_seen_twice_counts_once(self):
        call = skill_call(2, 'toolu_same', 'backlog-delivery:pbi-plan')
        self.t.session(SID, [user(0, 'go'), call, call])
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses']['backlog-delivery:pbi-plan']['count'], 1)

    def test_command_text_anywhere_else_is_not_counted(self):
        cmd = '<command-name>/%s</command-name>'
        tool_result = {'type': 'user', 'timestamp': ts(2), 'message': {'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': 'toolu_b', 'content': cmd % 'in-result:x'}]}}
        attachment = {'type': 'attachment', 'timestamp': ts(3), 'attachment': {'type': 'text', 'content': cmd % 'in-attachment:x'}}
        system = {'type': 'system', 'timestamp': ts(3), 'content': cmd % 'in-system:x'}
        self.t.session(SID, [
            user(0, 'go'),
            reply(1, 'm-bash', tools=[('toolu_b', 'Bash', {'command': 'echo "%s"' % (cmd % 'in-tool-use:x')})]),
            tool_result, attachment, system,
            typed(4, '/review-agents:dup', meta=True),  # the isMeta copy Claude Code writes after some commands
            typed(5, '/loop'),  # a bare slash command
            user(6, 'Please run <command-name>/mid:sentence</command-name> for me'),  # does not start with the tags
            skill_call(7, 'toolu_bad', 'bad id <img src=x>'),
            typed(8, '/bad:id with spaces'),
        ])
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses'], {})
        self.assertIn('bad id', self.t.err)

    def test_skill_calls_inside_agent_transcripts_are_not_counted(self):
        self.t.basic()
        self.t.agent(SID, 'askill', [skill_call(3, 'toolu_inner', 'backlog-delivery:pbi-plan')], {'agentType': 'Plan'})
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['skillUses'], {})

    def test_parser_version_was_bumped(self):
        # Results cached by parser 3 carry neither skillUses nor agentType, so they must be re-read once.
        self.assertGreater(es.PARSER_VERSION, 3)


def pconfig(*projects, **sessions):
    s = {'days': 7}
    s.update(sessions)
    return {'projects': list(projects), 'sessions': s, 'runs': {'runningWindowMinutes': 10, 'manual': []}}


def proj(pid, *sids, **over):
    p = {'id': pid, 'name': pid.title(), 'repoPath': 'C:/nowhere/' + pid, 'branch': 'main', 'sessions': list(sids)}
    p.update(over)
    return p


REPO = 'C:/work/repo'  # never created: linking reads paths, not the disk


def edit_call(m, tid, path, name='Edit'):
    return reply(m, 'm-' + tid, tools=[(tid, name, {'notebook_path' if name == 'NotebookEdit' else 'file_path': path})])


def tool_result(m, tid, is_error=False):
    return {'type': 'user', 'timestamp': ts(m), 'message': {'role': 'user', 'content': [
        {'type': 'tool_result', 'tool_use_id': tid, 'is_error': is_error, 'content': 'refused' if is_error else 'ok'}]}}


def edit_session(t, sid, *paths, name='Edit'):
    """A session whose main transcript successfully edited paths, and nothing else."""
    recs = [user(0, 'go')]
    for i, p in enumerate(paths):
        recs += [edit_call(1 + i, 'te%d' % i, p, name), tool_result(1 + i, 'te%d' % i)]
    return t.session(sid, recs)


def linked(t, sid):
    doc = t.docs('sessions')[sid]
    return doc['project'], doc.get('linkedBy')


class Projects(TreeCase):
    def test_sessions_and_runs_carry_their_project(self):
        self.t.basic()
        self.t.basic(SID2)
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        sessions, runs = self.t.docs('sessions'), self.t.docs('runs')
        self.assertEqual(sessions[SID]['project'], 'app')
        self.assertIsNone(sessions[SID2]['project'])
        self.assertEqual(runs['acw11']['project'], 'app')
        self.assertIsNone(runs['acw22']['project'])

    def edits(self, repo_path, *paths, sid=SID):
        """One session whose code-writer edited paths, exported with the project's repoPath as repo_path."""
        tools = [('toolu_e%d' % i, 'Edit', {'file_path': p}) for i, p in enumerate(paths)]
        self.t.session(sid, [user(0, 'go'), launch(1, 'toolu_cw'), notify(30, 'acw', result='DONE', tokens='5000', ms='60000')])
        self.t.agent(sid, 'acw', [user(1, 'task'), reply(2, 'm-a1', text='DONE', tools=tools)], CW_META)
        self.assertEqual(self.t.run(pconfig(proj('app', sid, repoPath=repo_path))), 0)
        return self.t.docs('runs')['acw']

    def test_a_run_document_names_the_files_the_run_edited_relative_to_the_repository(self):
        # AC-82's fourth element: the files a run touched, read from the write tools of its own transcript and
        # published relative to the project's repository, so no absolute local path is published for them.
        doc = self.edits(CWD, CWD + '\\site\\index.html', 'C:/work/app/exporters/derive.py')
        self.assertEqual(doc['files'], ['site/index.html', 'exporters/derive.py'])

    def test_a_run_document_names_a_file_edited_outside_the_repository_without_its_folder(self):
        doc = self.edits(CWD, CWD + '\\a.py', 'C:\\Users\\jdk\\.claude\\settings.json')
        self.assertEqual(doc['files'], ['a.py', '…/settings.json'])

    def test_a_run_document_that_edited_nothing_carries_no_files_key(self):
        self.t.basic()
        self.assertEqual(self.t.run(pconfig(proj('app', SID, repoPath=CWD))), 0)
        self.assertNotIn('files', self.t.docs('runs')['acw11'])

    def test_a_cache_from_before_edited_files_were_parsed_is_not_reused(self):
        # Edited paths are parsed from the transcript and cached with the row, so a cache signed by an earlier
        # parser holds rows with no "files" key and must not be replayed as a run that edited nothing.
        cfg = pconfig(proj('app', SID, repoPath=CWD))
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), notify(30, 'acw', result='DONE', tokens='5000', ms='60000')])
        self.t.agent(SID, 'acw', [user(1, 'task'), reply(2, 'm-a1', text='DONE',
                                                         tools=[('toolu_e0', 'Edit', {'file_path': CWD + '\\a.py'})])], CW_META)
        self.assertEqual(self.t.run(cfg), 0)
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        # Signed as parser 6 signed it: the last parser that did not read edited files. Signing it
        # PARSER_VERSION - 1 would pass whether or not the version was bumped for them.
        cache[SID]['sig'][0] = 6
        for row in cache[SID]['result']['rows']:
            row.pop('files', None)
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(self.t.docs('runs')['acw']['files'], ['a.py'])

    def test_build_flag_marks_only_the_meta_status_project(self):
        # Older copies of the page show "build" sessions with the single set of tabs, which are that project's.
        self.t.basic()
        self.t.basic(SID2)
        self.assertEqual(self.t.run(pconfig(proj('pc', SID, statusDoc='meta/status'), proj('app', SID2))), 0)
        sessions = self.t.docs('sessions')
        self.assertTrue(sessions[SID]['build'])
        self.assertFalse(sessions[SID2]['build'])
        self.assertEqual(sessions[SID2]['project'], 'app')

    def test_session_listed_twice_counts_once(self):
        self.t.basic()
        self.assertEqual(self.t.run(pconfig(proj('app', SID, SID))), 0)
        doc, session = self.t.docs('projects')['app'], self.t.docs('sessions')[SID]
        self.assertEqual((doc['sessions'], doc['runs']), ([SID], 1))
        self.assertEqual(doc['usage']['totals'], session['usage']['totals'])

    def test_session_keeps_its_folder_name(self):
        self.t.basic()
        self.t.run(pconfig())
        self.assertEqual(self.t.docs('sessions')[SID]['folder'], 'app')

    def test_project_document(self):
        self.t.basic()
        self.t.basic(SID2)
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('projects')['app']
        session = self.t.docs('sessions')[SID]
        self.assertEqual((doc['name'], doc['repoPath'], doc['branch'], doc['statusDoc'], doc['order']),
                         ('App', 'C:/nowhere/app', 'main', 'status/app', 0))
        self.assertEqual((doc['sessions'], doc['runs'], doc['running'], doc['last']), ([SID], 1, 0, session['last']))
        self.assertEqual(doc['usage']['totals'], session['usage']['totals'])

    def test_project_usage_combines_its_sessions(self):
        self.t.basic()
        self.t.basic(SID2)
        self.t.run(pconfig(proj('app', SID, SID2), proj('empty')))
        projects, sessions = self.t.docs('projects'), self.t.docs('sessions')
        u = projects['app']['usage']
        self.assertEqual(u['totals']['requests'], sessions[SID]['usage']['totals']['requests'] + sessions[SID2]['usage']['totals']['requests'])
        self.assertEqual(sorted(a['id'] for a in u['subagents']), ['acw11', 'acw22'])
        self.assertEqual((projects['app']['runs'], projects['app']['order']), (2, 0))
        self.assertEqual((projects['empty']['sessions'], projects['empty']['runs'], projects['empty']['usage'], projects['empty']['order']),
                         ([], 0, None, 1))

    def test_linked_session_without_a_transcript_fails(self):
        self.t.basic()
        self.assertNotEqual(self.t.run(pconfig(proj('app', '99999999-0000-0000-0000-000000000000'))), 0)
        self.assertIn('99999999', self.t.err)

    def test_a_linked_session_last_active_30_days_ago_is_still_exported_with_its_project(self):
        def aged(recs):
            for r in recs:
                t = datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) - timedelta(days=30)
                r['timestamp'] = t.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            return recs
        # SID is linked to the project; SID2, just as old, is linked to nothing and falls outside the window.
        for sid in (SID, SID2):
            self.t.session(sid, aged([user(0, 'go'), launch(1, 'toolu_cw'), notify(30, 'acw' + sid[:2], result='DONE')]))
            self.t.agent(sid, 'acw' + sid[:2], aged([reply(2, 'a', text='DONE')]), CW_META)
        old = time.time() - 30 * 86400
        for folder, _, files in os.walk(self.t.root):
            for f in files:
                os.utime(os.path.join(folder, f), (old, old))
        self.assertEqual(self.t.run(pconfig(proj('app', SID), days=7)), 0)
        sessions, runs = self.t.docs('sessions'), self.t.docs('runs')
        self.assertEqual(sorted(sessions), [SID])
        self.assertEqual(sessions[SID]['project'], 'app')
        self.assertEqual((sorted(runs), runs['acw11']['project']), (['acw11'], 'app'))
        self.assertEqual(self.t.docs('projects')['app']['sessions'], [SID])

    def test_projects_dropped_from_the_config_are_removed(self):
        self.t.basic()
        self.t.run(pconfig(proj('app', SID)))
        self.t.run(pconfig())
        self.assertEqual(self.t.docs('projects'), {})
        self.assertIsNone(self.t.docs('sessions')[SID]['project'])


SID3 = '33333333-aaaa-bbbb-cccc-000000000003'
SID4 = '44444444-aaaa-bbbb-cccc-000000000004'
SID5 = '55555555-aaaa-bbbb-cccc-000000000005'


class AutoLink(TreeCase):
    """A session no project lists is linked to the project whose files it successfully edited."""

    def cw_session(self, sid, main_edits=(), agent_edits=(), name='Edit', agent_failed=False):
        """A session that launched one code-writer; main_edits are made in the main transcript, agent_edits by the
        agent, whose edits all fail when agent_failed."""
        aid = 'acw' + sid[:2]
        recs = [user(0, 'go')]
        for i, p in enumerate(main_edits):
            recs += [edit_call(1, 'tm%d' % i, p, name), tool_result(1, 'tm%d' % i)]
        self.t.session(sid, recs + [launch(2, 'toolu_cw'), notify(30, aid, result='DONE', tokens='5', ms='60000')])
        arecs = [user(2, 'task')]
        for i, p in enumerate(agent_edits):
            arecs += [edit_call(3, 'ta%d' % i, p, name), tool_result(3, 'ta%d' % i, is_error=agent_failed)]
        self.t.agent(sid, aid, arecs + [reply(4, 'm-done', text='DONE')], CW_META)
        return aid

    def test_one_successful_edit_links_the_session_its_runs_and_the_project(self):
        for name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            with self.subTest(tool=name):
                self.t = Tree()
                self.addCleanup(self.t.cleanup)
                self.t.basic(SID2)
                aid = self.cw_session(SID, [REPO + '/a.py'], name=name)
                self.assertEqual(self.t.run(pconfig(proj('p', SID2, repoPath=REPO))), 0)
                self.assertEqual((linked(self.t, SID), linked(self.t, SID2)), (('p', 'edits'), ('p', 'config')))
                self.assertEqual(self.t.docs('runs')[aid]['project'], 'p')
                self.assertEqual(self.t.docs('projects')['p']['sessions'], [SID2, SID])
                self.assertEqual(self.t.docs('projects')['p']['runs'], 2)

    def test_an_edit_made_only_by_a_subagent_links_and_its_files_become_repo_relative(self):
        aid = self.cw_session(SID, agent_edits=['C:\\work\\repo\\src\\b.py'])
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath='C:/elsewhere'))), 0)
        self.assertEqual((linked(self.t, SID), self.t.docs('runs')[aid]['files']), ((None, None), ['…/b.py']))
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath=REPO))), 0)
        self.assertEqual((linked(self.t, SID), self.t.docs('runs')[aid]['files']), (('p', 'edits'), ['src/b.py']))

    def test_worktree_edits_link_by_the_default_or_the_configured_roots(self):
        edit_session(self.t, SID, REPO + '-worktrees/PBI-1/a.py')
        edit_session(self.t, SID2, 'C:\\other\\x\\a.py')
        edit_session(self.t, SID3, REPO + '-worktrees-old/x/f')
        edit_session(self.t, SID4, REPO + '-worktrees/f')
        edit_session(self.t, SID5, 'C:/wt/x/f')
        cases = (
            (proj('p', repoPath=REPO), ('p', None, None, 'p', None)),
            (proj('p', repoPath=REPO + '/'), ('p', None, None, 'p', None)),
            (proj('p', repoPath='C:\\work\\repo\\'), ('p', None, None, 'p', None)),
            (proj('p', repoPath=REPO, worktreeRoots=['C:/other']), (None, 'p', None, None, None)),
            (proj('p', repoPath=REPO, worktreeRoots=[]), (None, None, None, None, None)),
            (proj('p', repoPath='', worktreeRoots=['C:/wt']), (None, None, None, None, 'p')),
        )
        # No git and no process: the rule reads paths only, so a launch would fail the export.
        with mock.patch('subprocess.run', side_effect=AssertionError('no process may be launched')):
            for p, want in cases:
                with self.subTest(project=p):
                    self.assertEqual(self.t.run(pconfig(p)), 0, self.t.err)
                    self.assertEqual(tuple(self.t.docs('sessions')[s]['project'] for s in (SID, SID2, SID3, SID4, SID5)), want)

    def test_a_listed_session_keeps_its_project_whatever_it_edited(self):
        edit_session(self.t, SID, 'C:/b/1.py', 'C:/b/2.py')
        self.assertEqual(self.t.run(pconfig(proj('a', SID, repoPath='C:/a'), proj('b', repoPath='C:/b'))), 0)
        self.assertEqual(linked(self.t, SID), ('a', 'config'))
        projects = self.t.docs('projects')
        self.assertEqual((projects['a']['sessions'], projects['b']['sessions']), ([SID], []))

    def test_reads_searches_and_shell_commands_do_not_link(self):
        tools = [('r%d' % i, n, {'file_path': REPO + '/a.py', 'pattern': REPO, 'path': REPO,
                                 'command': 'echo x > %s/a.py && cat %s/b.py' % (REPO, REPO)})
                 for i, n in enumerate(('Read', 'Grep', 'Glob', 'Bash', 'PowerShell'))]
        read_result = {'type': 'user', 'timestamp': ts(3), 'message': {'role': 'user', 'content': [
            {'type': 'tool_result', 'tool_use_id': 'r0', 'content': 'Edit %s/a.py: "file_path": "%s/a.py"' % (REPO, REPO)}]}}
        self.t.session(SID, [user(0, 'go'), reply(1, 'm1', tools=tools), read_result, reply(4, 'm2', text='read it')])
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath=REPO))), 0)
        self.assertEqual(linked(self.t, SID), (None, None))
        self.assertEqual(self.t.docs('projects')['p']['sessions'], [])

    def test_a_failed_edit_is_not_evidence_in_the_main_or_a_subagent_transcript(self):
        self.t.session(SID, [user(0, 'go'), edit_call(1, 'tm', REPO + '/a.py'), tool_result(2, 'tm', is_error=True)])
        self.cw_session(SID2, agent_edits=[REPO + '/b.py'], agent_failed=True)
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath=REPO))), 0)
        self.assertEqual((linked(self.t, SID), linked(self.t, SID2)), ((None, None), (None, None)))

    def test_an_auto_linked_session_whose_transcript_has_gone_never_fails_the_run(self):
        self.t.basic(SID2)
        path = edit_session(self.t, SID, REPO + '/a.py')
        cfg = pconfig(proj('p', SID2, repoPath=REPO))
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(self.t.docs('projects')['p']['sessions'], [SID2, SID])
        os.remove(path)
        self.assertEqual(self.t.run(cfg), 0, self.t.err)
        self.assertNotIn(SID, self.t.docs('sessions'))
        self.assertEqual(self.t.docs('projects')['p']['sessions'], [SID2])

    def test_an_auto_linking_session_outside_the_window_is_not_exported(self):
        recs = [user(0, 'go'), edit_call(1, 'te', REPO + '/a.py'), tool_result(1, 'te')]
        for r in recs:
            r['timestamp'] = (BASE - timedelta(days=8)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        path = self.t.session(SID, recs)
        old = time.time() - 8 * 86400
        os.utime(path, (old, old))
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath=REPO), days=7)), 0)
        self.assertEqual((self.t.docs('sessions'), self.t.docs('projects')['p']['sessions']), ({}, []))

    def test_an_auto_linked_session_of_the_meta_status_project_is_not_a_build_session(self):
        edit_session(self.t, SID, REPO + '/a.py')
        self.assertEqual(self.t.run(pconfig(proj('pc', repoPath=REPO, statusDoc='meta/status'))), 0)
        self.assertEqual((linked(self.t, SID), self.t.docs('sessions')[SID]['build']), (('pc', 'edits'), False))

    def test_an_auto_linked_sessions_review_round_joins_the_projects_findings_ledger(self):
        self.t.session(SID, [user(0, 'go'), edit_call(1, 'te', REPO + '/a.py'), tool_result(1, 'te'),
                             launch(2, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1'))])
        self.t.agent(SID, 'acr1', [reply(3, 'a', text='reviewing')], review_meta('toolu_r1'))
        self.assertEqual(self.t.run(pconfig(proj('p', repoPath=REPO))), 0)
        item = self.t.docs('projectTabs')['p.findings']['items']['PBI-001']
        self.assertEqual([f['id'] for f in item['open']], ['F1'])

    def test_neither_the_cached_edits_nor_worktree_roots_are_published(self):
        self.t.basic(SID2)
        self.cw_session(SID, [REPO + '/a.py'], [REPO + '-worktrees/x/b.py'])
        self.assertEqual(self.t.run(pconfig(proj('p', SID2, repoPath=REPO, worktreeRoots=[REPO + '-worktrees']))), 0)
        self.assertEqual(linked(self.t, SID), ('p', 'edits'))
        for folder, _, files in os.walk(self.t.out):
            if os.path.basename(folder) == '.cache':
                continue
            for f in files:
                with io.open(os.path.join(folder, f), encoding='utf-8') as fh:
                    doc = json.load(fh)
                with self.subTest(file=f):
                    self.assertNotIn('worktreeRoots', json.dumps(doc))
                    self.assertNotIn('edits', doc)

    def test_only_a_session_that_edited_nothing_under_a_root_is_left_in_other_sessions(self):
        self.t.basic(SID2)
        edit_session(self.t, SID, REPO + '/a.py')
        edit_session(self.t, SID3, 'C:/elsewhere/a.py')
        self.assertEqual(self.t.run(pconfig(proj('p', SID2, repoPath=REPO))), 0)
        sessions = self.t.docs('sessions')
        self.assertEqual({sid for sid, d in sessions.items() if d['project'] is None}, {SID3})

    def test_a_kept_parse_without_cached_edits_links_on_its_subagent_files(self):
        # A session that fails to re-parse keeps its last cache entry; just after the parser version bump that
        # entry has no main-transcript edits, so the session links on its subagents' files alone.
        self.cw_session(SID, ['C:/b/1.py', 'C:/b/2.py'], ['C:/a/1.py'])
        cfg = pconfig(proj('a', repoPath='C:/a'), proj('b', repoPath='C:/b'))
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(linked(self.t, SID), ('b', 'edits'))
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        cache[SID]['sig'][0] = es.PARSER_VERSION - 1
        del cache[SID]['result']['doc']['edits']
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        with mock.patch.object(es, 'parse_session', side_effect=ValueError('unreadable')):
            self.assertEqual(self.t.run(cfg), 0)
        self.assertIn('keeping its last export', self.t.err)
        self.assertEqual(linked(self.t, SID), ('a', 'edits'))
        self.assertNotIn('edits', self.t.docs('sessions')[SID])


def finding(fid, loc='app.py:1'):
    return {'id': fid, 'severity': 'HIGH', 'title': 't-' + fid, 'subject': {'type': 'file', 'id': loc, 'name': 'x'}, 'remediation': 'fix-' + fid}


def review_result(verdict, *fids):
    """A code-reviewer's result: the headline verdict, then its structured findings, as its real output ends."""
    body = {'schema_version': '1', 'audit': {'agent': 'code-reviewer', 'verdict': verdict}, 'findings': [finding(f) for f in fids]}
    return '%s\n\nsome prose.\n\n```json\n%s\n```' % (verdict, json.dumps(body))


def review_meta(tool_id, pbi='PBI-001'):
    return {'agentType': 'review-agents:code-reviewer', 'description': 'Review ' + pbi, 'toolUseId': tool_id}


def review_result_no_block(verdict):
    """A code-reviewer's real, findings-file workflow: it writes findings to a file and replies in prose, so
    its result carries no fenced JSON at all."""
    return '%s. Findings written to docs/backlog/reviews/PBI-001/findings.json.' % verdict


class Findings(TreeCase):
    def review_meta(self, tool_id):
        return review_meta(tool_id)

    def test_ac77_two_rounds_open_and_resolved(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1', 'F2', 'F3')),
                             launch(11, 'toolu_r2'), notify(20, 'acr2', result=review_result('GO-WITH-CONDITIONS', 'F2'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.t.agent(SID, 'acr2', [reply(12, 'b', text='reviewing')], self.review_meta('toolu_r2'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        item = self.t.docs('projectTabs')['app.findings']['items']['PBI-001']
        self.assertEqual(sorted(f['id'] for f in item['open']), ['F2'])
        self.assertEqual(sorted(f['id'] for f in item['resolved']), ['F1', 'F3'])
        self.assertEqual(item['rounds'], 2)
        self.assertEqual(item['roundsToGo'], 2)

    def test_findings_document_has_no_generated_at_or_source_missing(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('GO'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('projectTabs')['app.findings']
        self.assertIn('generatedAt', doc)
        self.assertEqual(doc['items']['PBI-001'], {'open': [], 'resolved': [], 'rounds': 1, 'roundsToGo': 1})

    def test_no_findings_document_without_a_review_round(self):
        self.t.basic()
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        self.assertNotIn('app.findings', self.t.docs('projectTabs'))

    def test_a_review_run_document_carries_its_own_findings(self):
        # Run detail (FR-121) shows the findings of the run the owner picked, so each round publishes its own
        # list beside the per-work-item ledger. A run outside the review lane reports none, so it has no key.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('runs')['acr1']
        self.assertEqual(doc['findings'],
                         [{'id': 'F1', 'severity': 'HIGH', 'title': 't-F1', 'location': 'app.py:1', 'remediation': 'fix-F1'}])
        # The row's other review-only fields are derivation state, never published beside the findings.
        self.assertNotIn('hasFindingsBlock', doc)
        self.assertNotIn('pbis', doc)

    def test_a_review_round_with_no_readable_block_publishes_no_findings_key(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result_no_block('NO-GO'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        self.assertNotIn('findings', self.t.docs('runs')['acr1'])

    def test_a_cache_from_the_previous_parser_version_is_not_reused(self):
        # A cache written before PARSER_VERSION's bump has cr-lane rows with no "findings" key at all (a field
        # an earlier parser never wrote). Its signature must not match, so the session is re-parsed rather than
        # replaying a findings-free round that would publish F1 as resolved.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        cfg = pconfig(proj('app', SID))
        self.assertEqual(self.t.run(cfg), 0)
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        cache[SID]['sig'][0] = es.PARSER_VERSION - 1  # as parser 5 would have signed it
        for row in cache[SID]['result']['rows']:
            row.pop('findings', None)
            row.pop('hasFindingsBlock', None)
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        self.assertEqual(self.t.run(cfg), 0)
        item = self.t.docs('projectTabs')['app.findings']['items']['PBI-001']
        self.assertEqual([f['id'] for f in item['open']], ['F1'])
        self.assertEqual(item['resolved'], [])

    def test_a_nogo_round_with_no_findings_block_does_not_resolve_earlier_findings(self):
        # This repo's own code-reviewer is told to write findings to a file and reply in prose, so a real
        # NO-GO round routinely carries no JSON block at all.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1')),
                             launch(11, 'toolu_r2'), notify(20, 'acr2', result=review_result_no_block('NO-GO'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.t.agent(SID, 'acr2', [reply(12, 'b', text='reviewing')], self.review_meta('toolu_r2'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        item = self.t.docs('projectTabs')['app.findings']['items']['PBI-001']
        self.assertEqual([f['id'] for f in item['open']], ['F1'])
        self.assertEqual(item['resolved'], [])
        self.assertEqual(item['rounds'], 2)

    def test_findings_carry_their_first_and_last_seen_round(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1', 'F2')),
                             launch(11, 'toolu_r2'), notify(20, 'acr2', result=review_result('GO-WITH-CONDITIONS', 'F2'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], self.review_meta('toolu_r1'))
        self.t.agent(SID, 'acr2', [reply(12, 'b', text='reviewing')], self.review_meta('toolu_r2'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        item = self.t.docs('projectTabs')['app.findings']['items']['PBI-001']
        f1 = next(f for f in item['resolved'] if f['id'] == 'F1')
        f2 = next(f for f in item['open'] if f['id'] == 'F2')
        self.assertEqual((f1['round'], f1['lastSeen']), (1, 1))
        self.assertEqual((f2['round'], f2['lastSeen']), (1, 2))

    def test_a_review_naming_two_pbis_is_credited_to_both(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'),
                             notify(10, 'acr1', result=review_result('NO-GO', 'F1'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')],
                     {'agentType': 'review-agents:code-reviewer', 'description': 'Review PBI-001/004', 'toolUseId': 'toolu_r1'})
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        items = self.t.docs('projectTabs')['app.findings']['items']
        self.assertEqual(set(items), {'PBI-001', 'PBI-004'})
        for pbi in ('PBI-001', 'PBI-004'):
            self.assertEqual([f['id'] for f in items[pbi]['open']], ['F1'])
            self.assertEqual(items[pbi]['rounds'], 1)


def asks(m, tool_id, question):
    return reply(m, 'msg-ask-' + tool_id, tools=[(tool_id, 'AskUserQuestion', {'questions': [{'question': question}]})])


def refused(m, tool_id, kind='permission-rule'):
    return {'type': 'user', 'timestamp': ts(m), 'toolDenialKind': kind, 'toolUseResult': 'Error: denied',
            'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool_id, 'is_error': True,
                                                     'content': 'Permission to use Bash has been denied.'}]}}


class TrendAndCost(TreeCase):
    """A builder's stated test count and coverage on its run document, and the PBI ids each agent run's usage is
    attributed to, which the page totals per work item."""

    def test_ac79_a_code_writer_run_records_the_test_count_its_result_states(self):
        self.t.basic(result='DONE. 664 tests green, coverage 88.5%.')
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('runs')['acw11']
        self.assertEqual(doc['tests'], 664)
        self.assertEqual(doc['coverage'], 88.5)

    def test_a_builder_whose_result_states_no_figures_carries_neither_key(self):
        self.t.basic()
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('runs')['acw11']
        self.assertNotIn('tests', doc)
        self.assertNotIn('coverage', doc)

    def test_a_review_run_quoting_a_test_count_records_none(self):
        # Only a code-writer's or test-writer's count is its own; a reviewer quoting it would plot it twice.
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result='GO. 664 tests green, coverage 90%')])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], review_meta('toolu_r1'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('runs')['acr1']
        self.assertNotIn('tests', doc)
        self.assertNotIn('coverage', doc)

    def test_a_stated_count_in_the_agents_own_transcript_is_not_recorded(self):
        # tests/coverage are read from the run's notification result, not the agent's own transcript text
        # (which classify() uses only as a fallback for the verdict).
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_cw'), notify(30, 'acw11', result='DONE', tokens='5000', ms='1740000')])
        self.t.agent(SID, 'acw11', [user(1, 'task'), reply(2, 'm-a1', text='All green. 999 tests green, coverage 95%.')], CW_META)
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('runs')['acw11']
        self.assertNotIn('tests', doc)
        self.assertNotIn('coverage', doc)

    def test_a_manual_runs_label_is_never_scanned_for_stated_figures(self):
        # place_manual() builds the row directly and never calls agent_row(), so a manual row naming a
        # builder lane still can't gain tests/coverage from text in its own label.
        self.t.basic()
        cfg = config()
        cfg['runs']['manual'] = [{'id': 'orch-x', 'after': 'acw11', 'label': '700 tests green, coverage 90%', 'lane': 'cw'}]
        self.assertEqual(self.t.run(cfg), 0)
        doc = self.t.docs('runs')['orch-x']
        self.assertNotIn('tests', doc)
        self.assertNotIn('coverage', doc)

    def test_each_agent_run_in_usage_names_the_pbi_ids_of_its_label(self):
        self.t.basic()
        self.t.session(SID2, [user(0, 'go'), launch(1, 'toolu_cw'), notify(30, 'acw22', result='DONE')])
        self.t.agent(SID2, 'acw22', [reply(2, 'm', text='DONE')], dict(CW_META, description='PBI-003/004 pair under TDD'))
        self.assertEqual(self.t.run(pconfig(proj('app', SID, SID2))), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['usage']['subagents'][0]['pbis'], ['PBI-001'])
        agents = self.t.docs('projects')['app']['usage']['subagents']
        self.assertEqual(sorted(a['pbis'] for a in agents), [['PBI-001'], ['PBI-003', 'PBI-004']])

    def test_a_cache_from_before_figures_were_parsed_is_not_reused(self):
        cfg = pconfig(proj('app', SID))
        self.t.basic(result='DONE. 664 tests green')
        self.assertEqual(self.t.run(cfg), 0)
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        # Signed as parser 8 signed it: the last parser that read neither test counts nor usage PBI ids.
        cache[SID]['sig'][0] = 8
        for row in cache[SID]['result']['rows']:
            row.pop('tests', None)
        for a in cache[SID]['result']['doc']['usage']['subagents']:
            a.pop('pbis', None)
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(self.t.docs('runs')['acw11']['tests'], 664)
        self.assertEqual(self.t.docs('sessions')[SID]['usage']['subagents'][0]['pbis'], ['PBI-001'])


class Waiting(TreeCase):
    """The session document's optional "waiting" field: facts read from the main transcript, nothing that
    depends on the time of the export."""

    def blocked(self, sid=SID):
        self.t.session(sid, [user(0, 'go'), reply(1, 'msg-bash', tools=[('toolu_b', 'Bash', {'command': 'rm x'})]),
                             refused(2, 'toolu_b'), asks(3, 'toolu_q', 'Which port should it bind?')])

    def test_a_session_with_a_pending_question_and_a_refusal_carries_waiting(self):
        self.blocked()
        self.t.basic(SID2)
        self.assertEqual(self.t.run(), 0)
        sessions = self.t.docs('sessions')
        self.assertEqual(sessions[SID]['waiting'], {
            'questions': [{'at': ts(3), 'question': 'Which port should it bind?', 'source': 'ask'}],
            'refusals': [{'at': ts(2), 'kind': 'permission-rule', 'tool': 'Bash', 'detail': 'Permission to use Bash has been denied.'}]})
        self.assertNotIn('waiting', sessions[SID2])

    def test_a_question_asked_inside_an_agent_transcript_is_not_listed(self):
        self.t.basic()
        self.t.agent(SID, 'acw11', [user(1, 'task'), asks(2, 'toolu_inner', 'Should I use the cache?')], CW_META)
        self.assertEqual(self.t.run(), 0)
        self.assertNotIn('waiting', self.t.docs('sessions')[SID])

    def test_waiting_holds_nothing_that_depends_on_the_export_time(self):
        self.blocked()
        path = os.path.join(self.t.out, 'sessions', SID + '.json')
        texts = []
        for later in (0, 5 * 3600):
            shutil.rmtree(os.path.join(self.t.out, '.cache'), ignore_errors=True)  # parsed again, not replayed
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(es.main(config=config(), out_dir=self.t.out, projects_root=self.t.root, now=time.time() + later), 0)
            with io.open(path, encoding='utf-8') as f:
                texts.append(f.read())
        self.assertEqual(texts[0], texts[1])
        self.assertIn('"waiting"', texts[0])

    def test_parser_version_was_bumped_for_waiting(self):
        # 7 is the version before sessions carried "waiting"; pinning a literal keeps this from passing unbumped.
        self.assertGreater(es.PARSER_VERSION, 7)

    def test_a_cache_from_before_waiting_was_parsed_is_not_reused(self):
        self.blocked()
        self.assertEqual(self.t.run(), 0)
        cache_path = os.path.join(self.t.out, '.cache', 'sessions.json')
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        cache[SID]['sig'][0] = 7  # as the parser before "waiting" signed it
        del cache[SID]['result']['doc']['waiting']
        with io.open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
        self.assertEqual(self.t.run(), 0)
        self.assertIn('waiting', self.t.docs('sessions')[SID])

    def test_waiting_adds_no_collection_and_no_project_tab(self):
        import refresh
        self.blocked()
        self.assertEqual(self.t.run(), 0)
        self.assertEqual(os.listdir(os.path.join(self.t.out, 'projectTabs')), [])
        got = refresh.plan(self.t.out)
        writes = got['writes'] if got['batches'] == 1 else [w for b in got['writes'] for w in b]
        collections = {w['collection'] for w in writes}
        self.assertIn('sessions', collections)
        self.assertLessEqual(collections, {'sessions', 'runs', 'projects', 'meta'})


class Ownership(TreeCase):
    """The findings document's lifecycle (CR-011-4): export_sessions.py, not the folder's incidental wipe by
    export_board.py, owns writing and removing its own projectTabs/<pid>.findings.json."""

    def make_round(self):
        self.t.session(SID, [user(0, 'go'), launch(1, 'toolu_r1'), notify(10, 'acr1', result=review_result('NO-GO', 'F1'))])
        self.t.agent(SID, 'acr1', [reply(2, 'a', text='reviewing')], review_meta('toolu_r1'))

    def test_stale_findings_document_is_removed_once_the_project_has_no_round(self):
        self.make_round()
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        self.assertIn('app.findings', self.t.docs('projectTabs'))
        # The session is no longer linked to the project, so it carries no round for "app" any more.
        self.assertEqual(self.t.run(pconfig(proj('app'))), 0)
        self.assertNotIn('app.findings', self.t.docs('projectTabs'))

    def test_export_board_run_alone_does_not_delete_the_findings_document(self):
        import export_board as eb
        self.make_round()
        cfg = pconfig(proj('app', SID))
        self.assertEqual(self.t.run(cfg), 0)
        self.assertIn('app.findings', self.t.docs('projectTabs'))
        self.assertEqual(eb.main(config=cfg, out_dir=self.t.out, data_dir=self.t.tmp), 0)
        self.assertIn('app.findings', self.t.docs('projectTabs'))

    def test_running_the_exporters_in_refresh_order_leaves_exactly_one_findings_document(self):
        import export_board as eb
        self.make_round()
        cfg = pconfig(proj('app', SID))
        # refresh.py's order: export_board.py first, export_sessions.py second, sharing out/projectTabs.
        self.assertEqual(eb.main(config=cfg, out_dir=self.t.out, data_dir=self.t.tmp), 0)
        self.assertEqual(self.t.run(cfg), 0)
        found = [n for n in os.listdir(os.path.join(self.t.out, 'projectTabs')) if n.endswith('.findings.json')]
        self.assertEqual(found, ['app.findings.json'])


# The 2026-09-12 fixture is defined once, in test_derive.py, and read from there rather than copied.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_derive import STALE_2026_09_12, STALE_DONE  # noqa: E402

AGENT_TYPE = {'cw': 'engineering-agents:code-writer', 'tw': 'engineering-agents:test-writer',
              'cr': 'review-agents:code-reviewer', 'plan': 'Plan', 'other': 'general-purpose'}


def agents_session(t, sid, runs):
    """One session that launched each of runs, (agent id, lane, verdict, label), in turn; each finished by
    notification with its verdict."""
    recs = [user(0, 'go')]
    for i, (aid, lane, verdict, label) in enumerate(runs):
        m = 1 + 2 * i
        recs += [launch(m, 'toolu_' + aid), notify(m + 1, aid, result='Verdict: ' + verdict, tokens='100', ms='60000')]
        t.agent(sid, aid, [reply(m, 'm-' + aid, text='Verdict: ' + verdict)],
                {'agentType': AGENT_TYPE[lane], 'description': label, 'toolUseId': 'toolu_' + aid})
    t.session(sid, recs)


def read_bytes(path):
    with io.open(path, 'rb') as f:
        return f.read()


class WorkItems(TreeCase):
    """The work-item state derived from a project's linked sessions, written on its project document."""

    def review_session(self, sid=SID):
        agents_session(self.t, sid, [('acw1', 'cw', 'DONE', 'Build PBI-001'), ('acr1', 'cr', 'GO', 'Code-review PBI-001')])

    def files(self):
        return {os.path.relpath(os.path.join(folder, n), self.t.out): read_bytes(os.path.join(folder, n))
                for folder, _, names in os.walk(self.t.out) for n in names}

    def test_project_document_carries_work_items(self):
        self.review_session()
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        doc = self.t.docs('projects')['app']
        item = doc['workItems']['PBI-001']
        self.assertEqual((item['state'], item['rounds'], item['verdict'], item['latestRound'], item['builds'], item['runs']),
                         ('done', 1, 'GO', 'acr1', 1, ['acw1', 'acr1']))
        self.assertEqual((doc['unattributedRounds'], doc['workItemStatus']), (0, 'shadow'))

    def test_rounds_in_an_unlinked_session_reach_no_project(self):
        self.review_session()
        self.assertEqual(self.t.run(pconfig(proj('app'), proj('other'))), 0)
        self.assertEqual(self.t.docs('runs')['acr1']['kind'], 'go')
        for pid, doc in self.t.docs('projects').items():
            self.assertEqual((doc['workItems'], doc['unattributedRounds']), ({}, 0), pid)

    def test_work_items_are_identical_when_the_parse_is_reused_from_the_cache(self):
        self.review_session()
        cfg = pconfig(proj('app', SID))
        self.assertEqual(self.t.run(cfg), 0)
        path = os.path.join(self.t.out, 'projects', 'app.json')
        first = read_bytes(path)
        real, calls = es.parse_session, []

        def spy(*a, **kw):
            calls.append(a[1])
            return real(*a, **kw)
        with mock.patch.object(es, 'parse_session', spy):
            self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(calls, [], 'the second export reused every cached parse')
        self.assertEqual(read_bytes(path), first)
        self.assertEqual(json.loads(first)['workItems']['PBI-001']['state'], 'done')

    def test_the_2026_09_12_scenario_end_to_end(self):
        agents_session(self.t, SID, [(rid, lane, verdict, label) for rid, _, lane, _, verdict, label in STALE_2026_09_12])
        self.assertEqual(self.t.run(pconfig(proj('dispatch-board', SID))), 0)
        runs = self.t.docs('runs')
        for rid, _, lane, kind, verdict, _ in STALE_2026_09_12:
            self.assertEqual((runs[rid]['lane'], runs[rid]['kind'], runs[rid]['verdict']), (lane, kind, verdict), rid)
        doc = self.t.docs('projects')['dispatch-board']
        items = doc['workItems']
        for pbi, rounds in STALE_DONE.items():
            self.assertEqual((items[pbi]['state'], items[pbi]['rounds']), ('done', rounds), pbi)
        self.assertEqual((items['PBI-003']['state'], items['PBI-017']['state']), ('done', 'conditions'))
        self.assertEqual(set(items), set(STALE_DONE) | {'PBI-003', 'PBI-017'})
        self.assertEqual(doc['unattributedRounds'], 1)

    def test_export_sessions_writes_no_board_tab_and_export_board_writes_no_project_document(self):
        import export_board as eb
        import test_export_board as teb
        root = os.path.join(self.t.tmp, 'repo')
        for rel, text in teb.FULL.items():
            os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
            with io.open(os.path.join(root, rel), 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
        if teb.HAS_GIT:
            teb.git(root, 'init')
            teb.git(root, 'add', '-A')
            teb.git(root, 'commit', '-m', 'first')
        data = os.path.join(self.t.tmp, 'data')
        os.makedirs(data)
        with io.open(os.path.join(data, 'app.json'), 'w', encoding='utf-8') as f:
            json.dump(teb.DATA, f)
        self.review_session()
        cfg = pconfig(proj('app', SID, repoPath=root, docs=dict(teb.DOCS)))
        alone = os.path.join(self.t.tmp, 'alone')
        # refresh.py's order in self.t.out: export_board.py first, export_sessions.py second.
        with contextlib.redirect_stdout(io.StringIO()):
            for out in (alone, self.t.out):
                self.assertEqual(eb.main(config=cfg, out_dir=out, data_dir=data, now=teb.NOW, run=teb.refuse_gh), 0)
        self.assertFalse(os.path.exists(os.path.join(alone, 'projects')), 'export_board.py writes no project document')
        self.assertEqual(self.t.run(cfg), 0)
        tabs = lambda out: {n: read_bytes(os.path.join(out, 'projectTabs', n)) for n in os.listdir(os.path.join(out, 'projectTabs'))}
        mine, theirs = tabs(self.t.out), tabs(alone)
        expected = {'app.%s.json' % t for t in ('spec', 'assumptions', 'decisions', 'backlog')} | ({'app.git.json'} if teb.HAS_GIT else set())
        self.assertEqual(set(theirs), expected)
        self.assertEqual(set(mine), expected | {'app.findings.json'})
        for name in expected:
            self.assertEqual(mine[name], theirs[name], name)
        self.assertIn('workItems', self.t.docs('projects')['app'])

    def test_an_unusable_work_item_status_exits_2_and_exports_nothing(self):
        self.review_session()
        self.assertEqual(self.t.run(pconfig(proj('app', SID))), 0)
        before = self.files()
        self.assertEqual(self.t.run(pconfig(proj('app', SID, workItemStatus='retired'))), 2)
        self.assertIn('workItemStatus', self.t.err)
        self.assertEqual(self.files(), before)


class LegacyProjects(TreeCase):
    def test_build_block_is_one_project(self):
        self.t.basic()
        cfg = config(build=[SID])
        cfg['build']['repoPath'] = 'C:/x/legacy-app'
        self.assertEqual(self.t.run(cfg), 0)
        self.assertEqual(self.t.docs('sessions')[SID]['project'], 'legacy-app')
        self.assertEqual(self.t.docs('projects')['legacy-app']['statusDoc'], 'meta/status')

    def test_usage_sessions_are_linked_too(self):
        self.t.basic()
        cfg = config()
        cfg['build']['repoPath'] = 'C:/x/legacy-app'
        cfg['usage'] = {'sessions': [{'label': 'x', 'sessionId': SID}]}
        self.t.run(cfg)
        self.assertEqual(self.t.docs('runs')['acw11']['project'], 'legacy-app')

    def test_no_build_block_means_no_projects(self):
        self.t.basic()
        self.t.run(config())
        self.assertEqual(self.t.docs('projects'), {})
        self.assertIsNone(self.t.docs('sessions')[SID]['project'])


def usage_block(first, last, hourly, models, subs, limits, overage=''):
    tot = lambda k: sum(m[k] for m in models)
    return {'source': 'x', 'weights': {'input': 1, 'cacheRead': 0.1, 'cacheWrite': 2, 'output': 5},
            'span': {'first': first, 'last': last},
            'totals': {k: tot(k) for k in ('input', 'cacheRead', 'cacheWrite', 'output', 'effective', 'requests')},
            'byModel': models, 'groups': [{'key': 'think', 'label': es.GROUP_LABEL['think'], 'effective': tot('effective')}],
            'subagents': [{'id': s, 'effective': 1} for s in subs], 'hourly': hourly, 'limits': limits, 'overage': overage}


def model(name, requests, effective):
    return {'model': name, 'label': es.MODEL_LABEL.get(name, name), 'requests': requests, 'input': 1, 'cacheRead': 2,
            'cacheWrite': 3, 'output': 4, 'effective': effective}


class AggregateUsage(unittest.TestCase):
    def test_nothing_to_aggregate(self):
        self.assertIsNone(es.aggregate_usage([]))
        self.assertIsNone(es.aggregate_usage([None]))

    def test_sums_merges_and_concatenates(self):
        a = usage_block('2026-09-10T10:05:00Z', '2026-09-10T11:40:00Z',
                        [{'hour': '2026-09-10T10', 'main': 5, 'sub': 1}, {'hour': '2026-09-10T11', 'main': 2, 'sub': 0}],
                        [model('claude-opus-5', 4, 100)], ['a1'], [{'firstAt': '2026-09-10T11:30:00Z', 'refused': 2}])
        b = usage_block('2026-09-10T11:10:00Z', '2026-09-10T13:20:00Z',
                        [{'hour': '2026-09-10T11', 'main': 1, 'sub': 4}, {'hour': '2026-09-10T13', 'main': 3, 'sub': 0}],
                        [model('claude-haiku-4-5-20251001', 1, 80), model('claude-opus-5', 2, 50)], ['b1'],
                        [{'firstAt': '2026-09-10T09:00:00Z', 'refused': 1}], overage='paused')
        u = es.aggregate_usage([a, b])
        self.assertEqual(u['totals'], {'input': 3, 'cacheRead': 6, 'cacheWrite': 9, 'output': 12, 'effective': 230, 'requests': 7})
        self.assertEqual([(m['model'], m['label'], m['requests'], m['effective'], m['input']) for m in u['byModel']],
                         [('claude-opus-5', 'Opus 5', 6, 150, 2), ('claude-haiku-4-5-20251001', 'Haiku 4.5', 1, 80, 1)])
        self.assertEqual(u['groups'], [{'key': 'think', 'label': es.GROUP_LABEL['think'], 'effective': 230}])
        self.assertEqual(u['hourly'], [{'hour': '2026-09-10T10', 'main': 5, 'sub': 1}, {'hour': '2026-09-10T11', 'main': 3, 'sub': 4},
                                       {'hour': '2026-09-10T12', 'main': 0, 'sub': 0}, {'hour': '2026-09-10T13', 'main': 3, 'sub': 0}])
        self.assertEqual([a['id'] for a in u['subagents']], ['a1', 'b1'])
        self.assertEqual([l['firstAt'] for l in u['limits']], ['2026-09-10T09:00:00Z', '2026-09-10T11:30:00Z'])
        self.assertEqual(u['span'], {'first': '2026-09-10T10:05:00Z', 'last': '2026-09-10T13:20:00Z'})
        self.assertEqual((u['overage'], u['weights']), ('paused', a['weights']))
        self.assertIn('2 sessions', u['source'])

    def test_limits_sharing_a_reset_are_one_limit(self):
        # Usage limits are account-wide: two sessions refused before the same reset hit one limit.
        reset = '2026-09-10T15:00:00+00:00'
        a = usage_block('2026-09-10T10:00:00Z', '2026-09-10T12:00:00Z', [], [model('m', 1, 1)], [], [
            {'firstAt': '2026-09-10T11:30:00Z', 'refused': 2, 'type': 'five_hour', 'resetsAt': reset},
            {'firstAt': '2026-09-10T08:00:00Z', 'refused': 1, 'type': 'five_hour', 'resetsAt': None}])
        b = usage_block('2026-09-10T10:00:00Z', '2026-09-10T12:00:00Z', [], [model('m', 1, 1)], [], [
            {'firstAt': '2026-09-10T11:10:00Z', 'refused': 3, 'type': 'five_hour', 'resetsAt': reset},
            {'firstAt': '2026-09-10T09:00:00Z', 'refused': 4, 'type': 'five_hour', 'resetsAt': None}])
        u = es.aggregate_usage([a, b])
        self.assertEqual([(l['firstAt'], l['refused'], l['resetsAt']) for l in u['limits']], [
            ('2026-09-10T08:00:00Z', 1, None), ('2026-09-10T09:00:00Z', 4, None), ('2026-09-10T11:10:00Z', 5, reset)])

    def test_hourly_series_is_capped_to_the_last_week(self):
        a = usage_block('2026-08-01T10:00:00Z', '2026-08-01T10:00:00Z', [{'hour': '2026-08-01T10', 'main': 1, 'sub': 0}], [model('m', 1, 1)], [], [])
        b = usage_block('2026-09-10T10:00:00Z', '2026-09-10T10:00:00Z', [{'hour': '2026-09-10T10', 'main': 2, 'sub': 0}], [model('m', 1, 1)], [], [])
        u = es.aggregate_usage([a, b])
        self.assertEqual(len(u['hourly']), es.HOURS)
        self.assertEqual(u['hourly'][-1], {'hour': '2026-09-10T10', 'main': 2, 'sub': 0})
        self.assertEqual(u['totals']['requests'], 2)


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
