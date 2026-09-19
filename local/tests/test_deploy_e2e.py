"""The on-PC deployment, end to end, as two real operating-system processes started exactly the way the Task
Scheduler actions start them: `python local/deploy/run_local.py --target collector` and `--target server`.

Nothing here is a stub. A throwaway projects root holds a synthetic Claude Code transcript; the collector writes
it into a throwaway SQLite database; the server opens that database read-only and serves the real
site/index.html, the snapshot and the event stream; and the finish of a running agent is appended to the
transcript while a stream is open, so the deployed pair is measured on the path NFR-18 describes.

Which criteria this file carries, and which it does not:

- **AC-65** its data leg: within the budget of a log-on start, and with no Claude Code session open, the page's
  data holds the sessions active in the last 7 days. The log-on trigger itself is Task Scheduler's, tested in
  test_deploy_tasks.py; that a *browser* is showing it is the owner's demonstration.
- **AC-66**: the listening socket of the deployed server is 127.0.0.1 only, read back out of `netstat -ano`.
- **AC-68** its server-and-deployment leg: a finish appended to a running agent's transcript reaches an
  already-open event stream as the run's new kind, with no second request of any kind. The **in-browser** leg —
  a page open in a browser, updating with no reload — is a demonstration and is not performed here.
- **NFR-17 / AC-70**: test_deploy_inspection.py.

Every case but one passes the targets a throwaway config, database and log folder, plus port 0. DeployedDefaults
is that one: it runs the command line the tasks really carry, `run_local.py --target <t>` and nothing else,
from a copy of the checkout, so the config, the database path, the page and the log folder are found the way a
log-on start finds them. The copy is what keeps it off the real out/ and the real port: its board.config.json
names a synthetic projects root and a free port. What it cannot show is port 8765 itself being free on the
owner's PC.

The budget is 10 minutes. The bounds asserted below are far tighter, because a deployment that needed minutes
here would be broken rather than merely slow, and a test that waited 10 minutes would never be run.
"""
import io, json, os, re, shutil, socket, subprocess, sys, tempfile, time, unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(REPO, 'tests'), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import server_support as ss  # noqa: E402
import test_export_sessions as tes  # noqa: E402

RUNNER = os.path.join(REPO, 'local', 'deploy', 'run_local.py')
SID = tes.SID
AID = 'acw01'
BUDGET = 600  # seconds; NFR-18 and NFR-21
START_BOUND = 120  # a deployment that took longer than this to serve its first record would be broken
PUSH_BOUND = 60  # the collector's interval here is 1s and the server's poll 1s, so a push is seconds
SERVING = re.compile(r'server: serving http://127\.0\.0\.1:(\d+) ')


def wait_for(predicate, timeout, what):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError('timed out after %ss waiting for %s' % (timeout, what))


