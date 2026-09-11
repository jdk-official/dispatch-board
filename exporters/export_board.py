"""Export the planning state of every project in board.config.json as JSON documents for the Live Dispatch Board.

    python exporters/export_board.py [out_dir]

For each project, reads the solution spec, PRD, brief, ADRs, local review notes and git of its repository
(paths from the project's docs, relative to its repoPath) and writes out/projectTabs/<projectId>.<tab>.json
for tab in spec, assumptions, decisions, backlog and git, replacing that folder. A tab is built only when
its source exists: spec, assumptions, decisions and backlog all need the spec, git needs a git repository.
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
import io, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

import board_config

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'board.config.json')
DATA_DIR = os.path.join(HERE, 'projects')
TABS = ('spec', 'assumptions', 'decisions', 'backlog', 'git')
STATES = ('done', 'conditions', 'partial', 'todo')
ROUNDS = (1, 2, 3)  # review rounds looked for, per gate


def warn(msg):
    print('export_board: ' + msg, file=sys.stderr)


def read(root, rel):
    with io.open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()


def clean(cell):
    cell = cell.strip().replace('\\|', '|')
    cell = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cell)   # links -> text
    return cell


def section(text, heading):
    m = re.search(r'^' + re.escape(heading) + r'\s*$', text, re.M)
    if not m:
        return ''
    rest = text[m.end():]
    level = heading.split(' ')[0]
    stop = re.search(r'^#{1,%d} ' % len(level), rest, re.M)
    return rest[:stop.start()] if stop else rest


def table(block):
    rows = []
    for line in block.splitlines():
        if not line.startswith('|') or re.match(r'^\|\s*-', line):
            continue
        cells = [clean(c) for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
        rows.append(cells)
    return rows[1:] if rows else []


def bullets(block):
    return [clean(m) for m in re.findall(r'^- (.+)$', block, re.M)]


LATER = '### Future iterations (not planned)'
# A list item's marker, "-", "*", "+" or "1.", then a space or the end of the line: never "-text" or "**bold".
MARKER = re.compile(r'(?:[-*+]|\d{1,9}\.)(?: (.*))?$')
# A horizontal rule such as "---", "* * *" or "- - -", which would otherwise read as a list item.
RULE = re.compile(r' {0,3}([-*_])(?: *\1){2,} *$')


def later_items(spec):
    """The ideas listed under the spec's LATER heading, as [{title, description}]; [] without the heading.

    The list runs to the next heading of the same level or higher, so a #### sub-heading inside it only groups
    more ideas. Each list item ("-", "*", "+" or "1." marker) indented by at most three spaces is one idea, and
    a wrapped or indented line straight after it continues it. A list line indented further (four spaces or a
    tab) is a nested item: it is not an idea of its own, and it and the lines that continue it are kept in its
    idea's text, marker included. An indented line after a blank line (a loose list's nested item or paragraph)
    also stays in the idea, so nothing written under an idea is lost; a blank line followed by an unindented
    line that starts no idea, or a horizontal rule, ends it. The title is the first bold span,
    less a trailing colon, and the description is the text after that span, less a leading colon. A bullet with words before its bold span
    keeps them: its description is the whole bullet. A bullet without a bold span is all title with no
    description, so no idea is dropped for how it is formatted.
    """
    block = section(spec.replace('\r\n', '\n'), LATER)
    found, current, blank = [], None, False
    for line in block.split('\n'):
        text = line.expandtabs(4)
        body = text.lstrip(' ')
        m = MARKER.match(body)
        indent = len(text) - len(body)
        if not line.strip():
            blank = True
            continue
        if RULE.match(text):
            current = None
        elif m and indent <= 3:
            current = [m.group(1) or '']
            found.append(current)
        elif blank and not indent:
            current = None  # a paragraph after the list, not part of the idea above it
        elif current is not None:
            current.append(line.strip())  # a wrapped line, or a nested item or a line that continues one
        blank = False
    items = []
    for parts in found:
        text = clean(' '.join(p.strip() for p in parts))
        if not text:
            continue
        b = re.search(r'\*\*(.+?)\*\*', text)
        title = b.group(1).strip().rstrip(':').rstrip() if b else ''
        if not title:
            items.append({'title': text, 'description': ''})
        elif text[:b.start()].strip():
            items.append({'title': title, 'description': text})
        else:
            items.append({'title': title, 'description': re.sub(r'^:\s*', '', text[b.end():].strip())})
    return items


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
        m = re.search(r'\*\*Verdict:\*\*\s*\*\*([^*]+)\*\*', read(root, path))
        return m.group(1).strip() if m else '—'
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


def build_state(data):
    """PBI id -> (state, review, open items, commit); state is one of STATES."""
    return {pbi: (e.get('state', 'todo'), e.get('review', '—'), e.get('open', ''), e.get('commit', ''))
            for pbi, e in (data.get('buildState') or {}).items()}


def not_worked_out(data):
    """The brief's "Things I haven't worked out": (item, spec ledger row, ADR id or None)."""
    return [(e.get('item', ''), e.get('row'), e.get('adr')) for e in data.get('notWorkedOut') or []]


