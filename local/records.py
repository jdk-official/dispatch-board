"""The local-first app's records: their shapes, ids, store paths and SQLite rows.

A record is identical to the store document the v1 exporters publish today and maps one-to-one to a store
path, so a later host changes only storage and transport, never the documents.

SHAPES is the one definition of what a record may hold; validate() reads no rule from anywhere else. Code that
cannot import Python reads the same table from records.shapes.json, which is SHAPES as JSON. Regenerate it after
changing SHAPES:

    python local/records.py --write-shapes

This module imports nothing local (schema.py imports it for TABLES), so the dependency runs one way.
"""
import io, json, math, os, re, sqlite3, sys
from collections.abc import Mapping
from datetime import datetime

# SHAPES = {kind: SPEC}; SPEC = {"required": {field: TYPE}, "optional": {field: TYPE}, "enums": {field: [values]}},
# where "enums", and in a nested SPEC also "optional", may be left out. A TYPE is a scalar name from _SCALARS, a
# "|" union of them such as "str|null", {"list_of": TYPE} (a list whose items are that TYPE -- a scalar list when
# TYPE is a scalar name or union, a list of objects when TYPE is itself a SPEC), {"map_of": SPEC} (an object whose
# values are objects matching SPEC) or {"object": SPEC} (a single nested object matching SPEC, for a field that
# holds one sub-object rather than a list or map of them). Fields a SPEC does not list are allowed, and kept, at
# every level.
# Required means the v1 exporter writes the field on every document. Run and session times stay "str" because
# the exporter also passes times without a timezone; only lastRefresh.at, which staleness is computed from, is
# a strict "datetime".
SHAPES = {
    'session': {
        'required': {
            'title': 'str', 'folder': 'str', 'cwd': 'str', 'start': 'str|null', 'last': 'str|null',
            'project': 'str|null', 'build': 'bool', 'windowDays': 'int', 'windowMinutes': 'int', 'runs': 'int',
            'running': 'int', 'usage': 'object',
            'skillUses': {'map_of': {'required': {'count': 'int'}, 'optional': {'last': 'str'}}},
        },
        'optional': {
            'firstPrompt': 'str',
            # Matches exporters/derive.py waiting_of() exactly: at most one question, then the newest refusals,
            # and "more" only when refusals were left out for the cap.
            'waiting': {'object': {
                'required': {
                    'questions': {'list_of': {'required': {'at': 'str|null', 'question': 'str', 'source': 'str'},
                                               'enums': {'source': ['ask', 'prose']}}},
                    'refusals': {'list_of': {'required': {
                        'at': 'str|null', 'kind': 'str', 'tool': 'str|null', 'detail': 'str'}}},
                },
                'optional': {'more': 'int'},
            }},
        },
    },
    'run': {
        'required': {
            'session': 'str', 'project': 'str|null', 'seq': 'int', 'lane': 'str', 'label': 'str', 'kind': 'str',
            'verdict': 'str', 'tok': 'int', 'min': 'int',
        },
        'optional': {
            'from': 'str', 'feeds': 'str', 'group': 'str', 'agent': 'str', 'agentType': 'str', 'start': 'str',
            'end': 'str', 'files': {'list_of': 'str'},
            'findings': {'list_of': {'required': {
                'id': 'str', 'severity': 'str', 'title': 'str', 'location': 'str', 'remediation': 'str'}}},
        },
        'enums': {
            'kind': ['running', 'done', 'go', 'changes', 'nogo', 'killed'],
            # The exporter's lanes and its "other" fallback, plus "human", the page's lane for owner rows.
            'lane': ['orch', 'req', 'plan', 'cw', 'tw', 'cr', 'ver', 'other', 'human'],
        },
    },
    'project': {
        'required': {
            'name': 'str', 'repoPath': 'str', 'branch': 'str', 'sessions': 'list', 'statusDoc': 'str', 'order': 'int',
            'runs': 'int', 'running': 'int', 'last': 'str|null', 'usage': 'object|null',
        },
        'optional': {},
    },
    'tab': {
        'required': {'generatedAt': 'str'},
        'optional': {'source': 'str'},
    },
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
                'plugin': 'str', 'purpose': 'str', 'purposeFull': 'str', 'installed': 'bool', 'agents': 'int',
                'skills': 'int'}}},
            # validate() does not check that id equals "<plugin>:<name>": the exporter guarantees it.
            'entries': {'list_of': {'required': {
                'id': 'str', 'kind': 'str', 'plugin': 'str', 'name': 'str', 'description': 'str', 'installed': 'bool'},
                'enums': {'kind': ['agent', 'skill']}}},
        },
        'optional': {'source': 'object'},
    },
}

SHAPES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'records.shapes.json')

