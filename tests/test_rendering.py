"""Rendering of the levels table into the harness's permission rules, and the record attach keeps of it.

Plan ``2026-10-26-command-permission-levels``, increment E (``docs/specs/command-permissions.md``, "Rendering").
A key whose command is owner-run is denied at ``block`` and ``delegated``, asked at ``ask`` and open at ``none``; the
guarded store's deny and the floor's ask rules never change. No key offers ``ask`` or ``none`` yet, so the tests offer
them to a few keys through the registry's table of offers."""

import hashlib
import json
import os
import unittest
import unittest.mock

from tests import test_attach
from workbench import levels, rendering, rules, settings

SETTINGS_FILE = ".fixture/settings.local.json"


class Rendered(test_attach.Base):
    OFFERS = {"wb pin": ("ask", "none"), "wb recover": ("ask", "none"), "approve-plan": ("delegated", "ask")}

    def setUp(self):
        super().setUp()
        offers = unittest.mock.patch.dict(levels._OFFERS, self.OFFERS)
        offers.start()
        self.addCleanup(offers.stop)

    def table(self, **levels_table):
        document = {"version": 2, "checkpoints": {}, "floor": [], "levels": {
            key.replace("_", " "): level for key, level in levels_table.items()}}
        self.guarded.write("settings", json.dumps(document).encode())

    def attached(self, **levels_table):
        self.ready()
        self.table(**levels_table)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def permissions(self):
        return json.loads(self.read(SETTINGS_FILE))["permissions"]

    def record(self):
        rel = rendering.RECORD % self.project_id
        return json.loads(self.guarded.read(rel))

    def levels_now(self):
        return rendering.table_of(self.guarded, (), ())

    def level(self, key, table=None):
        table = table if table is not None else self.levels_now()
        return rendering.effective_level(self.guarded, self.project_id, self.place, table, key)


