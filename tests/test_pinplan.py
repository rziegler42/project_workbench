"""The pins an install, add or upgrade implies, and how they differ from the pins that exist."""

import collections
import unittest

from workbench import declarations, pinplan, pins

Verified = collections.namedtuple("Verified", "type package name module declaration_hash")
Module = collections.namedtuple("Module", "commands checks")
NOW = "2026-10-22T10:00:00Z"
OLD = "2026-10-01T00:00:00Z"
A, B, D = "a" * 64, "b" * 64, "d" * 64
PATH = ".workbench/p/tool/helper/tool"


def module(commands=(), checks=()):
    return Module(tuple(commands), tuple(checks))


def verified(mod, kind="process", package="p", name="tool"):
    return Verified(kind, package, name, mod, D)


def command(name="tool", helper="helper/tool", runtime="exec", kit=None):
    return declarations.Command(name, helper, runtime, kit, ())


def held_pin(path=PATH, sha=A, kit=None, who="workbench install", declaration=D):
    return pins.Pin("tool", path, sha, who, OLD, kit, declaration)


class Wanted(unittest.TestCase):
    def test_a_command_is_pinned_under_its_name_and_a_check_under_its_last_segment(self):
        mod = module([command("tool")], [declarations.Check("checks/linter", 1)])
        found = pinplan.wanted([verified(mod)], lambda path: A)
        self.assertEqual([("tool", PATH, A, None, D),
                          ("linter", ".workbench/p/tool/checks/linter", A, 1, D)],
                         [tuple(w) for w in found])

    def test_only_a_python_command_has_a_kit(self):
        mod = module([command("a", "h/a", "python", 1), command("b", "h/b", "exec", None)])
        found = {w.name: w.kit for w in pinplan.wanted([verified(mod)], lambda path: A)}
        self.assertEqual({"a": 1, "b": None}, found)

    def test_a_helper_with_no_hash_is_left_out(self):
        self.assertEqual([], pinplan.wanted([verified(module([command()]))], lambda path: None))

    def test_a_harness_module_declares_nothing_that_is_pinned(self):
        self.assertEqual([], pinplan.wanted([verified(module([command()]), kind="harness")],
                                            lambda path: A))

    def test_a_module_with_no_helper_adds_no_pin(self):
        self.assertEqual([], pinplan.wanted([verified(module())], lambda path: A))


class Changes(unittest.TestCase):
    def make(self, held, written=(PATH,), sha=A, kit=None, path=PATH, declaration=D):
        want = [pinplan.Wanted("tool", path, sha, kit, declaration)]
        return pinplan.changes(held, want, "workbench upgrade", NOW, set(written))

    def test_an_absent_pin_is_created_even_for_a_helper_the_plan_does_not_write(self):
        made = self.make({}, written=())
        self.assertEqual([pinplan.CREATE], [c.action for c in made])
        self.assertEqual(("workbench upgrade", NOW), (made[0].pin.pinned_by, made[0].pin.time))

    def test_an_equal_pin_is_left_alone(self):
        self.assertEqual([], self.make({"tool": held_pin()}))

    def test_a_helper_the_plan_does_not_write_keeps_its_pin(self):
        self.assertEqual([], self.make({"tool": held_pin(sha=B)}, written=()))

    def test_a_helper_the_plan_writes_updates_the_pin_at_the_same_path(self):
        made = self.make({"tool": held_pin(sha=B)})
        self.assertEqual([pinplan.UPDATE], [c.action for c in made])
        self.assertEqual(A, made[0].pin.sha256)

    def test_a_pin_records_the_declaration_it_was_confirmed_with(self):
        made = self.make({})
        self.assertEqual(D, made[0].pin.declaration)

    def test_a_changed_declaration_alone_updates_the_pin_even_when_the_helper_is_not_written(self):
        made = self.make({"tool": held_pin(declaration=B)}, written=())
        self.assertEqual([pinplan.UPDATE], [c.action for c in made])
        self.assertEqual(D, made[0].pin.declaration)

    def test_a_pin_without_a_declaration_gains_one(self):
        made = self.make({"tool": held_pin(declaration=None)}, written=())
        self.assertEqual([pinplan.UPDATE], [c.action for c in made])

    def test_a_pin_the_owner_typed_for_another_path_is_a_listed_replacement(self):
        made = self.make({"tool": held_pin(path="scripts/other")})
        self.assertEqual([pinplan.REPLACE], [c.action for c in made])
        self.assertEqual("scripts/other", made[0].old.path)

    def test_a_changed_kit_for_the_same_bytes_is_updated_even_when_the_helper_is_not_written(self):
        made = self.make({"tool": held_pin(kit=None)}, written=(), kit=1)
        self.assertEqual([pinplan.UPDATE], [c.action for c in made])

    def test_a_pin_for_a_name_no_module_declares_any_more_is_not_touched(self):
        held = {"gone": pins.Pin("gone", "x/y", A, "owner", OLD, None)}
        self.assertEqual(held, pinplan.apply(held, []))

    def test_apply_keeps_the_other_pins_and_does_not_change_its_argument(self):
        other = pins.Pin("other", "x/y", B, "owner", OLD, None)
        held = {"other": other}
        result = pinplan.apply(held, self.make({}))
        self.assertEqual({"other", "tool"}, set(result))
        self.assertEqual({"other": other}, held)


class Shown(unittest.TestCase):
    def test_the_fields_leave_out_the_time_and_keep_the_old_pin(self):
        made = pinplan.changes({"tool": held_pin(path="scripts/other", who="me", declaration=None)},
                               [pinplan.Wanted("tool", PATH, A, 1, D)], "workbench add", NOW, {PATH})
        row = pinplan.fields(made)[0]
        self.assertNotIn("time", row)
        self.assertEqual("workbench add", row["pinned_by"])
        self.assertEqual({"path": "scripts/other", "sha256": A, "kit": None, "pinned_by": "me",
                          "declaration": None}, row["was"])
        self.assertEqual(D, row["declaration"])

    def test_a_replacement_is_listed_with_the_old_path_hash_and_maker(self):
        made = pinplan.changes({"tool": held_pin(path="scripts/other", who="me", declaration=None)},
                               [pinplan.Wanted("tool", PATH, B, None, D)], "workbench add", NOW, {PATH})
        text = "\n".join(pinplan.lines(made, str))
        self.assertIn("replace pin tool: " + PATH + " sha256 " + B + " run directly, declaration " + D[:12], text)
        self.assertIn("(was scripts/other sha256 " + A[:12] + ", run directly, declaration none, made by me)", text)


if __name__ == "__main__":
    unittest.main()
