"""The `code-work` helper's `region` subcommand: the hash of a plan's hashed region.

Plan `2026-10-22-plan-approval-records`, increment D. The region is the whole plan except the status line, the
review record and the result. Only the exact headings `## Review record`, `## Second opinion` and `## Result` start
an excluded section; any other heading ends one, so everything a reader could take for another section is hashed.
A plan that cannot be read with certainty is refused. The helper is loaded by its path and run in process."""

import hashlib
import json
import os
import re
import unittest

from test_codework_helper import Project, helper, plan
from tests import support_install

NAME = "2026-10-22-thing.md"
PLAN = "docs/plans/" + NAME
TAIL = "\n## Review record\n\nNone yet.\n\n## Result\n\nNot started.\n"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def text(status="Proposed", body=None, tail=TAIL):
    return plan(status=status, body=body) + tail


def expected(content):
    """The hash of `content` as the contract states it, worked out here from the rules and not from the helper."""
    lines = [line.rstrip(" \t") for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


class Region(Project):
    def region(self, name=PLAN, cwd=None):
        return self.check("region", name, cwd=cwd)

    def hash_of(self, content, name=NAME):
        self.write("docs/plans/" + name, content)
        code, out, err = self.region("docs/plans/" + name)
        self.assertEqual((0, ""), (code, err), out)
        report = json.loads(out)
        self.assertEqual(["format", "region_hash", "unhashed"], sorted(report))
        self.assertRegex(report["region_hash"], HEX)
        return report["region_hash"]

    def refused(self, content, contains="", name=NAME):
        self.write("docs/plans/" + name, content)
        code, out, err = self.region("docs/plans/" + name)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        return err

    def differs(self, one, two):
        self.assertNotEqual(self.hash_of(one), self.hash_of(two))

    def same(self, one, two):
        self.assertEqual(self.hash_of(one), self.hash_of(two))


class Report(Region):
    def test_it_prints_one_json_object_and_nothing_else(self):
        self.write(PLAN, text())
        code, out, err = self.region()
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.endswith("\n") and out.count("\n") == 1, out)
        report = json.loads(out)
        self.assertEqual(1, report["format"])
        self.assertEqual(["Status", "Review record", "Result"], report["unhashed"])

    def test_the_hash_is_the_stated_one(self):
        content = text()
        without = content.replace("Status: Proposed\n", "")
        without = without[:without.index("## Review record")]
        self.assertEqual(expected(without), self.hash_of(content))

    def test_the_names_are_those_present(self):
        self.write(PLAN, plan())
        self.assertEqual(["Status"], json.loads(self.region()[1])["unhashed"])
        self.write(PLAN, plan() + "\n## Second opinion\n\nx\n")
        self.assertEqual(["Status", "Second opinion"], json.loads(self.region()[1])["unhashed"])

    def test_it_changes_nothing(self):
        self.write(PLAN, text())
        before = self.snapshot()
        self.region()
        self.assertEqual(before, self.snapshot())

    def test_it_runs_from_a_directory_below_the_root(self):
        self.write(PLAN, text())
        below = os.path.join(self.place, "docs", "plans")
        self.assertEqual(self.region()[1], self.region(cwd=below)[1])


