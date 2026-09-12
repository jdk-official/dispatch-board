"""local/server.py: binding, the request gate, the page wrapper, the data snapshot, not-ready and error
responses, the network-path guard and the command line. Live push is test_server_live.py.
"""
import contextlib, http.client, io, json, os, socket, sqlite3, sys, threading, unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(HERE, 'exporters'), os.path.join(HERE, 'local'), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import db  # noqa: E402
import records  # noqa: E402
import schema  # noqa: E402
import server  # noqa: E402
import server_support as ss  # noqa: E402


class Binding(ss.Env):
    def test_binds_127_0_0_1_only_and_refuses_reuse(self):
        srv = self.start()
        self.assertEqual(srv.server_address[0], '127.0.0.1')
        self.assertEqual(srv.address_family, socket.AF_INET)
        self.assertFalse(srv.allow_reuse_address)

    def test_a_connection_to_the_lan_address_is_refused(self):
        srv = self.start()
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            self.skipTest('no resolvable LAN address')
        if lan_ip == '127.0.0.1':
            self.skipTest('this machine has no LAN address other than loopback')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            with self.assertRaises(OSError):
                s.connect((lan_ip, srv.port))
        finally:
            s.close()


class Page(ss.Env):
    def test_the_page_is_wrapped_with_hoisted_title_and_local_marker(self):
        srv = self.start()
        resp, body = self.client.get('/')
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(resp.getheader('Cache-Control'), 'no-store')
        self.assertIsNotNone(resp.getheader('Content-Length'))
        self.assertIn('Content-Security-Policy', {k for k in resp.msg.keys()})
        text = body.decode('utf-8')
        self.assertTrue(text.startswith('<!doctype html>'))
        self.assertEqual(text.count('<html'), 1)
        self.assertEqual(text.count('<head>'), 1)
        self.assertEqual(text.count('<body>'), 1)
        self.assertIn('<meta charset="utf-8">', text)
        self.assertIn('name="viewport"', text)
        head, _, rest = text.partition('</head>')
        self.assertIn('<title>Board</title>', head)
        self.assertNotIn('<title>', rest)
        self.assertIn('window.__DISPATCH_LOCAL__={"snapshot":"/api/snapshot","events":"/api/events","version":1};', text)
        self.assertIn('<p id="content">hello</p>', text)

    def test_no_title_falls_back_to_dispatch_board(self):
        path = os.path.join(self.tmp, 'notitle.html')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('<p>no title here</p>')
        srv = self.start(page=path)
        resp, body = self.client.get('/')
        self.assertIn('<title>Dispatch board</title>', body.decode('utf-8'))

    def test_head_gives_same_headers_no_body(self):
        srv = self.start()
        resp, body = self.client.head('/')
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader('Content-Type'), 'text/html; charset=utf-8')
        self.assertEqual(body, b'')

    def test_unknown_path_is_404(self):
        srv = self.start()
        resp, body = self.client.get('/nope')
        self.assertEqual(resp.status, 404)
        self.assertEqual(body, b'not found\n')

    def test_the_repositorys_own_page_is_served_as_one_well_formed_document(self):
        """AC-SV5 against site/index.html itself, not the synthetic fixture: it is the file that actually ships,
        and it is 104 KB of content whose later <title> occurrences sit in JS template literals."""
        srv = self.start(page='site/index.html')
        resp, body = self.client.get('/')
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader('Content-Type'), 'text/html; charset=utf-8')
        text = body.decode('utf-8')
        self.assertTrue(text.startswith('<!doctype html>'))
        self.assertEqual(text.count('<html'), 1)
        self.assertEqual(text.count('<head>'), 1)
        self.assertEqual(text.count('<body>'), 1)
        self.assertEqual(text.count('</body>'), 1)
        head, _, rest = text.partition('</head>')
        self.assertIn('<meta charset="utf-8">', head)
        self.assertIn('name="viewport"', head)
        self.assertIn('window.__DISPATCH_LOCAL__={"snapshot":"/api/snapshot","events":"/api/events","version":1};',
                      head)
        with io.open(db.resolve('site/index.html'), encoding='utf-8') as f:
            source = f.read()
        title = source[source.index('<title>'):source.index('</title>') + len('</title>')]
        self.assertIn(title, head)
        # the file's own bytes, minus the hoisted title, are the body
        self.assertIn(source[len(title):], rest)

    def test_missing_page_gives_500_naming_path_while_api_still_answers(self):
        missing = os.path.join(self.tmp, 'gone.html')
        srv = self.start(page=missing)
        resp, body = self.client.get('/')
        self.assertEqual(resp.status, 500)
        self.assertIn(missing, body.decode('utf-8'))
        resp2, _ = self.client.get('/api/snapshot')
        self.assertEqual(resp2.status, 503)  # no db written yet, but it does answer rather than crash


