"""The level log: two lines per run above ``block``, appended and never rewritten, in the guarded store.

Plan ``2026-10-26-command-permission-levels``, increment D (``docs/specs/command-permissions.md``, "The log")."""

import os
import tempfile
import threading
import unittest
import unittest.mock

import support
from workbench import levellog, store
from workbench.wbkit import safefs


class LogBase(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.root = os.path.join(self.base, "store")
        self.store = store.Store(self.root)
        self.store.ensure()
        self.path = os.path.join(self.root, levellog.LOG)

    def lines(self):
        with open(self.path, "rb") as handle:
            return handle.read().splitlines()

    def raw(self):
        with open(self.path, "rb") as handle:
            return handle.read()

    def begin(self, **kwargs):
        arguments = dict(key="approve-plan", level="delegated", evidence="converged-2-of-3")
        arguments.update(kwargs)
        return levellog.begin(self.store, **arguments)


class WritingTest(LogBase):
    def test_the_log_is_a_file_directly_in_the_store(self):
        self.assertEqual("level-log", levellog.LOG)
        self.begin()
        self.assertEqual(self.path, os.path.join(self.root, "level-log"))

    def test_an_attempt_and_an_outcome_share_an_identifier(self):
        op = self.begin()
        levellog.finish(self.store, op, "done", "recorded")
        attempt, outcome = self.lines()
        self.assertTrue(attempt.startswith(b"A\t" + op.encode() + b"\t"))
        self.assertTrue(outcome.startswith(b"O\t" + op.encode() + b"\t"))
        self.assertTrue(attempt.endswith(b"\tapprove-plan\tdelegated\tconverged-2-of-3"))
        self.assertTrue(outcome.endswith(b"\tdone\trecorded"))

    def test_nothing_is_rewritten(self):
        op = self.begin()
        first = self.raw()
        levellog.finish(self.store, op, "refused", "no")
        self.assertTrue(self.raw().startswith(first))
        self.begin()
        self.assertTrue(self.raw().startswith(first))

    def test_identifiers_come_from_secrets_and_differ(self):
        with unittest.mock.patch.object(levellog.secrets, "token_hex", return_value="ab" * 8) as token:
            op = self.begin()
        token.assert_called_once()
        self.assertEqual("ab" * 8, op)
        self.assertNotEqual(self.begin(), self.begin())

    def test_block_and_unknown_levels_write_nothing(self):
        for level in ("block", "BLOCK", "", "ask ", None):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):
                    self.begin(level=level)
        self.assertFalse(os.path.exists(self.path))

    def test_a_key_or_evidence_that_could_add_a_field_or_a_line_writes_nothing(self):
        for field, value in (("key", "a" * 97), ("key", "a\tb"), ("key", "a\nb"), ("key", "Bad Key"), ("key", ""), ("evidence", "a b"),
                             ("evidence", "x\ny"), ("evidence", "x\ty"), ("evidence", "x" * 129),
                             ("evidence", "é")):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    self.begin(**{field: value})
        self.assertFalse(os.path.exists(self.path))

    def test_a_reason_is_cleaned_to_one_line_and_cut_to_200_characters(self):
        op = self.begin()
        levellog.finish(self.store, op, "refused", "bad\nline\twith \x1b[31m escape ‮ and " + "x" * 5000)
        self.assertEqual(2, len(self.lines()))
        outcome = self.lines()[1].decode("ascii")
        self.assertNotIn("\x1b", outcome)
        reason = outcome.split("\t", 4)[4]
        self.assertLessEqual(len(reason), 200)
        self.assertNotIn("\t", reason)

    def test_every_line_is_within_1024_bytes_counted_in_bytes(self):
        op = self.begin(evidence="x" * 128, key="a" * 90)
        levellog.finish(self.store, op, "refused", "\U0001f600" * 5000)
        for line in self.lines():
            self.assertLessEqual(len(line) + 1, 1024)

    def test_an_outcome_is_done_or_refused(self):
        op = self.begin()
        with self.assertRaises(ValueError):
            levellog.finish(self.store, op, "maybe", "")
        with self.assertRaises(ValueError):
            levellog.finish(self.store, "not an id\n", "done", "")
        self.assertEqual(1, len(self.lines()))

    def test_the_writer_does_not_read_the_log(self):
        with open(self.path, "wb") as handle:
            handle.write(b"garbage that is not a record\n" * 3)
        with unittest.mock.patch.object(store.Store, "read", side_effect=AssertionError("read")):
            self.begin()
        self.assertEqual(4, len(self.lines()))


