"""The tracked projects listed in board.config.json, read the same way by every exporter.

Each project is {id, name, repoPath, branch, sessions, statusDoc, docs}: sessions are the Claude Code
session ids that build it, statusDoc is the store document its live flag and updatedAt go to, and docs
are paths relative to repoPath. A config without a "projects" list (the shape used before projects
existed) is read as one project made from build.* and usage.sessions, with the document paths
export_board.py always read for it.

catalogue() reads the "catalogue" block: where export_catalogue.py finds the agent-catalog marketplace clone
and the installed-plugins file. manual() reads runs.manual: the rows for work the orchestrator did in-line.
local() reads the "local" block: where the local-first app's SQLite database lives.
"""
import os, re

# Ids become file names under out/ and store document ids, so they are kept to one safe path segment.
ID = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
# A status document must stay out of the collections refresh.py replaces and deletes. meta/lastRefresh is
# reserved for the local app's record of the last refresh, so no project's status may take that path.
STATUS_DOC = re.compile(r'^(?!meta/lastRefresh$)(meta|status)/[A-Za-z0-9_-]{1,100}$')
# The lanes and kinds a runs.manual row may use: the run values the local app's record shapes accept
# (local/records.shapes.json). Copied rather than imported, because the local app depends on the exporters
# and never the other way round.
RUN_LANES = ('orch', 'req', 'plan', 'cw', 'tw', 'cr', 'ver', 'human', 'other')
RUN_KINDS = ('running', 'done', 'go', 'changes', 'nogo', 'killed')
# A runs.manual id becomes a file name under out/runs and a run record's id, so it takes the local app's run-id
# form (_SEGMENT in local/records.py), applied with fullmatch: one path segment with no "/" or "\", no C0 or C1
# control character, and not "." or "..". Copied rather than imported, like RUN_LANES.
RUN_ID = re.compile(r'(?!\.\.?\Z)[^/\\\x00-\x1f\x7f-\x9f]+')
# The exporter also writes that id as out/runs/<id>.json on the Windows refresher, where RUN_ID is not enough:
# a colon makes the path drive-relative (d:x lands on D:), * ? < > | " fail the write after out/ has been emptied,
# a leading dot hides the file from the *.json glob refresh.py pushes, Windows strips a trailing dot or space, and
# a device name (with or without an extension) opens the device. Kept separate so RUN_ID stays the local form;
# refusing more than the local form is safe, because every id the exporter writes still passes local to_row.
UNSAFE_FILE_NAME = re.compile(r'[:*?<>|"]|\A\.|[. ]\Z|\A(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z', re.I | re.S)
LEGACY_DOCS = {
    'spec': 'docs/backlog/specs/platform-catalogue.md',
    'design': 'docs/backlog/specs/pbi-008-design-system.md',
    'prd': 'docs/prd/platform-catalogue.md',
    'brief': 'docs/brief/raw-notes.md',
    'adrDir': 'docs/adr',
    'board': 'docs/backlog/BOARD.md',
    'reviews': [
        {'gate': 'Plan gate', 'path': 'docs/backlog/reviews/platform-catalogue/plan-gate-review-r{round}.md'},
        {'gate': 'PBI-008 spec gate', 'path': 'docs/backlog/reviews/PBI-008/spec-review-r{round}.md'},
    ],
}
CATALOGUE = {
    'marketplacePath': '~/.claude/plugins/marketplaces/agent-catalog',
    'installedPath': '~/.claude/plugins/installed_plugins.json',
}


def catalogue(cfg):
    """The catalogue block's two paths, with defaults filled in and a leading ~ expanded. Raises ValueError for
    a block that is not an object or a value that is not a string, so a typo cannot silently point elsewhere."""
    block = cfg.get('catalogue', {})
    if not isinstance(block, dict):
        raise ValueError('"catalogue" must be an object, not %s' % type(block).__name__)
    out = {}
    for key, default in CATALOGUE.items():
        value = block.get(key, default)
        if not isinstance(value, str):
            raise ValueError('catalogue.%s must be a string, not %s' % (key, type(value).__name__))
        out[key] = os.path.expanduser(value)
    return out


LOCAL_DATABASE = 'out/local/board.db'  # relative paths are resolved against the repository root by their reader


def local(cfg):
    """{"databasePath": <str>} from the local block, with the default filled in and a leading ~ expanded. Raises
    ValueError for a block that is not an object, or a path that is not a string or is blank."""
    block = cfg.get('local', {})
    if not isinstance(block, dict):
        raise ValueError('"local" must be an object, not %s' % type(block).__name__)
    value = block.get('databasePath', LOCAL_DATABASE)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('local.databasePath must be a non-empty string, not %r' % (value,))
    return {'databasePath': os.path.expanduser(value)}


