import io
import os
import shutil
import subprocess
import unittest
import unittest.mock

from tests.test_projectfs import Fixture
from workbench import check, cli, doccheck, manifest

HASH = "a" * 64

SPEC = "# Power\n\nStatus: Current. Approved on 2026-10-21.\n\n## Scope\n\nText.\n"
DECISION = "# Use SPI flash\n\nStatus: Accepted\nDate: 2026-01-15\n\n## Context\n\nText.\n"
ROADMAP = ("# Roadmap: first-release\n\nStatus: Active\nUpdated: 2026-10-21\n\n## Purpose\n\nx\n\n"
           "## Candidates\n\n### pick-a-board: Pick a board\n\nx\n\n### write-driver — Write\n")


def installed_document(module=doccheck.MODULE, package=doccheck.PACKAGE):
    return {
        "base": HASH, "files": [],
        "packages": [{"commit": "", "modules": [{"declaration": HASH, "name": module,
                                                  "tree": HASH, "version": "0.1.0"}],
                      "name": package, "ref": "", "source": "https://example.test/p",
                      "tree": HASH}],
        "seed": "11111111-2222-4333-8444-555555555555", "version": 1, "workbench": "0.1.0",
    }


class Base(Fixture):
    def put(self, rel, data):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def fresh(self, rel, data):
        """Only this document under docs/, so one subtest never sees another's file."""
        shutil.rmtree(os.path.join(self.root, "docs"), ignore_errors=True)
        self.put(rel, data)

    def install(self, **changes):
        self.put(".workbench/manifest.json", manifest.serialize(installed_document(**changes)))

    def problems(self):
        problems, warnings = doccheck.examine(self.writer())
        self.assertEqual([], warnings)
        return problems

    def only(self, *needles):
        """The one problem, which holds every needle."""
        problems = self.problems()
        self.assertEqual(1, len(problems), problems)
        for needle in needles:
            self.assertIn(needle, problems[0])
        return problems[0]


class Presence(Base):
    def test_a_project_without_a_manifest_gets_no_report_whatever_its_documents(self):
        self.put("docs/specs/Bad_Name.md", "no status\n")
        self.assertEqual(([], []), doccheck.examine(self.writer()))

    def test_a_project_with_another_module_gets_no_report(self):
        self.install(module="other")
        self.put("docs/specs/Bad_Name.md", "no status\n")
        self.assertEqual([], self.problems())

    def test_a_package_of_another_name_does_not_count(self):
        self.install(package="elsewhere")
        self.put("docs/specs/Bad_Name.md", "no status\n")
        self.assertEqual([], self.problems())

    def test_an_unreadable_manifest_is_not_this_checks_to_report(self):
        self.put(".workbench/manifest.json", b"not json")
        self.put("docs/specs/Bad_Name.md", "no status\n")
        self.assertEqual([], self.problems())

    def test_the_module_with_none_of_the_folders_gives_no_problem(self):
        self.install()
        self.assertEqual([], self.problems())

    def test_the_module_with_only_a_readme_in_each_folder_is_clean(self):
        self.install()
        for folder in ("specs", "roadmaps", "decisions", "references"):
            self.put("docs/%s/README.md" % folder, "# %s\n" % folder)
        self.assertEqual([], self.problems())

    def test_a_link_in_place_of_the_manifest_is_not_followed(self):
        os.makedirs(os.path.join(self.root, ".workbench"))
        self.put("../outside/manifest.json", manifest.serialize(installed_document()))
        os.symlink(os.path.join(self.outside, "manifest.json"),
                   os.path.join(self.root, ".workbench", "manifest.json"))
        self.put("docs/specs/Bad_Name.md", "x\n")
        self.assertEqual([], self.problems())


