"""Tests for local/records.py: the SHAPES grammar and validate(), the shipped JSON copy, id forms, store
paths, and the row mapping (to_row / from_row).

Nothing here touches the store, the real out/ or ~/.claude; the one file written goes to a temporary folder.
"""
import contextlib, copy, io, json, os, shutil, sqlite3, sys, tempfile, unittest

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
sys.path.insert(0, os.path.join(HERE, 'local'))
import records  # noqa: E402
import board_config  # noqa: E402

KINDS = ('session', 'run', 'project', 'tab', 'status', 'lastRefresh', 'catalogue')
NOW = '2026-09-11T12:00:00+00:00'

PLUGIN = {'plugin': 'eng', 'purpose': 'Builds things.', 'purposeFull': 'Builds things. Well.', 'installed': True,
          'agents': 1, 'skills': 1}
ENTRY = {'id': 'eng:code-writer', 'kind': 'agent', 'plugin': 'eng', 'name': 'code-writer', 'description': 'Writes code',
         'installed': True}
VALID = {
    'session': {'title': 'Widget', 'folder': 'app', 'cwd': 'C:\\work\\app', 'start': '2026-09-11T10:00:00.000Z',
                'last': '2026-09-11T11:00:00.000Z', 'project': 'alpha', 'build': False, 'windowDays': 7,
                'windowMinutes': 10, 'runs': 1, 'running': 0, 'usage': {'totals': {'effective': 5}},
                'skillUses': {'eng:tdd': {'count': 2, 'last': '2026-09-11T10:30:00.000Z'}}},
    'run': {'session': 'sid-1', 'project': None, 'seq': 1, 'lane': 'cw', 'label': 'PBI-001 widget', 'kind': 'done',
            'verdict': 'DONE', 'tok': 5000, 'min': 29},
    'project': {'name': 'Alpha', 'repoPath': 'C:/work/alpha', 'branch': 'main', 'sessions': [], 'statusDoc': 'meta/status',
                'order': 0, 'runs': 0, 'running': 0, 'last': None, 'usage': None},
    'tab': {'generatedAt': NOW},
    'status': {},
    'lastRefresh': {'at': '2026-09-11T12:00:00Z', 'writer': 'collector'},
    'catalogue': {'generatedAt': NOW, 'plugins': [PLUGIN], 'entries': [ENTRY]},
}
# One field per kind with a value of the wrong type, and the error validate() reports for it.
WRONG = {
    'session': ('windowDays', '7', 'windowDays: expected int'),
    'run': ('tok', '5000', 'tok: expected int'),
    'project': ('order', '0', 'order: expected int'),
    'tab': ('generatedAt', 5, 'generatedAt: expected str'),
    'status': ('live', 'yes', 'live: expected bool'),
    'lastRefresh': ('writer', 5, 'writer: expected str'),
    'catalogue': ('plugins', {}, 'plugins: expected list'),
}
IDS = {'session': '11111111-aaaa-bbbb-cccc-000000000001', 'run': 'a8f34de3e0564883', 'project': 'alpha',
       'tab': 'alpha.backlog', 'status': 'status/alpha', 'lastRefresh': 'lastRefresh', 'catalogue': 'index'}
PATHS = {'session': 'sessions/11111111-aaaa-bbbb-cccc-000000000001', 'run': 'runs/a8f34de3e0564883',
         'project': 'projects/alpha', 'tab': 'projectTabs/alpha.backlog', 'status': 'status/alpha',
         'lastRefresh': 'meta/lastRefresh', 'catalogue': 'catalogue/index'}


def doc(kind, /, **changes):
    d = copy.deepcopy(VALID[kind])
    d.update(changes)
    return d


def without(kind, field):
    d = copy.deepcopy(VALID[kind])
    del d[field]
    return d


# ---------------------------------------------------------------- T1: shapes and grammar

