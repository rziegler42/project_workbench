"""`wb acknowledge` moves the pin of a helper that was holding the bytes it accepts, and no other."""

import os
import unittest.mock

from tests import test_acknowledge
from tests.test_upgrade_pins import HARNESS, TOOL, sha, tool, HELPER
from workbench import approvals, pins, store


class Pinned(test_acknowledge.Acknowledge):
    MODULES = {"h": (HARNESS, {}), "tool": tool()}

    def held(self):
        return pins.load(self.guarded, self.project_id)

    def edited(self, text=b"# pulled\n"):
        self.installed_project()
        self.edit(TOOL, lambda data: data + text)
        return HELPER + text


class Moves(Pinned):
    def test_the_pin_that_held_the_accepted_bytes_moves_to_the_new_ones(self):
        data = self.edited()
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        pin = self.held()["tool"]
        self.assertEqual((sha(data), "workbench acknowledge", TOOL), (pin.sha256, pin.pinned_by, pin.path))
        self.assertIn("moves the pin tool: %s from sha256 %s to sha256 %s" % (TOOL, sha(HELPER)[:12], sha(data)[:12]), out)
        self.assertIn("and moves 1 pin, so the launcher runs the bytes now there", out)
        self.assertIn("acknowledged 1 paths and moved 1 pin; the project was not touched", out)

    def test_other_pins_are_untouched(self):
        self.edited()
        before = self.held()
        self.run_it()
        self.assertEqual(before["lint"], self.held()["lint"])

    def test_a_pin_the_owner_holds_at_other_bytes_is_not_moved(self):
        self.edited()
        pins.set_pin(self.guarded, self.project_id, "tool", TOOL, sha(b"older"), "owner")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(sha(b"older"), self.held()["tool"].sha256)
        self.assertNotIn("moves the pin", out)

    def test_a_pin_the_owner_typed_is_not_moved_even_when_it_holds_the_accepted_bytes(self):
        data = self.edited()
        pins.set_pin(self.guarded, self.project_id, "tool", TOOL, sha(HELPER), "owner")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)
        self.assertNotEqual(sha(data), self.held()["tool"].sha256)
        self.assertNotIn("moves the pin", out)

    def test_a_moved_pin_keeps_its_declaration(self):
        before = self.installed_project() or self.held()["tool"].declaration
        self.edit(TOOL, lambda data: data + b"# pulled\n")
        self.run_it()
        self.assertEqual(before, self.held()["tool"].declaration)
        self.assertIsNotNone(before)

    def test_a_pin_for_another_path_is_not_moved(self):
        self.edited()
        pins.set_pin(self.guarded, self.project_id, "tool", "scripts/other", sha(HELPER), "owner")
        self.run_it()
        self.assertEqual(("scripts/other", sha(HELPER)), (self.held()["tool"].path, self.held()["tool"].sha256))

    def test_a_removed_helper_leaves_its_pin_so_nothing_runs(self):
        self.installed_project()
        os.remove(os.path.join(self.place, *TOOL.split("/")))
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)

    def test_an_edit_to_a_file_with_no_pin_moves_nothing(self):
        self.installed_project()
        self.edit(".workbench/p/tool/extra.txt", lambda data: data + b"x")
        before = self.held()
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(before, self.held())
        self.assertIn("acknowledged 1 paths; the project was not touched", out)


class Confirmed(Pinned):
    def digest(self):
        code, out, err = self.run_it(answer="not the digest")
        self.assertEqual(1, code)
        return [line for line in out.splitlines() if line.startswith("digest: ")][-1]

    def test_the_move_is_in_the_digest(self):
        self.edited()
        with_move = self.digest()
        pins.set_pin(self.guarded, self.project_id, "tool", TOOL, sha(b"older"), "owner")
        self.assertNotEqual(with_move, self.digest())

    def test_a_clock_that_moves_between_the_two_reads_does_not_change_the_list(self):
        data = self.edited()
        ticks = iter("2026-10-22T10:00:%02dZ" % n for n in range(60))
        with unittest.mock.patch.object(approvals, "utc_now", lambda: next(ticks)):
            code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(sha(data), self.held()["tool"].sha256)

    def test_a_damaged_pins_file_refuses_and_writes_nothing(self):
        self.edited()
        self.guarded.write("projects/%s/pins" % self.project_id, b"{not json")
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual(1, code)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(before, self.snapshot())

    def test_a_stop_after_the_baselines_says_the_pins_may_not_have_moved(self):
        data = self.edited()
        real = store.Store.write

        def refuse(this, rel, payload, *rest, **named):
            if rel.endswith("/pins"):
                raise OSError("disk full")
            return real(this, rel, payload, *rest, **named)

        with unittest.mock.patch.object(store.Store, "write", refuse):
            code, out, err = self.run_it()
        self.assertEqual(3, code, (out, err))
        self.assertIn("the baselines or the pins may have been replaced", err)
        self.assertEqual(sha(HELPER), self.held()["tool"].sha256)
        self.assertEqual(sha(data), self.baselines()[TOOL])


if __name__ == "__main__":
    unittest.main()
