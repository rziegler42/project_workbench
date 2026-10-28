"""The levels an owner-run argument of a module's command offers: the ``levels`` and ``preview`` fields of a command, the
keys they give, and the rule rendered for them. Increment C of the plan dated 2026-10-27 that gives the review workflow
levels; the decision is ``2026-10-27-owner-run-arguments-take-a-level``.

Everything here is synthetic: a module named `tool` with a command `tool`. The installer knows no module."""

import copy
import unittest

from tests import support_project, test_settingscmd
from tests.support_project import HELPER_PATH, tool
from tests.test_declarations import dump, module
from workbench import declarations as d
from workbench import levels, rendering

ARGUMENTS = ["check", "show", "wipe", "reset"]


def declared(**fields):
    base = {"helper": "scripts/run", "arguments": ARGUMENTS, "owner": ["wipe", "reset"]}
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

    def test_a_command_without_the_fields_offers_nothing_beyond_block(self):
        got = self.command()
        self.assertEqual((), got.levels)
        self.assertIsNone(got.preview)

    def test_a_command_built_without_the_fields_has_none(self):
        got = d.Command("c", "h", "exec", None, ("a",))
        self.assertEqual((), got.levels)
        self.assertIsNone(got.preview)

    def test_levels_and_a_preview_are_read(self):
        got = self.command(levels={"wipe": ["ask", "none"], "reset": ["ask"]}, preview="show")
        self.assertEqual((("wipe", ("ask", "none")), ("reset", ("ask",))), got.levels)
        self.assertEqual("show", got.preview)

    def test_none_alone_needs_no_preview(self):
        got = self.command(levels={"wipe": ["none"]})
        self.assertEqual((("wipe", ("none",)),), got.levels)
        self.assertIsNone(got.preview)

    def test_ask_without_a_preview_is_refused(self):
        self.assertIn("preview", self.refused(levels={"wipe": ["ask"]}))

    def test_a_preview_without_ask_is_refused(self):
        self.refused(levels={"wipe": ["none"]}, preview="show")
        self.refused(preview="show")

    def test_the_preview_must_be_a_declared_argument_that_is_not_owner_run_or_describe(self):
        wanted = {"wipe": ["ask"]}
        self.refused(levels=wanted, preview="missing")
        self.refused(levels=wanted, preview="reset")
        self.refused(levels=wanted, preview="describe", arguments=ARGUMENTS + ["describe"])
        for bad in (3, None, ["show"], True):
            self.refused(levels=wanted, preview=bad)

    def test_a_level_other_than_ask_or_none_is_refused(self):
        for bad in ("delegated", "block", "maybe", "ASK", "", 3, None, ["ask"]):
            self.refused(levels={"wipe": [bad]}, preview="show")

    def test_delegated_is_named_in_the_refusal(self):
        self.assertIn("delegated", self.refused(levels={"wipe": ["delegated"]}, preview="show"))

    def test_a_repeated_level_is_refused(self):
        self.refused(levels={"wipe": ["ask", "ask"]}, preview="show")

    def test_an_empty_list_is_refused(self):
        self.refused(levels={"wipe": []})

    def test_a_key_that_is_not_an_owner_run_argument_is_refused(self):
        self.assertIn("check", self.refused(levels={"check": ["none"]}))
        self.refused(levels={"nowhere": ["none"]})

    def test_levels_on_a_command_with_no_owner_argument_is_refused(self):
        self.refused(owner=[], levels={"wipe": ["none"]})

    def test_levels_that_are_not_an_object_are_refused(self):
        for bad in (["wipe"], "wipe", 3, None, True, "none"):
            self.refused(levels=bad)

    def test_a_list_of_levels_that_is_not_a_list_is_refused(self):
        for bad in ("ask", {"ask": 1}, 3, None):
            self.refused(levels={"wipe": bad}, preview="show")

    def test_the_fields_are_part_of_the_declaration_hash(self):
        plain = copy.deepcopy(declared())
        marked = copy.deepcopy(declared(levels={"wipe": ["none"]}))
        self.assertNotEqual(self.parse(plain).declaration, self.parse(marked).declaration)

    def test_a_declaration_without_the_fields_is_the_declaration_as_written(self):
        # The hash covers the declaration as written (``declarations``, module docstring), so a command that gives neither
        # field has no trace of them in it.
        got = self.parse(declared()).declaration
        self.assertNotIn(b"levels", got if isinstance(got, bytes) else repr(got).encode())
        self.assertNotIn(b"preview", got if isinstance(got, bytes) else repr(got).encode())

    def test_a_hand_built_command_cannot_widen_the_offer(self):
        for bad in ("delegated", "block", "maybe"):
            keys = levels.registry(commands=[("t", ("go",), ("go",), (("go", (bad,)),))])
            self.assertEqual((levels.BLOCK,), keys["wb run t go"].offers)


