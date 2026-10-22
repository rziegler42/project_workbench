"""`wb install` pins the helpers the confirmed modules declare, in the step the owner confirms."""

import hashlib
import io
import os
import unittest.mock

from tests.test_install import InstallBase, SEED, correct
from tests.test_preview import HARNESS
from workbench import approvals, manifest, pins, preview, projectfs, sources, store, target, unfinished

HELPER = b"#!/bin/sh\necho ran\n"
CHECK = b"print('x')\n"
TOOL = ({"ships": ["helper/tool", "checks/lint"],
         "commands": {"tool": {"helper": "helper/tool", "arguments": ["go"]}},
         "checks": [{"helper": "checks/lint", "kit": 1}]},
        {"helper/tool": HELPER, "checks/lint": CHECK})
PLAIN = ({"ships": ["scripts/run.sh"]}, {"scripts/run.sh": b"#!/bin/sh\n"})
PROJECT = manifest.project_id(SEED)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Pins(InstallBase):
    def setUp(self):
        InstallBase.setUp(self)
        self.path = self.package(modules={"h": (HARNESS, {}), "tool": TOOL, "plain": PLAIN})
        self.approve(self.path)

    def install_it(self, name="proj", reply=correct):
        place = self.place(name)
        code, out, err = self.run_install(place, self.path, reply=reply, seed=SEED,
                                          select=("h", "tool", "plain"))
        return place, code, out, err

    def held(self):
        return pins.load(self.guarded, PROJECT)


class Made(Pins):
    def test_a_command_and_a_check_are_pinned_with_the_declared_path_hash_and_kit(self):
        place, code, out, err = self.install_it()
        self.assertEqual(0, code, (out, err))
        held = self.held()
        self.assertEqual({"tool", "lint"}, set(held))
        self.assertEqual((".workbench/p/tool/helper/tool", sha(HELPER), None, "workbench install"),
                         (held["tool"].path, held["tool"].sha256, held["tool"].kit, held["tool"].pinned_by))
        self.assertEqual((".workbench/p/tool/checks/lint", sha(CHECK), 1),
                         (held["lint"].path, held["lint"].sha256, held["lint"].kit))
        for pin in held.values():
            self.assertEqual(pin.sha256, sha(self.read(place, *pin.path.split("/"))))

    def test_the_preview_lists_each_pin_and_the_pins_write(self):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(self.place(), [(self.path, None)], ["h", "tool", "plain"])
        self.assertEqual(0, preview.run(self.guarded, command, out, err, seed=SEED), err.getvalue())
        text = out.getvalue()
        self.assertIn("create pin tool: .workbench/p/tool/helper/tool sha256 " + sha(HELPER) + " run directly", text)
        self.assertIn("create pin lint: .workbench/p/tool/checks/lint sha256 " + sha(CHECK) + " kit 1", text)
        self.assertIn("write projects/%s/pins" % PROJECT, text)
        self.assertEqual({}, self.held())

    def test_a_module_with_no_helper_to_pin_writes_no_pins_file(self):
        place = self.place("only-plain")
        code, out, err = self.run_install(place, self.path, seed=SEED, select=("h", "plain"))
        self.assertEqual(0, code, (out, err))
        self.assertIsNone(self.guarded.kind("projects/%s/pins" % PROJECT))

    def test_a_clock_that_moves_between_the_two_builds_does_not_change_the_plan(self):
        ticks = iter("2026-10-22T10:00:%02dZ" % n for n in range(60))
        with unittest.mock.patch.object(approvals, "utc_now", lambda: next(ticks)):
            place, code, out, err = self.install_it()
        self.assertEqual(0, code, (out, err))
        self.assertEqual({"tool", "lint"}, set(self.held()))
        self.assertEqual(1, len({pin.time for pin in self.held().values()}))

    def test_what_is_pinned_runs_through_the_launcher_without_a_typed_pin(self):
        place, code, out, err = self.install_it()
        self.assertEqual(0, code, (out, err))
        for name in ("tool", "lint"):
            pin = pins.lookup(self.guarded, PROJECT, name)
            data = self.read(place, *pin.path.split("/"))
            self.assertEqual(pin.sha256, sha(data))


class Refused(Pins):
    def test_a_cancelled_install_pins_nothing(self):
        place, code, out, err = self.install_it(reply=lambda text: "no")
        self.assertEqual(1, code)
        self.assertEqual({}, self.held())

    def test_an_install_that_stops_before_the_pins_is_recorded_for_recovery(self):
        real = store.Store.write

        def refuse(this, rel, data, *rest, **named):
            if rel.endswith("/pins"):
                raise OSError("disk full")
            return real(this, rel, data, *rest, **named)

        with unittest.mock.patch.object(store.Store, "write", refuse):
            place, code, out, err = self.install_it()
        self.assertEqual(3, code, (out, err))
        with target.open_target(place, self.store_root, marked=True) as held:
            found = unfinished.examine(projectfs.Writer(held), self.store_root)
        stores = {item.path: item.state for item in found.items if item.kind == "store"}
        self.assertEqual("after", stores["projects/%s/baselines" % PROJECT])
        self.assertEqual("before", stores["projects/%s/pins" % PROJECT])
        self.assertEqual("partial", found.store)


if __name__ == "__main__":
    unittest.main()