class Shapes(unittest.TestCase):
    def test_the_seven_kinds_are_defined(self):
        self.assertEqual(set(records.SHAPES), set(KINDS))

    def test_shapes_is_the_spec_table(self):
        # Written out by hand from the spec's record-shapes table, not derived from SHAPES, so loosening a type,
        # dropping a required field or widening an enum in SHAPES fails here even though validate() stays happy.
        self.assertEqual(records.SHAPES, {
            'session': {
                'required': {
                    'title': 'str', 'folder': 'str', 'cwd': 'str', 'start': 'str|null', 'last': 'str|null',
                    'project': 'str|null', 'build': 'bool', 'windowDays': 'int', 'windowMinutes': 'int',
                    'runs': 'int', 'running': 'int', 'usage': 'object',
                    'skillUses': {'map_of': {'required': {'count': 'int'}, 'optional': {'last': 'str'}}},
                },
                'optional': {'firstPrompt': 'str'},
            },
            'run': {
                'required': {
                    'session': 'str', 'project': 'str|null', 'seq': 'int', 'lane': 'str', 'label': 'str',
                    'kind': 'str', 'verdict': 'str', 'tok': 'int', 'min': 'int',
                },
                'optional': {
                    'from': 'str', 'feeds': 'str', 'group': 'str', 'agent': 'str', 'agentType': 'str',
                    'start': 'str', 'end': 'str',
                },
                'enums': {
                    'kind': ['running', 'done', 'go', 'changes', 'nogo', 'killed'],
                    'lane': ['orch', 'req', 'plan', 'cw', 'tw', 'cr', 'ver', 'other', 'human'],
                },
            },
            'project': {
                'required': {
                    'name': 'str', 'repoPath': 'str', 'branch': 'str', 'sessions': 'list', 'statusDoc': 'str',
                    'order': 'int', 'runs': 'int', 'running': 'int', 'last': 'str|null', 'usage': 'object|null',
                },
                'optional': {},
            },
            'tab': {'required': {'generatedAt': 'str'}, 'optional': {'source': 'str'}},
            'status': {
                'required': {},
                'optional': {'title': 'str', 'message': 'str', 'live': 'bool', 'updatedAt': 'str', 'metrics': 'object'},
            },
            'lastRefresh': {
                'required': {'at': 'datetime', 'writer': 'str'},
                'optional': {},
                'enums': {'writer': ['collector', 'refresher']},
            },
            'catalogue': {
                'required': {
                    'generatedAt': 'str',
                    'plugins': {'list_of': {'required': {
                        'plugin': 'str', 'purpose': 'str', 'purposeFull': 'str', 'installed': 'bool',
                        'agents': 'int', 'skills': 'int'}}},
                    'entries': {'list_of': {
                        'required': {'id': 'str', 'kind': 'str', 'plugin': 'str', 'name': 'str',
                                     'description': 'str', 'installed': 'bool'},
                        'enums': {'kind': ['agent', 'skill']}}},
                },
                'optional': {'source': 'object'},
            },
        })

    def test_a_minimal_valid_document_of_every_kind_passes(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(records.validate(kind, doc(kind)), [])

    def test_a_missing_required_field_is_reported_for_every_kind_that_has_one(self):
        for kind in KINDS:
            for field in records.SHAPES[kind]['required']:
                with self.subTest(kind=kind, field=field):
                    self.assertEqual(records.validate(kind, without(kind, field)), ['%s: required field missing' % field])

    def test_a_wrong_type_is_reported_for_every_kind(self):
        for kind in KINDS:
            field, value, error = WRONG[kind]
            with self.subTest(kind=kind):
                self.assertEqual(records.validate(kind, doc(kind, **{field: value})), [error])

    def test_unknown_fields_are_allowed_and_kept_at_every_level(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                d = doc(kind, zzExtra={'anything': [1, 2]})
                before = copy.deepcopy(d)
                self.assertEqual(records.validate(kind, d), [])
                self.assertEqual(d, before)
        cat = doc('catalogue', plugins=[dict(PLUGIN, extra=1)], entries=[dict(ENTRY, extra='x')])
        self.assertEqual(records.validate('catalogue', cat), [])
        self.assertEqual(cat['entries'][0]['extra'], 'x')
        ses = doc('session', skillUses={'eng:tdd': {'count': 1, 'extra': True}})
        self.assertEqual(records.validate('session', ses), [])

    def test_status_has_no_required_fields(self):
        self.assertEqual(records.SHAPES['status']['required'], {})
        self.assertEqual(records.validate('status', {}), [])
        self.assertEqual(records.validate('status', {'live': 'true'}), ['live: expected bool'])
        full = {'title': 't', 'message': 'm', 'live': True, 'updatedAt': NOW, 'metrics': {'tests': 3}}
        self.assertEqual(records.validate('status', full), [])

    def test_a_document_that_is_not_an_object_is_one_error(self):
        for bad in (None, [], 'x', 5):
            with self.subTest(bad=bad):
                self.assertEqual(records.validate('status', bad), ['<document>: expected object'])

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            records.validate('answer', {})

    def test_errors_are_all_reported_together(self):
        d = without('run', 'label')
        d.update(seq='1', kind='odd')
        self.assertEqual(sorted(records.validate('run', d)),
                         sorted(['label: required field missing', 'seq: expected int',
                                 "kind: 'odd' is not one of %r" % records.SHAPES['run']['enums']['kind']]))


class Enums(unittest.TestCase):
    def test_run_kind(self):
        for k in ('running', 'done', 'go', 'changes', 'nogo', 'killed'):
            self.assertEqual(records.validate('run', doc('run', kind=k)), [], k)
        self.assertEqual(records.validate('run', doc('run', kind='approved')),
                         ["kind: 'approved' is not one of ['running', 'done', 'go', 'changes', 'nogo', 'killed']"])

    def test_run_lane(self):
        for lane in ('orch', 'req', 'plan', 'cw', 'tw', 'cr', 'ver', 'other', 'human'):
            self.assertEqual(records.validate('run', doc('run', lane=lane)), [], lane)
        self.assertEqual(records.validate('run', doc('run', lane='qa')),
                         ["lane: 'qa' is not one of ['orch', 'req', 'plan', 'cw', 'tw', 'cr', 'ver', 'other', 'human']"])

    def test_last_refresh_writer(self):
        for w in ('collector', 'refresher'):
            self.assertEqual(records.validate('lastRefresh', doc('lastRefresh', writer=w)), [], w)
        self.assertEqual(records.validate('lastRefresh', doc('lastRefresh', writer='page')),
                         ["writer: 'page' is not one of ['collector', 'refresher']"])

    def test_a_wrong_typed_enum_field_is_one_type_error(self):
        self.assertEqual(records.validate('run', doc('run', kind=5)), ['kind: expected str'])


class Nested(unittest.TestCase):
    def test_an_entry_kind_outside_the_enum_names_its_index(self):
        entries = [ENTRY, dict(ENTRY, id='eng:x', name='x'), dict(ENTRY, kind='skill'), dict(ENTRY, kind='tool')]
        self.assertEqual(records.validate('catalogue', doc('catalogue', entries=entries)),
                         ["entries[3].kind: 'tool' is not one of ['agent', 'skill']"])

    def test_an_entry_missing_installed(self):
        e = dict(ENTRY)
        del e['installed']
        self.assertEqual(records.validate('catalogue', doc('catalogue', entries=[ENTRY, e])),
                         ['entries[1].installed: required field missing'])

    def test_an_entry_that_is_not_an_object(self):
        self.assertEqual(records.validate('catalogue', doc('catalogue', entries=['eng:x'])), ['entries[0]: expected object'])

    def test_plugin_agents_not_an_int(self):
        self.assertEqual(records.validate('catalogue', doc('catalogue', plugins=[dict(PLUGIN, agents='1')])),
                         ['plugins[0].agents: expected int'])

    def test_skill_use_count_not_an_int(self):
        self.assertEqual(records.validate('session', doc('session', skillUses={'x': {'count': '2'}})),
                         ["skillUses['x'].count: expected int"])

    def test_skill_use_value_not_an_object(self):
        self.assertEqual(records.validate('session', doc('session', skillUses={'x': 2})), ["skillUses['x']: expected object"])

    def test_skill_use_last_is_optional_but_typed(self):
        self.assertEqual(records.validate('session', doc('session', skillUses={'x': {'count': 1}})), [])
        self.assertEqual(records.validate('session', doc('session', skillUses={'x': {'count': 1, 'last': 5}})),
                         ["skillUses['x'].last: expected str"])

    def test_skill_uses_not_an_object(self):
        self.assertEqual(records.validate('session', doc('session', skillUses=[])), ['skillUses: expected object'])

    def test_the_nested_rules_live_in_shapes(self):
        cat = records.SHAPES['catalogue']['required']
        self.assertEqual(cat['entries']['list_of']['enums'], {'kind': ['agent', 'skill']})
        self.assertIn('installed', cat['entries']['list_of']['required'])
        self.assertEqual(cat['plugins']['list_of']['required']['agents'], 'int')
        self.assertEqual(records.SHAPES['session']['required']['skillUses'],
                         {'map_of': {'required': {'count': 'int'}, 'optional': {'last': 'str'}}})


class Scalars(unittest.TestCase):
    def test_int_rejects_bool(self):
        self.assertEqual(records.validate('run', doc('run', seq=True)), ['seq: expected int'])
        self.assertEqual(records.validate('run', doc('run', tok=1.5)), ['tok: expected int'])

    def test_datetime_accepts_iso_times_with_a_timezone(self):
        for at in ('2026-09-11T12:00:00Z', '2026-09-11T12:00:00+01:00', '2026-09-11T12:00:00+0100',
                   '2026-09-11T12:00:00.123+00:00'):
            with self.subTest(at=at):
                self.assertEqual(records.validate('lastRefresh', doc('lastRefresh', at=at)), [])

    def test_datetime_rejects_a_time_without_a_timezone_or_that_does_not_parse(self):
        for at in ('2026-09-11T12:00:00', '2026-09-11', 'not a time', ''):
            with self.subTest(at=at):
                self.assertEqual(records.validate('lastRefresh', doc('lastRefresh', at=at)), ['at: expected datetime'])

    def test_datetime_with_a_non_string_is_a_type_error_and_never_raises(self):
        for at in (5, None, 1.5, True, ['2026-09-11T12:00:00Z'], {}):
            with self.subTest(at=at):
                self.assertEqual(records.validate('lastRefresh', doc('lastRefresh', at=at)), ['at: expected datetime'])

    def test_run_carries_start_end_agent_type_and_agent(self):
        full = doc('run', lane='other', start='2026-09-11T10:00:00.000Z', end='2026-09-11T10:29:00.000Z',
                   agentType='general-purpose', agent='general-purpose', group='A', **{'from': 'a1', 'feeds': 'a2'})
        self.assertEqual(records.validate('run', full), [])
        self.assertEqual(records.validate('run', doc('run', end=5)), ['end: expected str'])
        for field in ('start', 'end', 'agentType', 'agent'):
            self.assertIn(field, records.SHAPES['run']['optional'], field)
        self.assertIn('skillUses', records.SHAPES['session']['required'])

    def test_nullable_fields(self):
        self.assertEqual(records.validate('session', doc('session', start=None, last=None, project=None)), [])
        self.assertEqual(records.validate('session', doc('session', start=5)), ['start: expected str|null'])
        self.assertEqual(records.validate('project', doc('project', usage=None, last=None)), [])
        self.assertEqual(records.validate('project', doc('project', usage={'totals': {}}, last='2026-09-11T10:00:00Z')), [])
        self.assertEqual(records.validate('project', doc('project', usage=[])), ['usage: expected object|null'])
        self.assertEqual(records.validate('project', doc('project', last=0)), ['last: expected str|null'])
        self.assertEqual(records.validate('run', doc('run', project='alpha')), [])


class ShippedCopy(unittest.TestCase):
    def test_shapes_is_json_serialisable(self):
        self.assertEqual(json.loads(json.dumps(records.SHAPES)), records.SHAPES)

    def assert_copy_equals_shapes(self, path):
        with io.open(path, encoding='utf-8', newline='') as f:
            text = f.read()
        self.assertEqual(json.loads(text), records.SHAPES)
        # With core.autocrlf set and no .gitattributes, git checks the file out with CRLF line endings, so the
        # canonical text is compared with its newlines normalised.
        self.assertEqual(text.replace('\r\n', '\n'), json.dumps(records.SHAPES, indent=2, sort_keys=True) + '\n')

    def test_the_committed_json_copy_equals_shapes(self):
        self.assert_copy_equals_shapes(os.path.join(HERE, 'local', 'records.shapes.json'))

    def test_a_crlf_checkout_of_the_json_copy_still_equals_shapes(self):
        tmp = tempfile.mkdtemp(prefix='records-test-')
        self.addCleanup(shutil.rmtree, tmp, True)
        canonical = json.dumps(records.SHAPES, indent=2, sort_keys=True) + '\n'
        crlf = os.path.join(tmp, 'crlf.json')
        with io.open(crlf, 'wb') as f:
            f.write(canonical.replace('\n', '\r\n').encode('utf-8'))
        self.assert_copy_equals_shapes(crlf)
        # Only line endings are forgiven: a copy whose text differs otherwise still fails.
        reindented = os.path.join(tmp, 'reindented.json')
        with io.open(reindented, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(records.SHAPES, indent=4, sort_keys=True) + '\n')
        with self.assertRaises(AssertionError):
            self.assert_copy_equals_shapes(reindented)

    def test_write_shapes_writes_the_canonical_text(self):
        tmp = tempfile.mkdtemp(prefix='records-test-')
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, 'records.shapes.json')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(records.main(['--write-shapes'], path=path), 0)
        with io.open(path, 'rb') as f:
            written = f.read()
        self.assertEqual(written, (json.dumps(records.SHAPES, indent=2, sort_keys=True) + '\n').encode('utf-8'))

    def test_anything_else_on_the_command_line_is_a_usage_error(self):
        tmp = tempfile.mkdtemp(prefix='records-test-')
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, 'records.shapes.json')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(records.main([], path=path), 2)
            self.assertEqual(records.main(['--other'], path=path), 2)
        self.assertFalse(os.path.exists(path))


