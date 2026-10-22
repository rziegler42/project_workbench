"""The `code-work` helper: its bounded reader and the `check` subcommand.

Plan `2026-10-21-code-work-plans`, increment B. The helper is one file that the launcher runs from a
private copy, so it is loaded here by its path and run in process, and once as a program from a
directory that holds files named like standard modules."""

import ast
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import support_helpers, support_install

ROOT = support_install.ROOT
HELPER = os.path.join(ROOT, "packages", "workbench", "code-work", "helper", "code-work")


helper = support_helpers.load("code-work")
doccheck = support_helpers.load("doccheck")

GOOD = """# A plan

Status: {status}
Created: 2026-10-21
Candidate: {candidate}
Specs: code-work

## Goal

Something.

## Increments

{body}"""


def increments(*labels):
    return "".join("### Increment %s — Title\n\nText.\n\n" % label for label in labels)


def plan(status="Approved", candidate="workbench-v1#thing", body=None, labels=("A", "B")):
    return GOOD.format(status=status, candidate=candidate,
                       body=increments(*labels) if body is None else body)


class Project(unittest.TestCase):
    """A directory shaped like an installed project, with its plans written by hand."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.place = os.path.realpath(holder.name)
        os.mkdir(os.path.join(self.place, ".git"))
        with open(os.path.join(self.place, ".git", "index"), "wb") as handle:
            handle.write(b"DIRC fake index\x00\xff")
        os.mkdir(os.path.join(self.place, ".workbench"))
        with open(os.path.join(self.place, ".workbench", "manifest.json"), "wb") as handle:
            handle.write(b"{}\n")
        os.makedirs(os.path.join(self.place, "docs", "plans"))

    def write(self, rel, data):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    def plan(self, name="2026-10-21-thing.md", text=None, **kwargs):
        self.write("docs/plans/" + name, plan(**kwargs) if text is None else text)

    def check(self, *args, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = helper.main(list(args) or ["check"], out, err, cwd or self.place)
        return code, out.getvalue(), err.getvalue()

    def problems(self, **kwargs):
        code, out, err = self.check(**kwargs)
        lines = [l for l in err.splitlines() if l.startswith("problem: ")]
        self.assertEqual(1 if lines else 0, code, err)
        return lines

    def snapshot(self):
        found = {}
        for base, dirs, files in os.walk(self.place):
            for name in dirs + files:
                full = os.path.join(base, name)
                info = os.lstat(full)
                found[os.path.relpath(full, self.place)] = (info.st_mode, info.st_size,
                                                            info.st_mtime_ns)
        return found

    def assertProblem(self, text, lines):
        self.assertTrue(any(text in line for line in lines), (text, lines))


class Source(unittest.TestCase):
    def test_the_helper_imports_only_the_standard_library_and_the_kit(self):
        with open(HELPER, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertEqual({"datetime", "html", "io", "itertools", "os", "re", "stat", "subprocess", "sys",
                          "wbkit"}, names)
        self.assertEqual({"wbkit"}, names - set(sys.stdlib_module_names))

    def test_the_only_import_of_subprocess_is_below_the_read_only_part(self):
        read_only, marker, below = self.split_text()
        self.assertNotIn("subprocess", read_only)
        self.assertIn("import subprocess", below)

    @staticmethod
    def split_text():
        """The helper's text above and below the line that begins the code that runs git."""
        with open(HELPER, encoding="utf-8") as handle:
            text = handle.read()
        marker = "# --- running git "
        above, found, below = text.partition(marker)
        assert found, "the helper has no line that begins the git code"
        return above, found, below

    def test_the_read_only_part_opens_nothing_for_writing_and_runs_no_program(self):
        text, _, _ = self.split_text()
        for word in ("subprocess", "os.system", "os.exec", "os.popen", "O_WRONLY", "O_RDWR",
                     "O_CREAT", "O_APPEND", "os.write", "os.rename", "os.unlink", "os.remove",
                     "os.mkdir", "os.rmdir", "os.chmod", "os.utime", "os.symlink", "os.link", "O_TRUNC",
                     "open(\"", "eval(", "exec(", "__import__"):
            self.assertNotIn(word, text, word)


