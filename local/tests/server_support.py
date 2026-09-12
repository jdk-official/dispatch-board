"""Shared helpers for the server tests: a throwaway database and page file, a running server per test, and a
small HTTP client with full control over the Host and Origin headers (needed to test the gate) and over raw,
possibly malformed request bytes. Not a test module (its name does not match test*.py).
"""
import http.client, os, shutil, socket, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(HERE, 'exporters'), os.path.join(HERE, 'local')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import db  # noqa: E402
import records  # noqa: E402
import server  # noqa: E402

PAGE = ('<title>Board</title>\n<p id="content">hello</p>\n<script>var x = 1;</script>\n')


def session_doc(**over):
    d = {'title': 't', 'folder': 'f', 'cwd': 'c', 'start': None, 'last': None, 'project': None, 'build': False,
        'windowDays': 7, 'windowMinutes': 10, 'runs': 0, 'running': 0, 'usage': {}, 'skillUses': {}}
    d.update(over)
    return d


def run_doc(**over):
    d = {'session': 's1', 'project': None, 'seq': 1, 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'v',
        'tok': 1, 'min': 1}
    d.update(over)
    return d


def project_doc(**over):
    d = {'name': 'n', 'repoPath': 'r', 'branch': 'b', 'sessions': [], 'statusDoc': 'status/p1', 'order': 0,
        'runs': 0, 'running': 0, 'last': None, 'usage': None}
    d.update(over)
    return d


def tab_doc(**over):
    d = {'generatedAt': '2026-01-01T00:00:00Z'}
    d.update(over)
    return d


def status_doc(**over):
    d = {}
    d.update(over)
    return d


def last_refresh_doc(**over):
    d = {'at': '2026-01-01T00:00:00+00:00', 'writer': 'collector'}
    d.update(over)
    return d


def catalogue_doc(**over):
    d = {'generatedAt': '2026-01-01T00:00:00Z', 'plugins': [], 'entries': []}
    d.update(over)
    return d

DOC_FACTORIES = {'session': session_doc, 'run': run_doc, 'project': project_doc, 'tab': tab_doc,
                'status': status_doc, 'lastRefresh': last_refresh_doc, 'catalogue': catalogue_doc}
# One conforming (kind, id) per kind, ready to write with Env.write(*ONE['kind']).
ONE = {'session': ('session', 's1', session_doc()), 'run': ('run', 'r1', run_doc()),
      'project': ('project', 'p1', project_doc()), 'tab': ('tab', 'p1.spec', tab_doc()),
      'status': ('status', 'status/p1', status_doc()), 'lastRefresh': ('lastRefresh', 'lastRefresh', last_refresh_doc()),
      'catalogue': ('catalogue', 'index', catalogue_doc())}


def raw_request(port, data, timeout=5):
    """The raw bytes a socket sends and receives; used for malformed or oversized requests http.client refuses
    to build (a bad request line, too many headers, a header line too long, a method outside the six)."""
    s = socket.create_connection(('127.0.0.1', port), timeout=timeout)
    try:
        s.sendall(data)
        s.settimeout(timeout)
        chunks = []
        try:
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except socket.timeout:
            pass
        return b''.join(chunks)
    finally:
        s.close()


def parse_status(raw):
    line = raw.split(b'\r\n', 1)[0]
    return int(line.split(b' ')[1])


def parse_head(raw):
    """(status, {header: value}, body) from raw response bytes; headers folded to lower case."""
    head, _, body = raw.partition(b'\r\n\r\n')
    lines = head.split(b'\r\n')
    status = int(lines[0].split(b' ')[1])
    headers = {}
    for line in lines[1:]:
        if b':' in line:
            k, _, v = line.partition(b':')
            headers[k.decode('latin-1').strip().lower()] = v.decode('latin-1').strip()
    return status, headers, body


