"""``wb install`` and ``wb adopt`` at the level ``none``: no terminal, nothing typed, the attempt and the outcome logged.

Plan ``2026-10-27-a-level-for-every-command``, increment F (``docs/specs/command-permissions.md``, "One way to run at
``none``"). The project the command is run from, its harness and its rendering record are those of ``test_approve_levels``;
the target is a new directory (or, for adopt, a repository with content) and the packages are those of ``test_install``."""

import io
import json
import os
import shutil
import tempfile
import unittest
import unittest.mock

from tests import support_harness
from tests.test_adopt_preview import AdoptPreviewBase
from tests.test_approve_levels import Ask
from tests.test_install import InstallBase, MARKER, Typist, correct
from tests.test_preview import HARNESS, NOTES
from workbench import approve, install, levellog, levelrun, preview, rendering, sources, verify

# The fixture of the project treats its own packages as first-party so that attach accepts them; the packages installed
# here are verified as an owner's would be, so the originals are put back once the project is attached.
VERIFY_PACKAGE, VERIFY_PACKAGES = verify.verify_package, verify.verify_packages

KEY_INSTALL, KEY_ADOPT = "wb install", "wb adopt"
WARNING = "warning: the existing .git is used as it is; no remote is recorded\n"


class NoInput(io.StringIO):
    """A standard input that fails if it is read: nothing is asked at ``none``."""

    def readline(self, limit=-1):
        raise AssertionError("standard input was read")

    read = readlines = readline


class Base(Ask):
    """A project with an attached harness, from which the command is run, and the packages of an install."""

    package = InstallBase.package
    approve_package = InstallBase.approve
    place = InstallBase.place
    tree = InstallBase.tree
    read = InstallBase.read

    def setUp(self):
        super().setUp()
        self.count = 0
        self.target_root = os.path.join(self.root, "targets")
        os.makedirs(self.target_root)

    def levels(self, **table):
        document = {"version": 2, "checkpoints": {}, "floor": [], "levels": table}
        self.guarded.write("settings", json.dumps(document).encode())

    def attach_with(self, **table):
        self.levels(**table)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        for name, original in (("verify_package", VERIFY_PACKAGE), ("verify_packages", VERIFY_PACKAGES)):
            patch = unittest.mock.patch.object(verify, name, original)
            patch.start()
            self.addCleanup(patch.stop)

    # The project already holds modules `h` and `tool` with these declarations; another name keeps the approvals apart.
    MODULES_OF_TARGET = ("hq", "notesq")

    def package_of_target(self):
        return self.package(name="q", modules={"hq": (HARNESS, {}), "notesq": NOTES})

    def good(self):
        path = self.package_of_target()
        os.chmod(os.path.join(path, "notesq", "scripts", "run.sh"), 0o755)
        self.approve_package(path)
        return path

    def target(self, name="proj"):
        return os.path.join(self.target_root, name)

    def log(self):
        if self.guarded.kind(levellog.LOG) != "file":
            return []
        return self.guarded.read(levellog.LOG).decode("ascii").splitlines()

    def run_install(self, place, path, adopt=False, stdin=None, select=("hq", "notesq"), seed=None):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(path, None)], list(select))
        code = install.run(self.guarded, command, stdin if stdin is not None else NoInput(), out, err, seed=seed,
                           adopt=adopt, cwd=self.real)
        return code, out.getvalue(), err.getvalue()

    def refused(self, place, path, contains="owner-run", **kwargs):
        before = (self.tree(self.target_root), self.log())
        code, out, err = self.run_install(place, path, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, (self.tree(self.target_root), self.log()))
        return err