class Plans(Project):
    def test_a_good_plan_passes_and_the_report_says_so(self):
        self.plan()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err))
        self.assertEqual("checked 1 plan\ncheck found no problems\n", out)

    def test_a_project_with_no_plans_folder_or_no_plans_reports_nothing_wrong(self):
        self.assertEqual((0, "checked 0 plans\ncheck found no problems\n", ""), self.check())
        shutil.rmtree(os.path.join(self.place, "docs"))
        self.assertEqual((0, "checked 0 plans\ncheck found no problems\n", ""), self.check())

    def test_the_readme_and_folders_and_other_files_are_not_plans(self):
        self.write("docs/plans/README.md", "# Plans\n")
        self.write("docs/plans/notes.txt", "x")
        os.mkdir(os.path.join(self.place, "docs", "plans", "archive.md"))
        self.write("docs/plans/archive/old.md", "not a plan")
        self.assertEqual("checked 0 plans\ncheck found no problems\n", self.check()[1])

    def test_it_changes_nothing(self):
        self.plan()
        self.plan("2026-10-21-bad.md", status="Wibble")
        before = self.snapshot()
        index = os.path.join(self.place, ".git", "index")
        with open(index, "rb") as handle:
            bytes_before = handle.read()
        self.check()
        self.assertEqual(before, self.snapshot())
        with open(index, "rb") as handle:
            self.assertEqual(bytes_before, handle.read())

    def test_the_candidate_line_is_exactly_one(self):
        self.plan(text=plan().replace("Candidate: workbench-v1#thing\n", ""))
        self.assertProblem("has no Candidate line", self.problems())
        self.plan(text=plan().replace("Specs:", "Candidate: workbench-v1#other\nSpecs:"))
        self.assertProblem("has 2 Candidate lines", self.problems())

    def test_candidate_none_needs_a_reason_and_a_reference_needs_both_parts(self):
        self.plan(candidate="none")
        self.assertProblem("`Candidate: none` with no reason", self.problems())
        self.plan(candidate="none (a follow-up to another plan)")
        self.assertEqual([], self.problems())
        self.plan(candidate="none — a follow-up")
        self.assertEqual([], self.problems())
        self.plan(candidate="none ()")
        self.assertProblem("with no reason", self.problems())
        for bad in ("workbench-v1", "workbench-v1#", "#thing", "Workbench#Thing", "a#b#c",
                    "a#b c", "nonexistent", "nonesuch", "none\u200b"):
            self.plan(candidate=bad)
            found = self.problems()
            self.assertTrue(any("has the Candidate" in l or "no reason" in l for l in found), bad)
        self.plan(candidate="none ?")
        self.assertProblem("with no reason", self.problems())

    def test_the_other_header_lines_are_required(self):
        for field, text in (("Status", "has no Status line"), ("Created", "has no Created line"),
                            ("Specs", "has no Specs line")):
            lines = [l for l in plan().splitlines(True) if not l.startswith(field + ":")]
            self.plan(text="".join(lines))
            self.assertProblem(text, self.problems())
        self.plan(text=plan().replace("# A plan\n", "A plan\n"))
        self.assertProblem("has no title", self.problems())

    def test_a_repeated_status_or_created_or_specs_line_is_a_problem(self):
        for field in ("Status: Approved", "Created: 2026-10-21", "Specs: code-work"):
            self.plan(text=plan().replace(field + "\n", field + "\n" + field + "\n"))
            self.assertProblem("lines near the top; there is one", self.problems())

    def test_the_status_is_one_of_the_five(self):
        for status in ("Proposed", "Approved", "In Progress", "Completed", "Superseded",
                       "Superseded by 2026-10-22-next", "Completed. Verified"):
            self.plan(status=status)
            self.assertEqual([], self.problems(), status)
        for status in ("Wibble", "", "Done", "In  Progress", "Progress", "Proposedly",
                       "Draft", "approved"):
            self.plan(status=status)
            self.assertProblem("a plan is Proposed, Approved, In Progress, Completed or Superseded",
                               self.problems())

    def test_created_is_a_real_date_and_matches_the_name(self):
        self.plan(text=plan().replace("Created: 2026-10-21", "Created: 2026-02-30"))
        self.assertProblem("not a date", self.problems())
        self.plan(text=plan().replace("Created: 2026-10-21", "Created: 21 October"))
        self.assertProblem("not a date", self.problems())
        self.plan(text=plan().replace("Created: 2026-10-21", "Created: 2026-10-20"))
        self.assertProblem("differs from the date in its name", self.problems())

    def test_the_name_is_a_dated_kebab_case_topic(self):
        for name in ("thing.md", "2026-10-21.md", "2026-10-21-Thing.md", "2026-10-21-a_b.md",
                     "2026-13-21-thing.md", "2026-10-21-thing.MD.md", "2026-10-21-a..b.md",
                     "2026-10-21--thing.md", "2026-10-21-thing-.md"):
            self.plan(name)
            lines = self.problems()
            self.assertTrue(any("a plan is named YYYY-MM-DD-<topic>.md" in l
                                or "is not a date" in l for l in lines), (name, lines))
            os.remove(os.path.join(self.place, "docs", "plans", name))

    def test_a_long_valid_name_is_not_cut_before_it_is_judged(self):
        name = "2026-10-21-" + "a" * 200 + ".md"
        self.plan(name)
        self.assertEqual([], self.problems())

    def test_two_plans_on_one_day_with_different_topics_do_not_collide(self):
        self.plan("2026-10-21-one.md")
        self.plan("2026-10-21-two.md")
        self.assertEqual("checked 2 plans\ncheck found no problems\n", self.check()[1])

    def test_a_case_variant_of_a_name_is_reported_where_the_filesystem_keeps_both(self):
        self.plan("2026-10-21-thing.md")
        self.plan("2026-10-21-Thing.md")
        if len(os.listdir(os.path.join(self.place, "docs", "plans"))) != 2:
            self.skipTest("the filesystem does not tell letter case apart")
        self.assertProblem("differs only in letter case", self.problems())


