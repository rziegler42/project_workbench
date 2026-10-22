"""The helper's `remove` (plan `2026-10-22-code-work-commit`, increment D).

Real repositories and real files. Every refusal is checked by what it leaves behind: nothing is deleted,
and nothing outside the repository is touched. The races use the helper's test hook, which runs between
the steps of the walk and swaps an entry for something else."""

import io
import json
import os
import stat
import unicodedata
import unittest
import unittest.mock

from tests import support_helpers

import support_git
from support_git import git, needs_git

H = support_helpers.load("code-work")
STANDARD = "/usr/bin" + os.pathsep + "/bin" + os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"


@needs_git
class Remove(support_git.Repo):
    def setUp(self):
        super().setUp()
        self.out_file = os.path.join(self.outside, "precious.txt")
        with open(self.out_file, "w") as handle:
            handle.write("keep me\n")
        self.out_dir = os.path.join(self.outside, "keep")
        os.mkdir(self.out_dir)
        self.out_inner = os.path.join(self.out_dir, "inner.txt")
        with open(self.out_inner, "w") as handle:
            handle.write("keep me too\n")
        self.addCleanup(setattr, H, "HOOK", None)

    def remove(self, *args, cwd=None, path=None):
        """Run `code-work remove <args>`; return ``(exit code, stdout, stderr)``."""
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": path or STANDARD, "HOME": self.scratch}, clear=True):
            code = H.main(["remove"] + list(args), out, err, cwd or self.repo)
        return code, out.getvalue(), err.getvalue()

    def preview(self, *paths, recursive=False):
        return self.remove(*(["--recursive"] if recursive else []), "--", *paths)

    def confirm(self, *paths, recursive=False):
        return self.remove(*(["--recursive"] if recursive else []), "--confirm", "--", *paths)

    def exists(self, rel):
        return os.path.lexists(os.path.join(self.repo, *rel.split("/")))

    def link(self, rel, target):
        full = os.path.join(self.repo, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        os.symlink(target, full)

    def assertRefused(self, result, text=None):
        code, out, err = result
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        if text:
            self.assertIn(text, err)

    def assertOutsideIntact(self):
        for path, text in ((self.out_file, "keep me\n"), (self.out_inner, "keep me too\n")):
            with open(path) as handle:
                self.assertEqual(text, handle.read())

    def tree(self):
        found = []
        for current, dirs, files in os.walk(self.repo):
            if ".git" in dirs:
                dirs.remove(".git")
            found.extend(os.path.relpath(os.path.join(current, name), self.repo) for name in dirs + files)
        return sorted(found)


class Basics(Remove):
    def test_a_preview_names_the_targets_and_removes_nothing(self):
        self.write("b.txt", "b\n")
        self.write("d/x.txt", "x\n")
        before = self.tree()
        code, out, err = self.preview("b.txt", "d", recursive=True)
        self.assertEqual((0, ""), (code, err))
        report = json.loads(out)
        self.assertEqual("preview", report["status"])
        self.assertEqual([{"path": "b.txt", "kind": "file"}, {"path": "d", "kind": "directory", "entries": 1}],
                         report["targets"])
        self.assertIn("--confirm", report["next_action"])
        self.assertEqual(before, self.tree())

    def test_confirm_removes_a_file_and_says_so(self):
        self.write("b.txt", "b\n")
        code, out, err = self.confirm("b.txt")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(("removed", [{"path": "b.txt", "kind": "file"}]),
                         (json.loads(out)["status"], json.loads(out)["targets"]))
        self.assertFalse(self.exists("b.txt"))
        self.assertTrue(self.exists("a.txt"))

    def test_a_tracked_file_leaves_the_work_tree_and_the_index_alone(self):
        before = git(self.repo, "ls-files", "-s").stdout
        self.assertEqual(0, self.confirm("a.txt")[0])
        self.assertFalse(self.exists("a.txt"))
        self.assertEqual(before, git(self.repo, "ls-files", "-s").stdout)

    def test_a_directory_needs_recursive_and_is_removed_whole(self):
        self.write("d/x.txt", "x\n")
        self.write("d/e/y.txt", "y\n")
        self.write("d/e/f/z.txt", "z\n")
        self.assertRefused(self.confirm("d"), "--recursive")
        self.assertTrue(self.exists("d/e/f/z.txt"))
        code, out, err = self.confirm("d", recursive=True)
        self.assertEqual((0, ""), (code, err))
        self.assertFalse(self.exists("d"))

    def test_recursive_on_a_file_still_removes_only_the_file(self):
        self.write("b.txt", "b\n")
        self.assertEqual(0, self.confirm("b.txt", recursive=True)[0])
        self.assertFalse(self.exists("b.txt"))
        self.assertTrue(self.exists("a.txt"))

    def test_a_link_is_removed_and_what_it_points_to_is_not(self):
        self.link("l", self.out_file)
        self.link("ld", self.out_dir)
        code, out, err = self.confirm("l", "ld")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["symlink", "symlink"], [t["kind"] for t in json.loads(out)["targets"]])
        self.assertFalse(self.exists("l") or self.exists("ld"))
        self.assertOutsideIntact()

    def test_links_inside_a_directory_are_removed_without_being_followed(self):
        self.link("d/l", self.out_file)
        self.link("d/ld", self.out_dir)
        self.assertEqual(0, self.confirm("d", recursive=True)[0])
        self.assertFalse(self.exists("d"))
        self.assertOutsideIntact()

    def test_an_empty_directory_a_pipe_and_an_ignored_file_are_removed(self):
        os.makedirs(os.path.join(self.repo, "empty"))
        os.mkfifo(os.path.join(self.repo, "pipe"))
        self.write(".gitignore", "ignored.txt\n")
        self.write("ignored.txt", "i\n")
        code, out, err = self.confirm("empty", "pipe", "ignored.txt", recursive=True)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["directory", "other", "file"], [t["kind"] for t in json.loads(out)["targets"]])
        self.assertFalse(any(self.exists(name) for name in ("empty", "pipe", "ignored.txt")))

    def test_paths_are_read_from_the_repository_root_whatever_the_directory(self):
        self.write("sub/c.txt", "c\n")
        self.write("c.txt", "root\n")
        self.assertEqual(0, self.remove("--confirm", "--", "c.txt", cwd=os.path.join(self.repo, "sub"))[0])
        self.assertFalse(self.exists("c.txt"))
        self.assertTrue(self.exists("sub/c.txt"))

    def test_a_file_that_is_not_readable_is_still_removed(self):
        self.write("b.txt", "b\n", mode=0)
        self.assertEqual(0, self.confirm("b.txt")[0])
        self.assertFalse(self.exists("b.txt"))

    def test_a_cleared_environment_without_git_in_the_path_is_refused(self):
        self.write("b.txt", "b\n")
        self.assertRefused(self.remove("--confirm", "--", "b.txt", path=self.outside), "git was not found")
        self.assertTrue(self.exists("b.txt"))


