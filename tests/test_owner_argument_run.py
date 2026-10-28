"""``wb run`` of an owner-run argument that offers a level: it runs without a terminal only at ``ask`` (with a digest) or
``none``, and writes an attempt and an outcome to the level log. Increment D of the plan dated 2026-10-27 that gives the
review workflow levels; the decision is ``2026-10-27-owner-run-arguments-take-a-level``.

The module is the synthetic `cmd`; its helper records every start, so a refusal can be shown to have run nothing. The project,
its process module and the synthetic harness are those of ``test_approve_levels``, attached so that a rendering record exists."""

import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests.support_project import HELPER_PATH, tool
from tests.test_approve_levels import Ask
from tests.test_run import SCRIPT
from workbench import approve, commands, launch, levellog

COMMAND = {"cmd": {"helper": HELPER_PATH, "arguments": ["check", "show", "wipe", "reset", "keep"],
                   "owner": ["wipe", "reset", "keep"], "levels": {"wipe": ["ask", "none"], "reset": ["none"]},
                   "preview": "show"}}
DIGEST = "a" * 32
WIPE = "wb run cmd wipe"


class Remote(Ask):
    MODULES = dict(Ask.MODULES, cmd=tool(COMMAND, helper=SCRIPT))

    def setUp(self):
        super().setUp()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.ran_log = os.path.join(os.path.realpath(holder.name), "ran.log")
        patch = unittest.mock.patch.dict(os.environ, {"WB_TEST_LOG": self.ran_log})
        patch.start()
        self.addCleanup(patch.stop)
        self.pin(name="cmd", path=self.installed("cmd"))

    def levels(self, **levels):
        """Set the owner's table (keys by their spelling, `_` for a space) and render it into the attached harness."""
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": {
            key.replace("_", " "): level for key, level in levels.items()}}).encode())
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def go(self, *args, terminal=False, cwd=None):
        err = io.StringIO()
        with tempfile.TemporaryFile() as out, unittest.mock.patch.object(approve, "is_terminal", lambda s: terminal):
            code = commands.run(self.guarded, list(args), err, cwd=cwd or self.real, stdout=out)
            out.seek(0)
            return code, out.read().decode(), err.getvalue()

    def ran(self):
        return os.path.exists(self.ran_log)

    def no_run(self, *args, contains=""):
        """The run is refused with one line, starts no helper and writes no log line."""
        before = self.log_lines()
        code, out, err = self.go(*args)
        self.assertEqual((1, ""), (code, out), err)
        self.assertEqual(1, len(err.splitlines()), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertFalse(self.ran())
        self.assertEqual(before, self.log_lines())
        return err


class Ask_(Remote):
    def setUp(self):
        super().setUp()
        self.levels(wb_run_cmd_wipe="ask")

    def test_a_good_digest_runs_the_helper_with_the_arguments_unchanged(self):
        code, out, err = self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:4", "a:wipe", "a:doc", "a:--digest", "a:" + DIGEST], out.splitlines())

    def test_the_run_leaves_an_attempt_with_the_digest_and_a_done_outcome(self):
        self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["A", WIPE, "ask", "digest:" + DIGEST], [attempt[0]] + attempt[3:])
        self.assertEqual(["O", attempt[1], "done"], [outcome[0], outcome[1], outcome[3]])

    def test_a_run_without_a_digest_is_refused_and_names_the_preview(self):
        err = self.no_run("cmd", "wipe", "doc", contains="digest")
        self.assertIn("show", err)

    def test_a_digest_that_is_not_32_lowercase_hex_is_refused(self):
        for bad in ("a" * 31, "a" * 33, "A" * 32, "g" * 32, "", "a" * 32 + "\n"):
            with self.subTest(bad=bad):
                self.no_run("cmd", "wipe", "doc", "--digest", bad, contains="digest")

    def test_the_digest_must_be_the_last_two_arguments(self):
        self.no_run("cmd", "wipe", "--digest", DIGEST, "doc", contains="digest")
        self.no_run("cmd", "wipe", "--digest", contains="digest")
        self.no_run("cmd", "wipe", "--digest", DIGEST, "--digest", DIGEST + "0", contains="digest")

    def test_a_stale_rendering_reads_block_and_runs_nothing(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.no_run("cmd", "wipe", "doc", "--digest", DIGEST, contains="terminal")

    def test_a_table_changed_after_the_rendering_reads_block_and_runs_nothing(self):
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": {
            WIPE: "none"}}).encode())
        self.no_run("cmd", "wipe", "doc", "--digest", DIGEST, contains="terminal")

    def test_a_missing_record_reads_block_and_runs_nothing(self):
        from workbench import rendering
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.no_run("cmd", "wipe", "doc", "--digest", DIGEST, contains="terminal")

    def test_a_pinned_helper_that_changed_is_refused_before_any_attempt_is_written(self):
        with open(os.path.join(self.real, *self.installed("cmd").split("/")), "ab") as handle:
            handle.write(b"# changed\n")
        self.no_run("cmd", "wipe", "doc", "--digest", DIGEST, contains="changed since it was pinned")

    def test_an_argument_at_ask_does_not_let_another_owner_argument_through(self):
        self.no_run("cmd", "keep", "--digest", DIGEST, contains="terminal")
        self.no_run("cmd", "reset", "--digest", DIGEST, contains="terminal")

    def test_a_helper_that_fails_is_a_refused_outcome_and_its_code_reaches_the_caller(self):
        self.put(self.installed("cmd"), b"#!/bin/sh\necho ran >> \"$WB_TEST_LOG\"\nexit 3\n")
        self.pin(name="cmd", path=self.installed("cmd"))
        code, out, err = self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        self.assertEqual(3, code)
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["O", "refused"], [outcome[0], outcome[3]])
        self.assertEqual("the helper exited with 3", outcome[4])

    def test_a_helper_that_cannot_start_after_the_attempt_is_a_refused_outcome(self):
        with unittest.mock.patch.object(launch.subprocess, "run", side_effect=OSError("no exec")):
            code, out, err = self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        self.assertEqual(1, code)
        self.assertTrue(err.startswith("refused: "), err)
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["A", "O", "refused"], [attempt[0], outcome[0], outcome[3]])

    def test_it_runs_from_a_subdirectory_of_the_project(self):
        deep = os.path.join(self.real, "docs", "a")
        os.makedirs(deep)
        code, out, err = self.go("cmd", "wipe", "doc", "--digest", DIGEST, cwd=deep)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(2, len(self.log_lines()))

    def test_a_log_that_cannot_take_the_attempt_starts_no_helper(self):
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the level log is full")):
            self.no_run("cmd", "wipe", "doc", "--digest", DIGEST, contains="level log is full")

    def test_an_interrupt_after_the_attempt_leaves_a_refused_outcome_and_goes_on(self):
        with unittest.mock.patch.object(launch.subprocess, "run", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["A", "O", "refused"], [attempt[0], outcome[0], outcome[3]])
        self.assertFalse(self.ran())

    def test_an_outcome_that_cannot_be_written_after_the_run_is_exit_3(self):
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("the log is full")):
            code, out, err = self.go("cmd", "wipe", "doc", "--digest", DIGEST)
        self.assertEqual(3, code)
        self.assertIn("outcome was not logged", err)
        self.assertTrue(self.ran())

    def test_the_preview_argument_runs_without_a_terminal_and_is_not_logged(self):
        code, out, err = self.go("cmd", "show", "wipe", "doc")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual([], self.log_lines())

    def test_a_run_at_a_terminal_works_as_before_and_is_not_logged(self):
        code, out, err = self.go("cmd", "wipe", "doc", terminal=True)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:2", "a:wipe", "a:doc"], out.splitlines())
        self.assertEqual([], self.log_lines())

    def test_wb_launch_still_refuses_the_argument_without_a_terminal(self):
        name = "cmd"
        with unittest.mock.patch.object(approve, "is_terminal", lambda s: False):
            reason = commands.launch_refusal(self.guarded, self.project_id, name, self.real,
                                             ["wipe", "doc", "--digest", DIGEST], io.StringIO(), io.StringIO())
        self.assertIn("terminal", reason)


