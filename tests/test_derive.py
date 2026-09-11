"""derive.py, imported directly: the parsing and derivation the exporters share, fed parsed records and text.

Importing it must touch no files, print nothing and need nothing beyond the standard library, so a collector
can import it and feed it records as it reads them.
"""
import copy, io, json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTERS = os.path.join(HERE, 'exporters')
sys.path.insert(0, EXPORTERS)
import derive  # noqa: E402

# Imports the module at argv[1] in a fresh interpreter and reports, as JSON, the modules it imports, every file,
# folder, process or socket event raised while its own top-level code runs (from sys.addaudithook), and what it
# printed. The modules it imports are loaded first, so their own loading is not counted against it.
PROBE = r'''
import ast, io, json, os, sys
path = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.dirname(path))
with io.open(path, encoding='utf-8') as f:
    tree = ast.parse(f.read())
names = sorted({a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
               | {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module})
for n in names:
    __import__(n)
target, events = os.path.normcase(path), []
IO = ('os.', 'subprocess.', 'socket.', 'shutil.', 'glob.', 'tempfile.', 'sqlite3.', 'urllib.', 'webbrowser.', 'ctypes.')

def hook(event, args):
    if event != 'open' and not event.startswith(IO):
        return
    f = sys._getframe(1)
    while f:
        if os.path.normcase(os.path.abspath(f.f_code.co_filename)) == target:
            events.append([event, repr(args)[:200]])
            return
        f = f.f_back
sys.addaudithook(hook)
out, err = io.StringIO(), io.StringIO()
real = sys.stdout, sys.stderr
sys.stdout, sys.stderr = out, err
try:
    __import__(os.path.splitext(os.path.basename(path))[0])
finally:
    sys.stdout, sys.stderr = real
print(json.dumps({'imports': names, 'events': events, 'out': out.getvalue(), 'err': err.getvalue()}))
'''


