"""`safe-git describe commit`, the fixes of the security pass (plan `2026-10-25-safe-git-describe`, increment F;
`docs/specs/safe-git.md`, "Errors" and "Facts of `describe commit`").

Each test is the regression of one finding: an attribute that converts a file on `git add`, a filter from the owner's
own configuration, the cost of a diff, a side that is not UTF-8, a missing HEAD object, the `check-ignore` shape and a
lone surrogate in the printed object. Real repositories, built on the fixtures of the `commit` tests."""

import difflib
import json
import os
import random
import time
import unittest
import unittest.mock

import test_safegit_commit as C
import test_safegit_describe_changes as DCH
import test_safegit_describe_commit as DC
from support_git import git, needs_git

H = C.H


@needs_git
class Attributes(DC.Describe):
    def setUp(self):
        super().setUp()
        self.write("a.txt", "two\n")

    def refuse_with_attributes(self, text, *paths, where=".gitattributes"):
        self.write(where, text)
        for path in paths:
            if not os.path.exists(os.path.join(self.repo, path)):
                self.write(path, "x\n")
        built = self.refused("path_converts_on_add", self.argv("S", *(paths or ("a.txt",))))
        return built

    def test_a_working_tree_encoding_attribute_is_refused_and_the_real_command_refuses_too(self):
        self.write("cfg.enc", "token = +AGc-hp_AAAAAAAAAAAAAAAAAAAA\n")
        self.refuse_with_attributes("*.enc working-tree-encoding=UTF-7\n", "cfg.enc")

    def test_a_filter_attribute_is_refused_whether_or_not_the_filter_is_configured(self):
        self.refuse_with_attributes("a.txt filter=nothing\n", "a.txt")

    def test_an_ident_attribute_is_refused(self):
        self.refuse_with_attributes("a.txt ident\n", "a.txt")

    def test_an_attribute_in_the_info_file_of_the_repository_is_refused_too(self):
        os.makedirs(os.path.join(self.repo, ".git", "info"), exist_ok=True)
        self.refuse_with_attributes("a.txt ident\n", "a.txt", where=".git/info/attributes")

    def test_an_attribute_in_the_directory_of_the_path_is_refused(self):
        self.write("sub/c.txt", "x\n")
        self.write("sub/.gitattributes", "c.txt filter=f\n")
        self.refused("path_converts_on_add", self.argv("S", "sub/c.txt"))

    def test_only_the_named_paths_are_asked_about(self):
        self.write(".gitattributes", "other.txt filter=f\n")
        built = self.describe(self.argv("S", "a.txt"))
        self.assertTrue(built["ok"], built)

    def test_an_attribute_that_is_unset_or_unspecified_is_no_refusal(self):
        self.write(".gitattributes", "a.txt -filter -ident -working-tree-encoding\n")
        self.assertTrue(self.describe(self.argv("S", "a.txt"))["ok"])

    def test_text_and_eol_are_not_refused_and_stay_a_documented_limit(self):
        self.write(".gitattributes", "*.txt text eol=crlf\n")
        self.assertTrue(self.describe(self.argv("S", "a.txt"))["ok"])

    def test_a_filter_of_the_owners_own_configuration_is_not_started_by_describe(self):
        marker = os.path.join(self.scratch, "started")
        with open(os.path.join(self.home, ".gitconfig"), "a") as handle:
            handle.write("[filter \"f\"]\n\tclean = touch '%s'; cat\n\tprocess = touch '%s'\n" % (marker, marker))
        self.write(".gitattributes", "a.txt filter=f\n")
        self.refused("path_converts_on_add", self.argv("S", "a.txt"))
        self.assertFalse(os.path.exists(marker))

    def test_an_empty_filter_value_and_a_macro_that_sets_a_filter_are_refused(self):
        self.refuse_with_attributes("a.txt filter=\n", "a.txt")

    def test_a_macro_that_sets_a_converting_attribute_is_refused(self):
        self.refuse_with_attributes("[attr]conv ident\na.txt conv\n", "a.txt")

    def test_one_converted_path_among_several_is_enough(self):
        self.write("b.txt", "b\n")
        self.write("c.txt", "c\n")
        self.refuse_with_attributes("c.txt ident\n", "a.txt", "b.txt", "c.txt")

    def test_check_attr_output_that_is_not_one_answer_for_each_path_and_attribute_is_unreadable(self):
        real = H.run
        def triple(attribute):
            return "a.txt\0%s\0unspecified\0" % attribute

        right = triple("filter") + triple("ident") + triple("working-tree-encoding")
        for text in ("", triple("filter"), triple("filter") + triple("ident"),
                     triple("ident") + triple("filter") + triple("working-tree-encoding"), right[:-1]):
            def short(argv, cwd, **kwargs):
                if argv[1] == "check-attr":
                    return unittest.mock.Mock(returncode=0, stdout=text)
                return real(argv, cwd, **kwargs)
            with self.subTest(text=text[:40]), unittest.mock.patch.object(H, "run", short):
                self.assertEqual(["repository_unreadable"], self.codes(self.describe(self.argv("S", "a.txt"))))

    def test_the_refusal_names_the_path_and_the_attribute(self):
        self.write(".gitattributes", "a.txt ident\n")
        message = self.describe(self.argv("S", "a.txt"))["errors"][0]["message"]
        self.assertIn("a.txt", message)
        self.assertIn("ident", message)

    def test_the_attribute_check_runs_after_the_program_check_and_before_the_whitespace_check(self):
        self.write("a.txt", "two \n")
        self.write(".gitattributes", "a.txt ident\n")
        self.assertEqual(["path_converts_on_add"], self.codes(self.describe(self.argv("S", "a.txt"))))