class Deployment(unittest.TestCase):
    """The collector and the server, each launched through run_local.py, against a throwaway tree."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='deploy-e2e-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.logs = os.path.join(self.tmp, 'logs')
        self.db_path = os.path.join(self.tmp, 'db', 'board.db')
        self.tree = tes.Tree()
        self.addCleanup(self.tree.cleanup)
        self.procs = []
        self.addCleanup(self.stop_all)

    # -------------------------------------------------------------- the fixture

    def transcripts(self):
        """One session that launched a code-writer which has not reported yet: the run is `running`."""
        self.main_path = self.tree.session(SID, [tes.user(0, 'Please build the widget'), tes.launch(1, 'toolu_cw')])
        self.tree.agent(SID, AID, [tes.user(1, 'task'), tes.reply(2, 'm-a1', text='Working on it')], tes.CW_META)

    def append_finish(self):
        """The moment NFR-18 measures: a finish appended to the running agent's transcript."""
        line = json.dumps(tes.notify(30, AID, result='All green. DONE', tokens='5000', ms='1740000'))
        with io.open(self.main_path, 'a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')

    def config(self):
        cfg = tes.config(projectsRoot=self.tree.root)
        cfg['catalogue'] = {'marketplacePath': os.path.join(self.tmp, 'no-marketplace'),
                            'installedPath': os.path.join(self.tmp, 'no-installed.json')}
        cfg['local'] = {'databasePath': self.db_path, 'port': 8765}  # the port is overridden with --port 0
        path = os.path.join(self.tmp, 'board.config.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        return path

    # -------------------------------------------------------------- the two processes

    def launch(self, target, extra):
        """Exactly the command line the Task Scheduler action carries, plus the arguments this test needs."""
        console = open(os.path.join(self.tmp, target + '.console.txt'), 'wb')
        self.addCleanup(console.close)
        p = subprocess.Popen([sys.executable, RUNNER, '--target', target, '--log-dir', self.logs, '--'] + extra,
                             cwd=self.tmp, stdout=console, stderr=subprocess.STDOUT)
        self.procs.append(p)
        return p

    def stop_all(self):
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()

    def log(self, target):
        path = os.path.join(self.logs, target + '.log')
        if not os.path.exists(path):
            return ''
        with io.open(path, encoding='utf-8', errors='replace') as f:
            return f.read()

    def console(self, target):
        with io.open(os.path.join(self.tmp, target + '.console.txt'), encoding='utf-8', errors='replace') as f:
            return f.read()

    def start_collector(self, cfg):
        self.collector = self.launch('collector', ['--config', cfg, '--interval', '1'])
        wait_for(lambda: 'sessions' in self.log('collector'), START_BOUND,
                 'the collector to commit a pass (console: %r)' % self.console('collector'))

    def start_server(self, cfg):
        self.server = self.launch('server', ['--config', cfg, '--port', '0', '--poll', '1'])
        match = wait_for(lambda: SERVING.search(self.log('server')), START_BOUND,
                         'the server to bind (console: %r)' % self.console('server'))
        self.port = int(match.group(1))
        self.client = ss.Client(self.port)
        return self.port

    def snapshot(self):
        resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 200, body)
        return json.loads(body.decode('utf-8'))

    def maybe_snapshot(self):
        """The snapshot, or None while the server is answering 503 because the database is not ready."""
        resp, body = self.client.get('/api/snapshot')
        return json.loads(body.decode('utf-8')) if resp.status == 200 else None

    def await_record(self, path, timeout=START_BOUND):
        def ready():
            snap = self.maybe_snapshot()
            return snap if snap and path in snap['records'] else None
        return wait_for(ready, timeout, '%s in the snapshot' % path)

    def deploy(self):
        cfg = self.config()
        started = time.time()
        self.start_collector(cfg)
        self.start_server(cfg)
        return started


# ---------------------------------------------------------------- AC-65: what a log-on start puts on the page

class LogOnStart(Deployment):
    def test_the_page_and_its_data_are_there_within_the_budget(self):
        self.transcripts()
        started = self.deploy()

        snap = self.await_record('sessions/' + SID)
        elapsed = time.time() - started
        self.assertLess(elapsed, BUDGET, 'NFR-21 allows 10 minutes')
        self.assertLess(elapsed, START_BOUND)

        entry = snap['records']['sessions/' + SID]
        self.assertEqual(entry['kind'], 'session')
        self.assertEqual(entry['doc']['windowDays'], 7)  # "sessions active in the last 7 days"
        self.assertEqual(snap['skipped'], 0)
        self.assertTrue([k for k in snap['records'] if k.startswith('runs/')], 'the session has runs')

        resp, body = self.client.get('/')
        self.assertEqual(resp.status, 200)
        self.assertTrue(body.startswith(b'<!doctype html>'))
        # The marker the page's data adapter reads to know it is being served locally, carrying both its URLs.
        marker = re.search(rb'window\.__DISPATCH_LOCAL__=(\{.*?\});', body)
        self.assertIsNotNone(marker, 'the served page carries the local-adapter marker')
        self.assertEqual(json.loads(marker.group(1).decode('utf-8'))['snapshot'], '/api/snapshot')
        self.assertEqual(json.loads(marker.group(1).decode('utf-8'))['events'], '/api/events')

    def test_both_processes_are_still_running_and_their_logs_hold_the_evidence(self):
        self.transcripts()
        self.deploy()
        self.assertIsNone(self.collector.poll(), 'the collector is still running')
        self.assertIsNone(self.server.poll(), 'the server is still running')
        self.assertIn('run_local: starting collector', self.log('collector'))
        self.assertIn('run_local: starting server', self.log('server'))
        self.assertIn('collector: ', self.log('collector'))
        self.assertIn('server: serving', self.log('server'))
        # Task Scheduler discards a process's own output, so the console it was given stays empty.
        self.assertEqual(self.console('collector').strip(), '')
        self.assertEqual(self.console('server').strip(), '')


