"""Parsing and derivation shared by the exporters and anything else that builds the board's records.

    import derive   # with exporters/ on sys.path

Nothing here reads a file, the config, git or the network, prints, or exits: callers pass parsed data
(transcript records as dicts, file text as strings) and get records back. So a reader that follows a
transcript as it grows can feed records one at a time (new_session / add_record, new_agent / add_agent) and
derive exactly what export_sessions.py writes. Where a derivation drops something it would warn about, it
calls the warn callable it was given with the message (nothing when none was given).

Sessions and runs (export_sessions.py): transcript record parsing, token and usage arithmetic, lane, verdict
and kind classification, run linking, redaction, usage aggregation and skill-use counting.
Project tabs (export_board.py): spec sections, tables, bullets, the Later list and build state.
Catalogue (export_catalogue.py): frontmatter and a plugin's one-line purpose.
"""
import fnmatch, json, math, os, posixpath, re  # os only for os.path's name handling, never to touch a file
from datetime import datetime, timezone, timedelta

HOURS = 168  # hourly usage series covers the last week of a session's activity
# Skill ids become keys in session documents and are matched against catalogue ids, so they are kept to a safe set.
SKILL_ID = re.compile(r'^[A-Za-z0-9_.:-]{1,100}$')
# The tools that write a file, and the input key each names its path in. A tool that only reads is not an edit.
EDIT_TOOLS = {'Edit': 'file_path', 'Write': 'file_path', 'MultiEdit': 'file_path', 'NotebookEdit': 'notebook_path'}
ABSOLUTE = re.compile(r'^(?:[A-Za-z]:/|/)')
# A home-relative ("~/…") or drive-relative ("C:foo", no slash after the drive letter) path: the repository
# test below cannot place either against a normalised root, so both are withheld like a path outside it.
UNPLACEABLE = re.compile(r'^~(?:/|$)|^[A-Za-z]:(?!/)')

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
# A review-lane run's structured findings: the LAST fenced code block at the very end of its result. Split in
# two so findings_of() can try each fence in turn and keep the rightmost match: FENCE_START finds every fence
# opening, FENCE_JSON (matched from just after one, with re.Pattern.match's pos) requires the greedy body --
# greedy so a finding's own nested braces stay inside the capture -- to reach the final closing fence and the
# end of the text. An earlier fence's opening also satisfies this (its greedy body can swallow everything up to
# the real block), so trying every opening left to right and keeping the last success lands on the real one.
FENCE_START = re.compile(r'```(?:json)?\s*')
FENCE_JSON = re.compile(r'(\{[\s\S]*\})\s*```\s*\Z')
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
TOKEN_FIELDS = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')


def is_number(v):
    """A usable JSON number: an int or a finite float, never a bool (JSON true reads as a Python int)."""
    return not isinstance(v, bool) and (isinstance(v, int) or (isinstance(v, float) and math.isfinite(v)))


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


def parse_line(line):
    """The JSON object a transcript line holds, or None for anything else."""
    try:
        o = json.loads(line)
    except (ValueError, RecursionError):  # RecursionError: nested deeper than the parser can follow
        return None
    return o if isinstance(o, dict) else None


def record_pairs(lines):
    """(raw line, parsed record) pairs for every line holding a JSON object; anything else is skipped."""
    for line in lines:
        o = parse_line(line)
        if o is not None:
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


