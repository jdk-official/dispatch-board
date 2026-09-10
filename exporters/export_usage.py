"""Summarise Claude usage from Claude Code transcripts as one JSON document for the board's usage tab.

Sessions to include are listed in board.config.json (usage.sessions). For each session the main
transcript and every subagent transcript are read. Streamed responses appear on several transcript
lines with the same message id; each is counted once. Transcript text is treated purely as data.

Effective usage weights token types by relative cost: input 1, cache read 0.1, cache write 2, output 5.
"""
import glob, io, json, os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8'))
SESSIONS = CFG['usage']['sessions']
OUT = os.path.join(HERE, 'out', 'usage.json')
MODEL_LABEL = {'claude-opus-5': 'Opus 5', 'claude-fable-5-1': 'Fable 5.1', 'claude-sonnet-5': 'Sonnet 5', 'claude-haiku-4-5-20251001': 'Haiku 4.5'}
GROUP_LABEL = {
    'subagents': 'Subagents (the agent fleet)', 'reread': 'Re-reading instructions and history',
    'think': 'Thinking and replies', 'files': 'Files and shell commands', 'browser': 'Browser checks',
    'artifact': 'Publishing this dashboard', 'dispatch': 'Dispatching agents', 'skills': 'Loading skills and tools',
    'loop': 'Overnight loop scheduling', 'ask': 'Questions to you', 'connectors': 'Connectors',
    'other': 'Other tools',
}


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
    if tool in ('ScheduleWakeup', 'CronCreate'):
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


def read(path):
    """Responses (deduplicated by message id) and rate-limit refusals from one transcript."""
    by, rejects = {}, []
    for line in io.open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('apiErrorStatus') == 429 or 'quotaLimits' in o:
            q = o.get('quotaLimits') or {}
            rejects.append({'at': o.get('timestamp'), 'resetsAt': q.get('resetsAt'), 'type': q.get('rateLimitType'),
                            'overage': q.get('overageDisabledReason')})
        if o.get('type') != 'assistant':
            continue
        m = o.get('message') or {}
        if not isinstance(m, dict) or not m.get('usage') or m.get('model') == '<synthetic>':
            continue
        r = by.setdefault(m.get('id') or o.get('uuid'), {'model': m.get('model'), 'ts': o.get('timestamp'), 'tools': [], 'usage': None})
        r['usage'] = m['usage']
        for c in m.get('content') or []:
            if isinstance(c, dict) and c.get('type') == 'tool_use':
                r['tools'].append(c.get('name', ''))
    return list(by.values()), rejects


totals = dict(input=0, cacheRead=0, cacheWrite=0, output=0, effective=0.0, requests=0)
models, groups, hourly, all_rejects, subagents = {}, {k: 0.0 for k in GROUP_LABEL}, {}, [], []
first = last = None


def add(resp, is_sub):
    global first, last
    i, cr, cw, o, eff = tokens(resp['usage'])
    for k, v in (('input', i), ('cacheRead', cr), ('cacheWrite', cw), ('output', o), ('effective', eff)):
        totals[k] += v
    totals['requests'] += 1
    mm = models.setdefault(resp['model'], dict(requests=0, input=0, cacheRead=0, cacheWrite=0, output=0, effective=0.0))
    mm['requests'] += 1
    for k, v in (('input', i), ('cacheRead', cr), ('cacheWrite', cw), ('output', o), ('effective', eff)):
        mm[k] += v
    if resp['ts']:
        b = hourly.setdefault(resp['ts'][:13], {'main': 0.0, 'sub': 0.0})
        b['sub' if is_sub else 'main'] += eff
        first = min(first, resp['ts']) if first else resp['ts']
        last = max(last, resp['ts']) if last else resp['ts']
    return i, cr, cw, o, eff


