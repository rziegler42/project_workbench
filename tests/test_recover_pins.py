"""`wb recover` clears an upgrade or add that stopped between its two store writes, and nowhere else."""

import unittest
import unittest.mock

from tests import test_recover
from tests.test_upgrade_pins import HARNESS, HELPER2, TOOL, sha, tool
from workbench import pins, store, unfinished


def stop_at_the_pins():
    """Fail the write of the pins entry, which comes after the baselines."""
    real = store.Store.write

    def refuse(this, rel, data, *rest, **named):
        if rel.endswith("/pins"):
            raise OSError("disk full")
        return real(this, rel, data, *rest, **named)

    return unittest.mock.patch.object(store.Store, "write", refuse)


class Stopped(test_recover.UpgradeBase):
    MODULES = {"h": (HARNESS, {}), "tool": tool()}

    def stopped(self):
        new = self.ready(tool=tool(HELPER2))
        with stop_at_the_pins():
            code, out, err = self.upgrade("--package", new)
        self.assertEqual(3, code, (out, err))
        return new, err

    def held(self):
        return pins.load(self.guarded, self.project_id)


class Clears(Stopped):
    def test_the_failure_report_names_a_step_that_works(self):
        new, err = self.stopped()
        self.assertIn("`wb recover`", err)
        self.assertIn("`wb pin`", err)

    def test_files_and_baselines_written_with_the_old_pins_clear_and_say_to_pin(self):
        self.stopped()
        examined = unfinished.parse(test_recover.marker_bytes(self.place))
        self.assertEqual("upgrade", examined.command)
        code, out, err = test_recover.run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("it still holds the old pins", out)
        self.assertIn("`wb pin`", out)
        self.assertNotIn("run `wb acknowledge` to accept", out)
        self.assertFalse(self.marker())

    def test_the_launcher_still_refuses_the_replaced_helper_and_the_pin_is_not_made_for_the_owner(self):
        self.stopped()
        test_recover.run_recover(self, self.place)
        self.assertEqual(sha(tool()[1]["helper/tool"]), self.held()["tool"].sha256)
        self.assertEqual(HELPER2, self.read(TOOL))
        self.assertNotEqual(self.held()["tool"].sha256, sha(self.read(TOOL)))
        code, out, err = self.upgrade("--package", self.version(tool=tool(HELPER2)))
        self.assertEqual(0, code, err)
        self.assertEqual(sha(tool()[1]["helper/tool"]), self.held()["tool"].sha256)

    def test_an_entry_that_holds_other_content_is_refused(self):
        self.stopped()
        self.guarded.write("projects/%s/pins" % self.project_id, b"{not json")
        self.refused(self.place, "holds other content")
        self.assertTrue(self.marker())

    def test_an_add_that_stopped_the_same_way_is_cleared(self):
        self.MODULES = {"h": (HARNESS, {})}
        self.install(self.version())
        richer = self.version(tool=tool())
        self.approve(richer)
        self.warm(richer)
        out, err = test_recover.io.StringIO(), test_recover.io.StringIO()

        class Ask(test_recover.io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        with stop_at_the_pins():
            code = test_recover.cli.main(["add", self.place, "--package", richer, "--select", "tool"],
                                         out, err, store_root=self.store_root, stdin=Ask(""))
        self.assertEqual(3, code, (out.getvalue(), err.getvalue()))
        code, out, err = test_recover.run_recover(self, self.place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertFalse(self.marker())


class Judged(unittest.TestCase):
    """`judge` on made-up examinations: which mixes of old and new store entries it accepts."""

    def examination(self, command, files, states):
        record = unfinished.parse(unfinished.build(
            command, "a" * 64, "0.1.0", [("docs/a.md", "create", None, "b" * 64)], [], (),
            [("projects/x/" + name, None, "c" * 64) for name in states]))
        items = tuple(unfinished.Item("store", "projects/x/" + name, state, "")
                      for name, state in states.items())
        summary = "all" if set(states.values()) == {"after"} else (
            "none" if set(states.values()) == {"before"} else "partial")
        return unfinished.Examination(record, "", items, files, summary)

    def judged(self, command, files, **states):
        return test_recover.recover.judge(self.examination(command, files, states))[0]

    def test_a_mix_of_old_and_new_is_cleared_for_an_upgrade_and_an_add(self):
        for command in ("upgrade", "add"):
            for states in ({"baselines": "after", "pins": "before"}, {"baselines": "before", "pins": "after"}):
                self.assertEqual("partial", self.judged(command, "after", **states), (command, states))

    def test_an_install_in_the_same_state_is_refused(self):
        self.assertIsNone(self.judged("install", "after", baselines="after", pins="before"))

    def test_an_entry_that_holds_other_content_is_refused(self):
        self.assertIsNone(self.judged("upgrade", "after", baselines="after", pins="other"))

    def test_a_record_with_no_store_item_is_no_evidence_of_a_mix(self):
        found = self.examination("upgrade", "after", {"baselines": "after", "pins": "before"})
        bare = found._replace(items=())
        self.assertIsNone(test_recover.recover.judge(bare)[0])

    def test_files_that_are_not_all_written_are_refused(self):
        for files in ("mixed", "before"):
            self.assertIsNone(self.judged("upgrade", files, baselines="after", pins="before"))

    def test_the_two_clean_states_are_unchanged(self):
        self.assertEqual("before", self.judged("upgrade", "before", baselines="before", pins="before"))
        self.assertEqual("after", self.judged("upgrade", "after", baselines="after", pins="after"))


if __name__ == "__main__":
    unittest.main()
