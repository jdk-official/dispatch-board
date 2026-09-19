"""Tests for local/deploy/tasks.py: the two Task Scheduler definitions that start the collector and the local
server when the owner logs on, and the schtasks calls that install, remove, start and stop them.

No test touches the real Task Scheduler and no test writes inside the repository: every schtasks call goes
through the tasks._run seam, replaced here with a recorder, and every generated XML file goes to a temporary
folder the test owns.
"""
import contextlib, io, os, shutil, sys, tempfile, unittest
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(REPO, 'local', 'deploy'),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tasks  # noqa: E402

NS = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
FAKE_REPO = os.path.join('C:' + os.sep, 'work', 'dispatch board')
FAKE_PY = os.path.join('C:' + os.sep, 'Program Files', 'Python', 'pythonw.exe')
USER = 'EXAMPLE\\owner'
# `schtasks /Query /FO CSV /NH` as it prints on any locale: a quoted task path, next run time and status per line.
LISTED = ('"\\AMDLinkUpdate","N/A","Ready"\n"\\Dispatch board\\Collector","N/A","Running"\n'
          '"\\Dispatch board\\Local server","N/A","Bereit"\n')
UNLISTED = '"\\AMDLinkUpdate","N/A","Ready"\n"\\Dispatch board\\Collector (old)","N/A","Bereit"\n'


def parse(target, **kw):
    kw.setdefault('repo', FAKE_REPO)
    kw.setdefault('python', FAKE_PY)
    kw.setdefault('user', USER)
    return ET.fromstring(tasks.definition(target, **kw))


def text(root, path):
    el = root.find(path, NS)
    return None if el is None else el.text


class Recorder:
    """Stands in for tasks._run: records the command lines and answers with a canned exit code."""

    def __init__(self, codes=None, errs=None, outs=None):
        self.cmds = []
        self.codes = codes or {}
        self.errs = errs or {}
        self.outs = outs or {}

    def __call__(self, cmd):
        self.cmds.append(list(cmd))
        return self.codes.get(cmd[1], 0), self.outs.get(cmd[1], ''), self.errs.get(cmd[1], '')

    def verbs(self):
        return [c[1] for c in self.cmds]


