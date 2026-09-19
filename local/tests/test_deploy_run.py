"""Tests for local/deploy/run_local.py: the wrapper Task Scheduler actually launches, which captures the
collector's or the server's stdout and stderr into a rotating log file.

Most cases drive a stub entry point, so an exit code, a raise and a Ctrl+C can each be exercised without a real
collector; one case runs the real collector through the wrapper against synthetic transcripts, so the capture is
proved against the process it exists for rather than against a stub only.
"""
import contextlib, io, json, os, re, shutil, subprocess, sys, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER = os.path.join(REPO, 'local', 'deploy', 'run_local.py')
for _p in (os.path.join(REPO, 'local', 'deploy'), os.path.join(REPO, 'tests'),
           os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import run_local  # noqa: E402
import test_export_sessions as tes  # noqa: E402

STAMP = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d ')


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='run-local-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.logs = os.path.join(self.tmp, 'logs')

    def read(self, name='collector.log'):
        with io.open(os.path.join(self.logs, name), encoding='utf-8') as f:
            return f.read()

    def run_with(self, entry, args=(), target='collector', **kw):
        return run_local.run(target, list(args), log_dir=self.logs, entry=entry, **kw)


# ---------------------------------------------------------------- where the log goes

class LogPath(unittest.TestCase):
    def test_the_default_is_a_git_ignored_folder_beside_the_database(self):
        self.assertEqual(run_local.log_dir(), os.path.join(REPO, 'out', 'local', 'logs'))
        self.assertEqual(run_local.log_path('server'), os.path.join(REPO, 'out', 'local', 'logs', 'server.log'))

    def test_the_default_is_relative_to_the_checkout_not_the_working_folder(self):
        # Task Scheduler may start the process in System32, so nothing may be resolved against os.getcwd().
        self.assertTrue(os.path.isabs(run_local.log_dir()))
        self.assertEqual(run_local.log_dir('X:\\elsewhere'), os.path.join('X:\\elsewhere', 'out', 'local', 'logs'))

    def test_a_failure_of_the_log_itself_is_reported_in_the_temp_folder(self):
        # Not beside the log: the folder that could not be written is the one place the reason cannot go.
        self.assertEqual(run_local.fallback_path('server'),
                         os.path.join(tempfile.gettempdir(), 'dispatch-board-server-log-failure.txt'))


class MakesItsFolder(Case):
    def test_a_missing_log_folder_is_created(self):
        self.assertFalse(os.path.exists(self.logs))
        self.run_with(lambda argv: 0)
        self.assertTrue(os.path.isfile(os.path.join(self.logs, 'collector.log')))


# ---------------------------------------------------------------- what it captures

class Capture(Case):
    def test_both_streams_reach_the_log(self):
        def entry(argv):
            print('collector: a committed pass')
            print('collector: a warning', file=sys.stderr)
            return 0
        self.assertEqual(self.run_with(entry), 0)
        log = self.read()
        self.assertIn('collector: a committed pass', log)
        self.assertIn('collector: a warning', log)

    def test_every_line_is_stamped_with_the_time(self):
        self.run_with(lambda argv: print('collector: hello') or 0)
        for line in self.read().splitlines():
            self.assertRegex(line, STAMP)

    def test_it_records_the_start_the_arguments_and_the_exit(self):
        self.assertEqual(self.run_with(lambda argv: 3, args=['--once']), 3)
        log = self.read()
        self.assertIn('run_local: starting collector', log)
        self.assertIn('--once', log)
        self.assertIn('exited 3', log)

    def test_a_line_without_a_newline_is_still_written(self):
        self.run_with(lambda argv: sys.stdout.write('collector: no newline here') or 0)
        self.assertIn('collector: no newline here', self.read())

    def test_a_blank_line_survives(self):
        self.run_with(lambda argv: print('a\n\nb') or 0)
        self.assertEqual([l.split(' ', 1)[1] for l in self.read().splitlines()][1:4], ['a', '', 'b'])

    def test_the_real_streams_are_restored_afterwards(self):
        out, err = sys.stdout, sys.stderr
        self.run_with(lambda argv: 0)
        self.assertIs(sys.stdout, out)
        self.assertIs(sys.stderr, err)

    def test_it_writes_nothing_but_the_log(self):
        self.run_with(lambda argv: print('x') or 0)
        self.assertEqual(os.listdir(self.logs), ['collector.log'])
        self.assertEqual(os.listdir(self.tmp), ['logs'])


class Failures(Case):
    def test_a_raise_is_logged_with_its_traceback_and_exits_one(self):
        def entry(argv):
            raise RuntimeError('the wheels came off')
        self.assertEqual(self.run_with(entry), 1)
        log = self.read()
        self.assertIn('RuntimeError', log)
        self.assertIn('the wheels came off', log)
        self.assertIn('Traceback', log)

    def test_ctrl_c_is_a_clean_stop(self):
        def entry(argv):
            raise KeyboardInterrupt
        self.assertEqual(self.run_with(entry), 0)
        self.assertIn('stopped', self.read())

    def test_an_exit_call_inside_the_target_is_taken_as_its_code(self):
        def entry(argv):
            raise SystemExit(2)
        self.assertEqual(self.run_with(entry), 2)
        self.assertIn('exited 2', self.read())


# ---------------------------------------------------------------- rotation

class Rotation(Case):
    def lines(self, n, size=200):
        def entry(argv):
            for i in range(n):
                print('collector: %04d %s' % (i, 'x' * size))
            return 0
        return entry

    def test_the_live_log_stays_under_the_cap(self):
        self.run_with(self.lines(400), max_bytes=4000, backups=3)
        self.assertLess(os.path.getsize(os.path.join(self.logs, 'collector.log')), 4000 + 400)

    def test_older_output_moves_into_numbered_backups(self):
        self.run_with(self.lines(400), max_bytes=4000, backups=3)
        self.assertTrue(os.path.exists(os.path.join(self.logs, 'collector.log.1')))

    def test_growth_is_bounded_by_the_cap_times_the_backups(self):
        self.run_with(self.lines(4000), max_bytes=4000, backups=3)
        names = sorted(os.listdir(self.logs))
        self.assertEqual(names, ['collector.log', 'collector.log.1', 'collector.log.2', 'collector.log.3'])
        total = sum(os.path.getsize(os.path.join(self.logs, n)) for n in names)
        self.assertLess(total, 4000 * 5)

    def test_the_newest_output_is_the_one_kept_live(self):
        self.run_with(self.lines(4000), max_bytes=4000, backups=3)
        self.assertIn('collector: 3999', self.read())

    def test_a_second_run_appends_rather_than_truncating(self):
        self.run_with(lambda argv: print('collector: first run') or 0)
        self.run_with(lambda argv: print('collector: second run') or 0)
        log = self.read()
        self.assertIn('collector: first run', log)
        self.assertIn('collector: second run', log)


# ---------------------------------------------------------------- when the log itself fails

class Diverted(Case):
    """Common ground for the cases where the log cannot take what it is given: the real streams are put back
    whatever the wrapper under test does, and the reports it makes land somewhere the test can read."""

    def setUp(self):
        super().setUp()
        saved = sys.stdout, sys.stderr
        self.addCleanup(lambda: (setattr(sys, 'stdout', saved[0]), setattr(sys, 'stderr', saved[1])))
        self.fallback = os.path.join(self.tmp, 'fallback.txt')
        self.err = io.StringIO()
        sys.stderr = self.err

    def fallback_text(self):
        if not os.path.exists(self.fallback):
            return ''
        with io.open(self.fallback, encoding='utf-8') as f:
            return f.read()


class LogWriteFails(Diverted):
    """A real failure of the log, not a mocked one. The rotation target collector.log.1 is a folder, so every
    rollover raises PermissionError out of os.remove, as an antivirus, backup or sync handle on the rotated
    file does on the owner's PC. Before the fix this recursed through the captured stderr until the process
    died with nothing on either stream and the streams left swapped."""

    def setUp(self):
        super().setUp()
        self.obstacle = os.path.join(self.logs, 'collector.log.1')
        os.makedirs(self.obstacle)
        self.reached = []

    def entry(self, n=40, then=None):
        def entry(argv):
            for i in range(n):
                print('collector: line %04d %s' % (i, 'x' * 40))
            if then:
                then()
                print('collector: after the obstacle went')
            self.reached.append(True)
            return 0
        return entry

    def go(self, entry, target='collector', max_bytes=500):
        return run_local.run(target, [], log_dir=self.logs, max_bytes=max_bytes, backups=1, entry=entry,
                             fallback=self.fallback)

    def test_the_target_keeps_running_and_its_exit_code_is_kept(self):
        self.assertEqual(self.go(self.entry()), 0)
        self.assertEqual(self.reached, [True], 'the target ran to its end')

    def test_the_real_streams_are_restored(self):
        out = sys.stdout
        self.go(self.entry())
        self.assertIs(sys.stdout, out)
        self.assertIs(sys.stderr, self.err)

    def test_the_reason_reaches_the_real_stderr_and_the_fallback_file(self):
        self.go(self.entry())
        for text in (self.err.getvalue(), self.fallback_text()):
            self.assertIn('PermissionError', text)
            self.assertIn('collector.log', text)
            self.assertNotIn('RecursionError', text)

    def test_the_lines_the_log_could_not_take_are_kept_in_the_fallback_file(self):
        self.go(self.entry())
        text = self.fallback_text()
        self.assertIn('collector: line 0039', text)
        self.assertIn('run_local: collector exited 0', text)

    def test_the_reason_is_reported_once_rather_than_once_a_line(self):
        self.go(self.entry())
        self.assertEqual(self.err.getvalue().count('could not be written'), 1)

    def test_with_no_stderr_at_all_as_under_pythonw_the_fallback_file_still_holds_it(self):
        sys.stderr = None
        self.assertEqual(self.go(self.entry()), 0)
        self.assertIn('PermissionError', self.fallback_text())
        self.assertIn('collector: line 0039', self.fallback_text())

    def test_the_log_is_written_again_once_the_obstacle_is_gone(self):
        # The recovery note quotes the fallback path and the rotation path, so under a long temp folder it alone
        # can outgrow a 500-byte cap and rotate the proof line out of the single backup. 5000 bytes leaves room
        # for any real temp path; 200 lines still push the log past the cap, so the rollover still fails.
        self.assertEqual(self.go(self.entry(n=200, then=lambda: os.rmdir(self.obstacle)), max_bytes=5000), 0)
        live = self.read() + self.read('collector.log.1')
        self.assertIn('collector: after the obstacle went', live)
        self.assertIn('run_local: the log is being written again', live)
        self.assertNotIn('collector: after the obstacle went', self.fallback_text())

    def test_the_fallback_file_is_bounded(self):
        real = run_local.FALLBACK_MAX_BYTES
        run_local.FALLBACK_MAX_BYTES = 2000
        self.addCleanup(setattr, run_local, 'FALLBACK_MAX_BYTES', real)
        self.go(self.entry(n=400))
        self.assertLess(os.path.getsize(self.fallback), 2000 + 400)


class LineWriterReentry(unittest.TestCase):
    def test_a_sink_that_writes_back_into_its_own_writer_is_diverted_not_recursed(self):
        diverted = []
        writer = run_local.LineWriter(lambda line: writer.write('nested: ' + line + '\n'), diverted.append)
        writer.write('hello\n')
        self.assertEqual(''.join(diverted), 'nested: hello\n')

    def test_a_sink_that_raises_diverts_the_line_with_its_reason(self):
        diverted = []

        def sink(line):
            raise OSError('disk full')
        writer = run_local.LineWriter(sink, diverted.append)
        writer.write('hello\n')
        self.assertIn('hello', ''.join(diverted))
        self.assertIn('disk full', ''.join(diverted))


class UnusableLogFolder(Diverted):
    """The log cannot even be opened: a file stands where the log folder should be. That is a failure of the log
    like any other, so it is handled the same way as one at run time: the target starts, the reason and its lines
    go to the fallback file, and the log is tried again on every line. Only when the fallback file cannot take the
    start line either is there no channel left but the exit code, and then the wrapper exits 73 without starting
    the target, which Task Scheduler records as the task's Last Run Result."""

    def setUp(self):
        super().setUp()
        open(self.logs, 'w').close()
        self.called = []

    def entry(self, argv):
        self.called.append(argv)
        print('collector: ran without its log')
        return 3

    def go(self, entry=None):
        return run_local.run('collector', [], log_dir=self.logs, entry=entry or self.entry, fallback=self.fallback)

    def test_the_target_starts_and_its_exit_code_is_kept(self):
        self.assertEqual(self.go(), 3)
        self.assertEqual(self.called, [[]])
        self.assertIs(sys.stderr, self.err)

    def test_main_starts_it_too(self):
        real = run_local.fallback_path
        run_local.fallback_path = lambda target: self.fallback
        self.addCleanup(setattr, run_local, 'fallback_path', real)
        self.assertEqual(run_local.main(['--target', 'server', '--log-dir', self.logs], entry=self.entry), 3)
        self.assertEqual(self.called, [[]])

    def test_the_reason_is_on_stderr_and_in_the_fallback_file(self):
        self.go()
        for text in (self.err.getvalue(), self.fallback_text()):
            self.assertIn('FileExistsError', text)
            self.assertIn(self.logs, text)
        self.assertIn('collector: ran without its log', self.fallback_text())
        self.assertIn('run_local: collector exited 3', self.fallback_text())

    def test_the_log_is_written_again_once_its_folder_can_be_made(self):
        def entry(argv):
            print('collector: before the obstacle went')
            os.remove(self.logs)
            print('collector: after the obstacle went')
            return 0
        self.assertEqual(self.go(entry), 0)
        log = self.read()
        self.assertIn('collector: after the obstacle went', log)
        self.assertIn('run_local: the log is being written again', log)
        self.assertIn('collector: before the obstacle went', self.fallback_text())
        self.assertNotIn('collector: after the obstacle went', self.fallback_text())

    def test_exit_73_without_starting_the_target_when_the_fallback_file_cannot_be_written_either(self):
        os.makedirs(self.fallback)  # a folder where the fallback file should be, so opening it really fails
        self.assertEqual(run_local.LOG_UNUSABLE, 73)
        self.assertEqual(self.go(), run_local.LOG_UNUSABLE)
        self.assertEqual(self.called, [])
        self.assertIs(sys.stderr, self.err)
        text = self.err.getvalue()
        for part in ('FileExistsError', self.logs, self.fallback, 'not started', '73'):
            self.assertIn(part, text)

    def test_an_unwritable_fallback_file_alone_does_not_stop_the_target(self):
        os.remove(self.logs)
        os.makedirs(self.fallback)
        self.assertEqual(self.go(), 3)
        self.assertEqual(self.called, [[]])
        self.assertIn('collector: ran without its log', self.read())

    def real_process(self):
        # --help makes the real collector print its usage and exit 0 without reading a config or a database.
        env = dict(os.environ, TMP=self.tmp, TEMP=self.tmp, TMPDIR=self.tmp)
        return subprocess.run([sys.executable, RUNNER, '--target', 'collector', '--log-dir', self.logs, '--', '--help'],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_a_real_process_starts_its_target_without_its_log(self):
        p = self.real_process()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('FileExistsError', p.stderr)
        with io.open(os.path.join(self.tmp, 'dispatch-board-collector-log-failure.txt'), encoding='utf-8') as f:
            text = f.read()
        self.assertIn('FileExistsError', text)
        self.assertIn('usage: collector.py', text)

    def test_a_real_process_exits_73_when_neither_the_log_nor_the_fallback_file_can_be_written(self):
        os.makedirs(os.path.join(self.tmp, 'dispatch-board-collector-log-failure.txt'))
        p = self.real_process()
        self.assertEqual(p.returncode, 73, p.stderr)
        self.assertIn('FileExistsError', p.stderr)
        self.assertIn('not started', p.stderr)


# ---------------------------------------------------------------- the command line

class CommandLine(Case):
    def setUp(self):
        super().setUp()
        quiet = contextlib.redirect_stderr(io.StringIO())  # argparse writes its usage there on a refusal
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)

    def test_an_unknown_target_is_a_usage_error(self):
        self.assertEqual(run_local.main(['--target', 'exporter', '--log-dir', self.logs]), 2)

    def test_a_missing_target_is_a_usage_error(self):
        self.assertEqual(run_local.main(['--log-dir', self.logs]), 2)

    def test_the_arguments_after_the_wrappers_own_go_to_the_target(self):
        seen = []
        self.assertEqual(run_local.main(['--target', 'collector', '--log-dir', self.logs,
                                         '--', '--once', '--interval', '5'],
                                        entry=lambda argv: seen.append(argv) or 0), 0)
        self.assertEqual(seen, [['--once', '--interval', '5']])

    def test_the_separating_dashes_are_optional(self):
        seen = []
        run_local.main(['--target', 'server', '--log-dir', self.logs, '--port', '0'],
                       entry=lambda argv: seen.append(argv) or 0)
        self.assertEqual(seen, [['--port', '0']])


# ---------------------------------------------------------------- against the real collector

class RealCollector(Case):
    """The wrapper's reason for existing: a scheduled collector's only voice is this log file."""

    def config(self, tree, **over):
        cfg = tes.config(projectsRoot=tree.root)
        cfg['catalogue'] = {'marketplacePath': os.path.join(self.tmp, 'no-marketplace'),
                            'installedPath': os.path.join(self.tmp, 'no-installed.json')}
        cfg['local'] = {'databasePath': os.path.join(self.tmp, 'db', 'board.db'), 'port': 8765}
        cfg.update(over)
        path = os.path.join(self.tmp, 'board.config.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)
        return path

    def test_a_committed_pass_is_captured(self):
        tree = tes.Tree()
        self.addCleanup(tree.cleanup)
        tree.basic()
        cfg = self.config(tree)
        self.assertEqual(run_local.main(['--target', 'collector', '--log-dir', self.logs,
                                         '--', '--once', '--config', cfg]), 0)
        log = self.read()
        self.assertIn('collector: ', log)
        self.assertIn('sessions', log)
        self.assertIn('run_local: collector exited 0', log)

    def test_a_refusal_is_captured_and_its_exit_code_carried_out(self):
        tree = tes.Tree()
        self.addCleanup(tree.cleanup)
        cfg = self.config(tree, local={'databasePath': '\\\\nas\\share\\board.db', 'port': 8765})
        self.assertEqual(run_local.main(['--target', 'collector', '--log-dir', self.logs,
                                         '--', '--once', '--config', cfg]), 2)
        log = self.read()
        self.assertIn('network path', log)
        self.assertIn('run_local: collector exited 2', log)


if __name__ == '__main__':
    unittest.main()
