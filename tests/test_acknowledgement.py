import hashlib
import json
import os
import tempfile
import unittest
import unittest.mock

from workbench import acknowledgement, projectfs, store, target
from workbench.acknowledgement import (ADDED, CHANGED, REMOVED, AcknowledgementError, Difference,
                                       UnknownProject)

PROJECT = "ab" * 32


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(document):
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


class Fixture(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.guarded = store.Store(os.path.join(self.base, "store"))
        self.guarded.ensure()
        self.root = os.path.join(self.base, "proj")
        os.mkdir(self.root)
        self.outside = os.path.join(self.base, "outside")
        os.mkdir(self.outside)

    def writer(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        held = target.Target(self.root, "existing", fd, "proj", os.fstat(fd))
        self.addCleanup(held.close)
        return projectfs.Writer(held)

    def put(self, rel, data=b"x"):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)

    def entry(self, name, data):
        self.guarded.write("projects/%s/%s" % (PROJECT, name), data)

    def baselines(self, mapping):
        self.entry("baselines", canonical({"baselines": mapping, "format": 1}))


class ReadBaselines(Fixture):
    def test_reads_what_install_writes(self):
        mapping = {".workbench/manifest.json": sha(b"m"), "AGENTS.md": sha(b"a")}
        self.baselines(mapping)
        self.assertEqual(mapping, acknowledgement.read_baselines(self.guarded, PROJECT))

    def test_no_entry_is_none(self):
        self.assertIsNone(acknowledgement.read_baselines(self.guarded, PROJECT))
        self.assertIsNone(acknowledgement.read_seen(self.guarded, PROJECT))

    def test_an_empty_mapping_is_accepted(self):
        self.baselines({})
        self.assertEqual({}, acknowledgement.read_baselines(self.guarded, PROJECT))

    def test_hostile_files_are_refused(self):
        good = sha(b"x")
        cases = {
            "not json": b"nope",
            "not an object": b"[]\n",
            "wrong format number": canonical({"baselines": {}, "format": 2}),
            "boolean format": canonical({"baselines": {}, "format": True}),
            "extra key": canonical({"baselines": {}, "format": 1, "more": 1}),
            "missing key": canonical({"format": 1}),
            "mapping is a list": canonical({"baselines": [], "format": 1}),
            "non-hex hash": canonical({"baselines": {"a": "z" * 64}, "format": 1}),
            "upper-case hash": canonical({"baselines": {"a": good.upper()}, "format": 1}),
            "short hash": canonical({"baselines": {"a": good[:63]}, "format": 1}),
            "hash is a number": canonical({"baselines": {"a": 1}, "format": 1}),
            "absolute path": canonical({"baselines": {"/etc/passwd": good}, "format": 1}),
            "parent path": canonical({"baselines": {"../a": good}, "format": 1}),
            "dot segment": canonical({"baselines": {"a/./b": good}, "format": 1}),
            "empty path": canonical({"baselines": {"": good}, "format": 1}),
            "backslash path": canonical({"baselines": {"a\\b": good}, "format": 1}),
            "unsorted keys": b'{\n  "format": 1,\n  "baselines": {}\n}\n',
            "unsorted paths": b'{\n  "baselines": {\n    "b": "%s",\n    "a": "%s"\n  },\n'
                              b'  "format": 1\n}\n' % (good.encode(), good.encode()),
            "duplicate key": b'{"baselines": {}, "baselines": {}, "format": 1}\n',
            "compact spacing": json.dumps({"baselines": {}, "format": 1}, sort_keys=True).encode()
                               + b"\n",
            "no final line feed": canonical({"baselines": {}, "format": 1}).rstrip(b"\n"),
            "trailing blank line": canonical({"baselines": {}, "format": 1}) + b"\n",
            "not utf-8": b"\xff\xfe",
        }
        for name, data in cases.items():
            with self.subTest(name):
                self.entry("baselines", data)
                with self.assertRaises(AcknowledgementError):
                    acknowledgement.read_baselines(self.guarded, PROJECT)

    def test_the_entry_must_be_a_regular_file(self):
        os.mkdir(os.path.join(self.base, "store", "projects", PROJECT))
        os.mkdir(os.path.join(self.base, "store", "projects", PROJECT, "baselines"))
        with self.assertRaises(AcknowledgementError):
            acknowledgement.read_baselines(self.guarded, PROJECT)

    def test_a_link_in_the_store_is_refused(self):
        directory = os.path.join(self.base, "store", "projects", PROJECT)
        os.makedirs(directory)
        with open(os.path.join(self.outside, "b"), "wb") as handle:
            handle.write(canonical({"baselines": {}, "format": 1}))
        os.symlink(os.path.join(self.outside, "b"), os.path.join(directory, "baselines"))
        with self.assertRaises(AcknowledgementError):
            acknowledgement.read_baselines(self.guarded, PROJECT)

    def test_a_bad_project_id_is_refused(self):
        for bad in ("", "../x", "AB" * 32, "ab" * 31, None, 5):
            with self.subTest(bad=bad), self.assertRaises(AcknowledgementError):
                acknowledgement.read_baselines(self.guarded, bad)


class ReadSeen(Fixture):
    def seen(self, **changes):
        document = {"format": 1, "kind": "path", "value": "/some/where"}
        document.update(changes)
        self.entry("seen", canonical(document))

    def test_reads_the_path(self):
        self.seen()
        self.assertEqual("/some/where", acknowledgement.read_seen(self.guarded, PROJECT))

    def test_hostile_records_are_refused(self):
        cases = {
            "other kind": {"kind": "remote"},
            "wrong format": {"format": 2},
            "relative path": {"value": "some/where"},
            "empty path": {"value": ""},
            "trailing slash": {"value": "/some/where/"},
            "nul in path": {"value": "/some\0where"},
            "path is a list": {"value": ["/some/where"]},
            "extra key": {"more": 1},
        }
        for name, changes in cases.items():
            with self.subTest(name):
                self.seen(**changes)
                with self.assertRaises(AcknowledgementError):
                    acknowledgement.read_seen(self.guarded, PROJECT)

    def test_the_root_path_is_a_path(self):
        self.seen(value="/")
        self.assertEqual("/", acknowledgement.read_seen(self.guarded, PROJECT))

    def test_a_missing_key_is_refused(self):
        self.entry("seen", canonical({"format": 1, "kind": "path"}))
        with self.assertRaises(AcknowledgementError):
            acknowledgement.read_seen(self.guarded, PROJECT)


class CheckKnown(unittest.TestCase):
    def test_a_known_project_at_its_path_passes(self):
        acknowledgement.check_known({}, "/p", "/p")

    def test_no_baselines_no_record_and_another_path_are_each_refused(self):
        for baselines, seen, here in ((None, "/p", "/p"), ({}, None, "/p"), ({}, "/q", "/p")):
            with self.subTest(baselines=baselines, seen=seen), \
                    self.assertRaises(UnknownProject):
                acknowledgement.check_known(baselines, seen, here)

    def test_an_unknown_project_is_an_acknowledgement_error(self):
        self.assertTrue(issubclass(UnknownProject, AcknowledgementError))

    def test_the_path_is_compared_exactly(self):
        for here in ("/P", "/p/", "/p/."):
            with self.subTest(here=here), self.assertRaises(UnknownProject):
                acknowledgement.check_known({}, "/p", here)


class Differences(Fixture):
    def installed(self):
        """A project as install leaves it: the manifest, a module file and a seeded file."""
        files = {".workbench/manifest.json": b"{}", ".workbench/pkg/mod/a.md": b"a",
                 ".workbench/.gitignore": b"local/\n", "AGENTS.md": b"agents"}
        for rel, data in files.items():
            self.put(rel, data)
        self.baselines_map = {rel: sha(data) for rel, data in files.items()}
        return self.baselines_map

    def found(self, writes=()):
        return acknowledgement.differences(self.writer(), self.baselines_map, writes)

    def test_a_clean_project_has_none(self):
        self.installed()
        self.assertEqual([], self.found())
        self.assertEqual([], self.found(["AGENTS.md"]))

    def test_a_changed_file(self):
        self.installed()
        self.put(".workbench/pkg/mod/a.md", b"edited")
        self.assertEqual([Difference(".workbench/pkg/mod/a.md", CHANGED, sha(b"a"),
                                     sha(b"edited"), "")], self.found())

    def test_a_changed_manifest(self):
        self.installed()
        self.put(".workbench/manifest.json", b"{ }")
        self.assertEqual([(".workbench/manifest.json", CHANGED)],
                         [(d.path, d.kind) for d in self.found()])

    def test_a_removed_file_and_a_removed_manifest(self):
        self.installed()
        os.remove(os.path.join(self.root, ".workbench", "pkg", "mod", "a.md"))
        os.remove(os.path.join(self.root, ".workbench", "manifest.json"))
        self.assertEqual([(".workbench/manifest.json", REMOVED, sha(b"{}"), None),
                          (".workbench/pkg/mod/a.md", REMOVED, sha(b"a"), None)],
                         [(d.path, d.kind, d.baseline, d.current) for d in self.found()])

    def test_an_added_file_anywhere_under_workbench(self):
        self.installed()
        self.put(".workbench/new.md", b"n")
        self.put(".workbench/pkg/mod/deep/er/b.md", b"b")
        self.assertEqual([(".workbench/new.md", ADDED, None, sha(b"n")),
                          (".workbench/pkg/mod/deep/er/b.md", ADDED, None, sha(b"b"))],
                         [(d.path, d.kind, d.baseline, d.current) for d in self.found()])

    def test_local_scratch_is_not_covered(self):
        self.installed()
        self.put(".workbench/local/harness.json", b"{}")
        self.put(".workbench/local/deep/x", b"x")
        self.assertEqual([], self.found())

    def test_a_local_that_is_a_link_or_a_file_is_not_scratch_and_is_reported(self):
        self.installed()
        work = os.path.join(self.root, ".workbench")
        os.symlink(self.outside, os.path.join(work, "local"))
        self.assertEqual([(".workbench/local", ADDED, "a link")],
                         [(d.path, d.kind, d.reason) for d in self.found()])
        os.unlink(os.path.join(work, "local"))
        self.put(".workbench/local", b"committed content")
        self.assertEqual([(".workbench/local", ADDED, sha(b"committed content"))],
                         [(d.path, d.kind, d.current) for d in self.found()])

    def test_a_baseline_under_local_is_not_compared(self):
        self.installed()
        self.baselines_map[".workbench/local/incomplete"] = sha(b"")
        self.assertEqual([], self.found())

    def test_an_empty_directory_is_not_a_difference(self):
        self.installed()
        os.mkdir(os.path.join(self.root, ".workbench", "empty"))
        self.assertEqual([], self.found())

    def test_a_file_outside_workbench_is_compared_only_when_it_will_be_written(self):
        self.installed()
        self.put("AGENTS.md", b"owner edit")
        self.assertEqual([], self.found())
        self.assertEqual([(("AGENTS.md"), CHANGED)],
                         [(d.path, d.kind) for d in self.found(["AGENTS.md"])])

    def test_a_write_target_that_is_new_is_no_difference(self):
        self.installed()
        self.assertEqual([], self.found(["docs/new.md"]))

    def test_a_write_target_present_without_a_baseline_is_added(self):
        self.installed()
        self.put("docs/new.md", b"mine")
        self.assertEqual([("docs/new.md", ADDED)],
                         [(d.path, d.kind) for d in self.found(["docs/new.md"])])

    def test_a_removed_write_target_is_removed(self):
        self.installed()
        os.remove(os.path.join(self.root, "AGENTS.md"))
        self.assertEqual([("AGENTS.md", REMOVED)],
                         [(d.path, d.kind) for d in self.found(["AGENTS.md"])])

    def test_a_link_in_the_walk_is_a_difference_and_is_not_followed(self):
        self.installed()
        with open(os.path.join(self.outside, "secret"), "wb") as handle:
            handle.write(b"secret")
        os.symlink(os.path.join(self.outside, "secret"),
                   os.path.join(self.root, ".workbench", "pkg", "link"))
        os.symlink(self.outside, os.path.join(self.root, ".workbench", "dirlink"))
        found = self.found()
        self.assertEqual([(".workbench/dirlink", ADDED, "a link"),
                          (".workbench/pkg/link", ADDED, "a link")],
                         [(d.path, d.kind, d.reason) for d in found])
        self.assertTrue(all(d.current is None for d in found))

    def test_a_link_where_a_baselined_file_is_changed(self):
        self.installed()
        path = os.path.join(self.root, ".workbench", "pkg", "mod", "a.md")
        os.remove(path)
        os.symlink(os.path.join(self.outside, "elsewhere"), path)
        self.assertEqual([(".workbench/pkg/mod/a.md", CHANGED, sha(b"a"), None, "a link")],
                         [tuple(d) for d in self.found()])

    def test_a_directory_where_a_file_is_expected_is_changed(self):
        self.installed()
        path = os.path.join(self.root, ".workbench", "pkg", "mod", "a.md")
        os.remove(path)
        os.mkdir(path)
        self.assertEqual([(".workbench/pkg/mod/a.md", CHANGED, "a directory")],
                         [(d.path, d.kind, d.reason) for d in self.found()])

    def test_a_fifo_is_a_difference_and_is_not_opened(self):
        self.installed()
        os.mkfifo(os.path.join(self.root, ".workbench", "pipe"))
        self.assertEqual([(".workbench/pipe", ADDED, "not a regular file")],
                         [(d.path, d.kind, d.reason) for d in self.found()])

    def test_a_link_at_a_write_target_is_a_difference(self):
        self.installed()
        os.remove(os.path.join(self.root, "AGENTS.md"))
        os.symlink(self.outside, os.path.join(self.root, "AGENTS.md"))
        self.assertEqual([("AGENTS.md", CHANGED, "not a regular file")],
                         [(d.path, d.kind, d.reason) for d in self.found(["AGENTS.md"])])

    def test_a_link_as_a_parent_of_a_write_target_is_a_difference(self):
        self.installed()
        os.symlink(self.outside, os.path.join(self.root, "docs"))
        self.assertEqual([("docs/new.md", "not a regular file")],
                         [(d.path, d.reason) for d in self.found(["docs/new.md"])])

    def test_workbench_itself_a_link_is_refused(self):
        os.symlink(self.outside, os.path.join(self.root, ".workbench"))
        self.baselines_map = {}
        with self.assertRaises(AcknowledgementError):
            self.found()

    def test_workbench_missing_makes_every_baselined_file_removed(self):
        self.baselines_map = {".workbench/manifest.json": sha(b"m"), "AGENTS.md": sha(b"a")}
        self.assertEqual([(".workbench/manifest.json", REMOVED)],
                         [(d.path, d.kind) for d in self.found()])

    def test_a_bad_write_path_is_refused(self):
        self.installed()
        for bad in ("/etc/passwd", "../x", "a//b", ""):
            with self.subTest(bad=bad), self.assertRaises(AcknowledgementError):
                self.found([bad])

    def test_a_huge_tree_is_refused(self):
        self.installed()
        with unittest.mock.patch.object(acknowledgement, "MAX_WALKED", 5):
            for number in range(10):
                self.put(".workbench/bulk/f%d" % number)
            with self.assertRaises(AcknowledgementError):
                self.found()

    def test_a_deep_tree_is_refused(self):
        self.installed()
        with unittest.mock.patch.object(acknowledgement, "MAX_DEPTH", 3):
            self.put(".workbench/a/b/c/d/e/f")
            with self.assertRaises(AcknowledgementError):
                self.found()

    def test_a_too_large_file_is_a_difference_not_a_crash(self):
        self.installed()
        self.put(".workbench/big", b"x" * 20)
        with unittest.mock.patch.object(projectfs.safefs, "MAX_FILE_BYTES", 10):
            found = self.found()
        self.assertEqual([(".workbench/big", ADDED)], [(d.path, d.kind) for d in found])
        self.assertTrue(found[0].reason.startswith("unreadable"))

    def test_nothing_is_written(self):
        self.installed()
        before = sorted(self.tree())
        writer = self.writer()
        acknowledgement.differences(writer, self.baselines_map, ["AGENTS.md", "docs/x"])
        self.assertEqual([], writer.written)
        self.assertEqual(before, sorted(self.tree()))

    def tree(self):
        for here, directories, files in os.walk(self.root):
            for name in directories + files:
                yield os.path.relpath(os.path.join(here, name), self.root)


if __name__ == "__main__":
    unittest.main()
