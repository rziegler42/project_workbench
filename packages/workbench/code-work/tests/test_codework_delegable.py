"""The `code-work` helper's `delegable` subcommand: whether a plan may be approved by a delegate.

Plan `2026-10-23-delegated-approval`, increment C. A plan is delegable when it has exactly one Risks section, the one
headed `## Risks and sensitive actions` outside a fence, a quotation and an HTML comment, and that section has no line
that begins, after any list marker and emphasis, with `Hard stop:` (any case, a space or hyphen between the words, a heading or checkbox prefix). Text outside the section cannot
change the answer, and whatever leaves the answer uncertain is not delegable. A path that is not a plan, a link and a
file larger than the check reads are refused. The helper is loaded by its path and run in process."""

import hashlib
import json
import os
import unittest

from test_codework_helper import Project, plan

NAME = "2026-10-23-thing.md"
PLAN = "docs/plans/" + NAME
HEADING = "## Risks and sensitive actions"
TAIL = "\n## Review record\n\nNone yet.\n\n## Result\n\nNot started.\n"
SAFE = "- No push, no install, no secret.\n- Local commits only.\n"


def text(risks=SAFE, heading=HEADING, before="", after=""):
    """A plan with one Risks section holding `risks`; `before` and `after` are other sections around it."""
    return plan() + before + "\n" + heading + "\n\n" + risks + after + TAIL


class Delegable(Project):
    def ask(self, content, name=NAME):
        self.write("docs/plans/" + name, content)
        code, out, err = self.check("delegable", "docs/plans/" + name)
        self.assertEqual((0, ""), (code, err), out)
        report = json.loads(out)
        self.assertEqual(["delegable", "document_sha256", "format", "reason"], sorted(report))
        self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), report["document_sha256"])
        self.assertEqual(1, report["format"])
        self.assertIsInstance(report["delegable"], bool)
        self.assertTrue(0 < len(report["reason"]) <= 200, report["reason"])
        self.assertTrue(all(" " <= char <= "~" for char in report["reason"]), report["reason"])
        return report

    def yes(self, content):
        report = self.ask(content)
        self.assertTrue(report["delegable"], report)
        return report

    def no(self, content, contains=""):
        report = self.ask(content)
        self.assertFalse(report["delegable"], report)
        self.assertIn(contains, report["reason"])
        return report

    def refused(self, *args, contains=""):
        code, out, err = self.check("delegable", *args)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)


class Answer(Delegable):
    def test_it_prints_one_json_object_and_nothing_else(self):
        self.write(PLAN, text())
        code, out, err = self.check("delegable", PLAN)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.endswith("\n") and out.count("\n") == 1, out)
        self.assertEqual(["delegable", "document_sha256", "format", "reason"], sorted(json.loads(out)))
        self.assertEqual(hashlib.sha256(text().encode()).hexdigest(), json.loads(out)["document_sha256"])

    def test_a_section_that_says_it_stops_at_every_action_is_delegable(self):
        self.yes(text("The plan stops at: no push, no install, no secret.\n"))

    def test_a_section_with_no_marker_is_delegable(self):
        self.yes(text(SAFE))

    def test_an_empty_section_is_delegable(self):
        self.yes(text(""))

    def test_a_hard_stop_makes_it_not_delegable(self):
        self.no(text("Hard stop: pushes to main.\n"), "Hard stop")

    def test_the_marker_after_a_list_marker_or_emphasis_or_indent(self):
        lines = ["- Hard stop: x", "* Hard stop: x", "+ Hard stop: x", "1. Hard stop: x", "2) Hard stop: x",
                 "**Hard stop:** x", "__Hard stop:__ x", "- **Hard stop:** x", "- *Hard stop*: x",
                 "  - Hard stop: nested", "    - 1. **Hard stop:** nested", "- `Hard stop:` x",
                 "\tHard stop: tab", "Hard stop:", "Hard stop:x", "### Hard stop: x", "- [ ] Hard stop: x",
                 "- [x] **Hard stop:** x"]
        for line in lines:
            with self.subTest(line):
                self.no(text(SAFE + line + "\n"), "Hard stop")

    def test_the_marker_ignores_case_spacing_and_a_hyphen(self):
        for line in ("hard stop: x", "HARD STOP: x", "Hard Stop: x", "Hard-stop: x", "Hard  stop: x", "Hard stop : x",
                     "**Hard stop** : x"):
            with self.subTest(line):
                self.no(text(SAFE + line + "\n"), "Hard stop")

    def test_text_that_only_mentions_the_marker_is_not_a_marker(self):
        for line in ("There is no Hard stop: here.", "Hard stops: none.", "Hard stop none.", "A Hard stop: is not",
                     "Hard stop", "-Hard stop: x", "Hardstop: x"):
            with self.subTest(line):
                self.yes(text(SAFE + line + "\n"))

    def test_a_marker_on_any_line_of_the_section_counts(self):
        self.no(text(SAFE + "\nMore text.\n\n- Hard stop: late.\n"), "Hard stop")

    def test_a_marker_below_a_subheading_of_the_section_counts(self):
        self.no(text(SAFE + "\n### Detail\n\nHard stop: x\n"), "Hard stop")

    def test_the_reason_names_the_cause(self):
        self.assertIn("no `Hard stop:`", self.yes(text())["reason"])
        self.assertIn("Hard stop", self.no(text("Hard stop: x\n"))["reason"])


