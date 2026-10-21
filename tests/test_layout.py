import copy
import json
import os
import unittest

from workbench import layout, neutral
from tests.support_harness import CLAUDE
from tests.test_modulefiles import Base


def edit(path, new, base=None):
    value = copy.deepcopy(base or CLAUDE)
    node = value
    for key in path[:-1]:
        node = node[key]
    if new is None:
        node.pop(path[-1], None)
    else:
        node[path[-1]] = new
    return value


class Accepted(unittest.TestCase):
    def test_the_claude_layout_is_accepted(self):
        self.assertEqual(layout.problems(CLAUDE), [])

    def test_the_minimal_layouts_are_accepted(self):
        self.assertEqual(layout.problems({}), [])
        self.assertEqual(layout.problems({"root": "none", "local_settings": "none",
                                          "hooks": "none"}), [])

    def test_the_constants_follow_the_neutral_reader(self):
        self.assertEqual(layout.TOOLS, neutral.TOOLS)
        self.assertEqual(layout.RULE_TOOLS, neutral.RULE_TOOLS)
        for kind, fields in layout.KIND_FIELDS.items():
            self.assertEqual(set(fields), set(neutral.FIELDS[kind][0]) | (
                set(neutral.FIELDS[kind][1]) - {"needs"}))


# A made-up harness, so these tests name no real one.
FIXTURE = {
    "root": {"file": "FIXTURE.md", "import": "AGENTS.md"},
    "kinds": {
        "skill": {"path": ".fixture/skills/{name}/SKILL.md",
                  "fields": {"name": "name", "description": "description"}},
        "command": {"path": ".fixture/prompts/{name}.md",
                    "fields": {"name": "name", "description": "description"}},
    },
    "exclude": ["FIXTURE.md", ".fixture/"],
    "tolerated": [".fixture/shared.json"],
}


class Facts(unittest.TestCase):
    def test_the_fixture_layout_is_accepted(self):
        self.assertEqual(layout.problems(FIXTURE), [])

    def test_facts_of_a_layout(self):
        self.assertEqual(layout.facts(FIXTURE), {
            "roots": ("FIXTURE.md", ".fixture"), "directories": (".fixture",),
            "generated": (".fixture/skills", ".fixture/prompts"),
            "tolerated": (".fixture/shared.json",)})

    def test_facts_of_the_claude_layout_include_its_settings_directory(self):
        found = layout.facts(CLAUDE)
        self.assertEqual(found["roots"], ("CLAUDE.md", ".claude"))
        self.assertEqual(found["directories"], (".claude",))
        self.assertEqual(found["generated"],
                         (".claude/skills", ".claude/agents", ".claude/commands"))

    def test_a_layout_with_nothing_gives_empty_facts(self):
        empty = {"roots": (), "directories": (), "generated": (), "tolerated": ()}
        self.assertEqual(layout.facts({}), empty)
        self.assertEqual(layout.facts({"root": "none", "local_settings": "none", "kinds": {}}), empty)

    def test_a_settings_file_alone_adds_its_directory(self):
        found = layout.facts({"local_settings": {"path": ".other/s.json"}})
        self.assertEqual((found["roots"], found["directories"], found["generated"]),
                         ((".other",), (".other",), ()))

    def test_a_top_level_settings_file_is_a_root_and_not_a_directory(self):
        found = layout.facts({"local_settings": {"path": "s.json"}})
        self.assertEqual((found["roots"], found["directories"]), (("s.json",), ()))

    def test_two_kinds_in_one_top_level_directory_give_it_once(self):
        found = layout.facts(FIXTURE)
        self.assertEqual(found["roots"].count(".fixture"), 1)


