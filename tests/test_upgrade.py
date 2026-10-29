import io
import os
import shutil
import sys
import unittest
import unittest.mock

from tests import support
from tests import test_upgrade_preview as base_tests
from workbench import acknowledgement, approve, cli, manifest, projectfs, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = base_tests.SCRIPT
POLICY = ".workbench/p/a/policy.md"
MANIFEST = ".workbench/manifest.json"
NOTES3 = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh", "scripts/extra.sh"]},
          {"files/docs/notes.md": b"# Notes\n", "scripts/run.sh": b"#!/bin/sh\necho 3\n",
           "scripts/extra.sh": b"#!/bin/sh\necho extra\n"})
EXTRA = ".workbench/p/notes/scripts/extra.sh"


class Upgrade(base_tests.UpgradePreview):
    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    def ready(self, **changes):
        """An installed project and a newer, approved, cached version of its package."""
        self.old = self.version()
        self.install(self.old)
        self.new = self.version(**changes)
        self.approve(self.new)
        self.warm(self.new)
        return self.new

    def upgrade(self, *args, answer=None, during=None, place=None):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                if during:
                    during()
                if answer is not None:
                    return answer + "\n"
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["upgrade", place or self.place] + list(args), out, err,
                        store_root=self.store_root, stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()

    def baselines(self):
        return acknowledgement.read_baselines(self.guarded, self.project_id)

    def snapshot(self):
        return self.tree(self.place), self.tree(self.store_root)

    def marker(self):
        return os.path.exists(os.path.join(self.place, *projectfs.MARKER.split("/")))


class Writes(Upgrade):
    def test_a_newer_module_is_written_end_to_end(self):
        new = self.ready(notes=base_tests.NOTES2)
        agents = self.read("AGENTS.md")
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))
        self.assertIn("wrote 3 paths in %s" % self.real, out)
        self.assertIn("nothing was committed; committing the result as one change makes it "
                      "revertable", out)
        self.assertFalse(self.marker())
        document = manifest.parse(self.read(MANIFEST))
        self.assertEqual(acknowledgement_hash(self.read(SCRIPT)),
                         [f for f in document["files"] if f["path"] == SCRIPT][0]["hash"])
        self.assertEqual(acknowledgement_hash(self.read(SCRIPT)), self.baselines()[SCRIPT])
        self.assertEqual(agents, self.read("AGENTS.md"))
        self.assertEqual(b"index", self.read(".git/index"))
        # the project is now as acknowledged, and a second upgrade has nothing to do
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing to change", out)

    def test_a_fill_change_replaces_only_the_block(self):
        new = self.ready(a=base_tests.FILL(b"Rule B\n"))
        before = self.read("AGENTS.md")
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        after = self.read("AGENTS.md")
        self.assertIn(b"Rule B", after)
        self.assertNotIn(b"Rule A", after)
        self.assertEqual(before.replace(b"Rule A", b"Rule B"), after)

    def test_a_new_file_of_a_module_is_created_and_recorded(self):
        new = self.ready(notes=NOTES3)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(NOTES3[1]["scripts/extra.sh"], self.read(EXTRA))
        self.assertIn(EXTRA, self.baselines())
        self.assertIn(EXTRA, [f["path"] for f in manifest.parse(self.read(MANIFEST))["files"]])

    def test_nothing_to_change_asks_nothing_and_writes_nothing(self):
        self.old = self.version()
        self.install(self.old)
        before = self.snapshot()
        code, out, err = self.upgrade("--package", self.old, answer="x")
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing to change", out)
        self.assertNotIn("To upgrade", out)
        self.assertEqual(before, self.snapshot())

    def test_a_conflict_is_left_and_reported(self):
        new = self.ready(notes=base_tests.NOTES2)
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        acknowledge_path(self, SCRIPT)
        mine = self.read(SCRIPT)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(mine, self.read(SCRIPT))
        self.assertIn("left as they are:\n  conflict %s" % SCRIPT, out)

    def test_a_script_stays_executable(self):
        self.old = self.version()
        self.install(self.old)
        new = self.version(notes=base_tests.NOTES2)
        os.chmod(os.path.join(new, "notes", "scripts", "run.sh"), 0o755)
        self.approve(new)
        self.warm(new)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        full = os.path.join(self.place, *SCRIPT.split("/"))
        self.assertEqual(0o755, os.stat(full).st_mode & 0o777)


