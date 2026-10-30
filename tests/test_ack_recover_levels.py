"""``wb acknowledge``, ``wb recover``, ``wb release-approvals`` and ``wb attach`` at the level ``none``.

Plan ``2026-10-27-a-level-for-every-command``, increment J (``docs/specs/command-permissions.md``, "One way to run at ``none``").
``acknowledge`` is governed by the checkpoint ``acknowledge-first-tier`` (the owner's choice: every path it can list is
first-tier material); ``recover`` by ``wb recover``; ``attach`` and ``release-approvals`` have no terminal test, so at ``none``
an unattended run is logged and at any other level they go on as they always did. The project, its harness and its rendering
record are those of ``test_approve_levels``; its process module declares the two acknowledge checkpoints here."""

import hashlib
import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests.test_approve_levels import Ask
from tests.test_delegation import process_module
from workbench import acknowledgement, approve, attach, cli, firstparty, levellog, levelrun, levels, projectfs, rendering
from workbench import unfinished

FIRST, SECOND = "acknowledge-first-tier", "acknowledge-second-tier"
FILE = "docs/README.md"
KEY_LOG = "wb recover"


class NoInput(io.StringIO):
    """A standard input that fails if it is read: nothing is asked at ``none``."""

    def readline(self, limit=-1):
        raise AssertionError("standard input was read")

    read = readlines = readline


