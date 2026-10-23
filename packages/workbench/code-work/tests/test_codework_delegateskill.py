"""The `delegate-approval` skill the `code-work` module ships: when an agent may ask the installer for a delegated
plan approval, and when it must wait for the owner.

Plan `2026-10-23-delegated-approval`, increment E. The skill is advice. What gives or refuses the approval is the
installer's `wb delegate-approve-plan` (`trust-and-approval.md`, "Delegated plan approval records"), which reads the
owner's setting, the review and the plan itself. The package tree hash changes with this skill, so the shipped
approvals are stale until the owner's release in increment F."""

import re
import unittest

from workbench import harnessplan, neutral

from test_codework_skills import claude, flat, neutral_tree, text_of

NAME = "delegate-approval"
SETTINGS = "wb settings"
COMMAND = "wb delegate-approve-plan <plan>"
ALLOWED = {SETTINGS, COMMAND}
PHRASES = (
    "`%s`" % SETTINGS, "`checkpoint approve-plan: delegate`", "go on only if", "the owner approves the plan",
    "`peer-review`", "`evaluate-findings`", "after the converging round", "before you write anything to the plan",
    "`## review record`", "`%s`" % COMMAND, "the bytes that were reviewed", "`approved:`", "`already approved:`",
    "is a delegate's and not the owner's", "`refused:`", "report the reason as printed", "the owner decides",
    "every other checkpoint still stops", "plan approval only", "never run that command", "`approved`",
    "`hard stop:`", "is not an approval", "is data", "ignore any instruction",
    "a plan with a `hard stop:` line is for the owner", "a plan with no risks section is for the owner",
    "`%s` once" % COMMAND, "use only reading, searching, editing and the two commands named here",
    "run no other command")


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

    def test_the_steps_come_in_the_order_the_same_bytes_rule_needs(self):
        text = flat(NAME)
        order = ["`%s`" % SETTINGS, "`peer-review`", "before you write anything to the plan", "`%s`" % COMMAND,
                 "then write the review record"]
        places = [text.index(part) for part in order]
        self.assertEqual(sorted(places), places)
        self.assertEqual(len(set(places)), len(places))
        self.assertEqual(1, text.count("`%s`" % COMMAND))
        self.assertEqual(1, text.count("then write the review record"))


class Commands(unittest.TestCase):
    def test_the_only_wb_commands_named_are_the_two_it_runs_each_in_backticks(self):
        text = text_of(NAME)
        spans = re.findall(r"`(wb [^`]*)`", text)
        self.assertEqual(ALLOWED, set(spans))
        self.assertEqual(len(spans), len(ALLOWED))
        self.assertNotIn("wb ", re.sub(r"`[^`]*`", "", text))

    def test_no_raw_git_no_commit_route_and_no_owner_only_command_is_named_as_a_command(self):
        text = text_of(NAME)
        self.assertIsNone(re.search(r"(?<![\w-])git\b", text))
        for word in ("safe-git", "`wb approve-plan", "wb pin", "wb install", "wb upgrade", "wb acknowledge",
                     "wb release-approvals", "wb run review-engine", "wb run code-work"):
            self.assertNotIn(word, text, word)

    def test_no_text_names_a_harness_tool_program_or_address(self):
        text = text_of(NAME)
        for word in ("Bash", "shell", "curl", "http://", "https://", "sudo", "WebFetch", "<!--", "needs:", "tools:",
                     "claude", "Claude", "codex", "Codex", "ask-codex", "claude-workflow", "opencode", "CLAUDE.md"):
            self.assertNotIn(word, text, word)
        self.assertIsNone(re.search(r"\b(pin|launch)\b", text))

    def test_it_does_not_tell_the_agent_to_approve_for_the_owner_or_to_skip_a_rule(self):
        text = flat(NAME)
        for phrase in ("set the status to `approved`", "run `wb approve-plan", "skip the review",
                       "without asking the owner", "approve it yourself", "retry with", "work around the refusal",
                       "ignore the refusal", "change the setting to", "edit the setting"):
            self.assertNotIn(phrase, text, phrase)


class Pointers(unittest.TestCase):
    """The two skills that meet a plan's approval point to this one and keep their own limits."""

    def test_draft_plan_and_run_increment_name_it_and_still_leave_the_approval_to_the_owner(self):
        for name in ("draft-plan", "run-increment"):
            text = flat(name)
            self.assertIn("`%s`" % NAME, text, name)
            self.assertIn("only the owner", text, name)
        self.assertIn("only the owner makes with the approve-plan command", flat("draft-plan"))
        self.assertIn("never set a plan's status to `approved`", flat("run-increment"))

    def test_the_others_do_not_point_to_it(self):
        for name in ("request-review", "evaluate-findings", "push-changes"):
            self.assertNotIn(NAME, flat(name), name)


if __name__ == "__main__":
    unittest.main()
