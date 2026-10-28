"""`preview` and `--digest` for `reset`, `archive`, `amend` and `prune`: the read-only preview of what each would change
or remove, the digest that binds it, and the check of that digest inside the lock. Increment F of the plan
`2026-10-27-levels-for-the-review-workflow` (`extend` is increment E, in `test_review_digest.py`). No bridge is called."""

import contextlib
import json
import os
import re
import unittest
import unittest.mock

import support_review
from support_review import NAMESPACE, OTHER_PLAN, PLAN, key_of, decision_entry

DIGEST = re.compile(r"digest: ([0-9a-f]{32})\n\Z")
GUESS = "0" * 32
OLD = "2020-01-01T00:00:00Z"


class Owner(support_review.Review):
    def preview(self, *argv):
        code, out, err = self.call("preview", *argv)
        self.assertEqual((0, ""), (code, err), out)
        found = DIGEST.search(out)
        self.assertIsNotNone(found, out)
        return found.group(1), out

    def digest(self, *argv):
        return self.preview(*argv)[0]

    def decided(self, **changes):
        """A review with R1-F1 (major) decided as applied."""
        return self.reviewed(decisions=[decision_entry("R1-F1", "applied", "first")], **changes)

    def checked_under_the_lock(self, digest, *argv):
        """Run `argv` with `--digest digest` and say whether every comparison of the digest was made with the lock held."""
        held, seen = [], []
        original_locked, original_compare = self.helper.Guarded.locked, self.helper.hmac.compare_digest

        @contextlib.contextmanager
        def locked(guarded):
            with original_locked(guarded):
                held.append(1)
                try:
                    yield
                finally:
                    held.pop()

        def compare(a, b):
            if digest in (a, b):
                seen.append(bool(held))
            return original_compare(a, b)
        with unittest.mock.patch.object(self.helper.Guarded, "locked", locked), \
                unittest.mock.patch.object(self.helper.hmac, "compare_digest", compare):
            got = self.document(*argv, "--digest", digest)
        return got, seen


class PreviewsWriteNothing(Owner):
    def test_no_preview_writes_anything_or_takes_the_lock(self):
        self.decided(closed=OLD)
        self.reviewed(path=OTHER_PLAN)
        before = (self.tree(self.root), self.tree(self.store))
        with unittest.mock.patch.object(self.helper.Guarded, "locked", side_effect=AssertionError("locked")):
            for argv in (["reset", OTHER_PLAN], ["archive", OTHER_PLAN], ["prune"]):
                self.preview(*argv)
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_the_preview_of_an_amendment_writes_nothing_and_never_takes_the_lock(self):
        self.decided()
        before = (self.tree(self.root), self.tree(self.store))
        with unittest.mock.patch.object(self.helper.Guarded, "locked", side_effect=AssertionError("locked")):
            self.preview("amend", PLAN, "R1-F1", "rejected", "--reason", "because")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_each_preview_ends_with_its_digest_and_names_the_document(self):
        self.decided()
        for argv in (["reset", PLAN], ["archive", PLAN], ["amend", PLAN, "R1-F1", "rejected"]):
            digest, out = self.preview(*argv)
            self.assertTrue(out.endswith("digest: %s\n" % digest), out)
            self.assertTrue(out.startswith("preview of %s\n" % argv[0]), out)
            self.assertIn(PLAN, out)

    def test_the_digest_is_the_same_twice(self):
        self.decided()
        for argv in (["reset", PLAN], ["archive", PLAN], ["amend", PLAN, "R1-F1", "rejected", "--reason", "x"]):
            self.assertEqual(self.digest(*argv), self.digest(*argv))

    def test_a_usage_that_does_not_fit_has_no_preview(self):
        self.decided()
        for argv in (["preview", "reset"], ["preview", "reset", PLAN, "x"], ["preview", "archive"],
                     ["preview", "archive", PLAN, "x"], ["preview", "amend", PLAN, "R1-F1"],
                     ["preview", "amend", PLAN, "R1-F1", "rejected", "--digest", GUESS],
                     ["preview", "amend", PLAN, "R1-F1", "rejected", "--reason"],
                     ["preview", "prune", "--apply"], ["preview", "prune", PLAN], ["preview", "decide", PLAN],
                     ["preview", "status", PLAN], ["preview", "reset", PLAN, "--digest", GUESS]):
            self.refused(*argv, contains="usage")