class Tolerated(unittest.TestCase):
    def bad(self, tolerated, text="layout.tolerated"):
        value = copy.deepcopy(FIXTURE)
        value["tolerated"] = tolerated
        found = layout.problems(value)
        self.assertTrue(found, "accepted: %r" % (tolerated,))
        self.assertTrue(any(text in message for message in found), found)

    def test_a_layout_need_not_tolerate_anything(self):
        value = copy.deepcopy(FIXTURE)
        del value["tolerated"]
        self.assertEqual(layout.problems(value), [])
        value["tolerated"] = []
        self.assertEqual(layout.problems(value), [])

    def test_a_path_in_a_kind_directory_is_accepted(self):
        value = copy.deepcopy(FIXTURE)
        value["tolerated"] = [".fixture/skills/extra.json", ".fixture/a/b/c.json"]
        self.assertEqual(layout.problems(value), [])

    def test_not_a_list_or_too_long(self):
        for value in ("x", {}, None, 3, [".fixture/%d.json" % n for n in range(17)]):
            self.bad(value)

    def test_the_limit_is_sixteen(self):
        value = copy.deepcopy(FIXTURE)
        value["tolerated"] = [".fixture/%d.json" % n for n in range(16)]
        self.assertEqual(layout.problems(value), [])

    def test_unsafe_or_reserved_paths(self):
        for path in (3, None, ["x"], "", "/abs/x", "../x", ".fixture/../x", ".fixture\\x", ".fixture/x\0",
                     ".git/config", ".workbench/x", ".Workbench/x", ".config/project-workbench/x"):
            self.bad([path])

    def test_a_path_outside_every_written_directory(self):
        for path in ("elsewhere/x.json", "x.json", ".other/x.json"):
            self.bad([path], "not inside a directory")

    def test_the_directory_must_be_spelled_as_the_layout_spells_it(self):
        self.bad([".FIXTURE/x.json"], "spelled")

    def test_a_single_segment_kind_directory_is_a_directory(self):
        value = {"kinds": {"skill": {"path": "skills/{name}/SKILL.md",
                                     "fields": {"name": "name", "description": "description"}}},
                 "exclude": ["skills/"], "tolerated": ["skills/x.json"]}
        self.assertEqual(layout.problems(value), [])
        self.assertEqual(layout.facts(value)["directories"], ("skills",))

    def test_a_path_that_contains_a_written_path_is_refused(self):
        value = {"kinds": {"skill": {"path": ".a/b/skills/{name}/SKILL.md",
                                     "fields": {"name": "name", "description": "description"}},
                           "command": {"path": ".a/c/{name}.md",
                                       "fields": {"name": "name", "description": "description"}}},
                 "exclude": [".a/"], "tolerated": [".a/b/x.json"]}
        self.assertEqual(layout.problems(value), [])
        for path in (".a/b", ".A/B"):
            value["tolerated"] = [path]
            self.assertTrue(any("layout.tolerated" in m for m in layout.problems(value)), path)

    def test_a_path_inside_a_file_the_layout_writes_is_refused(self):
        value = copy.deepcopy(CLAUDE)
        value["tolerated"] = [CLAUDE["local_settings"]["path"] + "/x"]
        self.assertTrue(any("inside a file" in m for m in layout.problems(value)))

    def test_unicode_spellings_of_one_path_are_a_duplicate(self):
        self.bad([".fixture/\u00e9.json", ".fixture/e\u0301.json"], "listed twice")

    def test_top_level_names_that_differ_only_in_case_are_refused(self):
        value = copy.deepcopy(FIXTURE)
        value["kinds"]["command"]["path"] = ".FIXTURE/prompts/{name}.md"
        value["exclude"] = ["FIXTURE.md", ".fixture/", ".FIXTURE/"]
        self.assertTrue(any("spelled" in m for m in layout.problems(value)))

    def test_a_listed_twice_path_even_in_another_case(self):
        self.bad([".fixture/x.json", ".fixture/x.json"], "listed twice")
        self.bad([".fixture/x.json", ".FIXTURE/X.json"], "listed twice")

    def test_a_path_the_layout_writes_is_not_tolerated(self):
        self.bad(["FIXTURE.md"], "written by this layout")
        self.bad(["FIXTURE.md/x.json"], "inside a file")
        self.bad([".fixture/skills"], "written by this layout")
        self.bad([".FIXTURE/Skills"], "written by this layout")

    def test_the_settings_file_is_not_tolerated(self):
        value = copy.deepcopy(CLAUDE)
        value["tolerated"] = [CLAUDE["local_settings"]["path"]]
        self.assertTrue(any("written by this layout" in m for m in layout.problems(value)))
        value["tolerated"] = [".claude/settings.json"]
        self.assertEqual(layout.problems(value), [])


