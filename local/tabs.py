"""The local-first app's tab and status documents: what one collector pass builds for each project in
board.config.json, and how it keeps, carries and merges them.

For the same repositories, config, data files and time, the tab documents here are export_board.py's, apart
from generatedAt and pulls, and the status documents are the ones refresh.py plans. Every derivation is
imported from derive.py and export_board.py rather than rewritten; only the sequence of git commands is
repeated, because the collector runs on a loop and needs its own timeout on each of them.

pulls are not collected. gh is a network client and the collector never contacts a network host, so the local
git tab is the exporter's document without that key, which the page already renders as "not available".

projectTabs has two writers, each owning a disjoint set of tab suffixes: export_board.py owns the five in
OWNED, and export_sessions.py owns "findings", whose whole lifecycle -- write and delete -- is its own. So
everything here is scoped to OWNED: what a pass builds, carries, deletes and groups for the mass-delete guard.
records.TAB_NAMES is deliberately not read, because it names every suffix the database accepts from either
writer; a pass that computed its intended set from it would delete the other writer's document every time.
A stored tab record whose suffix is not in OWNED takes part in nothing here.
"""
import os, subprocess, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(HERE, 'exporters'), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import derive  # noqa: E402
# The module, never its names: export_board.carried is a kept tab's bytes and derive.carried a kept agent row,
# so importing either name here would shadow the other.
import export_board  # noqa: E402

OWNED = ('spec', 'assumptions', 'decisions', 'backlog', 'git')
DATA_DIR = export_board.DATA_DIR  # the repository's projects/ folder, resolved from the repository root
TIMEOUT = 15  # seconds per git call; the collector runs on a loop, so a hung git must not stall it
# What reading one project's documents may raise without costing the rest of the pass. UnicodeDecodeError is
# named rather than caught as the ValueError it is a subclass of: a plain ValueError here is load_data's, and
# that one must fail the whole pass (see build).
READ_ERRORS = (OSError, UnicodeDecodeError)
# What running one project's git may raise without costing the rest of the pass. SubprocessError covers
# TimeoutExpired; UnicodeDecodeError is git output the strict decode in _stdout cannot read, which a non-UTF-8
# commit subject or branch name produces and which is neither an OSError nor a SubprocessError.
GIT_ERRORS = (OSError, subprocess.SubprocessError, UnicodeDecodeError)


def owns(record_id):
    """True when a stored tab id's suffix is one of the five this pass owns. Project ids never contain a dot,
    so the suffix is everything after the first one, as records.to_row splits it."""
    return record_id.split('.', 1)[-1] in OWNED if '.' in record_id else False


def _stdout(run, root, args):
    r = run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=TIMEOUT,
            **export_board.no_window_flags())
    return (r.stdout or '').strip()


def is_repo(run, root):
    """True when root is inside a git work tree. A git that cannot be run raises here, where export_board's
    answers False: locally that is a failure to report and carry the last tab through, not a plain folder."""
    r = run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=root, capture_output=True, text=True,
            encoding='utf-8', timeout=TIMEOUT, **export_board.no_window_flags())
    return r.returncode == 0 and (r.stdout or '').strip() == 'true'


def git_tab(root, now, run):
    """The git tab of the repository at root: export_board.git_tab's commands, each under TIMEOUT, with the
    document itself derived by derive.git_doc so the two sides cannot drift."""
    out = lambda *args: _stdout(run, root, args)
    branch = out('branch', '--show-current')
    default = derive.git_default(out('rev-parse', '--verify', '--quiet', 'master'),
                                 out('rev-parse', '--verify', '--quiet', 'main'))
    log = out('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict')
    files, status, remotes = out('ls-files'), out('status', '--short'), out('remote', '-v')
    # Skipped rather than run without both branches; derive.git_doc empties them under the same condition.
    ahead = out('rev-list', '--count', '%s..%s' % (default, branch)) if default and branch else ''
    shortstat = out('diff', '--shortstat', default, branch) if default and branch else ''
    return derive.git_doc(root, branch, default, log, files, status, remotes,
                          out('rev-parse', '--short', 'HEAD'), ahead, shortstat, now)


