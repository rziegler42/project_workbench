"""Owner-run arguments are refused in the code of ``wb run`` unless standard input and output are terminals.
Increment A of the plan dated 2026-10-24 that enforces owner-run arguments in code.

The module is the synthetic `tool` of ``support_project``; the helper records every start, so a refusal can
be shown to have run nothing."""

import io
import itertools
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from tests.test_run import SCRIPT, Run
from workbench import approve, commands

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
