"""The local-first app's collector: follows the Claude Code transcripts as they grow and writes session, run,
project, tab, status, catalogue and last-refresh records into the local SQLite database. It is the database's
only writer.

    python local/collector.py [--once] [--allow-mass-delete] [--interval SECONDS] [--config PATH]

For the same transcripts, config and time, the database holds exactly the documents export_sessions.py writes:
every derivation comes from exporters/derive.py and the exporter's own helpers, and only the few lines that
assemble rows across sessions are repeated here. The tab and status records are local/tabs.py's, and hold
export_board.py's documents and refresh.py's status rule under the same guarantee.

A transcript already read is reopened only for its new bytes. How far each file was read (its cursor) and the
derivation state its lines built are kept in the collector_* tables, committed in the same transaction as the
records they produced, so a crash can neither count a line twice nor lose it, and a restart carries on where the
last pass stopped. Excluded sessions leave only a marker holding the file's device, file id, size and a digest of
the exclude list: nothing that names or describes the session.

A pass is refused, and writes nothing at all, when it would delete more than half of the stored runs and sessions
other than by age, finds no sessions but would still delete one other than by age, or would delete a project or the
catalogue; --once --allow-mass-delete lets one such pass through. Exit codes with --once: 0 after a committed pass,
2 after a refusal, 1 after any other failure (another collector holding the lock included).
"""
import argparse, contextlib, copy, glob, hashlib, io, json, os, shutil, sqlite3, sys, tempfile, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(HERE, 'exporters'), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import board_config  # noqa: E402
import db  # noqa: E402
import derive  # noqa: E402
import export_catalogue  # noqa: E402
import export_sessions  # noqa: E402
import records  # noqa: E402
import tabs  # noqa: E402

CONFIG = os.path.join(HERE, 'board.config.json')
STATE_VERSION = 1  # bump when the layout of the stored state changes, to read every transcript again once
KINDS = ('session', 'run', 'project')
# The kinds a pass may delete, and the kinds it upserts before the status records, which depend on what those
# writes changed. status is in neither: refresh.py never deletes a status document, and nor does a pass here.
DELETABLE = KINDS + ('tab',)
UPSERTED = KINDS + ('catalogue', 'tab')
# What storing one record may raise without costing the rest of the pass.
RECORD_ERRORS = (ValueError, UnicodeEncodeError, RecursionError, TypeError, OverflowError, sqlite3.DataError)
CURSOR_KEYS = {'path', 'dev', 'ino', 'offset', 'size', 'mtime'}
SESSION_KEYS = {'v', 'parser', 'window', 'main', 'state', 'result'}
AGENT_KEYS = {'cursor', 'state', 'meta', 'metaSig'}
RESULT_KEYS = {'doc', 'rows', 'skipped'}  # derive.session_result's output


class Refusal(Exception):
    """The pass was refused and wrote nothing (exit 2)."""


def warn(msg):
    print('collector: ' + msg, file=sys.stderr)


def _open(path):
    return io.open(path, 'rb')


# --- the state codec -----------------------------------------------------------
# derive's running state is not JSON as it stands: skillCalls is a set, and several maps have None keys. One
# generic tagged form covers any mix of these types, so a field added to derive later needs no change here.

def _enc(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, list):
        return [_enc(x) for x in v]
    if isinstance(v, dict):
        if all(isinstance(k, str) and k != '$' for k in v):
            return {k: _enc(x) for k, x in v.items()}
        return {'$': 'map', 'v': [[_enc(k), _enc(x)] for k, x in v.items()]}
    for kind, tag in ((frozenset, 'frozenset'), (set, 'set'), (tuple, 'tuple')):
        if isinstance(v, kind):
            return {'$': tag, 'v': [_enc(x) for x in v]}
    raise TypeError('the collector cannot store a %s' % type(v).__name__)


def _dec(v):
    if isinstance(v, list):
        return [_dec(x) for x in v]
    if isinstance(v, dict):
        if '$' not in v:
            return {k: _dec(x) for k, x in v.items()}
        items = v['v']
        if v['$'] == 'map':
            return {_dec(k): _dec(x) for k, x in items}
        return {'set': set, 'frozenset': frozenset, 'tuple': tuple}[v['$']](_dec(x) for x in items)
    return v


def encode(value):
    """JSON text for a value built from None, bool, int, float, str, list, tuple, set, frozenset and dict (any
    hashable keys), keeping every container's type and every dict's key order. ASCII only, so a lone surrogate is
    stored as an escape. Raises TypeError for any other type."""
    return json.dumps(_enc(value), ensure_ascii=True)