class Increments(Project):
    def test_the_heading_form_is_exact(self):
        self.plan(labels=("A",))
        self.assertEqual([], self.problems())
        for line in ("### Increment A - Title", "### Increment A: Title", "### Increment A",
                     "### Increment a — Title", "### Increment  A — Title",
                     "### Increment Å — Title", "### Increment A —", "### Increment 1 — Title",
                     "###  Increment A — Title", "### Increment AAAA — Title",
                     "### Increment A-a — Title"):
            self.plan(body=line + "\n\nText.\n")
            lines = self.problems()
            self.assertProblem("is not of the form", lines)

    def test_a_heading_close_to_the_form_is_a_problem_not_silence(self):
        for line in ("### increment A — T", "### INCREMENT A — T", "#### Increment A — T",
                     "## Increment A — T", "# Increment A — T", "###### Increment A — T"):
            self.plan(body=increments("A") + line + "\n\nText.\n")
            self.assertProblem("is not of the form", self.problems())
        self.plan(body="### Increment A — T\n\n    ### Increment B — T\n\n")
        self.assertEqual([], self.problems())

    def test_labels_run_a_to_z_then_aa_and_may_be_inserted_with_a_hyphen(self):
        letters = [chr(c) for c in range(65, 91)]
        self.plan(labels=letters)
        self.assertEqual([], self.problems())
        self.plan(labels=("A", "B", "B-A", "B-A-A", "B-B", "C", "Z", "AA", "AB"))
        self.assertEqual([], self.problems())

    def test_a_repeated_or_out_of_order_label_is_a_problem(self):
        self.plan(labels=("A", "B", "B"))
        self.assertProblem("repeats an earlier one", self.problems())
        self.plan(labels=("A", "C", "B"))
        self.assertProblem("comes after C", self.problems())
        self.plan(labels=("B-A", "B"))
        self.assertProblem("comes after B-A", self.problems())
        self.plan(labels=("AA", "Z"))
        self.assertProblem("comes after AA", self.problems())

    def test_more_than_fifteen_is_a_warning_and_more_than_twenty_six_a_problem(self):
        self.plan(labels=[chr(c) for c in range(65, 65 + 16)])
        code, out, err = self.check()
        self.assertEqual(0, code)
        self.assertIn("warning: ", err)
        self.assertIn("16 increments", err)
        self.assertNotIn("problem:", err)
        letters = [chr(c) for c in range(65, 91)] + ["AA"]
        self.plan(labels=letters)
        self.assertProblem("has 27 increments; more than 26 is two plans", self.problems())

    def test_a_thousand_headings_are_cut_and_say_what_was_not_looked_at(self):
        def label(n):
            out = ""
            while n:
                n, rest = divmod(n - 1, 26)
                out = chr(65 + rest) + out
            return out
        self.plan(body=increments(*[label(n) for n in range(1, 1202)]))
        lines = self.problems()
        self.assertProblem("more than 1000 increments; the rest were not looked at", lines)
        self.assertTrue(len(lines) <= helper.MAX_REPORTED + 1)

    def test_the_heading_form_elsewhere_is_text_and_the_section_is_required(self):
        self.plan(body=increments("A") + "\n## Result\n\n" + increments("A", "A", "Z"))
        self.assertEqual([], self.problems())
        self.plan(text=plan().replace("## Increments", "## Steps"))
        self.assertProblem("has no `## Increments` section, so its 2 increment headings were not "
                           "checked", self.problems())
        self.plan(text=plan(labels=()).replace("## Increments", "## Steps"))
        self.assertProblem("has no `## Increments` section", self.problems())