def acknowledgement_hash(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def acknowledge_path(case, rel):
    baselines = acknowledgement.read_baselines(case.guarded, case.project_id)
    baselines[rel] = acknowledgement_hash(case.read(rel))
    case.guarded.write("projects/%s/baselines" % case.project_id, acknowledgement._canonical(
        {"baselines": baselines, "format": 1}))


class Refusals(Upgrade):
    def test_a_wrong_answer_writes_nothing(self):
        new = self.ready(notes=base_tests.NOTES2)
        before = self.snapshot()
        code, out, err = self.upgrade("--package", new, answer="no")
        self.assertEqual((1, ""), (code, err))
        self.assertIn("cancelled: nothing was written", out)
        self.assertEqual(before, self.snapshot())

    def test_a_newer_module_that_is_not_approved_is_refused(self):
        self.old = self.version()
        self.install(self.old)
        new = self.version(notes=base_tests.NOTES2)
        self.warm(new)
        before = self.snapshot()
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not approved", err)
        self.assertEqual(before, self.snapshot())

    def test_an_unacknowledged_edit_is_refused_naming_acknowledge(self):
        new = self.ready(notes=base_tests.NOTES2)
        self.edit(SCRIPT, lambda data: data + b"# someone's\n")
        before = self.snapshot()
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((1, ""), (code, out))
        self.assertIn("run `wb acknowledge` yourself", err)
        self.assertEqual(before, self.snapshot())

    def test_a_file_edited_between_the_preview_and_the_answer_is_refused(self):
        new = self.ready(notes=base_tests.NOTES2)
        edited = []

        def change():
            if not edited:
                edited.append(1)
                self.edit(SCRIPT, lambda data: data + b"# sneaked in\n")

        code, out, err = self.upgrade("--package", new, during=change)
        self.assertEqual(1, code)
        self.assertIn("changed while the plan was shown", err)
        self.assertTrue(self.read(SCRIPT).endswith(b"# sneaked in\n"))
        self.assertNotIn(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))
        self.assertFalse(self.marker())

    def test_the_package_changing_between_the_preview_and_the_answer_is_refused(self):
        new = self.ready(notes=base_tests.NOTES2)
        before = self.read(SCRIPT)

        def change():
            with open(os.path.join(new, "notes", "scripts", "run.sh"), "wb") as handle:
                handle.write(b"#!/bin/sh\necho evil\n")

        code, out, err = self.upgrade("--package", new, during=change)
        self.assertEqual(1, code)
        self.assertIn("nothing was written", err)
        self.assertEqual(before, self.read(SCRIPT))
        self.assertFalse(self.marker())

    def test_a_target_swapped_while_the_plan_was_shown_is_refused(self):
        new = self.ready(notes=base_tests.NOTES2)
        moved = self.place + ".moved"

        def swap():
            os.rename(self.place, moved)
            shutil.copytree(moved, self.place, symlinks=True)

        code, out, err = self.upgrade("--package", new, during=swap)
        self.assertEqual(1, code)
        self.assertIn("refused", err)
        for place in (self.place, moved):
            with open(os.path.join(place, *SCRIPT.split("/")), "rb") as handle:
                self.assertNotIn(base_tests.NOTES2[1]["scripts/run.sh"], handle.read())

    def test_without_terminals_nothing_is_read_or_written(self):
        new = self.ready(notes=base_tests.NOTES2)
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code = cli.main(["upgrade", self.place, "--package", new], out, err,
                            store_root=self.store_root, stdin=io.StringIO("x\n"))
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertIn("refused: upgrade is owner-run", err.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_a_leftover_marker_refuses_the_next_run(self):
        new = self.ready(notes=base_tests.NOTES2)
        full = os.path.join(self.place, *projectfs.MARKER.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb"):
            pass
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code)
        self.assertIn("unfinished", err)

    def test_select_is_a_usage_error(self):
        err = io.StringIO()
        code = cli.main(["upgrade", self.place, "--select", "x"], io.StringIO(), err,
                        store_root=self.store_root, stdin=io.StringIO(""))
        self.assertEqual(2, code)


class Failures(Upgrade):
    def failing_replace(self, after):
        real = projectfs.Writer.replace_file
        calls = []

        def replace(writer, *args, **kwargs):
            calls.append(args[0])
            if len(calls) > after:
                raise projectfs.safefs.SafeFsError("disk full")
            return real(writer, *args, **kwargs)

        return unittest.mock.patch.object(projectfs.Writer, "replace_file", replace)

    def test_a_failure_after_the_first_write_keeps_the_marker_and_exits_3(self):
        new = self.ready(notes=NOTES3, a=base_tests.FILL(b"Rule B\n"))
        was = self.baselines()
        with self.failing_replace(0):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, out)
        self.assertIn("failed: disk full", err)
        self.assertIn("written:\n", err)
        self.assertIn(EXTRA, err)
        self.assertIn("not written:\n", err)
        self.assertIn("the upgrade is unfinished", err)
        self.assertTrue(self.marker())
        self.assertEqual(was, self.baselines())
        self.assertEqual(manifest.parse(self.read(MANIFEST))["workbench"], "0.1.0")

    def test_the_manifest_is_the_last_file_written(self):
        new = self.ready(notes=NOTES3, a=base_tests.FILL(b"Rule B\n"))
        order = []
        real_create, real_replace = (projectfs.Writer.create_file, projectfs.Writer.replace_file)

        def create(writer, rel, *a, **k):
            order.append(rel)
            return real_create(writer, rel, *a, **k)

        def replace(writer, rel, *a, **k):
            order.append(rel)
            return real_replace(writer, rel, *a, **k)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create), \
                unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(0, code, err)
        self.assertEqual(projectfs.MARKER, order[0])
        self.assertEqual(MANIFEST, order[-1])
        self.assertLess(order.index(EXTRA), order.index("AGENTS.md"))

    def test_a_link_planted_where_a_file_is_created_stops_the_write(self):
        new = self.ready(notes=NOTES3)
        real = projectfs.Writer.create_file
        outside = os.path.join(self.root, "outside")

        def create(writer, rel, *a, **k):
            if rel == projectfs.MARKER:
                real(writer, rel, *a, **k)
                os.makedirs(os.path.dirname(os.path.join(self.place, *EXTRA.split("/"))),
                            exist_ok=True)
                os.symlink(outside, os.path.join(self.place, *EXTRA.split("/")))
                return None
            return real(writer, rel, *a, **k)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, out)
        self.assertFalse(os.path.exists(outside))
        self.assertTrue(self.marker())

    def test_a_file_swapped_after_the_check_is_not_replaced(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = projectfs.Writer.create_file

        def create(writer, rel, *a, **k):
            result = real(writer, rel, *a, **k)
            if rel == projectfs.MARKER:
                self.edit(SCRIPT, lambda data: data + b"# raced\n")
            return result

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, out)
        self.assertTrue(self.read(SCRIPT).endswith(b"# raced\n"))
        self.assertIn("not as it was installed", err)