def decode(text):
    return _dec(json.loads(text))


def _decoded(text):
    try:
        v = decode(text)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return None
    return v if isinstance(v, dict) else None


# --- incremental reads -----------------------------------------------------------

def read_new(cursor, path):
    """(lines, new cursor, reset): the complete lines appended to path since cursor. reset is True when the file
    was replaced (another file id) or truncated, and the lines are then the whole file. An unchanged file is not
    opened. A trailing line without its newline is left for the next read. The cursor given is never changed."""
    s = os.stat(path)
    offset, reset = (cursor or {}).get('offset', 0), False
    if cursor and ((cursor['ino'] and (s.st_dev, s.st_ino) != (cursor['dev'], cursor['ino'])) or s.st_size < offset):
        offset, reset = 0, True
    new = {'path': path, 'dev': s.st_dev, 'ino': s.st_ino, 'offset': offset, 'size': s.st_size, 'mtime': s.st_mtime}
    if s.st_size == offset:
        return [], new, reset
    with _open(path) as f:
        f.seek(offset)
        chunk = f.read(s.st_size - offset)
    cut = chunk.rfind(b'\n') + 1
    new['offset'] = offset + cut
    # The same decoder and newline handling as the exporter's io.open(path, encoding='utf-8', errors='replace').
    return list(io.TextIOWrapper(io.BytesIO(chunk[:cut]), encoding='utf-8', errors='replace')), new, reset


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _cursor_ok(c):
    return c is None or (isinstance(c, dict) and set(c) == CURSOR_KEYS and isinstance(c['path'], str)
                         and all(_int(c[k]) and c[k] >= 0 for k in ('dev', 'ino', 'offset', 'size'))
                         and isinstance(c['mtime'], (int, float)) and not isinstance(c['mtime'], bool))


def _result_ok(r):
    return r is None or (isinstance(r, dict) and set(r) == RESULT_KEYS and isinstance(r['doc'], dict)
                         and isinstance(r['rows'], list) and all(isinstance(x, dict) for x in r['rows'])
                         and isinstance(r['skipped'], list))


# A stored row is used only when its whole layout is the one this code writes; anything else, like text that does
# not decode, resets that session (or agent) and reads its files from 0 once, rather than failing every pass.
def _session_ok(entry, sid):
    return (isinstance(entry, dict) and set(entry) == SESSION_KEYS and entry['v'] == STATE_VERSION
            and entry['parser'] == export_sessions.PARSER_VERSION and _cursor_ok(entry['main'])
            and isinstance(entry['state'], dict) and set(entry['state']) == set(derive.new_session(sid))
            and _result_ok(entry['result']))


def _agent_ok(entry):
    return (isinstance(entry, dict) and set(entry) == AGENT_KEYS and _cursor_ok(entry['cursor'])
            and isinstance(entry['state'], dict) and set(entry['state']) == set(derive.new_agent()))


def _sig(path):
    try:
        s = os.stat(path)
    except OSError:
        return None
    return [s.st_mtime, s.st_size]


def post_feed_excluded(st, folder, state):
    """True when a session's first cwd, possibly only just read, puts it under sessions.exclude."""
    return bool(st['exclude']) and bool(state['cwd']) and derive.excluded(st['exclude'], folder, state['cwd'])


# --- the in-memory cache ---------------------------------------------------------
# Decoded state kept between passes of a long-running collector, valid only for the connection that loaded it and
# only while no other connection has committed since (PRAGMA data_version).
_cache = {}


def forget():
    _cache.clear()


def _load(conn):
    version = conn.execute('PRAGMA data_version').fetchone()[0]
    if _cache.get('conn') is conn and _cache.get('version') == version:
        return _cache
    agents = {}
    for sid, aid, text in conn.execute('SELECT session, agent, data FROM collector_agents'):
        agents.setdefault(sid, {})[aid] = (text, _decoded(text))
    _cache.clear()
    _cache.update(conn=conn, version=version, agents=agents,
                  sessions={sid: (text, _decoded(text)) for sid, text in conn.execute('SELECT id, data FROM collector_sessions')},
                  markers={(dev, ino): (size, rule) for dev, ino, size, rule in
                           conn.execute('SELECT dev, ino, size, rule FROM collector_excluded')})
    return _cache


# --- one pass --------------------------------------------------------------------

class _Agents:
    """What one session's agent files gave this pass: the entries to store, the summaries and rows in the
    exporter's order, the agents skipped, the agent ids present on disk, and the bytes read."""

    def __init__(self):
        self.entries, self.subs, self.rows, self.skipped, self.present, self.bytes = {}, [], [], [], set(), 0


