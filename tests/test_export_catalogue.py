"""Tests for exporters/export_catalogue.py and the catalogue block in exporters/board_config.py, run against
a synthetic marketplace folder and installed-plugins file built in a temporary directory.

Every export test passes its own config, whose catalogue block points into that directory, and its own out
dir, so nothing here reads the real ~/.claude or writes the repo's out/. One test reads the repo's
board.config.json on purpose, to check its catalogue block has the shape the exporter expects.
"""
import contextlib, io, json, os, shutil, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
import board_config as bc  # noqa: E402
import export_catalogue as ec  # noqa: E402

BOM = '\ufeff'
DEEP = '[' * 100000 + ']' * 100000  # valid JSON, nested past the decoder's recursion limit


@contextlib.contextmanager
def deny_listing(*folders):
    """Listing any of these folders raises PermissionError, whether it goes through os.listdir or os.scandir
    (glob uses scandir); every other folder lists as usual. Windows cannot make a folder unlistable to its owner
    from a test, so the refusal is simulated."""
    denied = {os.path.normcase(os.path.abspath(f)) for f in folders}
    real = {'listdir': os.listdir, 'scandir': os.scandir}

    def guard(name):
        def call(path='.'):
            if os.path.normcase(os.path.abspath(os.fsdecode(path))) in denied:
                raise PermissionError(13, 'Access is denied', path)
            return real[name](path)
        return call
    with mock.patch('os.listdir', guard('listdir')), mock.patch('os.scandir', guard('scandir')):
        yield


def agent_text(name, desc, nl='\n'):
    return nl.join(['---', 'name: %s' % name, 'description: "%s"' % desc, 'tools: Read, Grep', '---', '', '# %s' % name, 'Body.', ''])


def skill_text(name, desc, nl='\n'):
    return nl.join(['---', 'name: %s' % name, 'description: %s' % desc, 'spec_version: 3', '---', '', 'Body.', ''])


