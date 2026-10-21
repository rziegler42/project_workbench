import copy
import json
import os
import unittest

from workbench import localmanifest, safefs
from workbench.localmanifest import LocalManifestError
from workbench.projectfs import WriteConflict
from tests.test_projectfs import Fixture

HASH = "a" * 64
OTHER = "b" * 64


def document(**changes):
    value = {
        "files": [{"hash": HASH, "path": ".claude/agents/reviewer.md"},
                  {"hash": OTHER, "path": ".claude/settings.local.json"},
                  {"hash": HASH, "path": "CLAUDE.md"}],
        "format": 1,
        "harness": "claude",
        "module_version": "1.2.0",
        "source": "packages/workbench",
        "tree": OTHER,
        "workbench": "0.1.0",
    }
    value.update(changes)
    return value


class Shape(unittest.TestCase):
    def test_the_canonical_bytes_are_stable_and_read_back(self):
        data = localmanifest.serialize(document())
        self.assertEqual(data, localmanifest.serialize(copy.deepcopy(document())))
        self.assertEqual(document(), localmanifest.parse(data))
        self.assertTrue(data.endswith(b"}\n"))
        data.decode("ascii")

    def test_the_layout_is_one_file_entry_per_line(self):
        lines = localmanifest.serialize(document()).decode().split("\n")
        self.assertIn('    {"hash": "%s", "path": "CLAUDE.md"}' % HASH, lines)
        self.assertEqual('  "files": [', lines[1])

    def test_an_empty_file_list_is_valid(self):
        data = localmanifest.serialize(document(files=[]))
        self.assertIn(b'"files": []', data)
        self.assertEqual([], localmanifest.parse(data)["files"])

    def test_a_non_canonical_document_is_refused(self):
        data = localmanifest.serialize(document())
        loose = json.dumps(json.loads(data), indent=4).encode()
        for text in (loose, data.replace(b"\n", b"\r\n"), data + b"\n", data[:-1], b"",
                     data.replace(b"  ", b"\t", 1), b"[]", b"null", b"{}"):
            with self.assertRaises(LocalManifestError, msg=text[:30]):
                localmanifest.parse(text)

    def test_a_duplicate_key_is_refused(self):
        data = localmanifest.serialize(document())
        doubled = data.replace(b'  "format": 1,\n', b'  "format": 1,\n  "format": 1,\n')
        with self.assertRaises(LocalManifestError):
            localmanifest.parse(doubled)

    def test_a_key_that_is_not_in_the_format_is_refused(self):
        for key in ("time", "allow", "manifest", "seed"):
            with self.assertRaises(LocalManifestError, msg=key):
                localmanifest.serialize(document(**{key: "x"}))
        missing = document()
        del missing["tree"]
        with self.assertRaises(LocalManifestError):
            localmanifest.serialize(missing)

    def test_bad_values_are_refused(self):
        bad = [
            {"format": 2}, {"format": True}, {"format": "1"}, {"format": 1.0},
            {"harness": "Claude"}, {"harness": ""}, {"harness": "a" * 65}, {"harness": 3},
            {"module_version": "v1"}, {"module_version": ""}, {"module_version": 1},
            {"source": ""}, {"source": "a\nb"}, {"source": "x" * 513}, {"source": None},
            {"tree": "A" * 64}, {"tree": "a" * 63}, {"tree": "sha"}, {"tree": None},
            {"workbench": ""}, {"workbench": "0.1 0"}, {"workbench": "-1"}, {"workbench": 1},
            {"files": None}, {"files": "x"}, {"files": [None]}, {"files": [[]]},
            {"files": [{"path": "a"}]},
            {"files": [{"hash": HASH, "path": "a", "mode": 1}]},
            {"files": [{"hash": "x", "path": "a"}]},
            {"files": [{"hash": HASH, "path": 3}]},
            {"files": [{"hash": HASH, "path": "../a"}]},
            {"files": [{"hash": HASH, "path": "/a"}]},
            {"files": [{"hash": HASH, "path": ".git/hooks/x"}]},
            {"files": [{"hash": HASH, "path": "a\nb"}]},
            {"files": [{"hash": HASH, "path": ".workbench/local/harness.json"}]},
            {"files": [{"hash": HASH, "path": ".workbench/local/x"}]},
            {"files": [{"hash": HASH, "path": ".workbench/local"}]},
            {"files": [{"hash": HASH, "path": ".Workbench/Local/harness.json"}]},
            {"files": [{"hash": HASH, "path": ".WORKBENCH/LOCAL"}]},
            {"files": [{"hash": HASH, "path": ".workbench/LOCAL/x/y"}]},
        ]
        for changes in bad:
            with self.assertRaises(LocalManifestError, msg=repr(changes)):
                localmanifest.serialize(document(**changes))

    def test_files_must_be_sorted_unique_and_not_overlap(self):
        a, b = {"hash": HASH, "path": "a"}, {"hash": HASH, "path": "b"}
        for files in ([b, a], [a, a], [a, {"hash": HASH, "path": "A"}],
                      [a, {"hash": HASH, "path": "a/b"}]):
            with self.assertRaises(LocalManifestError, msg=repr(files)):
                localmanifest.serialize(document(files=files))

    def test_the_file_count_and_size_are_bounded(self):
        many = [{"hash": HASH, "path": "f%05d" % n} for n in range(localmanifest.MAX_FILES + 1)]
        with self.assertRaises(LocalManifestError):
            localmanifest.serialize(document(files=many))
        with self.assertRaises(LocalManifestError):
            localmanifest.parse(b" " * (localmanifest.MAX_BYTES + 1))

    def test_the_largest_allowed_document_fits_the_size_bound(self):
        longest = [{"hash": HASH, "path": ("d%04d/" % n) + "x" * 400}
                   for n in range(localmanifest.MAX_FILES)]
        data = localmanifest.serialize(document(files=longest))
        self.assertLess(len(data), localmanifest.MAX_BYTES)
        self.assertEqual(longest, localmanifest.parse(data)["files"])

    def test_non_bytes_are_refused(self):
        for value in (None, "x", 3):
            with self.assertRaises(LocalManifestError):
                localmanifest.parse(value)

    def test_the_record_is_not_a_committed_manifest(self):
        from workbench import manifest
        self.assertNotIn("seed", localmanifest.TOP_KEYS)
        with self.assertRaises(manifest.ManifestError):
            manifest.parse(localmanifest.serialize(document()))


