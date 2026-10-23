"""The `push-changes` skill the `code-work` module ships: the routine for a push, which is the owner's word.

Plan `2026-10-23-push-checkpoint`, increment C. The skill is advice. What stops a push is the `ask` rule the
floor renders for `git push` and for each force form, which the last test pins for the Claude layout. The skill
is the only one that names a raw git command, and it names exactly one: the plain push the owner approved."""

import json
import re
import unittest

from workbench import harnessplan, neutral

from test_codework_skills import PACKAGE, claude, flat, neutral_tree, text_of

NAME = "push-changes"
CHECK = "wb run safe-git push-check"
SHARED = "wb run code-work shared"
PUSH = "git push <remote> <branch>"
ALLOWED = {CHECK, SHARED}
PHRASES = (
    "push only on the owner's word", "a commit is not a word", "`default_branch`", "`shared`", "`%s`" % CHECK,
    "`%s`" % SHARED, "the commits to be sent", "every finding", "stop on any finding", "never force",
    "never push a branch the owner did not name", "never change the remote",
    "the harness's prompt is not the owner's word", "the harness will ask")
FORCE_FORMS = ("git push --force*", "git push -f*", "git push * --force*", "git push * -f*")


class Skill(unittest.TestCase):
    def test_the_reader_accepts_it_with_no_files_or_needs(self):
        items = {(i.kind, i.name): i for i in neutral.read_items(neutral_tree())}
        self.assertEqual(((), ()), (items[("skill", NAME)].files, items[("skill", NAME)].needs))

    def test_front_matter_holds_only_a_name_and_a_description(self):
        head = text_of(NAME).split("---\n")[1].splitlines()
        self.assertEqual(["name: " + NAME, head[1]], head)
        self.assertTrue(head[1].startswith("description: "))

    def test_claude_plans_it_at_its_path_and_reports_nothing(self):
        layout = claude()
        planned = harnessplan.translate(neutral.read_items(neutral_tree()), layout["layout"], {}, {},
                                        provides=layout["provides"])
        self.assertEqual((), planned.reports)
        by_path = {f.path: f.data for f in planned.files}
        path = ".claude/skills/%s/SKILL.md" % NAME
        body = neutral_tree()["skills/%s/SKILL.md" % NAME].split(b"---\n", 2)[2]
        self.assertEqual(body, by_path[path].split(b"---\n", 2)[2])

    def test_the_text_carries_the_phrases_of_the_routine(self):
        text = flat(NAME)
        for phrase in PHRASES:
            self.assertIn(phrase, text, phrase)

    def test_the_text_is_short_enough_to_read_in_one_go(self):
        self.assertLessEqual(len(text_of(NAME).splitlines()), 60)


class Commands(unittest.TestCase):
    def test_the_only_wb_commands_named_are_the_two_it_runs_each_in_backticks(self):
        text = text_of(NAME)
        spans = re.findall(r"`(wb [^`]*)`", text)
        self.assertEqual(ALLOWED, set(spans))
        self.assertEqual(len(spans), len(ALLOWED))
        self.assertNotIn("wb ", re.sub(r"`[^`]*`", "", text))

    def test_the_one_raw_git_command_is_the_plain_push_of_a_named_branch_and_remote(self):
        text = text_of(NAME)
        self.assertEqual(1, text.count("`%s`" % PUSH))
        self.assertIsNone(re.search(r"(?<![\w-])git\b", text.replace(PUSH, "")))

    def test_no_force_form_no_deletion_no_remote_change_and_no_other_git(self):
        text = text_of(NAME)
        for form in ("--force", "-f ", "--delete", "--mirror", "--all", "--tags", "--no-verify", "--receive-pack",
                     "--exec", "--repo", "remote add", "remote set-url", "set-url", "+refs", "git config",
                     "git remote", "git fetch", "git reset", "git rebase", "git commit", "git add"):
            self.assertNotIn(form, text, form)
        self.assertIsNone(re.search(r"git push[^`]*\s:", text))

    def test_no_text_names_a_harness_tool_program_or_address(self):
        text = text_of(NAME)
        for word in ("Bash", "shell", "curl", "http://", "https://", "sudo", "WebFetch", "<!--", "needs:", "tools:",
                     "claude", "Claude", "codex", "Codex", "ask-codex", "claude-workflow", "opencode", "CLAUDE.md"):
            self.assertNotIn(word, text, word)
        self.assertIsNone(re.search(r"\b(pin|launch)\b", text))

    def test_it_does_not_tell_the_agent_to_skip_a_rule_or_to_approve_for_the_owner(self):
        text = flat(NAME)
        for phrase in ("without asking the owner", "skip the check", "ignore the finding", "ignore the findings",
                       "approve the prompt", "answer the prompt", "approve it yourself", "set the status"):
            self.assertNotIn(phrase, text, phrase)


class Floor(unittest.TestCase):
    """The enforced part: an attached `code-work` with `safe-git` leaves the floor's `ask` on every push."""

    def test_the_claude_settings_ask_on_a_push_and_on_each_force_form(self):
        layout = claude()
        document = json.loads(harnessplan.render_permissions(
            [], layout["layout"], "/Users/t/.config/project-workbench", "/Users/t"))
        ask, deny = document["permissions"]["ask"], document["permissions"]["deny"]
        for command in ("git push", "git push *") + FORCE_FORMS:
            self.assertIn("Bash(%s)" % command, ask, command)
            self.assertNotIn("Bash(%s)" % command, deny, command)
        self.assertNotIn("allow", document["permissions"])
        for rule in document["permissions"]["ask"] + deny:
            self.assertNotIn(PUSH, rule)

    def test_no_module_manifest_allows_a_push(self):
        for module in ("code-work", "safe-git"):
            with open("%s/%s/module.json" % (PACKAGE, module), encoding="utf-8") as handle:
                self.assertNotIn("git push", handle.read(), module)


if __name__ == "__main__":
    unittest.main()
