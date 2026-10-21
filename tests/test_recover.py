"""``wb recover``: clear the marker of an unfinished write where that is safe, and nowhere else."""

import hashlib
import io
import os
import shutil
import stat
import sys
import unittest
import unittest.mock

from tests import support
from tests import test_add
from tests import test_install
from tests import test_upgrade
from tests import test_upgrade_preview as base_tests
from tests.test_marker_record import marker_bytes
from workbench import approve, cli, confirm, installplan, projectfs, recover, store, target, unfinished

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = ".workbench/manifest.json"
SCRIPT = base_tests.SCRIPT
SEED = test_install.SEED


def shape(top):
    """{relative path: what is there} for everything under `top`, links not followed."""
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs + files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, top)
            if rel == os.path.join(".workbench", "local", "harness.json"):
                continue  # written by attach after the install, which the marker does not list
            mode = os.lstat(full).st_mode
            if stat.S_ISLNK(mode):
                found[rel] = ("link", os.readlink(full))
            elif stat.S_ISDIR(mode):
                found[rel] = ("dir",)
            else:
                with open(full, "rb") as handle:
                    found[rel] = ("file", hashlib.sha256(handle.read()).hexdigest())
    return found


def entries(case):
    """The per-project entries of the guarded store; what a command writes there."""
    return shape(os.path.join(case.store_root, "projects"))


def run_recover(case, place, answer=None, before=None, args=(), store_root=None):
    """`wb recover` with the digest typed (or `answer`); `before` runs when the answer is read."""
    out, err = io.StringIO(), io.StringIO()

    class Ask(io.StringIO):
        def readline(this, *a):
            if before:
                before()
            if answer is not None:
                return answer + "\n"
            digests = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")]
            return digests[-1][len("digest: "):][:confirm.CONFIRM_CHARS] + "\n"

    code = cli.main(["recover", place] + list(args), out, err,
                    store_root=store_root or case.store_root, stdin=Ask(""))
    return code, out.getvalue(), err.getvalue()


