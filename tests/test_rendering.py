"""Rendering of the levels table into the harness's permission rules, and the record attach keeps of it.

Plan ``2026-10-26-command-permission-levels``, increment E (``docs/specs/command-permissions.md``, "Rendering").
A key whose command is owner-run is denied at ``block`` and ``delegated``, asked at ``ask`` and open at ``none``; the
guarded store's deny and the floor's ask rules never change. No key offers ``ask`` or ``none`` yet, so the tests offer
them to a few keys through the registry's table of offers."""

import hashlib
import json
import os
import shutil
import unittest
import unittest.mock

from tests import support_harness, test_attach
from workbench import harnessplan, levels, rendering, rules, settings

SETTINGS_FILE = ".fixture/settings.local.json"


class Rendered(test_attach.Base):
    OFFERS = {"wb pin": ("ask", "none"), "wb recover": ("ask", "none"), "approve-plan": ("delegated", "ask")}

    LAYOUT = None

    def setUp(self):
        super().setUp()
        offers = unittest.mock.patch.dict(levels._OFFERS, self.OFFERS)
        offers.start()
        self.addCleanup(offers.stop)
        # By default the harness describes the command gate, so a relaxed key can be rendered.
        shutil.rmtree(self.dist)
        self.dist = support_harness.distribution(
            os.path.join(self.root, "distribution"), layout=self.LAYOUT or support_harness.gated_layout(),
            provides=support_harness.GATED_PROVIDES)

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
        # Only the wb spellings of the relaxed keys leave the deny list; the interpreter spellings stay denied.
        self.assertEqual(sorted(set(plain["deny"]) - set(changed["deny"])),
                         sorted(r for r in plain["deny"] if r.startswith(("Bash(wb pin", "Bash(wb recover"))))
        self.assertNotIn("allow", self.permissions())


class RecordTest(Rendered):
    def test_attach_writes_a_record_of_what_it_rendered(self):
        self.attached(wb_pin="ask", wb_recover="none")
        record = self.record()
        data = self.read(SETTINGS_FILE)
        self.assertEqual(2, record["format"])
        self.assertTrue(record["gate"])
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

    def test_check_is_quiet_about_a_shared_settings_file_created_later_when_no_key_is_relaxed(self):
        self.attached()
        with open(os.path.join(self.place, ".fixture", "settings.json"), "w") as handle:
            handle.write("{}\n")
        code, text = self.check()
        self.assertNotIn("rendering record", text)

    def test_check_reports_a_shared_settings_file_created_later_when_a_key_is_relaxed(self):
        self.attached(wb_pin="ask")
        with open(os.path.join(self.place, ".fixture", "settings.json"), "w") as handle:
            handle.write("{}\n")
        code, text = self.check()
        self.assertEqual(1, code, text)
        self.assertIn(".fixture/settings.json: was created after the rendering record", text)

    def test_check_says_when_a_relaxed_key_has_no_gate(self):
        self.ready()
        os.makedirs(os.path.join(self.place, ".fixture"), exist_ok=True)
        os.mkdir(os.path.join(self.place, ".fixture", "settings.json"))
        self.table(wb_pin="ask")
        self.assertEqual(0, self.attach()[0])
        code, text = self.check()
        self.assertEqual(1, code, text)
        self.assertIn("rendered at ask or none but no command gate was recorded", text)

    def test_check_reports_a_harness_file_that_differs_from_the_record(self):
        self.attached(wb_pin="ask")
        with open(os.path.join(self.place, SETTINGS_FILE), "ab") as handle:
            handle.write(b" ")
        code, text = self.check()
        self.assertEqual(1, code, text)
        self.assertIn("differs from the rendering record", text)


