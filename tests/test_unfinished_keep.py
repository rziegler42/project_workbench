"""The marker's record of an adoption: a kept file is recorded as unchanged, never as written."""

import unittest

from workbench import unfinished

H1, H2 = "1" * 64, "2" * 64
PROJECT = "a" * 64


def build(**changes):
    values = dict(command="adopt", project=PROJECT, version="0.1.0",
                  files=[("AGENTS.md", "keep", H1, H1), ("docs/a.md", "create", None, H2)],
                  dirs=[".workbench", "docs"], git=[], store=[])
    values.update(changes)
    return unfinished.build(**values)


class KeepTest(unittest.TestCase):
    def test_an_adopt_record_with_a_kept_file_reads_back(self):
        record = unfinished.parse(build())
        self.assertEqual("adopt", record.command)
        self.assertEqual([unfinished.FileWrite("AGENTS.md", "keep", H1, H1),
                          unfinished.FileWrite("docs/a.md", "create", None, H2)], list(record.files))

    def test_a_kept_file_needs_the_same_hash_before_and_after(self):
        for files in ([("a", "keep", H1, H2)], [("a", "keep", None, H1)], [("a", "keep", H1, None)]):
            with self.subTest(files=files), self.assertRaises(unfinished.UnfinishedError):
                build(files=files)

    def test_install_upgrade_and_add_records_still_read(self):
        for command in ("install", "upgrade", "add"):
            record = unfinished.parse(build(command=command, files=[("a", "create", None, H1)]))
            self.assertEqual(command, record.command)

    def test_an_unknown_command_or_operation_is_refused(self):
        with self.assertRaises(unfinished.UnfinishedError):
            build(command="adopted")
        with self.assertRaises(unfinished.UnfinishedError):
            build(files=[("a", "keeps", H1, H1)])


if __name__ == "__main__":
    unittest.main()
