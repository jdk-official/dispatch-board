"""Export the planning state of every project in board.config.json as JSON documents for the Live Dispatch Board.

    python exporters/export_board.py [out_dir]

For each project, reads the solution spec, PRD, brief, ADRs, local review notes and git of its repository
(paths from the project's docs, relative to its repoPath) and writes out/projectTabs/<projectId>.<tab>.json
for tab in spec, assumptions, decisions, backlog and git, replacing only those five tabs (TABS) of that
folder -- a document another exporter writes there, such as export_sessions.py's <projectId>.findings, is
outside TABS and is never touched here; that exporter owns its own document's whole lifecycle. A tab is
built only when its source exists: spec, assumptions, decisions and backlog all need the spec, git needs a
git repository.
A tab that was exported before but cannot be built now (the repoPath has moved, the spec was renamed, git
is unavailable) keeps its last export, with a warning on stderr, so one broken project cannot blank its
tabs on the board while the others refresh. The kept document gets carriedSince, the UTC time the carry
began, which later runs leave as it is; a tab rebuilt once its source is back has no carriedSince. A
project dropped from the config loses its tabs.

A project whose origin remote is on github.com also gets its recent pull requests in the git tab (`pulls`),
listed with the GitHub CLI. When gh cannot list them (not installed, not signed in, too slow, odd output) the
git tab is written without `pulls`, with a warning on stderr; that never fails the export.

Build state per PBI, the brief's open questions and the backlog's note about the BOARD are not recorded in
the build repo, so they are kept by hand in projects/<projectId>.json in this repo. A missing file means no
build state. A malformed one stops the export and leaves out/ as it was, so a typo cannot reset every PBI
to "not started".
"""
import io, json, os, re, subprocess, sys
from datetime import datetime, timezone

import board_config
import derive
# The spec parsing and the git tab's arithmetic live in derive.py; these names stay importable from here.
from derive import (  # noqa: F401
    LATER, MARKER, RULE, STATES, USERINFO, build_state, bullets, clean, later_items, not_worked_out,
    public_remote, section, table)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'board.config.json')
DATA_DIR = os.path.join(HERE, 'projects')
TABS = ('spec', 'assumptions', 'decisions', 'backlog', 'git')
ROUNDS = (1, 2, 3)  # review rounds looked for, per gate


def warn(msg):
    print('export_board: ' + msg, file=sys.stderr)


def read(root, rel):
    with io.open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8').stdout.strip()


def is_repo(root):
    try:
        r = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=root, capture_output=True, text=True, encoding='utf-8')
    except OSError:  # git is not installed
        return False
    return r.returncode == 0 and r.stdout.strip() == 'true'


def verdict(root, path):
    try:
        return derive.review_verdict(read(root, path))
    except FileNotFoundError:
        return None


def load_data(data_dir, pid):
    """The hand-kept data for a project (buildState, notWorkedOut, boardNote), or {} when it has no file.
    Raises ValueError for a file that is not valid JSON or not in that shape."""
    path = os.path.join(data_dir, pid + '.json')
    try:
        with io.open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except ValueError as e:
        raise ValueError('%s is not valid JSON (%s)' % (path, e))
    if not isinstance(data, dict):
        raise ValueError('%s must hold a JSON object' % path)
    state, nwo = data.get('buildState'), data.get('notWorkedOut')
    if state is not None and not (isinstance(state, dict) and all(isinstance(e, dict) for e in state.values())):
        raise ValueError('%s: buildState must map each PBI id to an object' % path)
    if nwo is not None and not (isinstance(nwo, list) and all(isinstance(e, dict) for e in nwo)):
        raise ValueError('%s: notWorkedOut must be a list of objects' % path)
    return data


def spec_tabs(p, data, now):
    """The spec, assumptions, decisions and backlog tabs, all read from the project's spec; {} without one."""
    root, paths = p['repoPath'], p['docs']

    def doc(key):
        rel = paths.get(key)
        return read(root, rel) if rel and os.path.isfile(os.path.join(root, rel)) else None

    spec = doc('spec')
    if spec is None:
        return {}
    ADRS = (paths.get('adrDir') or '').rstrip('/')
    prd, brief, design = doc('prd'), doc('brief') or '', doc('design') or ''
    adrs = []
    if ADRS and os.path.isdir(os.path.join(root, ADRS)):
        for name in sorted(n for n in os.listdir(os.path.join(root, ADRS)) if n.endswith('.md')):
            adrs.append(derive.adr_entry(read(root, ADRS + '/' + name), ADRS + '/' + name))
    rounds = []
    for review in paths.get('reviews') or []:
        for r in ROUNDS:
            v = verdict(root, review['path'].replace('{round}', str(r)))
            if v:
                rounds.append({'gate': review['gate'], 'round': r, 'verdict': v})
    return derive.spec_docs(p['id'], paths, spec, prd, brief, design, adrs, rounds, data, now)