def response(by, o):
    """Record one assistant response, deduplicated by message id (streamed responses span several lines)."""
    m = o.get('message')
    if o.get('type') != 'assistant' or not isinstance(m, dict) or not isinstance(m.get('usage'), dict) or not m['usage'] \
            or m.get('model') == '<synthetic>':
        return
    # A count that is not a number would break every sum over the session, so the record is skipped instead.
    if not all(m['usage'].get(k) is None or is_number(m['usage'][k]) for k in TOKEN_FIELDS):
        return
    r = by.setdefault(m.get('id') or o.get('uuid'),
                      {'model': m.get('model'), 'ts': stamp(o), 'tools': [], 'files': [], 'usage': None})
    r['usage'] = m['usage']
    for c in m.get('content') or []:
        if isinstance(c, dict) and c.get('type') == 'tool_use':
            r['tools'].append(c.get('name', ''))
            key = EDIT_TOOLS.get(c.get('name'))
            path = (c.get('input') if isinstance(c.get('input'), dict) else {}).get(key) if key else None
            if isinstance(path, str) and path.strip():
                # Kept with the call's own id, not yet known to have written anything: a later tool_result may
                # mark the id failed, and agent_summary() drops it then, rather than trusting the call alone.
                r['files'].append((c.get('id'), path.strip()))


def failed_edit(failed, o):
    """Note the tool_use id of a tool call whose result came back an error, so a refused or failed edit is not
    published as one the run made."""
    m = o.get('message')
    if o.get('type') != 'user' or not isinstance(m, dict):
        return
    for c in m.get('content') or []:
        if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('is_error') and c.get('tool_use_id'):
            failed.add(c['tool_use_id'])


def reject(rejects, o):
    if o.get('apiErrorStatus') == 429 or 'quotaLimits' in o:
        q = o.get('quotaLimits') if isinstance(o.get('quotaLimits'), dict) else {}
        rejects.append({'at': stamp(o), 'resetsAt': q.get('resetsAt'), 'type': q.get('rateLimitType'),
                        'overage': q.get('overageDisabledReason')})


def excluded(patterns, folder, cwd):
    names = [folder] + ([cwd, cwd.replace('\\', '/')] if cwd else [])
    return any(fnmatch.fnmatch(n, p) for p in patterns for n in names)


def new_agent():
    """The running state of one agent's own transcript, fed record by record with add_agent()."""
    return {'by': {}, 'rejects': [], 'first': None, 'last': None, 'text': '', 'failed': set()}


def add_agent(state, o):
    if stamp(o):
        state['first'] = state['first'] or o['timestamp']
        state['last'] = o['timestamp']
    reject(state['rejects'], o)
    response(state['by'], o)
    failed_edit(state['failed'], o)
    if o.get('type') == 'assistant':
        t = text_of((o.get('message') or {}).get('content'))
        if t.strip():
            state['text'] = t


def agent_summary(state):
    """An agent transcript's responses, refusals, first and last times, last reply and final context size. It is a
    copy, so records fed after it leave it as it is (a streamed response keeps adding tools to its entry in state).
    A response's files drop any edit call whose id ended up in state['failed'], so a refused or failed Edit,
    Write, MultiEdit or NotebookEdit is not published as a file the run touched."""
    resps = [dict(r, tools=list(r['tools']), files=[p for tid, p in r['files'] if tid not in state['failed']])
             for r in state['by'].values()]
    last = resps[-1]['usage'] if resps else {}
    ctx = sum(last.get(k) or 0 for k in TOKEN_FIELDS)
    return {'resps': resps, 'rejects': list(state['rejects']), 'first': state['first'], 'last': state['last'],
            'text': state['text'], 'ctx': ctx}


def read_agent(records):
    """agent_summary() of an agent transcript given as parsed records."""
    state = new_agent()
    for o in records:
        add_agent(state, o)
    return agent_summary(state)


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


def use_skill(uses, sid, skill, ts, warn=None):
    """Count one use of skill in uses ({id: {count, last}}). An id outside SKILL_ID is dropped with a warning;
    a use without a readable time is counted but leaves last as it was."""
    if not isinstance(skill, str) or not SKILL_ID.match(skill):
        if warn:
            warn('session %s: skill id %r dropped' % (sid, str(skill)[:80]))
        return
    u = uses.setdefault(skill, {'count': 0})
    u['count'] += 1
    if ts and (not u.get('last') or epoch(ts) > epoch(u['last'])):
        u['last'] = ts