class Outside(Delegable):
    def test_a_marker_in_another_section_cannot_make_it_not_delegable(self):
        self.yes(text(before="\n## Goal\n\nHard stop: this is the goal.\n",
                      after="\n## Next\n\nHard stop: after.\n"))

    def test_the_marker_in_the_result_or_the_review_record_cannot_make_it_not_delegable(self):
        self.yes(plan() + "\n" + HEADING + "\n\n" + SAFE
                 + "\n## Review record\n\nHard stop: x\n\n## Result\n\nHard stop: y\n")

    def test_a_marker_in_a_fence_a_quote_or_a_comment_of_the_section_is_not_the_plans_statement(self):
        for risks in (SAFE + "```\nHard stop: x\n```\n", SAFE + "> Hard stop: x\n",
                      SAFE + "<!--\nHard stop: x\n-->\n", SAFE + "<!-- Hard stop: x -->\n"):
            with self.subTest(risks):
                self.yes(text(risks))

    def test_a_fence_in_the_section_does_not_end_it(self):
        self.no(text(SAFE + "```\nsome code\n```\nHard stop: x\n"), "Hard stop")

    def test_a_level_one_or_two_heading_ends_the_section(self):
        self.yes(text(after="\n## Other\n\nHard stop: x\n"))
        self.yes(text(after="\n# Other\n\nHard stop: x\n"))

    def test_a_level_three_heading_does_not_end_the_section(self):
        self.no(text(after="\n### Other\n\nHard stop: x\n"), "Hard stop")

    def test_a_rule_or_a_setext_underline_does_not_end_the_section(self):
        self.no(text(SAFE + "\n---\n\nHard stop: x\n"), "Hard stop")
        self.no(text(SAFE + "\nOther\n=====\n\nHard stop: x\n"), "Hard stop")

    def test_the_hard_stop_text_in_the_status_line_or_header_is_not_the_section(self):
        self.yes(text().replace("Status: Approved", "Status: Approved Hard stop: x", 1))


class Fails(Delegable):
    def test_no_risks_section_is_not_delegable(self):
        self.no(plan() + TAIL, "no Risks section")

    def test_two_risks_sections_are_not_delegable(self):
        self.no(text(after="\n" + HEADING + "\n\n" + SAFE), "more than one")

    def test_two_sections_are_not_delegable_whichever_holds_the_marker(self):
        self.no(text(before="\n" + HEADING + "\n\nHard stop: x\n"), "more than one")

    def test_a_heading_in_another_case_or_form_is_not_a_risks_section(self):
        for heading in ("## risks and sensitive actions", "## RISKS AND SENSITIVE ACTIONS",
                        "## Risks and sensitive actions:", "## Risks And Sensitive Actions",
                        "##  Risks and sensitive actions", "### Risks and sensitive actions",
                        "# Risks and sensitive actions", "#### Risks and sensitive actions",
                        "## Risks and sensitive actions ##"):
            with self.subTest(heading):
                self.no(text(heading=heading), "")

    def test_a_second_heading_in_another_case_makes_it_not_delegable(self):
        self.no(text(after="\n## risks and sensitive actions\n\nHard stop: x\n"), "more than one")
        self.no(text(after="\n### Risks and sensitive actions\n\nHard stop: x\n"), "more than one")

    def test_a_heading_with_trailing_white_space_is_the_heading(self):
        self.yes(text(heading=HEADING + "  \t"))

    def test_a_heading_inside_a_fence_a_quote_or_a_comment_is_not_a_section(self):
        for hidden in ("```\n%s\n```\n" % HEADING, "> %s\n" % HEADING, "<!--\n%s\n-->\n" % HEADING):
            with self.subTest(hidden):
                self.no(plan() + "\n" + hidden + TAIL, "no Risks section")

    def test_a_hidden_heading_next_to_a_real_one_does_not_make_it_two(self):
        self.yes(text(before="\n```\n%s\nHard stop: x\n```\n" % HEADING))

    def test_a_fence_or_a_comment_that_is_never_closed_is_not_delegable(self):
        self.no(text(SAFE + "```\nHard stop: x\n"), "never closed")
        self.no(text(SAFE + "<!--\nHard stop: x\n"), "never closed")

    def test_a_plan_that_is_not_utf8_is_not_delegable(self):
        self.write(PLAN, text().encode("utf-8") + b"\xff\xfe")
        code, out, err = self.check("delegable", PLAN)
        self.assertEqual((0, ""), (code, err))
        report = json.loads(out)
        self.assertFalse(report["delegable"])
        self.assertIn("UTF-8", report["reason"])

    def test_a_plan_that_has_no_status_line_is_not_delegable(self):
        self.no(text().replace("Status: Approved\n", "", 1), "Status")

    def test_a_long_line_before_the_section_does_not_hide_a_marker(self):
        self.no(text(SAFE + "x" * 5000 + "\nHard stop: x\n"), "Hard stop")

    def test_a_marker_in_the_middle_of_a_long_line_is_not_a_marker(self):
        self.yes(text(SAFE + "word " * 1000 + "Hard stop: x\n"))

    def test_padding_longer_than_a_line_is_read_does_not_hide_a_marker(self):
        self.no(text(SAFE + " " * 3000 + "Hard stop: x\n"), "Hard stop")

    def test_a_setext_heading_is_taken_for_a_section(self):
        self.no(text(after="\nRisks and sensitive actions\n----\n\nHard stop: x\n"), "more than one")
        self.no(plan() + "\nRisks and sensitive actions\n============\n\n" + SAFE + TAIL, "exactly")

    def test_carriage_returns_end_lines(self):
        self.no(text(SAFE).replace("\n", "\r\n").replace("commits", "commits\rHard stop: x\r"), "Hard stop")

    def test_the_reason_is_ascii_whatever_the_plan_says(self):
        report = self.no(text(SAFE + "Hard stop: café ‮\n"))
        self.assertTrue(all(" " <= char <= "~" for char in report["reason"]))


