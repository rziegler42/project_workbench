"""The `code-work` helper's `plans` and `report` subcommands.

Plan `2026-10-21-code-work-plans`, increment C. Both read plans (and `report` reads roadmaps) through
the reader that `check` uses, so the bounds and the refusal to follow a link are tested once there and
spot-checked here. The roadmaps are written in the groundwork format."""

import os
import shutil
import unittest

from test_codework_helper import Project, helper, plan

ROADMAP = """# Roadmap: {name}

Status: Active
Updated: 2026-10-21

## Purpose

Words.

## Candidates

{body}
## Deferred work

### not-a-candidate — after the section
"""


def roadmap(*ids, extra=""):
    body = "".join("### %s — Title of %s\n\n**Outcome:** x.\n\n" % (i, i) for i in ids)
    return ROADMAP.format(name="r", body=body + extra)


class Reports(Project):
    def roadmap(self, name="first", *ids, text=None):
        self.write("docs/roadmaps/%s.md" % name, roadmap(*ids) if text is None else text)

    def done(self, topic, candidate, status="Completed"):
        self.plan("2026-10-21-%s.md" % topic, candidate=candidate, status=status)

    def index(self):
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            return handle.read()

    def run_command(self, command):
        code, out, err = self.check(command)
        return code, out.splitlines(), err.splitlines()


class Plans(Reports):
    def test_it_lists_the_plans_that_are_not_finished_sorted_by_name(self):
        self.done("zeta", "r#a", "Proposed")
        self.done("alpha", "r#a", "In Progress")
        self.done("middle", "r#a", "Approved")
        self.done("finished", "r#a", "Completed")
        self.done("old", "r#a", "Superseded")
        code, out, err = self.run_command("plans")
        self.assertEqual((0, []), (code, err))
        self.assertEqual(["2026-10-21-alpha.md: In Progress", "2026-10-21-middle.md: Approved",
                          "2026-10-21-zeta.md: Proposed"], out)

    def test_two_plans_of_one_day_are_both_listed(self):
        self.done("one", "r#a", "Approved")
        self.done("two", "r#a", "Approved")
        self.assertEqual(2, len(self.run_command("plans")[1]))

    def test_a_status_followed_by_a_note_counts_and_a_longer_word_does_not(self):
        self.done("note", "r#a", "Approved (by the owner, 2026-10-21)")
        self.done("longer", "r#a", "Approvedish")
        self.done("lower", "r#a", "approved")
        code, out, err = self.run_command("plans")
        self.assertEqual((0, ["2026-10-21-note.md: Approved"], []), (code, out, err))

    def test_a_status_line_inside_a_fence_or_below_the_header_is_not_the_status(self):
        self.plan("2026-10-21-fenced.md", text="# P\n\n```\nStatus: Approved\n```\n"
                  "Created: 2026-10-21\nCandidate: none, x\nSpecs: s\n\n## Increments\n")
        self.plan("2026-10-21-late.md", text="# P\n\nCreated: 2026-10-21\nCandidate: none, x\n"
                  "Specs: s\n\n## Goal\n\nStatus: Approved\n")
        self.assertEqual((0, [], []), self.run_command("plans"))

    def test_a_plan_with_two_status_lines_is_listed_by_the_first(self):
        self.plan("2026-10-21-two.md", text="# P\n\nStatus: Proposed\nStatus: Approved\n")
        self.assertEqual(["2026-10-21-two.md: Proposed"], self.run_command("plans")[1])

    def test_no_plans_and_no_folder_print_nothing_and_succeed(self):
        self.assertEqual((0, [], []), self.run_command("plans"))
        shutil.rmtree(os.path.join(self.place, "docs", "plans"))
        self.assertEqual((0, [], []), self.run_command("plans"))

    def test_the_readme_and_a_folder_are_not_plans(self):
        self.write("docs/plans/README.md", "# R\n\nStatus: Approved\n")
        os.mkdir(os.path.join(self.place, "docs", "plans", "2026-10-21-dir.md"))
        self.assertEqual((0, [], []), self.run_command("plans"))

    def test_a_name_with_an_escape_is_shown_written_out(self):
        self.plan("2026-10-21-x\x1b[31m.md", status="Approved")
        code, out, err = self.run_command("plans")
        self.assertEqual(0, code)
        self.assertEqual(["2026-10-21-x\\x1b[31m.md: Approved"], out)

    def test_a_link_is_not_followed_and_is_a_problem(self):
        target = os.path.join(self.place, "elsewhere.md")
        with open(target, "w") as handle:
            handle.write(plan(status="Approved"))
        os.symlink(target, os.path.join(self.place, "docs", "plans", "2026-10-21-link.md"))
        code, out, err = self.run_command("plans")
        self.assertEqual((1, []), (code, out))
        self.assertTrue(any("not a regular file" in line for line in err), err)

    def test_a_link_at_the_folder_is_a_problem_and_lists_nothing(self):
        os.rename(os.path.join(self.place, "docs", "plans"), os.path.join(self.place, "real"))
        os.symlink(os.path.join(self.place, "real"), os.path.join(self.place, "docs", "plans"))
        self.write("real/2026-10-21-x.md", plan(status="Approved"))
        code, out, err = self.run_command("plans")
        self.assertEqual((1, []), (code, out))
        self.assertTrue(any("cannot be listed" in line for line in err), err)

    def test_a_plan_that_cannot_be_read_for_the_bound_is_a_problem(self):
        old = helper.MAX_FILES
        helper.MAX_FILES = 2
        self.addCleanup(setattr, helper, "MAX_FILES", old)
        for topic in ("a", "b", "c"):
            self.done(topic, "r#a", "Approved")
        code, out, err = self.run_command("plans")
        self.assertEqual(1, code)
        self.assertEqual(2, len(out))
        self.assertTrue(any("not looked at" in line for line in err), err)

    def test_it_writes_nothing(self):
        self.done("one", "r#a", "Approved")
        before = self.snapshot()
        index = self.index()
        self.run_command("plans")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(index, self.index())

    def test_it_takes_no_arguments(self):
        self.assertEqual(1, self.check("plans", "extra")[0])


