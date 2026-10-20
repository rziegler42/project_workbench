import copy
import hashlib
import os
import shutil
import unittest

from tests import test_installplan as helpers
from workbench import installed, installplan, manifest, projectfs, target
from workbench.installed import (AS_INSTALLED, EDITED, GONE, MISSING, UNREADABLE,
                                 InstalledError)

FILL = lambda text: ({"fills": [{"slot": "slot:policy", "source": "policy.md"}]},
                     {"policy.md": text})
MODULES = {"h": (helpers.HARNESS, {}), "notes": helpers.PlanTest.NOTES,
           "a": FILL(b"Rule A\n"), "b": FILL(b"Rule B\n")}
NAMES = ["h", "notes", "a", "b"]


class Fixture(unittest.TestCase):
    """A project written from a real install plan, then read back."""

    package = helpers.PlanTest.package
    select = helpers.PlanTest.select
    build = helpers.PlanTest.build
    plan = helpers.PlanTest.plan

    def setUp(self):
        helpers.PlanTest.setUp(self)
        self.made = self.plan(MODULES, NAMES, state="empty")
        self.project = os.path.join(self.root, "proj")
        for action in self.made.actions:
            if action.kind == "create-dir":
                os.makedirs(os.path.join(self.project, action.path), exist_ok=True)
        for action in self.made.actions:
            if action.kind == "create-file" and action.path != installplan_marker():
                full = os.path.join(self.project, *action.path.split("/"))
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "wb") as handle:
                    handle.write(action.data)

    def writer(self):
        fd = os.open(self.project, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        held = target.Target(self.project, "existing", fd, "proj", os.fstat(fd))
        self.addCleanup(held.close)
        return projectfs.Writer(held)

    def read(self, version="0.1.0"):
        return installed.read(self.writer(), version)

    def path(self, rel):
        return os.path.join(self.project, *rel.split("/"))

    def rewrite(self, rel, edit):
        with open(self.path(rel), "rb") as handle:
            data = handle.read()
        with open(self.path(rel), "wb") as handle:
            handle.write(edit(data))

    def states(self, result=None):
        result = result or self.read()
        return {(e.path, e.block): e.state for e in result.entries}


def installplan_marker():
    return installplan.MARKER_PATH


class ReadBack(Fixture):
    def test_a_fresh_install_reads_back_as_installed(self):
        result = self.read()
        self.assertTrue(result.entries)
        self.assertEqual({AS_INSTALLED}, set(self.states(result).values()))
        self.assertEqual(self.made.manifest, result.document)
        kinds = {e.owner_class for e in result.entries}
        self.assertEqual({"module-owned", "seeded", "slot block"}, kinds)

    def test_there_is_an_entry_for_every_manifest_entry_and_block(self):
        result = self.read()
        self.assertEqual(len(self.made.manifest["files"]), len(result.entries))
        self.assertIn(("AGENTS.md", "p/a"), self.states())
        self.assertIn(("AGENTS.md", "p/b"), self.states())

    def test_a_block_entry_carries_its_slot_and_a_file_entry_does_not(self):
        slots = {(e.path, e.block): e.slot for e in self.read().entries}
        self.assertEqual("policy", slots[("AGENTS.md", "p/a")])
        self.assertIsNone(slots[("AGENTS.md", None)])

    def test_the_manifest_hash_is_that_of_the_file(self):
        with open(self.path(".workbench/manifest.json"), "rb") as handle:
            self.assertEqual(hashlib.sha256(handle.read()).hexdigest(),
                             self.read().manifest_hash)

    def test_a_seeded_file_with_blocks_is_hashed_without_them(self):
        entry = [e for e in self.read().entries if e.path == "AGENTS.md" and e.block is None][0]
        self.assertEqual(AS_INSTALLED, entry.state)
        self.assertEqual(entry.hash, entry.current)

    def test_nothing_is_written(self):
        writer = self.writer()
        before = sorted(os.walk(self.project))
        installed.read(writer, "0.1.0")
        self.assertEqual([], writer.written)
        self.assertEqual(before, sorted(os.walk(self.project)))


class States(Fixture):
    def test_an_edited_module_file(self):
        rel = ".workbench/p/notes/files/docs/notes.md"
        self.rewrite(rel, lambda d: d + b"more\n")
        self.assertEqual(EDITED, self.states()[(rel, None)])
        entry = [e for e in self.read().entries if e.path == rel][0]
        self.assertNotEqual(entry.hash, entry.current)

    def test_an_edited_seeded_file_outside_the_blocks(self):
        self.rewrite("AGENTS.md", lambda d: d + b"\nowner text\n")
        states = self.states()
        self.assertEqual(EDITED, states[("AGENTS.md", None)])
        self.assertEqual(AS_INSTALLED, states[("AGENTS.md", "p/a")])
        self.assertEqual(AS_INSTALLED, states[("AGENTS.md", "p/b")])

    def test_a_missing_file_and_so_missing_blocks(self):
        os.remove(self.path("docs/notes.md"))
        self.assertEqual(MISSING, self.states()[("docs/notes.md", None)])
        os.remove(self.path("AGENTS.md"))
        states = self.states()
        self.assertEqual({MISSING}, {states[("AGENTS.md", b)] for b in (None, "p/a", "p/b")})

    def test_an_edited_block(self):
        self.rewrite("AGENTS.md", lambda d: d.replace(b"Rule A", b"Rule A, changed"))
        states = self.states()
        self.assertEqual(EDITED, states[("AGENTS.md", "p/a")])
        self.assertEqual(AS_INSTALLED, states[("AGENTS.md", "p/b")])
        self.assertEqual(AS_INSTALLED, states[("AGENTS.md", None)])

    def test_a_block_whose_markers_were_removed_is_gone(self):
        def drop(data):
            return data.replace(b"<!-- BEGIN p/b slot:policy -->\nRule B\n"
                                b"<!-- END p/b slot:policy -->\n", b"Rule B\n")
        self.rewrite("AGENTS.md", drop)
        states = self.states()
        self.assertEqual(GONE, states[("AGENTS.md", "p/b")])
        self.assertEqual(AS_INSTALLED, states[("AGENTS.md", "p/a")])
        # The text left behind is not a recorded block, so the file shows as edited.
        self.assertEqual(EDITED, states[("AGENTS.md", None)])

    def test_an_unrecorded_block_makes_the_file_edited(self):
        self.rewrite("AGENTS.md", lambda d: d + b"<!-- BEGIN x/y slot:policy -->\nz\n"
                                                b"<!-- END x/y slot:policy -->\n")
        self.assertEqual(EDITED, self.states()[("AGENTS.md", None)])

    def test_a_scan_error_is_a_state_not_an_exception(self):
        self.rewrite("AGENTS.md", lambda d: d + b"<!-- BEGIN p/a slot:policy -->\n")
        result = self.read()
        states = self.states(result)
        self.assertEqual({UNREADABLE}, {states[("AGENTS.md", b)] for b in (None, "p/a", "p/b")})
        detail = [e.detail for e in result.entries if e.path == "AGENTS.md"][0]
        self.assertIn("slot markers", detail)

    def test_a_malformed_marker_is_unreadable_by_name(self):
        self.rewrite("AGENTS.md", lambda d: d + b"<!-- BEGIN broken\n")
        self.assertEqual(UNREADABLE, self.states()[("AGENTS.md", "p/a")])

    def test_a_link_in_place_of_a_file_is_unreadable(self):
        rel = ".workbench/p/notes/files/docs/notes.md"
        os.remove(self.path(rel))
        os.symlink(self.root, self.path(rel))
        self.assertEqual(UNREADABLE, self.states()[(rel, None)])

    def test_a_link_as_a_parent_is_unreadable(self):
        shutil.rmtree(self.path("docs"))
        os.symlink(self.root, self.path("docs"))
        self.assertEqual(UNREADABLE, self.states()[("docs/notes.md", None)])

    def test_a_directory_in_place_of_a_file_is_unreadable(self):
        os.remove(self.path("docs/notes.md"))
        os.mkdir(self.path("docs/notes.md"))
        self.assertEqual(UNREADABLE, self.states()[("docs/notes.md", None)])

    def test_a_fifo_is_unreadable_and_not_opened(self):
        os.remove(self.path("docs/notes.md"))
        os.mkfifo(self.path("docs/notes.md"))
        self.assertEqual(UNREADABLE, self.states()[("docs/notes.md", None)])


class TheManifest(Fixture):
    def put_manifest(self, document):
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))

    def document(self):
        return copy.deepcopy(self.made.manifest)

    def test_no_manifest_is_refused(self):
        os.remove(self.path(".workbench/manifest.json"))
        with self.assertRaises(InstalledError):
            self.read()

    def test_a_link_or_directory_as_the_manifest_is_refused(self):
        os.remove(self.path(".workbench/manifest.json"))
        os.mkdir(self.path(".workbench/manifest.json"))
        with self.assertRaises(InstalledError):
            self.read()

    def test_a_hand_edited_manifest_that_is_not_canonical_is_refused(self):
        self.rewrite(".workbench/manifest.json", lambda d: d.replace(b"{\n", b"{ \n", 1))
        with self.assertRaises(InstalledError):
            self.read()

    def test_garbage_is_refused(self):
        for data in (b"", b"nope", b"[]", b"\xff"):
            with self.subTest(data=data):
                self.rewrite(".workbench/manifest.json", lambda d: data)
                with self.assertRaises(InstalledError):
                    self.read()

    def test_a_hand_edited_manifest_in_canonical_form_still_parses(self):
        document = self.document()
        document["files"][0]["hash"] = "0" * 64
        self.put_manifest(document)
        result = self.read()
        self.assertEqual("0" * 64, result.document["files"][0]["hash"])
        self.assertEqual(EDITED, result.entries[0].state)

    def test_a_manifest_naming_a_path_it_may_not_is_refused(self):
        for bad in (".workbench/manifest.json", ".workbench/local/harness.json",
                    ".workbench/local", ".workbench/LOCAL/harness.json", ".workbench/Local",
                    ".WORKBENCH/MANIFEST.JSON", ".workbench/Manifest.json"):
            with self.subTest(bad=bad):
                document = self.document()
                document["files"].append({"class": "module-owned", "hash": "0" * 64,
                                          "path": bad})
                document["files"].sort(key=lambda f: (f["path"].encode(), f.get("block", "")))
                self.put_manifest(document)
                with self.assertRaises(InstalledError):
                    self.read()

    def test_the_path_check_itself_ignores_case(self):
        for bad in (".workbench/LOCAL/x", ".workbench/Local", ".WORKBENCH/MANIFEST.JSON"):
            with self.subTest(bad=bad), self.assertRaises(InstalledError):
                installed._check_paths({"files": [{"path": bad}]})
        installed._check_paths({"files": [{"path": ".workbench/localx/x"}]})

    def test_a_manifest_path_that_escapes_is_refused(self):
        document = self.document()
        document["files"].append({"class": "module-owned", "hash": "0" * 64, "path": "../x"})
        with self.assertRaises(manifest.ManifestError):
            manifest.serialize(document)
        # Written by hand, the strict reader refuses it too.
        self.rewrite(".workbench/manifest.json", lambda d: d.replace(
            b'"path": "AGENTS.md"', b'"path": "../AGENTS.md"', 1))
        with self.assertRaises(InstalledError):
            self.read()

    def test_a_path_colliding_with_another_is_refused(self):
        document = self.document()
        document["files"].append({"class": "module-owned", "hash": "0" * 64,
                                  "path": "agents.md"})
        document["files"].sort(key=lambda f: (f["path"].encode(), f.get("block", "")))
        self.put_manifest(document)
        with self.assertRaises(InstalledError):
            self.read()