class RulesTest(Rendered):
    def test_a_key_at_block_is_denied_in_both_forms_and_not_asked(self):
        self.attached()
        permissions = self.permissions()
        for rule in ("Bash(wb pin)", "Bash(wb pin *)"):
            self.assertIn(rule, permissions["deny"])
            self.assertNotIn(rule, permissions["ask"])

    def test_a_key_at_ask_is_asked_and_not_denied_and_so_is_the_stores_own_wb(self):
        self.attached(wb_pin="ask")
        permissions = self.permissions()
        store = os.path.realpath(self.store_root)
        for rule in ("Bash(wb pin)", "Bash(wb pin *)", "Bash(%s/bin/wb pin)" % store, "Bash(%s/bin/wb pin *)" % store):
            self.assertIn(rule, permissions["ask"], rule)
            self.assertNotIn(rule, permissions["deny"], rule)

    def test_a_key_at_none_has_neither_rule(self):
        self.attached(wb_pin="none")
        permissions = self.permissions()
        for rule in ("Bash(wb pin)", "Bash(wb pin *)"):
            self.assertNotIn(rule, permissions["deny"])
            self.assertNotIn(rule, permissions["ask"])

    def test_delegated_keeps_the_deny(self):
        self.ready()
        self.guarded.write("settings", json.dumps({"version": 2, "levels": {"approve-plan": "delegated"}}).encode())
        self.assertEqual(0, self.attach()[0])
        self.assertIn("Bash(wb approve-plan)", self.permissions()["deny"])

    def test_nothing_else_changes_whatever_the_table_says(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        plain = self.permissions()
        os.unlink(os.path.join(self.place, SETTINGS_FILE))
        os.unlink(os.path.join(self.place, ".workbench", "local", "harness.json"))
        self.table(wb_pin="ask", wb_recover="none")
        self.assertEqual(0, self.attach()[0])
        changed = self.permissions()
        store = os.path.realpath(self.store_root).lstrip("/")
        self.assertIn("Edit(//%s/**)" % store, changed["deny"])
        self.assertIn("Bash(git push --force*)", changed["ask"])
        self.assertIn("Bash(wb install)", changed["deny"])
        self.assertEqual(sorted(set(plain["deny"]) - set(changed["deny"])),
                         sorted(r for r in plain["deny"] if " pin" in r or " recover" in r))
        self.assertNotIn("allow", self.permissions())


class RecordTest(Rendered):
    def test_attach_writes_a_record_of_what_it_rendered(self):
        self.attached(wb_pin="ask", wb_recover="none")
        record = self.record()
        data = self.read(SETTINGS_FILE)
        self.assertEqual(1, record["format"])
        self.assertTrue(record["permissions"])
        self.assertEqual("fixture", record["harness"])
        self.assertEqual(SETTINGS_FILE, record["file"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), record["file_hash"])
        self.assertEqual(rendering.digest(self.levels_now()), record["table_digest"])
        self.assertEqual("ask", record["keys"]["wb pin"])
        self.assertEqual("none", record["keys"]["wb recover"])
        self.assertEqual("deny", record["keys"]["wb install"])

    def test_the_record_lists_every_key_of_the_registry(self):
        self.attached()
        self.assertEqual(sorted(levels.registry()), sorted(self.record()["keys"]))

    def test_a_key_whose_command_is_not_matched_is_recorded_as_unruled(self):
        self.ready()
        self.table()
        built = rendering.plan({"accept-decision": "block", "wb pin": "block"})
        self.assertEqual("unruled", built.keys["accept-decision"])
        self.assertEqual("deny", built.keys["wb pin"])

    def test_the_record_is_in_the_guarded_store_and_not_in_the_project(self):
        self.attached()
        self.assertEqual("file", self.guarded.kind(rendering.RECORD % self.project_id))
        self.assertFalse([path for path in self.content() if path.endswith("rendering")])


class EffectiveLevelTest(Rendered):
    def test_ask_and_none_hold_when_the_record_and_the_file_match(self):
        self.attached(wb_pin="ask", wb_recover="none")
        self.assertEqual("ask", self.level("wb pin"))
        self.assertEqual("none", self.level("wb recover"))

    def test_block_and_delegated_do_not_depend_on_the_record(self):
        self.attached()
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.assertEqual("block", self.level("wb pin"))
        self.assertEqual("delegated", rendering.effective_level(
            self.guarded, self.project_id, self.place, {"approve-plan": "delegated"}, "approve-plan"))

    def test_no_record_reads_as_block(self):
        self.ready()
        self.table(wb_pin="ask")
        self.assertEqual("block", self.level("wb pin"))

    def test_a_damaged_record_reads_as_block(self):
        self.attached(wb_pin="ask")
        for data in (b"{", b"[]", b"null", b'{"format": 2}', b'{"format": 1}', b"\xff"):
            with self.subTest(data=data):
                self.guarded.write(rendering.RECORD % self.project_id, data)
                self.assertEqual("block", self.level("wb pin"))

    def test_a_record_with_a_key_deleted_reads_that_key_as_block(self):
        self.attached(wb_pin="ask", wb_recover="ask")
        record = self.record()
        del record["keys"]["wb pin"]
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))
        self.assertEqual("ask", self.level("wb recover"))

    def test_a_record_that_says_the_wrong_rule_reads_as_block(self):
        self.attached(wb_pin="ask", wb_recover="none")
        record = self.record()
        record["keys"]["wb pin"] = "deny"
        record["keys"]["wb recover"] = "ask"
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))
        self.assertEqual("block", self.level("wb recover"))

    def test_a_table_changed_since_attach_reads_as_block(self):
        self.attached(wb_pin="ask")
        self.table(wb_pin="ask", wb_recover="ask")
        self.assertEqual("block", self.level("wb pin"))

    def test_a_harness_file_edited_after_attach_reads_ask_and_none_as_block(self):
        self.attached(wb_pin="ask", wb_recover="none")
        with open(os.path.join(self.place, SETTINGS_FILE), "ab") as handle:
            handle.write(b" ")
        self.assertEqual("block", self.level("wb pin"))
        self.assertEqual("block", self.level("wb recover"))

    def test_a_removed_harness_file_reads_as_block(self):
        self.attached(wb_pin="ask")
        os.unlink(os.path.join(self.place, SETTINGS_FILE))
        self.assertEqual("block", self.level("wb pin"))

    def test_a_harness_without_permissions_reads_as_block(self):
        self.attached(wb_pin="ask")
        record = self.record()
        record["permissions"] = False
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))

    def test_another_harness_reads_as_block(self):
        self.attached(wb_pin="ask")
        record = self.record()
        record["harness"] = "other/harness"
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))

    def test_a_record_with_no_local_manifest_reads_as_block(self):
        self.attached(wb_pin="ask")
        os.unlink(os.path.join(self.place, ".workbench", "local", "harness.json"))
        self.assertEqual("block", self.level("wb pin"))

    def test_a_symbolic_link_in_place_of_the_harness_file_reads_as_block(self):
        self.attached(wb_pin="ask")
        full = os.path.join(self.place, SETTINGS_FILE)
        with open(full, "rb") as handle:
            data = handle.read()
        os.unlink(full)
        copy = os.path.join(self.outside, "copy")
        with open(copy, "wb") as handle:
            handle.write(data)
        os.symlink(copy, full)
        self.assertEqual("block", self.level("wb pin"))

    def test_a_failure_after_the_record_leaves_the_keys_at_block(self):
        self.ready()
        self.table(wb_pin="ask")
        from workbench import projectfs
        with unittest.mock.patch.object(projectfs.Writer, "create_file", side_effect=OSError("disk full")):
            code, out, err = self.attach()
        self.assertEqual(3, code, err)
        self.assertIsNotNone(rendering.read(self.guarded, self.project_id))
        self.assertEqual("block", self.level("wb pin"))

    def test_with_no_levels_table_the_rendered_rules_are_the_old_ones(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        permissions = self.permissions()
        for pattern in rules.owner_run_patterns():
            self.assertIn("Bash(%s)" % pattern, permissions["deny"])
        self.assertEqual([], [rule for rule in permissions["ask"] if "wb " in rule and "/bin/wb" in rule])

    def test_an_unknown_key_or_level_reads_as_block(self):
        self.attached(wb_pin="ask")
        self.assertEqual("block", self.level("wb nothing"))
        self.assertEqual("block", rendering.effective_level(self.guarded, self.project_id, self.place,
                                                           {"wb pin": "allow"}, "wb pin"))


class DriftTest(Rendered):
    def check(self):
        import io
        from workbench import cli
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist)
        return code, out.getvalue() + err.getvalue()

    def test_check_is_quiet_about_a_file_that_matches_the_record(self):
        self.attached(wb_pin="ask")
        code, text = self.check()
        self.assertNotIn("rendering record", text)

    def test_check_reports_a_harness_file_that_differs_from_the_record(self):
        self.attached(wb_pin="ask")
        with open(os.path.join(self.place, SETTINGS_FILE), "ab") as handle:
            handle.write(b" ")
        code, text = self.check()
        self.assertEqual(1, code, text)
        self.assertIn("differs from the rendering record", text)


if __name__ == "__main__":
    unittest.main()
