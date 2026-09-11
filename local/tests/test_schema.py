"""Tests for local/schema.py: the tables and indexes create_schema() makes, its user_version handling, and
that it leaves the file exactly as it was on any failure. Every database is a file in a temporary folder.
"""
import io, os, shutil, sqlite3, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, 'local'))
import records  # noqa: E402
import schema  # noqa: E402

TABLES = {'sessions', 'runs', 'projects', 'project_tabs', 'statuses', 'last_refresh', 'catalogue'}
INDEXES = {  # name -> (table, columns)
    'idx_sessions_project': ('sessions', ['project']),
    'idx_sessions_last': ('sessions', ['last']),
    'idx_runs_session': ('runs', ['session']),
    'idx_runs_project': ('runs', ['project']),
    'idx_project_tabs_project': ('project_tabs', ['project']),
}
BROKEN = 'CREATE TABLE broken ('  # a syntax error, so the statement fails after the real ones have run
MODES = {'default': {}, 'isolation_level=None': {'isolation_level': None}, 'autocommit=True': {'autocommit': True}}


class SchemaCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='schema-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, 'store.db')

    def connect(self, **kw):
        conn = sqlite3.connect(self.path, **kw)
        self.addCleanup(conn.close)  # runs before the folder is removed: cleanups run last-in, first-out
        return conn

    def state(self):
        """What a fresh connection sees on disk: user_version, table names and named index names."""
        conn = sqlite3.connect(self.path)
        try:
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            rows = conn.execute('SELECT type, name FROM sqlite_master').fetchall()
        finally:
            conn.close()
        tables = {n for t, n in rows if t == 'table'}
        indexes = {n for t, n in rows if t == 'index' and not n.startswith('sqlite_autoindex_')}
        return version, tables, indexes

    def raw(self):
        with io.open(self.path, 'rb') as f:
            return f.read()


class Create(SchemaCase):
    def test_creates_the_tables_and_named_indexes_at_version_1(self):
        conn = self.connect()
        schema.create_schema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertEqual(schema.SCHEMA_VERSION, 1)
        self.assertEqual(self.state(), (1, TABLES, set(INDEXES)))

    def test_twice_is_idempotent(self):
        conn = self.connect()
        schema.create_schema(conn)
        first = self.state()
        schema.create_schema(conn)
        self.assertEqual(self.state(), first)
        self.assertFalse(conn.in_transaction)

    def test_indexes_are_on_the_right_columns(self):
        conn = self.connect()
        schema.create_schema(conn)
        for name, (table, cols) in INDEXES.items():
            with self.subTest(index=name):
                self.assertEqual(conn.execute('SELECT tbl_name FROM sqlite_master WHERE name = ?', (name,)).fetchone()[0], table)
                self.assertEqual([r[2] for r in conn.execute('PRAGMA index_info("%s")' % name)], cols)

    def test_columns_follow_tables(self):
        conn = self.connect()
        schema.create_schema(conn)
        for kind, (table, cols) in records.TABLES.items():
            with self.subTest(table=table):
                info = {r[1]: r for r in conn.execute('PRAGMA table_info("%s")' % table)}
                self.assertEqual(list(info), list(cols))
                self.assertEqual(info['id'][5], 1)   # the primary key
                self.assertEqual(info['id'][2], 'TEXT')
                self.assertEqual(info['doc'][3], 1)  # NOT NULL
                self.assertEqual(info['doc'][2], 'TEXT')

    def test_no_answers_table(self):
        conn = self.connect()
        schema.create_schema(conn)
        names = {r[0] for r in conn.execute('SELECT name FROM sqlite_master')}
        self.assertFalse([n for n in names if 'answer' in n.lower()])
        self.assertFalse([s for s in schema.DDL if 'answer' in s.lower()])

    def test_ddl_is_create_if_not_exists_only(self):
        for stmt in schema.DDL:
            self.assertRegex(stmt, r'^CREATE (TABLE|INDEX) IF NOT EXISTS ')

    def test_ddl_names_are_plain_and_unquoted(self):
        names = set(INDEXES) | {t for t, _ in records.TABLES.values()} | {c for _, cols in records.TABLES.values() for c in cols}
        for name in sorted(names):
            self.assertRegex(name, r'\A[a-z_]+\Z')
        for stmt in schema.DDL:
            self.assertNotIn('"', stmt)

    def test_works_in_every_connection_mode(self):
        for mode, kw in MODES.items():
            with self.subTest(mode=mode):
                if os.path.exists(self.path):
                    os.remove(self.path)
                conn = sqlite3.connect(self.path, **kw)
                try:
                    schema.create_schema(conn)
                    self.assertFalse(conn.in_transaction)
                finally:
                    conn.close()
                self.assertEqual(self.state(), (1, TABLES, set(INDEXES)))


class Versions(SchemaCase):
    def test_a_newer_version_raises_and_leaves_the_file_unchanged(self):
        conn = self.connect()
        conn.execute('CREATE TABLE keep (x)')
        conn.execute('PRAGMA user_version = 2')
        before = self.raw()
        with self.assertRaises(RuntimeError):
            schema.create_schema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertEqual(self.state(), (2, {'keep'}, set()))
        self.assertEqual(self.raw(), before)

    def test_a_foreign_runs_table_raises_and_leaves_the_file_unchanged(self):
        conn = self.connect()
        conn.execute('CREATE TABLE runs (x)')
        before = self.raw()
        with self.assertRaises(sqlite3.OperationalError) as cm:
            schema.create_schema(conn)
        self.assertIn('no such column', str(cm.exception))
        self.assertFalse(conn.in_transaction)
        self.assertEqual(self.state(), (0, {'runs'}, set()))
        self.assertEqual(self.raw(), before)

    def test_a_partial_version_1_file_heals(self):
        conn = self.connect()
        schema.create_schema(conn)
        conn.execute('DROP TABLE runs')
        conn.execute('DROP INDEX idx_sessions_last')
        self.assertEqual(self.state()[0], 1)
        self.assertNotIn('runs', self.state()[1])
        schema.create_schema(conn)
        self.assertEqual(self.state(), (1, TABLES, set(INDEXES)))