def _needs_rederive(old_result):
    """True when a stored result must be re-derived though no file changed: a running row can turn killed as time
    passes, and a skipped agent's kept row waits for its file to read again."""
    return bool(old_result and (old_result.get('skipped') or any(r['kind'] == 'running' for r in old_result['rows'])))


class _Pass:
    def __init__(self, conn, st, t0, cache):
        self.conn, self.st, self.t0, self.cache = conn, st, t0, cache
        self.limit = st['days'] * 86400
        self.rule = hashlib.sha256(json.dumps(st['exclude']).encode('utf-8')).hexdigest()
        self.results, self.why = {}, {}  # why: sid -> 'age' for a session the window dropped
        self.sessions_out, self.agents_out, self.agents_del, self.drop = {}, {}, set(), set()
        self.markers, self.seen = dict(cache['markers']), set()
        self.bytes = self.rederived = 0

    def excluded(self, folder, path, s, key, entry):
        """Decided from the folder, the cwd already in state, or a marker, before falling back to reading the start
        of the file as the exporter does."""
        pats = self.st['exclude']
        if derive.excluded(pats, folder, ''):
            return True
        cur = entry and entry['main']
        # A first cwd never changes in a file that is only appended to, so the one in state stands while the
        # file is the same one and has not shrunk.
        if cur and entry['state']['cwd'] and s.st_size >= cur['offset'] and \
                (not cur['ino'] or (cur['dev'], cur['ino']) == (s.st_dev, s.st_ino)):
            return derive.excluded(pats, folder, entry['state']['cwd'])
        m = self.markers.get(key)
        if m:
            if s.st_size >= m[0] and m[1] == self.rule:
                self.markers[key] = (s.st_size, self.rule)
                return True
            del self.markers[key]  # replaced in place, truncated or a new exclude list: decide again
        cwd = export_sessions.cwd_of(path)
        out = derive.excluded(pats, folder, cwd)
        if out and cwd and s.st_ino:
            self.markers[key] = (s.st_size, self.rule)
        return out

    def discover(self, mains, found):
        st = self.st
        self.present = found
        for main_path in mains:
            base, sid = os.path.dirname(main_path), os.path.basename(main_path)[:-len('.jsonl')]
            try:
                s = os.stat(main_path)
            except OSError as e:
                if not isinstance(e, FileNotFoundError):
                    warn('session %s skipped (%s: %s)' % (sid, type(e).__name__, e))
                continue
            key = (str(s.st_dev), str(s.st_ino))
            self.seen.add(key)
            if sid not in st['build'] and self.t0 - s.st_mtime > self.limit:
                self.why[sid] = 'age'
                self.drop.add(sid)
                continue
            stored = self.cache['sessions'].get(sid)
            entry = stored[1] if stored and _session_ok(stored[1], sid) else None
            try:
                if st['exclude'] and self.excluded(os.path.basename(base), main_path, s, key, entry):
                    self.drop.add(sid)
                    continue
            except OSError as e:
                if not isinstance(e, FileNotFoundError):
                    warn('session %s skipped (%s: %s)' % (sid, type(e).__name__, e))
                continue
            self.session(base, sid, main_path, entry)
        # A vanished main transcript takes its session's state, agents included, with it.
        self.drop |= (set(self.cache['sessions']) | set(self.cache['agents'])) - self.present

    def session(self, base, sid, main_path, entry):
        """Read, feed and re-derive one session. Everything from reading its main transcript up to encoding its new
        state runs inside the one try below: any raise there is a main-transcript failure, and since _derive stages
        nothing before its last step, the session keeps its stored state, cursors and result."""
        fresh = entry is None
        if fresh:  # new, or its stored state was reset: every file of the session is read from the start
            entry = {'v': STATE_VERSION, 'parser': export_sessions.PARSER_VERSION, 'window': self.st['window'],
                     'main': None, 'state': derive.new_session(sid), 'result': None}
        cached_agents = self.cache['agents'].get(sid, {})
        old_result = entry['result']
        try:
            done = self._derive(base, sid, main_path, entry, fresh, cached_agents)
        except Exception as e:
            self._keep(sid, fresh, old_result, e)
            return
        if done is None:  # its first cwd, only just read, excludes it
            return
        nbytes, result = done
        self.bytes += nbytes
        self.judge(sid, result)

    def _derive(self, base, sid, main_path, entry, fresh, cached_agents):
        """(bytes read, result), staging the session's new state; None for a session the post-feed exclusion check
        drops. Raises on a main-transcript failure."""
        st = self.st
        state, cursor, reset = self._feed_main(sid, main_path, entry)
        nbytes = cursor['offset'] - (entry['main']['offset'] if entry['main'] and not reset else 0)
        changed = fresh or reset or cursor != entry['main'] or entry['window'] != st['window']
        ag = self._agents(base, sid, state, fresh, cached_agents)
        agents_del = {aid for aid in cached_agents if aid not in ag.present or (fresh and aid not in ag.entries)}
        changed = changed or bool(ag.entries) or bool(agents_del) or bool(ag.skipped)
        if post_feed_excluded(st, os.path.basename(base), state):
            self.drop.add(sid)
            return None
        old_result = entry['result']
        if changed or _needs_rederive(old_result):
            result = self._rederive(state, ag, old_result)
        else:
            result = old_result
        if changed or result is not old_result:
            self._stage(sid, entry, cursor, state, result, ag.entries, agents_del)
        return nbytes + ag.bytes, result

    def _feed_main(self, sid, main_path, entry):
        """(state, cursor, reset): the main transcript's new lines fed into a copy of its state, never the stored one."""
        lines, cursor, reset = read_new(entry['main'], main_path)
        state = entry['state']
        if reset or lines:  # fed on a copy, kept only if every line goes in
            state = derive.new_session(sid) if reset else copy.deepcopy(state)
            for raw, o in derive.record_pairs(lines):
                derive.add_record(state, o, raw, warn)
        return state, cursor, reset

    def _agents(self, base, sid, state, fresh, cached_agents):
        """Every agent file of the session, in the exporter's order. A file whose read or derivation raises is
        skipped with a warning and costs only that agent: its stored state and cursor stay."""
        ag = _Agents()
        paths = sorted(glob.glob(os.path.join(base, sid, 'subagents', 'agent-*.jsonl')))
        for path in paths:
            aid = os.path.basename(path)[len('agent-'):-len('.jsonl')]
            old = None if fresh else (cached_agents.get(aid) or (None, None))[1]
            a = old if _agent_ok(old) else None
            try:
                sub, row, acur, areset, astate, meta, msig = self._agent(path, aid, state, a)
            except Exception as e:  # one unreadable agent must not hide the rest of the session
                warn('session %s: agent %s skipped (%s: %s)' % (sid, aid, type(e).__name__, e))
                ag.skipped.append(aid)
                continue
            # Outside the agent's try: a raise here is the session's failure, not this agent's.
            ag.bytes += acur['offset'] - (a['cursor']['offset'] if a and a['cursor'] and not areset else 0)
            if not a or acur != a['cursor'] or msig != a.get('metaSig'):
                ag.entries[aid] = {'cursor': acur, 'state': astate, 'meta': meta, 'metaSig': msig}
            ag.subs.append(sub)
            ag.rows.append(row)
        ag.present = {os.path.basename(p)[len('agent-'):-len('.jsonl')] for p in paths}
        return ag

    def _agent(self, path, aid, state, a):
        """(sub, row, cursor, reset, state, meta, metaSig) for one agent file, fed on a copy of its stored entry a
        (None when it has none)."""
        alines, acur, areset = read_new(a['cursor'] if a else None, path)
        astate = a['state'] if a else derive.new_agent()
        if areset or alines or not a:
            astate = derive.new_agent() if (areset or not a) else copy.deepcopy(astate)
            for _, o in derive.record_pairs(alines):
                derive.add_agent(astate, o)
        mpath = path[:-len('.jsonl')] + '.meta.json'
        msig = _sig(mpath)
        meta = a['meta'] if a and a.get('metaSig') == msig and isinstance(a.get('meta'), dict) \
            else export_sessions.load_meta(mpath)
        sub = derive.agent_summary(astate)
        row = derive.agent_row(state, aid, meta, sub, self.t0 - acur['mtime'], self.st['window'])
        return sub, row, acur, areset, astate, meta, msig

    def _rederive(self, state, ag, old_result):
        if not state['by']:
            result = None  # nothing was ever answered in this session
        else:
            result = derive.session_result(state, ag.subs, ag.rows, ag.skipped)
            if result['skipped']:
                # Until it reads again, a skipped agent keeps its last row, so its run is not deleted.
                result['rows'] += [derive.carried(r, self.st['window'], self.t0) for r in (old_result or {}).get('rows', [])
                                   if r['id'] in result['skipped']]
        self.rederived += 1
        return result

    def _stage(self, sid, entry, cursor, state, result, agents, agents_del):
        """Queue the session's new state for write_state. Every encode runs before anything is queued, so an
        unencodable state leaves the pass's queues as they were."""
        new = dict(entry, window=self.st['window'], main=cursor, state=state, result=result)
        text = encode(new)
        out = {aid: (encode(a), a) for aid, a in agents.items()}
        if text != (self.cache['sessions'].get(sid) or (None,))[0]:
            self.sessions_out[sid] = (text, new)
        self.agents_out.update({(sid, aid): v for aid, v in out.items()})
        self.agents_del |= {(sid, aid) for aid in agents_del}

    def _keep(self, sid, fresh, old_result, e):
        """A main-transcript failure: the session keeps its stored state, cursors and result, so the next pass reads
        the same bytes again; its kept rows are carried as the exporter carries a session it could not parse."""
        warn('session %s could not be read (%s: %s); %s' % (
            sid, type(e).__name__, e, 'keeping its last result' if old_result and not fresh else 'left out'))
        result = None if fresh else old_result
        if result:
            result = dict(result, rows=[derive.carried(r, self.st['window'], self.t0) for r in result['rows']])
        self.judge(sid, result)

    def judge(self, sid, result):
        """Window by last activity, judged as the exporter judges it."""
        if not result:
            return
        last = result['doc'].get('last')
        if sid in self.st['build'] or (last and self.t0 - derive.epoch(last) <= self.limit):
            self.results[sid] = result
        else:
            self.why[sid] = 'age'

    def assemble(self):
        """The session, run and project documents: the tail of export_sessions.main, line for line."""
        st, results = self.st, self.results
        # The exporter's link decision, rebound for every document below; self.st keeps the config-only build set,
        # so windows, pruning and the missing-transcript check still treat an auto-linked session as unlisted.
        project_of, linked_by = derive.link_sessions(results, st['projects'], st['project_of'])
        st = dict(st, project_of=project_of, linked_by=linked_by)
        rows = sorted((dict(r, session=sid) for sid, res in results.items() for r in res['rows']), key=lambda r: r['start'] or '')
        derive.place_manual(rows, st['manual'])
        docs = {k: {} for k in KINDS}
        running, counts = {}, {}
        repo_of = {p['id']: p['repoPath'] for p in st['projects']}
        for sid in results:
            mine = [r for r in rows if r['session'] == sid]
            derive.link(mine)
            pid = st['project_of'].get(sid)
            for i, r in enumerate(mine, 1):
                docs['run'][r['id']] = derive.run_doc(r, i, pid, repo_of.get(pid))
            running[sid], counts[sid] = sum(r['kind'] == 'running' for r in mine), len(mine)
            docs['session'][sid] = derive.session_doc(results[sid], sid, st, len(mine), running[sid])
        for order, p in enumerate(st['projects']):
            docs['project'][p['id']] = derive.project_doc(p, order, results, counts, running, st['project_of'])
        return docs

    def catalogue(self, config):
        """export_catalogue's document, or None when it kept its last export (nothing to read, or nothing found)."""
        tmp = tempfile.mkdtemp(prefix='collector-catalogue-')
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = export_catalogue.main(config, out_dir=tmp, now=datetime.fromtimestamp(self.t0, timezone.utc).isoformat(timespec='seconds'))
            if code:
                raise Refusal('the catalogue block of the config is unusable; nothing written')
            path = os.path.join(tmp, 'catalogue', 'index.json')
            if not os.path.isfile(path):
                return None
            with io.open(path, encoding='utf-8') as f:
                return json.load(f)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def reasons(self, stored, docs):
        """[(kind, id, reason)] for every stored record the pass no longer produces."""
        st = self.st
        aged = {sid for sid, why in self.why.items() if why == 'age' and sid not in st['build']}
        for sid, doc in stored['session'].items():
            if sid in docs['session'] or sid in self.present or sid in st['build']:
                continue
            try:  # a vanished transcript of a long-quiet session is Claude Code's own clean-up
                if doc.get('last') and self.t0 - derive.epoch(doc['last']) > self.limit:
                    aged.add(sid)
            except (TypeError, ValueError):
                pass
        out = []
        # A tab is not a session: it has no last activity to prune by, and belongs to a project that is either
        # configured or gone, so a tab id is never in aged and every tab deletion carries the reason "other".
        for kind in DELETABLE:
            for rid, doc in stored[kind].items():
                if rid not in docs[kind]:
                    sid = rid if kind == 'session' else doc.get('session') if kind == 'run' else None
                    out.append((kind, rid, 'age' if sid in aged else 'other'))
        return out

    def guard(self, stored, deletions):
        held = len(stored['session']) + len(stored['run'])
        gone = [(k, i) for k, i, why in deletions if why == 'other' and k in ('session', 'run')]
        refused = []
        if gone and (not self.results or 2 * len(gone) > held):
            refused.append('%d of the %d stored runs and sessions other than by age (%s)%s' % (
                len(gone), held, ', '.join(i for _, i in gone[:10]) + (', ...' if len(gone) > 10 else ''),
                '; the pass found no sessions at all' if not self.results else ''))
        lost = [i for k, i, _ in deletions if k == 'project']
        if lost:
            refused.append('project %s' % ', '.join(lost))
        # The carry rule keeps a tab whose source went missing, so a project losing every tab it had stored can
        # only mean it left the export. stored['tab'] holds the owned records alone, so a project whose only
        # stored tab is another writer's has no group here and cannot trip this.
        tabs_of = {}
        for rid in stored['tab']:
            tabs_of.setdefault(rid.split('.', 1)[0], []).append(rid)
        gone_tabs = {i for k, i, _ in deletions if k == 'tab'}
        emptied = sorted(pid for pid, ids in tabs_of.items() if all(i in gone_tabs for i in ids))
        if emptied:
            refused.append('every tab of project %s (check its repoPath and docs in board.config.json)'
                           % ', '.join(emptied))
        if any(k == 'catalogue' for k, _, _ in deletions):
            refused.append('the catalogue')
        if refused:
            raise Refusal('refusing to delete %s. Nothing was written. Check sessions.projectsRoot, the transcripts, '
                          '"projects" and "catalogue" in the config; if the deletions are intended, run '
                          '--once --allow-mass-delete.' % '; and '.join(refused))

    def store(self, kind, rid, doc, old):
        """Write one record unless it is unchanged (generatedAt aside); True when written. A record that cannot be
        stored is skipped with a warning and its stored version kept."""
        self.conn.execute('SAVEPOINT rec')
        try:
            doc = json.loads(json.dumps(doc, ensure_ascii=False))  # the document exactly as the exporter's file holds it
            strip = lambda d: {k: v for k, v in d.items() if k != 'generatedAt'}
            if old is not None and strip(old) == strip(doc):
                self.conn.execute('RELEASE rec')
                return False
            db.upsert(self.conn, kind, records.to_row(kind, rid, doc))
        except RECORD_ERRORS as e:
            self.conn.execute('ROLLBACK TO rec')
            self.conn.execute('RELEASE rec')
            warn('%s %s not stored (%s: %s)' % (kind, rid, type(e).__name__, e))
            return False
        self.conn.execute('RELEASE rec')
        return True

    def write_state(self):
        c = self.conn
        for sid in self.drop:
            c.execute('DELETE FROM collector_sessions WHERE id = ?', (sid,))
            c.execute('DELETE FROM collector_agents WHERE session = ?', (sid,))
        for sid, (text, _) in self.sessions_out.items():
            c.execute('INSERT INTO collector_sessions (id, data) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data', (sid, text))
        for sid, aid in self.agents_del:
            c.execute('DELETE FROM collector_agents WHERE session = ? AND agent = ?', (sid, aid))
        for (sid, aid), (text, _) in self.agents_out.items():
            c.execute('INSERT INTO collector_agents (session, agent, data) VALUES (?, ?, ?) '
                      'ON CONFLICT(session, agent) DO UPDATE SET data = excluded.data', (sid, aid, text))
        self.markers = {k: v for k, v in self.markers.items() if k in self.seen}
        for key, value in self.cache['markers'].items():
            if key not in self.markers:
                c.execute('DELETE FROM collector_excluded WHERE dev = ? AND ino = ?', key)
        for key, value in self.markers.items():
            if self.cache['markers'].get(key) != value:
                c.execute('INSERT INTO collector_excluded (dev, ino, size, rule) VALUES (?, ?, ?, ?) '
                          'ON CONFLICT(dev, ino) DO UPDATE SET size = excluded.size, rule = excluded.rule', key + value)

    def promote(self):
        """After COMMIT: the cache becomes what the database now holds."""
        cache = self.cache
        for sid in self.drop:
            cache['sessions'].pop(sid, None)
            cache['agents'].pop(sid, None)
        for sid, v in self.sessions_out.items():
            cache['sessions'][sid] = v
        for sid, aid in self.agents_del:
            cache['agents'].get(sid, {}).pop(aid, None)
        for (sid, aid), v in self.agents_out.items():
            cache['agents'].setdefault(sid, {})[aid] = v
        cache['markers'] = self.markers
        cache['conn'] = self.conn
        cache['version'] = self.conn.execute('PRAGMA data_version').fetchone()[0]


