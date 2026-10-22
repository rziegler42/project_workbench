"""The shipped Claude module as the harness to attach, for the test files not yet moved to the synthetic
harness (`test_check.py`, `test_groundwork_fixture.py`).

Interim: plan 2026-10-21-module-harness-paths, increments G and H switch those files to the synthetic
harness and delete this file."""

import io
import os

from tests import support, test_attach
from workbench import cli, localmanifest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = os.path.join(ROOT, "packages", "workbench")
HARNESS = "workbench/claude"
LOCAL = localmanifest.PATH
SETTINGS = ".claude/settings.local.json"
HARNESS_PATHS = ["CLAUDE.md", ".claude/agents/reviewer.md", ".claude/commands/ship.md",
                 ".claude/settings.local.json", ".claude/skills/sample/SKILL.md"]
Base = test_attach.Base


class RealHarness:
    """Mix in before `Base`: `attach` attaches the shipped module from the running distribution."""

    def attach(self, *args, harness=HARNESS, package=test_attach.DEFAULT, **kwargs):
        support.require_release(self)
        package = REAL if package is test_attach.DEFAULT else package
        kwargs.setdefault("dist", None)
        return Base.attach(self, *args, harness=harness, package=package, **kwargs)

    def warm(self, path):
        cli.main(["verify", path], io.StringIO(), io.StringIO(), store_root=self.store_root)