class Versions(Fixture):
    def setUp(self):
        super().setUp()
        with open(self.path(".workbench/manifest.json"), "rb") as handle:
            self.original = handle.read()

    def set_version(self, version):
        # Written by hand, so values the serializer would refuse reach the reader too.
        self.rewrite(".workbench/manifest.json", lambda d: self.original.replace(
            b'"workbench": "0.1.0"', b'"workbench": "%s"' % version.encode(), 1))

    def test_an_equal_or_lower_recorded_version_proceeds(self):
        for recorded, running in (("0.1.0", "0.1.0"), ("0.1", "0.1.0"), ("0.1.0", "0.1"),
                                  ("0.9.0", "0.10.0"), ("1.2", "1.10"), ("0.1.0", "2")):
            with self.subTest(recorded=recorded, running=running):
                self.set_version(recorded)
                installed.read(self.writer(), running)

    def test_a_higher_recorded_version_is_refused(self):
        for recorded, running in (("0.2.0", "0.1.0"), ("1.10", "1.9"), ("0.1.1", "0.1")):
            with self.subTest(recorded=recorded, running=running):
                self.set_version(recorded)
                with self.assertRaises(InstalledError) as caught:
                    installed.read(self.writer(), running)
                self.assertIn("newer", str(caught.exception))

    def test_a_version_that_is_not_dotted_decimal_is_refused_on_either_side(self):
        for recorded in ("1.0-beta", "1.x", "v1.0", ".1", "1.", "1..0", "1.0.0.0.0.0.0.0.0",
                         "9999999999"):
            with self.subTest(recorded=recorded):
                self.set_version(recorded)
                with self.assertRaises(InstalledError):
                    installed.read(self.writer(), "0.1.0")
        self.set_version("0.1.0")
        for running in ("1.0-beta", "", None, 1):
            with self.subTest(running=running), self.assertRaises(InstalledError):
                installed.read(self.writer(), running)

    def test_version_keys_ignore_trailing_zero_parts(self):
        self.assertEqual(installed.version_key("1.0"), installed.version_key("1.0.0"))
        self.assertLess(installed.version_key("1.9"), installed.version_key("1.10"))


if __name__ == "__main__":
    unittest.main()
