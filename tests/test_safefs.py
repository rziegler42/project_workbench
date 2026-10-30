import contextlib
import errno
import hashlib
import os
import stat
import tempfile
import unittest
import unittest.mock

from workbench.wbkit import safefs
from workbench.wbkit.safefs import SafeFsError


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
    def test_executable_files_get_the_owner_execute_bit_and_others_do_not(self):
        root = self.root
        safefs.write_tree(root, {"a/run.sh": b"#!/bin/sh\n", "a/plain.txt": b"x", "b": b"y"},
                          executable={"a/run.sh"})
        self.assertTrue(os.stat(os.path.join(root, "a", "run.sh")).st_mode & stat.S_IXUSR)
        self.assertFalse(os.stat(os.path.join(root, "a", "plain.txt")).st_mode & stat.S_IXUSR)
        self.assertFalse(os.stat(os.path.join(root, "b")).st_mode & stat.S_IXUSR)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(root, "a", "run.sh")).st_mode), 0o755)

    def test_executable_naming_a_file_that_is_not_written_is_refused_and_writes_nothing(self):
        root = self.root
        with self.assertRaises(safefs.SafeFsError):
            safefs.write_tree(root, {"a": b"x"}, executable={"a", "missing"})
        self.assertEqual(os.listdir(root), [])

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