class Documents(Base):
    def setUp(self):
        super().setUp()
        self.install()

    def test_well_formed_documents_are_clean(self):
        self.put("docs/specs/power-supply.md", SPEC)
        self.put("docs/decisions/2026-01-15-use-spi-flash.md", DECISION)
        self.put("docs/roadmaps/first-release.md", ROADMAP)
        self.put("docs/specs/README.md", "# Specs\n")
        self.put("docs/specs/diagram.png", b"\x89PNG")
        os.makedirs(os.path.join(self.root, "docs", "roadmaps", "archive"))
        self.put("docs/roadmaps/archive/old.md", "no status\n")
        self.assertEqual([], self.problems())

    def test_a_spec_named_with_a_date_or_not_in_kebab_case_is_reported(self):
        for name in ("Power.md", "power_supply.md",
                     "power supply.md", "power--supply.md", "-power.md", "power-.md",
                     "a..b.md", "power.MD.md"):
            with self.subTest(name=name):
                self.fresh("docs/specs/" + name, SPEC)
                self.only("docs/specs/" + name, "<topic>.md")

    def test_a_spec_or_roadmap_named_with_a_date_is_reported(self):
        for kind, folder in (("spec", "specs"), ("roadmap", "roadmaps")):
            for name in ("2026-10-21-power.md", "2026-10-21.md"):
                with self.subTest(kind=kind, name=name):
                    self.fresh("docs/%s/%s" % (folder, name), "# T\n\nStatus: Draft\n")
                    self.only("docs/%s/%s" % (folder, name), "with no date")

    def test_a_decision_needs_a_real_date_in_its_name(self):
        for name in ("use-spi.md", "2026-1-5-use-spi.md", "2026-01-15.md", "2026-13-01-x.md",
                     "2026-02-30-x.md", "0000-01-01-x.md", "2026-01-15-Use.md", "26-01-15-x.md"):
            with self.subTest(name=name):
                self.fresh("docs/decisions/" + name, DECISION)
                self.only("docs/decisions/" + name)

    def test_a_name_that_is_not_usable_is_reported_and_not_read(self):
        self.put("docs/specs/a\x1bb.md", "x\n")
        self.put("docs/specs/c:d.md", "x\n")
        self.put("docs/specs/e\\f.md", "x\n")
        found = self.problems()
        self.assertEqual(3, len(found), found)
        for line in found:
            self.assertIn("the name is not usable", line)
            self.assertNotIn("\x1b", line)

    def test_a_missing_status_line_is_reported(self):
        self.put("docs/specs/power.md", "# Power\n\n## Scope\n\nStatus: Current\n")
        self.only("docs/specs/power.md", "no status line")

    def test_a_status_outside_the_set_is_reported_for_each_kind(self):
        cases = (("docs/specs/power.md", "Accepted", "Draft, Current or Superseded"),
                 ("docs/decisions/2026-01-15-x.md", "Current",
                  "Proposed, Accepted, Rejected or Superseded"),
                 ("docs/roadmaps/first.md", "Current", "Draft, Active or Archived"))
        for path, status, listed in cases:
            with self.subTest(path=path):
                self.fresh(path, "# T\n\nStatus: %s\n\n## A\n" % status)
                self.only(path, "has the status %s" % status, listed)

    def test_a_status_must_match_in_letter_case_and_end_the_word(self):
        for status in ("current", "CURRENT", "Currently", "Current-ish", "Current2", "",
                       "Ра"):
            with self.subTest(status=status):
                self.fresh("docs/specs/power.md", "# T\n\nStatus: %s\n" % status)
                self.only("docs/specs/power.md", "status")

    def test_a_status_followed_by_text_is_the_status(self):
        for tail in (".", ", approved", " (draft)", " - note", ": x"):
            with self.subTest(tail=tail):
                self.put("docs/specs/power.md", "# T\n\nStatus: Current%s\n" % tail)
                self.assertEqual([], self.problems())

    def test_a_repeated_status_line_is_reported(self):
        self.put("docs/specs/power.md", "# T\n\nStatus: Current\nStatus: Draft\n\n## A\n")
        self.only("docs/specs/power.md", "2 status lines")

    def test_a_status_line_in_a_fence_or_quote_or_below_a_heading_does_not_count(self):
        self.put("docs/specs/power.md",
                 "# T\n\nStatus: Current\n\n```\nStatus: Draft\n```\n> Status: Draft\n\n"
                 "## Scope\n\nStatus: Draft\n~~~~\nStatus: Draft\n~~~~\n")
        self.assertEqual([], self.problems())

    def test_a_status_only_inside_a_fence_is_missing(self):
        self.put("docs/specs/power.md", "# T\n\n```\nStatus: Current\n```\n")
        self.only("no status line")

    def test_a_shorter_closing_fence_does_not_end_the_fence(self):
        self.put("docs/specs/power.md", "# T\n\n````\n```\nStatus: Current\n````\n")
        self.only("no status line")

    def test_a_status_after_the_header_limit_is_missing(self):
        self.put("docs/specs/power.md", "# T\n" + "\n" * doccheck.MAX_HEADER + "Status: Current\n")
        self.only("no status line")

    def test_a_superseded_record_must_name_its_successor(self):
        self.put("docs/specs/old.md", "# T\n\nStatus: Superseded\n\n## A\n")
        self.only("docs/specs/old.md", "names no successor")
        for text in ("Status: Superseded by new-spec\n", "Status: Superseded\nSuperseded by: x\n",
                     "Status: Superseded. Superseded by [new](new.md).\n"):
            with self.subTest(text=text):
                self.put("docs/specs/old.md", "# T\n\n" + text + "\n## A\n")
                self.assertEqual([], self.problems())

    def test_a_successor_in_a_fence_or_below_a_heading_does_not_count(self):
        self.put("docs/specs/old.md",
                 "# T\n\nStatus: Superseded\n\n```\nSuperseded by x\n```\n> Superseded by x\n"
                 "## A\n\nSuperseded by x\n")
        self.only("names no successor")

    def test_a_superseded_by_with_nothing_after_it_names_nothing(self):
        self.put("docs/specs/old.md", "# T\n\nStatus: Superseded by\n")
        self.only("names no successor")

    def test_the_status_of_a_superseded_record_is_otherwise_valid(self):
        self.put("docs/decisions/2026-01-15-x.md", "# T\n\nStatus: Superseded by 2026-02-01-y\n")
        self.assertEqual([], self.problems())

    def test_a_file_that_is_not_utf8_is_read_with_replacement_and_not_a_crash(self):
        self.put("docs/specs/power.md", b"# T\n\nStatus: Current\n\xff\xfe\n")
        self.assertEqual([], self.problems())


