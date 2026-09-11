"""Export every recent Claude Code session for the board: one sessions/<id> document each (title,
folder, activity, usage) and one runs/<agentId> row per agent the session dispatched.

    python exporters/export_sessions.py [out_dir]

Sessions are discovered, not listed: every main transcript under sessions.projectsRoot written to in
the last sessions.days days, plus every session linked to a project in board.config.json
(projects[].sessions; build.sessions and usage.sessions in the older shape). Each session and run
records its project id, or null when it is linked to none, and out/projects/<projectId>.json combines
a project's linked sessions: run counts, latest activity, and one usage block for all of them. Sessions
whose working folder or project folder name matches a sessions.exclude glob are never read. The first
prompt is published only with sessions.showFirstPrompt, and then with obvious secrets redacted.

Per session, the main transcript records when each agent was launched (Agent tool use), stopped
(TaskStop) and finished (a <task-notification> with status, result, subagent_tokens and duration_ms);
subagents/ holds each agent's own transcript and meta (agentType, description). A run with no finish
whose transcript was written to recently is "running". Rows no transcript can produce (work the
orchestrator did in-line) come from runs.manual, each placed straight after its "after" run.
Transcript text is treated purely as data.

For the Agent catalogue tab, a subagent's run document also records its agentType (from its meta, omitted
when the meta has none) and start (its launch time, omitted when unknown); runs.manual rows carry neither.
Each session document records skillUses, {"<skill id>": {count, last}} ({} when unused), from its main
transcript only. It counts Skill tool calls (their input.skill; their args are never read) and plugin
commands the owner typed (a user record, not isMeta, whose text starts with <command-message> or
<command-name> and names "/<plugin>:<skill>"). Bare slash commands such as /loop are not counted, and
nothing inside tool calls, tool results, attachments or system records is scanned. A skill id outside
SKILL_ID is dropped with a warning.

Effective usage weights token types by relative cost: input 1, cache read 0.1, cache write 2, output 5.

Parsed sessions are cached in out/.cache/sessions.json and re-read only when a transcript or the
running window changes, while one of the session's agents is running, or after one of its agent files
could not be read. Everything else taken from the config (project links, window, first prompt) is applied
when the documents are written. Writes out/sessions/*.json, out/runs/*.json and out/projects/*.json,
replacing all three.

A malformed or vanished transcript file costs only that agent or session (a warning on stderr; an
agent or session that cannot be re-read keeps its last cached result, except that an agent's row kept as
running becomes killed once the running window has passed since its end). A line nested too deeply to parse,
or a response whose token counts are not numbers, costs only that record. The exit code is non-zero, and out/ is
left as it was, only when the export itself cannot be trusted: projectsRoot is missing, the project list
is unusable, a sessions or runs value is not its documented type or a runs.manual row is malformed, or a
linked session's transcript cannot be found.
"""
import fnmatch, glob, io, json, math, os, re, shutil, sys, tempfile, time
from datetime import datetime, timezone, timedelta

import board_config

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'board.config.json')
HOURS = 168  # hourly usage series covers the last week of a session's activity
PARSER_VERSION = 5  # bump when parsing changes, to drop cached results
# Skill ids become keys in session documents and are matched against catalogue ids, so they are kept to a safe set.
SKILL_ID = re.compile(r'^[A-Za-z0-9_.:-]{1,100}$')

LANE = {'requirements-author': 'req', 'Plan': 'plan', 'code-writer': 'cw', 'test-writer': 'tw',
        'code-reviewer': 'cr', 'verifier': 'ver'}
REVIEW_LANES = ('plan', 'cr', 'ver')
BUILD_LANES = ('req', 'cw', 'tw')
TOKEN = r'(NO-GO|NOT-DONE|GO-WITH-CONDITIONS|GO-WITH-NOTES|CHANGES-REQUIRED|APPROVE-WITH-(?:NOTES|CONDITIONS)|DONE-WITH-CONDITIONS|APPROVED?|REJECT(?:ED)?|GO|DONE)'
REVIEW_TOKENS = ('NO-GO', 'GO-WITH-CONDITIONS', 'GO-WITH-NOTES', 'CHANGES-REQUIRED', 'APPROVE-WITH-NOTES',
                 'APPROVE-WITH-CONDITIONS', 'APPROVE', 'APPROVED', 'REJECT', 'REJECTED', 'GO')
BUILD_TOKENS = ('NOT-DONE', 'DONE-WITH-CONDITIONS', 'DONE')
# A verifier reports whether it could exercise the change or had to declare a fallback, rather than a review verdict.
VERIFIER_TOKENS = ('exercised', 'fallback-declared')
VERIFIER_WORD = r'(exercised|fallback-declared)'
VERIFIER_TIERS = (
    (r'\boutcome\W{0,6}' + VERIFIER_WORD + r'\b',),  # the JSON "outcome" key or an "Outcome:" label
    (r'\bverdict\W{0,6}' + VERIFIER_WORD + r'\b', r'(?:\*\*|`)' + VERIFIER_WORD + r'(?:\*\*|`)'),
    (r'\b' + VERIFIER_WORD + r'\b',),
)
# A verifier leads with its outcome and then says what it observed or why it could not run the flow, so a word
# straight after a negation ("not exercised", "could not be exercised", "wasn't exercised") is never its outcome.
NEGATED = re.compile(r"(?:\b(?:not|never|no|cannot|without|unable\s+to|rather\s+than|instead\s+of)|n't)"
                     r"(?:[\s-]+(?:be|been|being|yet|fully|actually|really))*[\s*`-]*$", re.I)