class Excluded(Region):
    def test_the_status_line_is_not_in_the_region(self):
        self.same(text(status="Proposed"), text(status="Approved"))
        self.same(text(status="Proposed"), text(status="Completed — it was finished"))

    def test_the_review_record_and_the_result_are_not_in_the_region(self):
        self.same(text(), text(tail="\n## Review record\n\nRound 1: three findings.\n\n## Result\n\nDone.\n"))
        self.same(text(), text(tail=""))
        self.same(text(), text(tail="\n## Second opinion\n\nx\n\n## Result\n\ny\n"))

    def test_an_excluded_section_may_hold_subheadings_and_lists(self):
        tail = "\n## Result\n\n### A\n\n- one\n\n#### B\n\ntext\n"
        self.same(text(tail=TAIL), text(tail=tail))

    def test_an_excluded_section_in_the_middle_ends_at_the_next_heading(self):
        middle = "\n## Result\n\nwhatever\n\n## Deferred work\n\nlater\n"
        one, two = text(tail=middle), text(tail=middle.replace("whatever", "other"))
        self.same(one, two)
        self.differs(one, text(tail=middle.replace("later", "sooner")))

    def test_every_other_part_of_the_plan_is_in_the_region(self):
        base = text()
        for label, old, new in (
                ("the title", "# A plan", "# Another plan"),
                ("created", "Created: 2026-10-21", "Created: 2026-10-22"),
                ("the candidate", "workbench-v1#thing", "workbench-v1#other"),
                ("the specs", "Specs: code-work", "Specs: code-work, more"),
                ("the goal", "Something.", "Something else."),
                ("an increment", "### Increment A — Title", "### Increment A — Other title"),
                ("an increment's text", "Text.", "Different text."),
                ("a new section", "## Increments", "## Risks\n\nNone.\n\n## Increments"),
                ("a section's heading", "## Goal", "## Aim")):
            with self.subTest(label):
                self.assertNotEqual(self.hash_of(base), self.hash_of(base.replace(old, new, 1)))

    def test_a_status_line_after_the_first_heading_is_text(self):
        self.differs(text(), text().replace("Something.", "Status: Approved\n\nSomething."))

    def test_a_second_status_line_in_the_header_is_refused(self):
        self.refused(text().replace("Created:", "Status: Approved\nCreated:"), "Status")

    def test_a_plan_with_no_status_line_before_its_first_heading_is_refused(self):
        self.refused(text().replace("Status: Proposed\n", ""), "Status")
        self.refused(text().replace("Status: Proposed\n", "").replace("Something.", "Status: Approved\n\nSomething."),
                     "Status")

    def test_a_status_line_in_a_fence_or_a_comment_or_a_quote_is_not_one(self):
        fenced = "# A plan\n\n```\nStatus: Approved\n```\n\nCreated: 2026-10-21\n\n## Goal\n\nx\n"
        self.refused(fenced, "Status")
        self.refused("# A plan\n\n<!--\nStatus: Approved\n-->\n\n## Goal\n\nx\n", "Status")
        self.refused("# A plan\n\n> Status: Approved\n\n## Goal\n\nx\n", "Status")
        self.refused("# A plan\n\n    Status: Approved\n\n## Goal\n\nx\n", "Status")

    def test_a_status_line_indented_by_up_to_three_spaces_is_the_status_line(self):
        self.same(text(), text().replace("Status: Proposed", "   Status: Approved"))