def run_pass(conn, config, projects_root=None, now=None, allow_mass_delete=False, clock=None, data_dir=None,
             run=None):
    """One pass: read what the transcripts gained, derive, and write the changed records, all in one transaction.
    Returns a report dict; raises Refusal (nothing written) for an unusable config, a missing projects root or
    linked transcript, an unusable catalogue block, or a pass the mass-delete guard stops.

    data_dir holds the projects' hand-kept data files (default the repository's projects/) and run stands in
    for subprocess.run when the tab pass runs git; a malformed data file raises ValueError and writes nothing,
    as it stops the whole export on the board."""
    started = time.time()
    t0 = started if now is None else now
    clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        try:
            st = export_sessions.settings(config, projects_root)
        except ValueError as e:
            raise Refusal('%s; nothing written' % e) from e
        if not os.path.isdir(st['root']):
            raise Refusal('sessions.projectsRoot %s does not exist; nothing written' % st['root'])
        mains = glob.glob(os.path.join(st['root'], '*', '*.jsonl'))  # in glob's order, as the exporter visits them
        found = {os.path.basename(p)[:-len('.jsonl')] for p in mains}
        missing = sorted(st['build'] - found)
        if missing:
            raise Refusal('no transcript under %s for project session(s) %s; nothing written' % (st['root'], ', '.join(missing)))
        # Outside the transaction: the document reads and the git calls need nothing from the database, and
        # holding the write lock across ten subprocesses per project would make the server and a second
        # collector wait on them. The carry decision is taken inside, from what is stored.
        stamp = datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec='seconds')
        built, notes = tabs.build(st['projects'], data_dir or tabs.DATA_DIR, stamp, run=run)
        for note in notes:
            warn(note)
        conn.execute('BEGIN IMMEDIATE')
        try:
            p = _Pass(conn, st, t0, _load(conn))
            p.discover(mains, found)
            docs = p.assemble()
            cat = p.catalogue(config)
            stored = {kind: db.stored(conn, kind) for kind in KINDS + ('catalogue', 'tab', 'status')}
            docs['catalogue'] = {'index': cat} if cat is not None else dict(stored['catalogue'])
            # A tab suffix another exporter owns is set aside before anything else looks at the stored tabs, so
            # the diff, the deletions and the guard are all scoped to the five this pass owns.
            stored['tab'] = {rid: doc for rid, doc in stored['tab'].items() if tabs.owns(rid)}
            docs['tab'] = tabs.carry(built, stored['tab'], stamp, warn)
            deletions = p.reasons(stored, docs)
            if not allow_mass_delete:
                p.guard(stored, deletions)
            wrote = [(kind, rid) for kind in UPSERTED for rid, doc in docs[kind].items()
                     if p.store(kind, rid, doc, stored[kind].get(rid))]
            for kind, rid, _ in deletions:
                db.delete(conn, kind, rid)
            # After the writes and the deletions, because a status moves only for a project whose own records
            # this pass really changed. One clock reading stamps both the statuses and the last-refresh record.
            at = clock().isoformat(timespec='seconds')
            changed = {tabs.project_of(kind, rid, docs[kind].get(rid)) for kind, rid in wrote}
            changed |= {tabs.project_of(kind, rid, stored[kind].get(rid)) for kind, rid, _ in deletions}
            docs['status'] = tabs.statuses(st['projects'], docs['run'], stored['status'], changed - {None}, at)
            statuses = sum(p.store('status', rid, doc, stored['status'].get(rid))
                           for rid, doc in docs['status'].items())
            written = len(wrote) + statuses
            p.write_state()
            db.upsert(conn, 'lastRefresh', records.to_row('lastRefresh', 'lastRefresh', {
                'at': at, 'writer': 'collector'}))
            conn.execute('COMMIT')
        except BaseException:
            if conn.in_transaction:
                conn.execute('ROLLBACK')
            raise
    except BaseException:
        forget()
        raise
    p.promote()
    return {'sessions': len(p.results), 'rederived': p.rederived, 'bytes': p.bytes, 'runs': len(docs['run']),
            'projects': len(docs['project']), 'tabs': len(docs['tab']), 'statuses': statuses, 'written': written,
            'deleted': len(deletions), 'aged': sum(why == 'age' for _, _, why in deletions),
            'seconds': time.time() - started}


