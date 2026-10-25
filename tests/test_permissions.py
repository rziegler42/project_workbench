import ast
import json
import os
import unittest

from workbench import cli, floor, harnessplan, neutral, rules
from tests.support_harness import SYNTHETIC
from tests.test_layout import edit

HOME = "/Users/tester"
STORE = HOME + "/.config/project-workbench"


def render(module_rules=(), layout=SYNTHETIC, store=STORE, home=HOME):
    return harnessplan.render_permissions(list(module_rules), layout, store, home)


def lists(layout=SYNTHETIC, **kw):
    document = json.loads(render(layout=layout, **kw))
    return document["permissions"]["deny"], document["permissions"]["ask"]


class OwnerRun(unittest.TestCase):
    def test_every_owner_run_command_is_denied_in_each_spelling(self):
        deny, _ = lists()
        for spelling in ("wb", "python3 -m workbench", "python3 -B -m workbench",
                         "python -m workbench", "python -B -m workbench"):
            for command in ("install", "upgrade", "add", "attach", "acknowledge", "recover",
                            "approve", "pin", "release-approvals"):
                self.assertIn("Bash(%s %s)" % (spelling, command), deny)
                self.assertIn("Bash(%s %s *)" % (spelling, command), deny)

    def test_preview_and_the_read_only_commands_are_not_denied(self):
        deny, ask = lists()
        for text in deny + ask:
            for word in ("preview", "verify", "launch"):
                self.assertNotIn(word, text)

    def test_run_is_not_denied_or_asked_in_any_spelling(self):
        deny, ask = lists()
        for spelling in rules.SPELLINGS:
            for text in deny + ask:
                self.assertFalse(text.startswith("Bash(%s run" % spelling), text)

    def test_the_constant_is_the_documented_list(self):
        self.assertEqual(set(rules.OWNER_RUN), {
            "install", "adopt", "upgrade", "add", "attach", "acknowledge", "recover", "approve", "pin",
            "release-approvals", "approve-plan"})

    def test_the_cli_routes_nothing_that_is_unclassified(self):
        """A command routed in cli.py is owner-run or agent-safe; a new one fails here."""
        with open(cli.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        routed = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_parser" and node.args
                    and isinstance(node.args[0], ast.Constant)):
                routed.add(node.args[0].value)
            if isinstance(node, ast.Compare) and "argv[0]" in ast.unparse(node.left):
                for comparator in node.comparators:
                    for part in ast.walk(comparator):
                        if isinstance(part, ast.Constant) and isinstance(part.value, str):
                            routed.add(part.value)
        self.assertEqual(routed & set(rules.NOT_YET_ROUTED), set(),
                         "routed now: empty NOT_YET_ROUTED")
        known = set(rules.OWNER_RUN) | set(rules.AGENT_SAFE)
        self.assertEqual(routed - known, set(), "routed in cli.py but not classified in rules.py")
        self.assertEqual(known - routed - set(rules.NOT_YET_ROUTED), set(),
                         "classified in rules.py but not routed")


class Store(unittest.TestCase):
    def test_writes_to_the_store_are_denied_in_the_double_slash_form(self):
        deny, _ = lists()
        self.assertIn("Edit(//Users/tester/.config/project-workbench)", deny)
        self.assertIn("Edit(//Users/tester/.config/project-workbench/**)", deny)

    def test_home_form(self):
        deny, _ = lists(edit(["local_settings", "absolute"], "~/"))
        self.assertIn("Edit(~/.config/project-workbench)", deny)
        self.assertIn("Edit(~/.config/project-workbench/**)", deny)

    def test_no_rule_uses_the_inert_write_name_or_a_single_slash_path(self):
        deny, ask = lists()
        for text in deny + ask:
            self.assertFalse(text.startswith("Write("), text)
            if text.startswith(("Edit(/", "Read(/")):
                self.assertTrue(text.startswith(("Edit(//", "Read(//")), text)

    def test_a_store_outside_home_cannot_use_the_home_form(self):
        with self.assertRaises(harnessplan.PlanError):
            render(layout=edit(["local_settings", "absolute"], "~/"), store="/srv/store")

    def test_a_path_that_is_not_safe_to_write_is_refused(self):
        for store in ("/Users/tester/a)b", "/Users/tester/a*b", "relative/store",
                      "/Users/tester/café", "/Users/tester/a\nb"):
            with self.assertRaises(harnessplan.PlanError, msg=store):
                render(store=store)


class Floor(unittest.TestCase):
    def test_every_hard_stop_has_rules(self):
        self.assertEqual(set(rules.FLOOR_RULES), {stop.id for stop in floor.FLOOR})
        for stop_id, entries in rules.FLOOR_RULES.items():
            self.assertTrue(entries, stop_id)
            for action, tool, pattern in entries:
                self.assertEqual(action, "ask")
                neutral.read_rules([{"action": action, "tool": tool, "pattern": pattern}])

    def test_the_floor_is_rendered_as_ask_rules(self):
        _, ask = lists()
        for entries in rules.FLOOR_RULES.values():
            for _, tool, pattern in entries:
                if tool == "shell":
                    self.assertIn("Bash(%s)" % pattern, ask)
        self.assertIn("Bash(git push --force*)", ask)
        self.assertIn("Bash(rm *)", ask)
        self.assertIn("Bash(pip install*)", ask)
        self.assertIn("Read(.env)", ask)
        self.assertIn("Read(//Users/tester/.ssh/**)", ask)

    def test_the_floor_is_rendered_without_any_module_rules(self):
        _, ask = lists()
        self.assertTrue(ask)