class Candidates(Base):
    def setUp(self):
        super().setUp()
        self.install()

    def roadmap(self, *headings, extra=""):
        body = "# R\n\nStatus: Active\n\n## Candidates\n\n" + "".join(
            "### %s\n\ntext\n\n" % each for each in headings) + extra
        self.put("docs/roadmaps/first.md", body)

    def test_two_candidates_with_one_id_are_reported_with_both_lines(self):
        self.roadmap("pick-a-board: One", "write-driver: Two", "pick-a-board — Three")
        problem = self.only("docs/roadmaps/first.md", "pick-a-board", "repeats", "on line 7")
        self.assertIn("line 15", problem)

    def test_ids_that_differ_only_in_case_or_form_are_duplicates(self):
        for other in ("Pick-A-Board", "PICK-A-BOARD", "pick‐a-board", "ｐick-a-board",
                      "pick-a-board"):
            with self.subTest(other=other):
                self.roadmap("pick-a-board", other)
                found = self.problems()
                self.assertTrue(any("repeats" in line for line in found) or
                                any("not a lowercase" in line for line in found), found)
        self.roadmap("pick-a-board", "ｐick-a-board")
        self.assertTrue(any("repeats" in line for line in self.problems()))
        self.roadmap("pick-a-board", "Pick-A-Board")
        self.assertTrue(any("repeats" in line for line in self.problems()))

    def test_an_id_that_is_not_a_slug_is_reported(self):
        for each in ("Pick", "pick_a_board", "pick--board", "-pick", "pick-", "0x1.5", "café"):
            with self.subTest(each=each):
                self.roadmap(each)
                self.only("not a lowercase kebab-case slug")

    def test_a_long_id_is_reported(self):
        self.roadmap("a" * 65)
        self.only("not a lowercase kebab-case slug")

    def test_an_id_in_a_fence_or_a_quote_does_not_count(self):
        self.roadmap("pick-a-board", extra=("```\n### pick-a-board\n```\n> ### pick-a-board\n\n"
                                            "~~~\n### pick-a-board\n~~~\n"))
        self.assertEqual([], self.problems())

    def test_a_heading_outside_the_candidates_section_does_not_count(self):
        self.put("docs/roadmaps/first.md",
                 "# R\n\nStatus: Active\n\n### pick-a-board\n\n## Candidates\n\n### pick-a-board\n\n"
                 "## Deferred work\n\n### pick-a-board\n")
        self.assertEqual([], self.problems())

    def test_the_candidates_heading_is_matched_without_case(self):
        self.put("docs/roadmaps/first.md",
                 "# R\n\nStatus: Active\n\n## CANDIDATES\n\n### a-b\n\n### a-b\n")
        self.only("repeats")

    def test_a_roadmap_with_headings_and_no_candidates_section_says_none_was_checked(self):
        self.put("docs/roadmaps/first.md", "# R\n\nStatus: Active\n\n### a-b\n\n### a-b\n")
        self.only("no ## Candidates section", "no candidate was checked")

    def test_a_roadmap_with_no_headings_and_no_section_is_clean(self):
        self.put("docs/roadmaps/first.md", "# R\n\nStatus: Active\n\nText.\n")
        self.assertEqual([], self.problems())

    def test_a_deeper_or_indented_heading_is_not_a_candidate(self):
        self.roadmap("a-b", extra="#### a-b\n\n    ### a-b\n\n")
        self.assertEqual([], self.problems())

    def test_a_terminal_escape_in_a_heading_is_shown_escaped(self):
        self.roadmap("\x1b[31mred\x1b[0m")
        problem = self.only("not a lowercase kebab-case slug")
        self.assertNotIn("\x1b", problem)
        self.assertIn("\\x1b", problem)

    def test_thousands_of_candidates_are_cut_and_the_cut_is_a_problem(self):
        self.roadmap(*("c-%d" % n for n in range(doccheck.MAX_CANDIDATES + 500)))
        self.only("more than %d candidates" % doccheck.MAX_CANDIDATES, "not looked at")

    def test_the_candidate_bound_can_be_lowered_to_see_it_bind(self):
        with unittest.mock.patch.object(doccheck, "MAX_CANDIDATES", 2):
            self.roadmap("a-a", "b-b", "c-c")
            self.only("more than 2 candidates")
            self.roadmap("a-a", "b-b")
            self.assertEqual([], self.problems())