class Spoofs(Region):
    """Anything that merely looks like an excluded heading stays hashed, and anything that looks like another
    heading ends an excluded section, so hidden text cannot be put into the unhashed part."""

    def under(self, heading, hidden="hidden text"):
        """A plan whose only mention of `heading` is followed by `hidden`."""
        return plan() + "\n" + heading + "\n\n" + hidden + "\n"

    def hashed(self, content, hidden="hidden text"):
        """Whether editing `hidden` in `content` changes the hash."""
        return self.hash_of(content) != self.hash_of(content.replace(hidden, "edited text"))

    def test_the_exact_heading_hides_what_is_under_it(self):
        self.assertFalse(self.hashed(self.under("## Result")))
        self.assertFalse(self.hashed(self.under("## Review record")))
        self.assertFalse(self.hashed(self.under("## Second opinion")))
        self.assertFalse(self.hashed(self.under("## Result   ")))

    def test_a_heading_that_is_not_exactly_one_hides_nothing(self):
        for heading in ("## result", "## RESULT", "## Review Record", "## Results", "## Result:", "## Result ##",
                        "##  Result", "##\tResult", "### Result", "# Result", "#### Result", "Result",
                        "## Result (draft)", "## \\Result", "## **Result**", "## Rеsult",   # Cyrillic e
                        "   ## Result", "    ## Result", "\t## Result", "> ## Result", "- ## Result",
                        "## Result ", "## Result", "## Resu​lt"):
            with self.subTest(heading):
                self.assertTrue(self.hashed(self.under(heading)))

    def test_an_excluded_heading_inside_a_fence_a_comment_or_a_quote_hides_nothing(self):
        for body in ("```\n## Result\n```\n\nhidden text", "~~~\n## Result\n~~~\n\nhidden text",
                     "<!--\n## Result\n-->\n\nhidden text", "> ## Result\n\nhidden text",
                     "<!-- ## Result -->\n\nhidden text"):
            with self.subTest(body):
                self.assertTrue(self.hashed(plan() + "\n" + body + "\n"))

    def test_a_heading_ends_an_excluded_section_in_whatever_form_it_takes(self):
        for ender in ("## Other", "## other", "## OTHER", "  ## Other", "   ## Other", "# Other", "## ", "##",
                      "#", "Other\n=====", "Other\n-----", "Other\n--", "Other\n==", "---", "===",
                      "-", "  Other\n  ---"):
            with self.subTest(ender):
                content = plan() + "\n## Result\n\ngone\n\n" + ender + "\n\nhidden text\n"
                self.assertTrue(self.hashed(content))
                self.assertFalse(self.hashed(content, "gone"))

    def test_an_excluded_section_is_not_ended_by_a_deeper_heading_or_a_line_that_only_looks_like_one(self):
        for inner in ("### Deeper", "#### Deeper", "####### Seven", "#hashtag", "#!shebang", "- item", "* * *",
                      "1. one", "    ## indented code", "`## Other`", "text ## Other"):
            with self.subTest(inner):
                content = plan() + "\n## Result\n\n" + inner + "\n\ngone\n"
                self.assertFalse(self.hashed(content, "gone"))

    def test_text_after_an_excluded_section_that_a_viewer_shows_as_a_section_is_hashed(self):
        content = plan() + "\n## Result\n\nfine\n\nSneaky\n------\n\nhidden text\n"
        self.assertTrue(self.hashed(content))

    def test_a_duplicated_excluded_heading_is_refused(self):
        self.refused(text() + "\n## Result\n\nagain\n", "more than one")
        self.refused(text() + "\n## Review record\n\nagain\n", "more than one")
        self.refused(plan() + "\n## Review record\n\nx\n\n## Second opinion\n\ny\n", "more than one")

    def test_a_duplicated_excluded_heading_in_a_fence_is_only_text(self):
        content = text(tail="\n## Result\n\nx\n\n## Other\n\n```\n## Result\n```\n")
        self.hash_of(content)

    def test_a_fence_or_a_comment_that_is_never_closed_is_refused(self):
        self.refused(text() + "\n```\nunclosed\n", "never closed")
        self.refused(plan() + "\n## Result\n\n```\nunclosed\n", "never closed")
        self.refused(text() + "\n<!-- unclosed\n", "never closed")

    def test_a_longer_fence_is_closed_only_by_a_fence_as_long(self):
        content = plan() + "\n````\n```\n## Result\n```\n````\n\nhidden text\n"
        self.assertTrue(self.hashed(content))


class Normalized(Region):
    def test_line_endings_trailing_whitespace_and_the_final_newline_are_normalized(self):
        base = text()
        self.same(base, base.replace("\n", "\r\n"))
        self.same(base, base.replace("\n", "\r"))
        self.same(base, base.replace("Something.", "Something.   ").replace("## Goal", "## Goal\t"))
        self.same(base, base.rstrip("\n"))
        self.same(base, base + "\n\n\n")
        self.same(base, "".join(line.rstrip() + "\n" for line in base.split("\n")))

    def test_anything_else_in_the_whitespace_is_a_change(self):
        base = text()
        self.differs(base, base.replace("Something.", " Something."))
        self.differs(base, base.replace("Something.\n", "Something.\n\n"))
        self.differs(base, base.replace("## Goal\n\nSomething.", "## Goal\nSomething."))
        self.differs(base, base.replace("Something.", "Something. "))
        self.differs(base, base.replace("Something.", "Some thing."))
        self.differs(base, "﻿" + base)

    def test_a_change_far_along_a_long_line_is_a_change(self):
        long = "x" * 3000
        base = text().replace("Something.", long)
        self.differs(base, base.replace(long, long[:-1] + "y"))
        self.differs(base, base.replace(long, long + "y"))

    def test_a_change_in_a_line_the_check_only_reads_the_start_of_is_a_change(self):
        long = "y" * 2500
        base = text(body="### Increment A — Title\n\n" + long + "\n")
        self.differs(base, base.replace(long, long[:-1] + "z"))

    def test_a_plan_that_is_not_text_is_refused(self):
        self.refused(text().encode() + b"\xff\xfe", "UTF-8")
        self.refused(text().replace("Something.", "Some\udc80").encode("utf-8", "surrogateescape"), "UTF-8")

    def test_a_plan_over_the_size_the_check_reads_is_refused(self):
        self.refused(text() + "x" * (helper.MAX_DOCUMENT + 1), "larger than")
        self.hash_of(text() + "x" * 1000)


