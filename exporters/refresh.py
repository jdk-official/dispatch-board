"""Run every exporter and list the store writes that changed since the last push.

    python exporters/refresh.py                       # export, then print the pending writes as JSON
    python exporters/refresh.py --allow-mass-delete   # the same, accepting a large delete (see below)
    python exporters/refresh.py --commit              # after the writes succeeded: record them as pushed

The printed "writes" array is exactly what Artifact write_db (db_op "batch") takes; each entry
points at a file under out/. A document counts as changed when its content differs from the last
push, ignoring the generatedAt stamp. refresh.py manages four collections: runs, sessions, projects and
projectTabs. Their documents recorded in out/.pushed.json that are no longer exported are deleted.
Documents never recorded there, and every other collection (such as the retired tabs/* and the
hand-written runs/r01-r36), are never touched: deleting those needs the owner's go-ahead.

Each project has a status document (its statusDoc: meta/status for platform-catalogue, status/<projectId>
for the others). It gets {live, updatedAt} only when that project's own data changed (its projects/ or
projectTabs/ documents, a session linked to it, or one of that session's runs) or its live flag flipped,
so its "updated" time is not moved by other projects or by unlinked sessions, including the refresher's
own. meta/status also holds hand-written title, message and metrics, so it is only ever merged into
(op "update"). Any other status document is created with "set" on its first write and merged into after.

An export with no sessions, one that would delete more than half of the pushed runs and sessions, one
that would delete any projects/ document, or one that would delete every pushed projectTabs document of a
project, is taken to be a broken export rather than real change: refresh.py prints why, exits non-zero
and leaves nothing pending, unless --allow-mass-delete is given.

State: out/.pushed.json (what the store holds), out/.pending.json (the last printed plan).
"""
import glob, hashlib, io, json, os, subprocess, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out')
BATCH = 50  # write_db batch limit
MANAGED = ('runs', 'sessions', 'projects', 'projectTabs')  # the collections refresh.py sets and deletes
TABS = ('spec', 'assumptions', 'decisions', 'backlog', 'git')  # projectTabs/<projectId>.<tab>, from export_board.py
META_STATUS = 'meta/status'


class MassDelete(Exception):
    pass


def load(path, default):
    try:
        with io.open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, obj):
    """Write through a temp file in the same folder, then swap it in: a truncated .pushed.json would read as
    "nothing pushed" and re-offer every document."""
    text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.' + os.path.basename(path) + '.', suffix='.tmp')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.remove(tmp)
        raise


def digest(path):
    doc = load(path, {})
    doc.pop('generatedAt', None)
    return hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def discard(path):
    if os.path.exists(path):
        os.remove(path)


def export(out):
    """Run both exporters into out; returns an error message, or None. Their warnings go to stderr."""
    for script in ('export_board.py', 'export_sessions.py'):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'exporters', script), out], capture_output=True, text=True, encoding='utf-8')
        if r.returncode:
            return '%s failed:\n%s' % (script, r.stderr or r.stdout)
        if r.stderr:
            sys.stderr.write(r.stderr)
    return None


def split(key):
    """"collection/doc_id" -> (collection, doc_id); doc ids may contain dots but never a slash."""
    return tuple(key.split('/', 1))


