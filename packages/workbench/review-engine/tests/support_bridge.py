"""A project with `review-engine` and the real `ask-codex` bridge installed and pinned, a fake `codex` outside it,
and the real `wb` launcher, so that a round goes through every hop it goes through for the owner. The vendor
program is a fake that records what it is given and does what a control file says; no test starts a real `codex`,
a vendor or a network call.

The installs run against a copy of the package in a temporary distribution whose approvals `release_approvals`
records in that copy, so the shipped approvals (stale until the plan's last increment) play no part."""

import io
import json
import os
import shutil
import sys
import unittest.mock

import support_review
from support_review import PLAN

from tests import support, support_install
from workbench import approve, firstparty, install, launch, sources, store
from workbench.wbkit import call
from workbench.wbkit import project as kit_project

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
SELECT = ("claude", "ask-codex", "review-engine")
SETTING = ".workbench/review.json"

FAKE = """#!{python}
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
data = sys.stdin.buffer.read()
control = json.load(open(os.path.join(here, "control.json")))
reply = argv[argv.index("--output-last-message") + 1] if "--output-last-message" in argv else None
schema = argv[argv.index("--output-schema") + 1] if "--output-schema" in argv else None
record = {{"argv": argv, "stdin": data.decode("utf-8", "replace"),
          "schema": open(schema, encoding="utf-8").read() if schema else None}}
with open(os.path.join(here, "calls.jsonl"), "a") as handle:
    handle.write(json.dumps(record) + "\\n")
if control.get("hang"):
    time.sleep(control["hang"])
for event in control.get("events", []):
    sys.stdout.write(json.dumps(event) + "\\n")
if control.get("stderr"):
    sys.stderr.write(control["stderr"])
if control.get("reply") is not None and reply:
    with open(reply, "wb") as handle:
        handle.write(control["reply"].encode("utf-8", "surrogatepass"))
sys.exit(control.get("code", 0))
"""

EVENTS = [{"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 5}}]


def finding(severity="minor", problem="A problem.", location="Scope", suggestion="Fix it."):
    return {"severity": severity, "location": location, "problem": problem, "suggestion": suggestion}


def reply(*findings, verdict=None, summary="A summary."):
    """The text of a valid reply with `findings`; the verdict follows them unless given."""
    meaningful = any(f["severity"] in ("blocker", "major") for f in findings)
    return json.dumps({"verdict": verdict or ("changes_needed" if meaningful else "no_meaningful_changes"),
                       "summary": summary, "findings": list(findings)})


def answer(**changes):
    body = {"contract": 1, "ok": True, "vendor": "codex", "model": "m-1", "reply": reply(finding()),
            "usage": {"input_tokens": 12, "output_tokens": 5, "total_tokens": None}}
    body.update(changes)
    return body


def failure(**changes):
    body = {"contract": 1, "ok": False, "vendor": "codex", "error": "not_signed_in", "detail": None,
            "retryable": False, "message": "Not logged in."}
    body.update(changes)
    return body


def result(body=None, code=None, stderr=b"", over=False, timed_out=False, raw=None):
    data = raw if raw is not None else (json.dumps(body) + "\n").encode()
    if code is None:
        code = 0 if isinstance(body, dict) and body.get("ok") is True else 1
    return call.Result(code, data, stderr, over, timed_out)


class Round(support_review.Review):
    """A project made by the installer from a copy of the package, with the setting naming `ask-codex`."""

    def setUp(self):
        self.base, self.root = self.make_base()
        self.home = os.path.join(self.base, "home")
        self.vendor = os.path.join(self.base, "vendor")
        self.tools = os.path.join(self.base, "tools")
        for folder in (self.home, self.vendor, self.tools):
            os.makedirs(folder)
        support.forbid_real_store(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)
        self.store = os.path.join(self.home, ".config", "project-workbench")
        self.guarded = store.Store(self.store)
        self.guarded.ensure()
        self.dist = os.path.join(self.base, "dist")
        shutil.copytree(os.path.join(ROOT, "packages"), os.path.join(self.dist, "packages"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "base"), os.path.join(self.dist, "base"))
        os.makedirs(os.path.join(self.dist, "workbench"))
        firstparty.release_approvals(self.dist)
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(self.root, [(os.path.join(self.dist, "packages", "workbench"), None)],
                                  list(SELECT))
        code = install.run(self.guarded, command, support_install.Typist(out, support_install.correct), out, err,
                           distribution=self.dist, seed=support_install.SEED, home=self.home)
        self.assertEqual(0, code, out.getvalue() + err.getvalue())
        launch.install_wrapper(self.guarded, firstparty.default_distribution())
        script = os.path.join(self.vendor, "codex")
        with open(script, "w") as handle:
            handle.write(FAKE.format(python=sys.executable))
        os.chmod(script, 0o755)
        os.symlink(sys.executable, os.path.join(self.tools, "python3"))
        self.control(reply=reply(finding()), events=EVENTS)
        path = os.pathsep.join([os.path.join(self.store, "bin"), self.vendor, self.tools])
        patch = unittest.mock.patch.dict(os.environ, {"HOME": self.home, "PATH": path})
        patch.start()
        self.addCleanup(patch.stop)
        self.project_id = kit_project.read_id(self.root)
        for path in (PLAN, support_review.SPEC, "docs/roadmaps/r.md", "docs/decisions/2026-01-01-d.md"):
            self.write(path, "# Title\n")
        self.setting(bridge="ask-codex")

    def make_base(self):
        import tempfile
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        base = os.path.realpath(holder.name)
        return base, os.path.join(base, "project")

    def setting(self, **fields):
        self.write(SETTING, json.dumps(dict({"format": 1}, **fields)))

    def control(self, **fields):
        with open(os.path.join(self.vendor, "control.json"), "w") as handle:
            json.dump(fields, handle)

    def calls(self):
        try:
            with open(os.path.join(self.vendor, "calls.jsonl")) as handle:
                return [json.loads(line) for line in handle]
        except FileNotFoundError:
            return []

    def round(self, document=PLAN, kind="plan"):
        """The object a round printed, after the checks every call must pass."""
        return self.document("review-" + kind, document)

    def forge_now(self, **changes):
        """Reseal the state of `PLAN` with `changes` made to its fields (a hand-made state with a good seal)."""
        state = self.state()
        state.update(changes)
        return self.forge(state)

    def bridge_helper(self):
        return ".workbench/workbench/ask-codex/helper/ask-codex"

    def snapshot(self):
        return self.tree(self.root), self.tree(self.store)
