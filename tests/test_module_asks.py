"""A module's declared asks: the ``asks`` field of a command and the module's ``ask_reads``, how they are read, and the
rules rendered for them. Increment B of the plan ``2026-10-29-policy-and-module-asks``; the decision is
``2026-10-29-workbench-asks-for-remove-submit-and-fetch``.

Everything here is synthetic: a module named `sample-notes` with a command `run-it`. The installer knows no module."""

import json
import os
import types
import unittest

from tests import test_install_attach
from tests.test_declarations import dump, module
from tests.test_permissions import HOME, STORE, lists, render
from workbench import declarations as d
from workbench import harnessstage, neutral, rules

ARGUMENTS = ["check", "show", "wipe", "reset"]


def declared(**fields):
    base = {"helper": "scripts/run", "arguments": ARGUMENTS, "owner": ["reset"]}
    base.update(fields)
    return module(ships=["scripts"], commands={"run-it": base})


def parse(decl):
    return d.parse_module(dump(decl), "sample", decl.get("name", "sample-notes"))


class Commands(unittest.TestCase):
    def command(self, **fields):
        return parse(declared(**fields)).commands[0]

    def refused(self, **fields):
        with self.assertRaises(d.DeclarationError) as ctx:
            parse(declared(**fields))
        self.assertEqual("commands", ctx.exception.rule)
        self.assertNotIn("unknown key", str(ctx.exception))
        return str(ctx.exception)

    def test_a_command_without_the_field_asks_nothing(self):
        self.assertEqual((), self.command().asks)

    def test_a_command_built_without_the_field_asks_nothing(self):
        self.assertEqual((), d.Command("c", "h", "exec", None, ("a",)).asks)

    def test_asks_are_read_in_the_order_written(self):
        self.assertEqual(("wipe", "show"), self.command(asks=["wipe", "show"]).asks)

    def test_an_ask_may_not_be_an_owner_run_argument(self):
        self.assertIn("owner", self.refused(asks=["reset"]))

    def test_an_ask_must_be_a_declared_argument(self):
        self.assertIn("arguments", self.refused(asks=["delete"]))

    def test_the_field_must_be_a_non_empty_list_of_different_strings(self):
        for label, value in (("a string", "wipe"), ("an object", {"wipe": 1}), ("empty", []), ("a number", [1]),
                             ("null", None), ("a repeat", ["wipe", "wipe"]), ("a list in a list", [["wipe"]])):
            with self.subTest(label):
                self.refused(asks=value)

    def test_other_unknown_fields_are_still_refused(self):
        with self.assertRaises(d.DeclarationError):
            parse(declared(ask=["wipe"]))

    def test_an_asked_argument_changes_the_declaration_hash(self):
        plain = parse(declared())
        asking = parse(declared(asks=["wipe"]))
        self.assertNotEqual(plain.declaration, asking.declaration)

    def test_the_declaration_is_kept_as_written_so_a_module_with_neither_field_hashes_as_before(self):
        written = declared()
        self.assertEqual(written, parse(written).declaration)
        self.assertEqual(written, parse(module()).declaration | {"commands": written["commands"], "ships": ["scripts"]})
        self.assertNotIn("asks", parse(written).declaration["commands"]["run-it"])
        self.assertNotIn("ask_reads", parse(written).declaration)
        asking = declared(asks=["wipe"])
        self.assertEqual(["wipe"], parse(asking).declaration["commands"]["run-it"]["asks"])