class GateTest(Rendered):
    def hooks(self):
        return json.loads(self.read(SETTINGS_FILE)).get("hooks")

    def test_no_gate_is_rendered_when_no_key_is_relaxed(self):
        self.attached()
        self.assertIsNone(self.hooks())
        self.assertFalse(self.record()["gate"])

    def test_a_relaxed_key_renders_the_bash_hook_and_the_record_says_so(self):
        self.attached(wb_pin="ask")
        entry, = self.hooks()["PreToolUse"]
        self.assertEqual("Bash", entry["matcher"])
        self.assertEqual([{"type": "command", "command": "wb gate-command fixture || exit 2", "timeout": 60}],
                         entry["hooks"])
        self.assertTrue(self.record()["gate"])

    def test_none_renders_the_gate_too(self):
        self.attached(wb_recover="none")
        self.assertTrue(self.record()["gate"])
        self.assertEqual(1, len(self.hooks()["PreToolUse"]))

    def test_the_ask_rule_names_the_wb_forms_only_and_the_interpreter_forms_stay_denied(self):
        self.attached(wb_pin="ask")
        permissions = self.permissions()
        store = os.path.realpath(self.store_root)
        for rule in ("Bash(wb pin)", "Bash(wb pin *)", "Bash(%s/bin/wb pin)" % store):
            self.assertIn(rule, permissions["ask"], rule)
        for spelling in ("python3 -m workbench", "python3 -B -m workbench", "python -m workbench"):
            for rule in ("Bash(%s pin)" % spelling, "Bash(%s pin *)" % spelling):
                self.assertIn(rule, permissions["deny"], rule)
                self.assertNotIn(rule, permissions["ask"], rule)

    def test_a_harness_that_cannot_describe_the_gate_keeps_the_keys_denied(self):
        shutil.rmtree(self.dist)
        self.dist = support_harness.distribution(os.path.join(self.root, "distribution"))
        self.attached(wb_pin="ask", wb_recover="none")
        permissions = self.permissions()
        self.assertIn("Bash(wb pin)", permissions["deny"])
        self.assertIn("Bash(wb recover)", permissions["deny"])
        self.assertNotIn("hooks", json.loads(self.read(SETTINGS_FILE)))
        self.assertFalse(self.record()["gate"])
        self.assertEqual("block", self.level("wb pin"))
        self.assertEqual("deny", self.record()["keys"]["wb pin"])

    def test_both_settings_files_are_protected_when_the_gate_is_rendered(self):
        self.attached(wb_pin="ask")
        deny = self.permissions()["deny"]
        for path in (".fixture/settings.local.json", ".fixture/settings.json"):
            self.assertIn("Edit(%s)" % path, deny)
            self.assertIn("Edit(%s)" % ("**/" + path), deny)
            self.assertIn("Edit(//%s/%s)" % (os.path.realpath(self.place).lstrip("/"), path), deny)

    def test_the_settings_files_are_not_protected_when_no_hook_is_rendered(self):
        self.attached()
        self.assertNotIn("Edit(.fixture/settings.json)", self.permissions()["deny"])

    def test_the_record_hashes_the_shared_settings_file(self):
        self.attached(wb_pin="ask")
        self.assertEqual({"path": ".fixture/settings.json", "hash": None}, self.record()["shared"])

    def test_both_hooks_share_the_event_when_both_are_rendered(self):
        layout = support_harness.gated_layout()
        data = harnessplan.render_permissions(
            [], layout, os.path.realpath(self.store_root), os.path.realpath(self.home), hook_for="fixture",
            command_gate_for="fixture", root=os.path.realpath(self.place))
        entries = json.loads(data)["hooks"]["PreToolUse"]
        self.assertEqual(["Edit", "Bash"], [entry["matcher"] for entry in entries])


class GateCommandTest(Rendered):
    """``wb gate-command <harness>`` as the rendered hook runs it, in an attached project."""

    def gate(self, command, harness="fixture", cwd=None, tool="Bash", field="command"):
        import io
        from workbench import cli
        payload = {"cwd": cwd or os.path.realpath(self.place), "tool_name": tool, "tool_input": {field: command}}
        err = io.StringIO()
        previous = os.getcwd()
        os.chdir(os.path.realpath(self.place))
        try:
            code = cli.main(["gate-command", harness], io.StringIO(), err, store_root=self.store_root,
                            distribution=self.dist, stdin=io.StringIO(json.dumps(payload)))
        finally:
            os.chdir(previous)
        return code, err.getvalue()

    def test_a_relaxed_key_blocks_a_wrapper_and_allows_the_exact_form(self):
        self.attached(wb_pin="ask")
        self.assertEqual((0, ""), self.gate("wb check"))
        self.assertEqual((0, ""), self.gate("wb pin docs/plans/a.md"))
        code, err = self.gate("bash -c 'wb pin docs/plans/a.md'")
        self.assertEqual(2, code)
        self.assertTrue(err.startswith("refused: "), err)

    def test_with_every_key_at_block_nothing_is_stopped(self):
        self.attached()
        self.assertEqual((0, ""), self.gate("bash -c 'wb pin x'"))

    def test_a_table_set_back_to_block_after_attach_still_guards_what_was_rendered(self):
        """The harness file keeps the ask rule and no deny until it is attached again (review finding F2)."""
        self.attached(wb_pin="ask")
        self.table()
        code, err = self.gate("bash -c 'wb pin x'")
        self.assertEqual(2, code, err)
        self.assertEqual((0, ""), self.gate("wb check"))

    def test_a_key_relaxed_in_the_table_after_attach_is_guarded_too(self):
        self.attached(wb_pin="ask")
        self.table(wb_pin="ask", wb_recover="ask")
        self.assertEqual(2, self.gate("bash -c 'wb recover x'")[0])
        self.assertEqual(2, self.gate("bash -c 'wb pin x'")[0])

    def test_an_unknown_harness_a_wrong_tool_and_a_wrong_field_are_blocks(self):
        self.attached(wb_pin="ask")
        self.assertEqual(2, self.gate("wb check", harness="nobody")[0])
        self.assertEqual(2, self.gate("wb check", tool="Write")[0])
        self.assertEqual(2, self.gate("wb check", field="cmd")[0])

    def test_a_gate_that_could_not_be_recorded_still_guards_what_was_rendered(self):
        """The shared path was unreadable at attach, so the record says no gate; the file still holds the hook and the ask rule."""
        self.ready()
        os.makedirs(os.path.join(self.place, ".fixture"), exist_ok=True)
        os.mkdir(os.path.join(self.place, ".fixture", "settings.json"))
        self.table(wb_pin="ask")
        self.assertEqual(0, self.attach()[0])
        self.table()
        self.assertEqual(2, self.gate("bash -c 'wb pin x'")[0])

    def test_a_directory_that_is_no_project_is_a_block(self):
        self.attached(wb_pin="ask")
        self.assertEqual(2, self.gate("wb check", cwd=self.outside)[0])

    def test_the_command_is_agent_safe_and_not_owner_run(self):
        self.assertIn("gate-command", rules.AGENT_SAFE)
        self.assertNotIn("gate-command", rules.OWNER_RUN)