class Base(Ask):
    MODULES = dict(Ask.MODULES, tool=process_module(checkpoints=["approve-plan", "other-step", FIRST, SECOND]))
    KEY = FIRST

    def table(self, **table):
        document = {"version": 2, "checkpoints": {}, "floor": [], "levels": table}
        self.guarded.write("settings", json.dumps(document).encode())

    def attach_at(self, level="none", key=None):
        self.table(**({key or self.KEY: level} if level else {}))
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def log(self):
        if self.guarded.kind(levellog.LOG) != "file":
            return []
        return self.guarded.read(levellog.LOG).decode("ascii").splitlines()

    def go(self, argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(cwd or self.real)
        try:
            code = cli.main(list(argv), out, err, store_root=self.store_root, distribution=self.dist, stdin=NoInput())
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def rendered(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json")) as handle:
            return handle.read()

    def baselines(self):
        return acknowledgement.read_baselines(self.guarded, self.project_id)

    def snapshot(self):
        # The launcher wrapper under bin/ is rewritten by every run, at a terminal or not, as it always was.
        store = {rel: item for rel, item in self.tree(self.store_root).items() if rel != "bin" and not rel.startswith("bin/")}
        return self.tree(self.real), store, self.log()

    def refused(self, argv, contains="owner-run", **kwargs):
        before = self.snapshot()
        code, out, err = self.go(argv, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, self.snapshot())
        return err


class AcknowledgeAtNone(Base):
    def setUp(self):
        super().setUp()
        self.attach_at("none")
        self.put(FILE, "# Docs\nedited by someone else\n")

    def test_it_acknowledges_with_no_terminal_and_asks_nothing(self):
        self.assertNotEqual(hashlib.sha256(self.read(FILE)).hexdigest(), self.baselines()[FILE])
        code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing is asked", out)
        self.assertIn("acknowledged", out)
        self.assertEqual(hashlib.sha256(self.read(FILE)).hexdigest(), self.baselines()[FILE])

    def test_the_project_is_not_touched(self):
        before = self.tree(self.real)
        self.assertEqual(0, self.go(["acknowledge", self.real])[0])
        self.assertEqual(before, self.tree(self.real))

    def test_the_log_has_the_attempt_before_the_write_and_the_outcome_after(self):
        seen = []
        write = self.guarded.__class__.write

        def watching(store, rel, data, *a, **k):
            if rel.endswith("/baselines"):
                seen.append(self.log())
            return write(store, rel, data, *a, **k)

        with unittest.mock.patch.object(self.guarded.__class__, "write", watching):
            code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual([FIRST, "none"], fields[3:5])
        self.assertRegex(fields[5], r"\Adigest:[0-9a-f]{64}\Z")
        self.assertEqual(["O", fields[1]], outcome.split("\t")[:2])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_nothing_to_acknowledge_writes_no_entry(self):
        self.assertEqual(0, self.go(["acknowledge", self.real])[0])
        log = self.log()
        code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing to acknowledge", out)
        self.assertEqual(log, self.log())

    def test_a_plan_for_another_project_than_the_level_was_read_for_is_refused(self):
        before = self.snapshot()
        elsewhere = levelrun.Route(False, "none", "0" * 64, self.real)
        with unittest.mock.patch.object(levelrun, "route", lambda *a, **k: elsewhere):
            code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertIn("not the project", err)
        self.assertEqual(before, self.snapshot())

    def test_a_table_edited_after_attach_reads_block(self):
        self.table(**{FIRST: "none", "wb recover": "none"})
        self.refused(["acknowledge", self.real])

    def test_a_missing_rendering_record_reads_block(self):
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.refused(["acknowledge", self.real])

    def test_a_harness_file_edited_after_attach_reads_block(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.refused(["acknowledge", self.real])

    def test_a_directory_that_is_no_project_cannot_run_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(["acknowledge", self.real], cwd=tmp)

    def test_an_attempt_that_cannot_be_written_changes_nothing(self):
        before = self.snapshot()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertIn("nothing was written", err)
        self.assertEqual(before, self.snapshot())

    def test_an_outcome_that_cannot_be_written_after_the_write_exits_3(self):
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("no space")):
            code, out, err = self.go(["acknowledge", self.real])
        self.assertEqual(3, code, (out, err))
        self.assertIn("outcome was not logged", err)

    def test_the_rendered_settings_open_wb_acknowledge_and_keep_the_interpreter_spelling_denied(self):
        text = self.rendered()
        self.assertNotIn("Bash(wb acknowledge", text)
        self.assertIn("Bash(python3 -m workbench acknowledge", text)


class AcknowledgeNotAtNone(Base):
    def test_it_refuses_without_a_terminal_at_block(self):
        self.attach_at("block")
        self.put(FILE, "# Docs\nedited\n")
        self.refused(["acknowledge", self.real])

    def test_the_second_tier_key_alone_does_not_let_it_run(self):
        self.attach_at("none", key=SECOND)
        self.put(FILE, "# Docs\nedited\n")
        self.refused(["acknowledge", self.real])

    def test_the_rendered_settings_keep_wb_acknowledge_denied_at_block(self):
        self.attach_at("block")
        text = self.rendered()
        self.assertIn("Bash(wb acknowledge", text)


class AcknowledgeWhenTheCheckpointIsNotDeclared(Ask):
    """A process module that does not declare ``acknowledge-first-tier`` leaves no key for the command: it reads block."""

    def test_a_table_entry_for_an_undeclared_checkpoint_does_not_let_it_run(self):
        document = {"version": 2, "checkpoints": {}, "floor": [], "levels": {FIRST: "none"}}
        self.guarded.write("settings", json.dumps(document).encode())
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.put(FILE, "# Docs\nedited\n")
        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(self.real)
        try:
            code = cli.main(["acknowledge", self.real], out, err, store_root=self.store_root, distribution=self.dist,
                            stdin=NoInput())
        finally:
            os.chdir(previous)
        self.assertEqual(1, code, (out.getvalue(), err.getvalue()))
        self.assertIn("owner-run", err.getvalue())
        with open(os.path.join(self.real, ".fixture", "settings.local.json")) as handle:
            self.assertIn("Bash(wb acknowledge", handle.read())  # the static deny of every owner-run command stays
        self.assertNotIn(FIRST, [entry.split("\t")[3] for entry in
                                 (self.guarded.read(levellog.LOG).decode().splitlines()
                                  if self.guarded.kind(levellog.LOG) == "file" else [])])


class RecoverAtNone(Base):
    KEY = "wb recover"

    def setUp(self):
        super().setUp()
        self.attach_at("none")
        os.mkdir(os.path.join(self.real, "scratch"))
        marker = unfinished.build("upgrade", self.project_id, "1", [("zz/new.txt", "create", None, "1" * 64)],
                                  dirs=["scratch"], store=[("projects/%s/zz" % self.project_id, None, "1" * 64)])
        full = os.path.join(self.real, *projectfs.MARKER.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(marker)

    def marker_present(self):
        return os.path.exists(os.path.join(self.real, *projectfs.MARKER.split("/")))

    def test_it_clears_the_marker_with_no_terminal_and_asks_nothing(self):
        code, out, err = self.go(["recover", self.real])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing is asked", out)
        self.assertFalse(self.marker_present())
        self.assertFalse(os.path.exists(os.path.join(self.real, "scratch")))

    def test_the_log_has_the_attempt_before_the_removal_and_the_outcome_after(self):
        seen = []
        original = projectfs.Writer.remove_marker

        def watching(writer):
            seen.append(self.log())
            return original(writer)

        with unittest.mock.patch.object(projectfs.Writer, "remove_marker", watching):
            code, out, err = self.go(["recover", self.real])
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual(["wb recover", "none"], fields[3:5])
        self.assertRegex(fields[5], r"\Adigest:[0-9a-f]{64}\Z")
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_no_marker_writes_no_entry(self):
        self.assertEqual(0, self.go(["recover", self.real])[0])
        log = self.log()
        code, out, err = self.go(["recover", self.real])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing to recover", out)
        self.assertEqual(log, self.log())

    def test_a_marker_in_a_state_that_is_not_safe_is_refused_and_nothing_changes(self):
        with open(os.path.join(self.real, "zz-new.txt"), "w") as handle:
            handle.write("x")
        os.makedirs(os.path.join(self.real, "zz"), exist_ok=True)
        with open(os.path.join(self.real, "zz", "new.txt"), "w") as handle:
            handle.write("written")
        before = self.snapshot()
        code, out, err = self.go(["recover", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertEqual(before, self.snapshot())

    def test_a_marker_in_a_directory_that_is_not_the_project_is_cleared_as_after_a_failed_install(self):
        other = os.path.join(self.root, "other")
        os.makedirs(os.path.join(other, ".workbench", "local"))
        marker = unfinished.build("install", None, "1", [("zz/new.txt", "create", None, "1" * 64)], dirs=[],
                                  store=[("projects/%s/zz" % ("0" * 64), None, "1" * 64)])
        with open(os.path.join(other, *projectfs.MARKER.split("/")), "wb") as handle:
            handle.write(marker)
        code, out, err = self.go(["recover", other])
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(KEY_LOG, self.log()[0].split("\t")[3])

    def test_a_marker_that_names_another_project_is_refused_and_nothing_is_removed(self):
        marker = unfinished.build("upgrade", "0" * 64, "1", [("zz/new.txt", "create", None, "1" * 64)], dirs=["scratch"],
                                  store=[("projects/%s/zz" % ("0" * 64), None, "1" * 64)])
        with open(os.path.join(self.real, *projectfs.MARKER.split("/")), "wb") as handle:
            handle.write(marker)
        before = self.snapshot()
        code, out, err = self.go(["recover", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertIn("another project", err)
        self.assertEqual(before, self.snapshot())

    def test_a_table_edited_after_attach_reads_block(self):
        self.table(**{"wb recover": "none", FIRST: "none"})
        self.refused(["recover", self.real])

    def test_a_directory_that_is_no_project_cannot_run_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(["recover", self.real], cwd=tmp)

    def test_an_attempt_that_cannot_be_written_changes_nothing(self):
        before = self.snapshot()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.go(["recover", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertEqual(before, self.snapshot())

    def test_an_outcome_that_cannot_be_written_after_the_removal_exits_3(self):
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("no space")):
            code, out, err = self.go(["recover", self.real])
        self.assertEqual(3, code, (out, err))
        self.assertFalse(self.marker_present())


class RecoverNotAtNone(Base):
    KEY = "wb recover"

    def test_it_refuses_without_a_terminal_at_block(self):
        self.attach_at("block")
        self.refused(["recover", self.real])


class NoTerminalTest(Base):
    """``attach`` and ``release-approvals`` have no terminal test: at ``none`` an unattended run is logged."""

    def calls(self, key, argv, target, result=0):
        with unittest.mock.patch.object(target[0], target[1], return_value=result) as mocked:
            code, out, err = self.go(argv)
        return code, out, err, mocked


class AttachAtNone(NoTerminalTest):
    KEY = "wb attach"
    ARGV = ["attach", "x", "--harness", "p/h"]

    def run_attach(self):
        return self.calls(self.KEY, self.ARGV, (attach, "run"))

    def test_an_unattended_run_at_none_is_logged_and_goes_on(self):
        self.attach_at("none")
        code, out, err, mocked = self.run_attach()
        self.assertEqual(0, code, (out, err))
        mocked.assert_called_once()
        attempt, outcome = self.log()
        self.assertEqual(["wb attach", "none", ""], attempt.split("\t")[3:])  # empty evidence: the whole call is wrapped
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_an_interrupt_before_writing_is_not_logged_as_a_write(self):
        self.attach_at("none")
        code, out, err, mocked = self.calls(self.KEY, self.ARGV, (attach, "run"), result=130)
        self.assertEqual(130, code)
        self.assertEqual(["refused", "interrupted before writing"], self.log()[1].split("\t")[3:])

    def test_a_refused_run_is_logged_as_refused_with_its_exit_code(self):
        self.attach_at("none")
        code, out, err, mocked = self.calls(self.KEY, self.ARGV, (attach, "run"), result=1)
        self.assertEqual(1, code)
        self.assertEqual("refused", self.log()[1].split("\t")[3])

    def test_an_attempt_that_cannot_be_written_stops_before_attaching(self):
        self.attach_at("none")
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err, mocked = self.run_attach()
        self.assertEqual(1, code, (out, err))
        mocked.assert_not_called()

    def test_at_a_terminal_it_is_not_logged(self):
        self.attach_at("none")
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True):
            code, out, err, mocked = self.run_attach()
        self.assertEqual(0, code)
        mocked.assert_called_once()
        self.assertEqual([], self.log())

    def test_at_block_it_goes_on_unlogged_as_before(self):
        self.attach_at("block")
        code, out, err, mocked = self.run_attach()
        self.assertEqual(0, code, (out, err))
        mocked.assert_called_once()
        self.assertEqual([], self.log())

    def test_in_a_directory_that_is_no_project_it_goes_on_unlogged(self):
        self.attach_at("none")
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(attach, "run", return_value=0) as mocked:
                code, out, err = self.go(self.ARGV, cwd=tmp)
        self.assertEqual(0, code)
        mocked.assert_called_once()
        self.assertEqual([], self.log())

    def test_the_rendered_settings_open_wb_attach(self):
        self.attach_at("none")
        text = self.rendered()
        self.assertNotIn("Bash(wb attach", text)
        self.assertIn("Bash(python3 -m workbench attach", text)


class ReleaseApprovalsAtNone(NoTerminalTest):
    KEY = "wb release-approvals"

    def run_release(self):
        released = firstparty.Release(2, 1, [])
        return self.calls(self.KEY, ["release-approvals"], (firstparty, "release_approvals"), result=released)

    def test_an_unattended_run_at_none_is_logged_and_goes_on(self):
        self.attach_at("none")
        code, out, err, mocked = self.run_release()
        self.assertEqual(0, code, (out, err))
        mocked.assert_called_once()
        attempt, outcome = self.log()
        self.assertEqual(["wb release-approvals", "none"], attempt.split("\t")[3:5])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_at_a_terminal_it_is_not_logged(self):
        self.attach_at("none")
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True):
            self.assertEqual(0, self.run_release()[0])
        self.assertEqual([], self.log())

    def test_at_block_it_goes_on_unlogged_as_before(self):
        self.attach_at("block")
        self.assertEqual(0, self.run_release()[0])
        self.assertEqual([], self.log())

    def test_outside_a_project_it_goes_on_unlogged(self):
        self.attach_at("none")
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(firstparty, "release_approvals", return_value=firstparty.Release(0, 0, [])):
                code, out, err = self.go(["release-approvals"], cwd=tmp)
        self.assertEqual(0, code, (out, err))
        self.assertEqual([], self.log())


class Offers(unittest.TestCase):
    def test_the_keys_offer_block_and_none(self):
        registry = levels.registry(checkpoints=(FIRST, SECOND))
        for key in (FIRST, SECOND, "wb recover", "wb attach"):
            with self.subTest(key=key):
                self.assertEqual(("block", "none"), registry[key].offers)
                self.assertEqual("block", registry[key].default)

    def test_the_release_offers_block_ask_and_none_and_defaults_to_block(self):
        key = levels.registry(checkpoints=(FIRST, SECOND))["wb release-approvals"]
        self.assertEqual(("block", "ask", "none"), key.offers)
        self.assertEqual("block", key.default)

    def test_the_first_tier_key_names_the_acknowledge_command(self):
        self.assertEqual(rendering.key_patterns(FIRST), rendering.rules.owner_run_command_patterns("acknowledge"))
        self.assertEqual([], rendering.key_patterns(SECOND))


if __name__ == "__main__":
    unittest.main()