# ---------------------------------------------------------------- T4: rows and paths

class Rows(unittest.TestCase):
    def test_to_row_returns_exactly_the_table_columns(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = records.to_row(kind, IDS[kind], doc(kind))
                self.assertEqual(list(row), list(records.TABLES[kind][1]))
                self.assertEqual(row['id'], IDS[kind])

    def test_tables(self):
        self.assertEqual(records.TABLES, {
            'session': ('sessions', ('id', 'project', 'last', 'doc')),
            'run': ('runs', ('id', 'session', 'project', 'seq', 'start', 'doc')),
            'project': ('projects', ('id', 'ord', 'doc')),
            'tab': ('project_tabs', ('id', 'project', 'tab', 'doc')),
            'status': ('statuses', ('id', 'doc')),
            'lastRefresh': ('last_refresh', ('id', 'doc')),
            'catalogue': ('catalogue', ('id', 'doc')),
        })

    def test_the_doc_column_is_canonical_json(self):
        d = doc('session', title='Café ☕', zz=1)
        row = records.to_row('session', IDS['session'], d)
        self.assertEqual(row['doc'], json.dumps(d, sort_keys=True, ensure_ascii=False, allow_nan=False))
        self.assertIn('Café ☕', row['doc'])

    def test_to_row_then_from_row_returns_an_equal_document_for_every_kind(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                d = doc(kind, zzUnknown={'kept': True})
                row = records.to_row(kind, IDS[kind], d)
                self.assertEqual(records.from_row(kind, row), d)
                self.assertEqual(records.from_row(kind, row['doc']), d)

    def test_from_row_accepts_a_mapping_or_the_doc_text(self):
        text = json.dumps(VALID['tab'])
        self.assertEqual(records.from_row('tab', {'doc': text}), VALID['tab'])
        self.assertEqual(records.from_row('tab', {'id': 'alpha.spec', 'project': 'alpha', 'tab': 'spec', 'doc': text}), VALID['tab'])
        self.assertEqual(records.from_row('tab', text), VALID['tab'])

    def test_key_columns(self):
        s = records.to_row('session', 'sid-1', doc('session'))
        self.assertEqual((s['project'], s['last']), ('alpha', '2026-09-11T11:00:00.000Z'))
        s = records.to_row('session', 'sid-1', doc('session', project=None, last=None))
        self.assertEqual((s['project'], s['last']), (None, None))
        r = records.to_row('run', 'a1', doc('run', project='alpha', seq=4, start='2026-09-11T10:00:00Z'))
        self.assertEqual((r['session'], r['project'], r['seq'], r['start']), ('sid-1', 'alpha', 4, '2026-09-11T10:00:00Z'))
        r = records.to_row('run', 'a1', doc('run'))
        self.assertEqual((r['project'], r['start']), (None, None))
        self.assertEqual(records.to_row('project', 'alpha', doc('project', order=3))['ord'], 3)

    def test_tab_columns_come_from_the_id(self):
        t = records.to_row('tab', 'beta_2.decisions', {'generatedAt': NOW, 'project': 'wrong', 'tab': 'wrong'})
        self.assertEqual((t['project'], t['tab']), ('beta_2', 'decisions'))

    def test_an_invalid_document_raises_listing_the_errors(self):
        with self.assertRaises(ValueError) as cm:
            records.to_row('run', 'a1', doc('run', kind='approved', tok='1'))
        self.assertIn("kind: 'approved' is not one of", str(cm.exception))
        self.assertIn('tok: expected int', str(cm.exception))
        with self.assertRaises(ValueError):
            records.from_row('run', json.dumps(doc('run', kind='approved')))
        with self.assertRaises(ValueError):
            records.from_row('run', '[1, 2]')
        with self.assertRaises(ValueError):
            records.from_row('run', 'not json')

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            records.to_row('session', 'sid-1', doc('session', usage={'effective': float('nan')}))
        with self.assertRaises(ValueError):
            records.to_row('status', 'meta/status', {'metrics': {'coverage': float('inf')}})
        with self.assertRaises(ValueError):
            records.from_row('status', '{"metrics": {"coverage": NaN}}')

    def test_from_row_rejects_infinity_and_numbers_too_large_for_a_float(self):
        for text in ('{"metrics": {"coverage": Infinity}}', '{"metrics": {"coverage": -Infinity}}',
                     '{"metrics": {"coverage": 1e999}}', '{"metrics": {"coverage": -1e999}}',
                     '{"metrics": {"coverage": 1E400}}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    records.from_row('status', text)
        self.assertEqual(records.from_row('status', '{"metrics": {"coverage": 1.5e308, "tests": 3}}'),
                         {'metrics': {'coverage': 1.5e308, 'tests': 3}})

    def test_to_row_raises_value_error_for_a_value_json_cannot_hold(self):
        for bad in ({1: 'a', 'b': 2}, {'s': {1, 2}}, {'b': b'x'}):
            with self.subTest(metrics=bad):
                with self.assertRaises(ValueError):
                    records.to_row('status', 'meta/status', {'metrics': bad})
        with self.assertRaises(ValueError):
            records.to_row('tab', 'alpha.spec', {'generatedAt': NOW, 1: 'mixed key types at the top'})

    def test_to_row_rejects_a_value_that_would_come_back_different(self):
        for bad in ({'pair': (1, 2)}, {1: 'a'}, {True: 'a'}, {None: 'a'}, {1.5: 'a'}):
            with self.subTest(metrics=bad):
                with self.assertRaises(ValueError):
                    records.to_row('status', 'meta/status', {'metrics': bad})
        with self.assertRaises(ValueError):
            records.to_row('tab', 'alpha.spec', doc('tab', zzExtra=('a', 'b')))

    def test_from_row_rejects_anything_but_text_or_a_mapping_holding_doc_text(self):
        text = json.dumps(VALID['tab'])
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        no_doc = conn.execute("SELECT 'alpha.spec' AS id").fetchone()
        blob_doc = conn.execute('SELECT ? AS doc', (text.encode('utf-8'),)).fetchone()
        for bad in (text.encode('utf-8'), bytearray(text, 'utf-8'), None, 5, (text,), [text],
                    {'id': 'alpha.spec'}, {'doc': None}, {'doc': text.encode('utf-8')}, {'doc': 5},
                    {'doc': VALID['tab']}, no_doc, blob_doc):
            with self.subTest(row=bad):
                with self.assertRaises(ValueError):
                    records.from_row('tab', bad)
        self.assertEqual(records.from_row('tab', conn.execute('SELECT ? AS doc', (text,)).fetchone()), VALID['tab'])

    def test_an_unknown_kind_raises(self):
        for call in (lambda: records.to_row('answer', 'x', {}), lambda: records.from_row('answer', '{}'),
                     lambda: records.store_path('answer', 'x')):
            with self.assertRaises(ValueError):
                call()


class Paths(unittest.TestCase):
    def test_store_path_for_every_kind(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(records.store_path(kind, IDS[kind]), PATHS[kind])
        self.assertEqual(records.store_path('status', 'meta/status'), 'meta/status')
        self.assertEqual(records.store_path('tab', 'a-b_C9.git'), 'projectTabs/a-b_C9.git')
        self.assertEqual(records.store_path('run', 'orch-adrs-spec'), 'runs/orch-adrs-spec')
        self.assertEqual(records.store_path('session', 'a.b'), 'sessions/a.b')
        self.assertEqual(records.store_path('session', 'a b'), 'sessions/a b')
        self.assertEqual(records.store_path('run', '...'), 'runs/...')

    def test_collection(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                coll = records.COLLECTION[kind]
                self.assertEqual(records.store_path(kind, IDS[kind]), IDS[kind] if coll is None else coll + '/' + IDS[kind])

    BAD = {
        'session': ['a/b', 'a\\b', '.', '..', 'a\x00b', 'a\x1fb', 'a\x7fb', 'a\x85b', 'a\nb', ''],
        'run': ['a/b', 'a\\b', '.', '..', 'a\tb', 'a\rb', 'a\x9fb', ''],
        'project': ['a/b', 'a b', 'a.b', 'x' * 101, 'ü', ''],
        'tab': ['alpha', 'alpha.usage', 'alpha.spec.git', 'bad id.spec', 'a/b.spec', '.spec', 'alpha.spec/x',
                'x' * 101 + '.spec', 'alpha.Spec', ''],
        'status': ['tabs/x', 'meta/a/b', 'meta/', 'status/a.b', 'meta', 'META/x', 'sessions/x', ''],
        'lastRefresh': ['lastrefresh', 'meta/lastRefresh', 'last_refresh', ''],
        'catalogue': ['main', 'index.json', 'catalogue/index', ''],
    }

    def test_a_bad_id_form_raises_for_every_kind(self):
        for kind, bad in self.BAD.items():
            # Session and run ids have no fixed alphabet, so a space is allowed in them; every other form has one.
            spaced = [] if kind in ('session', 'run') else [' ' + IDS[kind]]
            for rid in bad + spaced + [None, 5, IDS[kind] + '\n', '\n' + IDS[kind]]:
                with self.subTest(kind=kind, id=rid):
                    with self.assertRaises(ValueError):
                        records.store_path(kind, rid)
                    with self.assertRaises(ValueError):
                        records.to_row(kind, rid, doc(kind))
                    with self.assertRaises(ValueError):
                        records.from_row(kind, {'id': rid, 'doc': json.dumps(doc(kind))})

    def test_meta_last_refresh_is_reserved_from_status(self):
        with self.assertRaises(ValueError):
            records.store_path('status', 'meta/lastRefresh')
        with self.assertRaises(ValueError):
            records.to_row('status', 'meta/lastRefresh', {})
        self.assertEqual(records.store_path('lastRefresh', 'lastRefresh'), 'meta/lastRefresh')

    def test_the_status_form_matches_board_config_except_the_reserved_id(self):
        samples = ['meta/status', 'status/dispatch-board', 'status/a_b-C9', 'meta/lastRefresh', 'meta/lastrefresh',
                   'meta/' + 'x' * 100, 'meta/' + 'x' * 101, 'status/', 'meta/', 'other/x', 'meta/a.b', 'meta/a/b',
                   'META/status', ' meta/x', 'meta/x ', 'status/ü', 'meta\\x', 'status/x\ty', '', 'status',
                   'status/x\ny']
        for s in samples:
            self.assertFalse(s.endswith('\n'), s)
            with self.subTest(id=s):
                expected = bool(board_config.STATUS_DOC.match(s)) and s != 'meta/lastRefresh'
                try:
                    records.store_path('status', s)
                    accepted = True
                except ValueError:
                    accepted = False
                self.assertEqual(accepted, expected)

    def test_a_trailing_newline_is_rejected_where_board_config_accepts_it(self):
        self.assertTrue(board_config.STATUS_DOC.match('meta/status\n'))
        self.assertTrue(board_config.ID.match('alpha\n'))
        with self.assertRaises(ValueError):
            records.store_path('status', 'meta/status\n')
        with self.assertRaises(ValueError):
            records.store_path('project', 'alpha\n')


if __name__ == '__main__':
    unittest.main()