class InstallAtNone(Base):
    def setUp(self):
        super().setUp()
        self.attach_with(**{KEY_INSTALL: "none"})

    def test_it_installs_with_no_terminal_and_asks_nothing(self):
        place = self.target()
        code, out, err = self.run_install(place, self.good())
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))
        self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
        self.assertIn("digest:", out)
        self.assertIn("nothing is asked", out)
        self.assertIn("nothing was committed", out)

    def test_it_writes_what_a_terminal_install_writes(self):
        path = self.good()
        at_terminal = self.target("terminal")
        out = io.StringIO()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True):
            command = sources.Command(at_terminal, [(path, None)], ["hq", "notesq"])
            self.assertEqual(0, install.run(self.guarded, command, Typist(out, correct), out, io.StringIO(),
                                            cwd=self.real))
        without = self.target("without")
        self.assertEqual(0, self.run_install(without, path)[0])

        def files(top):
            found = {}
            for rel in self.tree(top):
                full = os.path.join(top, rel)
                # The manifest holds each project's own seed and identifier; the rest is the same bytes.
                if os.path.isfile(full) and not rel.startswith(".git" + os.sep) and rel != os.path.join(".workbench", "manifest.json") \
                        and not rel.startswith(os.path.join(".workbench", "local")):
                    found[rel] = (os.stat(full).st_mode & 0o777, self.read(full))
            return found
        self.assertTrue(files(at_terminal))
        self.assertEqual(files(at_terminal), files(without))
        self.assertEqual(2, len(self.log()))  # only the run without a terminal is logged

    def test_the_log_has_the_attempt_before_the_writes_and_the_outcome_after(self):
        place = self.target()
        seen = []
        original = install._write

        def write(*args, **kwargs):
            seen.append(self.log())
            return original(*args, **kwargs)

        with unittest.mock.patch.object(install, "_write", write):
            code, out, err = self.run_install(place, self.good())
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual(["A", seen[0][0].split("\t")[1]], fields[:2])
        self.assertEqual(["wb install", "none"], fields[3:5])
        self.assertRegex(fields[5], r"\Adigest:[0-9a-f]{64}\Z")
        self.assertEqual(["O", fields[1]], outcome.split("\t")[:2])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_the_digest_logged_is_the_digest_printed(self):
        code, out, err = self.run_install(self.target(), self.good())
        self.assertEqual(0, code, err)
        printed = [line.split()[-1] for line in out.splitlines() if line.startswith("digest:")][-1]
        self.assertEqual("digest:" + printed, self.log()[0].split("\t")[5])

    def test_a_table_edited_after_attach_reads_block(self):
        self.levels(**{KEY_INSTALL: "none", "wb adopt": "none"})
        self.refused(self.target(), self.good())

    def test_a_missing_rendering_record_reads_block(self):
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.refused(self.target(), self.good())

    def test_a_harness_file_edited_after_attach_reads_block(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.refused(self.target(), self.good())

    def test_a_directory_that_is_no_project_cannot_run_it_and_says_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            command = sources.Command(self.target(), [(self.good(), None)], ["hq", "notesq"])
            code = install.run(self.guarded, command, NoInput(), out, err, cwd=tmp)
        self.assertEqual(1, code)
        self.assertTrue(err.getvalue().startswith("refused: install is owner-run"), err.getvalue())
        self.assertEqual({}, self.tree(self.target_root))
        self.assertEqual([], self.log())

    def test_an_unapproved_module_is_refused_before_any_write(self):
        path = self.package_of_target()
        self.refused(self.target(), path, contains="approv")

    def test_a_package_that_changes_while_it_runs_is_refused_before_any_write(self):
        path = self.good()
        original = preview.prepare
        calls = []

        def prepare(*args, **kwargs):
            plan, warnings = original(*args, **kwargs)
            calls.append(1)
            return (plan._replace(digest="0" * 64) if len(calls) > 1 else plan), warnings

        with unittest.mock.patch.object(preview, "prepare", prepare):
            self.refused(self.target(), path, contains="changed")

    def test_an_unwritable_log_refuses_before_any_write(self):
        os.mkdir(os.path.join(self.store_root, levellog.LOG))
        self.refused(self.target(), self.good(), contains="level log")

    def test_a_failure_while_writing_exits_3_and_logs_a_refused_outcome(self):
        place = self.target()
        path = self.good()
        with unittest.mock.patch.object(type(self.guarded), "write", side_effect=OSError("disk full")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, (out, err))
        self.assertIn("failed: disk full", err)
        attempt, outcome = self.log()
        self.assertEqual(["refused", "stopped after writing (exit 3)"], outcome.split("\t")[3:])

    def test_an_outcome_that_cannot_be_logged_after_the_writes_exits_3(self):
        original = install._finish

        def finish(*args, **kwargs):
            original(*args, **kwargs)
            os.unlink(os.path.join(self.store_root, levellog.LOG))
            os.mkdir(os.path.join(self.store_root, levellog.LOG))

        with unittest.mock.patch.object(install, "_finish", finish):
            code, out, err = self.run_install(self.target(), self.good())
        self.assertEqual(3, code, (out, err))
        self.assertIn("outcome was not logged", err)
        self.assertTrue(os.path.isfile(os.path.join(self.target(), ".workbench", "manifest.json")))

    def test_a_terminal_run_asks_as_before_and_is_not_logged(self):
        place = self.target()
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.good(), None)], ["hq", "notesq"])
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True):
            code = install.run(self.guarded, command, Typist(out, correct), out, err, cwd=self.real)
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))
        self.assertIn("type the first 12 characters", out.getvalue())
        self.assertEqual([], self.log())

    def test_a_terminal_run_reads_no_level(self):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(self.target(), [(self.good(), None)], ["hq", "notesq"])
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True), \
                unittest.mock.patch.object(levelrun, "level_now", side_effect=AssertionError("read")):
            code = install.run(self.guarded, command, Typist(out, correct), out, err, cwd=self.real)
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))

    def test_an_interrupt_after_the_writes_is_reported_as_written(self):
        place = self.target()
        path = self.good()
        with unittest.mock.patch.object(levelrun, "done", side_effect=KeyboardInterrupt()):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code, (out, err))
        self.assertIn("interrupted before its outcome was logged", err)
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))
        self.assertEqual(1, len(self.log()))

    def test_a_target_inside_the_project_the_level_was_read_for_is_accepted(self):
        # The level is the owner's setting for the project the agent works in; the target is not that project.
        os.mkdir(os.path.join(self.real, "sub"))
        inside = os.path.join(self.real, "sub", "child")
        code, out, err = self.run_install(inside, self.good())
        self.assertEqual(0, code, (out, err))
        self.assertEqual(2, len(self.log()))

    def test_an_interrupt_before_any_write_logs_nothing(self):
        with unittest.mock.patch.object(preview, "prepare", side_effect=KeyboardInterrupt()):
            code, out, err = self.run_install(self.target(), self.good())
        self.assertEqual(130, code)
        self.assertEqual([], self.log())