class HostAndOrigin(ss.Env):
    def test_allowed_hosts_pass(self):
        srv = self.start()
        for host in ('127.0.0.1:%d' % srv.port, 'localhost:%d' % srv.port):
            resp, _ = self.client.get('/', host=host)
            self.assertEqual(resp.status, 200, host)

    def test_bad_hosts_are_403_one_line_no_echo(self):
        srv = self.start()
        cases = ['evil.test:%d' % srv.port, 'board.example.com', '127.0.0.1:1', None]
        for host in cases:
            with self.subTest(host=host):
                resp, body = self.client.get('/', host=host)
                self.assertEqual(resp.status, 403)
                self.assertEqual(resp.getheader('Content-Type'), 'text/plain; charset=utf-8')
                text = body.decode('utf-8')
                self.assertEqual(text.count('\n'), 1)
                self.assertNotIn('<', text)
                if host:
                    self.assertNotIn(host.split(':')[0], text)
                self.assertNotIn('sessions/', text)

    def test_non_get_needs_origin_or_403(self):
        srv = self.start()
        for method in ('POST', 'PUT', 'DELETE', 'OPTIONS'):
            with self.subTest(method=method):
                resp, _ = self.client.request(method, '/')
                self.assertEqual(resp.status, 403)
                resp2, _ = self.client.request(method, '/', origin='http://evil.test')
                self.assertEqual(resp2.status, 403)

    def test_non_get_with_allowed_origin_gives_405(self):
        srv = self.start()
        origin = 'http://127.0.0.1:%d' % srv.port
        for method in ('POST', 'PUT', 'DELETE', 'OPTIONS'):
            with self.subTest(method=method):
                resp, _ = self.client.request(method, '/', origin=origin)
                self.assertEqual(resp.status, 405)

    def test_get_with_foreign_origin_is_403(self):
        srv = self.start()
        resp, _ = self.client.get('/', origin='http://evil.test')
        self.assertEqual(resp.status, 403)

    def test_get_with_allowed_origin_is_ok(self):
        srv = self.start()
        resp, _ = self.client.get('/', origin='http://localhost:%d' % srv.port)
        self.assertEqual(resp.status, 200)

    def test_no_response_carries_a_cors_header(self):
        srv = self.start()
        for method, origin in (('GET', None), ('OPTIONS', 'http://127.0.0.1:%d' % srv.port)):
            resp, _ = self.client.request(method, '/', origin=origin)
            self.assertFalse([k for k in resp.msg.keys() if k.lower().startswith('access-control-allow-')])


