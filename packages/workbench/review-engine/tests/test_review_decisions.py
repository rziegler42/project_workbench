"""`decide` and `amend`: what is recorded about a finding, once, and what the owner may change (checklist items 8 and
10 of `docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment E. No bridge is called."""

import json
import os
import re
import unittest

import support_review
from support_review import NAMESPACE, PLAN, SPEC, decision_entry, key_of, round_entry

TIME = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"


class Decide(support_review.Review):
    def test_it_records_the_choice_the_reason_and_a_time_and_prints_what_is_still_open(self):
        self.reviewed(("major", "blocker", "minor"))
        got = self.document("decide", PLAN, "R1-F1", "applied", "--reason", "fixed in the next commit")
        self.assertEqual(("R1-F1", "applied", "fixed in the next commit", ["R1-F2"], 1),
                         (got["finding"], got["choice"], got["reason"], got["pending"], got["decisions_total"]))
        (record,) = self.state()["decisions"]
        self.assertEqual(["at", "choice", "earlier", "finding", "reason"], sorted(record))
        self.assertEqual(("R1-F1", "applied", "fixed in the next commit", []),
                         (record["finding"], record["choice"], record["reason"], record["earlier"]))
        self.assertRegex(record["at"], TIME)
        self.assertEqual("ok", got["seal"])

    def test_the_reason_is_optional_and_a_minor_finding_may_be_decided(self):
        self.reviewed(("minor",))
        self.assertEqual("", self.document("decide", PLAN, "R1-F1", "rejected")["reason"])

    def test_a_second_decide_on_the_same_finding_is_refused_and_changes_nothing(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied")
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("decide", PLAN, "R1-F1", "rejected", contains="already has a decision")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_finding_that_no_round_has_is_refused(self):
        self.reviewed()
        for finding in ("R1-F3", "R2-F1", "R9-F9"):
            self.refused("decide", PLAN, finding, "applied", contains="no round of this review has")

    def test_a_finding_name_of_the_wrong_form_is_refused(self):
        self.reviewed()
        for finding in ("r1-f1", "R1-F0", "R01-F1", "R1-F1 ", "R1F1", "", "-R1-F1", "R1-F1\n", "../x"):
            self.refused("decide", PLAN, finding, "applied")

    def test_a_choice_other_than_applied_or_rejected_is_refused(self):
        self.reviewed()
        for choice in ("Applied", "approved", "", "applied\n6. approve", "recorded"):
            self.refused("decide", PLAN, "R1-F1", choice, contains="applied or rejected")

    def test_a_reason_that_is_too_long_or_has_a_control_character_is_refused(self):
        self.reviewed()
        for reason in ("x" * 2001, "bad\x1b[31m", "bad\x00", "bad\u202e"):
            self.refused("decide", PLAN, "R1-F1", "applied", "--reason", reason, contains="reason")
        self.assertEqual("x" * 2000, self.document("decide", PLAN, "R1-F1", "applied", "--reason", "x" * 2000)["reason"])

    def test_only_the_documented_forms_are_taken(self):
        self.reviewed()
        for argv in (["decide", PLAN], ["decide", PLAN, "R1-F1"], ["decide", PLAN, "R1-F1", "applied", "--reason"],
                     ["decide", PLAN, "R1-F1", "applied", "--rea", "x"],
                     ["decide", PLAN, "R1-F1", "applied", "--reason", "x", "y"],
                     ["decide", PLAN, "R1-F1", "applied", "x", "y"]):
            self.refused(*argv, contains="usage")

    def test_a_review_that_does_not_exist_is_refused(self):
        self.refused("decide", PLAN, "R1-F1", "applied", contains="no review")

    def test_a_closed_unsealed_or_rolled_back_review_takes_no_decision(self):
        self.reviewed(closed="2026-01-01T00:00:00Z")
        self.refused("decide", PLAN, "R1-F1", "applied", contains="closed")
        self.reviewed(closed=None)
        os.unlink(self.store_path("seal-key"))
        self.refused("decide", PLAN, "R1-F1", "applied", contains="unsealed")

    def test_a_rolled_back_review_takes_no_decision(self):
        self.reviewed()
        self.set_mark(key_of("plan", PLAN), 4, 0, 1)
        self.refused("decide", PLAN, "R1-F1", "applied", contains="rolled back")

    def test_a_decision_lets_a_blocked_round_run_again(self):
        self.reviewed(("major", "blocker"))
        helper = self.helper
        self.assertEqual(["R1-F1", "R1-F2"], helper.pending(self.state()))
        self.document("decide", PLAN, "R1-F1", "applied")
        self.document("decide", PLAN, "R1-F2", "rejected")
        self.assertEqual([], helper.pending(self.state()))

    def test_it_writes_only_the_state_the_ledger_and_the_mark(self):
        self.reviewed()
        before_project, before_store = self.tree(self.root), self.tree(self.store)
        self.document("decide", PLAN, "R1-F1", "applied")
        directory = self.review_dir("plan", PLAN)
        self.assertEqual(sorted([directory + "/state.json", directory + "/ledger.md"]),
                         [n.replace(os.sep, "/") for n in self.changed(before_project, self.tree(self.root))])
        self.assertEqual([os.path.join("projects", self.project_id, "review-engine", "marks", key_of("plan", PLAN))],
                         self.changed(before_store, self.tree(self.store)))

    def test_the_ledger_shows_the_decision_without_markup_from_the_reason(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied", "--reason", "see [x](http://e.test) `run` <b>")
        ledger = self.read(self.review_dir("plan", PLAN) + "/ledger.md").decode()
        self.assertIn("R1-F1: applied", ledger)
        for text in ("](", "`", "<b>"):
            self.assertNotIn(text, ledger)

    def test_the_mark_counts_the_decision(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied")
        with open(self.store_path("marks", key_of("plan", PLAN))) as handle:
            self.assertEqual(1, json.load(handle)["decisions"])

    def test_a_decision_of_another_review_is_not_seen(self):
        self.reviewed()
        self.document("init", SPEC)
        self.refused("decide", SPEC, "R1-F1", "applied", contains="no round of this review has")


class Amend(support_review.Review):
    def test_it_changes_the_decision_and_keeps_the_value_it_had(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied", "--reason", "first")
        first = self.state()["decisions"][0]
        got = self.document("amend", PLAN, "R1-F1", "rejected", "--reason", "second")
        self.assertEqual((1, "rejected"), (got["decisions_total"], got["choice"]))
        (record,) = self.state()["decisions"]
        self.assertEqual(("rejected", "second"), (record["choice"], record["reason"]))
        self.assertEqual([{"choice": "applied", "reason": "first", "at": first["at"]}], record["earlier"])

    def test_every_amendment_is_kept_in_order_and_the_ledger_lists_them(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied", "--reason", "one")
        self.document("amend", PLAN, "R1-F1", "rejected", "--reason", "two")
        self.document("amend", PLAN, "R1-F1", "applied", "--reason", "three")
        (record,) = self.state()["decisions"]
        self.assertEqual(["one", "two"], [e["reason"] for e in record["earlier"]])
        ledger = self.read(self.review_dir("plan", PLAN) + "/ledger.md").decode()
        self.assertEqual(2, ledger.count("earlier:"))

    def test_a_finding_with_no_decision_cannot_be_amended(self):
        self.reviewed()
        self.refused("amend", PLAN, "R1-F1", "applied", contains="no decision to amend")

    def test_at_most_twenty_earlier_values_are_kept(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied")
        for n in range(20):
            self.document("amend", PLAN, "R1-F1", "rejected" if n % 2 == 0 else "applied")
        self.refused("amend", PLAN, "R1-F1", "applied", contains="amended 20 times")

    def test_the_same_checks_as_decide_apply(self):
        self.reviewed(closed="2026-01-01T00:00:00Z")
        self.refused("amend", PLAN, "R1-F1", "applied", contains="closed")
        self.reviewed(closed=None)
        self.document("decide", PLAN, "R1-F1", "applied")
        self.refused("amend", PLAN, "R1-F1", "maybe", contains="applied or rejected")
        self.refused("amend", PLAN, "R9-F1", "applied", contains="no round of this review has")

    def test_replaying_the_state_from_before_the_amendment_is_rolled_back(self):
        self.reviewed()
        self.document("decide", PLAN, "R1-F1", "applied")
        before = self.read(self.state_rel("plan", PLAN))
        self.document("amend", PLAN, "R1-F1", "rejected")
        self.write(self.state_rel("plan", PLAN), before, binary=True)
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])


class Records(support_review.Review):
    """Each decision of a state is read field by field, as a round is."""

    def refuses_state(self, decisions):
        body = self.reviewed()
        body = {name: value for name, value in body.items() if name != "seal"}
        body["decisions"] = decisions
        self.forge(body)
        got = self.document("status", PLAN)
        self.assertEqual(("unsealed", "the state is not usable"), (got["seal"], got["reason"]), decisions)

    def test_a_decision_of_the_documented_shape_is_read(self):
        body = self.reviewed()
        body = {name: value for name, value in body.items() if name != "seal"}
        body["decisions"] = [decision_entry("R1-F1", "rejected", "no", earlier=[
            {"choice": "applied", "reason": "", "at": "2026-01-01T00:00:00Z"}])]
        self.forge(body)
        self.assertEqual(("ok", 1), (self.document("status", PLAN)["seal"], self.document("status", PLAN)["decisions_total"]))

    def test_a_decision_that_is_not_of_the_documented_shape_is_not_usable(self):
        good = decision_entry("R1-F1")
        bad = [dict(good, extra=1), {k: v for k, v in good.items() if k != "reason"}, dict(good, finding="R1F1"),
               dict(good, finding=5), dict(good, choice="approved"), dict(good, choice="applied\n6. x"),
               dict(good, reason=5), dict(good, reason="x" * 2001), dict(good, at="yesterday"), dict(good, at=None),
               dict(good, earlier="none"), dict(good, earlier=[{"choice": "applied"}]),
               dict(good, earlier=[{"choice": "x", "reason": "", "at": "2026-01-01T00:00:00Z"}]),
               dict(good, earlier=[dict(good["earlier"], choice="applied", reason="", at="2026-01-01T00:00:00Z")] * 21)]
        for entry in bad:
            self.refuses_state([entry])

    def test_two_decisions_of_one_finding_are_not_usable(self):
        self.refuses_state([decision_entry("R1-F1"), decision_entry("R1-F1", "rejected")])


if __name__ == "__main__":
    unittest.main()