def new_session(sid):
    """The running state of a session's main transcript, fed record by record with add_record()."""
    return {'sid': sid, 'title': None, 'aiTitle': None, 'cwd': None, 'first': None, 'start': None, 'last': None,
            'by': {}, 'rejects': [], 'launched': {}, 'stopped': {}, 'notes': {}, 'sync': {}, 'uses': {}, 'skillCalls': set()}


def add_record(state, o, raw=None, warn=None):
    """Fold one main-transcript record into state. raw, the line it was parsed from, lets a line without a
    task notification skip the search for one; without it the record's strings are searched."""
    ts, t = stamp(o), o.get('type')
    if ts:
        state['start'] = min(state['start'], ts) if state['start'] else ts
        state['last'] = max(state['last'], ts) if state['last'] else ts
    if t == 'custom-title' and o.get('customTitle'):
        state['title'] = o['customTitle']
    elif t == 'ai-title' and o.get('aiTitle'):
        state['aiTitle'] = o['aiTitle']
    state['cwd'] = state['cwd'] or (o.get('cwd') if isinstance(o.get('cwd'), str) else None)
    m = o.get('message') if isinstance(o.get('message'), dict) else {}
    if t == 'user' and state['first'] is None and isinstance(m.get('content'), str) and not m['content'].lstrip().startswith('<'):
        state['first'] = ' '.join(m['content'].split())
    # A typed command; Claude Code writes an isMeta copy of some commands, which would count them twice.
    if t == 'user' and o.get('isMeta') is not True and isinstance(m.get('content'), str) \
            and m['content'].startswith(('<command-message>', '<command-name>')):
        name = tag(m['content'], 'command-name').strip()
        if ':' in name:  # only plugin commands; a bare one such as /loop is not a catalogue skill
            use_skill(state['uses'], state['sid'], name[1:] if name.startswith('/') else name, ts, warn)
    reject(state['rejects'], o)
    response(state['by'], o)
    if t == 'assistant':
        for c in m.get('content') or []:
            if not isinstance(c, dict) or c.get('type') != 'tool_use':
                continue
            if c.get('name') in ('Agent', 'Task'):
                state['launched'][c.get('id')] = ts
            elif c.get('name') == 'TaskStop':
                state['stopped'][(c.get('input') if isinstance(c.get('input'), dict) else {}).get('task_id')] = ts
            elif c.get('name') == 'Skill' and (c.get('id') is None or c.get('id') not in state['skillCalls']):
                state['skillCalls'].add(c.get('id'))  # a streamed response can repeat its blocks
                use_skill(state['uses'], state['sid'], (c.get('input') if isinstance(c.get('input'), dict) else {}).get('skill'), ts, warn)
    if t == 'user' and isinstance(m.get('content'), list):
        tur = o.get('toolUseResult')
        for c in m['content']:
            if isinstance(c, dict) and c.get('type') == 'tool_result' and isinstance(tur, dict) and tur.get('status') == 'completed':
                # A foreground agent returns its result inline rather than by notification.
                state['sync'][c.get('tool_use_id')] = {'at': ts, 'status': 'completed', 'result': text_of(c.get('content')),
                                                       'tokens': tur.get('totalTokens'), 'ms': tur.get('totalDurationMs')}
    if ('<task-notification>' in raw) if raw is not None else any('<task-notification>' in s for s in strings(o)):
        for s in strings(o):
            for block in re.findall(r'<task-notification>.*?</task-notification>', s, re.S):
                tid = tag(block, 'task-id').strip()
                if tid:  # an agent may notify more than once; the latest wins
                    state['notes'][tid] = {'at': ts, 'status': tag(block, 'status').strip(), 'result': tag(block, 'result'),
                                           'tokens': tag(block, 'subagent_tokens'), 'ms': tag(block, 'duration_ms')}


