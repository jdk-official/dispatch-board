"""The collector's session, run and project records equal the session exporter's documents for the same synthetic
transcripts, config and now: in one pass, when the transcripts are written a few lines at a time with a pass after
each step, after a restart halfway, and with sessions.exclude in use.

The transcripts are test_conformance.Fixture's and scenarios built from tests/test_export_sessions.py's record
builders (imported as a module, so none of its tests are collected here).
"""
import contextlib, io, json, os, shutil, time, unittest

import collector_support as cs
from collector_support import Env, tes
import collector  # noqa: E402
import test_conformance as tc  # noqa: E402

S = ['%d%d%d%d%d%d%d%d-aaaa-bbbb-cccc-00000000000%d' % ((i,) * 8 + (i,)) for i in range(1, 8)]
SECRET = 'C:\\work\\secret'


def scenarios(t):
    """Sessions covering the exporter's cases, written into a tes.Tree."""
    t.basic(sid=S[0])  # a finish by notification
    t.session(S[1], [tes.user(0, 'review it'), tes.launch(1, 'toolu_in'),
                     tes.inline(20, 'toolu_in', 'Verdict: **GO**', tokens=900, ms=120000)])
    t.agent(S[1], 'ain', [tes.user(1, 'task'), tes.reply(3, 'm-in', text='Verdict: GO')],
            {'agentType': 'review-agents:code-reviewer', 'description': 'Review PBI-001', 'toolUseId': 'toolu_in'})
    t.session(S[2], [tes.user(0, 'build'), tes.launch(1, 'toolu_rl')])  # a rate-limit kill
    t.agent(S[2], 'arl', [tes.user(1, 'task'), tes.reply(2, 'm-rl', text="You've hit your session limit · resets 4pm")],
            {'agentType': 'engineering-agents:test-writer', 'description': 'PBI-001 tests', 'toolUseId': 'toolu_rl'})
    t.session(S[3], [tes.user(0, 'go'), tes.launch(1, 'toolu_st'), tes.stop(5, 'ast'),  # a stop, then a completed finish
                     tes.notify(30, 'ast', result='All green. DONE', tokens='700', ms='600000')])
    t.agent(S[3], 'ast', [tes.user(1, 'task'), tes.reply(2, 'm-st', text='All green. DONE')],
            {'agentType': 'engineering-agents:code-writer', 'description': 'PBI-002 fix review notes', 'toolUseId': 'toolu_st'})
    bad = tes.reply(9, 'm-bad')
    bad['message']['usage']['output_tokens'] = 'lots'
    t.session(S[4], [tes.user(0, 'skills'), tes.skill_call(1, 'toolu_k1', 'eng:tdd'), tes.typed(2, '/eng:plan'),
                     tes.typed(3, '/eng:plan', meta=True), tes.skill_call(4, 'toolu_k2', 'bare'),
                     'not json at all', '[1, 2]', '[' * 50000 + ']' * 50000, bad, tes.reply(10, 'm-ok', text='done')])
    t.session(S[5], [{'type': 'ai-title', 'aiTitle': 'A generated title'}] + [tes.user(0, 'hello'), tes.reply(1, 'm-q', text='hi')],
              folder='C--other')
    t.session(S[6], [tes.user(0, 'secret work', SECRET), tes.reply(1, 'm-s', text='ok')], folder='C--work-secret')


def transcript_files(root):
    """Every transcript and meta file under root, as {path: bytes}."""
    found = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            with open(os.path.join(dirpath, n), 'rb') as f:
                found[os.path.join(dirpath, n)] = f.read()
    return found


