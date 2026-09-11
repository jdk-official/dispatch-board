"""local/db.py: opening the database (network-path guard, read-only pre-check, WAL, schema, state tables,
re-check), the write helpers and the Changes watcher. Every file lives in a temporary folder."""
import contextlib, io, os, shutil, sqlite3, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
sys.path.insert(0, os.path.join(HERE, 'local'))
import db  # noqa: E402
import records  # noqa: E402
import schema  # noqa: E402

STATE = ('collector_sessions', 'collector_agents', 'collector_excluded')
UNC = ('\\\\nas\\share\\board.db', '//nas/share/board.db', '\\\\?\\UNC\\nas\\share\\board.db', '\\\\?\\C:\\x\\board.db')


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def snapshot(path):
    """The bytes, journal mode, table list and user_version of a file, read without changing it."""
    with open(path, 'rb') as f:
        raw = f.read()
    c = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True)
    try:
        mode = 'wal' if raw[18:20] == b'\x02\x02' else 'rollback'
        return raw, mode, sorted(tables(c)), c.execute('PRAGMA user_version').fetchone()[0]
    finally:
        c.close()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='db-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, 'sub', 'board.db')
        self.conns = []

    def open(self, path=None, **kw):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            conn = db.open_db(path or self.path, **kw)
        self.conns.append(conn)
        self.addCleanup(conn.close)
        self.err = err.getvalue()
        return conn


class Open(Base):
    def test_a_fresh_file_opens_in_wal_with_every_table_and_version_1(self):
        conn = self.open()
        self.assertEqual(conn.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0], schema.SCHEMA_VERSION)
        want = {t for t, _ in records.TABLES.values()} | set(STATE)
        self.assertLessEqual(want, tables(conn))
        self.assertFalse(conn.in_transaction)

    def test_state_table_columns_and_text_keys(self):
        conn = self.open()
        cols = {t: [(r[1], r[2]) for r in conn.execute('PRAGMA table_info(%s)' % t)] for t in STATE}
        self.assertEqual(cols['collector_sessions'], [('id', 'TEXT'), ('data', 'TEXT')])
        self.assertEqual(cols['collector_agents'], [('session', 'TEXT'), ('agent', 'TEXT'), ('data', 'TEXT')])
        self.assertEqual(cols['collector_excluded'], [('dev', 'TEXT'), ('ino', 'TEXT'), ('size', 'INTEGER'), ('rule', 'TEXT')])

    def test_opening_again_keeps_the_rows(self):
        conn = self.open()
        conn.execute("INSERT INTO collector_sessions VALUES ('s', '{}')")
        conn.close()
        self.assertEqual(self.open().execute('SELECT id FROM collector_sessions').fetchall(), [('s',)])

    def test_a_relative_path_resolves_against_the_repository_root(self):
        self.assertEqual(db.resolve('out/local/board.db'), os.path.join(HERE, 'out', 'local', 'board.db'))
        cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            self.assertEqual(db.resolve('out/local/board.db'), os.path.join(HERE, 'out', 'local', 'board.db'))
            root = os.path.join(self.tmp, 'repo')
            conn = self.open('data/board.db', root=root)
            self.assertTrue(os.path.isfile(os.path.join(root, 'data', 'board.db')))
            self.assertFalse(os.path.exists(os.path.join(self.tmp, 'data')))
            conn.close()
        finally:
            os.chdir(cwd)

    def test_healing_adds_a_missing_records_table(self):
        conn = self.open()
        conn.execute('DROP TABLE statuses')
        conn.close()
        self.assertIn('statuses', tables(self.open()))


class NetworkPath(Base):
    def test_unc_and_extended_paths_are_refused_before_anything_is_created(self):
        for p in UNC:
            with self.subTest(path=p):
                self.assertTrue(db.network_path(p))
                with mock.patch('os.makedirs') as mk, mock.patch('sqlite3.connect') as connect:
                    with self.assertRaises(db.NetworkPath) as cm:
                        db.open_db(p)
                self.assertIn(p, str(cm.exception))
                self.assertEqual(cm.exception.path, p)
                mk.assert_not_called()
                connect.assert_not_called()

    def test_a_relative_path_under_a_unc_root_is_refused(self):
        self.assertTrue(db.network_path('board.db', root='\\\\nas\\share\\repo'))

    def test_a_link_into_a_share_is_refused(self):
        p = os.path.join(self.tmp, 'link', 'board.db')
        with mock.patch('os.path.realpath', return_value='\\\\nas\\share\\board.db'):
            self.assertTrue(db.network_path(p))
            with self.assertRaises(db.NetworkPath):
                db.open_db(p)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'link')))

    def test_a_mapped_network_drive_is_refused(self):
        types = lambda root: db.DRIVE_REMOTE if root.upper() == 'Z:\\' else 3
        with mock.patch.object(db, 'WINDOWS', True), mock.patch.object(db, 'drive_type', side_effect=types):
            self.assertTrue(db.network_path('Z:\\board\\board.db'))
            with mock.patch('os.makedirs') as mk, self.assertRaises(db.NetworkPath):
                db.open_db('Z:\\board\\board.db')
            mk.assert_not_called()
            self.assertFalse(db.network_path(self.path))

    def test_a_plain_local_path_is_accepted(self):
        self.assertFalse(db.network_path(self.path))
        self.open()

    def test_the_checks_stop_at_the_first_hit(self):
        real = os.path.realpath
        with mock.patch.object(db, 'WINDOWS', True), \
                mock.patch.object(db, 'drive_type', side_effect=lambda r: db.DRIVE_REMOTE if r.upper() == 'Z:\\' else 3) as dt, \
                mock.patch('os.path.realpath', side_effect=real) as rp:
            for p in UNC:
                self.assertTrue(db.network_path(p))
            self.assertEqual((dt.call_count, rp.call_count), (0, 0))
            self.assertTrue(db.network_path('Z:\\board.db'))
            self.assertEqual(rp.call_count, 0)
            self.assertEqual(dt.call_count, 1)