class Client:
    """A small HTTP client with explicit control over Host and Origin (None omits the header)."""

    def __init__(self, port):
        self.port = port

    def request(self, method, path, host='default', origin=None, headers=None, timeout=5):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=timeout)
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        if host == 'default':
            host = '127.0.0.1:%d' % self.port
        if host is not None:
            conn.putheader('Host', host)
        if origin is not None:
            conn.putheader('Origin', origin)
        for k, v in (headers or {}).items():
            conn.putheader(k, v)
        conn.endheaders()
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    def get(self, path, **kw):
        return self.request('GET', path, **kw)

    def head(self, path, **kw):
        return self.request('HEAD', path, **kw)

    def raw(self, data, timeout=5):
        return raw_request(self.port, data, timeout=timeout)

    def open_stream(self, path='/api/events', host='default', origin=None, headers=None, timeout=5, rcvbuf=None):
        """A live socket with the request already sent and the status line and headers already read; the caller
        reads the body incrementally. Returns (sock, status, headers).

        rcvbuf shrinks the socket's receive buffer, which is how a caller makes a stream it never reads really
        stall: the window is negotiated during the handshake, so it has to be set before connect()."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if rcvbuf is not None:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
        s.settimeout(timeout)
        s.connect(('127.0.0.1', self.port))
        if host == 'default':
            host = '127.0.0.1:%d' % self.port
        lines = ['GET %s HTTP/1.1' % path]
        if host is not None:
            lines.append('Host: %s' % host)
        if origin is not None:
            lines.append('Origin: %s' % origin)
        for k, v in (headers or {}).items():
            lines.append('%s: %s' % (k, v))
        lines.append('')
        lines.append('')
        s.sendall('\r\n'.join(lines).encode('ascii'))
        s.settimeout(timeout)
        buf = b''
        while b'\r\n\r\n' not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        head, _, rest = buf.partition(b'\r\n\r\n')
        lines = head.split(b'\r\n')
        status = int(lines[0].split(b' ')[1])
        headers_out = {}
        for line in lines[1:]:
            if b':' in line:
                k, _, v = line.partition(b':')
                headers_out[k.decode('latin-1').strip().lower()] = v.decode('latin-1').strip()
        return s, status, headers_out, rest


class StreamReader:
    """Reads Server-Sent Events off a live socket in a background thread, buffering complete events."""

    def __init__(self, sock, leftover=b''):
        import threading
        self.sock, self.buf, self.events, self.lock = sock, leftover, [], threading.Lock()
        self.stopped = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stopped:
            try:
                chunk = self.sock.recv(65536)
            except OSError:
                break
            if not chunk:
                break
            with self.lock:
                self.buf += chunk
                self._extract()

    def _extract(self):
        while b'\n\n' in self.buf:
            raw, self.buf = self.buf.split(b'\n\n', 1)
            event = {}
            for line in raw.split(b'\n'):
                if line.startswith(b':'):
                    event['comment'] = line[1:].strip()
                    continue
                if b':' in line:
                    k, _, v = line.partition(b':')
                    event[k.decode('ascii')] = v.decode('utf-8').strip()
            if event:
                self.events.append(event)

    def wait_for(self, predicate, timeout=10):
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                for e in self.events:
                    if predicate(e):
                        return e
            time.sleep(0.05)
        return None

    def snapshot(self):
        with self.lock:
            return list(self.events)

    def close(self):
        self.stopped = True
        try:
            self.sock.close()
        except OSError:
            pass


class Env(unittest.TestCase):
    """A temporary database and page file, and a running server bound to them; call self.start() after writing
    any fixture records. Everything is cleaned up automatically."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='server-test-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db_path = os.path.join(self.tmp, 'db', 'board.db')
        self.page_path = os.path.join(self.tmp, 'index.html')
        with open(self.page_path, 'w', encoding='utf-8') as f:
            f.write(PAGE)
        self.srv = None

    def tearDown(self):
        if self.srv is not None:
            self.srv.stop()

    def connect(self):
        return db.open_db(self.db_path)

    def write(self, kind, rid, doc):
        conn = self.connect()
        try:
            db.upsert(conn, kind, records.to_row(kind, rid, doc))
        finally:
            conn.close()

    def start(self, page=None, poll=None, port=0):
        # An explicit config, so no test reads the repository's committed board.config.json: the arguments
        # below override both of its values anyway, and reading it would couple every server test to it.
        config = {'local': {'databasePath': self.db_path, 'port': 8765}}
        self.srv = server.serve(config=config, db_path=self.db_path, port=port, page=page or self.page_path,
                                poll=poll)
        self.client = Client(self.srv.port)
        return self.srv
