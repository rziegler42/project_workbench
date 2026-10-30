"""``wb run`` of an owner-run argument that is the command of a declared checkpoint: the key it reads and logs, and the outcome
line that carries what the helper says it did. Increment C of the plan ``2026-10-29-accept-decision-at-ask``; the accepted
record is ``2026-10-29-accept-decision-offers-the-ask-level``.

The module is the synthetic `cmd`, its checkpoint the synthetic `other-step` that the process module of ``test_delegation``
declares. The helper prints whatever result line the test puts in the environment, so each way a line can be wrong is shown to
make the outcome `refused`. The installer knows no module."""

import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests.support_project import HELPER_PATH, tool
from tests.test_approve_levels import Ask
from workbench import approve, commands, levellog, ownerargs

STEP = "other-step"
WIPE = "wb run cmd wipe"
DIGEST = "a" * 32
SHA = "b" * 64
EMAIL = "12345+example@users.noreply.github.com"
APPROVER = "Example Approver <%s>" % EMAIL
COMMAND = {"cmd": {"helper": HELPER_PATH, "arguments": ["check", "show", "wipe", "keep"], "owner": ["wipe", "keep"],
                   "levels": {"wipe": ["ask", "none"]}, "preview": "show", "checkpoint_of": {"wipe": STEP}}}
HELPER = (b"#!/bin/sh\n"
          b"echo ran >> \"$WB_TEST_LOG\"\n"
          b"echo working\n"
          b"if [ -n \"$WB_TEST_RESULT\" ]; then printf '%s\\n' \"$WB_TEST_RESULT\"; fi\n"
          b"if [ -n \"$WB_TEST_NOTE\" ]; then echo noted >&2; fi\n"
          b"exit \"${WB_TEST_EXIT:-0}\"\n")


def result(**fields):
    line = {"format": 1, "record": "docs/decisions/x.md", "sha256": SHA, "approver": APPROVER, "via": "ask"}
    line.update(fields)
    return json.dumps(line)


class Mapped(Ask):
    MODULES = dict(Ask.MODULES, cmd=tool(COMMAND, helper=HELPER))
    LEVEL = "ask"
    TABLE = None  # the owner's table, when it is not the checkpoint at LEVEL

    def setUp(self):
        super().setUp()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.ran_log = os.path.join(os.path.realpath(holder.name), "ran.log")
        self.environ({"WB_TEST_LOG": self.ran_log, "WB_TEST_RESULT": result(via=self.LEVEL), "WB_TEST_EXIT": "0"})
        self.pin(name="cmd", path=self.installed("cmd"))
        self.render(**(self.TABLE or {STEP: self.LEVEL}))

    def environ(self, values):
        patch = unittest.mock.patch.dict(os.environ, values)
        patch.start()
        self.addCleanup(patch.stop)

    def render(self, **levels):
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": levels}).encode())
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def go(self, *args, terminal=False):
        err = io.StringIO()
        with tempfile.TemporaryFile() as out, unittest.mock.patch.object(approve, "is_terminal", lambda s: terminal):
            code = commands.run(self.guarded, list(args), err, cwd=self.real, stdout=out)
            out.seek(0)
            return code, out.read().decode(), err.getvalue()

    def ran(self):
        return os.path.exists(self.ran_log)

    def entries(self):
        return [line.split("\t") for line in self.log_lines()]

    def outcome(self):
        """The last attempt and outcome lines (a test that loops runs the helper more than once)."""
        attempt, outcome = self.entries()[-2:]
        return attempt, outcome

    def accept(self):
        return self.go("cmd", "wipe", "docs/decisions/x.md", "--digest", DIGEST)


