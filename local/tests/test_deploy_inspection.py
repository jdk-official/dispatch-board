"""AC-70 as an exercised check rather than a read one: the collector's and the local server's source invokes no
`claude` command and names no Anthropic host, so refreshing the board costs no Claude usage and needs no open
session (NFR-17).

What it proves. Every module is parsed, and: no string literal names a claude executable; the raw text holds no
bare lowercase `claude` token, which is what an invocation would look like however its arguments are built; every
process launch - subprocess's launchers, os.system, os.popen, os.startfile and the os exec and spawn families,
with the program given positionally or as `args=` - whose program can be read statically names a program on the
allow-list, and every one whose program cannot be read is on a hand-checked list that counts the call sites in
each function, so a second site inside a listed function fails as surely as one in a new function; every import
by a built name is on a hand-checked list counted the same way, and an import by a literal name (`__import__`,
`importlib.import_module`) names neither a network-client module nor socket or ctypes; no network-client module
(ssl, _socket, imaplib, poplib, socketserver and multiprocessing.connection included) is imported, either by
name or as a submodule read off a package that is imported (`import http.server`, then `http.client`); socket
is used only for the two attributes a listener needs and ctypes only for the drive-type call, whether they are
imported plainly, under an alias, as a submodule (`import ctypes.wintypes`) or name by name, and in that last
case every attribute read off the imported name (`from ctypes import windll`, then `windll.kernel32...`) counts
too; and the raw text of each file, comments and docstrings included, holds no Anthropic or claude.ai host. The
same host and claude-executable checks cover the exporter modules the collector imports, and that list is
checked against the real imports so it cannot fall behind them.

What it cannot prove. It is a tripwire, not a proof. A program name or host assembled at run time out of pieces
that never spell `claude` or a host, or read out of the config, would pass. So would anything reached without
being named where it is used: a launcher, a module or an attribute of one kept under another name
(`go = subprocess.run`, `k = ctypes.windll`), a module fetched with getattr or out of sys.modules, code run
through exec or eval, a module passed around as a value, or a module re-exported by an exporter
(`export_board.urllib`). The hand-checked lists count sites rather than read them, so a reviewed site replaced by
a different one in the same function, leaving the count unchanged, would pass too. The launch, import, socket
and ctypes checks read `local/` only, not the exporters. All of these are visible in a diff, and each allow-list
below fails as soon as something new appears, which is the point at which a reviewer is asked to look.
"""
import ast, collections, io, os, re, unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCAL = os.path.join(REPO, 'local')
DEPLOY = os.path.join(LOCAL, 'deploy')
EXPORTERS = os.path.join(REPO, 'exporters')
# The exporter modules the collector and the server import, so the check covers the source they really run.
IMPORTED = ['board_config.py', 'derive.py', 'export_board.py', 'export_catalogue.py', 'export_sessions.py']

# git for the repository facts in the tab records, schtasks to register the log-on tasks. Nothing else.
ALLOWED_PROGRAMS = {'git', 'schtasks'}
CLAUDE_EXE = re.compile(r'(^|[\\/])claude(\.exe|\.cmd|\.bat|\.ps1)?$', re.IGNORECASE)
# A bare lowercase `claude` token anywhere in the text: what the command is called on a command line. The
# lower case and the boundaries are what let the prose "Claude Code" and the path fragment ".claude" through.
CLAUDE_TOKEN = re.compile(r'(?<![\w.$/\\-])claude(?![\w-])')
HOSTS = re.compile(r'anthropic\.com|claude\.ai|/v1/messages', re.IGNORECASE)
NETWORK_MODULES = {'urllib', 'urllib.request', 'urllib3', 'http.client', 'httplib', 'requests', 'httpx',
                   'ftplib', 'smtplib', 'telnetlib', 'xmlrpc', 'xmlrpc.client', 'webbrowser', 'asyncio', 'ssl',
                   '_socket', 'imaplib', 'poplib', 'socketserver', 'multiprocessing.connection'}
# Allowed as plain imports, where the attribute checks below read what is taken off them, but never as an import
# by a literal name, where those checks cannot follow the module that comes back.
WATCHED_ROOTS = {'socket', 'ctypes'}
# socket is imported by server.py to bind the listener; these are the only two attributes a listener needs.
ALLOWED_SOCKET_ATTRS = {'AF_INET', 'timeout'}
# ctypes is imported by db.py to ask Windows whether the database is on a network drive, and for nothing else.
ALLOWED_CTYPES_ATTRS = {'windll', 'kernel32', 'GetDriveTypeW'}
# The launchers themselves plus the two seams this tree puts in front of them (tabs.run, tasks._run), so a
# command handed to a seam is read at the call site where it is still a literal.
COMMAND_CALLS = {'run', '_run', 'Popen', 'call', 'check_call', 'check_output', 'system', 'popen', 'startfile',
                 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe',
                 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe',
                 'posix_spawn', 'posix_spawnp'}