class InstallOtherLevels(Base):
    """A clone attaches once, so each level is its own test."""

    def test_the_default_level_refuses_without_a_terminal(self):
        self.attach_with()
        self.refused(self.target(), self.good())

    def test_a_level_of_block_refuses_without_a_terminal(self):
        self.attach_with(**{KEY_INSTALL: "block"})
        self.refused(self.target(), self.good())

    def test_another_key_at_none_does_not_open_install(self):
        self.attach_with(**{KEY_ADOPT: "none"})
        self.refused(self.target(), self.good())

    def test_the_level_ask_is_not_offered_and_reads_block(self):
        self.attach_with(**{KEY_INSTALL: "ask"})
        self.refused(self.target(), self.good())


class AdoptAtNone(Base, AdoptPreviewBase):
    def setUp(self):
        Base.setUp(self)
        self.attach_with(**{KEY_ADOPT: "none"})

    def repo_target(self, name="repo"):
        place = os.path.join(self.target_root, name)
        os.makedirs(os.path.join(place, ".git"))
        with open(os.path.join(place, ".git", "index"), "wb") as handle:
            handle.write(b"index")
        with open(os.path.join(place, "README.md"), "wb") as handle:
            handle.write(b"hello\n")
        return place

    def test_it_adopts_with_no_terminal_and_logs_under_its_own_key(self):
        place = self.repo_target()
        code, out, err = self.run_install(place, self.good(), adopt=True)
        self.assertEqual((0, WARNING), (code, err), out)
        self.assertEqual(b"hello\n", self.read(place, "README.md"))
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))
        attempt, outcome = self.log()
        self.assertEqual(["wb adopt", "none"], attempt.split("\t")[3:5])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_an_unapproved_module_is_refused_before_any_write(self):
        self.refused(self.repo_target(), self.package_of_target(), adopt=True, contains="approv")


class AdoptOtherLevels(Base, AdoptPreviewBase):
    def setUp(self):
        Base.setUp(self)

    def repo_target(self):
        return AdoptAtNone.repo_target(self)

    def test_the_key_of_install_does_not_open_adopt(self):
        self.attach_with(**{KEY_INSTALL: "none"})
        self.refused(self.repo_target(), self.good(), adopt=True)

    def test_the_default_level_refuses_without_a_terminal(self):
        self.attach_with()
        self.refused(self.repo_target(), self.good(), adopt=True, contains="preview adopt")


if __name__ == "__main__":
    unittest.main()
