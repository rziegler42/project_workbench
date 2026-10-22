import json
import os
import tempfile
import unittest

import support
from workbench import declarations, floor, settings, store
from workbench.wbkit import safefs


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


class CapsTest(SettingsBase):
    CAPS = (declarations.Cap("review-rounds", 3, 5), declarations.Cap("same-failure-retries", 1, 2))

    def effective(self, document=None, checkpoints=("approve-plan",)):
        if document is not None:
            self.put(document)
        loaded = settings.load(self.store)
        return loaded, settings.effective(loaded, checkpoints, self.CAPS)

    def test_with_no_caps_every_default_applies(self):
        for document in (None, {"version": 1}, {"version": 1, "caps": {}}):
            with self.subTest(document=document):
                loaded, got = self.effective(document)
                self.assertEqual({"review-rounds": 3, "same-failure-retries": 1}, got.caps)
                self.assertEqual([], loaded.problems + got.notes)

    def test_a_version_1_file_without_caps_still_loads(self):
        self.put({"version": 1, "checkpoints": {"a": "delegate"}, "floor": []})
        loaded = settings.load(self.store)
        self.assertEqual("delegate", loaded.checkpoint("a"))
        self.assertEqual(({}, []), (dict(loaded.caps), loaded.problems))

    def test_a_valid_owner_value_is_effective(self):
        _, got = self.effective({"version": 1, "caps": {"review-rounds": 5, "same-failure-retries": 1}})
        self.assertEqual({"review-rounds": 5, "same-failure-retries": 1}, got.caps)
        self.assertEqual([], got.notes)
        _, got = self.effective({"version": 1, "caps": {"review-rounds": 1}})
        self.assertEqual(1, got.caps["review-rounds"])

    def test_a_value_out_of_range_uses_the_default_with_a_note(self):
        for value in (0, -1, 6, 2 ** 70):
            with self.subTest(value=value):
                loaded, got = self.effective({"version": 1, "caps": {"review-rounds": value}})
                self.assertEqual(3, got.caps["review-rounds"])
                self.assertEqual(1, len(got.notes))
                self.assertIn("review-rounds", got.notes[0])
                self.assertEqual([], loaded.problems)

    def test_a_value_of_the_wrong_type_uses_the_default_with_one_note(self):
        for value in (True, False, "3", None, [3], {"n": 3}):
            with self.subTest(value=value):
                loaded, got = self.effective({"version": 1, "caps": {"review-rounds": value}})
                self.assertEqual(3, got.caps["review-rounds"])
                self.assertEqual(1, len(loaded.problems + got.notes))
                self.assertIn("review-rounds", (loaded.problems + got.notes)[0])

    def test_a_fraction_makes_the_file_damaged_so_every_default_applies(self):
        loaded, got = self.effective(b'{"version": 1, "caps": {"review-rounds": 3.0}}')
        self.assertEqual({"review-rounds": 3, "same-failure-retries": 1}, got.caps)
        self.assertIn("damaged", loaded.problems[0])

    def test_an_undeclared_cap_is_ignored_with_a_note(self):
        loaded, got = self.effective({"version": 1, "caps": {"nonsense": 4, "review-rounds": 2}})
        self.assertEqual({"review-rounds": 2, "same-failure-retries": 1}, got.caps)
        self.assertEqual(1, len(got.notes))
        self.assertIn("nonsense", got.notes[0])

    def test_an_invalid_cap_name_is_reported_escaped_and_ignored(self):
        loaded, got = self.effective({"version": 1, "caps": {"Bad Name\x1b[31m": 2, "x" * 65: 2}})
        self.assertEqual(2, len(loaded.problems))
        self.assertTrue(all("\x1b" not in text for text in loaded.problems))
        self.assertEqual({"review-rounds": 3, "same-failure-retries": 1}, got.caps)

    def test_caps_that_are_not_an_object_use_every_default(self):
        for value in ([], "3", 3, None):
            with self.subTest(value=value):
                loaded, got = self.effective({"version": 1, "caps": value})
                self.assertEqual({"review-rounds": 3, "same-failure-retries": 1}, got.caps)
                self.assertEqual(1, len(loaded.problems))

    def test_a_damaged_file_uses_every_default_and_the_existing_note(self):
        for data in (b"{", b"[]", {"version": 2, "caps": {"review-rounds": 4}}):
            with self.subTest(data=data):
                loaded, got = self.effective(data)
                self.assertEqual({"review-rounds": 3, "same-failure-retries": 1}, got.caps)
                self.assertEqual("stop", got.checkpoints["approve-plan"])
                self.assertTrue(loaded.problems)

    def test_a_checkpoint_is_delegate_only_when_declared_and_set_exactly(self):
        document = {"version": 1, "checkpoints": {"approve-plan": "delegate", "other": "delegate"}}
        _, got = self.effective(document, checkpoints=("approve-plan", "push-shared-branch"))
        self.assertEqual({"approve-plan": "delegate", "push-shared-branch": "stop"}, got.checkpoints)
        self.assertEqual(1, len(got.notes))
        self.assertIn("other", got.notes[0])

    def test_a_stop_for_an_undeclared_checkpoint_is_noted_too(self):
        _, got = self.effective({"version": 1, "checkpoints": {"other": "stop"}})
        self.assertEqual({"approve-plan": "stop"}, got.checkpoints)
        self.assertEqual(1, len(got.notes))

    def test_the_seed_is_unchanged(self):
        settings.seed(self.store)
        self.assertEqual({"checkpoints": {}, "floor": [stop.id for stop in floor.FLOOR], "version": 1},
                         json.loads(self.raw()))


class FloorIsNotInTheFileTest(SettingsBase):
    # Structural, not behavioural: effective_stops takes nothing from the file, which
    # test_floor checks by its imports. These tests keep that true if a caller is added,
    # and check that the loaded settings expose no stops to be misused.
    def test_the_loaded_settings_expose_no_stops(self):
        settings.initialize(self.store)
        loaded = settings.load(self.store)
        self.assertEqual(set(loaded._fields), {"checkpoints", "problems", "caps"})
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