def edited(resps):
    """The files the responses wrote, first write first and each named once. A streamed response is recorded
    again as it grows, so the same path arrives several times and only the first occurrence is kept."""
    out = []
    for r in resps:
        for path in r.get('files') or []:
            if path not in out:
                out.append(path)
    return out


def agent_row(state, aid, meta, sub, age, window):
    """The run row for agent aid: meta is its meta.json object, sub its agent_summary(), age seconds since its
    transcript was written. sub gains the agent's id, agentType and description, as usage_doc() reads them."""
    tuid = meta.get('toolUseId') if isinstance(meta.get('toolUseId'), str) else None
    sub.update(id=aid, agentType=str(meta.get('agentType') or ''), description=str(meta.get('description') or aid))

    short = sub['agentType'].split(':')[-1]
    lane = LANE.get(short, 'other')
    begin = state['launched'].get(tuid) or sub['first']
    fin = state['notes'].get(aid) or state['sync'].get(tuid)
    end = (fin or {}).get('at') or sub['last'] or begin
    kind, verdict, minutes = classify(lane, fin, state['stopped'].get(aid), sub['text'], begin, end, age, window)
    label = re.sub(r'\s+under TDD$', '', sub['description'])
    row = {'id': aid, 'start': begin, 'end': end, 'lane': lane, 'label': label, 'kind': kind, 'verdict': verdict,
           'tok': num((fin or {}).get('tokens')) or sub['ctx'], 'min': minutes, 'pbis': pbis(label),
           'fix': lane in BUILD_LANES and bool(FIX.search(label)), 'agentType': sub['agentType'],
           'files': edited(sub['resps'])}
    if lane == 'other':
        row['agent'] = short or 'agent'
    if lane == 'cr':
        # found is None when the result carried no parseable findings block; hasFindingsBlock lets findings_doc()
        # and run_doc() tell that apart from a round that reported an empty findings list. hasFindingsBlock itself
        # stays off the run document: run_doc() copies an explicit key list, and an absent findings key says the same.
        found = findings_of((fin or {}).get('result') or '')
        row['findings'] = found or []
        row['hasFindingsBlock'] = found is not None
    return row


def session_result(state, subs, rows, skipped):
    """A session's parse: its document before the config is applied, its agent rows and the agents skipped.
    subs are the agent_row()-updated summaries of the agents that were read, in the order of rows. The document
    is a copy, so records fed to state after it leave it as it is."""
    last = state['last']
    for s in subs:
        if s['last']:
            last = max(last, s['last']) if last else s['last']
    first = redact(state['first'])[:200] if state['first'] else ''
    cwd = state['cwd']
    main = {'resps': list(state['by'].values()), 'rejects': state['rejects']}
    doc = {'title': state['title'] or state['aiTitle'], 'cwd': cwd or '', 'folder': os.path.basename((cwd or '').rstrip('\\/')),
           'firstPrompt': first, 'start': state['start'], 'last': last, 'usage': usage_doc(main, subs, (state['start'], last)),
           'skillUses': {k: dict(v) for k, v in state['uses'].items()}}
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


def findings_of(text):
    """The structured findings a review-lane run's result ends with: the last fenced code block, when it
    parses as an object holding a "findings" list (the catalog's code-reviewer schema). Each finding's id,
    severity, title, file:line (its subject's id) and remediation are kept, coerced to strings.
    None -- not an error -- when the result carries no such block: no fence at the end, one that fails to
    parse, or an object without a findings list. A list, possibly empty, when a block was found: the round
    itself reported no findings, which is a real state (nothing open) rather than an unreadable one."""
    m = None
    for start in FENCE_START.finditer(text):
        cand = FENCE_JSON.match(text, start.end())
        if cand:
            m = cand  # keep the rightmost fence whose body reaches the end of the text
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except (ValueError, RecursionError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get('findings'), list):
        return None
    out = []
    for f in data['findings']:
        if not isinstance(f, dict):
            continue
        fid = str(f.get('id', ''))
        if not fid:
            continue  # every id-less finding would coerce to "" and collapse into one entry in findings_doc()
        subject = f.get('subject') if isinstance(f.get('subject'), dict) else {}
        out.append({'id': fid, 'severity': str(f.get('severity', '')),
                    'title': str(f.get('title', '')), 'location': str(subject.get('id', '')),
                    'remediation': str(f.get('remediation', ''))})
    return out