def summary(r):
    return ('collector: %d sessions (%d re-derived, %d bytes read), %d runs, %d projects, %d tabs; '
            '%d written, %d deleted (%d by age) | %.1fs') % (
        r['sessions'], r['rederived'], r['bytes'], r['runs'], r['projects'], r['tabs'], r['written'],
        r['deleted'], r['aged'], r['seconds'])


def _locked(e):
    return isinstance(e, sqlite3.OperationalError) and 'locked' in str(e)


def _stamped(msg):
    """A loop-mode report: nobody watches a scheduled collector, so its log needs the time of each one."""
    warn('%s %s' % (datetime.now().isoformat(timespec='seconds'), msg))


JSON_TYPES = {list: 'an array', str: 'a string', int: 'a number', float: 'a number', bool: 'true or false',
              type(None): 'null'}


def config_object(cfg, source='the config', verb='must be'):
    """cfg itself when it is a dict. Anything else raises ValueError: every reader of the config calls .get on it,
    so a hand-saved array or null would otherwise surface as an AttributeError far from its cause."""
    if not isinstance(cfg, dict):
        raise ValueError('%s %s a JSON object, not %s' % (source, verb, JSON_TYPES.get(type(cfg), type(cfg).__name__)))
    return cfg


def read_config(path):
    """The board config at path. Raises OSError when it cannot be read and ValueError when it is not JSON, nests
    too deeply to parse, or is not an object at the top: all of them refusals, never a crash."""
    try:
        with io.open(path, encoding='utf-8') as f:
            cfg = json.load(f)
    except RecursionError as e:
        raise ValueError('%s nests too deeply to parse' % path) from e
    return config_object(cfg, path, 'must hold')


