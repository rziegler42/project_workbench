"""The shared way for an owner-run installer command to run at the level ``none`` (``workbench/levelrun.py``).

Plan ``2026-10-27-a-level-for-every-command``, increment D. No command but ``approve-plan`` uses it yet, so the commands
here are small functions the test passes in. The project, its process module and the synthetic harness are those of
``test_approve_levels``; the harness is attached so that a rendering record exists. Nothing here runs in a terminal unless a
test says so."""

import io
import os
import tempfile
import unittest
import unittest.mock

from tests.test_approve_levels import Ask
from workbench import levellog, levelrun, rendering, settings

TERMINAL_ONLY = "this command is owner-run: use a terminal"


class Streams:
    """Standard input and output of a command; whether they are terminals is the test's to say."""

    def __init__(self):
        self.stdin, self.out = io.StringIO(), io.StringIO()


class Routing(Ask):
    def route(self, key="approve-plan", terminal=False):
        streams = Streams()
        with unittest.mock.patch.object(levelrun.approve, "is_terminal", lambda stream: terminal):
            return levelrun.route(self.guarded, self.real, key, streams.stdin, streams.out, TERMINAL_ONLY)

    def refuses(self, **kwargs):
        with self.assertRaises(levelrun.Refusal) as caught:
            self.route(**kwargs)
        return str(caught.exception)

    def test_at_none_with_a_sound_record_a_run_without_a_terminal_may_go_on(self):
        self.attached(approve_plan="none")
        found = self.route()
        self.assertEqual((False, "none", self.project_id), found[:3])
        self.assertEqual(os.path.realpath(self.real), os.path.realpath(found.root))

    def test_at_block_the_caller_s_refusal_is_given(self):
        self.attached(approve_plan="block")
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_with_no_levels_the_default_is_block(self):
        self.attached()
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_a_terminal_goes_on_whatever_the_level_and_reads_nothing(self):
        self.attached(approve_plan="block")
        with unittest.mock.patch.object(rendering, "current_table", side_effect=AssertionError("read")):
            found = self.route(terminal=True)
        self.assertEqual((True, None, None, None), tuple(found))

    def test_a_missing_rendering_record_reads_block(self):
        self.attached(approve_plan="none")
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_a_harness_file_edited_after_attach_reads_block(self):
        self.attached(approve_plan="none")
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_a_table_edited_after_attach_reads_block(self):
        self.attached(approve_plan="none")
        self.table(approve_plan="ask")
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_a_level_the_key_does_not_offer_reads_block(self):
        self.attached(other_step="none")
        level, _, _ = levelrun.level_now(self.guarded, self.real, "other-step")
        self.assertEqual("block", level)
        self.assertEqual(TERMINAL_ONLY, self.refuses(key="other-step"))

    def test_a_key_that_is_not_in_the_table_reads_block(self):
        self.attached(approve_plan="none")
        self.assertEqual(TERMINAL_ONLY, self.refuses(key="wb nothing"))

    def test_an_unusable_project_is_a_refusal_with_its_own_text(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(levelrun.Refusal) as caught:
            levelrun.level_now(self.guarded, tmp, "approve-plan")
        self.assertNotEqual(TERMINAL_ONLY, str(caught.exception))
        self.assertNotEqual("", str(caught.exception))

    def test_a_damaged_settings_file_reads_block(self):
        self.attached(approve_plan="none")
        self.guarded.write("settings", b"{")
        self.assertEqual(TERMINAL_ONLY, self.refuses())

    def test_the_level_ask_is_not_a_run_without_a_terminal_here(self):
        self.attached(approve_plan="ask")
        self.assertEqual(TERMINAL_ONLY, self.refuses())


class Logging(Ask):
    def setUp(self):
        super().setUp()
        self.calls = []

    def change(self, result="changed"):
        def run():
            self.calls.append("change")
            return result
        return run

    def test_the_attempt_is_written_before_the_change_and_the_outcome_after(self):
        def run():
            self.assertEqual(1, len(self.log_lines()))
            self.calls.append("change")
            return "result"
        result, op = levelrun.logged(self.guarded, "approve-plan", "none", run, "digest:abc")
        self.assertEqual("result", result)
        self.assertEqual(["change"], self.calls)
        self.assertEqual(1, len(self.log_lines()))
        levelrun.done(self.guarded, op, "recorded")
        attempt, outcome = self.log_lines()
        self.assertEqual(["A", op], attempt.split("\t")[:2])
        self.assertEqual(["approve-plan", "none", "digest:abc"], attempt.split("\t")[3:])
        self.assertEqual(["O", op], outcome.split("\t")[:2])
        self.assertEqual(["done", "recorded"], outcome.split("\t")[3:])

    def test_a_change_that_would_change_nothing_writes_no_entry(self):
        result, op = levelrun.logged(self.guarded, "approve-plan", "none", self.change(False), needed=False)
        self.assertEqual((False, None), (result, op))
        levelrun.done(self.guarded, op)
        self.assertEqual([], self.log_lines())

    def test_an_unwritable_log_refuses_before_the_change(self):
        os.mkdir(os.path.join(self.store_root, levellog.LOG))
        with self.assertRaises(levellog.LogError):
            levelrun.logged(self.guarded, "approve-plan", "none", self.change())
        self.assertEqual([], self.calls)

    def test_a_full_log_refuses_before_the_change(self):
        with unittest.mock.patch.object(levellog, "MAX_BYTES", 10):
            with self.assertRaises(levellog.LogFull):
                levelrun.logged(self.guarded, "approve-plan", "none", self.change())
        self.assertEqual([], self.calls)

    def test_a_change_that_fails_leaves_a_refused_outcome_and_the_error_goes_on(self):
        def run():
            raise ValueError("cannot be written")
        with self.assertRaises(ValueError):
            levelrun.logged(self.guarded, "approve-plan", "none", run)
        attempt, outcome = self.log_lines()
        self.assertEqual(["refused", "cannot be written"], outcome.split("\t")[3:])
        self.assertEqual(attempt.split("\t")[1], outcome.split("\t")[1])

    def test_an_interrupt_leaves_a_refused_outcome_and_goes_on(self):
        def run():
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            levelrun.logged(self.guarded, "approve-plan", "none", run)
        self.assertEqual("refused", self.log_lines()[1].split("\t")[3])

    def test_an_outcome_that_cannot_be_written_after_the_change_is_reported(self):
        result, op = levelrun.logged(self.guarded, "approve-plan", "none", self.change())
        with unittest.mock.patch.object(levellog.kit.safefs, "append_line",
                                        side_effect=levellog.kit.safefs.SafeFsError("disk")):
            with self.assertRaises(levellog.OutcomeError):
                levelrun.done(self.guarded, op)
        self.assertEqual(["change"], self.calls)
        self.assertEqual(1, len(self.log_lines()))

    def test_block_is_never_logged(self):
        with self.assertRaises(ValueError):
            levelrun.logged(self.guarded, "approve-plan", "block", self.change())
        self.assertEqual([], self.calls)


class Boundaries(unittest.TestCase):
    def test_the_installer_part_uses_the_kit_s_decision(self):
        self.assertIs(levelrun.kit.may_run, __import__("workbench.wbkit.levels", fromlist=["may_run"]).may_run)

    def test_the_levels_the_key_reads_are_the_settings_levels(self):
        self.assertEqual(settings.LEVELS, levelrun.kit.LEVELS)


if __name__ == "__main__":
    unittest.main()
