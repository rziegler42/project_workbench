"""`call.run_command` against the real `wb` launcher, a real store and synthetic modules.

The helper the command runs is a shell script that records each start, so a test that expects a refusal
can show that nothing ran."""

import os
import tempfile
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import tool
from workbench import firstparty, launch, store
from workbench.wbkit import call

SCRIPT = "#!/bin/sh\necho ran >> '%s'\ncat\n"


class RealLauncher(support_project.Project):
    def setUp(self):
        support_project.Project.setUp(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.log = os.path.join(os.path.realpath(holder.name), "ran.log")
        fields, files = tool(helper=(SCRIPT % self.log).encode())
        fields["provides"] = ["p:bridge"]
        self.MODULES = {"h": (support_project.HARNESS, {}), "tool": (fields, files)}
        # The launcher finds its store from HOME, so the store lives where the launcher will look.
        self.store_root = os.path.join(self.home, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.ready()
        self.pin()
        # Installing used a synthetic distribution; the launcher must run this workbench.
        launch.install_wrapper(self.guarded, firstparty.default_distribution())
        self.environment = {"HOME": self.home, "PATH": os.pathsep.join(
            [os.path.join(self.store_root, "bin"), os.environ.get("PATH", "")])}
        patch = unittest.mock.patch.dict(os.environ, self.environment)
        patch.start()
        self.addCleanup(patch.stop)

    def go(self, arguments=("check",), **kwargs):
        kwargs.setdefault("limit", 1 << 20)
        kwargs.setdefault("timeout", 60)
        return call.run_command(self.real, "tool", list(arguments), **kwargs)

    def ran(self):
        return os.path.exists(self.log)


class Calls(RealLauncher):
    def test_the_prompt_reaches_the_pinned_helper_and_its_output_comes_back(self):
        result = self.go(stdin=b"hello\n", provides="p:bridge")
        self.assertEqual((0, b"hello\n", b"", False, False), tuple(result))

    def test_the_helper_gets_the_arguments_after_the_first_unchanged(self):
        result = self.go(["check", "--model", "a b"], provides="p:bridge")
        self.assertEqual(0, result.code)
        self.assertTrue(self.ran())


class Refuses(RealLauncher):
    def refused(self, result, contains):
        self.assertEqual(1, result.code, result)
        self.assertTrue(result.stderr.startswith(b"refused: "), result.stderr)
        self.assertIn(contains, result.stderr.decode())
        self.assertFalse(self.ran())

    def test_a_module_that_does_not_provide_the_capability(self):
        self.refused(self.go(provides="p:other"), "does not provide p:other")

    def test_a_command_no_installed_module_declares(self):
        result = call.run_command(self.real, "nothing", ["check"], limit=1000, timeout=60)
        self.refused(result, "no installed module declares")

    def test_a_command_that_is_not_pinned(self):
        self.unpin("tool")
        self.refused(self.go(provides="p:bridge"), "is not pinned")

    def test_a_helper_edited_after_it_was_pinned(self):
        self.edit(self.installed(), lambda data: data + b"echo changed\n")
        self.refused(self.go(provides="p:bridge"), "has changed since it was pinned")

    def test_an_argument_the_declaration_does_not_list(self):
        self.refused(self.go(["delete"], provides="p:bridge"), "is not an argument")


if __name__ == "__main__":
    unittest.main()
