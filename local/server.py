"""The local-first app's server: serves the page, a JSON snapshot of the database and a live event stream on
127.0.0.1, and nothing else. It is a reader only: it writes no record, no table and no schema, and creates no
file of its own (SQLite may still create a `-wal`/`-shm` pair beside a WAL database it opens, which is outside
this module's control).

    python local/server.py [--port N] [--config PATH] [--poll SECONDS]

Every request passes a Host and Origin gate before it is routed (do_GET/do_HEAD/do_POST/do_PUT/do_DELETE/
do_OPTIONS all funnel through _handle()); a refusal is always one line of text/plain that never echoes what it
rejected. The database is opened read-only with its own connection (open_read()), never through db.open_db,
which writes. Records are read with db.stored(), falling back to a per-row read when one row of a kind is bad,
so one corrupt record costs only itself. A change is noticed by polling PRAGMA data_version (db.Changes) and
pushed to every open /api/events stream as one 'change' event; the watcher only enqueues, and a stream that is
not draining its queue is dropped rather than allowed to block another client.

Callable in-process: serve(config=None, db_path=None, port=None, page=None, poll=None) -> Server, already
bound and serving in a background thread; main(argv=None, ...) -> int, the blocking command line.
"""
import argparse, http.server, io, json, os, queue, re, socket, sqlite3, sys, threading, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _p in (os.path.join(REPO, 'exporters'), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import board_config  # noqa: E402
import db  # noqa: E402
import records  # noqa: E402
import schema  # noqa: E402

DEFAULT_CONFIG = os.path.join(REPO, 'board.config.json')
BUSY_TIMEOUT = 5  # seconds; matches PBI-019's writer so a reader waits no longer than a writer would
POLL_DEFAULT = 2
HEARTBEAT = 15  # seconds between ": ping" comments; tests drive this down along with --poll
QUEUE_MAXSIZE = 32
MAX_STREAMS = 8

TITLE_RE = re.compile(r'<title>.*?</title>', re.IGNORECASE | re.DOTALL)
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' "
       "https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")

FORBIDDEN_HOST = 'forbidden: the Host header is not a local address'
FORBIDDEN_ORIGIN = 'forbidden: the Origin header is not a local address'
FORBIDDEN_NO_ORIGIN = 'forbidden: this request needs an Origin header'
NOT_READY = 'the local database is not ready yet; the collector has not written it'
READ_FAILED = 'the local database could not be read; try again'
# The shared one-line body per status, whoever raises it: this module for 404, 405 and 500, the framework for
# 400, 414, 431, 501 and 505. A refusal that needs headers of its own (403, 503) names its line at its call site.
REFUSAL_LINES = {400: 'bad request', 404: 'not found', 405: 'method not allowed', 414: 'bad request',
                 431: 'bad request', 500: 'the server failed to handle this request', 501: 'method not allowed',
                 505: 'bad request'}


def warn(msg):
    print('server: ' + msg, file=sys.stderr)


class NotReady(Exception):
    """The database exists but cannot be served yet: no schema, or a schema newer than this server reads."""