class Seam(unittest.TestCase):
    def setUp(self):
        self.calls = Recorder()
        real = tasks._run
        tasks._run = self.calls
        self.addCleanup(setattr, tasks, '_run', real)
        self.tmp = tempfile.mkdtemp(prefix='deploy-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for quiet in (contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO())):
            quiet.__enter__()
            self.addCleanup(quiet.__exit__, None, None, None)


# ---------------------------------------------------------------- the definitions

class Definition(unittest.TestCase):
    def test_both_targets_are_defined(self):
        self.assertEqual(sorted(tasks.TARGETS), ['collector', 'server'])

    def test_it_is_a_logon_task_for_the_named_user(self):
        for target in tasks.TARGETS:
            root = parse(target)
            self.assertIsNotNone(root.find('t:Triggers/t:LogonTrigger', NS), target)
            self.assertEqual(text(root, 't:Triggers/t:LogonTrigger/t:UserId'), USER, target)
            self.assertEqual(text(root, 't:Triggers/t:LogonTrigger/t:Enabled'), 'true', target)
            self.assertEqual(text(root, 't:Principals/t:Principal/t:UserId'), USER, target)

    def test_it_runs_as_the_owner_without_elevation(self):
        for target in tasks.TARGETS:
            root = parse(target)
            self.assertEqual(text(root, 't:Principals/t:Principal/t:LogonType'), 'InteractiveToken', target)
            self.assertEqual(text(root, 't:Principals/t:Principal/t:RunLevel'), 'LeastPrivilege', target)

    def test_the_collector_starts_first_and_the_server_follows_it(self):
        self.assertIsNone(text(parse('collector'), 't:Triggers/t:LogonTrigger/t:Delay'))
        self.assertEqual(text(parse('server'), 't:Triggers/t:LogonTrigger/t:Delay'), tasks.SERVER_DELAY)

    def test_the_action_runs_the_log_capturing_wrapper(self):
        for target in tasks.TARGETS:
            root = parse(target)
            self.assertEqual(text(root, 't:Actions/t:Exec/t:Command'), FAKE_PY, target)
            args = text(root, 't:Actions/t:Exec/t:Arguments')
            self.assertIn(os.path.join(FAKE_REPO, 'local', 'deploy', 'run_local.py'), args, target)
            self.assertIn('--target ' + target, args, target)
            self.assertEqual(text(root, 't:Actions/t:Exec/t:WorkingDirectory'), FAKE_REPO, target)

    def test_a_path_with_a_space_is_quoted_in_the_arguments(self):
        args = text(parse('collector'), 't:Actions/t:Exec/t:Arguments')
        self.assertIn('"%s"' % os.path.join(FAKE_REPO, 'local', 'deploy', 'run_local.py'), args)

    def test_settings_suit_a_process_that_is_meant_never_to_end(self):
        for target in tasks.TARGETS:
            root = parse(target)
            self.assertEqual(text(root, 't:Settings/t:ExecutionTimeLimit'), 'PT0S', target)
            self.assertEqual(text(root, 't:Settings/t:MultipleInstancesPolicy'), 'IgnoreNew', target)
            self.assertEqual(text(root, 't:Settings/t:DisallowStartIfOnBatteries'), 'false', target)
            self.assertEqual(text(root, 't:Settings/t:StopIfGoingOnBatteries'), 'false', target)
            self.assertEqual(text(root, 't:Settings/t:RunOnlyIfIdle'), 'false', target)
            self.assertEqual(text(root, 't:Settings/t:IdleSettings/t:StopOnIdleEnd'), 'false', target)
            self.assertEqual(text(root, 't:Settings/t:RestartOnFailure/t:Count'), '3', target)

    def test_a_path_holding_an_ampersand_is_escaped(self):
        root = parse('collector', repo=os.path.join('C:' + os.sep, 'a & b'))
        self.assertIn('a & b', text(root, 't:Actions/t:Exec/t:WorkingDirectory'))

    def test_an_unknown_target_is_refused(self):
        with self.assertRaises(ValueError):
            tasks.definition('exporter', repo=FAKE_REPO, python=FAKE_PY, user=USER)

    def test_the_defaults_describe_this_checkout(self):
        root = parse('collector', repo=None, python=None, user=None)
        self.assertEqual(text(root, 't:Actions/t:Exec/t:WorkingDirectory'), tasks.REPO)
        self.assertTrue(text(root, 't:Principals/t:Principal/t:UserId'))


class Interpreter(unittest.TestCase):
    def test_it_prefers_the_windowless_interpreter_beside_the_running_one(self):
        tmp = tempfile.mkdtemp(prefix='deploy-test-')
        self.addCleanup(shutil.rmtree, tmp, True)
        exe = os.path.join(tmp, 'python.exe')
        win = os.path.join(tmp, 'pythonw.exe')
        for p in (exe, win):
            open(p, 'w').close()
        self.assertEqual(tasks.python_exe(exe), win)

    def test_it_falls_back_when_there_is_no_windowless_interpreter(self):
        tmp = tempfile.mkdtemp(prefix='deploy-test-')
        self.addCleanup(shutil.rmtree, tmp, True)
        exe = os.path.join(tmp, 'python.exe')
        open(exe, 'w').close()
        self.assertEqual(tasks.python_exe(exe), exe)


# ---------------------------------------------------------------- install, uninstall, start, stop

class Install(Seam):
    def test_it_creates_both_tasks_by_xml(self):
        self.assertEqual(tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER), 0)
        self.assertEqual(self.calls.verbs(), ['/Create', '/Create'])
        names = [c[c.index('/TN') + 1] for c in self.calls.cmds]
        self.assertEqual(names, [tasks.task_name('collector'), tasks.task_name('server')])
        for cmd in self.calls.cmds:
            self.assertIn('/XML', cmd)
            self.assertIn('/F', cmd)  # /F replaces an existing task, which is what makes a re-run idempotent

    def test_a_re_run_issues_the_same_commands(self):
        tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER)
        first = [c[:4] for c in self.calls.cmds]
        self.calls.cmds = []
        self.assertEqual(tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER), 0)
        self.assertEqual([c[:4] for c in self.calls.cmds], first)

    def test_the_xml_it_hands_schtasks_is_outside_the_repository(self):
        tasks.install(repo=REPO, python=FAKE_PY, user=USER)
        for cmd in self.calls.cmds:
            path = cmd[cmd.index('/XML') + 1]
            self.assertFalse(os.path.abspath(path).startswith(os.path.abspath(REPO) + os.sep), path)

    def test_the_xml_is_removed_once_schtasks_has_read_it(self):
        seen = []
        real = tasks._run

        def spy(cmd):
            path = cmd[cmd.index('/XML') + 1]
            with open(path, 'rb') as f:
                seen.append((path, f.read()))
            return real(cmd)
        tasks._run = spy
        tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER)
        self.assertEqual(len(seen), 2)
        for path, body in seen:
            self.assertFalse(os.path.exists(path), path)
            self.assertTrue(body.startswith(b'\xff\xfe'), 'schtasks /XML needs UTF-16')
            self.assertIn('encoding="UTF-16"', body.decode('utf-16'))

    def test_a_schtasks_failure_is_reported_as_a_non_zero_exit(self):
        self.calls.codes['/Create'] = 1
        self.assertEqual(tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER), 1)

    def test_a_dry_run_calls_schtasks_for_nothing(self):
        self.assertEqual(tasks.install(repo=FAKE_REPO, python=FAKE_PY, user=USER, dry_run=True), 0)
        self.assertEqual(self.calls.cmds, [])


