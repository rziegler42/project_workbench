"""The registry of keys the personal settings' ``levels`` table may name (``docs/specs/command-permissions.md``).

Plan ``2026-10-26-command-permission-levels``, increment C. The registry is built from what the installer knows
(``rules.OWNER_RUN``, a process module's checkpoints and the owner-run arguments of installed commands), so no
module is named here."""

import unittest

from workbench import floor, levels, rules


# The keys the installer's own owner-run commands give. A new command in ``rules.OWNER_RUN`` fails
# ``test_the_owner_run_keys_are_the_ones_listed`` until it is listed here, so it cannot gain a key unseen.
OWNER_RUN_KEYS = ("wb install", "wb adopt", "wb upgrade", "wb add", "wb attach", "wb recover",
                  "wb approve", "wb pin", "wb release-approvals", "approve-plan")
# Owner-run commands that reach declared checkpoints: their keys are those checkpoints' names, not a command spelling.
CHECKPOINTED = ("acknowledge", "approve-plan")


class RegistryTest(unittest.TestCase):
    def test_the_owner_run_keys_are_the_ones_listed(self):
        self.assertEqual(sorted(OWNER_RUN_KEYS), sorted(levels.registry()))

    def test_every_owner_run_command_has_a_key_unless_a_checkpoint_names_it(self):
        keys = levels.registry()
        for command in rules.OWNER_RUN:
            with self.subTest(command=command):
                if command == "approve-plan":
                    self.assertIn("approve-plan", keys)
                elif command in CHECKPOINTED:
                    self.assertNotIn("wb " + command, keys)
                else:
                    self.assertIn("wb " + command, keys)

    def test_a_command_with_checkpoints_has_no_command_spelling_key(self):
        keys = levels.registry(checkpoints=("acknowledge-first-tier", "acknowledge-second-tier"))
        self.assertNotIn("wb acknowledge", keys)
        self.assertIn("acknowledge-first-tier", keys)

    def test_two_declarations_of_one_key_are_refused(self):
        with self.assertRaises(levels.RegistryError):
            levels.registry(commands=(("t", ("x",)), ("t", ("x",))))
        with self.assertRaises(levels.RegistryError):
            levels.registry(commands=(("t", ("x", "x")),))

    def test_approve_plan_is_one_key_named_as_its_checkpoint(self):
        keys = levels.registry(checkpoints=("approve-plan",))
        self.assertEqual(1, list(keys).count("approve-plan"))
        self.assertNotIn("wb approve-plan", keys)

    def test_every_declared_checkpoint_has_a_key_and_comes_first_in_declaration_order(self):
        keys = list(levels.registry(checkpoints=("zed", "ant", "approve-plan")))
        self.assertEqual(["zed", "ant", "approve-plan"], keys[:3])

    def test_an_owner_run_argument_of_a_module_command_is_a_key_in_the_wb_spelling(self):
        keys = levels.registry(commands=(("tool", ("go", "stop")), ("other", ())))
        self.assertIn("wb run tool go", keys)
        self.assertIn("wb run tool stop", keys)
        self.assertFalse([key for key in keys if key.startswith("wb run other")])

    def test_a_checkpoint_declared_twice_is_one_key(self):
        keys = levels.registry(checkpoints=("a", "a"))
        self.assertEqual(1, list(keys).count("a"))

    def test_no_floor_action_is_a_key(self):
        keys = levels.registry(checkpoints=("a",), commands=(("t", ("x",)),))
        for stop in floor.FLOOR:
            self.assertNotIn(stop.id, keys)

    def test_a_checkpoint_that_names_a_floor_action_is_not_a_key(self):
        keys = levels.registry(checkpoints=(floor.FLOOR[0].id,))
        self.assertNotIn(floor.FLOOR[0].id, keys)


class OfferedLevelsTest(unittest.TestCase):
    def keys(self):
        return levels.registry(checkpoints=("approve-plan", "accept-decision", "push-shared-branch"),
                               commands=(("tool", ("go",)),))

    def test_block_is_offered_by_every_key(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertIn("block", key.offers)

    def test_delegated_is_offered_only_to_approve_plan(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertEqual(name == "approve-plan", "delegated" in key.offers)

    def test_only_approve_plan_offers_ask_or_none(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertEqual(name == "approve-plan", "ask" in key.offers)
                self.assertEqual(name == "approve-plan", "none" in key.offers)

    def test_accept_decision_offers_block_only(self):
        self.assertEqual(("block",), self.keys()["accept-decision"].offers)

    def test_the_default_of_every_key_is_block(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertEqual("block", key.default)


if __name__ == "__main__":
    unittest.main()