class Evasions(Base):
    """Forms a renderer reads as a heading, a line or a fence that a scanner can miss."""

    def setUp(self):
        super().setUp()
        self.install()

    def roadmap(self, text):
        self.put("docs/roadmaps/first.md", text)

    def test_a_candidates_heading_with_decoration_is_still_the_section(self):
        for heading in ("## Candidates ##", "## Candidates:", "## Candidates <!-- x -->",
                        "## Candidates #", "## CANDIDATES.", "##   Candidates   ##  ",
                        "## Candidates ## <!-- x -->"):
            with self.subTest(heading=heading):
                self.roadmap("# R\n\nStatus: Active\n\n%s\n\n### a\n\n### a\n" % heading)
                self.only("repeats")

    def test_other_headings_are_not_the_section(self):
        for heading in ("## Candidates of the past", "## Candidate", "## Not Candidates"):
            with self.subTest(heading=heading):
                self.roadmap("# R\n\nStatus: Active\n\n%s\n\n### a\n\n### a\n" % heading)
                self.only("no ## Candidates section")

    def test_a_carriage_return_alone_ends_a_line(self):
        self.roadmap("# R\rStatus: Active\r## Candidates\r### a\r### a\r")
        self.only("repeats")
        self.put("docs/specs/power.md", "# T\rStatus: Current\rStatus: Draft\r")
        found = self.problems()
        self.assertTrue(any("2 status lines" in line for line in found), found)

    def test_carriage_return_and_line_feed_together_end_one_line(self):
        self.roadmap("# R\r\nStatus: Active\r\n\r\n## Candidates\r\n\r\n### a\r\n### b\r\n")
        self.assertEqual([], self.problems())

    def test_a_backtick_fence_with_a_backtick_in_its_info_string_is_not_a_fence(self):
        self.roadmap("# R\n\nStatus: Active\n\n```x`y\n\n## Candidates\n\n### a\n\n### a\n")
        self.only("repeats")

    def test_a_tilde_fence_may_have_a_backtick_in_its_info_string(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n~~~x`y\n### a\n### a\n~~~\n")
        self.assertEqual([], self.problems())

    def test_an_unclosed_fence_is_reported(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### a\n\n```\n### a\n")
        self.only("a code fence is never closed")
        self.put("docs/specs/power.md", "# T\n\nStatus: Current\n\n~~~\ntext\n")
        self.assertTrue(any("never closed" in line for line in self.problems()))

    def test_a_closed_fence_is_not_reported(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n```\n### a\n```\n")
        self.assertEqual([], self.problems())

    def test_a_superseded_by_with_no_name_or_in_the_title_names_no_successor(self):
        for text in ("# T superseded by x\n\nStatus: Superseded\n",
                     "# T\n\nStatus: Superseded\nSuperseded by:\n",
                     "# T\n\nStatus: Superseded\nSuperseded by :  \n",
                     "# T\n\nStatus: Superseded\nThis was superseded by x.\n"):
            with self.subTest(text=text):
                self.fresh("docs/specs/old.md", text)
                self.only("names no successor")

    def test_the_named_forms_of_a_successor_are_accepted(self):
        for text in ("Status: Superseded by new\n", "Status: Superseded\nSuperseded by: new\n",
                     "Status: Superseded\nsuperseded by [new](new.md)\n",
                     "Status: Superseded. Superseded by new\n"):
            with self.subTest(text=text):
                self.fresh("docs/specs/old.md", "# T\n\n" + text)
                self.assertEqual([], self.problems())

    def test_a_document_over_the_per_document_limit_is_examined_only_in_part_and_says_so(self):
        with unittest.mock.patch.object(doccheck, "MAX_DOCUMENT", 200):
            self.put("docs/specs/power.md", SPEC + "x\n" * 500)
            self.only("larger than the 200 bytes looked at", "only the start was examined")

    def test_a_status_after_the_per_document_limit_is_not_seen_and_the_cut_is_a_problem(self):
        with unittest.mock.patch.object(doccheck, "MAX_DOCUMENT", 100):
            self.put("docs/specs/power.md", "# T\n" + "\n" * 150 + "Status: Current\n")
            found = self.problems()
        self.assertTrue(any("only the start was examined" in line for line in found), found)

    def test_a_large_file_of_newlines_is_not_held_as_a_list_of_lines(self):
        import time
        import tracemalloc
        self.put("docs/specs/power.md", "# T\n\nStatus: Current\n" + "\n" * (3 * 1024 * 1024))
        tracemalloc.start()
        try:
            start = time.monotonic()
            found = self.problems()
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertLess(time.monotonic() - start, 10)
        self.assertTrue(any("only the start was examined" in line for line in found), found)
        # Held as a list of lines this was several hundred megabytes.
        self.assertLess(peak, 64 * 1024 * 1024)

    def test_a_fence_opener_with_a_backtick_beyond_the_line_cut_is_not_a_fence(self):
        opener = "```" + " " * (doccheck._LINE + 100) + "`"
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n%s\n### a\n\n### a\n```\n" % opener)
        found = self.problems()
        self.assertTrue(any("repeats" in line for line in found), found)

    def test_a_second_status_line_cannot_be_hidden_behind_such_an_opener(self):
        opener = "```" + " " * (doccheck._LINE + 100) + "`"
        self.put("docs/specs/power.md", "# T\n\nStatus: Current\n%s\nStatus: Draft\n```\n" % opener)
        found = self.problems()
        self.assertTrue(any("2 status lines" in line for line in found), found)

    def test_headings_inside_list_items_count_as_candidates(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n- ### a\n\n1. ### a\n")
        self.only("repeats")

    def test_a_candidates_heading_written_with_markup_is_still_the_section(self):
        for heading in ("## *Candidates*", "## &#67;andidates", "## `Candidates`", "## _Candidates_",
                        "## Candi&#100;ates", "## \\Candidates"):
            with self.subTest(heading=heading):
                self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### x\n\n## Notes\n\n"
                             "%s\n\n### a\n\n### a\n" % heading)
                self.only("repeats")

    def test_a_setext_candidates_heading_is_still_the_section(self):
        for underline in ("---", "-", "  ----  "):
            with self.subTest(underline=underline):
                self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### x\n\n## Notes\n\n"
                             "Candidates\n%s\n\n### a\n\n### a\n" % underline)
                self.only("repeats")

    def test_a_setext_heading_of_another_name_ends_the_section(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### x\n\nNotes\n---\n\n"
                     "### a\n\n### a\n")
        self.assertEqual([], self.problems())
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### x\n\nNotes\n=====\n\n"
                     "### a\n\n### a\n")
        self.assertEqual([], self.problems())

    def test_a_rule_after_a_blank_line_is_not_a_setext_underline(self):
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n### a\n\n---\n\n### a\n")
        self.only("repeats")

    def test_padding_cannot_push_the_words_out_of_a_heading(self):
        for heading in ("## Candidates" + " " * 500 + "##", "## Candidates" + " " * 500 + "<!-- x -->",
                        "## Candidates <!-- " + "x" * 600 + " -->", "## Candidates <!-- " + "x" * 600,
                        "##" + " " * 500 + "Candidates"):
            with self.subTest(heading=heading[:40]):
                self.roadmap("# R\n\nStatus: Active\n\n%s\n\n### a\n\n### a\n" % heading)
                self.only("repeats")

    def test_a_roadmap_of_padded_headings_is_not_quadratic(self):
        import time
        lines = ["## a" + " " * 1990 + "x\n"] * 300 + ["## a <!--" * 200 + "\n"] * 100
        self.roadmap("# R\n\nStatus: Active\n\n## Candidates\n\n" + "".join(lines))
        start = time.monotonic()
        self.problems()
        self.assertLess(time.monotonic() - start, 2)

    def test_a_fence_opened_on_a_list_item_line_is_closed_by_its_indented_fence(self):
        self.put("docs/specs/power.md", "# T\n\nStatus: Current\n\n- ```\n  code\n  ```\n\ntext\n")
        self.assertEqual([], self.problems())

    def test_a_directory_of_many_bad_names_stops_at_the_reported_bound(self):
        for n in range(doccheck.MAX_REPORTED + 30):
            self.put("docs/specs/Bad%d.md" % n, SPEC)
        found = self.problems()
        self.assertEqual(doccheck.MAX_REPORTED + 1, len(found))
        self.assertEqual("more document problems are not listed", found[-1])

    def test_a_fifo_named_as_a_document_is_reported_without_hanging(self):
        os.makedirs(os.path.join(self.root, "docs", "specs"))
        os.mkfifo(os.path.join(self.root, "docs", "specs", "power.md"))
        self.only("docs/specs/power.md: is not a regular file (other)")