class Refused(unittest.TestCase):
    def bad(self, value, text=""):
        found = layout.problems(value)
        self.assertTrue(found, "accepted: %r" % (value,))
        self.assertTrue(any(text in message for message in found), found)

    def test_not_an_object(self):
        for value in ([], "x", None, 3):
            self.bad(value)

    def test_root(self):
        for root in ("CLAUDE.md", [], {"file": "CLAUDE.md"}, {"import": "AGENTS.md"},
                     {"file": "a/b", "import": "AGENTS.md"}, {"file": "CLAUDE.md", "import": "../x"},
                     {"file": "/abs", "import": "AGENTS.md"}, {"file": ".git", "import": "x"},
                     {"file": 3, "import": "x"},
                     {"file": "CLAUDE.md", "import": "AGENTS.md", "extra": 1}):
            self.bad(edit(["root"], root), "layout.root")

    def test_reserved_places_are_refused_by_their_own_guard(self):
        self.bad(edit(["root", "file"], ".workbench"), "inside .workbench")
        self.bad(edit(["root", "file"], ".WorkBench"), "inside .workbench")
        for path in (".workbench/{name}/SKILL.md", ".Workbench/{name}/SKILL.md"):
            self.bad(edit(["kinds", "skill", "path"], path), "inside .workbench")
        for path in (".config/project-workbench/{name}/SKILL.md",
                     ".Config/Project-Workbench/{name}/SKILL.md"):
            self.bad(edit(["kinds", "skill", "path"], path), "guarded store")
        self.bad(edit(["local_settings", "path"], ".config/project-workbench/x.json"),
                 "guarded store")
        self.bad(edit(["local_settings", "path"], ".workbench/x.json"), "inside .workbench")
        self.bad(edit(["exclude"], CLAUDE["exclude"] + [".workbench/local/"]), "inside .workbench")
        self.bad(edit(["exclude"], CLAUDE["exclude"] + [".config/project-workbench/"]),
                 "guarded store")
        self.bad(edit(["exclude"], CLAUDE["exclude"] + [".git/"]), "git metadata")

    def test_kinds_keys_and_shape(self):
        self.bad(edit(["kinds"], []), "kinds")
        self.bad(edit(["kinds", "hook"], CLAUDE["kinds"]["skill"]), "hook")
        self.bad(edit(["kinds", "skill"], {"path": ".claude/skills/{name}/SKILL.md"}), "fields")
        self.bad(edit(["kinds", "skill", "extra"], 1), "extra")
        self.bad(edit(["kinds", "skill", "tools"], {"read": ["Read"]}), "tools")

    def test_kind_paths(self):
        for path in (".claude/skills/{name}.md", ".claude/skills/x/SKILL.md", "{name}/SKILL.md",
                     "/abs/{name}/SKILL.md", "../x/{name}/SKILL.md", ".git/{name}/SKILL.md",
                     ".workbench/{name}/SKILL.md", ".config/project-workbench/{name}/SKILL.md",
                     ".Config/Project-Workbench/{name}/SKILL.md", "a/{x}/{name}/SKILL.md",
                     ".claude\\skills/{name}/SKILL.md", 5):
            self.bad(edit(["kinds", "skill", "path"], path), "skill.path")
        for path in (".claude/agents/{name}/SKILL.md", ".claude/agents/{name}",
                     ".claude/agents/x.md"):
            self.bad(edit(["kinds", "agent", "path"], path), "agent.path")

    def test_two_kinds_may_not_share_a_directory(self):
        self.bad(edit(["kinds", "command", "path"], ".claude/agents/{name}.md"), "overlaps")
        self.bad(edit(["kinds", "command", "path"], ".claude/agents/sub/{name}.md"), "overlaps")
        self.bad(edit(["kinds", "command", "path"], ".CLAUDE/Agents/{name}.md"), "overlaps")

    def test_fields(self):
        for fields in ({"name": "name"}, {"description": "description"}, [],
                       {"name": "n", "description": "n"},
                       {"name": "name", "description": "description", "args": "x"},
                       {"name": "name", "description": "Description"},
                       {"name": "name", "description": 3},
                       {"name": "name", "description": "a b"}):
            self.bad(edit(["kinds", "skill", "fields"], fields), "fields")

    def test_tools(self):
        for tools in ({"read": []}, {"read": "Read"}, {"delete": ["x"]}, {"read": ["a b"]},
                      {"read": ["Read", "Read"]}, {"read": [3]}, [], {"read": ["x"] * 9}):
            self.bad(edit(["kinds", "agent", "tools"], tools), "tools")

    def test_local_settings(self):
        base = ["local_settings"]
        self.bad(edit(base, "settings.json"), "local_settings")
        self.bad(edit(base + ["path"], "../x"), "path")
        self.bad(edit(base + ["path"], ".git/info/x"), "path")
        self.bad(edit(base + ["path"], ".workbench/x"), "path")
        self.bad(edit(base + ["path"], ".config/project-workbench/x.json"), "guarded")
        self.bad(edit(base + ["format"], "toml"), "format")
        self.bad(edit(base + ["actions"], {"deny": "permissions.deny"}), "ask")
        self.bad(edit(base + ["actions"], {"deny": "a.b", "ask": "a.b"}), "different")
        self.bad(edit(base + ["actions"], {"deny": "a b.c", "ask": "a.d"}), "dotted")
        self.bad(edit(base + ["actions"], {"deny": "permissions", "ask": "a.d"}), "dotted")
        self.bad(edit(base + ["absolute"], "/"), "absolute")
        self.bad(edit(base + ["absolute"], "~"), "absolute")
        self.bad(edit(base + ["extra"], 1), "extra")
        self.bad(edit(base + ["rules"], {"net": "Web({pattern})"}), "net")

    def test_rule_templates(self):
        base = ["local_settings", "rules"]
        for tool, template in (("shell", "Bash({path})"), ("shell", "Bash(x)"),
                               ("shell", "Bash({pattern}) && x"), ("shell", "{pattern}"),
                               ("shell", "Bash({pattern}"), ("shell", "Bash({pattern},{path})"),
                               ("shell", "Ba sh({pattern})"), ("shell", "Bash:{pattern}"),
                               ("shell", "$(x)({pattern})"), ("read", "Read({pattern})"),
                               ("write", "Write({pattern})"), ("write", 3), ("web", "")):
            self.bad(edit(base + [tool], template), "must be Name")

    def test_hooks(self):
        self.bad(edit(["hooks"], {"settings_key": "a b"}), "hooks")
        self.bad(edit(["hooks"], {"command": "x"}), "hooks")
        self.bad(edit(["hooks"], "all"), "hooks")
        self.assertEqual(layout.problems(edit(["hooks"], {"settings_key": "hooks"})), [])

    def test_exclude_paths(self):
        for entry in ("/abs", "../x", "a/../x", ".git", ".git/", ".GIT/info", ".workbench",
                      ".workbench/local/", ".config/project-workbench/", "*.md", ".claude/*",
                      "a b", "#x", "!x", "a\\b", "a[1]", "a?", "", 3, "x:y", ".claude//"):
            self.bad(edit(["exclude"], CLAUDE["exclude"] + [entry]), "exclude")
        self.bad(edit(["exclude"], "CLAUDE.md"), "exclude")
        self.bad(edit(["exclude"], ["CLAUDE.md", ".claude/"] * 1 + ["CLAUDE.md"]), "twice")
        self.bad(edit(["exclude"], ["CLAUDE.md"] + [".c%d/" % n for n in range(layout.MAX_EXCLUDE)]),
                 "at most")

    def test_every_written_path_must_be_excluded(self):
        self.bad(edit(["exclude"], [".claude/"]), "root.file")
        self.bad(edit(["exclude"], ["CLAUDE.md"]), "no exclude entry")
        self.bad(edit(["exclude"], ["CLAUDE.md", ".claude/skills/"]), "kinds.agent")
        self.bad(edit(["exclude"], ["CLAUDE.md", ".claude/settings.local.json"]), "kinds.agent")
        # a file entry does not cover what is under a directory of that name
        self.bad(edit(["exclude"], ["CLAUDE.md", ".claude"]), "no exclude entry")
        # git compares exactly, so a differently-cased entry covers nothing
        self.bad(edit(["exclude"], ["claude.md", ".Claude/"]), "no exclude entry")
        self.bad(edit(["exclude"], ["claude.md", ".Claude/"]), "covers no path")
        # a directory entry does not cover a file of that name
        self.bad(edit(["exclude"], ["CLAUDE.md/", ".claude/"]), "layout.root.file")
        self.bad(edit(["exclude"], ["CLAUDE.md", ".claude/skills/", ".claude/agents/",
                                    ".claude/commands/"]), "local_settings.path")
        self.bad(edit(["local_settings", "path"], ".claude/s.json",
                      edit(["exclude"], ["CLAUDE.md", ".claude/skills/", ".claude/agents/",
                                         ".claude/commands/", ".claude/s.json/"])),
                 "local_settings.path")

    def test_an_exclude_entry_must_cover_a_written_path(self):
        self.bad(edit(["exclude"], CLAUDE["exclude"] + ["docs/"]), "covers no path")
        self.bad(edit(["exclude"], CLAUDE["exclude"] + ["src"]), "covers no path")
        self.assertEqual(layout.problems(edit(["exclude"], [
            "CLAUDE.md", ".claude/skills/", ".claude/agents/", ".claude/commands/",
            ".claude/settings.local.json"])), [])

    def test_written_paths_may_not_overlap(self):
        self.bad(edit(["local_settings", "path"], ".claude/agents/s.json"), "overlaps")
        self.bad(edit(["local_settings", "path"], "CLAUDE.md"), "overlaps")

    def test_the_permission_lists_cannot_be_an_allow_or_nested(self):
        base = ["local_settings", "actions"]
        for actions in ({"deny": "permissions.allow", "ask": "permissions.ask"},
                        {"deny": "permissions.deny", "ask": "permissions.allow"},
                        {"deny": "permissions.deny", "ask": "permissions.deny.ask"},
                        {"deny": "permissions.deny.deny", "ask": "permissions.deny"}):
            self.bad(edit(base, actions), "actions")
        self.assertEqual(layout.problems(edit(base, {"deny": "permissions.deny", "ask": "permissions.ask"})), [])
        value = edit(["hooks"], {"settings_key": "permissions"})
        self.bad(value, "top-level key")

    def test_inert_template_names_and_missing_rules(self):
        base = ["local_settings", "rules"]
        for tool, template in (("write", "Write({path})"), ("read", "NotebookEdit({path})"),
                               ("read", "Glob({path})"), ("shell", "Glob({pattern})")):
            self.bad(edit(base + [tool], template), "never consults")
        self.bad(edit(base, {}), "missing key")
        self.bad(edit(base, {"read": "Read({path})", "shell": "Bash({pattern})"}), "write")

    def test_an_agent_field_may_not_borrow_the_tools_name(self):
        self.bad(edit(["kinds", "agent", "fields", "model"], "tools"), "may not map")

    def test_a_directory_that_contains_the_guarded_store_is_refused(self):
        self.bad(edit(["kinds", "skill", "path"], ".config/{name}/SKILL.md"), "guarded store")

    def test_a_root_file_may_not_import_itself(self):
        self.bad(edit(["root", "import"], "CLAUDE.md"), "itself")

    def test_notes(self):
        for notes in ("x", ["a\nb"], [""], [3], ["x" * (layout.MAX_NOTE_CHARS + 1)],
                      ["n"] * (layout.MAX_NOTES + 1)):
            self.bad(edit(["notes"], notes), "notes")

    def test_all_problems_are_reported_together(self):
        value = edit(["exclude"], [])
        value["root"] = "x"
        self.assertGreaterEqual(len(layout.problems(value)), 3)