class None_(Remote):
    def setUp(self):
        super().setUp()
        self.levels(wb_run_cmd_wipe="none", wb_run_cmd_reset="none", wb_run_cmd_keep="none")

    def test_it_runs_without_a_digest_and_is_logged(self):
        code, out, err = self.go("cmd", "wipe", "doc")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:2", "a:wipe", "a:doc"], out.splitlines())
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["A", WIPE, "none", ""], [attempt[0]] + attempt[3:])
        self.assertEqual("done", outcome[3])

    def test_the_other_argument_that_offers_none_runs_too(self):
        self.assertEqual(0, self.go("cmd", "reset", "doc")[0])
        self.assertEqual("wb run cmd reset", self.log_lines()[0].split("\t")[3])

    def test_an_owner_argument_that_declares_no_level_stays_owner_run(self):
        self.no_run("cmd", "keep", contains="terminal")


class NotOffered(Remote):
    def test_a_level_the_declaration_does_not_offer_reads_block(self):
        self.levels(wb_run_cmd_reset="ask")
        self.no_run("cmd", "reset", "--digest", DIGEST, contains="terminal")


class Block(Remote):
    def test_with_no_level_set_the_argument_is_refused_as_before(self):
        self.levels()
        self.no_run("cmd", "wipe", "doc", contains="terminal")

    def test_a_declared_argument_with_no_table_at_all_is_refused_as_before(self):
        self.no_run("cmd", "wipe", "doc", contains="terminal")


if __name__ == "__main__":
    unittest.main()