def plan(out, allow_mass_delete=False):
    """Diff out/ against the last push. Returns {batches, live, writes} and records it as pending, or None
    when nothing changed. Raises MassDelete, leaving nothing pending, for a delete that looks like a broken export."""
    pushed_path, pending_path = os.path.join(out, '.pushed.json'), os.path.join(out, '.pending.json')
    docs = {}  # "collection/doc_id" -> file
    for coll in MANAGED:
        for f in glob.glob(os.path.join(out, coll, '*.json')):
            docs[coll + '/' + os.path.basename(f)[:-5]] = f

    pushed = load(pushed_path, {})
    state = {k: digest(f) for k, f in docs.items()}
    writes = [{'op': 'set', 'collection': split(k)[0], 'doc_id': split(k)[1], 'file_path': docs[k].replace('\\', '/')}
              for k in sorted(docs) if pushed.get(k) != state[k]]
    # Only documents recorded as pushed can be deleted; anything the store holds that was never pushed stays.
    # "#" keys are status bookkeeping, not documents.
    deletes = [k for k in sorted(pushed) if '#' not in k and split(k)[0] in MANAGED and k not in docs]
    gone = [k for k in deletes if split(k)[0] in ('runs', 'sessions')]
    held = [k for k in pushed if '#' not in k and split(k)[0] in ('runs', 'sessions')]
    no_sessions = not any(k.startswith('sessions/') for k in docs)
    refused = []
    if gone and (no_sessions or 2 * len(gone) > len(held)):
        refused.append('%d of the %d pushed runs and sessions%s. This usually means session discovery broke (check '
                       'sessions.projectsRoot and the transcripts)' % (
                           len(gone), len(held), ' (the export has no sessions at all)' if no_sessions else ''))
    # A project is a handful of documents, so these are judged per project rather than as a share. export_board.py
    # keeps a tab whose source went missing, so a project losing all its tabs means it left the export.
    lost = [k for k in deletes if split(k)[0] == 'projects']
    if lost:
        refused.append('%s. A project is no longer exported (check "projects" in board.config.json)' % ', '.join(lost))
    tabs_of, gone_set = {}, set(deletes)
    for k in pushed:
        if '#' not in k and split(k)[0] == 'projectTabs':
            tabs_of.setdefault(split(k)[1].split('.', 1)[0], []).append(k)  # project ids never contain a dot
    emptied = sorted(pid for pid, ks in tabs_of.items() if all(k in gone_set for k in ks))
    if emptied:
        refused.append('every tab of project %s (check its repoPath and docs in board.config.json)' % ', '.join(emptied))
    if refused and not allow_mass_delete:
        discard(pending_path)
        raise MassDelete('refusing to delete %s. Nothing is pending. If the deletes are intended, re-run with '
                         '--allow-mass-delete.' % '; and '.join(refused))
    writes += [{'op': 'delete', 'collection': split(k)[0], 'doc_id': split(k)[1]} for k in deletes]

    # A project's status document is live while one of its runs is running, and its updatedAt moves only
    # when something that project shows has changed.
    changed = {w['collection'] + '/' + w['doc_id'] for w in writes}
    data = {k: load(f, {}) for k, f in docs.items() if split(k)[0] in ('projects', 'sessions', 'runs')}
    live_any = False
    for key in sorted(k for k in data if k.startswith('projects/')):
        pid = split(key)[1]
        sdoc = data[key].get('statusDoc') or 'status/' + pid
        tabs = {'projectTabs/%s.%s' % (pid, t) for t in TABS} & set(docs)
        linked = {k for k, d in data.items() if split(k)[0] in ('sessions', 'runs') and d.get('project') == pid}
        mine = {key} | tabs | linked
        live = any(data[k].get('kind') == 'running' for k in linked if k.startswith('runs/'))
        live_any = live_any or live
        # "#build" is the key meta/status used when it tracked the only build, so an existing .pushed.json carries over.
        state[sdoc + '#live'] = str(live)
        state[sdoc + '#build'] = sorted(mine)
        # A document that was this project's at the last push still counts, so deleting one of its runs moves updatedAt.
        relevant = mine | set(pushed.get(sdoc + '#build') or [])
        if changed & relevant or pushed.get(sdoc + '#live') != state[sdoc + '#live']:
            coll, doc_id = split(sdoc)
            status = os.path.join(out, coll, doc_id + '.json')
            os.makedirs(os.path.dirname(status), exist_ok=True)
            save(status, {'live': live, 'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds')})
            op = 'update' if sdoc == META_STATUS or (sdoc + '#live') in pushed else 'set'
            writes.append({'op': op, 'collection': coll, 'doc_id': doc_id, 'file_path': status.replace('\\', '/')})

    if not writes:
        discard(pending_path)  # an older plan must not be committed as if it were this one
        return None
    save(pending_path, {'state': state})
    batches = [writes[i:i + BATCH] for i in range(0, len(writes), BATCH)]
    return {'batches': len(batches), 'live': live_any, 'writes': batches[0] if len(batches) == 1 else batches}


def commit(out):
    """Record the pending plan as pushed; returns how many state entries it recorded, or None if nothing was pending."""
    pending_path = os.path.join(out, '.pending.json')
    pending = load(pending_path, None)
    if not pending:
        return None
    save(os.path.join(out, '.pushed.json'), pending['state'])
    os.remove(pending_path)
    return len(pending['state'])


def main(argv=None, out=OUT, run_export=export):
    argv = sys.argv[1:] if argv is None else argv
    if '--commit' in argv:
        n = commit(out)
        if n is None:
            print('nothing pending: run refresh.py first', file=sys.stderr)
            return 1
        print('recorded %d documents as pushed' % n)
        return 0
    err = run_export(out)
    if err:
        print(err, file=sys.stderr)
        return 1
    try:
        p = plan(out, allow_mass_delete='--allow-mass-delete' in argv)
    except MassDelete as e:
        print('refresh.py: %s' % e, file=sys.stderr)
        return 2
    if p is None:
        print('nothing to push')
        return 0
    print(json.dumps(p, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
