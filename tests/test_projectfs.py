import os
import stat
import tempfile
import unittest

from workbench import projectfs, safefs, target
from workbench.projectfs import WriteConflict, Writer


class WriterTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