class Uninstall(Seam):
    def test_it_deletes_both_tasks(self):
        self.assertEqual(tasks.uninstall(), 0)
        self.assertEqual(self.calls.verbs(), ['/Delete', '/Delete'])
        for cmd in self.calls.cmds:
            self.assertIn('/F', cmd)

    def test_a_task_that_was_never_installed_is_not_a_failure(self):
        self.calls.codes['/Delete'] = 1
        self.calls.errs['/Delete'] = 'ERROR: The system cannot find the file specified.\n'
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasks.uninstall(), 0)
        self.assertIn('not installed', out.getvalue())

    def test_a_delete_schtasks_refused_is_a_failure(self):
        self.calls.codes['/Delete'] = 1
        self.calls.errs['/Delete'] = 'ERROR: Access is denied.\n'
        self.calls.outs['/Query'] = LISTED
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasks.uninstall(), 1)
        self.assertIn('could not be removed', out.getvalue())

    def test_a_failed_delete_that_gives_no_reason_is_a_failure(self):
        # A task Task Scheduler still lists is a failure whatever schtasks said, or did not say, about the delete.
        self.calls.codes['/Delete'] = 1
        self.calls.outs['/Query'] = LISTED
        self.assertEqual(tasks.uninstall(), 1)

    # schtasks translates its messages but not its exit codes, its CSV layout or the task names, so these cases
    # speak German to prove that uninstall reads only what is not translated.
    def test_on_a_non_english_windows_a_task_that_was_never_installed_is_not_a_failure(self):
        self.calls.codes['/Delete'] = 1
        self.calls.errs['/Delete'] = 'FEHLER: Das System kann die angegebene Datei nicht finden.\n'
        self.calls.outs['/Query'] = UNLISTED
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasks.uninstall(), 0)
        self.assertEqual(out.getvalue().count('was not installed'), 2)
        self.assertNotIn('still registered', out.getvalue())
        self.assertEqual(self.calls.cmds[1], ['schtasks', '/Query', '/FO', 'CSV', '/NH'])

    def test_on_a_non_english_windows_a_task_that_is_still_listed_is_a_failure(self):
        self.calls.codes['/Delete'] = 1
        self.calls.errs['/Delete'] = 'FEHLER: Zugriff verweigert\n'
        self.calls.outs['/Query'] = LISTED
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasks.uninstall(), 1)
        self.assertEqual(out.getvalue().count('still registered'), 2)
        self.assertNotIn('not installed', out.getvalue())

    def test_the_english_not_found_text_does_not_outweigh_a_listing_that_still_holds_the_task(self):
        self.calls.codes['/Delete'] = 1
        self.calls.errs['/Delete'] = 'ERROR: The system cannot find the file specified.\n'
        self.calls.outs['/Query'] = LISTED
        self.assertEqual(tasks.uninstall(), 1)

    def test_when_the_listing_cannot_be_read_either_removal_is_unconfirmed_and_a_failure(self):
        self.calls.codes['/Delete'] = 1
        self.calls.codes['/Query'] = 1
        self.calls.errs['/Delete'] = 'FEHLER: Der Aufgabenplanungsdienst ist nicht verfügbar.\n'
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(tasks.uninstall(), 1)
        self.assertIn('could not be confirmed', out.getvalue())
        self.assertNotIn('still registered', out.getvalue())
        self.assertNotIn('not installed', out.getvalue())

    def test_a_dry_run_calls_schtasks_for_nothing(self):
        self.assertEqual(tasks.uninstall(dry_run=True), 0)
        self.assertEqual(self.calls.cmds, [])


class StartStopStatus(Seam):
    def test_start_runs_both_tasks_in_order(self):
        self.assertEqual(tasks.start(), 0)
        self.assertEqual(self.calls.verbs(), ['/Run', '/Run'])
        names = [c[c.index('/TN') + 1] for c in self.calls.cmds]
        self.assertEqual(names, [tasks.task_name('collector'), tasks.task_name('server')])

    def test_stop_ends_both_tasks(self):
        self.assertEqual(tasks.stop(), 0)
        self.assertEqual(self.calls.verbs(), ['/End', '/End'])

    def test_status_queries_both_tasks_and_survives_a_missing_one(self):
        self.calls.codes['/Query'] = 1
        self.assertEqual(tasks.status(), 0)
        self.assertEqual(self.calls.verbs(), ['/Query', '/Query'])


class CommandLine(Seam):
    def test_every_subcommand_reaches_its_function(self):
        for argv, verb in ((['install'], '/Create'), (['uninstall'], '/Delete'), (['start'], '/Run'),
                           (['stop'], '/End'), (['status'], '/Query')):
            self.calls.cmds = []
            self.assertEqual(tasks.main(argv + ['--repo', FAKE_REPO, '--python', FAKE_PY, '--user', USER]), 0, argv)
            self.assertEqual(set(self.calls.verbs()), {verb}, argv)

    def test_show_prints_the_xml_and_calls_schtasks_for_nothing(self):
        self.assertEqual(tasks.main(['show', '--repo', FAKE_REPO, '--python', FAKE_PY, '--user', USER]), 0)
        self.assertEqual(self.calls.cmds, [])

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(tasks.main([]), 2)


if __name__ == '__main__':
    unittest.main()
