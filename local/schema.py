"""The SQLite schema that stores the local-first app's records: one table per record kind, laid out by
records.TABLES, created or completed by create_schema().

Every statement is CREATE ... IF NOT EXISTS, so running the whole list again heals a version-1 file that lost a
table or an index. It cannot repair a table whose columns are wrong; any schema change after version 1 needs
its own reviewed change to this module.
"""
import records

SCHEMA_VERSION = 1
_TYPES = {'id': 'TEXT PRIMARY KEY', 'doc': 'TEXT NOT NULL', 'seq': 'INTEGER', 'ord': 'INTEGER'}  # any other: TEXT
_INDEXES = (  # (name, table, column); sessions(last) is what pruning by age reads
    ('idx_sessions_project', 'sessions', 'project'),
    ('idx_sessions_last', 'sessions', 'last'),
    ('idx_runs_session', 'runs', 'session'),
    ('idx_runs_project', 'runs', 'project'),
    ('idx_project_tabs_project', 'project_tabs', 'project'),
)

# Names go unquoted on purpose. SQLite reads a double-quoted name that matches no column as a string literal, so
# on a foreign table that lacks the column a quoted CREATE INDEX would quietly index a constant and the file would
# still be stamped version 1. Unquoted, it fails with "no such column" and the whole transaction rolls back. Every
# name is a fixed lowercase word, so none needs quoting.
DDL = [
    'CREATE TABLE IF NOT EXISTS %s (%s)' % (table, ', '.join('%s %s' % (c, _TYPES.get(c, 'TEXT')) for c in cols))
    for table, cols in records.TABLES.values()
] + ['CREATE INDEX IF NOT EXISTS %s ON %s (%s)' % index for index in _INDEXES]


def create_schema(conn):
    """Create the tables and indexes in conn's database, or complete them, and set user_version to SCHEMA_VERSION,
    all in one BEGIN IMMEDIATE transaction; on any failure the file is left exactly as it was.

    Raises ValueError when conn is already in a transaction (an autocommit=False connection always is) and
    RuntimeError when the file's user_version is newer than SCHEMA_VERSION.
    """
    if conn.in_transaction:
        raise ValueError('create_schema needs a connection with no open transaction '
                         '(an autocommit=False connection is always in one)')
    # Explicit statements rather than conn.commit() and conn.rollback(), which do nothing on an autocommit=True
    # connection. executescript() is never used: it commits any open transaction first. IMMEDIATE takes the write
    # lock up front, so two processes cannot both upgrade the same file.
    conn.execute('BEGIN IMMEDIATE')
    try:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError('the store is at schema version %d, newer than this code (version %d)'
                               % (version, SCHEMA_VERSION))
        for statement in DDL:
            conn.execute(statement)
        conn.execute('PRAGMA user_version = %d' % SCHEMA_VERSION)
        conn.execute('COMMIT')
    except BaseException:
        # SQLite ends the transaction itself after some errors; a ROLLBACK then would raise and hide the real one.
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