class Files(Fixture):
    def test_none_recorded_reads_as_none(self):
        self.assertIsNone(localmanifest.read(self.writer()))

    def test_write_then_read_round_trips(self):
        writer = self.writer()
        data = localmanifest.write(writer, document())
        with open(os.path.join(self.root, localmanifest.PATH), "rb") as handle:
            self.assertEqual(data, handle.read())
        self.assertEqual(document(), localmanifest.read(self.writer()))
        self.assertIn(localmanifest.PATH, writer.written)

    def test_an_existing_record_is_a_conflict_and_is_not_replaced(self):
        writer = self.writer()
        localmanifest.write(writer, document())
        with self.assertRaises(WriteConflict):
            localmanifest.write(writer, document(harness="other"))
        self.assertEqual("claude", localmanifest.read(writer)["harness"])

    def test_a_linked_record_is_not_written_through(self):
        os.makedirs(os.path.join(self.root, ".workbench"))
        os.symlink(self.outside, os.path.join(self.root, ".workbench", "local"))
        with self.assertRaises(WriteConflict):
            localmanifest.write(self.writer(), document())
        self.assertEqual([], os.listdir(self.outside))

    def test_a_record_that_is_a_link_is_refused_on_read(self):
        os.makedirs(os.path.join(self.root, ".workbench", "local"))
        target = os.path.join(self.outside, "t")
        with open(target, "wb") as handle:
            handle.write(localmanifest.serialize(document()))
        os.symlink(target, os.path.join(self.root, localmanifest.PATH))
        with self.assertRaises(LocalManifestError):
            localmanifest.read(self.writer())

    def test_a_record_that_is_not_canonical_is_refused_on_read(self):
        os.makedirs(os.path.join(self.root, ".workbench", "local"))
        with open(os.path.join(self.root, localmanifest.PATH), "wb") as handle:
            handle.write(b'{"harness": "claude"}')
        with self.assertRaises(LocalManifestError):
            localmanifest.read(self.writer())

    def test_an_invalid_document_writes_nothing(self):
        with self.assertRaises(LocalManifestError):
            localmanifest.write(self.writer(), document(files=[{"hash": "x", "path": "a"}]))
        self.assertEqual([], os.listdir(self.root))

    def test_the_path_is_the_one_the_spec_names(self):
        self.assertEqual(".workbench/local/harness.json", localmanifest.PATH)
        safefs.validate_relpath(localmanifest.PATH)


if __name__ == "__main__":
    unittest.main()