class Marker(Upgrade):
    def test_a_local_directory_that_is_a_link_refuses_without_writing(self):
        new = self.ready(notes=base_tests.NOTES2)
        outside = os.path.join(self.root, "outside")
        os.makedirs(outside)
        local = os.path.join(self.place, ".workbench", "local")
        if os.path.lexists(local):
            shutil.rmtree(local)
        os.symlink(outside, local)
        before = self.tree(outside)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code, out)
        self.assertNotIn("failed:", err)
        self.assertEqual(before, self.tree(outside))
        self.assertNotIn(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))

    def test_a_local_that_is_a_file_refuses_without_writing(self):
        new = self.ready(notes=base_tests.NOTES2)
        local = os.path.join(self.place, ".workbench", "local")
        if os.path.lexists(local):
            shutil.rmtree(local)
        with open(local, "wb") as handle:
            handle.write(b"x")
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code, out)
        self.assertIn("refused: ", err)
        self.assertNotIn("is left in place", err)
        self.assertNotIn(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))

    def test_a_marker_that_cannot_be_made_exits_1_and_writes_no_file(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = projectfs.Writer.create_file

        def create(writer, rel, *a, **k):
            if rel == projectfs.MARKER:
                raise projectfs.WriteConflict("a link is in the way")
            return real(writer, rel, *a, **k)

        before = self.tree(self.place)
        with unittest.mock.patch.object(projectfs.Writer, "create_file", create):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code, out)
        self.assertIn("no file of the project was written", err)
        self.assertNotIn("is left in place", err)
        self.assertEqual(before, self.tree(self.place))

    def test_the_failure_report_says_how_to_recover(self):
        new = self.ready(notes=NOTES3, a=base_tests.FILL(b"Rule B\n"))
        real = projectfs.Writer.replace_file
        with unittest.mock.patch.object(projectfs.Writer, "replace_file",
                                        side_effect=projectfs.safefs.SafeFsError("disk full")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertIn("put the files listed as written back", err)
        self.assertTrue(real)


DIGEST_LINE = "digest: "


def typed_digest(out):
    def read(*args):
        lines = [x for x in out.getvalue().splitlines() if x.startswith(DIGEST_LINE)]
        return lines[-1][len(DIGEST_LINE):][:12] + "\n"
    return read


class Chain(base_tests.UpgradePreview):
    """The project is made by the real `wb install`, acknowledged clean, then upgraded."""

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)
        self.old = self.version()
        self.approve(self.old)
        code, out, err = self.cmd("install", "--package", self.old, "--select", "h", "notes", "a")
        self.assertEqual((0, ""), (code, err), out)
        self.real = os.path.realpath(self.place)
        self.project_id = manifest.project_id(manifest.parse(self.read(MANIFEST))["seed"])
        code, out, err = self.cmd("acknowledge")
        self.assertEqual((0, "nothing to acknowledge\n", ""), (code, out, err))

    def cmd(self, name, *args):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            readline = typed_digest(out)

        code = cli.main([name, self.place] + list(args), out, err, store_root=self.store_root,
                        stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()

    def files(self):
        found = {}
        for base, dirs, names in os.walk(self.place):
            if ".git" in dirs:
                dirs.remove(".git")
            for name in names:
                full = os.path.join(base, name)
                with open(full, "rb") as handle:
                    found[os.path.relpath(full, self.place)] = handle.read()
        return found

    def newer(self, **changes):
        new = self.version(**changes)
        self.approve(new)
        self.warm(new)
        return new

    def mark_acknowledged(self, rel):
        code, out, err = self.cmd("acknowledge")
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn(rel, out)

    def test_each_classification_end_to_end(self):
        self.edit(SCRIPT, lambda d: d + b"mine\n")
        self.mark_acknowledged(SCRIPT)
        new = self.newer(notes=NOTES3, a=base_tests.FILL(b"Rule B\n"))
        before = self.files()
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual((0, ""), (code, err), out)
        for expected in ("create %s" % EXTRA, "replace %s" % POLICY,
                         "replace AGENTS.md block p/a slot:policy",
                         "conflict %s" % SCRIPT, "skip docs/README.md [seeded]"):
            self.assertIn(expected, out)
        after = self.files()
        self.assertEqual(set(before) - {".workbench/local/incomplete"},
                         set(after) - {EXTRA} - {".workbench/local/incomplete"})
        changed = {path for path in before if path in after and before[path] != after[path]}
        self.assertEqual({POLICY, ".workbench/p/notes/module.json", "AGENTS.md", MANIFEST},
                         changed)
        self.assertEqual(before[SCRIPT], after[SCRIPT])
        self.assertEqual(before["AGENTS.md"].replace(b"Rule A", b"Rule B"), after["AGENTS.md"])
        for seeded in ("docs/README.md", "docs/notes.md"):
            self.assertEqual(before[seeded], after[seeded])
        self.assertIn(acknowledgement_hash(after[MANIFEST]), out)
        stored = self.guarded.read("projects/%s/baselines" % self.project_id)
        self.assertIn(acknowledgement_hash(stored), out)
        self.assertEqual((0, "nothing to acknowledge\n", ""), self.cmd("acknowledge"))

    def test_slot_gone_and_a_dropped_module_are_left_in_place(self):
        agents = self.read("AGENTS.md")
        start = agents.index(b"<!-- BEGIN p/a")
        stop = agents.index(b"<!-- END p/a slot:policy -->\n") + len(b"<!-- END p/a slot:policy -->\n")
        self.edit("AGENTS.md", lambda d: d[:start] + d[stop:])
        self.mark_acknowledged("AGENTS.md")
        new = self.version(notes=NOTES3, a=base_tests.FILL(b"Rule B\n"))
        self.approve(new)
        self.warm(new)
        before = self.files()
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("slot gone", out)
        self.assertEqual(before["AGENTS.md"], self.files()["AGENTS.md"])
        # a package that no longer declares module a
        dropped = self.package("p", {"h": (base_tests.HARNESS, {}), "notes": NOTES3})
        self.approve(dropped)
        self.warm(dropped)
        code, out, err = self.cmd("upgrade", "--package", dropped)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("left in place", out)
        self.assertEqual(set(before), set(self.files()) - {EXTRA} | {EXTRA} & set(before))
        self.assertTrue(os.path.exists(os.path.join(self.place, POLICY)))

    def test_a_missing_slot_marker_appends_a_new_block(self):
        self.edit("AGENTS.md", lambda d: d.replace(b"<!-- @slot: policy -->\n", b""))
        self.mark_acknowledged("AGENTS.md")
        extra = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"],
                  "fills": [{"slot": "slot:policy", "source": "policy.md"}]},
                 {"files/docs/notes.md": b"# Notes\n", "scripts/run.sh": b"#!/bin/sh\n",
                  "policy.md": b"Rule N\n"})
        new = self.newer(notes=extra)
        before = self.read("AGENTS.md")
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("append AGENTS.md block p/notes slot:policy", out)
        after = self.read("AGENTS.md")
        self.assertTrue(after.startswith(before))
        self.assertIn(b"Rule N", after)

    def test_an_upgrade_right_after_an_uncommitted_install_works(self):
        new = self.newer(notes=base_tests.NOTES2)
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))
        self.assertIn("nothing was committed", out)

    def test_the_not_approved_cases_leave_everything_unchanged(self):
        new = self.version(notes=base_tests.NOTES2)
        self.warm(new)
        before = (self.files(), self.tree(self.store_root))
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual(1, code)
        self.assertIn("not approved", err)
        approved = self.newer(notes=base_tests.NOTES2)
        before = (self.files(), self.tree(self.store_root))
        for answer in ("", "no"):
            outs, errs = io.StringIO(), io.StringIO()

            class Ask(io.StringIO):
                def readline(this, *a):
                    return answer + "\n"

            self.assertEqual(1, cli.main(["upgrade", self.place, "--package", approved], outs, errs,
                                         store_root=self.store_root, stdin=Ask("")))
        self.assertEqual(before[0], self.files())
        self.assertEqual(before[1], self.tree(self.store_root))

    def test_a_lower_workbench_version_is_refused(self):
        document = manifest.parse(self.read(MANIFEST))
        document["workbench"] = "9.0.0"
        self.edit(MANIFEST, lambda d: manifest.serialize(document))
        new = self.newer(notes=base_tests.NOTES2)
        code, out, err = self.cmd("upgrade", "--package", new)
        self.assertEqual(1, code)
        self.assertIn("newer than", err)


