"""`init` and `status`: the arguments, the output object and the refusals (checklist items 10 and 13 of
`docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment C. No bridge is called."""

import json
import os
import unittest

import support_review
from support_review import PLAN, SPEC, decision_entry, key_of, round_entry


class Init(support_review.Review):
    def test_it_makes_the_review_and_prints_its_status(self):
        got = self.document("init", PLAN)
        self.assertEqual({"document": PLAN, "kind": "plan", "key": key_of("plan", PLAN), "seal": "ok", "reason": "",
                          "rounds_used": 0, "rounds_total": 0, "bound": 3, "ceiling": 5, "decisions_total": 0,
                          "closed": None}, got)

    def test_the_state_it_writes_has_exactly_the_documented_fields(self):
        self.document("init", PLAN)
        state = self.state()
        self.assertEqual(["closed", "decisions", "format", "generation", "kind", "path", "rounds", "seal", "window"],
                         sorted(state))
        self.assertEqual((1, "plan", PLAN, {"first": 1, "bound": 3}, [], [], None),
                         (state["format"], state["kind"], state["path"], state["window"], state["rounds"],
                          state["decisions"], state["closed"]))
        self.assertEqual(1, state["generation"])
        self.assertRegex(state["seal"], r"^[0-9a-f]{64}$")

    def test_each_kind_is_found_from_its_directory(self):
        for kind, path in (("plan", PLAN), ("spec", SPEC), ("roadmap", "docs/roadmaps/r.md"),
                           ("adr", "docs/decisions/2026-01-01-d.md")):
            self.assertEqual(kind, self.document("init", path)["kind"])

    def test_a_review_that_exists_is_not_made_again(self):
        self.document("init", PLAN)
        before = self.read(self.state_rel("plan", PLAN))
        self.refused("init", PLAN, contains="already")
        self.assertEqual(before, self.read(self.state_rel("plan", PLAN)))

    def test_a_directory_with_no_state_file_in_the_way_does_not_count_as_a_review(self):
        os.makedirs(self.path(self.review_dir("plan", PLAN)))
        self.assertEqual("ok", self.document("init", PLAN)["seal"])

    def test_a_state_file_that_is_a_link_counts_as_a_review_and_is_not_replaced(self):
        os.makedirs(self.path(self.review_dir("plan", PLAN)))
        os.symlink(os.path.join(self.base, "target"), self.path(self.state_rel("plan", PLAN)))
        self.refused("init", PLAN, contains="already")
        self.assertFalse(os.path.exists(os.path.join(self.base, "target")))

    def test_a_document_that_is_refused_starts_nothing(self):
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("init", "README.md")
        self.refused("init", "../x.md")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))


class Status(support_review.Review):
    def test_it_prints_the_object_of_init_and_says_no_round_has_asked_yet(self):
        made = self.document("init", PLAN)
        self.assertEqual(dict(made, request="none"), self.document("status", PLAN))

    def test_it_counts_the_rounds_of_the_window_and_the_decisions(self):
        self.document("init", PLAN)
        state = self.state()
        state["rounds"] = [round_entry(n) for n in range(1, 5)]
        state["window"] = {"first": 3, "bound": 4}
        state["decisions"] = [decision_entry("R1-F1")]
        state["closed"] = "2026-02-03T04:05:06Z"
        self.forge(state)
        got = self.document("status", PLAN)
        self.assertEqual((2, 4, 4, 1, "2026-02-03T04:05:06Z"),
                         (got["rounds_used"], got["rounds_total"], got["bound"], got["decisions_total"],
                          got["closed"]))

    def test_it_changes_nothing(self):
        self.document("init", PLAN)
        before = (self.tree(self.root), self.tree(self.store))
        self.document("status", PLAN)
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_document_with_no_review_is_refused_and_nothing_is_made(self):
        before = (self.tree(self.root), self.tree(self.store))
        self.refused("status", PLAN, contains="no review")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))

    def test_a_review_whose_directory_is_a_link_is_not_followed(self):
        self.document("init", PLAN)
        directory = self.path(self.review_dir("plan", PLAN))
        os.rename(directory, os.path.join(self.base, "moved"))
        os.symlink(os.path.join(self.base, "moved"), directory)
        got = self.document("status", PLAN)
        self.assertEqual("unsealed", got["seal"])
        self.assertNotIn("rounds_total", got)