class Keys(unittest.TestCase):
    def key(self, name, entry):
        return levels.registry(commands=[entry])[name]

    def test_an_argument_without_levels_offers_block_only(self):
        key = self.key("wb run tool wipe", ("tool", ("wipe",), ("wipe", "show")))
        self.assertEqual((levels.BLOCK,), key.offers)
        self.assertEqual(levels.BLOCK, key.default)

    def test_the_levels_a_declaration_names_are_offered_after_block(self):
        entry = ("tool", ("wipe", "reset"), ("wipe", "reset", "show"),
                 (("wipe", ("ask", "none")), ("reset", ("ask",))))
        keys = levels.registry(commands=[entry])
        self.assertEqual((levels.BLOCK, levels.ASK, levels.NONE), keys["wb run tool wipe"].offers)
        self.assertEqual((levels.BLOCK, levels.ASK), keys["wb run tool reset"].offers)

    def test_the_default_stays_block(self):
        entry = ("tool", ("wipe",), ("wipe", "show"), (("wipe", ("ask", "none")),))
        self.assertEqual(levels.BLOCK, self.key("wb run tool wipe", entry).default)

    def test_the_preview_argument_is_an_ordinary_key_that_defaults_to_none(self):
        entry = ("tool", ("wipe",), ("wipe", "show"), (("wipe", ("ask",)),))
        key = self.key("wb run tool show", entry)
        self.assertEqual(levels.NONE, key.default)
        self.assertTrue(key.agent)

    def test_a_level_for_an_argument_that_is_not_owner_run_is_not_offered(self):
        entry = ("tool", ("wipe",), ("wipe", "show"), (("show", ("ask",)),))
        self.assertEqual((levels.BLOCK, levels.NONE), self.key("wb run tool show", entry).offers)

    def test_the_table_may_set_an_offered_level_and_not_an_unoffered_one(self):
        from workbench import settings
        entry = ("tool", ("wipe", "reset"), ("wipe", "reset", "show"), (("wipe", ("ask",)),))
        loaded = settings.Settings({}, [], {}, {"wb run tool wipe": "ask", "wb run tool reset": "ask"}, False)
        got = settings.effective(loaded, (), (), [entry])
        self.assertEqual("ask", got.levels["wb run tool wipe"])
        self.assertEqual("block", got.levels["wb run tool reset"])
        self.assertTrue(any("wb run tool reset" in note and "not offered" in note for note in got.notes))


class Rendered(unittest.TestCase):
    def test_an_argument_at_ask_renders_an_ask_rule_for_the_wb_spelling_only(self):
        built = rendering.plan({"wb run tool wipe": "ask"})
        self.assertEqual("ask", built.keys["wb run tool wipe"])
        self.assertIn("wb run tool wipe", built.ask)
        self.assertIn("wb run tool wipe *", built.ask)
        self.assertTrue(all(pattern.startswith("wb ") for pattern in built.ask))

    def test_an_argument_at_block_renders_a_deny(self):
        built = rendering.plan({"wb run tool wipe": "block"})
        self.assertEqual("deny", built.keys["wb run tool wipe"])
        self.assertEqual([], built.ask)


class ThroughTheInstalledModule(test_settingscmd.Settings):
    """The callers that read an installed module's commands pass its ``levels`` on: `wb settings` and the effective table."""

    INSTALL = False
    COMMAND = {"tool": {"helper": HELPER_PATH, "arguments": ["show", "wipe"], "owner": ["wipe"],
                        "levels": {"wipe": ["ask"]}, "preview": "show"}}

    def setUp(self):
        test_settingscmd.Settings.setUp(self)
        module, files = tool(self.COMMAND)
        module.update(type="process", checkpoints=test_settingscmd.CHECKPOINTS, caps=test_settingscmd.CAPS)
        self.MODULES = dict(support_project.Project.MODULES, tool=(module, files))
        self.ready()

    def test_the_settings_command_accepts_ask_for_the_declared_argument(self):
        self.owner({"version": 2, "levels": {"wb run tool wipe": "ask"}})
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        self.assertIn("level wb run tool wipe: ask\n", out)
        self.assertNotIn("not offered", out)

    def test_without_an_entry_the_level_is_block(self):
        code, out, err = self.settings()
        self.assertEqual(0, code, err)
        self.assertIn("level wb run tool wipe: block\n", out)

    def test_the_effective_table_the_harness_renders_holds_it(self):
        self.owner({"version": 2, "levels": {"wb run tool wipe": "ask"}})
        table, _, _ = rendering.current_table(self.guarded, self.real)
        self.assertEqual("ask", table["wb run tool wipe"])


if __name__ == "__main__":
    unittest.main()