class Hostile(Base):
    def setUp(self):
        super().setUp()
        self.install()

    def test_a_link_at_the_folder_is_not_followed(self):
        self.put("../outside/first.md", "# R\n\nStatus: Nonsense\n")
        os.makedirs(os.path.join(self.root, "docs"))
        os.symlink(self.outside, os.path.join(self.root, "docs", "roadmaps"))
        found = self.problems()
        self.assertEqual(1, len(found), found)
        self.assertIn("docs/roadmaps: cannot be listed", found[0])

    def test_a_link_at_a_file_is_reported_and_not_read(self):
        self.put("../outside/target.md", "# R\n\nStatus: Nonsense\n")
        os.makedirs(os.path.join(self.root, "docs", "roadmaps"))
        os.symlink(os.path.join(self.outside, "target.md"),
                   os.path.join(self.root, "docs", "roadmaps", "first.md"))
        self.only("docs/roadmaps/first.md", "symlink", "not read")

    def test_a_link_at_docs_is_not_followed(self):
        self.put("../outside/specs/power.md", "no status\n")
        os.symlink(self.outside, os.path.join(self.root, "docs"))
        found = self.problems()
        self.assertEqual(3, len(found), found)
        self.assertTrue(all("cannot be listed" in line for line in found))

    def test_a_directory_named_like_a_document_is_ignored(self):
        os.makedirs(os.path.join(self.root, "docs", "specs", "power.md"))
        self.assertEqual([], self.problems())

    def test_a_file_over_the_read_limit_is_a_problem_and_not_a_crash(self):
        with unittest.mock.patch("workbench.safefs.MAX_FILE_BYTES", 1000):
            with unittest.mock.patch("workbench.projectfs.safefs.MAX_FILE_BYTES", 1000):
                self.put("docs/specs/power.md", "# T\n\nStatus: Current\n" + "x" * 5000)
                found = self.problems()
        self.assertEqual(1, len(found), found)
        self.assertIn("cannot be read", found[0])

    def test_more_bytes_than_the_budget_stop_the_reading_and_say_so(self):
        with unittest.mock.patch.object(doccheck, "MAX_BYTES", 500):
            for n in range(5):
                self.put("docs/specs/s%d.md" % n, SPEC + "x" * 300)
            found = self.problems()
        self.assertEqual(4, len(found), found)
        self.assertIn("only the start was examined", found[0])
        self.assertTrue(all("not looked at" in line for line in found[1:]), found)

    def test_more_documents_than_the_bound_stop_the_reading_and_say_so(self):
        with unittest.mock.patch.object(doccheck, "MAX_FILES", 3):
            for n in range(5):
                self.put("docs/specs/s%d.md" % n, SPEC)
            found = self.problems()
        self.assertEqual(2, len(found), found)
        self.assertTrue(all("not looked at" in line for line in found))

    def test_the_findings_reported_are_bounded(self):
        for n in range(doccheck.MAX_REPORTED + 50):
            self.put("docs/specs/Bad%d.md" % n, SPEC)
        found = self.problems()
        self.assertEqual(doccheck.MAX_REPORTED + 1, len(found))
        self.assertEqual("more document problems are not listed", found[-1])

    def test_names_that_differ_only_in_case_are_reported_as_a_collision(self):
        class Fake:
            BAD_NAME = "badname"

            def list_dir(self, rel, lenient=False):
                return [("Power.md", "file"), ("power.md", "file")] if rel == "docs/specs" else None

            def read_file(self, rel):
                return unittest.mock.Mock(data=SPEC.encode())

        problems = []
        doccheck._area(Fake(), "docs/specs", "spec", doccheck.SPEC_STATUSES, [10, 10 ** 6],
                       problems)
        self.assertTrue(any("collides with" in line for line in problems), problems)

    def test_nothing_is_written_or_changed(self):
        self.put("docs/specs/Bad.md", SPEC)
        self.put("docs/roadmaps/first.md", ROADMAP)
        def snapshot():
            found = {}
            for base, dirs, files in os.walk(self.root):
                for name in files + dirs:
                    full = os.path.join(base, name)
                    data = b""
                    if os.path.isfile(full):
                        with open(full, "rb") as handle:
                            data = handle.read()
                    found[full] = (data, os.lstat(full).st_mtime_ns)
            return found

        before = snapshot()
        self.problems()
        self.assertEqual(before, snapshot())


