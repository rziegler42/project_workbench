"""A project, a fake `codex` outside it, and the helper loaded to be called in this process.

The fake is a script that records its arguments, environment, working directory, standard input and the
schema file it was given, and then does what a control file beside it says: write a reply, print events or
error text, exit with a code, hang, or write too much. No test starts a real `codex`."""

import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

from tests import support_helpers

FAKE = """#!{python}
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
data = sys.stdin.buffer.read()
control = json.load(open(os.path.join(here, "control.json")))
reply = argv[argv.index("--output-last-message") + 1] if "--output-last-message" in argv else None
schema = argv[argv.index("--output-schema") + 1] if "--output-schema" in argv else None
record = {{"argv": argv, "env": dict(os.environ), "cwd": os.getcwd(), "stdin": data.decode("utf-8", "replace"),
          "scratch": os.path.dirname(reply) if reply else None,
          "schema": open(schema, encoding="utf-8").read() if schema else None}}
with open(os.path.join(here, "calls.jsonl"), "a") as handle:
    handle.write(json.dumps(record) + "\\n")
if control.get("hang"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    open(os.path.join(here, "pids"), "w").write(str(child.pid))
    time.sleep(300)
if control.get("stdout_bytes"):
    sys.stdout.write("x" * control["stdout_bytes"])
if control.get("stderr_bytes"):
    sys.stderr.write("e" * control["stderr_bytes"])
for event in control.get("events", []):
    sys.stdout.write(json.dumps(event) + "\\n")
if control.get("stderr"):
    sys.stderr.write(control["stderr"])
if control.get("reply") is not None and reply:
    with open(reply, "wb") as handle:
        handle.write(control["reply"].encode("utf-8", "surrogatepass"))
if control.get("reply_hex") and reply:
    with open(reply, "wb") as handle:
        handle.write(bytes.fromhex(control["reply_hex"]))
if control.get("reply_bytes") and reply:
    with open(reply, "wb") as handle:
        handle.write(b"r" * control["reply_bytes"])
if control.get("kill_self"):
    os.kill(os.getpid(), 9)
sys.exit(control.get("code", 0))
"""

OK_EVENTS = [{"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 5}}]


class Bridge(unittest.TestCase):
    """The helper, a project at `self.root` and a fake `codex` in `self.outside` on the trusted `PATH`."""

    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("ask-codex")

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "project")
        self.outside = os.path.join(self.base, "outside")
        self.temp = os.path.join(self.base, "tmp")
        for folder in (os.path.join(self.root, ".git"), os.path.join(self.root, ".workbench"),
                       os.path.join(self.root, "bin"), os.path.join(self.root, "docs"), self.outside,
                       self.temp):
            os.makedirs(folder)
        with open(os.path.join(self.root, ".workbench", "manifest.json"), "w") as handle:
            handle.write("{}\n")
        with open(os.path.join(self.root, "docs", "plan.md"), "w") as handle:
            handle.write("# Plan\n")
        self.fake(self.outside)
        self.control(reply="the reply\n", events=OK_EVENTS)
        self.path([self.outside], TMPDIR=self.temp, HOME=os.path.join(self.base, "home"))

    def fake(self, folder):
        script = os.path.join(folder, "codex")
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

    def ask(self, *args, prompt=b"Review docs/plan.md\n", cwd=None):
        """``(code, standard output, standard error)`` of ``ask-codex ask <args>`` with `prompt` on standard input."""
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(["ask", *args], io.BytesIO(prompt), out, err, cwd or self.root)
        return code, out.getvalue(), err.getvalue()

    def document(self, *args, **kwargs):
        """The one object a call printed, after the checks every call must pass."""
        code, out, err = self.ask(*args, **kwargs)
        self.assertEqual("", err)
        self.assertTrue(out.endswith("\n") and "\n" not in out[:-1], "not one line")
        self.assertLessEqual(len(out.encode()), self.helper.MAX_OBJECT)
        document = json.loads(out)
        self.assertEqual(code, 0 if document["ok"] else 1)
        self.assertEqual(1, document["contract"])
        self.assertEqual("codex", document["vendor"])
        return document

    def refused(self, *args, contains="", **kwargs):
        code, out, err = self.ask(*args, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)
        self.assertIn(contains, err)
        self.assertEqual([], self.calls(), "the program was started")
        return err

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
