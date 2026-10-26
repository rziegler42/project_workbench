"""`safe-git describe commit`, the change lists and the diff (plan `2026-10-25-safe-git-describe`, increment E;
`docs/specs/safe-git.md`, "Facts of `describe commit`" and "Caps and their sources").

Real repositories, built on the fixtures of the `commit` tests. The lists and the diff are computed from the HEAD blob
and the work-tree file by the helper itself, with no git filter, text conversion or external diff, and the work-tree
file is opened without following a link. The refusals and the scalar facts are increment D."""

import json
import os
import unittest
import unittest.mock

import test_safegit_commit as C
import test_safegit_describe_commit as DC
import test_safegit_describe_remove as DR
from support_git import git, needs_git

H = C.H

LISTS = ("new_paths", "modified_paths", "deleted_paths", "unchanged_paths", "binary_paths", "not_regular_paths")


@needs_git
class Changes(DC.Describe):
    def setUp(self):
        super().setUp()
        self.write("d.txt", "gone\n")
        self.write("u.txt", "same\n")
        git(self.repo, "add", "d.txt", "u.txt")
        git(self.repo, "commit", "-q", "-m", "more")
        self.first = self.head()

    def facts(self, *paths, **more):
        built = self.describe(self.argv("S", *paths, **more))
        self.assertTrue(built["ok"], built)
        return built["facts"]

    def after_the_checks(self, action):
        """Run `action` once, after the last check of the paths (`git diff --check`) and before the reading of their
        contents: the race the facts have to survive."""
        real = H.run
        done = []

        def swapped(argv, cwd, **kwargs):
            result = real(argv, cwd, **kwargs)
            if argv[1] == "diff" and "--check" in argv and not done:
                done.append(True)
                action()
            return result

        return unittest.mock.patch.object(H, "run", swapped)


class Lists(Changes):
    def test_each_kind_of_change_is_in_its_own_list(self):
        self.write("a.txt", "two\n")
        self.write("n.txt", "new\n")
        os.unlink(os.path.join(self.repo, "d.txt"))
        facts = self.facts("a.txt", "n.txt", "d.txt", "u.txt")
        self.assertEqual(["n.txt"], facts["new_paths"])
        self.assertEqual(["a.txt"], facts["modified_paths"])
        self.assertEqual(["d.txt"], facts["deleted_paths"])
        self.assertEqual(["u.txt"], facts["unchanged_paths"])
        self.assertEqual([], facts["binary_paths"])
        self.assertEqual([], facts["not_regular_paths"])

    def test_the_facts_come_in_the_order_of_the_table(self):
        self.write("a.txt", "two\n")
        self.assertEqual(["head", "expected_head", "leave_other_staged", "path_count", "subject", "trailers", "body",
                          "attribution_allowed", "program_findings", "staged_paths", "requested_paths", "paths",
                          "new_paths", "modified_paths", "deleted_paths", "unchanged_paths", "binary_paths",
                          "not_regular_paths", "diff", "omitted"], list(self.facts("a.txt")))

    def test_a_list_keeps_the_order_the_paths_were_given_in(self):
        for name in ("z.txt", "b.txt", "m.txt"):
            self.write(name, "x\n")
        self.assertEqual(["z.txt", "b.txt", "m.txt"], self.facts("z.txt", "b.txt", "m.txt")["new_paths"])

    def test_every_named_path_is_in_exactly_one_of_the_four_lists(self):
        self.write("a.txt", "two\n")
        self.write("n.txt", "new\n")
        os.unlink(os.path.join(self.repo, "d.txt"))
        facts = self.facts("a.txt", "n.txt", "d.txt", "u.txt")
        listed = sum((facts[name] for name in LISTS[:4]), [])
        self.assertEqual(sorted(facts["paths"]), sorted(listed))

    def test_an_empty_new_file_and_an_empty_deleted_file_are_listed(self):
        self.write("empty.txt", "")
        self.write("gone.txt", "")
        git(self.repo, "add", "gone.txt")
        git(self.repo, "commit", "-q", "-m", "empty")
        self.first = self.head()
        os.unlink(os.path.join(self.repo, "gone.txt"))
        facts = self.facts("empty.txt", "gone.txt")
        self.assertEqual((["empty.txt"], ["gone.txt"], ""), (facts["new_paths"], facts["deleted_paths"], facts["diff"]))

    def test_a_branch_with_no_commit_has_only_new_paths(self):
        git(self.repo, "symbolic-ref", "HEAD", "refs/heads/fresh")
        git(self.repo, "rm", "--cached", "-q", "a.txt", "d.txt", "u.txt")
        built = self.describe(self.argv("S", "a.txt", "u.txt", expected="none"))
        self.assertTrue(built["ok"], built)
        facts = built["facts"]
        self.assertEqual(["a.txt", "u.txt"], facts["new_paths"])
        for name in LISTS[1:]:
            self.assertEqual([], facts[name], name)
        self.assertEqual("--- HEAD/a.txt\n+++ work/a.txt\n@@ -0,0 +1 @@\n+one\n--- HEAD/u.txt\n+++ work/u.txt\n"
                         "@@ -0,0 +1 @@\n+same\n", facts["diff"])

    def test_a_path_that_was_deleted_in_the_index_only_is_new(self):
        git(self.repo, "rm", "--cached", "-q", "u.txt")
        git(self.repo, "commit", "-q", "-m", "untrack")
        self.first = self.head()
        self.assertEqual(["u.txt"], self.facts("u.txt")["new_paths"])


