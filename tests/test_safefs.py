import os
import stat
import tempfile
import unittest

from workbench import safefs
from workbench.safefs import SafeFsError


class TempTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        base = os.path.realpath(holder.name)
        self.root = os.path.join(base, "root")
        self.outside = os.path.join(base, "outside")
        os.mkdir(self.root)
        os.mkdir(self.outside)
        self.addCleanup(self.clear_hook)

    def clear_hook(self):
        safefs._hook = None

    def put(self, rel, data=b"data", base=None):
        path = os.path.join(base or self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def listing(self, root=None):
        found = []
        for dirpath, dirnames, filenames in os.walk(root or self.root):
            found.extend(os.path.join(dirpath, n) for n in dirnames + filenames)
        return sorted(found)


class RelpathTest(unittest.TestCase):
    def test_accepts_ordinary_paths(self):
        for rel in ("a", "a/b.txt", "dir/.hidden", "a b/c", "git~", "git~x", "gitx~1", "x" * 512, "..." + "/x", ".gitignore"):
            with self.subTest(rel=rel):
                self.assertEqual(safefs.validate_relpath(rel), rel.split("/"))

    def test_refuses_unsafe_paths(self):
        bad = [None, b"a", "", "/abs", ".", "..", "a/../b", "a/./b", "a//b", "a/", "./a",
               "a\\b", "C:/x", "a:b", ".git", ".GIT/config", "a/.Git/b", ".git./x",
               ".git /x", ".git. ./x", "a/.GiT  ../b", "GIT~1/hooks/x", "a/git~2", "Git~10. /b",
               "x" * 513, "a\x00b", "a\tb", "a\nb"]
        for rel in bad:
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    safefs.validate_relpath(rel)
                self.assertFalse(safefs.relpath_ok(rel))


class ContainmentTest(TempTest):
    def test_real_directory(self):
        safefs.real_directory(self.root, "root")
        link = os.path.join(self.outside, "link")
        os.symlink(self.root, link)
        with self.assertRaises(SafeFsError):
            safefs.real_directory(link, "root")
        with self.assertRaises(SafeFsError):
            safefs.real_directory(self.put("f"), "root")
        with self.assertRaises(SafeFsError):
            safefs.real_directory(os.path.join(self.root, "missing"), "root")

    def test_is_within(self):
        self.put("sub/f")
        self.assertTrue(safefs.is_within(self.root, self.root))
        self.assertTrue(safefs.is_within(os.path.join(self.root, "sub", "f"), self.root))
        self.assertFalse(safefs.is_within(self.outside, self.root))
        self.assertFalse(safefs.is_within(self.root + "-sibling", self.root))

    def test_symlinked_ancestor_does_not_place_a_path_inside(self):
        link = os.path.join(self.root, "link")
        os.symlink(self.outside, link)
        self.put("f", base=self.outside)
        self.assertFalse(safefs.is_within(os.path.join(link, "f"), self.root))

    def test_case_variant_is_inside_on_a_case_insensitive_filesystem(self):
        variant = self.root.replace("root", "ROOT")
        if not os.path.exists(variant):
            self.skipTest("case-sensitive filesystem")
        self.assertTrue(safefs.is_within(variant, self.root))


class RootTest(TempTest):
    def test_symlink_root_is_refused(self):
        link = os.path.join(self.outside, "link")
        os.symlink(self.root, link)
        with self.assertRaises(SafeFsError):
            safefs.Root(link)

    def test_file_and_missing_root_are_refused(self):
        with self.assertRaises(SafeFsError):
            safefs.Root(self.put("f"))
        with self.assertRaises(SafeFsError):
            safefs.Root(os.path.join(self.root, "missing"))

    def test_unsupported_platform_is_refused_by_reader_and_writer(self):
        original = safefs._support_problems
        safefs._support_problems = lambda: ["directory-relative open"]
        self.addCleanup(setattr, safefs, "_support_problems", original)
        with self.assertRaisesRegex(SafeFsError, "cannot read or write files safely"):
            safefs.Root(self.root)
        with self.assertRaisesRegex(SafeFsError, "cannot read or write files safely"):
            safefs.write_tree(self.root, {"a": b"x"})


class WalkTest(TempTest):
    def test_walk_lists_kinds_sorted(self):
        self.put("b/f")
        self.put("a")
        os.symlink("a", os.path.join(self.root, "link"))
        os.mkfifo(os.path.join(self.root, "pipe"))
        with safefs.Root(self.root) as root:
            kinds = [(e.rel, e.kind) for e in root.walk()]
        self.assertEqual(kinds, [("a", "file"), ("b", "dir"), ("b/f", "file"),
                                 ("link", "symlink"), ("pipe", "other")])

    def test_walk_does_not_descend_a_symlinked_directory(self):
        self.put("secret", base=self.outside)
        os.symlink(self.outside, os.path.join(self.root, "d"))
        with safefs.Root(self.root) as root:
            self.assertEqual([(e.rel, e.kind) for e in root.walk()], [("d", "symlink")])

    def test_walk_refuses_git_metadata_and_unsafe_names(self):
        os.mkdir(os.path.join(self.root, ".git"))
        with safefs.Root(self.root) as root:
            with self.assertRaises(SafeFsError):
                root.walk()

    def test_classify_covers_devices(self):
        self.assertEqual(safefs.classify(stat.S_IFCHR), "other")
        self.assertEqual(safefs.classify(stat.S_IFBLK), "other")
        self.assertEqual(safefs.classify(stat.S_IFSOCK), "other")


class ReaderTest(TempTest):
    def read(self, rel, **kw):
        with safefs.Root(self.root) as root:
            return root.read_file(rel, **kw)

    def test_reads_a_regular_file_and_a_nested_one(self):
        self.put("f", b"one")
        self.put("a/b/g", b"two")
        self.assertEqual(self.read("f"), b"one")
        self.assertEqual(self.read("a/b/g"), b"two")

    def test_expected_identity_from_listing_is_accepted_when_unchanged(self):
        self.put("f", b"one")
        with safefs.Root(self.root) as root:
            entry = root.walk()[0]
            self.assertEqual(root.read_file("f", expected=entry.identity), b"one")

    def test_missing_symlink_directory_and_fifo_are_refused(self):
        self.put("f", b"x", base=self.outside)
        os.symlink(os.path.join(self.outside, "f"), os.path.join(self.root, "link"))
        os.mkdir(os.path.join(self.root, "d"))
        os.mkfifo(os.path.join(self.root, "pipe"))
        for rel in ("nope", "link", "d", "pipe"):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    self.read(rel)

    def test_closed_root_does_not_read_from_the_working_directory(self):
        self.put("SECRET", b"cwd")
        root = safefs.Root(self.root)
        root.close()
        previous = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        for rel in ("SECRET", "sub/SECRET"):
            with self.assertRaisesRegex(SafeFsError, "closed"):
                root.read_file(rel)
        with self.assertRaisesRegex(SafeFsError, "closed"):
            root.walk()

    def test_file_swapped_for_a_fifo_between_listing_and_open_is_refused_without_blocking(self):
        path = self.put("f", b"x")

        def swap(stage, **info):
            if stage == "listed":
                os.unlink(path)
                os.mkfifo(path)

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.read("f")

    def test_unsafe_relative_path_is_refused(self):
        with self.assertRaises(SafeFsError):
            self.read("../outside/f")

    def test_too_large_is_refused(self):
        self.put("f", b"x" * 11)
        with self.assertRaisesRegex(SafeFsError, "too large"):
            self.read("f", limit=10)
        self.assertEqual(self.read("f", limit=11), b"x" * 11)

    def test_ancestor_swapped_for_a_symlink_after_validation_is_refused(self):
        self.put("sub/f", b"inside")
        self.put("f", b"SECRET", base=self.outside)

        def swap(stage, **info):
            if stage == "validated":
                os.rename(os.path.join(self.root, "sub"), os.path.join(self.root, "sub.orig"))
                os.symlink(self.outside, os.path.join(self.root, "sub"))

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.read("sub/f")

    def test_file_replaced_by_a_symlink_between_listing_and_open_is_refused(self):
        path = self.put("f", b"inside")
        self.put("f", b"SECRET", base=self.outside)

        def swap(stage, **info):
            if stage == "listed":
                os.unlink(path)
                os.symlink(os.path.join(self.outside, "f"), path)

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.read("f")

    def test_file_replaced_by_a_different_regular_file_is_refused(self):
        path = self.put("f", b"inside")
        other = self.put("other", b"replaced", base=self.outside)

        def swap(stage, **info):
            if stage == "listed":
                os.rename(other, path)

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "changed before it was read"):
            self.read("f")

    def test_file_changed_since_the_listing_is_refused(self):
        path = self.put("f", b"aaaa")
        with safefs.Root(self.root) as root:
            entry = root.walk()[0]
            self.put("f", b"bbbbb")
            with self.assertRaisesRegex(SafeFsError, "since it was listed"):
                root.read_file("f", expected=entry.identity)
        self.assertTrue(os.path.exists(path))

    def rewrite_same_size(self, path, data):
        before = os.stat(path)
        with open(path, "r+b") as handle:
            handle.write(data)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))

    def test_same_size_rewrite_with_restored_mtime_between_listing_and_open_is_refused(self):
        path = self.put("f", b"aaaa")

        def swap(stage, **info):
            if stage == "listed":
                self.rewrite_same_size(path, b"bbbb")

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "changed before it was read"):
            self.read("f")

    def test_same_size_rewrite_with_restored_mtime_during_the_read_is_refused(self):
        path = self.put("f", b"aaaa")

        def swap(stage, **info):
            if stage == "read":
                self.rewrite_same_size(path, b"bbbb")

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "changed while it was read"):
            self.read("f")

    def test_file_modified_after_open_is_refused(self):
        path = self.put("f", b"aaaa")

        def swap(stage, **info):
            if stage == "opened":
                with open(path, "ab") as handle:
                    handle.write(b"more")

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.read("f")

    def test_file_that_grows_during_the_read_is_refused(self):
        path = self.put("f", b"aaaa")

        def swap(stage, **info):
            if stage == "read":
                with open(path, "ab") as handle:
                    handle.write(b"b" * 100)

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.read("f", limit=50)