def spec_tabs(p, data, now):
    """The spec, assumptions, decisions and backlog tabs, all read from the project's spec; {} without one."""
    root, paths = p['repoPath'], p['docs']

    def doc(key):
        rel = paths.get(key)
        return read(root, rel) if rel and os.path.isfile(os.path.join(root, rel)) else None

    spec = doc('spec')
    if spec is None:
        return {}
    SPEC, PRD, BRIEF, ADRS = paths['spec'], paths.get('prd'), paths.get('brief'), (paths.get('adrDir') or '').rstrip('/')
    prd, brief, design = doc('prd'), doc('brief') or '', doc('design') or ''
    rev = re.search(r'^revision:\s*(\d+)', spec, re.M)
    drev = re.search(r'^revision:\s*(\d+)', design, re.M)

    # --- assumptions -----------------------------------------------------
    human = []
    human_line = re.search(r'Rows the human must confirm or correct at the plan gate:\*\*\s*(.+)', spec)
    if human_line:
        human_rows = re.sub(r'\([^)]*\)', '', human_line.group(1).split('.')[0])   # drop "(and explicitly AC-3, AC-4, AC-10)"
        human = sorted({int(n) for n in re.findall(r'\b(\d+)\b', human_rows)})
    ledger = []
    for c in table(section(spec, '## Assumptions & open questions')):
        if len(c) < 6 or not c[0].isdigit():
            continue
        n = int(c[0])
        status = re.sub(r'\*', '', c[3]).strip()
        level = re.match(r'\**(Low[–-]Medium|Medium|High|Low)', c[5])
        ledger.append({'n': n, 'question': c[1], 'resolution': c[2], 'status': status,
                       'source': c[4], 'impact': c[5], 'level': level.group(1) if level else '—',
                       'needsYou': n in human})
    by_n = {r['n']: r for r in ledger}

    # --- decisions -------------------------------------------------------
    decisions = [{'decision': c[0], 'rationale': c[1], 'madeBy': c[2], 'date': c[3]}
                 for c in table(section(spec, '## Key decisions')) if len(c) >= 4]
    adrs = []
    if ADRS and os.path.isdir(os.path.join(root, ADRS)):
        for name in sorted(n for n in os.listdir(os.path.join(root, ADRS)) if n.endswith('.md')):
            t = read(root, ADRS + '/' + name)
            fm = lambda k: (re.search(r'^%s:\s*(.+)$' % k, t, re.M) or [None, ''])[1].split('#')[0].strip()
            adrs.append({'id': fm('id'), 'title': fm('title'), 'status': fm('status'), 'resolves': fm('resolves'),
                         'path': ADRS + '/' + name})
    not_worked = []
    for item, n, adr in not_worked_out(data):
        r = by_n.get(n, {})
        not_worked.append({'item': item, 'row': n, 'adr': adr, 'landed': r.get('resolution', '—'),
                           'status': r.get('status', '—'), 'needsYou': r.get('needsYou', False)})

    # --- spec ------------------------------------------------------------
    goals = [{'id': 'G-' + g, 'text': clean(t)} for g, t in re.findall(r'^- \*\*G-(\d+)\*\* (.+)$', spec, re.M)]
    core = [clean(t) for t in re.findall(r'^\d+\. \*\*(.+?)\*\*', section(brief, "## Why this is not just a content site"), re.M)]
    rounds = []
    for review in paths.get('reviews') or []:
        for r in ROUNDS:
            v = verdict(root, review['path'].replace('{round}', str(r)))
            if v:
                rounds.append({'gate': review['gate'], 'round': r, 'verdict': v})
    approval = re.search(r'\*\*Human approval:\*\*\s*\n>\s*\*\*([^*]+)\*\*', spec)
    approved_by = re.search(r'\*\*Approved by:\*\*\s*(.+)', spec)

    # --- backlog ---------------------------------------------------------
    state_of, pbis = build_state(data), []
    for c in table(section(spec, '### PBI list (proposed)')):
        if len(c) < 7 or not c[0].startswith('PBI-'):
            continue
        state, review, open_items, commit = state_of.get(c[0], ('todo', '—', '', ''))
        pbis.append({'id': c[0], 'title': c[1], 'dependsOn': c[2], 'group': c[3], 'risk': c[4],
                     'requiresSpec': c[5], 'state': state, 'review': review, 'open': open_items, 'commit': commit})

    return {
        'spec': {
            'source': SPEC, 'generatedAt': now, 'revision': rev.group(1) if rev else '—',
            'designRevision': drev.group(1) if drev else '—',
            'goals': goals, 'scopeIn': bullets(section(spec, '### In scope')),
            'scopeOut': bullets(section(spec, '### Out of scope')), 'logicCore': core,
            'prd': None if prd is None else {
                'path': PRD,
                'frs': len(re.findall(r'^- \*\*FR-\d+', prd, re.M)),
                'nfrs': len(re.findall(r'^- \*\*NFR-\d+', prd, re.M)),
                'constraints': len(re.findall(r'^- \*\*C-\d+', prd, re.M)),
                'acs': len(re.findall(r'^- \*\*AC-\d+', prd, re.M)),
                'assumptions': len(re.findall(r'^\| \*\*A-\d+', prd, re.M))},
            'rounds': rounds,
            'approval': approval.group(1).strip() if approval else '—',
            'approvedBy': approved_by.group(1).strip() if approved_by else '—',
        },
        'assumptions': {'source': SPEC, 'generatedAt': now, 'rows': ledger, 'humanList': human},
        'decisions': {'source': ', '.join(x for x in (SPEC, ADRS and ADRS + '/', BRIEF) if x), 'generatedAt': now,
                      'notWorkedOut': not_worked, 'adrs': adrs, 'decisions': decisions},
        'backlog': {'source': '%s (PBI list) + build state kept in projects/%s.json in the dispatch-board repo' % (SPEC, p['id']),
                    'generatedAt': now, 'pbis': pbis, 'board': data.get('boardNote', ''), 'later': later_items(spec)},
    }


