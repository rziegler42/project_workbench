import json
import os
import shutil
import tempfile
import unittest

from workbench import approvals, declarations, firstparty, harnessplan, request, verify
from tests import support
from tests.support_harness import SKILL, items, tree

CLAUDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.dirname(CLAUDE_DIR)
MODULE = os.path.join(CLAUDE_DIR, "module.json")


EXPECTED_LAYOUT = {
    "root": {"file": "CLAUDE.md", "import": "AGENTS.md"},
    "kinds": {
        "skill": {"path": ".claude/skills/{name}/SKILL.md",
                  "fields": {"name": "name", "description": "description"}},
        "agent": {"path": ".claude/agents/{name}.md",
                  "fields": {"name": "name", "description": "description", "tools": "tools",
                             "model": "model"},
                  "tools": {"read": ["Read"], "search": ["Grep", "Glob"],
                            "edit": ["Edit", "Write"], "shell": ["Bash"]}},
        "command": {"path": ".claude/commands/{name}.md",
                    "fields": {"name": "name", "description": "description",
                               "args": "argument-hint"}},
    },
    "local_settings": {
        "path": ".claude/settings.local.json", "format": "json",
        "actions": {"deny": "permissions.deny", "ask": "permissions.ask"},
        "rules": {"shell": "Bash({pattern})", "read": "Read({path})", "write": "Edit({path})"},
        "absolute": "//"},
    "hooks": {
        "settings_key": "hooks", "event": "PreToolUse", "timeout": 20, "block_code": 2,
        "targets": {"Edit": ["file_path"], "MultiEdit": ["file_path"], "NotebookEdit": ["notebook_path"],
                    "Write": ["file_path"]}},
    "exclude": ["CLAUDE.md", ".claude/"],
    "notes": [],
}


def declaration():
    with open(MODULE, encoding="utf-8") as handle:
        return json.load(handle)


def loaded_module():
    result = declarations.load_package(PACKAGE, first_party=True)
    assert not result.problems, result.problems
    return next(m for m in result.modules if m.name == "claude")


class Shipped(unittest.TestCase):
    def test_the_package_verifies_as_first_party_and_installs_claude(self):
        support.require_release(self)
        self.assertTrue(firstparty.is_first_party(PACKAGE))
        result = verify.verify_package(PACKAGE, select=["claude"],
                                       first_party=firstparty.is_first_party(PACKAGE))
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertEqual([m.name for m in result.modules], ["ask-codex", "claude", "code-work", "groundwork", "safe-git", "review-engine"])

    def test_the_shipped_records_match_the_current_hashes(self):
        support.require_release(self)
        result = verify.verify_package(PACKAGE, first_party=True)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        tree = firstparty.shipped_tree(firstparty.default_distribution())
        module = next(m for m in result.modules if m.name == "claude")
        got = approvals.check_module(tree, "workbench/claude", module.declaration_hash,
                                     module.tree_hash)
        self.assertTrue(got.approved, got.reason)
        self.assertEqual(got.record.approver, firstparty.RELEASE_APPROVER)

    def test_the_package_is_the_claude_code_work_and_groundwork_modules(self):
        self.assertEqual(sorted(os.listdir(PACKAGE)),
                         ["ask-codex", "claude", "code-work", "groundwork", "package.json", "review-engine", "safe-git"])
        self.assertEqual(sorted(os.listdir(CLAUDE_DIR)), ["module.json", "tests"])