class Market:
    """A throwaway marketplace (plugins/<plugin>/agents/*.md, plugins/<plugin>/skills/*/SKILL.md, manifests),
    an installed-plugins file and an out dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix='board-test-')
        self.mp = os.path.join(self.tmp, 'agent-catalog')
        self.installed = os.path.join(self.tmp, 'installed_plugins.json')
        self.out = os.path.join(self.tmp, 'out')
        self.err = ''

    def cfg(self, **over):
        block = {'marketplacePath': self.mp, 'installedPath': self.installed}
        block.update(over)
        return {'catalogue': block}

    def write(self, path, text, bom=False, crlf=False, raw=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if raw is None:
            if crlf:
                text = text.replace('\r\n', '\n').replace('\n', '\r\n')
            raw = ((BOM if bom else '') + text).encode('utf-8')
        with io.open(path, 'wb') as f:
            f.write(raw)
        return path

    def agent(self, plugin, fname, text, **kw):
        return self.write(os.path.join(self.mp, 'plugins', plugin, 'agents', fname + '.md'), text, **kw)

    def skill(self, plugin, folder, text, **kw):
        return self.write(os.path.join(self.mp, 'plugins', plugin, 'skills', folder, 'SKILL.md'), text, **kw)

    def manifest(self, plugin, desc=None, text=None, **kw):
        body = text if text is not None else json.dumps({'name': plugin, 'description': desc, 'version': '0.1.0'}, indent=2)
        return self.write(os.path.join(self.mp, 'plugins', plugin, '.claude-plugin', 'plugin.json'), body, **kw)

    def install(self, *plugins, text=None):
        body = text if text is not None else json.dumps({'version': 2, 'plugins': {p: [{'scope': 'user', 'version': '0.1.0'}] for p in plugins}})
        self.write(self.installed, body)

    def run(self, cfg=None):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = ec.main(config=cfg or self.cfg(), out_dir=self.out)
        self.err = err.getvalue()
        return code

    @property
    def index_path(self):
        return os.path.join(self.out, 'catalogue', 'index.json')

    def index(self):
        with io.open(self.index_path, encoding='utf-8') as f:
            return json.load(f)

    def standard(self):
        """Two plugins, one installed: agents, skills and manifests in their everyday shape."""
        self.agent('engineering-agents', 'code-writer', agent_text('code-writer', 'Implements a change under TDD.'))
        self.agent('engineering-agents', 'test-writer', agent_text('test-writer', 'Backfills tests.'))
        self.skill('engineering-agents', 'tdd-loop', skill_text('tdd-loop', 'Runs red, green, refactor.'))
        self.manifest('engineering-agents', 'Mutating engineering doer agents with a TDD verification loop. code-writer (implements).')
        self.skill('workflow-agents', 'wf-run', skill_text('wf-run', 'Runs a workflow.'))
        self.agent('workflow-agents', 'orchestrator', agent_text('orchestrator', 'Coordinates the fleet.'))
        self.manifest('workflow-agents', 'Workflow agents')
        self.install('engineering-agents@agent-catalog', 'review-agents@agent-catalog', 'workflow-agents@another-market')

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class MarketCase(unittest.TestCase):
    def setUp(self):
        self.m = Market()
        self.addCleanup(self.m.cleanup)


# ---------------------------------------------------------------- the export

class Export(MarketCase):
    def test_every_agent_and_skill_is_one_entry(self):
        self.m.standard()
        self.assertEqual(self.m.run(), 0)
        doc = self.m.index()
        self.assertEqual(doc['entries'], [
            {'id': 'engineering-agents:code-writer', 'kind': 'agent', 'plugin': 'engineering-agents', 'name': 'code-writer',
             'description': 'Implements a change under TDD.', 'installed': True},
            {'id': 'engineering-agents:test-writer', 'kind': 'agent', 'plugin': 'engineering-agents', 'name': 'test-writer',
             'description': 'Backfills tests.', 'installed': True},
            {'id': 'engineering-agents:tdd-loop', 'kind': 'skill', 'plugin': 'engineering-agents', 'name': 'tdd-loop',
             'description': 'Runs red, green, refactor.', 'installed': True},
            {'id': 'workflow-agents:orchestrator', 'kind': 'agent', 'plugin': 'workflow-agents', 'name': 'orchestrator',
             'description': 'Coordinates the fleet.', 'installed': False},
            {'id': 'workflow-agents:wf-run', 'kind': 'skill', 'plugin': 'workflow-agents', 'name': 'wf-run',
             'description': 'Runs a workflow.', 'installed': False},
        ])
        self.assertEqual(doc['plugins'], [
            {'plugin': 'engineering-agents', 'purpose': 'Mutating engineering doer agents with a TDD verification loop.',
             'purposeFull': 'Mutating engineering doer agents with a TDD verification loop. code-writer (implements).',
             'installed': True, 'agents': 2, 'skills': 1},
            {'plugin': 'workflow-agents', 'purpose': 'Workflow agents', 'purposeFull': 'Workflow agents',
             'installed': False, 'agents': 1, 'skills': 1},
        ])
        self.assertEqual(doc['source'], {'marketplacePath': self.m.mp, 'installedPath': self.m.installed})
        self.assertIn('generatedAt', doc)

    def test_the_file_is_written_whole(self):
        self.m.standard()
        self.assertEqual(self.m.run(), 0)
        self.assertEqual(os.listdir(os.path.join(self.m.out, 'catalogue')), ['index.json'])  # no temp file left behind

    def test_name_falls_back_to_the_file_or_folder_name(self):
        self.m.agent('p', 'from-file', '---\ndescription: An agent without a name.\n---\n')
        self.m.skill('p', 'from-folder', '---\nname:\ndescription: A skill with an empty name.\n---\n')
        self.assertEqual(self.m.run(), 0)
        self.assertEqual([(e['id'], e['name']) for e in self.m.index()['entries']],
                         [('p:from-file', 'from-file'), ('p:from-folder', 'from-folder')])

    def test_an_entry_with_an_unusable_id_is_skipped_with_a_warning(self):
        self.m.agent('p', 'good', agent_text('good', 'Fine.'))
        self.m.agent('p', 'spaced', agent_text('has a space', 'Bad id.'))
        self.m.skill('p', 'hostile', skill_text('<img src=x>', 'Bad id.'))
        self.assertEqual(self.m.run(), 0)
        self.assertEqual([e['id'] for e in self.m.index()['entries']], ['p:good'])
        self.assertIn('has a space', self.m.err)
        self.assertIn('<img src=x>', self.m.err)

    def test_plugins_without_agents_or_skills_are_left_out(self):
        self.m.standard()
        self.m.manifest('empty-plugin', 'Nothing here.')
        os.makedirs(os.path.join(self.m.mp, 'plugins', 'empty-plugin', 'agents'))
        self.assertEqual(self.m.run(), 0)
        self.assertEqual([p['plugin'] for p in self.m.index()['plugins']], ['engineering-agents', 'workflow-agents'])

    def test_entries_sort_by_plugin_then_agents_first_then_name(self):
        self.m.skill('b', 'alpha', skill_text('alpha', 'x'))
        self.m.agent('b', 'zulu', agent_text('zulu', 'x'))
        self.m.agent('b', 'mike', agent_text('mike', 'x'))
        self.m.agent('a', 'yankee', agent_text('yankee', 'x'))
        self.assertEqual(self.m.run(), 0)
        self.assertEqual([e['id'] for e in self.m.index()['entries']], ['a:yankee', 'b:mike', 'b:zulu', 'b:alpha'])

    def test_crlf_and_a_bom_parse_identically(self):
        desc = 'Reviews a change: severity-tagged findings, then GO or NO-GO.'
        manifest = 'Read-only review agents. They grade what the writers built.'
        self.m.agent('lf', 'reviewer', agent_text('reviewer', desc))
        self.m.manifest('lf', manifest)
        self.m.agent('crlf', 'reviewer', agent_text('reviewer', desc), bom=True, crlf=True)
        self.m.manifest('crlf', manifest, bom=True, crlf=True)
        self.m.install('lf@agent-catalog')
        self.assertEqual(self.m.run(), 0)
        doc = self.m.index()
        by = {e['plugin']: e for e in doc['entries']}
        self.assertEqual((by['crlf']['name'], by['crlf']['description']), (by['lf']['name'], by['lf']['description']))
        self.assertEqual(by['crlf']['description'], desc)
        purposes = {p['plugin']: (p['purpose'], p['purposeFull']) for p in doc['plugins']}
        self.assertEqual(purposes['crlf'], purposes['lf'])
        self.assertEqual(purposes['crlf'][0], 'Read-only review agents.')
        self.assertEqual(self.m.err, '')

    def test_only_a_matching_pair_of_quotes_is_removed(self):
        self.m.agent('p', 'single', "---\nname: single\ndescription: 'Single quoted.'\n---\n")
        self.m.agent('p', 'unmatched', '---\nname: unmatched\ndescription: "Starts quoted, ends not\n---\n')
        self.m.agent('p', 'inner', '---\nname: inner\ndescription:   Says "hello": twice.  \n---\n')
        self.assertEqual(self.m.run(), 0)
        by = {e['name']: e['description'] for e in self.m.index()['entries']}
        self.assertEqual(by, {'single': 'Single quoted.', 'unmatched': '"Starts quoted, ends not', 'inner': 'Says "hello": twice.'})

    def test_a_block_value_is_ignored_with_a_warning(self):
        self.m.skill('p', 'folded', '---\nname: folded\ndescription: >\n  A folded block\n  over two lines.\n---\n')
        self.assertEqual(self.m.run(), 0)
        self.assertEqual([(e['name'], e['description']) for e in self.m.index()['entries']], [('folded', '')])
        self.assertIn('folded', self.m.err)

    def test_installed_comes_from_the_agent_catalog_keys(self):
        self.m.standard()
        self.m.run()
        self.assertEqual({p['plugin']: p['installed'] for p in self.m.index()['plugins']},
                         {'engineering-agents': True, 'workflow-agents': False})


class Purpose(unittest.TestCase):
    def test_no_full_stop_keeps_the_whole_description(self):
        self.assertEqual(ec.purpose('Workflow agents for the fleet', 'wf'), 'Workflow agents for the fleet')

    def test_first_sentence(self):
        self.assertEqual(ec.purpose('One. Two.', 'p'), 'One.')
        self.assertEqual(ec.purpose('Really! More text.', 'p'), 'Really!')
        self.assertEqual(ec.purpose('Why? Because.', 'p'), 'Why?')
        self.assertEqual(ec.purpose('Ends here.', 'p'), 'Ends here.')

    def test_a_dot_inside_a_word_is_not_a_sentence_end(self):
        self.assertEqual(ec.purpose('Ships v1.2 today. Later more.', 'p'), 'Ships v1.2 today.')
        self.assertEqual(ec.purpose('Reads (PRD->spec.md) files. Next.', 'p'), 'Reads (PRD->spec.md) files.')

    def test_e_g_and_i_e_are_not_sentence_ends(self):
        self.assertEqual(ec.purpose('Tools, E.g. linters and i.e. formatters. Second sentence.', 'p'),
                         'Tools, E.g. linters and i.e. formatters.')
        self.assertEqual(ec.purpose('Grounding, e.g. docs', 'p'), 'Grounding, e.g. docs')

    def test_over_120_characters_is_cut_at_a_word_boundary(self):
        desc = ('Disciplined PBI delivery workflow: planner (PRD->spec->backlog), coordinator, worker, and reviewer '
                'skills enforcing a gated state machine. More.')
        got = ec.purpose(desc, 'backlog-delivery')
        self.assertEqual(got, 'Disciplined PBI delivery workflow: planner (PRD->spec->backlog), coordinator, worker, and reviewer skills enforcing a…')
        self.assertLessEqual(len(got), 120)

    def test_the_cut_drops_trailing_commas_and_spaces(self):
        desc = 'word ' * 22 + 'abcdefgh, tail tail tail tail.'  # a comma falls just before the cut
        got = ec.purpose(desc, 'p')
        self.assertTrue(got.endswith('abcdefgh…'), got)
        self.assertLessEqual(len(got), 120)

    def test_a_single_long_word_is_cut_hard(self):
        got = ec.purpose('x' * 200, 'p')
        self.assertEqual(got, 'x' * 119 + '…')

    def test_no_usable_description_gives_the_plugin_name(self):
        for desc in ('', '   ', None, 42, ['a']):
            self.assertEqual(ec.purpose(desc, 'governance'), 'governance', desc)


class PurposeInTheExport(MarketCase):
    def test_manifest_cases(self):
        long = 'A very long manifest description that runs on and on, well past the one hundred and twenty character limit set for one line.'
        cases = {'nostop': 'No full stop here', 'eg': 'Checks, E.g. policy and quota. Then more.', 'long': long, 'empty': ''}
        for plugin, desc in cases.items():
            self.m.agent(plugin, 'a', agent_text('a', 'x'))
            self.m.manifest(plugin, desc)
        self.m.agent('nomanifest', 'a', agent_text('a', 'x'))
        self.assertEqual(self.m.run(), 0)
        got = {p['plugin']: (p['purpose'], p['purposeFull']) for p in self.m.index()['plugins']}
        self.assertEqual(got['nostop'], ('No full stop here', 'No full stop here'))
        self.assertEqual(got['eg'], ('Checks, E.g. policy and quota.', cases['eg']))
        self.assertTrue(got['long'][0].endswith('…') and len(got['long'][0]) <= 120, got['long'][0])
        self.assertEqual(got['long'][1], long)
        self.assertEqual(got['empty'], ('empty', ''))
        self.assertEqual(got['nomanifest'], ('nomanifest', ''))


# ---------------------------------------------------------------- failures

class Failures(MarketCase):
    def exported_once(self):
        self.m.standard()
        self.assertEqual(self.m.run(), 0)
        with io.open(self.m.index_path, 'rb') as f:
            return f.read()

    def assert_kept(self, before):
        with io.open(self.m.index_path, 'rb') as f:
            self.assertEqual(f.read(), before)

    def test_missing_marketplace_keeps_the_last_export(self):
        before = self.exported_once()
        self.assertEqual(self.m.run(self.m.cfg(marketplacePath=os.path.join(self.m.tmp, 'nowhere'))), 0)
        self.assert_kept(before)
        self.assertIn('nowhere', self.m.err)

    def test_missing_plugins_folder_keeps_the_last_export(self):
        before = self.exported_once()
        shutil.rmtree(os.path.join(self.m.mp, 'plugins'))
        self.assertEqual(self.m.run(), 0)
        self.assert_kept(before)
        self.assertIn('plugins', self.m.err)

    def test_zero_entries_keeps_the_last_export(self):
        before = self.exported_once()
        shutil.rmtree(os.path.join(self.m.mp, 'plugins'))
        self.m.manifest('lonely', 'Only a manifest.')
        self.assertEqual(self.m.run(), 0)
        self.assert_kept(before)
        self.assertIn('no agents or skills', self.m.err)

    def test_missing_marketplace_with_no_previous_export_writes_nothing(self):
        self.assertEqual(self.m.run(), 0)
        self.assertFalse(os.path.exists(self.m.index_path))
        self.assertTrue(self.m.err)

    def test_malformed_manifest_falls_back_to_the_plugin_name(self):
        self.m.standard()
        self.m.manifest('engineering-agents', text='{"description": "truncated')
        self.m.manifest('workflow-agents', raw=b'{"description": "caf\xe9 agents"}')  # not UTF-8
        self.assertEqual(self.m.run(), 0)
        got = {p['plugin']: p['purpose'] for p in self.m.index()['plugins']}
        self.assertEqual(got, {'engineering-agents': 'engineering-agents', 'workflow-agents': 'workflow-agents'})
        self.assertIn('engineering-agents', self.m.err)
        self.assertIn('workflow-agents', self.m.err)

    def test_deeply_nested_manifest_falls_back_to_the_plugin_name(self):
        self.m.standard()
        self.m.manifest('engineering-agents', text=DEEP)
        self.assertEqual(self.m.run(), 0)
        got = {p['plugin']: (p['purpose'], p['purposeFull']) for p in self.m.index()['plugins']}
        self.assertEqual(got['engineering-agents'], ('engineering-agents', ''))
        self.assertEqual(got['workflow-agents'], ('Workflow agents', 'Workflow agents'))
        self.assertIn('engineering-agents', self.m.err)

    def test_deeply_nested_installed_file_marks_nothing_installed(self):
        self.m.standard()
        self.m.install(text=DEEP)
        self.assert_nothing_installed()

    def test_unlistable_plugins_folder_keeps_the_last_export(self):
        before = self.exported_once()
        with deny_listing(os.path.join(self.m.mp, 'plugins')):
            self.assertEqual(self.m.run(), 0)
        self.assert_kept(before)
        self.assertIn('plugins', self.m.err)

    def test_unlistable_agents_or_skills_folder_is_warned_and_skipped(self):
        self.m.standard()
        agents = os.path.join(self.m.mp, 'plugins', 'engineering-agents', 'agents')
        skills = os.path.join(self.m.mp, 'plugins', 'workflow-agents', 'skills')
        with deny_listing(agents, skills):
            self.assertEqual(self.m.run(), 0)
        self.assertEqual([e['id'] for e in self.m.index()['entries']],
                         ['engineering-agents:tdd-loop', 'workflow-agents:orchestrator'])
        self.assertIn(agents, self.m.err)
        self.assertIn(skills, self.m.err)

    def test_manifest_that_is_not_an_object(self):
        self.m.standard()
        self.m.manifest('engineering-agents', text='["a list"]')
        self.assertEqual(self.m.run(), 0)
        self.assertEqual(self.m.index()['plugins'][0]['purpose'], 'engineering-agents')

    def assert_nothing_installed(self):
        self.assertEqual(self.m.run(), 0)
        doc = self.m.index()
        self.assertFalse(any(e['installed'] for e in doc['entries']))
        self.assertFalse(any(p['installed'] for p in doc['plugins']))
        self.assertIn('installed', self.m.err)

    def test_missing_installed_file_marks_nothing_installed(self):
        self.m.standard()
        os.remove(self.m.installed)
        self.assert_nothing_installed()

    def test_malformed_installed_file_marks_nothing_installed(self):
        self.m.standard()
        self.m.install(text='{"plugins": {')
        self.assert_nothing_installed()

    def test_installed_file_of_the_wrong_shape_marks_nothing_installed(self):
        self.m.standard()
        self.m.install(text='{"plugins": ["engineering-agents@agent-catalog"]}')
        self.assert_nothing_installed()

    def test_installed_file_that_is_not_utf8_marks_nothing_installed(self):
        self.m.standard()
        self.m.write(self.m.installed, None, raw=b'{"plugins": {"engineering-agents@agent-catalog": ["\xe9"]}}')
        self.assert_nothing_installed()

    def test_unreadable_or_malformed_entry_files_are_skipped(self):
        self.m.standard()
        self.m.agent('engineering-agents', 'latin1', None, raw=b'---\nname: latin1\ndescription: caf\xe9\n---\n')
        self.m.agent('engineering-agents', 'nofront', 'name: nofront\nJust text, no frontmatter.\n')
        os.makedirs(os.path.join(self.m.mp, 'plugins', 'engineering-agents', 'agents', 'folder.md'))
        self.assertEqual(self.m.run(), 0)
        names = [e['name'] for e in self.m.index()['entries']]
        self.assertNotIn('latin1', names)
        self.assertNotIn('nofront', names)
        self.assertIn('code-writer', names)
        for bad in ('latin1', 'nofront', 'folder'):
            self.assertIn(bad, self.m.err)

    def test_a_config_type_error_exits_2(self):
        self.m.standard()
        self.assertEqual(self.m.run(self.m.cfg(marketplacePath=['not', 'a', 'string'])), 2)
        self.assertEqual(self.m.run(self.m.cfg(installedPath=7)), 2)
        self.assertEqual(self.m.run({'catalogue': 'not an object'}), 2)
        self.assertFalse(os.path.exists(self.m.index_path))


# ---------------------------------------------------------------- config

class Config(unittest.TestCase):
    def test_defaults_are_expanded(self):
        got = bc.catalogue({})
        self.assertEqual(got, {
            'marketplacePath': os.path.expanduser('~/.claude/plugins/marketplaces/agent-catalog'),
            'installedPath': os.path.expanduser('~/.claude/plugins/installed_plugins.json')})
        self.assertFalse(got['marketplacePath'].startswith('~'))

    def test_configured_values_starting_with_a_tilde_are_expanded(self):
        got = bc.catalogue({'catalogue': {'marketplacePath': '~/m', 'installedPath': 'C:/abs/installed.json'}})
        self.assertEqual(got, {'marketplacePath': os.path.expanduser('~/m'), 'installedPath': 'C:/abs/installed.json'})

    def test_non_string_values_raise(self):
        for block in ({'marketplacePath': None}, {'installedPath': 3}, {'marketplacePath': {}}):
            with self.assertRaises(ValueError):
                bc.catalogue({'catalogue': block})
        with self.assertRaises(ValueError):
            bc.catalogue({'catalogue': ['x']})

    def test_repo_config_catalogue_block(self):
        with io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        self.assertEqual(cfg['catalogue'], {'marketplacePath': '~/.claude/plugins/marketplaces/agent-catalog',
                                            'installedPath': '~/.claude/plugins/installed_plugins.json'})
        bc.catalogue(cfg)  # does not raise


if __name__ == '__main__':
    unittest.main()