def findings_doc(rows):
    """The findings ledger for one project's runs: {PBI id: {open, resolved, rounds, roundsToGo?}}. rows are
    that project's runs in read order (chronological); only a finished cr-lane run (kind go/changes/nogo)
    with a PBI id is a code-review round -- a run still running or cut off before finishing has not produced
    one yet, and a round whose result carried no parseable findings block (hasFindingsBlock False: this
    repo's own reviewers routinely write findings to a file and reply in prose) still counts as a round but
    is never authoritative for what is open, so it cannot wrongly resolve findings it could not read. A
    finding present in the most recently read round that DID carry a block is open; one seen only in an
    earlier round is resolved, so a round that lists a previous round's finding again keeps it open. Each
    finding also carries round (1-based, first seen) and lastSeen (1-based, most recently seen), so the page
    can show its age. roundsToGo is the round, 1-based, that first reached GO; left out while none has."""
    rounds = {}
    for r in rows:
        if r.get('lane') != 'cr' or r.get('kind') not in ('go', 'changes', 'nogo') or not r.get('pbis'):
            continue
        for code in r['pbis']:
            rounds.setdefault('PBI-' + code, []).append(r)
    items = {}
    for pbi, runs in rounds.items():
        with_block = [r for r in runs if r.get('hasFindingsBlock')]
        latest_ids = {f['id'] for f in with_block[-1]['findings']} if with_block else set()
        seen, first_round, last_round = {}, {}, {}
        for i, r in enumerate(runs, 1):
            for f in r.get('findings') or []:
                seen[f['id']] = f  # a finding's most recently read text wins if it recurs
                first_round.setdefault(f['id'], i)
                last_round[f['id']] = i
        with_round = lambda f: dict(f, round=first_round[f['id']], lastSeen=last_round[f['id']])
        item = {'open': sorted((with_round(f) for fid, f in seen.items() if fid in latest_ids), key=lambda f: f['id']),
                'resolved': sorted((with_round(f) for fid, f in seen.items() if fid not in latest_ids), key=lambda f: f['id']),
                'rounds': len(runs)}
        go_at = next((i + 1 for i, r in enumerate(runs) if r.get('kind') == 'go'), None)
        if go_at is not None:
            item['roundsToGo'] = go_at
        items[pbi] = item
    return items


def place_manual(rows, manual):
    """Insert each runs.manual row straight after its "after" run in rows (sorted by start, each with its session).
    A row whose anchor is not in rows is left out: its session is outside the window."""
    for m in manual:
        anchor = next((i for i, r in enumerate(rows) if r['id'] == m.get('after')), None)
        if anchor is None:
            continue
        a = rows[anchor]
        row = {'id': m['id'], 'session': a['session'], 'start': a['end'], 'end': a['end'], 'lane': m.get('lane', 'orch'),
               'label': m['label'], 'kind': m.get('kind', 'done'), 'verdict': m.get('verdict', ''), 'tok': 0, 'min': 0, 'pbis': [], 'fix': False}
        if m.get('from'):
            row['from'] = m['from']
        rows.insert(anchor + 1, row)