def build(projects, data_dir, stamp, run=None):
    """({project id: {tab name: document}}, [warning]) for one pass: export_board.main's rule project by
    project, without its gh call. run stands in for subprocess.run.

    A failure reading one project's documents or running its git costs that project's tabs for this pass and
    nothing else: it warns, builds nothing for that project, and leaves the carry rule to keep what is stored.
    The collector runs every 60 seconds and a failed pass writes nothing at all, so confining the failure is
    what stops one unreadable file from emptying the whole local board for as long as it stays unreadable.
    """
    run = run or subprocess.run
    built, warnings = {}, []
    for p in projects:
        pid, root = p['id'], p['repoPath']
        built[pid] = {}
        if not root or not os.path.isdir(root):
            warnings.append('project %s: repository %s does not exist' % (pid, root or '(no repoPath)'))
            continue
        # Outside the confined block below, so its ValueError fails the whole pass as it stops the whole
        # export. A malformed projects/<pid>.json is not a missing source but the hand-kept build state:
        # reading it as absent would silently reset every PBI of that project to "not started", and no
        # carried document protects against that, because the tab would be rebuilt, just wrongly.
        data = export_board.load_data(data_dir, pid)
        try:
            built[pid] = export_board.spec_tabs(p, data, stamp)
        except READ_ERRORS as e:
            warnings.append('project %s: cannot read its documents (%s: %s); keeping the last export'
                            % (pid, type(e).__name__, e))
        try:
            if is_repo(run, root):
                built[pid]['git'] = git_tab(root, stamp, run)
        except GIT_ERRORS as e:
            warnings.append('project %s: cannot read its git repository (%s: %s); keeping the last export'
                            % (pid, type(e).__name__, e))
        outside = sorted(set(built[pid]) - set(OWNED))
        if outside:  # another writer's suffix must not reach the pass, whose every set is scoped to OWNED
            raise ValueError('project %s: %s is not a tab this pass owns' % (pid, ', '.join(outside)))
    return built, warnings


def carry(built, stored, stamp, warn=None):
    """{tab id: document} to store: what this pass built, plus the stored record of a tab it could not rebuild.

    The first pass that keeps a record adds carriedSince, the time the carry began, in the UTC-with-a-Z form
    export_board writes into the kept file. A later carrying pass returns the stored document unchanged, so it
    stays in the intended set -- a carried tab is still a tab this pass means to hold, and leaving it out would
    put it in the deletion set -- while the unchanged-record check skips the write and its first carriedSince
    survives. A rebuilt tab has no marker, because the built document has none. stored holds the owned tab
    records alone, so a findings record is never carried.
    """
    since = datetime.fromisoformat(stamp).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    out = {}
    for pid, docs in built.items():
        kept = []
        for tab in OWNED:
            record_id = '%s.%s' % (pid, tab)
            if tab in docs:
                out[record_id] = docs[tab]
            elif record_id in stored:
                kept.append(tab)
                old = stored[record_id]
                out[record_id] = old if 'carriedSince' in old else dict(old, carriedSince=since)
        if kept and warn:
            warn('project %s: cannot rebuild %s; keeping the last export' % (pid, ', '.join(kept)))
    return out


def project_of(kind, record_id, doc):
    """The project whose data a written or deleted record is, or None when it is no project's. A tab suffix
    this pass does not own is no project's here: another exporter owns that document, so a change to it is not
    this pass's news about the project."""
    if kind == 'project':
        return record_id
    if kind == 'tab':
        pid, _, tab = record_id.partition('.')
        return pid if tab in OWNED else None
    if kind in ('session', 'run'):
        return (doc or {}).get('project')
    return None


def statuses(projects, runs, stored, changed, updated_at):
    """{status id: document} for the projects whose status record this pass must write, by refresh.py's rule:
    a project's updatedAt moves only when its own records were written or deleted (changed) or its live flag
    flipped, an absent record counting as a flip. A project left out keeps the updatedAt it has.

    live is true when one of that project's runs from this pass is running. The document written is the stored
    one with live and updatedAt replaced, because db.upsert replaces the whole document where the board's
    status writes merge into it (op "update"): a title, message or metrics written by hand must survive. No
    local source holds those three, so this pass never supplies one.
    """
    out = {}
    for p in projects:
        pid, record_id = p['id'], p['statusDoc']
        live = any(d.get('project') == pid and d.get('kind') == 'running' for d in runs.values())
        old = stored.get(record_id)
        if pid in changed or old is None or old.get('live') != live:
            out[record_id] = dict(old or {}, live=live, updatedAt=updated_at)
    return out
