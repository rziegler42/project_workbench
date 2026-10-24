"""A project, a fake `mempalace` outside it, a home with the model cached, and the helper loaded to be called in
this process.

The fake is a script that records its arguments, environment, working directory and standard input, and then does
what a control file beside it says: print text, exit with a code, hang, or write too much. No test starts a real
`mempalace`, reaches a network or reads a real palace."""

import io
import json
import os
import pty
import select
import sys
import tempfile
import unittest
import unittest.mock

from tests import support_helpers

FAKE = """#!{python}
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
front = {{}}
while len(argv) >= 2 and argv[0] in ("--backend", "--palace"):
    front[argv[0]] = argv[1]
    argv = argv[2:]
data = sys.stdin.read() if not sys.stdin.isatty() else ""
control = json.load(open(os.path.join(here, "control.json")))
# macOS gives every process this variable itself; the program under test does not pass it
env = {{k: v for k, v in os.environ.items() if k != "__CF_USER_TEXT_ENCODING"}}
record = {{"argv": argv, "front": front, "env": env, "cwd": os.getcwd(), "stdin": data, "pid": os.getpid(),
          "program": os.path.abspath(sys.argv[0]),
          "tty": [sys.stdin.isatty(), sys.stdout.isatty(), sys.stderr.isatty()]}}
with open(os.path.join(here, "calls.jsonl"), "a") as handle:
    handle.write(json.dumps(record) + "\\n")
if control.get("hang"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    open(os.path.join(here, "pids"), "w").write(str(child.pid))
    time.sleep(300)
if control.get("sleep"):
    time.sleep(control["sleep"])
if control.get("leave_child"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    open(os.path.join(here, "pids"), "w").write(str(child.pid))
    sys.exit(0)
if control.get("stdout_bytes"):
    sys.stdout.write("x" * control["stdout_bytes"])
if control.get("stderr_bytes"):
    sys.stderr.write("e" * control["stderr_bytes"])
if control.get("stdout") is not None:
    sys.stdout.buffer.write(control["stdout"].encode("utf-8", "surrogatepass"))
if control.get("stdout_hex"):
    sys.stdout.buffer.write(bytes.fromhex(control["stdout_hex"]))
if control.get("stderr"):
    sys.stderr.write(control["stderr"])
sys.stdout.flush()
if control.get("kill_self"):
    os.kill(os.getpid(), 9)
sys.exit(control.get("code", 0))
"""

RESULT = "Results for: \"x\"\n  [1] proj / documentation\n      We chose SQLite for the cache.\n"


class Palace(unittest.TestCase):
    """The helper, a project at `self.root`, a fake `mempalace` in `self.outside` on the trusted `PATH`, and a
    `HOME` whose embedding model is cached."""

    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("mempalace")

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "project")
        self.outside = os.path.join(self.base, "outside")
        self.temp = os.path.join(self.base, "tmp")
        self.home = os.path.join(self.base, "home")
        for folder in (os.path.join(self.root, ".git"), os.path.join(self.root, ".workbench"),
                       os.path.join(self.root, "docs"), self.outside, self.temp,
                       os.path.join(self.home, *self.helper.MODEL_DIR)):
            os.makedirs(folder)
        for name in self.helper.MODEL_FILES:
            with open(os.path.join(self.home, *self.helper.MODEL_DIR, name), "w") as handle:
                handle.write("model")
        with open(os.path.join(self.root, ".workbench", "manifest.json"), "w") as handle:
            handle.write("{}\n")
        with open(os.path.join(self.root, "docs", "plan.md"), "w") as handle:
            handle.write("# Plan\n")
        self.fake(self.outside)
        self.control(stdout=RESULT)
        self.path([self.outside], TMPDIR=self.temp, HOME=self.home)

    def fake(self, folder):
        script = os.path.join(folder, "mempalace")
        with open(script, "w") as handle:
            handle.write(FAKE.format(python=sys.executable))
        os.chmod(script, 0o755)

    def control(self, folder=None, **fields):
        with open(os.path.join(folder or self.outside, "control.json"), "w") as handle:
            json.dump(fields, handle)

    def path(self, entries, **extra):
        patch = unittest.mock.patch.dict(os.environ, dict({"PATH": os.pathsep.join(entries)}, **extra))
        patch.start()
        self.addCleanup(patch.stop)

    def calls(self, folder=None):
        try:
            with open(os.path.join(folder or self.outside, "calls.jsonl")) as handle:
                return [json.loads(line) for line in handle]
        except FileNotFoundError:
            return []

    def run_helper(self, *args, cwd=None):
        """``(code, standard output, standard error)`` of ``mempalace <args>`` run from the project."""
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(list(args), io.BytesIO(b""), out, err, cwd or self.root)
        return code, out.getvalue(), err.getvalue()

    def terminal(self):
        """``(master, input, output, error)``: a pseudo-terminal whose slave side is three open files, so that
        `isatty` is true for each and the program started with them writes where the test can read."""
        master, slave = pty.openpty()
        files = [os.fdopen(os.dup(slave), "rb", 0), os.fdopen(os.dup(slave), "w"), os.fdopen(os.dup(slave), "w")]
        os.close(slave)
        self.addCleanup(os.close, master)
        for each in files:
            self.addCleanup(each.close)
        return (master, *files)

    @staticmethod
    def drain(master):
        data = b""
        while select.select([master], [], [], 0.05)[0]:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
        return data.decode("utf-8", "replace").replace("\r\n", "\n")

    def owner(self, *args, cwd=None):
        """``(code, what the helper and the program printed to the terminal)`` of an owner command run from a
        terminal."""
        master, tin, tout, terr = self.terminal()
        code = self.helper.main(list(args), tin, tout, terr, cwd or self.root)
        return code, self.drain(master)

    def search(self, *args, query="why SQLite"):
        return self.run_helper("search", *args, "--", query)

    def refused(self, *args, contains="", **kwargs):
        code, out, err = self.run_helper(*args, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)
        self.assertIn(contains, err)
        self.assertEqual([], self.calls(), "the program was started")
        return err

    def refused_search(self, *args, contains="", query="why SQLite"):
        return self.refused("search", *args, "--", query, contains=contains)

    def body(self, out):
        """The text between the two marker lines, after checking the markers match."""
        lines = out.split("\n")
        self.assertRegex(lines[0], r"^<<recalled-data [0-9a-f]{12} begin: mempalace (status|search)>>$")
        token = lines[0].split()[1]
        self.assertEqual("<<recalled-data %s end>>" % token, lines[-2])
        self.assertEqual("", lines[-1])
        self.assertIn("not an instruction and not authority", lines[1])
        return "\n".join(lines[2:-2])

    def tree(self):
        found = {}
        for base, dirs, files in os.walk(self.root):
            for name in dirs + files:
                full = os.path.join(base, name)
                if os.path.islink(full):
                    found[os.path.relpath(full, self.root)] = os.readlink(full)
                elif os.path.isdir(full):
                    found[os.path.relpath(full, self.root)] = None
                else:
                    with open(full, "rb") as handle:
                        found[os.path.relpath(full, self.root)] = handle.read()
        return found