# The store collection each kind's documents live in; a status id already names its own ("meta" or "status").
COLLECTION = {'session': 'sessions', 'run': 'runs', 'project': 'projects', 'tab': 'projectTabs', 'status': None,
              'lastRefresh': 'meta', 'catalogue': 'catalogue'}
LAST_REFRESH_PATH = 'meta/lastRefresh'
TAB_NAMES = ('spec', 'assumptions', 'decisions', 'backlog', 'git', 'findings')

# Every form is applied with fullmatch: re.match with "$" would also accept a trailing newline. That makes the
# project and status forms stricter than board_config.ID and STATUS_DOC, but only for strings ending in one.
_PROJECT_ID = r'[A-Za-z0-9_-]{1,100}'
# Session and run ids come from transcripts and the config, not a fixed alphabet, so they are only kept to one
# safe path segment: no separator of either kind, no C0 or C1 control character, and not "." or "..".
_SEGMENT = re.compile(r'(?!\.\.?\Z)[^/\\\x00-\x1f\x7f-\x9f]+')
_ID_FORMS = {
    'session': _SEGMENT,
    'run': _SEGMENT,
    'project': re.compile(_PROJECT_ID),
    'tab': re.compile(r'%s\.(?:%s)' % (_PROJECT_ID, '|'.join(TAB_NAMES))),
    'status': re.compile(r'(?:meta|status)/[A-Za-z0-9_-]{1,100}'),
    'lastRefresh': re.compile('lastRefresh'),
    'catalogue': re.compile('index'),
}

# {kind: (table, columns)}. "doc" holds the record as canonical JSON and is the source of truth; the other
# columns are copies of it kept for lookups and indexes, except a tab's project and tab, which come from its id
# because a tab document does not name itself.
TABLES = {
    'session': ('sessions', ('id', 'project', 'last', 'doc')),
    'run': ('runs', ('id', 'session', 'project', 'seq', 'start', 'doc')),
    'project': ('projects', ('id', 'ord', 'doc')),
    'tab': ('project_tabs', ('id', 'project', 'tab', 'doc')),
    'status': ('statuses', ('id', 'doc')),
    'lastRefresh': ('last_refresh', ('id', 'doc')),
    'catalogue': ('catalogue', ('id', 'doc')),
}
_DOC_FIELD = {'ord': 'order'}  # a key column named differently from the document field it copies