class Report(Reports):
    def test_a_candidate_with_a_completed_plan_is_complete(self):
        self.roadmap("first", "alpha", "beta")
        self.done("one", "first#alpha")
        self.done("two", "first#beta", "Approved")
        self.assertEqual((0, ["complete first#alpha"], []), self.run_command("report"))

    def test_two_completed_plans_for_one_candidate_report_it_once(self):
        self.roadmap("first", "alpha")
        self.done("one", "first#alpha")
        self.done("two", "first#alpha")
        self.assertEqual(["complete first#alpha"], self.run_command("report")[1])

    def test_the_lines_are_sorted_by_roadmap_and_candidate(self):
        self.roadmap("second", "b", "a")
        self.roadmap("first", "z")
        for topic, ref in (("p1", "second#b"), ("p2", "first#z"), ("p3", "second#a")):
            self.done(topic, ref)
        self.assertEqual(["complete first#z", "complete second#a", "complete second#b"],
                         self.run_command("report")[1])

    def test_one_candidate_id_in_two_roadmaps_is_two_candidates(self):
        self.roadmap("first", "same")
        self.roadmap("second", "same")
        self.done("one", "second#same")
        self.assertEqual(["complete second#same"], self.run_command("report")[1])

    def test_a_plan_naming_a_roadmap_that_is_not_there_is_unresolved(self):
        self.roadmap("first", "alpha")
        self.done("one", "gone#alpha")
        self.assertEqual((0, ["unresolved 2026-10-21-one.md names gone#alpha: no such roadmap"], []),
                         self.run_command("report"))

    def test_a_plan_naming_a_candidate_that_is_not_there_is_unresolved(self):
        self.roadmap("first", "alpha")
        self.done("one", "first#beta", "Approved")
        self.assertEqual(["unresolved 2026-10-21-one.md names first#beta: no such candidate"],
                         self.run_command("report")[1])

    def test_an_id_that_matches_only_after_case_folding_does_not_match(self):
        self.roadmap("first", "alpha")
        self.done("one", "first#ALPHA")
        out = self.run_command("report")[1]
        self.assertNotIn("complete first#alpha", out)
        self.assertEqual([], [l for l in out if l.startswith("complete")])

    def test_a_candidate_marked_dropped_stays_a_candidate(self):
        self.roadmap(text=roadmap("alpha", extra="### old — Old (dropped: no longer needed)\n\n"))
        self.done("one", "first#old")
        self.assertEqual(["complete first#old"], self.run_command("report")[1])

    def test_candidate_none_and_two_candidate_lines_name_nothing(self):
        self.roadmap("first", "alpha")
        self.plan("2026-10-21-none.md", candidate="none, a reason", status="Completed")
        self.plan("2026-10-21-two.md", status="Completed",
                  text=plan(status="Completed").replace(
                      "Specs:", "Candidate: first#alpha\nSpecs:", 1))
        self.assertEqual((0, [], []), self.run_command("report"))

    def test_only_headings_under_the_candidates_section_are_candidates(self):
        text = roadmap("alpha", extra="```\n### fenced — x\n```\n> ### quoted — x\n\n")
        self.roadmap(text=text)
        for topic, ref in (("p1", "first#fenced"), ("p2", "first#quoted"),
                           ("p3", "first#not-a-candidate")):
            self.done(topic, ref)
        out = self.run_command("report")[1]
        self.assertEqual([], [line for line in out if line.startswith("complete")])
        self.assertEqual(3, len([line for line in out if line.startswith("unresolved")]))

    def test_a_candidate_heading_in_a_comment_is_not_a_candidate(self):
        self.roadmap(text=roadmap("alpha", extra="<!--\n### hidden — x\n-->\n"))
        self.done("one", "first#hidden")
        self.assertEqual(["unresolved 2026-10-21-one.md names first#hidden: no such candidate"],
                         self.run_command("report")[1])

    def test_without_roadmaps_it_prints_nothing_and_succeeds(self):
        self.done("one", "first#alpha")
        self.assertEqual((0, [], []), self.run_command("report"))
        os.makedirs(os.path.join(self.place, "docs", "roadmaps"))
        self.assertEqual(1, len(self.run_command("report")[1]))

    def test_with_roadmaps_and_no_plans_folder_it_prints_nothing(self):
        self.roadmap("first", "alpha")
        shutil.rmtree(os.path.join(self.place, "docs", "plans"))
        self.assertEqual((0, [], []), self.run_command("report"))

    def test_the_readme_and_a_folder_in_roadmaps_are_not_roadmaps(self):
        self.write("docs/roadmaps/README.md", roadmap("alpha"))
        os.mkdir(os.path.join(self.place, "docs", "roadmaps", "dir.md"))
        self.done("one", "readme#alpha")
        self.assertEqual((0, ["unresolved 2026-10-21-one.md names readme#alpha: no such roadmap"],
                          []), self.run_command("report"))

    def test_an_escape_in_a_candidate_id_is_written_out(self):
        self.roadmap(text=roadmap("a\x1b[31mb"))
        self.done("one", "first#alpha")
        code, out, err = self.run_command("report")
        self.assertEqual(0, code)
        for line in out + err:
            self.assertNotIn("\x1b", line)

    def test_too_many_candidates_is_a_problem_naming_what_was_not_looked_at(self):
        old = helper.MAX_CANDIDATES
        helper.MAX_CANDIDATES = 3
        self.addCleanup(setattr, helper, "MAX_CANDIDATES", old)
        self.roadmap("first", "a", "b", "c", "d", "e")
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("not looked at" in line and "first.md" in line for line in err), err)

    def test_a_fence_or_comment_never_closed_in_a_roadmap_is_a_problem(self):
        self.roadmap("first", text=roadmap("alpha", extra="```\n### hidden — x\n"))
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("never closed" in line for line in err), err)

    def test_a_link_at_a_roadmap_or_at_the_folder_is_not_followed(self):
        os.makedirs(os.path.join(self.place, "docs", "roadmaps"))
        outside = os.path.join(self.place, "outside.md")
        with open(outside, "w") as handle:
            handle.write(roadmap("alpha"))
        os.symlink(outside, os.path.join(self.place, "docs", "roadmaps", "first.md"))
        self.done("one", "first#alpha")
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("not a regular file" in line for line in err), err)
        self.assertEqual([], [l for l in out if l.startswith("complete")])

    def test_a_link_at_the_roadmaps_folder_is_a_problem(self):
        os.makedirs(os.path.join(self.place, "real"))
        os.symlink(os.path.join(self.place, "real"), os.path.join(self.place, "docs", "roadmaps"))
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("cannot be listed" in line for line in err), err)

    def test_a_large_roadmap_is_cut_and_said_to_be(self):
        old = helper.MAX_DOCUMENT
        helper.MAX_DOCUMENT = 200
        self.addCleanup(setattr, helper, "MAX_DOCUMENT", old)
        self.roadmap("first", "alpha", "beta", "gamma", "delta")
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("only the start was examined" in line for line in err), err)

    def test_it_writes_nothing(self):
        self.roadmap("first", "alpha")
        self.done("one", "first#alpha")
        before = self.snapshot()
        index = self.index()
        self.run_command("report")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(index, self.index())

    def test_text_after_a_comment_closes_on_its_line_is_not_a_heading(self):
        for closer in ("<!--\n--> ### forged\n", "<!-- note --> ### forged\n"):
            self.roadmap(text=roadmap("real", extra=closer))
            self.done("one", "first#forged")
            self.assertEqual(["unresolved 2026-10-21-one.md names first#forged: no such candidate"],
                             self.run_command("report")[1], closer)

    def test_a_header_field_after_a_closing_comment_marker_is_not_a_field(self):
        text = "# P\n\n<!--\n--> Status: Approved\nStatus: Proposed\nCreated: 2026-10-21\n"
        self.plan("2026-10-21-x.md", text=text)
        self.assertEqual(["2026-10-21-x.md: Proposed"], self.run_command("plans")[1])

    def test_a_roadmap_not_read_in_full_makes_no_unresolved_claim(self):
        os.makedirs(os.path.join(self.place, "docs", "roadmaps"))
        outside = os.path.join(self.place, "outside.md")
        with open(outside, "w") as handle:
            handle.write(roadmap("alpha"))
        os.symlink(outside, os.path.join(self.place, "docs", "roadmaps", "first.md"))
        self.roadmap("second", "beta")
        self.done("one", "first#alpha")
        self.done("two", "second#beta")
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertEqual(["complete second#beta"], out)

    def test_a_plan_whose_header_is_hidden_by_an_unclosed_comment_is_a_problem(self):
        self.plan("2026-10-21-x.md", text="# P <!-- note\n\nStatus: Approved\n")
        code, out, err = self.run_command("plans")
        self.assertEqual((1, []), (code, out))
        self.assertTrue(any("status was not looked for" in line for line in err), err)
        self.roadmap("first", "alpha")
        code, out, err = self.run_command("report")
        self.assertEqual(1, code)
        self.assertTrue(any("status was not looked for" in line for line in err), err)

    def test_it_agrees_with_the_installer_on_the_candidate_ids(self):
        """The same roadmap text gives the same IDs as `doccheck`, so the two cannot disagree on
        which candidate a plan completes. (`doccheck` does not hide a heading inside an HTML comment and
        the helper does; that is the one known difference and it errs toward reporting less.)"""
        from workbench import doccheck
        corpus = [
            roadmap("alpha", "beta-two", extra="```\n### x — y\n```\n"),
            "# R\n\nStatus: Active\n\n## **Candidates**\n\n### a — A\n\n## Other\n\n### b — B\n",
            "# R\n\nCandidates\n----------\n\n### a — A\n\nOther\n-----\n\n### b — B\n",
            "# R\n\n## &#67;andidates:\n\n- ### a — A\n> ### q — Q\n### d — D\n",
            "# R\n\n### a — A\n\n## Candidates ##\n\n###\tb: B\n### \n",
        ]
        for text in corpus:
            ours = [i for i, _ in helper.roadmap_candidates(text)[0]]
            theirs = [i for _, i in doccheck._candidates(doccheck._lines(text))[0]]
            self.assertEqual(theirs, ours, text)


class Dispatched(Reports):
    def test_unknown_arguments_name_all_three_subcommands(self):
        code, out, err = self.check("bogus")
        self.assertEqual(1, code)
        self.assertIn("check|plans|report", err)


if __name__ == "__main__":
    unittest.main()
