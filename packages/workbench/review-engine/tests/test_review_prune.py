"""`prune`: which closed reviews are listed, and what `--apply` removes (checklist items 11 and 12 of
`docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment E. No bridge is called."""

import json
import os
import time
import unittest

import support_review
from support_review import NAMESPACE, OTHER_PLAN, PLAN, SPEC, key_of

OLD = "2020-01-01T00:00:00Z"
NEWER = "2020-06-01T00:00:00Z"


class Prune(support_review.Review):
    def listed(self, *argv):
        got = self.document("prune", *argv)
        self.assertEqual((90, ["apply", "removed", "retention_days", "reviews"]),
                         (got["retention_days"], sorted(got)))
        return got

    def test_with_no_reviews_it_lists_nothing(self):
        self.assertEqual({"apply": False, "retention_days": 90, "reviews": [], "removed": []}, self.listed())

    def test_a_closed_review_past_its_retention_is_listed_and_the_others_are_not(self):
        self.reviewed(closed=OLD)
        self.reviewed(path=OTHER_PLAN)
        self.reviewed(path=SPEC, kind="spec")
        got = self.listed()
        self.assertEqual([{"key": key_of("plan", PLAN), "path": PLAN, "closed": OLD}], got["reviews"])

    def test_a_review_closed_just_now_is_not_listed(self):
        self.reviewed()
        self.document("archive", PLAN)
        self.assertEqual([], self.listed()["reviews"])

    def test_a_review_closed_less_than_the_retention_ago_is_not_listed(self):
        recent = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 89 * 86400))
        self.reviewed(closed=recent)
        self.assertEqual([], self.listed()["reviews"])

    def test_the_preview_changes_nothing(self):
        self.reviewed(closed=OLD)
        before = (self.tree(self.root), self.tree(self.store))
        self.listed()
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_apply_removes_the_directory_and_the_mark_of_each_and_only_those(self):
        self.reviewed(closed=OLD)
        self.reviewed(path=OTHER_PLAN)
        self.reviewed(path=SPEC, kind="spec", closed=NEWER)
        self.set_mark(key_of("plan", PLAN), 1, 0, 1)
        sentinel = self.read(PLAN)
        got = self.listed("--apply")
        self.assertEqual(([key_of("plan", PLAN), key_of("spec", SPEC)], True),
                         ([i["key"] for i in got["reviews"]], got["apply"]))
        self.assertEqual(sorted(got["removed"]), sorted(i["key"] for i in got["reviews"]))
        self.assertFalse(os.path.exists(self.path(self.review_dir("plan", PLAN))))
        self.assertFalse(os.path.exists(self.path(self.review_dir("spec", SPEC))))
        self.assertTrue(os.path.isdir(self.path(self.review_dir("plan", OTHER_PLAN))))
        self.assertEqual(sorted([key_of("plan", OTHER_PLAN)]), sorted(os.listdir(self.store_path("marks"))))
        self.assertEqual(sentinel, self.read(PLAN))
        self.assertEqual([], self.listed()["reviews"])

    def test_after_a_prune_the_same_document_can_be_reviewed_again(self):
        self.reviewed(closed=OLD)
        self.listed("--apply")
        self.assertEqual("ok", self.document("init", PLAN)["seal"])
        self.assertEqual("ok", self.document("status", PLAN)["seal"])

    def test_a_review_that_is_open_unsealed_or_rolled_back_is_never_listed(self):
        self.reviewed()
        self.reviewed(path=OTHER_PLAN, closed=OLD)
        os.unlink(self.store_path("seal-key"))
        self.assertEqual([], self.listed()["reviews"])
        self.assertEqual([], self.listed("--apply")["removed"])
        self.assertTrue(os.path.isdir(self.path(self.review_dir("plan", OTHER_PLAN))))

    def test_a_closed_review_whose_state_was_edited_is_not_listed(self):
        self.reviewed(closed=OLD)
        state = self.state()
        state["window"]["bound"] = 5
        self.write(self.state_rel("plan", PLAN), json.dumps(state))
        self.assertEqual([], self.listed()["reviews"])

    def test_a_directory_with_a_file_that_is_not_the_engines_is_left_whole(self):
        self.reviewed(closed=OLD)
        self.write(self.review_dir("plan", PLAN) + "/notes.txt", "mine\n")
        self.assertEqual([], self.listed("--apply")["removed"])
        self.assertTrue(os.path.exists(self.path(self.review_dir("plan", PLAN) + "/notes.txt")))
        self.assertTrue(os.path.exists(self.path(self.state_rel("plan", PLAN))))

    def test_a_directory_in_the_review_directory_is_left_whole(self):
        self.reviewed(closed=OLD)
        os.makedirs(self.path(self.review_dir("plan", PLAN) + "/round-1.json"))
        self.assertEqual([], self.listed("--apply")["removed"])
        self.assertTrue(os.path.exists(self.path(self.state_rel("plan", PLAN))))

    def test_a_link_named_like_a_review_is_neither_listed_nor_followed(self):
        self.reviewed(closed=OLD)
        real = self.path(self.review_dir("plan", PLAN))
        outside = os.path.join(self.base, "outside")
        os.rename(real, outside)
        os.symlink(outside, real)
        self.assertEqual([], self.listed("--apply")["removed"])
        self.assertTrue(os.path.exists(os.path.join(outside, "state.json")))

    def test_a_directory_whose_name_is_not_the_key_of_its_state_is_left_alone(self):
        self.reviewed(closed=OLD)
        os.rename(self.path(self.review_dir("plan", PLAN)), self.path(NAMESPACE + "/plan-0000000000000000"))
        self.assertEqual([], self.listed("--apply")["removed"])
        self.assertTrue(os.path.isdir(self.path(NAMESPACE + "/plan-0000000000000000")))

    def test_names_that_are_not_review_names_are_left_alone(self):
        self.reviewed(closed=OLD)
        self.write(NAMESPACE + "/README", "x\n")
        os.makedirs(self.path(NAMESPACE + "/other"))
        self.listed("--apply")
        self.assertTrue(os.path.exists(self.path(NAMESPACE + "/README")))
        self.assertTrue(os.path.isdir(self.path(NAMESPACE + "/other")))

    def test_remove_review_removes_nothing_when_one_entry_is_a_link(self):
        self.reviewed(closed=OLD)
        directory = self.path(self.review_dir("plan", PLAN))
        target = os.path.join(self.base, "precious")
        with open(target, "w") as handle:
            handle.write("keep\n")
        os.unlink(os.path.join(directory, "ledger.md"))
        os.symlink(target, os.path.join(directory, "ledger.md"))
        with self.assertRaises(self.helper.Refused):
            self.helper.remove_review(self.root, key_of("plan", PLAN))
        with open(target) as handle:
            self.assertEqual("keep\n", handle.read())
        self.assertTrue(os.path.exists(os.path.join(directory, "state.json")))

    def test_only_the_documented_forms_are_taken(self):
        for argv in (["prune", "apply"], ["prune", "--apply", "--x"], ["prune", "--apply", "x"], ["prune", PLAN],
                     ["prune", "--Apply"]):
            self.refused(*argv, contains="usage")

    def test_apply_writes_nothing_outside_the_namespace_and_the_marks(self):
        self.reviewed(closed=OLD)
        before_project, before_store = self.tree(self.root), self.tree(self.store)
        self.listed("--apply")
        changes = [n.replace(os.sep, "/") for n in self.changed(before_project, self.tree(self.root))]
        self.assertTrue(all(n.startswith(NAMESPACE) for n in changes), changes)
        self.assertEqual([os.path.join("projects", self.project_id, "review-engine", "marks", key_of("plan", PLAN))],
                         self.changed(before_store, self.tree(self.store)))


if __name__ == "__main__":
    unittest.main()
