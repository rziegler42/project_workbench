"""`extend`, `reset` and `archive`: the bound, the window and the close (checklist items 9 and 10 of
`docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment E. No bridge is called.

The declaration lists these as owner-run, so the installer denies the agent them; here they are run in-process
as the owner would run them."""

import json
import os
import re
import shutil
import unittest

import support_review
from support_review import PLAN, decision_entry, key_of, round_entry

TIME = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"


class Extend(support_review.Review):
    def test_it_raises_the_bound_by_the_number_and_keeps_the_window(self):
        self.reviewed()
        got = self.document("extend", PLAN, "2")
        self.assertEqual(5, got["bound"])
        self.assertEqual({"first": 1, "bound": 5}, self.state()["window"])

    def test_it_never_passes_the_ceiling_of_five(self):
        self.reviewed()
        self.refused("extend", PLAN, "3", contains="ceiling of 5")
        self.document("extend", PLAN, "1")
        self.document("extend", PLAN, "1")
        self.refused("extend", PLAN, "1", contains="ceiling of 5")
        self.assertEqual(5, self.state()["window"]["bound"])

    def test_a_number_that_is_not_from_one_to_five_is_refused(self):
        self.reviewed()
        for number in ("0", "6", "-1", "1.5", "x", "", "01", "1 ", "١", "10"):
            self.refused("extend", PLAN, number, contains="1 to 5")
        self.assertEqual(3, self.state()["window"]["bound"])

    def test_it_takes_exactly_a_document_and_a_number(self):
        self.reviewed()
        for argv in (["extend"], ["extend", PLAN], ["extend", PLAN, "1", "2"]):
            self.refused(*argv, contains="usage")

    def test_a_review_that_is_missing_closed_unsealed_or_rolled_back_is_not_extended(self):
        self.refused("extend", PLAN, "1", contains="no review")
        self.reviewed(closed="2026-01-01T00:00:00Z")
        self.refused("extend", PLAN, "1", contains="closed")
        self.reviewed(closed=None)
        self.set_mark(key_of("plan", PLAN), 3, 0, 1)
        self.refused("extend", PLAN, "1", contains="rolled back")
        self.set_mark(key_of("plan", PLAN), 0, 0, 1)
        os.unlink(self.store_path("seal-key"))
        self.refused("extend", PLAN, "1", contains="unsealed")


