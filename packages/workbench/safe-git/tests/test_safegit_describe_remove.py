"""`safe-git describe remove` (plan `2026-10-25-safe-git-describe`, increment C; `docs/specs/safe-git.md`, "Describe").

Real repositories and real files, built on the fixtures of the `remove` tests. A refusal is checked twice: `describe`
reports it as data with its code, and the real `remove` given the same arguments refuses it. Every call is checked by
what it leaves behind: the repository is byte for byte the same."""

import hashlib
import io
import json
import os
import stat
import subprocess
import unittest
import unittest.mock

from tests import support_helpers

import support_git
import test_safegit_remove as R
from support_git import git, needs_git

H = R.H
SHAPES = support_helpers.load("safe-git")


def snapshot(root):
    """Every entry under `root`, `.git` included: its type bits, size, change time and the hash of a regular file."""
    found = {}
    for base, dirs, files in os.walk(root):
        for name in dirs + files:
            full = os.path.join(base, name)
            info = os.lstat(full)
            digest = None
            if stat.S_ISREG(info.st_mode):
                with open(full, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
            found[os.path.relpath(full, root)] = (info.st_mode, info.st_size, info.st_mtime_ns, digest)
    return found


@needs_git
class Describe(R.Remove):
    def describe(self, *args, cwd=None):
        """The object `describe remove <args>` prints; the exit status is 0 and standard error is empty."""
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": R.STANDARD, "HOME": self.scratch}, clear=True):
            code = H.main(["describe", "remove"] + list(args), out, err, cwd or self.repo)
        self.assertEqual((0, ""), (code, err.getvalue()))
        text = out.getvalue()
        self.assertEqual(1, text.count("\n"))
        built = json.loads(text)
        self.assertEqual(["contract", "action", "ok", "truncated", "errors", "facts"], list(built))
        self.assertEqual((1, "remove"), (built["contract"], built["action"]))
        return built

    def described(self, *paths, recursive=False, confirm=False):
        options = (["--recursive"] if recursive else []) + (["--confirm"] if confirm else [])
        return self.describe(*options, "--", *paths)

    def codes(self, built):
        return [error["code"] for error in built["errors"]]


class Refusals(Describe):
    """One case for each code of the removal rows and of the rows for both actions."""

    def check(self, code, args, cwd=None):
        """`describe` gives `code` for `args`, and the real `remove` refuses the same arguments."""
        before = snapshot(self.repo)
        built = self.describe(*args, cwd=cwd)
        self.assertEqual([code], self.codes(built), built)
        self.assertFalse(built["ok"])
        self.assertTrue(0 < len(built["errors"][0]["message"]) <= 500)
        self.assertRefused(self.remove(*args, cwd=cwd))
        self.assertEqual(before, snapshot(self.repo))
        return built

    def test_usage(self):
        for args in ([], ["b.txt"], ["--force", "--", "b.txt"], ["--confirm", "--confirm", "--", "b.txt"],
                     ["--recursive", "--recursive", "--", "b.txt"], ["--"], ["--confirm", "--"],
                     ["--"] + ["p%d" % number for number in range(H.MAX_PATHS + 1)]):
            with self.subTest(args=args[:4]):
                self.check("usage", args)

    def test_a_refused_command_line_still_reports_what_was_given(self):
        built = self.check("usage", ["--confirm", "--force", "--", "b.txt", "c.txt"])
        facts = built["facts"]
        self.assertEqual((True, False, ["b.txt", "c.txt"]),
                         (facts["confirm"], facts["recursive"], facts["requested_paths"]))

    def test_repository_unreadable(self):
        self.check("repository_unreadable", ["--", "a.txt"], cwd=self.outside)

    def test_repository_unreadable_for_a_git_that_cannot_be_found(self):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": self.outside, "HOME": self.scratch}, clear=True):
            code = H.main(["describe", "remove", "--", "a.txt"], out, err, self.repo)
        self.assertEqual((0, ""), (code, err.getvalue()))
        built = json.loads(out.getvalue())
        self.assertEqual(["repository_unreadable"], self.codes(built))
        self.assertIn("git was not found", built["errors"][0]["message"])

    def test_path_refused(self):
        self.link("sub", self.out_dir)
        for spelling in ("/etc/passwd", "*", "b.t?t", "[b].txt", "-b.txt", ".git", ".GIT/config", "d/.git", "git~1",
                         "a:b", "d\\x", "d//x", "./b.txt", "d/../b.txt", "x" * 5000, "b\ttxt", "sub/inner.txt", ""):
            with self.subTest(path=spelling):
                self.check("path_refused", ["--", spelling])
        self.assertOutsideIntact()

    def test_path_duplicate(self):
        self.write("d/x.txt", "x\n")
        for names in (["d", "d"], ["d", "d/x.txt"], ["d/x.txt", "d"], ["a.txt", "A.txt"], ["d", "D/x.txt"]):
            with self.subTest(names=names):
                self.check("path_duplicate", ["--recursive", "--"] + names)

    def test_git_metadata_refused(self):
        self.check("git_metadata_refused", ["--", "﹒git"])

    def test_target_missing(self):
        self.write("d/x.txt", "x\n")
        for spelling in ("missing.txt", "missing/x.txt", "d/missing.txt"):
            with self.subTest(path=spelling):
                self.check("target_missing", ["--", spelling])

    def test_recursive_required(self):
        self.write("d/x.txt", "x\n")
        self.check("recursive_required", ["--", "d"])

    def test_repository_root_refused(self):
        self.write("d/x.txt", "x\n")
        inode = os.lstat(os.path.join(self.repo, "d")).st_ino
        with unittest.mock.patch.object(H, "_same", lambda first, second: first.st_ino == inode):
            self.check("repository_root_refused", ["--recursive", "--", "d"])

    def test_nested_repository(self):
        for where in ("n", "d/n"):
            full = os.path.join(self.repo, *where.split("/"))
            os.makedirs(full)
            git(full, "init", "-q")
            self.write(where + "/f.txt", "f\n")
        self.check("nested_repository", ["--recursive", "--", "n"])
        self.check("nested_repository", ["--recursive", "--", "d"])
        self.check("nested_repository", ["--", "n/f.txt"])
        self.write("e/.git", "gitdir: ../elsewhere\n")
        self.check("nested_repository", ["--recursive", "--", "e"])

    def test_other_filesystem(self):
        self.write("d/e/x.txt", "x\n")
        real = H._device
        inode_d = os.lstat(os.path.join(self.repo, "d")).st_ino
        inode_e = os.lstat(os.path.join(self.repo, "d", "e")).st_ino
        for inode, args in ((inode_e, ["--recursive", "--", "d"]), (inode_d, ["--", "d/e/x.txt"]),
                            (inode_d, ["--recursive", "--", "d"])):
            with self.subTest(args=args):
                with unittest.mock.patch.object(H, "_device", lambda info, inode=inode: real(info) + (info.st_ino == inode)):
                    self.check("other_filesystem", args)

    def test_tree_too_large(self):
        for number in range(8):
            self.write("d/f%d.txt" % number, "x\n")
        self.write("deep/" + "/".join("n" for _ in range(30)) + "/x.txt", "x\n")
        with unittest.mock.patch.object(H, "MAX_REMOVE_ENTRIES", 5):
            self.check("tree_too_large", ["--recursive", "--", "d"])
            self.check("tree_too_large", ["--", "d/f0.txt"])
        with unittest.mock.patch.object(H, "MAX_REMOVE_DEPTH", 10):
            self.check("tree_too_large", ["--recursive", "--", "deep"])

    def test_target_changed(self):
        self.write("d/e/x.txt", "x\n")
        for stage, rel, target in (("planning", "d", "d"), ("scanning", "e", "d/e")):
            with self.subTest(stage=stage):
                def swap(seen, where, stage=stage, rel=rel, target=target):
                    if (seen, where) == (stage, rel):
                        H.HOOK = None
                        full = os.path.join(self.repo, *target.split("/"))
                        os.rename(full, full + "-old")
                        os.mkdir(full)
                H.HOOK = swap
                built = self.describe("--recursive", "--", "d")
                H.HOOK = None
                self.assertEqual(["target_changed"], self.codes(built))
                os.rmdir(os.path.join(self.repo, *target.split("/")))
                os.rename(os.path.join(self.repo, *target.split("/")) + "-old", os.path.join(self.repo, *target.split("/")))

    def test_a_refusal_has_every_fact_empty_or_null_and_the_totals_left_out(self):
        facts = self.check("target_missing", ["--recursive", "--", "a.txt", "missing.txt"])["facts"]
        self.assertEqual(["a.txt", "missing.txt"], facts["requested_paths"])
        for name in ("target_paths", "file_targets", "directory_targets", "link_targets", "other_targets",
                     "tracked_targets", "ignored_targets", "ignore_unknown_targets"):
            self.assertEqual([], facts[name], name)
        self.assertIsNone(facts["tracked_file_total"])
        self.assertNotIn("entry_total", facts)
        self.assertNotIn("size_total", facts)
        self.assertEqual(["entry_total", "size_total"], facts["omitted"])
        self.assertTrue(self.check("target_missing", ["--", "missing.txt"])["truncated"])

    def test_the_refusals_of_the_removal_checks_carry_a_code(self):
        """A refusal with no code would stop `describe` with no object, which the engine reads as a decline."""
        for argv in (["--"], ["x"], [], ["--force", "--", "x"]):
            with self.assertRaises(H.Refused) as caught:
                H.parse_remove(argv)
            self.assertEqual("usage", caught.exception.code)
        root_fd = H.safefs.open_root(self.repo, "repository")
        try:
            for path in ("missing", "../x", "*"):
                with self.assertRaises(H.Refused) as caught:
                    H.plan_removal(root_fd, [path], False)
                self.assertIsNotNone(caught.exception.code, path)
        finally:
            os.close(root_fd)


class Facts(Describe):
    def tree(self):
        self.write("b.txt", "bee\n")
        self.write("d/one.txt", "1\n")
        self.write("d/e/two.txt", "22\n")
        self.write("d/e/f/three.txt", "333\n")
        os.makedirs(os.path.join(self.repo, "d", "empty"))
        self.link("ln", "a.txt")
        os.mkfifo(os.path.join(self.repo, "pipe"))
        self.write("c.txt", "untracked\n")
        git(self.repo, "add", "b.txt", "d/one.txt", "d/e/two.txt")

    def test_the_facts_of_a_valid_removal_are_the_ones_the_real_preview_acts_on(self):
        self.tree()
        paths = ["b.txt", "d", "ln", "pipe", "c.txt"]
        built = self.described(*paths, recursive=True)
        self.assertTrue(built["ok"])
        self.assertEqual([], built["errors"])
        self.assertFalse(built["truncated"])
        facts = built["facts"]
        root_fd = H.safefs.open_root(self.repo, "repository")
        try:
            targets = H.plan_removal(root_fd, paths, True)
        finally:
            os.close(root_fd)
        self.assertEqual([t.path for t in targets], facts["target_paths"])
        self.assertEqual(paths, facts["requested_paths"])
        self.assertEqual([t.path for t in targets if t.kind == "file"], facts["file_targets"])
        self.assertEqual([t.path for t in targets if t.kind == "directory"], facts["directory_targets"])
        self.assertEqual([t.path for t in targets if t.kind == "symlink"], facts["link_targets"])
        self.assertEqual([t.path for t in targets if t.kind == "other"], facts["other_targets"])
        self.assertEqual((["b.txt", "c.txt"], ["d"], ["ln"], ["pipe"]),
                         (facts["file_targets"], facts["directory_targets"], facts["link_targets"],
                          facts["other_targets"]))
        self.assertEqual((False, True), (facts["confirm"], facts["recursive"]))
        self.assertEqual([], facts["omitted"])

    def test_the_totals_equal_a_count_made_by_the_test(self):
        self.tree()
        paths = ["b.txt", "d", "ln", "pipe", "c.txt"]
        entries = size = 0
        for path in paths:
            full = os.path.join(self.repo, path)
            entries += 1
            if os.path.isdir(full) and not os.path.islink(full):
                for base, dirs, files in os.walk(full):
                    entries += len(dirs) + len(files)
                    for name in files:
                        item = os.path.join(base, name)
                        if stat.S_ISREG(os.lstat(item).st_mode):
                            size += os.lstat(item).st_size
            elif stat.S_ISREG(os.lstat(full).st_mode):
                size += os.lstat(full).st_size
        tracked = len(git(self.repo, "ls-files", "-z", "--", *paths).stdout.split("\0")) - 1
        facts = self.described(*paths, recursive=True)["facts"]
        self.assertEqual((entries, size, tracked), (facts["entry_total"], facts["size_total"],
                                                    facts["tracked_file_total"]))
        self.assertEqual(3, facts["tracked_file_total"])
        self.assertGreater(facts["size_total"], 0)

    def test_tracked_ignored_and_ordinary_targets(self):
        self.tree()
        self.write(".gitignore", "ignored.txt\nbuild/\n")
        self.write("ignored.txt", "i\n")
        self.write("build/x.txt", "x\n")
        facts = self.described("b.txt", "d", "c.txt", "ignored.txt", "build", "a.txt", recursive=True)["facts"]
        self.assertEqual(["b.txt", "d", "a.txt"], facts["tracked_targets"])
        self.assertEqual(["ignored.txt", "build"], facts["ignored_targets"])
        self.assertEqual([], facts["ignore_unknown_targets"])
        self.assertEqual(4, facts["tracked_file_total"])

    def test_a_tracked_file_in_an_ignored_place_is_tracked_and_not_ignored(self):
        self.write("ignored.txt", "i\n")
        self.write(".gitignore", "ignored.txt\n")
        git(self.repo, "add", "-f", "ignored.txt")
        facts = self.described("ignored.txt")["facts"]
        self.assertEqual(["ignored.txt"], facts["tracked_targets"])
        self.assertEqual([], facts["ignored_targets"])

    def test_tracking_is_found_whatever_the_case_the_file_system_folds(self):
        self.write("D/one.txt", "1\n")
        git(self.repo, "add", "D/one.txt")
        facts = self.described("D", recursive=True)["facts"]
        self.assertEqual(["D"], facts["tracked_targets"])

    def test_a_target_whose_ignored_status_cannot_be_found_is_named_and_never_guessed(self):
        self.write("ignored.txt", "i\n")
        self.write("c.txt", "c\n")
        self.write(".gitignore", "ignored.txt\n")
        real = H.run

        def failing(argv, cwd, **kwargs):
            if argv[1] == "check-ignore":
                raise H.Refused("git check-ignore did not finish within 120 seconds", code="repository_unreadable")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", failing):
            facts = self.described("ignored.txt", "c.txt")["facts"]
        self.assertEqual(["ignored.txt", "c.txt"], facts["ignore_unknown_targets"])
        self.assertEqual([], facts["ignored_targets"])

    def test_an_error_exit_of_check_ignore_is_unknown_and_no_exit_is_ignored(self):
        self.write("ignored.txt", "i\n")
        self.write(".gitignore", "ignored.txt\n")
        real = H.run

        def odd(argv, cwd, **kwargs):
            if argv[1] == "check-ignore":
                return subprocess.CompletedProcess(argv, 128, "", "fatal")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", odd):
            facts = self.described("ignored.txt")["facts"]
        self.assertEqual(["ignored.txt"], facts["ignore_unknown_targets"])
        self.assertEqual([], facts["ignored_targets"])

    def test_the_totals_are_complete_up_to_ten_thousand_entries(self):
        self.write("d/keep.txt", "k\n")
        for number in range(9998):
            os.close(os.open(os.path.join(self.repo, "d", "f%d" % number), os.O_CREAT | os.O_WRONLY, 0o644))
        facts = self.described("d", recursive=True)["facts"]       # the target and 9,999 entries
        self.assertEqual(10000, facts["entry_total"])
        self.assertEqual(2, facts["size_total"])
        self.assertEqual([], facts["omitted"])

    def test_more_than_ten_thousand_entries_leave_the_totals_out(self):
        self.write("d/keep.txt", "k\n")
        for number in range(9999):
            os.close(os.open(os.path.join(self.repo, "d", "f%d" % number), os.O_CREAT | os.O_WRONLY, 0o644))
        built = self.described("d", recursive=True)
        facts = built["facts"]
        self.assertTrue(built["ok"])
        self.assertTrue(built["truncated"])
        self.assertNotIn("entry_total", facts)
        self.assertNotIn("size_total", facts)
        self.assertEqual(["entry_total", "size_total"], facts["omitted"])
        self.assertEqual(0, facts["tracked_file_total"])
        self.assertEqual(["d"], facts["target_paths"])

    def test_a_long_list_of_targets_is_left_out_whole_and_named(self):
        paths = []
        for number in range(201):
            self.write("many/f%d" % number, "x\n")
            paths.append("many/f%d" % number)
        built = self.described(*paths)
        self.assertTrue(built["truncated"])
        for name in ("requested_paths", "target_paths", "file_targets"):
            self.assertNotIn(name, built["facts"])
            self.assertIn(name, built["facts"]["omitted"])
        self.assertEqual(0, built["facts"]["tracked_file_total"])

    def test_confirm_and_recursive_only_report_the_options_and_delete_nothing(self):
        self.tree()
        before = snapshot(self.repo)
        built = self.described("b.txt", "d", recursive=True, confirm=True)
        self.assertEqual((True, True), (built["facts"]["confirm"], built["facts"]["recursive"]))
        self.assertEqual(before, snapshot(self.repo))


class Inert(Describe):
    def test_the_repository_is_byte_for_byte_the_same_after_every_kind_of_call(self):
        self.write("b.txt", "bee\n")
        self.write("d/x.txt", "x\n")
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", "i\n")
        self.link("ln", "a.txt")
        git(self.repo, "add", "b.txt")
        before = snapshot(self.repo)
        for args in (["--", "b.txt"], ["--recursive", "--confirm", "--", "d", "b.txt", "ln", "ignored.txt"],
                     ["--", "missing"], ["--force"], ["--recursive", "--", "d"]):
            with self.subTest(args=args):
                self.describe(*args)
                self.assertEqual(before, snapshot(self.repo))

    def test_only_read_commands_run_and_only_in_the_specified_shapes(self):
        self.write("d/x.txt", "x\n")
        self.write("ignored.txt", "i\n")
        directory = self.recording_git()
        path = directory + os.pathsep + R.STANDARD
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": path, "HOME": self.scratch}, clear=True):
            self.assertEqual(0, H.main(["describe", "remove", "--recursive", "--", "d", "ignored.txt"], out, err,
                                       self.repo))
        runs = [arguments for arguments, _ in self.runs()]
        self.assertLessEqual({arguments[0] for arguments in runs}, {"rev-parse", "ls-files", "check-ignore"})
        self.assertIn(["ls-files", "-z", "--", "d", "ignored.txt"], runs)
        self.assertIn(["check-ignore", "-q", "--", "d"], runs)
        self.assertIn(["check-ignore", "-q", "--", "ignored.txt"], runs)
        self.assertTrue(all(H.git_shape_ok(["git"] + arguments) for arguments in runs))

    def test_a_repository_that_selects_a_program_runs_none_of_them(self):
        self.write("b.txt", "b\n")
        marker = os.path.join(self.scratch, "ran")
        script = os.path.join(self.outside, "tool")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(script, 0o755)
        for key in ("core.fsmonitor", "core.sshCommand", "core.editor", "core.pager", "diff.external",
                    "core.hooksPath", "core.askPass", "core.excludesFile", "credential.helper"):
            self.config(key, script)
        os.makedirs(os.path.join(self.repo, ".git", "hooks"), exist_ok=True)
        for hook in ("pre-commit", "post-checkout", "fsmonitor-watchman", "post-index-change"):
            hook_path = os.path.join(self.repo, ".git", "hooks", hook)
            with open(hook_path, "w") as handle:
                handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
            os.chmod(hook_path, 0o755)
        built = self.described("b.txt", "a.txt")
        self.assertTrue(built["ok"], built)
        self.assertFalse(os.path.exists(marker))


class GitShapes(unittest.TestCase):
    """The two shapes added for `describe`, each in one fixed form."""

    def ok(self, *argv):
        return SHAPES.git_shape_ok(["git"] + list(argv))

    def test_the_allowed_forms(self):
        self.assertTrue(self.ok("check-ignore", "-q", "--", "a"))
        self.assertTrue(self.ok("check-ignore", "-q", "--", "d/e.txt"))
        self.assertTrue(self.ok("ls-files", "-z", "--", "a"))
        self.assertTrue(self.ok("ls-files", "-z", "--", "a", "d/b"))

    def test_no_other_form_of_check_ignore_passes(self):
        for rest in ([], ["-q"], ["--", "a"], ["-q", "a"], ["-q", "--"], ["-q", "--", "a", "b"],
                     ["--no-index", "-q", "--", "a"], ["-q", "--no-index", "--", "a"], ["-v", "-q", "--", "a"],
                     ["-q", "-v", "--", "a"], ["--stdin", "-q", "--", "a"], ["-q", "--stdin"], ["-q", "-z", "--", "a"],
                     ["-n", "-q", "--", "a"], ["-q", "--", "/etc/passwd"], ["-q", "--", "../x"], ["-q", "--", ""],
                     ["-q", "--", "a/../b"], ["--quiet", "--", "a"], ["-q", "--", "a\0"]):
            with self.subTest(rest=rest):
                self.assertFalse(self.ok("check-ignore", *rest))

    def test_no_other_form_of_ls_files_with_z_passes(self):
        for rest in (["-z"], ["-z", "--"], ["--", "a"], ["-z", "a"], ["-z", "-o", "--", "a"], ["-z", "--others", "--", "a"],
                     ["-z", "-c", "--", "a"], ["-z", "-m", "--", "a"], ["-z", "--exclude-standard", "--", "a"],
                     ["-z", "--", "/etc/passwd"], ["-z", "--", "../x"], ["-z", "--", ""], ["-z", "--eol", "--", "a"],
                     ["-z", "--recurse-submodules", "--", "a"], ["-z", "-t", "--", "a"], ["-z", "--format=%(path)", "--", "a"],
                     ["--error-unmatch"], ["-s", "-z", "-o"], ["-s"]):
            with self.subTest(rest=rest):
                self.assertFalse(self.ok("ls-files", *rest))

    def test_the_forms_that_were_allowed_before_still_are(self):
        self.assertTrue(self.ok("ls-files", "-s", "-z"))
        self.assertTrue(self.ok("ls-files", "-s", "-z", "--", "a"))
        self.assertTrue(self.ok("ls-files", "--error-unmatch", "--", "a"))

    def test_a_global_option_or_another_subcommand_is_still_refused(self):
        self.assertFalse(SHAPES.git_shape_ok(["git", "-c", "core.fsmonitor=x", "check-ignore", "-q", "--", "a"]))
        self.assertFalse(SHAPES.git_shape_ok(["git", "--no-pager", "ls-files", "-z", "--", "a"]))
        self.assertFalse(self.ok("check-attr", "-q", "--", "a"))
        self.assertFalse(self.ok("cat-file", "-p", "HEAD:a"))   # `cat-file` is allowed in two forms only
        self.assertFalse(self.ok("hash-object", "a"))


if __name__ == "__main__":
    unittest.main()