class Refusals(Base):
    def foreign(self, version=None, statuses_x=False):
        os.makedirs(os.path.dirname(self.path))
        c = sqlite3.connect(self.path, isolation_level=None)
        if statuses_x:
            c.execute('CREATE TABLE statuses (x)')
            c.execute("INSERT INTO statuses VALUES ('keep')")
        else:
            c.execute('CREATE TABLE other (a)')
        if version is not None:
            c.execute('PRAGMA user_version = %d' % version)
        c.close()
        return snapshot(self.path)

    def assert_unmodified(self, before):
        self.assertEqual(snapshot(self.path), before)
        self.assertEqual(before[1], 'rollback')
        for suffix in ('-wal', '-shm'):
            self.assertFalse(os.path.exists(self.path + suffix))

    def test_a_newer_user_version_is_refused_and_left_unmodified(self):
        before = self.foreign(version=schema.SCHEMA_VERSION + 1)
        with self.assertRaises(db.Refused) as cm:
            db.open_db(self.path)
        self.assertIn(str(schema.SCHEMA_VERSION + 1), str(cm.exception))
        self.assertIn(self.path, str(cm.exception))
        self.assert_unmodified(before)

    def test_a_records_table_with_other_columns_is_refused_and_left_unmodified(self):
        before = self.foreign(statuses_x=True)
        with self.assertRaises(db.Refused) as cm:
            db.open_db(self.path)
        self.assertIn('statuses(x)', str(cm.exception))
        self.assert_unmodified(before)

    def test_a_file_that_is_not_a_database_is_refused_with_its_bytes_unchanged(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'wb') as f:
            f.write(b'these are my notes, not a database\n' * 3)
        with open(self.path, 'rb') as f:
            before = f.read()
        with self.assertRaises(db.Refused) as cm:
            db.open_db(self.path)
        self.assertIn(self.path, str(cm.exception))
        with open(self.path, 'rb') as f:
            self.assertEqual(f.read(), before)
        for suffix in ('-wal', '-shm', '-journal'):
            self.assertFalse(os.path.exists(self.path + suffix))

    def test_a_path_sqlite_cannot_open_is_refused(self):
        os.makedirs(self.path)  # a folder where the database file belongs
        with self.assertRaises(db.Refused) as cm:
            db.open_db(self.path)
        self.assertIn(self.path, str(cm.exception))
        self.assertIn('cannot be used as the database', str(cm.exception))
        self.assertEqual(os.listdir(self.path), [])

    def test_a_journal_mode_other_than_wal_is_refused(self):
        real = sqlite3.connect

        class NoWal:
            def __init__(self, c):
                self.c = c

            def execute(self, sql, *a):
                if sql.upper().startswith('PRAGMA JOURNAL_MODE'):
                    return self.c.execute('PRAGMA journal_mode')
                return self.c.execute(sql, *a)

            def __getattr__(self, name):
                return getattr(self.c, name)

        opened = []
        with mock.patch('sqlite3.connect', side_effect=lambda *a, **k: opened.append(NoWal(real(*a, **k))) or opened[-1]):
            with self.assertRaises(db.Refused) as cm:
                db.open_db(self.path)
        self.assertIn('journal mode', str(cm.exception))
        self.assertIn('delete', str(cm.exception))

    def test_a_create_schema_runtime_error_becomes_refused(self):
        with mock.patch.object(schema, 'create_schema', side_effect=RuntimeError('newer')):
            with self.assertRaises(db.Refused):
                db.open_db(self.path)

    def test_the_re_check_refuses_a_records_table_wrong_after_create_schema(self):
        def broken(conn):  # every table right except statuses, as a racing writer or a defect could leave it
            conn.execute('CREATE TABLE statuses (x)')
            for statement in schema.DDL:
                if 'statuses' not in statement:
                    conn.execute(statement)
        with mock.patch.object(schema, 'create_schema', side_effect=broken):
            with self.assertRaises(db.Refused) as cm:
                db.open_db(self.path)
        self.assertIn('statuses(x)', str(cm.exception))

    def test_a_locked_database_stays_the_lock_error(self):
        self.open().close()
        other = sqlite3.connect(self.path, isolation_level=None)
        self.addCleanup(other.close)
        other.execute('BEGIN IMMEDIATE')
        with mock.patch.object(db, 'TIMEOUT', 0.05):
            with self.assertRaises(sqlite3.OperationalError) as cm:
                db.open_db(self.path)
        self.assertNotIsInstance(cm.exception, db.Refused)
        self.assertIn('locked', str(cm.exception))
        other.execute('ROLLBACK')


