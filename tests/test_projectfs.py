import hashlib
import os
import stat
import tempfile
import unittest

from workbench import projectfs, safefs, target
from workbench.projectfs import WriteConflict, Writer


class Fixture(unittest.TestCase):
    """A project directory, a store, a directory outside both, and a writer for the project."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.store = os.path.join(self.base, "store")
        os.mkdir(self.store)
        self.root = os.path.join(self.base, "proj")
        os.mkdir(self.root)
        self.outside = os.path.join(self.base, "outside")
        os.mkdir(self.outside)
        self.addCleanup(self.clear_hook)

    def clear_hook(self):
        safefs._hook = None

    def writer(self, path=None):
        if path is None:
            # Classification refuses a directory that already holds links and stray files,
            # which is what these tests need, so the target is held directly.
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            held = target.Target(self.root, "existing", fd, "proj", os.fstat(fd))
        else:
            held = target.open_target(path, self.store, home=self.base + "/nohome")
        self.addCleanup(held.close)
        return Writer(held)

    def read(self, rel):
        with open(os.path.join(self.root, *rel.split("/")), "rb") as handle:
            return handle.read()


class WriterTest(Fixture):

    def test_creates_file_exclusively_and_records_it(self):
        writer = self.writer()
        writer.create_file("docs/a.md", b"hello")
        writer.create_file("b.txt", b"")
        self.assertEqual(b"hello", self.read("docs/a.md"))
        self.assertEqual(["docs/", "docs/a.md", "b.txt"], writer.written)

    def test_create_git_makes_the_skeleton_and_refuses_any_existing_git(self):
        skeleton = (("objects", None), ("objects/pack", None), ("HEAD", b"ref: x\n"))
        writer = self.writer()
        writer.create_git(skeleton)
        self.assertEqual([".git/"], writer.written)
        self.assertEqual(b"ref: x\n", self.read(".git/HEAD"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".git", "objects", "pack")))
        with self.assertRaises(WriteConflict):
            writer.create_git(skeleton)

    def test_create_git_does_not_follow_a_planted_link(self):
        os.symlink(self.outside, os.path.join(self.root, ".git"))
        with self.assertRaises(WriteConflict):
            self.writer().create_git((("HEAD", b"x"),))
        self.assertEqual([], os.listdir(self.outside))

    def test_existing_file_is_a_conflict_not_overwritten(self):
        with open(os.path.join(self.root, "a"), "wb") as handle:
            handle.write(b"keep")
        writer = self.writer()
        with self.assertRaises(WriteConflict):
            writer.create_file("a", b"new")
        self.assertEqual(b"keep", self.read("a"))
        self.assertEqual([], writer.written)

    def test_existing_directory_at_a_file_path_is_a_conflict(self):
        os.mkdir(os.path.join(self.root, "d"))
        with self.assertRaises(WriteConflict):
            self.writer().create_file("d", b"x")

    def test_symlink_at_any_component_is_a_conflict(self):
        os.symlink(self.outside, os.path.join(self.root, "link"))
        os.symlink(self.outside, os.path.join(self.root, "target.txt"))
        os.mkdir(os.path.join(self.root, ".workbench"))
        os.symlink(self.outside, os.path.join(self.root, ".workbench", "local"))
        os.mkdir(os.path.join(self.base, "wbtarget"))
        os.symlink(os.path.join(self.base, "wbtarget"), os.path.join(self.root, "wblink"))
        for rel in ("target.txt", "link/x", ".workbench/local/incomplete", "wblink/y"):
            writer = self.writer()
            with self.assertRaises(WriteConflict, msg=rel):
                writer.create_file(rel, b"x")
        self.assertEqual([], os.listdir(self.outside))
        self.assertEqual([], os.listdir(os.path.join(self.base, "wbtarget")))
        with self.assertRaises(WriteConflict):
            self.writer().create_dir("link/sub")
        self.assertEqual([], os.listdir(self.outside))

    def test_parent_swapped_for_link_after_check_does_not_escape(self):
        os.mkdir(os.path.join(self.root, "docs"))
        moved = os.path.join(self.base, "moved")

        def swap(stage, **info):
            if stage == "projectfs_walked":
                os.rename(os.path.join(self.root, "docs"), moved)
                os.symlink(self.outside, os.path.join(self.root, "docs"))

        safefs._hook = swap
        self.writer().create_file("docs/a.md", b"x")
        self.assertEqual([], os.listdir(self.outside))
        self.assertEqual(["a.md"], os.listdir(moved))

    def test_parent_swapped_for_link_before_the_walk_is_a_conflict(self):
        os.mkdir(os.path.join(self.root, "docs"))

        def swap(stage, **info):
            if stage == "projectfs_validated":
                os.rmdir(os.path.join(self.root, "docs"))
                os.symlink(self.outside, os.path.join(self.root, "docs"))

        safefs._hook = swap
        with self.assertRaises(WriteConflict):
            self.writer().create_file("docs/a.md", b"x")
        self.assertEqual([], os.listdir(self.outside))

    def test_executable_bit_only_when_asked(self):
        writer = self.writer()
        writer.create_file("run.sh", b"#!/bin/sh\n", executable=True)
        writer.create_file("plain.txt", b"x")
        self.assertEqual(0o755, stat.S_IMODE(os.stat(os.path.join(self.root, "run.sh")).st_mode))
        self.assertFalse(os.stat(os.path.join(self.root, "plain.txt")).st_mode & stat.S_IXUSR)

    def test_paths_are_validated(self):
        writer = self.writer()
        for rel in ("", "/abs", "a/../b", ".git/config", "a//b", "a\\b"):
            with self.assertRaises(safefs.SafeFsError, msg=rel):
                writer.create_file(rel, b"x")
        with self.assertRaises(safefs.SafeFsError):
            writer.create_file("ok", "text")
        self.assertEqual([], os.listdir(self.root))

    def test_create_dir_accepts_an_existing_real_directory(self):
        os.mkdir(os.path.join(self.root, "d"))
        writer = self.writer()
        writer.create_dir("d")
        writer.create_dir("d/e/f")
        self.assertEqual(["d/e/", "d/e/f/"], writer.written)

    def test_make_target_inside_held_parent(self):
        path = os.path.join(self.base, "fresh")
        writer = self.writer(path)
        with self.assertRaises(safefs.SafeFsError):
            writer.create_file("a", b"x")
        writer.make_target()
        self.assertTrue(writer.made_target)
        self.assertEqual("new-empty", writer.target.state)
        writer.target.recheck()
        writer.create_file("a", b"x")
        with open(os.path.join(path, "a"), "rb") as handle:
            self.assertEqual(b"x", handle.read())
        with self.assertRaises(safefs.SafeFsError):
            writer.make_target()

    def test_make_target_refused_when_parent_swapped(self):
        parent = os.path.join(self.base, "outer")
        os.mkdir(parent)
        writer = self.writer(os.path.join(parent, "fresh"))
        os.rename(parent, os.path.join(self.base, "outer2"))
        os.mkdir(parent)
        with self.assertRaises(target.TargetError):
            writer.make_target()
        self.assertEqual([], os.listdir(parent))
        self.assertEqual([], os.listdir(os.path.join(self.base, "outer2")))

    def test_make_target_conflicts_when_it_appeared(self):
        path = os.path.join(self.base, "fresh")
        writer = self.writer(path)
        os.mkdir(path)
        with self.assertRaises(target.TargetError):
            writer.make_target()

    def test_remove_marker_only_removes_the_marker(self):
        writer = self.writer()
        writer.create_file(".workbench/local/incomplete", b"")
        writer.create_file(".workbench/local/keep", b"k")
        writer.create_file(".workbench/manifest.json", b"{}")
        writer.remove_marker()
        self.assertFalse(os.path.exists(os.path.join(self.root, ".workbench/local/incomplete")))
        self.assertEqual(["keep"], os.listdir(os.path.join(self.root, ".workbench/local")))
        self.assertTrue(os.path.exists(os.path.join(self.root, ".workbench/manifest.json")))
        with self.assertRaises(safefs.SafeFsError):
            writer.remove_marker()

    def test_remove_marker_refuses_a_link_or_directory(self):
        os.makedirs(os.path.join(self.root, ".workbench", "local"))
        os.mkdir(os.path.join(self.root, ".workbench", "local", "incomplete"))
        with self.assertRaises(WriteConflict):
            self.writer().remove_marker()
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".workbench/local/incomplete")))

    def test_failed_write_leaves_earlier_files_and_lists_them(self):
        writer = self.writer()
        writer.create_file("one", b"1")
        with open(os.path.join(self.root, "two"), "wb") as handle:
            handle.write(b"existing")
        with self.assertRaises(WriteConflict):
            writer.create_file("two", b"2")
        self.assertEqual(["one"], writer.written)
        self.assertEqual(b"1", self.read("one"))
        self.assertEqual(b"existing", self.read("two"))

    def test_a_closed_target_is_refused(self):
        writer = self.writer()
        writer.target.close()
        with self.assertRaises(safefs.SafeFsError):
            writer.create_file("a", b"x")
        self.assertEqual("incomplete", os.path.basename(projectfs.MARKER))


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ReadReplaceTest(Fixture):
    """`read_file` and `replace_file`."""

    def put(self, rel, data, mode=None):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        if mode is not None:
            os.chmod(path, mode)
        return path

    def litter(self):
        return [n for n in os.listdir(self.root) if n.endswith(".tmp")]

    # --- read ---

    def test_read_returns_bytes_hash_and_mode(self):
        self.put("docs/a.md", b"hello", 0o640)
        got = self.writer().read_file("docs/a.md")
        self.assertEqual((b"hello", sha(b"hello"), 0o640), tuple(got))

    def test_read_of_a_missing_file_or_directory_is_none(self):
        writer = self.writer()
        self.assertIsNone(writer.read_file("nope"))
        self.assertIsNone(writer.read_file("no/dir/a"))

    def test_read_of_an_empty_file(self):
        self.put("e", b"")
        self.assertEqual(sha(b""), self.writer().read_file("e").hash)

    def test_read_refuses_a_link_a_directory_and_a_link_above(self):
        self.put("real", b"secret")
        os.symlink(os.path.join(self.root, "real"), os.path.join(self.root, "link"))
        os.mkdir(os.path.join(self.root, "d"))
        os.symlink(self.outside, os.path.join(self.root, "up"))
        self.put("f", b"x")
        for rel in ("link", "d", "up/x", "f/x"):
            with self.subTest(rel=rel), self.assertRaises(WriteConflict):
                self.writer().read_file(rel)

    def test_read_refuses_a_fifo_without_blocking(self):
        os.mkfifo(os.path.join(self.root, "pipe"))
        with self.assertRaises(WriteConflict):
            self.writer().read_file("pipe")

    def test_read_refuses_a_file_over_the_limit(self):
        self.put("big", b"x" * 20)
        original = safefs.MAX_FILE_BYTES
        safefs.MAX_FILE_BYTES = 10
        self.addCleanup(setattr, safefs, "MAX_FILE_BYTES", original)
        with self.assertRaises(safefs.SafeFsError):
            self.writer().read_file("big")

    def test_read_and_replace_refuse_a_file_with_another_hard_link(self):
        outside = os.path.join(self.outside, "victim")
        with open(outside, "wb") as handle:
            handle.write(b"OUTSIDE")
        os.link(outside, os.path.join(self.root, "linked"))
        with self.assertRaises(WriteConflict):
            self.writer().read_file("linked")
        with self.assertRaises(WriteConflict):
            self.writer().replace_file("linked", sha(b"OUTSIDE"), b"new")
        with open(outside, "rb") as handle:
            self.assertEqual(b"OUTSIDE", handle.read())
        self.assertEqual([], self.litter())

    def test_read_validates_the_path(self):
        for rel in ("", "/abs", "a/../b", "a//b"):
            with self.subTest(rel=rel), self.assertRaises(safefs.SafeFsError):
                self.writer().read_file(rel)

    def test_read_with_a_parent_swapped_after_the_walk_stays_inside(self):
        self.put("docs/a.md", b"inside")
        with open(os.path.join(self.outside, "a.md"), "wb") as handle:
            handle.write(b"OUTSIDE")
        moved = os.path.join(self.base, "moved")

        def swap(stage, **info):
            if stage == "projectfs_walked":
                os.rename(os.path.join(self.root, "docs"), moved)
                os.symlink(self.outside, os.path.join(self.root, "docs"))

        safefs._hook = swap
        self.assertEqual(b"inside", self.writer().read_file("docs/a.md").data)

    # --- replace ---

    def test_replace_changes_the_content_and_records_the_path(self):
        self.put("docs/a.md", b"old")
        writer = self.writer()
        writer.replace_file("docs/a.md", sha(b"old"), b"new")
        self.assertEqual(b"new", self.read("docs/a.md"))
        self.assertEqual(["docs/a.md"], writer.written)
        self.assertEqual(["a.md"], os.listdir(os.path.join(self.root, "docs")))

    def test_replace_to_empty_and_from_empty(self):
        self.put("a", b"")
        writer = self.writer()
        writer.replace_file("a", sha(b""), b"x")
        writer.replace_file("a", sha(b"x"), b"")
        self.assertEqual(b"", self.read("a"))

    def test_replace_with_a_different_hash_refuses_and_changes_nothing(self):
        self.put("a", b"edited by the owner")
        writer = self.writer()
        with self.assertRaises(WriteConflict):
            writer.replace_file("a", sha(b"old"), b"new")
        self.assertEqual(b"edited by the owner", self.read("a"))
        self.assertEqual([], writer.written)
        self.assertEqual([], self.litter())

    def test_replace_of_a_missing_file_or_directory_refuses(self):
        for rel in ("nope", "no/dir/a"):
            with self.subTest(rel=rel), self.assertRaises(WriteConflict):
                self.writer().replace_file(rel, sha(b""), b"x")
        self.assertEqual([], os.listdir(self.root))

    def test_replace_of_a_link_or_directory_refuses_and_leaves_the_victim(self):
        victim = os.path.join(self.outside, "victim")
        with open(victim, "wb") as handle:
            handle.write(b"victim")
        os.symlink(victim, os.path.join(self.root, "link"))
        os.mkdir(os.path.join(self.root, "d"))
        os.symlink(self.outside, os.path.join(self.root, "up"))
        for rel in ("link", "d", "up/victim"):
            with self.subTest(rel=rel), self.assertRaises(WriteConflict):
                self.writer().replace_file(rel, sha(b"victim"), b"new")
        with open(victim, "rb") as handle:
            self.assertEqual(b"victim", handle.read())
        self.assertEqual(["victim"], os.listdir(self.outside))
        self.assertEqual([], self.litter())

    def test_a_link_planted_at_the_file_between_check_and_rename_is_replaced_not_followed(self):
        victim = os.path.join(self.outside, "victim")
        with open(victim, "wb") as handle:
            handle.write(b"victim")
        path = self.put("a", b"old")

        def plant(stage, **info):
            if stage == "projectfs_checked":
                os.unlink(path)
                os.symlink(victim, path)

        safefs._hook = plant
        self.writer().replace_file("a", sha(b"old"), b"new")
        with open(victim, "rb") as handle:
            self.assertEqual(b"victim", handle.read())
        self.assertFalse(os.path.islink(path))
        self.assertEqual(b"new", self.read("a"))

    def test_a_directory_planted_between_check_and_rename_refuses_and_removes_the_sibling(self):
        path = self.put("a", b"old")

        def plant(stage, **info):
            if stage == "projectfs_checked":
                os.unlink(path)
                os.mkdir(path)

        safefs._hook = plant
        writer = self.writer()
        with self.assertRaises(safefs.SafeFsError):
            writer.replace_file("a", sha(b"old"), b"new")
        self.assertTrue(os.path.isdir(path))
        self.assertEqual([], self.litter())
        self.assertEqual([], writer.written)

    def test_parent_swapped_for_a_link_after_the_walk_does_not_escape(self):
        self.put("docs/a.md", b"old")
        with open(os.path.join(self.outside, "a.md"), "wb") as handle:
            handle.write(b"OUTSIDE")
        moved = os.path.join(self.base, "moved")

        def swap(stage, **info):
            if stage == "projectfs_walked":
                os.rename(os.path.join(self.root, "docs"), moved)
                os.symlink(self.outside, os.path.join(self.root, "docs"))

        safefs._hook = swap
        self.writer().replace_file("docs/a.md", sha(b"old"), b"new")
        with open(os.path.join(self.outside, "a.md"), "rb") as handle:
            self.assertEqual(b"OUTSIDE", handle.read())
        self.assertEqual(["a.md"], os.listdir(moved))
        with open(os.path.join(moved, "a.md"), "rb") as handle:
            self.assertEqual(b"new", handle.read())
        self.assertEqual(["a.md"], os.listdir(self.outside))

    def test_parent_swapped_for_a_link_before_the_walk_refuses(self):
        self.put("docs/a.md", b"old")

        def swap(stage, **info):
            if stage == "projectfs_validated":
                os.rename(os.path.join(self.root, "docs"), os.path.join(self.base, "moved"))
                os.symlink(self.outside, os.path.join(self.root, "docs"))

        safefs._hook = swap
        with self.assertRaises(WriteConflict):
            self.writer().replace_file("docs/a.md", sha(b"old"), b"new")
        self.assertEqual([], os.listdir(self.outside))

    def test_a_taken_sibling_name_refuses_and_is_never_touched(self):
        self.put("a", b"old")
        self.put("planted.tmp", b"keep")
        taken = ".workbench-%d-%s.tmp" % (os.getpid(), "aabbccddeeff")
        self.put(taken, b"keep")
        saved = os.urandom
        os.urandom = lambda n: bytes.fromhex("aabbccddeeff")
        self.addCleanup(setattr, os, "urandom", saved)
        with self.assertRaises(WriteConflict):
            self.writer().replace_file("a", sha(b"old"), b"new")
        self.assertEqual(b"keep", self.read(taken))
        self.assertEqual(b"old", self.read("a"))

    def test_the_sibling_is_removed_when_the_write_fails(self):
        self.put("a", b"old")
        real = os.fsync

        def broken(fd):
            raise OSError(5, "disk")

        os.fsync = broken
        self.addCleanup(setattr, os, "fsync", real)
        with self.assertRaises(safefs.SafeFsError):
            self.writer().replace_file("a", sha(b"old"), b"new")
        self.assertEqual([], self.litter())
        self.assertEqual(b"old", self.read("a"))

    def test_replace_modes_under_umask_zero(self):
        self.put("plain", b"old", 0o644)
        self.put("run", b"old", 0o600)
        old = os.umask(0)
        self.addCleanup(os.umask, old)
        writer = self.writer()
        writer.replace_file("plain", sha(b"old"), b"x")
        writer.replace_file("run", sha(b"old"), b"#!/bin/sh\n", executable=True)
        self.assertEqual(0o644, self.mode("plain"))
        self.assertEqual(0o755, self.mode("run"))

    def mode(self, rel):
        return stat.S_IMODE(os.stat(os.path.join(self.root, rel)).st_mode)

    def test_replace_never_widens_a_private_file(self):
        for before, after in ((0o600, 0o600), (0o640, 0o640), (0o666, 0o644), (0o755, 0o644),
                              (0o700, 0o600), (0o4755, 0o644), (0o2644, 0o644)):
            with self.subTest(before=oct(before)):
                self.put("f", b"old", before)
                os.chmod(os.path.join(self.root, "f"), before)
                self.writer().replace_file("f", sha(b"old"), b"new")
                self.assertEqual(after, self.mode("f"))

    def test_replace_sets_no_setuid_or_setgid_bit_even_for_an_executable(self):
        self.put("f", b"old", 0o4755)
        self.writer().replace_file("f", sha(b"old"), b"new", executable=True)
        self.assertEqual(0o755, self.mode("f"))

    def test_the_sibling_is_private_until_the_hash_has_passed(self):
        self.put("f", b"old", 0o600)
        seen = []

        def look(stage, **info):
            if stage == "projectfs_checked":
                seen.extend(self.mode(n) for n in os.listdir(self.root) if n.endswith(".tmp"))

        safefs._hook = look
        self.writer().replace_file("f", sha(b"old"), b"new")
        self.assertEqual([0o600], seen)

    def test_a_failed_chmod_removes_the_sibling_and_leaves_the_original(self):
        self.put("f", b"old", 0o600)
        real = os.fchmod

        def broken(fd, mode):
            raise OSError(1, "no")

        os.fchmod = broken
        self.addCleanup(setattr, os, "fchmod", real)
        with self.assertRaises(safefs.SafeFsError):
            self.writer().replace_file("f", sha(b"old"), b"new")
        self.assertEqual([], self.litter())
        self.assertEqual(b"old", self.read("f"))

    def test_replace_validates_its_arguments(self):
        self.put("a", b"old")
        writer = self.writer()
        for rel in ("", "/abs", "a/../b", ".git/config"):
            with self.subTest(rel=rel), self.assertRaises(safefs.SafeFsError):
                writer.replace_file(rel, sha(b"old"), b"x")
        with self.assertRaises(safefs.SafeFsError):
            writer.replace_file("a", sha(b"old"), "text")
        self.assertEqual(b"old", self.read("a"))
        self.assertEqual([], self.litter())

    def test_replace_does_not_unlink_anything_but_its_own_sibling(self):
        self.put("a", b"old")
        self.put("b", b"other")
        self.writer().replace_file("a", sha(b"old"), b"new")
        self.assertEqual(["a", "b"], sorted(os.listdir(self.root)))
        self.assertEqual(b"other", self.read("b"))

    def test_a_closed_target_is_refused_for_read_and_replace(self):
        writer = self.writer()
        writer.target.close()
        with self.assertRaises(safefs.SafeFsError):
            writer.read_file("a")
        with self.assertRaises(safefs.SafeFsError):
            writer.replace_file("a", sha(b""), b"x")
        with self.assertRaises(safefs.SafeFsError):
            writer.list_dir("a")

    def test_list_dir_gives_sorted_names_and_kinds_without_following_links(self):
        os.mkdir(os.path.join(self.root, "d"))
        self.put("d/b", b"1")
        self.put("d/a", b"2")
        os.mkdir(os.path.join(self.root, "d", "sub"))
        os.symlink(self.outside, os.path.join(self.root, "d", "link"))
        os.mkfifo(os.path.join(self.root, "d", "pipe"))
        self.assertEqual([("a", "file"), ("b", "file"), ("link", "symlink"), ("pipe", "other"),
                          ("sub", "dir")], self.writer().list_dir("d"))

    def test_list_dir_of_a_missing_directory_is_none(self):
        self.assertIsNone(self.writer().list_dir("nothing"))
        self.assertIsNone(self.writer().list_dir("nothing/below"))

    def test_list_dir_refuses_a_link_or_a_file_in_the_way(self):
        os.symlink(self.outside, os.path.join(self.root, "up"))
        self.put("plain", b"x")
        for rel in ("up", "up/deeper", "plain", "plain/deeper"):
            with self.subTest(rel=rel), self.assertRaises(WriteConflict):
                self.writer().list_dir(rel)

    def test_list_dir_refuses_a_bad_name_unless_lenient(self):
        os.mkdir(os.path.join(self.root, "d"))
        self.put("d/ok", b"1")
        self.put("d/ctl\x01name", b"2")
        with self.assertRaises(safefs.SafeFsError):
            self.writer().list_dir("d")
        self.assertEqual([("ctl\x01name", "badname"), ("ok", "file")],
                         self.writer().list_dir("d", lenient=True))

    def test_list_dir_lenient_lists_a_name_that_is_not_utf8(self):
        os.mkdir(os.path.join(self.root, "d"))
        with unittest.mock.patch.object(os, "listdir", return_value=["ok", "bad\udcff"]):
            found = self.writer().list_dir("d", lenient=True)
        self.assertEqual([("bad\udcff", "badname")], [f for f in found if f[0] != "ok"])

    def test_list_dir_changes_nothing(self):
        os.mkdir(os.path.join(self.root, "d"))
        writer = self.writer()
        writer.list_dir("d")
        self.assertEqual([], writer.written)
        self.assertEqual(["d"], os.listdir(self.root))


if __name__ == "__main__":
    unittest.main()
