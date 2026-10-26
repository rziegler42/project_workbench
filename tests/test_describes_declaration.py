"""The `describes` field of a command: the actions its `describe` argument answers. Increment A of the plan dated
2026-10-25 that builds the `describe` command of a git module.

Everything here is synthetic: a module named `sample-notes` with a command `run-it`. The installer knows no module."""

import copy
import unittest

from tests.test_declarations import dump, module
from workbench import declarations as d


def declared(**fields):
    return module(ships=["scripts"], commands={"run-it": dict({"helper": "scripts/run"}, **fields)})


class Declaration(unittest.TestCase):
    def parse(self, decl):
        return d.parse_module(dump(decl), "sample", decl.get("name", "sample-notes"))

    def refused(self, **fields):
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(declared(**fields))
        self.assertEqual("commands", ctx.exception.rule)
        return str(ctx.exception)

    def test_a_command_with_no_describes_list_describes_nothing(self):
        got = self.parse(declared(arguments=["describe"])).commands[0]
        self.assertEqual((), got.describes)

    def test_an_empty_list_is_allowed_with_or_without_the_describe_argument(self):
        for arguments in ([], ["check"], ["describe"]):
            got = self.parse(declared(arguments=arguments, describes=[])).commands[0]
            self.assertEqual((), got.describes)

    def test_a_list_of_actions_is_kept_in_order(self):
        got = self.parse(declared(arguments=["describe", "commit"], describes=["remove", "commit"])).commands[0]
        self.assertEqual(("remove", "commit"), got.describes)
        self.assertEqual(("describe", "commit"), got.arguments)

    def test_sixteen_actions_are_allowed_and_seventeen_are_not(self):
        names = ["a%d" % n for n in range(d.MAX_DESCRIBES)]
        self.assertEqual(16, len(names))
        self.parse(declared(arguments=["describe"], describes=names))
        self.refused(arguments=["describe"], describes=names + ["a99"])

    def test_an_action_of_thirty_two_characters_is_allowed_and_longer_is_not(self):
        self.parse(declared(arguments=["describe"], describes=["x" * 32]))
        self.refused(arguments=["describe"], describes=["x" * 33])

    def test_a_non_empty_list_needs_describe_among_the_arguments(self):
        self.assertIn("describe", self.refused(arguments=["check"], describes=["commit"]))
        self.refused(describes=["commit"])

    def test_describe_may_not_be_owner_run(self):
        self.assertIn("describe", self.refused(arguments=["describe"], owner=["describe"], describes=[]))
        self.refused(arguments=["describe", "wipe"], owner=["describe"], describes=["commit"])

    def test_describe_may_be_owner_run_in_no_form_even_when_the_list_is_empty(self):
        self.refused(arguments=["describe"], owner=["describe"])

    def test_a_repeated_action_is_refused(self):
        self.refused(arguments=["describe"], describes=["commit", "commit"])

    def test_a_list_that_is_not_a_list_of_strings_is_refused(self):
        for bad in ("commit", {"commit": 1}, 3, None, [3], [None], [["commit"]], [True]):
            self.refused(arguments=["describe"], describes=bad)

    def test_an_action_of_the_wrong_form_is_refused(self):
        for bad in ("Commit", "com mit", "-commit", "commit;ls", "", "commit*", "co/mmit", "1commit", "commit\n"):
            self.refused(arguments=["describe"], describes=[bad])

    def test_the_field_is_part_of_the_declaration_hash(self):
        plain = copy.deepcopy(declared(arguments=["describe"]))
        marked = copy.deepcopy(declared(arguments=["describe"], describes=["commit"]))
        other = copy.deepcopy(declared(arguments=["describe"], describes=["remove"]))
        got = [self.parse(item).declaration for item in (plain, marked, other)]
        self.assertNotEqual(got[0], got[1])
        self.assertNotEqual(got[1], got[2])
        self.assertNotEqual(got[0], got[2])

    def test_an_unknown_field_is_still_refused(self):
        self.refused(arguments=["describe"], describe=["commit"])

    def test_a_command_built_without_the_field_has_none(self):
        self.assertEqual((), d.Command("c", "h", "exec", None, ("a",)).describes)
        self.assertEqual(("x",), d.Command("c", "h", "exec", None, ("a",), (), ("x",)).describes)


if __name__ == "__main__":
    unittest.main()