class GateFramework(ss.Env):
    def test_the_six_do_methods_exist(self):
        for m in ('GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS'):
            self.assertTrue(hasattr(server.Handler, 'do_' + m))

    def test_a_method_outside_the_six_is_501(self):
        srv = self.start()
        raw = self.client.raw(b'PATCH / HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n' % srv.port)
        status, headers, body = ss.parse_head(raw)
        self.assertEqual(status, 501)
        self.assertEqual(headers.get('content-type'), 'text/plain; charset=utf-8')
        self.assertNotIn('PATCH', body.decode('utf-8'))

    def test_oversized_request_line_is_414(self):
        srv = self.start()
        line = b'GET /' + b'a' * 70000 + b' HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n' % srv.port
        raw = self.client.raw(line)
        status, headers, body = ss.parse_head(raw)
        self.assertEqual(status, 414)
        self.assertLess(len(body), 200)

    def test_too_many_headers_is_431(self):
        srv = self.start()
        extra = ''.join('X-%d: 1\r\n' % i for i in range(120))
        req = ('GET / HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n' % srv.port + extra + '\r\n').encode('ascii')
        raw = self.client.raw(req)
        status, headers, body = ss.parse_head(raw)
        self.assertEqual(status, 431)

    def test_malformed_request_line_is_400(self):
        srv = self.start()
        raw = self.client.raw(b'GET /a b HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n' % srv.port)
        status, headers, body = ss.parse_head(raw)
        self.assertEqual(status, 400)
        self.assertEqual(body, b'bad request\n')

    def test_expect_100_continue_is_answered_before_the_gate_but_reaches_no_route(self):
        """handle_expect_100 answers from inside parse_request, so it runs before the Host check like the 400,
        414, 431, 501 and 505 paths do. What matters is that it still reaches no route: the request behind it is
        refused as usual and no board data comes back."""
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        raw = self.client.raw(b'GET /api/snapshot HTTP/1.1\r\nHost: evil.test\r\nExpect: 100-continue\r\n'
                              b'Connection: close\r\n\r\n')
        self.assertTrue(raw.startswith(b'HTTP/1.1 100 Continue'), raw[:60])
        self.assertIn(b' 403 ', raw)
        self.assertNotIn(b'sessions/', raw)
        self.assertNotIn(b'Python', raw)

    def assert_refusal_shape(self, expect, status, headers, body, offending=()):
        self.assertEqual(status, expect)
        self.assertEqual(headers.get('content-type'), 'text/plain; charset=utf-8')
        self.assertEqual(headers.get('cache-control'), 'no-store')
        self.assertEqual(headers.get('x-content-type-options'), 'nosniff')
        self.assertEqual(headers.get('content-length'), str(len(body)))
        text = body.decode('utf-8')
        self.assertNotIn('<', text)
        self.assertEqual(text.count('\n'), 1)
        self.assertNotIn('sessions/', text)
        for token in offending:
            self.assertNotIn(token, text)

    def test_every_refusal_has_the_same_plain_shape(self):
        """AC-SV2: all eight refusals the server can emit, checked against one property list rather than each
        against a smaller subset of its own."""
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        allowed_origin = 'http://127.0.0.1:%d' % srv.port
        cases = []
        for expect, resp_body, offending in (
                (403, self.client.get('/', host='evil.test:%d' % srv.port), ('evil.test',)),
                (403, self.client.get('/', host=None), ()),
                (403, self.client.request('POST', '/', origin='http://evil.test'), ('evil.test',)),
                (404, self.client.get('/nope'), ()),
                (405, self.client.request('POST', '/', origin=allowed_origin), ())):
            resp, body = resp_body
            cases.append((expect, resp.status, {k.lower(): v for k, v in resp.getheaders()}, body, offending))
        host_line = b'Host: 127.0.0.1:%d\r\n' % srv.port
        for expect, data, offending in (
                (400, b'GET /a b HTTP/1.1\r\n' + host_line + b'\r\n', ('/a b',)),
                (414, b'GET /' + b'a' * 70000 + b' HTTP/1.1\r\n' + host_line + b'\r\n', ('aaaa',)),
                (431, b'GET / HTTP/1.1\r\n' + host_line
                      + b''.join(b'X-%d: 1\r\n' % i for i in range(120)) + b'\r\n', ()),
                (501, b'PATCH / HTTP/1.1\r\n' + host_line + b'\r\n', ('PATCH',)),
                (505, b'GET / HTTP/2.5\r\n' + host_line + b'\r\n', ('HTTP/2.5',))):
            status, headers, body = ss.parse_head(self.client.raw(data))
            cases.append((expect, status, headers, body, offending))
        for expect, status, headers, body, offending in cases:
            with self.subTest(status=expect, body=body):
                self.assert_refusal_shape(expect, status, headers, body, offending)


class SnapshotConformance(ss.Env):
    def test_every_record_is_returned_with_skipped_zero(self):
        for kind, rid, doc in ss.ONE.values():
            self.write(kind, rid, doc)
        srv = self.start()
        resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 200)
        payload = json.loads(body)
        self.assertEqual(payload['skipped'], 0)
        for kind, rid, doc in ss.ONE.values():
            path = records.store_path(kind, rid)
            self.assertIn(path, payload['records'])
            entry = payload['records'][path]
            self.assertEqual(entry['kind'], kind)
            self.assertEqual(entry['id'], rid)
            self.assertEqual(records.validate(kind, entry['doc']), [])
        self.assertGreaterEqual(len(payload['records']), len(ss.ONE))

    def test_a_corrupt_row_is_skipped_others_of_its_kind_still_served(self):
        self.write('session', 's1', ss.session_doc())
        self.write('session', 's2', ss.session_doc())
        conn = self.connect()
        conn.execute("UPDATE sessions SET doc = 'not json' WHERE id = 's2'")
        conn.close()
        srv = self.start()
        resp, body = self.client.get('/api/snapshot')
        payload = json.loads(body)
        self.assertEqual(payload['skipped'], 1)
        self.assertIn('sessions/s1', payload['records'])
        self.assertNotIn('sessions/s2', payload['records'])