class AtAsk(Mapped):
    def test_the_log_names_the_checkpoint_and_not_the_argument(self):
        code, out, err = self.accept()
        self.assertEqual(0, code, err)
        attempt, outcome = self.outcome()
        self.assertEqual(["A", STEP, "ask", "digest:" + DIGEST], [attempt[0]] + attempt[3:])
        self.assertNotIn(WIPE, "\n".join(self.log_lines()))

    def test_the_outcome_carries_the_email_the_route_and_the_hash(self):
        self.accept()
        _, outcome = self.outcome()
        self.assertEqual(["O", "done"], [outcome[0], outcome[3]])
        self.assertEqual("accepted by %s via ask sha256:%s" % (EMAIL, SHA), outcome[4])

    def test_the_name_is_not_in_the_log(self):
        self.accept()
        self.assertNotIn("Example Approver", "\n".join(self.log_lines()))

    def test_the_helpers_output_reaches_the_caller_and_its_error_text_reaches_standard_error(self):
        self.environ({"WB_TEST_NOTE": "1"})
        code, out, err = self.accept()
        self.assertEqual(0, code)
        self.assertEqual("working", out.splitlines()[0])
        self.assertEqual(result(via="ask"), out.splitlines()[-1])
        self.assertIn("noted", err)

    def test_a_run_without_a_digest_is_refused_and_runs_nothing(self):
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("digest", err)
        self.assertFalse(self.ran())
        self.assertEqual([], self.log_lines())

    def test_a_helper_that_exits_with_a_failure_is_a_refused_outcome_and_its_code_reaches_the_caller(self):
        self.environ({"WB_TEST_EXIT": "1"})
        code, out, err = self.accept()
        self.assertEqual(1, code)
        _, outcome = self.outcome()
        self.assertEqual(["O", "refused", "the helper exited with 1"], [outcome[0], outcome[3], outcome[4]])

    def test_output_over_the_limit_stops_the_helper_and_is_a_refused_outcome(self):
        with unittest.mock.patch.object(ownerargs, "OUTPUT_LIMIT", 10):
            code, out, err = self.accept()
        self.assertEqual(1, code, err)
        _, outcome = self.outcome()
        self.assertEqual("refused", outcome[3])
        self.assertIn("more than 10 bytes", outcome[4])

    def test_a_run_that_outlasts_its_time_is_a_refused_outcome(self):
        with unittest.mock.patch.object(ownerargs, "TIMEOUT", -1):
            code, out, err = self.accept()
        self.assertEqual(124, code, err)
        _, outcome = self.outcome()
        self.assertEqual("refused", outcome[3])

    def test_a_stale_rendering_reads_block_and_runs_nothing(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        code, out, err = self.accept()
        self.assertEqual(1, code)
        self.assertFalse(self.ran())

    def test_another_owner_argument_does_not_borrow_the_level(self):
        code, out, err = self.go("cmd", "keep", "--digest", DIGEST)
        self.assertEqual(1, code)
        self.assertFalse(self.ran())

    def test_a_terminal_run_reads_no_level_and_writes_no_entry(self):
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md", terminal=True)
        self.assertEqual(0, code, err)
        self.assertTrue(self.ran())
        self.assertEqual([], self.log_lines())


class ALineThatIsNotRight(Mapped):
    def refused_outcome(self, line, contains="result"):
        self.environ({"WB_TEST_RESULT": line})
        code, out, err = self.accept()
        self.assertEqual(3, code, err)
        self.assertIn(contains, err)
        self.assertTrue(self.ran())
        attempt, outcome = self.outcome()
        self.assertEqual(["O", "refused"], [outcome[0], outcome[3]])
        self.assertNotIn("accepted by", "\n".join(self.log_lines()))

    def test_no_line_at_all(self):
        self.refused_outcome("")

    def test_text_that_is_not_json(self):
        self.refused_outcome("accepted")

    def test_json_that_is_not_an_object(self):
        for text in ("[]", "3", "null", '"x"'):
            with self.subTest(text=text):
                self.refused_outcome(text)

    def test_a_field_missing(self):
        for name in ("format", "record", "sha256", "approver", "via"):
            with self.subTest(name=name):
                line = json.loads(result())
                del line[name]
                self.refused_outcome(json.dumps(line))

    def test_a_field_added(self):
        self.refused_outcome(result(extra=1))

    def test_a_format_that_is_not_one(self):
        for value in (2, 0, "1", True, None, 1.0):
            with self.subTest(value=value):
                self.refused_outcome(result(format=value))

    def test_a_hash_that_is_not_64_lowercase_hex(self):
        for value in ("b" * 63, "b" * 65, "B" * 64, "g" * 64, "", 3, None):
            with self.subTest(value=value):
                self.refused_outcome(result(sha256=value))

    def test_a_route_other_than_the_level_the_run_had(self):
        self.refused_outcome(result(via="none"))
        self.refused_outcome(result(via="delegated"))
        self.refused_outcome(result(via=3))

    def test_an_approver_that_is_not_the_grammar(self):
        for value in ("Example Approver", "<a@b.c>", "Name <not an email>", "x" * 400, "Name <%s>\n" % EMAIL, 3, None):
            with self.subTest(value=value):
                self.refused_outcome(result(approver=value))

    def test_a_record_that_is_not_a_relative_path(self):
        for value in ("/etc/passwd", "../x.md", "docs//x.md", "", "docs/decisions/x.md\n", 3, None):
            with self.subTest(value=value):
                self.refused_outcome(result(record=value))

    def test_a_line_over_512_bytes(self):
        line = result(record="docs/decisions/" + "x" * 600 + ".md")
        self.assertGreater(len(line.encode()), 512)
        self.refused_outcome(line)

    def test_a_line_of_exactly_512_bytes_is_accepted(self):
        pad = 512 - len(result(record="docs/decisions/.md").encode())
        line = result(record="docs/decisions/" + "x" * pad + ".md")
        self.assertEqual(512, len(line.encode()))
        self.environ({"WB_TEST_RESULT": line})
        code, out, err = self.accept()
        self.assertEqual(0, code, err)

    def test_only_the_last_line_is_the_result(self):
        self.environ({"WB_TEST_RESULT": result(via="ask") + "\nlater text"})
        code, out, err = self.accept()
        self.assertEqual(3, code, err)

    def test_a_duplicate_key_is_refused(self):
        line = result()[:-1] + ', "via": "ask"}'
        self.refused_outcome(line)


class AtNone(Mapped):
    LEVEL = "none"

    def test_the_route_is_none_and_there_is_no_digest(self):
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md")
        self.assertEqual(0, code, err)
        attempt, outcome = self.outcome()
        self.assertEqual(["A", STEP, "none", ""], [attempt[0]] + attempt[3:])
        self.assertEqual("accepted by %s via none sha256:%s" % (EMAIL, SHA), outcome[4])

    def test_a_line_that_says_ask_is_refused(self):
        self.environ({"WB_TEST_RESULT": result(via="ask")})
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md")
        self.assertEqual(3, code, err)
        _, outcome = self.outcome()
        self.assertEqual("refused", outcome[3])


class OnlyTheArgumentsOwnKeyIsSet(Mapped):
    TABLE = {WIPE: "ask"}

    def test_it_is_not_the_key_while_a_process_module_declares_the_checkpoint(self):
        code, out, err = self.accept()
        self.assertEqual(1, code)
        self.assertFalse(self.ran())
        self.assertEqual([], self.log_lines())


class AtBlock(Mapped):
    LEVEL = "block"

    def test_nothing_runs_without_a_terminal(self):
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("terminal", err)
        self.assertFalse(self.ran())
        self.assertEqual([], self.log_lines())


class WithoutADeclaringModule(Ask):
    """The mapping names a checkpoint that no process module declares, so the argument keeps its own key and the helper's line is
    still checked."""

    MODULES = dict(Ask.MODULES, cmd=tool({"cmd": dict(COMMAND["cmd"], checkpoint_of={"wipe": "no-such-step"})}, helper=HELPER))

    def setUp(self):
        super().setUp()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.ran_log = os.path.join(os.path.realpath(holder.name), "ran.log")
        patch = unittest.mock.patch.dict(os.environ, {"WB_TEST_LOG": self.ran_log, "WB_TEST_RESULT": result(via="ask"),
                                                      "WB_TEST_EXIT": "0"})
        patch.start()
        self.addCleanup(patch.stop)
        self.pin(name="cmd", path=self.installed("cmd"))
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": {
            WIPE: "ask"}}).encode())
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def go(self, *args):
        err = io.StringIO()
        with tempfile.TemporaryFile() as out, unittest.mock.patch.object(approve, "is_terminal", lambda s: False):
            code = commands.run(self.guarded, list(args), err, cwd=self.real, stdout=out)
            out.seek(0)
            return code, out.read().decode(), err.getvalue()

    def test_the_log_names_the_arguments_own_key(self):
        code, out, err = self.go("cmd", "wipe", "docs/decisions/x.md", "--digest", DIGEST)
        self.assertEqual(0, code, err)
        attempt, outcome = [line.split("\t") for line in self.log_lines()]
        self.assertEqual(["A", WIPE, "ask"], [attempt[0]] + attempt[3:5])
        self.assertEqual("accepted by %s via ask sha256:%s" % (EMAIL, SHA), outcome[4])


if __name__ == "__main__":
    unittest.main()