@needs_git
class Shapes(unittest.TestCase):
    def ok(self, *argv):
        return H.git_shape_ok(["git"] + list(argv))

    def test_check_attr_is_allowed_in_one_form_only(self):
        self.assertTrue(self.ok("check-attr", "-z", "filter", "ident", "working-tree-encoding", "--", "a.txt", "d/b"))
        for argv in (["check-attr"], ["check-attr", "-z", "filter", "ident", "working-tree-encoding"],
                     ["check-attr", "-z", "filter", "ident", "working-tree-encoding", "--"],
                     ["check-attr", "-z", "-a", "--", "a"], ["check-attr", "-z", "--all", "--", "a"],
                     ["check-attr", "-z", "filter", "--", "a"],
                     ["check-attr", "-z", "text", "ident", "working-tree-encoding", "--", "a"],
                     ["check-attr", "-z", "--cached", "filter", "ident", "working-tree-encoding", "--", "a"],
                     ["check-attr", "-z", "--stdin", "filter", "ident", "working-tree-encoding", "--", "a"],
                     ["check-attr", "filter", "ident", "working-tree-encoding", "--", "a"],
                     ["check-attr", "-z", "filter", "ident", "working-tree-encoding", "--", "../a"],
                     ["check-attr", "-z", "filter", "ident", "working-tree-encoding", "--", "/a"]):
            with self.subTest(argv=argv):
                self.assertFalse(self.ok(*argv))

    def test_check_ignore_refuses_a_pathspec_a_glob_a_backslash_and_an_option(self):
        for target in (":(top)x", ":x", "*.log", "a?", "a[b]", "a\\b", "-x"):
            with self.subTest(target=target):
                self.assertFalse(self.ok("check-ignore", "-q", "--", target))
        for target in ("a.txt", "dir/a b", "dir/.hidden", "é", "log-10:00.txt"):
            with self.subTest(target=target):
                self.assertTrue(self.ok("check-ignore", "-q", "--", target))