class GateEffectiveLevelTest(Rendered):
    def test_a_symbolic_link_or_a_directory_at_the_shared_path_reads_as_block(self):
        """Absent at attach is not the same as unreadable later (review finding F3)."""
        self.attached(wb_pin="ask")
        self.assertEqual("ask", self.level("wb pin"))
        shared = os.path.join(self.place, ".fixture", "settings.json")
        target = os.path.join(self.outside, "elsewhere.json")
        with open(target, "w") as handle:
            handle.write("{}\n")
        os.symlink(target, shared)
        self.assertEqual("block", self.level("wb pin"))
        os.unlink(shared)
        self.assertEqual("ask", self.level("wb pin"))
        os.mkdir(shared)
        self.assertEqual("block", self.level("wb pin"))

    def test_a_shared_path_that_cannot_be_read_at_attach_does_not_render_the_gate(self):
        self.ready()
        os.makedirs(os.path.join(self.place, ".fixture"), exist_ok=True)
        os.mkdir(os.path.join(self.place, ".fixture", "settings.json"))
        self.table(wb_pin="ask")
        self.assertEqual(0, self.attach()[0])
        self.assertFalse(self.record()["gate"])
        self.assertEqual("block", self.level("wb pin"))

    def test_a_record_without_the_gate_reads_as_block(self):
        self.attached(wb_pin="ask")
        record = self.record()
        record["gate"] = False
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))

    def test_a_record_with_no_gate_field_is_damaged_and_reads_as_block(self):
        self.attached(wb_pin="ask")
        record = self.record()
        del record["gate"]
        self.guarded.write(rendering.RECORD % self.project_id, json.dumps(record).encode())
        self.assertEqual("block", self.level("wb pin"))

    def test_a_shared_settings_file_created_after_attach_reads_as_block(self):
        self.attached(wb_pin="ask")
        self.assertEqual("ask", self.level("wb pin"))
        with open(os.path.join(self.place, ".fixture", "settings.json"), "w") as handle:
            handle.write('{"disableAllHooks": true}\n')
        self.assertEqual("block", self.level("wb pin"))

    def test_a_shared_settings_file_that_was_there_at_attach_and_changed_reads_as_block(self):
        self.ready()
        os.makedirs(os.path.join(self.place, ".fixture"), exist_ok=True)
        path = os.path.join(self.place, ".fixture", "settings.json")
        with open(path, "w") as handle:
            handle.write("{}\n")
        self.table(wb_pin="ask")
        self.assertEqual(0, self.attach()[0])
        self.assertIsNotNone(self.record()["shared"]["hash"])
        self.assertEqual("ask", self.level("wb pin"))
        with open(path, "w") as handle:
            handle.write('{"disableAllHooks": true}\n')
        self.assertEqual("block", self.level("wb pin"))

    def test_the_settings_file_edited_to_remove_the_hook_reads_as_block(self):
        self.attached(wb_pin="ask")
        document = json.loads(self.read(SETTINGS_FILE))
        del document["hooks"]
        with open(os.path.join(self.place, SETTINGS_FILE), "w") as handle:
            json.dump(document, handle)
        self.assertEqual("block", self.level("wb pin"))


if __name__ == "__main__":
    unittest.main()