class ModuleRules(unittest.TestCase):
    def test_a_module_rule_is_rendered_by_action(self):
        deny, ask = lists(module_rules=[neutral.Rule("deny", "shell", "make release*"),
                                        neutral.Rule("ask", "write", "docs/**"),
                                        neutral.Rule("deny", "read", "/etc/shadow")])
        self.assertIn("Bash(make release*)", deny)
        self.assertIn("Edit(docs/**)", ask)
        self.assertIn("Read(//etc/shadow)", deny)

    def test_a_deny_removes_the_same_ask(self):
        deny, ask = lists(module_rules=[neutral.Rule("deny", "shell", "git push")])
        self.assertIn("Bash(git push)", deny)
        self.assertNotIn("Bash(git push)", ask)

    def test_only_neutral_rules_are_accepted(self):
        for bad in ({"action": "allow", "tool": "shell", "pattern": "ls"},
                    ("allow", "shell", "ls"), neutral.Rule("allow", "shell", "ls"),
                    neutral.Rule("deny", "mcp", "x")):
            with self.assertRaises(harnessplan.PlanError):
                render(module_rules=[bad])


class Hostile(unittest.TestCase):
    def test_a_layout_without_a_read_template_is_a_plan_error(self):
        layout = edit(["local_settings", "rules"],
                      {"shell": "Bash({pattern})", "write": "Edit({path})"})
        with self.assertRaises(harnessplan.PlanError):
            render(layout=layout)

    def test_a_hand_built_rule_with_a_bad_pattern_is_refused(self):
        for pattern in ("x)", "", "a:*", "a\nb", "../x", " x", None, 3):
            with self.assertRaises(harnessplan.PlanError, msg=repr(pattern)):
                render(module_rules=[neutral.Rule("deny", "shell", pattern)])

    def test_dot_and_empty_segments_in_the_base_paths_are_refused(self):
        for store in ("/Users/tester/../x", "/Users//tester/.config", "/Users/tester/./s", "/"):
            with self.assertRaises(harnessplan.PlanError, msg=store):
                render(store=store)
        with self.assertRaises(harnessplan.PlanError):
            render(home="/Users/../x")

    def test_a_home_pattern_is_rendered_in_each_form(self):
        rule = [neutral.Rule("deny", "write", "~/.bashrc")]
        deny, _ = lists(module_rules=rule)
        self.assertIn("Edit(//Users/tester/.bashrc)", deny)
        deny, _ = lists(edit(["local_settings", "absolute"], "~/"), module_rules=rule)
        self.assertIn("Edit(~/.bashrc)", deny)

    def test_the_install_forms_are_asked_for(self):
        _, ask = lists()
        for text in ("npm i", "npm ci*", "yarn", "python -m pip install*", "uv sync*"):
            self.assertIn("Bash(%s)" % text, ask)


class Home(unittest.TestCase):
    def test_a_tilde_that_is_not_the_home_form_is_refused(self):
        for tool in ("read", "write"):
            for pattern in ("~", "~root/x", "~x"):
                with self.assertRaises(harnessplan.PlanError, msg=pattern):
                    render(module_rules=[neutral.Rule("deny", tool, pattern)])


class Output(unittest.TestCase):
    def test_there_is_no_allow_anywhere(self):
        data = render(module_rules=[neutral.Rule("deny", "shell", "x")])
        document = json.loads(data)
        self.assertEqual(set(document), {"permissions"})
        self.assertEqual(set(document["permissions"]), {"deny", "ask"})
        self.assertNotIn(b"allow", data.lower())

    def test_the_output_is_byte_identical_and_sorted(self):
        first = render(module_rules=[neutral.Rule("deny", "shell", "b"),
                                     neutral.Rule("deny", "shell", "a")])
        second = render(module_rules=[neutral.Rule("deny", "shell", "a"),
                                      neutral.Rule("deny", "shell", "b")])
        self.assertEqual(first, second)
        deny, ask = lists()
        self.assertEqual(deny, sorted(deny))
        self.assertEqual(ask, sorted(ask))
        self.assertTrue(first.endswith(b"}\n"))

    def test_a_key_other_than_permissions_cannot_render(self):
        layout = edit(["local_settings", "actions"], {"deny": "rules.deny", "ask": "rules.ask"})
        with self.assertRaises(harnessplan.PlanError):
            render(layout=layout)

    def test_a_layout_with_no_settings_cannot_render(self):
        with self.assertRaises(harnessplan.PlanError):
            render(layout=edit(["local_settings"], "none"))

    def test_an_unverified_layout_is_refused(self):
        with self.assertRaises(harnessplan.PlanError):
            render(layout=edit(["exclude"], []))

    def test_the_file_is_utf8_json_with_ascii_only(self):
        render().decode("ascii")


if __name__ == "__main__":
    unittest.main()
