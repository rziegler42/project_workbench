"""A command's owner-run argument as the command of a declared checkpoint: the ``checkpoint_of`` field, the key it gives, the
rules rendered for it, the command gate's reading and ``wb settings``. Increment C of the plan
``2026-10-29-accept-decision-at-ask``; the accepted record is ``2026-10-29-accept-decision-offers-the-ask-level``.

Everything here is synthetic: a module named `tool` with a command `run-it`, and the checkpoint `other-step` (or one nobody
declares). The installer names no module and no checkpoint of a real one."""

import copy
import io
import json
import unittest

from tests import support_project, test_settingscmd
from tests.support_project import HELPER_PATH, tool
from tests.test_command_gate import STORE_BIN, run as gate_run
from tests.test_declarations import dump, module
from workbench import command_gate, levels, rendering, settings
from workbench import declarations as d

ARGUMENTS = ["check", "show", "wipe", "reset"]
STEP = "other-step"
WIPE = "wb run run-it wipe"


def declared(**fields):
    base = {"helper": "scripts/run", "arguments": ARGUMENTS, "owner": ["wipe", "reset"],
            "levels": {"wipe": ["ask", "none"], "reset": ["none"]}, "preview": "show"}
    base.update(fields)
    return module(ships=["scripts"], commands={"run-it": base})


class Declaration(unittest.TestCase):
    def parse(self, decl):
        return d.parse_module(dump(decl), "sample", decl.get("name", "sample-notes"))

    def command(self, **fields):
        return self.parse(declared(**fields)).commands[0]

    def refused(self, **fields):
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(declared(**fields))
        self.assertEqual("commands", ctx.exception.rule)
        self.assertNotIn("unknown key", str(ctx.exception))  # refused for its value, not as a field nobody knows
        return str(ctx.exception)

    def test_a_command_without_the_field_maps_nothing(self):
        self.assertEqual((), self.command().checkpoint_of)
        self.assertEqual((), d.Command("c", "h", "exec", None, ("a",)).checkpoint_of)

    def test_the_mapping_is_read_in_the_order_written(self):
        got = self.command(checkpoint_of={"wipe": STEP, "reset": "third-step"})
        self.assertEqual((("wipe", STEP), ("reset", "third-step")), got.checkpoint_of)

    def test_an_empty_object_maps_nothing(self):
        self.assertEqual((), self.command(checkpoint_of={}).checkpoint_of)

    def test_an_argument_that_is_not_owner_run_is_refused(self):
        self.assertIn("check", self.refused(checkpoint_of={"check": STEP}))
        self.refused(checkpoint_of={"nowhere": STEP})

    def test_an_owner_run_argument_that_offers_no_level_is_refused(self):
        self.assertIn("keep", self.refused(owner=["wipe", "reset", "keep"], arguments=ARGUMENTS + ["keep"],
                                           checkpoint_of={"keep": STEP}))

    def test_a_name_that_is_not_the_form_of_a_checkpoint_is_refused(self):
        for bad in ("", "Step", "1step", "-step", "has space", "step_two", "a" * 65, "step\n", 3, None, True, ["x"]):
            with self.subTest(bad=bad):
                self.refused(checkpoint_of={"wipe": bad})

    def test_the_longest_name_is_accepted(self):
        name = "a" * 64
        self.assertEqual((("wipe", name),), self.command(checkpoint_of={"wipe": name}).checkpoint_of)

    def test_a_name_claimed_twice_is_refused(self):
        self.assertIn(STEP, self.refused(checkpoint_of={"wipe": STEP, "reset": STEP}))

    def test_a_value_that_is_not_an_object_is_refused(self):
        for bad in ([STEP], STEP, 3, None, True):
            with self.subTest(bad=bad):
                self.refused(checkpoint_of=bad)

    def test_the_field_is_part_of_the_declaration_hash(self):
        plain = copy.deepcopy(declared())
        marked = copy.deepcopy(declared(checkpoint_of={"wipe": STEP}))
        self.assertNotEqual(self.parse(plain).declaration, self.parse(marked).declaration)

    def test_a_declaration_without_the_field_is_the_declaration_as_written(self):
        got = self.parse(declared()).declaration
        self.assertNotIn(b"checkpoint_of", got if isinstance(got, bytes) else repr(got).encode())


def entry(checkpoint_of=(("wipe", STEP),), wanted=("ask", "none")):
    return ("run-it", ("wipe",), ("wipe", "show"), (("wipe", wanted),), checkpoint_of)