RATE_LIMIT = re.compile(r"hit your (?:session|weekly|usage) limit", re.I)
FIX = re.compile(r'\b(review|LOWs?|notes|fix(?:es)?|CR-\d)', re.I)
# Obvious credentials in prompt text. The long-run rule needs a digit, an upper- and a lower-case letter
# and leaves out "/", so ordinary words, paths and commit hashes under 32 characters survive.
SECRETS = [
    (re.compile(r'(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)(\s*[=:]\s*)\S+'), r'\1\2[redacted]'),
    (re.compile(r'\bsk-[A-Za-z0-9_-]{16,}'), '[redacted]'),
    (re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}'), '[redacted]'),
    (re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'), '[redacted]'),
    (re.compile(r'\b[0-9a-fA-F]{32,}\b'), '[redacted]'),
    (re.compile(r'(?=[A-Za-z0-9+_-]*\d)(?=[A-Za-z0-9+_-]*[A-Z])(?=[A-Za-z0-9+_-]*[a-z])[A-Za-z0-9+_-]{32,}={0,2}'), '[redacted]'),
]

MODEL_LABEL = {'claude-opus-5': 'Opus 5', 'claude-fable-5-1': 'Fable 5.1', 'claude-sonnet-5': 'Sonnet 5', 'claude-haiku-4-5-20251001': 'Haiku 4.5'}
GROUP_LABEL = {
    'subagents': 'Subagents (the agent fleet)', 'reread': 'Re-reading instructions and history',
    'think': 'Thinking and replies', 'files': 'Files and shell commands', 'browser': 'Browser checks',
    'artifact': 'Publishing this dashboard', 'dispatch': 'Dispatching agents', 'skills': 'Loading skills and tools',
    'loop': 'Loop scheduling', 'ask': 'Questions to you', 'connectors': 'Connectors', 'other': 'Other tools',
}


def is_number(v):
    """A usable JSON number: an int or a finite float, never a bool (JSON true reads as a Python int)."""
    return not isinstance(v, bool) and (isinstance(v, int) or (isinstance(v, float) and math.isfinite(v)))


# (block, key, check, what the value must be) for each typed value under sessions and runs; board_config.manual
# checks the runs.manual rows. A value of the wrong type is refused rather than read loosely: bool("false") is
# True, and a string exclude would be matched one character at a time, so "*-private" would exclude everything.
CONFIG_TYPES = (
    ('sessions', 'days', is_number, 'a number'),
    ('sessions', 'projectsRoot', lambda v: isinstance(v, str), 'a string'),
    ('sessions', 'exclude', lambda v: isinstance(v, list) and all(isinstance(p, str) for p in v), 'a list of strings'),
    ('sessions', 'showFirstPrompt', lambda v: isinstance(v, bool), 'true or false'),
    ('runs', 'runningWindowMinutes', is_number, 'a number'),
)


def check_types(cfg):
    """Raise ValueError, naming the key, for a sessions or runs block that is not an object or a value in it that
    does not have its CONFIG_TYPES type. A value that is left out takes its default."""
    for block in ('sessions', 'runs'):
        if not isinstance(cfg.get(block, {}), dict):
            raise ValueError('"%s" must be an object, not %s' % (block, type(cfg[block]).__name__))
    for block, key, ok, what in CONFIG_TYPES:
        values = cfg.get(block, {})
        if key in values and not ok(values[key]):
            raise ValueError('%s.%s must be %s, not %r' % (block, key, what, values[key]))


def settings(cfg, projects_root=None):
    """The parts of board.config.json this exporter reads, with their defaults. Raises ValueError for an unusable
    project list, a value of the wrong type or a malformed runs.manual row."""
    check_types(cfg)
    scfg, rcfg = cfg.get('sessions', {}), cfg.get('runs', {})
    projects, project_of = board_config.projects(cfg), {}
    for p in projects:
        for sid in p['sessions']:
            project_of.setdefault(sid, p['id'])  # a session listed under two projects belongs to the first
    meta = {p['id'] for p in projects if p['statusDoc'] == 'meta/status'}
    return {
        'root': projects_root or scfg.get('projectsRoot') or os.path.join(os.path.expanduser('~'), '.claude', 'projects'),
        'days': scfg.get('days', 7),
        'build': set(project_of),  # linked sessions: always exported, and a missing transcript is fatal
        # The session document's "build" flag is read only by copies of the page from before projects, which
        # show a build session with the one set of tabs they know: those of meta/status's project.
        'legacy_build': {sid for sid, pid in project_of.items() if pid in meta},
        'projects': projects,
        'project_of': project_of,
        'window': rcfg.get('runningWindowMinutes', 10) * 60,
        'window_minutes': rcfg.get('runningWindowMinutes', 10),
        'manual': board_config.manual(cfg),
        'exclude': list(scfg.get('exclude') or []),
        'show_first_prompt': bool(scfg.get('showFirstPrompt', False)),
    }


def warn(msg):
    print('export_sessions: ' + msg, file=sys.stderr)


def group_of(tool):
    if tool in ('Bash', 'PowerShell', 'Write', 'Edit', 'Read', 'Glob', 'Grep', 'NotebookEdit'):
        return 'files'
    if tool.startswith('mcp__Claude_Browser__') or tool.startswith('mcp__claude-in-chrome__'):
        return 'browser'
    if tool == 'Artifact':
        return 'artifact'
    if tool in ('Agent', 'TaskStop', 'SendMessage', 'Workflow'):
        return 'dispatch'
    if tool in ('Skill', 'ToolSearch'):
        return 'skills'
    if tool in ('ScheduleWakeup', 'CronCreate', 'CronDelete'):
        return 'loop'
    if tool == 'AskUserQuestion':
        return 'ask'
    if tool.startswith('mcp__'):
        return 'connectors'
    return 'other'


def tokens(u):
    i = u.get('input_tokens') or 0
    cr = u.get('cache_read_input_tokens') or 0
    cw = u.get('cache_creation_input_tokens') or 0
    o = u.get('output_tokens') or 0
    return i, cr, cw, o, i + 0.1 * cr + 2 * cw + 5 * o


def records(path):
    """(raw line, parsed record) pairs for every line holding a JSON object; anything else is skipped."""
    with io.open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                o = json.loads(line)
            except (ValueError, RecursionError):  # RecursionError: nested deeper than the parser can follow
                continue
            if isinstance(o, dict):
                yield line, o


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def text_of(content):
    if isinstance(content, str):
        return content
    return '\n'.join(c.get('text', '') for c in content or [] if isinstance(c, dict) and c.get('type') == 'text')


def tag(block, name):
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), block, re.S)
    return m.group(1) if m else ''


