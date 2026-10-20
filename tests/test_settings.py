import json
import os
import tempfile
import unittest

import support
from workbench import floor, safefs, settings, store


class SettingsBase(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.root = os.path.join(self.base, "store")
        self.store = store.Store(self.root)
        self.store.ensure()

    def put(self, data):
        with open(os.path.join(self.root, "settings"), "wb") as handle:
            handle.write(data if isinstance(data, bytes) else json.dumps(data).encode())

    def raw(self):
        with open(os.path.join(self.root, "settings"), "rb") as handle:
            return handle.read()


class SeedTest(SettingsBase):
    def test_seeds_when_missing(self):
        self.assertTrue(settings.seed(self.store))
        document = json.loads(self.raw())
        self.assertEqual(document["version"], 1)
        self.assertEqual(document["floor"], [stop.id for stop in floor.FLOOR])
        self.assertEqual(document["checkpoints"], {})

    def test_seed_is_deterministic_and_does_not_overwrite(self):
        settings.seed(self.store)
        first = self.raw()
        self.put({"version": 1, "checkpoints": {"plan-approval": "delegate"}, "floor": []})
        edited = self.raw()
        self.assertFalse(settings.seed(self.store))
        self.assertEqual(self.raw(), edited)
        self.assertNotEqual(first, edited)

    def test_two_seeds_write_identical_bytes(self):
        settings.seed(self.store)
        first = self.raw()
        os.unlink(os.path.join(self.root, "settings"))
        settings.seed(self.store)
        self.assertEqual(self.raw(), first)

    def test_a_damaged_file_survives_initialization_unchanged_and_is_reported(self):
        self.put(b"{ not json")
        loaded = settings.initialize(self.store)
        self.assertEqual(self.raw(), b"{ not json")
        self.assertEqual(len(loaded.problems), 1)
        self.assertIn("damaged", loaded.problems[0])
        self.assertEqual(loaded.checkpoint("plan-approval"), "stop")

    def test_a_symbolic_link_in_place_of_the_file_is_not_followed_or_replaced(self):
        target = os.path.join(self.base, "target")
        with open(target, "wb") as handle:
            handle.write(b'{"version": 1, "checkpoints": {"x": "delegate"}}')
        os.symlink(target, os.path.join(self.root, "settings"))
        loaded = settings.initialize(self.store)
        self.assertTrue(os.path.islink(os.path.join(self.root, "settings")))
        with open(target, "rb") as handle:
            self.assertIn(b"delegate", handle.read())
        self.assertEqual(loaded.checkpoint("x"), "stop")
        self.assertIn("not a regular file", loaded.problems[0])

    def test_a_directory_in_place_of_the_file_is_reported(self):
        os.mkdir(os.path.join(self.root, "settings"))
        loaded = settings.initialize(self.store)
        self.assertIn("not a regular file", loaded.problems[0])
        self.assertEqual(loaded.checkpoint("x"), "stop")


class CheckpointTest(SettingsBase):
    def test_with_no_settings_every_checkpoint_stops(self):
        loaded = settings.load(self.store)
        self.assertEqual(loaded.problems, [])
        for name in ("plan-approval", "fetch-output", "anything", ""):
            self.assertEqual(loaded.checkpoint(name), "stop")

    def test_seeded_settings_stop_everything(self):
        loaded = settings.initialize(self.store)
        self.assertEqual((loaded.problems, loaded.checkpoint("plan-approval")), ([], "stop"))

    def test_delegate_applies_only_to_the_named_checkpoint(self):
        self.put({"version": 1, "checkpoints": {"plan-approval": "delegate", "other": "stop"}})
        loaded = settings.load(self.store)
        self.assertEqual(loaded.problems, [])
        self.assertEqual(loaded.checkpoint("plan-approval"), "delegate")
        self.assertEqual(loaded.checkpoint("other"), "stop")
        self.assertEqual(loaded.checkpoint("third"), "stop")

    def test_a_name_that_is_not_text_reads_as_stop(self):
        self.put({"version": 1, "checkpoints": {"a": "delegate"}})
        loaded = settings.load(self.store)
        for name in (["a"], {"a": 1}, None, 5, b"a", ("a",)):
            with self.subTest(name=name):
                self.assertEqual(loaded.checkpoint(name), "stop")

    def test_a_hostile_value_reads_as_stop(self):
        bad = ["DELEGATE", "Delegate", "allow", "", None, True, 1, ["delegate"],
               {"delegate": 1}, "delegate "]
        for value in bad:
            with self.subTest(value=value):
                self.put({"version": 1, "checkpoints": {"plan-approval": value, "ok": "delegate"}})
                loaded = settings.load(self.store)
                self.assertEqual(loaded.checkpoint("plan-approval"), "stop")
                self.assertEqual(loaded.checkpoint("ok"), "delegate")
                self.assertEqual(len(loaded.problems), 1)

    def test_an_invalid_checkpoint_name_is_reported_and_ignored(self):
        self.put({"version": 1, "checkpoints": {"Bad Name": "delegate", "x" * 65: "delegate"}})
        loaded = settings.load(self.store)
        self.assertEqual(loaded.checkpoints, {})
        self.assertEqual(len(loaded.problems), 2)

    def test_the_wrong_shape_makes_everything_stop(self):
        for document in ({"version": 1, "checkpoints": []}, {"version": 1, "checkpoints": "delegate"},
                         {"version": 2, "checkpoints": {"a": "delegate"}},
                         {"checkpoints": {"a": "delegate"}},
                         {"version": True, "checkpoints": {"a": "delegate"}},
                         {"version": "1", "checkpoints": {"a": "delegate"}}):
            with self.subTest(document=document):
                self.put(document)
                loaded = settings.load(self.store)
                self.assertEqual(loaded.checkpoint("a"), "stop")
                self.assertTrue(loaded.problems)

    def test_other_bad_documents_make_everything_stop(self):
        for data in (b"[]", b"null", b"", b"\xff\xfe", b'{"version": 1, "version": 1}',
                     b'{"version": 1.0}', b'{"version": NaN}', b'{"a": "\\ud800"}',
                     b"x" * (2 * 1024 * 1024)):
            with self.subTest(data=data[:20]):
                self.put(data)
                loaded = settings.load(self.store)
                self.assertEqual(loaded.checkpoint("a"), "stop")
                self.assertTrue(loaded.problems)

    def test_an_unknown_entry_is_reported_escaped_and_ignored(self):
        self.put({"version": 1, "checkpoints": {"a": "delegate"}, "evil\x1b[31m": 1})
        loaded = settings.load(self.store)
        self.assertEqual(loaded.checkpoint("a"), "delegate")
        self.assertEqual(len(loaded.problems), 1)
        self.assertNotIn("\x1b", loaded.problems[0])

    def test_an_unreadable_file_makes_everything_stop(self):
        self.put({"version": 1, "checkpoints": {"a": "delegate"}})
        os.chmod(os.path.join(self.root, "settings"), 0)
        self.addCleanup(os.chmod, os.path.join(self.root, "settings"), 0o600)
        if os.access(os.path.join(self.root, "settings"), os.R_OK):
            self.skipTest("this account can read a file with no permissions")
        loaded = settings.load(self.store)
        self.assertEqual(loaded.checkpoint("a"), "stop")
        self.assertIn("cannot be read", loaded.problems[0])


class FloorIsNotInTheFileTest(SettingsBase):
    # Structural, not behavioural: effective_stops takes nothing from the file, which
    # test_floor checks by its imports. These tests keep that true if a caller is added,
    # and check that the loaded settings expose no stops to be misused.
    def test_the_loaded_settings_expose_no_stops(self):
        settings.initialize(self.store)
        loaded = settings.load(self.store)
        self.assertEqual(set(loaded._fields), {"checkpoints", "problems"})
        self.assertFalse(any("stop" in name.lower() and name != "checkpoint"
                             for name in dir(loaded) if not name.startswith("_")))
        self.assertNotIn("floor", loaded.checkpoints)

    def test_damaging_or_emptying_the_floor_copy_changes_nothing(self):
        before = floor.effective_stops()
        for document in ({"version": 1, "floor": []}, {"version": 1}, {"version": 1, "floor": ["x"]},
                         {"version": 1, "floor": "none"}):
            with self.subTest(document=document):
                self.put(document)
                loaded = settings.load(self.store)
                self.assertEqual(loaded.problems, [])
                self.assertEqual(floor.effective_stops(), before)
                self.assertEqual(floor.effective_stops(), floor.FLOOR)

    def test_deleting_the_file_changes_nothing(self):
        settings.initialize(self.store)
        os.unlink(os.path.join(self.root, "settings"))
        self.assertEqual(floor.effective_stops(), floor.FLOOR)


class KindTest(SettingsBase):
    def test_absent_file_dir_and_link(self):
        self.assertIsNone(self.store.kind("settings"))
        self.assertIsNone(self.store.kind("packages/none/record"))
        self.assertEqual(self.store.kind("packages"), "dir")
        self.put({})
        self.assertEqual(self.store.kind("settings"), "file")
        os.symlink(self.base, os.path.join(self.root, "last"))
        self.assertEqual(self.store.kind("last"), "symlink")

    def test_a_link_on_the_way_is_refused_not_followed(self):
        with open(os.path.join(self.base, "secret"), "wb") as handle:
            handle.write(b"x")
        os.symlink(self.base, os.path.join(self.root, "packages", "link"))
        with self.assertRaises(safefs.SafeFsError):
            self.store.kind("packages/link/secret")

    def test_a_file_on_the_way_is_refused(self):
        self.put({})
        with self.assertRaises(safefs.SafeFsError):
            self.store.kind("settings/inside")

    def test_bad_paths_are_refused(self):
        for rel in ("", "../x", "/x", "a/../b", ".git"):
            with self.subTest(rel=rel):
                with self.assertRaises(safefs.SafeFsError):
                    self.store.kind(rel)


if __name__ == "__main__":
    unittest.main()
