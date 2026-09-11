"""Run every exporter and list the store writes that changed since the last push.

    python exporters/refresh.py                       # export, then print the pending writes as JSON
    python exporters/refresh.py --allow-mass-delete   # the same, accepting a large delete (see below)
    python exporters/refresh.py --commit              # after the writes succeeded: record them as pushed

The printed "writes" array is exactly what Artifact write_db (db_op "batch") takes; each entry
points at a file under out/. A document counts as changed when its content differs from the last
push, ignoring the generatedAt stamp. Runs, sessions and tabs recorded in out/.pushed.json that are no
longer exported are deleted; documents never recorded there (such as the stale tabs/usage and the
hand-written runs/r01-r36) are never touched.

meta/status gets a merge of {live, updatedAt} only when build data changed (a tabs/* document, a build
session's document, or a run of a build session) or the live flag flipped, so the page's "updated"
time is not moved by unrelated sessions, including the refresher's own.

An export with no sessions, or one that would delete more than half of the pushed runs and sessions,
is taken to be a broken discovery rather than real change: refresh.py prints why, exits non-zero and
leaves nothing pending, unless --allow-mass-delete is given.

State: out/.pushed.json (what the store holds), out/.pending.json (the last printed plan).
"""
import glob, hashlib, io, json, os, subprocess, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'out')
BATCH = 50  # write_db batch limit
TABS = ('spec', 'assumptions', 'decisions', 'backlog', 'git')  # export_board.py's project tabs


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


def plan(out, allow_mass_delete=False):
    """Diff out/ against the last push. Returns {batches, live, writes} and records it as pending, or None
    when nothing changed. Raises MassDelete, leaving nothing pending, for a delete that looks like a broken export."""
    pushed_path, pending_path = os.path.join(out, '.pushed.json'), os.path.join(out, '.pending.json')
    docs = {}  # "collection/doc_id" -> file
    for tab in TABS:
        docs['tabs/' + tab] = os.path.join(out, tab + '.json')
    for coll in ('runs', 'sessions'):
        for f in glob.glob(os.path.join(out, coll, '*.json')):
            docs[coll + '/' + os.path.basename(f)[:-5]] = f

    pushed = load(pushed_path, {})
    state = {k: digest(f) for k, f in docs.items()}
    writes = [{'op': 'set', 'collection': k.split('/')[0], 'doc_id': k.split('/')[1], 'file_path': docs[k].replace('\\', '/')}
              for k in sorted(docs) if pushed.get(k) != state[k]]
    # Only documents recorded as pushed can be deleted; anything the store holds that was never pushed stays.
    deletes = [k for k in sorted(pushed) if k.split('/')[0] in ('runs', 'sessions', 'tabs') and k not in docs]
    gone = [k for k in deletes if k.split('/')[0] in ('runs', 'sessions')]
    held = [k for k in pushed if k.split('/')[0] in ('runs', 'sessions')]
    no_sessions = not any(k.startswith('sessions/') for k in docs)
    if gone and not allow_mass_delete and (no_sessions or 2 * len(gone) > len(held)):
        discard(pending_path)
        raise MassDelete('refusing to delete %d of the %d pushed runs and sessions%s. This usually means session '
                         'discovery broke (check sessions.projectsRoot and the transcripts). Nothing is pending. If the '
                         'deletes are intended, re-run with --allow-mass-delete.' % (
                             len(gone), len(held), ' (the export has no sessions at all)' if no_sessions else ''))
    writes += [{'op': 'delete', 'collection': k.split('/')[0], 'doc_id': k.split('/')[1]} for k in deletes]

    # meta/status belongs to the build: it is live while a build session has an agent running, and its
    # updatedAt moves only when something the build's tabs show has changed.
    runs = {k: load(f, {}) for k, f in docs.items() if k.startswith('runs/')}
    builds = {k.split('/')[1] for k, f in docs.items() if k.startswith('sessions/') and load(f, {}).get('build')}
    live = any(r.get('kind') == 'running' and r.get('session') in builds for r in runs.values())
    build_docs = {'sessions/' + b for b in builds} | {k for k, r in runs.items() if r.get('session') in builds}
    state['meta/status#live'] = str(live)
    state['meta/status#build'] = sorted(build_docs)
    # A document that was build data at the last push still counts, so deleting a build run moves updatedAt.
    relevant = build_docs | set(pushed.get('meta/status#build') or [])
    changed = {w['collection'] + '/' + w['doc_id'] for w in writes}
    if any(k.startswith('tabs/') or k in relevant for k in changed) or pushed.get('meta/status#live') != state['meta/status#live']:
        status = os.path.join(out, 'meta', 'status.json')
        os.makedirs(os.path.dirname(status), exist_ok=True)
        save(status, {'live': live, 'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds')})
        writes.append({'op': 'update', 'collection': 'meta', 'doc_id': 'status', 'file_path': status.replace('\\', '/')})

    if not writes:
        discard(pending_path)  # an older plan must not be committed as if it were this one
        return None
    save(pending_path, {'state': state})
    batches = [writes[i:i + BATCH] for i in range(0, len(writes), BATCH)]
    return {'batches': len(batches), 'live': live, 'writes': batches[0] if len(batches) == 1 else batches}


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