class Hostile(Project):
    def test_a_candidate_line_or_heading_in_a_fence_or_quote_does_not_count(self):
        body = ("```\nCandidate: workbench-v1#fenced\n### Increment A — one\n```\n"
                "> Candidate: workbench-v1#quoted\n> ### Increment A — two\n\n"
                "~~~\nStatus: Wibble\n~~~\n" + increments("A"))
        self.plan(body=body)
        self.assertEqual([], self.problems())

    def test_a_field_in_a_fence_or_quote_or_comment_in_the_header_does_not_count(self):
        for hidden in ("```\n{}\n```\n", "> {}\n", "<!--\n{}\n-->\n", "<!-- start\n{}\n  end -->\n"):
            for field in ("Candidate: workbench-v1#thing", "Status: Approved", "Created: 2026-10-21",
                          "Specs: code-work"):
                name = field.split(":")[0]
                lines = [l for l in plan().splitlines(True) if not l.startswith(name + ":")]
                text = "".join(lines).replace("## Goal", hidden.format(field) + "\n## Goal")
                self.plan(text=text)
                self.assertProblem("has no %s line" % name, self.problems())
        self.plan(text=plan().replace("Specs:", "```\nCandidate: workbench-v1#two\n```\nSpecs:"))
        self.assertEqual([], self.problems())

    def test_a_hidden_increment_heading_or_section_does_not_count(self):
        self.plan(body="<!--\n### Increment A — hidden\n-->\n" + increments("A"))
        self.assertEqual([], self.problems())
        self.plan(text=plan().replace("## Increments", "<!--\n## Increments\n-->\n## Steps"))
        self.assertProblem("has no `## Increments` section", self.problems())

    def test_a_comment_that_ends_on_its_line_hides_nothing_after_it(self):
        self.plan(text=plan().replace("Specs: code-work\n", "<!-- note --> Specs: code-work\n"))
        self.assertProblem("has no Specs line", self.problems())
        self.plan(text=plan().replace("Specs: code-work\n", "Specs: code-work <!-- note -->\n"))
        self.assertEqual([], self.problems())
        self.plan(text=plan().replace("Specs: code-work\n", "<!-- note -->\nSpecs: code-work\n"))
        self.assertEqual([], self.problems())

    def test_an_unclosed_comment_is_a_problem(self):
        self.plan(body="<!--\n" + increments("A"))
        self.assertProblem("an HTML comment is never closed", self.problems())

    def test_a_field_after_the_first_section_does_not_count(self):
        self.plan(text=plan().replace("Specs: code-work\n", "") + "\nSpecs: later\n")
        self.assertProblem("has no Specs line", self.problems())

    def test_an_unclosed_fence_is_a_problem(self):
        self.plan(body="```\n" + increments("A"))
        self.assertProblem("a code fence is never closed", self.problems())

    def test_escapes_and_lookalikes_are_not_shown_raw(self):
        self.plan(status="\x1b[31mred\x1b[0m у‮")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", err + out)
        self.assertNotIn("у", err + out)
        self.assertNotIn("‮", err + out)
        self.assertIn("\\x1b", err)

    def test_a_name_with_a_control_character_is_shown_escaped(self):
        try:
            self.plan("2026-10-21-a\x1b[2Jb.md")
        except OSError:
            self.skipTest("the filesystem refuses the name")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", err)

    def test_a_name_that_is_not_utf8_is_not_usable(self):
        full = os.path.join(os.fsencode(self.place), b"docs", b"plans", b"2026-10-21-\xff.md")
        try:
            with open(full, "wb") as handle:
                handle.write(b"x")
        except OSError:
            self.skipTest("the filesystem refuses the name")
        self.assertProblem("the name is not usable", self.problems())

    def test_a_link_in_the_place_of_a_plan_is_not_read(self):
        outside = os.path.join(self.place, "outside.md")
        with open(outside, "w") as handle:
            handle.write(plan())
        os.symlink(outside, os.path.join(self.place, "docs", "plans", "2026-10-21-link.md"))
        lines = self.problems()
        self.assertProblem("is not a regular file", lines)

    def test_a_link_at_the_plans_folder_is_not_followed(self):
        real = os.path.join(self.place, "elsewhere")
        os.mkdir(real)
        with open(os.path.join(real, "2026-10-21-thing.md"), "w") as handle:
            handle.write(plan())
        shutil.rmtree(os.path.join(self.place, "docs", "plans"))
        os.symlink(real, os.path.join(self.place, "docs", "plans"))
        self.assertProblem("docs/plans: cannot be listed", self.problems())

    def test_a_link_at_docs_is_not_followed(self):
        real = os.path.join(self.place, "elsewhere")
        os.makedirs(os.path.join(real, "plans"))
        shutil.rmtree(os.path.join(self.place, "docs"))
        os.symlink(real, os.path.join(self.place, "docs"))
        self.assertProblem("cannot be listed", self.problems())

    def test_a_fifo_in_the_place_of_a_plan_is_not_opened(self):
        os.mkfifo(os.path.join(self.place, "docs", "plans", "2026-10-21-pipe.md"))
        self.assertProblem("is not a regular file", self.problems())

    def test_a_plan_over_the_size_bound_says_only_the_start_was_examined(self):
        text = plan()
        self.plan(text=text + "x" * (helper.MAX_DOCUMENT + 10))
        self.assertProblem("only the start was examined", self.problems())

    def test_more_than_the_total_bytes_leaves_the_rest_unexamined_and_says_so(self):
        for index in range(6):
            self.plan("2026-10-21-p%d.md" % index, text=plan() + "x" * (helper.MAX_DOCUMENT - 100))
        lines = self.problems()
        self.assertProblem("not looked at; more than", lines)

    def test_more_than_the_file_count_leaves_the_rest_unexamined_and_says_so(self):
        for index in range(helper.MAX_FILES + 5):
            self.plan("2026-10-21-p%05d.md" % index)
        lines = self.problems()
        self.assertProblem("not looked at; more than %d files" % helper.MAX_FILES, lines)
        self.assertTrue(len(lines) <= helper.MAX_REPORTED + 1)

    def test_findings_are_bounded(self):
        for index in range(300):
            self.plan("2026-10-21-p%03d.md" % index, status="Wibble")
        code, out, err = self.check()
        self.assertEqual(1, code)
        problems = [l for l in err.splitlines() if l.startswith("problem: ")]
        self.assertLessEqual(len(problems), helper.MAX_REPORTED + 2)
        self.assertIn("more plan problems are not listed", err)
        self.assertIn("stopped after %d problems; the plans after" % helper.MAX_REPORTED, err)
        self.assertRegex(out, r"check found \d{3} problems")

    def test_invalid_utf8_inside_a_plan_does_not_crash(self):
        self.plan(text=plan().encode() + b"\xff\xfe### Increment A \xe2\n")
        self.check()

    def test_a_very_long_line_and_many_blank_lines_cost_little(self):
        self.plan(text=plan() + "#" * 500000 + "\n" + "\n" * 200000)
        self.problems()