class Diff(Changes):
    def test_the_diff_is_head_against_the_work_tree_path_by_path(self):
        self.write("a.txt", "two\n")
        self.write("n.txt", "new\n")
        os.unlink(os.path.join(self.repo, "d.txt"))
        self.assertEqual("--- HEAD/a.txt\n+++ work/a.txt\n@@ -1 +1 @@\n-one\n+two\n"
                         "--- HEAD/n.txt\n+++ work/n.txt\n@@ -0,0 +1 @@\n+new\n"
                         "--- HEAD/d.txt\n+++ work/d.txt\n@@ -1 +0,0 @@\n-gone\n",
                         self.facts("a.txt", "n.txt", "d.txt", "u.txt")["diff"])

    def test_an_unchanged_path_adds_nothing(self):
        self.assertEqual("", self.facts("u.txt")["diff"])

    def test_context_is_three_lines_and_far_apart_changes_are_two_hunks(self):
        body = "".join("line%d\n" % number for number in range(1, 21))
        self.write("long.txt", body)
        git(self.repo, "add", "long.txt")
        git(self.repo, "commit", "-q", "-m", "long")
        self.first = self.head()
        self.write("long.txt", body.replace("line2\n", "LINE2\n").replace("line18\n", "LINE18\n"))
        diff = self.facts("long.txt")["diff"]
        self.assertEqual(2, diff.count("\n@@ "))
        self.assertIn(" line5\n", diff)
        self.assertNotIn(" line6\n", diff)

    def test_a_missing_final_newline_is_marked_as_git_marks_it(self):
        self.write("a.txt", "x")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "x")
        self.first = self.head()
        self.write("a.txt", "y")
        self.assertEqual("--- HEAD/a.txt\n+++ work/a.txt\n@@ -1 +1 @@\n-x\n\\ No newline at end of file\n"
                         "+y\n\\ No newline at end of file\n", self.facts("a.txt")["diff"])

    def test_only_a_line_feed_ends_a_line_and_the_other_breaks_stay_in_the_text(self):
        self.write("n.txt", "a\r\nb\x0cc\x1d d\n")
        self.assertEqual("--- HEAD/n.txt\n+++ work/n.txt\n@@ -0,0 +1,2 @@\n+a\r\n+b\x0cc\x1d d\n",
                         self.facts("n.txt")["diff"])

    def test_text_that_is_not_utf8_is_shown_with_escapes_so_two_different_bytes_differ(self):
        self.write("n.txt", b"caf\xe9\n")
        built = self.describe(self.argv("S", "n.txt"))
        self.assertIn("+caf\\xe9\n", built["facts"]["diff"])
        self.assertEqual([], built["facts"]["binary_paths"])
        self.write("a.txt", b"\xff\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "latin")
        self.first = self.head()
        self.write("a.txt", b"\xfe\n")
        diff = self.facts("a.txt")["diff"]
        self.assertIn("-\\xff\n", diff)
        self.assertIn("+\\xfe\n", diff)

    def test_the_line_ending_of_a_file_is_not_changed_by_the_attributes_of_the_repository(self):
        self.write(".gitattributes", "*.txt text eol=crlf\n")
        self.write("n.txt", "a\nb\n")
        self.assertEqual("--- HEAD/n.txt\n+++ work/n.txt\n@@ -0,0 +1,2 @@\n+a\n+b\n", self.facts("n.txt")["diff"])
        self.write("a.txt", "one\r\n")
        self.assertEqual(["a.txt"], self.facts("a.txt")["modified_paths"])
        self.assertIn("+one\r\n", self.facts("a.txt")["diff"])

    def test_a_change_of_the_executable_bit_alone_is_a_modification_with_a_line_that_says_so(self):
        os.chmod(os.path.join(self.repo, "u.txt"), 0o755)
        facts = self.facts("u.txt")
        self.assertEqual((["u.txt"], []), (facts["modified_paths"], facts["unchanged_paths"]))
        self.assertEqual("mode HEAD/u.txt 100644 -> work/u.txt 100755\n", facts["diff"])
        self.assertEqual(0, self.commit(*self.argv("S", "u.txt"))[0])
        self.assertIn("100755", self.index())

    def test_a_new_executable_file_and_a_deleted_one_are_marked_and_a_plain_new_file_is_not(self):
        self.write("run.sh", "go\n", mode=0o755)
        self.write("plain.txt", "p\n")
        self.assertEqual("mode HEAD/run.sh none -> work/run.sh 100755\n--- HEAD/run.sh\n+++ work/run.sh\n"
                         "@@ -0,0 +1 @@\n+go\n--- HEAD/plain.txt\n+++ work/plain.txt\n@@ -0,0 +1 @@\n+p\n",
                         self.facts("run.sh", "plain.txt")["diff"])
        git(self.repo, "add", "run.sh")
        git(self.repo, "commit", "-q", "-m", "run")
        self.first = self.head()
        os.unlink(os.path.join(self.repo, "run.sh"))
        self.assertTrue(self.facts("run.sh")["diff"].startswith("mode HEAD/run.sh 100755 -> work/run.sh none\n"))

    def test_a_file_with_a_nul_byte_is_listed_as_binary_and_its_diff_is_withheld(self):
        self.write("a.txt", b"x\0y\n")
        self.write("new.bin", b"\0\1\2")
        facts = self.facts("a.txt", "new.bin", "u.txt")
        self.assertEqual(["a.txt", "new.bin"], facts["binary_paths"])
        self.assertEqual((["new.bin"], ["a.txt"]), (facts["new_paths"], facts["modified_paths"]))
        self.assertEqual("", facts["diff"])

    def test_a_nul_byte_in_the_old_content_or_in_a_deleted_file_makes_it_binary_too(self):
        self.write("old.bin", b"a\0b\n")
        self.write("gone.bin", b"\0")
        git(self.repo, "add", "old.bin", "gone.bin")
        git(self.repo, "commit", "-q", "-m", "bin")
        self.first = self.head()
        self.write("old.bin", "now text\n")
        os.unlink(os.path.join(self.repo, "gone.bin"))
        facts = self.facts("old.bin", "gone.bin")
        self.assertEqual(["old.bin", "gone.bin"], facts["binary_paths"])
        self.assertEqual((["old.bin"], ["gone.bin"], ""), (facts["modified_paths"], facts["deleted_paths"],
                                                          facts["diff"]))

    def test_the_text_paths_are_still_shown_beside_a_binary_one(self):
        self.write("b.bin", b"\0")
        self.write("n.txt", "t\n")
        self.assertEqual("--- HEAD/n.txt\n+++ work/n.txt\n@@ -0,0 +1 @@\n+t\n", self.facts("b.bin", "n.txt")["diff"])


class Real(Changes):
    def test_the_lists_and_the_diff_describe_the_commit_the_real_command_makes(self):
        self.write("a.txt", "two\nthree\n")
        self.write("n.txt", "new\n")
        os.unlink(os.path.join(self.repo, "d.txt"))
        # git lists the paths of a patch in order of name, and `describe` in the order given
        args = self.argv("Change", "a.txt", "d.txt", "n.txt")
        built = self.describe(args)
        self.assertTrue(built["ok"], built)
        facts = built["facts"]
        self.assertEqual((0, ""), self.commit(*args)[::2])
        status = dict(line.split("\t")[::-1] for line in git(
            self.repo, "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD").stdout.splitlines())
        self.assertEqual({"a.txt": "M", "n.txt": "A", "d.txt": "D"}, status)
        self.assertEqual(sorted(facts["new_paths"] + facts["modified_paths"] + facts["deleted_paths"]),
                         sorted(status))
        patch = git(self.repo, "show", "--format=", "--no-ext-diff", "--no-textconv", "HEAD").stdout
        def changed(text):
            return [line for line in text.splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")]

        self.assertEqual(changed(patch), changed(facts["diff"]))

    def test_a_path_in_the_unchanged_list_is_one_the_real_command_does_not_stage(self):
        facts = self.facts("u.txt")
        self.assertEqual(["u.txt"], facts["unchanged_paths"])
        self.assertRefused(self.commit(*self.argv("S", "u.txt")))


class Refusals(Changes):
    def test_a_refusal_leaves_the_lists_empty_and_the_diff_null(self):
        self.write("a.txt", "two\n")
        built = self.describe(self.argv("S", "a.txt", "nothing.txt"))
        self.assertEqual(["path_unknown"], self.codes(built))
        for name in LISTS:
            self.assertEqual([], built["facts"][name], name)
        self.assertIsNone(built["facts"]["diff"])
        built = self.describe(["--force"])
        self.assertEqual(([], None), (built["facts"]["new_paths"], built["facts"]["diff"]))

    def test_whitespace_errors_stop_before_the_lists(self):
        self.write("a.txt", "two \n")
        built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["whitespace_errors"], self.codes(built))
        self.assertEqual(([], None), (built["facts"]["modified_paths"], built["facts"]["diff"]))

    def test_a_git_failure_while_reading_the_old_content_is_an_unreadable_repository_and_gives_no_partial_lists(self):
        self.write("a.txt", "two\n")
        self.write("n.txt", "new\n")
        real = H.run_capped

        def failing(argv, cwd, limit, **kwargs):
            if argv[1] == "cat-file":
                raise H.Refused("git cat-file failed (128)")
            return real(argv, cwd, limit, **kwargs)

        with unittest.mock.patch.object(H, "run_capped", failing):
            built = self.describe(self.argv("S", "n.txt", "a.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built))
        for name in LISTS:
            self.assertEqual([], built["facts"][name], name)
        self.assertIsNone(built["facts"]["diff"])

    def test_a_blob_that_is_not_the_size_git_reported_is_an_unreadable_repository(self):
        self.write("a.txt", "two\n")
        real = H.run

        def lying(argv, cwd, **kwargs):
            if argv[1:3] == ["cat-file", "-s"]:
                return unittest.mock.Mock(returncode=0, stdout="2\n", stderr="")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", lying):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built))

    def test_a_size_that_is_not_a_number_is_an_unreadable_repository(self):
        self.write("a.txt", "two\n")
        real = H.run

        def odd(argv, cwd, **kwargs):
            if argv[1:3] == ["cat-file", "-s"]:
                return unittest.mock.Mock(returncode=0, stdout="many\n", stderr="")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", odd):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built))

    @unittest.skipIf(os.geteuid() == 0, "root reads any file")
    def test_a_file_that_cannot_be_read_is_a_refused_path(self):
        self.write("n.txt", "new\n")
        os.chmod(os.path.join(self.repo, "n.txt"), 0)
        self.addCleanup(os.chmod, os.path.join(self.repo, "n.txt"), 0o644)
        built = self.describe(self.argv("S", "n.txt", "u.txt"))
        self.assertEqual(["path_refused"], self.codes(built))
        self.assertEqual(([], None), (built["facts"]["new_paths"], built["facts"]["diff"]))


class NotRegular(Changes):
    def secret(self):
        path = os.path.join(self.outside, "secret.txt")
        with open(path, "w") as handle:
            handle.write("TOPSECRET\n")
        return path

    def assertOnly(self, built, path):
        self.assertTrue(built["ok"], built)
        facts = built["facts"]
        self.assertEqual([path], facts["not_regular_paths"])
        for name in LISTS[:5]:
            self.assertEqual([], facts[name], name)
        self.assertEqual("", facts["diff"])
        self.assertNotIn("TOPSECRET", json.dumps(built))

    def test_a_file_that_became_a_link_to_a_file_is_not_followed(self):
        target = self.secret()

        def swap():
            os.unlink(os.path.join(self.repo, "u.txt"))
            os.symlink(target, os.path.join(self.repo, "u.txt"))

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "u.txt"))
        self.assertOnly(built, "u.txt")

    def test_a_new_file_that_became_a_link_is_not_followed(self):
        target = self.secret()
        self.write("n.txt", "x\n")

        def swap():
            os.unlink(os.path.join(self.repo, "n.txt"))
            os.symlink(target, os.path.join(self.repo, "n.txt"))

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "n.txt"))
        self.assertOnly(built, "n.txt")

    def test_a_file_under_a_directory_that_became_a_link_is_not_followed(self):
        self.write("sub/c.txt", "c\n")
        git(self.repo, "add", "sub/c.txt")
        git(self.repo, "commit", "-q", "-m", "sub")
        self.first = self.head()
        elsewhere = os.path.join(self.outside, "sub")
        os.mkdir(elsewhere)
        with open(os.path.join(elsewhere, "c.txt"), "w") as handle:
            handle.write("TOPSECRET\n")

        def swap():
            os.rename(os.path.join(self.repo, "sub"), os.path.join(self.scratch, "moved"))
            os.symlink(elsewhere, os.path.join(self.repo, "sub"))

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "sub/c.txt"))
        self.assertOnly(built, "sub/c.txt")

    def test_a_fifo_is_not_opened_for_reading(self):
        def swap():
            os.unlink(os.path.join(self.repo, "u.txt"))
            os.mkfifo(os.path.join(self.repo, "u.txt"))

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "u.txt"))
        self.assertOnly(built, "u.txt")

    def test_a_directory_in_the_place_of_a_file_is_not_a_regular_file(self):
        def swap():
            os.unlink(os.path.join(self.repo, "u.txt"))
            os.mkdir(os.path.join(self.repo, "u.txt"))

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "u.txt"))
        self.assertOnly(built, "u.txt")

    def test_a_file_in_the_place_of_a_directory_on_the_way_is_not_a_regular_file(self):
        self.write("sub/c.txt", "c\n")
        git(self.repo, "add", "sub/c.txt")
        git(self.repo, "commit", "-q", "-m", "sub")
        self.first = self.head()

        def swap():
            os.unlink(os.path.join(self.repo, "sub", "c.txt"))
            os.rmdir(os.path.join(self.repo, "sub"))
            self.write("sub", "now a file\n")

        with self.after_the_checks(swap):
            built = self.describe(self.argv("S", "sub/c.txt"))
        self.assertOnly(built, "sub/c.txt")

    def test_a_file_that_vanished_after_the_checks_is_a_deletion(self):
        with self.after_the_checks(lambda: os.unlink(os.path.join(self.repo, "u.txt"))):
            facts = self.facts("u.txt")
        self.assertEqual(["u.txt"], facts["deleted_paths"])


