"""The marker an unfinished `install`, `upgrade` or `add` leaves holds the plan being written."""

import hashlib
import os
import unittest
import unittest.mock

from tests import test_add
from tests import test_install
from tests import test_upgrade
from tests import test_upgrade_preview as base_tests
from workbench import install, installplan, projectfs, store, unfinished

MANIFEST = ".workbench/manifest.json"
SCRIPT = base_tests.SCRIPT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def marker_bytes(place):
    with open(os.path.join(place, *projectfs.MARKER.split("/")), "rb") as handle:
        return handle.read()


def tree_files(top):
    """{relative path: sha256} of every regular file except the marker and `.git`."""
    found = {}
    for base, dirs, names in os.walk(top):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in names:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, top).replace(os.sep, "/")
            if rel != projectfs.MARKER:
                with open(full, "rb") as handle:
                    found[rel] = sha(handle.read())
    return found


class InstallRecord(test_install.InstallBase):
    def failing_files(self, place, path, at):
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == at:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            return self.run_install(place, path, seed=test_install.SEED)

    def finished_files(self, path):
        """The files and store entry an uninterrupted install of the same inputs writes."""
        other = self.place("reference")
        code, out, err = self.run_install(other, path, seed=test_install.SEED)
        self.assertEqual(0, code, (out, err))
        return other

    def test_a_failure_among_the_files_leaves_the_plan_in_the_marker(self):
        path = self.good()
        place = self.place()
        code, out, err = self.failing_files(place, path, 4)
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(place))
        other = self.finished_files(path)
        written = tree_files(other)
        self.assertEqual("install", record.command)
        self.assertEqual(written, {f.path: f.after for f in record.files})
        self.assertEqual({"create"}, {f.op for f in record.files})
        self.assertEqual({None}, {f.before for f in record.files})
        self.assertIn(".workbench", record.dirs)
        self.assertEqual({d for d in record.dirs},
                         {os.path.relpath(base, other).replace(os.sep, "/")
                          for base, _, _ in os.walk(other)
                          if ".git" not in base.split(os.sep)} - {".", ".workbench/local"})
        self.assertEqual([p for p, _ in installplan.GIT_SKELETON], [g.path for g in record.git])
        project = record.project
        self.assertEqual(["projects/%s/baselines" % project, "projects/%s/seen" % project],
                         [s.path for s in record.store])
        self.assertEqual(sha(self.guarded.read("projects/%s/baselines" % project)),
                         record.store[0].after)
        self.assertEqual(test_install.manifest.project_id(test_install.SEED), project)

    def test_the_record_is_in_place_before_anything_else_is_written(self):
        path = self.good()
        place = self.place()
        seen = []
        original = projectfs.Writer.create_git

        def check(writer, skeleton):
            seen.append(unfinished.parse(marker_bytes(place)).command)
            return original(writer, skeleton)

        with unittest.mock.patch.object(projectfs.Writer, "create_git", check):
            code, out, err = self.run_install(place, path)
        self.assertEqual((0, ["install"]), (code, seen), err)

    def test_a_failure_making_the_git_skeleton_leaves_the_record(self):
        path = self.good()
        place = self.place()
        original = projectfs.Writer.create_git

        def failing(writer, skeleton):
            original(writer, skeleton[:3])
            raise OSError("disk full")

        with unittest.mock.patch.object(projectfs.Writer, "create_git", failing):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(place))
        self.assertEqual(len(installplan.GIT_SKELETON), len(record.git))

    def test_an_existing_git_directory_is_not_in_the_record(self):
        path = self.good()
        place = self.place("proj", "git")
        code, out, err = self.failing_files(place, path, 4)
        self.assertEqual(3, code, err)
        self.assertEqual((), unfinished.parse(marker_bytes(place)).git)

    def test_a_failure_writing_the_store_leaves_the_record(self):
        path = self.good()
        place = self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("store full")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(place))
        self.assertEqual(2, len(record.store))
        self.assertIn(MANIFEST, {f.path for f in record.files})

    def test_an_interrupt_leaves_the_record(self):
        path = self.good()
        place = self.place()
        original = projectfs.Writer.create_file
        calls = [0]

        def interrupted(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == 3:
                raise KeyboardInterrupt
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", interrupted):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, err)
        self.assertEqual("install", unfinished.parse(marker_bytes(place)).command)

    def test_the_marker_of_a_finished_install_is_gone_and_the_record_is_not_in_the_project(self):
        path = self.good()
        place = self.place()
        code, out, err = self.run_install(place, path)
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(place, *projectfs.MARKER.split("/"))))

    def test_a_plan_that_cannot_be_recorded_writes_nothing(self):
        path = self.good()
        place = self.place()
        with unittest.mock.patch.object(unfinished, "build",
                                        side_effect=unfinished.UnfinishedError("too big")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(1, code, out)
        self.assertIn("refused:", err)
        self.assertIn("too big", err)
        self.assertIn("nothing was written", err)
        self.assertFalse(os.path.exists(place))

    def test_the_record_does_not_change_the_digest_the_owner_types(self):
        path = self.good()
        place = self.place()
        shown = []
        original = installplan.render

        def render(plan, target_path, show_digest=False):
            shown.append(plan)
            return original(plan, target_path, show_digest)

        with unittest.mock.patch.object(installplan, "render", render):
            code, out, err = self.failing_files(place, path, 4)
        self.assertEqual(3, code, err)
        (plan,) = shown
        self.assertIn(plan.digest, out)
        marker_action = [a for a in plan.actions if a.path == installplan.MARKER_PATH][0]
        self.assertEqual((b"", sha(b"")), (marker_action.data, marker_action.hash))


    def test_whatever_the_marker_holds_the_digest_the_owner_typed_still_matches(self):
        path = self.good()
        place = self.place()
        with unittest.mock.patch.object(install, "record_of", return_value=b'{"other": 1}\n'):
            code, out, err = self.run_install(place, path)
        self.assertEqual(0, code, err)


class UpgradeRecord(test_upgrade.Upgrade):
    def test_a_failure_among_the_files_leaves_the_plan_in_the_marker(self):
        new = self.ready(notes=base_tests.NOTES2)
        old_script, old_manifest = self.read(SCRIPT), self.read(MANIFEST)
        original = projectfs.Writer.replace_file

        def failing(writer, rel, *a, **k):
            if rel == SCRIPT:
                raise OSError("disk full")
            return original(writer, rel, *a, **k)

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", failing):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(self.place))
        self.assertEqual(("upgrade", self.project_id), record[:2])
        by_path = {f.path: f for f in record.files}
        self.assertEqual(unfinished.FileWrite(SCRIPT, "replace", sha(old_script),
                                              sha(base_tests.NOTES2[1]["scripts/run.sh"])),
                         by_path[SCRIPT])
        self.assertEqual(("replace", sha(old_manifest)),
                         (by_path[MANIFEST].op, by_path[MANIFEST].before))
        self.assertEqual((), record.git)
        self.assertEqual(["projects/%s/baselines" % self.project_id], [s.path for s in record.store])

    def test_the_record_equals_what_a_finished_upgrade_wrote(self):
        new = self.ready(notes=test_upgrade.NOTES3)
        failing = unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full"))
        with failing:
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(self.place))
        files = tree_files(self.place)
        self.assertEqual({f.path: f.after for f in record.files},
                         {f.path: files[f.path] for f in record.files})
        self.assertEqual([test_upgrade.EXTRA],
                         sorted(f.path for f in record.files if f.op == "create"))
        self.assertTrue(all(f.before is None for f in record.files if f.op == "create"))
        self.assertEqual((), record.dirs)  # the new file's directory is already there

    def test_a_plan_that_cannot_be_recorded_writes_nothing(self):
        new = self.ready(notes=base_tests.NOTES2)
        before = self.snapshot()
        with unittest.mock.patch.object(unfinished, "build",
                                        side_effect=unfinished.UnfinishedError("too big")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code, out)
        self.assertIn("too big", err)
        self.assertIn("nothing was written", err)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.marker())


class AddRecord(test_add.Add):
    def test_a_failure_leaves_the_plan_in_the_marker(self):
        richer = self.ready(a=test_add.FILL(b"Rule A\n"))
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("full")):
            code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual(3, code, err)
        record = unfinished.parse(marker_bytes(self.place))
        self.assertEqual(("add", self.project_id), record[:2])
        by_path = {f.path: f for f in record.files}
        self.assertEqual(("create", None, sha(b"Rule A\n")),
                         (by_path[test_add.POLICY_A].op, by_path[test_add.POLICY_A].before,
                          by_path[test_add.POLICY_A].after))
        self.assertEqual("replace", by_path["AGENTS.md"].op)
        self.assertEqual(sha(self.read("AGENTS.md")), by_path["AGENTS.md"].after)
        self.assertEqual(sha(self.read(MANIFEST)), by_path[MANIFEST].after)


if __name__ == "__main__":
    unittest.main()
