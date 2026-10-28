"""`preview extend` and `extend ... --digest`: the read-only preview of an extension, the digest that binds it, and the
check of that digest inside the review's lock. Increment E of the plan `2026-10-27-levels-for-the-review-workflow`;
the decision is `2026-10-27-owner-run-arguments-take-a-level`. No bridge is called.

The launcher (``workbench/ownerargs.py``) only checks the form of the digest at `ask`; the check that counts is the
helper's, which is what these tests exercise."""

import contextlib
import os
import re
import unittest
import unittest.mock

import support_review
from support_review import PLAN, OTHER_PLAN, key_of

DIGEST = re.compile(r"digest: ([0-9a-f]{32})\n\Z")
GUESS = "0" * 32


class Preview(support_review.Review):
    def preview(self, *argv):
        code, out, err = self.call("preview", *argv)
        self.assertEqual((0, ""), (code, err), out)
        found = DIGEST.search(out)
        self.assertIsNotNone(found, out)
        return found.group(1), out

    def test_it_prints_what_an_extension_would_change_and_ends_with_the_digest(self):
        self.reviewed()
        digest, out = self.preview("extend", PLAN, "2")
        self.assertEqual(32, len(digest))
        self.assertTrue(out.endswith("digest: %s\n" % digest))
        self.assertIn(PLAN, out)
        self.assertIn("bound now: 3", out)
        self.assertIn("bound after: 5", out)

    def test_it_writes_nothing_and_never_takes_the_lock(self):
        self.reviewed()
        before = (self.tree(self.root), self.tree(self.store))
        with unittest.mock.patch.object(self.helper.Guarded, "locked", side_effect=AssertionError("locked")):
            self.preview("extend", PLAN, "2")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_the_digest_is_the_same_twice(self):
        self.reviewed()
        self.assertEqual(self.preview("extend", PLAN, "2")[0], self.preview("extend", PLAN, "2")[0])

    def test_the_digest_binds_the_number(self):
        self.reviewed()
        self.assertNotEqual(self.preview("extend", PLAN, "1")[0], self.preview("extend", PLAN, "2")[0])

    def test_the_digest_binds_the_document(self):
        self.reviewed()
        self.reviewed(path=OTHER_PLAN)
        self.assertNotEqual(self.preview("extend", PLAN, "1")[0], self.preview("extend", OTHER_PLAN, "1")[0])

    def test_the_digest_binds_the_state_of_the_review(self):
        self.reviewed()
        first = self.preview("extend", PLAN, "1")[0]
        self.document("decide", PLAN, "R1-F1", "applied")
        self.assertNotEqual(first, self.preview("extend", PLAN, "1")[0])

    def test_a_closed_unsealed_missing_or_full_review_has_no_preview(self):
        self.refused("preview", "extend", PLAN, "1", contains="no review")
        self.reviewed(closed="2026-01-01T00:00:00Z")
        self.refused("preview", "extend", PLAN, "1", contains="closed")
        self.reviewed(closed=None, window={"first": 1, "bound": 5})
        self.refused("preview", "extend", PLAN, "1", contains="ceiling of 5")
        self.reviewed(window={"first": 1, "bound": 3})
        self.set_mark(key_of("plan", PLAN), 3, 0, 1)
        self.refused("preview", "extend", PLAN, "1", contains="rolled back")
        self.set_mark(key_of("plan", PLAN), 0, 0, 1)
        os.unlink(self.store_path("seal-key"))
        self.refused("preview", "extend", PLAN, "1", contains="unsealed")

    def test_a_number_that_is_not_from_one_to_five_has_no_preview(self):
        self.reviewed()
        for number in ("0", "6", "x", "", "01", "1 "):
            self.refused("preview", "extend", PLAN, number, contains="1 to 5")

    def test_an_extension_is_previewed_with_exactly_a_document_and_a_number(self):
        self.reviewed()
        for argv in (["preview"], ["preview", "extend"], ["preview", "extend", PLAN],
                     ["preview", "extend", PLAN, "1", "2"], ["preview", "extend", PLAN, "1", "--digest", GUESS]):
            self.refused(*argv, contains="usage")