class Reset(Owner):
    def test_the_digest_of_the_preview_resets_the_window(self):
        self.decided(window={"first": 1, "bound": 5})
        self.document("reset", PLAN, "--digest", self.digest("reset", PLAN))
        self.assertEqual({"first": 2, "bound": 3}, self.state()["window"])

    def test_the_preview_says_where_the_window_goes(self):
        self.decided(window={"first": 1, "bound": 5})
        out = self.preview("reset", PLAN)[1]
        self.assertIn("bound now: 5", out)
        self.assertIn("window after: first 2, bound 3", out)

    def test_a_wrong_digest_changes_nothing(self):
        self.decided(window={"first": 1, "bound": 5})
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("reset", PLAN, "--digest", GUESS, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_the_digest_of_another_document_does_not_reset_this_one(self):
        self.decided()
        self.reviewed(path=OTHER_PLAN)
        self.refused("reset", OTHER_PLAN, "--digest", self.digest("reset", PLAN), contains="digest")
        self.assertEqual({"first": 1, "bound": 3}, self.state(path=OTHER_PLAN)["window"])

    def test_the_digest_of_another_command_does_not_reset(self):
        self.decided()
        self.refused("reset", PLAN, "--digest", self.digest("archive", PLAN), contains="digest")

    def test_a_review_that_changed_after_the_preview_is_refused(self):
        self.decided(window={"first": 1, "bound": 5})
        digest = self.digest("reset", PLAN)
        self.document("decide", PLAN, "R1-F2", "rejected")
        self.refused("reset", PLAN, "--digest", digest, contains="digest")
        self.assertEqual({"first": 1, "bound": 5}, self.state()["window"])

    def test_a_digest_is_good_for_one_reset_only(self):
        self.decided(window={"first": 1, "bound": 5})
        digest = self.digest("reset", PLAN)
        self.document("reset", PLAN, "--digest", digest)
        self.refused("reset", PLAN, "--digest", digest, contains="digest")

    def test_an_unsealed_review_is_previewed_with_what_the_reset_replaces(self):
        self.decided()
        sealed = self.digest("reset", PLAN)
        os.unlink(self.store_path("seal-key"))
        digest, out = self.preview("reset", PLAN)
        self.assertNotEqual(sealed, digest)
        self.assertIn("seal: unsealed", out)
        self.assertIn("replaced", out)
        got = self.document("reset", PLAN, "--digest", digest)
        self.assertEqual("ok", got["seal"])

    def test_an_unsealed_review_edited_after_the_preview_with_the_same_counts_is_refused(self):
        # Nothing vouches for the content of an unsealed state, so the digest must bind the content itself.
        self.reviewed(decisions=[decision_entry("R1-F1", "rejected", "first")])
        os.unlink(self.store_path("seal-key"))
        digest = self.digest("reset", PLAN)
        body = self.state()
        body["decisions"][0]["choice"] = "applied"
        self.write(self.state_rel("plan", PLAN), json.dumps(body))
        self.refused("reset", PLAN, "--digest", digest, contains="digest")
        self.assertEqual("applied", self.state()["decisions"][0]["choice"])

    def test_archive_and_amend_of_an_unsealed_review_are_refused_for_that_whatever_the_digest(self):
        self.decided()
        os.unlink(self.store_path("seal-key"))
        self.refused("archive", PLAN, "--digest", GUESS, contains="unsealed")
        self.refused("amend", PLAN, "R1-F1", "rejected", "--digest", GUESS, contains="unsealed")

    def test_a_rolled_back_review_whose_state_is_gone_is_reset_with_its_digest(self):
        self.decided()
        self.set_mark(key_of("plan", PLAN), 3, 0, 1)
        os.unlink(self.path(self.state_rel("plan", PLAN)))
        digest, out = self.preview("reset", PLAN)
        self.assertIn("replaced", out)
        self.refused("reset", PLAN, "--digest", GUESS, contains="digest")
        self.document("reset", PLAN, "--digest", digest)

    def test_a_rolled_back_review_edited_after_the_preview_is_refused(self):
        self.decided()
        self.set_mark(key_of("plan", PLAN), 3, 0, 1)
        digest = self.digest("reset", PLAN)
        body = self.state()
        body["rounds"][0]["findings"][0]["severity"] = "nit"
        self.write(self.state_rel("plan", PLAN), json.dumps(body))
        self.refused("reset", PLAN, "--digest", digest, contains="digest")

    def test_a_rolled_back_review_is_previewed_and_reset_with_its_digest(self):
        self.decided()
        self.set_mark(key_of("plan", PLAN), 3, 0, 1)
        digest, out = self.preview("reset", PLAN)
        self.assertIn("seal: rolled back", out.replace("_", " "))
        self.refused("reset", PLAN, "--digest", GUESS, contains="digest")
        self.document("reset", PLAN, "--digest", digest)

    def test_a_closed_or_missing_review_has_no_preview(self):
        self.refused("preview", "reset", PLAN, contains="no review")
        self.decided(closed=OLD)
        self.refused("preview", "reset", PLAN, contains="closed")

    def test_without_a_digest_it_works_as_before(self):
        self.decided(window={"first": 1, "bound": 5})
        self.assertEqual(3, self.document("reset", PLAN)["bound"])

    def test_the_digest_is_compared_under_the_lock(self):
        self.decided(window={"first": 1, "bound": 5})
        got, seen = self.checked_under_the_lock(self.digest("reset", PLAN), "reset", PLAN)
        self.assertEqual([True], seen)
        self.assertEqual(3, got["bound"])


class Archive(Owner):
    def test_the_digest_of_the_preview_closes_the_review(self):
        self.decided()
        self.document("archive", PLAN, "--digest", self.digest("archive", PLAN))
        self.assertIsNotNone(self.state()["closed"])

    def test_the_preview_says_what_is_left_open(self):
        self.reviewed()
        out = self.preview("archive", PLAN)[1]
        self.assertIn("rounds: 1", out)
        self.assertIn("undecided: 1", out)

    def test_a_wrong_digest_changes_nothing(self):
        self.decided()
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("archive", PLAN, "--digest", GUESS, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))
        self.assertIsNone(self.state()["closed"])

    def test_the_digest_of_another_document_or_command_does_not_archive(self):
        self.decided()
        self.reviewed(path=OTHER_PLAN)
        self.refused("archive", OTHER_PLAN, "--digest", self.digest("archive", PLAN), contains="digest")
        self.refused("archive", PLAN, "--digest", self.digest("reset", PLAN), contains="digest")
        self.assertIsNone(self.state(path=OTHER_PLAN)["closed"])

    def test_a_review_that_changed_after_the_preview_is_refused(self):
        self.decided()
        digest = self.digest("archive", PLAN)
        self.document("decide", PLAN, "R1-F2", "rejected")
        self.refused("archive", PLAN, "--digest", digest, contains="digest")
        self.assertIsNone(self.state()["closed"])

    def test_a_review_that_was_closed_after_the_preview_is_refused(self):
        self.decided()
        digest = self.digest("archive", PLAN)
        self.document("archive", PLAN)
        self.refused("archive", PLAN, "--digest", digest, contains="closed")

    def test_the_digest_is_compared_under_the_lock(self):
        self.decided()
        _, seen = self.checked_under_the_lock(self.digest("archive", PLAN), "archive", PLAN)
        self.assertEqual([True], seen)

    def test_a_closed_or_missing_review_has_no_preview(self):
        self.refused("preview", "archive", PLAN, contains="no review")
        self.decided(closed=OLD)
        self.refused("preview", "archive", PLAN, contains="closed")


