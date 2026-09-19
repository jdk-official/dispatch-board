"""Registers the two Task Scheduler tasks that start the local-first app when the owner logs on to Windows: the
collector (the database's only writer) and the local server (its reader).

    python local/deploy/tasks.py install [--dry-run]   create or replace both tasks
    python local/deploy/tasks.py uninstall             remove both
    python local/deploy/tasks.py start | stop          run or end them now, without logging off
    python local/deploy/tasks.py status                what Task Scheduler holds
    python local/deploy/tasks.py show                  print the XML that would be registered, and stop

Both tasks run as the owner with an interactive token and no elevation, so nothing here needs an administrator.
Each one launches run_local.py rather than the target directly, because Task Scheduler discards a process's
stdout and stderr and run_local.py captures them to a log file instead.

Registration goes through `schtasks /Create /TN <name> /XML <file> /F`. The `/F` is what makes a re-run
idempotent: it replaces a task of that name instead of failing, so install is create-or-update and the owner can
re-run it after moving the checkout or upgrading Python. The XML is generated into a temporary folder and
deleted once schtasks has read it, so nothing machine-specific is ever written inside the repository.

The definitions carry no password and no secret: an interactive-token task stores none.
"""
import argparse, csv, getpass, io, os, subprocess, sys, tempfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNNER = os.path.join(REPO, 'local', 'deploy', 'run_local.py')

FOLDER = '\\Dispatch board'
TARGETS = {
    'collector': ('Collector', 'Dispatch board: collects the Claude Code transcripts into the local database.'),
    'server': ('Local server', 'Dispatch board: serves the board page and its data on 127.0.0.1.'),
}
# The collector starts at log-on; the server follows 15 seconds later, by which time the collector has created
# the database and its schema. The delay is a courtesy, not a requirement: a server started first answers 503
# until the database appears and then serves it with no restart.
SERVER_DELAY = 'PT15S'
# Three restarts a minute apart cover a transient failure; a refusal that will not heal (a bad config, say)
# stops after them and leaves its reason in the log rather than restarting for ever.
RESTART_COUNT = 3
RESTART_INTERVAL = 'PT1M'