class Arguments(Remove):
    def test_each_malformed_command_line_is_refused(self):
        self.write("b.txt", "b\n")
        for argv in (["b.txt"], ["--confirm", "b.txt"], ["--"], ["--confirm", "--"], [],
                     ["--force", "--", "b.txt"], ["--confirm=1", "--", "b.txt"],
                     ["--confirm", "--confirm", "--", "b.txt"], ["--recursive", "--recursive", "--", "b.txt"]):
            with self.subTest(argv=argv):
                self.assertRefused(self.remove(*argv))
        self.assertTrue(self.exists("b.txt"))

    def test_too_many_paths_are_refused(self):
        self.assertRefused(self.remove("--", *["p%d" % number for number in range(H.MAX_PATHS + 1)]))


class Paths(Remove):
    def test_each_unsafe_or_inexact_spelling_is_refused_and_nothing_is_removed(self):
        self.write("b.txt", "b\n")
        self.write("d/x.txt", "x\n")
        for name in ("*", "b.t?t", "[b].txt", "-b.txt", "\ufe52git"):
            self.write(name, "real\n")
        spellings = ["", ".", "..", "/etc/passwd", "d/../b.txt", "./b.txt", "d//x.txt", "d/", "*", "b.t?t",
                     "[b].txt", "-b.txt", "--", ".git", ".GIT/config", ".git ", ".git.", "d/.git", "d/.Git/x",
                     "git~1", "a:b", "d\\x.txt", "missing.txt", "d/missing.txt", "missing/x.txt", "x" * 5000,
                     "b.txt\n", "b\ttxt", ".g\u200cit", "\ufe52git"]
        before = self.tree()
        for spelling in spellings:
            with self.subTest(path=spelling):
                args = ["--confirm", "--", spelling] if spelling != "--" else ["--confirm", "--", "--", "b.txt"]
                self.assertRefused(self.remove(*args))
        self.assertEqual(before, self.tree())

    def test_one_bad_path_stops_the_others_from_being_removed(self):
        self.write("b.txt", "b\n")
        self.assertRefused(self.confirm("b.txt", "missing.txt"))
        self.assertTrue(self.exists("b.txt"))

    def test_the_git_directory_is_never_a_target_in_any_spelling(self):
        for spelling in (".git", ".GIT", ".Git/HEAD", ".git/objects", "./.git"):
            with self.subTest(path=spelling):
                self.assertRefused(self.confirm(spelling, recursive=True), "")
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".git", "HEAD")))

    def test_overlapping_targets_are_refused_whatever_their_order_or_spelling(self):
        self.write("d/x.txt", "x\n")
        self.write("caf\u00e9.txt", "x\n")
        for names in (["d", "d/x.txt"], ["d/x.txt", "d"], ["d", "d"], ["a.txt", "A.txt"], ["d", "D/x.txt"],
                      ["d/x.txt", "d/X.TXT"], ["caf\u00e9.txt", unicodedata.normalize("NFD", "caf\u00e9.txt")]):
            with self.subTest(names=names):
                self.assertRefused(self.confirm(*names, recursive=True), "overlapping")
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_link_at_a_parent_is_refused_and_nothing_behind_it_is_touched(self):
        self.link("sub", self.out_dir)
        self.link("toGit", ".git")
        self.assertRefused(self.confirm("sub/inner.txt"))
        self.assertRefused(self.confirm("toGit/HEAD"))
        self.assertOutsideIntact()
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".git", "HEAD")))

    def test_a_link_to_the_repository_root_is_removed_as_a_link_only(self):
        self.link("up", ".")
        self.assertEqual(0, self.confirm("up", recursive=True)[0])
        self.assertFalse(self.exists("up"))
        self.assertTrue(self.exists("a.txt"))
        self.assertTrue(os.path.isdir(os.path.join(self.repo, ".git")))


