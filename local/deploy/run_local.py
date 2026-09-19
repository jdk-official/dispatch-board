"""Runs the collector or the local server with its stdout and stderr captured to a rotating log file. This is
what the Task Scheduler tasks launch (tasks.py), because a scheduled process's output otherwise goes nowhere:
without this file a refused collector pass or a server that would not bind leaves the board stalled with no
visible reason.

    python local/deploy/run_local.py --target collector|server [--log-dir DIR] [--max-bytes N] [--backups N]
                                     [-- arguments for the target ...]

The wrapper's own options come first; everything after them, with an optional `--` between, is handed to the
target unchanged, so `--target collector -- --interval 30` is a collector with a 30-second interval.

The target runs **in this process**: its main() is called with sys.stdout and sys.stderr pointed at a line
writer. One process rather than two means there is no pipe to drain and no child to orphan when Task Scheduler
ends the task, and a crash inside the target is caught here and written to the log with its traceback instead of
disappearing. The exit code the target returns is this process's exit code, so Task Scheduler's Last Run Result
shows the real one.

Growth is bounded, not merely rotated: RotatingFileHandler keeps the live log under --max-bytes (1 MB) and at
most --backups (5) numbered files beside it, so a target left running for months costs at most about 6 MB per
log. The log folder defaults to out/local/logs, which is git-ignored and sits beside the database, and it is
resolved from this file rather than from the working folder, because Task Scheduler may start the process in
System32.

When the log itself cannot be written. The log is diagnostics; the board is the product. So:

- **Once the target is running**, a failed write or rotation (a full disk, an antivirus, backup or sync handle
  on a rotated file, a second wrapper on the same log) never stops it. The line the log could not take goes to
  the fallback file instead, `dispatch-board-<target>-log-failure.txt` in the user's temp folder, with the reason
  written once each time it changes, and on the real stderr as well when there is one (pythonw has none). The
  log is tried again for every line, so a passing obstacle heals by itself, and the first line written after it
  says how many went to the fallback file. The fallback file starts again once it passes 1 MB.
- **If the log cannot be opened at all** when the target starts (a file where the folder should be, a folder
  that cannot be created, a log that cannot be opened), that is the same failure and takes the same path. The
  log and its folder are opened at the first line rather than beforehand, so the target starts, its lines and
  the reason go to the fallback file, and the open is tried again for every line until it succeeds.
- **Only when the fallback file cannot take the start line either** is there no file left to hold the reason.
  Then the process exits with LOG_UNUSABLE (73) without starting the target, with the reason on the real stderr
  when there is one: Task Scheduler records 73 as the Last Run Result, a code neither target uses.

The fallback file is in the temp folder rather than beside the log because the log folder is the one place
that has just been shown not to take writes.
"""
import argparse, importlib, io, logging, logging.handlers, os, sys, tempfile, threading, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(REPO, 'local'),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TARGETS = ('collector', 'server')
MAX_BYTES = 1_000_000
BACKUPS = 5
FALLBACK_MAX_BYTES = 1_000_000
# sysexits.h's EX_CANTCREAT, "cannot create an output file". The collector and the server exit 0, 1 or 2, so
# this cannot be mistaken for anything a target reports.
LOG_UNUSABLE = 73
# Local time to the second, matching the stamp collector.py already puts on its loop-mode reports, so the log
# reads as one stream rather than two clocks.
STAMP = '%Y-%m-%dT%H:%M:%S'


def log_dir(repo=None):
    return os.path.join(repo or REPO, 'out', 'local', 'logs')


def log_path(target, directory=None, repo=None):
    return os.path.join(directory or log_dir(repo), target + '.log')


def fallback_path(target):
    return os.path.join(tempfile.gettempdir(), 'dispatch-board-%s-log-failure.txt' % target)


class Fallback:
    """Where the wrapper writes what the log could not take: the real stderr, when the process has one, and a
    small file of its own. Neither may raise, since each is the last place a reason can go."""

    def __init__(self, path, stream):
        # written: whether the last text reached the file, which is how run() tells that the start line reached
        # no file at all.
        self.path, self.stream, self.written = path, stream, False

    def __call__(self, text):
        if not text.endswith('\n'):
            text += '\n'
        if self.stream is not None:
            try:
                self.stream.write(text)
                self.stream.flush()
            except Exception:
                pass
        try:
            mode = 'w' if os.path.getsize(self.path) > FALLBACK_MAX_BYTES else 'a'
        except OSError:
            mode = 'a'
        try:
            with io.open(self.path, mode, encoding='utf-8') as f:
                f.write(text)
            self.written = True
        except Exception:
            self.written = False

    def line(self, text):
        """A line the log could not take, stamped the way the log would have stamped it. The real stderr is left
        out: a console run already showed it there as it was printed, before the capture."""
        stream, self.stream = self.stream, None
        try:
            self(time.strftime(STAMP) + ' ' + text)
        finally:
            self.stream = stream