class WriteTest(TempTest):
    def test_writes_files_and_creates_directories(self):
        written = safefs.write_tree(self.root, {"a/b/c.txt": b"one", "d": b"two"})
        self.assertEqual(written, ["a/b/c.txt", "d"])
        with open(os.path.join(self.root, "a", "b", "c.txt"), "rb") as handle:
            self.assertEqual(handle.read(), b"one")
        self.assertEqual(sorted(os.listdir(self.root)), ["a", "d"])

    def test_replacement_keeps_the_mode_of_the_old_file(self):
        path = self.put("f", b"old")
        os.chmod(path, 0o750)
        safefs.write_tree(self.root, {"f": b"new"})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o750)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"new")

    def test_hardlinked_file_is_not_written_through(self):
        path = self.put("f", b"old")
        link = os.path.join(self.outside, "hard")
        os.link(path, link)
        safefs.write_tree(self.root, {"f": b"new"})
        with open(link, "rb") as handle:
            self.assertEqual(handle.read(), b"old")

    def test_path_through_a_symlink_is_refused(self):
        os.symlink(self.outside, os.path.join(self.root, "d"))
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"d/f": b"x"})
        self.assertEqual(os.listdir(self.outside), [])

    def test_destination_symlink_non_file_and_readonly_are_refused(self):
        self.put("target", b"keep", base=self.outside)
        os.symlink(os.path.join(self.outside, "target"), os.path.join(self.root, "link"))
        os.mkdir(os.path.join(self.root, "dir"))
        ro = self.put("ro", b"keep")
        os.chmod(ro, 0o444)
        for rel in ("link", "dir", "ro"):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    safefs.write_tree(self.root, {rel: b"new"})
        with open(os.path.join(self.outside, "target"), "rb") as handle:
            self.assertEqual(handle.read(), b"keep")
        with open(ro, "rb") as handle:
            self.assertEqual(handle.read(), b"keep")

    def test_file_in_the_way_of_a_directory_is_refused(self):
        self.put("a", b"file")
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"a/b": b"x"})
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"p": b"x", "p/q": b"y"})

    def test_case_and_normalization_collisions_are_refused_and_write_nothing(self):
        for tree in ({"README": b"a", "readme": b"b"},
                     {"A": b"a", "a/x": b"b"},
                     {"café": b"a", "café": b"b"}):
            with self.subTest(tree=sorted(tree)):
                with self.assertRaises(SafeFsError):
                    safefs.write_tree(self.root, tree)
        self.assertEqual(self.listing(), [])

    def test_setuid_bits_of_the_old_file_are_not_carried_over(self):
        path = self.put("f", b"old")
        os.chmod(path, 0o4755)
        safefs.write_tree(self.root, {"f": b"new"})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o755)

    def test_directory_swapped_for_a_symlink_after_the_check_is_refused(self):
        self.put("sub/keep", b"x")

        def swap(stage, **info):
            if stage == "after_check":
                os.rename(os.path.join(self.root, "sub"), os.path.join(self.root, "sub.orig"))
                os.symlink(self.outside, os.path.join(self.root, "sub"))

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"sub/f": b"new"})
        self.assertEqual(os.listdir(self.outside), [])

    def test_unsafe_paths_are_refused_and_write_nothing(self):
        for rel in ("/abs", "../x", "a/../../x", "a\\b", "C:/x", ".git/config", ".GIT./x", "a/.git /b"):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    safefs.write_tree(self.root, {rel: b"x"})
        self.assertEqual(self.listing(), [])
        self.assertEqual(self.listing(self.outside), [])

    def test_symlink_root_is_refused(self):
        link = os.path.join(self.outside, "link")
        os.symlink(self.root, link)
        with self.assertRaises(SafeFsError):
            safefs.write_tree(link, {"f": b"x"})
        self.assertEqual(self.listing(), [])

    def test_missing_root_is_refused(self):
        with self.assertRaises(SafeFsError):
            safefs.write_tree(os.path.join(self.root, "missing"), {"f": b"x"})

    def test_non_bytes_content_is_refused(self):
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"f": "text"})

    def test_failure_before_rename_leaves_old_content_and_no_stragglers(self):
        path = self.put("f", b"old")

        def fail(stage, **info):
            if stage == "before_rename":
                raise SafeFsError("injected failure")

        safefs._hook = fail
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"f": b"new", "g": b"other"})
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"old")
        self.assertEqual(sorted(os.listdir(self.root)), ["f"])

    def test_failure_after_the_first_rename_removes_the_remaining_temporaries(self):
        self.put("f", b"old")
        calls = []

        def fail(stage, **info):
            if stage == "before_rename":
                calls.append(info["rel"])
                if len(calls) == 2:
                    raise SafeFsError("injected failure")

        safefs._hook = fail
        with self.assertRaises(SafeFsError):
            safefs.write_tree(self.root, {"f": b"new", "g": b"other"})
        self.assertEqual(sorted(os.listdir(self.root)), ["f"])
        with open(os.path.join(self.root, "f"), "rb") as handle:
            self.assertEqual(handle.read(), b"new")

    def test_parent_swapped_for_a_symlink_before_the_rename_cannot_redirect_the_write(self):
        self.put("sub/f", b"old")
        moved = os.path.join(self.root, "sub.orig")

        def swap(stage, **info):
            if stage == "before_rename":
                os.rename(os.path.join(self.root, "sub"), moved)
                os.symlink(self.outside, os.path.join(self.root, "sub"))

        safefs._hook = swap
        safefs.write_tree(self.root, {"sub/f": b"new"})
        self.assertEqual(os.listdir(self.outside), [])
        with open(os.path.join(moved, "f"), "rb") as handle:
            self.assertEqual(handle.read(), b"new")

    def test_destination_swapped_for_a_symlink_before_the_rename_is_replaced_not_followed(self):
        path = self.put("f", b"old")
        target = self.put("target", b"keep", base=self.outside)

        def swap(stage, **info):
            if stage == "before_rename":
                os.unlink(path)
                os.symlink(target, path)

        safefs._hook = swap
        safefs.write_tree(self.root, {"f": b"new"})
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), b"keep")
        self.assertFalse(os.path.islink(path))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"new")


if __name__ == "__main__":
    unittest.main()