class NestedRepositories(Remove):
    def nested(self, where):
        full = os.path.join(self.repo, *where.split("/"))
        os.makedirs(full)
        git(full, "init", "-q")
        with open(os.path.join(full, "f.txt"), "w") as handle:
            handle.write("f\n")

    def test_a_directory_that_holds_a_repository_at_any_depth_is_refused(self):
        for where in ("n", "d/n", "d/e/f/n"):
            with self.subTest(where=where):
                self.nested(where)
                self.assertRefused(self.confirm(where.split("/")[0], recursive=True), "nested repository")
                self.assertTrue(os.path.isdir(os.path.join(self.repo, *where.split("/"), ".git")))

    def test_a_path_inside_a_nested_repository_is_refused(self):
        self.nested("n")
        self.assertRefused(self.confirm("n/f.txt"), "nested Git repository")
        self.assertTrue(self.exists("n/f.txt"))

    def test_a_git_file_of_a_work_tree_or_submodule_counts(self):
        self.write("d/.git", "gitdir: ../elsewhere\n")
        self.write("d/x.txt", "x\n")
        self.assertRefused(self.confirm("d", recursive=True), "nested repository")
        self.assertRefused(self.confirm("d/x.txt"), "nested Git repository")
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_separate_git_directory_inside_a_subdirectory_is_refused(self):
        work = os.path.join(self.scratch, "work")
        os.mkdir(work)
        os.makedirs(os.path.join(self.repo, "d"))
        git(work, "init", "-q", "--separate-git-dir", os.path.join(self.repo, "d", "gd"))
        self.assertTrue(os.path.isdir(os.path.join(self.repo, "d", "gd", "objects")))
        self.assertRefused(self.confirm("d", recursive=True), "nested repository")
        self.assertTrue(os.path.isdir(os.path.join(self.repo, "d", "gd", "objects")))

    def test_a_bare_repository_in_a_directory_is_refused(self):
        os.makedirs(os.path.join(self.repo, "d"))
        git(os.path.join(self.repo, "d"), "init", "-q", "--bare", "bare.git")
        git(os.path.join(self.repo, "d"), "init", "-q", "--bare", "plain")
        self.assertRefused(self.confirm("d/plain", recursive=True), "nested repository")
        self.assertTrue(os.path.isdir(os.path.join(self.repo, "d", "plain", "objects")))

    def test_a_look_alike_of_dot_git_below_a_directory_counts_as_git_metadata(self):
        for number, name in enumerate((".g\u200cit", ".GIT", ".git ", ".git.", "git~1", "\ufe52git")):
            with self.subTest(name=name):
                self.write("d%d/%s" % (number, name), "gitdir: x\n")
                self.assertRefused(self.confirm("d%d" % number, recursive=True), "nested repository")
                self.assertTrue(self.exists("d%d/%s" % (number, name)))

    def test_a_git_directory_whose_parts_are_links_is_still_a_repository(self):
        real = os.path.join(self.outside, "real.git")
        git(self.outside, "init", "-q", "--bare", real)
        for where in ("d", "d/nb"):
            with self.subTest(where=where):
                full = os.path.join(self.repo, *where.split("/"))
                os.makedirs(full)
                with open(os.path.join(full, "HEAD"), "w") as handle:
                    handle.write("ref: refs/heads/main\n")
                os.symlink(os.path.join(real, "objects"), os.path.join(full, "objects"))
                os.symlink(os.path.join(real, "refs"), os.path.join(full, "refs"))
                self.assertRefused(self.confirm("d", recursive=True), "nested repository")
                self.assertTrue(os.path.islink(os.path.join(full, "refs")))
                if where == "d":
                    for name in ("HEAD", "objects", "refs"):
                        os.unlink(os.path.join(full, name))
                    os.rmdir(full)

    def test_a_linked_work_trees_git_directory_is_a_repository(self):
        os.makedirs(os.path.join(self.repo, "d", "wt"))
        for name in ("HEAD", "commondir"):
            self.write("d/wt/" + name, "x\n")
        self.assertRefused(self.confirm("d", recursive=True), "nested repository")
        self.assertTrue(self.exists("d/wt/commondir"))

    def test_the_repository_root_cannot_be_named_any_way(self):
        for spelling in (".", "", "d/..", "./", ".//"):
            with self.subTest(path=spelling):
                self.assertRefused(self.confirm(spelling, recursive=True))
        self.assertTrue(os.path.isdir(os.path.join(self.repo, ".git")))

    def test_a_directory_that_is_the_root_by_identity_is_refused(self):
        self.write("d/x.txt", "x\n")
        inode = os.lstat(os.path.join(self.repo, "d")).st_ino
        with unittest.mock.patch.object(H, "_same", lambda first, second: first.st_ino == inode):
            self.assertRefused(self.confirm("d", recursive=True), "repository root")
        self.assertTrue(self.exists("d/x.txt"))