def config_object(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('the config must be a JSON object, not %s' % type(cfg).__name__)
    return cfg


def read_config(path):
    """The board config at path. Raises OSError when it cannot be read and ValueError when it is not JSON, nests
    too deeply to parse, or is not an object at the top: all refusals, never a crash."""
    try:
        with io.open(path, encoding='utf-8') as f:
            cfg = json.load(f)
    except RecursionError as e:
        raise ValueError('%s nests too deeply to parse' % path) from e
    return config_object(cfg)


# --- reading the database, read-only -----------------------------------------------------------

def open_read(path, root=None):
    """A read-only connection to the database at path, or None when it is not there yet or has no schema.
    Raises NotReady when its schema is newer than this server understands, and sqlite3.Error on any other
    failure to open or query it. Never creates the file: db.open_db does that, and it writes."""
    full = db.resolve(path, root)
    if not os.path.exists(full):
        return None
    conn = sqlite3.connect(full, isolation_level=None, timeout=BUSY_TIMEOUT, check_same_thread=False)
    try:
        conn.execute('PRAGMA query_only = 1')
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version > schema.SCHEMA_VERSION:
            raise NotReady('the local database is at schema version %d, newer than this server (version %d)'
                           % (version, schema.SCHEMA_VERSION))
        if version == 0:
            conn.close()
            return None
        try:
            conn.execute('SELECT 1 FROM sessions LIMIT 1')
        except sqlite3.OperationalError:
            conn.close()
            return None
    except BaseException:
        conn.close()
        raise
    return conn


def _stored_fallback(conn, kind):
    """{id: doc} for a kind whose db.stored() raised: the same SELECT read row by row, skipping only the rows
    that do not conform. Returns (stored, skipped)."""
    table = records.TABLES[kind][0]
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    stored, skipped = {}, 0
    for row in cur.execute('SELECT id, doc FROM %s ORDER BY id' % table):
        try:
            stored[row['id']] = records.from_row(kind, row)
        except ValueError as e:
            skipped += 1
            warn('%s %s skipped: %s' % (kind, row['id'], e))
    return stored, skipped


def read_snapshot(conn):
    """({store_path: {"kind", "id", "doc"}}, skipped) for every conforming record in records.TABLES, read inside
    one short read transaction so the page never sees a run whose session is missing. Only records.TABLES is
    read, so no collector_* table and no answers table, however present, is ever visible here."""
    out, skipped = {}, 0
    conn.execute('BEGIN DEFERRED')
    try:
        for kind in records.TABLES:
            try:
                stored = db.stored(conn, kind)
            except ValueError:
                stored, n = _stored_fallback(conn, kind)
                skipped += n
            for rid, doc in stored.items():
                try:
                    path = records.store_path(kind, rid)
                except ValueError as e:
                    skipped += 1
                    warn('%s %s skipped: %s' % (kind, rid, e))
                    continue
                out[path] = {'kind': kind, 'id': rid, 'doc': doc}
        conn.execute('COMMIT')
    except BaseException:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
    return out, skipped


class State:
    """One read-only connection, one change watcher, the current snapshot and its version, all behind one lock so
    the connection is never touched by two threads at once."""

    def __init__(self, path, root=None):
        self.path, self.root = path, root
        self.lock = threading.Lock()
        self.conn = self.changes = None
        self.snapshot, self.skipped, self.version, self.have_snapshot = {}, 0, 1, False

    def _ensure_conn(self):
        if self.conn is None:
            self.conn = open_read(self.path, self.root)
            if self.conn is not None:
                self.changes = db.Changes(self.conn)
        return self.conn

    def _close_conn(self):
        """Closes the read-only connection and forgets it, so the next read opens a clean one. The caller holds
        the lock. Closing is explicit rather than left to refcounting, because an open handle keeps a lock on the
        database file on Windows."""
        if self.conn is not None:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
        self.conn = self.changes = None

    def _refresh_locked(self):
        conn = self._ensure_conn()
        if conn is None:
            raise NotReady(NOT_READY)
        first = not self.have_snapshot
        # poll() must run every call, even the first, so its own "unchanged since last poll" tracking is
        # primed; "or" short-circuiting it away on the first call would leave the next real poll blind.
        changed_since = self.changes.poll()
        if not (first or changed_since):
            return self.version, self.snapshot, {}, []
        try:
            new_snapshot, skipped = read_snapshot(conn)
        except sqlite3.Error:
            # A failed read leaves the connection unusable; the next request reopens it cleanly.
            self._close_conn()
            raise
        changed = {p: r for p, r in new_snapshot.items() if self.snapshot.get(p) != r}
        removed = [p for p in self.snapshot if p not in new_snapshot]
        self.snapshot, self.skipped = new_snapshot, skipped
        if first:
            self.have_snapshot = True
            return self.version, self.snapshot, {}, []
        if changed or removed:
            self.version += 1
        return self.version, self.snapshot, changed, removed

    def refresh(self):
        """(version, records, changed, removed): re-reads when the database changed or has never been read, and
        returns the delta; otherwise returns the current snapshot and an empty delta. Raises NotReady or
        sqlite3.Error, from the caller's perspective, when there is nothing to serve."""
        with self.lock:
            return self._refresh_locked()

    def current(self):
        """(version, records, skipped): the snapshot as it stands, refreshing first. The three come from one hold
        of the lock, so the skipped count always belongs to the snapshot it is reported with."""
        with self.lock:
            version, snapshot, _, _ = self._refresh_locked()
            return version, snapshot, self.skipped

    def close(self):
        """Releases the database handle. The state is still usable: the next read reopens it."""
        with self.lock:
            self._close_conn()


# --- live push -----------------------------------------------------------------------------------

class _Client:
    def __init__(self):
        self.queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
        self.overflowed = False


class Hub:
    """Registers one bounded queue per open stream and pushes deltas to them. No watcher thread runs while no
    stream is open: the first registration starts it, the last removal stops it."""

    def __init__(self, state, poll_interval):
        self.state, self.poll_interval = state, poll_interval
        self.lock = threading.Lock()
        self.clients, self.watcher, self.stop = set(), None, None

    def register(self):
        with self.lock:
            if len(self.clients) >= MAX_STREAMS:
                return None
            client = _Client()
            was_empty = not self.clients
            self.clients.add(client)
            # An empty clients set means unregister() has already set the stop Event, so whatever thread is still
            # running is committed to exiting and must not be reused however alive it still looks - between the
            # set() and the thread's own exit, is_alive() is true and the client would end up with no watcher at
            # all. A fresh Event and a fresh thread are minted instead; the dying one holds no client.
            if was_empty or self.watcher is None or not self.watcher.is_alive():
                self.stop = threading.Event()
                self.watcher = threading.Thread(target=self._watch, args=(self.stop,), daemon=True)
                self.watcher.start()
            return client

    def unregister(self, client):
        with self.lock:
            self.clients.discard(client)
            if not self.clients and self.stop is not None:
                self.stop.set()

    def _watch(self, stop):
        # The hub keeps its own baseline rather than trusting refresh()'s own "changed"/"removed": that delta is
        # a one-shot value, and a concurrent /api/snapshot request calling refresh() first would consume it,
        # leaving the watcher's own call empty even though the database really did change. Diffing the always-
        # current full snapshot against what the hub itself last saw is correct regardless of who else polled.
        try:
            last_version, last_snapshot, _, _ = self.state.refresh()
        except Exception:
            last_version, last_snapshot = None, {}
        while not stop.wait(self.poll_interval):
            try:
                version, snapshot, _, _ = self.state.refresh()
            except Exception:
                continue  # not ready or a read failure: nothing to push; the next poll tries again
            if version == last_version:
                continue
            changed = {p: r for p, r in snapshot.items() if last_snapshot.get(p) != r}
            removed = [p for p in last_snapshot if p not in snapshot]
            last_version, last_snapshot = version, snapshot
            if not (changed or removed):
                continue
            payload = json.dumps({'version': version, 'set': changed, 'deleted': removed}, ensure_ascii=True)
            data = ('event: change\nid: %d\ndata: %s\n\n' % (version, payload)).encode('ascii')
            with self.lock:
                dead = []
                for client in self.clients:
                    try:
                        client.queue.put_nowait(data)
                    except queue.Full:
                        client.overflowed = True
                        dead.append(client)
                for client in dead:
                    self.clients.discard(client)


def _query_param(query, name):
    for part in (query or '').split('&'):
        key, _, value = part.partition('=')
        if key == name:
            return value
    return None


def _position(query, header):
    """The larger of ?since= and Last-Event-ID that parses as a non-negative integer; None if neither does."""
    values = []
    for raw in (_query_param(query, 'since'), header):
        if raw is None:
            continue
        try:
            n = int(raw)
        except ValueError:
            continue
        if n >= 0:
            values.append(n)
    return max(values) if values else None


# --- the request handler ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    # A backstop only: send_error is overridden below and never reaches the base implementation that reads these.
    error_message_format = '%(code)d\n'
    error_content_type = 'text/plain; charset=utf-8'

    def version_string(self):
        return 'dispatch-board'

    def do_GET(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_PUT(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_OPTIONS(self):
        self._handle()

    def send_error(self, code, message=None, explain=None):
        # Overridden so a framework-raised refusal (400, 414, 431, 501, 505) never echoes what it rejected.
        self._respond_plain(code, REFUSAL_LINES.get(code, 'error'))

    def _handle(self):
        try:
            path, _, query = self.path.partition('?')
            if not self._host_ok():
                return
            if not self._origin_ok():
                return
            self._route(path, query)
        except OSError as e:
            # Every connection-loss class - a broken pipe, a reset, a socket timeout - is an OSError, so one
            # clause covers them and the write paths already swallow their own. Nothing can be written back here,
            # because the connection may be gone; the errno is named so a repeated environmental fault (a
            # file-descriptor or disk failure, say) is visible to the owner rather than silently discarded.
            warn('request failed (%s errno %s: %s)' % (type(e).__name__, e.errno, e))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            try:
                self._respond_plain(500, REFUSAL_LINES[500])
            except Exception:
                pass

    def _host_ok(self):
        header = self.headers.get('Host')
        if not header:
            warn('rejected a request with no Host header')
            self._respond_plain(403, FORBIDDEN_HOST)
            return False
        host, _, port_text = header.partition(':')
        ok = host.lower() in ('127.0.0.1', 'localhost')
        if ok and port_text:
            try:
                ok = int(port_text) == self.server.server_address[1]
            except ValueError:
                ok = False
        if not ok:
            warn('rejected a request with Host %r' % header)
            self._respond_plain(403, FORBIDDEN_HOST)
            return False
        return True

    def _origin_ok(self):
        origin = self.headers.get('Origin')
        port = self.server.server_address[1]
        if origin is None:
            if self.command not in ('GET', 'HEAD'):
                warn('rejected a %s request with no Origin header' % self.command)
                self._respond_plain(403, FORBIDDEN_NO_ORIGIN)
                return False
            return True
        if origin not in ('http://127.0.0.1:%d' % port, 'http://localhost:%d' % port):
            warn('rejected a request with Origin %r' % origin)
            self._respond_plain(403, FORBIDDEN_ORIGIN)
            return False
        return True

    def _route(self, path, query):
        if path not in ('/', '/api/snapshot', '/api/events'):
            self._respond_plain(404, REFUSAL_LINES[404])
        elif self.command not in ('GET', 'HEAD'):
            self._respond_plain(405, REFUSAL_LINES[405])
        elif path == '/':
            self._serve_page()
        elif path == '/api/snapshot':
            self._serve_snapshot()
        else:
            self._serve_events(query)

    def _security_headers(self, csp=False):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        if csp:
            self.send_header('Content-Security-Policy', CSP)

    def _respond_plain(self, code, line, extra_headers=()):
        body = (line + '\n').encode('ascii', 'backslashreplace')
        # A request line whose version never parsed - the 505 and bad-version-400 paths - leaves request_version
        # at HTTP/0.9, and the base class then writes the body alone, with no status line and no header at all.
        # Every refusal owes the same shape, so the reply is written as HTTP/1.1 whatever the request claimed.
        if self.request_version == 'HTTP/0.9':
            self.request_version = self.protocol_version
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self._security_headers()
            for key, value in extra_headers:
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    # -------- GET /

    def _serve_page(self):
        try:
            with io.open(self.server.page_path, encoding='utf-8') as f:
                content = f.read()
        except OSError:
            self._respond_plain(500, 'the page could not be read: %s' % self.server.page_path)
            return
        body = _wrap_page(content).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self._security_headers(csp=True)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    # -------- GET /api/snapshot

    def _serve_snapshot(self):
        try:
            version, snapshot, skipped = self.server.state.current()
        except NotReady as e:
            self._respond_plain(503, str(e), (('Retry-After', '5'),))
            return
        except sqlite3.Error:
            self._respond_plain(503, READ_FAILED, (('Retry-After', '5'),))
            return
        payload = {'version': version, 'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()),
                  'skipped': skipped, 'records': snapshot}
        body = json.dumps(payload, ensure_ascii=True).encode('ascii')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self._security_headers()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    # -------- GET /api/events

    def _serve_events(self, query):
        # Registering first is what closes the gap between the version this client is judged against and the
        # baseline the watcher will diff from: registration is what starts the watcher and makes it take that
        # baseline, so a commit landing before it is folded into the baseline and never pushed. Reading the
        # version afterwards means such a commit puts the version ahead of the client's position, and it is sent
        # a reset instead of being left silently one commit behind.
        client = self.server.hub.register()
        if client is None:
            self._respond_plain(503, 'too many open streams', (('Retry-After', '5'),))
            return
        try:
            version, _, _, _ = self.server.state.refresh()
        except NotReady as e:
            self.server.hub.unregister(client)
            self._respond_plain(503, str(e), (('Retry-After', '5'),))
            return
        except sqlite3.Error:
            self.server.hub.unregister(client)
            self._respond_plain(503, READ_FAILED, (('Retry-After', '5'),))
            return
        position = _position(query, self.headers.get('Last-Event-ID'))
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Accel-Buffering', 'no')
            self._security_headers()
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command == 'HEAD':
                return
            self.connection.settimeout(10)
            self.wfile.write(b'retry: 3000\n\n')
            self.wfile.flush()
            if position is None or position != version:
                data = json.dumps({'version': version}, ensure_ascii=True)
                self.wfile.write(('event: reset\nid: %d\ndata: %s\n\n' % (version, data)).encode('ascii'))
                self.wfile.flush()
            self._stream_loop(client)
        except (BrokenPipeError, ConnectionResetError, OSError, socket.timeout):
            pass
        finally:
            self.server.hub.unregister(client)

    def _stream_loop(self, client):
        q = client.queue
        while not client.overflowed:
            try:
                item = q.get(timeout=HEARTBEAT)
            except queue.Empty:
                self.wfile.write(b': ping\n\n')
                self.wfile.flush()
                continue
            self.wfile.write(item)
            self.wfile.flush()

    def log_request(self, code='-', size='-'):
        # The request line is a latin-1 decode of arbitrary bytes from any local process, so it can carry control
        # characters and terminal escape sequences. repr escapes them, so nothing a request chooses can act on
        # the terminal the owner reads this log in.
        self.log_message('%r %s %s', self.requestline, str(code), str(size))

    def log_message(self, fmt, *args):
        sys.stderr.write('server: %s - %s\n' % (self.address_string(), fmt % args))


def _wrap_page(content):
    window = content[:8192]
    m = TITLE_RE.search(window)
    if m:
        title_tag, body = m.group(0), content[:m.start()] + content[m.end():]
    else:
        title_tag, body = '<title>Dispatch board</title>', content
    return (
        '<!doctype html>\n<html lang="en"><head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<style>:root{color-scheme:light}body{margin:0;background:#faf9f7;'
        'font:14px system-ui,-apple-system,"Segoe UI",sans-serif}img{max-width:100%}'
        '[hidden]{display:none!important}</style>\n' + title_tag + '\n'
        '<script>window.__DISPATCH_LOCAL__={"snapshot":"/api/snapshot","events":"/api/events","version":1};</script>\n'
        '</head><body>\n' + body + '\n</body></html>')


# --- the server, and its command line ---------------------------------------------------------------

class Server(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, addr, db_path, page, poll_interval):
        super().__init__(addr, Handler)
        self.page_path = db.resolve(page or 'site/index.html')
        self.state = State(db_path)
        self.hub = Hub(self.state, poll_interval)
        self.port = self.server_address[1]
        self.url = 'http://127.0.0.1:%d' % self.port
        self._stopped = threading.Event()

    def stop(self):
        self._stopped.set()
        self.shutdown()
        self.server_close()
        self.state.close()

    def wait(self):
        while not self._stopped.wait(0.5):
            pass


def _settings(config, db_path, port):
    cfg = config_object(config) if config is not None else read_config(DEFAULT_CONFIG)
    local = board_config.local(cfg)
    path = local['databasePath'] if db_path is None else db_path
    prt = local['port'] if port is None else port
    return cfg, path, prt


def serve(config=None, db_path=None, port=None, page=None, poll=None):
    """Starts serving in a background thread and returns the bound Server, with .port, .url and .stop(). Raises
    db.NetworkPath for a network database path, ValueError for a bad config, and OSError from the bind."""
    _, path, prt = _settings(config, db_path, port)
    if db.network_path(path):
        raise db.NetworkPath(path)
    srv = Server(('127.0.0.1', prt if prt is not None else 0), path, page, POLL_DEFAULT if poll is None else poll)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv=None, config=None, db_path=None, port=None, page=None, poll=None, ready=None):
    """The command line, callable in-process; returns the exit code. ready(server), when given, is called once
    the server is bound and before main() blocks, so a test can hold the instance and call .stop() on it."""
    ap = argparse.ArgumentParser(prog='server.py', description='Serve the local-first app: the page, the data snapshot and live push.')
    ap.add_argument('--port', type=int, help='override local.port (0 binds a free port)')
    ap.add_argument('--config', help='the board config (default: the repository board.config.json)')
    ap.add_argument('--poll', type=float, help='seconds between PRAGMA data_version polls (default 2)')
    try:
        args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    try:
        cfg = config_object(config) if config is not None else read_config(args.config or DEFAULT_CONFIG)
        local = board_config.local(cfg)
    except (OSError, ValueError) as e:
        warn('%s; not started' % e)
        return 2
    path = local['databasePath'] if db_path is None else db_path
    prt = port if port is not None else (args.port if args.port is not None else local['port'])
    interval = poll if poll is not None else (args.poll if args.poll is not None else POLL_DEFAULT)
    if db.network_path(path):
        warn('refusing to start: the database path %s is a network path; SQLite over SMB or NFS is unsafe (C-14)' % path)
        return 2
    try:
        srv = Server(('127.0.0.1', prt), path, page, interval)
    except OSError as e:
        warn('could not bind port %d (%s)' % (prt, e))
        return 2
    print('server: serving %s from %s' % (srv.url, path), flush=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if ready is not None:
        ready(srv)
    try:
        srv.wait()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        warn('failed (%s: %s)' % (type(e).__name__, e))
        srv.stop()
        return 1
    srv.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