class ReplaceFileTest(TempTest):
    """Plan ``2026-10-29-accept-decision-at-ask``, Increment D: ``Root.replace_file`` replaces one existing file only if it still
    has the bytes the caller read, and writes nothing otherwise."""

    OLD = b"Status: Proposed\nbody\n"
    NEW = b"Status: Accepted by A <a@example.org> on 2026-10-30\nbody\n"

    @staticmethod
    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def replace(self, rel="f", expected=None, data=None, **kwargs):
        with safefs.Root(self.root) as root:
            return root.replace_file(rel, self.sha(self.OLD) if expected is None else expected,
                                     self.NEW if data is None else data, **kwargs)

    def content(self, rel="f"):
        with open(os.path.join(self.root, *rel.split("/")), "rb") as handle:
            return handle.read()

    def test_replaces_the_bytes_returns_their_hash_and_keeps_the_mode(self):
        path = self.put("f", self.OLD)
        os.chmod(path, 0o640)
        self.assertEqual(self.replace(), self.sha(self.NEW))
        self.assertEqual(self.content(), self.NEW)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_replaces_a_file_below_a_directory(self):
        self.put("docs/decisions/f", self.OLD)
        self.replace("docs/decisions/f")
        self.assertEqual(self.content("docs/decisions/f"), self.NEW)

    def test_setuid_bits_of_the_old_file_are_not_carried_over(self):
        path = self.put("f", self.OLD)
        os.chmod(path, 0o4755)
        self.replace()
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o755)

    def test_bytes_that_differ_from_the_expected_hash_are_refused_and_nothing_is_written(self):
        self.put("f", b"someone else's text\n")
        with self.assertRaisesRegex(SafeFsError, "differs"):
            self.replace()
        self.assertEqual(self.content(), b"someone else's text\n")
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_malformed_expected_hash_is_refused(self):
        self.put("f", self.OLD)
        for expected in ("", "abc", self.sha(self.OLD).upper(), self.sha(self.OLD)[:-1], self.sha(self.OLD) + "0", 5,
                         self.sha(self.OLD).encode()):
            with self.subTest(expected=expected):
                with self.assertRaises(SafeFsError):
                    self.replace(expected=expected)
        self.assertEqual(self.content(), self.OLD)

    def test_data_that_is_not_bytes_is_refused(self):
        self.put("f", self.OLD)
        for data in ("text", bytearray(b"x"), None, 3):
            with self.subTest(data=data):
                with self.assertRaises(SafeFsError):
                    with safefs.Root(self.root) as root:
                        root.replace_file("f", self.sha(self.OLD), data)
        self.assertEqual(self.content(), self.OLD)

    def test_a_symbolic_link_as_the_file_is_refused_and_its_target_is_untouched(self):
        target = self.put("target", self.OLD, base=self.outside)
        os.symlink(target, os.path.join(self.root, "f"))
        with self.assertRaises(SafeFsError):
            self.replace()
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), self.OLD)
        self.assertTrue(os.path.islink(os.path.join(self.root, "f")))

    def test_a_symbolic_link_as_a_directory_is_refused(self):
        self.put("f", self.OLD, base=self.outside)
        os.symlink(self.outside, os.path.join(self.root, "sub"))
        with self.assertRaises(SafeFsError):
            self.replace("sub/f")
        self.assertEqual(os.listdir(self.outside), ["f"])
        with open(os.path.join(self.outside, "f"), "rb") as handle:
            self.assertEqual(handle.read(), self.OLD)

    def test_a_directory_and_a_fifo_are_refused(self):
        os.mkdir(os.path.join(self.root, "d"))
        os.mkfifo(os.path.join(self.root, "p"))
        for rel in ("d", "p"):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    self.replace(rel)

    def test_a_file_with_another_hard_link_is_refused(self):
        path = self.put("f", self.OLD)
        other = os.path.join(self.outside, "link")
        os.link(path, other)
        with self.assertRaisesRegex(SafeFsError, "hard link"):
            self.replace()
        with open(other, "rb") as handle:
            self.assertEqual(handle.read(), self.OLD)

    def test_a_file_over_the_limit_is_refused(self):
        self.put("f", self.OLD)
        with self.assertRaisesRegex(SafeFsError, "too large"):
            self.replace(limit=len(self.OLD) - 1)
        self.assertEqual(self.content(), self.OLD)

    def test_new_data_over_the_limit_is_refused(self):
        self.put("f", self.OLD)
        with self.assertRaisesRegex(SafeFsError, "too large"):
            self.replace(limit=len(self.OLD), data=self.OLD + b"x")
        self.assertEqual(self.content(), self.OLD)

    def test_unsafe_paths_are_refused_and_write_nothing(self):
        for rel in ("/abs", "../x", "a/../../x", "a\\b", "C:/x", ".git/config", ".GIT./x", "", None):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    self.replace(rel)
        self.assertEqual(self.listing(), [])
        self.assertEqual(self.listing(self.outside), [])

    def test_a_file_that_is_not_there_is_refused_and_nothing_is_created(self):
        for rel in ("f", "sub/f"):
            with self.subTest(rel=rel):
                with self.assertRaises(SafeFsError):
                    self.replace(rel)
        self.assertEqual(self.listing(), [])

    def test_a_read_only_file_is_refused(self):
        if os.geteuid() == 0:
            self.skipTest("root can write a read-only file")
        path = self.put("f", self.OLD)
        os.chmod(path, 0o444)
        with self.assertRaisesRegex(SafeFsError, "not writable"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)

    def test_a_closed_root_is_refused(self):
        self.put("f", self.OLD)
        root = safefs.Root(self.root)
        root.close()
        with self.assertRaisesRegex(SafeFsError, "closed"):
            root.replace_file("f", self.sha(self.OLD), self.NEW)

    def test_a_file_rewritten_before_the_rename_is_refused_and_keeps_the_other_writers_text(self):
        path = self.put("f", self.OLD)

        def rewrite(stage, **info):
            if stage == "before_replace":
                with open(path, "wb") as handle:
                    handle.write(b"Status: Proposed\nedited\n")

        safefs._hook = rewrite
        with self.assertRaisesRegex(SafeFsError, "changed"):
            self.replace()
        self.assertEqual(self.content(), b"Status: Proposed\nedited\n")
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_file_swapped_for_another_before_the_rename_is_refused(self):
        path = self.put("f", self.OLD)

        def swap(stage, **info):
            if stage == "before_replace":
                os.unlink(path)
                self.put("f", b"Status: Proposed\nanother file\n")

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "changed"):
            self.replace()
        self.assertEqual(self.content(), b"Status: Proposed\nanother file\n")
        self.assertEqual(os.listdir(self.root), ["f"])

    def staged_name(self):
        return [n for n in os.listdir(self.root) if n.startswith(".workbench-")][0]

    def test_the_staged_file_swapped_for_a_link_before_the_rename_is_refused(self):
        self.put("f", self.OLD)
        target = self.put("target", b"attacker's file\n", base=self.outside)

        def swap(stage, **info):
            if stage == "before_replace":
                staged = os.path.join(self.root, self.staged_name())
                os.unlink(staged)
                os.symlink(target, staged)

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "staged"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertFalse(os.path.islink(os.path.join(self.root, "f")))
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_the_staged_file_swapped_for_other_bytes_before_the_rename_is_refused(self):
        self.put("f", self.OLD)

        def swap(stage, **info):
            if stage == "before_replace":
                staged = os.path.join(self.root, self.staged_name())
                os.unlink(staged)
                with open(staged, "wb") as handle:
                    handle.write(b"attacker's bytes\n")

        safefs._hook = swap
        with self.assertRaisesRegex(SafeFsError, "staged"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_the_staged_file_removed_before_the_rename_is_refused(self):
        self.put("f", self.OLD)

        def remove(stage, **info):
            if stage == "before_replace":
                os.unlink(os.path.join(self.root, self.staged_name()))

        safefs._hook = remove
        with self.assertRaisesRegex(SafeFsError, "staged"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_hard_link_added_before_the_rename_is_refused(self):
        path = self.put("f", self.OLD)

        def link(stage, **info):
            if stage == "before_replace":
                os.link(path, os.path.join(self.outside, "other"))

        safefs._hook = link
        with self.assertRaisesRegex(SafeFsError, "changed"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_failing_rename_removes_the_staged_file(self):
        self.put("f", self.OLD)
        with safefs.Root(self.root) as root:
            with unittest.mock.patch("os.rename", side_effect=OSError(errno.EIO, "injected")):
                with self.assertRaisesRegex(SafeFsError, "cannot write"):
                    root.replace_file("f", self.sha(self.OLD), self.NEW)
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_failing_write_of_the_staged_file_leaves_nothing_behind(self):
        self.put("f", self.OLD)
        with unittest.mock.patch("os.fchmod", side_effect=OSError(errno.EPERM, "injected")):
            with self.assertRaisesRegex(SafeFsError, "cannot write"):
                self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_file_swapped_for_a_link_before_the_rename_is_refused(self):
        path = self.put("f", self.OLD)
        target = self.put("target", self.OLD, base=self.outside)

        def swap(stage, **info):
            if stage == "before_replace":
                os.unlink(path)
                os.symlink(target, path)

        safefs._hook = swap
        with self.assertRaises(SafeFsError):
            self.replace()
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_directory_swapped_for_a_link_before_the_rename_cannot_redirect_the_write(self):
        self.put("sub/f", self.OLD)
        moved = os.path.join(self.root, "sub.orig")

        def swap(stage, **info):
            if stage == "before_replace":
                os.rename(os.path.join(self.root, "sub"), moved)
                os.symlink(self.outside, os.path.join(self.root, "sub"))

        safefs._hook = swap
        self.replace("sub/f")
        self.assertEqual(os.listdir(self.outside), [])
        with open(os.path.join(moved, "f"), "rb") as handle:
            self.assertEqual(handle.read(), self.NEW)

    def test_a_failure_before_the_rename_leaves_the_old_bytes_and_no_temporary(self):
        self.put("f", self.OLD)

        def fail(stage, **info):
            if stage == "before_replace":
                raise SafeFsError("injected failure")

        safefs._hook = fail
        with self.assertRaisesRegex(SafeFsError, "injected"):
            self.replace()
        self.assertEqual(self.content(), self.OLD)
        self.assertEqual(os.listdir(self.root), ["f"])

    def test_a_file_that_changes_while_it_is_read_is_refused(self):
        path = self.put("f", self.OLD)

        def rewrite(stage, **info):
            if stage == "read":
                with open(path, "ab") as handle:
                    handle.write(b"more\n")

        safefs._hook = rewrite
        with self.assertRaises(SafeFsError):
            self.replace()
        self.assertEqual(self.content(), self.OLD + b"more\n")
        self.assertEqual(os.listdir(self.root), ["f"])


class AppendCreateRaceTest(TempTest):
    """Plan ``2026-10-28-fix-append-create-race``: on macOS a creating ``openat`` can fail with ``ENOENT`` while another
    writer creates the same name, although the directory exists."""

    @contextlib.contextmanager
    def failing_creates(self, failures):
        """Make the first `failures` opens of the name ``log`` raise ``ENOENT``; yield the list of its opens."""
        real = os.open
        opens = []

        def fake(path, flags, *args, **kwargs):
            if path == "log":
                opens.append(path)
                if len(opens) <= failures:
                    raise FileNotFoundError(errno.ENOENT, "No such file or directory", path)
            return real(path, flags, *args, **kwargs)

        with unittest.mock.patch.object(safefs.os, "open", new=fake), \
                unittest.mock.patch.object(safefs.os, "supports_dir_fd", new=set(os.supports_dir_fd) | {fake}):
            yield opens

    def test_one_enoent_from_the_creating_open_is_retried_once(self):
        with self.failing_creates(1) as opens:
            safefs.append_line(self.root, "log", b"one\n")
        self.assertEqual(2, len(opens))
        with open(os.path.join(self.root, "log"), "rb") as handle:
            self.assertEqual(b"one\n", handle.read())

    def test_a_second_enoent_is_refused_after_exactly_two_opens(self):
        with self.failing_creates(2) as opens:
            with self.assertRaises(SafeFsError) as caught:
                safefs.append_line(self.root, "log", b"one\n")
        self.assertIn("cannot open", str(caught.exception))
        self.assertEqual(2, len(opens))
        self.assertFalse(os.path.exists(os.path.join(self.root, "log")))


if __name__ == "__main__":
    unittest.main()