class Digest(support_review.Review):
    def digest(self, number="2", path=PLAN):
        code, out, err = self.call("preview", "extend", path, number)
        self.assertEqual(0, code, err)
        return DIGEST.search(out).group(1)

    def bound(self):
        return self.state()["window"]["bound"]

    def test_the_digest_of_the_preview_extends_the_bound(self):
        self.reviewed()
        got = self.document("extend", PLAN, "2", "--digest", self.digest("2"))
        self.assertEqual(5, got["bound"])
        self.assertEqual(5, self.bound())

    def test_without_a_digest_it_works_as_before(self):
        self.reviewed()
        self.assertEqual(5, self.document("extend", PLAN, "2")["bound"])

    def test_a_wrong_digest_changes_nothing(self):
        self.reviewed()
        before = self.tree(self.root)
        self.refused("extend", PLAN, "2", "--digest", GUESS, contains="digest")
        self.assertEqual(before, self.tree(self.root))
        self.assertEqual(3, self.bound())

    def test_the_digest_of_one_number_does_not_extend_by_another(self):
        self.reviewed()
        self.refused("extend", PLAN, "2", "--digest", self.digest("1"), contains="digest")
        self.assertEqual(3, self.bound())

    def test_the_digest_of_one_document_does_not_extend_another(self):
        self.reviewed()
        self.reviewed(path=OTHER_PLAN)
        self.refused("extend", OTHER_PLAN, "1", "--digest", self.digest("1", PLAN), contains="digest")
        self.assertEqual(3, self.state(path=OTHER_PLAN)["window"]["bound"])

    def test_a_digest_is_good_for_one_extension_only(self):
        self.reviewed()
        digest = self.digest("1")
        self.document("extend", PLAN, "1", "--digest", digest)
        self.refused("extend", PLAN, "1", "--digest", digest, contains="digest")
        self.assertEqual(4, self.bound())

    def test_a_review_that_changed_after_the_preview_is_refused(self):
        self.reviewed()
        digest = self.digest("1")
        self.document("decide", PLAN, "R1-F1", "applied")
        self.refused("extend", PLAN, "1", "--digest", digest, contains="digest")
        self.assertEqual(3, self.bound())

    def test_a_review_that_was_closed_after_the_preview_is_refused(self):
        self.reviewed()
        digest = self.digest("1")
        self.document("archive", PLAN)
        self.refused("extend", PLAN, "1", "--digest", digest, contains="closed")

    def test_a_digest_that_is_not_32_lowercase_hex_is_refused_before_anything_is_read(self):
        self.reviewed()
        good = self.digest("1")
        for bad in (good[:31], good + "0", good.upper(), "g" * 32, "", good + "\n", " " + good[1:]):
            with self.subTest(bad=bad):
                self.refused("extend", PLAN, "1", "--digest", bad, contains="digest")
        self.assertEqual(3, self.bound())

    def test_the_digest_must_be_the_last_two_arguments(self):
        self.reviewed()
        good = self.digest("1")
        for argv in (["extend", PLAN, "--digest", good, "1"], ["extend", PLAN, "1", "--digest"],
                     ["extend", PLAN, "1", good], ["extend", "--digest", good, PLAN, "1"],
                     ["extend", PLAN, "1", "--digest", good, "--digest", good]):
            self.refused(*argv, contains="usage")
        self.assertEqual(3, self.bound())

    def test_a_bound_that_would_pass_the_ceiling_is_refused_whatever_the_digest(self):
        self.reviewed()
        digest = self.digest("2")
        self.document("extend", PLAN, "1")
        self.refused("extend", PLAN, "3", "--digest", digest, contains="ceiling of 5")

    def test_decide_takes_no_digest(self):
        self.reviewed()
        self.refused("decide", PLAN, "R1-F1", "applied", "--digest", GUESS, contains="usage")

    def test_the_digest_is_compared_with_the_state_that_is_written(self):
        # The comparison is made while the review's lock is held, so no other run can change the state between the
        # comparison and the write.
        self.reviewed()
        digest = self.digest("1")
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
            self.document("extend", PLAN, "1", "--digest", digest)
        self.assertEqual([True], seen)


if __name__ == "__main__":
    unittest.main()