class Transactions(SchemaCase):
    def test_a_connection_already_in_a_transaction_raises(self):
        conn = self.connect()
        conn.execute('BEGIN')
        with self.assertRaises(ValueError):
            schema.create_schema(conn)
        self.assertTrue(conn.in_transaction)  # the caller's transaction is left alone
        conn.execute('ROLLBACK')
        self.assertEqual(self.state(), (0, set(), set()))

    @unittest.skipUnless(sys.version_info >= (3, 12), 'the autocommit argument needs Python 3.12')
    def test_an_autocommit_false_connection_raises(self):
        conn = self.connect(autocommit=False)
        with self.assertRaises(ValueError):
            schema.create_schema(conn)
        conn.rollback()
        self.assertEqual(self.state(), (0, set(), set()))

    @unittest.skipUnless(sys.version_info >= (3, 12), 'the autocommit argument needs Python 3.12')
    def test_autocommit_true_commits_the_schema(self):
        conn = self.connect(autocommit=True)
        schema.create_schema(conn)
        self.assertFalse(conn.in_transaction)
        conn.close()
        self.assertEqual(self.state(), (1, TABLES, set(INDEXES)))

    def test_a_failing_statement_leaves_the_file_as_it_was_in_every_mode(self):
        for mode, kw in MODES.items():
            if 'autocommit' in kw and sys.version_info < (3, 12):
                continue
            with self.subTest(mode=mode):
                if os.path.exists(self.path):
                    os.remove(self.path)
                conn = sqlite3.connect(self.path, **kw)
                try:
                    before = self.raw()
                    with mock.patch.object(schema, 'DDL', schema.DDL + [BROKEN]):
                        with self.assertRaises(sqlite3.OperationalError):
                            schema.create_schema(conn)
                    self.assertFalse(conn.in_transaction)
                finally:
                    conn.close()
                self.assertEqual(self.state(), (0, set(), set()))
                self.assertEqual(self.raw(), before)

    def test_a_failure_while_healing_keeps_the_version_1_file(self):
        conn = self.connect()
        schema.create_schema(conn)
        conn.execute('DROP TABLE runs')
        before_state, before = self.state(), self.raw()
        with mock.patch.object(schema, 'DDL', schema.DDL + [BROKEN]):
            with self.assertRaises(sqlite3.OperationalError):
                schema.create_schema(conn)
        self.assertFalse(conn.in_transaction)
        self.assertEqual(self.state(), before_state)
        self.assertEqual(self.raw(), before)


class RowsInTheStore(SchemaCase):
    """to_row's column dict inserts as-is, and from_row reads a sqlite3.Row back to the same document."""

    DOCS = {
        'session': ('sid-1', {'title': 't', 'folder': 'f', 'cwd': 'c', 'start': None, 'last': '2026-09-11T10:00:00Z',
                              'project': 'alpha', 'build': False, 'windowDays': 7, 'windowMinutes': 10, 'runs': 0,
                              'running': 0, 'usage': {}, 'skillUses': {}}),
        'run': ('a1', {'session': 'sid-1', 'project': 'alpha', 'seq': 1, 'lane': 'orch', 'label': 'l', 'kind': 'done',
                       'verdict': '', 'tok': 0, 'min': 0}),
        'project': ('alpha', {'name': 'Alpha', 'repoPath': '', 'branch': '', 'sessions': ['sid-1'], 'statusDoc': 'meta/status',
                              'order': 2, 'runs': 1, 'running': 0, 'last': None, 'usage': None}),
        'tab': ('alpha.git', {'generatedAt': '2026-09-11T12:00:00+00:00', 'source': 'git, local repository', 'head': 'abc'}),
        'status': ('meta/status', {'live': False, 'updatedAt': '2026-09-11T12:00:00+00:00'}),
        'lastRefresh': ('lastRefresh', {'at': '2026-09-11T12:00:00Z', 'writer': 'refresher'}),
        'catalogue': ('index', {'generatedAt': '2026-09-11T12:00:00+00:00', 'plugins': [], 'entries': []}),
    }

    def test_every_kind_round_trips_through_its_table(self):
        conn = self.connect()
        schema.create_schema(conn)
        conn.row_factory = sqlite3.Row
        for kind, (rid, d) in self.DOCS.items():
            with self.subTest(kind=kind):
                table, cols = records.TABLES[kind]
                row = records.to_row(kind, rid, d)
                conn.execute('INSERT INTO "%s" (%s) VALUES (%s)' % (
                    table, ', '.join('"%s"' % c for c in cols), ', '.join(':' + c for c in cols)), row)
                back = conn.execute('SELECT * FROM "%s" WHERE id = ?' % table, (rid,)).fetchone()
                self.assertEqual(dict(zip(back.keys(), back)), row)
                self.assertEqual(records.from_row(kind, back), d)
        conn.commit()
        self.assertEqual(conn.execute("SELECT project, tab FROM project_tabs WHERE id = 'alpha.git'").fetchone()[:], ('alpha', 'git'))
        self.assertEqual(conn.execute("SELECT ord FROM projects WHERE id = 'alpha'").fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