class Limits(Remove):
    def test_a_tree_with_too_many_entries_is_refused(self):
        for number in range(8):
            self.write("d/f%d.txt" % number, "x\n")
        with unittest.mock.patch.object(H, "MAX_REMOVE_ENTRIES", 5):
            self.assertRefused(self.confirm("d", recursive=True), "more than")
        self.assertTrue(self.exists("d/f7.txt"))

    def test_a_directory_listing_over_the_bound_is_refused(self):
        for number in range(8):
            self.write("d/f%d.txt" % number, "x\n")
        with unittest.mock.patch.object(H, "MAX_REMOVE_ENTRIES", 5):
            self.assertRefused(self.confirm("d/f0.txt"), "more than")
        self.assertTrue(self.exists("d/f0.txt"))

    def test_a_tree_nested_too_deeply_is_refused(self):
        self.write("d/" + "/".join("n" for _ in range(30)) + "/x.txt", "x\n")
        with unittest.mock.patch.object(H, "MAX_REMOVE_DEPTH", 10):
            self.assertRefused(self.confirm("d", recursive=True), "deeper")
        self.assertTrue(self.exists("d"))

    def test_another_filesystem_inside_a_directory_is_refused(self):
        self.write("d/e/x.txt", "x\n")
        real = H._device
        calls = []

        def device(info):
            calls.append(info)
            return real(info) + (1 if stat.S_ISDIR(info.st_mode) and info.st_ino == self.inode("d/e") else 0)

        with unittest.mock.patch.object(H, "_device", device):
            self.assertRefused(self.confirm("d", recursive=True), "filesystem")
        self.assertTrue(self.exists("d/e/x.txt"))

    def test_another_filesystem_on_the_way_to_a_target_is_refused(self):
        self.write("d/x.txt", "x\n")
        real = H._device
        inode = self.inode("d")

        def device(info):
            return real(info) + (1 if info.st_ino == inode else 0)

        with unittest.mock.patch.object(H, "_device", device):
            self.assertRefused(self.confirm("d/x.txt"), "another filesystem")
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_target_directory_that_is_another_filesystem_is_refused(self):
        self.write("d/x.txt", "x\n")
        real = H._device
        inode = self.inode("d")
        with unittest.mock.patch.object(H, "_device", lambda info: real(info) + (info.st_ino == inode)):
            self.assertRefused(self.confirm("d", recursive=True), "another filesystem")
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_directory_that_becomes_another_filesystem_during_the_walk_stops_it(self):
        self.write("d/e/x.txt", "x\n")
        real = H._device
        inode = self.inode("d/e")
        armed = []
        H.HOOK = lambda stage, rel: armed.append(True) if (stage, rel) == ("entry", "d/e") else None
        with unittest.mock.patch.object(H, "_device", lambda info: real(info) + (bool(armed) and info.st_ino == inode)):
            code, out, err = self.confirm("d", recursive=True)
        self.assertEqual(1, code)
        self.assertIn("another filesystem", json.loads(out)["reason"])
        self.assertTrue(self.exists("d/e/x.txt"))

    def test_a_tree_that_grows_deeper_than_the_bound_during_the_walk_stops_it(self):
        self.write("d/e/x.txt", "x\n")
        H.HOOK = lambda stage, rel: setattr(H, "MAX_REMOVE_DEPTH", 1) if (stage, rel) == ("entry", "d") else None
        self.addCleanup(setattr, H, "MAX_REMOVE_DEPTH", H.MAX_REMOVE_DEPTH)
        code, out, err = self.confirm("d", recursive=True)
        self.assertEqual(1, code)
        self.assertIn("deeper", json.loads(out)["reason"])
        self.assertTrue(self.exists("d/e/x.txt"))

    def test_the_bound_on_entries_counts_the_whole_tree_and_not_one_directory(self):
        for sub in "efg":
            for number in range(3):
                self.write("d/%s/f%d.txt" % (sub, number), "x\n")
        with unittest.mock.patch.object(H, "MAX_REMOVE_ENTRIES", 8):
            self.assertRefused(self.confirm("d", recursive=True), "more than")
        self.assertTrue(self.exists("d/g/f2.txt"))

    def test_a_directory_swapped_while_it_is_being_checked_is_refused(self):
        self.write("d/e/x.txt", "x\n")
        for stage, rel in (("planning", "d"), ("scanning", "e")):
            with self.subTest(stage=stage):
                def swap(seen, where, stage=stage, rel=rel):
                    if (seen, where) == (stage, rel):
                        H.HOOK = None
                        target = "d" if stage == "planning" else "d/e"
                        full = os.path.join(self.repo, *target.split("/"))
                        os.rename(full, full + "-old")
                        os.mkdir(full)
                H.HOOK = swap
                self.assertRefused(self.confirm("d", recursive=True), "changed while it was being checked")
                H.HOOK = None
                self.assertTrue(self.exists("d-old" if stage == "planning" else "d/e-old"))
                os.rmdir(os.path.join(self.repo, "d" if stage == "planning" else "d/e"))
                os.rename(os.path.join(self.repo, "d-old" if stage == "planning" else "d/e-old"),
                          os.path.join(self.repo, "d" if stage == "planning" else "d/e"))

    def inode(self, rel):
        return os.lstat(os.path.join(self.repo, *rel.split("/"))).st_ino