class Reads(unittest.TestCase):
    def reads(self, value):
        return parse(module(ask_reads=value))

    def test_a_module_without_the_field_asks_for_no_read(self):
        self.assertEqual((), parse(module()).ask_reads)

    def test_a_module_built_without_the_field_asks_for_no_read(self):
        self.assertEqual((), d.Module("m", "1.0.0", "module", "x", (), (), (), (), (), (), (), (), (), (), None, {}).ask_reads)

    def test_patterns_under_the_home_directory_are_read(self):
        got = self.reads(["~/.vendor/login.json", "~/.config/vendor/**"])
        self.assertEqual(("~/.vendor/login.json", "~/.config/vendor/**"), got.ask_reads)

    def test_every_bad_pattern_is_refused(self):
        bad = {"not a list": "~/.a", "empty": [], "not text": [1], "a repeat": ["~/.a", "~/.a"], "null": None,
               "no home prefix": ["/etc/shadow"], "relative": [".vendor/login"], "another user": ["~root/.a"],
               "only the prefix": ["~/"], "only wildcards": ["~/**"], "wildcards and slashes": ["~/*/**"],
               "a wildcard first": ["~/**/x"], "dot and wildcard": ["~/.*"], "wildcards and a dot": ["~/*.*"],
               "dots and a wildcard": ["~/..*"], "a dot segment": ["~/./x"], "a dot segment in the middle": ["~/a/./b"],
               "an empty segment": ["~//x"], "an empty segment in the middle": ["~/a//b"], "a trailing slash": ["~/x/"],
               "a dot alone": ["~/."],
               "a parent segment": ["~/../etc/shadow"], "a parent in the middle": ["~/a/../b"],
               "a parent alone": ["~/.."], "a parent at the end": ["~/a/.."], "an encoded parent": ["~/%2e%2e/x"],
               "an edge space": ["~/.a "], "a leading space": [" ~/.a"],
               "non-ASCII": ["~/.café"], "a control character": ["~/.a\n"], "a backslash": ["~/.a\\b"],
               "empty text": [""], "too long": ["~/" + "a" * 200], "too many": ["~/.a%d" % n for n in range(17)]}
        for label, value in bad.items():
            with self.subTest(label):
                with self.assertRaises(d.DeclarationError) as ctx:
                    self.reads(value)
                self.assertEqual("ask_reads", ctx.exception.rule)

    def test_the_characters_and_the_length_are_those_of_a_neutral_rule(self):
        self.assertEqual(neutral.PATTERN_CHARS, d.ASK_READ_CHARS)
        self.assertEqual(neutral.MAX_PATTERN_CHARS, d.MAX_ASK_READ_CHARS)

    def test_a_pattern_the_schema_accepts_is_a_neutral_rule(self):
        for pattern in ("~/.vendor/login.json", "~/.config/vendor/**", "~/a b/c*", "~/.x@y=z+w-v_u", "~/.ssh/**", "~/*.json",
                        "~/.vendor-x/**"):
            with self.subTest(pattern):
                self.assertEqual(1, len(neutral.read_rules([{"action": "ask", "tool": "read", "pattern": pattern}])))
                self.assertEqual((pattern,), self.reads([pattern]).ask_reads)

    def test_the_longest_pattern_and_the_most_patterns_are_read(self):
        self.assertEqual(1, len(self.reads(["~/" + "a" * 198]).ask_reads))
        self.assertEqual(16, len(self.reads(["~/.a%d" % n for n in range(16)]).ask_reads))


def installed(*decls):
    """The modules as the staging sees them: objects with a `.module`."""
    return [types.SimpleNamespace(module=parse(item), type=parse(item).type) for item in decls]


