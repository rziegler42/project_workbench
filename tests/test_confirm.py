import collections
import io
import unittest
import unittest.mock

from workbench import confirm, projectfs

Action = collections.namedtuple("Action", "kind path")
Plan = collections.namedtuple("Plan", "actions store_writes")
DIGEST = "0123456789abcdef" * 4


class Writer:
    def __init__(self, written, made_target=False):
        self.written = written
        self.made_target = made_target


class Stream(io.StringIO):
    def __init__(self, text):
        super().__init__(text)
        self.limits = []

    def fileno(self):
        return 99

    def readline(self, limit=-1):
        self.limits.append(limit)
        return super().readline(limit)


class TypedDigest(unittest.TestCase):
    def test_token_is_the_first_twelve_characters(self):
        self.assertEqual(DIGEST[:12], confirm.token_of(DIGEST))
        self.assertEqual(12, len(confirm.token_of(DIGEST)))

    def test_matching_answer_is_accepted_with_surrounding_space(self):
        with unittest.mock.patch.object(confirm.termios, "tcflush"):
            self.assertTrue(confirm.typed_matches(Stream("  %s \n" % DIGEST[:12]), DIGEST))

    def test_other_answers_are_not(self):
        for answer in ("\n", "yes\n", DIGEST[:11] + "\n", DIGEST[:13] + "\n", DIGEST[1:13] + "\n"):
            with self.subTest(answer=answer), unittest.mock.patch.object(confirm.termios,
                                                                          "tcflush"):
                self.assertFalse(confirm.typed_matches(Stream(answer), DIGEST))

    def test_typed_ahead_input_is_discarded_before_the_read(self):
        order = []
        stream = Stream(DIGEST[:12] + "\n")
        stream.readline = lambda limit=-1: order.append("read") or DIGEST[:12]
        with unittest.mock.patch.object(
                confirm.termios, "tcflush", lambda fd, what: order.append(("flush", fd, what))):
            self.assertTrue(confirm.typed_matches(stream, DIGEST))
        self.assertEqual([("flush", 99, confirm.termios.TCIFLUSH), "read"], order)

    def test_the_answer_is_bounded(self):
        stream = Stream(DIGEST[:12] + "\n")
        with unittest.mock.patch.object(confirm.termios, "tcflush"):
            confirm.typed_matches(stream, DIGEST)
        self.assertEqual([confirm.MAX_ANSWER], stream.limits)

    def test_a_stream_that_cannot_be_flushed_is_still_read(self):
        class NoDescriptor(io.StringIO):
            def fileno(self):
                raise OSError("no descriptor")

        self.assertTrue(confirm.typed_matches(NoDescriptor(DIGEST[:12] + "\n"), DIGEST))

    def test_an_overlong_line_is_cut_and_so_does_not_match(self):
        with unittest.mock.patch.object(confirm.termios, "tcflush"):
            line = "x" * (confirm.MAX_ANSWER + 50) + DIGEST[:12] + "\n"
            self.assertFalse(confirm.typed_matches(Stream(line), DIGEST))


class FailureReport(unittest.TestCase):
    def progress(self, written, planned, store=(), stored=(), made_target=False):
        progress = confirm.Progress()
        progress.writer = Writer(written, made_target)
        progress.plan = Plan(planned, list(store))
        progress.stored = list(stored)
        return progress

    def report(self, progress, cause="boom"):
        err = io.StringIO()
        confirm.report_failure(progress, cause, err)
        return err.getvalue()

    def test_lists_what_was_written_and_what_was_not(self):
        text = self.report(self.progress(
            [projectfs.MARKER, "a"],
            [Action("create-file", "a"), Action("create-dir", "d"), Action("git-init", None)],
            made_target=True))
        self.assertIn("failed: boom\n", text)
        self.assertIn("written:\n  ./ (the target directory)\n  %s\n  a\n" % projectfs.MARKER,
                      text)
        self.assertIn("not written:\n  d/\n  .git/\n", text)
        self.assertIn("%s is left in place" % projectfs.MARKER, text)
        self.assertNotIn("guarded store entries are not", text)

    def test_store_entries_not_yet_written_are_listed(self):
        text = self.report(self.progress(
            ["a"], [Action("create-file", "a")], store=[("s/1", b""), ("s/2", b"")],
            stored=["s/1"]))
        self.assertIn("not written:\n  s/2\n", text)
        self.assertIn("the project's files are written but its guarded store entries are not",
                      text)

    def test_long_groups_are_cut(self):
        names = ["f%03d" % number for number in range(confirm.LISTED + 5)]
        text = self.report(self.progress([], [Action("create-file", n) for n in names]))
        self.assertIn("  f%03d\n" % (confirm.LISTED - 1), text)
        self.assertNotIn("  f%03d\n" % confirm.LISTED, text)
        self.assertIn("  and 5 more\n", text)

    def test_the_cause_is_shown_as_ascii(self):
        text = self.report(self.progress([], []), cause="bad \x1b[31mred‮")
        self.assertNotIn("\x1b", text)
        self.assertNotIn("‮", text)

    def test_progress_starts_empty(self):
        progress = confirm.Progress()
        self.assertEqual((False, None, None, []),
                         (progress.started, progress.writer, progress.plan, progress.stored))


if __name__ == "__main__":
    unittest.main()
