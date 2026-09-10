"""Export the planning state of the build repo named in board.config.json as JSON documents for the Live Dispatch Board.

Reads the solution spec, PRD, brief, ADRs, local review notes and git, and writes one
JSON file per board tab into the output directory (default: out/). Re-run after any
change to the spec or the branch; the orchestrating session pushes the files to the
board's store. Build state per PBI is not recorded anywhere in the repo, so it lives in
BUILD_STATE below and must be edited by hand as PBIs move.
"""
import io, json, os, re, subprocess, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8'))
ROOT = CFG['build']['repoPath']   # the repository being built, not this one
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
SPEC = 'docs/backlog/specs/platform-catalogue.md'
DESIGN = 'docs/backlog/specs/pbi-008-design-system.md'
PRD = 'docs/prd/platform-catalogue.md'
BRIEF = 'docs/brief/raw-notes.md'

# state: done | conditions | partial | todo
BUILD_STATE = {
    'PBI-000': ('done', 'GO-WITH-CONDITIONS, all applied', '', '4caa5dc'),
    'PBI-001': ('done', 'GO-WITH-CONDITIONS, then GO-WITH-NOTES; all applied', '', '4caa5dc'),
    'PBI-002': ('done', 'GO-WITH-CONDITIONS; Lows applied', '', '5238445'),
    'PBI-003': ('done', 'NO-GO, fixed, then GO-WITH-NOTES', '', '4caa5dc'),
    'PBI-004': ('done', 'NO-GO, fixed, then GO-WITH-NOTES', '', '4caa5dc'),
    'PBI-005': ('done', 'NO-GO, fixed, then GO-WITH-NOTES', '', '4caa5dc'),
    'PBI-006': ('done', 'GO-WITH-NOTES; attribution rule recorded as ledger row 31', '', '4caa5dc'),
    'PBI-007': ('done', 'GO-WITH-NOTES; all applied', '', '4caa5dc'),
    'PBI-008': ('done', 'Spec gate 3 rounds; code review GO-WITH-CONDITIONS, applied', '', 'b6a8d48'),
    'PBI-009': ('conditions', 'GO-WITH-CONDITIONS',
                'Two Medium open: the shelf restyles the DEPRECATED stamp via text-data (CR-001); '
                'a JSDoc word re-emits the dead .hidden utility (CR-002). Ledger scroll wrapper not yet applied at 360px.',
                'b6a8d48'),
    'PBI-010': ('partial', 'Not reviewed',
                'Build agent killed by the rate limit: state.ts, profile.ts and reasons.ts written with tests; '
                'not wired into main.ts; the onboarding-plan view is not built.',
                'b6a8d48'),
    'PBI-011': ('todo', '—', 'Delivery verification: offline navigation, axe, viewports, bundle budget.', ''),
    'PBI-012': ('todo', '—', 'GitHub Pages workflow file (authored, not run).', ''),
}

# The brief's "Things I haven't worked out", mapped to where each landed in the spec ledger.
NOT_WORKED_OUT = [
    ('Where the catalogue data lives: Markdown or JSON, one file or many', 1, 'ADR-0001'),
    ('SLA maths for redundant deployments', 6, None),
    ('Does a deprecated dependency block an onboarding plan or warn?', 2, 'ADR-0002'),
    ('Who owns a catalogue entry, and what stops it going stale', 7, None),
    ('Does cost / chargeback belong here at all?', 3, 'ADR-0003'),
    ('Search in a static site', 5, None),
]


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding='utf-8') as f:
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


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8').stdout.strip()


def verdict(path):
    try:
        m = re.search(r'\*\*Verdict:\*\*\s*\*\*([^*]+)\*\*', read(path))
        return m.group(1).strip() if m else '—'
    except FileNotFoundError:
        return None


now = datetime.now(timezone.utc).isoformat(timespec='seconds')
spec, prd, brief, design = read(SPEC), read(PRD), read(BRIEF), read(DESIGN)
rev = re.search(r'^revision:\s*(\d+)', spec, re.M)
drev = re.search(r'^revision:\s*(\d+)', design, re.M)

# --- assumptions ---------------------------------------------------------
human_line = re.search(r'Rows the human must confirm or correct at the plan gate:\*\*\s*(.+)', spec).group(1)
human_rows = re.sub(r'\([^)]*\)', '', human_line.split('.')[0])   # drop "(and explicitly AC-3, AC-4, AC-10)"
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

# --- decisions -----------------------------------------------------------
decisions = [{'decision': c[0], 'rationale': c[1], 'madeBy': c[2], 'date': c[3]}
             for c in table(section(spec, '## Key decisions')) if len(c) >= 4]
adrs = []
for name in sorted(os.listdir(os.path.join(ROOT, 'docs/adr'))):
    t = read('docs/adr/' + name)
    fm = lambda k: (re.search(r'^%s:\s*(.+)$' % k, t, re.M) or [None, ''])[1].split('#')[0].strip()
    adrs.append({'id': fm('id'), 'title': fm('title'), 'status': fm('status'), 'resolves': fm('resolves'),
                 'path': 'docs/adr/' + name})