class ChangedRequest(support_review.Review):
    """`status` compares the setting now with what the last round asked (checklist item 4)."""

    def asked(self, setting, **last):
        if setting is not None:
            self.write(".workbench/review.json", setting if isinstance(setting, str) else json.dumps(setting))
        self.reviewed()
        state = self.state()
        state["rounds"][0].update(last)
        self.forge(state)
        return self.document("status", PLAN)["request"]

    def test_the_same_setting_is_the_same_request(self):
        self.assertEqual("same", self.asked({"format": 1, "bridge": "ask-codex"}))
        self.assertEqual("same", self.asked({"format": 1, "bridge": "ask-codex", "model": "m", "effort": "low"},
                                            requested={"model": "m", "effort": "low"}))

    def test_a_changed_bridge_model_or_effort_is_a_changed_request(self):
        self.assertEqual("changed", self.asked({"format": 1, "bridge": "other"}))
        self.assertEqual("changed", self.asked({"format": 1, "bridge": "ask-codex", "model": "m"}))
        self.assertEqual("changed", self.asked({"format": 1, "bridge": "ask-codex"},
                                               requested={"model": None, "effort": "high"}))

    def test_a_setting_that_cannot_be_read_is_reported_and_status_still_answers(self):
        self.assertEqual("unreadable", self.asked(None))
        self.assertEqual("unreadable", self.asked("not json"))
        self.assertEqual("unreadable", self.asked({"format": 1}))

    def test_a_review_with_no_round_has_no_request_to_compare(self):
        self.write(".workbench/review.json", json.dumps({"format": 1, "bridge": "other"}))
        self.document("init", PLAN)
        self.assertEqual("none", self.document("status", PLAN)["request"])

    def test_a_review_that_cannot_be_used_prints_no_request(self):
        self.write(self.state_rel("plan", PLAN), "{}")
        got = self.document("status", PLAN)
        self.assertEqual("unsealed", got["seal"])
        self.assertNotIn("request", got)

    def test_status_changes_nothing_when_it_compares(self):
        self.asked({"format": 1, "bridge": "other"})
        before = (self.tree(self.root), self.tree(self.store))
        self.document("status", PLAN)
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))


class Arguments(support_review.Review):
    def test_the_first_argument_must_be_a_command_that_exists(self):
        for argv in ([], ["extend", "3"], ["STATUS", PLAN], ["--help"], [""], ["decide", "R1-F1", "applied"]):
            self.refused(*argv, contains="usage")

    def test_each_command_takes_exactly_one_document(self):
        for argv in (["status"], ["init"], ["status", PLAN, SPEC], ["init", PLAN, "--x"], ["init", ""]):
            self.refused(*argv)

    def test_a_directory_that_is_not_a_project_is_refused(self):
        self.refused("status", PLAN, cwd=self.base, contains="not inside a workbench project")

    def test_a_project_whose_manifest_has_no_seed_is_refused(self):
        self.write(".workbench/manifest.json", "{}\n")
        self.refused("init", PLAN, contains="manifest")

    def test_it_works_from_a_subdirectory_of_the_project(self):
        sub = os.path.join(self.root, "docs", "plans")
        self.assertEqual("plan", self.document("init", PLAN, cwd=sub)["kind"])

    def test_every_object_is_one_line_of_json_and_ascii(self):
        code, out, err = self.call("init", PLAN)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.isascii())
        self.assertEqual(out, json.dumps(json.loads(out), sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