class Registry(unittest.TestCase):
    def keys(self, checkpoints=(STEP,), *entries):
        return levels.registry(checkpoints, list(entries) or [entry()])

    def test_with_a_process_module_that_declares_it_the_key_is_the_checkpoints(self):
        keys = self.keys()
        self.assertIn(STEP, keys)
        self.assertNotIn(WIPE, keys)
        self.assertEqual((levels.BLOCK, levels.ASK, levels.NONE), keys[STEP].offers)
        self.assertEqual(levels.BLOCK, keys[STEP].default)
        self.assertFalse(keys[STEP].agent)

    def test_without_a_process_module_that_declares_it_the_argument_keeps_its_own_key(self):
        keys = self.keys(())
        self.assertNotIn(STEP, keys)
        self.assertEqual((levels.BLOCK, levels.ASK, levels.NONE), keys[WIPE].offers)
        self.assertEqual(levels.BLOCK, keys[WIPE].default)

    def test_another_checkpoint_does_not_make_the_mapping_apply(self):
        keys = self.keys(("elsewhere",))
        self.assertNotIn(STEP, keys)
        self.assertIn(WIPE, keys)

    def test_the_mapped_argument_is_one_key_not_two(self):
        keys = self.keys()
        self.assertEqual(1, [name for name in keys].count(STEP))
        self.assertEqual([], [name for name in keys if name == WIPE])

    def test_the_preview_argument_keeps_its_own_agent_key(self):
        keys = self.keys()
        self.assertTrue(keys["wb run run-it show"].agent)

    def test_a_checkpoint_with_no_command_offers_what_it_offered_before(self):
        keys = levels.registry((STEP,), [("run-it", (), ("show",))])
        self.assertEqual((levels.BLOCK,), keys[STEP].offers)

    def test_the_levels_are_those_the_declaration_names(self):
        keys = levels.registry((STEP,), [entry(wanted=("none",))])
        self.assertEqual((levels.BLOCK, levels.NONE), keys[STEP].offers)
        keys = levels.registry((STEP,), [entry(wanted=("ask",))])
        self.assertEqual((levels.BLOCK, levels.ASK), keys[STEP].offers)

    def test_delegated_is_never_offered_by_the_mapping(self):
        for wanted in (("ask", "none"), ("none",), ("delegated",)):
            self.assertNotIn(levels.DELEGATED, levels.registry((STEP,), [entry(wanted=wanted)])[STEP].offers)

    def test_a_mapping_of_an_argument_that_is_not_owner_run_or_offers_no_level_is_ignored(self):
        keys = levels.registry((STEP,), [("run-it", (), ("wipe", "show"), (("wipe", ("ask",)),), (("wipe", STEP),))])
        self.assertEqual((levels.BLOCK,), keys[STEP].offers)
        keys = levels.registry((STEP,), [("run-it", ("wipe",), ("wipe", "show"), (), (("wipe", STEP),))])
        self.assertEqual((levels.BLOCK,), keys[STEP].offers)
        self.assertIn(WIPE, keys)

    def test_a_checkpoint_claimed_by_two_commands_is_refused(self):
        other = ("other", ("wipe",), ("wipe", "show"), (("wipe", ("ask",)),), (("wipe", STEP),))
        with self.assertRaises(levels.RegistryError) as ctx:
            levels.registry((STEP,), [entry(), other])
        self.assertIn(STEP, str(ctx.exception))

    def test_two_commands_claiming_it_without_a_process_module_do_not_collide(self):
        other = ("other", ("wipe",), ("wipe", "show"), (("wipe", ("ask",)),), (("wipe", STEP),))
        keys = levels.registry((), [entry(), other])
        self.assertIn(WIPE, keys)
        self.assertIn("wb run other wipe", keys)

    def test_an_entry_without_the_fifth_item_is_unchanged(self):
        plain = ("run-it", ("wipe",), ("wipe", "show"), (("wipe", ("ask", "none")),))
        keys = levels.registry((STEP,), [plain])
        self.assertEqual((levels.BLOCK,), keys[STEP].offers)
        self.assertEqual((levels.BLOCK, levels.ASK, levels.NONE), keys[WIPE].offers)

    def test_the_commands_of_the_checkpoints_that_apply(self):
        self.assertEqual({STEP: WIPE}, levels.checkpoint_commands((STEP,), [entry()]))
        self.assertEqual({}, levels.checkpoint_commands((), [entry()]))
        self.assertEqual({}, levels.checkpoint_commands((STEP,), [("run-it", ("wipe",), ("wipe", "show"))]))

    def test_the_key_that_offers_ask_for_the_accept_decision_checkpoint_lists_the_levels_in_order(self):
        keys = levels.registry(("accept-decision",), [entry((("wipe", "accept-decision"),))])
        self.assertEqual((levels.BLOCK, levels.ASK, levels.NONE), keys["accept-decision"].offers)
        keys = levels.registry(("accept-decision",), [("run-it", (), ("show",))])
        self.assertEqual((levels.BLOCK, levels.NONE), keys["accept-decision"].offers)


