"""A real, exercised proof (not a mock) that the collector's git helper opens no console window when its
parent has none of its own -- the exact shape of a log-on task, which starts under pythonw.exe.

Windows gives a console-subsystem child (git.exe, python.exe) a console of its own -- a brand new, visible
one -- whenever its parent has none and the launch does not ask otherwise. CREATE_NO_WINDOW is what asks
otherwise. So a checker child that reports its own GetConsoleWindow() is a deterministic witness: 0 with the
flag, non-zero without it, launched from a genuinely console-less parent (pythonw.exe) either way. The parent
runs export_board.no_window_flags() for real, under real win32, rather than a patched platform check, so this
proves the actual call shape local/tabs.py's git launches use.

The child is launched through plain python.exe rather than sys.executable of the pythonw.exe parent: pythonw
is itself a windowed-subsystem program that never gets a console however it is launched, so using it as the
child would pass the "no console" case vacuously. git.exe, like python.exe, is a console-subsystem program,
so python.exe is the shape that actually exercises the defect.
"""
import os, shutil, subprocess, sys, tempfile, textwrap, unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PYTHONW = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')

CHECKER = textwrap.dedent("""\
    import ctypes, sys
    sys.stdout.write(str(ctypes.windll.kernel32.GetConsoleWindow()))
""")

OUTER = textwrap.dedent("""\
    import os, subprocess, sys
    repo, python_exe, checker, mode, result = sys.argv[1:6]
    sys.path.insert(0, os.path.join(repo, 'exporters'))
    import export_board
    kwargs = export_board.no_window_flags() if mode == 'flag' else {}
    r = subprocess.run([python_exe, checker], capture_output=True, text=True, **kwargs)
    with open(result, 'w', encoding='utf-8') as f:
        f.write(r.stdout)
""")


@unittest.skipUnless(sys.platform == 'win32', 'CREATE_NO_WINDOW and GetConsoleWindow are Windows-only')
class NoConsoleWindowUnderAConsoleLessParent(unittest.TestCase):
    def setUp(self):
        if not os.path.exists(PYTHONW):
            self.skipTest('no pythonw.exe beside %s' % sys.executable)
        self.tmp = tempfile.mkdtemp(prefix='no-console-window-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.checker = os.path.join(self.tmp, 'checker.py')
        self.outer = os.path.join(self.tmp, 'outer.py')
        with open(self.checker, 'w', encoding='utf-8') as f:
            f.write(CHECKER)
        with open(self.outer, 'w', encoding='utf-8') as f:
            f.write(OUTER)

    def launch(self, use_flag):
        """Runs outer.py under pythonw.exe -- a console-less parent -- which launches the checker through
        export_board.no_window_flags() (flag) or with nothing (noflag), and returns the checker's own
        GetConsoleWindow() reading."""
        result = os.path.join(self.tmp, 'result.txt')
        p = subprocess.run(
            [PYTHONW, self.outer, REPO, sys.executable, self.checker, 'flag' if use_flag else 'noflag', result],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(result, encoding='utf-8') as f:
            return f.read().strip()

    def test_create_no_window_leaves_the_child_with_no_console(self):
        self.assertEqual(self.launch(use_flag=True), '0')

    def test_without_it_a_console_less_parent_really_does_open_one(self):
        # Proves the witness is not vacuously 0 regardless of the flag: this reproduces the popping window.
        self.assertNotEqual(self.launch(use_flag=False), '0')


if __name__ == '__main__':
    unittest.main()
