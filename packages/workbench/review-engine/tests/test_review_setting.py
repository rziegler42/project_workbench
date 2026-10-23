"""The project setting `.workbench/review.json`: strict, bounded, a request and never an authorization (checklist
item 4 of `docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment D."""

import json
import os
import unittest

import support_review

NAME = ".workbench/review.json"


class Setting(support_review.Review):
    def read(self, text=None, **fields):
        if text is not None:
            self.write(NAME, text, binary=isinstance(text, bytes))
        elif fields:
            self.write(NAME, json.dumps(fields))
        return self.helper.read_setting(self.root)

    def refused(self, text=None, contains=NAME, **fields):
        with self.assertRaises(self.helper.Refused) as caught:
            self.read(text, **fields)
        self.assertIn(contains, str(caught.exception))
        return str(caught.exception)

    def test_a_bridge_alone_is_a_setting_with_no_model_and_no_effort(self):
        got = self.read(format=1, bridge="ask-codex")
        self.assertEqual(("ask-codex", None, None), (got.bridge, got.model, got.effort))

    def test_a_model_and_an_effort_are_read(self):
        got = self.read(format=1, bridge="ask-codex", model="gpt-5.1:mini", effort="high")
        self.assertEqual(("ask-codex", "gpt-5.1:mini", "high"), (got.bridge, got.model, got.effort))

    def test_each_effort_level_is_read(self):
        for level in ("low", "medium", "high"):
            self.assertEqual(level, self.read(format=1, bridge="b", effort=level).effort)

    def test_a_missing_file_is_a_refusal_that_names_it_and_no_bridge_is_chosen(self):
        text = self.refused()
        self.assertIn("bridge", text)

    def test_a_file_that_is_not_one_strict_object_is_a_refusal(self):
        for text in ("", "not json", "[]", "null", '{"format": 1, "bridge": "b"', '{"format": 1, "format": 1}',
                     '{"format": 1.0, "bridge": "b"}', b"\xff\xfe", '{"format": 1, "bridge": "\\ud800"}'):
            self.refused(text)

    def test_a_file_over_its_bound_is_a_refusal(self):
        self.refused(json.dumps({"format": 1, "bridge": "b", "model": "m" * 5000}))
        self.write(NAME, json.dumps({"format": 1, "bridge": "b"}) + " " * 4097)
        self.refused(None)

    def test_the_format_must_be_the_whole_number_one(self):
        for value in (2, 0, "1", True, None, [1]):
            self.refused(json.dumps({"format": value, "bridge": "b"}), contains="format")

    def test_a_setting_with_no_bridge_is_a_refusal_that_names_the_file(self):
        self.refused(json.dumps({"format": 1}), contains="bridge")
        self.refused(json.dumps({"format": 1, "model": "m"}), contains="bridge")

    def test_a_bridge_must_be_one_command_name(self):
        for bad in ("", " ", "a b", "-a", "../x", "a/b", "a;b", "$(x)", "x" * 65, 1, None, ["a"], "a\nb", "é"):
            self.refused(json.dumps({"format": 1, "bridge": bad}), contains="bridge")
        self.read(format=1, bridge="x" * 64)

    def test_a_model_is_the_bridges_own_charset_and_length(self):
        for bad in ("", "-m", ".m", "m m", "m;m", "m/m", "m" * 65, 1, ["m"], "m\n"):
            self.refused(json.dumps({"format": 1, "bridge": "b", "model": bad}), contains="model")
        self.read(format=1, bridge="b", model="m" * 64)

    def test_an_effort_is_one_of_three_levels(self):
        for bad in ("", "max", "HIGH", " high", 1, ["high"]):
            self.refused(json.dumps({"format": 1, "bridge": "b", "effort": bad}), contains="effort")

    def test_an_unknown_field_is_a_refusal(self):
        self.refused(json.dumps({"format": 1, "bridge": "b", "retries": 3}), contains="retries")
        self.refused(json.dumps({"format": 1, "bridge": "b", "vendor": "x"}), contains="vendor")

    def test_a_setting_that_is_a_link_or_not_a_file_is_a_refusal(self):
        os.symlink(os.path.join(self.base, "elsewhere.json"), self.path(NAME))
        self.refused(None)

    def test_reading_the_setting_changes_nothing(self):
        self.write(NAME, json.dumps({"format": 1, "bridge": "b"}))
        before = (self.tree(self.root), self.tree(self.store))
        self.helper.read_setting(self.root)
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))


if __name__ == "__main__":
    unittest.main()