def publishable_files(paths, repo):
    """The paths a run edited, in the form the board may publish, given the project's repository root (or None).

    An absolute path under the repository is published relative to it, so the board says which file was touched
    without publishing where the repository sits on this machine. A path outside it is published as "…/" and its
    file name, its folders withheld: which file was touched is the fact the board is after, the folders of a file
    outside the project are not the board's to publish, and the prefix stops it reading as a file at the
    repository's root. A git worktree of the repository is outside it too, since nothing in a transcript ties
    the two. A relative path the agent wrote is published as written unless it climbs out with "..". A
    home-relative ("~/…") or drive-relative ("C:foo") path is withheld the same way: the Edit and Write tools
    refuse both, but nothing here should trust that upstream refusal to publish one that reached this far as
    written, folders included. Parent steps are resolved before the repository test, so "<repo>/../elsewhere"
    is outside. The repository root itself is not a file. Order is kept, each file named once.
    """
    root = posixpath.normpath(str(repo).replace('\\', '/')).rstrip('/') if repo else ''
    out = []
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            continue
        p = posixpath.normpath(path.strip().replace('\\', '/'))
        if root and (p + '/').lower().startswith(root.lower() + '/'):
            name = p[len(root):].lstrip('/')
        elif ABSOLUTE.match(p) or p == '..' or p.startswith('../') or UNPLACEABLE.match(p):
            name = '…/' + p.rsplit('/', 1)[-1]
        else:
            name = p
        if name and name not in out:
            out.append(name)
    return out


def run_doc(r, seq, project, repo=None):
    """The published run document for row r, seq-th in its session, whose session belongs to project (or None).
    repo is that project's repoPath, which the files the run edited are published relative to; without one every
    absolute path is published as "…/" and its file name, as publishable_files() does for a path outside it.

    A review round also publishes its own findings, which the per-project ledger cannot stand in for: that ledger
    is keyed by work item, so it holds nothing for a review that named no PBI id and cannot say which round a
    finding was read from. An empty list means the round read a findings block and listed nothing; no findings
    key at all means nothing readable was reported, which is every run outside a finished review round.
    """
    doc = {k: r[k] for k in ('session', 'lane', 'label', 'kind', 'verdict', 'tok', 'min')}
    doc['seq'] = seq
    doc['project'] = project
    for k in ('from', 'feeds', 'group', 'agent'):
        if r.get(k):
            doc[k] = r[k]
    if 'agentType' in r:  # a subagent's row: runs.manual rows record neither an agent type nor a launch
        for k in ('agentType', 'start'):
            if r.get(k):
                doc[k] = r[k]
    if r.get('hasFindingsBlock'):
        doc['findings'] = r['findings']
    files = publishable_files(r.get('files') or [], repo)
    if files:
        doc['files'] = files
    return doc


def project_doc(p, order, results, counts, running, project_of):
    """The published project document: its linked sessions that were exported, their run counts, latest activity
    and combined usage. results, counts and running are keyed by session id."""
    linked = [sid for sid in p['sessions'] if sid in results and project_of[sid] == p['id']]
    lasts = [results[sid]['doc']['last'] for sid in linked if results[sid]['doc'].get('last')]
    return {'name': p['name'], 'repoPath': p['repoPath'], 'branch': p['branch'], 'sessions': linked,
            'statusDoc': p['statusDoc'], 'order': order, 'runs': sum(counts[sid] for sid in linked),
            'running': sum(running[sid] for sid in linked), 'last': max(lasts) if lasts else None,
            'usage': aggregate_usage([results[sid]['doc'].get('usage') for sid in linked])}


# --- project tabs ------------------------------------------------------------

STATES = ('done', 'conditions', 'partial', 'todo')
LATER = '### Future iterations (not planned)'
# A list item's marker, "-", "*", "+" or "1.", then a space or the end of the line: never "-text" or "**bold".
MARKER = re.compile(r'(?:[-*+]|\d{1,9}\.)(?: (.*))?$')
# A horizontal rule such as "---", "* * *" or "- - -", which would otherwise read as a list item.
RULE = re.compile(r' {0,3}([-*_])(?: *\1){2,} *$')


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


