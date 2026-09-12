"""local/server.py: live push (AC-68, AC-SV9, AC-SV10), the stream cap, and running beside a real collector
pass (AC-SV11).
"""
import json, os, queue, sys, threading, time, unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(HERE, 'exporters'), os.path.join(HERE, 'local'), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import collector  # noqa: E402
import db  # noqa: E402
import server  # noqa: E402
import server_support as ss  # noqa: E402


class Live(ss.Env):
    def setUp(self):
        super().setUp()
        self._orig_poll, self._orig_heartbeat = server.POLL_DEFAULT, server.HEARTBEAT
        server.HEARTBEAT = 0.3
        self.addCleanup(setattr, server, 'HEARTBEAT', self._orig_heartbeat)

    def start_fast(self, **kw):
        return self.start(poll=0.2, **kw)

    def open_events(self, since=None, last_event_id=None):
        path = '/api/events'
        if since is not None:
            path += '?since=%d' % since
        headers = {'Last-Event-ID': str(last_event_id)} if last_event_id is not None else None
        sock, status, headers_out, rest = self.client.open_stream(path, headers=headers)
        self.addCleanup(sock.close)
        reader = ss.StreamReader(sock, rest)
        self.addCleanup(reader.close)
        return status, headers_out, reader

    def test_change_delivered_within_three_poll_intervals(self):
        self.write('run', 'r1', ss.run_doc(kind='running'))
        srv = self.start_fast()
        status, headers, reader = self.open_events()
        self.assertEqual(status, 200)
        self.assertEqual(headers.get('content-type'), 'text/event-stream; charset=utf-8')
        self.assertEqual(headers.get('cache-control'), 'no-store')
        self.assertEqual(headers.get('connection'), 'close')
        self.assertIsNone(reader.wait_for(lambda e: e.get('event') == 'change', timeout=0.5))
        self.write('run', 'r1', ss.run_doc(kind='done'))
        event = reader.wait_for(lambda e: e.get('event') == 'change', timeout=3 * 0.2 + 2)
        self.assertIsNotNone(event, reader.snapshot())
        self.assertIn('id', event)
        payload = json.loads(event['data'])
        self.assertIn('runs/r1', payload['set'])
        self.assertEqual(payload['set']['runs/r1']['doc']['kind'], 'done')
        self.assertGreater(payload['version'], 1)
        self.assertEqual(str(payload['version']), event['id'])

    def test_stream_events_hold_no_collector_state_or_answers(self):
        self.write('run', 'r1', ss.run_doc(kind='running'))
        srv = self.start_fast()
        status, headers, reader = self.open_events()
        conn = self.connect()
        conn.execute("INSERT INTO collector_sessions (id, data) VALUES ('s1', '{\"secret\": 1}')")
        conn.execute('CREATE TABLE IF NOT EXISTS answers (id TEXT PRIMARY KEY, doc TEXT)')
        conn.execute("INSERT OR REPLACE INTO answers (id, doc) VALUES ('a', '{\"answer\": \"secret-answer-text\"}')")
        conn.close()
        self.write('run', 'r1', ss.run_doc(kind='done'))
        event = reader.wait_for(lambda e: e.get('event') == 'change', timeout=3)
        self.assertIsNotNone(event)
        self.assertNotIn('collector_', event['data'])
        self.assertNotIn('secret-answer-text', event['data'])
        self.assertNotIn('answers', event['data'])

    def test_deleted_record_arrives_in_deleted(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        status, headers, reader = self.open_events()
        conn = self.connect()
        db.delete(conn, 'run', 'r1')
        conn.close()
        event = reader.wait_for(lambda e: e.get('event') == 'change', timeout=3)
        self.assertIsNotNone(event)
        payload = json.loads(event['data'])
        self.assertIn('runs/r1', payload['deleted'])

    def test_retry_line_sent_at_open(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        status, headers, reader = self.open_events()
        event = reader.wait_for(lambda e: e.get('retry') == '3000', timeout=1)
        self.assertIsNotNone(event, reader.snapshot())

    def test_current_since_no_reset_stale_gives_reset_with_id(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        resp, body = self.client.get('/api/snapshot')
        current = json.loads(body)['version']
        status, headers, reader = self.open_events(since=current)
        time.sleep(0.5)
        self.assertIsNone(reader.wait_for(lambda e: e.get('event') == 'reset', timeout=0.1))
        reader.close()

        status2, headers2, reader2 = self.open_events(since=1000000)
        event = reader2.wait_for(lambda e: e.get('event') == 'reset', timeout=2)
        self.assertIsNotNone(event)
        self.assertIn('id', event)
        self.assertEqual(json.loads(event['data'])['version'], int(event['id']))

    def test_an_unparsable_position_gives_a_reset(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        status, headers, reader = self.open_events(last_event_id='not-a-number')
        event = reader.wait_for(lambda e: e.get('event') == 'reset', timeout=3)
        self.assertIsNotNone(event, reader.snapshot())

    def test_no_reset_loop_after_obeying_a_reset(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        status, headers, reader = self.open_events(since=1)
        # Force a real change so the version is ahead of "since=1" is guaranteed even if 1 happened to be current.
        self.write('run', 'r1', ss.run_doc(kind='done'))
        resp, body = self.client.get('/api/snapshot')
        version = json.loads(body)['version']
        reader.close()
        status2, headers2, reader2 = self.open_events(last_event_id=version)
        time.sleep(1.0)
        self.assertIsNone(reader2.wait_for(lambda e: e.get('event') == 'reset', timeout=0.1))

    def test_larger_of_since_and_last_event_id_wins_either_way(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        resp, body = self.client.get('/api/snapshot')
        current = json.loads(body)['version']
        status, _, reader = self.open_events(since=current, last_event_id=1)
        time.sleep(0.4)
        self.assertIsNone(reader.wait_for(lambda e: e.get('event') == 'reset', timeout=0.1))
        reader.close()
        status2, _, reader2 = self.open_events(since=1, last_event_id=current)
        time.sleep(0.4)
        self.assertIsNone(reader2.wait_for(lambda e: e.get('event') == 'reset', timeout=0.1))

    def test_heartbeat_arrives_within_twice_the_interval_and_disconnect_is_dropped(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        status, headers, reader = self.open_events()
        event = reader.wait_for(lambda e: 'comment' in e, timeout=2 * server.HEARTBEAT + 1)
        self.assertIsNotNone(event)

    def test_poll_count_stops_with_no_clients_and_resumes_on_connect(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start(poll=0.1)
        calls = {'n': 0}
        real_poll = db.Changes.poll

        def counted(self):
            calls['n'] += 1
            return real_poll(self)

        with mock.patch.object(db.Changes, 'poll', counted):
            status, headers, reader = self.open_events()
            time.sleep(0.5)
            self.assertGreater(calls['n'], 0)
            reader.close()
            # Detecting a closed socket needs a write attempt to fail, which can lag AC-SV10's stated tolerance
            # (one heartbeat plus one poll interval) under load; wait for the count to go quiet across two
            # consecutive windows, rather than a fixed sleep that a busy machine could outrun, then confirm it
            # stays quiet over a further window.
            deadline, stable_since, prev = time.time() + 8, None, -1
            while time.time() < deadline:
                if calls['n'] == prev:
                    if stable_since and time.time() - stable_since >= 0.6:
                        break
                    stable_since = stable_since or time.time()
                else:
                    stable_since = None
                prev = calls['n']
                time.sleep(0.1)
            n1 = calls['n']
            time.sleep(0.4)
            n2 = calls['n']
            self.assertEqual(n1, n2)
            status2, headers2, reader2 = self.open_events()
            time.sleep(0.5)
            self.assertGreater(calls['n'], n2)

    def registered(self, srv, n, timeout=5):
        """The hub's registered clients, once there are exactly n of them."""
        clients = set()
        deadline = time.time() + timeout
        while time.time() < deadline:
            with srv.hub.lock:
                clients = set(srv.hub.clients)
            if len(clients) == n:
                return clients
            time.sleep(0.02)
        self.fail('expected %d registered stream(s), found %d' % (n, len(clients)))

    def test_no_client_can_stall_another(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start(poll=0.1)
        calls = {'n': 0}
        real_poll = db.Changes.poll

        def counted(self):
            calls['n'] += 1
            return real_poll(self)

        # A stream that really stalls: a tiny receive window so the peer cannot keep sending, no recv() at all,
        # and events large enough to fill the send buffer within a change or two. Its own queue is shrunk to 2
        # so the overflow follows immediately rather than needing 32 buffered events.
        big = 'x' * 60000
        with mock.patch.object(server, 'QUEUE_MAXSIZE', 2), mock.patch.object(db.Changes, 'poll', counted):
            sock_stalled, status1, _, _ = self.client.open_stream(rcvbuf=512)
            self.addCleanup(sock_stalled.close)
            self.assertEqual(status1, 200)
            stalled = next(iter(self.registered(srv, 1)))
            status2, headers2, reader2 = self.open_events()
            for i in range(40):
                self.write('run', 'r1', ss.run_doc(kind='done' if i % 2 else 'running', label=big, tok=i))
                event = reader2.wait_for(lambda e: e.get('event') == 'change', timeout=5)
                self.assertIsNotNone(event, 'the healthy stream stalled at change %d' % i)
                del reader2.events[:]
                if stalled.overflowed:
                    break
            polls = calls['n']
            self.assertTrue(stalled.overflowed, 'the stalled client never overflowed its bounded queue')
            with srv.hub.lock:
                self.assertNotIn(stalled, srv.hub.clients, 'the overflowed client was not dropped from the hub')
            # The watcher survives the drop: it keeps polling and the healthy stream keeps receiving.
            deadline = time.time() + 5
            while time.time() < deadline and calls['n'] <= polls:
                time.sleep(0.05)
            self.assertGreater(calls['n'], polls, 'the poll counter stopped rising after the stalled client')
            self.write('run', 'r1', ss.run_doc(kind='killed', tok=99))
            self.assertIsNotNone(reader2.wait_for(lambda e: e.get('event') == 'change', timeout=5),
                                 'the healthy stream stopped receiving after the stalled client was dropped')
        resp, _ = self.client.get('/api/snapshot')
        self.assertEqual(resp.status, 200)

    def test_a_commit_between_the_position_read_and_registration_still_reaches_the_client(self):
        self.write('run', 'r1', ss.run_doc(kind='running'))
        srv = self.start(poll=0.2)
        resp, body = self.client.get('/api/snapshot')
        current = json.loads(body)['version']
        real_register = server.Hub.register

        def commit_then_register(hub):
            # A collector commit landing in the window between the two calls the stream makes. Whichever order
            # they run in, the client must not be left judged current against a version that already missed it.
            self.write('run', 'r1', ss.run_doc(kind='done'))
            return real_register(hub)

        with mock.patch.object(server.Hub, 'register', commit_then_register):
            status, headers, reader = self.open_events(since=current)
        event = reader.wait_for(lambda e: e.get('event') in ('reset', 'change'), timeout=5)
        self.assertIsNotNone(event, 'a commit racing the stream open was neither pushed nor reset')

    def test_ninth_stream_gets_503(self):
        self.write('run', 'r1', ss.run_doc())
        srv = self.start_fast()
        socks = []
        try:
            for _ in range(server.MAX_STREAMS):
                sock, status, _, _ = self.client.open_stream()
                socks.append(sock)
                self.assertEqual(status, 200)
            resp, body = self.client.get('/api/events')
            self.assertEqual(resp.status, 503)
            self.assertEqual(resp.getheader('Retry-After'), '5')
        finally:
            for s in socks:
                s.close()


class _StubState:
    """A State stand-in for the hub: refresh() hands back whatever records have been set and a version that rises
    with them, counts its calls so the watcher's polling can be observed, and can be held inside refresh() so the
    window between one watcher being told to stop and the thread actually exiting can be opened deliberately."""

    def __init__(self):
        self.lock = threading.Lock()
        self.version, self.records, self.calls = 1, {}, 0
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()

    def hold(self):
        self.release.clear()

    def set_records(self, records_map):
        with self.lock:
            self.version += 1
            self.records = dict(records_map)

    def refresh(self):
        self.entered.set()
        self.release.wait(10)
        with self.lock:
            self.calls += 1
            return self.version, dict(self.records), {}, []


def _record(rid, kind='done'):
    return {'kind': 'run', 'id': rid, 'doc': ss.run_doc(kind=kind)}


class HubDirect(unittest.TestCase):
    """The hub driven without sockets, so the paths a real stream's own draining hides - the bounded queue
    overflowing (§7.1, AC-SV10) and the watcher lifecycle - are really executed.
    """

    def hub(self, state, poll=0.05):
        hub = server.Hub(state, poll)
        self.addCleanup(lambda: hub.stop.set() if hub.stop is not None else None)
        return hub

    def next_event(self, client, why, timeout=5):
        try:
            return client.queue.get(timeout=timeout)
        except queue.Empty:
            self.fail(why)

    def test_a_client_that_never_drains_overflows_and_is_dropped(self):
        state = _StubState()
        hub = self.hub(state)
        stalled, healthy = hub.register(), hub.register()
        for i in range(server.QUEUE_MAXSIZE):
            stalled.queue.put_nowait(b'filler %d\n\n' % i)  # nothing ever drains this one
        self.assertTrue(stalled.queue.full())

        state.set_records({'runs/r1': _record('r1')})
        item = self.next_event(healthy, 'the healthy client received nothing')
        self.assertIn(b'event: change', item)
        self.assertIn(b'runs/r1', item)
        self.assertTrue(stalled.overflowed, 'the full queue was not marked overflowed')
        with hub.lock:
            self.assertNotIn(stalled, hub.clients, 'the overflowed client was not dropped')
            self.assertIn(healthy, hub.clients)

        before = state.calls
        state.set_records({'runs/r1': _record('r1'), 'runs/r2': _record('r2')})
        self.assertIn(b'runs/r2', self.next_event(healthy, 'the watcher stopped pushing after the drop'))
        self.assertGreater(state.calls, before, 'the watcher stopped polling after the drop')

    def test_a_stream_registering_while_the_watcher_exits_gets_its_own_watcher(self):
        state = _StubState()
        state.hold()  # the first watcher blocks inside its baseline refresh(), widening the window
        hub = self.hub(state)
        first = hub.register()
        self.assertTrue(state.entered.wait(5))
        hub.unregister(first)  # tells that watcher to stop while its thread is still alive
        second = hub.register()
        state.release.set()

        deadline = time.time() + 2
        while time.time() < deadline and state.calls < 2:
            time.sleep(0.02)
        state.set_records({'runs/r1': _record('r1')})
        item = self.next_event(second, 'no change reached a stream that opened while the watcher was exiting')
        self.assertIn(b'runs/r1', item)
        self.assertTrue(hub.watcher.is_alive())


class BesideACollector(ss.Env):
    def test_snapshot_and_stream_survive_a_real_collector_pass(self):
        import tempfile
        projects_root = tempfile.mkdtemp(dir=self.tmp)
        cfg = {'sessions': {'days': 7, 'projectsRoot': projects_root},
              'catalogue': {'marketplacePath': os.path.join(self.tmp, 'no-market'),
                            'installedPath': os.path.join(self.tmp, 'no-installed.json')}}
        conn = db.open_db(self.db_path)
        conn.close()
        srv = self.start(poll=0.1)
        sock, status, _, rest = self.client.open_stream()
        self.addCleanup(sock.close)
        reader = ss.StreamReader(sock, rest)
        self.addCleanup(reader.close)

        writer = db.open_db(self.db_path)
        try:
            report = collector.run_pass(writer, cfg, projects_root=projects_root, now=time.time())
            self.assertIsNotNone(report)
            resp, body = self.client.get('/api/snapshot')
            self.assertEqual(resp.status, 200)
            payload = json.loads(body)
            self.assertIn('meta/lastRefresh', payload['records'])
            event = reader.wait_for(lambda e: e.get('event') == 'change', timeout=3)
            self.assertIsNotNone(event)
        finally:
            writer.close()

    def test_snapshot_still_answers_with_another_connection_holding_begin_immediate(self):
        conn = db.open_db(self.db_path)
        conn.close()
        srv = self.start()
        holder = db.open_db(self.db_path)
        holder.execute('BEGIN IMMEDIATE')
        try:
            resp, body = self.client.get('/api/snapshot')
            self.assertEqual(resp.status, 200)
        finally:
            holder.execute('ROLLBACK')
            holder.close()


if __name__ == '__main__':
    unittest.main()