class StateTables(Base):
    def test_a_wrong_state_table_drops_and_recreates_all_three(self):
        conn = self.open()
        conn.execute("INSERT INTO collector_sessions VALUES ('s', '{}')")
        conn.execute("INSERT INTO collector_agents VALUES ('s', 'a', '{}')")
        conn.execute("INSERT INTO collector_excluded VALUES ('1', '2', 3, 'r')")
        conn.execute('DROP TABLE collector_excluded')
        conn.execute('CREATE TABLE collector_excluded (dev, ino)')
        conn.execute("INSERT INTO collector_excluded VALUES ('1', '2')")
        conn.close()
        conn = self.open()
        self.assertIn('state table collector_excluded had columns (dev, ino)', self.err)
        self.assertIn('all three state tables dropped and recreated', self.err)
        for t in STATE:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0], 0, t)
        self.assertEqual([r[1] for r in conn.execute('PRAGMA table_info(collector_excluded)')], ['dev', 'ino', 'size', 'rule'])

    def test_right_state_tables_are_kept_with_no_warning(self):
        conn = self.open()
        conn.execute("INSERT INTO collector_agents VALUES ('s', 'a', '{}')")
        conn.close()
        conn = self.open()
        self.assertEqual(self.err, '')
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM collector_agents').fetchone()[0], 1)


class Helpers(Base):
    DOCS = {
        'session': ('s1', {'title': 't', 'folder': 'f', 'cwd': 'c', 'start': None, 'last': None, 'project': None,
                           'build': False, 'windowDays': 7, 'windowMinutes': 10, 'runs': 0, 'running': 0,
                           'usage': {}, 'skillUses': {}}),
        'run': ('r1', {'session': 's1', 'project': None, 'seq': 1, 'lane': 'cw', 'label': 'l', 'kind': 'done',
                       'verdict': 'v', 'tok': 1, 'min': 1}),
        'project': ('p1', {'name': 'n', 'repoPath': '', 'branch': '', 'sessions': [], 'statusDoc': 'status/p1',
                           'order': 0, 'runs': 0, 'running': 0, 'last': None, 'usage': None}),
        'catalogue': ('index', {'generatedAt': 'x', 'plugins': [], 'entries': []}),
        'lastRefresh': ('lastRefresh', {'at': '2026-09-11T12:00:00+00:00', 'writer': 'collector'}),
    }

    def test_upsert_then_stored_round_trips_each_kind_and_updates_in_place(self):
        conn = self.open()
        for kind, (rid, doc) in self.DOCS.items():
            db.upsert(conn, kind, records.to_row(kind, rid, doc))
            self.assertEqual(db.stored(conn, kind), {rid: doc})
            changed = dict(doc, **({'label': 'm'} if kind == 'run' else {'generatedAt': 'y'} if kind == 'catalogue' else {}))
            db.upsert(conn, kind, records.to_row(kind, rid, changed))
            self.assertEqual(db.stored(conn, kind), {rid: changed})
            db.delete(conn, kind, rid)
            self.assertEqual(db.stored(conn, kind), {})

    def test_a_lone_surrogate_in_a_savepoint_raises_and_leaves_the_transaction_usable(self):
        conn = self.open()
        rid, doc = self.DOCS['run']
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('SAVEPOINT rec')
        with self.assertRaises(UnicodeEncodeError):
            db.upsert(conn, 'run', records.to_row('run', rid, dict(doc, label='\ud800')))
        conn.execute('ROLLBACK TO rec')
        conn.execute('RELEASE rec')
        db.upsert(conn, 'run', records.to_row('run', rid, doc))
        conn.execute('COMMIT')
        self.assertEqual(db.stored(conn, 'run'), {rid: doc})


class Changes(Base):
    def test_poll(self):
        writer = self.open()
        reader = sqlite3.connect(self.path, isolation_level=None)
        self.addCleanup(reader.close)
        watch = db.Changes(reader)
        self.assertFalse(watch.poll())
        self.assertFalse(watch.poll())
        writer.execute('BEGIN IMMEDIATE')
        writer.execute("INSERT INTO collector_sessions VALUES ('s', '{}')")
        writer.execute('COMMIT')
        self.assertTrue(watch.poll())
        self.assertFalse(watch.poll())
        writer.execute('BEGIN IMMEDIATE')
        writer.execute("INSERT INTO collector_sessions VALUES ('t', '{}')")
        writer.execute('ROLLBACK')
        self.assertFalse(watch.poll())


if __name__ == '__main__':
    unittest.main()
