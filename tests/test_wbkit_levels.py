"""The kit's level functions: may a run go ahead, and the level log's lines (``workbench/wbkit/levels.py``).

Plan ``2026-10-27-a-level-for-every-command``, increment D (``docs/specs/command-permissions.md``). The kit names no
module and no installer file, so a helper can use these later; the installer's ``levellog`` calls them."""

import os
import re
import tempfile
import unittest
import unittest.mock

from workbench import levellog, levels as installer_levels, wbkit
from workbench.wbkit import levels, safefs


class MayRun(unittest.TestCase):
    def test_a_terminal_lets_any_level_run(self):
        for level in (levels.BLOCK, levels.ASK, levels.DELEGATED, levels.NONE, None, "open", 3):
            with self.subTest(level=level):
                self.assertTrue(levels.may_run(level, True))

    def test_without_a_terminal_only_none_runs(self):
        self.assertTrue(levels.may_run(levels.NONE, False))
        for level in (levels.BLOCK, levels.ASK, levels.DELEGATED):
            with self.subTest(level=level):
                self.assertFalse(levels.may_run(level, False))

    def test_an_unknown_missing_or_unreadable_level_falls_back_to_the_terminal_test(self):
        for level in (None, "", "NONE", "open", 0, ["none"], {"none": 1}, b"none"):
            with self.subTest(level=level):
                self.assertFalse(levels.may_run(level, False))

    def test_only_true_is_a_terminal(self):
        for terminal in (1, "yes", object(), [0], None, 0):
            with self.subTest(terminal=terminal):
                self.assertFalse(levels.may_run(levels.BLOCK, terminal))

    def test_the_answer_is_a_bool(self):
        self.assertIs(levels.may_run(levels.NONE, False), True)
        self.assertIs(levels.may_run(levels.BLOCK, False), False)
        self.assertIs(levels.may_run(None, 1), False)

    def test_is_terminal_reads_a_stream_and_never_raises(self):
        class Plain:
            pass

        class Bad:
            def fileno(self):
                raise ValueError("closed")

        self.assertFalse(levels.is_terminal(Plain()))
        self.assertFalse(levels.is_terminal(Bad()))
        with tempfile.TemporaryFile() as handle:
            self.assertFalse(levels.is_terminal(handle))


class Names(unittest.TestCase):
    def test_adding_the_module_did_not_raise_the_kit_api(self):
        # The addition changes no existing kit function, so a helper released against API 1 still loads.
        self.assertEqual(1, wbkit.API)

    def test_the_levels_are_those_of_the_installer(self):
        self.assertEqual(installer_levels.LEVELS, levels.LEVELS)
        self.assertEqual((installer_levels.BLOCK, installer_levels.ASK, installer_levels.DELEGATED,
                          installer_levels.NONE), (levels.BLOCK, levels.ASK, levels.DELEGATED, levels.NONE))

    def test_the_log_limits_are_those_of_the_installer(self):
        self.assertEqual((levellog.LOG, levellog.MAX_BYTES, levellog.MAX_LINE, levellog.MAX_REASON, levellog.MAX_KEY),
                         (levels.LOG, levels.MAX_BYTES, levels.MAX_LINE, levels.MAX_REASON, levels.MAX_KEY))

    def test_the_installers_log_errors_are_the_kits(self):
        self.assertIs(levellog.LogError, levels.LogError)
        self.assertIs(levellog.LogFull, levels.LogFull)
        self.assertIs(levellog.OutcomeError, levels.OutcomeError)