class Verification(Base):
    def set_layout(self, value):
        self.edit_module("sample-harness", layout=value)

    def test_a_good_layout_verifies_and_changes_nothing_else(self):
        self.set_layout(CLAUDE)
        result = self.check("sample-harness")
        self.assertEqual(result.problems, [], [str(p) for p in result.problems])

    def test_a_bad_layout_refuses_the_module_before_any_approval(self):
        self.set_layout(edit(["exclude"], []))
        result = self.refused("layout", "sample-harness")
        self.assertIn("no exclude entry", str(result.problems[0]))

    def test_every_problem_is_a_layout_problem(self):
        self.set_layout({"root": "x", "kinds": [], "notes": "n"})
        result = self.check("sample-harness")
        self.assertGreaterEqual(len(result.problems), 3)
        self.assertEqual({p.rule for p in result.problems}, {"layout"})

    def test_the_fixture_layout_is_unchanged_and_valid(self):
        path = os.path.join(self.path, "sample-harness", "module.json")
        with open(path) as handle:
            self.assertEqual(layout.problems(json.load(handle)["layout"]), [])


if __name__ == "__main__":
    unittest.main()


class SettingsKeysAndNames(unittest.TestCase):
    def bad(self, value, text):
        found = layout.problems(value)
        self.assertTrue(any(text in m for m in found), found)

    def test_action_keys_are_one_parent_with_deny_and_ask(self):
        for actions in ({"deny": "a.b.deny", "ask": "a.b.ask"},
                        {"deny": "a.deny", "ask": "b.ask"},
                        {"deny": "permissions.allow.deny", "ask": "permissions.ask"}):
            self.bad(edit(["local_settings", "actions"], actions), "layout.local_settings")

    def test_only_the_permissions_key_is_accepted(self):
        for key in ("env", "Permissions", "zzz"):
            self.bad(edit(["local_settings", "actions"],
                          {"deny": key + ".deny", "ask": key + ".ask"}), "must be one of")

    def test_each_tool_class_uses_only_its_own_rule_name(self):
        for rules in ({"shell": "bash({pattern})", "write": "Edit({path})"},
                      {"shell": "Bash({pattern})", "write": "Read({path})"},
                      {"shell": "Bash({pattern})", "write": "Edit({path})", "read": "Edit({path})"},
                      {"shell": "Task({pattern})", "write": "Edit({path})"},
                      {"shell": "Bash({pattern})", "write": "Edit({path})", "web": "BASH({pattern})"}):
            self.bad(edit(["local_settings", "rules"], rules), "layout.local_settings.rules")

    def test_no_key_is_named_allow(self):
        self.bad(edit(["local_settings", "actions"], {"deny": "allow.deny", "ask": "allow.ask"}),
                 "allow")

    def test_two_tool_classes_may_not_share_a_rule_name(self):
        rules = {"shell": "Bash({pattern})", "write": "Bash({path})"}
        self.bad(edit(["local_settings", "rules"], rules), "same rule name")

    def test_a_rule_may_not_be_named_allow(self):
        rules = {"shell": "Allow({pattern})", "write": "Edit({path})"}
        self.bad(edit(["local_settings", "rules"], rules), "allow")


class AgentAndSettingsTables(unittest.TestCase):
    def bad(self, value, text=""):
        found = layout.problems(value)
        self.assertTrue(any(text in m for m in found), found)

    def test_the_tools_field_is_the_harness_field_tools(self):
        fields = {"name": "name", "description": "description", "tools": "x-tools"}
        self.bad(edit(["kinds", "agent", "fields"], fields), "'tools' must map")
        fields["tools"] = "allowed-tools"
        self.bad(edit(["kinds", "agent", "fields"], fields), "'tools' must map")

    def test_a_neutral_tool_only_grants_its_own_harness_tools(self):
        for table in ({"read": ["Bash"]}, {"read": ["Task"]}, {"read": ["Read", "Bash"]},
                      {"shell": ["Read"]}, {"search": ["Edit"]}):
            self.bad(edit(["kinds", "agent", "tools"], table), "may only grant")

    def test_the_settings_path_is_pinned(self):
        for path in (".claude/settings.json", ".claude/settings.local.json.bak",
                     "docs/settings.local.json"):
            layout_value = edit(["local_settings", "path"], path)
            self.bad(layout_value, "must be one of")