def write_marker(place, data):
    full = os.path.join(place, *projectfs.MARKER.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as handle:
        handle.write(data)


class Common:
    """Behaviour that does not depend on which command was interrupted."""

    def refused(self, place, contains, answer=None, **kwargs):
        before = (shape(place), entries(self))
        code, out, err = run_recover(self, place, answer, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, (shape(place), entries(self)))
        return out, err


class InstallBase(Common, test_install.InstallBase):
    def stop_at(self, place, path, at):
        """Install, with the `at`-th file creation failing (the marker is the first)."""
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == at:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            code, out, err = self.run_install(place, path, seed=SEED)
        self.assertEqual(3, code, err)

    def project(self):
        return test_install.manifest.project_id(SEED)

    def reference(self, path, place=None):
        """An uninterrupted install of the same inputs at the same place: its tree and its store
        entries. Both are then removed, so the install under test finds a new project."""
        other = place or self.place()
        code, out, err = self.run_install(other, path, seed=SEED)
        self.assertEqual(0, code, (out, err))
        kept = self.finished(other)
        shutil.rmtree(os.path.join(self.store_root, "projects", self.project()))
        shutil.rmtree(other)
        return kept

    def finished(self, place):
        return shape(place), shape(os.path.join(self.store_root, "projects", self.project()))


class RecoverInstall(InstallBase):
    def test_the_marker_alone_is_cleared_and_the_install_can_be_run_again(self):
        path, place = self.good(), self.place()
        wanted = self.reference(path, place)
        with unittest.mock.patch.object(projectfs.Writer, "create_git",
                                        side_effect=OSError("disk full")):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        code, out, err = run_recover(self, place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("cleared the marker", out)
        self.assertEqual({}, shape(place))
        self.assertTrue(os.path.isdir(place))
        self.assertEqual(0, self.run_install(place, path, seed=SEED)[0])
        self.assertEqual(wanted, self.finished(place))

    def test_every_point_among_the_files_clears_to_a_target_install_accepts(self):
        path = self.good()
        for at in (2, 3):
            place = self.place("proj%d" % at)
            wanted = self.reference(path, place)
            self.stop_at(place, path, at)
            code, out, err = run_recover(self, place)
            if at == 2:
                self.assertEqual((0, ""), (code, err), out)
                self.assertEqual({".git", ".git/HEAD"}, {p for p in shape(place) if
                                                         p in (".git", ".git/HEAD")})
                self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))
                self.assertEqual(0, self.run_install(place, path, seed=SEED)[0])
                self.assertEqual(wanted, self.finished(place))
                shutil.rmtree(os.path.join(self.store_root, "projects", self.project()))
            else:
                # Part of the files are written: a restore by hand comes first.
                self.assertEqual(1, code, out)
                self.assertIn("to deal with", err)
                self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))

    def test_only_the_marker_and_the_recorded_empty_directories_are_removed(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        before = shape(place)
        record = unfinished.parse(marker_bytes(place))
        code, out, err = run_recover(self, place)
        self.assertEqual((0, ""), (code, err), out)
        after = shape(place)
        removed = set(before) - set(after)
        self.assertFalse(set(after) - set(before))
        self.assertEqual({p: before[p] for p in after}, after)
        self.assertEqual(set(record.dirs) | {projectfs.MARKER, ".workbench/local"}, removed)

    def test_a_finished_install_whose_marker_was_left_is_cleared_and_is_whole(self):
        path, place = self.good(), self.place()
        wanted = self.reference(path, place)
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        code, out, err = run_recover(self, place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertFalse(os.path.exists(os.path.join(place, projectfs.MARKER)))
        self.assertEqual(wanted, self.finished(place))

    def test_files_written_and_the_store_not_is_refused_with_the_advice_to_put_them_back(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        out, err = self.refused(place, "files after")
        self.assertIn("store none", err)
        self.assertIn("put the project back as it was before the install", err)
        self.assertIn("install again", err)

    def test_files_written_and_part_of_the_store_is_refused(self):
        path, place = self.good(), self.place()
        real = store.Store.write
        calls = [0]

        def once(guarded, rel, data):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("full")
            return real(guarded, rel, data)

        with unittest.mock.patch.object(store.Store, "write", once):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        out, err = self.refused(place, "store partial")
        self.assertIn("install again", err)

    def test_files_partly_written_are_refused_and_listed(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 4)
        out, err = self.refused(place, "files mixed")
        self.assertIn("to deal with", err)
        self.assertIn("  written ", err)

    def test_a_partly_written_git_skeleton_is_refused(self):
        path, place = self.good(), self.place()
        original = projectfs.Writer.create_git

        def failing(writer, skeleton):
            original(writer, skeleton[:3])
            raise OSError("disk full")

        with unittest.mock.patch.object(projectfs.Writer, "create_git", failing):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        self.refused(place, "files mixed")

    def test_a_failure_among_the_directories_clears_what_was_made(self):
        path, place = self.good(), self.place()
        original = projectfs.Writer.create_dir
        calls = [0]

        def failing(writer, rel):
            calls[0] += 1
            if calls[0] == 3:
                raise OSError("disk full")
            return original(writer, rel)

        with unittest.mock.patch.object(projectfs.Writer, "create_dir", failing):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        self.assertTrue(os.path.isdir(os.path.join(place, ".workbench", "p")))
        code, out, err = run_recover(self, place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual({".git"} | {p for p in shape(place) if p.startswith(".git/")},
                         set(shape(place)))

    def test_a_git_skeleton_stopped_at_each_file_is_refused_until_it_is_whole(self):
        path = self.good()
        skeleton = installplan.GIT_SKELETON
        original = projectfs.Writer.create_git
        for stop in range(len(skeleton) + 1):
            place = self.place("skeleton-%d" % stop)

            def failing(writer, rel, stop=stop):
                original(writer, rel[:stop])
                raise OSError("disk full")

            with unittest.mock.patch.object(projectfs.Writer, "create_git", failing):
                self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
            if stop < len(skeleton):
                self.refused(place, "files mixed")
            else:
                self.assertEqual(0, run_recover(self, place)[0])
                self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))

    def test_more_removals_than_can_be_listed_are_refused(self):
        place = self.place("many", "empty")
        dirs = ["d%d" % n for n in range(recover.MAX_LISTED + 1)]
        for name in dirs:
            os.mkdir(os.path.join(place, name))
        write_marker(place, unfinished.build("upgrade", None, "1", [("f", "create", None, "1" * 64)],
                                             dirs=dirs,
                                             store=[("projects/x/baselines", None, "1" * 64)]))
        self.refused(place, "more than the %d that can be reviewed" % recover.MAX_LISTED)

    def test_a_marker_that_vanishes_before_the_unlink_counts_as_removed(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        original = projectfs.Writer.remove_marker

        def gone(writer):
            original(writer)
            raise projectfs.MarkerMissing("gone")

        with unittest.mock.patch.object(projectfs.Writer, "remove_marker", gone):
            code, out, err = run_recover(self, place)
        self.assertEqual((0, ""), (code, err), out)

    def test_an_interrupt_after_the_unlink_says_the_marker_is_gone(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        original = projectfs.Writer.remove_marker

        def late(writer):
            original(writer)
            raise KeyboardInterrupt

        with unittest.mock.patch.object(projectfs.Writer, "remove_marker", late):
            code, out, err = run_recover(self, place)
        self.assertEqual(3, code, out)
        self.assertIn("the marker is gone", err)

    def test_a_case_variant_of_workbench_is_never_removed(self):
        """The record is refused wherever the filesystem tells letters apart or not, so the
        variant, which may be `.workbench` itself, is never a directory to remove."""
        place = self.place("variant", "empty")
        os.makedirs(os.path.join(place, ".Workbench", "stuff"))
        good = unfinished.build(
            "install", None, "1", [("f", "create", None, "1" * 64)],
            dirs=[".workbench", ".workbench/stuff"],
            store=[("projects/x/baselines", None, "1" * 64)])
        with self.assertRaises(unfinished.UnfinishedError):
            unfinished.parse(good.replace(b'".workbench', b'".Workbench'))
        write_marker(place, good.replace(b'".workbench', b'".Workbench'))
        code, out, err = run_recover(self, place)
        self.assertEqual(1, code, out)
        self.assertTrue(os.path.isdir(os.path.join(place, ".Workbench", "stuff")))
        self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))

    def test_a_marker_without_a_record_is_refused_and_left(self):
        for content in (b"", b"garbage", b"{}", b"\xff" * 4):
            with self.subTest(content):
                place = self.place("empty-%d" % len(content), "empty")
                write_marker(place, content)
                self.refused(place, "no usable record")
                shutil.rmtree(place)

    def test_a_forged_record_with_no_files_or_no_store_is_refused(self):
        for files, writes in (([], [("projects/x/seen", None, "1" * 64)]),
                              ([("a", "create", None, "1" * 64)], [])):
            with self.subTest(files):
                place = self.place("forged-%d" % len(files), "empty")
                write_marker(place, unfinished.build("install", None, "1", files, store=writes))
                self.refused(place, "refused")
                shutil.rmtree(place)

    def test_a_marker_that_is_a_link_or_a_directory_is_refused_and_nothing_is_followed(self):
        outside = os.path.join(self.root, "outside")
        with open(outside, "wb") as handle:
            handle.write(b"keep")
        place = self.place("linked", "empty")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        os.symlink(outside, os.path.join(place, projectfs.MARKER))
        self.refused(place, "no usable record")
        os.unlink(os.path.join(place, projectfs.MARKER))
        os.mkdir(os.path.join(place, projectfs.MARKER))
        self.refused(place, "no usable record")
        with open(outside, "rb") as handle:
            self.assertEqual(b"keep", handle.read())

    def test_a_recorded_directory_that_holds_anything_is_kept_and_refuses(self):
        path = self.good()
        for holder in ("file", "link", "dir"):
            place = self.place("holds-" + holder)
            self.stop_at(place, path, 2)
            record = unfinished.parse(marker_bytes(place))
            kept = os.path.join(place, "docs", "mine")
            if holder == "file":
                with open(kept, "wb") as handle:
                    handle.write(b"mine")
            elif holder == "link":
                os.symlink(self.root, kept)
            else:
                os.makedirs(os.path.join(kept, "deeper"))
            self.assertIn("docs", record.dirs)
            self.refused(place, "files mixed")
            self.assertTrue(os.path.lexists(kept))

    def test_a_foreign_file_in_workbench_or_local_keeps_everything(self):
        path = self.good()
        for rel in (".workbench/mine", ".workbench/local/mine"):
            place = self.place("foreign-" + rel.replace("/", "-"))
            self.stop_at(place, path, 2)
            with open(os.path.join(place, *rel.split("/")), "wb") as handle:
                handle.write(b"mine")
            self.refused(place, "refused")
            self.assertTrue(os.path.exists(os.path.join(place, *rel.split("/"))))

    def test_a_recorded_directory_replaced_by_a_link_is_refused_and_not_removed(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        os.rmdir(os.path.join(place, "docs"))
        elsewhere = os.path.join(self.root, "elsewhere")
        os.mkdir(elsewhere)
        os.symlink(elsewhere, os.path.join(place, "docs"))
        self.refused(place, "files mixed")
        self.assertTrue(os.path.isdir(elsewhere))

    def test_a_directory_that_cannot_be_removed_leaves_the_marker(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        before = shape(place)
        with unittest.mock.patch.object(projectfs.Writer, "remove_empty_dir",
                                        side_effect=OSError("busy")):
            code, out, err = run_recover(self, place)
        self.assertEqual(3, code, out)
        self.assertIn("failed: busy", err)
        self.assertIn("the marker is still there", err)
        self.assertEqual(before, shape(place))

    def test_a_marker_that_cannot_be_removed_says_what_was_done(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("busy")):
            code, out, err = run_recover(self, place)
        self.assertEqual(3, code, out)
        self.assertIn("removed so far:", err)
        self.assertIn("the marker is still there", err)
        self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))

    def test_an_interrupt_while_removing_is_exit_3_and_says_so(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=KeyboardInterrupt):
            code, out, err = run_recover(self, place)
        self.assertEqual(3, code, out)
        self.assertIn("failed: interrupted", err)

    def test_an_interrupt_at_the_prompt_removes_nothing_and_is_exit_130(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        before = shape(place)

        def interrupt():
            raise KeyboardInterrupt

        code, out, err = run_recover(self, place, before=interrupt)
        self.assertEqual(130, code, err)
        self.assertIn("cancelled: nothing was removed", out)
        self.assertEqual(before, shape(place))

    def test_no_marker_means_nothing_to_recover(self):
        path, place = self.good(), self.place()
        self.assertEqual(0, self.run_install(place, path, seed=SEED)[0])
        before = (shape(place), entries(self))
        code, out, err = run_recover(self, place)
        self.assertEqual((0, "", True), (code, err, "nothing to recover" in out), out)
        self.assertEqual(before, (shape(place), entries(self)))

    def test_a_directory_that_is_not_a_project_is_refused_as_ever(self):
        place = self.place("other", "empty")
        with open(os.path.join(place, "mine.txt"), "wb") as handle:
            handle.write(b"x")
        self.refused(place, "holds other content")

    def test_the_target_directory_is_never_removed(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(projectfs.Writer, "create_git",
                                        side_effect=OSError("disk full")):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        self.assertEqual(0, run_recover(self, place)[0])
        self.assertTrue(os.path.isdir(place))
        self.assertEqual([], os.listdir(place))


class Answers(InstallBase):
    def stopped(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        return place

    def test_a_wrong_short_or_empty_answer_removes_nothing(self):
        place = self.stopped()
        before = (shape(place), entries(self))
        for answer in ("no", "", "abc", "x" * 300):
            with self.subTest(answer[:5]):
                code, out, err = run_recover(self, place, answer)
                self.assertEqual(1, code, err)
                self.assertIn("cancelled: nothing was removed", out)
                self.assertEqual(before, (shape(place), entries(self)))

    def test_the_digest_is_shown_with_what_would_be_removed(self):
        place = self.stopped()
        code, out, err = run_recover(self, place, "no")
        self.assertIn("command: recover", out)
        self.assertIn("this removes:", out)
        self.assertIn("  the marker %s" % projectfs.MARKER, out)
        self.assertIn("  the empty directory docs", out)
        self.assertIn("nothing else is written or removed", out)
        self.assertIn("unauthenticated", out)
        self.assertNotIn("run `wb recover` yourself", out)

    def test_the_digest_covers_the_marker_the_examination_and_the_target(self):
        place = self.stopped()
        digests = set()
        for _ in range(2):
            out = run_recover(self, place, "no")[1]
            digests.add([x for x in out.splitlines() if x.startswith("digest: ")][0])
        self.assertEqual(1, len(digests))
        other = self.good()
        second = self.place("second")
        self.stop_at(second, other, 2)
        out = run_recover(self, second, "no")[1]
        self.assertNotIn([x for x in out.splitlines() if x.startswith("digest: ")][0], digests)

    def test_typed_ahead_input_is_discarded(self):
        place = self.stopped()
        with unittest.mock.patch.object(confirm, "discard_typed_ahead") as discard:
            run_recover(self, place, "no")
        discard.assert_called_once()

    def test_a_project_changed_after_the_list_was_shown_is_refused(self):
        place = self.stopped()
        before = shape(place)

        def change():
            with open(os.path.join(place, "docs", "arrived"), "wb") as handle:
                handle.write(b"x")

        code, out, err = run_recover(self, place, before=change)
        self.assertEqual(1, code, out)
        self.assertIn("holds docs", err)
        self.assertEqual(set(before) | {"docs/arrived"}, set(shape(place)))
        self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))

    def test_a_change_that_leaves_the_state_acceptable_still_changes_the_digest(self):
        place = self.stopped()

        def change():
            os.rmdir(os.path.join(place, "docs"))

        code, out, err = run_recover(self, place, before=change)
        self.assertEqual(1, code, out)
        self.assertIn("changed while the list was shown", err)
        self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))
        self.assertTrue(os.path.isdir(os.path.join(place, ".workbench")))

    def test_a_marker_edited_after_the_list_was_shown_is_refused(self):
        place = self.stopped()
        record = unfinished.parse(marker_bytes(place))

        def edit():
            write_marker(place, unfinished.build(
                "install", record.project, record.workbench,
                [(f.path, f.op, f.before, f.after) for f in record.files], record.dirs[:-1],
                [(g.path, None) for g in record.git if g.hash is None], []))

        code, out, err = run_recover(self, place, before=edit)
        self.assertEqual(1, code, out)
        self.assertTrue(os.path.exists(os.path.join(place, projectfs.MARKER)))
        self.assertIn("refused", err)

    def test_a_target_swapped_after_the_list_was_shown_is_refused(self):
        place = self.stopped()
        moved = place + ".moved"

        def swap():
            os.rename(place, moved)
            os.mkdir(place)

        code, out, err = run_recover(self, place, before=swap)
        self.assertEqual(1, code, out)
        self.assertIn("the target changed", err)
        self.assertTrue(os.path.exists(os.path.join(moved, projectfs.MARKER)))
        self.assertEqual([], os.listdir(place))


class Terminals(InstallBase):
    def test_without_terminals_nothing_is_read_and_nothing_is_removed(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        before = (shape(place), entries(self))
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False), \
                unittest.mock.patch.object(unfinished, "examine") as examine:
            code, out, err = run_recover(self, place)
        self.assertEqual((1, ""), (code, out))
        self.assertIn("refused: recover is owner-run", err)
        examine.assert_not_called()
        self.assertEqual(before, (shape(place), entries(self)))

    def test_usage(self):
        for argv in (["recover", "--bogus"], ["recover", "a", "b"], ["recover", "--dir"],
                     ["recover", ""]):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(2, cli.main(argv, out, err, store_root=self.store_root,
                                         stdin=io.StringIO("")), argv)
            self.assertIn("usage:", err.getvalue())

    def test_dir_names_the_target_and_the_command_is_in_the_usage_text(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["recover", "--dir", place], out, err, store_root=self.store_root,
                        stdin=io.StringIO("no\n"))
        self.assertEqual(1, code, err.getvalue())
        self.assertIn("command: recover", out.getvalue())
        err = io.StringIO()
        cli.main([], io.StringIO(), err, store_root=self.store_root)
        self.assertIn("recover [<target> | --dir <path>]", err.getvalue())

    def test_the_refusal_report_is_the_one_every_command_gives(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.run_install(place, path, seed=SEED)[0])
        _, again = self.refused(place, "files after")
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["acknowledge", place], out, err, store_root=self.store_root,
                        stdin=io.StringIO(""))
        self.assertEqual(1, code)
        self.assertIn("the marker records an unfinished install", err.getvalue())
        self.assertIn("`wb recover`", err.getvalue())
        self.assertNotIn("`wb recover`", again.replace("recover` again", "").replace(
            "`wb recover` again", ""))