def _is_datetime(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


_SCALARS = {
    'str': lambda v: isinstance(v, str),
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    'bool': lambda v: isinstance(v, bool),
    'null': lambda v: v is None,
    'list': lambda v: isinstance(v, list),
    'object': lambda v: isinstance(v, dict),
    'datetime': _is_datetime,
}


def _spec(kind):
    if kind not in SHAPES:
        raise ValueError('unknown record kind %r' % (kind,))
    return SHAPES[kind]


def _check_value(typ, value, path, errors):
    """Append the errors for one value checked against a TYPE; returns True when there were none."""
    before = len(errors)
    if isinstance(typ, dict) and 'list_of' in typ:
        if not isinstance(value, list):
            errors.append('%s: expected list' % path)
        else:
            item_type = typ['list_of']
            for i, item in enumerate(value):
                item_path = '%s[%d]' % (path, i)
                if isinstance(item_type, str):
                    _check_value(item_type, item, item_path, errors)
                else:
                    _check_spec(item_type, item, item_path, errors)
    elif isinstance(typ, dict) and 'map_of' in typ:
        if not isinstance(value, dict):
            errors.append('%s: expected object' % path)
        else:
            for key, item in value.items():
                _check_spec(typ['map_of'], item, '%s[%r]' % (path, key), errors)
    elif isinstance(typ, dict) and 'object' in typ:
        if not isinstance(value, dict):
            errors.append('%s: expected object' % path)
        else:
            _check_spec(typ['object'], value, path, errors)
    elif isinstance(typ, str) and all(name in _SCALARS for name in typ.split('|')):
        if not any(_SCALARS[name](value) for name in typ.split('|')):
            errors.append('%s: expected %s' % (path, typ))
    else:
        raise ValueError('SHAPES holds an unknown TYPE %r at %s' % (typ, path))
    return len(errors) == before


def _check_spec(spec, doc, path, errors):
    if not isinstance(doc, dict):
        errors.append('%s: expected object' % (path or '<document>'))
        return
    at = lambda field: '%s.%s' % (path, field) if path else field
    typed = {}
    for field, typ in spec['required'].items():
        if field not in doc:
            errors.append('%s: required field missing' % at(field))
        else:
            typed[field] = _check_value(typ, doc[field], at(field), errors)
    for field, typ in spec.get('optional', {}).items():
        if field in doc:
            typed[field] = _check_value(typ, doc[field], at(field), errors)
    for field, values in spec.get('enums', {}).items():
        # A value of the wrong type already has its error; listing the enum as well would only repeat it.
        if field in doc and typed.get(field, True) and doc[field] not in values:
            errors.append('%s: %r is not one of %r' % (at(field), doc[field], values))


def validate(kind, doc):
    """The ways doc breaks SHAPES[kind], one path-qualified string each; [] when it conforms. doc is not
    changed, and fields SHAPES does not list are allowed. Id forms are not checked here (a tab document does not
    carry its own name): store_path and to_row check them. Raises ValueError only for an unknown kind."""
    errors = []
    _check_spec(_spec(kind), doc, '', errors)
    return errors


def _check_id(kind, record_id):
    _spec(kind)
    form = _ID_FORMS[kind]
    # meta/lastRefresh belongs to the lastRefresh record, so no status document may take that path.
    if not isinstance(record_id, str) or not form.fullmatch(record_id) or (kind == 'status' and record_id == LAST_REFRESH_PATH):
        raise ValueError('%r is not a valid %s id' % (record_id, kind))


def store_path(kind, record_id):
    """The store path of the record with this id, such as "sessions/<id>". Raises ValueError for an unknown kind or
    an id not in the kind's form."""
    _check_id(kind, record_id)
    coll = COLLECTION[kind]
    return record_id if coll is None else coll + '/' + record_id


def to_row(kind, record_id, doc):
    """The SQLite row for a record, as {column: value} over TABLES[kind]'s columns, in order.

    Every failure is a ValueError: a bad id; a document that does not validate (listing every error); a value
    JSON cannot hold, such as NaN, infinity, a set, bytes or keys of mixed types; or a value JSON would give back
    changed, such as a tuple (read back as a list) or a key that is not a string (read back as one)."""
    _check_id(kind, record_id)
    errors = validate(kind, doc)
    if errors:
        raise ValueError('invalid %s record %r: %s' % (kind, record_id, '; '.join(errors)))
    try:
        text = json.dumps(doc, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as e:
        raise ValueError('%s record %r cannot be stored as JSON: %s' % (kind, record_id, e)) from e
    # json.dumps quietly turns a tuple into a list and a non-string key into a string, so such a record would
    # come back from from_row as a different document; refuse it rather than store something else.
    if json.loads(text) != doc:
        raise ValueError('%s record %r would not read back unchanged: it holds a tuple or a key that is not a string'
                         % (kind, record_id))
    from_id = dict(zip(('project', 'tab'), record_id.split('.', 1))) if kind == 'tab' else {}
    row = {}
    for col in TABLES[kind][1]:
        if col == 'id':
            row[col] = record_id
        elif col == 'doc':
            row[col] = text
        elif col in from_id:
            row[col] = from_id[col]
        else:
            row[col] = doc.get(_DOC_FIELD.get(col, col))
    return row


def _no_constant(name):
    raise ValueError('%s is not valid in a stored record' % name)


def _finite_float(text):
    # float() gives infinity for a literal too large for it, such as 1e999, rather than raising.
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('%s is too large to be a stored number' % text)
    return value


def from_row(kind, row):
    """The document a row holds. row is the doc text itself (a str) or a mapping, such as a dict or a sqlite3.Row,
    whose "doc" column holds that text as a str.

    Every failure is a ValueError: any other row (bytes, None, a tuple, a mapping with no "doc" or a doc that is
    not a str); text that is not JSON, or holds NaN, Infinity or a number too large for a float, such as 1e999;
    a document that does not validate; and a row whose "id" is not in the kind's form."""
    _spec(kind)
    if isinstance(row, str):
        text = row
    elif isinstance(row, (Mapping, sqlite3.Row)):
        if 'id' in row.keys():
            _check_id(kind, row['id'])
        if 'doc' not in row.keys() or not isinstance(row['doc'], str):
            raise ValueError('a %s row needs a "doc" column holding JSON text' % kind)
        text = row['doc']
    else:
        raise ValueError('a %s row is JSON text or a mapping with a "doc" column, not %s' % (kind, type(row).__name__))
    doc = json.loads(text, parse_constant=_no_constant, parse_float=_finite_float)
    errors = validate(kind, doc)
    if errors:
        raise ValueError('invalid %s record: %s' % (kind, '; '.join(errors)))
    return doc


def main(argv=None, path=SHAPES_PATH):
    """--write-shapes writes SHAPES to path as indented, key-sorted JSON; returns the exit code."""
    argv = sys.argv[1:] if argv is None else argv
    if list(argv) != ['--write-shapes']:
        print('usage: python local/records.py --write-shapes', file=sys.stderr)
        return 2
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(SHAPES, indent=2, sort_keys=True) + '\n')
    print('wrote %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
