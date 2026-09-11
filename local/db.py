"""The local-first app's SQLite database: opening it safely, the collector's state tables, the record write helpers
and a change watcher for the server.

open_db() refuses a network path before touching it, refuses a file it would have to modify to use (a newer schema,
a records table with other columns, a file that is not a database, no WAL) before modifying it, and otherwise
leaves the file in WAL mode with the records schema and the collector's three state tables.

The state tables (collector_*) are the collector's private cache of how far it has read each transcript. They are
not records: they sit outside records.TABLES and user_version, and the server ignores them.
"""
import os, sqlite3, sys

import records
import schema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 10  # seconds another connection's write lock is waited for
WINDOWS = sys.platform == 'win32'
DRIVE_REMOTE = 4  # GetDriveTypeW's value for a mapped network drive

# dev and ino are the decimal text of os.stat's values: a Windows file id can pass SQLite's signed 64-bit INTEGER.
STATE_TABLES = {
    'collector_sessions': (('id', 'data'), 'id TEXT PRIMARY KEY, data TEXT NOT NULL'),
    'collector_agents': (('session', 'agent', 'data'),
                         'session TEXT NOT NULL, agent TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY (session, agent)'),
    'collector_excluded': (('dev', 'ino', 'size', 'rule'),
                           'dev TEXT NOT NULL, ino TEXT NOT NULL, size INTEGER NOT NULL, rule TEXT NOT NULL, '
                           'PRIMARY KEY (dev, ino)'),
}


class NetworkPath(Exception):
    """The database path is on a network share or a mapped network drive, where SQLite's locking is unsafe."""

    def __init__(self, path):
        super().__init__('the database path %s is a network path' % path)
        self.path = path


class Refused(Exception):
    """The file at the database path cannot be used as it is, and was not changed."""


def warn(msg):
    print('collector: ' + msg, file=sys.stderr)


def resolve(path, root=None):
    """The absolute form of a configured path; a relative one is taken from the repository root, never the working
    folder, since a scheduled start may run from anywhere."""
    return os.path.abspath(os.path.join(root or REPO, path))


def drive_type(root):
    import ctypes
    return ctypes.windll.kernel32.GetDriveTypeW(root)


def _unc(path):
    return path.startswith(('\\\\', '//'))


def _remote_drive(path):
    drive = os.path.splitdrive(path)[0]
    return WINDOWS and len(drive) == 2 and drive[1] == ':' and drive_type(drive + '\\') == DRIVE_REMOTE


def network_path(path, root=None):
    """True for a path on a share. The checks run cheapest first and stop at the first hit: the configured text,
    its absolute form, its drive letter, then its real path (which follows links, and may ask Windows about the
    server a link leads to). A \\\\?\\ path is refused too, even a local one: it fails safe."""
    if _unc(path):
        return True
    full = resolve(path, root)
    if _unc(full) or _remote_drive(full):
        return True
    real = os.path.realpath(full)
    return _unc(real) or _remote_drive(real)


def _columns(conn, table):
    return tuple(r[1] for r in conn.execute('PRAGMA table_info(%s)' % table))


def _check_records(conn, path, missing_ok):
    for table, cols in records.TABLES.values():
        got = _columns(conn, table)
        if (got or not missing_ok) and got != cols:
            raise Refused('%s: table %s(%s) does not have the columns (%s); refusing to use this file'
                          % (path, table, ', '.join(got), ', '.join(cols)))


def _state_tables(conn, warn):
    conn.execute('BEGIN IMMEDIATE')
    try:
        wrong = [(t, got) for t, (cols, _) in STATE_TABLES.items() for got in [_columns(conn, t)] if got and got != cols]
        for table, got in wrong:
            warn('state table %s had columns (%s); all three state tables dropped and recreated, so every transcript '
                 'is read again from the start' % (table, ', '.join(got)))
        if wrong:  # all three together, so no cursor or marker survives to skip a read
            for table in STATE_TABLES:
                conn.execute('DROP TABLE IF EXISTS %s' % table)
        for table, (_, ddl) in STATE_TABLES.items():
            conn.execute('CREATE TABLE IF NOT EXISTS %s (%s)' % (table, ddl))
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise


def _locked(e):
    return isinstance(e, sqlite3.OperationalError) and 'locked' in str(e)


def open_db(path, root=None, warn=warn):
    """A connection to the database at path (relative to the repository root), ready for the collector: WAL mode,
    the records schema and the state tables, every table's columns checked. Raises NetworkPath, Refused, or
    sqlite3.OperationalError when another connection holds the lock."""
    if network_path(path, root):
        raise NetworkPath(path)
    full = resolve(path, root)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    conn = None
    try:
        # Inside the try: a path SQLite cannot open (a folder, no permission) is refused like any other unusable file.
        conn = sqlite3.connect(full, isolation_level=None, timeout=TIMEOUT)
        # Reads only, so a file refused here is left exactly as it was.
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version > schema.SCHEMA_VERSION:
            raise Refused('%s is at schema version %d, newer than this code (version %d); refusing to use it'
                          % (full, version, schema.SCHEMA_VERSION))
        _check_records(conn, full, missing_ok=True)
        mode = conn.execute('PRAGMA journal_mode=WAL').fetchone()[0]
        if str(mode).lower() != 'wal':
            raise Refused('%s: the journal mode is %s, not wal; refusing to use it' % (full, mode))
        conn.execute('PRAGMA synchronous=NORMAL')
        try:
            schema.create_schema(conn)
        except RuntimeError as e:
            raise Refused('%s: %s' % (full, e)) from e
        _state_tables(conn, warn)
        _check_records(conn, full, missing_ok=False)
        for table, (cols, _) in STATE_TABLES.items():
            got = _columns(conn, table)
            if got != cols:
                raise Refused('%s: table %s(%s) does not have the columns (%s)' % (full, table, ', '.join(got), ', '.join(cols)))
    except BaseException as e:
        if conn is not None:
            conn.close()
        if isinstance(e, sqlite3.DatabaseError) and not _locked(e):
            raise Refused('%s cannot be used as the database (%s: %s)' % (full, type(e).__name__, e)) from e
        raise
    return conn


def upsert(conn, kind, row):
    """Insert or replace one record from records.to_row(kind, ...)."""
    table, cols = records.TABLES[kind]
    conn.execute('INSERT INTO %s (%s) VALUES (%s) ON CONFLICT(id) DO UPDATE SET %s' % (
        table, ', '.join(cols), ', '.join('?' * len(cols)), ', '.join('%s=excluded.%s' % (c, c) for c in cols[1:])),
        [row[c] for c in cols])


def delete(conn, kind, record_id):
    conn.execute('DELETE FROM %s WHERE id = ?' % records.TABLES[kind][0], (record_id,))


def stored(conn, kind):
    """{id: document} for every stored record of this kind."""
    return {rid: records.from_row(kind, doc)
            for rid, doc in conn.execute('SELECT id, doc FROM %s ORDER BY id' % records.TABLES[kind][0])}


class Changes:
    """Tells a reader when another connection has committed. poll() is False the first time, then True once for
    every poll that follows another connection's commit. Poll outside any open read transaction."""

    def __init__(self, conn):
        self.conn, self.version = conn, None

    def poll(self):
        version = self.conn.execute('PRAGMA data_version').fetchone()[0]
        changed = self.version is not None and version != self.version
        self.version = version
        return changed