class DeployedDefaults(Deployment):
    """The tasks' own command line, with no argument for the target, in a copy of the checkout."""

    def checkout(self):
        tree = os.path.join(self.tmp, 'checkout')
        skip = shutil.ignore_patterns('__pycache__', 'tests')
        shutil.copytree(os.path.join(REPO, 'local'), os.path.join(tree, 'local'), ignore=skip)
        shutil.copytree(os.path.join(REPO, 'exporters'), os.path.join(tree, 'exporters'), ignore=skip)
        os.makedirs(os.path.join(tree, 'site'))
        shutil.copy2(os.path.join(REPO, 'site', 'index.html'), os.path.join(tree, 'site', 'index.html'))
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
        probe.close()
        cfg = tes.config(projectsRoot=self.tree.root)
        cfg['catalogue'] = {'marketplacePath': os.path.join(self.tmp, 'no-marketplace'),
                            'installedPath': os.path.join(self.tmp, 'no-installed.json')}
        cfg['local'] = {'databasePath': 'out/local/board.db', 'port': port}  # relative, as the repository's is
        with io.open(os.path.join(tree, 'board.config.json'), 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        return tree, port

    def test_the_scheduled_command_line_finds_the_checkouts_config_database_page_and_log_folder(self):
        self.transcripts()
        tree, port = self.checkout()
        runner = os.path.join(tree, 'local', 'deploy', 'run_local.py')
        logs = os.path.join(tree, 'out', 'local', 'logs')
        for target in ('collector', 'server'):
            console = open(os.path.join(self.tmp, target + '.console.txt'), 'wb')
            self.addCleanup(console.close)
            # Started from outside the checkout, as Task Scheduler may start it in System32.
            self.procs.append(subprocess.Popen([sys.executable, runner, '--target', target], cwd=self.tmp,
                                               stdout=console, stderr=subprocess.STDOUT))

        def log(target):
            path = os.path.join(logs, target + '.log')
            if not os.path.exists(path):
                return ''
            with io.open(path, encoding='utf-8', errors='replace') as f:
                return f.read()
        wait_for(lambda: 'server: serving http://127.0.0.1:%d ' % port in log('server'), START_BOUND,
                 'the server to bind the port its config names (console: %r)' % self.console('server'))
        self.client = ss.Client(port)
        snap = self.await_record('sessions/' + SID)
        self.assertEqual(snap['records']['sessions/' + SID]['doc']['windowDays'], 7)
        resp, body = self.client.get('/')
        self.assertEqual(resp.status, 200)
        self.assertTrue(body.startswith(b'<!doctype html>'))
        self.assertTrue(os.path.isfile(os.path.join(tree, 'out', 'local', 'board.db')))
        self.assertIn('run_local: starting collector', log('collector'))
        self.assertIn('collector: ', log('collector'))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'out')), 'nothing was resolved against the working folder')
        self.assertEqual(self.console('collector').strip(), '')
        self.assertEqual(self.console('server').strip(), '')


# ---------------------------------------------------------------- the two processes side by side

class StartOrder(Deployment):
    """The collector owns the database and the server only reads it, so the pair must survive either order."""

    def test_a_server_started_first_waits_for_the_collector_and_is_not_restarted(self):
        self.transcripts()
        cfg = self.config()
        self.start_server(cfg)
        resp, _ = self.client.get('/')
        self.assertEqual(resp.status, 200, 'the page is served before there is any data')
        resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 503)
        self.assertEqual(resp.getheader('Retry-After'), '5')
        self.assertIn(b'not ready', body)
        self.assertFalse(os.path.exists(self.db_path), 'the server created no database of its own')

        pid = self.server.pid
        self.start_collector(cfg)
        self.await_record('sessions/' + SID)
        self.assertEqual(self.server.pid, pid, 'the same server process now serves the data')
        self.assertIsNone(self.server.poll())