class Equivalence(unittest.TestCase):
    def setUp(self):
        self.e = Env(self)
        self.now = time.time()

    def configs(self):
        """(name, config, projects root) for each fixture, the transcripts already written."""
        f = tc.Fixture()
        self.addCleanup(f.cleanup)
        f.transcripts()
        fcfg = f.config()
        fcfg['catalogue'] = self.e.cfg()['catalogue']
        scenarios(self.e.t)
        return [('conformance fixture', fcfg, f.root),
                ('tree scenarios', self.e.cfg(build=[S[0], S[3]]), self.e.root),
                ('tree scenarios, excluded by cwd', self.e.cfg(build=[S[0]], exclude=[SECRET + '*']), self.e.root)]

    def run_pass(self, cfg, root, conn=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            collector.run_pass(conn or self.e.conn, cfg, projects_root=root, now=self.now)
        return err.getvalue()

    def fresh_db(self, name):
        path = os.path.join(self.e.tmp, 'db-%s.db' % name.replace(' ', '-').replace(',', ''))
        collector.forget()
        import db
        with contextlib.redirect_stderr(io.StringIO()):
            conn = db.open_db(path)
        self.e.conns.append(conn)
        return conn

    def test_one_pass_equals_the_exporter(self):
        for name, cfg, root in self.configs():
            with self.subTest(name):
                conn = self.fresh_db(name)
                self.run_pass(cfg, root, conn)
                want = self.e.exported(cfg, self.now, root)
                self.assertTrue(want['session'] and want['run'])
                self.assertEqual(self.e.stored(conn), want)

    def test_the_exclusion_fixture_leaves_the_secret_session_out(self):
        name, cfg, root = self.configs()[2]
        conn = self.fresh_db(name)
        self.run_pass(cfg, root, conn)
        self.assertNotIn(S[6], self.e.stored(conn)['session'])
        self.assertEqual(len(conn.execute('SELECT * FROM collector_excluded').fetchall()), 1)

    def test_writing_a_few_lines_at_a_time_ends_equal_to_the_exporter(self):
        for name, cfg, root in self.configs():
            with self.subTest(name):
                final = transcript_files(root)
                grown = os.path.join(self.e.tmp, 'grown-%d' % len(name))
                shutil.rmtree(grown, ignore_errors=True)
                lines = {os.path.relpath(p, root): raw.splitlines(keepends=True) for p, raw in final.items()}
                steps = max(len(v) for k, v in lines.items() if k.endswith('.jsonl'))
                conn = self.fresh_db(name + '-inc')
                for rel, ls in lines.items():  # meta files are written whole at the start
                    if rel.endswith('.meta.json'):
                        os.makedirs(os.path.dirname(os.path.join(grown, rel)), exist_ok=True)
                        with open(os.path.join(grown, rel), 'wb') as fh:
                            fh.write(b''.join(ls))
                k = 0
                while k < steps:
                    k = min(steps, k + (1 if k < 12 else 3))  # every line boundary early on, then a few at a time
                    for rel, ls in lines.items():
                        if rel.endswith('.jsonl') and ls[:k]:
                            p = os.path.join(grown, rel)
                            os.makedirs(os.path.dirname(p), exist_ok=True)
                            with open(p, 'wb') as fh:
                                fh.write(b''.join(ls[:k]))
                    os.makedirs(grown, exist_ok=True)
                    self.run_pass(cfg, grown, conn)
                want = self.e.exported(cfg, self.now, grown)
                self.assertEqual(self.e.stored(conn), want)


class Restart(unittest.TestCase):
    """The incremental case with a new connection and no cache halfway through, on one database file."""

    def test_incremental_with_a_restart_halfway(self):
        e = Env(self)
        now = time.time()
        scenarios(e.t)
        cfg = e.cfg(build=[S[0]], exclude=[SECRET + '*'])
        final = transcript_files(e.root)
        grown = os.path.join(e.tmp, 'grown')
        lines = {os.path.relpath(p, e.root): raw.splitlines(keepends=True) for p, raw in final.items()}
        steps = max(len(v) for k, v in lines.items() if k.endswith('.jsonl'))
        for rel, ls in lines.items():
            if rel.endswith('.meta.json'):
                os.makedirs(os.path.dirname(os.path.join(grown, rel)), exist_ok=True)
                with open(os.path.join(grown, rel), 'wb') as fh:
                    fh.write(b''.join(ls))
        for k in range(1, steps + 1):
            for rel, ls in lines.items():
                if rel.endswith('.jsonl') and ls[:k]:
                    p = os.path.join(grown, rel)
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, 'wb') as fh:
                        fh.write(b''.join(ls[:k]))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                collector.run_pass(e.conn, cfg, projects_root=grown, now=now)
            if k == steps // 2:
                e.reconnect()
        self.assertEqual(e.stored(), e.exported(cfg, now, grown))


if __name__ == '__main__':
    unittest.main()
