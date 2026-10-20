"""Examining and reporting what a project holds after an unfinished write."""

import io
import os
import time
import types
import unittest
import unittest.mock

from tests import test_install
from tests import test_upgrade
from tests import test_upgrade_preview as base_tests
from workbench import cli, installplan, projectfs, store, target, unfinished, upgrade
from tests.test_marker_record import marker_bytes, sha

MANIFEST = ".workbench/manifest.json"
SCRIPT = base_tests.SCRIPT


class Held:
    """A directory held open as an existing target, for reading only."""

    def __init__(self, place):
        self.fd = os.open(place, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.target = target.Target(place, "existing", self.fd, os.path.basename(place),
                                    os.fstat(self.fd))
        self.writer = projectfs.Writer(self.target)

    def close(self):
        os.close(self.fd)


def examine(case, place, store_root=None):
    held = Held(place)
    try:
        return unfinished.examine(held.writer, store_root or case.store_root)
    finally:
        held.close()


def states(found, kind):
    return {i.path: i.state for i in found.items if i.kind == kind}


def snapshot(*tops):
    found = {}
    for top in tops:
        for base, dirs, files in os.walk(top):
            for name in dirs + files:
                full = os.path.join(base, name)
                info = os.lstat(full)
                found[full] = (info.st_mode, info.st_size, info.st_mtime_ns)
    return found


class InstallStops(test_install.InstallBase):
    def stop_at(self, place, path, at):
        """Install, with the `at`-th file creation failing."""
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == at:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            code, out, err = self.run_install(place, path, seed=test_install.SEED)
        self.assertEqual(3, code, err)

    def test_files_partly_written_are_mixed_and_the_store_is_none(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 4)
        found = examine(self, place)
        self.assertEqual(("mixed", "none"), (found.files, found.store))
        files = states(found, "file")
        self.assertEqual({"after", "before"}, set(files.values()))
        self.assertEqual({"after"}, set(states(found, "git").values()))
        self.assertEqual({"before"}, set(states(found, "store").values()))
        text = "\n".join(unfinished.render(found))
        self.assertIn("unfinished install", text)
        self.assertIn("written ", text)
        self.assertIn("`wb recover`", text)
        self.assertIn("unauthenticated", text)

    def test_nothing_written_after_the_marker_and_git_is_before(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        found = examine(self, place)
        self.assertEqual(("before", "none"), (found.files, found.store), found.items)
        self.assertEqual({"before"}, set(states(found, "file").values()))
        self.assertEqual("empty", states(found, "dir")[".workbench"])

    def test_the_marker_alone_is_before(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(projectfs.Writer, "create_git",
                                        side_effect=OSError("disk full")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        found = examine(self, place)
        self.assertEqual(("before", "none"), (found.files, found.store))
        self.assertEqual({"absent"}, set(states(found, "git").values()))

    def test_a_partly_written_git_skeleton_is_other(self):
        path, place = self.good(), self.place()
        original = projectfs.Writer.create_git

        def failing(writer, skeleton):
            original(writer, skeleton[:3])
            raise OSError("disk full")

        with unittest.mock.patch.object(projectfs.Writer, "create_git", failing):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        found = examine(self, place)
        self.assertEqual("mixed", found.files)
        self.assertIn("other", set(states(found, "git").values()))

    def test_files_after_with_the_store_not_written(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        found = examine(self, place)
        self.assertEqual(("after", "none"), (found.files, found.store))

    def test_files_after_with_part_of_the_store_written(self):
        path, place = self.good(), self.place()
        real = store.Store.write
        calls = [0]

        def once(guarded, rel, data):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("full")
            return real(guarded, rel, data)

        with unittest.mock.patch.object(store.Store, "write", once):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        found = examine(self, place)
        self.assertEqual(("after", "partial"), (found.files, found.store))

    def test_everything_written_but_the_marker_not_removed(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        found = examine(self, place)
        self.assertEqual(("after", "all"), (found.files, found.store))

    def stopped(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.run_install(place, path, seed=test_install.SEED)[0])
        return place

    def test_a_file_that_was_changed_is_other(self):
        place = self.stopped()
        with open(os.path.join(place, "AGENTS.md"), "ab") as handle:
            handle.write(b"edited")
        found = examine(self, place)
        self.assertEqual("mixed", found.files)
        self.assertEqual("other", states(found, "file")["AGENTS.md"])
        self.assertIn("  other AGENTS.md (holds other content)", unfinished.render(found))

    def test_a_link_a_directory_and_a_hard_link_at_a_recorded_path_are_other(self):
        place = self.stopped()
        outside = os.path.join(self.root, "outside")
        with open(outside, "wb") as handle:
            handle.write(b"secret")
        agents = os.path.join(place, "AGENTS.md")
        os.unlink(agents)
        os.symlink(outside, agents)
        found = examine(self, place)
        self.assertEqual("other", states(found, "file")["AGENTS.md"])
        os.unlink(agents)
        os.mkdir(agents)
        self.assertEqual("other", states(examine(self, place), "file")["AGENTS.md"])
        os.rmdir(agents)
        os.link(outside, agents)
        self.assertEqual("other", states(examine(self, place), "file")["AGENTS.md"])
        with open(outside, "rb") as handle:
            self.assertEqual(b"secret", handle.read())

    def test_a_link_in_the_directories_above_a_recorded_path_is_other(self):
        place = self.stopped()
        elsewhere = os.path.join(self.root, "elsewhere")
        os.rename(os.path.join(place, ".workbench", "p"), elsewhere)
        os.symlink(elsewhere, os.path.join(place, ".workbench", "p"))
        found = examine(self, place)
        moved = [i for i in found.items if i.kind == "file" and i.path.startswith(".workbench/p/")]
        self.assertTrue(moved)
        self.assertEqual({"other"}, {i.state for i in moved})

    @unittest.skipIf(os.geteuid() == 0, "root can read everything")
    def test_an_unreadable_file_is_other(self):
        place = self.stopped()
        os.chmod(os.path.join(place, "AGENTS.md"), 0)
        self.assertEqual("other", states(examine(self, place), "file")["AGENTS.md"])

    def test_a_store_entry_that_is_not_what_was_written_is_other(self):
        place = self.stopped()
        project = test_install.manifest.project_id(test_install.SEED)
        self.guarded.write("projects/%s/seen" % project, b"something else")
        found = examine(self, place)
        self.assertEqual("partial", found.store)
        self.assertEqual("other", states(found, "store")["projects/%s/seen" % project])

    def test_a_store_entry_that_is_a_link_is_other(self):
        place = self.stopped()
        project = test_install.manifest.project_id(test_install.SEED)
        full = os.path.join(self.store_root, "projects", project)
        os.makedirs(full)
        os.symlink(os.path.join(self.root, "x"), os.path.join(full, "seen"))
        self.assertEqual("other", states(examine(self, place), "store")["projects/%s/seen" % project])

    def test_a_missing_store_is_none(self):
        place = self.stopped()
        found = examine(self, place, os.path.join(self.root, "no-such-store"))
        self.assertEqual("none", found.store)

    def test_a_recorded_directory_that_holds_a_foreign_file_is_other_in_the_before_state(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        with open(os.path.join(place, ".workbench", "mine"), "wb") as handle:
            handle.write(b"x")
        found = examine(self, place)
        self.assertEqual("holds", states(found, "dir")[".workbench"])
        self.assertEqual("mixed", found.files)
        self.assertIn("  holds .workbench", unfinished.render(found))

    def test_examining_changes_nothing(self):
        place = self.stopped()
        before = snapshot(place, self.store_root)
        examine(self, place)
        self.assertEqual(before, snapshot(place, self.store_root))

    def test_a_spent_read_budget_marks_the_rest_as_not_read(self):
        place = self.stopped()
        with unittest.mock.patch.object(unfinished, "BUDGET", 10):
            found = examine(self, place)
        files = [i for i in found.items if i.kind == "file"]
        self.assertTrue(any("budget" in i.detail for i in files))
        self.assertEqual("mixed", found.files)


class InstallReports(test_install.InstallBase):
    def stop(self, **patches):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            self.assertEqual(3, self.run_install(place, path, seed=test_install.SEED)[0])
        return path, place

    def test_a_finished_install_with_only_the_marker_left_lists_nothing_to_deal_with(self):
        path, place = self.stop()
        found = examine(self, place)
        self.assertEqual(("after", "all"), (found.files, found.store))
        self.assertIn("holds", set(states(found, "dir").values()))
        text = "\n".join(unfinished.render(found))
        self.assertNotIn("to deal with", text)
        self.assertNotIn("  holds ", text)

    def test_install_and_preview_install_refuse_a_marked_target_with_the_same_report(self):
        path, place = self.stop()
        code, out, again = self.run_install(place, path, seed=test_install.SEED)
        self.assertEqual(1, code)
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "install", place, "--package", path, "--select", "h", "notes"],
                        out, err, store_root=self.store_root)
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertEqual(again, err.getvalue())
        self.assertIn("the marker records an unfinished install", again)

    def test_a_forged_record_with_no_files_or_no_store_is_not_after_all(self):
        place = os.path.join(self.root, "forged")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        for files, store_writes in (([], [("projects/x/seen", None, "1" * 64)]),
                                    ([("a", "create", None, "1" * 64)], [])):
            with open(os.path.join(place, projectfs.MARKER), "wb") as handle:
                handle.write(unfinished.build("install", None, "1", files, store=store_writes))
            found = examine(self, place)
            self.assertNotEqual(("before", "none"), (found.files, found.store))
            self.assertIn("mixed" if not files else "partial", (found.files, found.store))

    def test_a_link_where_git_was_made_is_other(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        elsewhere = os.path.join(self.root, "elsewhere")
        os.rename(os.path.join(place, ".git"), elsewhere)
        os.symlink(elsewhere, os.path.join(place, ".git"))
        found = examine(self, place)
        self.assertEqual("mixed", found.files)
        self.assertIn(("git", ".git", "other"),
                      [(i.kind, i.path, i.state) for i in found.items])

    def stop_at(self, place, path, at):
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == at:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            self.assertEqual(3, self.run_install(place, path, seed=test_install.SEED)[0])

    def test_a_recorded_directory_that_became_a_file_is_other(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        os.rmdir(os.path.join(place, "docs"))
        with open(os.path.join(place, "docs"), "wb") as handle:
            handle.write(b"x")
        found = examine(self, place)
        self.assertEqual("other", states(found, "dir")["docs"])
        self.assertEqual("mixed", found.files)

    def test_a_fifo_at_a_recorded_path_is_other_and_does_not_block(self):
        path, place = self.good(), self.place()
        self.stop_at(place, path, 2)
        os.mkfifo(os.path.join(place, "AGENTS.md"))
        self.assertEqual("other", states(examine(self, place), "file")["AGENTS.md"])
        os.unlink(os.path.join(place, ".git", "HEAD"))
        os.mkfifo(os.path.join(place, ".git", "HEAD"))
        self.assertEqual("other", states(examine(self, place), "git")[".git/HEAD"])

    def test_the_marked_target_refusal_closes_what_it_opened(self):
        path, place = self.stop()
        count = len(os.listdir("/dev/fd"))
        for _ in range(5):
            with self.assertRaises(target.UnfinishedMarker) as caught:
                target.open_target(place, self.store_root)
        self.assertEqual(count, len(os.listdir("/dev/fd")))
        self.assertTrue(any("files after" in line for line in caught.exception.report))

    def test_a_failure_while_examining_still_refuses_and_closes(self):
        path, place = self.stop()
        count = len(os.listdir("/dev/fd"))
        with unittest.mock.patch.object(unfinished, "examine", side_effect=RuntimeError("boom")):
            with self.assertRaises(target.UnfinishedMarker) as caught:
                target.open_target(place, self.store_root)
        self.assertEqual(count, len(os.listdir("/dev/fd")))
        self.assertIn("could not be examined: boom", " ".join(caught.exception.report))


class Primitives(test_install.InstallBase):
    def test_dir_holds_and_git_entry_read_without_following(self):
        place = self.place("proj", "empty")
        os.makedirs(os.path.join(place, "a", "b"))
        os.makedirs(os.path.join(place, ".git", "objects"))
        with open(os.path.join(place, ".git", "HEAD"), "wb") as handle:
            handle.write(b"ref")
        os.symlink(place, os.path.join(place, ".git", "loop"))
        os.symlink(place, os.path.join(place, "link"))
        held = Held(place)
        self.addCleanup(held.close)
        writer = held.writer
        self.assertIsNone(writer.dir_holds("nope"))
        self.assertTrue(writer.dir_holds("a"))
        self.assertFalse(writer.dir_holds("a", ignore=("b",)))
        self.assertFalse(writer.dir_holds("a/b"))
        with self.assertRaises(projectfs.WriteConflict):
            writer.dir_holds("link")
        self.assertEqual(("dir", None), writer.git_entry(""))
        self.assertEqual(("dir", None), writer.git_entry("objects"))
        self.assertEqual(("file", unfinished.sha(b"ref")), writer.git_entry("HEAD"))
        self.assertIsNone(writer.git_entry("missing"))
        self.assertIsNone(writer.git_entry("missing/deeper"))
        with self.assertRaises(projectfs.WriteConflict):
            writer.git_entry("loop")
        with self.assertRaises(projectfs.WriteConflict):
            writer.git_entry("loop/x")
        with self.assertRaises(Exception):
            writer.git_entry("../x")
        with open(os.path.join(place, ".git", "big"), "wb") as handle:
            handle.write(b"x" * 70000)
        with self.assertRaises(projectfs.WriteConflict):
            writer.git_entry("big")

    def test_many_recorded_directories_are_examined_quickly(self):
        place = os.path.join(self.root, "many")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        dirs = ["d%d/e" % n for n in range(4500)] + ["d%d" % n for n in range(4500)]
        with open(os.path.join(place, projectfs.MARKER), "wb") as handle:
            handle.write(unfinished.build("upgrade", None, "1", [("f", "create", None, "1" * 64)],
                                          dirs=dirs))
        started = time.monotonic()
        found = examine(self, place)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(9000, len(states(found, "dir")))

    def test_the_read_budget_counts_store_reads_too(self):
        path, place = self.good(), self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.run_install(place, path, seed=test_install.SEED)[0])
        project = test_install.manifest.project_id(test_install.SEED)
        self.guarded.write("projects/%s/seen" % project, b"x" * 100)
        self.guarded.write("projects/%s/baselines" % project, b"y" * 100)
        with unittest.mock.patch.object(unfinished, "BUDGET", 10_000_000):
            self.assertNotIn("budget", " ".join(i.detail for i in examine(self, place).items))
        with unittest.mock.patch.object(unfinished, "BUDGET", 150):
            found = examine(self, place)
        self.assertTrue(any(i.kind == "store" and "budget" in i.detail for i in found.items),
                        found.items)


class NoRecord(test_install.InstallBase):
    def marked(self, content):
        place = self.place("proj", "empty")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        with open(os.path.join(place, projectfs.MARKER), "wb") as handle:
            handle.write(content)
        return place

    def test_an_empty_or_unreadable_marker_gives_no_record(self):
        for content in (b"", b"garbage", b"{}", b"[", b"\xff" * 10):
            with self.subTest(content):
                place = self.marked(content)
                found = examine(self, place)
                self.assertIsNone(found.record)
                self.assertEqual((None, None, ()), (found.files, found.store, found.items))
                text = "\n".join(unfinished.render(found))
                self.assertIn("no usable record", text)
                self.assertIn("remove the marker yourself", text)
                os.unlink(os.path.join(place, projectfs.MARKER))
                os.rmdir(os.path.join(place, ".workbench", "local"))
                os.rmdir(os.path.join(place, ".workbench"))
                os.rmdir(place)

    def test_a_marker_that_is_a_directory_gives_no_record(self):
        place = self.place("proj", "empty")
        os.makedirs(os.path.join(place, projectfs.MARKER))
        found = examine(self, place)
        self.assertIsNone(found.record)
        self.assertIn("cannot be read", found.problem)

    def test_a_record_that_claims_a_path_outside_the_project_is_never_trusted(self):
        outside = os.path.join(self.root, "outside")
        with open(outside, "wb") as handle:
            handle.write(b"x")
        place = self.marked(b'{"command":"install","dirs":[],"files":[{"after":"%s","before":null,'
                            b'"op":"create","path":"../outside"}],"format":1,"git":[],'
                            b'"project":null,"store":[],"workbench":"1"}\n' % (b"0" * 64))
        found = examine(self, place)
        self.assertIsNone(found.record)

    def test_hostile_names_are_shown_escaped(self):
        with self.assertRaises(unfinished.UnfinishedError):  # a bidirectional override
            unfinished.build("install", None, "1",
                             [("caf\u00e9/\u202ex.md", "create", None, "1" * 64)])
        place = self.marked_again()
        text = "\n".join(unfinished.render(examine(self, place)))
        self.assertIn("caf\\u00e9", text)
        self.assertNotIn("\u00e9", text)

    def marked_again(self):
        place = os.path.join(self.root, "proj2")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        data = unfinished.build("install", None, "1",
                                [("café/a.md", "replace", "2" * 64, "1" * 64)])
        with open(os.path.join(place, projectfs.MARKER), "wb") as handle:
            handle.write(data)
        return place

    def test_a_long_list_is_capped(self):
        place = os.path.join(self.root, "big")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        files = [("f/%04d.md" % n, "replace", "2" * 64, "1" * 64) for n in range(600)]
        with open(os.path.join(place, projectfs.MARKER), "wb") as handle:
            handle.write(unfinished.build("upgrade", None, "1", files))
        lines = unfinished.render(examine(self, place))
        self.assertLessEqual(len(lines), unfinished.MAX_LISTED + 8)
        self.assertIn("  and 100 more", lines)


class Refusal(test_upgrade.Upgrade):
    def test_a_store_entry_that_is_not_a_file_cannot_be_recorded(self):
        plan = types.SimpleNamespace(writes=[], dirs=(), mode="upgrade",
                                     document={"seed": "seed-1", "workbench": "1"})
        guarded = types.SimpleNamespace(kind=lambda path: "symlink")
        with unittest.mock.patch.object(upgrade.upgradeplan, "store_writes",
                                        return_value=(("projects/x/baselines", b"d"),)):
            with self.assertRaises(unfinished.UnfinishedError) as caught:
                upgrade.record_of(guarded, plan)
        self.assertIn("not a file", str(caught.exception))

    def test_every_command_refuses_a_marked_project_with_the_same_report(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        reports = {}
        for argv in (["preview", "upgrade", self.place, "--package", new],
                     ["upgrade", self.place, "--package", new],
                     ["add", self.place, "--package", new, "--select", "notes"],
                     ["preview", "add", self.place, "--package", new, "--select", "notes"],
                     ["acknowledge", self.place]):
            out, err = io.StringIO(), io.StringIO()
            code = cli.main(argv, out, err, store_root=self.store_root, stdin=io.StringIO(""))
            self.assertEqual((1, ""), (code, out.getvalue()), argv)
            reports[argv[0] + " " + argv[1]] = err.getvalue()
        self.assertEqual(1, len(set(reports.values())), reports)
        text = next(iter(reports.values()))
        self.assertTrue(text.startswith("refused: an unfinished install or upgrade is here"), text)
        self.assertIn("the marker records an unfinished upgrade", text)
        self.assertIn("files after", text)
        self.assertIn("store none", text)
        self.assertIn("`wb recover`", text)
        for line in text.splitlines()[1:]:
            self.assertTrue(line.startswith("  "), line)

    def test_the_failure_report_names_wb_recover(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertIn("`wb recover`", err)

    def test_an_upgrade_stopped_among_the_files_is_mixed(self):
        new = self.ready(notes=base_tests.NOTES2)
        original = projectfs.Writer.replace_file

        def failing(writer, rel, *a, **k):
            if rel == MANIFEST:
                raise OSError("disk full")
            return original(writer, rel, *a, **k)

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", failing):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        found = examine(self, self.place)
        self.assertEqual(("mixed", "none"), (found.files, found.store))
        self.assertEqual("before", states(found, "file")[MANIFEST])
        self.assertEqual("after", states(found, "file")[SCRIPT])
        self.assertEqual(sha(self.read(SCRIPT)), [
            f.after for f in found.record.files if f.path == SCRIPT][0])

    def test_an_upgrade_completed_but_for_the_marker_is_after_all(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(projectfs.Writer, "remove_marker",
                                        side_effect=OSError("no")):
            self.assertEqual(3, self.upgrade("--package", new)[0])
        found = examine(self, self.place)
        self.assertEqual(("after", "all"), (found.files, found.store))
        self.assertEqual(marker_bytes(self.place), unfinished.build(
            "upgrade", found.record.project, found.record.workbench,
            [(f.path, f.op, f.before, f.after) for f in found.record.files], found.record.dirs,
            (), [(s.path, s.before, s.after) for s in found.record.store]))


if __name__ == "__main__":
    unittest.main()