# The userinfo of a URL remote: everything between "://" and the last "@" before the host's first "/".
USERINFO = re.compile(r'(?<=://)[^/\s]*@')


def public_remote(line):
    """A `git remote -v` line without the userinfo of its URL, so a token stored in a remote URL is never published."""
    return USERINFO.sub('', line)


def git_tab(root, now):
    branch = git(root, 'branch', '--show-current')
    default = 'master' if git(root, 'rev-parse', '--verify', '--quiet', 'master') else ('main' if git(root, 'rev-parse', '--verify', '--quiet', 'main') else '')
    commits = []
    for line in git(root, 'log', '--pretty=format:%h|%ad|%s', '--date=iso-strict').splitlines():
        sha, date, subject = line.split('|', 2)
        commits.append({'sha': sha, 'date': date, 'subject': subject})
    tracked = git(root, 'ls-files').splitlines()
    by_dir = {}
    for f in tracked:
        d = f.split('/')[0] if '/' in f else '(root)'
        by_dir[d] = by_dir.get(d, 0) + 1
    dirty = [l for l in git(root, 'status', '--short').splitlines() if l.strip()]
    remotes = [public_remote(l) for l in git(root, 'remote', '-v').splitlines() if l.strip()]
    ahead = git(root, 'rev-list', '--count', '%s..%s' % (default, branch)) if default and branch else ''
    shortstat = git(root, 'diff', '--shortstat', default, branch) if default and branch else ''
    return {'source': 'git, local repository', 'generatedAt': now, 'repoPath': root.replace('\\', '/'),
            'branch': branch, 'defaultBranch': default, 'head': git(root, 'rev-parse', '--short', 'HEAD'),
            'remotes': remotes, 'ahead': ahead, 'shortstat': shortstat, 'dirty': dirty,
            'tracked': len(tracked), 'byDir': by_dir, 'commits': commits}


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

    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
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