class Command(Base):
    """`wb check` end to end, in a real git repository, without attaching a harness."""

    def setUp(self):
        super().setUp()
        os.chmod(self.store, 0o700)
        self.git("init", "-q", "--template=")

    def git(self, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                               "-c", "commit.gpgsign=false"] + list(args), cwd=self.root, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)

    def check(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.root], out, err, store_root=self.store,
                        home=os.path.join(self.base, "nohome"))
        return code, out.getvalue(), err.getvalue()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "x")

    def test_a_clean_project_with_the_module_has_no_problems(self):
        self.install()
        self.put("docs/specs/power-supply.md", SPEC)
        self.put("docs/roadmaps/first-release.md", ROADMAP)
        self.commit()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertTrue(out.endswith("check found no problems\n"), out)

    def test_a_wrong_name_and_a_duplicate_candidate_are_problems_with_exit_one(self):
        self.install()
        self.put("docs/specs/Power.md", SPEC)
        self.put("docs/roadmaps/first-release.md", ROADMAP + "\n### pick-a-board\n")
        self.commit()
        code, out, err = self.check()
        self.assertEqual(1, code)
        lines = [line for line in err.splitlines() if line.startswith("problem: ")]
        self.assertEqual(2, len(lines), err)
        self.assertTrue(any("docs/specs/Power.md: a spec is named" in line for line in lines))
        self.assertTrue(any("repeats" in line for line in lines))
        self.assertIn("check found 2 problems", out)

    def test_a_project_without_the_module_is_not_reported(self):
        self.put(".workbench/manifest.json", manifest.serialize(installed_document(module="other")))
        self.put("docs/specs/Power.md", "no status\n")
        self.commit()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)

    def test_a_hostile_heading_never_reaches_the_terminal_raw(self):
        self.install()
        self.put("docs/roadmaps/first-release.md",
                 "# R\n\nStatus: Active\n\n## Candidates\n\n### \x1b]0;pwned\x07\n")
        self.commit()
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", out + err)
        self.assertNotIn("\x07", out + err)

    def test_the_git_index_is_not_changed(self):
        self.install()
        self.put("docs/specs/Power.md", SPEC)
        self.commit()
        path = os.path.join(self.root, ".git", "index")
        with open(path, "rb") as handle:
            before = handle.read()
        self.check()
        with open(path, "rb") as handle:
            self.assertEqual(before, handle.read())


if __name__ == "__main__":
    unittest.main()
