"""Tests for exporters/export_board.py and the project list in exporters/board_config.py, run against
synthetic repositories in a temporary directory.

Every export test passes its own config, data folder and out dir, so none of them reads board.config.json
or writes the repo's out/. Two tests read committed files on purpose: the repo's board.config.json and its
projects/*.json data files, to check they have the shape the exporters expect. The exporter's gh calls go to an
injected runner: the default one fails the test, so no test can reach the real gh or the network.
"""
import ast, contextlib, glob, io, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
import board_config as bc  # noqa: E402
import derive  # noqa: E402
import export_board as eb  # noqa: E402

HAS_GIT = shutil.which('git') is not None
NOW = '2026-09-11T00:00:00+00:00'
# Later run times, for the keep-last tests: carriedSince is the run time in UTC, written with a Z.
NOW_Z, CARRIED, CARRIED_Z, LATEST = '2026-09-11T00:00:00Z', '2026-09-11T08:30:00+00:00', '2026-09-11T08:30:00Z', '2026-09-12T09:00:00+00:00'

SPEC = """---
revision: 4
---
# App: solution spec

**Rows the human must confirm or correct at the plan gate:** 2, 3 (and explicitly AC-3). Everything else is settled.

- **G-1** Ship the `widget`.
- **G-2** Keep it **small**.

### In scope
- Widgets

### Out of scope
- Gadgets

## Assumptions & open questions

| # | Question | Resolution | Status | Source | Impact |
|---|---|---|---|---|---|
| 1 | Where does the data live? | JSON | RESOLVED | PRD | Low - one file |
| 2 | Who owns an entry? | The team | **ASSUMED** | brief | Medium - rework |
| 3 | Search? | In the client | ASSUMED | brief | High - rewrite |

## Key decisions

| Decision | Rationale | Made by | Date |
|---|---|---|---|
| Use JSON | simple | owner | 2026-09-01 |

## Backlog

### PBI list (proposed)

| ID | Title | Depends on | Group | Risk | Requires spec | Notes |
|---|---|---|---|---|---|---|
| PBI-001 | Widget | — | core | Low | no | x |
| PBI-002 | Gadget | PBI-001 | core | Low | no | y |
"""
PRD = "- **FR-1** a\n- **FR-2** b\n- **NFR-1** c\n- **C-1** d\n- **AC-1** e\n| **A-1** | f |\n"
BRIEF = "# Brief\n\n## Why this is not just a content site\n\n1. **Eligibility.** text\n2. **Cost.** text\n"
ADR = "---\nid: ADR-0001\ntitle: Data in JSON\nstatus: proposed\nresolves: row 1\n---\n\nBody.\n"
REVIEW = "# Plan gate review\n\n**Verdict:** **GO**\n"
DATA = {
    'buildState': {'PBI-001': {'state': 'done', 'review': 'GO', 'open': '', 'commit': 'abc1234'}},
    'notWorkedOut': [{'item': 'Where the data lives', 'row': 1, 'adr': 'ADR-0001'}],
    'boardNote': 'Nothing is on the BOARD yet.',
}
FULL = {'docs/backlog/specs/app.md': SPEC, 'docs/prd/app.md': PRD, 'docs/brief/raw-notes.md': BRIEF,
        'docs/adr/0001-data.md': ADR, 'docs/backlog/reviews/app/plan-gate-review-r1.md': REVIEW}
FUTURE = """### Future iterations (not planned)

Ideas for after this iteration. They are not PBIs.

- **Phone notifications**: a review returns NO-GO (see [ADR-0002](docs/adr/0002-push.md)).
- **Hosting**: Static Web Apps: Functions and `Entra ID`.
- **Archive:** keep sessions older than 7 days.
- A plain idea with no bold span
- **Wrapped idea**: the first line
  and its continuation.
- Maybe **later still**: words before the bold span.
-

### Allowed and blocked areas (per PBI)

- **Not an idea**: this bullet belongs to the next section.
"""
LATER = [
    {'title': 'Phone notifications', 'description': 'a review returns NO-GO (see ADR-0002).'},
    {'title': 'Hosting', 'description': 'Static Web Apps: Functions and `Entra ID`.'},
    {'title': 'Archive', 'description': 'keep sessions older than 7 days.'},
    {'title': 'A plain idea with no bold span', 'description': ''},
    {'title': 'Wrapped idea', 'description': 'the first line and its continuation.'},
    {'title': 'later still', 'description': 'Maybe **later still**: words before the bold span.'},
]
DOCS = {'prd': 'docs/prd/app.md', 'spec': 'docs/backlog/specs/app.md', 'brief': 'docs/brief/raw-notes.md',
        'adrDir': 'docs/adr', 'board': 'docs/backlog/BOARD.md',
        'reviews': [{'gate': 'Plan gate', 'path': 'docs/backlog/reviews/app/plan-gate-review-r{round}.md'}]}


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.invalid',
               GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.invalid')
    subprocess.run(['git', '-c', 'init.defaultBranch=main', '-c', 'commit.gpgsign=false', *args],
                   cwd=cwd, env=env, check=True, capture_output=True)


def project(pid, root, **over):
    p = {'id': pid, 'name': pid, 'repoPath': root, 'branch': 'main', 'sessions': [], 'docs': dict(DOCS)}
    p.update(over)
    return p


def refuse_gh(cmd, **kwargs):
    raise AssertionError('the export ran %r without a fake gh' % (cmd,))


class FakeGh:
    """Stands in for subprocess.run when the exporter calls gh: records each call, then raises or answers."""

    def __init__(self, stdout='', returncode=0, stderr='', raises=None):
        self.stdout, self.returncode, self.stderr, self.raises = stdout, returncode, stderr, raises
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if self.raises:
            raise self.raises
        return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, self.stderr)