# Launch-shaped calls whose program is a variable, as (file, enclosing function): number of such call sites, each
# read by hand. tasks._run is the seam that hands its callers' literal schtasks commands to subprocess (those
# literals are read at the call sites), and run_local.main calls the wrapper's own run(), which launches nothing.
# The count is what makes a new site inside one of these functions fail rather than pass as already read.
UNREADABLE_LAUNCHES = {('tasks.py', '_run'): 1, ('run_local.py', 'main'): 1}
IMPORT_CALLS = {'import_module', '__import__'}
# run_local._entry imports the target named on its command line, which argparse limits to collector or server.
DYNAMIC_IMPORTS = {('run_local.py', '_entry'): 1}


def source_files():
    found = [os.path.join(LOCAL, n) for n in sorted(os.listdir(LOCAL)) if n.endswith('.py')]
    found += [os.path.join(DEPLOY, n) for n in sorted(os.listdir(DEPLOY)) if n.endswith('.py')]
    return found


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


def literals(tree):
    """Every string constant that is not a module, class or function docstring."""
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, 'body', [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def calls(tree, names, keywords=('args', 'name')):
    """(enclosing function name or None, first argument) for every call to a function or method in names that is
    given one, positionally or by one of the keywords."""
    out = []

    def visit(node, where):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            where = node.name
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', None)
            if name in names:
                arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg in keywords), None)
                if arg is not None:
                    out.append((where, arg))
        for child in ast.iter_child_nodes(node):
            visit(child, where)
    visit(tree, None)
    return out