class SideBySide(Deployment):
    def test_the_reader_and_the_writer_do_not_fight(self):
        self.transcripts()
        self.deploy()
        self.await_record('sessions/' + SID)
        stamps, deadline = set(), time.time() + 6
        while time.time() < deadline:
            snap = self.maybe_snapshot()
            self.assertIsNotNone(snap, 'the server refused a read while the collector was writing')
            self.assertEqual(snap['skipped'], 0)
            self.assertIn('sessions/' + SID, snap['records'])
            stamps.add(snap['records']['meta/lastRefresh']['doc']['at'])
            time.sleep(0.3)
        self.assertGreater(len(stamps), 1, 'the collector kept committing while the server kept reading')
        self.assertNotIn('holds the database lock', self.log('collector'))
        self.assertNotIn('could not be read', self.log('server'))


# ---------------------------------------------------------------- AC-66: what the deployed server listens on

class ListeningSocket(Deployment):
    def netstat_lines(self):
        try:
            p = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            self.skipTest('netstat is not available (%s)' % e)
        if p.returncode != 0:
            self.skipTest('netstat exited %d' % p.returncode)
        return p.stdout.splitlines()

    def test_netstat_shows_it_bound_to_127_0_0_1_only(self):
        self.transcripts()
        self.deploy()
        suffix = ':%d' % self.port
        local = [line.split()[1] for line in self.netstat_lines()
                 if len(line.split()) >= 4 and line.split()[0].upper() == 'TCP' and line.split()[1].endswith(suffix)]
        self.assertTrue(local, 'netstat listed no socket on port %d' % self.port)
        self.assertEqual(set(local), {'127.0.0.1' + suffix})

    def test_the_machines_own_address_refuses_the_connection(self):
        self.transcripts()
        self.deploy()
        try:
            lan = socket.gethostbyname(socket.gethostname())
        except OSError as e:
            self.skipTest('no LAN address (%s)' % e)
        if lan.startswith('127.'):
            self.skipTest('this machine resolves to a loopback address')
        with self.assertRaises(OSError):
            socket.create_connection((lan, self.port), timeout=5).close()


# ---------------------------------------------------------------- AC-68 / NFR-18: the push, without a reload

class FinishReachesAnOpenStream(Deployment):
    def test_a_finish_appended_to_a_transcript_arrives_on_the_open_stream(self):
        self.transcripts()
        self.deploy()
        snap = self.await_record('runs/' + AID)
        self.assertEqual(snap['records']['runs/' + AID]['doc']['kind'], 'running')

        sock, status, headers, rest = self.client.open_stream('/api/events?since=%d' % snap['version'], timeout=30)
        self.addCleanup(sock.close)
        self.assertEqual(status, 200)
        self.assertTrue(headers['content-type'].startswith('text/event-stream'))
        reader = ss.StreamReader(sock, rest)
        self.addCleanup(reader.close)

        at = time.time()
        self.append_finish()
        event = reader.wait_for(lambda e: e.get('event') == 'change'
                                and json.loads(e['data']).get('set', {}).get('runs/' + AID, {})
                                .get('doc', {}).get('kind') not in (None, 'running'),
                                timeout=PUSH_BOUND)
        elapsed = time.time() - at
        self.assertIsNotNone(event, 'no change event carried the finish in %ss; events: %r'
                             % (PUSH_BOUND, reader.snapshot()))
        self.assertLess(elapsed, BUDGET, 'NFR-18 allows 10 minutes')
        self.assertEqual(json.loads(event['data'])['set']['runs/' + AID]['doc']['kind'], 'done')
        self.assertEqual(json.loads(event['data'])['set']['runs/' + AID]['doc']['verdict'], 'DONE')

        # "Without a reload": the new kind arrived on the connection that was already open, and the page never
        # asked for anything else. The browser leg of AC-68 is the owner's demonstration, not this test.
        self.assertEqual(len([e for e in reader.snapshot() if e.get('event') == 'reset']), 0)


if __name__ == '__main__':
    unittest.main()
