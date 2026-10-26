import json
import os
import tempfile
import types
import unittest

import support
from workbench import declarations, floor, planapprovals, settings, store
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
                         {"version": 3, "checkpoints": {"a": "delegate"}},
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
        for data in (b"{", b"[]", {"version": 3, "caps": {"review-rounds": 4}}):
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


class LevelsTest(SettingsBase):
    """The ``levels`` table of a version 2 file (docs/specs/command-permissions.md, "The table")."""

    def effective(self, document=None, checkpoints=("approve-plan", "beta")):
        if document is not None:
            self.put(document)
        loaded = settings.load(self.store)
        return loaded, settings.effective(loaded, checkpoints, ())

    def declared(self, got):
        """The levels of the two checkpoints these tests declare."""
        return {name: got.levels[name] for name in ("approve-plan", "beta")}

    def test_every_known_key_reads_as_block_with_no_file_or_a_version_1_file(self):
        for document in (None, {"version": 1}):
            with self.subTest(document=document):
                _, got = self.effective(document)
                self.assertEqual({"block"}, set(got.levels.values()))
                self.assertIn("wb install", got.levels)

    def test_with_no_file_or_a_version_1_file_every_key_reads_as_block(self):
        for document in (None, {"version": 1}, {"version": 1, "checkpoints": {"approve-plan": "stop"}}):
            with self.subTest(document=document):
                loaded, got = self.effective(document)
                self.assertEqual({"approve-plan": "block", "beta": "block"}, self.declared(got))
                self.assertEqual([], loaded.problems + got.notes)

    def test_a_version_1_checkpoint_of_delegate_reads_as_delegated_for_approve_plan_only(self):
        _, got = self.effective({"version": 1, "checkpoints": {"approve-plan": "delegate", "beta": "delegate"}})
        self.assertEqual({"approve-plan": "delegated", "beta": "block"}, self.declared(got))
        self.assertEqual({"approve-plan": "delegate", "beta": "stop"}, got.checkpoints)

    def test_a_version_2_file_without_levels_loads(self):
        loaded, got = self.effective({"version": 2, "checkpoints": {"approve-plan": "delegate"}})
        self.assertEqual([], loaded.problems + got.notes)
        self.assertEqual("delegated", got.levels["approve-plan"])

    def test_block_is_read_in_a_version_2_table(self):
        loaded, got = self.effective({"version": 2, "levels": {"approve-plan": "block", "beta": "block"}})
        self.assertEqual(({"approve-plan": "block", "beta": "block"}, []), (self.declared(got), loaded.problems + got.notes))

    def test_delegated_in_the_table_is_read_for_approve_plan_and_makes_it_delegate(self):
        loaded, got = self.effective({"version": 2, "levels": {"approve-plan": "delegated"}})
        self.assertEqual([], loaded.problems + got.notes)
        self.assertEqual(("delegated", "delegate"), (got.levels["approve-plan"], got.checkpoints["approve-plan"]))

    def test_delegated_for_any_other_key_reads_as_block_with_a_note(self):
        _, got = self.effective({"version": 2, "levels": {"beta": "delegated"}})
        self.assertEqual(("block", "stop"), (got.levels["beta"], got.checkpoints["beta"]))
        self.assertEqual(1, len(got.notes))
        self.assertIn("beta", got.notes[0])

    def test_ask_and_none_are_read_but_not_offered_yet_so_they_read_as_block_with_a_note(self):
        for level in ("ask", "none"):
            with self.subTest(level=level):
                loaded, got = self.effective({"version": 2, "levels": {"approve-plan": level}})
                self.assertEqual([], loaded.problems)
                self.assertEqual(("block", "stop"), (got.levels["approve-plan"], got.checkpoints["approve-plan"]))
                self.assertEqual(1, len(got.notes))
                self.assertIn(level, got.notes[0])

    def test_a_value_that_is_not_one_of_the_four_levels_reads_as_block_with_a_note(self):
        bad = ["BLOCK", "Ask", "allow", "", None, True, 1, ["block"], {"block": 1}, "block "]
        for value in bad:
            with self.subTest(value=value):
                loaded, got = self.effective({"version": 2, "levels": {"approve-plan": value, "beta": "block"}})
                self.assertEqual("block", got.levels["approve-plan"])
                self.assertEqual(1, len(loaded.problems))
                self.assertIn("approve-plan", loaded.problems[0])

    def test_a_bad_value_does_not_unlock_a_delegate_checkpoint(self):
        loaded, got = self.effective({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                      "levels": {"approve-plan": "nonsense"}})
        self.assertEqual(("block", "stop"), (got.levels["approve-plan"], got.checkpoints["approve-plan"]))

    def test_levels_that_are_not_an_object_make_every_key_block(self):
        for value in ([], "block", None, 3):
            with self.subTest(value=value):
                loaded, got = self.effective({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                              "levels": value})
                self.assertEqual({"approve-plan": "block", "beta": "block"}, self.declared(got))
                self.assertEqual("stop", got.checkpoints["approve-plan"])
                self.assertEqual(1, len(loaded.problems))

    def test_a_duplicate_key_damages_the_file_so_every_key_blocks(self):
        for data in (b'{"version": 2, "levels": {"beta": "block", "beta": "block"}}',
                     b'{"version": 2, "checkpoints": {"approve-plan": "delegate"}, "levels": {}, "levels": {}}'):
            with self.subTest(data=data):
                loaded, got = self.effective(data)
                self.assertEqual({"approve-plan": "block", "beta": "block"}, self.declared(got))
                self.assertEqual("stop", got.checkpoints["approve-plan"])
                self.assertIn("damaged", loaded.problems[0])

    def test_a_damaged_file_and_an_unsupported_version_read_every_key_as_block(self):
        for data in (b"{ not json", {"version": 3, "levels": {"approve-plan": "delegated"}},
                     {"version": True, "levels": {"approve-plan": "delegated"}}):
            with self.subTest(data=data):
                loaded, got = self.effective(data)
                self.assertEqual({"approve-plan": "block", "beta": "block"}, self.declared(got))
                self.assertEqual("stop", got.checkpoints["approve-plan"])
                self.assertTrue(loaded.problems)

    def test_a_version_1_file_does_not_read_levels(self):
        loaded, got = self.effective({"version": 1, "levels": {"approve-plan": "delegated"}})
        self.assertEqual(("block", "stop"), (got.levels["approve-plan"], got.checkpoints["approve-plan"]))
        self.assertEqual(1, len(loaded.problems))
        self.assertIn("levels", loaded.problems[0])

    def test_a_key_in_both_takes_the_stricter_and_the_difference_is_noted(self):
        cases = (("delegate", "block", "block"), ("stop", "delegated", "block"), ("delegate", "delegated", "delegated"),
                 ("stop", "block", "block"))
        for checkpoint, level, want in cases:
            with self.subTest(checkpoint=checkpoint, level=level):
                loaded, got = self.effective({"version": 2, "checkpoints": {"approve-plan": checkpoint},
                                              "levels": {"approve-plan": level}})
                self.assertEqual(want, got.levels["approve-plan"])
                self.assertEqual("delegate" if want == "delegated" else "stop", got.checkpoints["approve-plan"])
                self.assertEqual([], loaded.problems)
                differs = {"delegate": "delegated", "stop": "block"}[checkpoint] != level
                self.assertEqual(1 if differs else 0, len(got.notes), got.notes)

    def test_a_key_that_is_not_known_is_noted_and_ignored(self):
        loaded, got = self.effective({"version": 2, "levels": {"nope": "block", "wb run tool nothing": "block"}})
        self.assertNotIn("nope", got.levels)
        self.assertEqual(2, len(got.notes))

    def test_a_key_that_is_not_a_valid_name_blocks_the_whole_table(self):
        for key in ("Approve-Plan", "approve-plan ", "approve plan\n", "", "x" * 200, "a\tb"):
            with self.subTest(key=key):
                loaded, got = self.effective({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                              "levels": {key: "block", "approve-plan": "delegated"}})
                self.assertEqual(self.declared(got), {"approve-plan": "block", "beta": "block"})
                self.assertEqual("stop", got.checkpoints["approve-plan"])
                self.assertEqual({"block"}, set(got.levels.values()))
                self.assertEqual(1, len(loaded.problems))

    def test_a_known_key_that_no_checkpoint_declares_has_a_level(self):
        loaded, got = self.effective({"version": 2, "levels": {"wb install": "block"}})
        self.assertEqual("block", got.levels["wb install"])
        self.assertEqual([], loaded.problems + got.notes)

    def test_an_owner_run_argument_of_an_installed_command_is_a_key(self):
        self.put({"version": 2, "levels": {"wb run tool go": "block", "wb run tool other": "block"}})
        loaded = settings.load(self.store)
        got = settings.effective(loaded, ("approve-plan",), (), commands=(("tool", ("go",)),))
        self.assertEqual("block", got.levels["wb run tool go"])
        self.assertEqual(1, len(got.notes))
        self.assertIn("wb run tool other", got.notes[0])

    def test_a_floor_action_cannot_be_named(self):
        for stop in floor.FLOOR:
            with self.subTest(stop=stop.id):
                loaded, got = self.effective({"version": 2, "levels": {stop.id: "none"}})
                self.assertEqual(1, len(loaded.problems))
                self.assertIn("floor", loaded.problems[0])
                self.assertNotIn(stop.id, got.levels)

    def test_a_level_a_key_does_not_offer_reads_as_block_with_a_note(self):
        for level in ("ask", "none", "delegated"):
            with self.subTest(level=level):
                loaded, got = self.effective({"version": 2, "levels": {"wb install": level}})
                self.assertEqual("block", got.levels["wb install"])
                self.assertEqual(1, len(got.notes))
                self.assertIn("wb install", got.notes[0])

    def test_an_invalid_key_is_reported_and_escaped(self):
        loaded, got = self.effective({"version": 2, "levels": {"Bad Key\x1b[31m": "block", "x" * 200: "block"}})
        self.assertEqual(2, len(loaded.problems))
        for text in loaded.problems:
            self.assertNotIn("\x1b", text)

    def test_a_key_with_a_trailing_newline_is_not_valid(self):
        loaded, _ = self.effective({"version": 2, "levels": {"approve-plan\n": "delegated"}})
        self.assertEqual(1, len(loaded.problems))

    def delegating(self, document):
        self.put(document)
        return planapprovals.delegating(self.store, types.SimpleNamespace(checkpoints=("approve-plan",)))

    def test_only_a_sound_delegated_reading_makes_the_plan_approval_delegate(self):
        self.assertTrue(self.delegating({"version": 1, "checkpoints": {"approve-plan": "delegate"}}))
        self.assertTrue(self.delegating({"version": 2, "levels": {"approve-plan": "delegated"}}))
        self.assertTrue(self.delegating({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                         "levels": {"approve-plan": "delegated"}}))
        for level in ("block", "ask", "none", "DELEGATED", "", None, True, ["delegated"]):
            with self.subTest(level=level):
                self.assertFalse(self.delegating({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                                  "levels": {"approve-plan": level}}))
        for levels in ([], "delegated", None):
            with self.subTest(levels=levels):
                self.assertFalse(self.delegating({"version": 2, "checkpoints": {"approve-plan": "delegate"},
                                                  "levels": levels}))

    def test_the_table_cannot_make_a_key_less_strict_than_its_default(self):
        for level in ("ask", "none", "delegated"):
            with self.subTest(level=level):
                _, got = self.effective({"version": 2, "levels": {"beta": level, "approve-plan": level}})
                self.assertEqual("block", got.levels["beta"])
                self.assertEqual("stop", got.checkpoints["beta"])


class FloorIsNotInTheFileTest(SettingsBase):
    # Structural, not behavioural: effective_stops takes nothing from the file, which
    # test_floor checks by its imports. These tests keep that true if a caller is added,
    # and check that the loaded settings expose no stops to be misused.
    def test_the_loaded_settings_expose_no_stops(self):
        settings.initialize(self.store)
        loaded = settings.load(self.store)
        self.assertEqual(set(loaded._fields), {"checkpoints", "problems", "caps", "levels", "levels_blocked"})
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
