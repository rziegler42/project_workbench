"""A project in a temporary directory, the two helpers loaded to be called in this process, and the project
file the spec gives as its example. No test starts a real `remote-runner`, and none contacts a host."""

import os
import tempfile
import unittest

from tests import support_helpers

FILE = ".workbench/remote-runner.toml"
OLD_FILE = ".claude/remote-runner.toml"

VALID = """[project]
id = "project-workbench"

[profiles.fast]
command = "make test-fast"

[profiles.fast.requirements]
min_cpu_cores = 4
min_memory_gib = 8
labels = ["test"]
os = "linux"

[profiles.full]
command = "python3 -B -W error tests/run_all.py"
"""


class Project(unittest.TestCase):
    """The helpers and a project at `self.root`: a `.git` directory and a `.workbench` with a manifest."""

    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("remote-runner")
        cls.check = support_helpers.load("remote-runner-check")

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "project")
        for folder in (".git", ".workbench", "sub"):
            os.makedirs(os.path.join(self.root, folder))
        self.write(".workbench/manifest.json", "{}\n")

    def write(self, rel, data):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    def snapshot(self):
        """Every path below the project with its kind and content, to show a refusal changed nothing."""
        found = {}
        for base, dirs, files in os.walk(self.root):
            for name in dirs + files:
                full = os.path.join(base, name)
                rel = os.path.relpath(full, self.root)
                if os.path.islink(full):
                    found[rel] = ("link", os.readlink(full))
                elif os.path.isdir(full):
                    found[rel] = ("dir", None)
                else:
                    with open(full, "rb") as handle:
                        found[rel] = ("file", handle.read())
        return found
