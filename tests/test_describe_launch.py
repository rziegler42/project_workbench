"""The launcher rule for `describe`: `wb run` and `wb launch` run `describe <action>` only for an action the command's
declaration lists in `describes`. Increment B of the plan dated 2026-10-25 that builds the `describe` command of a git
module.

The module is the synthetic `tool` of ``support_project``. The rule is generic: nothing here names a module."""

import io
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from tests.test_run import SCRIPT, Run
from workbench import cli, launch

DESCRIBING = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "describe"], "describes": ["commit", "remove"]}}
EMPTY = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "describe"]}}


class Described(Run):
    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(DESCRIBING, helper=SCRIPT)}

    def test_a_listed_action_runs_with_its_arguments(self):
        self.pinned()
        code, out, err = self.go("tool", "describe", "commit", "--x", "a b")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:4", "a:describe", "a:commit", "a:--x", "a:a b"], out.splitlines())
        self.assertTrue(self.ran())

    def test_each_listed_action_runs(self):
        self.pinned()
        for action in ("commit", "remove"):
            with self.subTest(action):
                self.assertEqual(0, self.go("tool", "describe", action)[0])

    def test_describe_with_no_action_is_refused_and_nothing_runs(self):
        self.pinned()
        self.refused("tool", "describe", contains="commit, remove")
        self.assertFalse(self.ran())

    def test_an_action_that_is_not_listed_is_refused_and_nothing_runs(self):
        self.pinned()
        for action in ("push", "Commit", "commit ", "", "--", "-commit", "commit;ls", "check"):
            with self.subTest(action):
                self.refused("tool", "describe", action, contains="not an action")
        self.assertFalse(self.ran())

    def test_the_refusal_names_the_declared_actions(self):
        self.pinned()
        self.refused("tool", "describe", "push", contains="commit, remove")

    def test_the_listed_action_must_be_the_second_argument(self):
        self.pinned()
        self.refused("tool", "describe", "--x", "commit", contains="not an action")

    def test_other_arguments_are_unchanged(self):
        self.pinned()
        self.refused("tool", "wipe", contains="is not an argument")
        self.assertEqual(0, self.go("tool", "check", "describe", "push")[0])

    def test_the_capability_form_applies_the_same_rule(self):
        fields, files = tool(DESCRIBING, helper=SCRIPT)
        fields["provides"] = ["p:bridge"]
        self.MODULES = {"h": (support_project.HARNESS, {}), "tool": (fields, files)}
        self.pinned()
        self.refused("--provides", "p:bridge", "tool", "describe", "push", contains="not an action")
        self.assertEqual(0, self.go("--provides", "p:bridge", "tool", "describe", "commit")[0])


class NothingListed(Run):
    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(EMPTY, helper=SCRIPT)}

    def test_every_action_is_refused_when_the_list_is_empty(self):
        self.pinned()
        for args in (("describe",), ("describe", "commit"), ("describe", "remove")):
            with self.subTest(args):
                self.refused("tool", *args, contains="describe")
        self.assertFalse(self.ran())

    def test_the_other_argument_still_runs(self):
        self.pinned()
        self.assertEqual(0, self.go("tool", "check")[0])


class Launched(Run):
    """``wb launch <id> <name> --root <dir> -- <args>`` of a pin the installer made."""

    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(DESCRIBING, helper=SCRIPT)}

    def go_launch(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(launch, "launch", return_value=0) as spy:
            code = cli.main(["launch", self.project_id, "tool", "--root", self.real, "--"] + list(args),
                            out, err, store_root=self.store_root)
        return code, err.getvalue(), spy

    def test_a_listed_action_launches(self):
        self.ready()
        code, err, spy = self.go_launch("describe", "commit")
        self.assertEqual((0, ""), (code, err))
        spy.assert_called_once()

    def test_an_unlisted_action_and_a_missing_action_are_refused_and_nothing_launches(self):
        self.ready()
        for args in (("describe", "push"), ("describe",), ("describe", "")):
            with self.subTest(args):
                code, err, spy = self.go_launch(*args)
                self.assertEqual(1, code)
                self.assertEqual(1, len(err.splitlines()), err)
                self.assertTrue(err.startswith("refused: "), err)
                spy.assert_not_called()

    def test_a_pin_the_owner_typed_for_the_declared_helper_keeps_the_rule(self):
        self.ready()
        self.pin()
        code, err, spy = self.go_launch("describe", "push")
        self.assertEqual(1, code)
        self.assertIn("refused: ", err)
        spy.assert_not_called()

    def test_a_pin_the_owner_typed_for_another_name_is_left_alone(self):
        self.ready()
        self.pin(name="mine")
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(launch, "launch", return_value=0) as spy:
            code = cli.main(["launch", self.project_id, "mine", "--root", self.real, "--", "describe", "push"],
                            out, err, store_root=self.store_root)
        self.assertEqual((0, ""), (code, err.getvalue()))
        spy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
