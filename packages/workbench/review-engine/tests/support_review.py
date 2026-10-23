"""A project, a guarded store under a temporary home, and the review-engine helper loaded to be called in this
process. No test starts a bridge or a model: this increment calls none."""

import hashlib
import io
import json
import os
import tempfile
import unicodedata
import unittest
import unittest.mock

from tests import support_helpers
from workbench import store as guarded
from workbench.wbkit import project as kit_project

PLAN = "docs/plans/2026-01-01-sample.md"
SPEC = "docs/specs/sample.md"
OTHER_PLAN = "docs/plans/2026-01-02-other.md"
NAMESPACE = ".workbench/workbench/review-engine"


def round_entry(n, severities=(), **changes):
    """A round of a state in the documented shape, with one finding for each of `severities`."""
    entry = {"n": n, "file": "round-%d.json" % n, "sha256": "%064x" % n, "document_sha256": "%064x" % (n + 1000),
             "at": "2026-01-01T00:00:00Z", "bridge": "ask-codex", "requested": {"model": None, "effort": None},
             "model": None, "verdict": "no_meaningful_changes", "reading": "no_meaningful_changes",
             "mismatch": False, "usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
             "findings": [{"id": "R%d-F%d" % (n, k + 1), "severity": s} for k, s in enumerate(severities)]}
    entry.update(changes)
    return entry


def key_of(kind, path):
    folded = unicodedata.normalize("NFD", unicodedata.normalize("NFD", path).casefold())
    return "%s-%s" % (kind, hashlib.sha256(folded.encode("utf-8")).hexdigest()[:16])


class Review(unittest.TestCase):
    """The helper, a project at `self.root`, and a store at `self.store` made by the installer's own code."""

    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("review-engine")

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "project")
        self.home = os.path.join(self.base, "home")
        for folder in (os.path.join(self.root, ".git"), os.path.join(self.root, ".workbench"),
                       os.path.join(self.root, "docs", "plans"), os.path.join(self.root, "docs", "specs"),
                       os.path.join(self.root, "docs", "roadmaps"), os.path.join(self.root, "docs", "decisions"),
                       self.home):
            os.makedirs(folder)
        self.write(".workbench/manifest.json", '{"seed": "sample-seed"}\n')
        for path in (PLAN, OTHER_PLAN, SPEC, "docs/roadmaps/r.md", "docs/decisions/2026-01-01-d.md"):
            self.write(path, "# Title\n")
        patch = unittest.mock.patch.dict(os.environ, {"HOME": self.home})
        patch.start()
        self.addCleanup(patch.stop)
        self.store = os.path.join(self.home, ".config", "project-workbench")
        guarded.Store(self.store).ensure()
        self.project_id = kit_project.read_id(self.root)

    # --- files -----------------------------------------------------------------------------------

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def write(self, rel, text, binary=False):
        full = self.path(rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as handle:
            handle.write(text)

    def read(self, rel):
        with open(self.path(rel), "rb") as handle:
            return handle.read()

    def review_dir(self, kind, path):
        return "%s/%s" % (NAMESPACE, key_of(kind, path))

    def state_rel(self, kind, path):
        return self.review_dir(kind, path) + "/state.json"

    def state(self, kind="plan", path=PLAN):
        return json.loads(self.read(self.state_rel(kind, path)))

    def store_path(self, *names):
        return os.path.join(self.store, "projects", self.project_id, "review-engine", *names)

    def key(self):
        with open(self.store_path("seal-key"), "rb") as handle:
            return handle.read()

    def forge(self, body, kind="plan", path=PLAN, key=None):
        """Write `body` as the state of a review with a seal made by `key` (the stored one by default)."""
        body = {name: value for name, value in body.items() if name != "seal"}
        body["seal"] = self.helper.seal(key if key is not None else self.key(), body)
        self.write(self.state_rel(kind, path), json.dumps(body))
        return body

    def set_mark(self, key_name, rounds, decisions, generation=0):
        os.makedirs(self.store_path("marks"), exist_ok=True)
        with open(self.store_path("marks", key_name), "w") as handle:
            json.dump({"rounds": rounds, "decisions": decisions, "generation": generation}, handle)

    # --- calls -----------------------------------------------------------------------------------

    def call(self, *argv, cwd=None):
        """``(code, standard output, standard error)`` of ``review-engine <argv>``."""
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(list(argv), io.BytesIO(b""), out, err, cwd or self.root)
        return code, out.getvalue(), err.getvalue()

    def document(self, *argv, **kwargs):
        """The one object a call printed, after the checks every call must pass (checklist item 13)."""
        code, out, err = self.call(*argv, **kwargs)
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(out.endswith("\n") and "\n" not in out[:-1], "not one line")
        return json.loads(out)

    def refused(self, *argv, contains="", **kwargs):
        code, out, err = self.call(*argv, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)
        self.assertIn(contains, err)
        return err

    # --- what changed ----------------------------------------------------------------------------

    def tree(self, top):
        found = {}
        for base, dirs, files in os.walk(top):
            for name in dirs + files:
                full = os.path.join(base, name)
                rel = os.path.relpath(full, top)
                if os.path.islink(full):
                    found[rel] = ("link", os.readlink(full))
                elif os.path.isdir(full):
                    found[rel] = ("dir", oct(os.stat(full).st_mode & 0o777))
                else:
                    with open(full, "rb") as handle:
                        found[rel] = ("file", oct(os.stat(full).st_mode & 0o777), handle.read())
        return found

    def changed(self, before, after):
        return sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))