def epoch(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00')).timestamp()


def stamp(o):
    """The record's timestamp if it is a readable ISO time, else None."""
    ts = o.get('timestamp')
    try:
        epoch(ts)
        return ts
    except (AttributeError, TypeError, ValueError):
        return None


def num(v):
    """A non-negative whole number from a tag or field that may be missing, blank or malformed; 0 if unreadable."""
    try:
        return max(0, int(float(str(v).strip())))
    except (TypeError, ValueError, OverflowError):
        return 0


def redact(text):
    for pat, repl in SECRETS:
        text = pat.sub(repl, text)
    return text


def verifier_outcome(text):
    """A verifier's outcome word, exercised or fallback-declared, or None, read in any case. An outcome label (the
    first of VERIFIER_TIERS) decides when there is one. Without it, every other mention counts together, whether
    Verdict-labelled, bold, code-quoted or bare, so a quoted exercised in the explanation cannot outrank a bare
    fallback-declared headline. A word after a negation is skipped. Wherever both words are found, fallback-declared
    wins: a verifier that ran part of a flow and declared a fallback for the rest did not exercise the change, and
    under-claiming is the safe direction."""
    for tiers in (VERIFIER_TIERS[:1], VERIFIER_TIERS[1:]):
        found = {m.group(1).lower() for tier in tiers for pat in tier for m in re.finditer(pat, text, re.I)
                 if not NEGATED.search(text[max(0, m.start() - 60):m.start()])}
        if found:
            return 'fallback-declared' if 'fallback-declared' in found else 'exercised'
    return None


def verdict_of(text, lane):
    """The agent's own verdict token: a labelled 'Verdict:' first, then a bold or code-quoted token, then a bare one.
    On the ver lane, the verifier's outcome word comes first."""
    if lane == 'ver':
        outcome = verifier_outcome(text)
        if outcome:
            return outcome
    allowed = REVIEW_TOKENS if lane in REVIEW_LANES else BUILD_TOKENS
    for pat in (r'[Vv]erdict\W{0,6}' + TOKEN, r'(?:\*\*|`)' + TOKEN + r'(?:\*\*|`)', r'\b' + TOKEN + r'\b'):
        found = [t for t in re.findall(pat, text) if t in allowed]
        if found:
            # Reviews state their verdict last (a re-review often quotes the previous round's first);
            # builders lead with it.
            return found[-1] if lane in REVIEW_LANES else found[0]
    return None


def kind_of(token, lane):
    if not token or token in VERIFIER_TOKENS:
        return 'done'  # a verifier's word is neither a pass nor a fail, so only its verdict text carries it
    if lane in BUILD_LANES:
        return 'changes' if token == 'NOT-DONE' else 'done'
    if lane not in REVIEW_LANES:
        return 'done'
    if token.startswith(('NO-GO', 'REJECT')):
        return 'nogo'
    if token == 'CHANGES-REQUIRED':
        return 'changes'
    return 'go'


def classify(lane, fin, stop_at, text, begin, end, age, window):
    """kind, verdict and minutes for one agent run. fin is its finish (notification or inline result) or
    None, stop_at when a TaskStop last named it, text its last reply, age seconds since its transcript was written."""
    result = (fin or {}).get('result') or ''
    # A stop that ends an agent is echoed by a "killed" notification, and the latest notification wins. So a
    # completed finish, whether it came after the stop (the agent was resumed) or before it (the stop came
    # too late to kill anything), means the stop did not end the run.
    if stop_at and not (fin and fin['status'] == 'completed'):
        kind, verdict = 'killed', 'stopped'
    elif RATE_LIMIT.search(text) or RATE_LIMIT.search(result):
        kind, verdict = 'killed', 'killed · rate limit'
    elif fin and fin['status'] == 'completed':
        token = verdict_of(result, lane) or verdict_of(text, lane)
        kind, verdict = kind_of(token, lane), token or 'finished'
    elif fin:
        kind, verdict = 'killed', fin['status'] or 'failed'
    elif age < window:
        kind, verdict = 'running', 'running'
    else:
        kind, verdict = 'killed', 'no result'
    ms = num((fin or {}).get('ms'))
    try:
        minutes = round(ms / 60000) if ms else (round((epoch(end) - epoch(begin)) / 60) if begin and end else 0)
    except (AttributeError, TypeError, ValueError):
        minutes = 0
    return kind, verdict, minutes


def carried(row, window, now):
    """The last row of an agent that could not be re-read, as it is carried over. Nothing reads its file, so a row
    kept as running would never end: once the running window has passed since its end, or it has no readable
    end, it becomes killed with no result, as classify() judges an agent that went quiet. A changed row is a copy;
    any other row is returned as it is."""
    if row.get('kind') != 'running':
        return row
    try:
        quiet = now - epoch(row['end']) >= window
    except (AttributeError, KeyError, TypeError, ValueError):
        quiet = True
    return dict(row, kind='killed', verdict='no result') if quiet else row


def pbis(desc):
    """PBI ids named in a description, including the PBI-003/004/005 shorthand."""
    out = []
    for m in re.finditer(r'PBI-(\d{3})((?:/\d{3})*)', desc):
        out.append(m.group(1))
        out += re.findall(r'\d{3}', m.group(2))
    return sorted(set(out))


TOKEN_FIELDS = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')


def response(by, o):
    """Record one assistant response, deduplicated by message id (streamed responses span several lines)."""
    m = o.get('message')
    if o.get('type') != 'assistant' or not isinstance(m, dict) or not isinstance(m.get('usage'), dict) or not m['usage'] \
            or m.get('model') == '<synthetic>':
        return
    # A count that is not a number would break every sum over the session, so the record is skipped instead.
    if not all(m['usage'].get(k) is None or is_number(m['usage'][k]) for k in TOKEN_FIELDS):
        return
    r = by.setdefault(m.get('id') or o.get('uuid'), {'model': m.get('model'), 'ts': stamp(o), 'tools': [], 'usage': None})
    r['usage'] = m['usage']
    for c in m.get('content') or []:
        if isinstance(c, dict) and c.get('type') == 'tool_use':
            r['tools'].append(c.get('name', ''))


def reject(rejects, o):
    if o.get('apiErrorStatus') == 429 or 'quotaLimits' in o:
        q = o.get('quotaLimits') if isinstance(o.get('quotaLimits'), dict) else {}
        rejects.append({'at': stamp(o), 'resetsAt': q.get('resetsAt'), 'type': q.get('rateLimitType'),
                        'overage': q.get('overageDisabledReason')})


def load_meta(path):
    """An agent's meta.json; a missing, truncated or non-object file reads as {}."""
    try:
        with io.open(path, encoding='utf-8') as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def cwd_of(path):
    """The working folder a transcript records, read only as far as its first mention."""
    return next((o['cwd'] for _, o in records(path) if isinstance(o.get('cwd'), str) and o['cwd']), '')


def excluded(patterns, folder, cwd):
    names = [folder] + ([cwd, cwd.replace('\\', '/')] if cwd else [])
    return any(fnmatch.fnmatch(n, p) for p in patterns for n in names)


def read_subagent(path):
    by, rejects, ts, last_text = {}, [], [], ''
    for _, o in records(path):
        if stamp(o):
            ts.append(o['timestamp'])
        reject(rejects, o)
        response(by, o)
        if o.get('type') == 'assistant':
            t = text_of((o.get('message') or {}).get('content'))
            if t.strip():
                last_text = t
    resps = list(by.values())
    last = resps[-1]['usage'] if resps else {}
    ctx = sum(last.get(k) or 0 for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens'))
    return {'resps': resps, 'rejects': rejects, 'first': ts[0] if ts else None, 'last': ts[-1] if ts else None,
            'text': last_text, 'ctx': ctx}


def usage_doc(main, subs, span):
    totals = dict(input=0, cacheRead=0, cacheWrite=0, output=0, effective=0.0, requests=0)
    models, groups, hourly = {}, {k: 0.0 for k in GROUP_LABEL}, {}

    def add(resp, is_sub):
        i, cr, cw, o, eff = tokens(resp['usage'])
        mm = models.setdefault(resp['model'], dict(requests=0, input=0, cacheRead=0, cacheWrite=0, output=0, effective=0.0))
        for d in (totals, mm):
            d['requests'] += 1
            for k, v in (('input', i), ('cacheRead', cr), ('cacheWrite', cw), ('output', o), ('effective', eff)):
                d[k] += v
        if resp['ts']:
            b = hourly.setdefault(resp['ts'][:13], {'main': 0.0, 'sub': 0.0})
            b['sub' if is_sub else 'main'] += eff
        return i, cr, cw, o, eff

    for r in main['resps']:
        i, cr, cw, o, eff = add(r, False)
        groups['reread'] += 0.1 * cr
        rest = i + 2 * cw + 5 * o
        tg = [group_of(t) for t in r['tools']] or ['think']
        for g in tg:
            groups[g] += rest / len(tg)
    agents = []
    for s in subs:
        eff_sum, mods = 0.0, {}
        for r in s['resps']:
            eff_sum += add(r, True)[4]
            mods[r['model']] = mods.get(r['model'], 0) + 1
        groups['subagents'] += eff_sum
        raw = s['agentType'] or 'unknown'
        top = max(mods, key=mods.get) if mods else None
        agents.append({'id': s['id'], 'type': 'Gate reviewer' if raw == 'Plan' else raw.split(':')[-1], 'agentType': raw,
                       'description': s['description'], 'requests': len(s['resps']), 'effective': round(eff_sum),
                       'model': top, 'modelLabel': MODEL_LABEL.get(top, top or '—'), 'start': s['first'], 'end': s['last']})

    all_rejects = main['rejects'] + [x for s in subs for x in s['rejects']]
    windows = {}  # refusals grouped by the reset time the platform reported
    for r in sorted(all_rejects, key=lambda x: x['at'] or ''):
        key = r['resetsAt']
        if key is None:  # a refusal without quota detail belongs to the next reset after it
            later_resets = sorted(k for k in windows if isinstance(k, (int, float)) and r['at'] and datetime.fromtimestamp(k, timezone.utc).isoformat() > r['at'])
            key = later_resets[0] if later_resets else 'unknown'
        w = windows.setdefault(key, {'firstAt': r['at'], 'refused': 0, 'type': r['type'] or 'five_hour'})
        w['refused'] += 1
    limits = [{'firstAt': w['firstAt'], 'refused': w['refused'], 'type': w['type'],
               'resetsAt': datetime.fromtimestamp(k, timezone.utc).isoformat() if isinstance(k, (int, float)) else None}
              for k, w in sorted(windows.items(), key=lambda kv: kv[1]['firstAt'] or '')]

    series = []
    if span[0] and span[1]:
        end = datetime.fromisoformat(span[1][:13] + ':00:00+00:00')
        t = max(datetime.fromisoformat(span[0][:13] + ':00:00+00:00'), end - timedelta(hours=HOURS - 1))
        while t <= end:
            k = t.strftime('%Y-%m-%dT%H')
            b = hourly.get(k, {'main': 0.0, 'sub': 0.0})
            series.append({'hour': k, 'main': round(b['main']), 'sub': round(b['sub'])})
            t += timedelta(hours=1)
    return {
        'source': 'Claude Code transcripts for this session and its %d agent run%s, on this computer' % (len(agents), '' if len(agents) == 1 else 's'),
        'weights': {'input': 1, 'cacheRead': 0.1, 'cacheWrite': 2, 'output': 5},
        'span': {'first': span[0], 'last': span[1]},
        'totals': {k: (round(v) if isinstance(v, float) else v) for k, v in totals.items()},
        'byModel': sorted([{'model': k, 'label': MODEL_LABEL.get(k, k), **{kk: (round(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()}}
                           for k, v in models.items()], key=lambda m: -m['effective']),
        'groups': [{'key': k, 'label': GROUP_LABEL[k], 'effective': round(v)} for k, v in groups.items() if v >= 1],
        'subagents': agents, 'hourly': series, 'limits': limits,
        'overage': 'Extra usage beyond the limit is turned off for your organisation, so work paused until each reset.'
                   if any(r['overage'] == 'org_level_disabled' for r in all_rejects) else '',
    }


def use_skill(uses, sid, skill, ts):
    """Count one use of skill in uses ({id: {count, last}}). An id outside SKILL_ID is dropped with a warning;
    a use without a readable time is counted but leaves last as it was."""
    if not isinstance(skill, str) or not SKILL_ID.match(skill):
        warn('session %s: skill id %r dropped' % (sid, str(skill)[:80]))
        return
    u = uses.setdefault(skill, {'count': 0})
    u['count'] += 1
    if ts and (not u.get('last') or epoch(ts) > epoch(u['last'])):
        u['last'] = ts


def parse_session(base, sid, main_path, st, now):
    """The session's document and agent rows as read from its transcripts. Nothing taken from the config
    except the running window is applied here, so the result can be cached against the transcripts alone.
    skipped lists the agents whose files could not be read this time."""
    title = ai_title = cwd = first = start = last = None
    by, rejects = {}, []
    launched, stopped, notes, sync = {}, {}, {}, {}
    uses, skill_calls = {}, set()
    for raw, o in records(main_path):
        ts, t = stamp(o), o.get('type')
        if ts:
            start = min(start, ts) if start else ts
            last = max(last, ts) if last else ts
        if t == 'custom-title' and o.get('customTitle'):
            title = o['customTitle']
        elif t == 'ai-title' and o.get('aiTitle'):
            ai_title = o['aiTitle']
        cwd = cwd or (o.get('cwd') if isinstance(o.get('cwd'), str) else None)
        m = o.get('message') if isinstance(o.get('message'), dict) else {}
        if t == 'user' and first is None and isinstance(m.get('content'), str) and not m['content'].lstrip().startswith('<'):
            first = ' '.join(m['content'].split())
        # A typed command; Claude Code writes an isMeta copy of some commands, which would count them twice.
        if t == 'user' and o.get('isMeta') is not True and isinstance(m.get('content'), str) \
                and m['content'].startswith(('<command-message>', '<command-name>')):
            name = tag(m['content'], 'command-name').strip()
            if ':' in name:  # only plugin commands; a bare one such as /loop is not a catalogue skill
                use_skill(uses, sid, name[1:] if name.startswith('/') else name, ts)
        reject(rejects, o)
        response(by, o)
        if t == 'assistant':
            for c in m.get('content') or []:
                if not isinstance(c, dict) or c.get('type') != 'tool_use':
                    continue
                if c.get('name') in ('Agent', 'Task'):
                    launched[c.get('id')] = ts
                elif c.get('name') == 'TaskStop':
                    stopped[(c.get('input') if isinstance(c.get('input'), dict) else {}).get('task_id')] = ts
                elif c.get('name') == 'Skill' and (c.get('id') is None or c.get('id') not in skill_calls):
                    skill_calls.add(c.get('id'))  # a streamed response can repeat its blocks
                    use_skill(uses, sid, (c.get('input') if isinstance(c.get('input'), dict) else {}).get('skill'), ts)
        if t == 'user' and isinstance(m.get('content'), list):
            tur = o.get('toolUseResult')
            for c in m['content']:
                if isinstance(c, dict) and c.get('type') == 'tool_result' and isinstance(tur, dict) and tur.get('status') == 'completed':
                    # A foreground agent returns its result inline rather than by notification.
                    sync[c.get('tool_use_id')] = {'at': ts, 'status': 'completed', 'result': text_of(c.get('content')),
                                                  'tokens': tur.get('totalTokens'), 'ms': tur.get('totalDurationMs')}
        if '<task-notification>' in raw:
            for s in strings(o):
                for block in re.findall(r'<task-notification>.*?</task-notification>', s, re.S):
                    tid = tag(block, 'task-id').strip()
                    if tid:  # an agent may notify more than once; the latest wins
                        notes[tid] = {'at': ts, 'status': tag(block, 'status').strip(), 'result': tag(block, 'result'),
                                      'tokens': tag(block, 'subagent_tokens'), 'ms': tag(block, 'duration_ms')}
    main = {'resps': list(by.values()), 'rejects': rejects}
    if not main['resps']:
        return None  # nothing was ever answered in this session

    subs, rows, skipped = [], [], []
    for path in sorted(glob.glob(os.path.join(base, sid, 'subagents', 'agent-*.jsonl'))):
        aid = os.path.basename(path)[len('agent-'):-len('.jsonl')]
        try:
            age = now - os.path.getmtime(path)
            meta = load_meta(path[:-len('.jsonl')] + '.meta.json')
            s = read_subagent(path)
            tuid = meta.get('toolUseId') if isinstance(meta.get('toolUseId'), str) else None
            s.update(id=aid, agentType=str(meta.get('agentType') or ''), description=str(meta.get('description') or aid))

            short = s['agentType'].split(':')[-1]
            lane = LANE.get(short, 'other')
            begin = launched.get(tuid) or s['first']
            fin = notes.get(aid) or sync.get(tuid)
            end = (fin or {}).get('at') or s['last'] or begin
            kind, verdict, minutes = classify(lane, fin, stopped.get(aid), s['text'], begin, end, age, st['window'])
            label = re.sub(r'\s+under TDD$', '', s['description'])
            row = {'id': aid, 'start': begin, 'end': end, 'lane': lane, 'label': label, 'kind': kind, 'verdict': verdict,
                   'tok': num((fin or {}).get('tokens')) or s['ctx'], 'min': minutes, 'pbis': pbis(label),
                   'fix': lane in BUILD_LANES and bool(FIX.search(label)), 'agentType': s['agentType']}
            if lane == 'other':
                row['agent'] = short or 'agent'
        except Exception as e:  # one unreadable agent file must not hide the rest of the session
            warn('session %s: agent %s skipped (%s: %s)' % (sid, aid, type(e).__name__, e))
            skipped.append(aid)
            continue
        subs.append(s)
        rows.append(row)
        if s['last']:
            last = max(last, s['last']) if last else s['last']

    first = redact(first)[:200] if first else ''
    doc = {'title': title or ai_title, 'cwd': cwd or '', 'folder': os.path.basename((cwd or '').rstrip('\\/')),
           'firstPrompt': first, 'start': start, 'last': last, 'usage': usage_doc(main, subs, (start, last)),
           'skillUses': uses}
    return {'doc': doc, 'rows': rows, 'skipped': skipped}


def session_doc(result, sid, st, runs, running):
    """The published session document: the cached parse plus everything the config decides."""
    doc = dict(result['doc'])
    first = doc.pop('firstPrompt', '')
    if not st['show_first_prompt']:
        first = ''  # the title fallback must not leak the prompt either
    doc['title'] = doc.get('title') or (first[:60] if first else sid[:8])
    if first:
        doc['firstPrompt'] = first
    doc.update(build=sid in st['legacy_build'], project=st['project_of'].get(sid), windowDays=st['days'],
               windowMinutes=st['window_minutes'], runs=runs, running=running)
    return doc


def aggregate_usage(usages):
    """One usage block for several sessions, in usage_doc()'s shape: totals, byModel and groups summed,
    hourly merged by hour (gaps filled, the last HOURS hours kept), subagents concatenated. Usage limits are
    account-wide, so limits that share a resetsAt are one limit: they become one entry with the earliest
    firstAt and the refused counts summed. Limits without a resetsAt stay separate. Limits are listed in time
    order. None when no session has usage."""
    usages = [u for u in usages if u]
    if not usages:
        return None
    totals, models, groups, hourly = {}, {}, {}, {}
    for u in usages:
        for k, v in (u.get('totals') or {}).items():
            totals[k] = totals.get(k, 0) + v
        for m in u.get('byModel') or []:
            mm = models.setdefault(m['model'], {'model': m['model'], 'label': m.get('label')})
            for k, v in m.items():
                if k not in ('model', 'label'):
                    mm[k] = mm.get(k, 0) + v
        for g in u.get('groups') or []:
            gg = groups.setdefault(g['key'], {'key': g['key'], 'label': g.get('label'), 'effective': 0})
            gg['effective'] += g.get('effective') or 0
        for h in u.get('hourly') or []:
            b = hourly.setdefault(h['hour'], {'main': 0, 'sub': 0})
            b['main'] += h.get('main') or 0
            b['sub'] += h.get('sub') or 0
    # The chart places bars by position, so hours with no activity between sessions are kept as zeros.
    series = []
    if hourly:
        end = datetime.fromisoformat(max(hourly) + ':00:00+00:00')
        t = max(datetime.fromisoformat(min(hourly) + ':00:00+00:00'), end - timedelta(hours=HOURS - 1))
        while t <= end:
            k = t.strftime('%Y-%m-%dT%H')
            series.append(dict({'hour': k}, **hourly.get(k, {'main': 0, 'sub': 0})))
            t += timedelta(hours=1)
    firsts = [u['span']['first'] for u in usages if (u.get('span') or {}).get('first')]
    lasts = [u['span']['last'] for u in usages if (u.get('span') or {}).get('last')]
    agents = [a for u in usages for a in u.get('subagents') or []]
    limits, by_reset = [], {}
    for l in (l for u in usages for l in u.get('limits') or []):
        key = l.get('resetsAt')
        if key is None or key not in by_reset:
            limits.append(dict(l))
            if key is not None:
                by_reset[key] = limits[-1]
            continue
        m = by_reset[key]
        m['refused'] = (m.get('refused') or 0) + (l.get('refused') or 0)
        if l.get('firstAt') and (not m.get('firstAt') or l['firstAt'] < m['firstAt']):
            m['firstAt'] = l['firstAt']
    order = list(GROUP_LABEL)
    return {
        'source': 'Claude Code transcripts for %d session%s and %d agent run%s, on this computer' % (
            len(usages), '' if len(usages) == 1 else 's', len(agents), '' if len(agents) == 1 else 's'),
        'weights': usages[0].get('weights'),
        'span': {'first': min(firsts) if firsts else None, 'last': max(lasts) if lasts else None},
        'totals': totals,
        'byModel': sorted(models.values(), key=lambda m: -(m.get('effective') or 0)),
        'groups': sorted(groups.values(), key=lambda g: order.index(g['key']) if g['key'] in order else len(order)),
        'subagents': agents, 'hourly': series,
        'limits': sorted(limits, key=lambda l: l.get('firstAt') or ''),
        'overage': next((u['overage'] for u in usages if u.get('overage')), ''),
    }


def link(rows):
    """Hand-offs (from), findings fed back (feeds) and parallel batches (group), inferred from order and PBI ids."""
    def before(r, pred):
        c = [x for x in rows if x is not r and x['end'] and r['start'] and x['end'] <= r['start'] and pred(x)]
        return max(c, key=lambda x: x['end']) if c else None

    for r in rows:
        shares = lambda x: bool(set(r['pbis']) & set(x['pbis']))
        if r['lane'] in ('cw', 'tw') and r['fix']:
            review = lambda x: x['lane'] in REVIEW_LANES and x['kind'] in ('go', 'changes', 'nogo')
            src = before(r, lambda x: review(x) and shares(x)) or (None if r['pbis'] else before(r, review))
            if src:
                r['feeds'] = src['id']
        elif r['lane'] in ('cw', 'tw') and r['pbis']:
            src = before(r, lambda x: x['lane'] == 'plan' and x['kind'] == 'go' and shares(x))
            if src:
                r['from'] = src['id']
        elif r['lane'] == 'cr':
            # Only a finished build hands off to review; a NOT-DONE build is kind "changes".
            built = lambda x: x['lane'] in ('cw', 'tw') and x['kind'] == 'done'
            src = before(r, lambda x: built(x) and shares(x)) if r['pbis'] else before(r, built)
            if src:
                r['from'] = src['id']
        elif r['lane'] == 'plan':
            same_chain = lambda x: x['lane'] == 'plan' and (shares(x) if r['pbis'] else not x['pbis'])
            src = before(r, same_chain) or before(r, lambda x: x['lane'] == 'orch')
            if src:
                r['from'] = src['id']

    # Parallel batch: new work (not fixes) in one lane launched within two minutes of the previous launch.
    batch, n = [], 0
    for r in [x for x in rows if x['lane'] in ('cw', 'tw') and not x['fix'] and x['start']] + [None]:
        if r and batch and r['lane'] == batch[-1]['lane'] and epoch(r['start']) - epoch(batch[-1]['start']) <= 120:
            batch.append(r)
            continue
        if len(batch) > 1:
            n += 1
            for x in batch:
                x['group'] = chr(64 + n)
        batch = [r] if r else []


def signature(base, sid, main_path, st):
    """What a cached parse depends on: parser version, running window, and each transcript file's mtime and
    size. Raises FileNotFoundError if the main transcript has gone; agent files that vanish are left out."""
    entries = [[os.path.basename(main_path), os.path.getmtime(main_path), os.path.getsize(main_path)]]
    for f in glob.glob(os.path.join(base, sid, 'subagents', '*')):
        try:
            entries.append([os.path.basename(f), os.path.getmtime(f), os.path.getsize(f)])
        except FileNotFoundError:
            continue  # removed since the folder was listed
    return [PARSER_VERSION, st['window']] + sorted(entries)


def write_json(path, obj, indent=1):
    """Write through a temp file in the same folder, then swap it in, so a failed write never leaves a
    truncated file for the next run to read."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.' + os.path.basename(path) + '.', suffix='.tmp')
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.remove(tmp)
        raise


def main(config=None, out_dir=None, projects_root=None, now=None):
    """Export into out_dir (default out/); returns the process exit code."""
    if config is None:
        with io.open(CONFIG, encoding='utf-8') as f:
            config = json.load(f)
    try:
        st = settings(config, projects_root)
    except ValueError as e:  # an unusable project list, or a config value of the wrong type
        print('export_sessions: %s; nothing exported' % e, file=sys.stderr)
        return 2
    out = out_dir or os.path.join(HERE, 'out')
    cache_path = os.path.join(out, '.cache', 'sessions.json')
    t0 = time.time() if now is None else now

    # An empty discovery would replace the board with nothing, so a missing root or build transcript is fatal.
    if not os.path.isdir(st['root']):
        print('export_sessions: sessions.projectsRoot %s does not exist; nothing exported' % st['root'], file=sys.stderr)
        return 2
    mains = glob.glob(os.path.join(st['root'], '*', '*.jsonl'))
    found = {os.path.basename(p)[:-len('.jsonl')] for p in mains}
    missing = sorted(st['build'] - found)
    if missing:
        print('export_sessions: no transcript under %s for project session(s) %s; nothing exported' % (st['root'], ', '.join(missing)), file=sys.stderr)
        return 2

    try:
        with io.open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    cache = cache if isinstance(cache, dict) else {}
    fresh, parsed, results = {}, 0, {}
    for main_path in mains:
        base, sid = os.path.dirname(main_path), os.path.basename(main_path)[:-len('.jsonl')]
        try:
            if sid not in st['build'] and t0 - os.path.getmtime(main_path) > st['days'] * 86400:
                continue
            if st['exclude'] and excluded(st['exclude'], os.path.basename(base), cwd_of(main_path)):
                continue
            sig = signature(base, sid, main_path, st)
        except OSError as e:
            if not isinstance(e, FileNotFoundError):  # a transcript deleted mid-run is not worth a warning
                warn('session %s skipped (%s: %s)' % (sid, type(e).__name__, e))
            continue
        hit = cache.get(sid) if isinstance(cache.get(sid), dict) else None
        cached = (hit or {}).get('result') or {}
        stale = False
        # A result that skipped an unreadable agent is never reused: a finished agent's file does not change
        # again, so a signature match would keep that agent missing for good.
        if hit and hit.get('sig') == sig and not cached.get('skipped') and not any(r['kind'] == 'running' for r in cached.get('rows', [])):
            fresh[sid] = hit
        else:
            try:
                result = parse_session(base, sid, main_path, st, t0)
                if result and result['skipped']:
                    # Until it reads again, a skipped agent keeps its last row, so refresh.py does not delete its run.
                    result['rows'] += [carried(r, st['window'], t0) for r in cached.get('rows', []) if r['id'] in result['skipped']]
                fresh[sid] = {'sig': sig, 'result': result}
                parsed += 1
            except Exception as e:  # one unreadable session must not stop the export
                warn('session %s could not be read (%s: %s); %s' % (
                    sid, type(e).__name__, e, 'keeping its last export' if hit else 'left out'))
                if not hit:
                    continue
                fresh[sid] = hit  # keeps the old signature, so the session is re-read next run
                stale = True
        result = fresh[sid]['result']
        if stale and result:
            # Nothing re-read the session's agents either, so the export gets a copy whose running rows are judged
            # as carried() judges an agent that could not be read. The cache keeps the rows as they were read.
            result = dict(result, rows=[carried(r, st['window'], t0) for r in result.get('rows', [])])
        # A transcript can be touched without new activity, so the window is judged on the last timestamp.
        if result and (sid in st['build'] or (result['doc'].get('last') and t0 - epoch(result['doc']['last']) <= st['days'] * 86400)):
            results[sid] = result
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    write_json(cache_path, fresh, indent=None)

    rows = sorted((dict(r, session=sid) for sid, res in results.items() for r in res['rows']), key=lambda r: r['start'] or '')
    for m in st['manual']:
        anchor = next((i for i, r in enumerate(rows) if r['id'] == m.get('after')), None)
        if anchor is None:
            continue  # its session is outside the window
        a = rows[anchor]
        row = {'id': m['id'], 'session': a['session'], 'start': a['end'], 'end': a['end'], 'lane': m.get('lane', 'orch'),
               'label': m['label'], 'kind': m.get('kind', 'done'), 'verdict': m.get('verdict', ''), 'tok': 0, 'min': 0, 'pbis': [], 'fix': False}
        if m.get('from'):
            row['from'] = m['from']
        rows.insert(anchor + 1, row)

    for d in ('sessions', 'runs', 'projects'):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True)
        os.makedirs(os.path.join(out, d))
    running, counts = {}, {}
    for sid in results:
        mine = [r for r in rows if r['session'] == sid]
        link(mine)
        for i, r in enumerate(mine, 1):
            doc = {k: r[k] for k in ('session', 'lane', 'label', 'kind', 'verdict', 'tok', 'min')}
            doc['seq'] = i
            doc['project'] = st['project_of'].get(sid)
            for k in ('from', 'feeds', 'group', 'agent'):
                if r.get(k):
                    doc[k] = r[k]
            if 'agentType' in r:  # a subagent's row: runs.manual rows record neither an agent type nor a launch
                for k in ('agentType', 'start'):
                    if r.get(k):
                        doc[k] = r[k]
            write_json(os.path.join(out, 'runs', r['id'] + '.json'), doc)
        running[sid], counts[sid] = sum(r['kind'] == 'running' for r in mine), len(mine)
        write_json(os.path.join(out, 'sessions', sid + '.json'), session_doc(results[sid], sid, st, len(mine), running[sid]))
    for order, p in enumerate(st['projects']):
        linked = [sid for sid in p['sessions'] if sid in results and st['project_of'][sid] == p['id']]
        lasts = [results[sid]['doc']['last'] for sid in linked if results[sid]['doc'].get('last')]
        write_json(os.path.join(out, 'projects', p['id'] + '.json'), {
            'name': p['name'], 'repoPath': p['repoPath'], 'branch': p['branch'], 'sessions': linked,
            'statusDoc': p['statusDoc'], 'order': order, 'runs': sum(counts[sid] for sid in linked),
            'running': sum(running[sid] for sid in linked), 'last': max(lasts) if lasts else None,
            'usage': aggregate_usage([results[sid]['doc'].get('usage') for sid in linked])})
    legacy = os.path.join(out, 'usage.json')  # replaced by the usage block in each session document
    if os.path.exists(legacy):
        os.remove(legacy)
    print('wrote %d sessions (%d re-read), %d runs (%d running) and %d projects | %.1fs' % (
        len(results), parsed, len(rows), sum(running.values()), len(st['projects']), time.time() - t0))
    return 0


if __name__ == '__main__':
    sys.exit(main(out_dir=sys.argv[1] if len(sys.argv) > 1 else None))