class Effective(unittest.TestCase):
    def table(self, entries, owner, checkpoints=(STEP,)):
        loaded = settings.Settings({}, [], {}, owner, False)
        return settings.effective(loaded, checkpoints, (), entries)

    def test_the_checkpoint_may_be_set_to_ask_and_to_none(self):
        for level in ("ask", "none", "block"):
            self.assertEqual(level, self.table([entry()], {STEP: level}).levels[STEP])

    def test_delegated_reads_block_with_a_note_that_it_is_not_offered(self):
        got = self.table([entry()], {STEP: "delegated"})
        self.assertEqual("block", got.levels[STEP])
        self.assertTrue(any(STEP in note and "not offered" in note for note in got.notes), got.notes)

    def test_without_the_mapping_the_checkpoint_offers_no_ask(self):
        got = self.table([("run-it", (), ("show",))], {STEP: "ask"})
        self.assertEqual("block", got.levels[STEP])
        self.assertTrue(any(STEP in note and "not offered" in note for note in got.notes), got.notes)

    def test_without_a_declaring_module_an_entry_for_the_checkpoint_is_noted_and_ignored(self):
        got = self.table([entry()], {STEP: "ask"}, checkpoints=())
        self.assertNotIn(STEP, got.levels)
        self.assertEqual("block", got.levels[WIPE])
        self.assertTrue(any(STEP in note and "does not know" in note for note in got.notes), got.notes)

    def test_without_a_declaring_module_the_argument_keeps_its_own_key_and_offers(self):
        got = self.table([entry()], {WIPE: "ask"}, checkpoints=())
        self.assertEqual("ask", got.levels[WIPE])


class Rendered(unittest.TestCase):
    def table(self, mapping=None, **levels_):
        return rendering.Table({key.replace("_", "-"): level for key, level in levels_.items()}, mapping or {STEP: WIPE})

    def test_a_plain_table_renders_as_before(self):
        built = rendering.plan({STEP: "ask"})
        self.assertEqual("unruled", built.keys[STEP])

    def test_the_checkpoint_at_ask_renders_an_ask_rule_for_the_arguments_spellings(self):
        built = rendering.plan(self.table(other_step="ask"))
        self.assertEqual("ask", built.keys[STEP])
        self.assertIn(WIPE, built.ask)
        self.assertIn(WIPE + " *", built.ask)
        self.assertTrue(all(pattern.startswith("wb ") for pattern in built.ask))

    def test_the_checkpoint_at_block_renders_a_deny_in_every_spelling(self):
        built = rendering.plan(self.table(other_step="block"))
        self.assertEqual("deny", built.keys[STEP])
        self.assertEqual([], built.ask)
        self.assertIn(WIPE, built.deny)
        self.assertTrue(any(not pattern.startswith("wb ") for pattern in built.deny))

    def test_the_checkpoint_at_none_renders_nothing_but_the_open_patterns(self):
        built = rendering.plan(self.table(other_step="none"))
        self.assertEqual("none", built.keys[STEP])
        self.assertEqual([], built.ask)
        self.assertEqual([], built.deny)
        self.assertIn(WIPE, built.open)

    def test_the_checkpoint_at_ask_is_denied_when_the_harness_cannot_gate(self):
        built = rendering.plan(self.table(other_step="ask"), gated=False)
        self.assertEqual("deny", built.keys[STEP])

    def test_the_patterns_are_those_of_the_arguments_own_key(self):
        own = rendering.plan({WIPE: "ask"})
        mapped = rendering.plan(self.table(other_step="ask"))
        self.assertEqual(own.ask, mapped.ask)
        self.assertEqual(own.open, mapped.open)

    def test_the_digest_of_a_table_with_no_mapping_is_that_of_its_plain_form(self):
        plain = {STEP: "ask"}
        self.assertEqual(rendering.digest(plain), rendering.digest(rendering.Table(plain)))

    def test_the_digest_says_which_argument_the_checkpoint_was_rendered_for(self):
        plain = rendering.digest({STEP: "ask"})
        mapped = rendering.digest(self.table(other_step="ask"))
        remapped = rendering.digest(self.table({STEP: "wb run run-it reset"}, other_step="ask"))
        self.assertEqual(3, len({plain, mapped, remapped}))

    def test_a_record_rendered_for_one_argument_reads_block_for_another(self):
        import hashlib
        built = rendering.Table({STEP: "ask"}, {STEP: WIPE})
        record = rendering.record_of("h", True, built, rendering.plan(built), "f", hashlib.sha256(b"x").hexdigest(), gate=True)
        other = rendering.Table({STEP: "ask"}, {STEP: "wb run run-it reset"})
        self.assertNotEqual(record["table_digest"], rendering.digest(other))