class IgnoresCollectorState(ss.Env):
    def test_no_response_holds_collector_state_or_answers(self):
        self.write('session', 's1', ss.session_doc())
        conn = self.connect()
        conn.execute("INSERT INTO collector_sessions (id, data) VALUES ('s1', '{\"secret\": 1}')")
        conn.execute("INSERT INTO collector_agents (session, agent, data) VALUES ('s1', 'a1', '{}')")
        conn.execute("INSERT INTO collector_excluded (dev, ino, size, rule) VALUES ('1', '2', 3, 'r')")
        conn.execute('CREATE TABLE answers (id TEXT PRIMARY KEY, doc TEXT)')
        conn.execute("INSERT INTO answers (id, doc) VALUES ('a', '{\"answer\": \"secret-answer-text\"}')")
        conn.close()
        srv = self.start()
        resp, page_body = self.client.get('/')
        resp2, snap_body = self.client.get('/api/snapshot')
        payload = json.loads(snap_body)
        for kind in payload['records'].values():
            self.assertIn(kind['kind'], records.TABLES)
        for body in (snap_body,):
            self.assertNotIn(b'collector_', body)
            self.assertNotIn(b'secret-answer-text', body)
            self.assertNotIn(b'answers', body)
        self.assertNotIn(b'collector_', page_body)
        self.assertNotIn(b'secret-answer-text', page_body)


class NeverWrites(ss.Env):
    def test_query_only_and_file_unchanged_even_with_writers_patched_to_raise(self):
        self.write('session', 's1', ss.session_doc())
        with open(self.db_path, 'rb') as f:
            before = f.read()
        before_mtime = os.path.getmtime(self.db_path)
        # A read-only inspection connection: db.open_db (or any writer) would itself touch the header.
        inspect_conn = sqlite3.connect(self.db_path)
        inspect_conn.execute('PRAGMA query_only = 1')
        before_version = inspect_conn.execute('PRAGMA data_version').fetchone()[0]
        before_master = inspect_conn.execute("SELECT name FROM sqlite_master ORDER BY name").fetchall()
        inspect_conn.close()

        def boom(*a, **k):
            raise AssertionError('the server must never call this')

        with mock.patch.object(db, 'open_db', boom), mock.patch.object(schema, 'create_schema', boom), \
             mock.patch.object(db, 'upsert', boom), mock.patch.object(db, 'delete', boom):
            srv = self.start()
            resp, _ = self.client.get('/')
            self.assertEqual(resp.status, 200)
            resp2, body2 = self.client.get('/api/snapshot')
            self.assertEqual(resp2.status, 200)
            self.assertEqual(srv.state.conn.execute('PRAGMA query_only').fetchone()[0], 1)

        with open(self.db_path, 'rb') as f:
            after = f.read()
        self.assertEqual(before, after)
        self.assertEqual(before_mtime, os.path.getmtime(self.db_path))
        inspect_conn = sqlite3.connect(self.db_path)
        inspect_conn.execute('PRAGMA query_only = 1')
        self.assertEqual(before_version, inspect_conn.execute('PRAGMA data_version').fetchone()[0])
        self.assertEqual(before_master, inspect_conn.execute("SELECT name FROM sqlite_master ORDER BY name").fetchall())
        inspect_conn.close()


class _CountingLock:
    """A lock that records how many times it was taken, so a test can prove a read happened under a single hold."""

    def __init__(self):
        self.lock, self.acquires = threading.Lock(), 0

    def acquire(self, *a, **kw):
        self.acquires += 1
        return self.lock.acquire(*a, **kw)

    def release(self):
        self.lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


class StateInternals(ss.Env):
    def test_current_reads_the_snapshot_and_its_skipped_count_under_one_lock(self):
        self.write('session', 's1', ss.session_doc())
        state = server.State(self.db_path)
        self.addCleanup(state.close)
        state.lock = _CountingLock()
        version, snapshot, skipped = state.current()
        self.assertIn('sessions/s1', snapshot)
        self.assertEqual(skipped, 0)
        self.assertEqual(state.lock.acquires, 1)

    def test_a_failed_read_closes_the_connection_before_dropping_it(self):
        self.write('session', 's1', ss.session_doc())
        state = server.State(self.db_path)
        self.addCleanup(state.close)
        state.current()
        conn = state.conn
        self.assertIsNotNone(conn)
        self.write('session', 's2', ss.session_doc())  # a commit, so the next refresh really re-reads
        with mock.patch.object(server, 'read_snapshot', side_effect=sqlite3.OperationalError('locked')):
            with self.assertRaises(sqlite3.OperationalError):
                state.refresh()
        self.assertIsNone(state.conn)
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')

    def test_stop_closes_the_read_only_connection(self):
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        resp, _ = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 200)
        conn = srv.state.conn
        self.assertIsNotNone(conn)
        srv.stop()
        self.srv = None
        self.assertIsNone(srv.state.conn)
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')