class Reset(support_review.Review):
    def test_it_opens_a_fresh_window_after_the_last_round_and_keeps_the_rounds(self):
        self.reviewed(("major",))
        self.document("extend", PLAN, "2")
        got = self.document("reset", PLAN)
        self.assertEqual((0, 1, 3), (got["rounds_used"], got["rounds_total"], got["bound"]))
        state = self.state()
        self.assertEqual({"first": 2, "bound": 3}, state["window"])
        self.assertEqual(1, len(state["rounds"]))

    def test_a_finding_of_the_old_window_no_longer_blocks(self):
        self.reviewed(("major",))
        self.assertEqual(["R1-F1"], self.helper.pending(self.state()))
        self.document("reset", PLAN)
        self.assertEqual([], self.helper.pending(self.state()))

    def test_a_review_with_no_rounds_is_reset_as_well(self):
        self.document("init", PLAN)
        self.document("reset", PLAN)
        self.assertEqual({"first": 1, "bound": 3}, self.state()["window"])

    def test_a_closed_review_is_not_reset_and_a_missing_one_is_refused(self):
        self.refused("reset", PLAN, contains="no review")
        self.reviewed(closed="2026-01-01T00:00:00Z")
        self.refused("reset", PLAN, contains="closed")

    def test_an_unsealed_review_is_set_right_and_the_mark_follows_its_counts(self):
        self.reviewed(("major",))
        state = self.state()
        state["window"]["bound"] = 5
        self.write(self.state_rel("plan", PLAN), json.dumps(state))
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])
        got = self.document("reset", PLAN)
        self.assertEqual(("ok", 3), (got["seal"], got["bound"]))
        self.assertEqual("ok", self.document("status", PLAN)["seal"])

    def test_a_review_with_no_key_gets_one_and_is_sealed_again(self):
        self.reviewed()
        os.unlink(self.store_path("seal-key"))
        self.assertEqual("ok", self.document("reset", PLAN)["seal"])
        self.assertEqual(32, len(self.key()))

    def test_a_rolled_back_review_is_set_right_and_the_mark_is_lowered_to_it(self):
        self.reviewed(("major",))
        self.set_mark(key_of("plan", PLAN), 5, 4, 1)
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])
        self.assertEqual("ok", self.document("reset", PLAN)["seal"])
        with open(self.store_path("marks", key_of("plan", PLAN))) as handle:
            mark = json.load(handle)
        self.assertEqual((1, 0), (mark["rounds"], mark["decisions"]))
        self.assertGreater(mark["generation"], 1)

    def test_a_state_that_is_gone_after_rounds_were_sealed_starts_again_empty(self):
        self.reviewed(("major",))
        self.set_mark(key_of("plan", PLAN), 2, 0, 7)
        os.unlink(self.path(self.state_rel("plan", PLAN)))
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])
        got = self.document("reset", PLAN)
        self.assertEqual(("ok", 0), (got["seal"], got["rounds_total"]))
        with open(self.store_path("marks", key_of("plan", PLAN))) as handle:
            mark = json.load(handle)
        self.assertEqual((0, 0), (mark["rounds"], mark["decisions"]))
        self.assertGreater(mark["generation"], 7)

    def test_a_state_that_cannot_be_read_is_not_reset(self):
        self.reviewed()
        self.write(self.state_rel("plan", PLAN), "not json")
        self.refused("reset", PLAN, contains="removes its directory")

    def test_a_seal_key_that_is_not_usable_is_never_replaced(self):
        self.reviewed()
        with open(self.store_path("seal-key"), "wb") as handle:
            handle.write(b"short")
        self.refused("reset", PLAN, contains="seal key")
        with open(self.store_path("seal-key"), "rb") as handle:
            self.assertEqual(b"short", handle.read())

    def test_setting_right_a_replayed_copy_says_what_it_replaced(self):
        self.reviewed(("major",))
        older = self.read(self.state_rel("plan", PLAN))
        self.document("decide", PLAN, "R1-F1", "applied")
        self.document("archive", PLAN)
        self.write(self.state_rel("plan", PLAN), older, binary=True)
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])
        got = self.document("reset", PLAN)
        self.assertEqual((None, 0), (got["closed"], got["decisions_total"]))
        self.assertEqual({"seal": "rolled_back", "closed": None, "rounds": 1, "decisions": 0,
                          "mark": {"rounds": 1, "decisions": 1}}, got["replaced"])

    def test_setting_right_an_unsealed_state_says_what_its_file_claimed(self):
        self.reviewed(("major",))
        state = self.state()
        state["decisions"] = [decision_entry("R1-F1", "rejected", "made up")]
        self.write(self.state_rel("plan", PLAN), json.dumps(state))
        got = self.document("reset", PLAN)
        self.assertEqual({"seal": "unsealed", "closed": None, "rounds": 1, "decisions": 1,
                          "mark": {"rounds": 0, "decisions": 0}}, got["replaced"])
        self.assertEqual(1, got["decisions_total"])   # the decision it claimed is now sealed: the owner was told

    def test_setting_right_a_state_that_is_gone_says_so(self):
        self.reviewed(("major",))
        self.set_mark(key_of("plan", PLAN), 2, 1, 7)
        os.unlink(self.path(self.state_rel("plan", PLAN)))
        self.assertEqual({"seal": "rolled_back", "closed": None, "rounds": None, "decisions": None,
                          "mark": {"rounds": 2, "decisions": 1}}, self.document("reset", PLAN)["replaced"])

    def test_a_generation_at_its_largest_is_refused_with_the_way_out_and_the_way_out_works(self):
        self.reviewed(("major",))
        state = self.state()
        state["generation"] = 2147483647
        self.write(self.state_rel("plan", PLAN), json.dumps(state))
        self.refused("reset", PLAN, contains="largest")
        self.set_mark(key_of("plan", PLAN), 1, 0, 1)   # the mark of the round it had sealed
        shutil.rmtree(self.path(self.review_dir("plan", PLAN)))
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])
        self.assertEqual("ok", self.document("reset", PLAN)["seal"])

    def test_a_reset_that_replaces_nothing_says_nothing_of_it(self):
        self.reviewed()
        self.assertNotIn("replaced", self.document("reset", PLAN))

    def test_replaying_the_state_from_before_a_reset_is_rolled_back(self):
        self.reviewed(("major",))
        before = self.read(self.state_rel("plan", PLAN))
        self.document("reset", PLAN)
        self.write(self.state_rel("plan", PLAN), before, binary=True)
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])


class Archive(support_review.Review):
    def test_it_closes_the_review_with_a_time_and_says_so_in_the_ledger(self):
        self.reviewed(("major",))
        got = self.document("archive", PLAN)
        self.assertRegex(got["closed"], TIME)
        self.assertEqual(got["closed"], self.state()["closed"])
        ledger = self.read(self.review_dir("plan", PLAN) + "/ledger.md").decode()
        self.assertIn("Closed: " + got["closed"], ledger)
        self.assertIn("Round 1,", ledger)

    def test_findings_with_no_decision_do_not_stop_it(self):
        self.reviewed(("blocker", "major"))
        self.assertRegex(self.document("archive", PLAN)["closed"], TIME)

    def test_a_closed_review_takes_nothing_more(self):
        self.reviewed()
        self.document("archive", PLAN)
        for argv in (["archive", PLAN], ["decide", PLAN, "R1-F1", "applied"], ["amend", PLAN, "R1-F1", "applied"],
                     ["extend", PLAN, "1"], ["reset", PLAN]):
            self.refused(*argv, contains="closed")

    def test_a_missing_unsealed_or_rolled_back_review_is_not_archived(self):
        self.refused("archive", PLAN, contains="no review")
        self.reviewed()
        self.set_mark(key_of("plan", PLAN), 4, 0, 1)
        self.refused("archive", PLAN, contains="rolled back")
        self.assertIsNone(self.state()["closed"])

    def test_the_summary_is_the_ledger_and_the_mark_is_kept(self):
        self.reviewed()
        self.document("archive", PLAN)
        with open(self.store_path("marks", key_of("plan", PLAN))) as handle:
            self.assertEqual(1, json.load(handle)["rounds"])


if __name__ == "__main__":
    unittest.main()
