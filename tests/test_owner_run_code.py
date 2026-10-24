"""Owner-run arguments are refused in the code of ``wb run`` unless standard input and output are terminals.
Increment A of the plan dated 2026-10-24 that enforces owner-run arguments in code.

The module is the synthetic `tool` of ``support_project``; the helper records every start, so a refusal can
be shown to have run nothing."""

import io
import itertools
import json
import tempfile
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from tests.test_run import SCRIPT, Run
from workbench import approve, cli, commands, hashing, launch, manifest

COMMAND = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "report", "wipe"], "owner": ["wipe"]}}


class OwnerRun(Run):
    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(COMMAND, helper=SCRIPT)}

    def terminals(self, *values):
        """Patch the terminal test: it answers `values` in turn, standard input first and then output, for
        every run."""
        patch = unittest.mock.patch.object(approve, "is_terminal", side_effect=itertools.cycle(values))
        self.addCleanup(patch.stop)
        return patch.start()


class Refused(OwnerRun):
    def reason(self, *args):
        self.pinned()
        self.terminals(False, False)
        self.refused(*args, contains="wipe")
        return self.go(*args)[2]

    def test_an_owner_argument_with_no_terminal_is_refused_and_nothing_runs(self):
        self.assertIn("terminal", self.reason("tool", "wipe"))

    def test_it_is_refused_with_further_arguments(self):
        self.reason("tool", "wipe", "--force", "x")

    def test_it_is_refused_through_the_capability_form(self):
        self.pinned()
        self.terminals(False, False)
        self.refused("--provides", "x", "tool", "wipe")

    def test_standard_input_alone_being_a_terminal_is_not_enough(self):
        self.pinned()
        self.terminals(True, False)
        self.refused("tool", "wipe", contains="terminal")

    def test_standard_output_alone_being_a_terminal_is_not_enough(self):
        self.pinned()
        self.terminals(False, True)
        self.refused("tool", "wipe", contains="terminal")

    def test_the_refusal_names_the_command_and_the_argument(self):
        self.pinned()
        self.terminals(False, False)
        code, _, err = self.go("tool", "wipe")
        self.assertEqual(1, code)
        self.assertIn("tool", err)
        self.assertIn("wipe", err)


class Allowed(OwnerRun):
    def test_an_owner_argument_runs_when_both_streams_are_terminals(self):
        self.pinned()
        self.terminals(True, True)
        code, out, err = self.go("tool", "wipe", "x")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:2", "a:wipe", "a:x"], out.splitlines())
        self.assertTrue(self.ran())

    def test_the_other_arguments_run_with_no_terminal_and_do_not_ask(self):
        self.pinned()
        spy = self.terminals(False, False)
        for argument in ("check", "report"):
            self.assertIn(self.go("tool", argument)[0], (0, 3))
        spy.assert_not_called()


class Launch(OwnerRun):
    """``wb launch <id> <name> --root <dir> -- <args>`` of a pin the installer made."""

    def go_launch(self, *args, root=None):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(launch, "launch", return_value=0) as spy:
            code = cli.main(["launch", self.project_id, "tool", "--root", root or self.real, "--"] + list(args),
                            out, err, store_root=self.store_root)
        return code, err.getvalue(), spy

    def refused_launch(self, *args, contains, **kwargs):
        code, err, spy = self.go_launch(*args, **kwargs)
        self.assertEqual(1, code)
        self.assertEqual(1, len(err.splitlines()), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        spy.assert_not_called()

    def drop_owner_list(self):
        """Remove the `owner` list from the installed declaration and make the manifest agree, as a
        project the agent controls could."""
        rel = ".workbench/p/tool/module.json"
        declaration = json.loads(self.read(rel))
        del declaration["commands"]["tool"]["owner"]
        self.edit(rel, lambda data: json.dumps(declaration).encode())
        document = manifest.parse(self.read(".workbench/manifest.json"))
        for package in document["packages"]:
            for item in package["modules"]:
                if item["name"] == "tool":
                    item["declaration"] = hashing.declaration_hash(declaration)
        self.edit(".workbench/manifest.json", lambda data: manifest.serialize(document))

    def test_an_owner_argument_with_no_terminal_is_refused_and_nothing_runs(self):
        self.ready()
        self.terminals(False, False)
        self.refused_launch("wipe", "x", contains="wipe")

    def test_an_owner_argument_runs_when_both_streams_are_terminals(self):
        self.ready()
        self.terminals(True, True)
        code, err, spy = self.go_launch("wipe")
        self.assertEqual((0, ""), (code, err))
        spy.assert_called_once()

    def test_the_other_arguments_run_with_no_terminal(self):
        self.ready()
        self.terminals(False, False)
        code, err, spy = self.go_launch("check")
        self.assertEqual((0, ""), (code, err))
        spy.assert_called_once()

    def test_a_declaration_that_drops_the_owner_list_is_refused_for_every_argument(self):
        self.ready()
        self.drop_owner_list()
        self.terminals(False, False)
        for argument in ("wipe", "check"):
            self.refused_launch(argument, contains="declaration")

    def test_a_root_with_no_project_is_refused_for_an_installer_pin(self):
        self.ready()
        self.terminals(False, False)
        with tempfile.TemporaryDirectory() as empty:
            self.refused_launch("wipe", root=empty, contains="refused")

    def test_a_pin_the_owner_typed_is_unchanged(self):
        self.ready()
        self.pin()
        self.terminals(False, False)
        code, err, spy = self.go_launch("wipe")
        self.assertEqual((0, ""), (code, err))
        spy.assert_called_once()


class NoOwnerList(Run):
    PLAIN = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "wipe"]}}
    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(PLAIN, helper=SCRIPT)}

    def test_a_command_with_no_owner_list_does_not_ask(self):
        self.pinned()
        with unittest.mock.patch.object(approve, "is_terminal", return_value=False) as spy:
            self.assertEqual(0, self.go("tool", "wipe")[0])
        spy.assert_not_called()


class Streams(OwnerRun):
    def test_the_terminal_test_reads_the_given_streams(self):
        self.pinned()
        stdin, stdout = io.StringIO(), io.StringIO()
        seen = []
        with unittest.mock.patch.object(approve, "is_terminal", side_effect=lambda s: seen.append(s) or True):
            commands.run(self.guarded, ["tool", "wipe"], io.StringIO(), cwd=self.real, stdin=stdin,
                         stdout=stdout)
        self.assertEqual([stdin, stdout], seen)


if __name__ == "__main__":
    unittest.main()
