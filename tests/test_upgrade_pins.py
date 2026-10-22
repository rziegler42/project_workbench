"""`wb upgrade` and `wb add` pin the helpers the confirmed modules declare, in the step the owner confirms."""

import hashlib
import io
import unittest.mock

from tests import test_upgrade
from tests import test_upgrade_preview as base_tests
from workbench import approvals, cli, pins

HARNESS = base_tests.HARNESS
HELPER, HELPER2 = b"#!/bin/sh\necho 1\n", b"#!/bin/sh\necho 2\n"
CHECK = b"print('x')\n"


def tool(helper=HELPER, extra=b"one\n"):
    return ({"ships": ["helper/tool", "checks/lint", "extra.txt"],
             "commands": {"tool": {"helper": "helper/tool", "arguments": ["go"]}},
             "checks": [{"helper": "checks/lint", "kit": 1}]},
            {"helper/tool": helper, "checks/lint": CHECK, "extra.txt": extra})


TOOL = ".workbench/p/tool/helper/tool"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Pins(test_upgrade.Upgrade):
    MODULES = {"h": (HARNESS, {}), "tool": tool()}

    def held(self):
        return pins.load(self.guarded, self.project_id)

    def forget(self):
        """The pins file of a project installed before the installer pinned anything."""
        self.guarded.write("projects/%s/pins" % self.project_id, pins.serialize({}))

    def run_add(self, *args):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["add", self.place] + list(args), out, err, store_root=self.store_root,
                        stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()


class Moves(Pins):
    def test_an_upgrade_that_changes_the_helper_moves_its_pin(self):
        new = self.ready(tool=tool(HELPER2))
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(HELPER2, self.read(TOOL))
        pin = self.held()["tool"]
        self.assertEqual((sha(HELPER2), "workbench upgrade", TOOL), (pin.sha256, pin.pinned_by, pin.path))
        self.assertEqual("workbench install", self.held()["lint"].pinned_by)

    def test_the_preview_lists_the_pin_it_will_move(self):
        new = self.ready(tool=tool(HELPER2))
        code, out, err = self.preview("--package", new)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("update pin tool: %s sha256 %s run directly (was %s sha256 %s, run directly, made by "
                      "workbench install)" % (TOOL, sha(HELPER2), TOOL, sha(HELPER)[:12]), out)
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)

    def test_an_upgrade_that_leaves_the_helper_alone_leaves_the_pin_alone(self):
        new = self.ready(tool=tool(extra=b"two\n"))
        before = self.held()
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(before, self.held())

    def test_a_helper_in_conflict_keeps_its_pin(self):
        new = self.ready(tool=tool(HELPER2))
        self.edit(TOOL, lambda data: data + b"# mine\n")
        self.acknowledge_file(TOOL)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(HELPER + b"# mine\n", self.read(TOOL))
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)

    def acknowledge_file(self, rel):
        baselines = self.baselines()
        baselines[rel] = sha(self.read(rel))
        self.guarded.write("projects/%s/baselines" % self.project_id,
                           base_tests.installplan.json_store({"baselines": baselines, "format": 1}))


class Replaces(Pins):
    def test_a_pin_the_owner_typed_for_another_path_is_a_listed_replacement(self):
        new = self.ready(tool=tool(HELPER2))
        pins.set_pin(self.guarded, self.project_id, "tool", "scripts/other", sha(b"x"), "owner")
        code, out, err = self.preview("--package", new)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("replace pin tool: %s sha256 %s run directly, declaration " % (TOOL, sha(HELPER2)), out)
        self.assertIn("(was scripts/other sha256 %s, run directly, declaration none, made by owner)"
                      % sha(b"x")[:12], out)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual((TOOL, "workbench upgrade"), (self.held()["tool"].path, self.held()["tool"].pinned_by))

    def test_the_replacement_is_in_the_digest(self):
        new = self.ready(tool=tool(HELPER2))

        def shown():
            code, out, err = self.upgrade("--package", new, answer="not the digest")
            self.assertEqual(1, code)
            return [line for line in out.splitlines() if line.startswith("digest: ")][0]

        plain = shown()
        pins.set_pin(self.guarded, self.project_id, "tool", "scripts/other", sha(b"x"), "owner")
        self.assertNotEqual(plain, shown())