def _one(conn, cfg, path, projects_root, now, allow, loop):
    """Run one pass and report it; returns its exit code."""
    say = _stamped if loop else warn
    try:
        report = run_pass(conn, cfg, projects_root=projects_root, now=now, allow_mass_delete=allow)
    except Refusal as e:
        say(str(e))
        return 2
    except Exception as e:
        if _locked(e):
            say('another collector holds the database lock on %s; this pass did not run' % path)
        else:
            say('pass failed (%s: %s); nothing written' % (type(e).__name__, e))
        return 1
    print(summary(report))
    return 0


def main(argv=None, config=None, db_path=None, projects_root=None, now=None):
    """The command line, callable in-process; returns the exit code."""
    ap = argparse.ArgumentParser(prog='collector.py', description='Collect Claude Code transcripts into the local database.')
    ap.add_argument('--once', action='store_true', help='run one pass and exit')
    ap.add_argument('--allow-mass-delete', action='store_true', help='with --once: let one guarded pass delete')
    ap.add_argument('--interval', type=float, default=60, help='seconds between passes (default 60)')
    ap.add_argument('--config', help='the board config (default: the repository board.config.json)')
    try:
        args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    if args.allow_mass_delete and not args.once:
        print('collector: --allow-mass-delete is accepted only with --once', file=sys.stderr)
        return 2

    def load():
        return config_object(config) if config is not None else read_config(args.config or CONFIG)
    try:
        cfg = load()
        path = db_path or board_config.local(cfg)['databasePath']
    except (OSError, ValueError) as e:
        warn('%s; not started' % e)
        return 2
    conn = None
    try:
        while conn is None:
            try:
                conn = db.open_db(path)
            except db.NetworkPath as e:
                warn('refusing to start: the database path %s is a network path; SQLite over SMB or NFS is unsafe (C-14)' % e.path)
                return 2
            except db.Refused as e:
                warn('refusing to start: %s' % e)
                return 2
            except sqlite3.OperationalError as e:
                if not _locked(e):
                    raise
                warn('another collector holds the database lock on %s; this pass did not run' % path)
                if args.once:
                    return 1
                time.sleep(args.interval)
        if args.once:
            return _one(conn, cfg, path, projects_root, now, args.allow_mass_delete, False)
        while True:
            # A config that cannot be re-read is a refused pass, as a config type error is: reported, nothing
            # written, and tried again at the next interval. Running on the previous config instead would carry on
            # with settings (an exclude list, say) that the owner has already replaced.
            try:
                cfg = load()
                if not db_path and board_config.local(cfg)['databasePath'] != path:
                    warn('local.databasePath changed; it takes effect when the collector restarts')
            except (OSError, ValueError) as e:
                _stamped('the config could not be re-read (%s); this pass did not run' % e)
            else:
                _one(conn, cfg, path, projects_root, now, False, True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        warn('failed (%s: %s)' % (type(e).__name__, e))
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    sys.exit(main())