class Isolation(ss.Env):
    def test_a_server_test_never_reads_the_repository_config(self):
        with mock.patch.object(server, 'read_config',
                               side_effect=AssertionError('the tests must not read board.config.json')):
            srv = self.start()
            resp, _ = self.client.get('/')
            self.assertEqual(resp.status, 200)


class Position(unittest.TestCase):
    def test_unparsable_and_negative_positions_count_as_no_position(self):
        self.assertIsNone(server._position(None, None))
        self.assertIsNone(server._position('since=abc', None))
        self.assertIsNone(server._position('since=-5', None))
        self.assertIsNone(server._position('since=', 'not-a-number'))
        self.assertIsNone(server._position('since=1.5', None))

    def test_the_larger_parseable_value_wins_whichever_side_it_came_from(self):
        self.assertEqual(server._position('since=abc', '12'), 12)
        self.assertEqual(server._position('since=7', 'abc'), 7)
        self.assertEqual(server._position('since=7', '12'), 12)
        self.assertEqual(server._position('since=12', '7'), 12)
        self.assertEqual(server._position('since=0', None), 0)


class NotReady(ss.Env):
    def test_no_database_file_page_ok_snapshot_503_no_file_created(self):
        srv = self.start()
        resp, _ = self.client.get('/')
        self.assertEqual(resp.status, 200)
        resp2, body2 = self.client.get('/api/snapshot')
        self.assertEqual(resp2.status, 503)
        self.assertEqual(resp2.getheader('Retry-After'), '5')
        self.assertFalse(os.path.exists(self.db_path))

    def test_schema_too_new_names_both_versions(self):
        self.write('session', 's1', ss.session_doc())
        conn = self.connect()
        conn.execute('PRAGMA user_version = %d' % (schema.SCHEMA_VERSION + 1))
        conn.close()
        srv = self.start()
        resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 503)
        text = body.decode('utf-8')
        self.assertIn(str(schema.SCHEMA_VERSION + 1), text)
        self.assertIn(str(schema.SCHEMA_VERSION), text)

    def test_once_the_collector_creates_the_db_records_serve_with_no_restart(self):
        srv = self.start()
        resp, _ = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 503)
        self.write('session', 's1', ss.session_doc())
        resp2, body2 = self.client.get('/api/snapshot')
        self.assertEqual(resp2.status, 200)
        payload = json.loads(body2)
        self.assertIn('sessions/s1', payload['records'])


class NetworkGuard(ss.Env):
    """AC-67 in full: exit 2, the path on stderr as configured, nothing listening on the configured port, and
    nothing created on disk. The port has to be a concrete one, not 0, for the third of those to be checkable.
    """

    def free_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def assert_nothing_listening(self, port):
        """No HTTP request is answered on the port, and the port can still be bound. The bind is the reliable
        half: a connect to a closed port on this host is dropped rather than refused, so it only ever times out.
        """
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
        try:
            with self.assertRaises(OSError):
                conn.request('GET', '/')
                conn.getresponse()
        finally:
            conn.close()
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as e:
            self.fail('something is listening on port %d (%s)' % (port, e))
        finally:
            probe.close()

    def listing(self, root):
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            found += [os.path.join(dirpath, name) for name in dirnames + filenames]
        return sorted(found)

    def test_unc_path_refuses_at_start_exits_2_no_socket_no_file_created(self):
        for path in ('\\\\nas\\share\\board.db', '//nas/share/board.db'):
            with self.subTest(path=path):
                port = self.free_port()
                before = self.listing(self.tmp)
                err = io.StringIO()
                cfg = {'local': {'databasePath': path, 'port': port}}
                with contextlib.redirect_stderr(err):
                    # ready() stops a server that did start, so a guard that failed to refuse shows up as a
                    # failed assertion rather than as main() blocking for ever.
                    code = server.main([], config=cfg, ready=lambda s: s.stop())
                self.assertEqual(code, 2)
                self.assertIn(path, err.getvalue())
                self.assert_nothing_listening(port)
                self.assertEqual(before, self.listing(self.tmp))

    def test_realpath_pointing_at_a_unc_path_refuses(self):
        port = self.free_port()
        before = self.listing(self.tmp)
        cfg = {'local': {'databasePath': self.db_path, 'port': port}}
        err = io.StringIO()
        with mock.patch.object(os.path, 'realpath', return_value='\\\\nas\\share\\board.db'):
            with contextlib.redirect_stderr(err):
                code = server.main([], config=cfg, ready=lambda s: s.stop())
        self.assertEqual(code, 2)
        self.assertIn(self.db_path, err.getvalue())
        self.assert_nothing_listening(port)
        self.assertFalse(os.path.exists(self.db_path))
        self.assertEqual(before, self.listing(self.tmp))


