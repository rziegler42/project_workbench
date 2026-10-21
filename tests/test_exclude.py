import os
import shutil
import stat
import unittest

from workbench import projectfs
from workbench.wbkit import safefs
from workbench.projectfs import WriteConflict
from tests.test_projectfs import Fixture


class Base(Fixture):
    """A project with room for a ``.git`` directory, and ways to look at it."""

    def setUp(self):
        super().setUp()
        self.git = os.path.join(self.root, ".git")
        self.info = os.path.join(self.git, "info")
        self.exclude = os.path.join(self.info, "exclude")

    def make_git(self, info=True, content=None):
        os.mkdir(self.git)
        if info:
            os.mkdir(self.info)
            if content is not None:
                with open(self.exclude, "wb") as handle:
                    handle.write(content)

    @staticmethod
    def slurp(path):
        with open(path, "rb") as handle:
            return handle.read()

    def text(self):
        return self.slurp(self.exclude)

    def snapshot(self):
        found = []
        for base, dirs, files in os.walk(self.git):
            for name in sorted(dirs + files):
                found.append(os.path.relpath(os.path.join(base, name), self.git))
        return sorted(found)


class Exclude(Base):
    """``Writer.add_exclude``: anchored literal lines appended to ``.git/info/exclude``."""

    def test_lines_are_anchored_and_added_in_order(self):
        self.make_git(content=b"# owner\n*.pyc\n")
        added = self.writer().add_exclude([".claude/skills/", "CLAUDE.md"])
        self.assertEqual([".claude/skills/", "CLAUDE.md"], added)
        self.assertEqual(b"# owner\n*.pyc\n/.claude/skills/\n/CLAUDE.md\n", self.text())

    def test_a_line_is_never_added_twice(self):
        self.make_git(content=b"/CLAUDE.md\n")
        writer = self.writer()
        self.assertEqual([], writer.add_exclude(["CLAUDE.md"]))
        self.assertEqual(["a"], writer.add_exclude(["a", "a", "CLAUDE.md"]))
        self.assertEqual([], writer.add_exclude(["a", "CLAUDE.md"]))
        self.assertEqual(b"/CLAUDE.md\n/a\n", self.text())

    def test_a_rerun_with_nothing_to_add_does_not_touch_the_file(self):
        self.make_git(content=b"/a\n")
        before = os.stat(self.exclude)
        self.writer().add_exclude(["a"])
        after = os.stat(self.exclude)
        self.assertEqual((before.st_ino, before.st_mtime_ns, before.st_size),
                         (after.st_ino, after.st_mtime_ns, after.st_size))

    def test_the_owners_lines_are_kept_byte_for_byte(self):
        owner = b"\xff\xfe odd bytes\r\n   \n!keep\n\\#x\n/a/\n"
        self.make_git(content=owner)
        self.writer().add_exclude(["b"])
        self.assertEqual(owner + b"/b\n", self.text())

    def test_a_crlf_owner_file_is_matched_line_by_line(self):
        self.make_git(content=b"/a\r\n*.pyc\r\n")
        writer = self.writer()
        self.assertEqual(["b"], writer.add_exclude(["a", "b"]))
        self.assertEqual(b"/a\r\n*.pyc\r\n/b\n", self.text())
        self.assertEqual([], writer.add_exclude(["a", "b"]))

    def test_an_owner_file_without_a_final_newline_gets_one(self):
        self.make_git(content=b"x")
        self.writer().add_exclude(["a"])
        self.assertEqual(b"x\n/a\n", self.text())

    def test_the_same_inode_is_appended_to_not_replaced(self):
        self.make_git(content=b"x\n")
        before = os.stat(self.exclude).st_ino
        self.writer().add_exclude(["a"])
        self.assertEqual(before, os.stat(self.exclude).st_ino)

    def test_a_missing_info_and_exclude_are_created_and_recorded(self):
        self.make_git(info=False)
        writer = self.writer()
        writer.add_exclude(["a"])
        self.assertEqual(b"/a\n", self.text())
        self.assertEqual([".git/info/", ".git/info/exclude"], writer.written)
        self.assertEqual(0o644, stat.S_IMODE(os.stat(self.exclude).st_mode) & 0o644)

    def test_a_missing_exclude_in_an_existing_info_is_created(self):
        self.make_git()
        writer = self.writer()
        writer.add_exclude(["a/"])
        self.assertEqual(b"/a/\n", self.text())
        self.assertEqual([".git/info/exclude"], writer.written)

    def test_an_empty_list_adds_nothing_and_touches_nothing(self):
        self.assertEqual([], self.writer().add_exclude([]))
        self.assertEqual([], os.listdir(self.root))
        self.make_git()
        self.assertEqual([], self.writer().add_exclude([]))
        self.assertFalse(os.path.exists(self.info + "/exclude"))

    def test_there_is_no_git_directory(self):
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual([], os.listdir(self.root))

    def test_a_git_file_is_refused_with_a_clear_message(self):
        with open(self.git, "w") as handle:
            handle.write("gitdir: ../elsewhere\n")
        with self.assertRaises(WriteConflict) as caught:
            self.writer().add_exclude(["a"])
        self.assertIn("is a file", str(caught.exception))
        self.assertEqual("gitdir: ../elsewhere\n", self.slurp(self.git).decode())

    def test_a_git_link_is_refused_and_nothing_is_written_through_it(self):
        os.mkdir(os.path.join(self.outside, "info"))
        os.symlink(self.outside, self.git)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual(["info"], os.listdir(self.outside))
        self.assertEqual([], os.listdir(os.path.join(self.outside, "info")))

    def test_an_info_link_is_refused(self):
        os.mkdir(self.git)
        os.symlink(self.outside, self.info)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual([], os.listdir(self.outside))

    def test_an_info_file_is_refused(self):
        os.mkdir(self.git)
        open(self.info, "w").close()
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])

    def test_an_exclude_link_is_refused_and_its_target_is_untouched(self):
        self.make_git()
        victim = os.path.join(self.outside, "victim")
        with open(victim, "wb") as handle:
            handle.write(b"keep\n")
        os.symlink(victim, self.exclude)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual(b"keep\n", self.slurp(victim))

    def test_a_dangling_exclude_link_is_not_created_through(self):
        self.make_git()
        os.symlink(os.path.join(self.outside, "new"), self.exclude)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual([], os.listdir(self.outside))

    def test_an_exclude_directory_is_refused(self):
        self.make_git()
        os.mkdir(self.exclude)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual([], os.listdir(self.exclude))

    def test_an_exclude_fifo_is_refused_without_blocking(self):
        self.make_git()
        os.mkfifo(self.exclude)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])

    def test_an_exclude_with_another_hard_link_is_refused(self):
        self.make_git(content=b"x\n")
        other = os.path.join(self.outside, "other")
        os.link(self.exclude, other)
        with self.assertRaises(WriteConflict):
            self.writer().add_exclude(["a"])
        self.assertEqual(b"x\n", self.slurp(other))

    def test_an_oversized_exclude_is_refused(self):
        self.make_git(content=b"")
        with open(self.exclude, "ab") as handle:
            handle.truncate(safefs.MAX_FILE_BYTES + 1)
        with self.assertRaises(safefs.SafeFsError):
            self.writer().add_exclude(["a"])

    def test_a_parent_swapped_for_a_link_after_the_walk_does_not_escape(self):
        self.make_git(content=b"x\n")
        moved = os.path.join(self.base, "moved")

        def swap(stage, **info):
            if stage == "projectfs_walked" and info["rel"] == projectfs.EXCLUDE:
                os.rename(self.info, moved)
                os.symlink(self.outside, self.info)

        safefs._hook = swap
        self.writer().add_exclude(["a"])
        self.assertEqual([], os.listdir(self.outside))
        self.assertEqual(b"x\n/a\n", self.slurp(os.path.join(moved, "exclude")))

    def test_a_bad_entry_refuses_everything_and_writes_nothing(self):
        self.make_git(content=b"x\n")
        bad = ["!a", "#a", "a*", "a?", "a[b]", "a b", "a\\b", "a\nb", "a\rb", "a\tb", "\\a",
               "a/*", "**/a", "", "/", "/a", "a//b", "a/./b", "a/../b", "../a", ".", "..", "a:b",
               ".git", ".git/", ".git/hooks/pre-commit", "a/.git/b", ".GIT/x", "git~1/x",
               "a" * 600, None, 3, b"a", ("a",)]
        writer = self.writer()
        for entry in bad:
            with self.assertRaises(safefs.SafeFsError, msg=repr(entry)):
                writer.add_exclude(["fine", entry])
            self.assertEqual(b"x\n", self.text(), repr(entry))

    def test_a_single_string_is_not_a_list_of_characters(self):
        self.make_git(content=b"x\n")
        with self.assertRaises(safefs.SafeFsError):
            self.writer().add_exclude("abc")
        self.assertEqual(b"x\n", self.text())

    def test_a_trailing_slash_marks_a_directory_and_is_kept(self):
        self.make_git()
        self.writer().add_exclude([".claude/", ".claude/settings.local.json"])
        self.assertEqual(b"/.claude/\n/.claude/settings.local.json\n", self.text())

    def test_unicode_letters_are_written_as_utf8(self):
        self.make_git()
        self.writer().add_exclude(["café"])
        self.assertEqual("/café\n".encode("utf-8"), self.text())

    def test_too_many_entries_are_refused(self):
        self.make_git()
        with self.assertRaises(safefs.SafeFsError):
            self.writer().add_exclude(["a%d" % n for n in range(projectfs.MAX_EXCLUDE_ENTRIES + 1)])
        self.assertFalse(os.path.exists(self.exclude))

    def test_a_closed_target_is_refused(self):
        self.make_git()
        writer = self.writer()
        writer.target.close()
        with self.assertRaises(safefs.SafeFsError):
            writer.add_exclude(["a"])

    def test_nothing_else_under_git_changes(self):
        self.make_git()
        for name in ("HEAD", "config"):
            with open(os.path.join(self.git, name), "wb") as handle:
                handle.write(b"keep\n")
        os.mkdir(os.path.join(self.git, "hooks"))
        before = self.snapshot()
        self.writer().add_exclude(["a", "b/"])
        self.assertEqual(sorted(before + ["info/exclude"]), self.snapshot())
        for name in ("HEAD", "config"):
            self.assertEqual(b"keep\n", self.slurp(os.path.join(self.git, name)))
        self.assertEqual(["exclude"], os.listdir(self.info))

    def test_the_primitive_has_no_path_parameter(self):
        import inspect
        self.assertEqual(["self", "entries"],
                         list(inspect.signature(projectfs.Writer.add_exclude).parameters))