def build_state(data):
    """PBI id -> (state, review, open items, commit); state is one of STATES."""
    return {pbi: (e.get('state', 'todo'), e.get('review', '—'), e.get('open', ''), e.get('commit', ''))
            for pbi, e in (data.get('buildState') or {}).items()}


def not_worked_out(data):
    """The brief's "Things I haven't worked out": (item, spec ledger row, ADR id or None)."""
    return [(e.get('item', ''), e.get('row'), e.get('adr')) for e in data.get('notWorkedOut') or []]


def review_verdict(text):
    """The bold verdict a review note states after "**Verdict:**", or "—" when it states none."""
    m = re.search(r'\*\*Verdict:\*\*\s*\*\*([^*]+)\*\*', text)
    return m.group(1).strip() if m else '—'


def adr_entry(text, path):
    """An ADR's id, title, status and what it resolves, from its "key: value" lines, with its path."""
    fm = lambda k: (re.search(r'^%s:\s*(.+)$' % k, text, re.M) or [None, ''])[1].split('#')[0].strip()
    return {'id': fm('id'), 'title': fm('title'), 'status': fm('status'), 'resolves': fm('resolves'), 'path': path}


def spec_docs(pid, paths, spec, prd, brief, design, adrs, rounds, data, now):
    """The spec, assumptions, decisions and backlog tabs of project pid. paths is its docs block; spec, prd,
    brief and design are those files' text (prd None when it has none, brief and design '' when missing); adrs
    are adr_entry() dicts; rounds the review rounds found, [{gate, round, verdict}]; data its hand-kept data."""
    SPEC, PRD, BRIEF, ADRS = paths['spec'], paths.get('prd'), paths.get('brief'), (paths.get('adrDir') or '').rstrip('/')
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
    not_worked = []
    for item, n, adr in not_worked_out(data):
        r = by_n.get(n, {})
        not_worked.append({'item': item, 'row': n, 'adr': adr, 'landed': r.get('resolution', '—'),
                           'status': r.get('status', '—'), 'needsYou': r.get('needsYou', False)})

    # --- spec ------------------------------------------------------------
    goals = [{'id': 'G-' + g, 'text': clean(t)} for g, t in re.findall(r'^- \*\*G-(\d+)\*\* (.+)$', spec, re.M)]
    core = [clean(t) for t in re.findall(r'^\d+\. \*\*(.+?)\*\*', section(brief, "## Why this is not just a content site"), re.M)]
    approval = re.search(r'\*\*Human approval:\*\*\s*\n>\s*\*\*([^*]+)\*\*', spec)
    approved_by = re.search(r'\*\*Approved by:\*\*\s*(.+)', spec)

    # --- backlog ---------------------------------------------------------
    state_of, pbi_rows = build_state(data), []
    for c in table(section(spec, '### PBI list (proposed)')):
        if len(c) < 7 or not c[0].startswith('PBI-'):
            continue
        state, review, open_items, commit = state_of.get(c[0], ('todo', '—', '', ''))
        pbi_rows.append({'id': c[0], 'title': c[1], 'dependsOn': c[2], 'group': c[3], 'risk': c[4],
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
        'backlog': {'source': '%s (PBI list) + build state kept in projects/%s.json in the dispatch-board repo' % (SPEC, pid),
                    'generatedAt': now, 'pbis': pbi_rows, 'board': data.get('boardNote', ''), 'later': later_items(spec)},
    }


# --- the git tab -------------------------------------------------------------
# The commands themselves stay with their callers: running git is I/O, and a caller may need its own timeout.

# The userinfo of a URL remote: everything between "://" and the last "@" before the host's first "/".
USERINFO = re.compile(r'(?<=://)[^/\s]*@')


def public_remote(line):
    """A `git remote -v` line without the userinfo of its URL, so a token stored in a remote URL is never published."""
    return USERINFO.sub('', line)


def git_default(master_out, main_out):
    """The repository's default branch from the stdout of `git rev-parse --verify --quiet` for master and for
    main: master when it exists, else main, else "" when it has neither."""
    return 'master' if master_out else ('main' if main_out else '')


def git_doc(root, branch, default, log, files, status, remotes_raw, head, ahead_out, shortstat_out, now):
    """The git tab of the repository at root, from the already-captured stdout (stripped) of the commands its
    caller ran: log as "%h|%ad|%s" lines, files from ls-files, status from status --short, remotes_raw from
    remote -v, head from rev-parse --short HEAD, and the rev-list and diff --shortstat output.

    ahead and shortstat are "" unless the repository has both a default branch and a current branch, since
    neither comparison means anything without both. A caller may therefore skip those two commands and pass
    "": the answer is the same either way, so it cannot diverge from the rule by getting the condition wrong.
    """
    commits = []
    for line in log.splitlines():
        sha, date, subject = line.split('|', 2)
        commits.append({'sha': sha, 'date': date, 'subject': subject})
    tracked = files.splitlines()
    by_dir = {}
    for f in tracked:
        d = f.split('/')[0] if '/' in f else '(root)'
        by_dir[d] = by_dir.get(d, 0) + 1
    dirty = [l for l in status.splitlines() if l.strip()]
    remotes = [public_remote(l) for l in remotes_raw.splitlines() if l.strip()]
    both = bool(default and branch)
    return {'source': 'git, local repository', 'generatedAt': now, 'repoPath': root.replace('\\', '/'),
            'branch': branch, 'defaultBranch': default, 'head': head,
            'remotes': remotes, 'ahead': ahead_out if both else '', 'shortstat': shortstat_out if both else '',
            'dirty': dirty, 'tracked': len(tracked), 'byDir': by_dir, 'commits': commits}


# --- catalogue ---------------------------------------------------------------

PURPOSE_MAX = 120  # characters in a plugin's one-line purpose, the ellipsis included


def frontmatter(text, source='', warn=None):
    """The single-line "key: value" pairs between the first two lines that are "---" in text, which is expected
    with its line ends already read as "\\n". Raises ValueError for text with no frontmatter. A block value is
    skipped, with a warning naming source and the key."""
    lines = text.split('\n')
    marks = [i for i, line in enumerate(lines) if line.strip() == '---']
    if len(marks) < 2:
        raise ValueError('no frontmatter')
    fm = {}
    for line in lines[marks[0] + 1:marks[1]]:
        if not line.strip() or line[0].isspace() or ':' not in line:
            continue  # blank, or the continuation of a block value
        key, value = (s.strip() for s in line.split(':', 1))
        if re.match(r'^[>|][+-]?\d*$', value):
            # Only single-line values are read; publishing a block's first line would misstate the text.
            if warn:
                warn('%s: "%s" is a block value, which is not read' % (source, key))
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        fm[key] = value
    return fm


def purpose(desc, plugin):
    """A plugin's one-line purpose: the first sentence of its manifest description, cut to PURPOSE_MAX
    characters at a word boundary. The plugin's name when there is no usable description."""
    if not isinstance(desc, str) or not desc.strip():
        return plugin
    text = desc.strip()
    end = len(text)
    for m in re.finditer(r'[.!?](?=\s|$)', text):
        if m.group() == '.' and re.search(r'(?i)(?:^|\W)(?:e\.g|i\.e)$', text[:m.start()]):
            continue  # "e.g." and "i.e." do not end a sentence
        end = m.end()
        break
    line = text[:end]
    if len(line) > PURPOSE_MAX:
        room = PURPOSE_MAX - 1  # leaves one character for the ellipsis
        cut = line[:room]
        if line[room] != ' ' and ' ' in cut:
            cut = cut[:cut.rfind(' ')]  # the last whole word that fits
        line = cut.rstrip(' ,') + '…'
    return line