class Refusals(Region):
    def refused_path(self, argument, contains=""):
        code, out, err = self.check("region", argument)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)

    def test_what_is_not_a_plan_by_its_path(self):
        self.write(PLAN, text())
        self.write("docs/plans/sub/" + NAME, text())
        self.write("docs/other.md", text())
        for argument in ("", "docs/plans", "docs/plans/", "docs/plans/README.md", "docs/plans/Bad.md",
                         "docs/plans/2026-13-01-x.md", "docs/plans/" + NAME + ".txt", "docs/plans/sub/" + NAME,
                         "docs/other.md", "docs/plans/../plans/" + NAME, "/etc/passwd", "../" + PLAN,
                         "./" + PLAN, PLAN + "/", "docs//plans/" + NAME, "docs/plans/" + NAME + "\0", "-r",
                         "--help", "DOCS/PLANS/" + NAME):
            with self.subTest(argument):
                self.refused_path(argument)

    def test_a_missing_plan_and_a_missing_folder(self):
        self.refused_path("docs/plans/2026-10-22-missing.md", "cannot be read")
        os.rmdir(os.path.join(self.place, "docs", "plans"))
        self.refused_path(PLAN)

    def test_a_link_is_not_followed(self):
        self.write("elsewhere.md", text())
        os.symlink(os.path.join(self.place, "elsewhere.md"), os.path.join(self.place, "docs", "plans", NAME))
        self.refused_path(PLAN, "cannot be read")

    def test_a_linked_plans_folder_is_not_followed(self):
        os.rename(os.path.join(self.place, "docs", "plans"), os.path.join(self.place, "real-plans"))
        os.symlink(os.path.join(self.place, "real-plans"), os.path.join(self.place, "docs", "plans"))
        self.write("real-plans/" + NAME, text())
        self.refused_path(PLAN)

    def test_a_directory_or_a_special_file_is_not_a_plan(self):
        os.makedirs(os.path.join(self.place, "docs", "plans", NAME))
        self.refused_path(PLAN)

    def test_the_arguments(self):
        for argv in (["region"], ["region", PLAN, PLAN], ["region", "--x", PLAN], ["regions", PLAN]):
            with self.subTest(argv):
                code, out, err = self.check(*argv)
                self.assertEqual((1, ""), (code, out))
                self.assertIn("usage: code-work check|plans|report", err)

    def test_outside_a_project(self):
        code, out, err = self.check("region", PLAN, cwd=os.path.dirname(self.place))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not inside a workbench project", err)

    def test_the_other_subcommands_still_take_no_argument(self):
        for command in ("check", "plans", "report"):
            code, out, err = self.check(command, PLAN)
            self.assertEqual((1, ""), (code, out))


class Repository(Region):
    """This repository's own plans, copied into a project: each one is read, or refused with a reason."""

    def test_each_plan_of_this_repository_has_a_region(self):
        folder = os.path.join(support_install.ROOT, "docs", "plans")
        names = [name for name in sorted(os.listdir(folder)) if name.endswith(".md") and name != "README.md"]
        self.assertTrue(names)
        for name in names:
            with open(os.path.join(folder, name), "rb") as handle:
                self.write("docs/plans/" + name, handle.read())
            with self.subTest(name):
                code, out, err = self.region("docs/plans/" + name)
                self.assertEqual((0, ""), (code, err), out)
                self.assertEqual("Status", json.loads(out)["unhashed"][0])

    def test_a_status_edit_of_a_real_plan_does_not_change_its_hash_and_a_body_edit_does(self):
        folder = os.path.join(support_install.ROOT, "docs", "plans")
        name = "2026-10-22-plan-approval-records.md"
        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            real = handle.read()
        first = self.hash_of(real, name)
        self.assertEqual(first, self.hash_of(real.replace("Status: Approved", "Status: In Progress", 1), name))
        self.assertNotEqual(first, self.hash_of(real.replace("## Goal", "## Goal\n\nextra", 1), name))


if __name__ == "__main__":
    unittest.main()