class CommandLine(ss.Env):
    def test_bad_port_exits_2(self):
        cfg = {'local': {'databasePath': self.db_path, 'port': 70000}}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = server.main([], config=cfg)
        self.assertEqual(code, 2)
        self.assertIn('local.port', err.getvalue())

    def test_port_already_in_use_exits_2_naming_port(self):
        srv = self.start()
        err = io.StringIO()
        cfg = {'local': {'databasePath': self.db_path, 'port': srv.port}}
        with contextlib.redirect_stderr(err):
            code = server.main([], config=cfg)
        self.assertEqual(code, 2)
        self.assertIn(str(srv.port), err.getvalue())

    def test_start_up_line_names_url_and_database_stop_exits_0(self):
        out = io.StringIO()
        holder = {}
        with contextlib.redirect_stdout(out):
            code = server.main([], config={'local': {'databasePath': self.db_path}}, port=0,
                               ready=lambda s: (holder.setdefault('srv', s), s.stop()))
        self.assertEqual(code, 0)
        self.assertIn('server: serving', out.getvalue())
        self.assertIn(self.db_path, out.getvalue())
        self.assertIn(holder['srv'].url, out.getvalue())

    def test_port_0_binds_a_free_port(self):
        holder = {}
        with contextlib.redirect_stdout(io.StringIO()):
            server.main([], config={'local': {'databasePath': self.db_path}}, port=0,
                       ready=lambda s: (holder.setdefault('srv', s), s.stop()))
        self.assertGreater(holder['srv'].port, 0)


class Errors(ss.Env):
    def test_a_handler_that_raises_gives_500_one_line_no_traceback_in_body(self):
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        err = io.StringIO()
        with mock.patch.object(server.State, 'current', side_effect=RuntimeError('boom')), \
             contextlib.redirect_stderr(err):
            resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 500)
        text = body.decode('utf-8')
        self.assertEqual(text, 'the server failed to handle this request\n')
        self.assertIn('RuntimeError', err.getvalue())
        self.assertIn('boom', err.getvalue())

    def test_no_server_header_names_python(self):
        srv = self.start()
        resp, _ = self.client.get('/')
        server_header = resp.getheader('Server') or ''
        self.assertNotIn('Python', server_header)
        self.assertIn('dispatch-board', server_header)

    def test_an_os_error_inside_a_handler_is_named_on_stderr(self):
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        err = io.StringIO()
        with mock.patch.object(server.State, 'current', side_effect=OSError(13, 'permission denied')), \
             contextlib.redirect_stderr(err):
            raw = self.client.raw(b'GET /api/snapshot HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nConnection: close\r\n\r\n'
                                  % srv.port)
        self.assertEqual(raw, b'')  # nothing can be written back: the connection may already be gone
        self.assertIn('errno 13', err.getvalue())

    def test_the_request_line_reaches_stderr_escaped(self):
        srv = self.start()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            raw = self.client.raw(b'GET /\x1b[31m\x07nope HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nConnection: close\r\n\r\n'
                                  % srv.port)
        status, headers, body = ss.parse_head(raw)
        self.assertEqual(status, 404)
        logged = err.getvalue()
        self.assertIn('nope', logged)
        self.assertNotIn('\x1b', logged)
        self.assertNotIn('\x07', logged)
        self.assertIn('\\x1b', logged)

    def test_a_read_that_times_out_is_503_not_a_crash(self):
        self.write('session', 's1', ss.session_doc())
        srv = self.start()
        with mock.patch.object(server, 'read_snapshot', side_effect=sqlite3.OperationalError('database is locked')):
            resp, body = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 503)
        self.assertEqual(resp.getheader('Retry-After'), '5')
        self.assertIn('try again', body.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
