"""Shared helpers for the collector tests: a throwaway projects root and database, and a spy on the collector's
file reads. Not a test module (its name does not match test*.py), so nothing here is collected twice.

The synthetic transcripts come from tests/test_export_sessions.py, imported as a module for its record builders and
Tree only, so the collector is checked on exactly the transcripts the exporter's own tests use.
"""
import contextlib, io, json, os, sys, tempfile

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(HERE, 'tests'), os.path.join(HERE, 'exporters'), os.path.join(HERE, 'local'),
           os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import board_config  # noqa: E402
import collector  # noqa: E402
import db  # noqa: E402
import export_sessions as es  # noqa: E402
import test_export_sessions as tes  # noqa: E402

KINDS = {'session': 'sessions', 'run': 'runs', 'project': 'projects'}
REAL_OPEN = collector._open


class Env:
    """A tes.Tree projects root plus a database beside it, cleaned up with the test."""

    def __init__(self, case):
        self.t = tes.Tree()
        self.root, self.tmp = self.t.root, self.t.tmp
        self.db_path = os.path.join(self.tmp, 'db', 'board.db')
        self.conns = []
        case.addCleanup(self.cleanup)
        self.conn = self.connect()
        self.out = self.err = ''
        self.configured = set()

    def connect(self):
        """A new connection with no in-memory cache: what a restarted collector has."""
        collector.forget()
        with contextlib.redirect_stderr(io.StringIO()):
            conn = db.open_db(self.db_path)
        self.conns.append(conn)
        return conn

    def reconnect(self):
        self.conn.close()
        self.conn = self.connect()

    def cfg(self, build=(), **sessions):
        c = tes.config(build, **sessions)
        c['catalogue'] = {'marketplacePath': os.path.join(self.tmp, 'no-marketplace'),
                          'installedPath': os.path.join(self.tmp, 'no-installed.json')}
        return c

    def seen(self, cfg):
        """Remember the statusDoc of every project this config names, read through the loader the pass itself
        uses, so a test can say which status records a pass was ever entitled to write. A config the loader
        refuses names no project a pass could write for, and the pass refuses it too."""
        try:
            self.configured |= {p['statusDoc'] for p in board_config.projects(cfg)}
        except ValueError:
            pass
        return cfg

    def run(self, cfg=None, now=None, conn=None, **kw):
        out, err = io.StringIO(), io.StringIO()
        cfg = self.seen(cfg or self.cfg())
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                return collector.run_pass(conn or self.conn, cfg, projects_root=self.root, now=now, **kw)
        finally:
            self.out, self.err = out.getvalue(), err.getvalue()

    def main(self, argv, cfg=None, now=None, db_path=None):
        out, err = io.StringIO(), io.StringIO()
        cfg = self.seen(cfg or self.cfg())
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = collector.main(argv, config=cfg, db_path=db_path or self.db_path,
                                  projects_root=self.root, now=now)
        self.out, self.err = out.getvalue(), err.getvalue()
        return code

    def exported(self, cfg=None, now=None, root=None):
        """The session exporter's documents for the same transcripts, config and now: {kind: {id: doc}}."""
        out = tempfile.mkdtemp(prefix='exported-', dir=self.tmp)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = es.main(cfg or self.cfg(), out, root or self.root, now)
        assert code == 0, err.getvalue()
        return {kind: docs(out, coll) for kind, coll in KINDS.items()}

    def stored(self, conn=None):
        return {kind: db.stored(conn or self.conn, kind) for kind in KINDS}

    def state(self, conn=None):
        """The raw state rows: ({sid: text}, {(sid, aid): text}, [(dev, ino, size, rule)])."""
        c = conn or self.conn
        return (dict(c.execute('SELECT id, data FROM collector_sessions')),
                {(s, a): d for s, a, d in c.execute('SELECT session, agent, data FROM collector_agents')},
                sorted(c.execute('SELECT dev, ino, size, rule FROM collector_excluded')))

    def session_state(self, sid):
        row = self.conn.execute('SELECT data FROM collector_sessions WHERE id = ?', (sid,)).fetchone()
        return collector.decode(row[0]) if row else None

    def last_refresh(self):
        row = self.conn.execute("SELECT doc FROM last_refresh WHERE id = 'lastRefresh'").fetchone()
        return row and row[0]

    def main_path(self, sid, folder=tes.FOLDER):
        return os.path.join(self.root, folder, sid + '.jsonl')

    def agent_path(self, sid, aid, folder=tes.FOLDER):
        return os.path.join(self.root, folder, sid, 'subagents', 'agent-%s.jsonl' % aid)

    def cleanup(self):
        for c in self.conns:
            c.close()
        collector.forget()
        self.t.cleanup()


def line(rec):
    return (rec if isinstance(rec, str) else json.dumps(rec)) + '\n'


def append(path, recs, newline=True):
    """Append records to a transcript; the bytes written."""
    data = ''.join(line(r) for r in recs)
    if not newline:
        data = data[:-1]
    raw = data.encode('utf-8')
    with open(path, 'ab') as f:
        f.write(raw)
    return raw


def docs(out, coll):
    d, found = os.path.join(out, coll), {}
    for f in (os.listdir(d) if os.path.isdir(d) else []):
        with io.open(os.path.join(d, f), encoding='utf-8') as fh:
            found[f[:-len('.json')]] = json.load(fh)
    return found


class Spy:
    """Stands in for collector._open and records, per open, the path, every seek and the bytes read."""

    def __init__(self):
        self.calls = []

    def __call__(self, path):
        rec = {'path': os.path.normcase(os.path.abspath(path)), 'seeks': [], 'data': b''}
        self.calls.append(rec)
        return _SpyFile(REAL_OPEN(path), rec)

    def of(self, path):
        p = os.path.normcase(os.path.abspath(path))
        return [c for c in self.calls if c['path'] == p]


class _SpyFile:
    def __init__(self, f, rec):
        self.f, self.rec = f, rec

    def seek(self, n, *a):
        self.rec['seeks'].append(n)
        return self.f.seek(n, *a)

    def read(self, *a):
        data = self.f.read(*a)
        self.rec['data'] += data
        return data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.f.close()

    def close(self):
        self.f.close()