def probe(path):
    r = subprocess.run([sys.executable, '-B', '-I', '-c', PROBE, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError('importing %s failed or exited (%d): %s' % (path, r.returncode, r.stderr))
    return json.loads(r.stdout)


class Import(unittest.TestCase):
    def test_importing_touches_no_files_and_prints_nothing(self):
        got = probe(os.path.join(EXPORTERS, 'derive.py'))
        self.assertEqual(got['events'], [])
        self.assertEqual((got['out'], got['err']), ('', ''))

    def test_imports_only_the_standard_library(self):
        got = probe(os.path.join(EXPORTERS, 'derive.py'))
        self.assertEqual([n for n in got['imports'] if n not in sys.stdlib_module_names], [])

    def test_the_probe_sees_a_module_that_reads_a_file_and_prints(self):
        # Without this, an empty events list could just mean the probe sees nothing.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'touchy.py')
            with io.open(path, 'w', encoding='utf-8') as f:
                f.write('import os\nopen(__file__).close()\nos.listdir(os.path.dirname(__file__))\nprint("hi")\n')
            got = probe(path)
        self.assertEqual(sorted({e for e, _ in got['events']}), ['open', 'os.listdir'])
        self.assertEqual(got['out'], 'hi\n')


def ts(minute):
    return '2026-09-10T10:%02d:00Z' % minute


def assistant(minute, mid, text='', tools=(), usage=None):
    content = ([{'type': 'text', 'text': text}] if text else []) + list(tools)
    return {'type': 'assistant', 'timestamp': ts(minute), 'message': {
        'id': mid, 'model': 'claude-opus-5', 'content': content,
        'usage': usage or {'input_tokens': 10, 'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 1, 'output_tokens': 2}}}


def user(minute, content, **extra):
    return dict({'type': 'user', 'timestamp': ts(minute), 'cwd': 'C:/work/app', 'message': {'role': 'user', 'content': content}}, **extra)


NOTE = ('<task-notification><task-id>acw</task-id><status>completed</status><result>Verdict: DONE</result>'
        '<subagent_tokens>5000</subagent_tokens><duration_ms>120000</duration_ms></task-notification>')
MAIN = [
    user(0, 'Ship it with password=hunter2 please'),
    assistant(1, 'm1', tools=[{'type': 'tool_use', 'id': 'toolu_cw', 'name': 'Agent', 'input': {}},
                              {'type': 'tool_use', 'id': 's1', 'name': 'Skill', 'input': {'skill': 'review-agents:code-reviewer'}}]),
    user(2, '<command-name>/backlog-delivery:pbi-plan</command-name>'),
    user(3, NOTE),
]
AGENT = [assistant(2, 'a1', text='All green. Verdict: DONE')]
META = {'agentType': 'backlog-delivery:code-writer', 'description': 'Build PBI-012 under TDD', 'toolUseId': 'toolu_cw'}


def feed(records, raw=False, warn=None):
    state = derive.new_session('sid-1')
    for o in records:
        derive.add_record(state, o, json.dumps(o) + '\n' if raw else None, warn)
    return state


class Sessions(unittest.TestCase):
    def test_tokens_weigh_cache_reads_writes_and_output(self):
        u = {'input_tokens': 10, 'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 1, 'output_tokens': 2}
        self.assertEqual(derive.tokens(u), (10, 100, 1, 2, 32.0))
        self.assertEqual(derive.tokens({})[4], 0)

    def test_record_pairs_keep_only_json_objects(self):
        lines = ['{"a": 1}\n', '[1]\n', 'not json\n', '[' * 100000 + ']' * 100000, '{"b": 2}']
        self.assertEqual(list(derive.record_pairs(lines)), [('{"a": 1}\n', {'a': 1}), ('{"b": 2}', {'b': 2})])

    def test_a_session_fed_record_by_record(self):
        state = feed(MAIN)
        sub = derive.read_agent(AGENT)
        row = derive.agent_row(state, 'acw', META, sub, age=9999, window=600)
        self.assertEqual({k: row[k] for k in ('lane', 'kind', 'verdict', 'tok', 'min', 'label', 'pbis', 'start', 'end')},
                         {'lane': 'cw', 'kind': 'done', 'verdict': 'DONE', 'tok': 5000, 'min': 2, 'label': 'Build PBI-012',
                          'pbis': ['012'], 'start': ts(1), 'end': ts(3)})
        doc = derive.session_result(state, [sub], [row], [])['doc']
        self.assertEqual((doc['cwd'], doc['folder'], doc['start'], doc['last']), ('C:/work/app', 'app', ts(0), ts(3)))
        self.assertEqual(doc['firstPrompt'], 'Ship it with password=[redacted] please')
        self.assertEqual(doc['skillUses'], {'review-agents:code-reviewer': {'count': 1, 'last': ts(1)},
                                            'backlog-delivery:pbi-plan': {'count': 1, 'last': ts(2)}})
        self.assertEqual(doc['usage']['totals']['requests'], 2)
        self.assertEqual(doc['usage']['subagents'][0]['type'], 'code-writer')

    def test_a_derived_document_does_not_change_as_more_records_arrive(self):
        more = [assistant(5, 'm3', tools=[{'type': 'tool_use', 'id': 's3', 'name': 'Skill', 'input': {'skill': 'review-agents:code-reviewer'}}]),
                {'type': 'system', 'timestamp': ts(6), 'apiErrorStatus': 429,
                 'quotaLimits': {'resetsAt': 1789045200, 'rateLimitType': 'five_hour', 'overageDisabledReason': 'org_level_disabled'}}]

        def derived(state):
            sub = derive.read_agent(AGENT)
            return derive.session_result(state, [sub], [derive.agent_row(state, 'acw', META, sub, 9999, 600)], [])['doc']

        state = feed(MAIN)
        first = derived(state)
        kept = copy.deepcopy(first)
        for o in more:
            derive.add_record(state, o)
        second = derived(state)
        self.assertEqual(first, kept)
        self.assertEqual(second['skillUses']['review-agents:code-reviewer'], {'count': 2, 'last': ts(5)})
        self.assertEqual([l['refused'] for l in second['usage']['limits']], [1])
        self.assertEqual(second, derived(feed(MAIN + more)))

    def test_an_agent_summary_does_not_change_as_more_records_arrive(self):
        state = derive.new_agent()
        derive.add_agent(state, AGENT[0])
        first = derive.agent_summary(state)
        kept = copy.deepcopy(first)
        # The same streamed response continuing with a tool call, then a refused request.
        derive.add_agent(state, assistant(3, 'a1', tools=[{'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {}}]))
        derive.add_agent(state, {'type': 'system', 'timestamp': ts(4), 'apiErrorStatus': 429})
        second = derive.agent_summary(state)
        self.assertEqual(first, kept)
        self.assertEqual((second['resps'][0]['tools'], len(second['rejects']), second['last']), (['Bash'], 1, ts(4)))

    def test_carried_ends_a_running_row_once_it_has_gone_quiet(self):
        now = derive.epoch(ts(30))
        live = {'id': 'a', 'kind': 'running', 'verdict': 'running', 'end': ts(25)}
        self.assertIs(derive.carried(live, 600, now), live)
        quiet = derive.carried(live, 60, now)
        self.assertEqual((quiet['kind'], quiet['verdict'], quiet['id']), ('killed', 'no result', 'a'))
        self.assertEqual(live['kind'], 'running')  # the kept row is copied, not changed
        self.assertEqual(derive.carried({'kind': 'running', 'end': None}, 600, now)['kind'], 'killed')
        done = {'kind': 'done', 'end': ts(0)}
        self.assertIs(derive.carried(done, 60, now), done)

    def test_excluded_matches_the_folder_or_either_form_of_the_cwd(self):
        self.assertTrue(derive.excluded(['C--Users-jdk-private*'], 'C--Users-jdk-private-x', None))
        self.assertTrue(derive.excluded(['C:/secret/*'], 'C--secret-a', 'C:\\secret\\a'))
        self.assertTrue(derive.excluded(['*\\secret\\*'], 'f', 'C:\\secret\\a'))
        self.assertFalse(derive.excluded(['*-private*'], 'C--work-app', 'C:/work/app'))
        self.assertFalse(derive.excluded([], 'anything', 'C:/anything'))

    def test_project_doc_combines_its_exported_linked_sessions(self):
        def usage(first, last, requests):
            return {'span': {'first': first, 'last': last}, 'totals': {'requests': requests, 'effective': 10 * requests},
                    'hourly': [{'hour': first[:13], 'main': requests, 'sub': 0}]}
        p = {'id': 'app', 'name': 'App', 'repoPath': 'C:/app', 'branch': 'main', 'statusDoc': 'status/app',
             'sessions': ['s1', 'gone', 's2', 's3', 'other']}
        results = {'s1': {'doc': {'last': ts(9), 'usage': usage(ts(1), ts(9), 2)}},
                   's2': {'doc': {'last': ts(20), 'usage': usage(ts(15), ts(20), 3)}},
                   's3': {'doc': {'last': None, 'usage': None}},
                   'other': {'doc': {'last': ts(59), 'usage': usage(ts(50), ts(59), 7)}}}
        project_of = {'s1': 'app', 's2': 'app', 's3': 'app', 'gone': 'app', 'other': 'first'}  # listed under an earlier project too
        doc = derive.project_doc(p, 1, results, {'s1': 2, 's2': 1, 's3': 4, 'other': 9}, {'s1': 0, 's2': 1, 's3': 0, 'other': 1}, project_of)
        self.assertEqual({k: doc[k] for k in ('name', 'repoPath', 'branch', 'statusDoc', 'order', 'sessions', 'runs', 'running', 'last')},
                         {'name': 'App', 'repoPath': 'C:/app', 'branch': 'main', 'statusDoc': 'status/app', 'order': 1,
                          'sessions': ['s1', 's2', 's3'], 'runs': 7, 'running': 1, 'last': ts(20)})
        self.assertEqual(doc['usage']['totals'], {'requests': 5, 'effective': 50})
        self.assertEqual(doc['usage']['span'], {'first': ts(1), 'last': ts(20)})
        empty = derive.project_doc(dict(p, sessions=['gone']), 0, results, {}, {}, project_of)
        self.assertEqual((empty['sessions'], empty['runs'], empty['last'], empty['usage']), ([], 0, None, None))

    def test_raw_lines_and_bare_records_derive_the_same(self):
        self.assertEqual(feed(MAIN, raw=True), feed(MAIN))

    def test_a_repeated_streamed_response_counts_once(self):
        state = feed(MAIN + [MAIN[1]])
        self.assertEqual(len(state['by']), 1)
        self.assertEqual(state['uses']['review-agents:code-reviewer']['count'], 1)

    def test_an_unsafe_skill_id_is_dropped_through_warn(self):
        said = []
        bad = assistant(4, 'm2', tools=[{'type': 'tool_use', 'id': 's2', 'name': 'Skill', 'input': {'skill': 'no spaces!'}}])
        state = feed([bad], warn=said.append)
        self.assertEqual(state['uses'], {})
        self.assertEqual(said, ["session sid-1: skill id 'no spaces!' dropped"])

    def test_classify(self):
        fin = {'status': 'completed', 'result': '**NO-GO**', 'ms': '60000'}
        self.assertEqual(derive.classify('cr', fin, None, '', ts(0), ts(5), 0, 600), ('nogo', 'NO-GO', 1))
        self.assertEqual(derive.classify('cw', None, ts(3), '', ts(0), ts(5), 0, 600)[:2], ('killed', 'stopped'))
        self.assertEqual(derive.classify('cw', None, None, '', ts(0), ts(5), 10, 600), ('running', 'running', 5))

    def test_link_hands_a_plan_go_to_the_build_of_the_same_pbi(self):
        plan = {'id': 'p', 'lane': 'plan', 'kind': 'go', 'pbis': ['012'], 'fix': False, 'start': ts(0), 'end': ts(1)}
        build = {'id': 'b', 'lane': 'cw', 'kind': 'done', 'pbis': ['012'], 'fix': False, 'start': ts(2), 'end': ts(3)}
        other = {'id': 'o', 'lane': 'cw', 'kind': 'done', 'pbis': ['009'], 'fix': False, 'start': ts(9), 'end': ts(10)}
        derive.link([plan, build, other])
        self.assertEqual(build.get('from'), 'p')
        self.assertNotIn('from', other)

    def test_manual_rows_follow_their_anchor_and_publish_without_agent_fields(self):
        rows = [{'id': 'a', 'session': 's', 'start': ts(0), 'end': ts(4), 'lane': 'cw', 'agentType': 'x:code-writer'}]
        derive.place_manual(rows, [{'id': 'm', 'after': 'a', 'label': 'by hand'}, {'id': 'z', 'after': 'gone', 'label': 'y'}])
        self.assertEqual([r['id'] for r in rows], ['a', 'm'])
        self.assertEqual((rows[1]['start'], rows[1]['lane'], rows[1]['kind']), (ts(4), 'orch', 'done'))
        rows[0].update(label='l', kind='done', verdict='DONE', tok=1, min=1)
        self.assertEqual(derive.run_doc(rows[0], 1, 'proj')['agentType'], 'x:code-writer')
        self.assertNotIn('start', derive.run_doc(rows[1], 2, None))

    def test_aggregated_limits_that_share_a_reset_are_one(self):
        def usage(first, refused):
            return {'limits': [{'firstAt': first, 'refused': refused, 'type': 'five_hour', 'resetsAt': 'R'}]}
        got = derive.aggregate_usage([usage(ts(5), 2), None, usage(ts(1), 3)])['limits']
        self.assertEqual(got, [{'firstAt': ts(1), 'refused': 5, 'type': 'five_hour', 'resetsAt': 'R'}])

    def test_session_doc_keeps_the_prompt_out_unless_asked(self):
        result = {'doc': {'title': None, 'firstPrompt': 'hello there', 'last': ts(0)}}
        st = {'show_first_prompt': False, 'legacy_build': set(), 'project_of': {}, 'days': 7, 'window_minutes': 10}
        doc = derive.session_doc(result, 'abcdefgh-1234', st, 0, 0)
        self.assertEqual(doc['title'], 'abcdefgh')
        self.assertNotIn('firstPrompt', doc)
        self.assertEqual(derive.session_doc(result, 'abcdefgh-1234', dict(st, show_first_prompt=True), 0, 0)['title'], 'hello there')


SPEC = '''---
revision: 3
---
**Rows the human must confirm or correct at the plan gate:** 2.

## Assumptions & open questions
| # | Question | Resolution | Status | Source | Impact |
|---|---|---|---|---|---|
| 1 | Q1 | R1 | **Open** | brief | High risk |
| 2 | Q2 | R2 | Resolved | prd | Low |

### In scope
- [Board](x.md) pages

### PBI list (proposed)
| ID | Title | Depends | Group | Risk | Spec | Notes |
|---|---|---|---|---|---|---|
| PBI-001 | First | — | A | Low | no | |
| PBI-002 | Second | PBI-001 | A | Med | yes | |

### Future iterations (not planned)
- **Dark mode**: later.
'''


class Board(unittest.TestCase):
    def test_spec_docs_from_text(self):
        data = {'buildState': {'PBI-001': {'state': 'done', 'commit': 'abc'}}, 'boardNote': 'note'}
        paths = {'spec': 'docs/spec.md', 'adrDir': 'docs/adr/'}
        docs = derive.spec_docs('app', paths, SPEC, None, '', '', [], [], data, 'NOW')
        rows = docs['assumptions']['rows']
        self.assertEqual([(r['status'], r['level'], r['needsYou']) for r in rows], [('Open', 'High', False), ('Resolved', 'Low', True)])
        self.assertEqual((docs['spec']['revision'], docs['spec']['designRevision'], docs['spec']['prd']), ('3', '—', None))
        self.assertEqual(docs['spec']['scopeIn'], ['Board pages'])
        self.assertEqual([(p['id'], p['state'], p['review'], p['commit']) for p in docs['backlog']['pbis']],
                         [('PBI-001', 'done', '—', 'abc'), ('PBI-002', 'todo', '—', '')])
        self.assertEqual(docs['backlog']['later'], [{'title': 'Dark mode', 'description': 'later.'}])
        self.assertEqual(docs['decisions']['source'], 'docs/spec.md, docs/adr/')
        self.assertIn('projects/app.json', docs['backlog']['source'])

    def test_section_stops_at_a_heading_of_the_same_level(self):
        text = '## A\none\n### A.1\ntwo\n## B\nthree\n'
        self.assertEqual(derive.section(text, '## A'), '\none\n### A.1\ntwo\n')
        self.assertEqual(derive.section(text, '## C'), '')

    def test_table_cells_unescape_pipes_and_drop_links(self):
        self.assertEqual(derive.table('| h | h2 |\n|---|---|\n| a \\| b | [t](u) |\n'), [['a | b', 't']])

    def test_review_verdict_and_adr_entry(self):
        self.assertEqual(derive.review_verdict('**Verdict:** **GO-WITH-NOTES** after r2'), 'GO-WITH-NOTES')
        self.assertEqual(derive.review_verdict('no verdict yet'), '—')
        adr = derive.adr_entry('id: ADR-001\ntitle: Use X  # why\nstatus: accepted\n', 'docs/adr/1.md')
        self.assertEqual(adr, {'id': 'ADR-001', 'title': 'Use X', 'status': 'accepted', 'resolves': '', 'path': 'docs/adr/1.md'})


class Catalogue(unittest.TestCase):
    def test_frontmatter_reads_single_line_values(self):
        said = []
        fm = derive.frontmatter('---\nname: "writer"\ndescription: >\n  folded\n---\nbody\n', 'a.md', said.append)
        self.assertEqual(fm, {'name': 'writer'})
        self.assertEqual(said, ['a.md: "description" is a block value, which is not read'])

    def test_text_without_frontmatter_is_refused(self):
        with self.assertRaises(ValueError):
            derive.frontmatter('# just a heading\n')

    def test_purpose_is_the_first_sentence_within_the_limit(self):
        self.assertEqual(derive.purpose('Agents, e.g. reviewers. More.', 'p'), 'Agents, e.g. reviewers.')
        self.assertEqual(derive.purpose('  ', 'p'), 'p')
        long = derive.purpose('word ' * 60, 'p')
        self.assertTrue(long.endswith('…') and len(long) <= derive.PURPOSE_MAX, long)


if __name__ == '__main__':
    unittest.main()