class Primitives(InstallBase):
    def held(self, place):
        fd = os.open(place, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.addCleanup(os.close, fd)
        held = target.Target(place, "existing", fd, os.path.basename(place), os.fstat(fd))
        return projectfs.Writer(held)

    def test_remove_empty_dir_removes_only_an_empty_real_directory(self):
        place = self.place("prim", "empty")
        os.makedirs(os.path.join(place, "a", "b"))
        os.makedirs(os.path.join(place, "full"))
        with open(os.path.join(place, "full", "f"), "wb") as handle:
            handle.write(b"x")
        os.symlink(self.root, os.path.join(place, "link"))
        with open(os.path.join(place, "file"), "wb") as handle:
            handle.write(b"x")
        writer = self.held(place)
        self.assertFalse(writer.remove_empty_dir("missing"))
        self.assertFalse(writer.remove_empty_dir("missing/deeper"))
        with self.assertRaises(projectfs.safefs.SafeFsError):
            writer.remove_empty_dir("a")      # holds b
        self.assertTrue(writer.remove_empty_dir("a/b"))
        self.assertTrue(writer.remove_empty_dir("a"))
        for rel in ("full", "link", "file", "link/x"):
            with self.assertRaises(projectfs.safefs.SafeFsError):
                writer.remove_empty_dir(rel)
        for rel in ("", "..", "../x", "/", "."):
            with self.assertRaises(projectfs.safefs.SafeFsError):
                writer.remove_empty_dir(rel)
        self.assertTrue(os.path.islink(os.path.join(place, "link")))
        self.assertTrue(os.path.isdir(self.root))
        self.assertTrue(os.path.exists(os.path.join(place, "full", "f")))

    def test_a_marked_target_opens_as_existing_only_when_asked(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        with self.assertRaises(target.UnfinishedMarker):
            target.open_target(place, self.store_root)
        with target.open_target(place, self.store_root, marked=True) as held:
            self.assertEqual("existing", held.state)
            self.assertTrue(held.has_incomplete_marker())
        count = len(os.listdir("/dev/fd"))
        for _ in range(3):
            with target.open_target(place, self.store_root, marked=True):
                pass
        self.assertEqual(count, len(os.listdir("/dev/fd")))

    def test_marked_does_not_loosen_any_other_refusal(self):
        for state in ("link", "file", "home"):
            place = self.place("p-" + state)
            if state == "link":
                os.symlink(self.root, place)
            elif state == "file":
                with open(place, "wb") as handle:
                    handle.write(b"x")
            else:
                place = self.root
            with self.assertRaises(target.TargetError):
                target.open_target(place, self.store_root, home=self.root, marked=True)


class Helpers(Common):
    def stop_first_write(self):
        """Make the upgrade fail at its first write after the marker."""
        calls = [0]
        create, replace = projectfs.Writer.create_file, projectfs.Writer.replace_file

        def count():
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("disk full")

        def failing_create(writer, rel, data, executable=False):
            count()
            return create(writer, rel, data, executable)

        def failing_replace(writer, rel, *a, **k):
            count()
            return replace(writer, rel, *a, **k)

        return unittest.mock.patch.multiple(projectfs.Writer, create_file=failing_create,
                                            replace_file=failing_replace)

    def uninterrupted(self, *args):
        """What the same upgrade or add gives when nothing goes wrong. The project and the store
        are saved, the command is run, and both are put back as they were."""
        saved = {}
        for name, top in (("place", self.place), ("store", self.store_root)):
            saved[name] = os.path.join(self.root, "saved-" + name)
            shutil.copytree(top, saved[name], symlinks=True)
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(list(args[:1]) + [self.place] + list(args[1:]), out, err,
                        store_root=self.store_root, stdin=Ask(""))
        self.assertEqual((0, ""), (code, err.getvalue()), out.getvalue())
        wanted = (shape(self.place), entries(self))
        for name, top in (("place", self.place), ("store", self.store_root)):
            shutil.rmtree(top)
            shutil.copytree(saved[name], top, symlinks=True)
        return wanted

    def acknowledge(self):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["acknowledge", self.place], out, err, store_root=self.store_root,
                        stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()


class UpgradeBase(Helpers, test_upgrade.Upgrade):
    pass


class AddBase(Helpers, test_add.Add):
    pass


class RecoverUpgrade(UpgradeBase):
    def test_nothing_written_is_cleared_and_the_rerun_equals_an_uninterrupted_upgrade(self):
        new = self.ready(notes=base_tests.NOTES2)
        wanted = self.uninterrupted("upgrade", "--package", new)
        with self.stop_first_write():
            self.assertEqual(3, self.upgrade("--package", new)[0])
        before = shape(self.place)
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(set(before) - {projectfs.MARKER}, set(shape(self.place)))
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(wanted, (shape(self.place), entries(self)))

    def test_a_finished_upgrade_whose_marker_was_left_is_cleared_and_whole(self):
        new = self.ready(notes=base_tests.NOTES2)
        wanted = self.uninterrupted("upgrade", "--package", new)
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(wanted, (shape(self.place), entries(self)))
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(0, code, err)
        self.assertIn("nothing to change", out)

    def test_files_written_and_the_old_baselines_kept_clear_then_acknowledge_accepts_them(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        record = unfinished.parse(marker_bytes(self.place))
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("run `wb acknowledge`", out)
        self.assertFalse(self.marker())
        code, out, err = self.acknowledge()
        self.assertEqual((0, ""), (code, err), out)
        written = {f.path for f in record.files}
        for path in written:
            self.assertIn(path, out)
        self.assertIn("acknowledged", out)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(0, code, err)
        self.assertIn("nothing to change", out)

    def test_files_partly_written_are_refused(self):
        new = self.ready(notes=test_upgrade.NOTES3)
        original = projectfs.Writer.replace_file

        def failing(writer, rel, *a, **k):
            if rel == MANIFEST:
                raise OSError("disk full")
            return original(writer, rel, *a, **k)

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", failing):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        self.refused(self.place, "files mixed")

    def test_the_failure_report_and_the_refusal_name_the_command(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            code, out, err = self.upgrade("--package", new)
        self.assertIn("`wb recover`", err)


class RecoverAdd(AddBase):
    def test_nothing_written_is_cleared_and_the_rerun_equals_an_uninterrupted_add(self):
        richer = self.ready(a=test_add.FILL(b"Rule A\n"))
        wanted = self.uninterrupted("add", "--package", richer, "--select", "a")
        with self.stop_first_write():
            self.assertEqual(3, self.add("--package", richer, "--select", "a")[0])
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(wanted, (shape(self.place), entries(self)))

    def test_a_finished_add_whose_marker_was_left_is_cleared_and_whole(self):
        richer = self.ready(a=test_add.FILL(b"Rule A\n"))
        wanted = self.uninterrupted("add", "--package", richer, "--select", "a")
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            self.assertEqual(3, self.add("--package", richer, "--select", "a")[0])
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(wanted, (shape(self.place), entries(self)))

    def test_files_written_and_the_old_baselines_kept_clear_then_acknowledge_accepts_them(self):
        richer = self.ready(a=test_add.FILL(b"Rule A\n"))
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.add("--package", richer, "--select", "a")[0])
        record = unfinished.parse(marker_bytes(self.place))
        code, out, err = run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("run `wb acknowledge`", out)
        code, out, err = self.acknowledge()
        self.assertEqual((0, ""), (code, err), out)
        for path in (f.path for f in record.files):
            self.assertIn(path, out)
        code, out, err = self.acknowledge()
        self.assertEqual((0, "nothing to acknowledge\n", ""), (code, out, err))


class Terminal(test_upgrade.Upgrade):
    """The command run in a child process whose terminals are real pseudo-terminals."""

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)
        self.store_root = os.path.join(self.root, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()

    def drive(self, answer, **kwargs):
        env = dict(os.environ, HOME=self.root, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
                   PATH=support.clean_path())
        argv = [sys.executable, "-B", "-m", "workbench", "recover", self.place]
        return support.drive_pty(self, argv, env, self.root, answer, b"> ", **kwargs)

    def digest(self, shown):
        return [line for line in shown.splitlines() if line.startswith("digest: ")][0][8:20]

    def stopped(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        return new

    def test_the_digest_typed_in_a_terminal_clears_the_marker(self):
        self.stopped()
        code, output, error = self.drive(self.digest)
        self.assertEqual((0, ""), (code, error), output)
        self.assertIn("cleared the marker", output)
        self.assertFalse(self.marker())

    def test_any_other_text_in_a_terminal_removes_nothing(self):
        self.stopped()
        before = self.snapshot()
        code, output, error = self.drive("no")
        self.assertEqual(1, code, error)
        self.assertIn("cancelled: nothing was removed", output)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.marker())

    def test_without_terminals_it_refuses(self):
        self.stopped()
        code, output, error = self.drive("x", stdin="pipe", stdout="pipe")
        self.assertEqual(1, code)
        self.assertIn("refused: recover is owner-run", error)
        self.assertTrue(self.marker())


if __name__ == "__main__":
    unittest.main()