class Check(Base):
    """``Writer.check_exclude`` finds, before any file is written, what ``add_exclude`` would refuse,
    and itself creates and writes nothing."""

    def refuses(self, setup, error=WriteConflict, entries=("a",)):
        setup()
        before = self.snapshot() if os.path.isdir(self.git) else None
        writer = self.writer()
        with self.assertRaises(error):
            writer.check_exclude(list(entries))
        with self.assertRaises(error):
            self.writer().add_exclude(list(entries))
        if before is not None:
            # Whatever add_exclude made on its way to the refusal is not what check made.
            self.assertEqual([], writer.written)

    def test_a_good_git_directory_is_accepted_and_nothing_is_made(self):
        for info, content in ((False, None), (True, None), (True, b"/a\n")):
            with self.subTest(info=info, content=content):
                os.mkdir(self.git)
                if info:
                    os.mkdir(self.info)
                    if content is not None:
                        with open(self.exclude, "wb") as handle:
                            handle.write(content)
                before = self.snapshot()
                writer = self.writer()
                writer.check_exclude(["a", "b/"])
                self.assertEqual(before, self.snapshot())
                self.assertEqual([], writer.written)
                shutil.rmtree(self.git)

    def test_the_entries_are_checked_as_add_exclude_checks_them(self):
        self.make_git()
        for bad in ("a b", "!a", "#a", "a*", "../a", ".git/x", "", "a\\b"):
            with self.subTest(entry=bad), self.assertRaises(safefs.SafeFsError):
                self.writer().check_exclude([bad])
        with self.assertRaises(safefs.SafeFsError):
            self.writer().check_exclude("CLAUDE.md")
        with self.assertRaises(safefs.SafeFsError):
            self.writer().check_exclude(["e%d" % n for n in range(projectfs.MAX_EXCLUDE_ENTRIES + 1)])

    def test_no_git_directory(self):
        self.refuses(lambda: None)

    def test_a_git_file(self):
        def setup():
            with open(self.git, "w") as handle:
                handle.write("gitdir: ../elsewhere\n")
        self.refuses(setup)

    def test_a_git_link(self):
        self.refuses(lambda: os.symlink(self.outside, self.git))

    def test_an_info_link(self):
        def setup():
            os.mkdir(self.git)
            os.symlink(self.outside, self.info)
        self.refuses(setup)

    def test_an_info_file(self):
        def setup():
            os.mkdir(self.git)
            open(self.info, "w").close()
        self.refuses(setup)

    def test_an_exclude_link_even_a_dangling_one(self):
        def setup():
            self.make_git()
            os.symlink(os.path.join(self.outside, "new"), self.exclude)
        self.refuses(setup)
        self.assertEqual([], os.listdir(self.outside))

    def test_an_exclude_directory(self):
        def setup():
            self.make_git()
            os.mkdir(self.exclude)
        self.refuses(setup)

    def test_an_exclude_fifo_is_refused_without_blocking(self):
        def setup():
            self.make_git()
            os.mkfifo(self.exclude)
        self.refuses(setup)

    def test_an_exclude_with_another_hard_link(self):
        def setup():
            self.make_git(content=b"x\n")
            os.link(self.exclude, os.path.join(self.outside, "other"))
        self.refuses(setup)

    def test_an_oversized_exclude(self):
        def setup():
            self.make_git(content=b"")
            with open(self.exclude, "ab") as handle:
                handle.truncate(safefs.MAX_FILE_BYTES + 1)
        self.refuses(setup, error=safefs.SafeFsError)

    def test_a_closed_target(self):
        self.make_git()
        writer = self.writer()
        writer.target.close()
        with self.assertRaises(safefs.SafeFsError):
            writer.check_exclude(["a"])


if __name__ == "__main__":
    unittest.main()