class LineWriter(io.TextIOBase):
    """A text stream that hands each complete line to a sink, holding back a partial one until it is finished.

    sys.stdout and sys.stderr are both pointed at one of these, so the log carries the two interleaved in the
    order they were written. Anything written while the sink is already running on this thread - the logging
    module reporting a failure of its own on sys.stderr, which is this writer - goes straight to the fallback,
    as does a line the sink raised on, so a failing sink can never recurse back into itself.
    """

    def __init__(self, sink, fallback=None):
        self.sink, self.fallback, self.buf, self.lock, self.busy = sink, fallback, '', threading.RLock(), False

    def _divert(self, text):
        if self.fallback is not None:
            self.fallback(text)

    def _send(self, line):
        self.busy = True
        try:
            self.sink(line)
        except Exception as e:
            self._divert('%s\nrun_local: the line above could not be logged (%s: %s)\n' % (line, type(e).__name__, e))
        finally:
            self.busy = False

    def write(self, text):
        with self.lock:
            if self.busy:
                self._divert(text)
                return len(text)
            self.buf += text
            while '\n' in self.buf:
                line, self.buf = self.buf.split('\n', 1)
                self._send(line.rstrip('\r'))
        return len(text)

    def flush(self):
        with self.lock:
            if self.buf and not self.busy:
                line, self.buf = self.buf, ''
                self._send(line)

    def writable(self):
        return True

    def isatty(self):
        return False

    @property
    def encoding(self):
        return 'utf-8'


class _Handler(logging.handlers.RotatingFileHandler):
    """The rotating log, with its own failures sent to the fallback rather than to logging's default of printing
    on sys.stderr, which during a run is the captured stream feeding this very handler."""

    def __init__(self, path, max_bytes, backups, fallback):
        # delay: nothing is opened here. The first emit opens the file, inside the try that routes a failure to
        # handleError, so a log that cannot be opened is diverted and retried like one that cannot be written.
        super().__init__(path, maxBytes=max_bytes, backupCount=backups, encoding='utf-8', delay=True)
        self.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt=STAMP))
        self.fallback, self.lost, self.reason = fallback, 0, None

    def _open(self):
        # The folder is made here rather than once up front, so a folder that could not be made at the start is
        # made by the first line after its obstacle goes.
        os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
        return super()._open()

    def handleError(self, record):
        e = sys.exc_info()[1]
        reason = '%s: %s' % (type(e).__name__, e)
        self.lost += 1
        if reason != self.reason:
            self.reason = reason
            self.fallback('%s run_local: %s could not be written (%s); the target keeps running and its lines '
                          'go to %s until the log takes them again' % (time.strftime(STAMP), self.baseFilename,
                                                                     reason, self.fallback.path))
        try:
            self.fallback.line(record.getMessage())
        except Exception:
            pass

    def emit(self, record):
        lost = self.lost
        super().emit(record)
        if self.lost and self.lost == lost:
            note = 'run_local: the log is being written again; %d earlier line(s) went to %s (%s)' % (
                self.lost, self.fallback.path, self.reason)
            self.lost, self.reason = 0, None
            super().emit(logging.makeLogRecord({'msg': note}))


def _entry(target):
    """The target's main(argv). Imported here rather than at module load, so this file can be read and its log
    paths used without pulling in the collector or the server."""
    return importlib.import_module(target).main


def run(target, args=(), log_dir=None, max_bytes=MAX_BYTES, backups=BACKUPS, entry=None, repo=None, fallback=None):
    """Runs one target with its output captured, and returns the exit code it should exit with.

    entry is the target's main(argv); it defaults to the real one and is replaced in the tests, which need to
    drive an exit code, a raise and a Ctrl+C without a real collector behind them. fallback is the fallback
    file's path, fallback_path(target) by default."""
    if target not in TARGETS:
        raise ValueError('unknown target %r; expected one of %s' % (target, ', '.join(TARGETS)))
    args = list(args)
    path = log_path(target, log_dir, repo)
    spare = Fallback(fallback or fallback_path(target), sys.stderr)
    handler = _Handler(path, max_bytes, backups, spare)
    logger = logging.Logger('run_local')  # not getLogger: a private logger leaves no handler in the registry
    logger.addHandler(handler)
    writer = LineWriter(logger.info, spare.line)
    saved = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = writer

    def note(msg):
        writer.write('run_local: ' + msg + '\n')

    try:
        note('starting %s %s' % (target, ' '.join(args)))
        if handler.lost and not spare.written:
            spare('%s run_local: %s not started: neither its log %s nor %s can be written (%s); exiting %d'
                  % (time.strftime(STAMP), target, path, spare.path, handler.reason, LOG_UNUSABLE))
            return LOG_UNUSABLE
        try:
            code = (entry or _entry(target))(args)
            code = 0 if code is None else code
        except KeyboardInterrupt:
            note('%s stopped (Ctrl+C)' % target)
            return 0
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except BaseException:
            writer.write(traceback.format_exc())
            note('%s failed; exited 1' % target)
            return 1
        note('%s exited %d' % (target, code))
        return code
    finally:
        # The streams go back first, so nothing below can leave them pointing at a writer that is being closed.
        sys.stdout, sys.stderr = saved
        try:
            writer.flush()
        finally:
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception as e:
                spare('%s run_local: %s could not be closed (%s: %s)'
                      % (time.strftime(STAMP), path, type(e).__name__, e))


def main(argv=None, entry=None):
    ap = argparse.ArgumentParser(prog='run_local.py', allow_abbrev=False,
                                 description='Run the collector or the local server, capturing its output to a log file.')
    ap.add_argument('--target', required=True, choices=list(TARGETS))
    ap.add_argument('--log-dir', help='where the log goes (default: out/local/logs in this checkout)')
    ap.add_argument('--max-bytes', type=int, default=MAX_BYTES, help='rotate the log past this size (default 1000000)')
    ap.add_argument('--backups', type=int, default=BACKUPS, help='how many rotated logs to keep (default 5)')
    try:
        args, rest = ap.parse_known_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    if rest and rest[0] == '--':
        rest = rest[1:]
    return run(args.target, rest, log_dir=args.log_dir, max_bytes=args.max_bytes, backups=args.backups, entry=entry)


if __name__ == '__main__':
    sys.exit(main())
