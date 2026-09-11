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
import glob, io, json, os, shutil, sys, tempfile, time

import board_config
import derive
# The parsing and derivation names other code imports from this module stay importable from here.
from derive import (  # noqa: F401
    BUILD_LANES, BUILD_TOKENS, FIX, GROUP_LABEL, HOURS, LANE, MODEL_LABEL, NEGATED, RATE_LIMIT, REVIEW_LANES,
    REVIEW_TOKENS, SECRETS, SKILL_ID, TOKEN, TOKEN_FIELDS, VERIFIER_TIERS, VERIFIER_TOKENS, VERIFIER_WORD,
    aggregate_usage, carried, classify, epoch, excluded, group_of, is_number, kind_of, link, num, pbis, redact,
    reject, response, session_doc, stamp, strings, tag, text_of, tokens, usage_doc, verdict_of, verifier_outcome)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(HERE, 'board.config.json')
PARSER_VERSION = 5  # bump when parsing changes, to drop cached results


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


def records(path):
    """(raw line, parsed record) pairs for every line holding a JSON object; anything else is skipped."""
    with io.open(path, encoding='utf-8', errors='replace') as f:
        yield from derive.record_pairs(f)


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


def read_subagent(path):
    return derive.read_agent(o for _, o in records(path))


def parse_session(base, sid, main_path, st, now):
    """The session's document and agent rows as read from its transcripts. Nothing taken from the config
    except the running window is applied here, so the result can be cached against the transcripts alone.
    skipped lists the agents whose files could not be read this time."""
    state = derive.new_session(sid)
    for raw, o in records(main_path):
        derive.add_record(state, o, raw, warn)
    if not state['by']:
        return None  # nothing was ever answered in this session

    subs, rows, skipped = [], [], []
    for path in sorted(glob.glob(os.path.join(base, sid, 'subagents', 'agent-*.jsonl'))):
        aid = os.path.basename(path)[len('agent-'):-len('.jsonl')]
        try:
            age = now - os.path.getmtime(path)
            meta = load_meta(path[:-len('.jsonl')] + '.meta.json')
            s = read_subagent(path)
            row = derive.agent_row(state, aid, meta, s, age, st['window'])
        except Exception as e:  # one unreadable agent file must not hide the rest of the session
            warn('session %s: agent %s skipped (%s: %s)' % (sid, aid, type(e).__name__, e))
            skipped.append(aid)
            continue
        subs.append(s)
        rows.append(row)
    return derive.session_result(state, subs, rows, skipped)


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
    derive.place_manual(rows, st['manual'])

    for d in ('sessions', 'runs', 'projects'):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True)
        os.makedirs(os.path.join(out, d))
    running, counts = {}, {}
    for sid in results:
        mine = [r for r in rows if r['session'] == sid]
        link(mine)
        for i, r in enumerate(mine, 1):
            write_json(os.path.join(out, 'runs', r['id'] + '.json'), derive.run_doc(r, i, st['project_of'].get(sid)))
        running[sid], counts[sid] = sum(r['kind'] == 'running' for r in mine), len(mine)
        write_json(os.path.join(out, 'sessions', sid + '.json'), session_doc(results[sid], sid, st, len(mine), running[sid]))
    for order, p in enumerate(st['projects']):
        write_json(os.path.join(out, 'projects', p['id'] + '.json'),
                   derive.project_doc(p, order, results, counts, running, st['project_of']))
    legacy = os.path.join(out, 'usage.json')  # replaced by the usage block in each session document
    if os.path.exists(legacy):
        os.remove(legacy)
    print('wrote %d sessions (%d re-read), %d runs (%d running) and %d projects | %.1fs' % (
        len(results), parsed, len(rows), sum(running.values()), len(st['projects']), time.time() - t0))
    return 0


if __name__ == '__main__':
    sys.exit(main(out_dir=sys.argv[1] if len(sys.argv) > 1 else None))