not_worked = []
for item, n, adr in NOT_WORKED_OUT:
    r = by_n.get(n, {})
    not_worked.append({'item': item, 'row': n, 'adr': adr, 'landed': r.get('resolution', '—'),
                       'status': r.get('status', '—'), 'needsYou': r.get('needsYou', False)})

# --- spec ----------------------------------------------------------------
goals = [{'id': 'G-' + g, 'text': clean(t)} for g, t in re.findall(r'^- \*\*G-(\d+)\*\* (.+)$', spec, re.M)]
core = [clean(t) for t in re.findall(r'^\d+\. \*\*(.+?)\*\*', section(brief, "## Why this is not just a content site"), re.M)]
rounds = []
for r in (1, 2, 3):
    v = verdict('docs/backlog/reviews/platform-catalogue/plan-gate-review-r%d.md' % r)
    if v:
        rounds.append({'gate': 'Plan gate', 'round': r, 'verdict': v})
for r in (1, 2, 3):
    v = verdict('docs/backlog/reviews/PBI-008/spec-review-r%d.md' % r)
    if v:
        rounds.append({'gate': 'PBI-008 spec gate', 'round': r, 'verdict': v})
approval = re.search(r'\*\*Human approval:\*\*\s*\n>\s*\*\*([^*]+)\*\*', spec)
approved_by = re.search(r'\*\*Approved by:\*\*\s*(.+)', spec)

# --- backlog -------------------------------------------------------------
pbis = []
for c in table(section(spec, '### PBI list (proposed)')):
    if len(c) < 7 or not c[0].startswith('PBI-'):
        continue
    state, review, open_items, commit = BUILD_STATE.get(c[0], ('todo', '—', '', ''))
    pbis.append({'id': c[0], 'title': c[1], 'dependsOn': c[2], 'group': c[3], 'risk': c[4],
                 'requiresSpec': c[5], 'state': state, 'review': review, 'open': open_items, 'commit': commit})

# --- git -----------------------------------------------------------------
branch = git('branch', '--show-current')
default = 'master' if git('rev-parse', '--verify', '--quiet', 'master') else ('main' if git('rev-parse', '--verify', '--quiet', 'main') else '')
commits = []
for line in git('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict').splitlines():
    sha, date, subject = line.split('|', 2)
    commits.append({'sha': sha, 'date': date, 'subject': subject})
tracked = git('ls-files').splitlines()
by_dir = {}
for f in tracked:
    d = f.split('/')[0] if '/' in f else '(root)'
    by_dir[d] = by_dir.get(d, 0) + 1
dirty = [l for l in git('status', '--short').splitlines() if l.strip()]
remotes = [l for l in git('remote', '-v').splitlines() if l.strip()]
ahead = git('rev-list', '--count', '%s..%s' % (default, branch)) if default and branch else ''
shortstat = git('diff', '--shortstat', default, branch) if default and branch else ''

docs = {
    'spec': {
        'source': SPEC, 'generatedAt': now, 'revision': rev.group(1) if rev else '—',
        'designRevision': drev.group(1) if drev else '—',
        'goals': goals, 'scopeIn': bullets(section(spec, '### In scope')),
        'scopeOut': bullets(section(spec, '### Out of scope')), 'logicCore': core,
        'prd': {'path': PRD,
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
    'decisions': {'source': SPEC + ', docs/adr/, ' + BRIEF, 'generatedAt': now,
                  'notWorkedOut': not_worked, 'adrs': adrs, 'decisions': decisions},
    'backlog': {'source': SPEC + ' (PBI list) + build state kept in scripts/export-board.py',
                'generatedAt': now, 'pbis': pbis,
                'board': 'Nothing is on the BOARD: PBIs land under Proposed only after the plan gate passes, and its human leg is still open. Everything below was built on the engineering branch.'},
    'git': {'source': 'git, local repository', 'generatedAt': now, 'repoPath': ROOT.replace('\\', '/'),
            'branch': branch, 'defaultBranch': default, 'head': git('rev-parse', '--short', 'HEAD'),
            'remotes': remotes, 'ahead': ahead, 'shortstat': shortstat, 'dirty': dirty,
            'tracked': len(tracked), 'byDir': by_dir, 'commits': commits},
}

os.makedirs(OUT, exist_ok=True)
for key, body in docs.items():
    with io.open(os.path.join(OUT, key + '.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(body, f, ensure_ascii=False, indent=1)
print('wrote %d tab documents to %s: %s' % (len(docs), OUT,
      ', '.join('%s=%d B' % (k, len(json.dumps(v, ensure_ascii=False).encode('utf-8'))) for k, v in docs.items())))
print('ledger rows %d (needs you %d); decisions %d; adrs %d; pbis %d; commits %d; goals %d; rounds %d' % (
    len(ledger), len(human), len(decisions), len(adrs), len(pbis), len(commits), len(goals), len(rounds)))