class Repos:
    """Throwaway repositories, a data folder and an out dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.out = os.path.join(self.tmp, 'out')
        self.data_dir = os.path.join(self.tmp, 'data')
        os.makedirs(self.data_dir)
        self.err = ''
        self.gh = refuse_gh

    def repo(self, name, files, with_git=True):
        root = os.path.join(self.tmp, name)
        for rel, text in files.items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
        os.makedirs(root, exist_ok=True)
        if with_git and HAS_GIT:
            git(root, 'init')
            if files:
                git(root, 'add', '-A')
                git(root, 'commit', '-m', 'first')
        return root

    def data(self, pid, obj):
        with io.open(os.path.join(self.data_dir, pid + '.json'), 'w', encoding='utf-8') as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))

    def run(self, projects, now=NOW):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = eb.main(config={'projects': projects}, out_dir=self.out, data_dir=self.data_dir, now=now, run=self.gh)
        self.err = err.getvalue()
        return code

    def tabs(self):
        found = {}
        for f in glob.glob(os.path.join(self.out, 'projectTabs', '*.json')):
            with io.open(f, encoding='utf-8') as fh:
                found[os.path.basename(f)[:-5]] = json.load(fh)
        return found


class ReposCase(unittest.TestCase):
    def setUp(self):
        self.r = Repos()
        self.addCleanup(shutil.rmtree, self.r.tmp, True)


# ---------------------------------------------------------------- one project's tabs

class ExportProject(ReposCase):
    def test_every_tab_is_written_under_the_project_id(self):
        root = self.r.repo('app', FULL)
        self.r.data('app', DATA)
        self.assertEqual(self.r.run([project('app', root)]), 0)
        expected = {'app.spec', 'app.assumptions', 'app.decisions', 'app.backlog'} | ({'app.git'} if HAS_GIT else set())
        self.assertEqual(set(self.r.tabs()), expected)

    def test_build_state_and_open_questions_come_from_the_data_file(self):
        root = self.r.repo('app', FULL)
        self.r.data('app', DATA)
        self.r.run([project('app', root)])
        t = self.r.tabs()
        pbis = {p['id']: p for p in t['app.backlog']['pbis']}
        self.assertEqual((pbis['PBI-001']['state'], pbis['PBI-001']['review'], pbis['PBI-001']['commit']), ('done', 'GO', 'abc1234'))
        self.assertEqual((pbis['PBI-002']['state'], pbis['PBI-002']['review']), ('todo', '—'))
        self.assertEqual(t['app.backlog']['board'], 'Nothing is on the BOARD yet.')
        self.assertIn('projects/app.json', t['app.backlog']['source'])
        self.assertEqual(t['app.decisions']['notWorkedOut'], [
            {'item': 'Where the data lives', 'row': 1, 'adr': 'ADR-0001', 'landed': 'JSON', 'status': 'RESOLVED', 'needsYou': False}])

    def test_spec_assumptions_and_decisions_are_read_from_the_docs(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        t = self.r.tabs()
        self.assertEqual(t['app.assumptions']['humanList'], [2, 3])
        self.assertEqual([r['needsYou'] for r in t['app.assumptions']['rows']], [False, True, True])
        self.assertEqual(t['app.spec']['revision'], '4')
        self.assertEqual(t['app.spec']['prd']['frs'], 2)
        self.assertEqual(t['app.spec']['logicCore'], ['Eligibility.', 'Cost.'])
        self.assertEqual(t['app.spec']['rounds'], [{'gate': 'Plan gate', 'round': 1, 'verdict': 'GO'}])
        self.assertEqual([a['id'] for a in t['app.decisions']['adrs']], ['ADR-0001'])
        self.assertEqual(t['app.decisions']['adrs'][0]['path'], 'docs/adr/0001-data.md')
        self.assertEqual(len(t['app.decisions']['decisions']), 1)
        self.assertEqual(t['app.spec']['generatedAt'], NOW)

    @unittest.skipUnless(HAS_GIT, 'git is not installed')
    def test_git_tab(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        g = self.r.tabs()['app.git']
        self.assertEqual((g['branch'], len(g['commits']), g['repoPath']), ('main', 1, root.replace('\\', '/')))

    def test_missing_data_file_means_no_build_state(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        t = self.r.tabs()
        self.assertEqual({p['state'] for p in t['app.backlog']['pbis']}, {'todo'})
        self.assertEqual(t['app.decisions']['notWorkedOut'], [])
        self.assertEqual(t['app.backlog']['board'], '')

    def test_malformed_data_file_stops_the_export_and_keeps_the_last_one(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        self.r.data('app', '{"buildState": {')
        self.assertNotEqual(self.r.run([project('app', root)]), 0)
        self.assertIn('app.json', self.r.err)
        self.assertIn('app.backlog', self.r.tabs())

    def test_spec_without_the_human_rows_line(self):
        root = self.r.repo('app', dict(FULL, **{'docs/backlog/specs/app.md': SPEC.replace('**Rows the human', 'Rows nobody')}))
        self.assertEqual(self.r.run([project('app', root)]), 0)
        self.assertEqual(self.r.tabs()['app.assumptions']['humanList'], [])


# ---------------------------------------------------------------- future iterations (the Backlog's Later group)

class FutureIterations(ReposCase):
    def export(self, spec):
        root = self.r.repo('app', dict(FULL, **{'docs/backlog/specs/app.md': spec}))
        self.assertEqual(self.r.run([project('app', root)]), 0)
        return self.r.tabs()['app.backlog']

    def test_each_bullet_under_the_heading_is_a_later_item(self):
        b = self.export(SPEC + '\n' + FUTURE)
        self.assertEqual(b['later'], LATER)
        self.assertEqual([p['id'] for p in b['pbis']], ['PBI-001', 'PBI-002'])

    def test_spec_without_the_heading_has_no_later_items_and_no_error(self):
        b = self.export(SPEC)
        self.assertEqual(b['later'], [])
        self.assertEqual(self.r.err, '')

    def test_crlf_line_endings(self):
        crlf = (SPEC + '\n' + FUTURE).replace('\n', '\r\n')
        self.assertEqual(eb.later_items(crlf), LATER)
        self.assertEqual(self.export(crlf)['later'], LATER)

    def test_the_section_ends_at_the_next_heading_of_its_level_or_higher(self):
        for nxt in ('### Allowed and blocked areas', '## Assumptions', '# Appendix'):
            spec = '### Future iterations (not planned)\n\n- **Idea**: kept.\n\n%s\n\n- **Not an idea**: next section.\n' % nxt
            self.assertEqual(eb.later_items(spec), [{'title': 'Idea', 'description': 'kept.'}], nxt)

    def test_a_sub_heading_inside_the_section_does_not_end_it(self):
        spec = '### Future iterations (not planned)\n\n- **A**: one.\n\n#### Further out\n\n- **B**: two.\n\n### Next\n\n- **C**: no.\n'
        self.assertEqual([x['title'] for x in eb.later_items(spec)], ['A', 'B'])

    def test_heading_at_the_end_of_the_file(self):
        self.assertEqual(eb.later_items(SPEC + '\n### Future iterations (not planned)\n- **Last**: no final newline'),
                         [{'title': 'Last', 'description': 'no final newline'}])

    def test_heading_without_bullets(self):
        self.assertEqual(eb.later_items('### Future iterations (not planned)\n\nNothing yet.\n\n## Next\n- x\n'), [])

    def test_a_blank_bold_span_counts_as_no_bold_span(self):
        self.assertEqual(eb.later_items('### Future iterations (not planned)\n- ** **: idea\n'),
                         [{'title': '** **: idea', 'description': ''}])

    def test_every_markdown_list_marker_with_up_to_three_spaces_starts_an_idea(self):
        spec = ('### Future iterations (not planned)\n\n'
                '* **Star**: one.\n'
                '+ **Plus**: two.\n'
                '1. **Numbered**: three.\n'
                '12. **Two digits**: four.\n'
                '   - **Indented three**: five.\n'
                ' * **Indented one**: six.\n')
        self.assertEqual(eb.later_items(spec), [
            {'title': 'Star', 'description': 'one.'}, {'title': 'Plus', 'description': 'two.'},
            {'title': 'Numbered', 'description': 'three.'}, {'title': 'Two digits', 'description': 'four.'},
            {'title': 'Indented three', 'description': 'five.'}, {'title': 'Indented one', 'description': 'six.'}])

    def test_deeper_indented_list_lines_are_nested_items_kept_in_their_ideas_description(self):
        spec = ('### Future iterations (not planned)\n\n'
                '- **Parent**: the idea\n'
                '  wrapped onto a second line.\n'
                '    - a nested point\n'
                '      that wraps\n'
                '    1. a numbered nested point\n'
                '\t* a tab-indented nested point\n'
                '- **Next**: another idea.\n')
        self.assertEqual(eb.later_items(spec), [
            {'title': 'Parent', 'description': 'the idea wrapped onto a second line. - a nested point that wraps '
                                               '1. a numbered nested point * a tab-indented nested point'},
            {'title': 'Next', 'description': 'another idea.'}])
        # A line indented less than a nested item, after one, still continues the idea.
        self.assertEqual(eb.later_items('### Future iterations (not planned)\n- **A**: one\n    - nested\n  back to A?\n'),
                         [{'title': 'A', 'description': 'one - nested back to A?'}])

    def test_an_indented_line_after_a_blank_line_stays_in_its_idea(self):
        spec = ('### Future iterations (not planned)\n\n'
                '- **A**: one\n'
                '    - nested\n'
                '\n'
                '    - after blank\n'
                '\n'
                '    more under A after a blank\n'
                '- **B**: two\n')
        self.assertEqual(eb.later_items(spec), [
            {'title': 'A', 'description': 'one - nested - after blank more under A after a blank'},
            {'title': 'B', 'description': 'two'}])

    def test_a_blank_line_then_an_unindented_line_that_starts_no_idea_ends_the_idea(self):
        spec = ('### Future iterations (not planned)\n\n'
                '- **A**: one\n\n'
                'A closing paragraph about the list.\n\n'
                '    indented under that paragraph, not A\n'
                '- **B**: two\n')
        self.assertEqual(eb.later_items(spec), [{'title': 'A', 'description': 'one'}, {'title': 'B', 'description': 'two'}])

    def test_a_thematic_break_is_not_an_idea(self):
        spec = '### Future iterations (not planned)\n\n- **A**: one.\n\n* * *\n\n- - -\n\n- **B**: two.\n'
        self.assertEqual([x['title'] for x in eb.later_items(spec)], ['A', 'B'])

    def test_bold_text_at_the_start_of_a_line_is_not_a_marker(self):
        spec = '### Future iterations (not planned)\n\n- **A**: one\n**still A**.\n'
        self.assertEqual(eb.later_items(spec), [{'title': 'A', 'description': 'one **still A**.'}])


# ---------------------------------------------------------------- missing sources

class MissingSources(ReposCase):
    def test_missing_spec_board_and_adrs_write_no_spec_tabs(self):
        root = self.r.repo('bare', {'docs/brief/raw-notes.md': BRIEF, 'docs/prd/app.md': PRD})
        self.assertEqual(self.r.run([project('bare', root)]), 0)
        self.assertEqual(set(self.r.tabs()), {'bare.git'} if HAS_GIT else set())

    def test_missing_prd_and_adr_folder_are_tolerated(self):
        root = self.r.repo('app', {'docs/backlog/specs/app.md': SPEC})
        self.assertEqual(self.r.run([project('app', root)]), 0)
        t = self.r.tabs()
        self.assertIsNone(t['app.spec']['prd'])
        self.assertEqual(t['app.spec']['logicCore'], [])
        self.assertEqual(t['app.decisions']['adrs'], [])
        self.assertEqual(t['app.spec']['rounds'], [])

    def test_folder_that_is_not_a_git_repo_has_no_git_tab(self):
        root = self.r.repo('app', FULL, with_git=False)
        self.assertEqual(self.r.run([project('app', root)]), 0)
        self.assertNotIn('app.git', self.r.tabs())

    def test_missing_repo_is_skipped_with_a_warning(self):
        root = self.r.repo('app', FULL)
        code = self.r.run([project('ghost', os.path.join(self.r.tmp, 'nowhere')), project('app', root)])
        self.assertEqual(code, 0)
        self.assertIn('ghost', self.r.err)
        names = set(self.r.tabs())
        self.assertFalse(any(n.startswith('ghost.') for n in names))
        self.assertIn('app.spec', names)

    def test_missing_repo_keeps_its_last_tabs_while_others_refresh(self):
        a, b = self.r.repo('app', FULL), self.r.repo('other', FULL)
        self.assertEqual(self.r.run([project('app', a), project('other', b)]), 0)
        before = self.r.tabs()
        shutil.move(b, b + '-moved')
        with io.open(os.path.join(a, 'docs/backlog/specs/app.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(SPEC.replace('revision: 4', 'revision: 5'))
        self.assertEqual(self.r.run([project('app', a), project('other', b)]), 0)
        self.assertIn('other', self.r.err)
        after = self.r.tabs()
        self.assertEqual({k: v for k, v in after.items() if k.startswith('other.')},
                         {k: dict(v, carriedSince=NOW_Z) for k, v in before.items() if k.startswith('other.')})
        self.assertTrue(any(k.startswith('other.') for k in after))
        self.assertEqual(after['app.spec']['revision'], '5')

    def test_renamed_spec_keeps_the_tabs_built_from_it(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        before = self.r.tabs()
        os.rename(os.path.join(root, 'docs/backlog/specs/app.md'), os.path.join(root, 'docs/backlog/specs/renamed.md'))
        self.assertEqual(self.r.run([project('app', root)]), 0)
        self.assertIn('app', self.r.err)
        after = self.r.tabs()
        for tab in ('spec', 'assumptions', 'decisions', 'backlog'):
            self.assertEqual(after['app.' + tab], dict(before['app.' + tab], carriedSince=NOW_Z), tab)

    def test_a_kept_tab_is_marked_with_the_time_its_carry_began(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        before = self.r.tabs()
        self.assertEqual(self.r.run([project('app', os.path.join(self.r.tmp, 'nowhere'))], now=CARRIED), 0)
        self.assertIn('project app: cannot rebuild spec, assumptions, decisions, backlog', self.r.err)
        self.assertIn('keeping the last export', self.r.err)
        after = self.r.tabs()
        self.assertEqual(set(after), set(before))
        for name, body in before.items():
            self.assertEqual(after[name], dict(body, carriedSince=CARRIED_Z), name)

    def test_kept_tabs_are_byte_identical(self):
        # refresh.py diffs file contents: the first carry adds carriedSince, which is one change to push, and
        # every later run while the source is still missing must leave the kept file byte for byte as it was,
        # with its first carriedSince, so refresh.py plans no write for it.
        root, gone = self.r.repo('app', FULL), os.path.join(self.r.tmp, 'nowhere')
        folder = os.path.join(self.r.out, 'projectTabs')
        self.r.run([project('app', root)])
        original = {}
        for name in self.r.tabs():
            with io.open(os.path.join(folder, name + '.json'), 'rb') as f:
                original[name] = f.read()
        self.r.run([project('app', gone)], now=CARRIED)
        first = {}
        for name, raw in original.items():
            with io.open(os.path.join(folder, name + '.json'), 'rb') as f:
                first[name] = f.read()
            # A carried tab is written in the same format as a rebuilt one, so the marker line is the only difference.
            self.assertTrue(raw.endswith(b'\n}'), name)
            self.assertEqual(first[name], raw[:-2] + (',\n "carriedSince": "%s"\n}' % CARRIED_Z).encode('utf-8'), name)
        self.r.run([project('app', gone)], now=LATEST)
        self.assertEqual(sorted(os.listdir(folder)), sorted(n + '.json' for n in first))
        for name, raw in first.items():
            with io.open(os.path.join(folder, name + '.json'), 'rb') as f:
                self.assertEqual(f.read(), raw, name)

    def test_a_tab_whose_source_comes_back_is_rebuilt_without_carried_since(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        shutil.move(root, root + '-moved')
        self.r.run([project('app', root)], now=CARRIED)
        self.assertTrue(all('carriedSince' in body for body in self.r.tabs().values()))
        shutil.move(root + '-moved', root)
        self.assertEqual(self.r.run([project('app', root)], now=LATEST), 0)
        self.assertNotIn('cannot rebuild', self.r.err)
        after = self.r.tabs()
        self.assertIn('app.spec', after)
        for name, body in after.items():
            self.assertNotIn('carriedSince', body, name)
            self.assertEqual(body['generatedAt'], LATEST, name)

    def test_a_source_lost_again_after_recovery_starts_a_new_carry(self):
        root, again = self.r.repo('app', FULL), '2026-09-13T07:15:00+00:00'
        self.r.run([project('app', root)])
        shutil.move(root, root + '-moved')
        self.r.run([project('app', root)], now=CARRIED)
        shutil.move(root + '-moved', root)
        self.r.run([project('app', root)], now=LATEST)
        rebuilt = self.r.tabs()
        shutil.move(root, root + '-moved')
        self.assertEqual(self.r.run([project('app', root)], now=again), 0)
        after = self.r.tabs()
        self.assertIn('app.spec', rebuilt)
        self.assertEqual(set(after), set(rebuilt))
        for name, body in rebuilt.items():
            self.assertNotIn('carriedSince', body, name)
            self.assertEqual(after[name], dict(body, carriedSince='2026-09-13T07:15:00Z'), name)

    def test_carried_since_is_the_run_time_converted_to_utc(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        self.r.run([project('app', os.path.join(self.r.tmp, 'nowhere'))], now='2026-09-11T09:30:00+01:00')
        tabs = self.r.tabs()
        self.assertIn('app.spec', tabs)
        for name, body in tabs.items():
            self.assertEqual(body['carriedSince'], '2026-09-11T08:30:00Z', name)

    def test_a_tab_that_exports_normally_never_has_carried_since(self):
        a, b = self.r.repo('app', FULL), self.r.repo('other', FULL)
        self.r.run([project('app', a), project('other', b)])
        self.assertFalse([n for n, body in self.r.tabs().items() if 'carriedSince' in body])
        # Beside a carried project, and beside tabs of its own that are carried, a rebuilt tab stays unmarked.
        os.rename(os.path.join(a, 'docs/backlog/specs/app.md'), os.path.join(a, 'docs/backlog/specs/renamed.md'))
        shutil.move(b, b + '-moved')
        self.r.run([project('app', a), project('other', b)], now=CARRIED)
        spec_tabs = ('spec', 'assumptions', 'decisions', 'backlog')
        marked = {n for n, body in self.r.tabs().items() if 'carriedSince' in body}
        self.assertEqual(marked, {'app.' + t for t in spec_tabs} | {'other.' + t for t in spec_tabs} | (
            {'other.git'} if HAS_GIT else set()))
        if HAS_GIT:
            self.assertNotIn('carriedSince', self.r.tabs()['app.git'])

    def test_a_kept_file_that_is_not_a_json_object_is_kept_as_it_was(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        folder = os.path.join(self.r.out, 'projectTabs')
        odd = {'app.spec': b'{"truncated": ', 'app.backlog': b'[1, 2]', 'app.decisions': b'\xff\xfe not utf-8'}
        for name, raw in odd.items():
            with io.open(os.path.join(folder, name + '.json'), 'wb') as f:
                f.write(raw)
        self.assertEqual(self.r.run([project('app', os.path.join(self.r.tmp, 'nowhere'))], now=CARRIED), 0)
        for name, raw in odd.items():
            with io.open(os.path.join(folder, name + '.json'), 'rb') as f:
                self.assertEqual(f.read(), raw, name)
        with io.open(os.path.join(folder, 'app.assumptions.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['carriedSince'], CARRIED_Z)  # a readable kept tab beside them is still marked

    def test_a_kept_file_json_cannot_round_trip_is_kept_as_it_was_while_others_export(self):
        # Both are valid JSON text: 200000 levels of nesting exhaust the parser's recursion limit, and the escape
        # for U+D800 parses to a lone surrogate that UTF-8 cannot encode.
        a, b = self.r.repo('app', FULL), self.r.repo('other', FULL)
        self.r.run([project('app', a), project('other', b)])
        folder = os.path.join(self.r.out, 'projectTabs')
        odd = {'app.spec': b'{"deep": ' + b'[' * 200000 + b']' * 200000 + b'}', 'app.decisions': b'{"note": "\\ud800"}'}
        for name, raw in odd.items():
            with io.open(os.path.join(folder, name + '.json'), 'wb') as f:
                f.write(raw)
        gone = os.path.join(self.r.tmp, 'nowhere')
        self.assertEqual(self.r.run([project('app', gone), project('other', b)], now=CARRIED), 0)
        for name, raw in odd.items():
            with io.open(os.path.join(folder, name + '.json'), 'rb') as f:
                self.assertEqual(f.read(), raw, name)
            self.assertEqual(self.r.err.count(name + '.json'), 1, name)  # one warning naming the file left unmarked
        with io.open(os.path.join(folder, 'app.assumptions.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['carriedSince'], CARRIED_Z)
        with io.open(os.path.join(folder, 'other.spec.json'), encoding='utf-8') as f:
            healthy = json.load(f)
        self.assertEqual(healthy['generatedAt'], CARRIED)
        self.assertNotIn('carriedSince', healthy)

    def test_project_list_that_is_not_a_list_stops_the_export(self):
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        self.assertEqual(self.r.run({'app': project('app', root)}), 2)
        self.assertIn('app.spec', self.r.tabs())

    def test_project_dropped_from_the_config_loses_its_tabs(self):
        a, b = self.r.repo('app', FULL), self.r.repo('other', FULL)
        self.r.run([project('app', a), project('other', b)])
        self.assertIn('other.spec', self.r.tabs())
        self.r.run([project('app', a)])
        self.assertFalse(any(n.startswith('other.') for n in self.r.tabs()))

    def test_retired_tab_files_are_removed(self):
        root = self.r.repo('app', FULL)
        os.makedirs(self.r.out)
        legacy = os.path.join(self.r.out, 'spec.json')
        with io.open(legacy, 'w', encoding='utf-8') as f:
            f.write('{}')
        self.r.run([project('app', root)])
        self.assertFalse(os.path.exists(legacy))

    def test_a_document_outside_tabs_is_never_deleted_even_for_a_dropped_project(self):
        # projectTabs/<pid>.findings.json is export_sessions.py's document, not this exporter's: it must
        # survive a run of export_board.py on its own, whether the project is still configured or was dropped.
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        folder = os.path.join(self.r.out, 'projectTabs')
        for pid in ('app', 'other'):
            with io.open(os.path.join(folder, pid + '.findings.json'), 'w', encoding='utf-8') as f:
                f.write('{"items": {}}')
        self.assertEqual(self.r.run([project('app', root)]), 0)
        self.assertIn('app.findings', self.r.tabs())
        self.assertIn('other.findings', self.r.tabs())


# ---------------------------------------------------------------- pull requests, from a fake gh

GH_ARGS = ['gh', 'pr', 'list', '--state', 'all', '--search', 'sort:updated-desc', '--limit', '20',
           '--json', 'number,title,state,url,headRefName,updatedAt', '--repo', 'o/app']
GH_PRS = [  # as gh prints them; gh's own order is not by update
    {'number': 7, 'title': 'Older', 'state': 'MERGED', 'url': 'https://github.com/o/app/pull/7', 'headRefName': 'pbi/old',
     'updatedAt': '2026-09-01T10:00:00Z'},
    {'number': 9, 'title': 'Newest <b>“quoted”</b>', 'state': 'OPEN', 'url': 'https://github.com/o/app/pull/9',
     'headRefName': 'pbi/new', 'updatedAt': '2026-09-10T10:00:00Z', 'isDraft': False},
    {'number': 8, 'title': 'Dropped', 'state': 'CLOSED', 'url': 'https://github.com/o/app/pull/8', 'headRefName': 'pbi/gone',
     'updatedAt': '2026-09-05T10:00:00Z'},
]
PULLS = [
    {'number': 9, 'title': 'Newest <b>“quoted”</b>', 'state': 'OPEN', 'url': 'https://github.com/o/app/pull/9',
     'branch': 'pbi/new', 'updatedAt': '2026-09-10T10:00:00Z'},
    {'number': 8, 'title': 'Dropped', 'state': 'CLOSED', 'url': 'https://github.com/o/app/pull/8', 'branch': 'pbi/gone',
     'updatedAt': '2026-09-05T10:00:00Z'},
    {'number': 7, 'title': 'Older', 'state': 'MERGED', 'url': 'https://github.com/o/app/pull/7', 'branch': 'pbi/old',
     'updatedAt': '2026-09-01T10:00:00Z'},
]


@unittest.skipUnless(HAS_GIT, 'git is not installed')
class PullRequests(ReposCase):
    def export(self, gh, name='app', remotes=(('origin', 'https://github.com/o/app.git'),)):
        root = self.r.repo(name, FULL)
        for remote, url in remotes:
            git(root, 'remote', 'add', remote, url)
        self.r.gh = gh
        self.assertEqual(self.r.run([project(name, root)]), 0)
        return root, self.r.tabs()[name + '.git']

    def test_pulls_come_from_gh_in_the_repo_most_recently_updated_first(self):
        gh = FakeGh(json.dumps(GH_PRS))
        root, g = self.export(gh)
        [(cmd, kw)] = gh.calls
        self.assertEqual(cmd, GH_ARGS)
        self.assertEqual(os.path.normcase(os.path.abspath(kw['cwd'])), os.path.normcase(os.path.abspath(root)))
        self.assertLessEqual(kw['timeout'], 15)
        self.assertEqual(g['pulls'], PULLS)
        self.assertEqual(self.r.err, '')
        self.assertEqual((g['branch'], len(g['commits'])), ('main', 1))

    def test_no_pull_requests_is_an_empty_list(self):
        _, g = self.export(FakeGh('[]\n'))
        self.assertEqual(g['pulls'], [])
        self.assertEqual(self.r.err, '')

    def assert_left_out(self, gh, why, name='app'):
        _, g = self.export(gh, name)
        self.assertNotIn('pulls', g)
        self.assertIn('project %s: cannot list pull requests' % name, self.r.err)
        self.assertIn(why, self.r.err)
        self.assertEqual((g['branch'], len(g['commits']), len(g['remotes'])), ('main', 1, 2))
        self.assertNotIn('keeping the last export', self.r.err)

    def test_gh_missing(self):
        self.assert_left_out(FakeGh(raises=FileNotFoundError(2, 'No such file or directory', 'gh')), 'gh could not be run')

    def test_gh_exits_non_zero(self):
        self.assert_left_out(FakeGh(returncode=1, stderr='\nTo get started with GitHub CLI, please run:  gh auth login\n'),
                             'gh exited 1: To get started with GitHub CLI')

    def test_gh_times_out(self):
        self.assert_left_out(FakeGh(raises=subprocess.TimeoutExpired(GH_ARGS, 15)), 'did not finish within 15 s')

    def test_gh_prints_malformed_json(self):
        for i, out in enumerate(('not json', '', '{"number": 1}', '[1, 2]', '[{"number": 1}, null]')):
            with self.subTest(out=out):
                self.assert_left_out(FakeGh(out), 'malformed JSON', name='app%d' % i)

    def test_a_previous_export_does_not_keep_its_pulls_when_gh_fails(self):
        root, g = self.export(FakeGh(json.dumps(GH_PRS)))
        self.assertIn('pulls', g)
        self.r.gh = FakeGh(returncode=4, stderr='HTTP 502')
        self.assertEqual(self.r.run([project('app', root)]), 0)
        self.assertNotIn('pulls', self.r.tabs()['app.git'])

    def test_origin_not_on_github_gets_no_pulls_and_no_warning(self):
        for i, remotes in enumerate((
                (('origin', 'https://gitlab.com/o/app.git'),),
                (('origin', 'https://github.com.evil.example/o/app.git'),),
                (('origin', 'git@example.com:github.com/app.git'),),
                (('upstream', 'https://github.com/o/app.git'),),
                ())):
            with self.subTest(remotes=remotes):
                _, g = self.export(refuse_gh, name='app%d' % i, remotes=remotes)
                self.assertNotIn('pulls', g)
                self.assertEqual(self.r.err, '')


@unittest.skipUnless(HAS_GIT, 'git is not installed')
class Remotes(ReposCase):
    def test_credentials_in_a_remote_url_are_never_published(self):
        root = self.r.repo('app', FULL)
        urls = {'origin': ('https://jdk:ghp_TOPSECRET0123456789abcdef@github.com/o/app.git', 'https://github.com/o/app.git'),
                'mirror': ('https://x-access-token:ANOTHERSECRET@gitlab.com/o/app.git', 'https://gitlab.com/o/app.git'),
                'bare': ('https://ONLYTOKENSECRET@example.com/o/app.git', 'https://example.com/o/app.git'),
                'scp': ('git@github.com:o/app.git', 'git@github.com:o/app.git')}
        for name, (url, _) in urls.items():
            git(root, 'remote', 'add', name, url)
        self.r.gh = FakeGh('[]')
        self.assertEqual(self.r.run([project('app', root)]), 0)
        g = self.r.tabs()['app.git']
        self.assertEqual(g['remotes'], ['%s\t%s (%s)' % (name, urls[name][1], op) for name in sorted(urls) for op in ('fetch', 'push')])
        self.assertIn('pulls', g)  # the stripped origin is still recognised as GitHub
        published = self.r.err
        for path in glob.glob(os.path.join(self.r.out, '**', '*'), recursive=True):
            if os.path.isfile(path):
                with io.open(path, encoding='utf-8') as f:
                    published += f.read()
        for secret in ('TOPSECRET', 'ANOTHERSECRET', 'ONLYTOKENSECRET', 'jdk:', 'x-access-token'):
            self.assertNotIn(secret, published)


class FakeGit:
    """Stands in for export_board.git: fixed captured stdout per argv. One instance drives both the live git_tab
    and the pre-move reference below, so the two see identical input and neither touches a repository."""

    def __init__(self, out):
        self.out, self.calls = out, []

    def __call__(self, root, *args):
        self.calls.append(args)
        return self.out.get(args, '')


def _reference_git_tab(root, now):
    """export_board.git_tab exactly as it stood at commit 5baa922, before its pure half moved into
    derive.git_default and derive.git_doc. Only the first line is new: it binds the two names the body calls.

    The git tab cannot be pinned to committed bytes -- its repoPath is a fresh temporary directory and its head
    and commit shas come from a repository built anew by each run -- so the old implementation is kept here and
    compared against the live one in-run instead, which compares the two implementations directly.
    """
    git, public_remote = eb.git, eb.public_remote
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


FAKE_ROOT = 'C:\\repos\\app'
CAPTURED = {
    ('branch', '--show-current'): 'work',
    ('rev-parse', '--verify', '--quiet', 'master'): '1111111',
    ('rev-parse', '--verify', '--quiet', 'main'): '2222222',
    ('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict'):
        'aaaaaaa|2026-09-10T10:00:00+01:00|Add the widget\nbbbbbbb|2026-09-09T09:00:00+01:00|Tidy up',
    ('ls-files',): 'README.md\nsite/index.html\nsite/app.js',
    ('status', '--short'): ' M site/app.js\n\n?? notes.txt',
    ('remote', '-v'): 'origin\thttps://github.com/o/r.git (fetch)\norigin\thttps://github.com/o/r.git (push)',
    ('rev-parse', '--short', 'HEAD'): 'aaaaaaa',
    ('rev-list', '--count', 'master..work'): '4',
    ('diff', '--shortstat', 'master', 'work'): ' 2 files changed, 9 insertions(+)',
}


class GitTabUnchanged(unittest.TestCase):
    """T-6 for the git tab: the same document as the pre-move implementation, keys, values and key order."""

    def cases(self):
        return [
            ('a default branch and a current branch', CAPTURED),
            ('neither branch', {**CAPTURED, ('branch', '--show-current'): '',
                                ('rev-parse', '--verify', '--quiet', 'master'): '',
                                ('rev-parse', '--verify', '--quiet', 'main'): ''}),
            ('a commit subject holding a pipe', {**CAPTURED,
                ('log', '--pretty=format:%h|%ad|%s', '--date=iso-strict'):
                    'aaaaaaa|2026-09-10T10:00:00+01:00|Split a|b on the first pipe only'}),
            ('a remote carrying userinfo', {**CAPTURED,
                ('remote', '-v'): 'origin\thttps://jdk:ghp_TOKEN@github.com/o/r.git (fetch)\n\n'
                                  'origin\tgit@github.com:o/r.git (push)'}),
        ]

    def drive(self, out):
        fake = FakeGit(out)
        before = eb.git
        eb.git = fake
        try:
            return eb.git_tab(FAKE_ROOT, NOW), _reference_git_tab(FAKE_ROOT, NOW), fake
        finally:
            eb.git = before

    def test_git_tab_equals_the_pre_move_implementation(self):
        for name, out in self.cases():
            with self.subTest(name):
                live, reference, fake = self.drive(out)
                self.assertEqual(live, reference)
                self.assertEqual(list(live), list(reference))
                self.assertTrue(fake.calls)

    def test_the_fake_drives_both_without_touching_a_repository(self):
        # Without this, an equal pair could just mean both implementations read the same real repository.
        live, reference, _ = self.drive(CAPTURED)
        self.assertEqual((live['repoPath'], live['head'], live['ahead']), ('C:/repos/app', 'aaaaaaa', '4'))
        self.assertFalse(os.path.exists(FAKE_ROOT))
        self.assertEqual(reference['branch'], 'work')

    def test_the_move_changes_no_public_surface(self):
        self.assertIs(eb.public_remote, derive.public_remote)
        self.assertEqual(eb.TABS, ('spec', 'assumptions', 'decisions', 'backlog', 'git'))


# The bytes export_board.main writes for app's four spec-derived tabs, captured from the implementation at
# commit 5baa922, before the git tab's pure half moved into derive. They are deterministic -- fixed text plus
# the injected now, with no sha, path or clock in them -- so unlike the git tab they can be pinned byte for byte.
PRE_MOVE_SPEC_TABS = json.loads(r'''
{
 "spec": "{\n \"source\": \"docs/backlog/specs/app.md\",\n \"generatedAt\": \"2026-09-11T00:00:00+00:00\",\n \"revision\": \"4\",\n \"designRevision\": \"—\",\n \"goals\": [\n  {\n   \"id\": \"G-1\",\n   \"text\": \"Ship the `widget`.\"\n  },\n  {\n   \"id\": \"G-2\",\n   \"text\": \"Keep it **small**.\"\n  }\n ],\n \"scopeIn\": [\n  \"Widgets\"\n ],\n \"scopeOut\": [\n  \"Gadgets\"\n ],\n \"logicCore\": [\n  \"Eligibility.\",\n  \"Cost.\"\n ],\n \"prd\": {\n  \"path\": \"docs/prd/app.md\",\n  \"frs\": 2,\n  \"nfrs\": 1,\n  \"constraints\": 1,\n  \"acs\": 1,\n  \"assumptions\": 1\n },\n \"rounds\": [\n  {\n   \"gate\": \"Plan gate\",\n   \"round\": 1,\n   \"verdict\": \"GO\"\n  }\n ],\n \"approval\": \"—\",\n \"approvedBy\": \"—\"\n}",
 "assumptions": "{\n \"source\": \"docs/backlog/specs/app.md\",\n \"generatedAt\": \"2026-09-11T00:00:00+00:00\",\n \"rows\": [\n  {\n   \"n\": 1,\n   \"question\": \"Where does the data live?\",\n   \"resolution\": \"JSON\",\n   \"status\": \"RESOLVED\",\n   \"source\": \"PRD\",\n   \"impact\": \"Low - one file\",\n   \"level\": \"Low\",\n   \"needsYou\": false\n  },\n  {\n   \"n\": 2,\n   \"question\": \"Who owns an entry?\",\n   \"resolution\": \"The team\",\n   \"status\": \"ASSUMED\",\n   \"source\": \"brief\",\n   \"impact\": \"Medium - rework\",\n   \"level\": \"Medium\",\n   \"needsYou\": true\n  },\n  {\n   \"n\": 3,\n   \"question\": \"Search?\",\n   \"resolution\": \"In the client\",\n   \"status\": \"ASSUMED\",\n   \"source\": \"brief\",\n   \"impact\": \"High - rewrite\",\n   \"level\": \"High\",\n   \"needsYou\": true\n  }\n ],\n \"humanList\": [\n  2,\n  3\n ]\n}",
 "decisions": "{\n \"source\": \"docs/backlog/specs/app.md, docs/adr/, docs/brief/raw-notes.md\",\n \"generatedAt\": \"2026-09-11T00:00:00+00:00\",\n \"notWorkedOut\": [\n  {\n   \"item\": \"Where the data lives\",\n   \"row\": 1,\n   \"adr\": \"ADR-0001\",\n   \"landed\": \"JSON\",\n   \"status\": \"RESOLVED\",\n   \"needsYou\": false\n  }\n ],\n \"adrs\": [\n  {\n   \"id\": \"ADR-0001\",\n   \"title\": \"Data in JSON\",\n   \"status\": \"proposed\",\n   \"resolves\": \"row 1\",\n   \"path\": \"docs/adr/0001-data.md\"\n  }\n ],\n \"decisions\": [\n  {\n   \"decision\": \"Use JSON\",\n   \"rationale\": \"simple\",\n   \"madeBy\": \"owner\",\n   \"date\": \"2026-09-01\"\n  }\n ]\n}",
 "backlog": "{\n \"source\": \"docs/backlog/specs/app.md (PBI list) + build state kept in projects/app.json in the dispatch-board repo\",\n \"generatedAt\": \"2026-09-11T00:00:00+00:00\",\n \"pbis\": [\n  {\n   \"id\": \"PBI-001\",\n   \"title\": \"Widget\",\n   \"dependsOn\": \"—\",\n   \"group\": \"core\",\n   \"risk\": \"Low\",\n   \"requiresSpec\": \"no\",\n   \"state\": \"done\",\n   \"review\": \"GO\",\n   \"open\": \"\",\n   \"commit\": \"abc1234\"\n  },\n  {\n   \"id\": \"PBI-002\",\n   \"title\": \"Gadget\",\n   \"dependsOn\": \"PBI-001\",\n   \"group\": \"core\",\n   \"risk\": \"Low\",\n   \"requiresSpec\": \"no\",\n   \"state\": \"todo\",\n   \"review\": \"—\",\n   \"open\": \"\",\n   \"commit\": \"\"\n  }\n ],\n \"board\": \"Nothing is on the BOARD yet.\",\n \"later\": []\n}"
}
''')


class SpecTabBytes(ReposCase):
    """T-6 for the four deterministic tabs: main writes the same bytes as it did before the move."""

    def test_the_four_spec_tabs_are_byte_identical_to_the_committed_fixture(self):
        root = self.r.repo('app', FULL, with_git=False)
        self.r.data('app', DATA)
        self.assertEqual(self.r.run([project('app', root)]), 0)
        for tab, want in sorted(PRE_MOVE_SPEC_TABS.items()):
            with io.open(os.path.join(self.r.out, 'projectTabs', 'app.%s.json' % tab), 'rb') as f:
                got = f.read()
            with self.subTest(tab):
                # The fixture can only pin bytes that hold no temporary path; this fails if one ever creeps in.
                self.assertNotIn(root.encode('utf-8'), got)
                self.assertNotIn(root.replace('\\', '/').encode('utf-8'), got)
                self.assertEqual(got, want.encode('utf-8'))


class PublicRemote(unittest.TestCase):
    def test_userinfo_is_stripped(self):
        for line, expected in (
                ('origin\thttps://jdk:ghp_TOKEN@github.com/o/r.git (fetch)', 'origin\thttps://github.com/o/r.git (fetch)'),
                ('origin\thttps://TOKEN@github.com/o/r (push)', 'origin\thttps://github.com/o/r (push)'),
                ('m\thttps://u:p@ss@example.com/o/r (fetch)', 'm\thttps://example.com/o/r (fetch)'),
                ('o\tssh://git@github.com/o/r.git (fetch)', 'o\tssh://github.com/o/r.git (fetch)')):
            self.assertEqual(eb.public_remote(line), expected)

    def test_lines_without_userinfo_are_unchanged(self):
        for line in ('o\tgit@github.com:o/r.git (fetch)', 'o\tC:/repos/app (fetch)', 'o\thttps://github.com/o/r@v2 (fetch)',
                     'o\tfile:///C:/repos/app (push)', 'o'):
            self.assertEqual(eb.public_remote(line), line)


class GithubOrigin(unittest.TestCase):
    def test_origin_urls_on_github(self):
        for url in ('https://github.com/o/r.git', 'https://GitHub.com/o/r', 'git@github.com:o/r.git',
                    'ssh://git@github.com/o/r.git', 'https://x-access-token@github.com/o/r.git'):
            self.assertTrue(eb.github_origin(['origin\t%s (fetch)' % url, 'origin\t%s (push)' % url]), url)

    def test_other_remotes(self):
        for lines in (['origin\thttps://gitlab.com/o/r.git (fetch)'], ['origin\thttps://github.com.evil.example/o/r (fetch)'],
                      ['origin\thttps://evil.example/github.com/o/r (fetch)'], ['upstream\thttps://github.com/o/r (fetch)'],
                      ['originals\thttps://github.com/o/r (fetch)'], [], ['origin']):
            self.assertFalse(eb.github_origin(lines), lines)

    def test_the_repository_is_named_from_the_origin_url(self):
        for url in ('https://github.com/o/r.git', 'https://github.com/o/r', 'https://github.com/o/r/', 'git@github.com:o/r.git',
                    'ssh://git@github.com/o/r.git', 'https://x-access-token@github.com/o/r.git'):
            self.assertEqual(eb.github_repo(['upstream\thttps://github.com/u/x (fetch)', 'origin\t%s (fetch)' % url]), 'o/r', url)

    def test_no_repository_name_without_a_plain_github_origin(self):
        for lines in (['origin\thttps://gitlab.com/o/r.git (fetch)'], ['upstream\thttps://github.com/o/r (fetch)'],
                      ['origin\thttps://github.com/o (fetch)'], ['origin\thttps://github.com/o/r/pulls (fetch)'], []):
            self.assertIsNone(eb.github_repo(lines), lines)

    @unittest.skipUnless(HAS_GIT, 'git is not installed')
    def test_gh_runs_without_repo_when_the_origin_path_is_not_owner_and_name(self):
        r = Repos()
        self.addCleanup(shutil.rmtree, r.tmp, True)
        root = r.repo('app', FULL)
        git(root, 'remote', 'add', 'origin', 'https://github.com/o')
        r.gh = FakeGh('[]')
        self.assertEqual(r.run([project('app', root)]), 0)
        [(cmd, _)] = r.gh.calls
        self.assertEqual(cmd, GH_ARGS[:-2])


# ---------------------------------------------------------------- the project list

class ProjectList(unittest.TestCase):
    def test_legacy_build_block_is_one_project(self):
        cfg = {'build': {'repoPath': 'C:/x/platform-catalogue', 'branch': 'build/logic-core', 'sessions': ['s1']},
               'usage': {'sessions': [{'sessionId': 's2', 'label': 'x'}]}}
        [p] = bc.projects(cfg)
        self.assertEqual((p['id'], p['name'], p['repoPath'], p['branch']),
                         ('platform-catalogue', 'platform-catalogue', 'C:/x/platform-catalogue', 'build/logic-core'))
        self.assertEqual(p['sessions'], ['s1', 's2'])
        self.assertEqual(p['statusDoc'], 'meta/status')
        self.assertEqual(p['docs'], bc.LEGACY_DOCS)

    def test_legacy_docs_are_the_paths_the_exporter_always_used(self):
        self.assertEqual(bc.LEGACY_DOCS['spec'], 'docs/backlog/specs/platform-catalogue.md')
        self.assertEqual(bc.LEGACY_DOCS['design'], 'docs/backlog/specs/pbi-008-design-system.md')
        self.assertEqual(bc.LEGACY_DOCS['prd'], 'docs/prd/platform-catalogue.md')
        self.assertEqual(bc.LEGACY_DOCS['brief'], 'docs/brief/raw-notes.md')
        self.assertEqual(bc.LEGACY_DOCS['adrDir'], 'docs/adr')

    def test_projects_list_wins_over_the_legacy_block(self):
        cfg = {'projects': [{'id': 'a', 'repoPath': 'C:/a', 'sessions': ['s9']}], 'build': {'repoPath': 'C:/b', 'sessions': ['s1']}}
        self.assertEqual([p['id'] for p in bc.projects(cfg)], ['a'])

    def test_no_projects(self):
        self.assertEqual(bc.projects({}), [])
        self.assertEqual(bc.projects({'build': {'sessions': []}}), [])

    def test_defaults(self):
        [p] = bc.projects({'projects': [{'id': 'a', 'repoPath': 'C:/a'}]})
        self.assertEqual((p['name'], p['sessions'], p['statusDoc'], p['docs'], p['branch']), ('a', [], 'status/a', {}, ''))

    def test_unusable_ids_and_status_docs_are_refused(self):
        for bad in ([{'id': 'a/b', 'repoPath': 'C:/a'}],
                    [{'id': 'a', 'repoPath': 'C:/a', 'statusDoc': 'runs/x'}],
                    [{'id': 'a', 'repoPath': 'C:/a'}, {'id': 'a', 'repoPath': 'C:/b'}],
                    [{'id': 'a', 'repoPath': 'C:/a', 'statusDoc': 'meta/status'}, {'id': 'b', 'repoPath': 'C:/b', 'statusDoc': 'meta/status'}]):
            with self.assertRaises(ValueError, msg=bad):
                bc.projects({'projects': bad})

    def test_projects_that_is_not_a_list_is_refused(self):
        # Read as "no projects", it would drop every project's documents at exit 0.
        for bad in ({'id': 'a'}, 'a', None, 3):
            with self.assertRaises(ValueError, msg=bad):
                bc.projects({'projects': bad})

    def test_entry_that_is_not_an_object_is_refused(self):
        for bad in (['a'], [None], [['a']]):
            with self.assertRaises(ValueError, msg=bad):
                bc.projects({'projects': bad})

    def test_a_session_listed_twice_is_kept_once_in_order(self):
        [p] = bc.projects({'projects': [{'id': 'a', 'sessions': ['s2', 's1', 's2', 's1', 's3']}]})
        self.assertEqual(p['sessions'], ['s2', 's1', 's3'])

    def test_meta_last_refresh_is_reserved(self):
        self.assertIsNone(bc.STATUS_DOC.match('meta/lastRefresh'))
        for ok in ('meta/status', 'meta/lastRefreshed', 'meta/lastrefresh', 'status/lastRefresh'):
            self.assertTrue(bc.STATUS_DOC.match(ok), ok)
        with self.assertRaises(ValueError) as cm:
            bc.projects({'projects': [{'id': 'a', 'repoPath': 'C:/a', 'statusDoc': 'meta/lastRefresh'}]})
        self.assertIn('meta/lastRefresh', str(cm.exception))


class ManualRows(unittest.TestCase):
    ROW = {'id': 'orch-x', 'after': 'a1', 'from': 'a1', 'lane': 'orch', 'label': 'In-line work', 'kind': 'done', 'verdict': 'wired'}

    def manual(self, *rows):
        return bc.manual({'runs': {'manual': list(rows)}})

    def test_valid_rows_are_returned_as_they_are(self):
        self.assertEqual(self.manual(self.ROW, {'id': 'b', 'label': 'minimal'}), [self.ROW, {'id': 'b', 'label': 'minimal'}])
        self.assertEqual(bc.manual({}), [])
        self.assertEqual(bc.manual({'runs': {}}), [])

    def test_every_run_lane_and_kind_is_accepted(self):
        self.assertEqual(set(bc.RUN_LANES), set('orch req plan cw tw cr ver human other'.split()))
        self.assertEqual(set(bc.RUN_KINDS), set('running done go changes nogo killed'.split()))
        for lane in bc.RUN_LANES:
            self.manual(dict(self.ROW, lane=lane))
        for kind in bc.RUN_KINDS:
            self.manual(dict(self.ROW, kind=kind))

    def test_lanes_and_kinds_match_the_local_record_shapes(self):
        # Read as data, not imported: the exporters must not depend on the local app.
        with io.open(os.path.join(HERE, 'local', 'records.shapes.json'), encoding='utf-8') as f:
            enums = json.load(f)['run']['enums']
        self.assertEqual(sorted(bc.RUN_LANES), sorted(enums['lane']))
        self.assertEqual(sorted(bc.RUN_KINDS), sorted(enums['kind']))

    def test_a_bad_row_is_refused_naming_it_and_the_field(self):
        for change, field in (({'lane': 'orhc'}, 'lane'), ({'lane': 'ORCH'}, 'lane'), ({'lane': None}, 'lane'),
                              ({'kind': 'finished'}, 'kind'), ({'kind': None}, 'kind'), ({'verdict': 3}, 'verdict'),
                              ({'from': ['a1']}, 'from'), ({'label': None}, 'label'), ({'verdict': None}, 'verdict')):
            with self.subTest(change=change):
                with self.assertRaises(ValueError) as cm:
                    self.manual({'id': 'fine', 'label': 'ok'}, dict(self.ROW, **change))
                self.assertIn('orch-x', str(cm.exception))
                self.assertIn(field, str(cm.exception))
                self.assertIn('runs.manual[1]', str(cm.exception))

    def test_a_row_without_a_string_id_or_label_is_refused(self):
        for row, field in (({'label': 'x'}, 'id'), ({'id': 5, 'label': 'x'}, 'id'), ({'id': 'r'}, 'label')):
            with self.subTest(row=row):
                with self.assertRaises(ValueError) as cm:
                    self.manual(row)
                self.assertIn('runs.manual[0]', str(cm.exception))
                self.assertIn(field, str(cm.exception))

    def test_an_id_that_is_not_one_safe_path_segment_is_refused(self):
        for rid in ('../x', 'a/b', 'a\\b', '.', '..', '', 'a\x00b', 'a\nb', 'x\n', 'a\x85b'):
            with self.subTest(id=rid):
                with self.assertRaises(ValueError) as cm:
                    self.manual({'id': 'fine', 'label': 'ok'}, dict(self.ROW, id=rid))
                self.assertIn('runs.manual[1]', str(cm.exception))
                self.assertIn('id %r' % rid, str(cm.exception))

    def test_an_id_unsafe_as_a_windows_file_name_is_refused(self):
        # The id is joined onto out/runs on the Windows refresher: a colon makes it drive-relative, the reserved
        # characters crash the write after out/ is emptied, a leading dot hides it from the *.json glob, Windows
        # strips a trailing dot or space, and a device name opens the device rather than a file.
        for rid in ('d:x', 'a?b', 'a*b', 'a|b', 'a"b', 'a<b', 'a>b', '.x', '..x', 'x.', 'x..', 'x ', 'CON', 'con.json',
                    'LPT1', 'prn', 'Aux', 'NUL.txt', 'COM1', 'com9.tar.gz', 'lpt9'):
            with self.subTest(id=rid):
                with self.assertRaises(ValueError) as cm:
                    self.manual({'id': 'fine', 'label': 'ok'}, dict(self.ROW, id=rid))
                self.assertIn('runs.manual[1]', str(cm.exception))
                self.assertIn('id %r' % rid, str(cm.exception))

    def test_ids_that_only_contain_dots_among_other_characters_are_accepted(self):
        for rid in ('a..b', 'orch-r2.1', 'in-line work', 'orch-adrs-spec', 'orch-toolchain', 'CONSOLE', 'con-x',
                    'COM10', 'LPT0', 'nul_x'):
            with self.subTest(id=rid):
                self.assertEqual(self.manual(dict(self.ROW, id=rid))[0]['id'], rid)

    def test_the_id_form_matches_the_local_run_id_form(self):
        # Read as data, not imported: the exporters must not depend on the local app.
        with io.open(os.path.join(HERE, 'local', 'records.py'), encoding='utf-8') as f:
            tree = ast.parse(f.read())
        assigned = {t.id: node.value for node in tree.body if isinstance(node, ast.Assign)
                    for t in node.targets if isinstance(t, ast.Name)}
        self.assertEqual(ast.literal_eval(assigned['_SEGMENT'].args[0]), bc.RUN_ID.pattern)
        forms = assigned['_ID_FORMS']
        run_form = forms.values[[ast.literal_eval(k) for k in forms.keys].index('run')]
        self.assertEqual(run_form.id, '_SEGMENT')

    def test_manual_that_is_not_a_list_of_objects_is_refused(self):
        for cfg, named in (({'runs': {'manual': {'id': 'x'}}}, 'runs.manual'), ({'runs': {'manual': ['x']}}, 'runs.manual[0]'),
                           ({'runs': []}, '"runs"')):
            with self.subTest(cfg=cfg):
                with self.assertRaises(ValueError) as cm:
                    bc.manual(cfg)
                self.assertIn(named, str(cm.exception))


# ---------------------------------------------------------------- committed files

class CommittedFiles(unittest.TestCase):
    def test_repo_config_lists_both_projects(self):
        with io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8') as f:
            ps = {p['id']: p for p in bc.projects(json.load(f))}
        pc, db = ps['platform-catalogue'], ps['dispatch-board']
        self.assertEqual((pc['repoPath'], pc['branch'], pc['statusDoc']), ('C:/Users/jdk/platform-catalogue', 'build/logic-core', 'meta/status'))
        self.assertIn('7f71729a-c7c5-4855-aab8-25ddf9bac96f', pc['sessions'])
        self.assertEqual({k: pc['docs'][k] for k in bc.LEGACY_DOCS}, bc.LEGACY_DOCS)
        self.assertEqual((db['repoPath'], db['branch'], db['statusDoc']), ('C:/Users/jdk/dispatch-board', 'main', 'status/dispatch-board'))
        self.assertIn('9562c312-123e-4f48-952b-32d375699bf7', db['sessions'])

    def test_repo_config_manual_rows_are_well_formed(self):
        with io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8') as f:
            self.assertTrue(bc.manual(json.load(f)))

    def test_data_files_are_well_formed(self):
        files = glob.glob(os.path.join(HERE, 'projects', '*.json'))
        self.assertTrue(files)
        for path in files:
            with io.open(path, encoding='utf-8') as f:
                data = json.load(f)
            self.assertIsInstance(data, dict, path)
            for pbi, e in (data.get('buildState') or {}).items():
                self.assertIn(e.get('state'), eb.STATES, '%s %s' % (path, pbi))
                for k in ('review', 'open', 'commit'):
                    self.assertIsInstance(e.get(k), str, '%s %s.%s' % (path, pbi, k))
            for e in data.get('notWorkedOut') or []:
                self.assertIsInstance(e.get('item'), str, path)
                self.assertIsInstance(e.get('row'), int, path)
                self.assertTrue(e.get('adr') is None or isinstance(e['adr'], str), path)
            self.assertIsInstance(data.get('boardNote', ''), str, path)


if __name__ == '__main__':
    unittest.main()