def _run(cmd):
    """The one seam every schtasks call goes through, so the tests can record commands without a Task Scheduler.
    Returns (exit code, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def task_name(target):
    return '%s\\%s' % (FOLDER, TARGETS[target][0])


def python_exe(executable=None):
    """The interpreter to schedule: pythonw.exe beside the running python.exe, so a log-on start opens no
    console window. Falls back to the running interpreter where there is no windowless build."""
    exe = executable or sys.executable
    head, tail = os.path.split(exe)
    root, ext = os.path.splitext(tail)
    if root.lower() == 'python':
        windowless = os.path.join(head, 'pythonw' + ext)
        if os.path.exists(windowless):
            return windowless
    return exe


def current_user():
    domain = os.environ.get('USERDOMAIN')
    name = os.environ.get('USERNAME') or getpass.getuser()
    return '%s\\%s' % (domain, name) if domain else name


def definition(target, repo=None, python=None, user=None):
    """The Task Scheduler XML for one target, as a string. Element order follows the task schema, which
    Task Scheduler enforces."""
    if target not in TARGETS:
        raise ValueError('unknown target %r; expected one of %s' % (target, ', '.join(sorted(TARGETS))))
    label, description = TARGETS[target]
    repo = REPO if repo is None else os.path.abspath(repo)
    python = python_exe() if python is None else python
    user = current_user() if user is None else user
    runner = os.path.join(repo, 'local', 'deploy', 'run_local.py')
    delay = '    <Delay>%s</Delay>\n' % SERVER_DELAY if target == 'server' else ''
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            '  <RegistrationInfo>\n'
            '    <Description>%(description)s</Description>\n'
            '    <URI>%(uri)s</URI>\n'
            '  </RegistrationInfo>\n'
            '  <Triggers>\n'
            '    <LogonTrigger>\n'
            '      <Enabled>true</Enabled>\n'
            '      <UserId>%(user)s</UserId>\n'
            '%(delay)s'
            '    </LogonTrigger>\n'
            '  </Triggers>\n'
            '  <Principals>\n'
            '    <Principal id="Author">\n'
            '      <UserId>%(user)s</UserId>\n'
            '      <LogonType>InteractiveToken</LogonType>\n'
            '      <RunLevel>LeastPrivilege</RunLevel>\n'
            '    </Principal>\n'
            '  </Principals>\n'
            '  <Settings>\n'
            '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
            '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
            '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
            '    <AllowHardTerminate>true</AllowHardTerminate>\n'
            '    <StartWhenAvailable>false</StartWhenAvailable>\n'
            '    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n'
            '    <IdleSettings>\n'
            '      <StopOnIdleEnd>false</StopOnIdleEnd>\n'
            '      <RestartOnIdle>false</RestartOnIdle>\n'
            '    </IdleSettings>\n'
            '    <AllowStartOnDemand>true</AllowStartOnDemand>\n'
            '    <Enabled>true</Enabled>\n'
            '    <Hidden>false</Hidden>\n'
            '    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n'
            '    <WakeToRun>false</WakeToRun>\n'
            '    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n'
            '    <Priority>7</Priority>\n'
            '    <RestartOnFailure>\n'
            '      <Interval>%(restart_interval)s</Interval>\n'
            '      <Count>%(restart_count)d</Count>\n'
            '    </RestartOnFailure>\n'
            '  </Settings>\n'
            '  <Actions Context="Author">\n'
            '    <Exec>\n'
            '      <Command>%(python)s</Command>\n'
            '      <Arguments>"%(runner)s" --target %(target)s</Arguments>\n'
            '      <WorkingDirectory>%(repo)s</WorkingDirectory>\n'
            '    </Exec>\n'
            '  </Actions>\n'
            '</Task>\n') % {
        'description': escape(description), 'uri': escape(task_name(target)), 'user': escape(user),
        'delay': delay, 'restart_interval': RESTART_INTERVAL, 'restart_count': RESTART_COUNT,
        'python': escape(python), 'runner': escape(runner), 'target': target, 'repo': escape(repo)}


def say(msg):
    print('tasks: ' + msg, flush=True)


def _report(verb, target, code, out, err):
    detail = (out or '').strip() or (err or '').strip()
    say('%s %s: schtasks exited %d%s' % (verb, task_name(target), code, ('; ' + detail) if detail else ''))


def install(repo=None, python=None, user=None, dry_run=False):
    """Creates or replaces both tasks. Returns 0 when every schtasks call succeeded."""
    worst = 0
    for target in sorted(TARGETS):
        xml = definition(target, repo=repo, python=python, user=user)
        if dry_run:
            say('would register %s with:' % task_name(target))
            print(xml)
            continue
        # A temporary folder, never the repository: the XML holds this machine's interpreter path, checkout
        # path and user name, none of which belongs in a committed file.
        tmp = tempfile.mkdtemp(prefix='dispatch-board-task-')
        path = os.path.join(tmp, target + '.xml')
        try:
            with open(path, 'w', encoding='utf-16') as f:
                f.write(xml)
            code, out, err = _run(['schtasks', '/Create', '/TN', task_name(target), '/XML', path, '/F'])
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
            try:
                os.rmdir(tmp)
            except OSError:
                pass
        _report('install', target, code, out, err)
        worst = worst or code
    return worst


def uninstall(dry_run=False):
    """Removes both tasks. A task that was never installed is reported, not failed: uninstall is idempotent
    too, and the empty '\\Dispatch board' folder Task Scheduler leaves behind is harmless. Any other refusal
    (access denied, the Task Scheduler service unavailable) is a failure, so a task that is still registered
    never looks removed. schtasks gives both the same exit code and words its messages in the Windows display
    language, so after a failed delete the task list is read instead: `schtasks /Query /FO CSV /NH` prints one
    quoted task path per line, and neither its exit code, its layout nor the task names are translated. When
    that list cannot be read either, the removal is reported as unconfirmed, and as a failure."""
    worst = 0
    for target in sorted(TARGETS):
        if dry_run:
            say('would delete %s' % task_name(target))
            continue
        code, out, err = _run(['schtasks', '/Delete', '/TN', task_name(target), '/F'])
        _report('uninstall', target, code, out, err)
        if not code:
            continue
        listed, listing, _ = _run(['schtasks', '/Query', '/FO', 'CSV', '/NH'])
        if listed:
            say('%s could not be removed, and schtasks /Query exited %d, so whether it remains could not be '
                'confirmed' % (task_name(target), listed))
            worst = worst or code
        elif task_name(target).lower() in {row[0].lower() for row in csv.reader(io.StringIO(listing or '')) if row}:
            say('%s could not be removed; it is still registered' % task_name(target))
            worst = worst or code
        else:
            say('%s was not installed' % task_name(target))
    return worst


def _each(verb, flag, order, dry_run=False, fatal=True):
    worst = 0
    for target in order:
        if dry_run:
            say('would %s %s' % (verb, task_name(target)))
            continue
        code, out, err = _run(['schtasks', flag, '/TN', task_name(target)])
        _report(verb, target, code, out, err)
        if fatal:
            worst = worst or code
    return worst


def start(dry_run=False):
    """Runs both now, collector first, so the owner need not log off and on to try the deployment."""
    return _each('start', '/Run', ['collector', 'server'], dry_run)


def stop(dry_run=False):
    return _each('stop', '/End', ['server', 'collector'], dry_run)


def status(dry_run=False):
    """Reports both; a task that is not installed is an answer, not a failure."""
    return _each('status', '/Query', ['collector', 'server'], dry_run, fatal=False)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='tasks.py', description='Install the log-on start for the local-first app.')
    ap.add_argument('command', nargs='?', choices=['install', 'uninstall', 'start', 'stop', 'status', 'show'])
    ap.add_argument('--dry-run', action='store_true', help='say what would happen and change nothing')
    ap.add_argument('--repo', help='the checkout to schedule (default: the one holding this script)')
    ap.add_argument('--python', help='the interpreter to schedule (default: pythonw beside this one)')
    ap.add_argument('--user', help='the account the tasks run as (default: the current one)')
    try:
        args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    if args.command is None:
        ap.print_usage(sys.stderr)
        print('tasks.py: a command is required', file=sys.stderr)
        return 2
    if args.command == 'show':
        for target in sorted(TARGETS):
            print(definition(target, repo=args.repo, python=args.python, user=args.user))
        return 0
    if args.command == 'install':
        return install(repo=args.repo, python=args.python, user=args.user, dry_run=args.dry_run)
    return {'uninstall': uninstall, 'start': start, 'stop': stop, 'status': status}[args.command](args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