def legacy(cfg):
    b = cfg.get('build') or {}
    sessions = list(b.get('sessions') or [])
    for s in (cfg.get('usage') or {}).get('sessions') or []:
        if s.get('sessionId') and s['sessionId'] not in sessions:
            sessions.append(s['sessionId'])
    repo = b.get('repoPath') or ''
    if not sessions and not repo:
        return []
    pid = os.path.basename(repo.replace('\\', '/').rstrip('/')) or 'build'
    return [{'id': pid, 'repoPath': repo, 'branch': b.get('branch', ''), 'sessions': sessions,
             'statusDoc': 'meta/status', 'docs': LEGACY_DOCS}]


def projects(cfg):
    """The projects in config order, with defaults filled in. Raises ValueError for a "projects" value that is
    not a list of objects, and for an id or statusDoc that cannot be used, or one that two projects share."""
    # Reading a malformed "projects" as "no projects" would drop every project's documents at exit 0.
    if 'projects' in cfg:
        raw = cfg['projects']
        if not isinstance(raw, list):
            raise ValueError('"projects" must be a list, not %s' % type(raw).__name__)
    else:
        raw = legacy(cfg)
    out, ids, docs = [], set(), set()
    for p in raw:
        if not isinstance(p, dict):
            raise ValueError('each entry in "projects" must be an object, not %r' % (p,))
        pid = p.get('id')
        if not isinstance(pid, str) or not ID.match(pid):
            raise ValueError('project id %r must be letters, digits, "-" and "_" only' % (pid,))
        status = p.get('statusDoc') or 'status/' + pid
        if not STATUS_DOC.match(status):
            raise ValueError('project %s: statusDoc %r must be meta/<id> or status/<id>, and not meta/lastRefresh' % (pid, status))
        if pid in ids:
            raise ValueError('project id %s is listed twice' % pid)
        if status in docs:
            raise ValueError('statusDoc %s is used by two projects' % status)
        ids.add(pid)
        docs.add(status)
        # A session listed twice would count its runs and usage twice in the project's totals.
        out.append({'id': pid, 'name': p.get('name') or pid, 'repoPath': p.get('repoPath') or '',
                    'branch': p.get('branch') or '', 'sessions': list(dict.fromkeys(p.get('sessions') or [])),
                    'statusDoc': status, 'docs': dict(p.get('docs') or {})})
    return out


def manual(cfg):
    """The runs.manual rows, as written. Raises ValueError, naming the row and the field, for a "runs" block that
    is not an object, a "manual" value that is not a list, or a row that is not an object, lacks a string id or
    label, has an id that is not of the RUN_ID form or is UNSAFE_FILE_NAME, has a verdict or from that is not a
    string, or has a lane or kind outside RUN_LANES / RUN_KINDS. A row may leave out lane, kind, verdict and from,
    which take their defaults when the row is exported."""
    block = cfg.get('runs', {})
    if not isinstance(block, dict):
        raise ValueError('"runs" must be an object, not %s' % type(block).__name__)
    rows = block.get('manual', [])
    if not isinstance(rows, list):
        raise ValueError('runs.manual must be a list, not %s' % type(rows).__name__)
    for i, row in enumerate(rows):
        where = 'runs.manual[%d]' % i
        if not isinstance(row, dict):
            raise ValueError('%s must be an object, not %r' % (where, row))
        if isinstance(row.get('id'), str):
            where += ' (%s)' % row['id']
        for key in ('id', 'label', 'verdict', 'from'):
            if (key in ('id', 'label') or key in row) and not isinstance(row.get(key), str):
                raise ValueError('%s: %s must be a string, not %r' % (where, key, row.get(key)))
        if not RUN_ID.fullmatch(row['id']) or UNSAFE_FILE_NAME.search(row['id']):
            raise ValueError('%s: id %r must be one path segment that is a safe Windows file name: not empty, no "/", '
                             '"\\", ":", "*", "?", "<", ">", "|" or \'"\', no control character, no leading dot, no '
                             'trailing dot or space, and not "." or ".." or a device name such as CON, NUL, COM1 or '
                             'LPT1' % (where, row['id']))
        for key, allowed in (('lane', RUN_LANES), ('kind', RUN_KINDS)):
            if key in row and row[key] not in allowed:
                raise ValueError('%s: %s %r must be one of %s' % (where, key, row[key], ', '.join(allowed)))
    return rows