def git_tab(root, now):
    """The git tab: run the commands, and let derive turn their output into the document."""
    branch = git(root, 'branch', '--show-current')
    default = derive.git_default(git(root, 'rev-parse', '--verify', '--quiet', 'master'),
                                 git(root, 'rev-parse', '--verify', '--quiet', 'main'))
    log = git(root, 'log', '--pretty=format:%h|%ad|%s', '--date=iso-strict')
    files, status, remotes = git(root, 'ls-files'), git(root, 'status', '--short'), git(root, 'remote', '-v')
    # Skipped rather than run without both branches; derive.git_doc empties them under the same condition.
    ahead = git(root, 'rev-list', '--count', '%s..%s' % (default, branch)) if default and branch else ''
    shortstat = git(root, 'diff', '--shortstat', default, branch) if default and branch else ''
    return derive.git_doc(root, branch, default, log, files, status, remotes,
                          git(root, 'rev-parse', '--short', 'HEAD'), ahead, shortstat, now)


# https://github.com/..., ssh://git@github.com/... and the scp form git@github.com:...; the host must end at
# the ":" or "/", so github.com.evil.example is not taken for GitHub.
GITHUB_URL = re.compile(r'^(?:[a-z][a-z0-9+.-]*://)?(?:[^@/\s]+@)?github\.com[:/]', re.I)
# Without the sort qualifier gh lists by creation, so an older PR that is still active would fall outside
# the 20 and out of the board.
PR_LIST = ['gh', 'pr', 'list', '--state', 'all', '--search', 'sort:updated-desc', '--limit', '20',
           '--json', 'number,title,state,url,headRefName,updatedAt']
PR_TIMEOUT = 15  # seconds; the refresher runs on a loop, so a hung gh must not stall it


def github_origin(remotes):
    """True when the `git remote -v` lines give an origin remote on github.com."""
    for line in remotes:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == 'origin' and GITHUB_URL.match(parts[1]):
            return True
    return False


