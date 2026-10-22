"""The `code-work` helper's `active` subcommand: the plans under way, for the installer's edit gate.

Plan `2026-10-22-checkpoint-settings-and-caps`, increment D. A plan is under way when its header says `Approved` or
`In Progress`. What cannot be read with certainty is refused, never guessed, because the gate reads an empty answer
as permission. The helper is loaded by its path and run in process."""

import json
import os
import unittest

from test_codework_helper import Project, plan
from tests import support_install

NAMES = {"Proposed": "2026-10-20-a.md", "Approved": "2026-10-21-b.md", "In Progress": "2026-10-22-c.md",
         "Completed": "2026-10-23-d.md", "Superseded": "2026-10-24-e.md"}
MAX_OUT = 8192


def dates(count, year=2026):
    """`count` different valid dates, as the start of a plan's name."""
    return ["%d-%02d-%02d" % (year, 1 + index // 4, 1 + index % 4) for index in range(count)]


class Active(Project):
    def active(self, cwd=None):
        return self.check("active", cwd=cwd)

    def listed(self):
        code, out, err = self.active()
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(out.endswith("\n") and out.count("\n") == 1, out)
        report = json.loads(out)
        self.assertEqual(["format", "plans"], sorted(report))
        self.assertEqual(1, report["format"])
        self.assertLessEqual(len(out.encode("ascii")), MAX_OUT)
        return report["plans"]

    def refused(self, contains=""):
        code, out, err = self.active()
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        return err


class Statuses(Active):
    def test_no_plans_lists_none(self):
        self.assertEqual([], self.listed())

    def test_only_approved_and_in_progress_are_listed_in_name_order(self):
        for status, name in NAMES.items():
            self.plan(name, status=status)
        self.assertEqual(["docs/plans/" + NAMES["Approved"], "docs/plans/" + NAMES["In Progress"]], self.listed())

    def test_a_status_with_a_note_after_it_counts(self):
        self.plan(NAMES["Approved"], status="Approved (round 2)")
        self.plan(NAMES["Proposed"], status="Proposed, not Approved")
        self.assertEqual(["docs/plans/" + NAMES["Approved"]], self.listed())

    def test_the_readme_and_other_files_are_not_plans(self):
        self.write("docs/plans/README.md", "Status: Approved\n")
        self.write("docs/plans/notes.txt", "Status: Approved\n")
        os.makedirs(os.path.join(self.place, "docs", "plans", "2026-10-21-dir.md"))
        self.assertEqual([], self.listed())

    def test_it_runs_from_a_directory_below_the_root(self):
        self.plan(NAMES["Approved"], status="Approved")
        below = os.path.join(self.place, "docs")
        self.assertEqual(0, self.active(cwd=below)[0])

    def test_it_changes_nothing(self):
        for status, name in NAMES.items():
            self.plan(name, status=status)
        before = self.snapshot()
        self.assertEqual(0, self.active()[0])
        self.assertEqual(before, self.snapshot())

    def test_it_takes_no_argument(self):
        for argv in (["active", "x"], ["active", "--all"], ["active", "docs/plans/" + NAMES["Approved"]]):
            with self.subTest(argv):
                code, out, err = self.check(*argv)
                self.assertEqual((1, ""), (code, out))
                self.assertIn("usage: code-work check|plans|report|active", err)


class Hostile(Active):
    def test_a_status_in_a_fence_a_comment_or_a_quote_is_not_one(self):
        for index, header in enumerate(("```\nStatus: Approved\n```\n", "<!--\nStatus: Approved\n-->\n",
                                        "> Status: Approved\n", "    Status: Approved\n")):
            self.write("docs/plans/2026-10-2%d-x.md" % index, "# A plan\n\n%s\nCreated: 2026-10-21\n\n## Goal\n\nx\n" % header)
        self.assertEqual([], self.listed())

    def test_a_plan_with_no_status_line_is_not_under_way(self):
        self.write("docs/plans/" + NAMES["Approved"], "# A plan\n\nCreated: 2026-10-21\n\n## Goal\n\nx\n")
        self.assertEqual([], self.listed())

    def test_a_status_line_after_the_first_heading_is_text(self):
        self.write("docs/plans/" + NAMES["Approved"], "# A plan\n\n## Goal\n\nStatus: Approved\n")
        self.assertEqual([], self.listed())

    def test_two_status_lines_list_the_plan_when_either_is_under_way(self):
        both = "# A plan\n\nStatus: Proposed\nStatus: Approved\nCreated: 2026-10-21\n\n## Goal\n\nx\n"
        self.write("docs/plans/" + NAMES["Proposed"], both)
        self.write("docs/plans/" + NAMES["Approved"], both.replace("Proposed", "Approved").replace(
            "Status: Approved\nCreated", "Status: Completed\nCreated"))
        self.assertEqual(["docs/plans/" + NAMES["Proposed"], "docs/plans/" + NAMES["Approved"]], self.listed())

    def test_a_status_the_indentation_allows_counts(self):
        self.write("docs/plans/" + NAMES["Approved"], "# A plan\n\n   Status: Approved\n\n## Goal\n\nx\n")
        self.assertEqual(["docs/plans/" + NAMES["Approved"]], self.listed())

    def test_a_fence_or_a_comment_open_in_the_header_is_refused(self):
        for tail in ("```\nStatus: Approved\n", "<!--\nStatus: Approved\n"):
            with self.subTest(tail):
                self.write("docs/plans/" + NAMES["Proposed"], "# A plan\n\n" + tail)
                self.refused("never closed")

    def test_a_fence_that_opens_after_the_header_does_not_matter(self):
        self.plan(NAMES["Approved"], text=plan(status="Approved") + "\n```\nunclosed\n")
        self.assertEqual(["docs/plans/" + NAMES["Approved"]], self.listed())

    def test_a_plan_under_way_that_is_not_named_like_a_plan_is_refused(self):
        self.write("docs/plans/Notes.md", plan(status="Approved"))
        self.refused("not named like a plan")

    def test_a_file_not_named_like_a_plan_that_is_not_under_way_is_ignored(self):
        self.write("docs/plans/Notes.md", plan(status="Proposed"))
        self.assertEqual([], self.listed())

    def test_a_link_is_refused_not_followed(self):
        outside = os.path.join(os.path.dirname(self.place), "elsewhere.md")
        with open(outside, "w") as handle:
            handle.write(plan(status="Approved"))
        self.addCleanup(os.remove, outside)
        os.symlink(outside, os.path.join(self.place, "docs", "plans", NAMES["Approved"]))
        self.refused("not a regular file")

    def test_a_linked_plans_folder_is_not_followed(self):
        os.rmdir(os.path.join(self.place, "docs", "plans"))
        elsewhere = os.path.join(os.path.dirname(self.place), "elsewhere")
        os.makedirs(elsewhere)
        self.addCleanup(os.rmdir, elsewhere)
        os.symlink(elsewhere, os.path.join(self.place, "docs", "plans"))
        self.addCleanup(os.remove, os.path.join(self.place, "docs", "plans"))
        code, out, err = self.active()
        self.assertEqual(1, code, out)

    def test_a_plan_larger_than_the_helper_reads_is_refused(self):
        self.write("docs/plans/" + NAMES["Approved"], plan(status="Approved") + "x" * (1024 * 1024 + 1))
        self.refused("larger than")

    def test_names_that_differ_only_in_case_are_refused(self):
        self.plan("2026-10-21-a.md", status="Approved")
        try:
            self.write("docs/plans/2026-10-21-A.md", plan(status="Approved"))
        except OSError:
            self.skipTest("a case-insensitive filesystem cannot hold both")
        if len(os.listdir(os.path.join(self.place, "docs", "plans"))) == 2:
            self.refused("differs only in letter case")

    def test_a_status_that_is_not_utf8_does_not_fail_the_helper(self):
        self.write("docs/plans/" + NAMES["Approved"], b"# A plan\n\nStatus: Approved\n\xff\xfe\n\n## Goal\n")
        self.assertEqual(["docs/plans/" + NAMES["Approved"]], self.listed())


class Bounds(Active):
    def test_thirty_two_plans_are_listed_and_a_thirty_third_is_refused(self):
        for date in dates(32):
            self.plan(date + "-p.md", status="Approved")
        self.assertEqual(32, len(self.listed()))
        self.plan("2027-01-01-p.md", status="Approved")
        self.refused("more than 32 plans")

    def test_plans_that_are_not_under_way_do_not_count_toward_the_bound(self):
        for date in dates(28, 2025):
            self.plan(date + "-p.md", status="Completed")
        for date in dates(32):
            self.plan(date + "-q.md", status="Approved")
        self.assertEqual(32, len(self.listed()))

    def test_a_path_over_the_bound_is_refused(self):
        name = "2026-10-21-" + "a" * 230 + ".md"
        self.assertGreater(len("docs/plans/" + name), 240)
        self.plan(name, status="Approved")
        self.refused("longer than 240")

    def test_the_longest_accepted_path_fits_the_output_bound(self):
        for date in dates(32):
            self.plan(date + "-" + "a" * (240 - len("docs/plans/2026-10-01-.md")) + ".md", status="Approved")
        self.assertEqual(32, len(self.listed()))

    def test_many_problems_are_cut_in_the_message(self):
        for day in range(1, 8):
            self.write("docs/plans/N%d.md" % day, plan(status="Approved"))
        err = self.refused("more problems are not listed")
        self.assertEqual(1, err.count("\n"))


class Repository(Active):
    def test_this_repositorys_own_plans_are_read_and_the_under_way_ones_listed(self):
        folder = os.path.join(support_install.ROOT, "docs", "plans")
        names = [name for name in sorted(os.listdir(folder)) if name.endswith(".md") and name != "README.md"]
        self.assertTrue(names)
        for name in names:
            with open(os.path.join(folder, name), "rb") as handle:
                self.write("docs/plans/" + name, handle.read())
        listed = self.listed()
        for path in listed:
            self.assertRegex(path, r"\Adocs/plans/[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+\.md\Z")
            self.assertTrue(os.path.isfile(os.path.join(folder, path.split("/")[-1])), path)


if __name__ == "__main__":
    unittest.main()