class Rendered(unittest.TestCase):
    def rules_of(self, *decls):
        return harnessstage.ask_rules(installed(*decls))

    def test_each_asked_argument_is_asked_in_every_spelling(self):
        found = self.rules_of(declared(asks=["wipe", "show"]))
        self.assertEqual({"ask"}, {rule.action for rule in found})
        self.assertEqual({"shell"}, {rule.tool for rule in found})
        want = rules.command_owner_patterns("run-it", ["wipe", "show"])
        self.assertEqual(sorted(want), sorted(rule.pattern for rule in found))
        for spelling in rules.SPELLINGS:
            for argument in ("wipe", "show"):
                self.assertIn("%s run run-it %s" % (spelling, argument), [rule.pattern for rule in found])
                self.assertIn("%s run run-it %s *" % (spelling, argument), [rule.pattern for rule in found])
                self.assertIn("%s run --provides * run-it %s" % (spelling, argument), [rule.pattern for rule in found])

    def test_each_read_is_asked_for_the_read_tool(self):
        found = self.rules_of(module(ask_reads=["~/.vendor/login.json"]))
        self.assertEqual([neutral.Rule("ask", "read", "~/.vendor/login.json")], found)

    def test_a_module_with_neither_field_renders_nothing_new(self):
        self.assertEqual([], self.rules_of(declared(), module()))
        self.assertEqual(render(), render(harnessstage.ask_rules(installed(declared()))))

    def test_the_rendered_rules_are_asks_and_never_an_allow_or_a_deny(self):
        found = self.rules_of(declared(asks=["wipe"]), module(name="other-notes", ask_reads=["~/.vendor/login.json"]))
        deny, ask = lists(module_rules=found)
        baseline_deny, baseline_ask = lists()
        self.assertEqual(baseline_deny, deny)
        self.assertIn("Bash(wb run run-it wipe)", ask)
        self.assertIn("Bash(wb run run-it wipe *)", ask)
        self.assertIn("Read(/%s/.vendor/login.json)" % HOME, ask)
        self.assertEqual({"ask", "deny"}, set(json.loads(render(module_rules=found))["permissions"]))

    def test_a_read_that_repeats_a_floor_rule_renders_once(self):
        _, baseline = lists()
        _, ask = lists(module_rules=[neutral.Rule("ask", "read", "~/.ssh/**")])
        self.assertEqual(baseline, ask)

    def test_an_asked_pattern_is_not_rendered_when_it_is_also_denied(self):
        found = self.rules_of(declared(asks=["wipe"]))
        deny, ask = lists(module_rules=found + [neutral.Rule("deny", "shell", "wb run run-it wipe")])
        self.assertIn("Bash(wb run run-it wipe)", deny)
        self.assertNotIn("Bash(wb run run-it wipe)", ask)

    def test_the_owner_rules_are_untouched(self):
        found = harnessstage.owner_rules(installed(declared(asks=["wipe"])))
        self.assertTrue(all(rule.action == "deny" for rule in found))
        self.assertIn("wb run run-it reset", [rule.pattern for rule in found])
        self.assertNotIn("wb run run-it wipe", [rule.pattern for rule in found])


TOOL = ({"ships": ["helper/tool"],
         "commands": {"tool": {"helper": "helper/tool", "arguments": ["go", "wipe"], "asks": ["wipe"]}},
         "ask_reads": ["~/.vendor/login.json"]},
        {"helper/tool": b"#!/bin/sh\necho ran\n"})


class Installed(test_install_attach.Base):
    """The whole path: an install writes the asks into the harness's local settings."""

    def settings(self, place):
        with open(os.path.join(place, ".fixture", "settings.local.json"), encoding="utf-8") as handle:
            return json.load(handle)["permissions"]

    def test_an_install_renders_the_declared_asks_and_never_an_allow(self):
        path = self.notes(*TOOL)
        place = self.place("proj")
        code, out, err = self.install(place, path)
        self.assertEqual(0, code, (out, err))
        permissions = self.settings(place)
        self.assertIn("Bash(wb run tool wipe)", permissions["ask"])
        self.assertIn("Bash(wb run tool wipe *)", permissions["ask"])
        self.assertNotIn("Bash(wb run tool go)", permissions["ask"])
        self.assertIn("Read(//%s/.vendor/login.json)" % os.path.realpath(self.home).lstrip("/"), permissions["ask"])
        self.assertEqual({"ask", "deny"}, set(permissions))

    def test_a_module_that_declares_nothing_renders_what_it_always_did(self):
        path = self.notes()
        place = self.place("proj")
        code, out, err = self.install(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertFalse([text for text in self.settings(place)["ask"] if "tool" in text])


if __name__ == "__main__":
    unittest.main()
