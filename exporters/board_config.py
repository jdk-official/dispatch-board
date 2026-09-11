"""The tracked projects listed in board.config.json, read the same way by every exporter.

Each project is {id, name, repoPath, branch, sessions, statusDoc, docs}: sessions are the Claude Code
session ids that build it, statusDoc is the store document its live flag and updatedAt go to, and docs
are paths relative to repoPath. A config without a "projects" list (the shape used before projects
existed) is read as one project made from build.* and usage.sessions, with the document paths
export_board.py always read for it.

catalogue() reads the "catalogue" block: where export_catalogue.py finds the agent-catalog marketplace clone
and the installed-plugins file.
"""
import os, re

# Ids become file names under out/ and store document ids, so they are kept to one safe path segment.
ID = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
# A status document must stay out of the collections refresh.py replaces and deletes.
STATUS_DOC = re.compile(r'^(meta|status)/[A-Za-z0-9_-]{1,100}$')
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
            raise ValueError('project %s: statusDoc %r must be meta/<id> or status/<id>' % (pid, status))
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