class Diffs(DCH.Changes):
    def big(self, name, pattern, count):
        self.write(name, "".join(pattern(number) for number in range(count)))

    def test_a_long_file_with_one_changed_line_is_diffed_in_a_short_time(self):
        lines = ["%02d\n" % (number % 100) for number in range(87000)]
        self.write("long.txt", "".join(lines))
        git(self.repo, "add", "long.txt")
        git(self.repo, "commit", "-q", "-m", "long")
        self.first = self.head()
        lines[40000] = "zz\n"
        self.write("long.txt", "".join(lines))
        started = time.monotonic()
        facts = self.facts("long.txt")
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(["long.txt"], facts["modified_paths"])
        around = tuple(number % 100 for number in (39997, 39998, 39999, 40000, 40001, 40002, 40003))
        self.assertEqual("--- HEAD/long.txt\n+++ work/long.txt\n@@ -39998,7 +39998,7 @@\n %02d\n %02d\n %02d\n-%02d\n"
                         "+zz\n %02d\n %02d\n %02d\n" % around, facts["diff"])

    def test_a_change_at_the_first_and_the_last_line_keeps_the_hunks_of_the_whole_file(self):
        self.write("a.txt", "".join("l%d\n" % number for number in range(30)))
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "thirty")
        self.first = self.head()
        self.write("a.txt", "".join(("first\n" if number == 0 else "last\n" if number == 29 else "l%d\n" % number)
                                    for number in range(30)))
        diff = self.facts("a.txt")["diff"]
        self.assertEqual(["--- HEAD/a.txt", "+++ work/a.txt", "@@ -1,4 +1,4 @@", "-l0", "+first", " l1", " l2", " l3",
                          "@@ -27,4 +27,4 @@", " l26", " l27", " l28", "-l29", "+last", ""], diff.split("\n"))

    def test_a_whole_file_rewrite_too_large_to_compare_is_left_out_not_waited_for(self):
        first = "".join("%02d\n" % (number % 100) for number in range(87000))
        second = "".join("%02d\n" % ((number * 7 + number // 100) % 100) for number in range(87000))
        self.write("long.txt", first)
        git(self.repo, "add", "long.txt")
        git(self.repo, "commit", "-q", "-m", "long")
        self.first = self.head()
        self.write("long.txt", second)
        started = time.monotonic()
        built = self.describe(self.argv("S", "long.txt"))
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertTrue(built["ok"], built)
        self.assertEqual((["long.txt"], True, ["diff"]), (built["facts"]["modified_paths"], built["truncated"],
                                                         built["facts"]["omitted"]))
        self.assertNotIn("diff", built["facts"])

    def test_the_diff_work_has_a_budget_and_the_diff_is_left_out_when_it_is_spent(self):
        self.write("a.txt", "two\n")
        with unittest.mock.patch.object(H, "DIFF_BUDGET", 0.0):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual((True, ["a.txt"], ["diff"]), (built["truncated"], built["facts"]["modified_paths"],
                                                      built["facts"]["omitted"]))


class Hunks(unittest.TestCase):
    def test_the_diff_made_here_is_the_diff_difflib_makes_where_the_lines_are_distinct(self):
        generator = random.Random(7)
        for trial in range(300):
            pool = ["line %d\n" % number for number in range(40)]
            first = generator.sample(pool, generator.randrange(0, 30))
            second = list(first)
            for _ in range(generator.randrange(0, 6)):
                where = generator.randrange(0, len(second) + 1)
                if second and generator.random() < 0.5:
                    del second[min(where, len(second) - 1)]
                else:
                    second.insert(where, "new %d\n" % generator.randrange(1000))
            old = "".join(first).encode()
            new = "".join(second).encode()
            if generator.random() < 0.2:
                new = new.rstrip(b"\n")
            expected = "".join(difflib.unified_diff(H._lines(old), H._lines(new), "HEAD/p", "work/p"))
            with self.subTest(trial=trial):
                self.assertEqual(expected, H._text_diff("p", old, new))

    def test_an_empty_side_and_a_missing_final_newline_are_written_as_difflib_writes_them(self):
        self.assertEqual("--- HEAD/p\n+++ work/p\n@@ -0,0 +1 @@\n+a\n\\ No newline at end of file\n",
                         H._text_diff("p", b"", b"a"))
        self.assertEqual("--- HEAD/p\n+++ work/p\n@@ -1 +0,0 @@\n-a\n", H._text_diff("p", b"a\n", b""))

    def test_more_lines_than_the_limit_that_differ_give_no_diff(self):
        first = "".join("a%d\n" % number for number in range(H.MAX_MIDDLE + 1)).encode()
        second = "".join("b%d\n" % number for number in range(H.MAX_MIDDLE + 1)).encode()
        self.assertIsNone(H._text_diff("p", first, second))
        self.assertIsNotNone(H._text_diff("p", first, first + b"x\n"))


class NotText(DCH.Changes):
    def test_a_side_that_is_not_utf8_is_listed_as_binary_and_its_diff_is_withheld(self):
        self.write("n.txt", b"caf\xe9\n")
        facts = self.facts("n.txt")
        self.assertEqual((["n.txt"], ["n.txt"], ""), (facts["new_paths"], facts["binary_paths"], facts["diff"]))

    def test_a_literal_escape_in_head_and_a_raw_byte_in_the_work_tree_are_not_an_empty_diff(self):
        self.write("a.txt", "caf\\xe9\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "literal")
        self.first = self.head()
        self.write("a.txt", b"caf\xe9\n")
        facts = self.facts("a.txt")
        self.assertEqual((["a.txt"], ["a.txt"], ""), (facts["modified_paths"], facts["binary_paths"], facts["diff"]))

    def test_a_head_side_that_is_not_utf8_makes_the_path_binary_too(self):
        self.write("a.txt", b"\xff\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "latin")
        self.first = self.head()
        self.write("a.txt", "plain\n")
        self.assertEqual(["a.txt"], self.facts("a.txt")["binary_paths"])


class MissingObject(DCH.Changes):
    def test_a_head_blob_that_cannot_be_read_is_an_unreadable_repository_and_not_a_new_file(self):
        blob = git(self.repo, "rev-parse", "HEAD:u.txt").stdout.strip()
        loose = os.path.join(self.repo, ".git", "objects", blob[:2], blob[2:])
        os.chmod(loose, 0o644)
        os.unlink(loose)
        built = self.describe(self.argv("S", "u.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built), built)
        self.assertEqual([], built["facts"]["new_paths"])

    def test_an_intent_to_add_path_is_still_new(self):
        self.write("n.txt", "new\n")
        git(self.repo, "add", "-N", "n.txt")
        self.assertEqual(["n.txt"], self.facts("n.txt")["new_paths"])


class Surrogate(unittest.TestCase):
    def test_a_lone_surrogate_is_printed_as_text_a_strict_reader_accepts(self):
        built = H.build_description("commit", [("subject_invalid", "bad \udcff")],
                                    [("subject", "a\udcffb"), ("trailers", ["K: \udc80"])])
        line = H.render_description(built)
        self.assertEqual(1, line.count("\n"))
        loaded = json.loads(line)
        for value in (loaded["facts"]["subject"], loaded["facts"]["trailers"][0], loaded["errors"][0]["message"]):
            self.assertFalse(any(0xD800 <= ord(char) <= 0xDFFF for char in value), value)
        self.assertEqual("a\\udcffb", loaded["facts"]["subject"])
        self.assertEqual("K: \\udc80", loaded["facts"]["trailers"][0])


if __name__ == "__main__":
    unittest.main()