class Bounds(Changes):
    def one_line(self, size):
        """A new file whose whole diff is `size` bytes."""
        head = "--- HEAD/n.txt\n+++ work/n.txt\n@@ -0,0 +1 @@\n+"
        self.write("n.txt", "x" * (size - len(head) - 1) + "\n")

    def test_a_diff_of_exactly_the_cap_is_given(self):
        self.one_line(H.MAX_DIFF)
        built = self.describe(self.argv("S", "n.txt"))
        self.assertTrue(built["ok"], built)
        self.assertEqual(H.MAX_DIFF, len(built["facts"]["diff"]))
        self.assertFalse(built["truncated"])
        self.assertEqual([], built["facts"]["omitted"])

    def test_a_diff_one_byte_over_the_cap_is_left_out_whole_and_named(self):
        self.one_line(H.MAX_DIFF + 1)
        built = self.describe(self.argv("S", "n.txt"))
        self.assertTrue(built["ok"], built)
        self.assertTrue(built["truncated"])
        self.assertNotIn("diff", built["facts"])
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertEqual(["n.txt"], built["facts"]["new_paths"])

    def test_the_diffs_of_many_paths_add_up_to_one_diff_that_obeys_the_cap(self):
        for number in range(4):
            self.write("p%d.txt" % number, "y" * 30000 + "\n")
        built = self.describe(self.argv("S", *["p%d.txt" % number for number in range(4)]))
        self.assertTrue(built["truncated"])
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertEqual(4, len(built["facts"]["new_paths"]))

    def test_a_blob_over_the_read_bound_is_not_read_and_leaves_the_diff_out(self):
        self.write("big.txt", "b" * 3000 + "\n")
        git(self.repo, "add", "big.txt")
        git(self.repo, "commit", "-q", "-m", "big")
        self.first = self.head()
        self.write("big.txt", "small\n")
        directory = self.recording_git()
        with unittest.mock.patch.object(H, "MAX_SIDE", 1000):
            built = self.describe(self.argv("S", "big.txt"), path=directory + os.pathsep + C.STANDARD)
        self.assertTrue(built["ok"], built)
        self.assertEqual(["big.txt"], built["facts"]["modified_paths"])
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])
        calls = [arguments[:2] for arguments, _ in self.runs() if arguments[0] == "cat-file"]
        self.assertEqual([["cat-file", "-s"]], calls)

    def test_a_work_file_over_the_read_bound_is_never_read(self):
        self.write("big.txt", "b" * 3000 + "\n")
        reads = []
        real = os.read

        def counting(fd, count):
            reads.append(count)
            return real(fd, count)

        root_fd = H.safefs.open_root(self.repo, "repository")
        try:
            with unittest.mock.patch.object(H, "MAX_SIDE", 1000), unittest.mock.patch.object(os, "read", counting):
                state = H._read_work(root_fd, ["big.txt"])
        finally:
            os.close(root_fd)
        self.assertEqual(("large", 3001), state[:2])
        self.assertEqual([], reads)

    def test_two_large_sides_that_may_be_equal_are_called_modified_and_not_compared(self):
        self.write("big.txt", "b" * 3000 + "\n")
        git(self.repo, "add", "big.txt")
        git(self.repo, "commit", "-q", "-m", "big")
        self.first = self.head()
        with unittest.mock.patch.object(H, "MAX_SIDE", 1000):
            built = self.describe(self.argv("S", "big.txt"))
        self.assertEqual((["big.txt"], ["diff"]), (built["facts"]["modified_paths"], built["facts"]["omitted"]))

    def test_a_list_over_the_array_cap_is_left_out_whole(self):
        for number in range(201):
            self.write("many/f%d" % number, "x\n")
        built = self.describe(self.argv("S", *["many/f%d" % number for number in range(201)]))
        self.assertTrue(built["truncated"])
        self.assertEqual(["requested_paths", "paths", "new_paths"], built["facts"]["omitted"])
        self.assertEqual([], built["facts"]["modified_paths"])
        self.assertIn("diff", built["facts"])


