"""Owner-run arguments: a command may declare first arguments only the owner runs, and an attached harness that
provides permissions denies each one. Increment B of the plan dated 2026-10-23 that adds the review engine.

Everything here is synthetic: a module named `tool` with a command `tool`, and the fixture harness. The installer
knows no module, so nothing in these tests or in `workbench/` names a first-party one."""

import copy
import json
import unittest

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from tests.test_attach import SETTINGS
from tests.test_declarations import dump, module
from workbench import declarations as d
from workbench import neutral, rules

SPELLINGS = ("wb", "python3 -m workbench", "python3 -B -m workbench", "python -m workbench",
             "python -B -m workbench")


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

    def test_a_command_with_no_owner_list_has_no_owner_run_argument(self):
        got = self.parse(declared(arguments=["check"])).commands[0]
        self.assertEqual((), got.owner)

    def test_an_empty_owner_list_is_the_same_as_none(self):
        got = self.parse(declared(arguments=["check"], owner=[])).commands[0]
        self.assertEqual((), got.owner)

    def test_an_owner_list_is_a_subset_of_the_arguments(self):
        got = self.parse(declared(arguments=["check", "wipe", "reset"], owner=["wipe", "reset"])).commands[0]
        self.assertEqual(("wipe", "reset"), got.owner)
        self.assertEqual(("check", "wipe", "reset"), got.arguments)

    def test_every_argument_may_be_owner_run(self):
        got = self.parse(declared(arguments=["wipe"], owner=["wipe"])).commands[0]
        self.assertEqual(("wipe",), got.owner)

    def test_an_owner_argument_that_is_not_an_argument_is_refused(self):
        self.assertIn("wipe", self.refused(arguments=["check"], owner=["wipe"]))

    def test_an_owner_list_on_a_command_with_no_arguments_is_refused(self):
        self.refused(owner=["wipe"])

    def test_a_repeated_owner_argument_is_refused(self):
        self.refused(arguments=["wipe"], owner=["wipe", "wipe"])

    def test_an_owner_list_that_is_not_a_list_of_strings_is_refused(self):
        for bad in ("wipe", {"wipe": 1}, 3, None, [3], [None], [["wipe"]], [True]):
            self.refused(arguments=["wipe"], owner=bad)

    def test_an_owner_argument_of_the_wrong_form_is_refused(self):
        for bad in ("Wipe", "wi pe", "-wipe", "wipe;ls", "", "x" * 33, "wipe*", "wi/pe"):
            self.refused(arguments=["wipe"], owner=[bad])

    def test_an_owner_list_may_not_be_longer_than_the_arguments(self):
        names = ["a%d" % n for n in range(d.MAX_ARGUMENTS)]
        self.refused(arguments=names, owner=names + ["a99"])

    def test_the_field_is_part_of_the_declaration_hash(self):
        plain = copy.deepcopy(declared(arguments=["wipe"]))
        marked = copy.deepcopy(declared(arguments=["wipe"], owner=["wipe"]))
        self.assertNotEqual(self.parse(plain).declaration, self.parse(marked).declaration)

    def test_a_command_built_without_the_field_has_none(self):
        self.assertEqual((), d.Command("c", "h", "exec", None, ("a",)).owner)


class Patterns(unittest.TestCase):
    def test_each_owner_argument_is_denied_bare_with_arguments_and_through_a_capability(self):
        got = rules.command_owner_patterns("tool", ("wipe",))
        for spelling in SPELLINGS:
            for text in ("%s run tool wipe", "%s run tool wipe *", "%s run --provides * tool wipe",
                         "%s run --provides * tool wipe *"):
                self.assertIn(text % spelling, got)
        self.assertEqual(len(SPELLINGS) * 4, len(got))

    def test_nothing_is_produced_without_an_owner_argument(self):
        self.assertEqual([], rules.command_owner_patterns("tool", ()))

    def test_only_the_named_argument_is_matched_and_no_other(self):
        for text in rules.command_owner_patterns("tool", ("wipe",)):
            self.assertIn(" tool wipe", text)
            self.assertNotIn("check", text)

    def test_every_pattern_is_a_valid_neutral_deny_rule(self):
        patterns = rules.command_owner_patterns("tool-x_1.2+3", ("wipe-all",))
        data = [{"action": "deny", "tool": "shell", "pattern": text} for text in patterns]
        self.assertEqual(len(patterns), len(neutral.read_rules(data)))

    def test_the_longest_name_and_argument_still_fit_a_neutral_rule(self):
        name, argument = "a" * d.MAX_NAME_CHARS, "b" * d.MAX_ARGUMENT_CHARS
        for text in rules.command_owner_patterns(name, (argument,)):
            self.assertLessEqual(len(text), neutral.MAX_PATTERN_CHARS)
            neutral.read_rules([{"action": "deny", "tool": "shell", "pattern": text}])

    def test_the_compiled_in_owner_run_list_is_the_one_listed(self):
        self.assertEqual(("install", "adopt", "upgrade", "add", "attach", "rerender", "acknowledge", "recover", "approve",
                          "pin", "release-approvals", "approve-plan"), rules.OWNER_RUN)


COMMAND = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "report", "wipe"], "owner": ["wipe"]}}


class Rendered(support_project.Project):
    """The rendered settings of an attached harness deny the owner-run arguments of the installed modules."""

    MODULES = dict(support_project.Project.MODULES, tool=tool(COMMAND))

    def deny_and_ask(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        document = json.loads(self.read(SETTINGS))
        return document["permissions"]["deny"], document["permissions"]["ask"]

    def test_the_owner_run_argument_is_denied_in_each_spelling(self):
        deny, _ = self.deny_and_ask()
        for spelling in SPELLINGS:
            for text in ("%s run tool wipe", "%s run tool wipe *", "%s run --provides * tool wipe",
                         "%s run --provides * tool wipe *"):
                self.assertIn("Bash(%s)" % (text % spelling), deny)

    def test_the_other_arguments_are_not_denied_or_asked(self):
        deny, ask = self.deny_and_ask()
        for text in deny + ask:
            self.assertNotIn("tool check", text)
            self.assertNotIn("tool report", text)

    def test_there_is_no_allow_and_the_output_has_only_deny_and_ask(self):
        self.ready()
        self.attach()
        document = json.loads(self.read(SETTINGS))
        self.assertEqual({"deny", "ask"}, set(document["permissions"]))

    def test_the_lists_are_sorted(self):
        deny, ask = self.deny_and_ask()
        self.assertEqual(sorted(deny), deny)
        self.assertEqual(sorted(ask), ask)


class NoOwnerArgument(support_project.Project):
    def test_a_module_with_no_owner_list_adds_no_rule(self):
        self.ready()
        self.attach()
        document = json.loads(self.read(SETTINGS))
        for text in document["permissions"]["deny"] + document["permissions"]["ask"]:
            self.assertNotIn(" run ", text)


if __name__ == "__main__":
    unittest.main()
