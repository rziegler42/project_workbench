"""A project, a fake `remote-runner` program outside it, and the helper loaded to be called in this process.

The fake records its argument vector, environment, working directory and process id, and then does what a
control file beside it says: print text, print a lot, write to standard error, exit with a code, or hang with a
child. No test starts the real program, and none contacts a host."""

import io
import json
import os
import sys
import unittest.mock

import support_remote
from support_remote import VALID

FAKE = """#!{python}
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
control = json.load(open(os.path.join(here, "control.json")))
record = {{"argv": sys.argv[1:], "env": dict(os.environ), "cwd": os.getcwd(), "pid": os.getpid(),
          "stdin_is_null": os.fstat(0).st_rdev == os.stat(os.devnull).st_rdev}}
with open(os.path.join(here, "calls.jsonl"), "a") as handle:
    handle.write(json.dumps(record) + "\\n")
if control.get("hang"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    open(os.path.join(here, "pids"), "w").write(str(child.pid))
    time.sleep(300)
if control.get("stdout_bytes"):
    sys.stdout.write("x" * control["stdout_bytes"])
    sys.stdout.flush()
if control.get("stdout") is not None:
    sys.stdout.write(control["stdout"])
if control.get("stderr"):
    sys.stderr.write(control["stderr"])
sys.exit(control.get("code", 0))
"""

COMMIT = "a" * 40
OTHER = "b" * 40
JOB = "20260101T000000Z--abc123"


def status_view(**fields):
    view = {"untrusted_job_data": True, "job": JOB, "project": "project-workbench", "state": "PASSED",
            "commit": COMMIT, "dut_commit": COMMIT, "dut_clean": True, "integrity": "ok", "snapshot": False,
            "base_commit": None, "source_ref": "main", "created_at": "2026-01-01T00:00:00Z", "pid": 1}
    view.update(fields)
    return json.dumps(view, indent=2)


class Wrapped(support_remote.Project):
    """The project file written, a fake `remote-runner` in `self.outside` on the trusted `PATH`."""

    def setUp(self):
        support_remote.Project.setUp(self)
        self.outside = os.path.join(self.base, "outside")
        os.makedirs(self.outside)
        self.temp = os.path.join(self.base, "tmp")
        os.makedirs(self.temp)
        self.write(support_remote.FILE, VALID)
        self.fake(self.outside)
        self.control(stdout='{"ok": true}\n')
        self.path([self.outside], TMPDIR=self.temp, HOME=os.path.join(self.base, "home"))

    def fake(self, folder, name="remote-runner"):
        script = os.path.join(folder, name)
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

    def run_it(self, *args, cwd=None):
        """``(code, standard output, standard error)`` of ``remote-runner <args>``."""
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(list(args), out, err, cwd or self.root)
        return code, out.getvalue(), err.getvalue()

    def document(self, *args, **kwargs):
        """The one object a call printed, after the checks every call must pass."""
        code, out, err = self.run_it(*args, **kwargs)
        self.assertEqual("", err)
        self.assertTrue(out.endswith("\n") and "\n" not in out[:-1], "not one line")
        document = json.loads(out)
        self.assertEqual(code, 0 if document["exit"] == 0 else 1)
        return document