def github_repo(remotes):
    """"owner/name" from the origin remote's github.com URL, or None when origin is not on github.com or its path
    is not just an owner and a repository name."""
    for line in remotes:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == 'origin' and GITHUB_URL.match(parts[1]):
            m = re.match(r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$', parts[1][GITHUB_URL.match(parts[1]).end():])
            return '%s/%s' % m.groups() if m else None
    return None


def pulls(pid, root, run, repo=None):
    """The repo's pull requests from gh, most recently updated first, or None (with a warning) when gh cannot
    list them. run stands in for subprocess.run. repo ("owner/name"), when known, is passed as --repo: gh
    otherwise picks the base repository by its own rules, which need not be the origin."""
    try:
        r = run(PR_LIST + (['--repo', repo] if repo else []), cwd=root, capture_output=True, text=True, encoding='utf-8',
                timeout=PR_TIMEOUT)
        if r.returncode != 0:
            detail = next((l.strip() for l in (r.stderr or '').splitlines() if l.strip()), '')
            reason = 'gh exited %d' % r.returncode + (': ' + detail if detail else '')
        else:
            found = json.loads(r.stdout)
            if isinstance(found, list) and all(isinstance(e, dict) for e in found):
                prs = [{'number': e.get('number'), 'title': e.get('title'), 'state': e.get('state'), 'url': e.get('url'),
                        'branch': e.get('headRefName'), 'updatedAt': e.get('updatedAt')} for e in found]
                # gh already sorts by update; sorting again keeps that order if the qualifier is ever ignored.
                # ISO times in one zone sort as text.
                return sorted(prs, key=lambda e: str(e['updatedAt'] or ''), reverse=True)
            reason = 'gh printed malformed JSON (not a list of objects)'
    except subprocess.TimeoutExpired:
        reason = 'gh did not finish within %d s' % PR_TIMEOUT
    except (OSError, subprocess.SubprocessError) as e:  # OSError: gh is not installed
        reason = 'gh could not be run (%s)' % e
    except (TypeError, ValueError) as e:  # ValueError covers invalid JSON and output that is not UTF-8
        reason = 'gh printed malformed JSON (%s)' % e
    warn('project %s: cannot list pull requests, %s; the git tab has none this time' % (pid, reason))
    return None


def tab_bytes(doc):
    """A tab document as the bytes written to out/projectTabs. Rebuilt and carried tabs both go through here, so a
    first carry differs from the file it was read from by the carriedSince line alone."""
    return json.dumps(doc, ensure_ascii=False, indent=1).encode('utf-8')


def carried(raw, since, path):
    """The bytes to write for a tab kept from its last export (raw, read from path), marked with carriedSince: since,
    the time the carry began. A file that already carries the marker is returned as it is, so while the source stays
    missing the file keeps its first carriedSince and refresh.py sees no change after the first carry. A file that is
    not a readable JSON object is also kept as it is, with a warning naming it: failing to parse or re-serialise it
    must not stop the export of every project."""
    reason = 'not a JSON object'
    try:
        doc = json.loads(raw.decode('utf-8'))
        if isinstance(doc, dict):
            if 'carriedSince' in doc:
                return raw
            doc['carriedSince'] = since
            return tab_bytes(doc)
    # ValueError covers bytes that are not UTF-8, invalid JSON and a lone surrogate that cannot be encoded back to
    # UTF-8; RecursionError, JSON nested deeper than the parser can follow.
    except (ValueError, RecursionError) as e:
        reason = type(e).__name__
    warn('kept file %s is not a readable JSON object (%s); it is kept without carriedSince' % (path, reason))
    return raw


def main(config=None, out_dir=None, data_dir=None, now=None, run=None):
    """Export every project into out_dir (default out/); returns the process exit code.
    run stands in for subprocess.run when gh lists pull requests (tests pass a fake)."""
    if config is None:
        with io.open(CONFIG, encoding='utf-8') as f:
            config = json.load(f)
    out = out_dir or os.path.join(HERE, 'out')
    stamp = now or datetime.now(timezone.utc).isoformat(timespec='seconds')
    since = datetime.fromisoformat(stamp).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Everything is read before out/ is touched, so a failure leaves the last export in place.
    folder = os.path.join(out, 'projectTabs')
    exported = []
    try:
        for p in board_config.projects(config):
            if not p['repoPath'] or not os.path.isdir(p['repoPath']):
                warn('project %s: repository %s does not exist' % (p['id'], p['repoPath'] or '(no repoPath)'))
                docs = {}
            else:
                docs = spec_tabs(p, load_data(data_dir or DATA_DIR, p['id']), stamp)
                if is_repo(p['repoPath']):
                    docs['git'] = git_tab(p['repoPath'], stamp)
                    if github_origin(docs['git']['remotes']):
                        prs = pulls(p['id'], p['repoPath'], run or subprocess.run, github_repo(docs['git']['remotes']))
                        if prs is not None:
                            docs['git']['pulls'] = prs
            # Kept as bytes: marked with carriedSince on the first carry, then exactly as they were, so refresh.py
            # sees no change and pushes nothing for them until the source comes back.
            kept = {}
            for tab in TABS:
                prev = os.path.join(folder, '%s.%s.json' % (p['id'], tab))
                if tab not in docs and os.path.isfile(prev):
                    with io.open(prev, 'rb') as f:
                        kept[tab] = carried(f.read(), since, prev)
            if kept:
                warn('project %s: cannot rebuild %s; keeping the last export' % (p['id'], ', '.join(kept)))
            exported.append((p['id'], docs, kept))
    except ValueError as e:
        print('export_board: %s; nothing exported' % e, file=sys.stderr)
        return 2

    # Only the tabs this exporter owns (TABS) are removed, and only when they are not about to be (re)written
    # below -- a project dropped from the config, or one whose kept-bytes read above found nothing to keep. A
    # document outside TABS, such as export_sessions.py's <projectId>.findings, is never this exporter's to
    # delete: the folder is shared, but each exporter manages only its own tab suffix's lifecycle.
    os.makedirs(folder, exist_ok=True)
    keep = {'%s.%s.json' % (pid, tab) for pid, docs, kept in exported for tab in list(docs) + list(kept)}
    for name in os.listdir(folder):
        if name.endswith('.json') and name[:-len('.json')].rsplit('.', 1)[-1] in TABS and name not in keep:
            os.remove(os.path.join(folder, name))
    for pid, docs, kept in exported:
        for key, body in docs.items():
            with io.open(os.path.join(folder, '%s.%s.json' % (pid, key)), 'wb') as f:
                f.write(tab_bytes(body))
        for key, raw in kept.items():
            with io.open(os.path.join(folder, '%s.%s.json' % (pid, key)), 'wb') as f:
                f.write(raw)
        print('%s: wrote %d tab documents to %s: %s' % (pid, len(docs), folder, ', '.join(
            '%s=%d B' % (k, len(json.dumps(v, ensure_ascii=False).encode('utf-8'))) for k, v in docs.items()) or 'none'))
        if 'assumptions' in docs:
            print('%s: ledger rows %d (needs you %d); decisions %d; adrs %d; pbis %d; goals %d; rounds %d' % (
                pid, len(docs['assumptions']['rows']), len(docs['assumptions']['humanList']), len(docs['decisions']['decisions']),
                len(docs['decisions']['adrs']), len(docs['backlog']['pbis']), len(docs['spec']['goals']), len(docs['spec']['rounds'])))
    for tab in TABS:  # the single-project layout wrote each tab at the top of out/
        legacy = os.path.join(out, tab + '.json')
        if os.path.exists(legacy):
            os.remove(legacy)
    return 0


if __name__ == '__main__':
    sys.exit(main(out_dir=sys.argv[1] if len(sys.argv) > 1 else None))