def _string(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _program(arg):
    """The program a launch names, or None when it cannot be read statically."""
    if isinstance(arg, (ast.List, ast.Tuple)):
        return _string(arg.elts[0]) if arg.elts else None
    return _string(arg)


def called_programs(tree):
    """The program of every call that looks like a process launch, where it can be read statically."""
    return [p for p in (_program(arg) for _, arg in calls(tree, COMMAND_CALLS)) if p is not None]


def unreadable_launches(tree):
    """Enclosing function: number of launch-shaped calls in it whose program cannot be read statically."""
    return collections.Counter(where for where, arg in calls(tree, COMMAND_CALLS) if _program(arg) is None)


def dynamic_imports(tree):
    """(enclosing function, module name or None when it is not a literal) for every import_module or __import__."""
    return [(where, _string(arg)) for where, arg in calls(tree, IMPORT_CALLS)]


def built_imports(tree):
    """Enclosing function: number of imports in it whose module name is not a literal."""
    return collections.Counter(where for where, name in dynamic_imports(tree) if name is None)


def watched(name):
    """Whether a module named by a literal import is one this check watches."""
    return name in NETWORK_MODULES or name.split('.')[0] in WATCHED_ROOTS


def reached_modules(tree):
    """Every dotted name read off an imported package by attribute, prefixes included. `import http.server`
    binds `http`, so `http.client.HTTPSConnection` reaches http.client without an import naming it."""
    roots = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            parts, root = [], node
            while isinstance(root, ast.Attribute):
                parts.append(root.attr)
                root = root.value
            if isinstance(root, ast.Name) and root.id in roots:
                name = roots[root.id]
                for part in reversed(parts):
                    name += '.' + part
                    out.add(name)
    return out


def network_modules(tree):
    """The network-client modules a file imports, or reaches as a submodule of a package it imports."""
    return (imported_modules(tree) | reached_modules(tree)) & NETWORK_MODULES


def module_uses(tree, module):
    """The names a file takes from a module: imported by name, or read off it as an attribute chain, under its
    own name or an alias. A submodule imported (`import ctypes.wintypes`) counts as a name taken, and so does
    every attribute read off a name imported from the module (`from ctypes import windll`)."""
    bound, used, prefix = set(), set(), module + '.'
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == module or a.name.startswith(prefix):
                    bound.add(a.asname or module)
                    used |= set(a.name.split('.')[1:])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module \
                and (node.module == module or node.module.startswith(prefix)):
            used |= set(node.module.split('.')[1:])
            for a in node.names:
                used.add(a.name)
                bound.add(a.asname or a.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            root = node.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in bound:
                used.add(node.attr)
    return used


def exporter_imports():
    """The exporter modules the local sources import, directly or through another exporter, as file names."""
    exporters = {n[:-3] for n in os.listdir(EXPORTERS) if n.endswith('.py')}

    def imports(path):
        return {m.split('.')[0] for m in imported_modules(ast.parse(read(path)))} & exporters
    todo, seen = set().union(*(imports(p) for p in source_files())), set()
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo |= imports(os.path.join(EXPORTERS, name + '.py'))
    return sorted(n + '.py' for n in seen)


def imported_modules(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
            out |= {'%s.%s' % (node.module, a.name) for a in node.names}
    return out


class TheCheckIsNotVacuous(unittest.TestCase):
    def test_it_covers_the_collector_the_server_and_the_deployment(self):
        names = {os.path.basename(p) for p in source_files()}
        self.assertLessEqual({'collector.py', 'server.py', 'db.py', 'records.py', 'schema.py', 'tabs.py',
                              'run_local.py', 'tasks.py'}, names)

    def test_the_patterns_catch_what_they_are_for(self):
        for bad in ('claude', 'claude.exe', 'C:\\bin\\claude', '/usr/local/bin/claude'):
            self.assertRegex(bad, CLAUDE_EXE)
        for ok in ('Claude Code transcripts', '~/.claude/plugins', 'claudette'):
            self.assertNotRegex(ok, CLAUDE_EXE)
        for bad in ('claude -p "go"', "os.system('claude --print')", 'run([\'claude\'])'):
            self.assertRegex(bad, CLAUDE_TOKEN)
        for ok in ('Claude Code transcripts', '~/.claude/plugins', 'claudette', 'the claude-code plugin'):
            self.assertNotRegex(ok, CLAUDE_TOKEN)
        for bad in ('https://api.anthropic.com/v1/messages', 'https://claude.ai/code/artifact/x'):
            self.assertRegex(bad, HOSTS)

    def test_the_launch_scan_reads_keyword_and_os_level_launches(self):
        self.assertEqual(called_programs(ast.parse("subprocess.Popen(args=['curl', 'x'])")), ['curl'])
        self.assertEqual(called_programs(ast.parse("os.startfile('evil.exe')")), ['evil.exe'])
        self.assertEqual(called_programs(ast.parse("os.execv('/bin/sh', ['sh'])")), ['/bin/sh'])
        self.assertEqual(called_programs(ast.parse("os.spawnv(0, 'x.exe', ['x'])")), [])  # mode first: unreadable
        self.assertEqual(unreadable_launches(ast.parse("os.spawnv(0, 'x.exe', ['x'])")), {None: 1})

    def test_a_launch_whose_program_is_a_variable_is_caught_where_it_is(self):
        self.assertEqual(unreadable_launches(ast.parse('def f(cmd):\n    subprocess.run(cmd)\n')), {'f': 1})

    def test_a_second_unreadable_site_inside_the_same_function_is_counted(self):
        tree = ast.parse('def f(cmd):\n    subprocess.run(cmd)\n    os.system(cmd)\n')
        self.assertEqual(unreadable_launches(tree), {'f': 2})
        tree = ast.parse('def g(t):\n    importlib.import_module(t)\n    __import__(t)\n')
        self.assertEqual(built_imports(tree), {'g': 2})

    def test_a_built_import_name_is_caught(self):
        self.assertEqual(dynamic_imports(ast.parse("importlib.import_module('urll' + 'ib.request')")), [(None, None)])
        self.assertEqual(dynamic_imports(ast.parse("__import__('ssl')")), [(None, 'ssl')])

    def test_a_literal_import_of_any_watched_module_is_caught(self):
        for name in ('socket', '_socket', 'ctypes', 'ctypes.wintypes', 'ssl', 'http.client', 'imaplib', 'poplib',
                     'socketserver', 'multiprocessing.connection'):
            self.assertTrue(watched(name), name)
        for name in ('collector', 'server', 'http.server', 'json', 'multiprocessing'):
            self.assertFalse(watched(name), name)

    def test_the_module_scan_reads_from_imports_aliases_and_attribute_chains(self):
        self.assertEqual(module_uses(ast.parse('from socket import create_connection'), 'socket'),
                         {'create_connection'})
        self.assertEqual(module_uses(ast.parse('import socket as s\ns.create_connection(x)'), 'socket'),
                         {'create_connection'})
        self.assertIn('CreateProcessW',
                      module_uses(ast.parse('import ctypes\nctypes.windll.kernel32.CreateProcessW(0)'), 'ctypes'))
        self.assertIn('ssl', NETWORK_MODULES)

    def test_the_module_scan_follows_names_taken_by_name_and_dotted_imports(self):
        self.assertIn('CreateProcessW',
                      module_uses(ast.parse('from ctypes import windll\nwindll.kernel32.CreateProcessW(0)'), 'ctypes'))
        self.assertIn('CreateProcessW', module_uses(
            ast.parse('import ctypes.wintypes\nctypes.windll.kernel32.CreateProcessW(0)'), 'ctypes'))
        self.assertIn('wintypes', module_uses(ast.parse('import ctypes.wintypes'), 'ctypes'))
        self.assertIn('wintypes', module_uses(ast.parse('from ctypes.wintypes import DWORD'), 'ctypes'))

    def test_the_network_scan_reads_unwatched_names_and_submodules_reached_through_a_package(self):
        for src, want in (('import http.server\nhttp.client.HTTPSConnection("x")', {'http.client'}),
                          ('import _socket', {'_socket'}),
                          ('import imaplib', {'imaplib'}),
                          ('import poplib', {'poplib'}),
                          ('import socketserver', {'socketserver'}),
                          ('from multiprocessing.connection import Client', {'multiprocessing.connection'}),
                          ('import multiprocessing\nmultiprocessing.connection.Client(x)',
                           {'multiprocessing.connection'})):
            self.assertEqual(network_modules(ast.parse(src)), want, src)


class NoClaudeInvocation(unittest.TestCase):
    def test_no_string_literal_names_a_claude_executable(self):
        for path in source_files():
            for lit in literals(ast.parse(read(path))):
                self.assertNotRegex(lit, CLAUDE_EXE, path)

    def test_no_file_holds_a_bare_claude_token(self):
        for path in source_files():
            for n, line in enumerate(read(path).splitlines(), 1):
                self.assertNotRegex(line, CLAUDE_TOKEN, '%s:%d' % (path, n))

    def test_every_statically_readable_process_launch_names_an_allowed_program(self):
        found = set()
        for path in source_files():
            for program in called_programs(ast.parse(read(path))):
                self.assertIn(program, ALLOWED_PROGRAMS, '%s: unexpected command %r' % (path, program))
                found.add(program)
        # The scan really reads this tree's launches rather than finding none and passing on an empty set.
        self.assertEqual(found, ALLOWED_PROGRAMS)

    def test_every_launch_whose_program_cannot_be_read_has_been_read_by_hand(self):
        found = collections.Counter()
        for path in source_files():
            for where, n in unreadable_launches(ast.parse(read(path))).items():
                found[(os.path.basename(path), where)] += n
        self.assertEqual(dict(found), UNREADABLE_LAUNCHES)

    def test_every_import_by_a_built_name_has_been_read_by_hand(self):
        found = collections.Counter()
        for path in source_files():
            tree = ast.parse(read(path))
            for where, n in built_imports(tree).items():
                found[(os.path.basename(path), where)] += n
            for where, name in dynamic_imports(tree):
                if name is not None:
                    self.assertFalse(watched(name), '%s: %s imports %r' % (path, where, name))
        self.assertEqual(dict(found), DYNAMIC_IMPORTS)


class NoAnthropicHost(unittest.TestCase):
    def test_no_file_names_an_anthropic_host(self):
        for path in source_files():
            self.assertNotRegex(read(path), HOSTS, path)

    def test_the_exporter_modules_the_collector_imports_name_none_either(self):
        for name in IMPORTED:
            path = os.path.join(REPO, 'exporters', name)
            text = read(path)
            self.assertNotRegex(text, HOSTS, path)
            for lit in literals(ast.parse(text)):
                self.assertNotRegex(lit, CLAUDE_EXE, path)

    def test_the_exporter_list_is_what_the_local_modules_really_import(self):
        self.assertEqual(sorted(IMPORTED), exporter_imports())


class NoNetworkClient(unittest.TestCase):
    def test_no_module_imports_a_network_client(self):
        for path in source_files():
            self.assertEqual(network_modules(ast.parse(read(path))), set(), path)
        self.assertIn('http.server.ThreadingHTTPServer', reached_modules(ast.parse(read(os.path.join(LOCAL, 'server.py')))),
                      'the scan reads the submodules the server reaches through the http package')

    def test_socket_is_used_only_to_bind_a_listener(self):
        for path in source_files():
            self.assertLessEqual(module_uses(ast.parse(read(path)), 'socket'), ALLOWED_SOCKET_ATTRS, path)
        self.assertEqual(module_uses(ast.parse(read(os.path.join(LOCAL, 'server.py'))), 'socket'),
                         ALLOWED_SOCKET_ATTRS, 'the scan reads the server, which does use socket')

    def test_native_code_is_reached_only_to_ask_for_a_drive_type(self):
        for path in source_files():
            self.assertLessEqual(module_uses(ast.parse(read(path)), 'ctypes'), ALLOWED_CTYPES_ATTRS, path)
        self.assertEqual(module_uses(ast.parse(read(os.path.join(LOCAL, 'db.py'))), 'ctypes'),
                         ALLOWED_CTYPES_ATTRS, 'the scan reads db.py, which does use ctypes')


if __name__ == '__main__':
    unittest.main()