class Refusals(Delegable):
    def test_a_missing_plan_is_refused(self):
        self.refused(PLAN, contains="cannot be read")

    def test_a_path_that_is_not_a_plan_is_refused(self):
        for path in ("docs/plans/README.md", "docs/plans/sub/" + NAME, "docs/specs/" + NAME, "../" + PLAN,
                     "/" + PLAN, PLAN + "/", "docs/plans/" + NAME + ".md", "docs\\plans\\" + NAME, ""):
            with self.subTest(path):
                self.write(PLAN, text())
                self.refused(path, contains="not a plan")

    def test_a_link_is_refused(self):
        self.write("docs/elsewhere.md", text())
        os.symlink(os.path.join(self.place, "docs", "elsewhere.md"), os.path.join(self.place, PLAN))
        self.refused(PLAN, contains="cannot be read")

    def test_a_linked_folder_is_refused(self):
        os.rename(os.path.join(self.place, "docs", "plans"), os.path.join(self.place, "docs", "real"))
        os.symlink(os.path.join(self.place, "docs", "real"), os.path.join(self.place, "docs", "plans"))
        self.write("docs/real/" + NAME, text())
        self.refused(PLAN)

    def test_a_directory_is_refused(self):
        os.makedirs(os.path.join(self.place, PLAN))
        self.refused(PLAN, contains="cannot be read")

    def test_a_file_larger_than_the_check_reads_is_refused(self):
        self.write(PLAN, text().encode("utf-8") + b"x" * (1024 * 1024))
        self.refused(PLAN, contains="larger than")

    def test_the_arguments(self):
        for argv in (["delegable"], ["delegable", PLAN, PLAN], ["delegable", "--x", PLAN], ["delegables", PLAN]):
            with self.subTest(argv):
                code, out, err = self.check(*argv)
                self.assertEqual((1, ""), (code, out))
                self.assertIn("usage: code-work", err)

    def test_the_other_subcommands_still_take_no_argument(self):
        for command in ("check", "plans", "report", "active", "shared"):
            code, out, err = self.check(command, PLAN)
            self.assertEqual((1, ""), (code, out))

    def test_outside_a_project(self):
        code, out, err = self.check("delegable", PLAN, cwd=os.path.dirname(self.place))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not inside a workbench project", err)

    def test_it_changes_nothing(self):
        self.write(PLAN, text())
        before = self.snapshot()
        self.check("delegable", PLAN)
        self.assertEqual(before, self.snapshot())


class Agreement(Delegable):
    def test_the_answer_does_not_depend_on_the_status_the_review_record_or_the_result(self):
        one = self.ask(text())
        two = self.ask(text().replace("Status: Approved", "Status: In Progress", 1)
                       .replace("None yet.", "A long review.\nHard stop: x").replace("Not started.", "Done."))
        self.assertNotEqual(one.pop("document_sha256"), two.pop("document_sha256"))
        self.assertEqual(one, two)


class Repository(Delegable):
    def test_each_plan_of_this_repository_gets_an_answer(self):
        from tests import support_install
        folder = os.path.join(support_install.ROOT, "docs", "plans")
        names = [name for name in sorted(os.listdir(folder)) if name.endswith(".md") and name != "README.md"]
        self.assertTrue(names)
        for name in names:
            with open(os.path.join(folder, name), "rb") as handle:
                self.write("docs/plans/" + name, handle.read())
            with self.subTest(name):
                code, out, err = self.check("delegable", "docs/plans/" + name)
                self.assertEqual((0, ""), (code, err), out)
                self.assertIsInstance(json.loads(out)["delegable"], bool)


if __name__ == "__main__":
    unittest.main()