class Dispatch(Project):
    def test_it_finds_the_project_from_a_subdirectory(self):
        self.plan()
        sub = os.path.join(self.place, "docs", "plans")
        self.assertEqual(0, self.check(cwd=sub)[0])
        deep = os.path.join(self.place, "a", "b")
        os.makedirs(deep)
        self.assertEqual(0, self.check(cwd=deep)[0])

    def test_outside_a_project_it_refuses(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        code, out, err = self.check(cwd=os.path.realpath(holder.name))
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: this is not inside a workbench project"), err)

    def test_a_manifest_without_a_git_directory_is_not_a_project(self):
        shutil.rmtree(os.path.join(self.place, ".git"))
        self.assertEqual(1, self.check()[0])

    def test_a_git_directory_without_a_manifest_is_not_a_project(self):
        os.remove(os.path.join(self.place, ".workbench", "manifest.json"))
        self.assertEqual(1, self.check()[0])

    def test_a_workbench_directory_that_is_a_link_is_not_a_project(self):
        real = os.path.join(self.place, "elsewhere")
        os.mkdir(real)
        with open(os.path.join(real, "manifest.json"), "wb") as handle:
            handle.write(b"{}")
        shutil.rmtree(os.path.join(self.place, ".workbench"))
        os.symlink(real, os.path.join(self.place, ".workbench"))
        self.assertEqual(1, self.check()[0])

    def test_a_manifest_that_is_a_link_is_not_a_project(self):
        path = os.path.join(self.place, ".workbench", "manifest.json")
        os.remove(path)
        os.symlink(os.path.join(self.place, "docs"), path)
        self.assertEqual(1, self.check()[0])

    def test_arguments_other_than_a_known_subcommand_are_refused(self):
        for args in (["bogus"], ["check", "extra"], ["--help"], [], ["-"], ["check", "--"],
                     ["CHECK"], ["check\n"]):
            out, err = io.StringIO(), io.StringIO()
            code = helper.main(args, out, err, self.place)
            self.assertEqual((1, ""), (code, out.getvalue()), args)
            self.assertTrue(err.getvalue().startswith("refused: usage: code-work check"), args)

    def test_run_as_a_program_from_a_directory_of_lookalike_modules(self):
        """The working directory holds `json.py`, `os.py` and `re.py` that would fail if imported."""
        self.plan()
        for name in ("json", "os", "re", "io", "stat", "datetime", "itertools", "sys"):
            self.write("%s.py" % name, "raise SystemExit('imported from the working directory')\n")
        copy = tempfile.TemporaryDirectory()
        self.addCleanup(copy.cleanup)
        private = os.path.join(copy.name, "code-work")
        shutil.copyfile(HELPER, private)
        runner = os.path.join(ROOT, "workbench", "runner.py")
        result = subprocess.run([sys.executable, "-I", "-B", runner, "1", private, "check"], cwd=self.place,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual((0, ""), (result.returncode, result.stderr))
        self.assertEqual("checked 1 plan\ncheck found no problems\n", result.stdout)


class Agreement(Project):
    CORPUS = [
        "plain\n```\nin fence\n```\nafter\n",
        "~~~\nx\n```\nstill\n~~~\nout\n",
        "> quoted\n  > indented quote\nplain\n",
        "- ```\n  fenced list\n  ```\nnext\n",
        "```a`b\nnot a fence\n```\n",
        "````\n```\nshort\n````\nout\n",
        "1. ~~~\n   x\n   ~~~\nout\r\nmore\rlast\n",
        "```\nnever closed\n### Increment A — x\n",
        "a" * 5000 + "\n```\n" + "b" * 5000 + "\n```\n",
        "\x00\n> \n```  \n``` x\n```\n",
    ]

    def test_the_helper_and_the_installer_agree_on_fences_and_quotes(self):
        for text in self.CORPUS:
            self.assertEqual(list(doccheck._lines(text)), list(helper.lines_of(text)), repr(text))
            mine, theirs = {}, {}
            list(doccheck._lines(text, theirs))
            list(helper.lines_of(text, mine))
            self.assertEqual(theirs["open"], mine["open"], repr(text))


class Repository(Project):
    def test_this_repositorys_own_plans_pass(self):
        """The plans written so far follow the format, so the check cannot be stricter than the
        practice it was written from."""
        source = os.path.join(ROOT, "docs", "plans")
        for name in os.listdir(source):
            if name.endswith(".md") and name != "README.md":
                shutil.copyfile(os.path.join(source, name),
                                os.path.join(self.place, "docs", "plans", name))
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertNotIn("problem:", err)


if __name__ == "__main__":
    unittest.main()