class Changed(unittest.TestCase):
    """A copy of the distribution: a change to the declaration is third-party again."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.dist = os.path.realpath(holder.name)
        shutil.copytree(PACKAGE, os.path.join(self.dist, "packages", "workbench"))
        shutil.copytree(os.path.join(firstparty.default_distribution(), firstparty.SHIPPED),
                        os.path.join(self.dist, firstparty.SHIPPED))
        self.package = os.path.join(self.dist, "packages", "workbench")

    def edit(self, **fields):
        path = os.path.join(self.package, "claude", "module.json")
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        document.update(fields)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)

    def test_the_unchanged_copy_is_first_party(self):
        support.require_release(self)
        self.assertTrue(firstparty.is_first_party(self.package, self.dist))

    def test_a_changed_description_is_third_party_again(self):
        self.edit(description="A changed description.")
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))
        result = verify.verify_package(self.package, select=["claude"], first_party=False)
        self.assertFalse(result.accepted)

    def test_a_changed_layout_is_third_party_again(self):
        document = declaration()
        document["layout"]["exclude"] = ["CLAUDE.md"]
        self.edit(layout=document["layout"])
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_an_added_file_is_third_party_again(self):
        with open(os.path.join(self.package, "claude", "extra.txt"), "w") as handle:
            handle.write("x")
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))


class Declaration(unittest.TestCase):
    def test_it_is_a_harness_that_provides_the_six_capabilities_it_renders(self):
        document = declaration()
        self.assertEqual(document["type"], "harness")
        self.assertEqual(document["name"], "claude")
        self.assertEqual(document["provides"],
                         ["instructions", "skills", "agents", "commands", "hooks", "permissions"])
        self.assertEqual(document["layout"]["hooks"], EXPECTED_LAYOUT["hooks"])
        for key in ("writes", "fills", "ships", "helpers", "requires", "blocks", "slots"):
            self.assertNotIn(key, document)

    def test_the_layout_is_the_verified_one(self):
        shipped = declaration()["layout"]
        expected = dict(EXPECTED_LAYOUT)
        expected.pop("notes")
        shipped = dict(shipped)
        notes = shipped.pop("notes")
        tolerated = shipped.pop("tolerated")
        self.assertEqual(shipped, expected)
        self.assertEqual(len(notes), 1)
        self.assertEqual(tolerated, [".claude/settings.json"])

    def test_the_rule_templates_are_the_names_claude_reads(self):
        """Claude reads `Bash`, `Read` and `Edit`; `Write(path)` is accepted and never consulted."""
        local = declaration()["layout"]["local_settings"]
        self.assertEqual(local["rules"], {"shell": "Bash({pattern})", "read": "Read({path})",
                                          "write": "Edit({path})"})
        self.assertEqual(local["absolute"], "//")
        self.assertEqual(local["path"], ".claude/settings.local.json")
        self.assertEqual(local["actions"], {"deny": "permissions.deny", "ask": "permissions.ask"})
        self.assertNotIn("Write(", json.dumps(local["rules"]))

    def test_the_layout_paths_are_the_ones_verified_for_claude(self):
        kinds = declaration()["layout"]["kinds"]
        self.assertEqual(kinds["skill"]["path"], ".claude/skills/{name}/SKILL.md")
        self.assertEqual(kinds["agent"]["path"], ".claude/agents/{name}.md")
        self.assertEqual(kinds["command"]["path"], ".claude/commands/{name}.md")
        self.assertEqual(kinds["command"]["fields"]["args"], "argument-hint")
        self.assertEqual(declaration()["layout"]["root"], {"file": "CLAUDE.md", "import": "AGENTS.md"})

    def test_every_written_path_is_excluded_from_git(self):
        layout = declaration()["layout"]
        self.assertEqual(layout["exclude"], ["CLAUDE.md", ".claude/"])


class Rendering(unittest.TestCase):
    def plan(self, found=None):
        document = declaration()
        return harnessplan.translate(found if found is not None else items(), document["layout"],
                                     {}, {}, provides=tuple(document["provides"]))

    def test_a_neutral_tree_translates_to_claudes_paths_with_the_modules_own_provides(self):
        self.assertEqual(sorted(f.path for f in self.plan().files), [
            ".claude/agents/reviewer.md", ".claude/commands/ship.md",
            ".claude/skills/sample/SKILL.md"])

    def test_the_tools_table_is_pinned_literally(self):
        self.assertEqual(declaration()["layout"]["kinds"]["agent"]["tools"], {
            "read": ["Read"], "search": ["Grep", "Glob"], "edit": ["Edit", "Write"],
            "shell": ["Bash"]})

    def test_the_rendered_agent_is_what_claude_was_shown_to_read(self):
        agent = next(f for f in self.plan().files if f.path == ".claude/agents/reviewer.md")
        self.assertEqual(agent.data, (b'---\nname: "reviewer"\ndescription: "Reviews changes"\n'
                                      b'tools: "Glob, Grep, Read"\nmodel: "sonnet"\n---\n'
                                      b"You review.\n"))
        command = next(f for f in self.plan().files if f.path == ".claude/commands/ship.md")
        self.assertIn(b'argument-hint: "[target]"\n', command.data)

    def test_an_item_that_needs_hooks_is_skipped_because_a_hook_has_no_neutral_form(self):
        from workbench import neutral
        text = SKILL.replace(b"A sample skill\n", b"A sample skill\nneeds: hooks\n")
        found = neutral.read_items(tree(**{"skills/sample/SKILL.md": text}))
        result = self.plan(found)
        self.assertNotIn(".claude/skills/sample/SKILL.md", [f.path for f in result.files])
        self.assertTrue(any(r.level == "skipped" and "hooks" in r.message for r in result.reports))

    def test_the_hook_it_renders_is_the_one_the_documentation_describes(self):
        layout = declaration()["layout"]
        document = json.loads(harnessplan.render_permissions([], layout, "/Users/t/.config/project-workbench",
                                                             "/Users/t", hook_for="claude",
                                                             root="/Users/t/work/project"))
        self.assertEqual({"PreToolUse": [{
            "matcher": "Edit|MultiEdit|NotebookEdit|Write",
            "hooks": [{"type": "command", "command": "wb gate claude || exit 2", "timeout": 20}]}]},
            document["hooks"])

    def test_the_hook_comes_with_a_deny_for_the_settings_file_and_the_exclude_file(self):
        layout = declaration()["layout"]
        deny = json.loads(harnessplan.render_permissions([], layout, "/Users/t/.config/project-workbench",
                                                         "/Users/t", hook_for="claude",
                                                         root="/Users/t/work/project"))["permissions"]["deny"]
        for path in (".claude/settings.local.json", ".git/info/exclude"):
            self.assertIn("Edit(%s)" % path, deny)
            self.assertIn("Edit(**/%s)" % path, deny)
            self.assertIn("Edit(//Users/t/work/project/%s)" % path, deny)

    def test_the_permissions_it_renders_are_claudes_syntax(self):
        layout = declaration()["layout"]
        data = harnessplan.render_permissions([], layout, "/Users/t/.config/project-workbench",
                                              "/Users/t")
        document = json.loads(data)
        deny, ask = document["permissions"]["deny"], document["permissions"]["ask"]
        self.assertIn("Bash(wb install)", deny)
        self.assertIn("Bash(wb install *)", deny)
        self.assertIn("Bash(python3 -m workbench attach *)", deny)
        self.assertIn("Edit(//Users/t/.config/project-workbench/**)", deny)
        self.assertIn("Bash(git push --force*)", ask)
        self.assertNotIn("allow", document["permissions"])


class Request(unittest.TestCase):
    def test_the_approval_request_shows_the_layout_in_plain_terms(self):
        module = loaded_module()
        hashes = next(m for m in verify.verify_package(PACKAGE, first_party=True).modules if m.name == "claude")
        text = request.render_module("workbench", module, hashes)
        for line in ("HIGH RISK", "type: harness", "approval: needs an explicit approval of its own",
                     "provides:", "harness layout:", "local_settings.path = ",
                     ".claude/settings.local.json", ".claude/skills/{name}/SKILL.md",
                     "Bash({pattern})", "Edit({path})", "exclude"):
            self.assertIn(line, text)
        self.assertIn(hashes.declaration_hash, text)


if __name__ == "__main__":
    unittest.main()