class ConcurrencyTest(LogBase):
    def test_parallel_appends_keep_every_line(self):
        def work():
            for _ in range(25):
                op = self.begin()
                levellog.finish(self.store, op, "done", "ok")

        threads = [threading.Thread(target=work) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        lines = self.lines()
        self.assertEqual(200, len(lines))
        read = levellog.read(self.store)
        self.assertEqual([], read.problems)
        self.assertEqual([], read.unfinished)
        self.assertEqual(100, len(read.operations))


class UnsafePathTest(LogBase):
    def refused(self):
        with self.assertRaises(levellog.LogError):
            self.begin()

    def test_a_symbolic_link_is_refused_and_not_followed(self):
        target = os.path.join(self.base, "target")
        with open(target, "wb") as handle:
            handle.write(b"keep")
        os.symlink(target, self.path)
        self.refused()
        with open(target, "rb") as handle:
            self.assertEqual(b"keep", handle.read())

    def test_a_directory_is_refused(self):
        os.mkdir(self.path)
        self.refused()

    def test_a_fifo_is_refused_without_blocking(self):
        os.mkfifo(self.path)
        self.refused()

    def test_a_file_with_another_hard_link_is_refused_and_unchanged(self):
        other = os.path.join(self.base, "other")
        with open(self.path, "wb") as handle:
            handle.write(b"keep\n")
        os.link(self.path, other)
        self.refused()
        with open(other, "rb") as handle:
            self.assertEqual(b"keep\n", handle.read())

    def test_the_file_is_private(self):
        self.begin()
        self.assertEqual(0, os.stat(self.path).st_mode & 0o077)


class CapTest(LogBase):
    def test_a_full_log_refuses_with_a_message_that_names_it_and_changes_nothing(self):
        with unittest.mock.patch.object(levellog, "MAX_BYTES", 300):
            while True:
                try:
                    self.begin()
                except levellog.LogFull as exc:
                    self.assertIn("level-log", str(exc))
                    break
            size = os.path.getsize(self.path)
            self.assertLessEqual(size, 300)
            with self.assertRaises(levellog.LogFull):
                self.begin()
            self.assertEqual(size, os.path.getsize(self.path))

    def test_the_cap_is_4_mib(self):
        self.assertEqual(4 * 1024 * 1024, levellog.MAX_BYTES)


class FinishFailureTest(LogBase):
    def test_an_outcome_that_cannot_be_written_is_reported_as_such(self):
        op = self.begin()
        with unittest.mock.patch.object(safefs, "append_line", side_effect=safefs.SafeFsError("disk")):
            with self.assertRaises(levellog.OutcomeError):
                levellog.finish(self.store, op, "done", "ok")
        self.assertEqual(1, len(self.lines()))

    def test_an_attempt_that_cannot_be_written_raises_a_log_error(self):
        with unittest.mock.patch.object(safefs, "append_line", side_effect=safefs.SafeFsError("disk")):
            with self.assertRaises(levellog.LogError):
                self.begin()


class ReadingTest(LogBase):
    def test_an_attempt_with_no_outcome_is_listed_as_unfinished_and_not_as_unapproved(self):
        done = self.begin()
        levellog.finish(self.store, done, "done", "ok")
        open_op = self.begin()
        read = levellog.read(self.store)
        self.assertEqual([open_op], [item.op for item in read.unfinished])
        text = "\n".join(levellog.report(read))
        self.assertIn(open_op, text)
        self.assertIn("unfinished", text)
        self.assertIn("does not mean", text)

    def test_a_damaged_line_is_reported_and_the_rest_is_read(self):
        op = self.begin()
        with open(self.path, "ab") as handle:
            handle.write(b"not a record\nO\tbadid\t\x1b[31m\n")
        levellog.finish(self.store, op, "done", "ok")
        read = levellog.read(self.store)
        self.assertEqual(2, len(read.problems))
        self.assertEqual([], read.unfinished)
        self.assertEqual(1, len(read.operations))
        for line in levellog.report(read):
            self.assertNotIn("\x1b", line)

    def test_an_attempt_at_block_and_a_line_over_1024_bytes_are_problems(self):
        op = self.begin()
        with open(self.path, "ab") as handle:
            handle.write(("A\t%s\t2026-01-01T00:00:00Z\tapprove-plan\tblock\t\n" % ("c" * 16)).encode())
            handle.write(("O\t%s\t2026-01-01T00:00:00Z\tdone\t%s\n" % (op, "x" * 1100)).encode())
        read = levellog.read(self.store)
        self.assertEqual(2, len(read.problems))
        self.assertEqual([op], [item.op for item in read.unfinished])

    def test_a_missing_log_reads_as_empty(self):
        read = levellog.read(self.store)
        self.assertEqual(([], [], []), (read.operations, read.unfinished, read.problems))

    def test_the_reason_is_the_last_field_and_opaque(self):
        op = self.begin()
        levellog.finish(self.store, op, "refused", "a\\tb c")
        read = levellog.read(self.store)
        self.assertEqual("a\\tb c", read.operations[0].reason)
        self.assertEqual("refused", read.operations[0].outcome)

    def test_a_forged_second_outcome_does_not_rewrite_the_first(self):
        op = self.begin()
        levellog.finish(self.store, op, "refused", "first")
        with open(self.path, "ab") as handle:
            handle.write(("O\t%s\t2026-01-01T00:00:00Z\tdone\tsecond\n" % op).encode())
        read = levellog.read(self.store)
        self.assertEqual("refused", read.operations[0].outcome)
        self.assertEqual(1, len(read.problems))


if __name__ == "__main__":
    unittest.main()