class Work(Remove):
    def test_many_targets_in_one_directory_list_it_once_per_phase(self):
        for number in range(6):
            self.write("big/f%d.txt" % number, "x\n")
        listed = []
        real = H._entries
        with unittest.mock.patch.object(H, "_entries", lambda fd: listed.append(fd) or real(fd)):
            self.assertEqual(0, self.confirm(*["big/f%d.txt" % n for n in range(6)])[0])
        self.assertEqual(2, len(listed))


class Races(Remove):
    """The hook runs at "entry" (before an entry is examined), "checked" (after, before it is acted on) and
    "listed" (after a directory was listed, before its entries are touched)."""

    def hook(self, stage, rel, action):
        done = []

        def run(seen_stage, seen_rel):
            if seen_stage == stage and seen_rel == rel and not done:
                done.append(True)
                action()

        H.HOOK = run
        return done

    def replace(self, rel, make):
        full = os.path.join(self.repo, *rel.split("/"))

        def action():
            if os.path.isdir(full) and not os.path.islink(full):
                for current, dirs, files in os.walk(full, topdown=False):
                    for name in files:
                        os.unlink(os.path.join(current, name))
                    for name in dirs:
                        path = os.path.join(current, name)
                        os.unlink(path) if os.path.islink(path) else os.rmdir(path)
                os.rmdir(full)
            else:
                os.unlink(full)
            make(full)

        return action

    def stopped(self, result):
        code, out, err = result
        self.assertEqual(1, code, err)
        self.assertTrue(err.startswith("stopped: "), err)
        return json.loads(out)

    def test_a_file_swapped_for_a_link_before_it_is_examined_loses_only_the_link(self):
        self.write("d/x.txt", "x\n")
        self.write("d/y.txt", "y\n")
        done = self.hook("entry", "d/x.txt", self.replace("d/x.txt", lambda full: os.symlink(self.out_file, full)))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertTrue(done)
        self.assertIn("changed type", report["reason"])
        self.assertEqual("d", report["stopped_in"])
        self.assertOutsideIntact()
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_file_swapped_for_a_link_after_it_was_examined_loses_only_the_link(self):
        self.write("d/x.txt", "x\n")
        done = self.hook("checked", "d/x.txt", self.replace("d/x.txt", lambda full: os.symlink(self.out_file, full)))
        self.assertEqual(0, self.confirm("d", recursive=True)[0])
        self.assertTrue(done)
        self.assertOutsideIntact()
        self.assertFalse(self.exists("d"))

    def test_a_directory_swapped_for_a_link_to_a_directory_is_not_followed(self):
        self.write("d/e/x.txt", "x\n")
        done = self.hook("entry", "d/e", self.replace("d/e", lambda full: os.symlink(self.out_dir, full)))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertTrue(done)
        self.assertEqual(["d"], [report["stopped_in"]])
        self.assertOutsideIntact()

    def test_a_directory_swapped_for_a_link_after_it_was_examined_is_not_followed(self):
        self.write("d/e/x.txt", "x\n")
        done = self.hook("checked", "d/e", self.replace("d/e", lambda full: os.symlink(self.out_dir, full)))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertTrue(done)
        self.assertIn("no longer a directory", report["reason"])
        self.assertOutsideIntact()

    def test_a_file_swapped_for_a_directory_is_left_with_its_contents(self):
        self.write("d/x.txt", "x\n")

        def make(full):
            os.mkdir(full)
            with open(os.path.join(full, "inner.txt"), "w") as handle:
                handle.write("inner\n")

        self.hook("checked", "d/x.txt", self.replace("d/x.txt", make))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertIn("could not be removed", report["reason"])
        self.assertTrue(self.exists("d/x.txt/inner.txt"))

    def test_a_directory_swapped_for_another_directory_is_not_removed_as_the_first(self):
        self.write("d/e/x.txt", "x\n")

        def make(full):
            os.mkdir(full)
            with open(os.path.join(full, "other.txt"), "w") as handle:
                handle.write("other\n")

        self.hook("entry", "d/e", self.replace("d/e", make))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertIn("replaced", report["reason"])
        self.assertTrue(self.exists("d/e/other.txt"))

    def test_a_git_directory_created_in_a_directory_during_the_walk_is_left_and_stops_it(self):
        self.write("d/x.txt", "x\n")

        def make():
            os.makedirs(os.path.join(self.repo, "d", ".git"))
            with open(os.path.join(self.repo, "d", ".git", "HEAD"), "w") as handle:
                handle.write("ref: refs/heads/main\n")

        self.hook("listed", "d", make)
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertIn(".git", report["reason"])
        self.assertTrue(self.exists("d/.git/HEAD"))
        self.assertFalse(self.exists("d/x.txt"))

    def test_a_file_added_to_a_directory_during_the_walk_is_left_and_stops_it(self):
        self.write("d/x.txt", "x\n")
        self.hook("listed", "d", lambda: self.write("d/new.txt", "n\n"))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertIn("not removed", report["reason"])
        self.assertTrue(self.exists("d/new.txt"))

    def test_a_nested_repository_that_appears_before_a_directory_is_listed_stops_the_walk(self):
        self.write("d/e/x.txt", "x\n")
        self.hook("entry", "d/e", lambda: git(os.path.join(self.repo, "d", "e"), "init", "-q"))
        report = self.stopped(self.confirm("d", recursive=True))
        self.assertIn("a .git entry", report["reason"])
        self.assertTrue(os.path.isdir(os.path.join(self.repo, "d", "e", ".git")))

    def test_a_parent_swapped_for_a_link_before_its_target_is_removed_is_not_followed(self):
        self.write("one/x.txt", "x\n")
        self.write("two/y.txt", "y\n")
        with open(os.path.join(self.out_dir, "y.txt"), "w") as handle:
            handle.write("outside y\n")

        def make(full):
            os.symlink(self.out_dir, full)

        self.hook("entry", "one/x.txt", self.replace("two", make))
        report = self.stopped(self.confirm("one/x.txt", "two/y.txt"))
        self.assertEqual(["one/x.txt"], report["removed"])
        self.assertEqual("two/y.txt", report["stopped_in"])
        with open(os.path.join(self.out_dir, "y.txt")) as handle:
            self.assertEqual("outside y\n", handle.read())

    def test_the_report_names_what_was_removed_and_what_was_not(self):
        self.write("one.txt", "1\n")
        self.write("d/x.txt", "x\n")
        self.write("three.txt", "3\n")
        self.hook("listed", "d", lambda: self.write("d/new.txt", "n\n"))
        report = self.stopped(self.confirm("one.txt", "d", "three.txt", recursive=True))
        self.assertEqual(["one.txt"], report["removed"])
        self.assertEqual("d", report["stopped_in"])
        self.assertEqual(["three.txt"], report["not_removed"])
        self.assertTrue(self.exists("three.txt"))
        self.assertFalse(self.exists("one.txt"))


