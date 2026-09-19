"""derive.py, imported directly: the parsing and derivation the exporters share, fed parsed records and text.

Importing it must touch no files, print nothing and need nothing beyond the standard library, so a collector
can import it and feed it records as it reads them.
"""
import copy, importlib.util, io, itertools, json, os, subprocess, sys, tempfile, unittest

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

    def test_run_doc_publishes_a_review_round_findings(self):
        # Run detail (FR-121) reads each run's own findings, which the per-project ledger cannot give it:
        # the ledger is keyed by work item, and leaves out a review that named no PBI id.
        row = {'id': 'a', 'session': 's', 'lane': 'cr', 'label': 'l', 'kind': 'changes', 'verdict': 'CHANGES-REQUIRED',
               'tok': 1, 'min': 2, 'findings': [{'id': 'F1', 'severity': 'HIGH', 'title': 't', 'location': 'app.py:1',
                                                 'remediation': 'fix'}], 'hasFindingsBlock': True}
        self.assertEqual(derive.run_doc(row, 1, 'proj')['findings'], row['findings'])

    def test_run_doc_publishes_an_empty_list_for_a_round_that_reported_none(self):
        row = {'id': 'a', 'session': 's', 'lane': 'cr', 'label': 'l', 'kind': 'go', 'verdict': 'GO', 'tok': 1, 'min': 2,
               'findings': [], 'hasFindingsBlock': True}
        self.assertEqual(derive.run_doc(row, 1, 'proj')['findings'], [])

    def test_run_doc_leaves_findings_out_when_no_block_was_read(self):
        # No key at all, so the page can tell "this round listed nothing" from "nothing readable was reported".
        row = {'id': 'a', 'session': 's', 'lane': 'cr', 'label': 'l', 'kind': 'nogo', 'verdict': 'NO-GO', 'tok': 1,
               'min': 2, 'findings': [], 'hasFindingsBlock': False}
        self.assertNotIn('findings', derive.run_doc(row, 1, 'proj'))
        build = {'id': 'b', 'session': 's', 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'DONE', 'tok': 1, 'min': 2}
        self.assertNotIn('findings', derive.run_doc(build, 2, 'proj'))

    def test_an_agents_edited_files_are_read_from_its_tool_inputs(self):
        # Run detail (FR-121) names the files a run touched. The paths are in the tool inputs of the agent's own
        # transcript; only the four tools that write a file count, and a streamed repeat is not a second file.
        def use(tid, name, inp):
            return {'type': 'tool_use', 'id': tid, 'name': name, 'input': inp}
        sub = derive.read_agent([
            assistant(1, 'a1', tools=[use('t1', 'Read', {'file_path': 'C:/work/app/read-only.py'}),
                                      use('t2', 'Edit', {'file_path': 'C:/work/app/a.py'})]),
            assistant(1, 'a1', tools=[use('t2', 'Edit', {'file_path': 'C:/work/app/a.py'})]),  # the streamed repeat
            assistant(2, 'a2', tools=[use('t3', 'Write', {'file_path': 'C:/work/app/b.py'}),
                                      use('t4', 'MultiEdit', {'file_path': 'C:/work/app/a.py'}),
                                      use('t5', 'NotebookEdit', {'notebook_path': 'C:/work/app/c.ipynb'}),
                                      use('t6', 'Edit', {'file_path': 42}),
                                      use('t7', 'Edit', 'not an object')]),
            assistant(3, 'a3', text='done'),
        ])
        row = derive.agent_row(feed([]), 'acw', META, sub, 0, 600)
        self.assertEqual(row['files'], ['C:/work/app/a.py', 'C:/work/app/b.py', 'C:/work/app/c.ipynb'])

    def test_a_refused_or_failed_edit_call_is_not_counted_as_edited(self):
        # CR-014-9: the tool_use record alone cannot say whether an Edit wrote the file; its tool_result can.
        def use(tid, name, inp):
            return {'type': 'tool_use', 'id': tid, 'name': name, 'input': inp}

        def result(tid, is_error):
            return {'type': 'user', 'timestamp': ts(2), 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': tid, 'is_error': is_error, 'content': 'x'}]}}
        sub = derive.read_agent([
            assistant(1, 'a1', tools=[use('t1', 'Edit', {'file_path': 'C:/work/app/blocked.py'}),
                                      use('t2', 'Edit', {'file_path': 'C:/work/app/a.py'})]),
            result('t1', True),   # refused or failed: the file was never written
            result('t2', False),  # succeeded: still counts
        ])
        row = derive.agent_row(feed([]), 'acw', META, sub, 0, 600)
        self.assertEqual(row['files'], ['C:/work/app/a.py'])

    def test_run_doc_publishes_edited_files_relative_to_the_repository(self):
        row = {'id': 'a', 'session': 's', 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'DONE', 'tok': 1, 'min': 2,
               'files': ['C:\\work\\app\\site\\index.html', 'C:/WORK/APP/exporters/derive.py', 'tests/test_derive.py']}
        # The repository root is stripped so the board publishes no absolute local path; a path that was already
        # relative is published as the agent wrote it, there being no root in it to strip.
        self.assertEqual(derive.run_doc(row, 1, 'proj', repo='C:/work/app')['files'],
                         ['site/index.html', 'exporters/derive.py', 'tests/test_derive.py'])

    def test_run_doc_names_a_file_outside_the_repository_without_its_folder(self):
        # Decision: a path outside the project's repository is published as "…/" and its file name, its folders
        # withheld. The prefix keeps it from reading as a file at the repository's root, which a bare name would.
        row = {'id': 'a', 'session': 's', 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'DONE', 'tok': 1, 'min': 2,
               'files': ['C:/Users/jdk/.claude/settings.json', '/etc/hosts', 'C:/work/app']}
        self.assertEqual(derive.run_doc(row, 1, 'proj', repo='C:/work/app')['files'], ['…/settings.json', '…/hosts'])
        # Without a repository to relativise against, every absolute path is treated the same way.
        self.assertEqual(derive.run_doc(row, 1, 'proj')['files'], ['…/settings.json', '…/hosts', '…/app'])

    def test_run_doc_treats_a_home_or_drive_relative_path_as_unplaceable(self):
        # CR-014-9: the Edit and Write tools refuse both forms, but a value that reached here regardless must
        # not publish a folder the repository test cannot see, so each is withheld like a path outside it.
        row = {'id': 'a', 'session': 's', 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'DONE', 'tok': 1, 'min': 2,
               'files': ['~/.ssh/id_rsa', 'C:foo/bar/baz.txt']}
        self.assertEqual(derive.run_doc(row, 1, 'proj', repo='C:/work/app')['files'], ['…/id_rsa', '…/baz.txt'])

    def test_run_doc_does_not_let_a_parent_step_pass_for_a_file_inside_the_repository(self):
        # A path that starts at the repository but climbs out of it, or a relative one that climbs, is outside it.
        row = {'id': 'a', 'session': 's', 'lane': 'cw', 'label': 'l', 'kind': 'done', 'verdict': 'DONE', 'tok': 1, 'min': 2,
               'files': ['C:/work/app/../private/key.txt', '../up/notes.md', 'C:/work/app/site/../README.md',
                         'C:/work/application/x.py']}
        self.assertEqual(derive.run_doc(row, 1, 'proj', repo='C:/work/app/')['files'],
                         ['…/key.txt', '…/notes.md', 'README.md', '…/x.py'])

    def test_run_doc_leaves_files_out_when_the_run_edited_none(self):
        row = {'id': 'a', 'session': 's', 'lane': 'cr', 'label': 'l', 'kind': 'go', 'verdict': 'GO', 'tok': 1, 'min': 2,
               'files': []}
        self.assertNotIn('files', derive.run_doc(row, 1, 'proj', repo='C:/work/app'))
        manual = {'id': 'm', 'session': 's', 'lane': 'orch', 'label': 'l', 'kind': 'done', 'verdict': '', 'tok': 0, 'min': 0}
        self.assertNotIn('files', derive.run_doc(manual, 2, 'proj', repo='C:/work/app'))

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


def report(*findings, verdict='NO-GO'):
    body = {'schema_version': '1', 'audit': {'agent': 'code-reviewer', 'verdict': verdict}, 'findings': [
        {'id': fid, 'severity': 'HIGH', 'title': 't-' + fid, 'subject': {'type': 'file', 'id': 'app.py:%d' % n, 'name': 'x'},
         'remediation': 'fix-' + fid} for n, fid in enumerate(findings, 1)]}
    return 'Some prose.\n\n```json\n%s\n```' % json.dumps(body)


class FindingsOf(unittest.TestCase):
    def test_a_result_with_no_json_yields_none_not_an_error(self):
        self.assertIsNone(derive.findings_of('Looks fine. GO'))

    def test_a_fenced_block_without_a_findings_list_yields_none(self):
        self.assertIsNone(derive.findings_of('```json\n{"schema_version": "1", "audit": {}}\n```'))

    def test_malformed_json_is_skipped_without_a_crash(self):
        self.assertIsNone(derive.findings_of('```json\n{"findings": [\n```'))

    def test_text_after_the_fence_means_it_does_not_end_with_json(self):
        self.assertIsNone(derive.findings_of(report('F1') + '\nOne more line.'))

    def test_findings_are_read_with_file_line_from_the_subject(self):
        found = derive.findings_of(report('F1', 'F2'))
        self.assertEqual([f['id'] for f in found], ['F1', 'F2'])
        self.assertEqual(found[0], {'id': 'F1', 'severity': 'HIGH', 'title': 't-F1', 'location': 'app.py:1', 'remediation': 'fix-F1'})

    def test_an_empty_findings_list_is_read_as_a_reported_empty_list_not_none(self):
        # A block was found and it reported nothing: a real "all clear", distinct from no block at all.
        self.assertEqual(derive.findings_of(report()), [])

    def test_an_earlier_decoy_fenced_object_does_not_swallow_the_real_block(self):
        text = 'Here is the schema I will use:\n```json\n{"example": true}\n```\n\nNow the findings.\n' + report('F1')
        found = derive.findings_of(text)
        self.assertEqual([f['id'] for f in found], ['F1'])

    def test_a_finding_with_no_id_is_dropped_rather_than_collapsed(self):
        body = {'schema_version': '1', 'audit': {}, 'findings': [
            {'severity': 'LOW', 'title': 'no id', 'subject': {}, 'remediation': 'x'},
            {'id': 'F1', 'severity': 'HIGH', 'title': 't-F1', 'subject': {'id': 'app.py:1'}, 'remediation': 'fix-F1'}]}
        text = 'prose\n```json\n%s\n```' % json.dumps(body)
        self.assertEqual([f['id'] for f in derive.findings_of(text)], ['F1'])


class StatedFigures(unittest.TestCase):
    """The test count and coverage percentage a builder's result states: the first integer followed by "tests",
    and the first percentage next to "coverage"."""

    def test_ac79_the_first_integer_followed_by_tests(self):
        self.assertEqual(derive.stated_tests('DONE. 664 tests green; 2 tests added earlier.'), 664)

    def test_a_grouped_count_is_read_whole_not_from_its_last_group(self):
        self.assertEqual(derive.stated_tests('Ran 1,234 tests, OK'), 1234)
        self.assertIsNone(derive.stated_tests('0.5 tests'))

    def test_no_count_when_nothing_is_followed_by_tests(self):
        self.assertIsNone(derive.stated_tests('All green. DONE'))
        self.assertIsNone(derive.stated_tests('1 test added'))

    def test_the_first_percentage_next_to_coverage_either_side(self):
        self.assertEqual(derive.stated_coverage('Coverage: 87.5% (lines); 90% branches'), 87.5)
        self.assertEqual(derive.stated_coverage('Suite green at 91% coverage.'), 91)
        self.assertEqual(derive.stated_coverage('a 12% speed-up; coverage 80% then coverage 85%'), 80)

    def test_no_coverage_without_a_percentage_beside_the_word(self):
        self.assertIsNone(derive.stated_coverage('coverage is good, 40% faster'))
        self.assertIsNone(derive.stated_coverage('"coverage": 91'))

    def test_a_percentage_over_100_is_not_a_coverage(self):
        self.assertIsNone(derive.stated_coverage('coverage 150%'))

    def test_matching_is_case_insensitive(self):
        self.assertEqual(derive.stated_tests('DONE. 700 TESTS green.'), 700)
        self.assertEqual(derive.stated_coverage('COVERAGE: 92%'), 92)

    def test_the_number_and_the_word_must_share_a_line(self):
        self.assertIsNone(derive.stated_tests('Tier 3\nTests: 410 passed'))
        self.assertEqual(derive.stated_coverage('pass rate 100%\nCoverage: 88%'), 88)

    def test_a_tests_path_is_not_a_stated_count(self):
        self.assertIsNone(derive.stated_tests('Section 24\n\ntests/page.test.mjs 139 checks'))
        self.assertIsNone(derive.stated_tests('see 24 tests/page.test.mjs'))


def cr(rid, pbi, findings, kind='changes', start=0, has_block=True):
    return {'id': rid, 'lane': 'cr', 'pbis': [pbi], 'kind': kind, 'start': ts(start), 'findings': findings,
            'hasFindingsBlock': has_block}


class FindingsDoc(unittest.TestCase):
    def test_ac77_two_rounds_one_finding_still_open(self):
        f1, f2, f3 = {'id': 'F1'}, {'id': 'F2'}, {'id': 'F3'}
        rows = [cr('r1', '001', [f1, f2, f3]), cr('r2', '001', [f2])]
        doc = derive.findings_doc(rows)
        item = doc['PBI-001']
        self.assertEqual(sorted(f['id'] for f in item['open']), ['F2'])
        self.assertEqual(sorted(f['id'] for f in item['resolved']), ['F1', 'F3'])
        self.assertEqual(item['rounds'], 2)
        self.assertNotIn('roundsToGo', item)

    def test_rounds_to_go_is_the_first_round_that_reached_go(self):
        rows = [cr('r1', '001', [{'id': 'F1'}], kind='changes'), cr('r2', '001', [], kind='go')]
        item = derive.findings_doc(rows)['PBI-001']
        self.assertEqual(item['roundsToGo'], 2)
        self.assertEqual(item['open'], [])
        self.assertEqual([f['id'] for f in item['resolved']], ['F1'])

    def test_rows_without_a_pbi_or_outside_the_cr_lane_are_ignored(self):
        rows = [cr('r1', '001', [{'id': 'F1'}]), {'id': 'p', 'lane': 'plan', 'pbis': ['001'], 'kind': 'go', 'findings': [{'id': 'ignored'}]},
                {'id': 'r2', 'lane': 'cr', 'pbis': [], 'kind': 'changes', 'start': ts(1), 'findings': [{'id': 'nowhere'}]}]
        doc = derive.findings_doc(rows)
        self.assertEqual(list(doc), ['PBI-001'])
        self.assertEqual(doc['PBI-001']['rounds'], 1)

    def test_no_cr_rows_yields_no_items(self):
        self.assertEqual(derive.findings_doc([{'id': 'c', 'lane': 'cw', 'pbis': ['001'], 'kind': 'done'}]), {})

    def test_a_review_still_running_or_cut_off_is_not_yet_a_round(self):
        for kind in ('running', 'killed'):
            rows = [{'id': 'r', 'lane': 'cr', 'pbis': ['001'], 'kind': kind, 'start': ts(0), 'findings': [{'id': 'F1'}]}]
            self.assertEqual(derive.findings_doc(rows), {}, kind)

    def test_a_nogo_round_with_no_findings_block_does_not_resolve_earlier_findings(self):
        # This repo's own reviewers write findings to a file and reply in prose, so a real round can be
        # NO-GO (nothing fixed) yet carry no findings JSON. It must count as a round, but not empty the ledger.
        f1, f2, f3 = {'id': 'F1'}, {'id': 'F2'}, {'id': 'F3'}
        rows = [cr('r1', '001', [f1, f2, f3]), cr('r2', '001', [], kind='nogo', start=1, has_block=False)]
        item = derive.findings_doc(rows)['PBI-001']
        self.assertEqual(sorted(f['id'] for f in item['open']), ['F1', 'F2', 'F3'])
        self.assertEqual(item['resolved'], [])
        self.assertEqual(item['rounds'], 2)

    def test_findings_carry_the_round_they_were_first_and_last_seen(self):
        rows = [cr('r1', '001', [{'id': 'F1'}, {'id': 'F2'}], start=0), cr('r2', '001', [{'id': 'F2'}], start=1),
                cr('r3', '001', [{'id': 'F2'}], start=2)]
        item = derive.findings_doc(rows)['PBI-001']
        f1 = next(f for f in item['resolved'] if f['id'] == 'F1')
        f2 = next(f for f in item['open'] if f['id'] == 'F2')
        self.assertEqual((f1['round'], f1['lastSeen']), (1, 1))
        self.assertEqual((f2['round'], f2['lastSeen']), (1, 3))


def run(rid, lane, kind, label, start=0, verdict=None):
    """An agent row as agent_row() builds it, with only the fields work_items() reads."""
    return {'id': rid, 'start': ts(start), 'lane': lane, 'kind': kind, 'verdict': verdict or kind.upper(),
            'label': label, 'pbis': derive.pbis(label)}


def stale_ts(minute):
    return '2026-09-12T%02d:%02d:00Z' % (10 + minute // 60, minute % 60)


# One linked session's runs on 2026-09-12, labelled as the real ones were: five work items merged and reviewed while
# the hand-kept state still called them Not started (PBI-005, 006, 011, 025 and 026), one agreeing item (PBI-003), one
# closed on GO-WITH-CONDITIONS (PBI-017), a review round that names no work item, and spec-gate (plan) and spec-author
# (other) runs that name a work item but are not evidence that it was built. PBI-010 is in the backlog and named by
# no run. (id, minute, lane, kind, verdict, label).
STALE_2026_09_12 = [
    ('s05p1', 0, 'plan', 'changes', 'CHANGES-REQUIRED', 'Spec gate review PBI-005'),
    ('s05p2', 1, 'plan', 'go', 'APPROVE-WITH-NOTES', 'Spec gate review PBI-005 round 2'),
    ('s25a', 2, 'other', 'done', 'DONE', 'Author PBI-025 spec'),
    ('s05b', 3, 'cw', 'done', 'DONE', 'Build PBI-005 local server'),
    ('s05r1', 4, 'cr', 'nogo', 'NO-GO', 'Code-review PBI-005'),
    ('s05f', 5, 'cw', 'done', 'DONE-WITH-CONDITIONS', 'Fix PBI-005 review findings'),
    ('s05r2', 6, 'cr', 'go', 'GO', 'Code-review PBI-005 round 2'),
    ('s06b', 7, 'cw', 'done', 'DONE', 'Build PBI-006 data adapter'),
    ('s06r1', 8, 'cr', 'go', 'GO-WITH-CONDITIONS', 'Code-review PBI-006'),
    ('s06f', 9, 'cw', 'done', 'DONE', 'Fix PBI-006 review conditions'),
    ('s06r2', 10, 'cr', 'go', 'GO', 'Code-review PBI-006 round 2'),
    ('s11b', 11, 'cw', 'done', 'DONE-WITH-CONDITIONS', 'Build PBI-011 findings ledger'),
    ('s11r1', 12, 'cr', 'nogo', 'NO-GO', 'Code-review PBI-011'),
    ('s11f', 13, 'cw', 'done', 'DONE', 'Fix PBI-011 review findings'),
    ('s11r2', 14, 'cr', 'go', 'GO', 'Code-review PBI-011 round 2'),
    ('s25b', 15, 'cw', 'done', 'DONE', 'Build PBI-025 local tabs'),
    ('s25r1', 16, 'cr', 'go', 'GO-WITH-CONDITIONS', 'Code-review PBI-025'),
    ('s25f', 17, 'cw', 'done', 'DONE', 'Fix PBI-025 review conditions'),
    ('s25r2', 18, 'cr', 'go', 'GO', 'Code-review PBI-025 round 2'),
    ('s26b', 19, 'cw', 'done', 'DONE', 'Build PBI-026 local shapes'),
    ('s26r1', 20, 'cr', 'go', 'GO', 'Code-review PBI-026'),
    ('s03r1', 21, 'cr', 'go', 'GO', 'Code-review PBI-003'),
    ('s17b', 22, 'cw', 'done', 'DONE', 'Build PBI-017 page'),
    ('s17r1', 23, 'cr', 'go', 'GO-WITH-CONDITIONS', 'Code-review PBI-017'),
    ('sr2', 24, 'cr', 'go', 'GO', 'Code review round 2'),
]
STALE_DONE = {'PBI-005': 2, 'PBI-006': 2, 'PBI-011': 2, 'PBI-025': 2, 'PBI-026': 1}  # work item -> review rounds


def stale_rows():
    return [{'id': rid, 'start': stale_ts(m), 'end': stale_ts(m), 'lane': lane, 'kind': kind, 'verdict': verdict,
             'label': label, 'pbis': derive.pbis(label)} for rid, m, lane, kind, verdict, label in STALE_2026_09_12]


class WorkItems(unittest.TestCase):
    """Work-item state derived from the code-writer, test-writer and code-reviewer runs that name a work item."""

    def test_work_items_latest_round_go_is_done(self):
        out = derive.work_items([run('r1', 'cr', 'nogo', 'Review PBI-001', 1, 'NO-GO'), run('r2', 'cr', 'go', 'Review PBI-001', 2, 'GO')])
        self.assertEqual(out['items']['PBI-001'], {'state': 'done', 'rounds': 2, 'verdict': 'GO', 'latestRound': 'r2',
                                                   'builds': 0, 'runs': ['r1', 'r2']})
        self.assertEqual(out['unattributedRounds'], 0)

    def test_work_items_conditions_tokens_are_conditions(self):
        for token in ('GO-WITH-CONDITIONS', 'APPROVE-WITH-CONDITIONS'):
            item = derive.work_items([run('r1', 'cr', 'go', 'Review PBI-001', 1, token)])['items']['PBI-001']
            self.assertEqual((item['state'], item['verdict']), ('conditions', token))

    def test_work_items_go_with_notes_and_approve_are_done(self):
        for token in ('GO', 'GO-WITH-NOTES', 'APPROVE', 'APPROVED', 'APPROVE-WITH-NOTES'):
            item = derive.work_items([run('r1', 'cr', 'go', 'Review PBI-001', 1, token)])['items']['PBI-001']
            self.assertEqual(item['state'], 'done', token)

    def test_work_items_latest_nogo_or_changes_is_partial(self):
        for kind, token in (('nogo', 'NO-GO'), ('nogo', 'REJECT'), ('changes', 'CHANGES-REQUIRED')):
            rows = [run('r1', 'cr', 'go', 'Review PBI-001', 1, 'GO'), run('r2', 'cr', kind, 'Review PBI-001', 2, token)]
            item = derive.work_items(rows)['items']['PBI-001']
            self.assertEqual((item['state'], item['rounds'], item['verdict']), ('partial', 2, token))

    def test_work_items_activity_without_a_round_is_partial(self):
        for lane, kind in (('cw', 'done'), ('cw', 'killed'), ('tw', 'done'), ('cr', 'running'), ('cr', 'killed')):
            item = derive.work_items([run('r1', lane, kind, 'Work on PBI-001')])['items']['PBI-001']
            self.assertEqual((item['state'], item['rounds'], item['verdict'], item['latestRound']), ('partial', 0, None, None), (lane, kind))
            self.assertEqual(item['builds'], 1 if lane in ('cw', 'tw') else 0)

    def test_work_items_a_build_after_a_go_does_not_downgrade_it(self):
        rows = [run('r1', 'cr', 'go', 'Review PBI-001', 1, 'GO'), run('b1', 'cw', 'done', 'Apply PBI-001 conditions', 2)]
        item = derive.work_items(rows)['items']['PBI-001']
        self.assertEqual((item['state'], item['builds'], item['runs']), ('done', 1, ['r1', 'b1']))
        rows = [run('r1', 'cr', 'nogo', 'Review PBI-001', 1, 'NO-GO'), run('b1', 'cw', 'done', 'Fix PBI-001', 2)]
        self.assertEqual(derive.work_items(rows)['items']['PBI-001']['state'], 'partial')

    def test_work_items_an_unfinished_review_after_a_go_does_not_downgrade_it(self):
        for kind in ('running', 'killed'):
            rows = [run('r1', 'cr', 'go', 'Review PBI-001', 1, 'GO'), run('r2', 'cr', kind, 'Review PBI-001', 2)]
            item = derive.work_items(rows)['items']['PBI-001']
            self.assertEqual((item['state'], item['rounds'], item['latestRound']), ('done', 1, 'r1'), kind)

    def test_work_items_a_run_naming_three_pbis_credits_all_three(self):
        out = derive.work_items([run('r1', 'cr', 'nogo', 'Code-review gate PBI-003/004/005', 1, 'NO-GO')])
        self.assertEqual(sorted(out['items']), ['PBI-003', 'PBI-004', 'PBI-005'])
        for pbi, item in out['items'].items():
            self.assertEqual((item['rounds'], item['state']), (1, 'partial'), pbi)

    def test_work_items_a_round_naming_no_pbi_credits_none_and_is_counted(self):
        out = derive.work_items([run('r1', 'cr', 'go', 'Code review round 2', 1, 'GO'), run('b1', 'cw', 'done', 'Tidy the page', 2)])
        self.assertEqual(out, {'items': {}, 'unattributedRounds': 1})

    def test_work_items_plan_ver_req_other_and_orch_lanes_are_never_evidence(self):
        rows = [run('p1', 'plan', 'go', 'Spec gate PBI-009', 1, 'APPROVE'), run('v1', 'ver', 'done', 'Verify PBI-009', 2, 'exercised'),
                run('o1', 'other', 'done', 'Author PBI-009 spec', 3), run('q1', 'req', 'done', 'PRD for PBI-009', 4),
                run('m1', 'orch', 'done', 'Merge PBI-009', 5)]
        self.assertEqual(derive.work_items(rows), {'items': {}, 'unattributedRounds': 0})

    def test_work_items_order_is_start_then_id(self):
        go, nogo = run('r1', 'cr', 'go', 'Review PBI-001', 1, 'GO'), run('r2', 'cr', 'nogo', 'Review PBI-001', 2, 'NO-GO')
        self.assertEqual(derive.work_items([go, nogo]), derive.work_items([nogo, go]))
        self.assertEqual(derive.work_items([nogo, go])['items']['PBI-001']['state'], 'partial')
        # With identical start times the larger id is the latest.
        a, b = dict(go, id='a'), dict(nogo, id='b', start=go['start'])
        self.assertEqual(derive.work_items([b, a])['items']['PBI-001']['latestRound'], 'b')
        rows = [run('x1', 'cw', 'done', 'Build PBI-001', 1), run('x2', 'cr', 'nogo', 'Review PBI-001/002', 2, 'NO-GO'),
                run('x3', 'cw', 'done', 'Fix PBI-001', 3), run('x4', 'cr', 'go', 'Review PBI-001', 3, 'GO'),
                run('x5', 'cr', 'go', 'Code review round 2', 4, 'GO'), dict(run('x6', 'tw', 'done', 'Tests PBI-002'), start=None)]
        want = derive.work_items(rows)
        for perm in itertools.permutations(rows):
            self.assertEqual(derive.work_items(list(perm)), want)
        self.assertEqual(json.dumps(want, sort_keys=False), json.dumps(derive.work_items(list(reversed(rows))), sort_keys=False))

    def test_work_items_rounds_equal_findings_doc_rounds(self):
        rows = stale_rows() + [dict(run('f1', 'cr', 'changes', 'Code-review PBI-017 round 2', 30, 'CHANGES-REQUIRED'),
                                    findings=[{'id': 'F1'}], hasFindingsBlock=True)]
        items, ledger = derive.work_items(rows)['items'], derive.findings_doc(rows)
        both = set(items) & set(ledger)
        self.assertEqual(both, {p for p, i in items.items() if i['rounds']})
        for pbi in both:
            self.assertEqual(items[pbi]['rounds'], ledger[pbi]['rounds'], pbi)

    def test_work_items_output_round_trips_through_json(self):
        out = derive.work_items(stale_rows())
        self.assertEqual(json.loads(json.dumps(out)), out)

    def test_the_2026_09_12_fixture_derives_done_for_the_five(self):
        out = derive.work_items(stale_rows())
        for pbi, rounds in STALE_DONE.items():
            self.assertEqual((out['items'][pbi]['state'], out['items'][pbi]['rounds']), ('done', rounds), pbi)
        self.assertEqual(out['items']['PBI-003']['state'], 'done')
        self.assertEqual(out['items']['PBI-017']['state'], 'conditions')
        self.assertEqual(out['unattributedRounds'], 1)
        self.assertEqual(set(out['items']), set(STALE_DONE) | {'PBI-003', 'PBI-017'})
        self.assertNotIn('todo', {i['state'] for i in out['items'].values()})


def project(pid='app', sessions=('s1',), **over):
    return dict({'id': pid, 'name': pid, 'repoPath': 'C:/' + pid, 'branch': 'main', 'statusDoc': 'status/' + pid,
                 'sessions': list(sessions)}, **over)


def exported(*rows, last=None):
    return {'doc': {'last': last, 'usage': None}, 'rows': list(rows)}


class ProjectWorkItems(unittest.TestCase):
    def test_project_doc_carries_work_items_from_its_linked_sessions_only(self):
        mine = run('m1', 'cr', 'go', 'Review PBI-001', 1, 'GO')
        results = {'s1': exported(mine), 'theirs': exported(run('t1', 'cr', 'go', 'Review PBI-002', 2, 'GO')),
                   'loose': exported(run('u1', 'cr', 'go', 'Review PBI-003', 3, 'GO')),
                   'twice': exported(run('w1', 'cr', 'go', 'Review PBI-004', 4, 'GO'))}
        # "twice" is listed under this project and an earlier one; "gone" is linked but was not exported.
        project_of = {'s1': 'app', 'theirs': 'other', 'twice': 'first', 'gone': 'app'}
        counts = dict.fromkeys(results, 1)
        doc = derive.project_doc(project(sessions=('s1', 'twice', 'gone')), 0, results, counts, counts, project_of)
        self.assertEqual(list(doc['workItems']), ['PBI-001'])
        self.assertEqual(doc['workItems']['PBI-001']['runs'], ['m1'])
        first = derive.project_doc(project('first', sessions=('twice',)), 0, results, counts, counts, project_of)
        self.assertEqual(list(first['workItems']), ['PBI-004'])

    def test_project_doc_always_writes_the_three_keys(self):
        doc = derive.project_doc(project(sessions=()), 0, {}, {}, {}, {})
        self.assertEqual((doc['workItems'], doc['unattributedRounds'], doc['workItemStatus']), ({}, 0, 'shadow'))
        hand_built = {k: v for k, v in project().items()}
        self.assertNotIn('workItemStatus', hand_built)
        doc = derive.project_doc(hand_built, 0, {'s1': exported(run('r', 'cr', 'go', 'Code review', 1, 'GO'))}, {'s1': 1}, {'s1': 0}, {'s1': 'app'})
        self.assertEqual((doc['workItems'], doc['unattributedRounds'], doc['workItemStatus']), ({}, 1, 'shadow'))

    def test_project_doc_passes_work_item_status_through(self):
        self.assertEqual(derive.project_doc(project(workItemStatus='derived'), 0, {}, {}, {}, {})['workItemStatus'], 'derived')
        self.assertEqual(derive.project_doc(project(workItemStatus='shadow'), 0, {}, {}, {}, {})['workItemStatus'], 'shadow')

    def test_a_project_doc_with_work_items_is_a_valid_local_record(self):
        spec = importlib.util.spec_from_file_location('local_records', os.path.join(HERE, 'local', 'records.py'))
        records = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(records)
        results = {'s1': exported(*stale_rows(), last=stale_ts(24))}
        doc = derive.project_doc(project('dispatch-board'), 1, results, {'s1': len(STALE_2026_09_12)}, {'s1': 0}, {'s1': 'dispatch-board'})
        self.assertEqual(len(doc['workItems']), 7)
        self.assertEqual(records.validate('project', doc), [])
        self.assertEqual(records.from_row('project', records.to_row('project', 'dispatch-board', doc)), doc)


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


class Git(unittest.TestCase):
    """The git tab's derivation: the arithmetic over captured git output, with no subprocess anywhere near it."""

    LOG = ('a1b2c3d|2026-09-10T10:00:00+01:00|Add the widget\n'
           'e4f5a6b|2026-09-09T09:00:00+01:00|Split a|b on the first pipe only')
    FILES = 'README.md\nsite/index.html\nsite/app.js\nexporters/derive.py'
    STATUS = ' M site/app.js\n\n?? notes.txt'
    REMOTES = 'origin\thttps://user:token@github.com/owner/repo.git (fetch)\n\norigin\tgit@github.com:owner/repo.git (push)'

    def doc(self, **over):
        args = dict(root='C:\\work\\app', branch='main', default='master', log=self.LOG, files=self.FILES,
                    status=self.STATUS, remotes_raw=self.REMOTES, head='a1b2c3d', ahead_out='3',
                    shortstat_out=' 2 files changed, 9 insertions(+)', now='NOW')
        args.update(over)
        return derive.git_doc(**args)

    def test_the_document_is_derived_from_the_captured_output(self):
        d = self.doc()
        self.assertEqual(d['source'], 'git, local repository')
        self.assertEqual(d['repoPath'], 'C:/work/app')
        self.assertEqual(d['byDir'], {'(root)': 1, 'site': 2, 'exporters': 1})
        self.assertEqual(d['tracked'], 4)
        self.assertEqual(d['dirty'], [' M site/app.js', '?? notes.txt'])
        self.assertEqual(d['commits'], [
            {'sha': 'a1b2c3d', 'date': '2026-09-10T10:00:00+01:00', 'subject': 'Add the widget'},
            {'sha': 'e4f5a6b', 'date': '2026-09-09T09:00:00+01:00', 'subject': 'Split a|b on the first pipe only'}])
        self.assertEqual(d['remotes'], ['origin\thttps://github.com/owner/repo.git (fetch)',
                                        'origin\tgit@github.com:owner/repo.git (push)'])
        self.assertEqual((d['branch'], d['defaultBranch'], d['head'], d['generatedAt']), ('main', 'master', 'a1b2c3d', 'NOW'))

    def test_ahead_and_shortstat_are_empty_without_both_branches(self):
        for over in ({'default': ''}, {'branch': ''}, {'default': '', 'branch': ''}):
            with self.subTest(**over):
                d = self.doc(**over)
                self.assertEqual((d['ahead'], d['shortstat']), ('', ''))

    def test_ahead_and_shortstat_pass_through_with_both_branches(self):
        d = self.doc()
        self.assertEqual((d['ahead'], d['shortstat']), ('3', ' 2 files changed, 9 insertions(+)'))

    def test_an_empty_repository_derives_empty_lists_and_counts(self):
        d = self.doc(log='', files='', status='', remotes_raw='', head='')
        self.assertEqual((d['commits'], d['tracked'], d['byDir'], d['dirty'], d['remotes']), ([], 0, {}, [], []))

    def test_git_default_prefers_master_over_main(self):
        self.assertEqual(derive.git_default('deadbee', ''), 'master')
        self.assertEqual(derive.git_default('', 'deadbee'), 'main')
        self.assertEqual(derive.git_default('', ''), '')
        self.assertEqual(derive.git_default('deadbee', 'cafebab'), 'master')

    def test_public_remote_strips_userinfo_and_leaves_the_scp_form_alone(self):
        self.assertEqual(derive.public_remote('origin\thttps://u:t@github.com/o/r.git (fetch)'),
                         'origin\thttps://github.com/o/r.git (fetch)')
        self.assertEqual(derive.public_remote('origin\tgit@github.com:o/r.git (push)'),
                         'origin\tgit@github.com:o/r.git (push)')

    def test_derive_still_runs_no_subprocess(self):
        # derive's contract is that it reads no file, config, git or network; the git tab's I/O stays in its callers.
        self.assertFalse(hasattr(derive, 'subprocess'))


def said(minute, mid, text, stop=None):
    """A final assistant reply carrying text, with its stop_reason."""
    o = assistant(minute, mid, text=text)
    o['message']['stop_reason'] = stop
    return o


def ask(minute, tid, *questions):
    return assistant(minute, 'm-ask-' + tid, tools=[{'type': 'tool_use', 'id': tid, 'name': 'AskUserQuestion',
                                                     'input': {'questions': [{'question': q} for q in questions]}}])


def call(minute, tid, name='Bash'):
    return assistant(minute, 'm-call-' + tid, tools=[{'type': 'tool_use', 'id': tid, 'name': name, 'input': {'command': 'ls'}}])


def result(minute, tid, text='ok', is_error=False):
    return user(minute, [{'type': 'tool_result', 'tool_use_id': tid, 'is_error': is_error, 'content': text}])


def denial(minute, tid, kind, detail='Permission to use Bash has been denied.'):
    # The recorded shape: a user record, isMeta absent, whose toolUseResult is a plain string, not a dict.
    return user(minute, [{'type': 'tool_result', 'tool_use_id': tid, 'is_error': True, 'content': detail}],
                toolDenialKind=kind, toolUseResult='Error: ' + detail, sourceToolAssistantUUID='uuid-' + tid)


def waiting(records):
    return derive.waiting_of(feed(records))


class Waiting(unittest.TestCase):
    """What a session's main transcript leaves waiting on the owner: an unanswered AskUserQuestion, a closing
    question in prose, and tool calls the permission check refused."""

    def test_an_unanswered_ask_is_a_question_waiting(self):
        got = waiting([user(0, 'go'), ask(1, 'q1', 'Which colour?')])
        self.assertEqual(got, {'questions': [{'at': ts(1), 'question': 'Which colour?', 'source': 'ask'}], 'refusals': []})

    def test_an_answered_ask_is_not_waiting(self):
        self.assertIsNone(waiting([user(0, 'go'), ask(1, 'q1', 'Which colour?'), result(2, 'q1', 'Blue')]))

    def test_an_owner_message_after_an_ask_clears_it(self):
        self.assertIsNone(waiting([user(0, 'go'), ask(1, 'q1', 'Which colour?'), user(3, 'blue, and carry on')]))

    def test_only_the_latest_pending_ask_is_listed(self):
        got = waiting([user(0, 'go'), ask(1, 'q1', 'First?'), ask(2, 'q2', 'Second?', 'Third?')])
        self.assertEqual(got['questions'], [{'at': ts(2), 'question': 'Second? · Third?', 'source': 'ask'}])

    def test_an_owner_message_clears_only_the_ask_before_it(self):
        # The owner spoke between the two asks: the first is answered by their presence, the second is not.
        got = waiting([user(0, 'go'), ask(1, 'q1', 'First?'), user(2, 'noted'), ask(3, 'q2', 'Second?')])
        self.assertEqual(got['questions'], [{'at': ts(3), 'question': 'Second?', 'source': 'ask'}])

    def test_is_owner_message(self):
        own = derive.is_owner_message
        self.assertTrue(own(user(0, 'Please build it')))
        self.assertFalse(own(user(0, 'Please build it', isMeta=True)))
        self.assertFalse(own(user(0, '<command-message>pbi-plan</command-message>')))
        self.assertFalse(own(user(0, '<system-reminder>x</system-reminder>')))
        self.assertFalse(own(result(0, 't1')))
        self.assertFalse(own(assistant(0, 'm', text='hello')))
        # A reply typed beside a pasted image arrives as list content.
        self.assertTrue(own(user(0, [{'type': 'image', 'source': {}}, {'type': 'text', 'text': 'this one'}])))
        self.assertFalse(own(user(0, [{'type': 'text', 'text': '<system-reminder>x</system-reminder>'}])))
        self.assertFalse(own(user(0, [{'type': 'text', 'text': 'why'}, {'type': 'tool_result', 'tool_use_id': 't'}])))
        self.assertFalse(own(user(0, 'Summary of the conversation so far...', isCompactSummary=True)))
        self.assertFalse(own(user(0, [{'type': 'text', 'text': '[Request interrupted by user for tool use]'}])))
        # The exclusion matches the fixed marker text exactly; a longer typed reply that merely mentions it is still the owner.
        self.assertTrue(own(user(0, "I saw '[Request interrupted by user for tool use]' but go ahead and retry")))

    def test_a_closing_question_in_prose_is_waiting_until_the_owner_replies(self):
        text = 'I finished the parser.\n\nWhich would you prefer, the flag or the config key?'
        got = waiting([user(0, 'go'), said(1, 'm1', text, 'end_turn')])
        self.assertEqual(got['questions'], [{'at': ts(1), 'question': 'Which would you prefer, the flag or the config key?',
                                             'source': 'prose'}])
        self.assertIsNone(waiting([user(0, 'go'), said(1, 'm1', text, 'end_turn'), user(2, 'the flag')]))

    def test_a_closing_solicitation_without_a_question_mark_is_waiting(self):
        got = waiting([user(0, 'go'), said(1, 'm1', 'Tests are green.\n\nSay the word if you would rather I delete it.')])
        self.assertEqual(got['questions'][0]['source'], 'prose')

    def test_a_question_mark_before_the_closing_paragraph_is_not_waiting(self):
        self.assertIsNone(waiting([user(0, 'go'), said(1, 'm1', 'Why did it fail? The cache was stale.\n\nFixed and pushed.')]))

    def test_a_reply_cut_off_mid_tool_call_is_not_a_question(self):
        self.assertIsNone(waiting([user(0, 'go'), said(1, 'm1', 'Shall I run the suite?', 'tool_use')]))

    def test_the_last_turn_ignores_bookkeeping_records(self):
        got = waiting([user(0, 'go'), said(1, 'm1', 'Want me to open the PR?'),
                       {'type': 'attachment', 'timestamp': ts(2), 'attachment': {}}, {'type': 'last-prompt', 'lastPrompt': 'go'}])
        self.assertEqual(got['questions'][0]['question'], 'Want me to open the PR?')

    def test_a_streamed_reply_keeps_its_text_across_its_lines(self):
        tail = assistant(2, 'm1', tools=[])  # the same message's next line, carrying no text
        got = waiting([user(0, 'go'), said(1, 'm1', 'Shall I merge it?'), tail])
        self.assertEqual(got['questions'][0]['question'], 'Shall I merge it?')

    def test_listed_refusals_name_the_refused_tool(self):
        for kind in ('permission-rule', 'automode-blocked', 'user-rejected'):
            got = waiting([user(0, 'go'), call(1, 't1', 'Bash'), denial(2, 't1', kind)])
            self.assertEqual(got['refusals'], [{'at': ts(2), 'kind': kind, 'tool': 'Bash',
                                                'detail': 'Permission to use Bash has been denied.'}], kind)

    def test_a_classifier_outage_is_not_a_refusal(self):
        self.assertIsNone(waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'automode-unavailable')]))

    def test_a_refusal_whose_tool_cannot_be_resolved_still_lists(self):
        got = waiting([user(0, 'go'), denial(2, 'unknown', 'permission-rule')])
        self.assertEqual(got['refusals'][0]['tool'], None)

    def test_a_string_tool_use_result_is_read_without_raising(self):
        state = feed([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'user-rejected')])
        self.assertEqual(state['sync'], {})
        self.assertEqual(len(state['denials']), 1)

    def test_an_owner_message_after_a_refusal_clears_it(self):
        self.assertIsNone(waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'permission-rule'), user(3, 'fine, skip it')]))

    def test_a_user_rejected_denial_still_lists_past_the_interruption_marker_that_follows_it(self):
        # Claude Code writes this exact marker a moment after the owner rejects a tool-use prompt; it is not typed.
        marker = user(3, [{'type': 'text', 'text': '[Request interrupted by user for tool use]'}])
        got = waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'user-rejected'), marker])
        self.assertEqual(got['refusals'], [{'at': ts(2), 'kind': 'user-rejected', 'tool': 'Bash',
                                            'detail': 'Permission to use Bash has been denied.'}])

    def test_an_automode_blocked_denial_still_lists_past_a_compaction_summary(self):
        summary = user(3, 'Summary of the conversation so far...', isCompactSummary=True)
        got = waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'automode-blocked'), summary])
        self.assertEqual(got['refusals'], [{'at': ts(2), 'kind': 'automode-blocked', 'tool': 'Bash',
                                            'detail': 'Permission to use Bash has been denied.'}])

    def test_a_typed_reply_after_the_interruption_marker_or_a_compaction_summary_still_clears(self):
        marker = user(2, [{'type': 'text', 'text': '[Request interrupted by user for tool use]'}])
        self.assertIsNone(waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'user-rejected'), marker, user(3, 'fine, skip it')]))
        summary = user(3, 'Summary of the conversation so far...', isCompactSummary=True)
        self.assertIsNone(waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'automode-blocked'), summary, user(4, 'fine, skip it')]))

    def test_an_esc_interruption_with_no_refusal_creates_no_item(self):
        self.assertIsNone(waiting([user(0, 'go'), user(1, [{'type': 'text', 'text': '[Request interrupted by user]'}])]))

    def test_an_owner_message_clears_only_the_refusal_before_it(self):
        # The owner spoke between the two refusals: the first is stale, the second still stands.
        got = waiting([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'permission-rule'), user(3, 'fine, skip it'),
                       call(4, 't2'), denial(5, 't2', 'automode-blocked')])
        self.assertEqual(got['refusals'], [{'at': ts(5), 'kind': 'automode-blocked', 'tool': 'Bash', 'detail': 'Permission to use Bash has been denied.'}])

    def test_ordinary_tool_failures_and_permission_boilerplate_are_not_refusals(self):
        recs = [user(0, 'go'), said(1, 'm0', 'Skills need permission to use tools.')]
        for i in range(20):
            recs += [call(2, 'f%d' % i), result(3, 'f%d' % i, 'exit 1: permission to use this path was denied', True)]
        recs.append(said(4, 'm9', 'All done.'))
        self.assertIsNone(waiting(recs))

    def test_a_session_lists_at_most_five_items_and_counts_the_rest(self):
        recs = [user(0, 'go')]
        for i in range(6):
            recs += [call(1 + i, 't%d' % i), denial(1 + i, 't%d' % i, 'automode-blocked')]
        got = waiting(recs)
        self.assertEqual((len(got['refusals']), got['more']), (5, 1))
        self.assertEqual([r['at'] for r in got['refusals']], [ts(i) for i in range(2, 7)], 'the newest five are kept')

    def test_the_cap_keeps_the_question(self):
        recs = [user(0, 'go'), ask(1, 'q1', 'Which colour?')]
        for i in range(6):
            recs += [call(2 + i, 't%d' % i), denial(2 + i, 't%d' % i, 'automode-blocked')]
        got = waiting(recs)
        self.assertEqual((len(got['questions']), len(got['refusals']), got['more']), (1, 4, 2))

    def test_a_structured_ask_wins_over_prose(self):
        got = waiting([user(0, 'go'), ask(1, 'q1', 'Which colour?'), said(2, 'm2', 'Shall I pick for you?')])
        self.assertEqual([q['source'] for q in got['questions']], ['ask'])

    def test_a_session_with_nothing_waiting_has_no_waiting_key(self):
        doc = derive.session_result(feed(MAIN), [], [], [])['doc']
        self.assertNotIn('waiting', doc)

    def test_the_session_document_carries_a_copy_of_waiting(self):
        state = feed([user(0, 'go'), call(1, 't1'), denial(2, 't1', 'permission-rule')])
        doc = derive.session_result(state, [], [], [])['doc']
        kept = copy.deepcopy(doc['waiting'])
        derive.add_record(state, call(3, 't2'))
        derive.add_record(state, denial(4, 't2', 'permission-rule'))
        self.assertEqual(doc['waiting'], kept)

    def test_new_session_gains_only_the_waiting_keys(self):
        self.assertEqual(set(derive.new_session('s')), {
            'sid', 'title', 'aiTitle', 'cwd', 'first', 'start', 'last', 'by', 'rejects', 'launched', 'stopped', 'notes',
            'sync', 'uses', 'skillCalls', 'tools', 'asks', 'answered', 'denials', 'lastOwnerAt', 'lastTurn'})

    def test_a_list_content_opener_is_an_owner_message_but_not_the_first_prompt(self):
        opener = user(0, [{'type': 'image', 'source': {}}, {'type': 'text', 'text': 'look at this'}])
        self.assertTrue(derive.is_owner_message(opener))
        self.assertIsNone(feed([opener])['first'])
        self.assertEqual(feed([opener, user(1, 'then build it')])['first'], 'then build it')


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