class Creates(Pins):
    def test_a_project_installed_before_pinning_is_pinned_at_the_acknowledged_bytes(self):
        path = self.ready(tool=tool())
        self.forget()
        code, out, err = self.upgrade("--package", path)
        self.assertEqual((0, ""), (code, err), out)
        self.assertNotIn("nothing to change", out)
        held = self.held()
        self.assertEqual({"tool", "lint"}, set(held))
        self.assertEqual((sha(HELPER), "workbench upgrade"), (held["tool"].sha256, held["tool"].pinned_by))

    def test_a_helper_the_project_edited_and_acknowledged_is_not_pinned_by_an_unrelated_upgrade(self):
        path = self.ready(tool=tool())
        self.forget()
        self.edit(TOOL, lambda data: data + b"# pulled edit\n")
        baselines = self.baselines()
        baselines[TOOL] = sha(self.read(TOOL))
        self.guarded.write("projects/%s/baselines" % self.project_id,
                           base_tests.installplan.json_store({"baselines": baselines, "format": 1}))
        code, out, err = self.upgrade("--package", path)
        self.assertEqual((0, ""), (code, err), out)
        self.assertNotIn("tool", self.held())
        self.assertIn("lint", self.held())

    def test_a_second_upgrade_has_nothing_to_change(self):
        path = self.ready(tool=tool())
        self.forget()
        self.assertEqual(0, self.upgrade("--package", path)[0])
        code, out, err = self.upgrade("--package", path)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("nothing to change", out)

    def test_add_pins_the_helper_of_the_module_it_adds(self):
        self.MODULES = {"h": (HARNESS, {})}
        self.install(self.version())
        richer = self.version(tool=tool())
        self.approve(richer)
        self.warm(richer)
        code, out, err = self.run_add("--package", richer, "--select", "tool")
        self.assertEqual((0, ""), (code, err), out)
        held = self.held()
        self.assertEqual({"tool", "lint"}, set(held))
        self.assertEqual("workbench add", held["tool"].pinned_by)
        self.assertEqual(sha(self.read(TOOL)), held["tool"].sha256)


class Collides(Pins):
    def test_adding_a_module_that_declares_a_pin_name_an_installed_one_holds_is_refused(self):
        self.MODULES = {"h": (HARNESS, {}), "tool": tool()}
        self.install(self.version())
        richer = self.package("p", {"h": (HARNESS, {}), "tool": tool(), "tool2": tool(HELPER2)})
        self.approve(richer)
        self.warm(richer)
        before = self.held()
        code, out, err = self.run_add("--package", richer, "--select", "tool2")
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn("one pin name is used more than once", err)
        self.assertEqual(before, self.held())


class Refuses(Pins):
    def test_a_damaged_pins_file_refuses_the_upgrade_and_writes_nothing(self):
        new = self.ready(tool=tool(HELPER2))
        self.guarded.write("projects/%s/pins" % self.project_id, b"{not json")
        before = self.snapshot()
        code, out, err = self.upgrade("--package", new)
        self.assertEqual(1, code)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(before, self.snapshot())

    def test_a_clock_that_moves_between_the_two_builds_does_not_change_the_plan(self):
        new = self.ready(tool=tool(HELPER2))
        ticks = iter("2026-10-22T10:00:%02dZ" % n for n in range(60))
        with unittest.mock.patch.object(approvals, "utc_now", lambda: next(ticks)):
            code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(sha(HELPER2), self.held()["tool"].sha256)


if __name__ == "__main__":
    unittest.main()
