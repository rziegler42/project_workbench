"""``wb upgrade`` and ``wb add`` at the level ``none``: no terminal, nothing typed, the attempt and the outcome logged.

Plan ``2026-10-27-a-level-for-every-command``, increment G (``docs/specs/command-permissions.md``, "One way to run at
``none``"). The project, its harness and its rendering record are those of ``test_approve_levels``. Unlike ``install``,
the command acts on the project it is run from, so the level is read for that project and the plan must be for it."""

import io
import os
import tempfile
import unittest
import unittest.mock

from tests.test_approve_levels import Ask
from tests.test_delegation import provider_module
from tests.test_preview import NOTES
from workbench import acknowledgement, approve, cli, levellog, levelrun, rendering, store, upgrade, verify

# The packages are approved and cached with the checks of an owner's machine; the project's fixture treats them as
# first-party so that attach and the commands accept the synthetic provider.
VERIFY_PACKAGES = verify.verify_packages

PROVIDER = ".workbench/p/review/helper/tool"
EXTRA = ".workbench/p/extra/scripts/run.sh"


class NoInput(io.StringIO):
    """A standard input that fails if it is read: nothing is asked at ``none``."""

    def readline(self, limit=-1):
        raise AssertionError("standard input was read")

    read = readlines = readline


class Base(Ask):
    """The attached project, a newer approved version of its package and a richer one with a module to add."""

    KEY = "wb upgrade"
    MODE = "upgrade"

    def setUp(self):
        super().setUp()
        self.levels = {self.KEY: "none"}

    def table(self, **table):
        import json
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": table}).encode())

    def attach_at(self, level="none"):
        self.table(**{self.KEY: level} if level else {})
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def package_for(self, modules):
        path = self.package("p", modules)
        saved = self.MODULES
        self.MODULES = modules
        try:
            with unittest.mock.patch.object(verify, "verify_packages", VERIFY_PACKAGES):
                self.approve(path)
                self.warm(path)
        finally:
            self.MODULES = saved
        return path

    def newer(self):
        module, files = provider_module()
        files = dict(files)
        files["helper/tool"] = files["helper/tool"] + b"# a newer version\n"
        return self.package_for(dict(self.MODULES, review=(module, files)))

    def richer(self):
        return self.package_for(dict(self.MODULES, extra=NOTES))

    def arguments(self):
        return ["--package", self.newer()] if self.MODE == "upgrade" else ["--package", self.richer(), "--select", "extra"]

    def log(self):
        if self.guarded.kind(levellog.LOG) != "file":
            return []
        return self.guarded.read(levellog.LOG).decode("ascii").splitlines()

    def run_it(self, argv, stdin=None, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(cwd or self.real)
        try:
            code = cli.main([self.MODE, self.real] + list(argv), out, err, store_root=self.store_root,
                            distribution=self.dist, stdin=stdin if stdin is not None else NoInput())
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def snapshot(self):
        return self.tree(self.real), self.tree(self.store_root), self.log()

    def refused(self, argv, contains="owner-run", **kwargs):
        before = self.snapshot()
        code, out, err = self.run_it(argv, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, self.snapshot())
        return err

    def written(self):
        return PROVIDER if self.MODE == "upgrade" else EXTRA

    def present(self):
        return os.path.exists(os.path.join(self.real, *self.written().split("/")))


class AtNone(Base):
    def setUp(self):
        super().setUp()
        self.attach_at("none")

    def test_it_runs_with_no_terminal_and_asks_nothing(self):
        self.assertFalse(self.present() and self.MODE == "add")
        code, out, err = self.run_it(self.arguments())
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(self.present())
        self.assertIn("nothing is asked", out)
        self.assertIn("digest:", out)
        self.assertIn("nothing was committed", out)

    def test_the_log_has_the_attempt_before_the_writes_and_the_outcome_after(self):
        arguments = self.arguments()
        seen = []
        original = upgrade._write

        def write(*args, **kwargs):
            seen.append(self.log())
            return original(*args, **kwargs)

        with unittest.mock.patch.object(upgrade, "_write", write):
            code, out, err = self.run_it(arguments)
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual([self.KEY, "none"], fields[3:5])
        self.assertRegex(fields[5], r"\Adigest:[0-9a-f]{64}\Z")
        self.assertEqual("digest:" + [line.split()[-1] for line in out.splitlines() if line.startswith("digest:")][-1],
                         fields[5])
        self.assertEqual(["O", fields[1]], outcome.split("\t")[:2])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_a_table_edited_after_attach_reads_block(self):
        self.table(**{self.KEY: "none", "wb install": "none"})
        self.refused(self.arguments())

    def test_a_missing_rendering_record_reads_block(self):
        arguments = self.arguments()
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.refused(arguments)

    def test_a_harness_file_edited_after_attach_reads_block(self):
        arguments = self.arguments()
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.refused(arguments)

    def test_a_directory_that_is_no_project_cannot_run_it_and_says_why(self):
        arguments = self.arguments()
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(arguments, cwd=tmp)

    def test_a_change_not_acknowledged_is_refused_and_nothing_is_written(self):
        arguments = self.arguments()
        full = os.path.join(self.real, *PROVIDER.split("/"))
        with open(full, "ab") as handle:
            handle.write(b"# edited by someone else\n")
        before = self.snapshot()
        code, out, err = self.run_it(arguments)
        self.assertEqual(1, code, (out, err))
        self.assertIn("wb acknowledge", err)
        self.assertEqual(before, self.snapshot())

    def test_a_plan_for_another_project_than_the_level_was_read_for_is_refused(self):
        arguments = self.arguments()
        elsewhere = levelrun.Route(False, "none", "0" * 16, self.real)
        before = self.snapshot()
        with unittest.mock.patch.object(upgrade.levelrun, "route", lambda *a, **k: elsewhere):
            code, out, err = self.run_it(arguments)
        self.assertEqual(1, code, (out, err))
        self.assertIn("not the project", err)
        self.assertEqual(before, self.snapshot())

    def test_an_attempt_that_cannot_be_written_writes_nothing(self):
        arguments = self.arguments()
        before = self.snapshot()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.run_it(arguments)
        self.assertEqual(1, code, (out, err))
        self.assertIn("the log is full", err)
        self.assertIn("nothing was written", err)
        self.assertEqual(before, self.snapshot())

    def test_an_outcome_that_cannot_be_written_after_the_writes_exits_3_and_says_so(self):
        arguments = self.arguments()
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("no space")):
            code, out, err = self.run_it(arguments)
        self.assertEqual(3, code, (out, err))
        self.assertIn("outcome was not logged", err)
        self.assertTrue(self.present())

    def test_a_failed_write_is_a_refused_outcome_and_exits_3(self):
        arguments = self.arguments()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("disk gone")):
            code, out, err = self.run_it(arguments)
        self.assertEqual(3, code, (out, err))
        attempt, outcome = self.log()
        self.assertEqual("refused", outcome.split("\t")[3])

    def test_a_marker_that_cannot_be_made_is_a_refused_outcome_before_writing(self):
        arguments = self.arguments()
        with unittest.mock.patch.object(upgrade, "_write", side_effect=upgrade.NotStarted("no marker")):
            code, out, err = self.run_it(arguments)
        self.assertEqual(1, code, (out, err))
        attempt, outcome = self.log()
        self.assertEqual(["refused", "refused before writing"], outcome.split("\t")[3:])

    def test_a_module_that_is_not_approved_is_refused_before_any_write(self):
        modules = dict(self.MODULES, extra=NOTES) if self.MODE == "add" else dict(self.MODULES)
        path = self.package("p", dict(modules, review=provider_module(ships=["helper/tool", "helper/more"])[0:1] + ({"helper/tool": b"x", "helper/more": b"y"},))) if self.MODE == "upgrade" else self.package("p", modules)
        argv = ["--package", path] + (["--select", "extra"] if self.MODE == "add" else [])
        before = self.snapshot()
        code, out, err = self.run_it(argv)
        self.assertEqual(1, code, (out, err))
        self.assertIn("approv", err)
        self.assertEqual(before, self.snapshot())

    def test_the_preview_is_unchanged_and_logs_nothing(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", self.MODE, self.real] + self.arguments(), out, err, store_root=self.store_root,
                        distribution=self.dist)
        self.assertEqual((0, ""), (code, err.getvalue()), out.getvalue())
        self.assertEqual([], self.log())


class UpgradeNothingToChange(Base):
    def test_nothing_to_change_writes_no_entry(self):
        self.attach_at("none")
        code, out, err = self.run_it(["--package", self.pkg])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing to change", out)
        self.assertEqual([], self.log())


class AtNoneForAdd(AtNone):
    KEY = "wb add"
    MODE = "add"


class AtBlock(Base):
    """The key at its default, and at ``block`` set in the table: the terminal rules apply as before."""

    def test_it_refuses_without_a_terminal_at_the_default(self):
        self.attach_at(None)
        self.refused(self.arguments())

    def test_it_refuses_without_a_terminal_at_block(self):
        self.attach_at("block")
        self.refused(self.arguments())

    def test_the_other_key_at_none_does_not_let_this_one_run(self):
        self.table(**{("wb add" if self.KEY == "wb upgrade" else "wb upgrade"): "none"})
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.refused(self.arguments())


class AtBlockForAdd(AtBlock):
    KEY = "wb add"
    MODE = "add"


if __name__ == "__main__":
    unittest.main()