class BetweenPreviewAndConfirm(Remove):
    def test_a_file_replaced_by_a_link_is_removed_as_the_link_it_now_is(self):
        self.write("b.txt", "b\n")
        self.assertEqual("file", json.loads(self.preview("b.txt")[1])["targets"][0]["kind"])
        os.unlink(os.path.join(self.repo, "b.txt"))
        os.symlink(self.out_file, os.path.join(self.repo, "b.txt"))
        code, out, err = self.confirm("b.txt")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual("symlink", json.loads(out)["targets"][0]["kind"])
        self.assertFalse(self.exists("b.txt"))
        self.assertOutsideIntact()

    def test_a_directory_replaced_by_one_that_holds_a_repository_is_refused(self):
        self.write("d/x.txt", "x\n")
        self.assertEqual(0, self.preview("d", recursive=True)[0])
        os.makedirs(os.path.join(self.repo, "d", "n"))
        git(os.path.join(self.repo, "d", "n"), "init", "-q")
        self.assertRefused(self.confirm("d", recursive=True), "nested repository")
        self.assertTrue(self.exists("d/x.txt"))

    def test_a_directory_replaced_by_a_file_needs_no_recursive_and_is_removed_as_a_file(self):
        self.write("d/x.txt", "x\n")
        self.assertEqual(0, self.preview("d", recursive=True)[0])
        os.unlink(os.path.join(self.repo, "d", "x.txt"))
        os.rmdir(os.path.join(self.repo, "d"))
        self.write("d", "now a file\n")
        self.assertEqual(0, self.confirm("d")[0])
        self.assertFalse(self.exists("d"))

    def test_a_file_replaced_by_a_directory_now_needs_recursive(self):
        self.write("b", "b\n")
        self.assertEqual(0, self.preview("b")[0])
        os.unlink(os.path.join(self.repo, "b"))
        self.write("b/x.txt", "x\n")
        self.assertRefused(self.confirm("b"), "--recursive")
        self.assertTrue(self.exists("b/x.txt"))


class GitUse(Remove):
    def test_only_read_commands_run_and_never_a_forbidden_one(self):
        self.write("d/x.txt", "x\n")
        directory = self.recording_git()
        path = directory + os.pathsep + STANDARD
        self.assertEqual(0, self.remove("--recursive", "--confirm", "--", "d", path=path)[0])
        commands = {arguments[0] for arguments, _ in self.runs()}
        self.assertTrue(commands)
        self.assertLessEqual(commands, {"rev-parse"})
        self.assertFalse(self.exists("d"))

    def test_a_repository_that_selects_a_program_may_still_have_files_removed(self):
        self.write("b.txt", "b\n")
        marker = os.path.join(self.scratch, "ran")
        script = os.path.join(self.outside, "tool")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(script, 0o755)
        self.config("core.fsmonitor", script)
        self.assertEqual(0, self.confirm("b.txt")[0])
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(self.exists("b.txt"))


if __name__ == "__main__":
    unittest.main()