class Lines(unittest.TestCase):
    OP = "ab" * 8
    TIME = "2026-10-27T12:00:00Z"

    def test_an_attempt_line_has_the_logs_format(self):
        line = levels.attempt_line(self.OP, self.TIME, "install", "none", "digest:abc")
        self.assertEqual(b"A\t%s\t%s\tinstall\tnone\tdigest:abc\n" % (self.OP.encode(), self.TIME.encode()), line)

    def test_an_outcome_line_has_the_logs_format_and_a_clean_cut_reason(self):
        line = levels.outcome_line(self.OP, self.TIME, "done", "ok\tnot\nthis" + "x" * 500)
        text = line.decode("ascii")
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(1, text.count("\n"))
        fields = text[:-1].split("\t")
        self.assertEqual(["O", self.OP, self.TIME, "done"], fields[:4])
        self.assertEqual(5, len(fields))
        self.assertLessEqual(len(fields[4]), levels.MAX_REASON)
        self.assertLessEqual(len(line), levels.MAX_LINE)

    def test_a_bad_attempt_is_a_value_error(self):
        for args in (("Bad Key", "none", ""), ("x" * 97, "none", ""), ("install", "block", ""),
                     ("install", "open", ""), ("install", "none", "a b"), ("install", "none", "x" * 129),
                     ("install", "none", "tab\t"), (3, "none", ""), ("install", "none", 3)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                levels.attempt_line(self.OP, self.TIME, *args)

    def test_a_bad_identifier_or_time_is_a_value_error(self):
        for op, time in (("a\tb" + "c" * 13, self.TIME), (self.OP, "2026-10-27 12:00:00"), (self.OP, "x\n"),
                         (self.OP, None), (None, self.TIME)):
            with self.subTest(op=op, time=time):
                with self.assertRaises(ValueError):
                    levels.attempt_line(op, time, "install", "none")
                with self.assertRaises(ValueError):
                    levels.outcome_line(op, time, "done")

    def test_a_bad_outcome_is_a_value_error(self):
        for args in (("zz", "done"), (self.OP, "ok"), (self.OP.upper(), "done"), (3, "done")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                levels.outcome_line(args[0], self.TIME, args[1], "")

    def test_the_lines_are_what_the_installers_reader_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            op = levels.begin(root, "install", "none", "digest:abc")
            levels.finish(root, op, "done", "recorded")
            with open(os.path.join(root, levels.LOG), "rb") as handle:
                data = handle.read()
        attempt, outcome = data.decode("ascii").splitlines()
        self.assertTrue(re.match(r"A\t[0-9a-f]{16}\t\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\tinstall\tnone\tdigest:abc\Z",
                                 attempt))
        self.assertTrue(re.match(r"O\t%s\t\S+\tdone\trecorded\Z" % op, outcome))


class Appending(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.realpath(self.tmp.name)
        self.path = os.path.join(self.root, levels.LOG)

    def raw(self):
        with open(self.path, "rb") as handle:
            return handle.read()

    def test_it_appends_one_line_each_and_never_reads(self):
        first = levels.begin(self.root, "install", "none")
        second = levels.begin(self.root, "upgrade", "none")
        self.assertNotEqual(first, second)
        self.assertEqual(2, len(self.raw().splitlines()))
        self.assertEqual(0o600, os.stat(self.path).st_mode & 0o777)
        with unittest.mock.patch("builtins.open", side_effect=AssertionError("read")):
            levels.finish(self.root, first, "done", "ok")
        self.assertEqual(3, len(self.raw().splitlines()))

    def test_a_value_error_writes_nothing(self):
        with self.assertRaises(ValueError):
            levels.begin(self.root, "install", "block")
        with self.assertRaises(ValueError):
            levels.finish(self.root, "zz", "done")
        self.assertFalse(os.path.exists(self.path))

    def test_it_refuses_a_link_a_directory_and_a_second_hard_link(self):
        target = os.path.join(self.root, "elsewhere")
        with open(target, "wb"):
            pass
        os.symlink(target, self.path)
        with self.assertRaises(levels.LogError):
            levels.begin(self.root, "install", "none")
        os.unlink(self.path)
        os.mkdir(self.path)
        with self.assertRaises(levels.LogError):
            levels.begin(self.root, "install", "none")
        os.rmdir(self.path)
        os.link(target, self.path)
        with self.assertRaises(levels.LogError):
            levels.begin(self.root, "install", "none")
        with open(target, "rb") as handle:
            self.assertEqual(b"", handle.read())

    def test_a_full_log_refuses_with_a_message_that_names_it(self):
        with unittest.mock.patch.object(levels, "MAX_BYTES", 120):
            with self.assertRaises(levels.LogFull) as caught:
                for _ in range(10):
                    levels.begin(self.root, "install", "none")
        self.assertIn(levels.LOG, str(caught.exception))
        self.assertLessEqual(len(self.raw()), 120)

    def test_an_outcome_that_cannot_be_written_is_an_outcome_error(self):
        op = levels.begin(self.root, "install", "none")
        with unittest.mock.patch.object(safefs, "append_line", side_effect=safefs.SafeFsError("disk")):
            with self.assertRaises(levels.OutcomeError):
                levels.finish(self.root, op, "done")
            with self.assertRaises(levels.LogError):
                levels.begin(self.root, "install", "none")
        self.assertEqual(1, len(self.raw().splitlines()))

    def test_finish_refused_never_raises(self):
        op = levels.begin(self.root, "install", "none")
        with unittest.mock.patch.object(safefs, "append_line", side_effect=safefs.SafeFsError("disk")):
            levels.finish_refused(self.root, op, "why")
        levels.finish_refused(self.root, op, "why")
        self.assertIn(b"refused\twhy", self.raw())


if __name__ == "__main__":
    unittest.main()