class Gate(unittest.TestCase):
    def table(self, level="ask"):
        return rendering.Table({STEP: level}, {STEP: WIPE})

    def go(self, command, level="ask"):
        table = self.table(level)
        return gate_run({"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": command}},
                        lambda cwd: ("Bash", "command", table, STORE_BIN))

    def test_the_exact_call_goes_ahead_at_ask(self):
        self.assertEqual((0, ""), self.go("wb run run-it wipe docs/decisions/x.md --digest " + "a" * 32))

    def test_a_wrapped_call_is_refused_at_ask(self):
        code, err = self.go("bash -c 'wb run run-it wipe x'")
        self.assertEqual(2, code)
        self.assertIn("refused", err)

    def test_a_spelling_by_expansion_is_refused_at_ask(self):
        code, _ = self.go("wb run run-it w${X}ipe x")
        self.assertEqual(2, code)

    def test_an_unrelated_call_goes_ahead(self):
        self.assertEqual((0, ""), self.go("wb check"))

    def test_at_block_the_gate_has_nothing_to_relax(self):
        self.assertEqual((0, ""), self.go("wb check", level="block"))

    def test_a_plain_table_still_names_no_command_for_the_checkpoint(self):
        code, err = gate_run({"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "bash -c 'wb run run-it wipe x'"}},
                             lambda cwd: ("Bash", "command", {STEP: "ask"}, STORE_BIN))
        self.assertEqual((0, ""), (code, err))


class ThroughTheInstalledModule(test_settingscmd.Settings):
    """The callers that read an installed module's commands pass the mapping on: `wb settings` and the effective table."""

    INSTALL = False

    def command(self, **fields):
        base = {"helper": HELPER_PATH, "arguments": ["show", "wipe"], "owner": ["wipe"], "levels": {"wipe": ["ask", "none"]},
                "preview": "show", "checkpoint_of": {"wipe": "beta"}}
        base.update(fields)
        return {"tool": base}

    def setup_module(self, **fields):
        mod, files = tool(self.command(**fields))
        mod.update(type="process", checkpoints=test_settingscmd.CHECKPOINTS, caps=test_settingscmd.CAPS)
        self.MODULES = dict(support_project.Project.MODULES, tool=(mod, files))
        self.ready()

    def lines(self, out):
        return {line.split(": ")[0]: line.split(": ")[1] for line in out.splitlines() if line.startswith("level ")}

    def test_the_declared_checkpoint_is_the_key_and_the_argument_has_none(self):
        self.setup_module()
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        found = self.lines(out)
        self.assertEqual("block", found["level beta"])
        self.assertNotIn("level wb run tool wipe", found)

    def test_ask_for_the_checkpoint_is_read_and_not_called_unoffered(self):
        self.setup_module()
        self.owner({"version": 2, "levels": {"beta": "ask"}})
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        self.assertEqual("ask", self.lines(out)["level beta"])
        self.assertNotIn("not offered", out)

    def test_delegated_for_the_checkpoint_reads_block_with_a_note(self):
        self.setup_module()
        self.owner({"version": 2, "levels": {"beta": "delegated"}})
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        self.assertEqual("block", self.lines(out)["level beta"])
        self.assertIn("not offered", out)

    def test_a_checkpoint_the_module_does_not_declare_leaves_the_argument_its_own_key(self):
        self.setup_module(checkpoint_of={"wipe": "gamma"})
        self.owner({"version": 2, "levels": {"gamma": "ask", "wb run tool wipe": "ask"}})
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        found = self.lines(out)
        self.assertNotIn("level gamma", found)
        self.assertEqual("ask", found["level wb run tool wipe"])
        self.assertIn("settings set a level for a key this version does not know: gamma", out)

    def test_the_table_the_harness_renders_holds_the_mapping(self):
        self.setup_module()
        self.owner({"version": 2, "levels": {"beta": "ask"}})
        table, _, _ = rendering.current_table(self.guarded, self.real)
        self.assertEqual("ask", table["beta"])
        self.assertNotIn("wb run tool wipe", table)
        self.assertEqual({"beta": "wb run tool wipe"}, table.command_of)

    def test_an_installed_module_without_the_field_gives_a_table_with_no_mapping(self):
        mod, files = tool({"tool": {"helper": HELPER_PATH, "arguments": ["show", "wipe"], "owner": ["wipe"]}})
        mod.update(type="process", checkpoints=test_settingscmd.CHECKPOINTS, caps=test_settingscmd.CAPS)
        self.MODULES = dict(support_project.Project.MODULES, tool=(mod, files))
        self.ready()
        table, _, _ = rendering.current_table(self.guarded, self.real)
        self.assertEqual({}, table.command_of)


if __name__ == "__main__":
    unittest.main()