class Finish(Upgrade):
    def test_ctrl_c_while_printing_the_result_is_not_a_failure(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch("workbench.upgrade._finish", side_effect=KeyboardInterrupt):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(0, code)
        self.assertNotIn("nothing was written", out + err)
        self.assertFalse(self.marker())

    def test_ctrl_c_before_the_answer_is_still_130(self):
        new = self.ready(notes=base_tests.NOTES2)
        before = self.snapshot()

        def interrupt():
            raise KeyboardInterrupt

        code, out, err = self.upgrade("--package", new, during=interrupt)
        self.assertEqual(130, code)
        self.assertIn("cancelled: nothing was written", out)
        self.assertEqual(before, self.snapshot())

    def test_a_marker_removed_by_someone_else_is_a_warning_not_a_failure(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = store.Store.write

        def write(guarded, rel, data):
            real(guarded, rel, data)
            os.unlink(os.path.join(self.place, *projectfs.MARKER.split("/")))

        with unittest.mock.patch.object(store.Store, "write", write):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(0, code, err)
        self.assertIn("warning: the marker", err)
        self.assertIn("was already gone", err)

    def test_a_marker_that_cannot_be_removed_is_a_failure_not_a_warning(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = projectfs.Writer.remove_marker

        def remove(writer):
            raise projectfs.safefs.SafeFsError("permission denied")

        with unittest.mock.patch.object(projectfs.Writer, "remove_marker", remove):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertNotIn("already gone", err)
        self.assertTrue(self.marker())
        self.assertTrue(real)

    def test_a_file_that_is_not_what_was_written_is_a_failure(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = store.Store.write

        def write(guarded, rel, data):
            real(guarded, rel, data)
            self.edit(SCRIPT, lambda d: d + b"# after\n")

        with unittest.mock.patch.object(store.Store, "write", write):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertIn("is not what was written", err)
        self.assertTrue(self.marker())
        self.assertIn("only the store entries or the marker are left", err)

    def test_a_directory_moved_away_after_the_write_is_not_reported_as_written(self):
        new = self.ready(notes=base_tests.NOTES2)
        real = store.Store.write

        def write(guarded, rel, data):
            real(guarded, rel, data)
            scripts = os.path.join(self.place, ".workbench", "p", "notes", "scripts")
            os.rename(scripts, os.path.join(self.root, "moved-away"))

        with unittest.mock.patch.object(store.Store, "write", write):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertNotIn("wrote", out)

    def test_a_failed_store_write_says_to_remove_the_marker_and_acknowledge(self):
        new = self.ready(notes=base_tests.NOTES2)
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("disk full")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertIn("run `wb acknowledge`", err)
        self.assertNotIn("put the files listed as written back", err)

    def test_a_failure_before_the_manifest_says_to_put_files_back(self):
        new = self.ready(notes=NOTES3)
        with unittest.mock.patch.object(projectfs.Writer, "replace_file",
                                        side_effect=projectfs.safefs.SafeFsError("disk full")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertIn("put the files listed as written back", err)


SKILL_ITEM = ".workbench/p/notes/harness/neutral/skills/sample/SKILL.md"
POINTER = "the rendered skills, agents or commands may be behind; `wb preview rerender` shows which"


SKILL_HEAD = b"---\nname: sample\ndescription: A sample skill\n---\n"
OTHER_ITEM = ".workbench/p/notes/harness/neutral/skills/other/SKILL.md"


def with_skill(text, scripts=b"#!/bin/sh\n", other=None):
    """The notes module with one neutral skill whose body is `text`, and a second skill when `other` is given."""
    files = {"files/docs/notes.md": b"# Notes\n", "scripts/run.sh": scripts,
             "harness/neutral/skills/sample/SKILL.md": SKILL_HEAD + text}
    if other is not None:
        files["harness/neutral/skills/other/SKILL.md"] = SKILL_HEAD.replace(b"sample", b"other") + other
    return {"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]}, files


class Pointer(Upgrade):
    """After an upgrade that wrote a harness item, one line points at `wb preview rerender`."""

    MODULES = {"h": (base_tests.HARNESS, {}), "notes": with_skill(b"Do the thing.\n"),
               "a": base_tests.FILL(b"Rule A\n")}

    def test_a_written_harness_item_prints_the_line_once_after_the_count(self):
        new = self.ready(notes=with_skill(b"Do the other thing.\n"))
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(b"Do the other thing.\n", self.read(SKILL_ITEM)[len(SKILL_HEAD):])
        self.assertEqual(1, out.count(POINTER), out)
        lines = out.splitlines()
        self.assertEqual(lines.index(POINTER) - 1,
                         [i for i, line in enumerate(lines) if line.lstrip("> ").startswith("wrote ")][0])

    def test_a_created_harness_item_prints_the_line(self):
        new = self.ready(notes=with_skill(b"Do the thing.\n", other=b"More.\n"))
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(SKILL_HEAD.replace(b"sample", b"other") + b"More.\n", self.read(OTHER_ITEM))
        self.assertEqual(1, out.count(POINTER), out)

    def test_an_upgrade_that_wrote_no_harness_item_prints_no_line(self):
        new = self.ready(notes=with_skill(b"Do the thing.\n", scripts=b"#!/bin/sh\necho 2\n"))
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("wrote ", out)
        self.assertNotIn("wb preview rerender", out)

    def test_the_preview_prints_no_line(self):
        new = self.ready(notes=with_skill(b"Do the other thing.\n"))
        code, out, err = self.preview("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertNotIn("wb preview rerender", out)

    def test_nothing_outside_the_workbench_folder_and_git_is_written(self):
        new = self.ready(notes=with_skill(b"Do the other thing.\n"))
        before = self.tree(self.place)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        after = self.tree(self.place)
        changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        self.assertTrue(all(path.split(os.sep)[0] in (".workbench", ".git") for path in changed), changed)
        self.assertIn("nothing was committed", out)

    def test_a_failed_upgrade_prints_no_line(self):
        new = self.ready(notes=with_skill(b"Do the other thing.\n"))
        with unittest.mock.patch.object(projectfs.Writer, "replace_file",
                                        side_effect=projectfs.safefs.SafeFsError("disk full")):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code)
        self.assertNotIn("wb preview rerender", out + err)


class Terminal(base_tests.UpgradePreview):
    """The command run in a child process whose terminals are real pseudo-terminals."""

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        self.store_root = os.path.join(self.root, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.old = self.version()
        self.install(self.old)
        self.new = self.version(notes=base_tests.NOTES2)
        self.approve(self.new)
        self.warm(self.new)

    def drive(self, answer, **kwargs):
        env = dict(os.environ, HOME=self.root, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
                   PATH=support.clean_path())
        argv = [sys.executable, "-B", "-m", "workbench", "upgrade", self.place, "--package",
                self.new]
        return support.drive_pty(self, argv, env, self.root, answer, b"> ", **kwargs)

    def digest(self, shown):
        return [x for x in shown.splitlines() if x.startswith("digest: ")][0][8:20]

    def test_the_digest_typed_in_a_terminal_upgrades(self):
        code, output, error = self.drive(self.digest)
        self.assertEqual((0, ""), (code, error), output)
        self.assertIn("nothing was committed", output)
        self.assertEqual(base_tests.NOTES2[1]["scripts/run.sh"], self.read(SCRIPT))

    def test_any_other_text_in_a_terminal_writes_nothing(self):
        before = self.tree(self.place)
        code, output, error = self.drive("no")
        self.assertEqual(1, code, error)
        self.assertIn("cancelled: nothing was written", output)
        self.assertEqual(before, self.tree(self.place))

    def test_without_terminals_it_refuses(self):
        code, output, error = self.drive("x", stdin="pipe", stdout="pipe")
        self.assertEqual(1, code)
        self.assertIn("refused: upgrade is owner-run", error)


if __name__ == "__main__":
    unittest.main()