class Inert(Changes):
    def test_nothing_changes_for_any_kind_of_change(self):
        self.write("a.txt", "two\n")
        self.write("n.txt", "new\n")
        self.write("b.bin", b"\0")
        os.unlink(os.path.join(self.repo, "d.txt"))
        os.chmod(os.path.join(self.repo, "u.txt"), 0o755)
        before = DR.snapshot(self.repo)
        for paths in (("a.txt",), ("n.txt",), ("d.txt",), ("u.txt",), ("b.bin",), ("a.txt", "n.txt", "d.txt", "u.txt")):
            with self.subTest(paths=paths):
                self.describe(self.argv("S", *paths))
                self.assertEqual(before, DR.snapshot(self.repo))
        self.assertEqual(self.first, self.head())

    def test_the_old_content_is_read_with_two_fixed_shapes_and_nothing_is_written(self):
        self.write("a.txt", "two\n")
        directory = self.recording_git()
        built = self.describe(self.argv("S", "a.txt"), path=directory + os.pathsep + C.STANDARD)
        self.assertTrue(built["ok"], built)
        found = [arguments for arguments, _ in self.runs() if arguments[0] == "cat-file"]
        self.assertEqual([["cat-file", "-s", "HEAD:a.txt"], ["cat-file", "blob", "HEAD:a.txt"]], found)
        self.assertLessEqual({arguments[0] for arguments, _ in self.runs()},
                             {"rev-parse", "ls-files", "diff", "config", "cat-file"})

    def test_no_program_a_filter_or_a_diff_driver_names_is_started(self):
        script = os.path.join(self.outside, "tool")
        marker = os.path.join(self.scratch, "ran")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\ncat\n" % marker)
        os.chmod(script, 0o755)
        with open(os.path.join(self.home, ".gitconfig"), "a") as handle:
            handle.write("[filter \"mark\"]\n\tclean = %s\n\tsmudge = %s\n\trequired = true\n" % (script, script))
            handle.write("[diff \"mark\"]\n\ttextconv = %s\n\tcommand = %s\n\tbinary = false\n" % (script, script))
            handle.write("[core]\n\tpager = %s\n" % script)
        self.write(".gitattributes", "n.txt filter=mark diff=mark\nu.txt diff=mark -text\nb.dat -diff\n")
        self.write("n.txt", "new\n")
        self.write("u.txt", "changed\n")
        built = self.describe(self.argv("S", "n.txt", "u.txt"))
        self.assertTrue(built["ok"], built)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(["n.txt"], built["facts"]["new_paths"])
        self.assertEqual(["u.txt"], built["facts"]["modified_paths"])
        self.assertIn("+changed\n", built["facts"]["diff"])
        self.assertIn("+new\n", built["facts"]["diff"])


class Headers(unittest.TestCase):
    def test_the_diff_of_text_is_made_without_git(self):
        self.assertEqual("--- HEAD/p\n+++ work/p\n@@ -1 +1 @@\n-a\n+b\n", H._text_diff("p", b"a\n", b"b\n"))
        self.assertEqual("", H._text_diff("p", b"a\n", b"a\n"))

    def test_a_mode_line_is_for_a_change_of_mode_and_not_for_a_plain_new_or_deleted_file(self):
        self.assertEqual("", H._mode_line("p", "100644", "100644"))
        self.assertEqual("", H._mode_line("p", None, "100644"))
        self.assertEqual("", H._mode_line("p", "100644", None))
        self.assertEqual("mode HEAD/p 100644 -> work/p 100755\n", H._mode_line("p", "100644", "100755"))
        self.assertEqual("mode HEAD/p none -> work/p 100755\n", H._mode_line("p", None, "100755"))
        self.assertEqual("mode HEAD/p 120000 -> work/p 100644\n", H._mode_line("p", "120000", "100644"))


if __name__ == "__main__":
    unittest.main()