for sess in SESSIONS:
    base, sid = sess['projectsDir'], sess['sessionId']
    main_path = os.path.join(base, sid + '.jsonl')
    if not os.path.exists(main_path):
        print('skipping missing session transcript:', main_path)
        continue
    resps, rej = read(main_path)
    all_rejects += rej
    for r in resps:
        i, cr, cw, o, eff = add(r, False)
        groups['reread'] += 0.1 * cr
        rest = i + 2 * cw + 5 * o
        tg = [group_of(t) for t in r['tools']] or ['think']
        for g in tg:
            groups[g] += rest / len(tg)
    for path in sorted(glob.glob(os.path.join(base, sid, 'subagents', '*.jsonl'))):
        meta_path = path[:-len('.jsonl')] + '.meta.json'
        meta = json.load(io.open(meta_path, encoding='utf-8')) if os.path.exists(meta_path) else {}
        resps, rej = read(path)
        all_rejects += rej
        eff_sum, mods, ts = 0.0, {}, [r['ts'] for r in resps if r['ts']]
        for r in resps:
            eff_sum += add(r, True)[4]
            mods[r['model']] = mods.get(r['model'], 0) + 1
        groups['subagents'] += eff_sum
        raw = meta.get('agentType', 'unknown')
        top_model = max(mods, key=mods.get) if mods else None
        subagents.append({'id': os.path.basename(path)[6:-6], 'session': sid, 'type': 'Gate reviewer' if raw == 'Plan' else raw.split(':')[-1],
                          'agentType': raw, 'description': meta.get('description', ''), 'requests': len(resps),
                          'effective': round(eff_sum), 'model': top_model, 'modelLabel': MODEL_LABEL.get(top_model, top_model or '—'),
                          'start': min(ts) if ts else None, 'end': max(ts) if ts else None})

# Limit windows: refusals grouped by the reset time the platform reported.
windows = {}
for r in sorted(all_rejects, key=lambda x: x['at'] or ''):
    key = r['resetsAt']
    if key is None:  # a refusal without quota detail belongs to the next reset after it
        later = sorted(k for k in windows if isinstance(k, (int, float)) and r['at'] and datetime.fromtimestamp(k, timezone.utc).isoformat() > r['at'])
        key = later[0] if later else 'unknown'
    w = windows.setdefault(key, {'firstAt': r['at'], 'refused': 0, 'type': r['type'] or 'five_hour'})
    w['refused'] += 1
limits = [{'firstAt': w['firstAt'], 'refused': w['refused'], 'type': w['type'],
           'resetsAt': datetime.fromtimestamp(k, timezone.utc).isoformat() if isinstance(k, (int, float)) else None}
          for k, w in sorted(windows.items(), key=lambda kv: kv[1]['firstAt'] or '')]
overage = 'Extra usage beyond the limit is turned off for your organisation, so work paused until each reset.' \
    if any(r['overage'] == 'org_level_disabled' for r in all_rejects) else ''

series = []
if first and last:
    t = datetime.fromisoformat(first[:13] + ':00:00+00:00')
    end = datetime.fromisoformat(last[:13] + ':00:00+00:00')
    while t <= end:
        k = t.strftime('%Y-%m-%dT%H')
        b = hourly.get(k, {'main': 0.0, 'sub': 0.0})
        series.append({'hour': k, 'main': round(b['main']), 'sub': round(b['sub'])})
        t += timedelta(hours=1)

doc = {
    'source': 'Claude Code transcripts for %d session(s) and %d subagent runs, on this computer' % (len(SESSIONS), len(subagents)),
    'generatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'weights': {'input': 1, 'cacheRead': 0.1, 'cacheWrite': 2, 'output': 5},
    'span': {'first': first, 'last': last},
    'totals': {k: (round(v) if isinstance(v, float) else v) for k, v in totals.items()},
    'byModel': sorted([{'model': k, 'label': MODEL_LABEL.get(k, k), **{kk: (round(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()}}
                       for k, v in models.items()], key=lambda m: -m['effective']),
    'groups': [{'key': k, 'label': GROUP_LABEL[k], 'effective': round(v)} for k, v in groups.items() if v >= 1],
    'subagents': subagents, 'hourly': series, 'limits': limits, 'overage': overage,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(doc, ensure_ascii=False, indent=1))
t = doc['totals']
print('wrote %s | requests %d | effective %.1fM | subagents %d | limit windows %d | %d bytes' % (
    OUT, t['requests'], t['effective'] / 1e6, len(subagents), len(limits), len(json.dumps(doc))))
