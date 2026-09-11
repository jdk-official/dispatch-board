"""Tests for exporters/export_board.py and the project list in exporters/board_config.py, run against
synthetic repositories in a temporary directory.

Every export test passes its own config, data folder and out dir, so none of them reads board.config.json
or writes the repo's out/. Two tests read committed files on purpose: the repo's board.config.json and its
projects/*.json data files, to check they have the shape the exporters expect.
"""
import contextlib, glob, io, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
import board_config as bc  # noqa: E402
import export_board as eb  # noqa: E402

HAS_GIT = shutil.which('git') is not None
NOW = '2026-09-11T00:00:00+00:00'

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


class Repos:
    """Throwaway repositories, a data folder and an out dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.out = os.path.join(self.tmp, 'out')
        self.data_dir = os.path.join(self.tmp, 'data')
        os.makedirs(self.data_dir)
        self.err = ''

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

    def run(self, projects):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = eb.main(config={'projects': projects}, out_dir=self.out, data_dir=self.data_dir, now=NOW)
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
                         {k: v for k, v in before.items() if k.startswith('other.')})
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
            self.assertEqual(after['app.' + tab], before['app.' + tab], tab)

    def test_kept_tabs_are_byte_identical(self):
        # refresh.py diffs file contents, so a carried-forward tab must not look like a change.
        root = self.r.repo('app', FULL)
        self.r.run([project('app', root)])
        path = os.path.join(self.r.out, 'projectTabs', 'app.spec.json')
        with io.open(path, 'rb') as f:
            before = f.read()
        self.r.run([project('app', os.path.join(self.r.tmp, 'nowhere'))])
        with io.open(path, 'rb') as f:
            self.assertEqual(f.read(), before)

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