class Amend(Owner):
    def test_the_digest_of_the_preview_amends_the_decision(self):
        self.decided()
        digest = self.digest("amend", PLAN, "R1-F1", "rejected", "--reason", "second")
        got = self.document("amend", PLAN, "R1-F1", "rejected", "--reason", "second", "--digest", digest)
        self.assertEqual(("rejected", "second"), (got["choice"], got["reason"]))
        record = self.state()["decisions"][0]
        self.assertEqual(("rejected", "applied"), (record["choice"], record["earlier"][0]["choice"]))

    def test_the_digest_without_a_reason(self):
        self.decided()
        digest = self.digest("amend", PLAN, "R1-F1", "rejected")
        self.assertEqual("rejected", self.document("amend", PLAN, "R1-F1", "rejected", "--digest", digest)["choice"])

    def test_the_preview_says_what_the_decision_is_and_what_it_becomes(self):
        self.decided()
        out = self.preview("amend", PLAN, "R1-F1", "rejected", "--reason", "second")[1]
        self.assertIn("finding: R1-F1", out)
        self.assertIn("now: applied", out)
        self.assertIn("becomes: rejected", out)
        self.assertIn("second", out)

    def test_the_digest_binds_the_choice_and_the_reason(self):
        self.decided()
        base = self.digest("amend", PLAN, "R1-F1", "rejected", "--reason", "a")
        self.assertNotEqual(base, self.digest("amend", PLAN, "R1-F1", "rejected", "--reason", "b"))
        self.assertNotEqual(base, self.digest("amend", PLAN, "R1-F1", "applied", "--reason", "a"))
        self.assertNotEqual(base, self.digest("amend", PLAN, "R1-F1", "rejected"))
        self.refused("amend", PLAN, "R1-F1", "rejected", "--reason", "b", "--digest", base, contains="digest")
        self.refused("amend", PLAN, "R1-F1", "applied", "--reason", "a", "--digest", base, contains="digest")
        self.assertEqual("applied", self.state()["decisions"][0]["choice"])

    def test_reasons_that_agree_in_their_first_300_characters_have_different_digests(self):
        self.decided()
        head = "x" * 300
        first = self.digest("amend", PLAN, "R1-F1", "rejected", "--reason", head + "a")
        self.assertNotEqual(first, self.digest("amend", PLAN, "R1-F1", "rejected", "--reason", head + "b"))
        self.refused("amend", PLAN, "R1-F1", "rejected", "--reason", head + "b", "--digest", first, contains="digest")

    def test_the_digest_binds_the_whole_of_the_reason_now_recorded(self):
        head = "y" * 300
        self.reviewed(decisions=[decision_entry("R1-F1", "applied", head + "1")])
        first = self.digest("amend", PLAN, "R1-F1", "rejected")
        self.reviewed(decisions=[decision_entry("R1-F1", "applied", head + "2")])
        self.assertNotEqual(first, self.digest("amend", PLAN, "R1-F1", "rejected"))

    def test_the_digest_binds_the_finding(self):
        self.reviewed(decisions=[decision_entry("R1-F1", "applied"), decision_entry("R1-F2", "applied")])
        first = self.digest("amend", PLAN, "R1-F1", "rejected")
        self.assertNotEqual(first, self.digest("amend", PLAN, "R1-F2", "rejected"))
        self.refused("amend", PLAN, "R1-F2", "rejected", "--digest", first, contains="digest")

    def test_a_wrong_digest_changes_nothing(self):
        self.decided()
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("amend", PLAN, "R1-F1", "rejected", "--digest", GUESS, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_decision_that_changed_after_the_preview_is_refused(self):
        self.decided()
        digest = self.digest("amend", PLAN, "R1-F1", "rejected")
        self.document("amend", PLAN, "R1-F1", "rejected", "--reason", "someone else")
        self.refused("amend", PLAN, "R1-F1", "rejected", "--digest", digest, contains="digest")
        self.assertEqual("someone else", self.state()["decisions"][0]["reason"])

    def test_a_finding_with_no_decision_or_that_is_not_one_has_no_preview(self):
        self.decided()
        self.refused("preview", "amend", PLAN, "R1-F2", "rejected", contains="no decision")
        self.refused("preview", "amend", PLAN, "R9-F9", "rejected", contains="no round")
        self.refused("preview", "amend", PLAN, "nope", "rejected", contains="not a finding")
        self.refused("preview", "amend", PLAN, "R1-F1", "maybe", contains="applied or rejected")

    def test_decide_still_takes_no_digest(self):
        self.reviewed()
        self.refused("decide", PLAN, "R1-F1", "applied", "--digest", GUESS, contains="usage")
        self.refused("decide", PLAN, "R1-F1", "applied", "--reason", "x", "--digest", GUESS, contains="usage")

    def test_a_reason_that_reads_like_a_digest_flag_is_still_only_a_reason(self):
        self.decided()
        got = self.document("amend", PLAN, "R1-F1", "rejected", "--reason", "--digest")
        self.assertEqual("--digest", got["reason"])

    def test_the_digest_is_compared_under_the_lock(self):
        self.decided()
        digest = self.digest("amend", PLAN, "R1-F1", "rejected")
        _, seen = self.checked_under_the_lock(digest, "amend", PLAN, "R1-F1", "rejected")
        self.assertEqual([True], seen)


class Prune(Owner):
    def closed_review(self, path=PLAN):
        self.reviewed(path=path, closed=OLD)

    def test_the_preview_lists_what_would_be_removed(self):
        self.closed_review()
        self.reviewed(path=OTHER_PLAN)
        out = self.preview("prune")[1]
        self.assertIn("preview of prune", out)
        self.assertIn(key_of("plan", PLAN), out)
        self.assertIn(PLAN, out)
        self.assertIn(OLD, out)
        self.assertNotIn(key_of("plan", OTHER_PLAN), out)

    def test_the_preview_of_nothing_has_a_digest_too(self):
        self.assertEqual(32, len(self.digest("prune")))

    def test_the_digest_of_the_preview_removes_those_reviews(self):
        self.closed_review()
        got = self.document("prune", "--apply", "--digest", self.digest("prune"))
        self.assertEqual([key_of("plan", PLAN)], got["removed"])
        self.assertFalse(os.path.exists(self.path(self.review_dir("plan", PLAN))))

    def test_the_digest_of_an_empty_list_removes_nothing(self):
        digest = self.digest("prune")
        self.closed_review()
        self.refused("prune", "--apply", "--digest", digest, contains="digest")
        self.assertTrue(os.path.exists(self.path(self.state_rel("plan", PLAN))))

    def test_a_list_that_changed_between_the_preview_and_the_run_is_refused_and_nothing_is_removed(self):
        self.closed_review()
        digest = self.digest("prune")
        self.closed_review(OTHER_PLAN)
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("prune", "--apply", "--digest", digest, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_list_that_lost_a_review_is_refused(self):
        self.closed_review()
        self.closed_review(OTHER_PLAN)
        digest = self.digest("prune")
        self.document("prune", "--apply", "--digest", self.digest("prune"))
        self.closed_review()
        self.refused("prune", "--apply", "--digest", digest, contains="digest")
        self.assertTrue(os.path.exists(self.path(self.state_rel("plan", PLAN))))

    def test_a_wrong_digest_removes_nothing(self):
        self.closed_review()
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("prune", "--apply", "--digest", GUESS, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_digest_is_good_for_one_removal_only(self):
        self.closed_review()
        digest = self.digest("prune")
        self.document("prune", "--apply", "--digest", digest)
        self.refused("prune", "--apply", "--digest", digest, contains="digest")

    def test_a_digest_is_for_apply_only(self):
        self.closed_review()
        self.refused("prune", "--digest", self.digest("prune"), contains="usage")
        self.assertTrue(os.path.exists(self.path(self.state_rel("plan", PLAN))))

    def test_without_a_digest_it_lists_and_applies_as_before(self):
        self.closed_review()
        self.assertEqual([key_of("plan", PLAN)], [r["key"] for r in self.document("prune")["reviews"]])
        self.assertEqual([key_of("plan", PLAN)], self.document("prune", "--apply")["removed"])

    def test_the_digest_is_compared_under_the_lock(self):
        self.closed_review()
        digest = self.digest("prune")
        held, seen = [], []
        original_locked, original_compare = self.helper.Guarded.locked, self.helper.hmac.compare_digest

        @contextlib.contextmanager
        def locked(guarded):
            with original_locked(guarded):
                held.append(1)
                try:
                    yield
                finally:
                    held.pop()

        def compare(a, b):
            if digest in (a, b):
                seen.append(bool(held))
            return original_compare(a, b)
        with unittest.mock.patch.object(self.helper.Guarded, "locked", locked), \
                unittest.mock.patch.object(self.helper.hmac, "compare_digest", compare):
            self.document("prune", "--apply", "--digest", digest)
        self.assertEqual([True], seen)


class FormOfTheDigest(Owner):
    def test_a_digest_that_is_not_32_lowercase_hex_is_refused_before_anything_is_read(self):
        self.decided(closed=None)
        good = self.digest("reset", PLAN)
        before = (self.tree(self.root), self.tree(self.store))
        for bad in (good[:31], good + "0", good.upper(), "g" * 32, "", good + "\n", " " + good[1:]):
            with self.subTest(bad=bad):
                for argv in (["reset", PLAN], ["archive", PLAN], ["amend", PLAN, "R1-F1", "rejected"],
                             ["prune", "--apply"]):
                    self.refused(*argv, "--digest", bad, contains="digest")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_the_digest_must_be_the_last_two_arguments(self):
        self.decided()
        good = self.digest("reset", PLAN)
        for argv in (["reset", PLAN, "--digest"], ["reset", PLAN, good], ["reset", "--digest", good, PLAN],
                     ["reset", PLAN, "--digest", good, "--digest", good],
                     ["archive", "--digest", good, PLAN], ["prune", "--digest", good, "--apply"],
                     ["amend", PLAN, "--digest", good, "R1-F1", "rejected"]):
            self.refused(*argv, contains="usage")

    def test_recompute_does_not_leak_into_the_error(self):
        self.decided()
        err = self.refused("reset", PLAN, "--digest", GUESS, contains="digest")
        self.assertNotIn(self.digest("reset", PLAN), err)


if __name__ == "__main__":
    unittest.main()
