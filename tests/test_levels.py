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
# The keys the agent-safe actions give (plan 2026-10-27-a-level-for-every-command, increment A).
AGENT_KEYS = ("wb verify", "wb preview install", "wb preview adopt", "wb preview upgrade", "wb preview add",
              "wb launch", "wb check", "wb plan-status", "wb settings")
# Agent-safe words that are not a key: the hook entry points, the words that only dispatch to an action, and an
# action that reaches another action's key.
NOT_KEYS = ("gate", "agent-gate", "gate-command", "preview", "run", "delegate-approve-plan")
# Owner-run commands that reach declared checkpoints: their keys are those checkpoints' names, not a command spelling.
CHECKPOINTED = ("acknowledge", "approve-plan")


class RegistryTest(unittest.TestCase):
    def test_the_keys_are_the_owner_run_and_the_agent_safe_ones_listed(self):
        self.assertEqual(sorted(OWNER_RUN_KEYS + AGENT_KEYS), sorted(levels.registry()))

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


class AgentSafeKeysTest(unittest.TestCase):
    def test_every_agent_safe_action_has_a_key_unless_it_is_one_of_the_named_exceptions(self):
        keys = levels.registry()
        for command in rules.AGENT_SAFE:
            with self.subTest(command=command):
                if command in NOT_KEYS:
                    self.assertNotIn("wb " + command, keys)
                else:
                    self.assertIn("wb " + command, keys)

    def test_the_named_exceptions_are_exactly_the_hook_entry_points_the_dispatchers_and_the_delegated_route(self):
        self.assertEqual(set(NOT_KEYS), set(rules.HOOK_ENTRY_POINTS) | set(rules.DISPATCHERS)
                         | set(rules.REACHES_ANOTHER_KEY))
        self.assertEqual({"gate", "agent-gate", "gate-command"}, set(rules.HOOK_ENTRY_POINTS))
        self.assertEqual({"preview", "run"}, set(rules.DISPATCHERS))
        self.assertEqual({"delegate-approve-plan": "approve-plan"}, dict(rules.REACHES_ANOTHER_KEY))

    def test_a_dispatcher_word_is_not_a_key_and_each_preview_action_is(self):
        keys = levels.registry()
        self.assertNotIn("wb preview", keys)
        self.assertNotIn("wb run", keys)
        for action in ("install", "adopt", "upgrade", "add"):
            self.assertIn("wb preview " + action, keys)

    def test_the_delegated_route_has_no_key_of_its_own_and_reaches_the_approve_plan_key(self):
        self.assertNotIn("wb delegate-approve-plan", levels.registry(checkpoints=("approve-plan",)))
        self.assertIn(rules.REACHES_ANOTHER_KEY["delegate-approve-plan"], levels.registry(checkpoints=("approve-plan",)))

    def test_no_action_reaches_two_keys(self):
        names = list(levels.registry(checkpoints=("approve-plan",), commands=(("t", ("a",), ("a", "b")),)))
        self.assertEqual(len(names), len(set(names)))

    def test_an_agent_safe_key_defaults_to_none_and_offers_block_and_none(self):
        keys = levels.registry()
        for name in AGENT_KEYS:
            with self.subTest(key=name):
                self.assertEqual("none", keys[name].default)
                self.assertEqual(("block", "none"), keys[name].offers)

    def test_an_owner_run_key_still_defaults_to_block(self):
        keys = levels.registry()
        for name in OWNER_RUN_KEYS:
            with self.subTest(key=name):
                self.assertEqual("block", keys[name].default)

    def test_the_hook_entry_points_are_not_keys_in_any_spelling(self):
        names = list(levels.registry(checkpoints=("approve-plan",), commands=(("t", ("a",), ("a", "b")),)))
        for word in rules.HOOK_ENTRY_POINTS:
            self.assertFalse([name for name in names if word in name.split()], word)

    def test_a_declared_argument_that_is_not_owner_run_is_a_key_defaulting_to_none(self):
        keys = levels.registry(commands=(("tool", ("go",), ("go", "look", "describe")),))
        self.assertEqual("block", keys["wb run tool go"].default)
        self.assertEqual("none", keys["wb run tool look"].default)
        self.assertEqual("none", keys["wb run tool describe"].default)
        self.assertEqual(("block", "none"), keys["wb run tool look"].offers)
        self.assertEqual(("block",), keys["wb run tool go"].offers)

    def test_two_arguments_of_one_name_are_refused(self):
        with self.assertRaises(levels.RegistryError):
            levels.registry(commands=(("t", (), ("x", "x")),))
        with self.assertRaises(levels.RegistryError):
            levels.registry(commands=(("t", (), ("x",)), ("t", ("x",))))

    def test_a_command_given_without_its_arguments_still_gives_its_owner_run_keys(self):
        keys = levels.registry(commands=(("tool", ("go", "stop")),))
        self.assertIn("wb run tool go", keys)
        self.assertIn("wb run tool stop", keys)

    def test_the_agent_keys_can_be_left_out_for_the_table_a_harness_renders(self):
        keys = levels.registry(agent=False)
        for name in AGENT_KEYS:
            self.assertNotIn(name, keys)
        self.assertEqual(sorted(OWNER_RUN_KEYS), sorted(keys))

    def test_leaving_the_agent_keys_out_leaves_out_the_arguments_that_are_not_owner_run_too(self):
        keys = levels.registry(commands=(("tool", ("go",), ("go", "look")),), agent=False)
        self.assertIn("wb run tool go", keys)
        self.assertNotIn("wb run tool look", keys)

    def test_the_preview_actions_are_the_ones_cli_routes(self):
        """`wb preview` dispatches to the actions ``cli._preview`` accepts; each must have a key."""
        import ast
        from workbench import cli
        with open(cli.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        accepted = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_preview":
                for part in ast.walk(node):
                    if (isinstance(part, ast.Compare) and "argv[1]" in ast.unparse(part.left)
                            and isinstance(part.comparators[0], ast.Tuple)):
                        accepted = tuple(item.value for item in part.comparators[0].elts)
        self.assertEqual(tuple(rules.PREVIEW_ACTIONS), accepted)

    def test_no_agent_safe_key_is_a_floor_action(self):
        for stop in floor.FLOOR:
            self.assertNotIn(stop.id, levels.registry())

    def test_every_key_name_is_a_valid_name_of_at_most_96_characters(self):
        from workbench import settings
        for name in levels.registry(commands=(("tool", ("go",), ("go", "look")),)):
            with self.subTest(key=name):
                self.assertLessEqual(len(name), settings.MAX_KEY)
                self.assertTrue(settings._KEY_RE.match(name))


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

    # The owner-run keys that offer ``none`` in this version; each increment of the plan ``2026-10-27-a-level-for-every-command``
    # adds the keys it builds.
    NONE_KEYS = ("approve-plan", "wb install", "wb adopt")

    def test_only_approve_plan_offers_ask_among_the_owner_run_keys(self):
        for name, key in self.keys().items():
            if name in AGENT_KEYS:
                continue
            with self.subTest(key=name):
                self.assertEqual(name == "approve-plan", "ask" in key.offers)

    def test_the_owner_run_keys_that_offer_none_are_those_built_so_far(self):
        for name, key in self.keys().items():
            if name in AGENT_KEYS:
                continue
            with self.subTest(key=name):
                self.assertEqual(name in self.NONE_KEYS, "none" in key.offers)

    def test_no_key_offers_ask_except_approve_plan(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertEqual(name == "approve-plan", "ask" in key.offers)

    def test_accept_decision_offers_block_only(self):
        self.assertEqual(("block",), self.keys()["accept-decision"].offers)

    def test_the_default_of_every_key_but_an_agent_safe_one_is_block(self):
        for name, key in self.keys().items():
            with self.subTest(key=name):
                self.assertEqual("none" if name in AGENT_KEYS else "block", key.default)


if __name__ == "__main__":
    unittest.main()
